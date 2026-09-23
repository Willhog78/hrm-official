from __future__ import annotations

from fractions import Fraction
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile

import pytest

from hrm_coordination import (
    StateAuthority,
    TransactionFabric,
    ReplayLedger,
    ResourceRef,
    Mutation,
    TransactionProposal,
    ProvenanceContribution,
    TemporalOrchestrator,
    ScheduleSpec,
    write_checkpoint,
)
from hrm_coordination.model import digest_obj


def make_system(initials: dict[str, dict], seed: str = "stage1-seed"):
    authorities = [StateAuthority(aid, values) for aid, values in sorted(initials.items())]
    cfg = digest_obj({"seed": seed, "initials": initials, "stage": 1})
    ledger = ReplayLedger(cfg)
    for aid, values in sorted(initials.items()):
        ledger.register_genesis(aid, values)
    fabric = TransactionFabric(seed, [a.port() for a in authorities], ledger)
    return authorities, ledger, fabric


def proposal(pid: str, epoch: int, mutations: list[tuple[str, str, int, object]], txid: str | None = None,
             provenance: ProvenanceContribution | None = None, claims=None):
    return TransactionProposal(
        proposal_id=pid,
        transaction_id=txid or f"tx-{pid}",
        proposer_id=f"worker-{pid}",
        logical_epoch=epoch,
        mutations=tuple(Mutation(ResourceRef(a, r), v, value) for a, r, v, value in mutations),
        provenance=provenance or ProvenanceContribution(source_authority=f"worker-{pid}"),
        fallible_claims=claims or {},
    )


def snapshot_values(fabric: TransactionFabric):
    out = {}
    for aid in fabric.authority_ids:
        out[aid] = {rid: (sv.value, sv.version) for rid, sv in fabric.projection(aid).items()}
    return out


def test_s1_1_deterministic_enumeration_and_worker_order():
    def run(reverse: bool):
        _, ledger, fabric = make_system({"A": {"x": 0}, "B": {"y": 0}})
        ps = [
            proposal("pA", 0, [("A", "x", 0, 1)]),
            proposal("pB", 0, [("B", "y", 0, 2)]),
        ]
        if reverse:
            ps.reverse()
        batch = fabric.resolve(0, ps)
        return snapshot_values(fabric), fabric.causal_state_digest(), ledger.digest(), batch.arbitration_digest
    assert run(False) == run(True)


def test_s1_2_explicit_multirate_scheduling():
    _, _, fabric = make_system({"A": {"n": 0}, "B": {"n": 0}, "C": {"n": 0}})
    orch = TemporalOrchestrator(fabric, Fraction(1, 10))

    def cb(aid):
        def inner(ctx, fab):
            sv = fab.projection(aid, ["n"])["n"]
            return [proposal(f"{aid}-{ctx.epoch}", ctx.epoch, [(aid, "n", sv.version, sv.value + 1)])]
        return inner

    orch.register(ScheduleSpec("clock-A", 1, 0, 1), cb("A"))
    orch.register(ScheduleSpec("clock-B", 2, 0, 2), cb("B"))
    orch.register(ScheduleSpec("clock-C", 3, 1, 1), cb("C"))
    orch.run(7)
    assert fabric.projection("A", ["n"])["n"].value == 7
    assert fabric.projection("B", ["n"])["n"].value == 4
    assert fabric.projection("C", ["n"])["n"].value == 2


def test_s1_3_stale_read_rejected():
    _, _, fabric = make_system({"A": {"x": 0}})
    assert fabric.resolve(0, [proposal("first", 0, [("A", "x", 0, 1)])]).results[0].status == "COMMITTED"
    result = fabric.resolve(1, [proposal("stale", 1, [("A", "x", 0, 99)])]).results[0]
    assert result.status == "REJECTED"
    assert "StaleReadError" in (result.reason or "")
    assert fabric.projection("A", ["x"])["x"].value == 1


