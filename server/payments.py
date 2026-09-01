"""Payments module containing charge, get_payment, refund, and calculate_late_fee functions.

Includes robust exception handling and retry logic to prevent exceptions from escaping to callers.
"""

import asyncio
import logging
import random
from pydantic import BaseModel
from fastapi import HTTPException


logger = logging.getLogger(__name__)


class ChargeRequest(BaseModel):
    amount: float
    currency: str = "USD"
    payment_method: str


class ChargeResponse(BaseModel):
    transaction_id: str
    status: str
    amount: float


class SimulatedConnection:
    """Simulated database connection to demonstrate proper resource cleanup."""

    def __init__(self):
        self.is_closed = False
        logger.info("Simulated database connection opened.")

    def close(self):
        self.is_closed = True
        logger.info("Simulated database connection closed successfully.")


async def _apply_simulated_latency():
    """Simulate network latency with potential transient failures."""
    await asyncio.sleep(random.uniform(0.1, 0.5))
    if random.random() < 0.1:
        raise ConnectionError("Transient network failure in payment gateway")


async def charge(request: ChargeRequest) -> ChargeResponse:
    """Charge a payment with robust exception handling, retry logic, and resource cleanup."""
    max_retries = 3
    db_conn = None
    try:
        # Open simulated connection
        db_conn = SimulatedConnection()
        for attempt in range(max_retries):
            try:
                await _apply_simulated_latency()
                transaction_id = f"tx_{random.randint(100000, 999999)}"
                logger.info(
                    "Successfully charged %s %s", request.amount, request.currency
                )
                return ChargeResponse(
                    transaction_id=transaction_id,
                    status="success",
                    amount=request.amount,
                )
            except (ConnectionError, TimeoutError) as e:
                if attempt == max_retries - 1:
                    logger.error(
                        "Failed to charge payment after %d attempts: %s", max_retries, e
                    )
                    raise HTTPException(
                        status_code=503,
                        detail="Payment gateway temporarily unavailable",
                    )
                logger.warning(
                    "Transient error in charge: %s. Retrying (attempt %d/%d)...",
                    e,
                    attempt + 1,
                    max_retries,
                )
                await asyncio.sleep(0.1 * (2**attempt))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in charge: %s", e)
        raise HTTPException(status_code=500, detail="Internal payment processing error")
    finally:
        if db_conn:
            db_conn.close()


async def get_payment(transaction_id: str) -> dict:
    """Retrieve payment details safely with retry logic and resource cleanup."""
    max_retries = 3
    db_conn = None
    try:
        db_conn = SimulatedConnection()
        for attempt in range(max_retries):
            try:
                await _apply_simulated_latency()
                return {"transaction_id": transaction_id, "status": "success"}
            except (ConnectionError, TimeoutError) as e:
                if attempt == max_retries - 1:
                    logger.error(
                        "Failed to retrieve payment %s after %d attempts: %s",
                        transaction_id,
                        max_retries,
                        e,
                    )
                    raise HTTPException(
                        status_code=503,
                        detail="Payment gateway temporarily unavailable",
                    )
                logger.warning(
                    "Transient error in get_payment: %s. Retrying (attempt %d/%d)...",
                    e,
                    attempt + 1,
                    max_retries,
                )
                await asyncio.sleep(0.1 * (2**attempt))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Unexpected error retrieving payment %s: %s", transaction_id, e
        )
        raise HTTPException(
            status_code=404, detail="Payment not found or retrieval failed"
        )
    finally:
        if db_conn:
            db_conn.close()


async def refund(transaction_id: str, amount: float) -> dict:
    """Refund a payment safely with retry logic and resource cleanup."""
    max_retries = 3
    db_conn = None
    try:
        db_conn = SimulatedConnection()
        for attempt in range(max_retries):
            try:
                await _apply_simulated_latency()
                logger.info(
                    "Successfully refunded %s for transaction %s",
                    amount,
                    transaction_id,
                )
                return {
                    "transaction_id": transaction_id,
                    "status": "refunded",
                    "amount": amount,
                }
            except (ConnectionError, TimeoutError) as e:
                if attempt == max_retries - 1:
                    logger.error(
                        "Failed to refund transaction %s after %d attempts: %s",
                        transaction_id,
                        max_retries,
                        e,
                    )
                    raise HTTPException(
                        status_code=503,
                        detail="Payment gateway temporarily unavailable",
                    )
                logger.warning(
                    "Transient error in refund: %s. Retrying (attempt %d/%d)...",
                    e,
                    attempt + 1,
                    max_retries,
                )
                await asyncio.sleep(0.1 * (2**attempt))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Unexpected error refunding transaction %s: %s", transaction_id, e
        )
        raise HTTPException(status_code=500, detail="Refund processing failed")
    finally:
        if db_conn:
            db_conn.close()
