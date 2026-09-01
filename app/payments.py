"""Payments module containing charge, get_payment, and refund functions.

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
        db_conn = SimulatedConnection()
        for attempt in range(max_retries):
            try:
                await _apply_simulated_latency()
                # Simulate successful charge
                transaction_id = f"tx_{random.randint(100000, 999999)}"
                logger.info(f"Successfully charged {request.amount} {request.currency}")
                return ChargeResponse(transaction_id=transaction_id, status="success", amount=request.amount)
            except (ConnectionError, TimeoutError) as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to charge payment after {max_retries} attempts: {e}")
                    raise HTTPException(status_code=503, detail="Payment gateway temporarily unavailable")
                logger.warning(f"Transient error in charge: {e}. Retrying (attempt {attempt + 1}/{max_retries})...")
                await asyncio.sleep(0.1 * (2 ** attempt))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in charge: {e}")
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
                    logger.error(f"Failed to retrieve payment {transaction_id} after {max_retries} attempts: {e}")
                    raise HTTPException(status_code=503, detail="Payment gateway temporarily unavailable")
                logger.warning(f"Transient error in get_payment: {e}. Retrying (attempt {attempt + 1}/{max_retries})...")
                await asyncio.sleep(0.1 * (2 ** attempt))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving payment {transaction_id}: {e}")
        raise HTTPException(status_code=404, detail="Payment not found or retrieval failed")
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
                logger.info(f"Successfully refunded {amount} for transaction {transaction_id}")
                return {"transaction_id": transaction_id, "status": "refunded", "amount": amount}
            except (ConnectionError, TimeoutError) as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to refund transaction {transaction_id} after {max_retries} attempts: {e}")
                    raise HTTPException(status_code=503, detail="Payment gateway temporarily unavailable")
                logger.warning(f"Transient error in refund: {e}. Retrying (attempt {attempt + 1}/{max_retries})...")
                await asyncio.sleep(0.1 * (2 ** attempt))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error refunding transaction {transaction_id}: {e}")
        raise HTTPException(status_code=500, detail="Refund processing failed")
    finally:
        if db_conn:
            db_conn.close()