def test_s1_4_conflict_arbitration_order_invariant():
    def run(ps):
        _, ledger, fabric = make_system({"A": {"x": 0}}, seed="conflict")
        batch = fabric.resolve(0, ps)
        return [(r.proposal_id, r.status) for r in batch.results], snapshot_values(fabric), ledger.digest()
    p1 = proposal("alpha", 0, [("A", "x", 0, 1)])
    p2 = proposal("beta", 0, [("A", "x", 0, 2)])
    assert run([p1, p2]) == run([p2, p1])
    assert sum(status == "COMMITTED" for _, status in run([p1, p2])[0]) == 1


def test_s1_5_local_atomic_transaction_failure_leaves_no_partial_state():
    authorities, _, fabric = make_system({"A": {"x": 0, "y": 0}})
    txid = "tx-local-fail"
    authorities[0].inject_stage_failure_once(txid)
    p = proposal("local-fail", 0, [("A", "x", 0, 1), ("A", "y", 0, 1)], txid=txid)
    result = fabric.resolve(0, [p]).results[0]
    assert result.status == "REJECTED"
    assert snapshot_values(fabric) == {"A": {"x": (0, 0), "y": (0, 0)}}


def test_s1_5_cross_partition_mid_commit_failure_has_zero_partial_observable_commit():
    authorities, _, fabric = make_system({"A": {"x": 10}, "B": {"y": 20}})
    txid = "tx-cross-fail"
    # A stages successfully first; B fails inside the commit path. A must remain invisible.
    by_id = {a.authority_id: a for a in authorities}
    by_id["B"].inject_stage_failure_once(txid)
    p = proposal("cross-fail", 0, [("A", "x", 0, 11), ("B", "y", 0, 21)], txid=txid)
    result = fabric.resolve(0, [p]).results[0]
    assert result.status == "REJECTED"
    assert snapshot_values(fabric) == {"A": {"x": (10, 0)}, "B": {"y": (20, 0)}}


def test_cross_partition_success_publishes_both_participants_together():
    _, ledger, fabric = make_system({"A": {"x": 10}, "B": {"y": 20}})
    p = proposal("cross-ok", 0, [("A", "x", 0, 11), ("B", "y", 0, 21)], txid="tx-cross-ok")
    result = fabric.resolve(0, [p]).results[0]
    assert result.status == "COMMITTED"
    assert snapshot_values(fabric) == {"A": {"x": (11, 1)}, "B": {"y": (21, 1)}}
    replay = ledger.replay_state()
    assert replay["A"]["x"] == {"value": 11, "version": 1}
    assert replay["B"]["y"] == {"value": 21, "version": 1}


def test_s1_6_coordination_port_does_not_expose_private_authority_state():
    auth = StateAuthority("A", {"tempting_secret": 7})
    port = auth.port()
    legal_names = {name for name in dir(port) if not name.startswith("__")}
    assert "state" not in legal_names
    assert "_StateAuthority__state" not in legal_names
    assert "tempting_secret" not in legal_names
    assert port.snapshot(["tempting_secret"])["tempting_secret"].value == 7


