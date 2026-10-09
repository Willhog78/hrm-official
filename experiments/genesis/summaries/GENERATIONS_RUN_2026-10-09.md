# Generations run — 30 years, four seeds (2026-10-09)

**Question.** Do world-born children reach adulthood and sustain another generation? Do animal losses and learned behaviour carry forward?

**Configuration**
- Production arm `v1`, as committed. It includes:
  - demand-limited milk;
  - the water-cycle scale fix;
  - the size-scaled child energy store.
- Streaming replay ledger: xz, 30-epoch groups.
- Runner: `experiments/genesis/run_generations.py --years 30 --checkpoint-years 5 --keep-checkpoints 2 --min-free-gb 0.4 --auto-resume`.
- Railway deployment `bffa7184`, volume `/data`. Nothing was tuned or injected during the run.

**Known limitation, unchanged for this run.** The hunger reference is inconsistent, as documented in `CHILD_ENERGY_STORE.md`.

**Life-history constants that bound what 30 years can show.** Maturity is at 18 years and independent feeding at 5 years (`human/calibration.py`). A child's generation is its mother's generation + 1.
- Generation 2 means a child of a world-born (generation-1) mother.
- The first generation-2 child was born in year 19, so no generation-2 individual can reach adulthood before about year 37.
- This run therefore shows generation-1 adulthood and generation-2 births. It cannot show generation-2 adulthood or generation-3 births.

## 1. Outcome at year 30

| Seed | Alive | Gen 0 / 1 / 2 | Adults (gen 0 + gen 1) | Gen-1 adults | Gen-1 births | Gen-2 births | Human deaths |
|---|---|---|---|---|---|---|---|
| a | 80 | 8 / 39 / 33 | 21 | 13 | 39 | 34 | 1 |
| b | 91 | 8 / 34 / 49 | 22 | 14 | 35 | 52 | 4 |
| c | 25 | 8 / 9 / 8 | 12 | 4 | 9 | 8 | 0 |
| d | 127 | 8 / 53 / 66 | 24 | 16 | 57 | 70 | 8 |

**Answer, observed.**
- In every seed, world-born children reached adulthood, starting in year 19. That is the earliest year possible, because the first children were born in year 1 and maturity is 18 years.
- Those adults then had children. Generation-2 births began in year 19 in a, b and d, and in year 20 in c, and continued every year in a, b and d through year 30.
- All 8 founders in every seed are still alive at year 30.

## 2. Demography

### Population by year (alive at year end)

| Year | a | b | c | d |
|---|---|---|---|---|
| 1 | 12 | 11 | 9 | 12 |
| 5 | 15 | 17 | 12 | 24 |
| 10 | 19 | 21 | 12 | 24 |
| 15 | 23 | 22 | 12 | 24 |
| 18 | 23 | 22 | 12 | 24 |
| 19 | 28 | 26 | 12 | 29 |
| 20 | 34 | 31 | 14 | 37 |
| 22 | 47 | 42 | 20 | 59 |
| 25 | 62 | 57 | 25 | 85 |
| 28 | 76 | 77 | 25 | 115 |
| 30 | 80 | 91 | 25 | 127 |

### The year-5 to year-18 plateau and its end

- **Seeds c and d stopped births completely.**
  - c had no births from year 5 to year 19.
  - d had none from year 6 to year 18.
- **Seeds a and b slowed to 0–1 births a year**, and had none at all from year 15 (a) and year 12 (b) until year 19.
- **Measured cause in seed d** (`scratchpad repro_check`, year 7): every one of the 1,460 adult-female days failed on a single condition, `no_adult_male_in_cell`. Energy, body mass (about 28 kg against a 25.2 kg threshold) and cooldown were all satisfied. The founders' sexes did not share cells. Reproduction rules were not changed.
- **Birth restart.** Founder mothers (gen-1 births) and world-born mothers (gen-2 births) resumed or began births in year 19 in a, b and d, and year 20 in c. The subsequent diagnosis traces qualifying males and daily eligibility; see `GENERATIONS_DIAGNOSIS_2026-10-09.md`.
  - Inference, not measured: new adult males now share cells with founder and generation-1 females, which removes the `no_adult_male_in_cell` block. A per-day diagnostic at year 19 would confirm or refute this.
