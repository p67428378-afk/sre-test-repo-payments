# SRE Payments Test Service

BFSI loan payment service — used for L3 SRE remediation pipeline testing.

## Features & Remediation

1. **Robust Error Handling**: Handled `ZeroDivisionError` in `app.calculator.calculate_late_fee` when `installment_count` is zero.
2. **Retry Logic**: Added robust retry logic to `app.main.calculate_late_fee_endpoint` to gracefully handle transient failures or exceptions.
3. **Structured Logging**: Configured structured JSON logging (`JsonFormatter`) to stdout for seamless GCP Cloud Logging ingestion.
4. **Unbuffered Output**: Configured `ENV PYTHONUNBUFFERED=1` in the `Dockerfile` to prevent log buffering and ensure immediate log delivery to GCP Cloud Logging.
5. **Metrics & Observability**: Added a `/metrics` endpoint exposing detailed application and calculator metrics.
6. **GCP Logging Verification**: Added `app/verify_gcp_logging.py` to verify GCP-side log ingestion and retention policies.

## Local Setup

1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Run the development server:
   ```bash
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
   ```

## Running Tests

Run the test suite using `pytest`:
```bash
pytest -v
```

## Test Credentials

No authentication is implemented for this service.
