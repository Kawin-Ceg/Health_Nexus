"""Smoke test for a seeded demo database, run against a live API.

    python tests/demo_smoke.py [http://localhost:8000] [password]

Run after `python -m app.seeds.seed_demo` with the backend started. The password defaults
to DEMO_PASSWORD from backend/.env. Read-only: it logs in and reads, it changes no records.
Checks every demo login, each role's main pages, and that roles cannot see each other's data.
"""

import sys

import httpx

API = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/") + "/api/v1"


def demo_password() -> str:
    if len(sys.argv) > 2:
        return sys.argv[2]
    sys.path.insert(0, ".")
    from app.core.config import get_settings

    password = get_settings().DEMO_PASSWORD
    if not password:
        sys.exit("Pass the demo password, or set DEMO_PASSWORD in backend/.env")
    return password


PASSWORD = demo_password()
failures: list[str] = []
passed = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global passed
    if ok:
        passed += 1
        print(f"  ok    {label}")
    else:
        failures.append(label)
        print(f"  FAIL  {label} {detail}")


def login(email: str) -> httpx.Client:
    client = httpx.Client(base_url=API, timeout=30)
    r = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    check(f"login {email}", r.status_code == 200, f"-> {r.status_code} {r.text[:120]}")
    if r.status_code == 200:
        client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return client


def get(client: httpx.Client, path: str, expect: int = 200, label: str | None = None, **params):
    r = client.get(path, params=params)
    check(label or f"GET {path} -> {expect}", r.status_code == expect, f"-> {r.status_code} {r.text[:160]}")
    return r.json() if r.status_code == 200 else None


def main() -> None:
    print(f"API: {API}\n\nAdmin")
    admin = login("admin.demo@example.com")
    o = get(admin, "/admin/overview")
    if o:
        check("admin sees PHC workers and citizens", o["users_by_role"]["phc_worker"] >= 2 and o["users_by_role"]["user"] >= 4)
        check("admin sees pending applications", o["pending_applications"] >= 3)
    get(admin, "/admin/applications")
    get(admin, "/admin/facilities")

    print("\nPHC worker, Mylapore")
    w1 = login("phc.worker@example.com")
    d1 = get(w1, "/phc/dashboard")
    if d1:
        check("Mylapore worker has 28 citizens", d1["citizens"] == 28, f"got {d1['citizens']}")
        check("Mylapore worker has people to review", d1["citizens_flagged"] > 0)
    get(w1, "/phc/worklist")
    get(w1, "/phc/reports", days=30)
    get(w1, "/phc/overview")
    get(w1, "/admin/overview", expect=403, label="worker blocked from admin pages")

    print("\nPHC worker, Adyar")
    w2 = login("tn-chn-phc-002@phc.example.com")
    d2 = get(w2, "/phc/dashboard")
    if d2:
        check("Adyar worker has exactly the 5 Adyar citizens", d2["citizens"] == 5, f"got {d2['citizens']}")
    directory = get(w1, "/phc/citizens", limit=100) or {}
    mylapore_ids = [i["citizen"]["id"] for i in directory.get("items", [])]
    if mylapore_ids:
        r = w2.get(f"/phc/citizens/{mylapore_ids[0]}/record")
        check("Adyar worker cannot open a Mylapore citizen's record", r.status_code in (403, 404), f"-> {r.status_code}")

    print("\nCitizens")
    seen: dict[str, str] = {}
    for email, expect_flags, expect_baseline in [
        ("citizen.demo@example.com", True, True),
        ("adyar.stable@example.com", False, True),
        ("adyar.bp@example.com", True, True),
        ("adyar.glucose@example.com", True, True),
        ("adyar.heartrate@example.com", True, True),
        ("adyar.new@example.com", False, False),
    ]:
        c = login(email)
        me = get(c, "/auth/me", label=f"{email}: own profile")
        if me:
            seen[email] = me["id"]
        s = get(c, "/health/summary", label=f"{email}: dashboard")
        if s:
            check(f"{email}: has readings", len(s["latest"]) > 0)
            check(f"{email}: flagged={expect_flags}", (s["open_flags"] > 0) == expect_flags, f"open_flags={s['open_flags']}")
        b = get(c, "/health/baseline", label=f"{email}: baseline status")
        if b is not None:
            stages = {v["key"]: v["stage"] for v in b["vitals"]}
            learning = all(st == "learning" for st in stages.values())
            check(f"{email}: baseline {'still learning' if not expect_baseline else 'established'}", learning != expect_baseline, str(stages))
        get(c, "/health/history", label=f"{email}: history")
        get(c, "/phc/dashboard", expect=403, label=f"{email}: blocked from PHC pages")
        get(c, "/admin/overview", expect=403, label=f"{email}: blocked from admin pages")

    other = seen.get("adyar.stable@example.com")
    if other:
        r = w1.get(f"/phc/citizens/{other}/record")
        check("Mylapore worker cannot open an Adyar citizen's record", r.status_code in (403, 404), f"-> {r.status_code}")

    print(f"\n{passed} passed, {len(failures)} failed")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
