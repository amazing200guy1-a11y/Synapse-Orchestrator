"""
Tests for Synapse-Orchestrator HTTP API
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Synapse-Orchestrator"
    assert data["status"] == "operational"
    assert data["agents_active"] == 11
    assert data["consensus_threshold"] == 0.92


def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "uptime_seconds" in data
    assert "rate_limiter_tokens_available" in data


def test_evaluate_endpoint_success():
    payload = {
        "payload": "EURUSD H1: price=1.0850, ATR=0.0042, RSI=62, order-block confluence at 1.0835."
    }
    response = client.post("/v1/consensus/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "weighted_score" in data
    assert "should_execute" in data
    assert "agreement" in data
    assert "room_scores" in data
    assert "sentiment" in data["room_scores"]
    assert "strategy" in data["room_scores"]
    assert "math" in data["room_scores"]


def test_evaluate_endpoint_validation_error():
    # Payload too short (fails pydantic min_length=5)
    payload = {"payload": "EUR"}
    response = client.post("/v1/consensus/evaluate", json=payload)
    assert response.status_code == 422
