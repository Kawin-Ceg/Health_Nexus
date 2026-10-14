import uuid

from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import get_current_user, require_user
from app.core.security import (
    ACCESS_TOKEN_TTL,
    REFRESH_COOKIE_NAME,
    REFRESH_COOKIE_PATH,
    REFRESH_TOKEN_TTL,
    create_access_token,
)
from app.db.session import get_session
from app.models import PhcApplication, RefreshToken, User
from app.models.enums import UserRole
from app.schemas.auth import (
    ApplicationOut,
    CitizenRegister,
    ConsentState,
    ConsentUpdate,
    ForgotPasswordRequest,
    LoginRequest,
    Message,
    PhcWorkerRegister,
    ResetPasswordRequest,
    SessionOut,
    TokenRequest,
    TokenResponse,
    UserOut,
)
from app.services import accounts, sessions
from app.services.consent import change_consents, current_consents
from app.services.mailer import send_password_reset_email, send_verification_email

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_refresh_cookie(response: Response, raw: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        raw,
        max_age=int(REFRESH_TOKEN_TTL.total_seconds()),
        httponly=True,
        samesite="lax",
        secure=get_settings().COOKIE_SECURE,
        path=REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        REFRESH_COOKIE_NAME,
        httponly=True,
        samesite="lax",
        secure=get_settings().COOKIE_SECURE,
        path=REFRESH_COOKIE_PATH,
    )


async def _user_out(db: AsyncSession, user: User) -> UserOut:
    out = UserOut.model_validate(user)
    if user.role == UserRole.pending_phc:
        application = await db.scalar(select(PhcApplication).where(PhcApplication.user_id == user.id))
        if application is not None:
            out.application = ApplicationOut.model_validate(application)
    return out


async def _token_response(db: AsyncSession, user: User, row: RefreshToken) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id, user.role.value, row.id),
        expires_in=int(ACCESS_TOKEN_TTL.total_seconds()),
        user=await _user_out(db, user),
    )


# --- Registration -----------------------------------------------------------


@router.post("/register/citizen", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register_citizen(
    data: CitizenRegister, background: BackgroundTasks, db: AsyncSession = Depends(get_session)
) -> UserOut:
    user, token = await accounts.register_citizen(db, data)
    background.add_task(send_verification_email, user.email, user.name, token)
    return await _user_out(db, user)


@router.post("/register/phc-worker", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register_phc_worker(
    data: PhcWorkerRegister, background: BackgroundTasks, db: AsyncSession = Depends(get_session)
) -> UserOut:
    user, token = await accounts.register_phc_worker(db, data)
    background.add_task(send_verification_email, user.email, user.name, token)
    return await _user_out(db, user)


# --- Sign in / out ----------------------------------------------------------


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_session)
) -> TokenResponse:
    user = await accounts.authenticate(db, data.email, data.password)
    raw, row = await sessions.start_session(db, user, request)
    await db.commit()
    _set_refresh_cookie(response, raw)
    return await _token_response(db, user, row)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_session),
    raw_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
):
    if not raw_cookie:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No refresh token.")
    try:
        user, row, raw = await sessions.rotate_session(db, raw_cookie, request)
    except HTTPException as exc:
        failure = JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
        # A race between two tabs: the winner has just set a good cookie, so leave it.
        if exc.detail != sessions.ALREADY_USED:
            _clear_refresh_cookie(failure)
        return failure
    _set_refresh_cookie(response, raw)
    return await _token_response(db, user, row)


@router.post("/logout", response_model=Message)
async def logout(
    response: Response,
    db: AsyncSession = Depends(get_session),
    raw_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
) -> Message:
    if raw_cookie:
        await sessions.revoke_by_token(db, raw_cookie, sessions.REASON_LOGOUT)
        await db.commit()
    _clear_refresh_cookie(response)
    return Message(detail="Signed out.")


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)) -> UserOut:
    return await _user_out(db, user)


# --- Sessions ---------------------------------------------------------------


async def _current_session(
    request: Request, user: User, db: AsyncSession, raw_cookie: str | None
) -> uuid.UUID | None:
    return await sessions.current_session_id(
        db, user.id, raw_cookie, getattr(request.state, "token_session_id", None)
    )


@router.get("/sessions", response_model=list[SessionOut])
async def list_sessions(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    raw_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
) -> list[SessionOut]:
    current = await _current_session(request, user, db, raw_cookie)
    return [
        SessionOut(
            id=row.id,
            device_label=row.device_label,
            ip_address=row.ip_address,
            created_at=row.created_at,
            last_activity_at=row.last_activity_at,
            is_current=row.id == current,
        )
        for row in await sessions.active_sessions(db, user.id)
    ]


@router.post("/sessions/revoke-others", response_model=Message)
async def revoke_other_sessions(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    raw_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
) -> Message:
    current = await _current_session(request, user, db, raw_cookie)
    if current is None:
        # Revoking "everything but this" would sign the caller out too.
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Could not identify your current session.")
    await sessions.revoke_all_for_user(db, user.id, sessions.REASON_USER_REVOKED, except_id=current)
    await db.commit()
    return Message(detail="Signed out of all other sessions.")


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    session_id: uuid.UUID,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    raw_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
) -> Response:
    # Scoped to the caller's own rows: someone else's session id is simply "not found".
    row = await db.scalar(
        select(RefreshToken).where(
            RefreshToken.id == session_id, RefreshToken.user_id == user.id, RefreshToken.revoked.is_(False)
        )
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found.")
    current = await _current_session(request, user, db, raw_cookie)
    sessions.revoke_row(row, sessions.REASON_USER_REVOKED)
    await db.commit()
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    if row.id == current:
        _clear_refresh_cookie(response)
    return response


# --- Email verification -----------------------------------------------------


@router.post("/email/send-verification", response_model=Message)
async def send_verification(
    background: BackgroundTasks, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)
) -> Message:
    token = await accounts.prepare_verification_email(db, user)
    if token is None:
        return Message(detail="Your email is already verified.")
    background.add_task(send_verification_email, user.email, user.name, token)
    return Message(detail="Verification email sent.")


@router.post("/email/verify", response_model=Message)
async def verify_email(data: TokenRequest, db: AsyncSession = Depends(get_session)) -> Message:
    await accounts.redeem_verification(db, data.token)
    return Message(detail="Email verified.")


# --- Password reset ---------------------------------------------------------

_FORGOT_REPLY = "If an account exists for that address, we have sent a link to reset the password."


@router.post("/password/forgot", response_model=Message)
async def forgot_password(
    data: ForgotPasswordRequest, background: BackgroundTasks, db: AsyncSession = Depends(get_session)
) -> Message:
    prepared = await accounts.prepare_password_reset(db, data.email)
    if prepared is not None:
        user, token = prepared
        background.add_task(send_password_reset_email, user.email, user.name, token)
    return Message(detail=_FORGOT_REPLY)


@router.post("/password/reset", response_model=Message)
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_session)) -> Message:
    await accounts.redeem_password_reset(db, data.token, data.new_password)
    return Message(detail="Password updated. Sign in with your new password.")


# --- Consent ----------------------------------------------------------------


@router.patch("/consent", response_model=ConsentState)
async def update_consent(
    data: ConsentUpdate,
    request: Request,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_session),
) -> ConsentState:
    choices = {c.consent_type: c.granted for c in data.consents}
    await change_consents(db, user, choices, source="settings", ip_address=sessions.client_ip(request))
    await db.commit()
    return ConsentState(consents=await current_consents(db, user.id))
