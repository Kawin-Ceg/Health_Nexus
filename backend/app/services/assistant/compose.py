"""Templated answers: turn a tool's rows into plain sentences without an LLM.

Every number in an answer comes from the rows. When Gemini is configured it
writes the answer instead, from the same rows; these templates are the
fallback and the reference for what a good answer contains.
"""

from datetime import datetime
from typing import Any

from app.core.config import get_settings
from app.services.metrics import VITALS, position
from app.services.visits import format_local

DISCLAIMER = (
    "This is information from your records, not a diagnosis. If you feel unwell, contact your health centre; "
    "in an emergency call 108."
)


def _when(value: Any) -> str:
    if isinstance(value, datetime):
        return format_local(value)
    return str(value)


def _num(value: Any, decimals: int) -> str:
    return f"{float(value):.{decimals}f}"


def _unit(shown: str, unit: str) -> str:
    return f"{shown}{unit}" if unit.startswith(("%", "/")) else f"{shown} {unit}"


def _vital(key: str, value: Any, lower: bool = False) -> str:
    spec = VITALS.get(key)
    if spec is None:
        return f"{key.replace('_', ' ')} {value}"
    label = spec.label.lower() if lower else spec.label
    return f"{label} {_unit(_num(value, spec.decimals), spec.unit)}"


def _vitals_line(vitals: dict[str, Any]) -> str:
    parts: list[str] = []
    if "systolic" in vitals and "diastolic" in vitals:
        bp = f"blood pressure {float(vitals['systolic']):.0f}/{float(vitals['diastolic']):.0f} mmHg"
        flag = {position("systolic", float(vitals["systolic"])), position("diastolic", float(vitals["diastolic"]))}
        parts.append(bp + (" (above normal)" if "above" in flag else " (below normal)" if "below" in flag else ""))
    for key, value in vitals.items():
        if key in ("systolic", "diastolic") or value is None:
            continue
        where = position(key, float(value)) if key in VITALS and VITALS[key].normal else "normal"
        suffix = "" if where == "normal" else f" ({where} normal)"
        parts.append(_vital(key, value, lower=True) + suffix)
    return "; ".join(parts) if parts else "no values"


def _person(row: dict[str, Any]) -> str:
    area = f", {row['area']}" if row.get("area") else ""
    return f"{row['name']} ({row.get('ref', '')}{area})"


def _sev(row: dict[str, Any]) -> str:
    sev = row.get("worst_severity") or row.get("severity")
    return f"{sev}" if sev else ""


def compose(tool_name: str, rows: list[dict[str, Any]], args: dict[str, Any]) -> str:
    fn = _COMPOSERS.get(tool_name)
    return fn(rows, args) if fn else _generic(rows)


def _generic(rows: list[dict[str, Any]]) -> str:
    lines = [", ".join(f"{k.replace('_', ' ')}: {v}" for k, v in r.items()) for r in rows[:10]]
    return "Here is what I found:\n" + "\n".join(f"- {line}" for line in lines)


def _latest(rows, args) -> str:
    r = rows[0]
    status = "It was flagged as unusual" if r["flagged"] else "It was not flagged"
    if r["flagged"] and r.get("resolution"):
        status += f" and a health worker has {r['resolution']} it"
    symptoms = f" You noted: {', '.join(r['symptoms'])}." if r.get("symptoms") else ""
    return (
        f"Your latest reading was on {_when(r['measured_at'])}: {_vitals_line(r['vitals'])}.{symptoms}\n"
        f"{status}.\n\n{DISCLAIMER}"
    )


def _stats(rows, args) -> str:
    lines = []
    for r in rows:
        spec = VITALS.get(r["vital"])
        if spec is None:
            continue
        normal = f" (normal {spec.normal[0]:g}-{spec.normal[1]:g})" if spec.normal else ""
        lines.append(
            f"- {spec.label}: average {_unit(_num(r['average'], spec.decimals), spec.unit)}, lowest {_num(r['lowest'], spec.decimals)}, "
            f"highest {_num(r['highest'], spec.decimals)} over {r['readings']} reading{'s' if r['readings'] != 1 else ''}{normal}"
        )
    return f"Over the last {args['days']} days:\n" + "\n".join(lines) + f"\n\n{DISCLAIMER}"


def _activity(rows, args) -> str:
    r = rows[0]
    if not r["readings_all_time"]:
        return "You have not logged any readings yet. Use Log vitals to add your first one."
    last = f" Your last reading was on {_when(r['last_reading_at'])}." if r["last_reading_at"] else ""
    return (
        f"In the last {args['days']} days you logged {r['readings']} reading{'s' if r['readings'] != 1 else ''}, "
        f"{r['flagged']} of them flagged. All time: {r['readings_all_time']}.{last}"
    )


