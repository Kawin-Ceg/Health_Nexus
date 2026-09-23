/** Format rules shared with the backend (backend/app/core/patterns.py).
 *  backend/tests/test_patterns.py fails if this string drifts from the Python one. */

// e.g. TNPHC-CHN-2847. String.raw keeps the source text identical to Python's raw string.
export const EMPLOYEE_ID_PATTERN = String.raw`^[A-Z]{2,6}-[A-Z]{2,6}-\d{3,6}$`;

const EMPLOYEE_ID_RE = new RegExp(EMPLOYEE_ID_PATTERN);

export const isValidEmployeeId = (value: string): boolean => EMPLOYEE_ID_RE.test(value);
