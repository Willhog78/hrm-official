from __future__ import annotations

import argparse
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from hrm_coordination import (
    AuthorityPort,
    Mutation,
    ProvenanceContribution,
    ProvenanceError,
    ReplayLedger,
    ResourceRef,
    SeedBank,
    StateAuthority,
    TransactionFabric,
    TransactionProposal,
    TemporalOrchestrator,
    ScheduleSpec,
    load_checkpoint,
    write_checkpoint,
)
from hrm_coordination.model import digest_obj


HERE = Path(__file__).resolve()
ROOT = HERE.parents[1]


def make_system(initials: dict[str, dict], seed: str = "stage1-seed", max_parallel_domains: int = 32):
    authorities = [StateAuthority(aid, values) for aid, values in sorted(initials.items())]
    cfg = digest_obj({"seed": seed, "initials": initials, "stage": 1, "hmt": "v0.2"})
    ledger = ReplayLedger(cfg)
    for aid, values in sorted(initials.items()):
        ledger.register_genesis(aid, values)
    fabric = TransactionFabric(
        seed,
        [a.port() for a in authorities],
        ledger,
        max_parallel_domains=max_parallel_domains,
    )
    return authorities, ledger, fabric


def proposal(
    pid: str,
    epoch: int,
    mutations: list[tuple[str, str, int, object]],
    *,
    txid: str | None = None,
    provenance: ProvenanceContribution | None = None,
    proposer_id: str | None = None,
):
    return TransactionProposal(
        proposal_id=pid,
        transaction_id=txid or f"tx-{pid}",
        proposer_id=proposer_id or f"worker-{pid}",
        logical_epoch=epoch,
        mutations=tuple(Mutation(ResourceRef(a, r), v, value) for a, r, v, value in mutations),
        provenance=provenance or ProvenanceContribution(source_authority=proposer_id or f"worker-{pid}"),
        fallible_claims={},
    )


def snapshot_values(fabric: TransactionFabric) -> dict[str, dict[str, tuple[object, int]]]:
    return {
        aid: {rid: (sv.value, sv.version) for rid, sv in fabric.projection(aid).items()}
        for aid in fabric.authority_ids
    }


def deterministic_scenario() -> dict[str, Any]:
    _, ledger, fabric = make_system({"A": {"x": 0}, "B": {"y": 10}}, seed="hmt-replay", max_parallel_domains=8)
    orch = TemporalOrchestrator(fabric)

    def cb_a(ctx, fab):
        sv = fab.projection("A", ["x"])["x"]
        return [proposal(f"A-{ctx.epoch}", ctx.epoch, [("A", "x", sv.version, sv.value + 1)])]

    def cb_b(ctx, fab):
        sv = fab.projection("B", ["y"])["y"]
        return [proposal(f"B-{ctx.epoch}", ctx.epoch, [("B", "y", sv.version, sv.value + 2)])]

    orch.register(ScheduleSpec("sched-A", 1), cb_a)
    orch.register(ScheduleSpec("sched-B", 1), cb_b)
    batches = orch.run(6, order_fn=lambda due, epoch: reversed(due) if epoch % 2 else due)
    return {
        "state_hash": fabric.causal_state_digest(),
        "ledger_export_hash": digest_obj(ledger.export()),
        "replay_root": ledger.digest(),
        "arbitration_digests": [b.arbitration_digest for b in batches],
        "terminal_state": snapshot_values(fabric),
    }


def card_01() -> dict[str, Any]:
    a = deterministic_scenario()
    b = deterministic_scenario()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    out = subprocess.check_output([sys.executable, str(HERE), "--child-deterministic"], text=True, env=env)
    c = json.loads(out)
    # JSON is the clean-process interchange format. Canonicalize the in-process
    # structures before exact comparison so Python tuple/list representation does
    # not create a false replay divergence. The locked hash/digest metrics remain
    # unchanged.
    a_norm = json.loads(json.dumps(a, sort_keys=True))
    b_norm = json.loads(json.dumps(b, sort_keys=True))
    passed = a_norm == b_norm == c
    return {
        "pass": passed,
        "state_hash": a["state_hash"],
        "ledger_export_hash": a["ledger_export_hash"],
        "replay_root": a["replay_root"],
        "divergence_epoch": None if passed else "comparison_mismatch",
        "comparisons_exact": passed,
    }


