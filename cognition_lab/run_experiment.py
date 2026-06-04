from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from hrm_core.kernel import HRMKernel


EXPERIMENTS = ROOT / "experiments"
REPORTS = ROOT / "reports"


COGNITION_FIELDS = (
    "stress",
    "trust",
    "fear",
    "health",
    "valence",
    "trauma_load",
    "trust_damage",
    "resilience",
)


def _safe_mean(values: Iterable[float], default: float = 0.0) -> float:
    values = list(values)
    if not values:
        return default
    return mean(values)


def averages(state: Dict[str, Any], agent_ids: Optional[set[str]] = None) -> Dict[str, float]:
    agents = state["agents"]
    if agent_ids is not None:
        agents = [a for a in agents if a.get("id") in agent_ids]

    return {
        field: round(_safe_mean(float(a.get(field, 0.0)) for a in agents), 4)
        for field in COGNITION_FIELDS
    }


def delta(a: Dict[str, float], b: Dict[str, float]) -> Dict[str, float]:
    return {key: round(b[key] - a[key], 4) for key in a}


def count_impacted_agents(state: Dict[str, Any], label: str, agent_ids: Optional[set[str]] = None) -> int:
    count = 0
    for agent in state["agents"]:
        if agent_ids is not None and agent.get("id") not in agent_ids:
            continue
        if any(m.get("event") == label for m in agent.get("memory", [])):
            count += 1
    return count


def average_memory_multiplier(state: Dict[str, Any], label: str, agent_ids: Optional[set[str]] = None) -> float:
    values = []

    for agent in state["agents"]:
        if agent_ids is not None and agent.get("id") not in agent_ids:
            continue
        for memory in agent.get("memory", []):
            if memory.get("event") == label:
                values.append(float(memory.get("memory_multiplier", 1.0)))

    if not values:
        return 1.0

    return round(mean(values), 4)


def average_memory_field(
    state: Dict[str, Any],
    label: str,
    field: str,
    default: float = 0.0,
    agent_ids: Optional[set[str]] = None,
) -> float:
    values = []

    for agent in state["agents"]:
        if agent_ids is not None and agent.get("id") not in agent_ids:
            continue
        for memory in agent.get("memory", []):
            if memory.get("event") == label:
                values.append(float(memory.get(field, default)))

    if not values:
        return round(default, 4)

    return round(mean(values), 4)


def classify_recovery(
    before_avg: Dict[str, float],
    after_repeated_avg: Dict[str, float],
    after_avg: Dict[str, float],
    field: str,
) -> str:
    event_change = after_repeated_avg[field] - before_avg[field]
    total_change = after_avg[field] - before_avg[field]

    if abs(event_change) < 0.0001:
        return "not_applicable"

    if field == "trust":
        if total_change < -0.0001:
            return "scar_persisted"
        return "fully_recovered_or_improved"

    if event_change > 0.0:
        if total_change > 0.0001:
            return "scar_persisted"
        return "fully_recovered_or_improved"

    if event_change < 0.0:
        if total_change < -0.0001:
            return "negative_shift_persisted"
        return "fully_recovered_or_improved"

    return "not_applicable"


def classify_total_delta(total_delta: Dict[str, float]) -> Dict[str, str]:
    return {
        "total_stress": "rose" if total_delta["stress"] > 0 else "fell_or_stable",
        "total_trust": "fell" if total_delta["trust"] < 0 else "rose_or_stable",
        "total_fear": "rose" if total_delta["fear"] > 0 else "fell_or_stable",
        "trauma_persistence": "persisted" if total_delta["trauma_load"] > 0 else "not_detected",
        "trust_damage_persistence": "persisted" if total_delta["trust_damage"] > 0 else "not_detected",
    }


