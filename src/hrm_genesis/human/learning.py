from __future__ import annotations


LEARNING_RATE = 0.35


def _contextual_key(x: int, y: int, context: str | None) -> str:
    base = f"{int(x)},{int(y)}"
    return f"{base}|{context}" if context else base


def update_expectations(expectations: dict, perception: dict, reward: float) -> dict:
    updated = dict(expectations)
    ox, oy = map(int, perception["origin"])
    context = perception.get("context")
    key = _contextual_key(ox, oy, context)
    prior = float(updated.get(key, 0.0))
    error = float(reward) - prior
    updated[key] = round(prior + LEARNING_RATE * error, 10)
    return updated


def expectation_for(
    expectations: dict,
    x: int,
    y: int,
    context: str | None = None,
) -> float:
    contextual = _contextual_key(x, y, context)
    if contextual in expectations:
        return float(expectations[contextual])
    return float(expectations.get(f"{int(x)},{int(y)}", 0.0))
