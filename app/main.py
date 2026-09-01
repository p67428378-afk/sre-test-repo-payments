"""SRE Payments Test Service."""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app.calculator import calculate_late_fee, calculate_late_fee_with_retry
from app.models import LateFeeRequest, LateFeeResponse, PaymentRequest, PaymentResponse


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging in GCP Cloud Logging."""
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "timestamp": self.formatTime(record, self.datefmt),
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)


# Configure logging
log_handler = logging.StreamHandler()
if os.getenv("LOG_FORMAT", "json").lower() == "json":
    log_handler.setFormatter(JSONFormatter())
else:
    log_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers = []
root_logger.addHandler(log_handler)

logger = logging.getLogger(__name__)


async def _error_loop() -> None:
    while True:
        await asyncio.sleep(60)
        try:
            calculate_late_fee_with_retry(1000.0, 30, 0)
        except Exception:
            logger.exception(
                "Late fee calculation failed — ZeroDivisionError in calculate_late_fee "
                "(installment_count=0 triggers division by zero)"
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.environ.get("APP_ENV") == "buggy":
        logger.warning("APP_ENV=buggy — triggering error loop for Cloud Logging population")
        try:
            calculate_late_fee_with_retry(1000.0, 30, 0)
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
    try:
        result = calculate_late_fee_with_retry(req.principal, req.overdue_days, req.installment_count)
        return LateFeeResponse(**result)
    except ZeroDivisionError:
        logger.exception(
            "ZeroDivisionError in calculate_late_fee — installment_count=%d", req.installment_count
        )
        raise HTTPException(status_code=422, detail="installment_count must be greater than zero")


@app.post("/process-payment", response_model=PaymentResponse)
def process_payment(req: PaymentRequest):
    logger.info("Payment accepted: payment_id=%s amount=%.2f", req.payment_id, req.amount)
    return PaymentResponse(
        payment_id=req.payment_id,
        status="accepted",
        amount=req.amount,
    )