def test_s1_11_port_closures_do_not_expose_the_whole_authority_object():
    """Post-Round-2 correction / regression test for a real finding.

    An earlier port implementation closed over the entire StateAuthority
    instance in every method. Standard, unprivileged Python reflection
    (``bound_method.__func__.__closure__``) could walk that single cell back
    to the live object and, from there, reach every private attribute in one
    hop -- including transaction bookkeeping and test-only failure-injection
    state a legal caller has no declared way to reach.

    This test locks in the containment fix: no port method's closure chain
    resolves back to a StateAuthority instance. It intentionally does not
    claim the boundary is hostile-process-safe -- CPython has no true
    in-process capability boundary (``gc.get_referrers`` can still walk to
    any live object), and each mutating closure still legitimately holds a
    live reference to the specific state/versions dicts it operates on. That
    residual is documented, not hidden; full isolation requires a process
    boundary, which is out of Stage-1 scope.
    """
    auth = StateAuthority("A", {"tempting_secret": 7})
    port = auth.port()

    def resolves_to_authority(func, seen=None) -> bool:
        seen = seen or set()
        if id(func) in seen:
            return False
        seen.add(id(func))
        if not hasattr(func, "__code__"):
            return False
        for name, cell in zip(func.__code__.co_freevars, func.__closure__ or ()):
            value = cell.cell_contents
            if isinstance(value, StateAuthority):
                return True
            if hasattr(value, "__code__") and resolves_to_authority(value, seen):
                return True
        return False

    for method_name in ("snapshot", "prepare", "stage_commit", "abort", "materialize_published", "checkpoint"):
        bound = getattr(port, method_name)
        assert not resolves_to_authority(bound.__func__), (
            f"port.{method_name} closure chain still reaches the full StateAuthority object"
        )


def test_s1_7_replay_completeness_and_chain_verification():
    _, ledger, fabric = make_system({"A": {"x": 0}, "B": {"y": 5}})
    fabric.resolve(0, [proposal("p0", 0, [("A", "x", 0, 1)])])
    fabric.resolve(1, [proposal("p1", 1, [("A", "x", 1, 2), ("B", "y", 0, 6)])])
    assert ledger.verify_chain()
    replay = ledger.replay_state()
    assert replay["A"]["x"] == {"value": 2, "version": 2}
    assert replay["B"]["y"] == {"value": 6, "version": 1}
    assert digest_obj(replay) == digest_obj({
        aid: {rid: {"value": sv.value, "version": sv.version} for rid, sv in fabric.projection(aid).items()}
        for aid in fabric.authority_ids
    })


def test_s1_8_feedback_lag_prevents_same_epoch_read_after_write_priority():
    _, _, fabric = make_system({"A": {"x": 0}})
    orch = TemporalOrchestrator(fabric)

    def cb(name, value):
        def inner(ctx, fab):
            sv = fab.projection("A", ["x"])["x"]
            assert sv.value == 0  # both callbacks observe the same S_n
            return [proposal(name, ctx.epoch, [("A", "x", sv.version, value)])]
        return inner

    orch.register(ScheduleSpec("w1", 1, feedback_lag_ticks=1), cb("p1", 1))
    orch.register(ScheduleSpec("w2", 1, feedback_lag_ticks=1), cb("p2", 2))
    batch = orch.step(worker_order=["w2", "w1"])
    assert sum(r.status == "COMMITTED" for r in batch.results) == 1


def test_s1_9_independent_conflict_domains_all_commit():
    initials = {f"A{i}": {"x": 0} for i in range(64)}
    _, _, fabric = make_system(initials, seed="partitioned")
    ps = [proposal(f"p{i}", 0, [(f"A{i}", "x", 0, i + 1)]) for i in range(64)]
    batch = fabric.resolve(0, list(reversed(ps)))
    assert all(r.status == "COMMITTED" for r in batch.results)
    assert all(fabric.projection(f"A{i}", ["x"])["x"].value == i + 1 for i in range(64))
    assert not hasattr(fabric, "_global_conflict_lock")


def test_s1_10_pathological_contention_is_deterministic():
    def run(reverse):
        _, _, fabric = make_system({"A": {"x": 0}}, seed="contention")
        ps = [proposal(f"p{i:04d}", 0, [("A", "x", 0, i)]) for i in range(1000)]
        if reverse:
            ps.reverse()
        batch = fabric.resolve(0, ps)
        return [(r.proposal_id, r.status) for r in batch.results], snapshot_values(fabric), batch.arbitration_digest
    a = run(False)
    b = run(True)
    assert a == b
    assert sum(status == "COMMITTED" for _, status in a[0]) == 1


