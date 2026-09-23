# HRM Stage 0 — Canon and Salvage Audit v1.1

**Controlling plan:** HRM Master Development Plan v1.1  
**Selected codebase ancestor:** Age of Agentus Gate-9 frozen baseline  
**Verified upstream SHA-256:** `ae6034d637b3e61649efc2f895d11311af22fe730b1606270ccd4755844de434`  
**Policy:** Fork Agentus; do not continue Gate 10 as HRM. Preserve the Gate-9 baseline byte-for-byte as the reference ancestor.

## Stage-0 rule

Old HRM is presumptively contaminated because most of its behavior was born inside one entangled kernel. Its default implementation disposition is **REWRITE or REJECT unless proven clean**. Old HRM remains valuable as a source of mechanisms, equations, empirical assumptions, tests, failure lessons, and behavioral questions.

Age of Agentus receives no blanket pass either. Its modularity, transaction discipline, qualification infrastructure, and several low-level mechanisms are strong salvage candidates, but every item is judged against HRM v1.1.

## Initial salvage ledger

| Source / lineage | Mechanism | Prior evidence / limitation | HRM disposition | §8 status | Reason | HRM dependency |
|---|---|---|---|---|---|---|
| Agentus Reality Contract | Cross-kernel ownership, projections, private-state boundaries | Frozen and adversarially reviewed; no direct private-state reads | **KEEP** | Live but unvalidated | This is the core anti-entanglement rule HRM needs | All stages |
| Agentus Gate 1/2 | Read → propose → validate/arbitrate → commit transaction semantics | Tested for stale reads, conflicts, ordering and rollback | **ADAPT** | Live but unvalidated | Preserve semantics, but fit them to v1.1's split coordination architecture | Stage 1 |
| Agentus Gate 2 | Deterministic event/replay evidence | Reproducible causal digests and event records | **KEEP** | Live but unvalidated | Essential for scientific replay and auditability | Stage 1 |
| Agentus Gate 1/2 | Opaque identity + provenance DAG | Split/merge/transform/birth provenance tested; self-loop defect found and corrected | **KEEP** | Live but unvalidated | HRM needs lineage across matter, organisms and artifacts | Stages 1–8 |
| Agentus Gate 2 | Matter entities + field reservoirs | Persistent discrete entities and continuous reservoirs exercised under conservation tests | **KEEP** | Live but unvalidated | Strong physical substrate abstraction | Stage 2 |
| Agentus Gate 2 | Mass, momentum, internal/kinetic energy accounting | Conservation and long-run residual tests passed | **KEEP** | Live but unvalidated | Strong invariant/accounting foundation | Stage 2 |
| Agentus Gate 2 | Abstract material component registry | Opaque registered components prevent semantic cheating | **ADAPT** | Live but unvalidated | HRM needs real elemental/compound/material properties rather than opaque components alone | Stage 2 |
| Agentus Gate 2 | Transformation/split/merge/deformation/contact machinery | Hostile suite and scaling tests passed; richer deformation/mixing deferred | **ADAPT** | Live but unvalidated | Keep generic mechanics; expand physical fidelity only where HRM requires it | Stage 2 |
| Agentus Gate 2 | Central Matter arbitration implementation | 25k pathological contention initially exposed O(n²) behavior; corrected; still a shared-authority risk | **ADAPT** | Live but unvalidated | v1.1 requires partitionable/scalable transaction fabric rather than assuming one global bottleneck | Stage 1–2 |
| Agentus Gate 3 | Physical World decomposition into Terrain, Forcing, Atmosphere, Hydrology, Transformation Drivers | Independent/coupled qualification; ownership blocker found and corrected | **KEEP architecture / ADAPT implementation** | Live but unvalidated | Excellent causal separation, but HRM needs much richer natural-world behavior | Stage 3 |
| Agentus Gate 3 | Matter owns conserved water/energy; atmosphere/hydrology propose processes | Reopen fixed illegal ownership of conserved stores | **KEEP** | Live but unvalidated | Prevents environmental modules from inventing matter/energy | Stage 3 |
| Agentus Gate 3 | Synchronization and feedback-lag testing | Explicit sensitivity and resweep doctrine | **KEEP** | Live but unvalidated | HRM spans very different physical/biological/cognitive timescales | All coupled stages |
| Agentus Gate 4 | Producer growth/reproduction/competition + matter exchange | Large independent and real-coupling qualification suites passed | **ADAPT** | Live but unvalidated | Good producer architecture; ecological detail is insufficient for HRM | Stage 4 |
| Agentus Gate 4 | Trait mutation/inheritance | Mechanically present and exercised | **ADAPT** | Live but unvalidated | Useful basis, but needs defensible plant genetics/ecology choices | Stage 4 |
| Agentus Gate 5 | Fauna identity, physiology, inheritance, mutation, reproductive compatibility | Qualified architecture; no privileged species ID | **KEEP architecture / REWRITE implementation** | Live but unvalidated | Species-from-lower-level-properties is excellent; current animal behavior is far too simple | Stage 5 |
| Agentus Gate 5 | Current fauna action model (`REST/MOVE/INTAKE/DRINK`) | Causally functional but intentionally minimal | **REWRITE** | Live but unvalidated | Cannot support realistic predator/prey behavior, ecology, learning, wildlife evolution or long-run historical pressure | Stage 5 |
| Agentus Gate 5 | Observer-derived species principle | Compatibility comes from inherited properties, not authored `species_id` | **KEEP** | Structural | Directly supports HRM's long-run changing fauna without hardcoded species outcomes | Stage 5/11 |
| Agentus Gate 7 | Bounded transition memory | Fixed-capacity traces, decay, observability and missing-data handling | **ADAPT** | Live but unvalidated | Strong clean memory substrate; HRM needs richer episodic/semantic/social memory | Stage 7 |
| Agentus Gate 7 | Similarity-weighted action→outcome learning | Predicts outcomes from stored sensorimotor transitions | **ADAPT** | Live but unvalidated | Good causal-learning seed; needs empirical human calibration and richer representation | Stage 7 |
| Agentus Gate 7 | Prediction error as outcome mismatch | Mechanically represented; later branch tests exposed some candidate-invariant uses | **ADAPT** | Live but unvalidated | Keep prediction error concept; do not inherit every existing scoring use | Stage 7 |
| Agentus Gate 7 | Proposal-only action boundary + seeded tie-breaking | Prevents direct state mutation and hidden enum/list priority | **KEEP** | Live but unvalidated | Clean intention/action separation | Stage 7–8 |
| Agentus Gate 7 | NeutralProposalController / controller genome | Functional but coefficient-driven and intentionally generic; several Gate-10 terms proved behaviorally inert in certain forms | **REWRITE** | Live but unvalidated | Not a sufficient human decision architecture | Stage 7 |
| Agentus Gate 8 | Projection boundary from real world to Homo Agentus | Integration tests cover perception, action translation, arbitration and replay | **KEEP / ADAPT** | Live but unvalidated | Exactly the interface HRM needs; expand perceptual channels without breaking locality | Stage 8 |
| Agentus Gate 9 | Read-only observer + frozen detector discipline | Confirmatory detectors frozen before interpretation; no writeback. First reference execution exposed a fauna/Matter derived-spatial-state ownership/synchronization bug; the invalid run was discarded, Gate-5/Gate-8 implementation was narrowly corrected inside existing authority boundaries, affected work was requalified, and detector thresholds/specification were not relaxed. | **KEEP** | Live but unvalidated | Foundational for honest emergence claims; defect history demonstrates why coupling/reopen discipline must be retained | Stage 11 |
| Agentus governance | BUILD → QUALIFY → adversarial review → freeze discipline | Repeatedly caught real ownership, provenance, timing, scaling and coupling defects | **KEEP** | Structural | v1.1 already adopts the useful tiered form | All stages |
| Agentus Gate 10 | Branch experiments on learning/controller coefficients | Useful positive and negative mechanism probes; baseline remained protected | **DEFER as evidence archive** | Structural | Do not make experimental branches the HRM substrate; consult when rebuilding cognition | Stage 7 |
| Old HRM v4.57 | Seasonal cycles, drought/winter pressure | Demonstrated in old engine but entangled with agent mutation | **REWRITE concept** | Rejected | Natural-world concept is useful; implementation violates modular boundary | Stage 3 |
| Old HRM v4.57 | Renewable/exhaustible stocks, depletion/regeneration | Functional but resource logic directly affected agent state | **REWRITE concept** | Rejected | Rebuild as world/matter processes | Stage 3–4 |
| Old HRM v4.57 | Spatially unequal yield + travel difficulty | Useful environmental heterogeneity | **REWRITE concept** | Rejected | Keep opportunity-space idea, discard group bonuses and behavioral shortcuts | Stage 3 |
| Old HRM v4.57 | Storage/local surplus/material sites | Functional but automated deposit/withdraw and human consequences | **REWRITE concept** | Rejected | Objects/storage can exist physically; use must be chosen by agents | Stage 2/8 |
| Old HRM v4.57 | Fauna carrying-capacity/migration concepts | Present in subsistence layer but coupled to hardcoded human behaviors | **REWRITE concept** | Rejected | Rebuild inside Animal Ecology | Stage 5 |
| Old HRM `memory.py` | Bounded/compressed retention with per-target summaries, recent buffer and retained high-salience events | Source-level audit confirms bounded retention but also explicit named `conflict`/`cooperation` counters and high-salience event classes (`conflict`, `deception`, `death`, `reconciliation`) | **REWRITE concept** | Live but unvalidated | Bounded retention/compression is useful; semantic counters and event-name salience would pre-author psychological/social meaning | Stage 7 |
| Old HRM `beliefs.py` | False/source-specific beliefs, confidence, decay, secondhand evidence | Strong idea; fixed safety/threat channels contaminate semantics | **REWRITE concept** | Live but unvalidated | Directly relevant to v1.1 distributed social information | Stage 7/9 |
| Old HRM `spatial_memory.py` | Uncertain learned locations + social transmission | Useful but tied to old world/kernel assumptions | **REWRITE concept** | Live but unvalidated | Agents must navigate believed geography rather than global truth | Stage 7 |
| Old HRM psychology/experiential | Valence, bonds, grudges, scars, identity tags | These fields directly feed later decisions | **REJECT named-state implementation** | Rejected | They pre-install outcomes HRM should observe rather than author | Stage 7/11 |
| Old HRM relationships | Trust, resentment, attachment, influence, alliance | Privileged relationship labels drive behavior | **REJECT implementation** | Rejected | Rebuild from evidence/history; observer may later label relationship patterns | Stage 7/9/11 |
| Old HRM goals/planning | Fixed survive/acquire/bond/reproduce/dominate/explore goals and templates | Directly scripts behavioral vocabulary | **REJECT implementation** | Rejected | HRM needs transient intentions from biology/cognition, not civilization-flavored goal templates | Stage 7 |
| Old HRM deception | Dedicated deception attempt/detection path | Hardcoded semantic behavior | **REWRITE as signaling capacity** | Rejected | A signal can disagree with belief; acceptance/detection should emerge from evidence | Stage 9 |
| Old HRM language | Automatic language growth + negotiation effects | Some useful signaling ideas; direct behavioral effects prescribed | **REWRITE** | Rejected | Language must become a causal information system, not a conflict-aversion switch | Stage 9 |
| Old HRM development | Life-stage plasticity + named trauma/bond imprinting | Age effects useful; named outcome writes contaminate | **REWRITE concept** | Rejected | Keep developmental plasticity only where empirically defensible | Stage 6–7 |
| Old HRM disease ecology | Aggregate disease equations tied to institutional trust/compliance/quarantine | Social responses pre-authored | **REWRITE from contact ecology** | Rejected | Disease should transmit through organisms/places; social response must emerge | Stage 5–7 |
| Old HRM settlements/territory/factions | Persistent named social structures with direct bonuses/effects | Explicit social conclusions feed behavior | **REJECT implementation** | Rejected | Observer may detect these later; substrate must not create them | Stage 11 only as measurements |
| Old HRM resource transfer | Named trade/theft/charity plus prescribed resentment/reputation effects | Useful physical transfer concept, contaminated interpretation | **REWRITE** | Rejected | Keep generic possession/material transfer; consequences are learned | Stage 8–9 |
| Old HRM innovation | Named innovation pairs/practices and direct rewards | Predetermines technology/institutions | **REJECT implementation** | Rejected | Techniques must arise from learned physical transformations | Stage 7–8 |
| Old HRM `governance.py` | Faction leader registry, legitimacy, privileged coordination signals, compliance/defiance, enforcement, succession and governance gaps | Exact source review: 778-line named governance system; leader legitimacy also gates institutional effects | **REJECT implementation** | Rejected | Installs leadership/governance as causal categories before they emerge | Stage 11 observer may later classify; lower-level signaling/action stays in Stages 8–9 |
| Old HRM `institutions.py` | Fixed council/market/militia types, formation thresholds, taxes, cooperation bonuses and conflict suppression | Exact source review shows named institution types and direct state/resource effects | **REJECT implementation** | Rejected | Predetermines institutional forms and their social/economic consequences | Stage 11 observation only; generic lower-level mechanisms elsewhere |
| Old HRM `culture.py` | Seeded named memes, spread/mutation, cultural-alignment score and direct cooperation/stress effects | Exact source review shows authored meme content and direct behavioral writes | **REJECT implementation** | Rejected | Culture must arise from distributed learning/transmission, not seeded named norms with bonuses | Stage 9 generic information; Stage 11 observation |
| Old HRM `institutional_memory.py` | Faction-level collective memory anchors, cultural profiles/priors, authority tolerance and proto-institutions | Exact source review shows authoritative group-level memory/profiles that feed future behavior | **REJECT causal implementation** | Rejected | Violates v1.1 ban on authoritative causal collective belief/norm/institution objects | Stage 9 individual/durable-record mechanisms; Stage 11 observation |
| Old HRM `social_viability.py` | Founder clustering plus direct trust/cooperation floors, food-sharing trust increments and pair-bond runway | Exact source review shows state injection specifically to bootstrap viable social/reproductive dynamics | **REJECT causal implementation / DEFER metrics** | Rejected | Desired viability is manufactured rather than caused by ordinary interaction | Stage 11 read-only metrics only if redesigned |
| Old HRM `specialization.py` | Role-family inference, specialization depth and direct passive effects for diplomacy/governance/protection/etc. | Exact source review shows named role families causally alter agent state | **REJECT implementation** | Rejected | Skills may be learned, but predefined social roles/bonuses predetermine specialization | Stages 7–8 skills; Stage 11 observation |
| Old HRM `city_twin.py` | External census/API calibration/scenario adapter | Not world physics | **DEFER** | Structural | Could later compare observer outputs with real data without controlling the simulation | Stage 11–12 |

