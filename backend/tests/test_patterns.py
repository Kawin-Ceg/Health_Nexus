from pathlib import Path

import pytest

from app.core.patterns import EMPLOYEE_ID_PATTERN, is_valid_employee_id

FRONTEND_PATTERNS = Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "patterns.ts"


def test_frontend_uses_the_same_employee_id_string():
    # String.raw keeps the source text identical to the Python raw string.
    assert f"String.raw`{EMPLOYEE_ID_PATTERN}`" in FRONTEND_PATTERNS.read_text(encoding="utf-8")


@pytest.mark.parametrize("value", ["TNPHC-CHN-2847", "TN-HW-20417", "AB-CD-123", "ABCDEF-GHIJKL-123456"])
def test_accepts(value):
    assert is_valid_employee_id(value)


@pytest.mark.parametrize(
    "value",
    ["tnphc-chn-2847", "T-CHN-2847", "TNPHC-CHN-12", "TNPHC-CHN-1234567", "TNPHC-CHN-2847\n", "TNPHC_CHN_2847", "TNPHC-CHN-٢٨٤٧", ""],
)
def test_rejects(value):
    assert not is_valid_employee_id(value)
