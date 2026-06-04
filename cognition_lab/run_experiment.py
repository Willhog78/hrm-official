from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import mean

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


def averages(state):
    agents = state["agents"]
    return {
        field: round(mean(a.get(field, 0.0) for a in agents), 4)
        for field in COGNITION_FIELDS
    }


def delta(a, b):
    return {key: round(b[key] - a[key], 4) for key in a}


def count_impacted_agents(state, label):
    return sum(
        1
        for agent in state["agents"]
        if any(m.get("event") == label for m in agent.get("memory", []))
    )


def average_memory_multiplier(state, label):
    values = []

    for agent in state["agents"]:
        for memory in agent.get("memory", []):
            if memory.get("event") == label:
                values.append(float(memory.get("memory_multiplier", 1.0)))

    if not values:
        return 1.0

    return round(mean(values), 4)


def average_memory_field(state, label, field, default=0.0):
    values = []

    for agent in state["agents"]:
        for memory in agent.get("memory", []):
            if memory.get("event") == label:
                values.append(float(memory.get(field, default)))

    if not values:
        return round(default, 4)

    return round(mean(values), 4)


def classify_recovery(before_avg, after_repeated_avg, after_avg, field):
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


def run_experiment(path: Path):
    experiment = json.loads(path.read_text(encoding="utf-8"))

    kernel = HRMKernel()

    event = experiment["event"]
    label = event["label"]
    repeat = max(1, int(experiment.get("repeat", 1)))
    gap_ticks = max(0, int(experiment.get("gap_ticks", 0)))
    final_ticks = max(0, int(experiment.get("ticks", 30)))

    before = kernel.export_state()
    before_avg = averages(before)

    event_steps = []

    previous_avg = before_avg

    for i in range(repeat):
        kernel.inject_event(event)

        immediate_state = kernel.export_state()
        immediate_avg = averages(immediate_state)

        event_steps.append(
            {
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
        )

        previous_avg = immediate_avg

        if i < repeat - 1 and gap_ticks > 0:
            kernel.tick(gap_ticks)
            gap_state = kernel.export_state()
            previous_avg = averages(gap_state)

    after_repeated_events = kernel.export_state()
    after_repeated_avg = averages(after_repeated_events)

    if final_ticks > 0:
        kernel.tick(final_ticks)

    after = kernel.export_state()
    after_avg = averages(after)

    event_phase_delta = delta(before_avg, after_repeated_avg)
    recovery_delta = delta(after_repeated_avg, after_avg)
    total_delta = delta(before_avg, after_avg)

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
            "total_stress": "rose" if total_delta["stress"] > 0 else "fell_or_stable",
            "total_trust": "fell" if total_delta["trust"] < 0 else "rose_or_stable",
            "total_fear": "rose" if total_delta["fear"] > 0 else "fell_or_stable",
            "trauma_persistence": "persisted" if total_delta["trauma_load"] > 0 else "not_detected",
            "trust_damage_persistence": "persisted" if total_delta["trust_damage"] > 0 else "not_detected",
            "stress_scar": classify_recovery(before_avg, after_repeated_avg, after_avg, "stress"),
            "fear_scar": classify_recovery(before_avg, after_repeated_avg, after_avg, "fear"),
            "trust_scar": classify_recovery(before_avg, after_repeated_avg, after_avg, "trust"),
        },
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
    print()
    print(f"Wrote report: {out}")


def main():
    files = sorted(EXPERIMENTS.glob("*.json"))
    if not files:
        raise SystemExit("No experiments found.")

    for path in files:
        run_experiment(path)


if __name__ == "__main__":
    main()
