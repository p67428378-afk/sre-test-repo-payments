# Observability and Code Review Report (INC0010190)

This document addresses the investigation of the observability gap and the code review of the payments service.

## 1. Investigation of `query_gcp_logs` Observability Gap

### Findings:
- **Log Suppression**: The background error loop in `app/main.py` only triggers when the environment variable `APP_ENV` is explicitly set to `"buggy"`. If `APP_ENV` is set to any other value (or unset), the error loop does not run, resulting in no errors being logged.
- **Logging Configuration**: The default logging configuration in `app/main.py` uses standard `logging.basicConfig(level=logging.INFO)`. In GCP Cloud Run, standard stdout/stderr logs are captured, but without structured JSON logging, some log parsers or queries (like `query_gcp_logs`) might fail to identify or filter the errors correctly.
- **Unhandled Exceptions**: Prior to our fix, `ZeroDivisionError` could escape to the FastAPI framework, resulting in generic 500 Internal Server Errors without structured detail, which can be harder to query or monitor.

### Remediation:
- We have implemented robust error handling directly inside `calculate_late_fee` to catch `ZeroDivisionError` and return a safe default (`late_fee: 0.0`).
- We have added explicit logging of any handled exceptions with clear, searchable log messages.
- We recommend configuring structured JSON logging (e.g., using `python-json-logger`) in production to ensure GCP Cloud Logging can index and query all error stack traces reliably.

## 2. Code Review of Payments Components

### Findings:
- **Module Existence**: The components `payments.charge`, `payments.get_payment`, and `payments.refund` mentioned in the diagnostic hints do not exist in this repository. The repository contains a simplified BFSI loan payment service with endpoints `/calculate-late-fee` and `/process-payment`.
- **Exception Handling Review**:
  - We reviewed the existing endpoints in `app/main.py`.
  - The `/calculate-late-fee` endpoint now uses `calculate_late_fee_with_retry` which includes robust retry logic for transient errors and handles `ZeroDivisionError` gracefully.
  - The `/process-payment` endpoint has been verified to log accepted payments and return structured responses without risk of unhandled exceptions escaping to callers.
