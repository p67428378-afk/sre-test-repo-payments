"""Loan late-fee calculator.

Clean version (main branch) — includes guard for installment_count=0.
"""

ANNUAL_LATE_RATE = 0.18


def calculate_late_fee(principal: float, overdue_days: int, installment_count: int) -> dict:
    """Calculate penalty for an overdue loan installment.

    Returns late_fee=0.0 when installment_count is zero (fully-paid loan edge case).
    """
    # Guard clause for zero loan_amount before fee calculation (INC0010190)
    daily_rate = ANNUAL_LATE_RATE / 365
    if principal is None or principal == 0:
        return {"late_fee": 0.0, "daily_rate": daily_rate}
    if principal < 0 or overdue_days < 0 or installment_count < 0:
        raise ValueError("Inputs must be non-negative")
    if installment_count == 0:
        return {"late_fee": 0.0, "daily_rate": daily_rate}
    try:
        per_installment = principal / installment_count
    except ZeroDivisionError:
        return {"late_fee": 0.0, "daily_rate": daily_rate}
    late_fee = per_installment * daily_rate * overdue_days
    return {"late_fee": round(late_fee, 2), "daily_rate": daily_rate}


def calculate_late_fee_with_retry(principal: float, overdue_days: int, installment_count: int, max_retries: int = 3) -> dict:
    """Call calculate_late_fee with retry logic for transient errors."""
    import time
    import logging
    logger = logging.getLogger(__name__)
    
    for attempt in range(max_retries):
        try:
            return calculate_late_fee(principal, overdue_days, installment_count)
        except (ConnectionError, TimeoutError, RuntimeError) as e:
            if attempt == max_retries - 1:
                raise e
            logger.warning(f"Transient error encountered: {e}. Retrying calculate_late_fee (attempt {attempt + 1}/{max_retries})...")
            time.sleep(0.1 * (2 ** attempt))
    return calculate_late_fee(principal, overdue_days, installment_count)
