from __future__ import annotations


MAX_EPISODES = 24
FORGET_AFTER_TICKS = 96


def empty_memory() -> dict:
    return {"episodes": [], "locations": {}, "recognized": []}


def remember(memory: dict, perception: dict, epoch: int, reward: float) -> dict:
    episodes = list(memory.get("episodes", []))
    episodes.append(
        {
            "epoch": int(epoch),
            "origin": list(perception["origin"]),
            "reward": round(float(reward), 10),
        }
    )
    episodes = [e for e in episodes if int(epoch) - int(e["epoch"]) <= FORGET_AFTER_TICKS]
    episodes = episodes[-MAX_EPISODES:]

    locations = dict(memory.get("locations", {}))
    for cell in perception["cells"]:
        key = f"{int(cell['x'])},{int(cell['y'])}"
        locations[key] = {
            "last_seen_epoch": int(epoch),
            "food_kg": float(cell["food_kg"]),
            "water_kg": float(cell["water_kg"]),
            "woody_kg": float(cell.get("woody_kg", 0.0)),
            "rock_exposure": float(cell.get("rock_exposure", 0.0)),
            "natural_shelter": float(cell.get("natural_shelter", 0.0)),
        }
    locations = {
        k: v for k, v in locations.items()
        if int(epoch) - int(v["last_seen_epoch"]) <= FORGET_AFTER_TICKS
    }
    return {
        "episodes": episodes,
        "locations": locations,
        "recognized": sorted(set(memory.get("recognized", [])) | set(perception.get("recognized", []))),
    }
