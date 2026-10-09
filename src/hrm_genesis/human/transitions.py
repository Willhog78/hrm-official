"""Bounded memory of an individual's experienced physical transitions.

Version 1 is write-only. Version 2 values short experienced chains from actual
physiological benefit, cost and uncertainty. Inputs are local perceptual
projections supplied by interactions, never raw world or peer state.
Version 3 additionally accumulates bounded delayed thermal returns.
Version 4 joins own observed consecutive progress over a six-action horizon.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json


MODEL = "experienced-transitions-v1"
VALUED_MODEL = "experienced-transitions-v2"
DELAYED_MODEL = "experienced-transitions-v3"
PROCEDURAL_MODEL = "experienced-transitions-v4"
DELAYED_MODELS = {DELAYED_MODEL, PROCEDURAL_MODEL}
VALUED_MODELS = {VALUED_MODEL, *DELAYED_MODELS}
MODELS = {MODEL, *VALUED_MODELS}
THERMAL_HORIZON = 32
THERMAL_DISCOUNT = 0.97
PLAN_DEPTH = 3
MIN_PLAN_EXPERIENCE = 2
UNKNOWN_OUTCOMES = 2
CONTINUATION_DISCOUNT = 0.9
MAX_PLAN_EXPANSIONS = 128
MAX_TRANSITIONS = 64
RECENT_LENGTH = 8
FORGET_AFTER_TICKS = 96
MAX_OBJECT_FORMS = 24
MAX_ACTS = 64
PROCEDURAL_DEPTH = 6
MAX_LINKS = 128


def _procedural_state(state: dict) -> str:
    # Current body reserves still guard live choice. They are not material
    # prerequisites and must not sever an otherwise intact overnight procedure.
    physical = {k: v for k, v in state.items() if k != "body"}
    if len(state.get("body", [])) >= 4:
        physical["injury"] = state["body"][3]
    return json.dumps(physical,
                      sort_keys=True, separators=(",", ":"))


def _material_changes(edge: dict) -> set[str]:
    """Coarse perceptible aspects changed by an actual transition."""
    before, after = edge["before"], edge["after"]
    changed = set()
    for field in ("held", "ground", "worn"):
        old = {json.dumps(f): f for f in before.get(field, [])}
        new = {json.dumps(f): f for f in after.get(field, [])}
        for key in old.keys() ^ new.keys():
            form = old.get(key, new.get(key))
            changed.add(f"{field}:{form[0]}")
    for i, (old, new) in enumerate(zip(before.get("pools", []), after.get("pools", []))):
        if old != new:
            changed.add(f"pool:{i}")
    if before.get("geometry") != after.get("geometry"):
        changed.add("geometry")
    return changed


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
    cognition["transition_memory"] = {"model": memory["model"], "edges": edges, "recent": recent}
    if memory["model"] == PROCEDURAL_MODEL:
        cognition["transition_memory"]["links"] = [link for link in memory.get("links", [])
                                                    if link["from"] in retained and link["to"] in retained
                                                    and int(epoch) - int(link["last_epoch"]) <= FORGET_AFTER_TICKS][-MAX_LINKS:]


def record(cognition: dict, before: dict, act: str, after: dict,
           effort_kcal: float, injury: float, epoch: int, *, model: str = MODEL) -> str:
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
    prior_ref = recent[-1] if recent else None
    recent.append({"edge": edge_id, "epoch": int(epoch)})
    cognition["transition_memory"] = {"model": model, "edges": edges,
                                       "recent": recent[-RECENT_LENGTH:]}
    if model == PROCEDURAL_MODEL:
        links = [dict(link) for link in memory.get("links", [])
                 if link["from"] in retained and link["to"] in retained]
        previous = next((e for e in edges if prior_ref and e["id"] == prior_ref["edge"]), None)
        if (previous is not None and 0 <= int(epoch) - int(prior_ref["epoch"]) <= 1
                and _procedural_state(previous["after"]) == _procedural_state(before)
                and (act in previous["enabled"] or _material_changes(previous) & _material_changes(edge))):
            link = next((link for link in links if link["from"] == previous["id"] and link["to"] == edge_id), None)
            if link is None:
                link = {"from": previous["id"], "to": edge_id, "n": 0}
            else:
                links.remove(link)
            link["n"] += 1
            link["last_epoch"] = int(epoch)
            links.append(link)
        cognition["transition_memory"]["links"] = links[-MAX_LINKS:]
    return edge_id


def credit(cognition: dict, edge_id: str, gain_basal: float) -> None:
    """Credit a particular experienced transition, never a time-near action.

    The physical caller owns attribution and the benefit budget. Direct and
    thermal components may add to one trial; n still counts physical attempts.
    """
    memory = cognition.get("transition_memory", {})
    if memory.get("model") not in VALUED_MODELS:
        return
    edges = []
    for original in memory["edges"]:
        edge = dict(original)
        if edge["id"] == edge_id:
            edge["gain_sum_basal"] = round(float(edge.get("gain_sum_basal", 0.0))
                                           + max(0.0, float(gain_basal)), 10)
        edges.append(edge)
    cognition["transition_memory"] = {**memory, "edges": edges}


def action_values(cognition: dict, state: dict, basal_kcal: float,
                  depth: int | None = None) -> dict[str, float]:
    """Bounded expected net value over experienced state transitions only.

    Costs and failures count. Two unknown adverse outcomes shrink expected
    benefit, without discounting costs. V2/V3 use newly enabled actions over
    three steps; V4 uses repeatedly observed consecutive progress over six.
    No state is applied to reality.
    """
    memory = cognition.get("transition_memory", {})
    if memory.get("model") not in VALUED_MODELS:
        return {}
    if memory["model"] == PROCEDURAL_MODEL:
        return _procedural_values(memory, state, basal_kcal,
                                  PROCEDURAL_DEPTH if depth is None else depth)
    basal = max(1e-9, float(basal_kcal))
    indexed: dict[str, dict[str, list[dict]]] = {}
    state_key = lambda s: json.dumps(s, sort_keys=True, separators=(",", ":"))
    for edge in memory["edges"]:
        indexed.setdefault(state_key(edge["before"]), {}).setdefault(edge["act"], []).append(edge)
    budget = MAX_PLAN_EXPANSIONS

    def evaluate(current: dict, remaining: int, used: frozenset[str], allowed=None) -> dict[str, float]:
        nonlocal budget
        if budget <= 0:
            return {}
        budget -= 1
        results = {}
        for act, outcomes in sorted(indexed.get(state_key(current), {}).items()):
            if act in used or (allowed is not None and act not in allowed):
                continue
            n = sum(int(e["n"]) for e in outcomes)
            if n < MIN_PLAN_EXPERIENCE:
                continue
            benefit = 0.0
            cost = 0.0
            for edge in outcomes:
                trials = int(edge["n"])
                continuation = 0.0
                if remaining > 1 and edge["enabled"]:
                    following = evaluate(edge["after"], remaining - 1,
                                         used | {act}, set(edge["enabled"]))
                    continuation = max(0.0, max(following.values(), default=0.0))
                benefit += float(edge.get("gain_sum_basal", 0.0))
                benefit += trials * CONTINUATION_DISCOUNT * continuation
                cost += trials * (float(edge["effort_kcal"]) / basal + 2.0 * float(edge["injury"]))
            results[act] = round(benefit / (n + UNKNOWN_OUTCOMES) - cost / n, 10)
        return results

    return evaluate(state, max(1, min(PLAN_DEPTH, PLAN_DEPTH if depth is None else int(depth))), frozenset())


def _procedural_values(memory: dict, state: dict, basal_kcal: float, depth: int) -> dict[str, float]:
    """Search only repeated own observed adjacency, with bounded state progress.

    Material-change overlap is a conservative dependence cue, not a complete
    causal proof. No no-op or return to an already visited material state can
    bootstrap a rewarded loop. Changed weather/access remain distinct states.
    """
    basal = max(1e-9, float(basal_kcal))
    indexed: dict[str, dict[str, list[dict]]] = {}
    for edge in memory["edges"]:
        indexed.setdefault(_procedural_state(edge["before"]), {}).setdefault(edge["act"], []).append(edge)
    links = {(link["from"], link["to"]) for link in memory.get("links", [])
             if int(link["n"]) >= MIN_PLAN_EXPERIENCE}
    budget = MAX_PLAN_EXPANSIONS

    def evaluate(current: dict, remaining: int, visited: frozenset[str], predecessor=None):
        nonlocal budget
        key = _procedural_state(current)
        if budget <= 0 or key in visited:
            return {}
        budget -= 1
        result = {}
        for act, outcomes in sorted(indexed.get(key, {}).items()):
            # All outcomes count, even outcomes not linked to the predecessor.
            if predecessor is not None and not any((predecessor, e["id"]) in links for e in outcomes):
                continue
            n = sum(int(e["n"]) for e in outcomes)
            if n < MIN_PLAN_EXPERIENCE:
                continue
            benefit = cost = 0.0
            for edge in outcomes:
                trials = int(edge["n"])
                future = {}
                if remaining > 1 and _procedural_state(edge["after"]) != key:
                    future = evaluate(edge["after"], remaining - 1, visited | {key}, edge["id"])
                benefit += float(edge.get("gain_sum_basal", 0.0))
                benefit += trials * CONTINUATION_DISCOUNT * max(0.0, max(future.values(), default=0.0))
                cost += trials * (float(edge["effort_kcal"]) / basal + 2.0 * float(edge["injury"]))
            result[act] = round(benefit / (n + UNKNOWN_OUTCOMES) - cost / n, 10)
        return result

    return evaluate(state, max(1, min(PROCEDURAL_DEPTH, int(depth))), frozenset())