def card_02() -> dict[str, Any]:
    _, ledger, fabric = make_system({"A": {"x": 0}, "B": {"noise": 0}}, seed="hmt-causal")
    previous_tx: str | None = None
    for epoch in range(6):
        x = fabric.projection("A", ["x"])["x"]
        n = fabric.projection("B", ["noise"])["noise"]
        prov = ProvenanceContribution(
            causal_parents=(() if previous_tx is None else (previous_tx,)),
            source_authority="chain",
            operation="CHAIN",
        )
        chain = proposal(f"chain-{epoch}", epoch, [("A", "x", x.version, x.value + 1)], txid=f"chain-tx-{epoch}", provenance=prov)
        noise = proposal(f"noise-{epoch}", epoch, [("B", "noise", n.version, n.value + 1)])
        batch = fabric.resolve(epoch, [noise, chain] if epoch % 2 else [chain, noise])
        assert next(r for r in batch.results if r.proposal_id == chain.proposal_id).status == "COMMITTED"
        previous_tx = chain.transaction_id

    tx_epoch = {r.transaction_id: r.epoch for r in ledger.records}
    inversions = 0
    for rec in ledger.records:
        for parent in rec.causal_parents:
            if parent in tx_epoch and tx_epoch[parent] >= rec.epoch:
                inversions += 1

    # Same-epoch/future dependency attack: neither referenced transaction is prior evidence.
    _, ledger2, fabric2 = make_system({"A": {"x": 0}, "B": {"y": 0}}, seed="hmt-causal-attack")
    p_future = proposal(
        "effect",
        0,
        [("A", "x", 0, 1)],
        provenance=ProvenanceContribution(causal_parents=("tx-cause",), source_authority="effect"),
    )
    p_cause = proposal("cause", 0, [("B", "y", 0, 1)], txid="tx-cause")
    attack = fabric2.resolve(0, [p_future, p_cause])
    illegal_acceptances = sum(r.proposal_id == "effect" and r.status == "COMMITTED" for r in attack.results)
    passed = inversions == 0 and illegal_acceptances == 0 and ledger.verify_chain() and ledger2.verify_chain()
    return {
        "pass": passed,
        "causal_inversions": inversions,
        "illegal_parent_acceptances": illegal_acceptances,
        "accepted_chain_records": sum(r.operation == "CHAIN" for r in ledger.records),
    }


def _conflict_run(seed: str, reverse: bool = False, mutant: bool = False) -> dict[str, Any]:
    _, ledger, fabric = make_system({"A": {"token": "free"}}, seed=seed)
    p_a = proposal("A-claim", 0, [("A", "token", 0, "A")], txid="tx-A")
    p_b = proposal("B-claim", 0, [("A", "token", 0, "B")], txid="tx-B")
    ps = [p_b, p_a] if reverse else [p_a, p_b]
    if mutant:
        def first_enumerated_wins(items):
            items = list(items)
            if not items:
                return [], {}
            winner = items[0]
            return [winner], {p.proposal_id: "CONFLICT_LOST" for p in items[1:]}
        fabric._select_nonconflicting = first_enumerated_wins  # disposable test mutant
    batch = fabric.resolve(0, ps)
    winner = next(r.proposal_id for r in batch.results if r.status == "COMMITTED")
    return {
        "winner": winner,
        "arbitration_digest": batch.arbitration_digest,
        "committed": sum(r.status == "COMMITTED" for r in batch.results),
        "ledger_root": ledger.digest(),
    }


def card_03() -> dict[str, Any]:
    fwd = _conflict_run("hmt-conflict", False)
    rev = _conflict_run("hmt-conflict", True)
    passed = fwd == rev and fwd["committed"] == 1
    return {"pass": passed, "forward": fwd, "reverse": rev}


def card_04() -> dict[str, Any]:
    _, _, fabric = make_system({"A": {"token": "free"}}, seed="hmt-double-spend")
    ps = [proposal(f"claim-{i:02d}", 0, [("A", "token", 0, f"owner-{i:02d}")]) for i in range(32)]
    batch = fabric.resolve(0, ps)
    committed = [r for r in batch.results if r.status == "COMMITTED"]
    sv = fabric.projection("A", ["token"])["token"]
    duplicate_ownership_count = max(0, len(committed) - 1)
    passed = len(committed) == 1 and sv.version == 1 and sv.value != "free" and duplicate_ownership_count == 0
    return {
        "pass": passed,
        "committed_claims": len(committed),
        "duplicate_ownership_count": duplicate_ownership_count,
        "final_owner": sv.value,
        "final_version": sv.version,
    }


class PausePort(AuthorityPort):
    def __init__(self, delegate: AuthorityPort, transaction_id: str, entered: threading.Event, release: threading.Event):
        self.delegate = delegate
        self.transaction_id = transaction_id
        self.entered = entered
        self.release = release

    @property
    def authority_id(self):
        return self.delegate.authority_id

    def snapshot(self, resource_ids=None):
        return self.delegate.snapshot(resource_ids)

    def prepare(self, transaction_id, mutations):
        return self.delegate.prepare(transaction_id, mutations)

    def stage_commit(self, transaction_id):
        return self.delegate.stage_commit(transaction_id)

    def abort(self, transaction_id):
        return self.delegate.abort(transaction_id)

    def materialize_published(self, transaction_id):
        if transaction_id == self.transaction_id:
            self.entered.set()
            if not self.release.wait(timeout=5):
                raise RuntimeError("test pause timed out")
        return self.delegate.materialize_published(transaction_id)

    def checkpoint(self):
        return self.delegate.checkpoint()


