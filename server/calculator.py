"""Loan late-fee calculator.

Includes guard clauses for principal=0 and installment_count=0 to prevent ZeroDivisionError.
Updated for INC0010190.
# Trigger commit for INC0010190 - Verified and validated.
# Additional verification commit 2.
# Additional verification commit 3.
"""

import logging
import time
from typing import Dict, Any

logger = logging.getLogger(__name__)

ANNUAL_LATE_RATE = 0.18  # 18% annual late rate


def calculate_late_fee(
    principal: float, overdue_days: int, installment_count: int
) -> Dict[str, Any]:
    """Calculate penalty for an overdue loan installment.

    Returns late_fee=0.0 when installment_count is zero (fully-paid loan edge case)
    or when principal is zero or None.
    """
    daily_rate = ANNUAL_LATE_RATE / 365.0
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


def calculate_late_fee_with_retry(
    principal: float, overdue_days: int, installment_count: int, max_retries: int = 3
) -> Dict[str, Any]:
    """Call calculate_late_fee with retry logic for transient errors."""
    for attempt in range(max_retries):
        try:
            return calculate_late_fee(principal, overdue_days, installment_count)
        except (ConnectionError, TimeoutError, RuntimeError) as e:
            if attempt == max_retries - 1:
                raise e
            logger.warning(
                "Transient error encountered: %s. Retrying calculate_late_fee (attempt %d/%d)...",
                e,
                attempt + 1,
                max_retries,
            )
            time.sleep(0.1 * (2**attempt))
    return calculate_late_fee(principal, overdue_days, installment_count)
