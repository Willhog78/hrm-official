from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import mean

# Ensure HRM_WORKING root is importable even when this script is run directly.
ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from hrm_core.kernel import HRMKernel


EXPERIMENTS = ROOT / "experiments"
REPORTS = ROOT / "reports"


def averages(state):
    agents = state["agents"]
    return {
        "stress": round(mean(a["stress"] for a in agents), 4),
        "trust": round(mean(a["trust"] for a in agents), 4),
        "fear": round(mean(a["fear"] for a in agents), 4),
        "health": round(mean(a["health"] for a in agents), 4),
        "valence": round(mean(a["valence"] for a in agents), 4),
    }


def delta(a, b):
    return {
        key: round(b[key] - a[key], 4)
        for key in a
    }


def run_experiment(path: Path):
    experiment = json.loads(path.read_text(encoding="utf-8"))

    kernel = HRMKernel()

    before = kernel.export_state()
    before_avg = averages(before)

    kernel.inject_event(experiment["event"])

    immediate = kernel.export_state()
    immediate_avg = averages(immediate)

    kernel.tick(experiment.get("ticks", 30))

    after = kernel.export_state()
    after_avg = averages(after)

    immediate_delta = delta(before_avg, immediate_avg)
    recovery_delta = delta(immediate_avg, after_avg)
    total_delta = delta(before_avg, after_avg)

    impacted_agents = [
        a for a in after["agents"]
        if any(m.get("event") == experiment["event"]["label"] for m in a.get("memory", []))
    ]

    report = {
        "experiment": experiment["name"],
        "ticks": experiment.get("ticks", 30),
        "event": experiment["event"],
        "population": len(after["agents"]),
        "impacted_agents": len(impacted_agents),
        "before": before_avg,
        "immediate": immediate_avg,
        "after": after_avg,
        "delta": {
            "event_impact": immediate_delta,
            "post_event_recovery": recovery_delta,
            "total": total_delta,
        },
        "interpretation": {
            "event_stress": "rose" if immediate_delta["stress"] > 0 else "fell_or_stable",
            "event_trust": "fell" if immediate_delta["trust"] < 0 else "rose_or_stable",
            "event_fear": "rose" if immediate_delta["fear"] > 0 else "fell_or_stable",
            "recovery_stress": "recovered" if recovery_delta["stress"] < 0 else "increased_or_stable",
            "recovery_fear": "recovered" if recovery_delta["fear"] < 0 else "increased_or_stable",
            "total_stress": "rose" if total_delta["stress"] > 0 else "fell_or_stable",
            "total_trust": "fell" if total_delta["trust"] < 0 else "rose_or_stable",
            "total_fear": "rose" if total_delta["fear"] > 0 else "fell_or_stable",
        },
    }

    REPORTS.mkdir(exist_ok=True)
    out = REPORTS / f"{experiment['name']}_report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\nCOGNITION LAB REPORT")
    print("====================")
    print(f"Experiment: {report['experiment']}")
    print(f"Population: {report['population']}")
    print(f"Impacted agents: {report['impacted_agents']}")
    print()
    print("Before:   ", report["before"])
    print("Immediate:", report["immediate"])
    print("After:    ", report["after"])
    print()
    print("Event impact delta:    ", report["delta"]["event_impact"])
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