- **Seed d's 4-a-year pattern.** d had exactly 4 gen-1 births in years 1–4, 19–22 and 24–27, which is consistent with all 4 founder females giving birth in those years.
- **Founder births ending.** In seed a, founders had no births after year 27; generation-1 mothers continued (2–3 births a year in years 28–30). In b and d, both founders and generation-1 mothers were still giving birth in year 30.
- **Seed c after year 25.** c had no births at all from year 26 to year 30, with 12 adults alive (8 founders and 4 generation-1). This was not diagnosed.

### Adulthood (generation 1 becoming adult)

| Seed | Year 19 | Year 20 | Year 21 | Year 22 | Years 23–30 | Total |
|---|---|---|---|---|---|---|
| a | 4 | 1 | 1 | 1 | 6 (one each in 24, 25, 26, 27, 29, 30) | 13 |
| b | 3 | 2 | 2 | 2 | 5 (one each in 24, 25, 26, 27, 29) | 14 |
| c | 1 | 1 | 1 | 1 | 0 | 4 |
| d | 4 | 4 | 4 | 4 | 0 | 16 |

Generation-1 children born after year 12 are not yet 18, so the adult counts are bounded by birth year, not by survival.

### Deaths (cause | generation | stage)

| Seed | Deaths |
|---|---|
| a | energy, gen 2, dependent: 1 (year 27) |
| b | energy, gen 1, dependent: 1 (year 5); energy, gen 2, dependent: 1 (year 24) + 2 (year 29) |
| c | none |
| d | energy, gen 1, dependent: 2 (year 5) + 2 (year 29); energy, gen 2, dependent: 1 (year 24) + 2 (year 25) + 1 (year 27) |

- Every death was a dependent child dying of energy shortfall.
- No adult or juvenile died in 30 years, in any seed.
- No founder died. Founders were adults at the start, so they are at least 48 years old by year 30. No human old-age deaths occurred.
- **Not diagnosed:** why these dependents died. In particular, whether the inconsistent hunger reference is involved is not established.

## 3. Animals

| Seed | Grazer | Stalker | Browser (start → year 30) |
|---|---|---|---|
| a | extinct by year 2: both initial grazers captured; the third capture was a browser | starved, year 3 | 1 → 631 |
| b | 1 survived year 1 (1 grazer captured); then grew to 4,090 at year 30 | captured by Agentus on day 17 | 2 → 819 |
| c | persisted; 2,044 at year 30 | 1 alive until year 23; starved | 2 → 712 |
| d | extinct in year 1: 2 captured by Agentus | starved, year 2 | 2 → 864 |

- **The extinctions in the first two years carried forward.** In seeds a and d, grazers were extinct and stalkers starved by year 3, and browsers then became the only animals.
- **The predator-free worlds grew steadily.**
  - Browsers increased in every seed.
  - Where grazers survived (b and c), they grew from single digits to thousands, with the steepest growth after year 20.
  - Edible plants stayed between 830 and 890 t.
  - Animal deaths after year 3 were old age and Agentus captures (c), plus one stalker starvation (c, year 23).

## 4. Useful behaviour

| Seed | Captures (30 y) | Imitation tries / paid | Follow days | Repeated acts (years) | Worn objects |
|---|---|---|---|---|---|
| a | 3 (years 1–2) | 444 / 0 | 0 | years 1, 2, 11, 12 only | 0 |
| b | 2 (year 1) | 283 / 0 | 0 | none | 0 |
| c | 28 (years 3–30) | 70 / 0 | 0 | many, years 12–30 | 0 |
| d | 2 (year 1) | 593 / 0 | 0 | years 1, 8 only | 0 |