def card_05() -> dict[str, Any]:
    matrix: list[dict[str, Any]] = []
    for phase in ("prepare", "stage"):
        for aid in ("A", "B", "C"):
            authorities, ledger, fabric = make_system({"A": {"x": 0}, "B": {"y": 0}, "C": {"z": 0}}, seed=f"rollback-{phase}-{aid}")
            by_id = {a.authority_id: a for a in authorities}
            txid = f"tx-{phase}-{aid}"
            if phase == "prepare":
                by_id[aid].inject_prepare_failure_once(txid)
            else:
                by_id[aid].inject_stage_failure_once(txid)
            p = proposal("span", 0, [("A", "x", 0, 1), ("B", "y", 0, 1), ("C", "z", 0, 1)], txid=txid)
            result = fabric.resolve(0, [p]).results[0]
            snap = snapshot_values(fabric)
            residual = sum(value != 0 or version != 0 for vals in snap.values() for value, version in vals.values())
            published = txid in fabric.checkpoint()["published"]
            ok = result.status == "REJECTED" and residual == 0 and not published and ledger.verify_chain()
            matrix.append({"phase": phase, "authority": aid, "residual": residual, "published": published, "pass": ok})

    # Successful multi-authority publication: pause before B materializes. A has
    # already materialized, but a legal read of A must still block on A's resource
    # publication lock until B/C are materialized too.
    _, ledger, fabric = make_system({"A": {"x": 0}, "B": {"y": 0}, "C": {"z": 0}}, seed="atomic-observer")
    txid = "tx-observer"
    entered = threading.Event()
    release = threading.Event()
    fabric._ports["B"] = PausePort(fabric._ports["B"], txid, entered, release)
    p = proposal("observe", 0, [("A", "x", 0, 1), ("B", "y", 0, 1), ("C", "z", 0, 1)], txid=txid)
    writer_result: dict[str, Any] = {}

    def writer():
        writer_result["batch"] = fabric.resolve(0, [p])

    wt = threading.Thread(target=writer, daemon=True)
    wt.start()
    reached = entered.wait(timeout=5)
    reader_done = threading.Event()
    reader_value: dict[str, Any] = {}

    def reader():
        reader_value["a"] = fabric.projection("A", ["x"])["x"].value
        reader_done.set()

    rt = threading.Thread(target=reader, daemon=True)
    rt.start()
    time.sleep(0.03)
    blocked_during_partial_window = reached and not reader_done.is_set()
    release.set()
    wt.join(timeout=5)
    rt.join(timeout=5)
    post = snapshot_values(fabric)
    observer_ok = (
        reached
        and blocked_during_partial_window
        and reader_done.is_set()
        and reader_value.get("a") == 1
        and post == {"A": {"x": (1, 1)}, "B": {"y": (1, 1)}, "C": {"z": (1, 1)}}
        and ledger.verify_chain()
    )
    # Round-2 DAR-S1-006: ledger admission itself is a fallible pre-publication
    # phase. Inject failure there and require zero causal or evidence drift.
    _, ledger_fail, fabric_fail = make_system({"A": {"x": 0}, "B": {"y": 0}}, seed="rollback-ledger-admission")
    original_prepare_batch = ledger_fail.prepare_batch

    def fail_prepare_batch(*args, **kwargs):
        raise ProvenanceError("injected ledger admission failure")

    ledger_fail.prepare_batch = fail_prepare_batch
    ledger_failure_raised = False
    try:
        fabric_fail.resolve(0, [proposal("ledger-fail", 0, [("A", "x", 0, 1), ("B", "y", 0, 1)], txid="tx-ledger-fail")])
    except ProvenanceError:
        ledger_failure_raised = True
    finally:
        ledger_fail.prepare_batch = original_prepare_batch

    ledger_admission_ok = (
        ledger_failure_raised
        and snapshot_values(fabric_fail) == {"A": {"x": (0, 0)}, "B": {"y": (0, 0)}}
        and len(ledger_fail.records) == 0
        and len(ledger_fail.epoch_blocks) == 0
        and ledger_fail.verify_chain()
        and fabric_fail.checkpoint()["published"] == {}
    )

    passed = all(r["pass"] for r in matrix) and observer_ok and ledger_admission_ok
    return {
        "pass": passed,
        "failure_matrix": matrix,
        "failure_positions_passed": sum(r["pass"] for r in matrix),
        "failure_positions_total": len(matrix),
        "observer_blocked_during_partial_window": blocked_during_partial_window,
        "observer_value": reader_value.get("a"),
        "observer_case_pass": observer_ok,
        "ledger_admission_failure_pass": ledger_admission_ok,
    }


