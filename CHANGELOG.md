# Changelog

All notable changes to Synapse-Orchestrator are documented here.

## [Unreleased]

## [1.1.0] — 2026-09-23
### Added
- Shared `conftest.py` with reusable pytest fixtures for all test modules.
- `pytest.ini` with `asyncio_mode = auto` to eliminate per-test decorators.
- `compute_consensus` now accepts optional `agent_breakdown`, `mode`, `elapsed_ms` (backward-compatible defaults).
- 7-test async suite covering full agreement, disagreement, boundary, empty payload, and whitespace validation.

## [1.0.0] — 2026-09-20
### Added
- Initial release: 11-agent multi-room LLM consensus engine.
- Concurrent HTTPX task pooling via `asyncio.gather`.
- Weighted scoring across Sentiment, Strategy, and Math rooms.
- Redis Pub/Sub broadcast on consensus signals >= 0.92.
- Mock simulation mode for offline / CI execution.