"""The assistant's retrieval catalog: every SQL query it is able to run.

This is the "SQL-driven" half of the RAG pipeline. The model (or the rule-based
router) only picks one of these tools and fills its declared parameters; it
never writes SQL. Scope binds are added on the server from the signed-in user
and are never parameters:

    :me        the caller's own user id
    :phc_id    the caller's health centre (PHC workers only)
    :district  an admin's district (NULL for a state-wide admin)

So a citizen's tools can only ever read rows with user_id = :me, a worker's
only rows in their catchment, and an admin's only aggregates and account
metadata, never anyone's readings.
"""

import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.models.enums import UserRole
from app.services.consent import COMMUNITY_SQL, WORKER_ACCESS_SQL
from app.services.localities import suppress
from app.services.triage import BANDS, citizen_ref, describe_signal, severity_of

CITIZEN = frozenset({UserRole.user})
WORKER = frozenset({UserRole.phc_worker})
ADMIN = frozenset({UserRole.admin})

# A worker's catchment, as everywhere else in the app (services/catchment.py).
_CATCHMENT = f"u.phc_id = :phc_id AND u.role = 'user' AND {WORKER_ACCESS_SQL}"
# Area-level figures count only citizens who allowed community health monitoring.
_COMMUNITY = COMMUNITY_SQL
_OPEN = "pd.is_anomaly AND pd.resolution IS NULL"
_SINCE = "now() - make_interval(days => :days)"


def _in_district(column: str) -> str:
    """An admin sees only their own district; a state-wide admin (no district) sees all."""
    return f"(CAST(:district AS text) IS NULL OR lower({column}) = lower(CAST(:district AS text)))"


# The advisories one citizen is shown, mirroring api/routes/advisories.targeting.
_FOR_ME = """(
  (a.scope = 'centre' AND a.phc_id = me.phc_id)
  OR (a.scope = 'centre' AND a.radius_km IS NOT NULL AND me.geo_lat IS NOT NULL
      AND power((a.centre_lat - me.geo_lat) * 111, 2)
        + power((a.centre_lng - me.geo_lng) * 111 * cos(radians(me.geo_lat)), 2) <= a.radius_km * a.radius_km)
  OR (a.scope = 'area' AND lower(a.district) = lower(me.district) AND lower(a.area) IN (lower(me.area), lower(me.pincode)))
  OR (a.scope = 'district' AND lower(a.district) = lower(me.district))
  OR (a.scope = 'state' AND lower(a.state) = lower(me.state))
)"""


@dataclass(frozen=True)
class Param:
    kind: str  # "int" | "enum" | "text"
    description: str
    default: Any = None
    lo: int = 1
    hi: int = 365
    choices: tuple[str, ...] = ()
    max_len: int = 80

    def clean(self, value: Any) -> Any:
        """Coerce whatever the model or the router produced; anything odd falls back to the default."""
        if value is None or value == "":
            return self.default
        if self.kind == "int":
            try:
                return max(self.lo, min(self.hi, int(float(value))))
            except (TypeError, ValueError):
                return self.default
        if self.kind == "enum":
            value = str(value).lower().strip()
            return value if value in self.choices else self.default
        text = " ".join(str(value).split())[: self.max_len]
        return text or self.default


@dataclass(frozen=True)
class Tool:
    name: str
    roles: frozenset[UserRole]
    title: str
    description: str
    sql: str
    params: dict[str, Param] = field(default_factory=dict)
    # Rule-based router: (regex, weight). The best total wins.
    patterns: tuple[tuple[str, float], ...] = ()
    needs_facility: bool = False
    # Extra binds derived from the cleaned params, e.g. a severity's score floor.
    derive: Callable[[dict[str, Any]], dict[str, Any]] | None = None
    post: Callable[[list[dict[str, Any]], dict[str, Any]], list[dict[str, Any]]] | None = None


def DAYS(default: int) -> Param:
    return Param("int", "How many days back to look (1-365).", default=default)


def LIMIT(default: int) -> Param:
    return Param("int", "How many rows at most (1-50).", default=default, hi=50)


SEVERITY = Param(
    "enum",
    "Only citizens whose worst open flag is at least this severe.",
    default="low",
    choices=tuple(name for name, _ in BANDS),
)


def _severity_floor(args: dict[str, Any]) -> dict[str, Any]:
    return {"min_score": dict(BANDS)[args["severity"]]}


