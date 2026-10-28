"""The API index of a guide, built by scanning the route files and the front-end service files."""

import re

from lib import ROOT, e, find, refline

CITIZEN_ROUTERS = [
    ("auth.py", None, {"register_phc_worker"}, ("router",)),
    ("onboarding.py", None, set(), ("router",)),
    ("vitals.py", None, set(), ("router",)),
    ("alerts.py", None, {"phc_unread_count"}, ("router",)),
    ("schedule.py", {"my_schedule", "explain_missed", "cancel_mine"}, set(), ("router",)),
    ("settings.py", None, set(), ("router",)),
    ("profile.py", None, set(), ("router",)),
    ("assistant.py", None, set(), ("router",)),
]
PLACEHOLDER = re.compile(r"\\\{[^}]*\\\}")

OVERRIDES = {
    ("POST", "/profile/avatar"): ("frontend/src/services/account.ts", "export function uploadImage"),
    ("POST", "/profile/cover"): ("frontend/src/services/account.ts", "export function uploadImage"),
    ("DELETE", "/profile/avatar"): ("frontend/src/services/account.ts", "export const removeImage"),
    ("DELETE", "/profile/cover"): ("frontend/src/services/account.ts", "export const removeImage"),
}


def _service_lines() -> list[tuple[str, str, int, str]]:
    rows = []
    for f in sorted((ROOT / "frontend/src/services").glob("*.ts")):
        lines = f.read_text(encoding="utf-8").split("\n")
        for i, line in enumerate(lines):
            rows.append((lines[i - 1] if i else "", line, i + 1, f"frontend/src/services/{f.name}"))
    return rows


def _caller_regex(full_path: str) -> str:
    """Matches the path as a front-end string, with `${...}` where the route has {id}."""
    return PLACEHOLDER.sub(lambda _m: r"\$\{[^}]*\}", re.escape(full_path))


def rows(routers=CITIZEN_ROUTERS, none_text: str = "no screen uses it yet") -> list[list[str]]:
    calls = _service_lines()
    out = []
    for fname, keep, skip, variables in routers:
        path = f"backend/app/api/routes/{fname}"
        text = (ROOT / path).read_text(encoding="utf-8")
        lines = text.split("\n")
        for var in variables:
            prefix = re.search(rf'^{var} = APIRouter\(prefix="([^"]*)"', text, re.M).group(1)
            decorator = re.compile(rf'^@{var}\.(get|post|patch|delete|put)\("([^"]*)"')
            for i, line in enumerate(lines):
                m = decorator.match(line)
                if not m:
                    continue
                method, sub = m.group(1).upper(), m.group(2)
                nxt = next(l for l in lines[i + 1 : i + 4] if "def " in l)
                name = re.search(r"def (\w+)", nxt).group(1)
                if (keep is not None and name not in keep) or name in skip:
                    continue
                full = prefix + sub
                rx = re.compile(r'["`]' + _caller_regex(full) + r'["`?]')
                verb = re.compile(rf"(?:\.|\b){method.lower()}\s*[<(]")
                hit = next(((svc, ln) for before, t, ln, svc in calls if rx.search(t) and (verb.search(t) or verb.search(before))), None)
                if (method, full) in OVERRIDES:
                    svc, pattern = OVERRIDES[(method, full)]
                    hit = (svc, find(svc, pattern))
                caller = refline(hit[0], hit[1]) if hit else f'<span class="small">{none_text}</span>'
                out.append([f"<b>{method}</b> <code>{e(full)}</code>", refline(path, i + 2), caller])
    return out
