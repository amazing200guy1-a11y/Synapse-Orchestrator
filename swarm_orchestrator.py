"""
Synapse-Orchestrator
--------------------
High-throughput multi-agent LLM consensus engine (public showcase edition).

- When OPENROUTER_API_KEY is present → live concurrent calls via OpenRouter.
- When the key is missing → automatic fallback to an advanced local mock
  simulation that models realistic network latency across the three rooms
  (Sentiment, Strategy, Math) and emits structured JSON consensus streams.

Designed to demonstrate production-grade typing, error surfaces, and
fail-closed consensus behaviour.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Sequence

import httpx
from pydantic import BaseModel, Field, ValidationError, field_validator

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger("synapse.orchestrator")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)

# ---------------------------------------------------------------------------
# Constants & Configuration
# ---------------------------------------------------------------------------

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
CONSENSUS_THRESHOLD = 0.92
REQUEST_TIMEOUT_SECONDS = 12.0

# Mock simulation latency bounds (seconds) — models concurrent network jitter
MOCK_LATENCY_MIN = 0.18
MOCK_LATENCY_MAX = 0.65


class Room(str, Enum):
    SENTIMENT = "sentiment"
    STRATEGY = "strategy"
    MATH = "math"


# Static weights must sum to 1.0
ROOM_WEIGHTS: Dict[Room, float] = {
    Room.SENTIMENT: 0.30,
    Room.STRATEGY: 0.40,
    Room.MATH: 0.30,
}

# Example model routing (live mode)
ROOM_MODELS: Dict[Room, str] = {
    Room.SENTIMENT: "anthropic/claude-3.5-sonnet",
    Room.STRATEGY: "openai/gpt-4o",
    Room.MATH: "deepseek/deepseek-chat",
}

# Mock agent identities (11-agent flavour across three rooms)
MOCK_AGENTS: Dict[Room, List[str]] = {
    Room.SENTIMENT: ["The Don", "Phantom", "Oracle"],
    Room.STRATEGY: ["Caesar", "Sage", "Guardian", "Vanguard"],
    Room.MATH: ["Titan", "Atlas", "Forge", "Sentinel"],
}


# ---------------------------------------------------------------------------
# Strict schemas
# ---------------------------------------------------------------------------

class AgentScore(BaseModel):
    """Forced structured output from every model / mock agent."""

    score: int = Field(..., ge=-10, le=10, description="Integer conviction in [-10, +10]")
    rationale: str = Field(..., max_length=256)

    @field_validator("score")
    @classmethod
    def score_must_be_int(cls, v: int) -> int:
        if not isinstance(v, int):
            raise ValueError("score must be an integer")
        return v


class ConsensusResult(BaseModel):
    agreement: float
    weighted_score: float
    room_scores: Dict[str, int]
    agent_breakdown: Dict[str, List[Dict[str, Any]]]
    should_execute: bool
    mode: str                          # "live" | "mock"
    message: str
    elapsed_ms: float


# ---------------------------------------------------------------------------
# Request descriptor
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RoomRequest:
    room: Room
    model: str
    system_prompt: str
    user_payload: str


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------

class SwarmOrchestrator:
    """
    Asynchronous multi-agent consensus engine.

    Live path  : shared httpx.AsyncClient + asyncio.gather → OpenRouter.
    Mock path  : concurrent asyncio.sleep latency simulation + deterministic
                 structured scores when no API key is available.
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        raw = api_key if api_key is not None else os.getenv("OPENROUTER_API_KEY")
        self.api_key: Optional[str] = raw.strip() if raw and raw.strip() else None
        self.mode: str = "live" if self.api_key else "mock"
        self._client: Optional[httpx.AsyncClient] = None

        if self.mode == "mock":
            logger.warning(
                "OPENROUTER_API_KEY not found — activating advanced local mock "
                "simulation engine (11-agent latency model)."
            )
        else:
            logger.info("Live OpenRouter mode enabled.")

    async def __aenter__(self) -> "SwarmOrchestrator":
        if self.mode == "live":
            assert self.api_key is not None
            self._client = httpx.AsyncClient(
                base_url=OPENROUTER_BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/amazing200guy1-a11y/Synapse-Orchestrator",
                    "X-Title": "Synapse-Orchestrator",
                },
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        return self

    async def __aexit__(self, *exc: Any) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------
    # Live path
    # ------------------------------------------------------------------

    async def _call_room_live(self, req: RoomRequest) -> AgentScore:
        assert self._client is not None

        payload = {
            "model": req.model,
            "messages": [
                {"role": "system", "content": req.system_prompt},
                {"role": "user", "content": req.user_payload},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "agent_score",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "score": {"type": "integer", "minimum": -10, "maximum": 10},
                            "rationale": {"type": "string", "maxLength": 256},
                        },
                        "required": ["score", "rationale"],
                        "additionalProperties": False,
                    },
                },
            },
            "temperature": 0.0,
            "max_tokens": 128,
        }

        try:
            resp = await self._client.post("/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return AgentScore.model_validate_json(content)
        except httpx.TimeoutException:
            logger.error("Timeout calling room %s (model=%s)", req.room.value, req.model)
            raise
        except (httpx.HTTPStatusError, ValidationError, KeyError, ValueError) as exc:
            logger.error("Failed to parse response from room %s: %s", req.room.value, exc)
            raise

    # ------------------------------------------------------------------
    # Mock path — concurrent latency + structured agent votes
    # ------------------------------------------------------------------

    async def _simulate_agent(
        self,
        room: Room,
        agent_name: str,
        payload: str,
    ) -> Dict[str, Any]:
        """
        Simulate a single agent inside a room.
        Realistic network jitter via asyncio.sleep; returns structured vote.
        """
        delay = random.uniform(MOCK_LATENCY_MIN, MOCK_LATENCY_MAX)
        await asyncio.sleep(delay)

        # Deterministic-ish but varied scores based on room + light noise
        base = {
            Room.SENTIMENT: 7,
            Room.STRATEGY: 8,
            Room.MATH: 6,
        }[room]
        noise = random.randint(-3, 3)
        score = max(-10, min(10, base + noise))

        rationale_pool = {
            Room.SENTIMENT: [
                "Order-flow imbalance favours continuation",
                "Retail sentiment extreme — fade probability elevated",
                "Narrative alignment with macro catalyst",
            ],
            Room.STRATEGY: [
                "Clean OTE entry with HTF bias confirmation",
                "Liquidity sweep complete — displacement confirmed",
                "Risk-reward below institutional threshold",
            ],
            Room.MATH: [
                "ATR-normalised edge positive after costs",
                "Volatility regime supportive of mean-reversion",
                "Expectancy degraded by current spread",
            ],
        }
        rationale = random.choice(rationale_pool[room])

        return {
            "agent": agent_name,
            "room": room.value,
            "score": score,
            "rationale": rationale,
            "latency_ms": round(delay * 1000, 1),
        }

    async def _call_room_mock(self, req: RoomRequest) -> tuple[AgentScore, List[Dict[str, Any]]]:
        """
        Fan-out concurrent mock agents for one room, then aggregate to a
        single room-level AgentScore (median-style for stability).
        """
        agents = MOCK_AGENTS[req.room]
        tasks = [
            self._simulate_agent(req.room, name, req.user_payload)
            for name in agents
        ]
        votes: List[Dict[str, Any]] = await asyncio.gather(*tasks)

        scores = [int(v["score"]) for v in votes]
        # Robust aggregation: median
        scores_sorted = sorted(scores)
        mid = len(scores_sorted) // 2
        if len(scores_sorted) % 2 == 0:
            room_score = int(round((scores_sorted[mid - 1] + scores_sorted[mid]) / 2))
        else:
            room_score = scores_sorted[mid]

        room_score = max(-10, min(10, room_score))
        rationale = f"Room aggregate from {len(votes)} agents (median={room_score})"

        return AgentScore(score=room_score, rationale=rationale), votes

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _build_requests(self, market_payload: str) -> List[RoomRequest]:
        system_prompts = {
            Room.SENTIMENT: (
                "You are the Sentiment Room. Score market sentiment from -10 (extreme fear) "
                "to +10 (extreme greed). Return only the required JSON schema."
            ),
            Room.STRATEGY: (
                "You are the Strategy Room. Evaluate setup quality and directional bias. "
                "Score from -10 (strong short) to +10 (strong long). Return only JSON."
            ),
            Room.MATH: (
                "You are the Math Room. Assess statistical edge, volatility regime, and "
                "risk-adjusted expectancy. Score from -10 to +10. Return only JSON."
            ),
        }
        return [
            RoomRequest(
                room=room,
                model=ROOM_MODELS[room],
                system_prompt=system_prompts[room],
                user_payload=market_payload,
            )
            for room in Room
        ]

    def compute_consensus(
        self,
        scores: Mapping[Room, int],
        agent_breakdown: Dict[str, List[Dict[str, Any]]],
        mode: str,
        elapsed_ms: float,
    ) -> ConsensusResult:
        """
        Deterministic weighted consensus.

        C = Σ (wᵢ × sᵢ) / 10          → range [-1, +1]
        agreement = |C|
        Execute only if agreement ≥ CONSENSUS_THRESHOLD (0.92).
        """
        if set(scores.keys()) != set(Room):
            raise ValueError("Scores must contain every room")

        weighted = sum(ROOM_WEIGHTS[r] * scores[r] for r in Room)
        normalized = weighted / 10.0
        agreement = abs(normalized)
        should_execute = agreement >= CONSENSUS_THRESHOLD
        room_scores = {r.value: scores[r] for r in Room}

        if should_execute:
            msg = (
                f"Consensus reached: agreement={agreement:.4f} ≥ {CONSENSUS_THRESHOLD}. "
                f"Execution signal authorized."
            )
        else:
            msg = (
                f"Consensus failed: agreement={agreement:.4f} < {CONSENSUS_THRESHOLD}. "
                f"Execution paused — mathematical disagreement."
            )

        return ConsensusResult(
            agreement=round(agreement, 6),
            weighted_score=round(normalized, 6),
            room_scores=room_scores,
            agent_breakdown=agent_breakdown,
            should_execute=should_execute,
            mode=mode,
            message=msg,
            elapsed_ms=round(elapsed_ms, 2),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def evaluate(self, market_payload: str) -> ConsensusResult:
        """
        Full pipeline: concurrent room evaluation → validation → weighted consensus.
        Automatically selects live or mock path.
        Fails closed on any individual room error in live mode.
        """
        if not market_payload or not market_payload.strip():
            raise ValueError("market_payload must be a non-empty string")

        requests = self._build_requests(market_payload)
        t0 = time.perf_counter()
        agent_breakdown: Dict[str, List[Dict[str, Any]]] = {
            r.value: [] for r in Room
        }

        if self.mode == "live":
            tasks = [self._call_room_live(req) for req in requests]
            results: Sequence[AgentScore] = await asyncio.gather(*tasks)
            scores = {req.room: result.score for req, result in zip(requests, results)}
            # Live path does not expand per-agent breakdown
            for req, result in zip(requests, results):
                agent_breakdown[req.room.value].append(
                    {
                        "agent": req.model,
                        "room": req.room.value,
                        "score": result.score,
                        "rationale": result.rationale,
                        "latency_ms": None,
                    }
                )
        else:
            # Mock path — true concurrent fan-out across all agents in all rooms
            room_tasks = [self._call_room_mock(req) for req in requests]
            room_results = await asyncio.gather(*room_tasks)

            scores = {}
            for req, (room_score, votes) in zip(requests, room_results):
                scores[req.room] = room_score.score
                agent_breakdown[req.room.value] = votes

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        consensus = self.compute_consensus(scores, agent_breakdown, self.mode, elapsed_ms)

        # Structured JSON stream to terminal (showcase visibility)
        logger.info("CONSENSUS_STREAM %s", consensus.model_dump_json())
        logger.info(consensus.message)

        return consensus


# ---------------------------------------------------------------------------
# Entry point (demo)
# ---------------------------------------------------------------------------

async def main() -> None:
    sample_payload = (
        "EURUSD H1: price=1.0850, ATR=0.0042, RSI=62, "
        "order-block confluence at 1.0835, FOMC blackout clear."
    )

    async with SwarmOrchestrator() as engine:
        result = await engine.evaluate(sample_payload)
        # Pretty-print for showcase
        print(json.dumps(result.model_dump(), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