| Old HRM `biology.py` | Sex/reproduction physiology mixed with behavioral asymmetries | Source-level audit of exact v4.57 bytes | **REWRITE physical biology only** | Rejected | Reproductive physiology is required, but old behavioral couplings are not | Stage 6 |
| Old HRM `biology.py` | Sex-specific dominance/risk/resilience/language/social-openness biases | Direct categorical trait offsets | **REJECT** | Rejected | Installs social/behavioral conclusions by sex | — |
| Old HRM `biology.py` | Attraction→cooperation, male competition, same-sex specialization bonuses | Direct outcome modifiers | **REJECT** | Rejected | Manufactures social/economic outcomes | — |
| Old HRM `reproduction.py` | Reproduction, trait blending, mutation | Coupled to faction alliance, role inheritance and composite fitness | **REWRITE biological reproduction** | Rejected | Keep reproduction/inheritance question; discard faction/role/fitness semantics | Stage 6 |
| Old HRM `information.py` | Source-tagged messages, hop count, fidelity, bounded inbox | Functional information transport mixed with faction/leader/ideology semantics | **ADAPT concept** | Live but unvalidated | Good substrate for fallible second-/third-hand information after semantic stripping | Stage 9 |
| Old HRM `information.py` | Leader broadcasts, institutional authority, faction hostility, sex processing bonus | Direct privileged social categories | **REJECT** | Rejected | Pre-installs leadership, institutions, factions and sex effects | — |
| Old HRM `information.py` | Relay error / mutation | Real fallibility concept but old drift is steered by ideology/outgroup state | **REWRITE** | Live but unvalidated | Preserve transmission error without authored group semantics | Stage 9 |
| Old HRM `language.py` | Signal/utterance carrier | Bounded utterance record | **REWRITE** | Live but unvalidated | Communication needs a carrier, not old semantic outcome hooks | Stage 8–9 |
| Old HRM `language.py` | Cooperation/conflict-driven language growth and direct negotiation peace effect | Language variable directly modifies conflict outcome | **REJECT** | Rejected | Hard-coded civilization/social effect | — |
| Old HRM `generational_psychology.py` | Story transmission | Intergenerational channel exists but mutates named trauma/care state | **REWRITE information transmission only** | Rejected | Intergenerational learning belongs; psychological package inheritance does not | Stage 9 |
| Agentus Gate-6 research register | External learning/generalization/forgetting/social-learning literature | Preserved exact source register; no universal parameters imported | **KEEP AS RESEARCH REFERENCE** | Structural | Useful empirical starting point for later calibration, not validation by itself | Stage 7/9 |
| Old HRM untraced numeric behavioral constants | Numerous hand-authored thresholds/weights | Source-level inspection; provenance not established | **REJECT AS SCIENTIFIC PARAMETERS** | Rejected | Plausibility/tuning is not empirical validation | Owning future stage must recalibrate |


