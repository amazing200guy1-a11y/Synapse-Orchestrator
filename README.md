# Synapse-Orchestrator: High-Throughput Multi-Agent LLM Consensus Engine via OpenRouter

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
[![Live Swagger Docs](https://img.shields.io/badge/Live_API-Interactive_Swagger_Docs-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://synapse-orchestrator.onrender.com/docs)
![AsyncIO](https://img.shields.io/badge/AsyncIO-Native-brightgreen?style=for-the-badge)
![OpenRouter](https://img.shields.io/badge/OpenRouter-Multi--Model-6E40C9?style=for-the-badge)
![Redis](https://img.shields.io/badge/Redis-Pub%2FSub-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![Pytest](https://img.shields.io/badge/Pytest-15%2F15_Passing-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)

**Institutional-grade multi-agent orchestration microservice and consensus engine** that fans out concurrent LLM evaluations across specialized analytical rooms, enforces a strict deterministic weighted consensus threshold (≥92%), and broadcasts high-conviction execution signals via Redis Pub/Sub and direct REST API endpoints.

Designed for low-latency decision systems where false positives are capital-destructive and thread-blocking is unacceptable.

---

## 🏛️ System Architecture

```
[ LIVE UNSTRUCTURED MARKET DATA / REST REQUEST ]
                      │
                      ▼
     ┌──────────────────────────────────────────────────┐
     │      SYNAPSE FASTAPI & ASYNCIO INFERENCE ENGINE  │
     │      Async HTTPX Connection Pool & Rate Limiter  │
     └────────────────────────┬─────────────────────────┘
                              │
     ┌────────────────────────┼─────────────────────────┐
     ▼                        ▼                         ▼
┌───────────────┐        ┌───────────────┐        ┌───────────────┐
│ SENTIMENT ROOM│        │ STRATEGY ROOM │        │   MATH ROOM   │
│ Model: Claude │        │ Model: GPT-4o │        │ Model: DeepS. │
└───────┬───────┘        └───────┬───────┘        └───────┬───────┘
        │                        │                        │
        └────────────────────────┼────────────────────────┘
                                 │ (Extracts JSON Score Arrays)
                                 ▼
     ┌──────────────────────────────────────────────────┐
     │     DETERMINISTIC WEIGHTED CONSENSUS FILTER      │
     │    Normalized Conviction Score: C = Σ(wᵢ × sᵢ)/10 │
     └────────────────────────┬─────────────────────────┘
                              │
               ┌──────────────┴──────────────┐
       [ Consensus ≥ 92% ]           [ Consensus < 92% ]
               │                             │
               ▼                             ▼
 ┌───────────────────────────┐ ┌───────────────────────────┐
 │ REDIS ASYNC PUB/SUB & API │ │    EXECUTION GATE PAUSED  │
 │ Broadcasts trade vector   │ │ Discards signal; Logs     │
 │ to all subscriber nodes   │ │ mathematical disagreement │
 └───────────────────────────┘ └───────────────────────────┘
```

---

## ⚡ Technical Design

### 1. Asynchronous Multi-Model Task Pooling
Traditional sequential LLM evaluations introduce multi-second latency and bottleneck runtime execution. Synapse-Orchestrator eliminates this bottleneck by:
- Managing a pooled `httpx.AsyncClient` with reusable keep-alive TCP connections.
- Dispatching all specialized room evaluations concurrently using `asyncio.gather()`.
- Unifying diverse foundation models (Claude 3.5, GPT-4o, DeepSeek) through an abstracted OpenRouter gateway with automated fallback mocks when API credentials are absent.
- Strict Pydantic JSON Schema enforcement guaranteeing structured integer returns in `[-10, +10]` range.

### 2. Deterministic Weighted Consensus Filter
Each analytical room yields an integer conviction score $s_i \in [-10, +10]$. Weights sum to 1.0:

| Analytical Room | Analytical Focus | Model (Default) | Weight |
|---|---|---|---|
| **Sentiment** | Narrative bias, news flow, order-book sentiment | Claude 3.5 Sonnet | 0.30 |
| **Strategy** | Market structure, order blocks, FVG liquidity | GPT-4o | 0.40 |
| **Math** | Statistical variance, Kelly criterion, volatility | DeepSeek-V3 / R1 | 0.30 |

Consensus formula:
$$C = \frac{\sum (w_i \times s_i)}{10} \quad \text{where } C \in [-1.0, +1.0]$$
$$\text{Agreement} = |C|$$

Signal execution requires **$\text{Agreement} \ge 0.92$** (92.0%). Any variance below this floor triggers a fail-closed discard.

---

## 🔌 REST API Endpoints (`api.py`)

Synapse provides production-ready FastAPI endpoints with interactive OpenAPI/Swagger documentation:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Service health status, architecture metadata, and room weights |
| `GET` | `/health` | Real-time liveness check and Redis connection heartbeat |
| `POST` | `/v1/consensus/evaluate` | Evaluates raw market telemetry through the 11-agent consensus engine |

### Sample Evaluation Request:
```bash
curl -X POST "http://localhost:8000/v1/consensus/evaluate" \
     -H "Content-Type: application/json" \
     -d '{
       "symbol": "EURUSD",
       "timeframe": "M15",
       "current_price": 1.08502,
       "atr": 0.0014,
       "market_state": "Bullish expansion above London session highs",
       "news_headline": "ECB maintains current rate posture amid steady inflation"
     }'
```

---

## 🧪 Automated Test Suite (15/15 Green)

The entire microservice and consensus engine are covered with asynchronous unit and integration tests:

```bash
pytest test_swarm.py test_api.py -v
```

```
============================= test session starts =============================
test_swarm.py::test_parse_valid_response PASSED                         [  6%]
test_swarm.py::test_parse_markdown_json PASSED                          [ 13%]
test_swarm.py::test_parse_clamped_score PASSED                         [ 20%]
test_swarm.py::test_parse_malformed_raises PASSED                       [ 26%]
test_swarm.py::test_consensus_bullish_approved PASSED                   [ 33%]
test_swarm.py::test_consensus_mixed_rejected PASSED                     [ 40%]
test_swarm.py::test_consensus_bearish_approved PASSED                   [ 46%]
test_swarm.py::test_rate_limiter PASSED                                 [ 53%]
test_swarm.py::test_evaluate_mock_consensus PASSED                      [ 60%]
test_swarm.py::test_broadcast_without_redis PASSED                      [ 66%]
test_swarm.py::test_invalid_room_weights_rejected PASSED                [ 73%]
test_api.py::test_root_endpoint PASSED                                  [ 80%]
test_api.py::test_health_endpoint PASSED                                [ 86%]
test_api.py::test_evaluate_endpoint_approved PASSED                     [ 93%]
test_api.py::test_evaluate_endpoint_rejected PASSED                     [100%]
============================== 15 passed in 0.42s ==============================
```

---

## 🚀 Deployment Instructions (Render.com / Docker)

Synapse-Orchestrator includes a zero-config `Procfile` ready for one-click deployment:

1. Connect GitHub repository `amazing200guy1-a11y/Synapse-Orchestrator` to **[render.com](https://render.com)**.
2. Select **Web Service**, Runtime: **Python 3**.
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `uvicorn api:app --host 0.0.0.0 --port $PORT`
5. Optional Environment Variables:
   - `OPENROUTER_API_KEY`: Your OpenRouter API key (defaults to deterministic fallback mock)
   - `REDIS_URL`: Redis Pub/Sub connection string

---

## 📁 Repository Structure

```
Synapse-Orchestrator/
├── api.py                    # Production FastAPI microservice layer
├── swarm_orchestrator.py     # Core async concurrency & consensus engine
├── test_swarm.py             # Consensus and rate limiter async tests
├── test_api.py               # FastAPI testclient integration tests
├── Procfile                  # Cloud deployment entrypoint (Render/Railway)
├── requirements.txt          # Pinned runtime dependencies
└── README.md                 # System architecture documentation
```

---

## 👨‍💻 Architect & Engineering Pedigree

**Usman Abayomi Bamidele**  
Senior Backend & AI Systems Engineer  
Specializing in High-Throughput Distributed Microservices, Multi-Agent Concurrency, and Low-Latency Financial Kernels.

- 🐙 **GitHub:** [@amazing200guy1-a11y](https://github.com/amazing200guy1-a11y)
- 💼 **LinkedIn:** [linkedin.com/in/usman-bamidele](https://www.linkedin.com/in/usman-bamidele)
- ✉️ **Contact:** [usmanbamidele200@gmail.com](mailto:usmanbamidele200@gmail.com)
- 🌐 **Live Telemetry Interface:** [sovereign-cockpit-ui.vercel.app](https://sovereign-cockpit-ui.vercel.app)

*License: MIT Open Source.*
