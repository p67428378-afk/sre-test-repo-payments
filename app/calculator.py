"""Loan late-fee calculator.

Clean version (main branch) — includes guard for installment_count=0.
"""

import logging
import time

ANNUAL_LATE_RATE = 0.18

logger = logging.getLogger(__name__)

# Simple metrics dictionary
METRICS = {
    "calculate_late_fee_calls": 0,
    "calculate_late_fee_errors": 0,
    "calculate_late_fee_duration_seconds": 0.0,
}


def calculate_late_fee(
    principal: float, overdue_days: int, installment_count: int
) -> dict:
    """Calculate penalty for an overdue loan installment.

    Returns late_fee=0.0 when installment_count is zero (fully-paid loan edge case).
    """
    start_time = time.time()
    METRICS["calculate_late_fee_calls"] += 1
    daily_rate = ANNUAL_LATE_RATE / 365

    logger.info(
        "Calculating late fee: principal=%.2f, overdue_days=%d, installment_count=%d",
        principal,
        overdue_days,
        installment_count,
    )

    if installment_count == 0:
        logger.warning("installment_count is zero, returning late_fee=0.0")
        duration = time.time() - start_time
        METRICS["calculate_late_fee_duration_seconds"] += duration
        return {"late_fee": 0.0, "daily_rate": daily_rate}

    try:
        per_installment = principal / installment_count
        late_fee = per_installment * daily_rate * overdue_days
        result = {"late_fee": round(late_fee, 2), "daily_rate": daily_rate}
        logger.info("Late fee calculated successfully: %s", result)
        duration = time.time() - start_time
        METRICS["calculate_late_fee_duration_seconds"] += duration
        return result
    except ZeroDivisionError as e:
        METRICS["calculate_late_fee_errors"] += 1
        logger.error("ZeroDivisionError in calculate_late_fee: %s", e)
        duration = time.time() - start_time
        METRICS["calculate_late_fee_duration_seconds"] += duration
        raise
