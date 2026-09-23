"""Format rules shared with the frontend.

The frontend keeps a byte-for-byte copy of EMPLOYEE_ID_PATTERN in
`frontend/src/lib/patterns.ts`; tests/test_patterns.py fails if they drift.
"""

import re

# e.g. TNPHC-CHN-2847
EMPLOYEE_ID_PATTERN = r"^[A-Z]{2,6}-[A-Z]{2,6}-\d{3,6}$"

# re.ASCII keeps \d to 0-9, matching JavaScript's behaviour.
_EMPLOYEE_ID_RE = re.compile(EMPLOYEE_ID_PATTERN, re.ASCII)


def is_valid_employee_id(value: str) -> bool:
    return _EMPLOYEE_ID_RE.fullmatch(value) is not None