def assign_agent_groups(kernel: HRMKernel, experiment: Dict[str, Any]) -> Dict[str, List[str]]:
    """Apply optional controlled cohorts before the experiment starts.

    Supported experiment fields:
      resilience_groups: [
        {"name": "low_resilience", "resilience": 0.15, "fraction": 0.333},
        ...
      ]

    Groups are deterministic. Agents are assigned by stable list order so repeated
    runs remain comparable. This is Cognition v0.4's test harness layer; it does
    not change the core cognition kernel.
    """
    group_specs = experiment.get("resilience_groups", [])
    agents = kernel.state.agents
    groups: Dict[str, List[str]] = {}

    if not group_specs:
        return groups

    # Interleaved assignment prevents geography, faction order, or initialization
    # order from becoming a hidden confound. With three groups, agents 0,3,6...
    # go to group 1; 1,4,7... to group 2; 2,5,8... to group 3.
    # This keeps each cohort spread across the same deterministic world.
    for index, spec in enumerate(group_specs):
        name = str(spec["name"])
        resilience = max(0.0, min(1.0, float(spec["resilience"])))
        selected = agents[index::len(group_specs)]

        for agent in selected:
            agent.resilience = resilience

        groups[name] = [agent.id for agent in selected]

    if bool(experiment.get("controlled_resilience_triplets", False)):
        normalize_resilience_triplets(kernel, len(group_specs))

    return groups


def normalize_resilience_triplets(kernel: HRMKernel, group_count: int) -> None:
    """Normalize non-resilience starting conditions across each cohort set.

    This is only used by controlled v0.4 experiments. It removes hidden
    confounds from position and baseline variance so the experiment isolates
    whether resilience alone changes trauma formation and recovery.
    """
    agents = kernel.state.agents

    for start in range(0, len(agents), group_count):
        cohort = agents[start:start + group_count]
        if len(cohort) < group_count:
            continue

        x = _safe_mean(a.x for a in cohort)
        y = _safe_mean(a.y for a in cohort)
        health = _safe_mean(a.health for a in cohort)
        baseline_stress = _safe_mean(a.baseline_stress for a in cohort)
        baseline_trust = _safe_mean(a.baseline_trust for a in cohort)
        baseline_fear = _safe_mean(a.baseline_fear for a in cohort)
        baseline_valence = _safe_mean(a.baseline_valence for a in cohort)

        for agent in cohort:
            agent.x = x
            agent.y = y
            agent.health = health
            agent.baseline_stress = baseline_stress
            agent.baseline_trust = baseline_trust
            agent.baseline_fear = baseline_fear
            agent.baseline_valence = baseline_valence
            agent.stress = baseline_stress
            agent.trust = baseline_trust
            agent.fear = baseline_fear
            agent.valence = baseline_valence
            agent.trauma_load = 0.0
            agent.trust_damage = 0.0
            agent.memory.clear()


def group_snapshot(state: Dict[str, Any], groups: Dict[str, List[str]]) -> Dict[str, Dict[str, Any]]:
    output: Dict[str, Dict[str, Any]] = {}

    for name, ids in groups.items():
        id_set = set(ids)
        output[name] = {
            "population": len(ids),
            "averages": averages(state, id_set),
        }

    return output


def group_delta(
    before: Dict[str, Dict[str, Any]],
    after: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, float]]:
    output: Dict[str, Dict[str, float]] = {}
    for name in before:
        output[name] = delta(before[name]["averages"], after[name]["averages"])
    return output


