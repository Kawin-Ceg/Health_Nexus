"""Format rules shared with the frontend.

The frontend keeps a byte-for-byte copy of EMPLOYEE_ID_PATTERN in
`frontend/src/lib/patterns.ts`; tests/test_patterns.py fails if they drift.
"""

import re

EMPLOYEE_ID_PATTERN = r"^[A-Z]{2,6}-[A-Z]{2,6}-\d{3,6}$"

_EMPLOYEE_ID_RE = re.compile(EMPLOYEE_ID_PATTERN, re.ASCII)


def is_valid_employee_id(value: str) -> bool:
    return _EMPLOYEE_ID_RE.fullmatch(value) is not None