def card_06() -> dict[str, Any]:
    initials = {"A": {"x": 0, "u": 0}, "B": {"y": 0, "v": 0}, "C": {"z": 0, "w": 0}}
    _, ledger, fabric = make_system(initials, seed="hmt-ledger")
    schedule = [
        [("A", "x"), ("B", "y")],
        [("C", "z"), ("A", "u")],
        [("B", "v"), ("C", "w")],
        [("A", "x"), ("C", "z")],
    ]
    for epoch, refs in enumerate(schedule):
        ps = []
        for i, (aid, rid) in enumerate(refs):
            sv = fabric.projection(aid, [rid])[rid]
            ps.append(proposal(f"p-{epoch}-{i}", epoch, [(aid, rid, sv.version, sv.value + epoch + i + 1)]))
        fabric.resolve(epoch, list(reversed(ps)) if epoch % 2 else ps)

    state = snapshot_values(fabric)
    traced = 0
    total_changed = 0
    orphans = 0
    for aid, values in state.items():
        for rid, (_, version) in values.items():
            if version == 0:
                continue
            total_changed += 1
            changes = [
                m
                for rec in ledger.records
                if rec.status == "COMMITTED"
                for m in rec.committed
                if m.ref.authority_id == aid and m.ref.resource_id == rid
            ]
            continuity = [m.before_version for m in changes] == list(range(version)) and [m.after_version for m in changes] == list(range(1, version + 1))
            if len(changes) == version and continuity:
                traced += 1
            else:
                orphans += 1
    replay = ledger.replay_state()
    causal_for_digest = {
        aid: {rid: {"value": value, "version": version} for rid, (value, version) in vals.items()}
        for aid, vals in state.items()
    }
    replay_equal = digest_obj(replay) == digest_obj(causal_for_digest)
    rate = 1.0 if total_changed == 0 else traced / total_changed
    # A rejected ledger-admission attempt must create neither an orphan state
    # change nor orphan evidence.
    _, ledger_fail, fabric_fail = make_system({"A": {"x": 0}, "B": {"y": 0}}, seed="hmt-ledger-admission")
    original_prepare_batch = ledger_fail.prepare_batch

    def fail_prepare_batch(*args, **kwargs):
        raise ProvenanceError("injected ledger admission failure")

    ledger_fail.prepare_batch = fail_prepare_batch
    ledger_failure_raised = False
    try:
        fabric_fail.resolve(0, [proposal("ledger-fail", 0, [("A", "x", 0, 1), ("B", "y", 0, 1)])])
    except ProvenanceError:
        ledger_failure_raised = True
    finally:
        ledger_fail.prepare_batch = original_prepare_batch
    ledger_failure_trace_ok = (
        ledger_failure_raised
        and snapshot_values(fabric_fail) == {"A": {"x": (0, 0)}, "B": {"y": (0, 0)}}
        and len(ledger_fail.records) == 0
        and len(ledger_fail.epoch_blocks) == 0
    )

    passed = rate == 1.0 and orphans == 0 and replay_equal and ledger.verify_chain() and ledger_failure_trace_ok
    return {
        "pass": passed,
        "trace_completion_rate": rate,
        "orphan_terminal_changes": orphans,
        "changed_terminal_variables": total_changed,
        "replay_equal": replay_equal,
        "ledger_admission_failure_trace_pass": ledger_failure_trace_ok,
    }


def _run_load(seed: str, count: int, profile: str) -> dict[str, Any]:
    if profile == "hotspot":
        initials = {"A": {"x": 0}}
        _, ledger, fabric = make_system(initials, seed=seed, max_parallel_domains=8)
        ps = [proposal(f"p-{i:05d}", 0, [("A", "x", 0, i + 1)]) for i in range(count)]
    elif profile == "diffuse":
        authority_count = min(64, max(1, count))
        initials: dict[str, dict[str, int]] = {f"A{a:02d}": {} for a in range(authority_count)}
        refs = []
        for i in range(count):
            aid = f"A{i % authority_count:02d}"
            rid = f"r{i:05d}"
            initials[aid][rid] = 0
            refs.append((aid, rid))
        _, ledger, fabric = make_system(initials, seed=seed, max_parallel_domains=32)
        ps = [proposal(f"p-{i:05d}", 0, [(aid, rid, 0, 1)]) for i, (aid, rid) in enumerate(refs)]
    else:
        raise ValueError(profile)

    domains = len(fabric.plan_conflict_domains(ps))
    start = time.perf_counter()
    batch = fabric.resolve(0, ps)
    elapsed = time.perf_counter() - start
    committed = sum(r.status == "COMMITTED" for r in batch.results)
    rejected = len(batch.results) - committed
    accounting_exact = len(batch.results) == count
    if profile == "hotspot":
        invariant_violations = 0 if committed == 1 and fabric.projection("A", ["x"])["x"].version == 1 else 1
    else:
        invariant_violations = 0 if committed == count and all(
            sv.version == 1 for aid in fabric.authority_ids for sv in fabric.projection(aid).values()
        ) else 1
    return {
        "seed": seed,
        "count": count,
        "profile": profile,
        "elapsed_s": elapsed,
        "throughput_per_s": count / elapsed if elapsed > 0 else float("inf"),
        "conflict_domains": domains,
        "committed": committed,
        "rejected": rejected,
        "accounting_exact": accounting_exact,
        "invariant_violations": invariant_violations,
        "ledger_valid": ledger.verify_chain(),
    }


