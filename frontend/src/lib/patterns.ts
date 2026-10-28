
export const EMPLOYEE_ID_PATTERN = String.raw`^[A-Z]{2,6}-[A-Z]{2,6}-\d{3,6}$`;

const EMPLOYEE_ID_RE = new RegExp(EMPLOYEE_ID_PATTERN);

export const isValidEmployeeId = (value: string): boolean => EMPLOYEE_ID_RE.test(value);
