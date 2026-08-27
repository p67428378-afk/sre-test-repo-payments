# SRE Payments Service (INC0010190 Remediation)

## Overview
BFSI loan payment service with late-fee calculator and payment processing endpoints.

## Bug Fix (INC0010190)
Resolved `ZeroDivisionError` in `calculate_late_fee` when `installment_count=0` (e.g. fully paid loans).
Added input validation, non-negative guards, and retry mechanism for transient exceptions.

## API Endpoints
- `GET /`: Service information and status
- `GET /healthz`: Health check probe
- `GET /readyz`: Readiness check probe
- `POST /calculate-late-fee`: Calculate penalty fee for overdue loan installments
- `POST /process-payment`: Process payment records

## Testing
Run pytest:
```bash
pytest
```
