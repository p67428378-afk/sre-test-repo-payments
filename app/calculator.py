"""Loan late-fee calculator.

BUGGY version — ZeroDivisionError when installment_count=0.
"""

ANNUAL_LATE_RATE = 0.18


def calculate_late_fee(principal: float, overdue_days: int, installment_count: int) -> dict:
    """Calculate penalty for an overdue loan installment."""
    daily_rate = ANNUAL_LATE_RATE / 365
    per_installment = principal / installment_count  # ZeroDivisionError when installment_count=0
    late_fee = per_installment * daily_rate * overdue_days
    return {"late_fee": round(late_fee, 2), "daily_rate": daily_rate}
