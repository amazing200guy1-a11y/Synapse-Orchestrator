"""
Synapse-Orchestrator HTTP API
-----------------------------
Production-grade FastAPI service exposing the 11-agent consensus engine.
Provides interactive OpenAPI/Swagger telemetry documentation at /docs.
"""

from __future__ import annotations

import time
from typing import Any, Dict
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from swarm_orchestrator import (
    SwarmOrchestrator,
    ConsensusResult,
    CONSENSUS_THRESHOLD,
    _API_RATE_LIMITER,
)

app = FastAPI(
    title="Synapse-Orchestrator API",
    description="High-Throughput 11-Agent LLM Consensus Engine with Deterministic Fail-Closed Security Gates.",
    version="1.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

START_TIME = time.time()


class EvaluateRequest(BaseModel):
    payload: str = Field(
        ...,
        min_length=5,
        description="Market telemetry snapshot or text payload to be evaluated by the 11-agent swarm.",
        json_schema_extra={
            "example": "EURUSD H1: price=1.0850, ATR=0.0042, RSI=62, order-block confluence at 1.0835, FOMC blackout clear."
        },
    )


@app.get("/", tags=["System"])
async def root() -> Dict[str, Any]:
    return {
        "service": "Synapse-Orchestrator",
        "version": "1.2.0",
        "documentation": "/docs",
        "status": "operational",
        "consensus_threshold": CONSENSUS_THRESHOLD,
        "agents_active": 11,
        "rooms": ["sentiment", "strategy", "math"],
    }


@app.get("/health", tags=["System"])
async def health_check() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "uptime_seconds": round(time.time() - START_TIME, 2),
        "rate_limiter_tokens_available": round(_API_RATE_LIMITER._tokens, 2),
    }


@app.post("/v1/consensus/evaluate", response_model=ConsensusResult, tags=["Consensus"])
async def evaluate_market(request: EvaluateRequest):
    """
    Evaluates market telemetry across the 11-agent consensus swarm.
    Fans out parallel evaluations across Sentiment, Strategy, and Math rooms,
    enforcing a strict >=92.0% agreement threshold before approval.
    """
    try:
        async with SwarmOrchestrator() as orchestrator:
            return await orchestrator.evaluate(request.payload)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Consensus engine failure: {str(exc)}")
