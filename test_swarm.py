"""
Async test suite for Synapse-Orchestrator.

Verifies:
  1. Full agreement (≥ 92 %) authorizes execution.
  2. Disagreement (< 92 %) cleanly pauses and logs the mathematical failure.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from swarm_orchestrator import (
    AgentScore,
    ConsensusResult,
    Room,
    SwarmOrchestrator,
    CONSENSUS_THRESHOLD,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_score(value: int) -> AgentScore:
    return AgentScore(score=value, rationale="mock")


# ---------------------------------------------------------------------------
# Unit tests for pure consensus math (no network)
# ---------------------------------------------------------------------------

def test_consensus_full_agreement() -> None:
    """All rooms at +10 → agreement = 1.0 ≥ 0.92 → execute."""
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
    """Mixed scores producing \~0.85 agreement → pause."""
    engine = SwarmOrchestrator(api_key="test-key")
    # 0.30*9 + 0.40*8 + 0.30*8 = 2.7 + 3.2 + 2.4 = 8.3 → 0.83
    scores = {
        Room.SENTIMENT: 9,
        Room.STRATEGY: 8,
        Room.MATH: 8,
    }
    result = engine.compute_consensus(scores)

    assert result.agreement < CONSENSUS_THRESHOLD
    assert result.should_execute is False
    assert "paused" in result.message.lower() or "disagreement" in result.message.lower()


def test_consensus_boundary() -> None:
    """Exactly ≥ 0.92 must pass."""
    engine = SwarmOrchestrator(api_key="test-key")
    scores = {
        Room.SENTIMENT: 10,
        Room.STRATEGY: 9,
        Room.MATH: 9,
    }
    # 0.30*10 + 0.40*9 + 0.30*9 = 3.0 + 3.6 + 2.7 = 9.3 → 0.93
    result = engine.compute_consensus(scores)
    assert result.agreement >= CONSENSUS_THRESHOLD
    assert result.should_execute is True


# ---------------------------------------------------------------------------
# Async integration-style tests (mocked network)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_evaluate_agreement_triggers_execution() -> None:
    """Mock all rooms returning high scores → should_execute=True."""
    mock_scores = [
        make_score(10),  # Sentiment
        make_score(10),  # Strategy
        make_score(10),  # Math
    ]

    with patch.object(
        SwarmOrchestrator, "_call_room", new_callable=AsyncMock
    ) as mock_call:
        mock_call.side_effect = mock_scores

        async with SwarmOrchestrator(api_key="test-key") as engine:
            result = await engine.evaluate("mock market payload")

        assert result.should_execute is True
        assert result.agreement >= CONSENSUS_THRESHOLD
        assert mock_call.await_count == 3


@pytest.mark.asyncio
async def test_evaluate_disagreement_blocks_execution() -> None:
    """Mock mixed scores (\~0.83) → should_execute=False and clean pause message."""
    mock_scores = [
        make_score(9),   # Sentiment
        make_score(8),   # Strategy
        make_score(8),   # Math
    ]

    with patch.object(
        SwarmOrchestrator, "_call_room", new_callable=AsyncMock
    ) as mock_call:
        mock_call.side_effect = mock_scores

        async with SwarmOrchestrator(api_key="test-key") as engine:
            result = await engine.evaluate("mock market payload")

        assert result.should_execute is False
        assert result.agreement < CONSENSUS_THRESHOLD
        assert "disagreement" in result.message.lower() or "paused" in result.message.lower()
        assert mock_call.await_count == 3
