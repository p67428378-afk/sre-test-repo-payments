import pytest
from unittest.mock import patch
from fastapi import HTTPException
from server.payments import charge, get_payment, refund, ChargeRequest


@pytest.mark.asyncio
async def test_charge_success():
    req = ChargeRequest(amount=100.0, currency="USD", payment_method="card")
    with patch("server.payments._apply_simulated_latency") as mock_latency:
        res = await charge(req)
        assert res.status == "success"
        assert res.amount == 100.0


@pytest.mark.asyncio
async def test_charge_transient_failure_retry():
    req = ChargeRequest(amount=100.0, currency="USD", payment_method="card")
    with patch(
        "server.payments._apply_simulated_latency",
        side_effect=[ConnectionError("Transient"), None],
    ):
        res = await charge(req)
        assert res.status == "success"


@pytest.mark.asyncio
async def test_charge_permanent_failure():
    req = ChargeRequest(amount=100.0, currency="USD", payment_method="card")
    with patch(
        "server.payments._apply_simulated_latency",
        side_effect=ConnectionError("Transient"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await charge(req)
        assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_get_payment_success():
    with patch("server.payments._apply_simulated_latency") as mock_latency:
        res = await get_payment("tx_123")
        assert res["transaction_id"] == "tx_123"
        assert res["status"] == "success"


@pytest.mark.asyncio
async def test_get_payment_retry():
    with patch(
        "server.payments._apply_simulated_latency",
        side_effect=[ConnectionError("Transient"), None],
    ):
        res = await get_payment("tx_123")
        assert res["transaction_id"] == "tx_123"
        assert res["status"] == "success"


@pytest.mark.asyncio
async def test_refund_success():
    with patch("server.payments._apply_simulated_latency") as mock_latency:
        res = await refund("tx_123", 50.0)
        assert res["transaction_id"] == "tx_123"
        assert res["status"] == "refunded"
        assert res["amount"] == 50.0
