"""SRE Payments Test Service.

Endpoints:
  GET  /healthz             Liveness probe — always 200
  GET  /readyz              Readiness probe — always 200
  GET  /                    Service info
  POST /calculate-late-fee  Late-fee calculation (ZeroDivisionError on buggy branch when installment_count=0)
  POST /process-payment     Idempotent payment record — always succeeds

When APP_ENV=buggy, a background task calls calculate_late_fee(1000, 30, 0) every 60 s.
On the buggy branch this produces ZeroDivisionError stacktraces in Cloud Run / Cloud Logging.
On the clean (main) branch the guard clause returns 0.0 silently.
"""

import asyncio
import json
import logging
import os
import sys
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app.calculator import calculate_late_fee
from app.calculator import METRICS as CALC_METRICS
from app.models import LateFeeRequest, LateFeeResponse, PaymentRequest, PaymentResponse

# Structured JSON logging for GCP Cloud Logging compatibility
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "time": self.formatTime(record, self.datefmt),
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())

# Reset existing handlers to avoid duplicate logs
root_logger = logging.getLogger()
for h in root_logger.handlers[:]:
    root_logger.removeHandler(h)
root_logger.addHandler(handler)
root_logger.setLevel(logging.INFO)

logger = logging.getLogger(__name__)

# App-level metrics
app_metrics = {
    "calls": 0,
    "errors": 0,
    "retries": 0,
}


async def _error_loop() -> None:
    """Repeatedly trigger the buggy calculation so ERROR logs appear in Cloud Logging."""
    while True:
        await asyncio.sleep(60)
        try:
            calculate_late_fee(1000.0, 30, 0)
        except Exception:
            logger.exception(
                "Late fee calculation failed — ZeroDivisionError in calculate_late_fee "
                "(installment_count=0 triggers division by zero)"
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.environ.get("APP_ENV") == "buggy":
        logger.warning(
            "APP_ENV=buggy — triggering error loop for Cloud Logging population"
        )
        try:
            calculate_late_fee(1000.0, 30, 0)
        except Exception:
            logger.exception(
                "Late fee calculation failed — ZeroDivisionError in calculate_late_fee "
                "(installment_count=0 triggers division by zero)"
            )
        asyncio.create_task(_error_loop())
    yield


app = FastAPI(
    title="SRE Payments Test Service",
    description="BFSI loan payment service — used for L3 remediation pipeline testing",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
def root():
    return {
        "service": "sre-payments-test",
        "version": "1.0.0",
        "env": os.environ.get("APP_ENV", "clean"),
        "status": "running",
    }


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz():
    return {"status": "ready"}


@app.post("/calculate-late-fee", response_model=LateFeeResponse)
def calculate_late_fee_endpoint(req: LateFeeRequest):
    app_metrics["calls"] += 1
    max_retries = 3
    retry_delay = 0.1

    logger.info(
        "Received late fee calculation request: principal=%.2f, overdue_days=%d, installment_count=%d",
        req.principal, req.overdue_days, req.installment_count
    )

    for attempt in range(max_retries):
        try:
            start_time = time.time()
            result = calculate_late_fee(
                req.principal, req.overdue_days, req.installment_count
            )
            duration = time.time() - start_time
            logger.info(
                "Late fee calculation completed in %.4f seconds on attempt %d",
                duration, attempt + 1
            )
            return LateFeeResponse(**result)
        except ZeroDivisionError:
            app_metrics["errors"] += 1
            logger.exception(
                "ZeroDivisionError in calculate_late_fee — installment_count=%d",
                req.installment_count,
            )
            raise HTTPException(
                status_code=422, detail="installment_count must be greater than zero"
            )
        except Exception as e:
            app_metrics["retries"] += 1
            if attempt < max_retries - 1:
                logger.warning(
                    "Transient error on attempt %d: %s. Retrying in %.1f seconds...",
                    attempt + 1, e, retry_delay
                )
                time.sleep(retry_delay)
            else:
                app_metrics["errors"] += 1
                logger.error("All %d attempts failed. Last error: %s", max_retries, e)
                raise HTTPException(
                    status_code=500, detail=f"Internal server error: {e}"
                )


@app.get("/metrics")
def get_metrics():
    return {
        "calculator": CALC_METRICS,
        "app": {
            "calculate_late_fee_calls": app_metrics["calls"],
            "calculate_late_fee_errors": app_metrics["errors"],
            "calculate_late_fee_retries": app_metrics["retries"],
        }
    }


@app.post("/process-payment", response_model=PaymentResponse)
def process_payment(req: PaymentRequest):
    logger.info(
        "Payment accepted: payment_id=%s amount=%.2f", req.payment_id, req.amount
    )
    return PaymentResponse(
        payment_id=req.payment_id,
        status="accepted",
        amount=req.amount,
    )