def test_s1_11_unknown_authority_cannot_be_mutated():
    _, _, fabric = make_system({"A": {"x": 0}})
    p = proposal("bad-owner", 0, [("NOT_A_KERNEL", "x", 0, 1)])
    result = fabric.resolve(0, [p]).results[0]
    assert result.status == "REJECTED"
    assert "unknown authority" in (result.reason or "")
    assert fabric.projection("A", ["x"])["x"].value == 0


def test_s1_13_authoritative_provenance_is_not_in_fallible_projection():
    _, ledger, fabric = make_system({"A": {"x": 0}})
    p = proposal(
        "claiming", 0, [("A", "x", 0, 1)],
        provenance=ProvenanceContribution(source_authority="AUTHORITY-A", operation="SET_SYNTHETIC"),
        claims={"heard_from": "someone", "asserted_value": 999},
    )
    assert fabric.resolve(0, [p]).results[0].status == "COMMITTED"
    projected = ledger.fallible_projection()[0]
    assert projected["claims"]["asserted_value"] == 999
    forbidden = {"causal_parents", "source_authority", "proposal_digest", "arbitration_digest", "config_fingerprint", "record_digest"}
    assert forbidden.isdisjoint(projected)
    assert ledger.records[0].source_authority == "AUTHORITY-A"


def test_malformed_authoritative_provenance_rejected_before_state_change():
    _, ledger, fabric = make_system({"A": {"x": 0}})
    p = proposal(
        "bad-prov", 0, [("A", "x", 0, 1)],
        provenance=ProvenanceContribution(causal_parents=("nonexistent-parent",), source_authority="A"),
    )
    result = fabric.resolve(0, [p]).results[0]
    assert result.status == "REJECTED"
    assert snapshot_values(fabric) == {"A": {"x": (0, 0)}}
    # The rejection is evidence (so its transaction_id is burned), with no effect.
    assert [(r.transaction_id, r.status, r.committed) for r in ledger.records] == [("tx-bad-prov", "REJECTED", ())]
    assert ledger.verify_chain()


def _continue_callback(ctx, fab):
    sv = fab.projection("A", ["x"])["x"]
    return [proposal(f"p{ctx.epoch}", ctx.epoch, [("A", "x", sv.version, sv.value + 1)])]


def test_s1_14_checkpoint_restart_fresh_process_determinism(tmp_path: Path):
    # Uninterrupted reference run.
    _, ledger_full, fabric_full = make_system({"A": {"x": 0}}, seed="restart")
    orch_full = TemporalOrchestrator(fabric_full)
    orch_full.register(ScheduleSpec("worker", 1), _continue_callback)
    orch_full.run(6)
    expected = {"state": snapshot_values(fabric_full), "ledger": ledger_full.digest(), "causal": fabric_full.causal_state_digest()}

    # Interrupted run to checkpoint after 3 epochs.
    _, ledger_part, fabric_part = make_system({"A": {"x": 0}}, seed="restart")
    orch_part = TemporalOrchestrator(fabric_part)
    orch_part.register(ScheduleSpec("worker", 1), _continue_callback)
    orch_part.run(3)
    cp = tmp_path / "checkpoint.json"
    write_checkpoint(cp, orch_part.checkpoint(), fabric_part, ledger_part)

    code = r'''
import json, sys
from fractions import Fraction
from hrm_coordination import load_checkpoint, TemporalOrchestrator, ScheduleSpec, ResourceRef, Mutation, TransactionProposal, ProvenanceContribution

def cb(ctx, fab):
    sv=fab.projection("A", ["x"])["x"]
    p=TransactionProposal(
        proposal_id=f"p{ctx.epoch}", transaction_id=f"tx-p{ctx.epoch}", proposer_id=f"worker-p{ctx.epoch}", logical_epoch=ctx.epoch,
        mutations=(Mutation(ResourceRef("A","x"),sv.version,sv.value+1),),
        provenance=ProvenanceContribution(source_authority=f"worker-p{ctx.epoch}"), fallible_claims={})
    return [p]
state, fabric, ledger, auths = load_checkpoint(sys.argv[1])
orch=TemporalOrchestrator(fabric, Fraction(state["contract_dt_numerator"], state["contract_dt_denominator"]), start_epoch=state["epoch"])
orch.register(ScheduleSpec("worker",1), cb)
orch.run(3)
snap={aid:{rid:(sv.value,sv.version) for rid,sv in fabric.projection(aid).items()} for aid in fabric.authority_ids}
print(json.dumps({"state":snap,"ledger":ledger.digest(),"causal":fabric.causal_state_digest()},sort_keys=True))
'''
    env = os.environ.copy()
    root = Path(__file__).resolve().parents[1]
    env["PYTHONPATH"] = str(root / "src")
    out = subprocess.check_output([sys.executable, "-c", code, str(cp)], text=True, env=env)
    resumed = json.loads(out)
    # tuples serialize as JSON arrays, normalize through JSON for exact comparison.
    expected_json = json.loads(json.dumps(expected, sort_keys=True))
    assert resumed == expected_json