def _with_refs(rows: list[dict[str, Any]], _: dict[str, Any]) -> list[dict[str, Any]]:
    for row in rows:
        if isinstance(row.get("citizen_id"), uuid.UUID):
            row["ref"] = citizen_ref(row["citizen_id"])
        for key in ("worst_score", "worst_open_score"):
            if row.get(key) is not None:
                row["worst_severity"] = severity_of(float(row[key]))
    return rows


def _flag_rows(rows: list[dict[str, Any]], _: dict[str, Any]) -> list[dict[str, Any]]:
    for row in rows:
        row["severity"] = severity_of(float(row["anomaly_score"]))
        row["reason"] = describe_signal(row.pop("features") or {}, row.get("vitals") or {})
    return rows


def _suppressed(rows: list[dict[str, Any]], _: dict[str, Any]) -> list[dict[str, Any]]:
    folded = suppress({r["locality"]: {"citizens": r["citizens"], "flagged": r["flagged"]} for r in rows})
    return sorted(
        ({"locality": k, **{key: int(v) for key, v in values.items()}} for k, values in folded.items()),
        key=lambda r: -r["citizens"],
    )


_REF = re.compile(r"^HN-([0-9A-F]{8})$", re.IGNORECASE)


def _citizen_match(args: dict[str, Any]) -> dict[str, Any]:
    """A name (substring, case-insensitive) or an HN- reference."""
    raw = args["name"].strip()
    ref = _REF.match(raw)
    if ref:
        return {"pattern": "", "ref_prefix": ref.group(1).lower()}
    escaped = raw.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
    return {"pattern": f"%{escaped}%", "ref_prefix": ""}


