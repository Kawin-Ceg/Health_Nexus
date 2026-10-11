from fastapi import APIRouter

from app.api.routes import admin, alerts, assistant, auth, onboarding, phc, profile, schedule, settings, vitals

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(onboarding.router)
api_router.include_router(vitals.router)
api_router.include_router(alerts.router)
api_router.include_router(alerts.phc_router)
api_router.include_router(schedule.router)
api_router.include_router(phc.router)
api_router.include_router(settings.router)
api_router.include_router(profile.router)
api_router.include_router(admin.router)
api_router.include_router(assistant.router)
