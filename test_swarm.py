"""
Async test suite for Synapse-Orchestrator.

Verifies:
  1. Full agreement (>= 0.92) authorizes execution.
  2. Disagreement (< 0.92) cleanly pauses and logs the mathematical failure.
  3. Boundary conditions at 0.92 threshold.
  4. End-to-end evaluate() in mock mode.
  5. Input validation (empty payloads, missing rooms).
"""

from __future__ import annotations

import pytest

from swarm_orchestrator import (
    AgentScore,
    ConsensusResult,
    Room,
    SwarmOrchestrator,
    CONSENSUS_THRESHOLD,
)


def make_score(value: int) -> AgentScore:
    return AgentScore(score=value, rationale="mock")


def test_consensus_full_agreement() -> None:
    """All rooms at +10 -> agreement = 1.0 >= 0.92 -> execute."""
    engine = SwarmOrchestrator(api_key="test-key")
    scores = {
        Room.SENTIMENT: 10,
        Room.STRATEGY: 10,
        Room.MATH: 10,
    }
    result = engine.compute_consensus(scores)

    assert isinstance(result, ConsensusResult)
    assert result.agreement == 1.0
    assert result.should_execute is True
    assert "authorized" in result.message.lower()


def test_consensus_disagreement() -> None:
    """Mixed scores producing ~0.83 agreement -> pause."""
    engine = SwarmOrchestrator(api_key="test-key")
    # 0.30*9 + 0.40*8 + 0.30*8 = 2.7 + 3.2 + 2.4 = 8.3 -> 0.83
    scores = {
        Room.SENTIMENT: 9,
        Room.STRATEGY: 8,
        Room.MATH: 8,
    }
    result = engine.compute_consensus(scores)

    assert isinstance(result, ConsensusResult)
    assert result.agreement < CONSENSUS_THRESHOLD
    assert result.should_execute is False
    assert "paused" in result.message.lower()


def test_consensus_boundary() -> None:
    """Exactly >= 0.92 must pass."""
    engine = SwarmOrchestrator(api_key="test-key")
    scores = {
        Room.SENTIMENT: 10,
        Room.STRATEGY: 9,
        Room.MATH: 9,
    }
    # 0.30*10 + 0.40*9 + 0.30*9 = 3.0 + 3.6 + 2.7 = 9.3 -> 0.93 >= 0.92
    result = engine.compute_consensus(scores)
    assert result.agreement >= CONSENSUS_THRESHOLD
    assert result.should_execute is True


def test_missing_room_scores_raises() -> None:
    """Missing a room in scores mapping must raise ValueError."""
    engine = SwarmOrchestrator(api_key="test-key")
    scores = {
        Room.SENTIMENT: 10,
        Room.STRATEGY: 10,
    }
    with pytest.raises(ValueError, match="Scores must contain every room"):
        engine.compute_consensus(scores)


@pytest.mark.asyncio
async def test_evaluate_mock_pipeline() -> None:
    """End-to-end evaluation in mock mode returns valid ConsensusResult."""
    engine = SwarmOrchestrator(api_key=None)
    assert engine.mode == "mock"
    result = await engine.evaluate("EURUSD H1: price=1.0850, test payload")
    assert isinstance(result, ConsensusResult)
    assert 0.0 <= result.agreement <= 1.0
    assert result.mode == "mock"
    assert len(result.room_scores) == 3


@pytest.mark.asyncio
async def test_evaluate_empty_payload_raises() -> None:
    """Empty payload must fail fast with ValueError."""
    engine = SwarmOrchestrator(api_key=None)
    with pytest.raises(ValueError, match="market_payload must be a non-empty string"):
        await engine.evaluate("")


@pytest.mark.asyncio
async def test_evaluate_whitespace_payload_raises() -> None:
    """Whitespace-only payload must fail fast with ValueError."""
    engine = SwarmOrchestrator(api_key=None)
    with pytest.raises(ValueError, match="market_payload must be a non-empty string"):
        await engine.evaluate("   \n\t  ")