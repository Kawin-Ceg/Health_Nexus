"""Measures the assistant's retrieval and rule-based path on this machine and writes measurements.json.

    cd backend && python ../docs/rag_guide/measure.py        (needs the database running and the demo seed data)

The Gemini timings are not measured here (the free tier allows 5 requests a minute); they are recorded by hand
from complete runs and kept in `gemini_samples` of the JSON file, which this script preserves.
"""

import asyncio
import json
import statistics as st
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import select  # noqa: E402

from app.db.session import SessionLocal, engine  # noqa: E402
from app.models import User  # noqa: E402
from app.services.assistant import retrieve, router, tools_for  # noqa: E402
from app.services.assistant.catalog import TOOLS  # noqa: E402
from app.services.assistant.compose import compose  # noqa: E402

USERS = {
    "user": "citizen.demo@example.com",
    "phc_worker": "phc.worker@example.com",
    "admin": "admin.chennai@admin.example.com",
}
QUESTIONS = {
    "user": ["Is my latest blood pressure normal?", "What were my average vitals over the last 30 days?", "Were any of my readings flagged this month?",
             "When is my next visit?", "Any advisories for my area?", "Which health centre looks after me?"],
    "phc_worker": ["Give me an overview of my catchment", "Who has critical flags right now?", "Who hasn't logged anything in 14 days?",
                   "What symptoms are being reported this week?", "Which localities have the most flags?"],
    "admin": ["Give me a platform overview", "Which PHC applications are waiting?", "Which health centres have citizens but no worker?",
              "How many people signed up in the last 30 days?"],
}


def ms(seconds: float) -> float:
    return round(seconds * 1000, 1)


async def main() -> None:
    old = json.loads((HERE / "measurements.json").read_text(encoding="utf-8")) if (HERE / "measurements.json").exists() else {}
    out: dict = {"gemini_samples": old.get("gemini_samples", []), "gemini_note": old.get("gemini_note", ""), "queries": {}, "rules_path": []}
    async with SessionLocal() as db:
        for role, email in USERS.items():
            user = await db.scalar(select(User).where(User.email == email))
            for tool in tools_for(user.role):
                args = {k: p.default for k, p in tool.params.items()}
                if tool.name == "citizen_summary":
                    args["name"] = "a"
                times, rows = [], 0
                for _ in range(7):
                    t = time.perf_counter()
                    data = await retrieve(tool, args, user, engine)
                    times.append(time.perf_counter() - t)
                    rows = len(data)
                times.sort()
                out["queries"].setdefault(tool.name, {})[role] = {"median_ms": ms(st.median(times)), "max_ms": ms(times[-1]), "rows": rows}
            for q in QUESTIONS[role]:
                t0 = time.perf_counter()
                plan = router.plan(user.role, q)
                t1 = time.perf_counter()
                if plan is None:
                    out["rules_path"].append({"role": role, "question": q, "tool": None})
                    continue
                data = await retrieve(plan.tool, plan.args, user, engine)
                t2 = time.perf_counter()
                text = compose(plan.tool.name, data, plan.args) if data else ""
                t3 = time.perf_counter()
                out["rules_path"].append({"role": role, "question": q, "tool": plan.tool.name, "plan_ms": ms(t1 - t0), "retrieve_ms": ms(t2 - t1),
                                          "compose_ms": ms(t3 - t2), "total_ms": ms(t3 - t0), "rows": len(data)})
    totals = [r["total_ms"] for r in out["rules_path"] if r.get("total_ms") is not None]
    out["rules_summary"] = {"questions": len(out["rules_path"]), "answered": len(totals),
                            "median_ms": round(st.median(totals), 1), "max_ms": round(max(totals), 1)}
    out["tool_count"] = len(TOOLS)
    (HERE / "measurements.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out["rules_summary"]), "queries measured:", sum(len(v) for v in out["queries"].values()))


if __name__ == "__main__":
    asyncio.run(main())