def _flags(rows, args) -> str:
    lines = []
    for r in rows[:10]:
        reviewed = f", {r['resolution']} by a health worker" if r.get("resolution") else ", not reviewed yet"
        reason = f": {r['reason']}" if r.get("reason") else ""
        lines.append(f"- {_when(r['measured_at'])}, {r['severity']}{reason}{reviewed}")
    more = f"\n(and {len(rows) - 10} more)" if len(rows) > 10 else ""
    return (
        f"{len(rows)} reading{'s were' if len(rows) != 1 else ' was'} flagged in the last {args['days']} days:\n"
        + "\n".join(lines) + more + f"\n\n{DISCLAIMER}"
    )


def _alerts(rows, args) -> str:
    unread = sum(1 for r in rows if not r["is_read"])
    lines = [f"- {_when(r['created_at'])} ({r['severity']}{', unread' if not r['is_read'] else ''}): {r['message']}" for r in rows]
    return f"Your {len(rows)} most recent notifications ({unread} unread):\n" + "\n".join(lines)


def _visits(rows, args) -> str:
    lines = []
    for r in rows:
        where = f" at {r['location']}" if r.get("location") else ""
        why = f", for {r['reason']}" if r.get("reason") else ""
        lines.append(f"- {_when(r['scheduled_for'])}: {r['status']}, with {r['worker']}{where}{why}")
    return "Your visits (last 30 days and upcoming):\n" + "\n".join(lines)


def _centre(rows, args) -> str:
    r = rows[0]
    block = f", {r['block']} block" if r.get("block") else ""
    staff = (
        (f"{r['workers']} health workers review" if r['workers'] != 1 else "1 health worker reviews") + " readings there."
        if r["workers"]
        else "No health worker is assigned there yet, so flagged readings are not reviewed for now."
    )
    return f"Your health centre is {r['name']}{block}, {r['district']}, {r['state']}. {staff}"


def _profile(rows, args) -> str:
    r = rows[0]
    conditions = ", ".join(r["existing_conditions"]) or "none listed"
    meds = ", ".join(r["current_medications"]) or "none listed"
    blood = r["blood_group"] or "not given"
    return (
        f"Your profile: age {r['age']}, {r['gender'].replace('_', ' ')}, blood group {blood}, "
        f"height {r['height_cm']:g} cm, weight {r['weight_kg']:g} kg.\n"
        f"- Existing conditions: {conditions}\n- Current medications: {meds}\n"
        "You can change these in Settings."
    )


def _overview(rows, args) -> str:
    r = rows[0]
    sev = ", ".join(f"{r[s]} {s}" for s in ("critical", "high", "moderate", "low") if r[s])
    return (
        f"Your catchment has {r['citizens']} citizens. {r['citizens_flagged']} have open flags "
        f"({r['open_flags']} flags{': ' + sev if sev else ''}).\n"
        f"In the last {args['days']} days, {r['citizens_submitting']} citizens logged {r['readings']} readings."
    )


def _flagged(rows, args) -> str:
    severity = args.get("severity", "low")
    floor = "" if severity == "low" else " at critical" if severity == "critical" else f" at {severity} or above"
    lines = [
        f"- {_person(r)}: {r['open_flags']} open flag{'s' if r['open_flags'] != 1 else ''}, worst {_sev(r)}, "
        f"last flagged {_when(r['last_flagged_at'])}"
        for r in rows
    ]
    return f"Citizens with open flags{floor}, worst first:\n" + "\n".join(lines)


def _citizen(rows, args) -> str:
    out = []
    for r in rows:
        flags = f"{r['open_flags']} open flag{'s' if r['open_flags'] != 1 else ''}" + (f" (worst {_sev(r)})" if r["open_flags"] else "")
        last = (
            f"Latest reading {_when(r['last_reading_at'])}: {_vitals_line(r['last_vitals'])}."
            if r.get("last_reading_at")
            else "Has never logged a reading."
        )
        visit = f" Next visit: {_when(r['next_visit'])}." if r.get("next_visit") else " No visit booked."
        out.append(f"{_person(r)}: {r['readings']} readings in the last {args['days']} days, {flags}. {last}{visit}")
    head = "" if len(rows) == 1 else f"{len(rows)} citizens match \"{args['name']}\":\n"
    return head + "\n".join(f"- {line}" if len(rows) > 1 else line for line in out)


def _silent(rows, args) -> str:
    lines = [
        f"- {_person(r)}: " + (f"last reading {_when(r['last_reading_at'])}" if r["last_reading_at"] else "never logged")
        for r in rows
    ]
    return f"{len(rows)} citizen{'s have' if len(rows) != 1 else ' has'} logged nothing in {args['days']} days:\n" + "\n".join(lines)


def _schedule(rows, args) -> str:
    lines = [
        f"- {_when(r['scheduled_for'])}: {_person({'name': r['citizen'], 'ref': r.get('ref'), 'area': r.get('area')})}"
        + (" (passed, needs an outcome)" if r["needs_outcome"] else "")
        + (f", {r['reason']}" if r.get("reason") else "")
        for r in rows
    ]
    return f"Your booked visits for the next {args['days']} days:\n" + "\n".join(lines)


def _localities(rows, args) -> str:
    lines = [
        f"- {r['locality']}: {r['flagged']} of {r['citizens']} citizens flagged ({r['flagged'] / r['citizens']:.0%})"
        for r in sorted(rows, key=lambda r: -(r["flagged"] / r["citizens"] if r["citizens"] else 0))
    ]
    return "Open flags by locality (localities under 3 citizens are merged so nobody can be identified):\n" + "\n".join(lines)


