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
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app.calculator import calculate_late_fee
from app.models import LateFeeRequest, LateFeeResponse, PaymentRequest, PaymentResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
        logger.warning("APP_ENV=buggy — triggering error loop for Cloud Logging population")
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
    try:
        result = calculate_late_fee(req.principal, req.overdue_days, req.installment_count)
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
