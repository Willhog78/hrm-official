"""The budget audit must observe without causing, and its energy ledger must close."""

from __future__ import annotations

import hrm_genesis.human.biology as biology
import hrm_genesis.human.interactions as cap
from qualification.genesis.budget_audit import Audit, run_audit
from qualification.genesis.tier_observer import unobserved_digest


def test_audit_uninstalls_cleanly():
    names = [(biology, n) for n in ("forage_at_cell", "_provision_dependent", "_apply_physiology",
                                    "_catabolize_lean_tissue", "_apply_predator_threat", "_age_profile")]
    names += [(cap, n) for n in ("run_interactions", "choose", "learn_from_tick")]
    originals = [getattr(m, n) for m, n in names]
    audit = Audit()
    audit.install()
    assert all(getattr(m, n) is not o for (m, n), o in zip(names, originals))
    audit.uninstall()
    assert [getattr(m, n) for m, n in names] == originals


def test_audit_is_non_causal_and_the_energy_budget_closes():
    seed, arm, days = "agentus-demography-a", "v1@reference-v2", 10
    result = run_audit(seed, arm, days)
    assert "crash" not in result, result.get("traceback")
    assert result["ledger_valid"]
    assert result["rows"], "no adult agent-days recorded"
    assert result["max_energy_residual_kcal"] < 1e-6
    assert result["ledger_digest"] == unobserved_digest(seed, arm, days)
