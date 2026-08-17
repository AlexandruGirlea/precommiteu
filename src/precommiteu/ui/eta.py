from __future__ import annotations

CLAMP_MIN = 3.0
CLAMP_MAX = 90.0


def _key(route: str) -> tuple[str, str]:
    return ("c_orch", "n_orch") if route == "orchestrator" else ("c_direct", "n_direct")


def observe(
    timing: dict,
    route: str,
    duration_s: float,
    chunks: int,
    fell_back: bool,
    exit_reason: str,
) -> None:
    # Fell-back and budget-exhausted files would poison the mean.
    if fell_back or exit_reason == "budget_exhausted_time":
        return
    c_key, n_key = _key(route)
    sample = min(max(duration_s / max(1, chunks), CLAMP_MIN), CLAMP_MAX)
    n = timing[n_key]
    timing[c_key] = sample if n == 0 else (timing[c_key] * n + sample) / (n + 1)
    timing[n_key] = n + 1


def remaining(
    timing: dict,
    queued: list[dict],
    current: dict | None,
    current_elapsed_s: float,
    cold_remaining_s: float,
) -> float:
    def cost(entry: dict) -> float:
        c = timing["c_orch"] if entry["route"] == "orchestrator" else timing["c_direct"]
        return c * max(1, entry["chunks"])

    total = cold_remaining_s + sum(cost(e) for e in queued)
    if current is not None:
        total += max(0.0, cost(current) - current_elapsed_s)
    return total


def smooth(shown: float | None, target: float, dt: float) -> float:
    if shown is None:
        return target
    if target < shown:
        return max(target, shown - dt)
    return shown * 0.85 + target * 0.15
