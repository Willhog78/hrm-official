from __future__ import annotations

from time import perf_counter
import json
import statistics

from hrm_coordination import StateAuthority, TransactionFabric, ReplayLedger, ResourceRef, Mutation, TransactionProposal, ProvenanceContribution
from hrm_coordination.model import digest_obj


def proposal(pid, epoch, aid, rid, value):
    return TransactionProposal(
        proposal_id=pid,
        transaction_id=f"tx-{pid}",
        proposer_id=f"worker-{pid}",
        logical_epoch=epoch,
        mutations=(Mutation(ResourceRef(aid, rid), 0, value),),
        provenance=ProvenanceContribution(source_authority=f"worker-{pid}"),
    )


def build(initials, seed):
    auths=[StateAuthority(a,v) for a,v in sorted(initials.items())]
    ledger=ReplayLedger(digest_obj({"seed":seed,"initials":initials,"stage":1,"benchmark":True}))
    for a,v in sorted(initials.items()): ledger.register_genesis(a,v)
    fabric=TransactionFabric(seed,[a.port() for a in auths],ledger)
    return auths,ledger,fabric


def timed(fn):
    t0=perf_counter(); result=fn(); return perf_counter()-t0,result


def contention(n):
    _,ledger,fabric=build({"A":{"x":0}},"bench-contention")
    ps=[proposal(f"c{i:06d}",0,"A","x",i+1) for i in range(n)]
    elapsed,batch=timed(lambda:fabric.resolve(0,list(reversed(ps))))
    commits=sum(r.status=="COMMITTED" for r in batch.results)
    assert commits==1
    assert ledger.verify_chain()
    return {"n":n,"seconds":elapsed,"proposals_per_second":n/elapsed,"committed":commits,"ledger_records":len(ledger.records),"state_digest":fabric.causal_state_digest(),"arbitration_digest":batch.arbitration_digest}


def partitioned(n, shards=64):
    per=(n+shards-1)//shards
    initials={f"A{s:03d}":{f"r{i:05d}":0 for i in range(per) if s*per+i<n} for s in range(shards)}
    initials={a:v for a,v in initials.items() if v}
    _,ledger,fabric=build(initials,"bench-partitioned")
    ps=[]
    k=0
    for aid,resources in sorted(initials.items()):
        for rid in sorted(resources):
            ps.append(proposal(f"p{k:06d}",0,aid,rid,k+1)); k+=1
    elapsed,batch=timed(lambda:fabric.resolve(0,list(reversed(ps))))
    commits=sum(r.status=="COMMITTED" for r in batch.results)
    assert commits==n
    assert ledger.verify_chain()
    return {"n":n,"shards":len(initials),"seconds":elapsed,"proposals_per_second":n/elapsed,"committed":commits,"ledger_records":len(ledger.records),"state_digest":fabric.causal_state_digest(),"arbitration_digest":batch.arbitration_digest}


def cross_partition_fault_sweep(n=400, fail_every=7):
    left={f"l{i:05d}":0 for i in range(n)}; right={f"r{i:05d}":0 for i in range(n)}
    auths,ledger,fabric=build({"A":left,"B":right},"bench-cross-atomic")
    amap={a.authority_id:a for a in auths}
    failures=[]; successes=[]
    elapsed_total=0.0
    for i in range(n):
        tid=f"x{i:05d}"; should_fail=(i%fail_every==0)
        if should_fail:
            amap["B"].inject_stage_failure_once(tid); failures.append(i)
        else: successes.append(i)
        p=TransactionProposal(
            proposal_id=f"xp{i:05d}",transaction_id=tid,proposer_id="cross-worker",logical_epoch=i,
            mutations=(Mutation(ResourceRef("A",f"l{i:05d}"),0,1),Mutation(ResourceRef("B",f"r{i:05d}"),0,1)),
            provenance=ProvenanceContribution(source_authority="cross-worker"),
        )
        elapsed,batch=timed(lambda p=p,i=i:fabric.resolve(i,[p])); elapsed_total+=elapsed
        status=batch.results[0].status
        assert status == ("REJECTED" if should_fail else "COMMITTED")
    for i in failures:
        assert fabric.projection("A",[f"l{i:05d}"])[f"l{i:05d}"].value==0
        assert fabric.projection("B",[f"r{i:05d}"])[f"r{i:05d}"].value==0
    for i in successes:
        assert fabric.projection("A",[f"l{i:05d}"])[f"l{i:05d}"].value==1
        assert fabric.projection("B",[f"r{i:05d}"])[f"r{i:05d}"].value==1
    return {"transactions":n,"forced_failures":len(failures),"successful":len(successes),"seconds":elapsed_total,"transactions_per_second":n/elapsed_total,"ledger_records":len(ledger.records),"ledger_chain_valid":ledger.verify_chain()}


def main():
    sizes=[1000,5000,10000,25000]
    out={"contention":[contention(n) for n in sizes],"partitioned":[partitioned(n) for n in sizes],"cross_partition_fault_sweep":cross_partition_fault_sweep()}
    print(json.dumps(out,indent=2,sort_keys=True))

if __name__=='__main__': main()
