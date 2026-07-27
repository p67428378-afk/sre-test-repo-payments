"""Unit tests for calculate_late_fee.

On main branch (clean): all tests pass.
On buggy/zero-division-late-fee branch: test_zero_installments_returns_zero fails
  with ZeroDivisionError — confirming the bug is present and the test catches it.
"""

import pytest

from app.calculator import calculate_late_fee

DAILY_RATE = 0.18 / 365


def test_normal_loan_produces_positive_fee():
    result = calculate_late_fee(10000.0, 30, 12)
    assert result["late_fee"] > 0
    assert result["daily_rate"] == pytest.approx(DAILY_RATE, rel=1e-6)


def test_zero_installments_returns_zero():
    """Fully-paid loan (installment_count=0) must return 0.0, not raise ZeroDivisionError."""
    result = calculate_late_fee(10000.0, 30, 0)
    assert result["late_fee"] == 0.0
    assert result["daily_rate"] == pytest.approx(DAILY_RATE, rel=1e-6)


def test_single_installment_fee_calculation():
    result = calculate_late_fee(1000.0, 10, 1)
    expected = round((1000.0 / 1) * DAILY_RATE * 10, 2)
    assert result["late_fee"] == pytest.approx(expected, rel=1e-6)


def test_large_principal_rounding():
    result = calculate_late_fee(500000.0, 90, 24)
    assert isinstance(result["late_fee"], float)
    assert result["late_fee"] > 0


def test_zero_or_none_principal_returns_zero():
    result_zero = calculate_late_fee(0.0, 30, 12)
    assert result_zero["late_fee"] == 0.0
    
    result_none = calculate_late_fee(None, 30, 12)
    assert result_none["late_fee"] == 0.0


def test_negative_inputs_raise_value_error():
    with pytest.raises(ValueError):
        calculate_late_fee(-100.0, 30, 12)
    with pytest.raises(ValueError):
        calculate_late_fee(1000.0, -5, 12)
    with pytest.raises(ValueError):
        calculate_late_fee(1000.0, 30, -1)