def test_s1_9_conflict_domains_are_explicit_and_execution_permutation_invariant():
    initials = {f"A{i}": {"x": 0} for i in range(12)}

    def run(reverse_components: bool):
        _, ledger, fabric = make_system(initials, seed="domain-plan")
        ps = [proposal(f"p{i:02d}", 0, [(f"A{i}", "x", 0, i + 1)]) for i in range(12)]
        plans = fabric.plan_conflict_domains(ps)
        assert len(plans) == 12
        order = list(reversed(range(len(plans)))) if reverse_components else None
        batch = fabric.resolve(0, ps, component_execution_order=order)
        return snapshot_values(fabric), ledger.digest(), batch.arbitration_digest, tuple((p.domain_id, p.proposal_ids) for p in plans)

    assert run(False) == run(True)

def test_empty_epoch_still_advances_replay_evidence_root():
    _, ledger, fabric = make_system({"A": {"x": 0}}, seed="empty-epoch")
    before = ledger.digest()
    batch = fabric.resolve(0, [])
    assert batch.results == ()
    after = ledger.digest()
    assert after != before
    assert len(ledger.epoch_blocks) == 1
    assert ledger.epoch_blocks[0].record_digests == ()


def test_replay_export_tamper_is_detected():
    _, ledger, fabric = make_system({"A": {"x": 0}}, seed="tamper")
    fabric.resolve(0, [proposal("p", 0, [("A", "x", 0, 1)])])
    exported = ledger.export()
    exported["records"][0]["committed"][0]["new_value"] = 999
    from hrm_coordination.ledger import ReplayLedger, ProvenanceError
    with pytest.raises(ProvenanceError, match="invalid imported ledger chain"):
        ReplayLedger.from_export(exported)


def test_round2_dar_s1_004_transaction_ids_are_run_global():
    from hrm_coordination import ProvenanceError

    _, ledger, fabric = make_system({"A": {"x": 0}}, seed="dar-s1-004")
    fabric.resolve(0, [proposal("first", 0, [("A", "x", 0, 1)], txid="DUP-TX")])
    before = snapshot_values(fabric)
    before_records = ledger.records
    before_blocks = ledger.epoch_blocks

    with pytest.raises(ProvenanceError, match="historical transaction_id reuse"):
        fabric.resolve(1, [proposal("second", 1, [("A", "x", 1, 2)], txid="DUP-TX")])

    assert snapshot_values(fabric) == before
    assert ledger.records == before_records
    assert ledger.epoch_blocks == before_blocks
    assert ledger.verify_chain()