def _mean_ci95(values: list[float]) -> dict[str, float]:
    mean = statistics.fmean(values)
    if len(values) < 2:
        return {"mean": mean, "low": mean, "high": mean}
    se = statistics.stdev(values) / math.sqrt(len(values))
    return {"mean": mean, "low": mean - 1.96 * se, "high": mean + 1.96 * se}


def card_07() -> dict[str, Any]:
    seeds = [f"load-{i:02d}" for i in range(20)]
    runs = []
    for count in (100, 1000, 5000):
        for profile in ("hotspot", "diffuse"):
            for seed in seeds:
                runs.append(_run_load(seed, count, profile))
    bad = [r for r in runs if r["invariant_violations"] != 0 or not r["accounting_exact"] or not r["ledger_valid"] or r["elapsed_s"] >= 30.0 or r["throughput_per_s"] <= 0]
    summaries = {}
    for count in (100, 1000, 5000):
        for profile in ("hotspot", "diffuse"):
            subset = [r for r in runs if r["count"] == count and r["profile"] == profile]
            summaries[f"{profile}-{count}"] = {
                "elapsed_ci95": _mean_ci95([r["elapsed_s"] for r in subset]),
                "throughput_ci95": _mean_ci95([r["throughput_per_s"] for r in subset]),
                "max_elapsed_s": max(r["elapsed_s"] for r in subset),
                "domain_count": subset[0]["conflict_domains"],
            }
    return {
        "pass": not bad,
        "run_count": len(runs),
        "failed_runs": bad,
        "summaries": summaries,
        "max_elapsed_s": max(r["elapsed_s"] for r in runs),
        "total_invariant_violations": sum(r["invariant_violations"] for r in runs),
    }


def card_08() -> dict[str, Any]:
    initials = {f"A{i}": {"x": 0} for i in range(8)}
    _, ledger, fabric = make_system(initials, seed="hmt-bottleneck", max_parallel_domains=8)
    ps = [proposal(f"p{i}", 0, [(f"A{i}", "x", 0, i + 1)]) for i in range(8)]
    original = fabric._execute_transaction
    counter_lock = threading.Lock()
    active = 0
    max_active = 0

    def instrumented(epoch, p):
        nonlocal active, max_active
        with counter_lock:
            active += 1
            max_active = max(max_active, active)
        try:
            time.sleep(0.020)
            return original(epoch, p)
        finally:
            with counter_lock:
                active -= 1

    fabric._execute_transaction = instrumented
    start = time.perf_counter()
    batch = fabric.resolve(0, ps)
    elapsed = time.perf_counter() - start
    serial_floor = 0.160
    speedup = serial_floor / elapsed
    correctness = all(r.status == "COMMITTED" for r in batch.results) and ledger.verify_chain()
    passed = max_active >= 4 and elapsed <= 0.100 and speedup >= 1.60 and correctness
    return {
        "pass": passed,
        "max_simultaneous_active_domains": max_active,
        "elapsed_s": elapsed,
        "serial_floor_s": serial_floor,
        "serial_floor_speedup": speedup,
        "correctness": correctness,
    }


def _partition_run(max_workers: int, explicit_order: list[int] | None = None) -> dict[str, Any]:
    initials = {f"A{i:02d}": {"x": 0} for i in range(64)}
    _, ledger, fabric = make_system(initials, seed="hmt-partition", max_parallel_domains=max_workers)
    ps = [proposal(f"p{i:02d}", 0, [(f"A{i:02d}", "x", 0, i + 1)]) for i in range(64)]
    if explicit_order is None:
        batch = fabric.resolve(0, ps)
    else:
        batch = fabric.resolve(0, ps, component_execution_order=explicit_order)
    return {
        "state_hash": fabric.causal_state_digest(),
        "ledger_root": ledger.digest(),
        "arbitration_digest": batch.arbitration_digest,
        "result_vector": [(r.proposal_id, r.status) for r in batch.results],
    }


def card_09() -> dict[str, Any]:
    serial = _partition_run(1)
    parallel = _partition_run(8)
    reversed_serial = _partition_run(8, list(reversed(range(64))))
    passed = serial == parallel == reversed_serial
    return {"pass": passed, "serial": serial, "parallel": parallel, "reversed_serial": reversed_serial}


def _raises_value_error(fn) -> bool:
    try:
        fn()
    except ValueError:
        return True
    return False


