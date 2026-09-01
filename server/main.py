"""SRE Payments Test Service.

Endpoints:
  GET  /healthz             Liveness probe — always 200
  GET  /readyz              Readiness probe — always 200
  GET  /                    Service info
  POST /calculate-late-fee  Late-fee calculation
  POST /process-payment     Idempotent payment record
"""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from starlette.middleware.cors import CORSMiddleware

from server.calculator import calculate_late_fee_with_retry
from server.models import (
    LateFeeRequest,
    LateFeeResponse,
    PaymentRequest,
    PaymentResponse,
)


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
    log_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers = []
root_logger.addHandler(log_handler)

logger = logging.getLogger(__name__)


async def _error_loop() -> None:
    """Trigger periodic calculation for telemetry / logging verification."""
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
        logger.warning("APP_ENV=buggy — triggering background check")
        try:
            calculate_late_fee_with_retry(1000.0, 30, 0)
        except Exception:
            logger.exception("Error in calculation during startup")
        asyncio.create_task(_error_loop())
    yield


app = FastAPI(
    title="SRE Payments Test Service",
    description="BFSI loan payment service — used for L3 remediation pipeline testing",
    version="1.0.0",
    lifespan=lifespan,
)

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    # Add validation to ensure installment_count is not zero before calling calculate_late_fee
    if req.installment_count == 0:
        logger.info(
            "installment_count is zero, returning 0.0 late fee directly without calling calculate_late_fee"
        )
        return LateFeeResponse(late_fee=0.0, daily_rate=0.18 / 365.0)

    try:
        result = calculate_late_fee_with_retry(
            req.principal, req.overdue_days, req.installment_count
        )
        return LateFeeResponse(**result)
    except ValueError as e:
        logger.warning("Validation error in calculate_late_fee: %s", e)
        raise HTTPException(status_code=422, detail=str(e))
    except ZeroDivisionError:
        logger.exception(
            "ZeroDivisionError in calculate_late_fee: installment_count=%d",
            req.installment_count,
        )
        raise HTTPException(
            status_code=422, detail="installment_count must be greater than zero"
        )


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
