---

### 2. `swarm_orchestrator.py`

```python
"""
Synapse-Orchestrator
--------------------
High-throughput multi-agent LLM consensus engine.

Dispatches concurrent evaluation requests across specialized model rooms
via OpenRouter, enforces a deterministic weighted consensus threshold,
and emits a clean execution signal only when agreement ≥ 92 %.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence

import httpx
from pydantic import BaseModel, Field, ValidationError, field_validator

# ---------------------------------------------------------------------------
# Configuration & Constants
# ---------------------------------------------------------------------------

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
CONSENSUS_THRESHOLD = 0.92
REQUEST_TIMEOUT_SECONDS = 12.0

logger = logging.getLogger("synapse.orchestrator")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)


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

# Example model routing (swap freely via OpenRouter)
ROOM_MODELS: Dict[Room, str] = {
    Room.SENTIMENT: "anthropic/claude-3.5-sonnet",
    Room.STRATEGY: "openai/gpt-4o",
    Room.MATH: "deepseek/deepseek-chat",
}


# ---------------------------------------------------------------------------
# Strict JSON Schema (Pydantic)
# ---------------------------------------------------------------------------

class AgentScore(BaseModel):
    """Forced structured output from every model."""

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
    should_execute: bool
    message: str


# ---------------------------------------------------------------------------
# Core Engine
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RoomRequest:
    room: Room
    model: str
    system_prompt: str
    user_payload: str


class SwarmOrchestrator:
    """
    Asynchronous multi-agent consensus engine.

    - Uses a shared httpx.AsyncClient for connection pooling.
    - Fans out all room evaluations with asyncio.gather.
    - Validates every response against AgentScore before aggregation.
    - Applies deterministic weighted consensus; fails closed on any error.
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise EnvironmentError("OPENROUTER_API_KEY is required")

        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "SwarmOrchestrator":
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
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _call_room(self, req: RoomRequest) -> AgentScore:
        """Issue a single structured completion request."""
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
            logger.error(
                "Failed to parse response from room %s: %s", req.room.value, exc
            )
            raise

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

    def compute_consensus(self, scores: Dict[Room, int]) -> ConsensusResult:
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
            should_execute=should_execute,
            message=msg,
        )

    async def evaluate(self, market_payload: str) -> ConsensusResult:
        """
        Full pipeline: concurrent room calls → validation → weighted consensus.
        Fails closed on any individual room error.
        """
        requests = self._build_requests(market_payload)

        # Fan-out: all rooms execute concurrently
        tasks = [self._call_room(req) for req in requests]
        results: Sequence[AgentScore] = await asyncio.gather(*tasks)

        scores: Dict[Room, int] = {
            req.room: result.score for req, result in zip(requests, results)
        }

        consensus = self.compute_consensus(scores)
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
        print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