## Stage-0 closure decisions

1. **Codebase ancestor:** Age of Agentus Gate-9 frozen baseline, SHA-256 `ae6034d637b3e61649efc2f895d11311af22fe730b1606270ccd4755844de434`.
2. **Gate 10:** evidence archive only; not the HRM baseline.
3. **Old HRM:** archaeological/research source only; no old causal implementation is imported wholesale.
4. **Homo Agentus:** name retained. Agentus Homo cognition is the starting substrate; HRM separates and expands biology/cognition in Stages 6–7.
5. **No prior internal test is promoted to HRM `Validated` solely because it passed Agentus qualification.**
6. **Agentus architecture is not discarded:** Reality boundaries, transactions, replay, provenance, Matter invariants, projection discipline, coupling discipline, bounded memory/learning patterns and observer quarantine are carried forward through the migration map.
7. **Where the owning scientific scope changes materially, implementation is rewritten against preserved contracts/tests rather than blindly copied.**

## Required Stage-0 inventory — completion check

| v1.1 required inventory | Result |
|---|---|
| Reality Contract and cross-kernel interface rules | **COMPLETE — KEEP/ADAPT** |
| Transaction/arbitration and deterministic replay | **COMPLETE — ADAPT into Stage 1 split architecture** |
| Identity and provenance | **COMPLETE — KEEP** |
| Matter conservation and transformation | **COMPLETE — KEEP/ADAPT; chemistry expansion deferred to Stage 2** |
| Synchronization and feedback-lag tests | **COMPLETE — KEEP doctrine/tests** |
| Cognition/learning including prediction-based learning | **COMPLETE — ADAPT; controller rewrite** |
| HRM environment: seasons/depletion/travel/heterogeneity | **COMPLETE — concepts retained; old coupling rejected** |
| Social/faction/role/innovation/settlement/governance/economic contamination | **COMPLETE — generic categories plus explicit source audit of `governance.py`, `institutions.py`, `culture.py`, `institutional_memory.py`, `social_viability.py`, and `specialization.py`; contaminated causal implementations rejected/rewrite-tagged** |
| Old HRM biological stack | **COMPLETE — source-level audit** |
| Old HRM communication/social-information stack | **COMPLETE — source-level audit including `memory.py` traceability** |
| Empirical sources/parameters | **COMPLETE FOR SALVAGE — references preserved; later validation assigned to owning stages** |
| Exact Agentus source migration map | **COMPLETE — every Gate-2/3/4/5/7/8 production source file mapped** |
| Stage-1 entry criteria | **COMPLETE — see `STAGE1/HRM_STAGE1_PROPOSED_ENTRY_CONTRACT_v1.0.md`** |

