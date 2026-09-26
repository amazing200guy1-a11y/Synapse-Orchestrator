"""
Synapse-Orchestrator — Concurrency & Latency Profiling Benchmark
================================================================
Measures p50, p95, and p99 consensus resolution latencies across
concurrent multi-agent swarm evaluations under simulated high load.
"""

from __future__ import annotations

import asyncio
import time
from typing import List
import numpy as np

from swarm_orchestrator import SwarmOrchestrator, TokenBucket


async def run_swarm_benchmark(total_requests: int = 100, max_concurrency: int = 25) -> dict:
    orchestrator = SwarmOrchestrator()
    semaphore = asyncio.Semaphore(max_concurrency)

    latencies: List[float] = []

    async def single_eval(idx: int):
        payload = f'{{"ticker": "ASSET-{idx}", "signal": "BUY", "confidence": 0.95}}'
        async with semaphore:
            t0 = time.perf_counter()
            await orchestrator.evaluate(payload)
            dt = (time.perf_counter() - t0) * 1000.0  # ms
            latencies.append(dt)

    t_start = time.perf_counter()
    tasks = [single_eval(i) for i in range(total_requests)]
    await asyncio.gather(*tasks)
    total_time = time.perf_counter() - t_start

    lat_arr = np.array(latencies)
    results = {
        "total_evaluations": total_requests,
        "concurrency_limit": max_concurrency,
        "elapsed_seconds": round(total_time, 3),
        "throughput_evals_per_sec": round(total_requests / total_time, 2),
        "latency_p50_ms": round(float(np.percentile(lat_arr, 50)), 2),
        "latency_p95_ms": round(float(np.percentile(lat_arr, 95)), 2),
        "latency_p99_ms": round(float(np.percentile(lat_arr, 99)), 2),
    }

    print("=" * 60)
    print(" SYNAPSE-ORCHESTRATOR CONCURRENCY BENCHMARK RESULTS")
    print("=" * 60)
    for k, v in results.items():
        print(f" {k:<30}: {v}")
    print("=" * 60)
    return results


if __name__ == "__main__":
    asyncio.run(run_swarm_benchmark(total_requests=100, max_concurrency=25))
