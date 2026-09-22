"""Shared pytest fixtures for Synapse-Orchestrator test suite."""
import pytest
from swarm_orchestrator import SwarmOrchestrator, Room


@pytest.fixture()
def mock_engine() -> SwarmOrchestrator:
    """Return a SwarmOrchestrator wired to mock mode (no API key)."""
    return SwarmOrchestrator(api_key=None)


@pytest.fixture()
def live_engine() -> SwarmOrchestrator:
    """Return a SwarmOrchestrator in live mode (expects OPENROUTER_API_KEY env var)."""
    return SwarmOrchestrator()


@pytest.fixture()
def full_agreement_scores() -> dict:
    return {Room.SENTIMENT: 10, Room.STRATEGY: 10, Room.MATH: 10}


@pytest.fixture()
def disagreement_scores() -> dict:
    return {Room.SENTIMENT: 9, Room.STRATEGY: 8, Room.MATH: 8}


@pytest.fixture()
def boundary_scores() -> dict:
    """Scores that produce agreement exactly >= 0.92."""
    return {Room.SENTIMENT: 10, Room.STRATEGY: 9, Room.MATH: 9}