## Stage-0 proposed disposition — pending independent acceptance

**PROPOSED: READY FOR FREEZE / CLOSE STAGE 0, PENDING REVIEWER ACCEPTANCE.**

The author-side audit work is complete and both conditional-pass correction rounds have been applied in this resubmission, including the `memory.py` traceability repair and explicit governance/culture/institution/specialization inventory. This ledger does **not** declare itself frozen.

**Stage 1 remains LOCKED / NOT AUTHORIZED** until an independent reviewer returns `PASS — FREEZE / CLOSE STAGE 0` and then completes the beginning-of-Stage-1 review.

## Named carry-forward risks / obligations

1. **Matter arbitration bottleneck risk:** Agentus previously exposed a pathological O(n²) contention implementation before correction. HRM Stage 1 must keep contention scaling and partitionability as explicit qualification obligations rather than assuming the corrected Agentus implementation is sufficient at HRM scale.
2. **Gate-9 coupling/synchronization defect history:** the first Gate-9 reference run exposed stale Gate-5 derived spatial state after lawful Matter-owned coupled motion. The invalid run was discarded and the implementation was narrowly corrected. HRM must preserve the rule that derived/private routing state follows canonical owner state through explicit synchronization rather than mutation inside read-only projections.
3. **Runtime concurrency claim is limited:** Stage-1 partitionability may be established architecturally without claiming Python-thread speedup. Before the Stage-10 multi-population baseline is frozen, HRM must perform a process-level or otherwise genuinely concurrent stress pass appropriate to the chosen implementation and population workload.