def test_round2_dar_s1_005_epoch_admission_is_historical_not_caller_trusted():
    from hrm_coordination import ProvenanceError

    _, ledger, fabric = make_system({"A": {"x": 0}}, seed="dar-s1-005-repeat")
    fabric.resolve(0, [proposal("e0", 0, [("A", "x", 0, 1)])])
    before = snapshot_values(fabric)

    with pytest.raises(ProvenanceError, match="not admissible; expected 1"):
        fabric.resolve(0, [proposal("repeat-e0", 0, [("A", "x", 1, 2)])])
    assert snapshot_values(fabric) == before
    assert [block.epoch for block in ledger.epoch_blocks] == [0]

    _, ledger2, fabric2 = make_system({"A": {"x": 0}}, seed="dar-s1-005-future")
    with pytest.raises(ProvenanceError, match="not admissible; expected 0"):
        fabric2.resolve(5, [proposal("future-e5", 5, [("A", "x", 0, 1)])])
    assert snapshot_values(fabric2) == {"A": {"x": (0, 0)}}
    assert ledger2.records == ()
    assert ledger2.epoch_blocks == ()


def test_sequential_epoch_contract_allows_explicit_empty_epochs():
    from hrm_coordination import ProvenanceError

    _, ledger, fabric = make_system({"A": {"x": 0}}, seed="sequential-empty")
    fabric.resolve(0, [])
    fabric.resolve(1, [])
    assert [block.epoch for block in ledger.epoch_blocks] == [0, 1]
    assert ledger.expected_epoch == 2

    with pytest.raises(ProvenanceError, match="not admissible; expected 2"):
        fabric.resolve(3, [])
    assert [block.epoch for block in ledger.epoch_blocks] == [0, 1]


def test_round2_dar_s1_006_ledger_admission_failure_precedes_materialization(monkeypatch):
    from hrm_coordination import ProvenanceError

    _, ledger, fabric = make_system({"A": {"x": 0}, "B": {"y": 0}}, seed="dar-s1-006")

    def fail_prepare_batch(*args, **kwargs):
        raise ProvenanceError("injected ledger admission failure")

    monkeypatch.setattr(ledger, "prepare_batch", fail_prepare_batch)
    p = proposal("span", 0, [("A", "x", 0, 1), ("B", "y", 0, 1)], txid="tx-ledger-fail")

    with pytest.raises(ProvenanceError, match="injected ledger admission failure"):
        fabric.resolve(0, [p])

    assert snapshot_values(fabric) == {"A": {"x": (0, 0)}, "B": {"y": (0, 0)}}
    assert ledger.records == ()
    assert ledger.epoch_blocks == ()
    assert ledger.verify_chain()
    assert fabric.checkpoint()["published"] == {}


def test_provenance_rejected_transaction_id_cannot_be_reused():
    from hrm_coordination import ProvenanceError

    _, ledger, fabric = make_system({"A": {"x": 0}}, seed="prov-reject-reuse")
    bad = proposal(
        "bad", 0, [("A", "x", 0, 1)], txid="TX-1",
        provenance=ProvenanceContribution(causal_parents=("no-such-parent",), source_authority="A"),
    )
    assert fabric.resolve(0, [bad]).results[0].status == "REJECTED"

    with pytest.raises(ProvenanceError, match="historical transaction_id reuse"):
        fabric.resolve(1, [proposal("retry", 1, [("A", "x", 0, 1)], txid="TX-1")])
    assert snapshot_values(fabric) == {"A": {"x": (0, 0)}}

    # The burned ID survives export/import.
    imported = ReplayLedger.from_export(ledger.export())
    with pytest.raises(ProvenanceError, match="historical transaction_id reuse"):
        imported.validate_transaction_ids([proposal("retry", 1, [("A", "x", 0, 1)], txid="TX-1")])