- **Hunting persisted only where prey stayed reachable.**
  - In a, b and d, every capture happened in years 1–2.
  - In a and d, the grazer the founders had learned to strike went extinct, so their positive learned value (`strike:animal_grazer|stone_heavy` in a, `strike:animal_grazer|none` in d) survives in living memory for 28 years with no target.
  - In b, the surviving grazers multiplied to thousands, yet no further capture occurred.
- **Seed c built up a repeated tool repertoire.** Seed c is the only one with a growing set of repeated acts:
  - striking browsers with a stick (from year 18), with a small stone (years 28–30) and with an edged stone (year 27);
  - binding two sticks (year 21), a stone to wood (years 28–29) and wood to a stick (year 27);
  - working bark and strands with a stone (year 29).

  Its captures rose to 9 in year 27 and 7 in year 30. Its positive learned values include `strike:stone_edged|bound_stone_small_on_stick` and `bind:stone_small+stick|strand`.
- **The immediate imitation payoff counter stayed zero.** Attempts rose with population, peaking at 128 in one year in d. This counter does not cover observation-based value updates or later benefits from preparation; zero is not evidence that all social learning failed.
- **Following and clothing never appeared.** Following was 0 throughout, and no object was ever worn, so insulation saving was 0.
- **World-born tool use is present in c.** The subsequent diagnosis attributes repeated acts and positive values to generation-1 individuals `human-b00000008` and `human-b00000009`. The original `positive_acts_living` summary alone could not establish this.

## 5. Run mechanics

| Seed | Finished (UTC) | Wall time | Final ledger digest | Peak RSS | Disk (ledger + checkpoints) |
|---|---|---|---|---|---|
| a | 05:24 | 7,569 s | `d5ad155f7b374d93…` | 0.41 GB | 956 MB |
| b | 05:56 | 9,506 s | `3270197ada885795…` | 0.55 GB | 962 MB |
| c | 05:02 | 6,257 s | `b33bce361106989d…` | 0.37 GB | 858 MB |
| d | 05:40 | 8,559 s | `5c2257fda22e3587…` | 0.48 GB | 1,002 MB |

- **Memory.** Peak memory stayed under 0.6 GB per seed for 30 years. The earlier in-memory ledger reached 4.35 GB by year 5.
- **Disk.** Ledger growth per year rose with population, from about 21 MB to about 50 MB.
- **Determinism.** The first 30-year attempt (gzip, no volume) was killed at years 17–22. Each of its yearly ledger digests, 37 in all, matches this run's digest for the same seed and year.
  - Last common years: a year 19 `d0d3f6e1…`, b year 19 `825312cc…`, c year 22 `ac791e82…`, d year 17 `46faab51…`.
  - The two runs used different codecs and grouping, and the matches confirm both are deterministic.
- **Volume.** After all four seeds: 3.6 GB of 4.6 GB used, 958 MB free.
- **No restarts.** No resume was needed: the runner did not restart, there was no Traceback, and the disk guard did not trigger.

## 6. What this does and does not establish

**Established, observed:**
- In all four seeds, world-born children survived to adulthood. Generation-2 births began in year 19 in a, b and d, and year 20 in c.
- Through year 30, gen-2 births continued in a, b and d, but stopped in c after year 25.

**Not established:**
- whether generation-2 children reach adulthood, which needs a run past about year 37;
- whether generation 3 appears;
- why seed c's births stopped after year 25;
- why the dependents died;
- the cause of the year-19 restart of founder births, which is inferred, not measured.

**Behaviour.** Seed c developed a repeated stick-and-stone repertoire, including world-born users. The immediate imitation payoff counter remained zero; the subsequent diagnosis identifies measurement and eligibility limitations. Following and clothing stayed absent.

No world or behaviour change is proposed here.