def _trend(rows, args) -> str:
    total = sum(r["readings"] for r in rows)
    flags = sum(r["flags"] for r in rows)
    lines = [f"- {r['day']}: {r['readings']} readings, {r['flags']} flagged" for r in rows[-14:]]
    return f"Last {args['days']} days: {total} readings, {flags} flagged.\n" + "\n".join(lines)


def _symptoms(rows, args) -> str:
    lines = [f"- {r['symptom']}: {r['reports']} reports from {r['citizens']} citizen{'s' if r['citizens'] != 1 else ''}" for r in rows]
    return f"Most reported symptoms in the last {args['days']} days:\n" + "\n".join(lines)


def _platform(rows, args) -> str:
    r = rows[0]
    return (
        f"Accounts: {r['citizens']} citizens, {r['phc_workers']} PHC workers, {r['awaiting_approval']} awaiting approval, "
        f"{r['deactivated']} deactivated.\n"
        f"Last {args['days']} days: {r['readings']} readings. Open flags now: {r['open_flags']}.\n"
        f"Waiting on you: {r['pending_applications']} worker applications, {r['open_concerns']} open concerns."
    )


def _pending(rows, args) -> str:
    lines = [
        f"- {r['name']} ({r['email']}{'' if r['email_confirmed'] else ', email not confirmed'}): "
        f"{r['designation'].replace('_', ' ')} at {r['phc_name']}, {r['district']}; applied {_when(r['applied_at'])}"
        for r in rows
    ]
    return f"{len(rows)} application{'s are' if len(rows) != 1 else ' is'} waiting, oldest first:\n" + "\n".join(lines) + "\nReview them under Applications."


def _facilities(rows, args) -> str:
    lines = [
        f"- {r['name']} ({r['district']}): {r['citizens']} citizens, "
        + (f"{r['workers']} worker{'s' if r['workers'] != 1 else ''}" if r["workers"] else "NO active worker")
        + f", {r['open_flags']} open flags"
        for r in rows
    ]
    return "Health centres with registered citizens (uncovered ones first):\n" + "\n".join(lines)


def _unlinked(rows, args) -> str:
    lines = [f"- {r['name']} ({r['email']}), {r['district'] or 'no district'}" for r in rows]
    return f"{len(rows)} approved worker{'s are' if len(rows) != 1 else ' is'} not linked to a health centre and can see no citizens:\n" + "\n".join(lines)


def _concerns(rows, args) -> str:
    lines = [f"- {r['status'].replace('_', ' ')}, {r['category'].replace('_', ' ')}: {r['concerns']} (oldest {_when(r['oldest'])})" for r in rows]
    return "Support concerns by status and category:\n" + "\n".join(lines)


def _signups(rows, args) -> str:
    names = {"user": "citizens", "phc_worker": "PHC workers", "pending_phc": "worker applicants", "admin": "admins"}
    lines = [f"- {names.get(r['role'], r['role'])}: {r['accounts']} ({r['email_confirmed']} confirmed their email)" for r in rows]
    return f"New accounts in the last {args['days']} days:\n" + "\n".join(lines)


def _districts(rows, args) -> str:
    lines = [f"- {r['district']}: {r['citizens']} citizens, {r['readings']} readings, {r['flags']} flagged" for r in rows]
    return f"Activity by district, last {args['days']} days (districts under 3 citizens are left out):\n" + "\n".join(lines)


def _usage(rows, args) -> str:
    names = {"user": "Citizens", "phc_worker": "PHC workers", "admin": "Admins", "pending_phc": "Applicants"}
    lines = [
        f"- {names.get(r['role'], r['role'])}: {r['questions']} questions, {r['not_answered']} not answered"
        + (f", ~{int(r['avg_latency_ms'])} ms per answer" if r.get("avg_latency_ms") is not None else "")
        for r in rows
    ]
    engine = "Gemini" if get_settings().gemini_keys else "the built-in rules (no Gemini key set)"
    return f"Assistant use in the last {args['days']} days, answered by {engine}:\n" + "\n".join(lines)


_COMPOSERS = {
    "my_latest_reading": _latest,
    "my_vital_stats": _stats,
    "my_activity": _activity,
    "my_flags": _flags,
    "my_alerts": _alerts,
    "my_visits": _visits,
    "my_health_centre": _centre,
    "my_profile": _profile,
    "catchment_overview": _overview,
    "flagged_citizens": _flagged,
    "citizen_summary": _citizen,
    "silent_citizens": _silent,
    "my_schedule": _schedule,
    "locality_breakdown": _localities,
    "catchment_trend": _trend,
    "symptom_counts": _symptoms,
    "platform_overview": _platform,
    "pending_applications": _pending,
    "facility_load": _facilities,
    "unlinked_workers": _unlinked,
    "concerns_summary": _concerns,
    "signups": _signups,
    "district_activity": _districts,
    "assistant_usage": _usage,
}