def test_checkpoint_with_state_diverging_from_ledger_is_rejected(tmp_path: Path):
    from hrm_coordination import ProvenanceError, load_checkpoint

    _, ledger, fabric = make_system({"A": {"x": 0}}, seed="checkpoint-tamper")
    fabric.resolve(0, [proposal("p", 0, [("A", "x", 0, 5)])])
    cp = tmp_path / "checkpoint.json"
    write_checkpoint(cp, {"epoch": 1}, fabric, ledger)

    _, clean_fabric, _, _ = load_checkpoint(cp)
    assert snapshot_values(clean_fabric) == {"A": {"x": (5, 1)}}

    for field, tamper in (("state", 999999), ("versions", 7)):
        raw = json.loads(cp.read_text(encoding="utf-8"))
        raw["fabric"]["authorities"][0][field]["x"] = tamper
        bad = tmp_path / f"tampered-{field}.json"
        bad.write_text(json.dumps(raw), encoding="utf-8")
        with pytest.raises(ProvenanceError, match="does not match ledger replay"):
            load_checkpoint(bad)


def test_imported_record_with_foreign_config_fingerprint_is_rejected():
    from hrm_coordination import ProvenanceError

    _, ledger, fabric = make_system({"A": {"x": 0}}, seed="foreign-config")
    fabric.resolve(0, [proposal("p", 0, [("A", "x", 0, 1)])])
    exported = ledger.export()

    # Rewrite the record under another config and recompute every digest so only
    # the fingerprint mismatch remains.
    for rec in exported["records"]:
        rec["config_fingerprint"] = "FOREIGN"
        rec["record_digest"] = digest_obj({k: v for k, v in rec.items() if k != "record_digest"})
    previous = digest_obj({"genesis": exported["genesis"], "config": exported["config_fingerprint"]})
    for block in exported["epoch_blocks"]:
        digests = sorted(r["record_digest"] for r in exported["records"] if r["epoch"] == block["epoch"])
        block["record_digests"] = digests
        block["previous_epoch_digest"] = previous
        block["epoch_digest"] = digest_obj({"epoch": block["epoch"], "previous_epoch_digest": previous, "record_digests": digests})
        previous = block["epoch_digest"]

    with pytest.raises(ProvenanceError, match="invalid imported ledger chain"):
        ReplayLedger.from_export(exported)


@pytest.mark.parametrize("max_parallel_domains", [1, 4])
def test_unexpected_domain_failure_aborts_all_staged_winners(monkeypatch, max_parallel_domains):
    authorities = [StateAuthority("A", {"x": 0}), StateAuthority("B", {"y": 0})]
    ledger = ReplayLedger(digest_obj({"seed": "domain-failure"}))
    ledger.register_genesis("A", {"x": 0})
    ledger.register_genesis("B", {"y": 0})
    fabric = TransactionFabric("domain-failure", [a.port() for a in authorities], ledger,
                               max_parallel_domains=max_parallel_domains)

    original = TransactionFabric._execute_transaction

    def failing(self, epoch, p):
        if p.proposal_id == "p2":
            raise RuntimeError("unexpected kernel failure")
        return original(self, epoch, p)

    monkeypatch.setattr(TransactionFabric, "_execute_transaction", failing)
    with pytest.raises(RuntimeError, match="unexpected kernel failure"):
        fabric.resolve(0, [proposal("p1", 0, [("A", "x", 0, 1)]), proposal("p2", 0, [("B", "y", 0, 1)])])
    monkeypatch.undo()

    assert snapshot_values(fabric) == {"A": {"x": (0, 0)}, "B": {"y": (0, 0)}}
    assert ledger.records == ()
    checkpoint = fabric.checkpoint()  # raised "clean transaction boundary" before the fix
    assert checkpoint["published"] == {}
    batch = fabric.resolve(0, [proposal("p3", 0, [("A", "x", 0, 7)])])
    assert batch.results[0].status == "COMMITTED"
    fabric.checkpoint()