def card_10() -> dict[str, Any]:
    _, _, f1 = make_system({"A": {"x": 0}}, seed="clock-stale")
    stale_argument = _raises_value_error(lambda: f1.resolve(0, [proposal("stale", -1, [("A", "x", 0, 1)])]))
    _, _, f2 = make_system({"A": {"x": 0}}, seed="clock-future")
    future_argument = _raises_value_error(lambda: f2.resolve(0, [proposal("future", 1, [("A", "x", 0, 1)])]))
    _, _, f3 = make_system({"A": {"x": 0}, "B": {"y": 0}}, seed="clock-dup-pid")
    dup_pid = _raises_value_error(lambda: f3.resolve(0, [
        proposal("dup", 0, [("A", "x", 0, 1)], txid="tx1"),
        proposal("dup", 0, [("B", "y", 0, 1)], txid="tx2"),
    ]))
    _, _, f4 = make_system({"A": {"x": 0}, "B": {"y": 0}}, seed="clock-dup-tx")
    dup_tx_batch = _raises_value_error(lambda: f4.resolve(0, [
        proposal("p1", 0, [("A", "x", 0, 1)], txid="same"),
        proposal("p2", 0, [("B", "y", 0, 1)], txid="same"),
    ]))

    # Round-2 historical attacks: caller and proposal may agree with each other
    # and still be inadmissible relative to persisted prior evidence.
    _, ledger5, f5 = make_system({"A": {"x": 0}}, seed="clock-history")
    f5.resolve(0, [proposal("e0", 0, [("A", "x", 0, 1)], txid="HIST-TX")])
    history_before = snapshot_values(f5)
    repeated_epoch = _raises_value_error(lambda: f5.resolve(0, [proposal("repeat", 0, [("A", "x", 1, 2)], txid="NEW-TX")]))
    historical_tx = _raises_value_error(lambda: f5.resolve(1, [proposal("reuse", 1, [("A", "x", 1, 2)], txid="HIST-TX")]))
    history_zero_mutation = snapshot_values(f5) == history_before and [b.epoch for b in ledger5.epoch_blocks] == [0]

    _, ledger6, f6 = make_system({"A": {"x": 0}}, seed="clock-skipped")
    skipped_future_epoch = _raises_value_error(lambda: f6.resolve(5, [proposal("e5", 5, [("A", "x", 0, 1)])]))
    skipped_zero_mutation = snapshot_values(f6) == {"A": {"x": (0, 0)}} and len(ledger6.epoch_blocks) == 0

    equal_a = _conflict_run("clock-equal", False)
    equal_b = _conflict_run("clock-equal", True)
    equal_deterministic = equal_a == equal_b
    passed = all([
        stale_argument, future_argument, dup_pid, dup_tx_batch, repeated_epoch, historical_tx,
        history_zero_mutation, skipped_future_epoch, skipped_zero_mutation, equal_deterministic,
    ])
    return {
        "pass": passed,
        "stale_argument_rejected": stale_argument,
        "future_argument_rejected": future_argument,
        "duplicate_proposal_id_rejected": dup_pid,
        "duplicate_transaction_id_in_batch_rejected": dup_tx_batch,
        "historical_epoch_reuse_rejected": repeated_epoch,
        "historical_transaction_id_reuse_rejected": historical_tx,
        "historical_attacks_zero_mutation": history_zero_mutation,
        "skipped_future_persisted_epoch_rejected": skipped_future_epoch,
        "skipped_future_zero_mutation": skipped_zero_mutation,
        "equal_epoch_deterministic": equal_deterministic,
    }


class CrashPort(AuthorityPort):
    def __init__(self, delegate: AuthorityPort, crash_point: str):
        self.delegate = delegate
        self.crash_point = crash_point

    @property
    def authority_id(self):
        return self.delegate.authority_id

    def _maybe(self, phase: str):
        if self.crash_point == f"after_{phase}_{self.authority_id}":
            os._exit(79)

    def snapshot(self, resource_ids=None):
        return self.delegate.snapshot(resource_ids)

    def prepare(self, transaction_id, mutations):
        out = self.delegate.prepare(transaction_id, mutations)
        self._maybe("prepare")
        return out

    def stage_commit(self, transaction_id):
        out = self.delegate.stage_commit(transaction_id)
        self._maybe("stage")
        return out

    def abort(self, transaction_id):
        return self.delegate.abort(transaction_id)

    def materialize_published(self, transaction_id):
        out = self.delegate.materialize_published(transaction_id)
        self._maybe("materialize")
        return out

    def checkpoint(self):
        return self.delegate.checkpoint()


