# Contributing to Synapse-Orchestrator

## Quick Start
```bash
git clone https://github.com/amazing200guy1-a11y/Synapse-Orchestrator
cd Synapse-Orchestrator
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -v
```

## Architecture
```
Market Data  -->  Swarm Router  -->  Agent Pool (11 agents)
                                          |
                             Consensus Aggregator (>= 70% threshold)
                                          |
                              Cryptographic Intent Seal
                                          |
                               Execution Signal Emit
```

## Adding a New Agent
1. Create a handler in `swarm_orchestrator.py`
2. Register it in `AGENT_REGISTRY`
3. Write at least one test in `test_swarm.py`
4. Ensure consensus math still holds with the new agent weight