def test_causal_state_digest_is_atomic_across_authorities():
    import threading

    _, _, fabric = make_system({"A": {"x": 0}, "B": {"y": 0}}, seed="digest-atomic")
    pre = fabric.causal_state_digest()
    cross = proposal("cross", 0, [("A", "x", 0, 1), ("B", "y", 0, 1)])

    # Commit a cross-authority transaction at the one point where a per-authority
    # read loop would have released A's lock but not yet taken B's.
    original = fabric._keys_for_projection
    fired = threading.Event()

    def interleave(authority_id, resource_ids):
        if authority_id == "B" and not fired.is_set():
            fired.set()
            writer = threading.Thread(target=fabric.resolve, args=(0, [cross]))
            writer.start()
            writer.join(timeout=5)
        return original(authority_id, resource_ids)

    fabric._keys_for_projection = interleave
    observed = fabric.causal_state_digest()
    del fabric._keys_for_projection
    if not fired.is_set():
        fabric.resolve(0, [cross])
    post = fabric.causal_state_digest()

    assert snapshot_values(fabric) == {"A": {"x": (1, 1)}, "B": {"y": (1, 1)}}
    assert observed in (pre, post)


@pytest.mark.parametrize("bad_mutations, reason", [
    ([], "at least one mutation"),
    ([("B", "y", 0, 1), ("B", "y", 0, 2)], "duplicate mutation resource"),
    ([("NOT_A_KERNEL", "x", 0, 1)], "unknown authority"),
    ([("B", "missing", 0, 1)], "unknown resource keys"),
])
def test_malformed_proposal_rejects_only_itself(bad_mutations, reason):
    from hrm_coordination import ProvenanceError

    _, ledger, fabric = make_system({"A": {"x": 0}, "B": {"y": 0}}, seed="malformed-isolation")
    good = proposal("good", 0, [("A", "x", 0, 1)])
    bad = proposal("bad", 0, bad_mutations, txid="TX-BAD")
    results = {r.proposal_id: r for r in fabric.resolve(0, [bad, good]).results}

    assert results["good"].status == "COMMITTED"
    assert results["bad"].status == "REJECTED"
    assert reason in (results["bad"].reason or "")
    assert snapshot_values(fabric) == {"A": {"x": (1, 1)}, "B": {"y": (0, 0)}}
    assert {(r.transaction_id, r.status) for r in ledger.records} == {("tx-good", "COMMITTED"), ("TX-BAD", "REJECTED")}
    assert ledger.verify_chain()
    assert ledger.replay_state()["A"]["x"] == {"value": 1, "version": 1}
    with pytest.raises(ProvenanceError, match="historical transaction_id reuse"):
        fabric.resolve(1, [proposal("retry", 1, [("B", "y", 0, 1)], txid="TX-BAD")])


def test_missing_identity_still_fails_whole_batch():
    _, ledger, fabric = make_system({"A": {"x": 0}, "B": {"y": 0}}, seed="identity-batch")
    good = proposal("good", 0, [("A", "x", 0, 1)])
    anonymous = TransactionProposal(
        proposal_id="anon",
        transaction_id="",
        proposer_id="worker-anon",
        logical_epoch=0,
        mutations=(Mutation(ResourceRef("B", "y"), 0, 1),),
    )
    with pytest.raises(ValueError, match="ids are required"):
        fabric.resolve(0, [good, anonymous])
    assert snapshot_values(fabric) == {"A": {"x": (0, 0)}, "B": {"y": (0, 0)}}
    assert ledger.records == ()
    assert ledger.epoch_blocks == ()


def test_plan_conflict_domains_still_raises_on_malformed_proposal():
    _, _, fabric = make_system({"A": {"x": 0}}, seed="plan-malformed")
    with pytest.raises(ValueError, match="unknown authority"):
        fabric.plan_conflict_domains([proposal("bad", 0, [("NOT_A_KERNEL", "x", 0, 1)])])
