# HRM Current Status

**Repository baseline:** clean rebuild; old June HRM kernel removed from the working tree.

## Stage 0

**FROZEN / CLOSED.** The salvage record treats old HRM as contaminated archaeology: ideas, equations, tests, and empirical questions may be inspected, but implementation does not carry forward by default.

## Stage 1

**ACTIVE — corrected post-Round-2; not declared frozen here.**

The supplied dependent Round-2 review found three blocking defects: historical transaction-ID ambiguity, caller-trusted epoch admission, and ledger admission occurring after causal materialization. The active source in this repository corrects those three defects and adds permanent hostile regressions.

Local verification performed during the repository replacement:

- Stage-1 coordination regression suite: **24/24 PASS**.
- HMT Stage-1 cards: **14/14 PASS when executed as isolated/constituent card runs**.
- The monolithic HMT runner exceeded this tool host's execution budget after the load card; that host limitation is recorded rather than counted as evidence.

The supplied review chain does not contain the final independent architecture verdict required to call Stage 1 frozen. Therefore this repository does not claim that verdict.

## Stage 2

**DRAFT / QUARANTINED.** The supplied Matter Slice-A candidate passes **25/25** of its own tests, but its contract contains a Stage-1-freeze assertion that is not established by the supplied review chain. It is retained under `drafts/stage2/` without promotion to the active baseline.