def _recover_from_checkpoint(checkpoint: str) -> dict[str, Any]:
    state, fabric, ledger, _ = load_checkpoint(checkpoint)
    start = int(state["epoch"])
    for epoch in (start, start + 1):
        ax = fabric.projection("A", ["x"])["x"]
        by = fabric.projection("B", ["y"])["y"]
        parent = () if epoch == start else (f"tx-e{epoch - 1}",)
        p = proposal(
            f"e{epoch}", epoch,
            [("A", "x", ax.version, ax.value + 1), ("B", "y", by.version, by.value + 1)],
            txid=f"tx-e{epoch}",
            provenance=ProvenanceContribution(causal_parents=parent, source_authority="recover"),
        )
        fabric.resolve(epoch, [p])
    return {
        "state_hash": fabric.causal_state_digest(),
        "ledger_root": ledger.digest(),
        "ledger_export_hash": digest_obj(ledger.export()),
        "record_count": len(ledger.records),
        "transaction_ids": [r.transaction_id for r in ledger.records],
    }


def child_crash(checkpoint: str, crash_point: str) -> None:
    state, fabric, ledger, _ = load_checkpoint(checkpoint)
    fabric._ports["A"] = CrashPort(fabric._ports["A"], crash_point)
    fabric._ports["B"] = CrashPort(fabric._ports["B"], crash_point)
    if crash_point == "after_ledger_append":
        original_commit = ledger.commit_prepared_batch
        def crash_commit(*args, **kwargs):
            out = original_commit(*args, **kwargs)
            os._exit(79)
        ledger.commit_prepared_batch = crash_commit
    epoch = int(state["epoch"])
    p = proposal(
        f"e{epoch}", epoch,
        [("A", "x", 0, 1), ("B", "y", 0, 1)],
        txid=f"tx-e{epoch}",
        provenance=ProvenanceContribution(source_authority="crash"),
    )
    fabric.resolve(epoch, [p])
    if crash_point == "before_checkpoint":
        os._exit(79)
    # A crash child must never survive its declared crash point.
    os._exit(78)


