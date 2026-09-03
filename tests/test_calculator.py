"""Unit tests for calculate_late_fee and API endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.calculator import calculate_late_fee as app_calculate_late_fee
from app.calculator import calculate_late_fee_with_retry as app_calculate_late_fee_with_retry
from app.main import app as app_fastapi
from server.calculator import calculate_late_fee, calculate_late_fee_with_retry
from server.main import app

DAILY_RATE = 0.18 / 365.0


def test_normal_loan_produces_positive_fee():
    result = calculate_late_fee(10000.0, 30, 12)
    assert result["late_fee"] > 0
    assert result["daily_rate"] == pytest.approx(DAILY_RATE, rel=1e-6)

    app_res = app_calculate_late_fee(10000.0, 30, 12)
    assert app_res["late_fee"] > 0
    assert app_res["daily_rate"] == pytest.approx(DAILY_RATE, rel=1e-6)


def test_zero_installments_returns_zero():
    """Fully-paid loan (installment_count=0) must return 0.0, not raise ZeroDivisionError."""
    result = calculate_late_fee(10000.0, 30, 0)
    assert result["late_fee"] == 0.0
    assert result["daily_rate"] == pytest.approx(DAILY_RATE, rel=1e-6)

    app_res = app_calculate_late_fee(10000.0, 30, 0)
    assert app_res["late_fee"] == 0.0
    assert app_res["daily_rate"] == pytest.approx(DAILY_RATE, rel=1e-6)


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


def test_calculate_late_fee_with_retry():
    result = calculate_late_fee_with_retry(10000.0, 30, 12)
    assert result["late_fee"] > 0
    assert result["daily_rate"] == pytest.approx(DAILY_RATE, rel=1e-6)

    app_res = app_calculate_late_fee_with_retry(10000.0, 30, 12)
    assert app_res["late_fee"] > 0
    assert app_res["daily_rate"] == pytest.approx(DAILY_RATE, rel=1e-6)


def test_api_endpoints():
    client = TestClient(app)

    # root
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["status"] == "running"

    # healthz / readyz
    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").status_code == 200

    # calculate-late-fee with installment_count=0
    res = client.post("/calculate-late-fee", json={"principal": 10000.0, "overdue_days": 30, "installment_count": 0})
    assert res.status_code == 200
    assert res.json()["late_fee"] == 0.0

    # process-payment
    res = client.post("/process-payment", json={"payment_id": "pay_123", "amount": 150.0, "borrower_id": "b_1"})
    assert res.status_code == 200
    assert res.json()["status"] == "accepted"


def test_app_api_endpoints():
    client = TestClient(app_fastapi)

    # root
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["status"] == "running"

    # healthz / readyz
    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").status_code == 200

    # calculate-late-fee with installment_count=0
    res = client.post("/calculate-late-fee", json={"principal": 10000.0, "overdue_days": 30, "installment_count": 0})
    assert res.status_code == 200
    assert res.json()["late_fee"] == 0.0

    # process-payment
    res = client.post("/process-payment", json={"payment_id": "pay_123", "amount": 150.0, "borrower_id": "b_1"})
    assert res.status_code == 200
    assert res.json()["status"] == "accepted"