def group_interpretation(total_group_delta: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
    if not total_group_delta:
        return {}

    by_trauma = sorted(
        total_group_delta.items(),
        key=lambda item: item[1].get("trauma_load", 0.0),
        reverse=True,
    )
    by_stress = sorted(
        total_group_delta.items(),
        key=lambda item: item[1].get("stress", 0.0),
        reverse=True,
    )
    by_fear = sorted(
        total_group_delta.items(),
        key=lambda item: item[1].get("fear", 0.0),
        reverse=True,
    )
    by_trust_damage = sorted(
        total_group_delta.items(),
        key=lambda item: item[1].get("trust_damage", 0.0),
        reverse=True,
    )

    return {
        "most_traumatized_group": by_trauma[0][0],
        "least_traumatized_group": by_trauma[-1][0],
        "highest_stress_scar_group": by_stress[0][0],
        "lowest_stress_scar_group": by_stress[-1][0],
        "highest_fear_scar_group": by_fear[0][0],
        "lowest_fear_scar_group": by_fear[-1][0],
        "highest_trust_damage_group": by_trust_damage[0][0],
        "lowest_trust_damage_group": by_trust_damage[-1][0],
        "resilience_divergence_detected": (
            by_trauma[0][0] != by_trauma[-1][0]
            and by_stress[0][0] != by_stress[-1][0]
        ),
    }


def agent_life_history_report(state: Dict[str, Any], limit: int = 10) -> Dict[str, Any]:
    agents = state["agents"]

    def core(agent: Dict[str, Any]) -> Dict[str, Any]:
        negative_memories = [m for m in agent.get("memory", []) if m.get("negative")]
        return {
            "id": agent["id"],
            "stress": round(float(agent.get("stress", 0.0)), 4),
            "trust": round(float(agent.get("trust", 0.0)), 4),
            "fear": round(float(agent.get("fear", 0.0)), 4),
            "valence": round(float(agent.get("valence", 0.0)), 4),
            "trauma_load": round(float(agent.get("trauma_load", 0.0)), 4),
            "trust_damage": round(float(agent.get("trust_damage", 0.0)), 4),
            "resilience": round(float(agent.get("resilience", 0.0)), 4),
            "negative_memory_count": len(negative_memories),
            "last_negative_events": [m.get("event") for m in negative_memories[-5:]],
        }

    return {
        "most_traumatized_agents": [
            core(a)
            for a in sorted(agents, key=lambda x: x.get("trauma_load", 0.0), reverse=True)[:limit]
        ],
        "most_trust_damaged_agents": [
            core(a)
            for a in sorted(agents, key=lambda x: x.get("trust_damage", 0.0), reverse=True)[:limit]
        ],
        "least_scarred_agents": [
            core(a)
            for a in sorted(
                agents,
                key=lambda x: (x.get("trauma_load", 0.0), x.get("trust_damage", 0.0)),
            )[:limit]
        ],
    }


def run_experiment(path: Path) -> Dict[str, Any]:
    experiment = json.loads(path.read_text(encoding="utf-8"))

    kernel = HRMKernel()
    groups = assign_agent_groups(kernel, experiment)

    event = experiment["event"]
    label = event["label"]
    repeat = max(1, int(experiment.get("repeat", 1)))
    gap_ticks = max(0, int(experiment.get("gap_ticks", 0)))
    final_ticks = max(0, int(experiment.get("ticks", 30)))

    before = kernel.export_state()
    before_avg = averages(before)
    before_groups = group_snapshot(before, groups)

    event_steps = []
    previous_avg = before_avg
    previous_groups = before_groups

    for i in range(repeat):
        kernel.inject_event(event)

        immediate_state = kernel.export_state()
        immediate_avg = averages(immediate_state)
        immediate_groups = group_snapshot(immediate_state, groups)

        step = {
            "event_number": i + 1,
            "tick": immediate_state["tick"],
            "averages": immediate_avg,
            "delta_from_previous": delta(previous_avg, immediate_avg),
            "impacted_agents": count_impacted_agents(immediate_state, label),
            "average_memory_multiplier": average_memory_multiplier(immediate_state, label),
            "average_trauma_sensitivity": average_memory_field(immediate_state, label, "trauma_sensitivity", 1.0),
            "average_trauma_gain": average_memory_field(immediate_state, label, "trauma_gain", 0.0),
            "average_trust_damage_gain": average_memory_field(immediate_state, label, "trust_damage_gain", 0.0),
        }

        if groups:
            step["groups"] = immediate_groups
            step["group_delta_from_previous"] = group_delta(previous_groups, immediate_groups)

        event_steps.append(step)

        previous_avg = immediate_avg
        previous_groups = immediate_groups

        if i < repeat - 1 and gap_ticks > 0:
            kernel.tick(gap_ticks)
            gap_state = kernel.export_state()
            previous_avg = averages(gap_state)
            previous_groups = group_snapshot(gap_state, groups)

    after_repeated_events = kernel.export_state()
    after_repeated_avg = averages(after_repeated_events)
    after_repeated_groups = group_snapshot(after_repeated_events, groups)

    if final_ticks > 0:
        kernel.tick(final_ticks)

    after = kernel.export_state()
    after_avg = averages(after)
    after_groups = group_snapshot(after, groups)

    event_phase_delta = delta(before_avg, after_repeated_avg)
    recovery_delta = delta(after_repeated_avg, after_avg)
    total_delta = delta(before_avg, after_avg)

    group_event_phase_delta = group_delta(before_groups, after_repeated_groups) if groups else {}
    group_recovery_delta = group_delta(after_repeated_groups, after_groups) if groups else {}
    group_total_delta = group_delta(before_groups, after_groups) if groups else {}

    report = {
        "experiment": experiment["name"],
        "repeat": repeat,
        "gap_ticks": gap_ticks,
        "final_ticks": final_ticks,
        "event": event,
        "population": len(after["agents"]),
        "impacted_agents": count_impacted_agents(after, label),
        "before": before_avg,
        "after_repeated_events": after_repeated_avg,
        "after": after_avg,
        "event_steps": event_steps,
        "delta": {
            "event_phase": event_phase_delta,
            "post_event_recovery": recovery_delta,
            "total": total_delta,
        },
        "interpretation": {
            "event_phase_stress": "rose" if event_phase_delta["stress"] > 0 else "fell_or_stable",
            "event_phase_trust": "fell" if event_phase_delta["trust"] < 0 else "rose_or_stable",
            "event_phase_fear": "rose" if event_phase_delta["fear"] > 0 else "fell_or_stable",
            "event_phase_trauma": "rose" if event_phase_delta["trauma_load"] > 0 else "fell_or_stable",
            "event_phase_trust_damage": "rose" if event_phase_delta["trust_damage"] > 0 else "fell_or_stable",
            "recovery_stress": "recovered" if recovery_delta["stress"] < 0 else "increased_or_stable",
            "recovery_fear": "recovered" if recovery_delta["fear"] < 0 else "increased_or_stable",
            **classify_total_delta(total_delta),
            "stress_scar": classify_recovery(before_avg, after_repeated_avg, after_avg, "stress"),
            "fear_scar": classify_recovery(before_avg, after_repeated_avg, after_avg, "fear"),
            "trust_scar": classify_recovery(before_avg, after_repeated_avg, after_avg, "trust"),
        },
        "agent_life_history_report": agent_life_history_report(after),
    }

    if groups:
        report["groups"] = {
            "assignments": groups,
            "before": before_groups,
            "after_repeated_events": after_repeated_groups,
            "after": after_groups,
            "delta": {
                "event_phase": group_event_phase_delta,
                "post_event_recovery": group_recovery_delta,
                "total": group_total_delta,
            },
            "interpretation": group_interpretation(group_total_delta),
        }

    REPORTS.mkdir(exist_ok=True)
    out = REPORTS / f"{experiment['name']}_report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\nCOGNITION LAB REPORT")
    print("====================")
    print(f"Experiment: {report['experiment']}")
    print(f"Population: {report['population']}")
    print(f"Repeat: {repeat}")
    print(f"Gap ticks: {gap_ticks}")
    print(f"Final recovery ticks: {final_ticks}")
    print(f"Impacted agents: {report['impacted_agents']}")
    print()
    print("Before:               ", report["before"])
    print("After repeated events:", report["after_repeated_events"])
    print("After final recovery: ", report["after"])
    print()

    print("Event steps:")
    for step in event_steps:
        print(
            f"  Event {step['event_number']}: "
            f"delta={step['delta_from_previous']} "
            f"memory_multiplier={step['average_memory_multiplier']} "
            f"trauma_sensitivity={step['average_trauma_sensitivity']} "
            f"trauma_gain={step['average_trauma_gain']} "
            f"trust_damage_gain={step['average_trust_damage_gain']} "
            f"impacted={step['impacted_agents']}"
        )

    print()
    print("Event phase delta:     ", report["delta"]["event_phase"])
    print("Recovery delta:        ", report["delta"]["post_event_recovery"])
    print("Total delta:           ", report["delta"]["total"])
    print()
    print("Interpretation:", report["interpretation"])

    if groups:
        print()
        print("Group total deltas:")
        for group_name, group_values in report["groups"]["delta"]["total"].items():
            print(f"  {group_name}: {group_values}")
        print("Group interpretation:", report["groups"]["interpretation"])

    print()
    print("Agent life-history samples:")
    for agent in report["agent_life_history_report"]["most_traumatized_agents"][:3]:
        print(
            f"  {agent['id']}: trauma={agent['trauma_load']} "
            f"trust_damage={agent['trust_damage']} resilience={agent['resilience']} "
            f"negative_memories={agent['negative_memory_count']}"
        )

    print()
    print(f"Wrote report: {out}")
    return report


def main() -> None:
    files = sorted(EXPERIMENTS.glob("*.json"))
    if not files:
        raise SystemExit("No experiments found.")

    for path in files:
        run_experiment(path)


if __name__ == "__main__":
    main()