def card_11() -> dict[str, Any]:
    crash_points = [
        "after_prepare_A", "after_prepare_B", "after_stage_A", "after_stage_B",
        "after_materialize_A", "after_materialize_B", "after_ledger_append", "before_checkpoint",
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    cases = []
    with tempfile.TemporaryDirectory() as td:
        cp = Path(td) / "clean-checkpoint.json"
        _, ledger, fabric = make_system({"A": {"x": 0}, "B": {"y": 0}}, seed="hmt-crash")
        orch = TemporalOrchestrator(fabric)
        write_checkpoint(cp, orch.checkpoint(), fabric, ledger)
        reference = _recover_from_checkpoint(str(cp))
        for point in crash_points:
            proc = subprocess.run(
                [sys.executable, str(HERE), "--child-crash", str(cp), point],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            recovered_out = subprocess.check_output(
                [sys.executable, str(HERE), "--child-recover", str(cp)], text=True, env=env
            )
            recovered = json.loads(recovered_out)
            unique = len(recovered["transaction_ids"]) == len(set(recovered["transaction_ids"]))
            ok = proc.returncode == 79 and recovered == reference and recovered["record_count"] == 2 and unique
            cases.append({"point": point, "crash_returncode": proc.returncode, "recovered_equal": recovered == reference, "unique_transactions": unique, "pass": ok})
    passed = all(c["pass"] for c in cases)
    return {
        "pass": passed,
        "cases": cases,
        "lost_events": 0 if passed else None,
        "duplicated_events": 0 if passed else None,
        "reference": reference,
    }


def card_12() -> dict[str, Any]:
    bank = SeedBank("hmt-seed-master")
    target_a = bank.stream("target")
    seq_a = [target_a.getrandbits(64) for _ in range(100)]
    noop = bank.stream("noop")
    _ = [noop.getrandbits(64) for _ in range(10000)]
    target_b = bank.stream("target")
    seq_b = [target_b.getrandbits(64) for _ in range(100)]
    stream_equal = seq_a == seq_b

    def target_with_noise(include_noise: bool):
        initials = {"T": {"x": 0}, "N": {"y": 0}}
        _, _, fabric = make_system(initials, seed="hmt-seed-arb")
        p1 = proposal("target-a", 0, [("T", "x", 0, 1)])
        p2 = proposal("target-b", 0, [("T", "x", 0, 2)])
        ps = [p1, p2]
        if include_noise:
            noise_rng = SeedBank("hmt-seed-master").stream("unrelated-domain")
            ps.append(proposal("noise", 0, [("N", "y", 0, noise_rng.randrange(1, 1000000))]))
        batch = fabric.resolve(0, ps)
        winner = next(r.proposal_id for r in batch.results if r.proposal_id.startswith("target-") and r.status == "COMMITTED")
        ranks = {p.proposal_id: fabric._proposal_rank(p) for p in (p1, p2)}
        return winner, ranks

    no_noise = target_with_noise(False)
    with_noise = target_with_noise(True)
    domain_equal = no_noise == with_noise
    passed = stream_equal and domain_equal
    return {
        "pass": passed,
        "stream_divergence_count": sum(a != b for a, b in zip(seq_a, seq_b)),
        "target_stream_equal": stream_equal,
        "target_domain_equal": domain_equal,
        "target_winner": no_noise[0],
    }


def _wilson95(successes: int, n: int) -> tuple[float, float]:
    z = 1.959963984540054
    p = successes / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / den
    return center - half, center + half


def card_13() -> dict[str, Any]:
    seeds = [f"fairness-{i:04d}" for i in range(1000)]
    wins_a = 0
    subgroup = {"forward": [0, 0], "reverse": [0, 0]}
    committed_exact = True
    for i, seed in enumerate(seeds):
        reverse = bool(i % 2)
        result = _conflict_run(seed, reverse)
        committed_exact &= result["committed"] == 1
        group = "reverse" if reverse else "forward"
        subgroup[group][1] += 1
        if result["winner"] == "A-claim":
            wins_a += 1
            subgroup[group][0] += 1
    rate = wins_a / len(seeds)
    ci = _wilson95(wins_a, len(seeds))
    subgroup_rates = {k: wins / n for k, (wins, n) in subgroup.items()}
    subgroup_ok = all(abs(r - 0.5) <= 0.075 for r in subgroup_rates.values())
    passed = 0.45 <= rate <= 0.55 and subgroup_ok and committed_exact
    return {
        "pass": passed,
        "n": len(seeds),
        "a_wins": wins_a,
        "a_win_rate": rate,
        "wilson95": {"low": ci[0], "high": ci[1]},
        "order_subgroup_rates": subgroup_rates,
        "committed_exact": committed_exact,
    }


def card_14() -> dict[str, Any]:
    seeds = [f"mutant-{i:02d}" for i in range(20)]
    control_passes = 0
    kills = 0
    cases = []
    for seed in seeds:
        control_fwd = _conflict_run(seed, False, mutant=False)
        control_rev = _conflict_run(seed, True, mutant=False)
        control_ok = control_fwd == control_rev
        control_passes += int(control_ok)
        mutant_fwd = _conflict_run(seed, False, mutant=True)
        mutant_rev = _conflict_run(seed, True, mutant=True)
        killed = mutant_fwd["winner"] != mutant_rev["winner"]
        kills += int(killed)
        cases.append({"seed": seed, "control_pass": control_ok, "mutant_killed": killed})
    passed = control_passes == 20 and kills == 20
    return {
        "pass": passed,
        "control_passes": control_passes,
        "control_total": 20,
        "mutant_kills": kills,
        "mutant_total": 20,
        "mutant_kill_rate": kills / 20,
        "cases": cases,
    }


CARDS = [
    ("HM-S01-01", card_01), ("HM-S01-02", card_02), ("HM-S01-03", card_03),
    ("HM-S01-04", card_04), ("HM-S01-05", card_05), ("HM-S01-06", card_06),
    ("HM-S01-07", card_07), ("HM-S01-08", card_08), ("HM-S01-09", card_09),
    ("HM-S01-10", card_10), ("HM-S01-11", card_11), ("HM-S01-12", card_12),
    ("HM-S01-13", card_13), ("HM-S01-14", card_14),
]


def run_gate() -> dict[str, Any]:
    started = time.time()
    cards = {}
    for card_id, fn in CARDS:
        t0 = time.perf_counter()
        try:
            result = fn()
        except Exception as exc:
            result = {"pass": False, "exception": f"{type(exc).__name__}: {exc}"}
        result["duration_s"] = time.perf_counter() - t0
        cards[card_id] = result
        print(f"{card_id}: {'PASS' if result.get('pass') else 'FAIL'} ({result['duration_s']:.3f}s)", file=sys.stderr, flush=True)
    all_pass = all(v.get("pass") is True for v in cards.values())
    return {
        "suite": "Hugh Mann Test v0.2 — Stage 1 Gate",
        "manifest_sha256": "2e8221abf363b57463d57732334ffa2d0568ea6d749eae00ee5f4a4673d76d35",
        "all_pass": all_pass,
        "passed_cards": sum(v.get("pass") is True for v in cards.values()),
        "total_cards": len(cards),
        "started_unix": started,
        "duration_s": time.time() - started,
        "environment": {
            "python": sys.version,
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "cpu_count": os.cpu_count(),
        },
        "cards": cards,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    parser.add_argument("--child-deterministic", action="store_true")
    parser.add_argument("--child-crash", nargs=2, metavar=("CHECKPOINT", "POINT"))
    parser.add_argument("--child-recover")
    args = parser.parse_args()

    if args.child_deterministic:
        print(json.dumps(deterministic_scenario(), sort_keys=True))
        return 0
    if args.child_crash:
        child_crash(args.child_crash[0], args.child_crash[1])
        return 78
    if args.child_recover:
        print(json.dumps(_recover_from_checkpoint(args.child_recover), sort_keys=True))
        return 0

    result = run_gate()
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if result["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
