import asyncio
from unittest.mock import patch
import pytest
from fastapi import HTTPException
from server.payments import (
    charge,
    get_payment,
    refund,
    calculate_late_fee,
    calculate_late_fee_with_retry,
    ChargeRequest,
    SimulatedConnection,
)


def test_charge_success():
    req = ChargeRequest(amount=100.0, currency="USD", payment_method="card")
    with patch("server.payments._apply_simulated_latency"):
        res = asyncio.run(charge(req))
        assert res.status == "success"
        assert res.amount == 100.0


def test_charge_transient_failure_retry():
    req = ChargeRequest(amount=100.0, currency="USD", payment_method="card")
    with patch(
        "server.payments._apply_simulated_latency",
        side_effect=[ConnectionError("Transient"), None],
    ):
        res = asyncio.run(charge(req))
        assert res.status == "success"


def test_charge_permanent_failure():
    req = ChargeRequest(amount=100.0, currency="USD", payment_method="card")
    with patch(
        "server.payments._apply_simulated_latency",
        side_effect=ConnectionError("Transient"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(charge(req))
        assert exc_info.value.status_code == 503


def test_get_payment_success():
    with patch("server.payments._apply_simulated_latency"):
        res = asyncio.run(get_payment("tx_123"))
        assert res["transaction_id"] == "tx_123"
        assert res["status"] == "success"


def test_get_payment_retry():
    with patch(
        "server.payments._apply_simulated_latency",
        side_effect=[ConnectionError("Transient"), None],
    ):
        res = asyncio.run(get_payment("tx_123"))
        assert res["transaction_id"] == "tx_123"
        assert res["status"] == "success"


def test_refund_success():
    with patch("server.payments._apply_simulated_latency"):
        res = asyncio.run(refund("tx_123", 50.0))
        assert res["transaction_id"] == "tx_123"
        assert res["status"] == "refunded"
        assert res["amount"] == 50.0


def test_simulated_connection_context_manager():
    """Verify that SimulatedConnection works as a context manager and closes properly."""
    with SimulatedConnection() as conn:
        assert not conn.is_closed
    assert conn.is_closed


def test_payments_calculate_late_fee_zero_installments():
    """Verify that calculate_late_fee via payments module handles installment_count=0."""
    res = calculate_late_fee(1000.0, 30, 0)
    assert res["late_fee"] == 0.0


def test_payments_calculate_late_fee_with_retry():
    """Verify retry wrapper in payments module."""
    res = calculate_late_fee_with_retry(1000.0, 30, 10)
    assert res["late_fee"] > 0