TOOLS: tuple[Tool, ...] = (
    # --- Citizens: only their own rows -----------------------------------------------
    Tool(
        name="my_latest_reading",
        roles=CITIZEN,
        title="Your latest reading",
        description="The citizen's most recent reading: each vital, symptoms, and whether it was flagged.",
        sql="""
SELECT hr.timestamp AS measured_at, hr.vitals, hr.symptoms,
       coalesce(pd.is_anomaly, false) AS flagged, pd.anomaly_score, pd.resolution
FROM health_records hr
LEFT JOIN processed_data pd ON pd.health_record_id = hr.id
WHERE hr.user_id = :me
ORDER BY hr.timestamp DESC
LIMIT 1""",
        patterns=(
            (r"\b(latest|last|recent|newest|current)\b.*\b(reading|vitals?|bp|blood pressure|sugar|glucose|temp|temperature|pulse|heart|oxygen|spo2)", 3),
            (r"\b(is|was) my\b.*\b(bp|blood pressure|sugar|glucose|temp|temperature|pulse|heart rate|oxygen|spo2)\b.*\b(ok|okay|normal|high|low|fine|good|bad)", 3),
            (r"\bhow am i\b|\bam i (ok|okay|fine|healthy)\b", 2),
            (r"\bmy (bp|blood pressure|sugar|glucose|temperature|pulse|heart rate|oxygen|spo2)\b", 1.5),
        ),
    ),
    Tool(
        name="my_vital_stats",
        roles=CITIZEN,
        title="Your vitals over time",
        description="Per vital: number of readings, average, lowest and highest over a window of days.",
        sql=f"""
SELECT v.key AS vital, count(*) AS readings,
       round(avg(v.value::numeric), 1) AS average,
       min(v.value::numeric) AS lowest, max(v.value::numeric) AS highest
FROM health_records hr
CROSS JOIN LATERAL json_each_text(hr.vitals) AS v(key, value)
WHERE hr.user_id = :me AND hr.timestamp >= {_SINCE}
GROUP BY v.key
ORDER BY v.key""",
        params={"days": DAYS(30)},
        patterns=(
            (r"\b(average|avg|mean|trend|range|highest|lowest|max|min|over time|usual|typical)\b", 3),
            (r"\b(this|last|past) (week|month|year)\b|\b\d+\s*(day|week|month)s?\b", 1),
        ),
    ),
    Tool(
        name="my_activity",
        roles=CITIZEN,
        title="How often you have logged",
        description="How many readings the citizen logged in a window, how many were flagged, and when the last one was.",
        sql=f"""
SELECT count(*) AS readings,
       count(*) FILTER (WHERE pd.is_anomaly) AS flagged,
       max(hr.timestamp) AS last_reading_at,
       (SELECT count(*) FROM health_records a WHERE a.user_id = :me) AS readings_all_time
FROM health_records hr
LEFT JOIN processed_data pd ON pd.health_record_id = hr.id
WHERE hr.user_id = :me AND hr.timestamp >= {_SINCE}""",
        params={"days": DAYS(30)},
        patterns=(
            (r"\bhow (many|often)\b.*\b(reading|log|logged|submit|record)", 3),
            (r"\b(count|number) of (my )?readings\b", 3),
            (r"\bwhen did i (last )?(log|submit|record)", 3),
        ),
    ),
    Tool(
        name="my_flags",
        roles=CITIZEN,
        title="Your flagged readings",
        description="Readings the model flagged as unusual in a window, with severity, the main reason, and whether a health worker reviewed them.",
        sql=f"""
SELECT hr.timestamp AS measured_at, pd.anomaly_score, pd.features, hr.vitals,
       pd.resolution, pd.reviewed_at
FROM processed_data pd
JOIN health_records hr ON hr.id = pd.health_record_id
WHERE pd.user_id = :me AND pd.is_anomaly AND hr.timestamp >= {_SINCE}
ORDER BY hr.timestamp DESC
LIMIT 20""",
        params={"days": DAYS(90)},
        post=_flag_rows,
        patterns=(
            (r"\b(flag|flagged|unusual|abnormal|anomal|warning|concerning|wrong)\b", 3),
            (r"\bwhy\b.*\b(flag|alert|unusual)", 2),
        ),
    ),
    Tool(
        name="my_alerts",
        roles=CITIZEN | WORKER,
        title="Your notifications",
        description="The caller's most recent notifications (alerts): message, severity, read or not.",
        sql="""
SELECT a.created_at, a.severity, a.message, a.is_read
FROM alerts a
WHERE a.user_id = :me
ORDER BY a.created_at DESC
LIMIT :limit""",
        params={"limit": LIMIT(5)},
        patterns=(
            (r"\b(alert|alerts|notification|notifications|messages?|unread)\b", 3),
        ),
    ),
    Tool(
        name="my_visits",
        roles=CITIZEN,
        title="Your visits",
        description="Home visits booked for the citizen by their health worker, recent and upcoming, with status.",
        sql="""
SELECT sv.scheduled_for, sv.status, sv.reason, sv.location, w.name AS worker
FROM scheduled_visits sv
JOIN users w ON w.id = sv.worker_id
WHERE sv.citizen_id = :me AND sv.scheduled_for >= now() - interval '30 days'
ORDER BY sv.scheduled_for DESC
LIMIT 10""",
        patterns=(
            (r"\b(visit|visits|appointment|appointments|coming to see|home visit|booked)\b", 3),
            (r"\bwhen (is|will)\b.*\b(nurse|worker|someone|doctor)\b", 2),
        ),
    ),
    Tool(
        name="my_health_centre",
        roles=CITIZEN,
        title="Your health centre",
        description="The citizen's linked Primary Health Centre and how many health workers serve it.",
        sql="""
SELECT f.name, f.block, f.district, f.state,
       (SELECT count(*) FROM users w
        WHERE w.phc_id = f.id AND w.role = 'phc_worker' AND w.is_active) AS workers
FROM users u
JOIN valid_phc_facilities f ON f.id = u.phc_id
WHERE u.id = :me""",
        patterns=(
            (r"\b(health cent(re|er)|phc|clinic|facility|hospital)\b", 3),
            (r"\bwho (looks after|reviews|sees)\b", 2),
        ),
    ),
    Tool(
        name="my_profile",
        roles=CITIZEN,
        title="Your health profile",
        description="The citizen's saved profile: age, gender, blood group, existing conditions and current medications.",
        sql="""
SELECT p.age, p.gender, p.blood_group, p.height_cm, p.weight_kg,
       p.existing_conditions, p.current_medications
FROM user_profiles p
WHERE p.user_id = :me""",
        patterns=(
            (r"\b(my profile|blood group|conditions?|medications?|medicines i (take|am on)|my (age|height|weight))\b", 3),
            (r"\bwhat (medicines|medications)\b.*\b(on|taking|listed)\b", 2),
        ),
    ),
    # --- PHC workers: only their catchment --------------------------------------------
    Tool(
        name="catchment_overview",
        roles=WORKER,
        title="Your catchment at a glance",
        description="Headline numbers for the worker's catchment: citizens, citizens flagged, open flags by severity, readings and active citizens in a window.",
        needs_facility=True,
        sql=f"""
WITH c AS (SELECT u.id FROM users u WHERE {_CATCHMENT}),
open AS (
  SELECT pd.user_id, pd.anomaly_score FROM processed_data pd
  WHERE pd.user_id IN (SELECT id FROM c) AND {_OPEN}
)
SELECT (SELECT count(*) FROM c) AS citizens,
       (SELECT count(DISTINCT user_id) FROM open) AS citizens_flagged,
       (SELECT count(*) FROM open) AS open_flags,
       (SELECT count(*) FROM open WHERE anomaly_score >= 0.75) AS critical,
       (SELECT count(*) FROM open WHERE anomaly_score >= 0.5 AND anomaly_score < 0.75) AS high,
       (SELECT count(*) FROM open WHERE anomaly_score >= 0.25 AND anomaly_score < 0.5) AS moderate,
       (SELECT count(*) FROM open WHERE anomaly_score < 0.25) AS low,
       (SELECT count(*) FROM health_records hr
        WHERE hr.user_id IN (SELECT id FROM c) AND hr.timestamp >= {_SINCE}) AS readings,
       (SELECT count(DISTINCT hr.user_id) FROM health_records hr
        WHERE hr.user_id IN (SELECT id FROM c) AND hr.timestamp >= {_SINCE}) AS citizens_submitting""",
        params={"days": DAYS(7)},
        patterns=(
            (r"\b(overview|summary|summarise|summarize|at a glance|how is my (area|catchment|centre|center)|how are things)\b", 3),
            (r"\bhow many (citizens|people|patients)\b", 2),
            (r"\b(open flags|flags open)\b", 1),
        ),
    ),
    Tool(
        name="flagged_citizens",
        roles=WORKER,
        title="Citizens with open flags",
        description="Citizens in the catchment with open (unreviewed) flags, worst first, optionally only at or above a severity.",
        needs_facility=True,
        sql=f"""
SELECT u.id AS citizen_id, u.name, u.area,
       count(*) AS open_flags, max(pd.anomaly_score) AS worst_score,
       max(hr.timestamp) AS last_flagged_at
FROM processed_data pd
JOIN users u ON u.id = pd.user_id
JOIN health_records hr ON hr.id = pd.health_record_id
WHERE {_CATCHMENT} AND {_OPEN}
GROUP BY u.id, u.name, u.area
HAVING max(pd.anomaly_score) >= :min_score
ORDER BY worst_score DESC
LIMIT :limit""",
        params={"severity": SEVERITY, "limit": LIMIT(10)},
        derive=_severity_floor,
        post=_with_refs,
        patterns=(
            (r"\b(who|which (citizens|people|patients))\b.*\b(flag|flagged|attention|review|critical|high risk|urgent|worst|sick)", 4),
            (r"\b(critical|urgent|worst|high[- ]risk|most at risk|need(s)? attention|to review|worklist|queue)\b", 3),
            (r"\bflagged (citizens|people|patients)\b", 3),
        ),
    ),
    Tool(
        name="citizen_summary",
        roles=WORKER,
        title="Citizen lookup",
        description="Look up a citizen in the catchment by name or HN- reference: readings in a window, open flags, latest reading and next visit.",
        needs_facility=True,
        sql=f"""
WITH m AS (
  SELECT u.id, u.name, u.area FROM users u
  WHERE {_CATCHMENT}
    AND ((:pattern <> '' AND u.name ILIKE :pattern)
         OR (:ref_prefix <> '' AND replace(u.id::text, '-', '') LIKE :ref_prefix || '%'))
  ORDER BY u.name
  LIMIT 5
)
SELECT m.id AS citizen_id, m.name, m.area,
       (SELECT count(*) FROM health_records hr
        WHERE hr.user_id = m.id AND hr.timestamp >= {_SINCE}) AS readings,
       (SELECT count(*) FROM processed_data pd WHERE pd.user_id = m.id AND {_OPEN}) AS open_flags,
       (SELECT max(pd.anomaly_score) FROM processed_data pd WHERE pd.user_id = m.id AND {_OPEN}) AS worst_open_score,
       l.timestamp AS last_reading_at, l.vitals AS last_vitals,
       (SELECT min(sv.scheduled_for) FROM scheduled_visits sv
        WHERE sv.citizen_id = m.id AND sv.status = 'scheduled' AND sv.scheduled_for >= now()) AS next_visit
FROM m
LEFT JOIN LATERAL (
  SELECT hr.timestamp, hr.vitals FROM health_records hr
  WHERE hr.user_id = m.id ORDER BY hr.timestamp DESC LIMIT 1
) l ON true""",
        params={"name": Param("text", "The citizen's name (or part of it) or their HN- reference.", default=""), "days": DAYS(30)},
        derive=_citizen_match,
        post=_with_refs,
        patterns=(
            (r"\bHN-[0-9A-F]{8}\b", 5),
            (r"\b(how is|how's|tell me about|look up|lookup|details (of|for|on)|status of|record (of|for))\b", 3),
        ),
    ),
    Tool(
        name="silent_citizens",
        roles=WORKER,
        title="Citizens who have gone quiet",
        description="Active citizens in the catchment with no reading in the last N days (or never), longest silence first.",
        needs_facility=True,
        sql=f"""
SELECT u.id AS citizen_id, u.name, u.area, max(hr.timestamp) AS last_reading_at
FROM users u
LEFT JOIN health_records hr ON hr.user_id = u.id
WHERE {_CATCHMENT} AND u.is_active
GROUP BY u.id, u.name, u.area
HAVING max(hr.timestamp) IS NULL OR max(hr.timestamp) < {_SINCE}
ORDER BY last_reading_at NULLS FIRST
LIMIT :limit""",
        params={"days": DAYS(14), "limit": LIMIT(15)},
        post=_with_refs,
        patterns=(
            (r"\b(silent|quiet|inactive|stopped|not (logged|logging|submitted|submitting)|(haven'?t|hasn'?t|have not|has not|didn'?t|did not) (logged|log|submitted|submit)|never logged|no readings?)\b", 4),
        ),
    ),
    Tool(
        name="my_schedule",
        roles=WORKER,
        title="Your visits",
        description="The worker's booked visits from now (and any past ones still waiting for an outcome) up to N days ahead.",
        sql=f"""
SELECT sv.scheduled_for, sv.status, sv.reason, sv.location,
       u.id AS citizen_id, u.name AS citizen, u.area,
       sv.scheduled_for < now() AS needs_outcome
FROM scheduled_visits sv
JOIN users u ON u.id = sv.citizen_id
WHERE sv.worker_id = :me AND sv.status = 'scheduled'
  AND sv.scheduled_for < now() + make_interval(days => :days)
ORDER BY sv.scheduled_for
LIMIT :limit""",
        params={"days": DAYS(7), "limit": LIMIT(15)},
        post=_with_refs,
        patterns=(
            (r"\b(visit|visits|schedule|appointments?|today'?s (visits|plan)|my day|booked)\b", 3),
        ),
    ),
    Tool(
        name="locality_breakdown",
        roles=WORKER,
        title="Flags by locality",
        description="For each locality in the catchment: citizens who allow community monitoring, and how many of them have an open flag. Localities under 3 citizens are merged.",
        needs_facility=True,
        sql=f"""
SELECT coalesce(nullif(trim(u.area), ''), 'Unspecified') AS locality,
       count(*) AS citizens,
       count(*) FILTER (WHERE EXISTS (
         SELECT 1 FROM processed_data pd WHERE pd.user_id = u.id AND {_OPEN}
       )) AS flagged
FROM users u
WHERE {_CATCHMENT} AND {_COMMUNITY}
GROUP BY 1""",
        post=_suppressed,
        patterns=(
            (r"\b(locality|localities|area|areas|village|villages|ward|wards|street|hotspot|cluster|where)\b", 3),
        ),
    ),
    Tool(
        name="catchment_trend",
        roles=WORKER,
        title="Readings and flags per day",
        description="Per day (India time) in the catchment: readings logged and how many were flagged.",
        needs_facility=True,
        sql=f"""
SELECT (hr.timestamp AT TIME ZONE 'Asia/Kolkata')::date AS day,
       count(*) AS readings,
       count(*) FILTER (WHERE pd.is_anomaly) AS flags
FROM health_records hr
JOIN users u ON u.id = hr.user_id
LEFT JOIN processed_data pd ON pd.health_record_id = hr.id
WHERE {_CATCHMENT} AND hr.timestamp >= {_SINCE}
GROUP BY 1
ORDER BY 1""",
        params={"days": DAYS(14)},
        patterns=(
            (r"\b(trend|per day|daily|each day|over time|rising|increasing|going up|spike)\b", 3),
        ),
    ),
    Tool(
        name="symptom_counts",
        roles=WORKER,
        title="Most reported symptoms",
        description="The symptoms reported most often with readings in the catchment over a window, with how many citizens reported each.",
        needs_facility=True,
        sql=f"""
SELECT s.symptom, count(*) AS reports, count(DISTINCT hr.user_id) AS citizens
FROM health_records hr
JOIN users u ON u.id = hr.user_id
CROSS JOIN LATERAL json_array_elements_text(hr.symptoms) AS s(symptom)
WHERE {_CATCHMENT} AND {_COMMUNITY} AND hr.timestamp >= {_SINCE}
GROUP BY s.symptom
ORDER BY reports DESC
LIMIT 10""",
        params={"days": DAYS(14)},
        patterns=(
            (r"\b(symptom|symptoms|fever|cough|headache|outbreak|going around|common complaints?)\b", 4),
        ),
    ),
    # --- Admins: aggregates and account metadata, never readings -----------------------
    Tool(
        name="platform_overview",
        roles=ADMIN,
        title="Platform overview",
        description="For the admin's district: accounts by role, deactivated accounts, readings in a window, open flags, pending worker applications and open concerns.",
        sql=f"""
SELECT (SELECT count(*) FROM users u WHERE u.role = 'user' AND {_in_district("u.district")}) AS citizens,
       (SELECT count(*) FROM users u WHERE u.role = 'phc_worker' AND {_in_district("u.district")}) AS phc_workers,
       (SELECT count(*) FROM users u WHERE u.role = 'pending_phc' AND {_in_district("u.district")}) AS awaiting_approval,
       (SELECT count(*) FROM users u WHERE NOT u.is_active AND {_in_district("u.district")}) AS deactivated,
       (SELECT count(*) FROM health_records hr JOIN users u ON u.id = hr.user_id
        WHERE hr.created_at >= {_SINCE} AND {_in_district("u.district")}) AS readings,
       (SELECT count(*) FROM processed_data pd JOIN users u ON u.id = pd.user_id
        WHERE {_OPEN} AND {_in_district("u.district")}) AS open_flags,
       (SELECT count(*) FROM phc_applications pa WHERE pa.status = 'pending' AND {_in_district("pa.district")}) AS pending_applications,
       (SELECT count(*) FROM concerns c JOIN users u ON u.id = c.user_id
        WHERE c.status IN ('open', 'in_review') AND {_in_district("u.district")}) AS open_concerns""",
        params={"days": DAYS(7)},
        patterns=(
            (r"\b(overview|summary|summarise|summarize|at a glance|how is the platform|stats|statistics|how many (users|accounts|citizens|workers))\b", 3),
        ),
    ),
    Tool(
        name="pending_applications",
        roles=ADMIN,
        title="PHC applications waiting",
        description="PHC worker applications waiting for a decision, oldest first.",
        sql=f"""
SELECT pa.created_at AS applied_at, u.name, u.email, u.is_verified AS email_confirmed,
       pa.designation, pa.phc_name, pa.district, pa.state, pa.years_of_service
FROM phc_applications pa
JOIN users u ON u.id = pa.user_id
WHERE pa.status = 'pending' AND {_in_district("pa.district")}
ORDER BY pa.created_at
LIMIT :limit""",
        params={"limit": LIMIT(20)},
        patterns=(
            (r"\b(application|applications|applicant|applicants|approve|approval|pending|waiting)\b", 4),
        ),
    ),
    Tool(
        name="facility_load",
        roles=ADMIN,
        title="Health centres by load",
        description="Health centres with registered citizens: citizens, active workers and open flags. Centres with citizens but no worker come first.",
        sql=f"""
SELECT f.name, f.district, f.state,
       count(*) FILTER (WHERE u.role = 'user') AS citizens,
       count(*) FILTER (WHERE u.role = 'phc_worker' AND u.is_active) AS workers,
       (SELECT count(*) FROM processed_data pd JOIN users c ON c.id = pd.user_id
        WHERE c.phc_id = f.id AND {_OPEN}) AS open_flags
FROM valid_phc_facilities f
JOIN users u ON u.phc_id = f.id
WHERE {_in_district("f.district")}
GROUP BY f.id, f.name, f.district, f.state
ORDER BY (count(*) FILTER (WHERE u.role = 'phc_worker' AND u.is_active) = 0) DESC, citizens DESC
LIMIT :limit""",
        params={"limit": LIMIT(15)},
        patterns=(
            (r"\b(facility|facilities|centre|centres|center|centers|phcs?|load|busiest|understaffed|no workers?|uncovered|coverage)\b", 3),
        ),
    ),
    Tool(
        name="unlinked_workers",
        roles=ADMIN,
        title="Workers with no health centre",
        description="Approved PHC workers not linked to any health centre (they see no citizens).",
        sql=f"""
SELECT u.name, u.email, u.created_at, u.district, u.state
FROM users u
WHERE u.role = 'phc_worker' AND u.phc_id IS NULL AND {_in_district("u.district")}
ORDER BY u.created_at
LIMIT 50""",
        patterns=(
            (r"\b(unlinked|not linked|without (a )?(centre|center|facility)|no (centre|center|facility))\b", 5),
        ),
    ),
    Tool(
        name="concerns_summary",
        roles=ADMIN,
        title="Support concerns",
        description="Support concerns counted by status and category.",
        sql=f"""
SELECT c.status, c.category, count(*) AS concerns, min(c.created_at) AS oldest
FROM concerns c
JOIN users u ON u.id = c.user_id
WHERE {_in_district("u.district")}
GROUP BY c.status, c.category
ORDER BY c.status, concerns DESC""",
        patterns=(
            (r"\b(concern|concerns|complaint|complaints|ticket|tickets|support)\b", 4),
        ),
    ),
    Tool(
        name="signups",
        roles=ADMIN,
        title="New accounts",
        description="New accounts per role in a window, with how many confirmed their email.",
        sql=f"""
SELECT u.role, count(*) AS accounts, count(*) FILTER (WHERE u.is_verified) AS email_confirmed
FROM users u
WHERE u.created_at >= {_SINCE} AND {_in_district("u.district")}
GROUP BY u.role
ORDER BY accounts DESC""",
        params={"days": DAYS(30)},
        patterns=(
            (r"\b(sign ?ups?|signed up|registrations?|registered|new (users|accounts|citizens)|growth|joined)\b", 4),
        ),
    ),
    Tool(
        name="district_activity",
        roles=ADMIN,
        title="Activity by district",
        description="Per district, counting only citizens who allow community monitoring: citizens, readings in a window and flags in that window. Districts under 3 citizens are not shown.",
        sql=f"""
SELECT coalesce(u.district, 'Unspecified') AS district,
       count(DISTINCT u.id) AS citizens,
       count(hr.id) AS readings,
       count(pd.id) FILTER (WHERE pd.is_anomaly) AS flags
FROM users u
LEFT JOIN health_records hr ON hr.user_id = u.id AND hr.timestamp >= {_SINCE}
LEFT JOIN processed_data pd ON pd.health_record_id = hr.id
WHERE u.role = 'user' AND {_COMMUNITY} AND {_in_district("u.district")}
GROUP BY 1
HAVING count(DISTINCT u.id) >= 3
ORDER BY readings DESC
LIMIT 20""",
        params={"days": DAYS(30)},
        patterns=(
            (r"\b(district|districts|state|states|region|regions|by area)\b", 3),
        ),
    ),
    Tool(
        name="assistant_usage",
        roles=ADMIN,
        title="Assistant usage",
        description="Questions asked to this assistant in a window, by role, and how many it could not answer.",
        sql=f"""
SELECT u.role,
       count(*) FILTER (WHERE m.role = 'user') AS questions,
       count(*) FILTER (WHERE m.role = 'assistant' AND m.was_refused) AS not_answered,
       round(avg(m.latency_ms) FILTER (WHERE m.role = 'assistant')) AS avg_latency_ms
FROM chat_messages m
JOIN users u ON u.id = m.user_id
WHERE m.created_at >= {_SINCE} AND {_in_district("u.district")}
GROUP BY u.role""",
        params={"days": DAYS(7)},
        patterns=(
            (r"\b(assistant|chatbot|chat bot|questions asked|usage)\b", 4),
        ),
    ),
    # --- Newer features -------------------------------------------------------------
    Tool(
        name="my_examinations",
        roles=CITIZEN,
        title="Your examinations",
        description="Examinations a PHC health worker recorded for the citizen: when, where, by whom and the vitals measured.",
        sql=f"""
SELECT hr.timestamp AS examined_at, hr.location, w.name AS examined_by, hr.vitals, hr.symptoms
FROM health_records hr
LEFT JOIN users w ON w.id = hr.recorded_by
WHERE hr.user_id = :me AND hr.source = 'phc' AND hr.timestamp >= {_SINCE}
ORDER BY hr.timestamp DESC
LIMIT 10""",
        params={"days": DAYS(365)},
        patterns=(
            (r"\b(exam|exams|examination|examinations|examined|check-?up|checkups?|health worker (measured|checked|recorded))\b", 4),
        ),
    ),
    Tool(
        name="my_readings_by_source",
        roles=CITIZEN,
        title="Where your readings came from",
        description="The citizen's readings in a window split by source: smartwatch sync, PHC examination, or typed in; with the latest of each.",
        sql=f"""
SELECT hr.source, count(*) AS readings, max(hr.timestamp) AS latest
FROM health_records hr
WHERE hr.user_id = :me AND hr.timestamp >= {_SINCE}
GROUP BY hr.source
ORDER BY readings DESC""",
        params={"days": DAYS(30)},
        patterns=(
            (r"\b(smart ?watch|watch|synced?|sync|wearable|source of my readings)\b", 4),
        ),
    ),
    Tool(
        name="my_advisories",
        roles=CITIZEN,
        title="Advisories for you",
        description="Community health advisories currently running for where the citizen lives or is registered: title, message, importance (low=green, medium=yellow, high=red) and end date.",
        sql=f"""
SELECT a.created_at, a.title, a.body, a.severity, a.expires_at
FROM advisories a
JOIN users me ON me.id = :me
WHERE a.withdrawn_at IS NULL AND a.expires_at > now() AND {_FOR_ME}
ORDER BY a.created_at DESC
LIMIT 10""",
        patterns=(
            (r"\b(advisory|advisories|notice|notices|announcement|announcements|precautions?|warnings? (in|for) my area)\b", 4),
        ),
    ),
    Tool(
        name="advisories_overview",
        roles=WORKER | ADMIN,
        title="Advisories published",
        description="Community advisories published in a window (a worker's centre, or an admin's district): title, importance, who it went to, whether running, and the admin's feedback.",
        sql=f"""
SELECT a.created_at, a.title, a.severity, a.scope, a.area, a.radius_km,
       CASE WHEN a.withdrawn_at IS NOT NULL THEN 'withdrawn'
            WHEN a.expires_at > now() THEN 'running' ELSE 'ended' END AS status,
       a.feedback
FROM advisories a
WHERE a.created_at >= {_SINCE}
  AND (CAST(:phc_id AS uuid) IS NULL OR a.phc_id = CAST(:phc_id AS uuid))
  AND {_in_district("a.district")}
ORDER BY a.created_at DESC
LIMIT :limit""",
        params={"days": DAYS(90), "limit": LIMIT(15)},
        patterns=(
            (r"\b(advisory|advisories|notice|notices|announcement|announcements|published|broadcast)\b", 4),
        ),
    ),
    Tool(
        name="outbreak_signals",
        roles=WORKER | ADMIN,
        title="Outbreak signals",
        description="Outbreak clusters the space-time clustering flagged in a window (a worker's centre, or an admin's district): syndrome, cases vs expected, place, onset dates and whether acknowledged.",
        sql=f"""
SELECT cd.syndrome, cd.cases, round(cd.expected::numeric, 1) AS expected, round(cd.p_value::numeric, 4) AS p_value,
       cd.region, cd.district, round(cd.radius_km::numeric, 1) AS radius_km,
       cd.first_onset, cd.last_onset, cd.acknowledged_at IS NOT NULL AS acknowledged
FROM community_data cd
WHERE cd.outbreak_flag AND cd.window_end >= {_SINCE}
  AND (CAST(:phc_id AS uuid) IS NULL OR cd.phc_ids::jsonb @> to_jsonb(ARRAY[CAST(:phc_id AS uuid)::text]))
  AND {_in_district("cd.district")}
ORDER BY cd.cases DESC
LIMIT 10""",
        params={"days": DAYS(14)},
        patterns=(
            (r"\b(outbreak|outbreaks|cluster|clusters|epidemic|spreading|signal|signals)\b", 5),
        ),
    ),
)

BY_NAME: dict[str, Tool] = {t.name: t for t in TOOLS}


def tools_for(role: UserRole) -> list[Tool]:
    return [t for t in TOOLS if role in t.roles]
