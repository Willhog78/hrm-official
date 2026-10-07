from __future__ import annotations


LEARNING_RATE = 0.35


def update_expectations(expectations: dict, perception: dict, reward: float) -> dict:
    updated = dict(expectations)
    ox, oy = map(int, perception["origin"])
    key = f"{ox},{oy}"
    prior = float(updated.get(key, 0.0))
    error = float(reward) - prior
    updated[key] = round(prior + LEARNING_RATE * error, 10)
    return updated


def expectation_for(expectations: dict, x: int, y: int) -> float:
    return float(expectations.get(f"{int(x)},{int(y)}", 0.0))


def update_contextual_expectations(
    expectations: dict,
    perception: dict,
    reward: float,
) -> dict:
    updated = dict(expectations)
    ox, oy = map(int, perception["origin"])
    context = str(perception.get("context", "mild"))
    key = f"{ox},{oy}|{context}"
    prior = float(updated.get(key, 0.0))
    error = float(reward) - prior
    updated[key] = round(prior + LEARNING_RATE * error, 10)
    return updated


def contextual_expectation_for(
    expectations: dict,
    x: int,
    y: int,
    context: str,
) -> float:
    return float(expectations.get(f"{int(x)},{int(y)}|{context}", 0.0))
