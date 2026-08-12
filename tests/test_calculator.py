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


def test_metrics_updated_on_calculation():
    from app.calculator import METRICS
    # Reset metrics
    METRICS["calculate_late_fee_calls"] = 0
    calculate_late_fee(1000.0, 30, 12)
    assert METRICS["calculate_late_fee_calls"] == 1


def test_metrics_endpoint():
    from fastapi.testclient import TestClient
    from app.main import app as fastapi_app
    client = TestClient(fastapi_app)
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "calculator" in data
    assert "app" in data


def test_retry_logic_on_transient_error(monkeypatch):
    from fastapi.testclient import TestClient
    import app.main

    # Mock calculate_late_fee to fail once then succeed
    calls = 0
    original_calculate_late_fee = app.main.calculate_late_fee

    def mock_calculate_late_fee(principal, overdue_days, installment_count):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("Transient database error")
        return original_calculate_late_fee(principal, overdue_days, installment_count)

    monkeypatch.setattr(app.main, "calculate_late_fee", mock_calculate_late_fee)

    client = TestClient(app.main.app)
    response = client.post("/calculate-late-fee", json={
        "principal": 1000.0,
        "overdue_days": 30,
        "installment_count": 12
    })
    assert response.status_code == 200
    assert calls == 2


def test_logging_configuration_and_buffering():
    # AC: Investigate why no logs are appearing in GCP Cloud Logging.
    # Verify that logging is configured with a StreamHandler writing to stdout/stderr
    # and that structured JSON logging is enabled for GCP Cloud Logging compatibility.
    import logging
    from app.main import JsonFormatter

    root_logger = logging.getLogger()
    assert len(root_logger.handlers) > 0

    has_stream_handler = False
    has_json_formatter = False
    for handler in root_logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            has_stream_handler = True
            if isinstance(handler.formatter, JsonFormatter):
                has_json_formatter = True

    assert has_stream_handler, "Logging must have a StreamHandler configured"
    assert has_json_formatter, "Logging must use JsonFormatter for GCP Cloud Logging compatibility"
