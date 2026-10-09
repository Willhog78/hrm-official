"""Bounded memory of an individual's experienced physical transitions.

Stage 1 is write-only: frequencies and costs are learned, but no reward,
sequence value or action preference is inferred. Inputs are local perceptual
projections supplied by interactions, never raw world or peer state.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json


MODEL = "experienced-transitions-v1"
MAX_TRANSITIONS = 64
RECENT_LENGTH = 8
FORGET_AFTER_TICKS = 96
MAX_OBJECT_FORMS = 24
MAX_ACTS = 64


def magnitude_band(value: float, thresholds: tuple[float, ...]) -> int:
    """Zero is distinct; positive magnitudes occupy declared coarse bands."""
    value = float(value)
    if value <= 1e-9:
        return 0
    return 1 + sum(value >= threshold for threshold in thresholds)


def bounded_forms(forms: list[tuple]) -> list[list]:
    """Canonical, identity-free perceptible forms, with counts capped at 3.

    Sorted truncation is deliberate: this abstraction cannot distinguish all
    clutter. It never stores object IDs or scans another individual's hands.
    """
    counts: dict[tuple, int] = {}
    for form in forms:
        counts[form] = min(3, counts.get(form, 0) + 1)
    return [[*form, counts[form]] for form in sorted(counts)[:MAX_OBJECT_FORMS]]


def forget(cognition: dict, epoch: int) -> None:
    """Age out records even on a tick with no chosen interaction."""
    if "transition_memory" not in cognition:
        return
    memory = cognition["transition_memory"]
    edges = [e for e in memory["edges"]
             if int(epoch) - int(e["last_epoch"]) <= FORGET_AFTER_TICKS]
    retained = {e["id"] for e in edges}
    recent = [r for r in memory["recent"]
              if r["edge"] in retained and int(epoch) - int(r["epoch"]) <= FORGET_AFTER_TICKS]
    cognition["transition_memory"] = {"model": MODEL, "edges": edges, "recent": recent}


def record(cognition: dict, before: dict, act: str, after: dict,
           effort_kcal: float, injury: float, epoch: int) -> None:
    """Remember one actual attempt, including attempts with no visible change.

    Separate outcomes for the same before-state/action retain their individual
    counts; a lucky outcome does not become a guaranteed prediction. Costs are
    running means for that outcome. New affordances are evidence of possibility,
    not benefit, causality proof, or a transferred recipe.
    """
    forget(cognition, epoch)
    memory = cognition.get("transition_memory", {"model": MODEL, "edges": [], "recent": []})
    payload = json.dumps([before, act, after], sort_keys=True, separators=(",", ":"))
    edge_id = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    edges = list(memory["edges"])
    prior = next((e for e in edges if e["id"] == edge_id), None)
    if prior is None:
        edge = {"id": edge_id, "before": deepcopy(before), "act": act,
                "after": deepcopy(after), "n": 0, "effort_kcal": 0.0,
                "injury": 0.0,
                "enabled": sorted(set(after["acts"]) - set(before["acts"])),
                "disabled": sorted(set(before["acts"]) - set(after["acts"]))}
    else:
        edge = dict(prior)
        edges.remove(prior)
    n = int(edge["n"]) + 1
    edge["n"] = n
    for field, value in (("effort_kcal", effort_kcal), ("injury", injury)):
        edge[field] = round(float(edge[field]) + (float(value) - float(edge[field])) / n, 10)
    edge["last_epoch"] = int(epoch)
    # Least recently experienced goes first; insertion order breaks same-tick ties.
    edges.append(edge)
    edges = edges[-MAX_TRANSITIONS:]
    retained = {e["id"] for e in edges}
    recent = [r for r in memory["recent"] if r["edge"] in retained]
    recent.append({"edge": edge_id, "epoch": int(epoch)})
    cognition["transition_memory"] = {"model": MODEL, "edges": edges,
                                       "recent": recent[-RECENT_LENGTH:]}
