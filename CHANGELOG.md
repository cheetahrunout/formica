# Formica — changelog

A *Lasius niger* colony simulator. Colony-level behaviour must emerge from
individual local rules; no ant may read a colony total. Every claim is measured
against a matched control rather than asserted.

Entries record what changed, the research basis, the measured result, and —
where relevant — what went wrong on the way. Failed attempts are kept because
several of them were more informative than the fix.

---

## v1.8b — a download is not a save

Marathon mode wrote one file per colony by synthesising an anchor click, and
`endRun` cleared `runLog` on the very next line. If the download did not land,
the run was gone — no error, no trace, no in-memory copy. Three ways that
happens, all silent:

- Chromium blocks repeated automatic downloads from one origin. The first run
  saves, then a permission prompt appears; unattended, every later run is
  dropped. That is exactly marathon mode's access pattern.
- "Ask where to save each file" turns an overnight run into a queue of dialogs.
- A crashed or closed tab loses the entire in-progress colony, which for a
  lifetime run is thousands of sim-days.

The blob URL was revoked after four seconds regardless, and the whole thing sat
inside a `try/catch` that swallowed the failure and let execution continue to
the line that wiped the log.

**Four tiers now, strongest first.**

- **In-memory mirror.** `memPut()` runs synchronously inside `persistRun()`
  before anything that can fail or await. Nothing downstream — a denied store, a
  blocked download, a missing folder — can lose a completed run within the
  session. This is the floor and it cannot be refused.
- **IndexedDB.** Survives reload and tab crash, needs no permission. Written
  before the in-memory log is cleared.
- **Directory handle.** If the operator grants a folder once, every run is
  written straight to disk unattended, with no prompt. This is what a machine
  left running overnight actually needs. The handle is stored and re-offered on
  reload; anything held is drained into the folder the moment one is granted.
- **Download.** Now the last resort, and a started download never releases the
  stored copy — only a confirmed disk write does.

Also added: `AUTOSAVE_EVERY` (20 samples, ~200 sim-days) checkpoints the
in-progress run under a fixed key, so a crash mid-colony costs at most one
interval instead of the whole colony. The completed run supersedes its own
checkpoint. A `saving:` readout in the control strip names the tier actually in
force, because a persistence scheme that silently degrades is the bug this entry
is about.

**Measured, worst case.** IndexedDB denied outright (`SecurityError` — an opaque
origin refuses `open`) *and* `browserDownload` stubbed to fail:

- a 250-day run survived intact — 25 rows, correct header, `seed 4242`,
  recoverable through **Export held**;
- three consecutive marathon `endRun("colony extinct")` calls held all three
  runs, none lost, before any download was even attempted;
- the recovered text round-tripped through `summarise-runs.py` and parsed
  cleanly as run 2, seed 1001, 16 emerged — no false flags;
- format unchanged: 28 columns, `diap laid bDied bEaten` still last, comment
  header intact. `logText()` is the original string builder, moved not rewritten.

**Not verified here.** The preview pane this was tested in serves the page from
a `data:` URL, so IndexedDB is refused and `showDirectoryPicker` could not be
exercised. On a real `file://` page in Edge or Chrome both should work, and the
`saving:` readout will say which. If it reads *session only*, the folder grant is
the one to fix, because that is the tier that makes an unattended night safe.

### v1.8b addendum — the in-progress file

Granting a folder worked first try on `file://` in Chrome, which settles the
open question above: `showDirectoryPicker` is available and unattended writes
land. The first checkpoint on disk exposed three faults that only appear once
the folder tier is actually live:

- **The disk copy went stale.** `checkpointRun()` wrote to memory and the store
  but not the folder, so after a crash the folder held an old day while the
  fresh state sat somewhere you need the page open to reach. Checkpoints now
  write to the folder too — that is the whole point of a checkpoint.
- **The partial filename carried the day**, so writing every checkpoint to disk
  would have left one file per interval, dozens over a night. `partialName()`
  omits the day, so each checkpoint overwrites one file.
- **A completed run left its partial behind**, which would have had
  `summarise-runs.py` count every colony twice. Completing a run now deletes the
  partial file, and the summariser separately refuses to treat an in-progress
  checkpoint as a colony — it is reported above the table and excluded from every
  aggregate, since counting it would drag peak population and lifespan down.

## v1.8c — pending, found by summarise-runs.py

The first log written by v1.8a tripped two flags that are real defects, both in
the marathon exit path, neither yet fixed:

- **`QUEEN DIED` is never logged when it coincides with extinction.** The event
  is an `else if` after the termination check, so when both fire on the same
  tick the death is dropped. In `formica-run001-colony_extinct-day5879.tsv`,
  `qAge` reaches exactly 3400.0 — `Q_LIFE_DAYS`, senescence — and the event list
  jumps from the last reactivation straight to `RUN END`. The log records that
  the colony ended but not why.
- **498 days of post-extinction padding.** The last worker died on day 5381; the
  run logged 50 more samples of `pop 0` until day 5878.6, because termination
  also requires `!queen.alive`. v1.8 fixed the `countBrood()===0` clause of this
  same condition; the queen clause was left, so the claim that the padding bug is
  fixed is only three-quarters true.

---

## v1.8 — larval diapause becomes the larva's own state

Prompted by analysing run 1 (`formica-run001-manual_save-day12705.tsv`), a
34.8-year marathon. The colony peaked at 644 workers on day 2941, declined for
3,590 days, and went extinct on day 6531.6. Two things in that file did not
add up: 15 larvae sat alive and completely unchanging for the last 6,853 days,
and the run kept logging for 6,173 days after the last worker died — 49% of the
file, every counter frozen, ended only by a manual save.

Both were one bug.

**Diagnosis.** `broodHalted()` read the queen directly:

    return queen.dormant || queen.glass > CFG.GLASS_LEN*CFG.GLASS_LARVA_AT;

`QUEEN_PROGRAM` returns early once she is dead, so her glass freezes wherever it
stood. She died on day 5878.6, which is 181.6 days after the last reactivation
on day 5697.0 — and 181.6 is exactly the `qGlass` value in every remaining row
of the file. The larval threshold is 195 × 0.76 = 148.2. Frozen at 181.6, the
condition was true forever: the halted branch skipped development, hunger, the
starvation test and the death roll alike, so the cohort could neither grow nor
die. The arithmetic closes on the other end too — the halt fires at glass 148.2,
i.e. day 5845.2, and the last emergence in the log is day 5851.5, the next
sample. The larvae were locked into a winter that could no longer be ended.

`endRun` requires `countBrood()===0`, which immortal brood makes unreachable, so
marathon mode could never terminate. Fixing brood mortality fixes termination;
`endRun` itself is unchanged.

**A global read, too.** Every larva in the nest was reading one individual's
internal state at any distance. That is the thing the project does not do.

**Induction stays endogenous — a thermal gate was considered and rejected.**
The source comment claimed temperature induction ("larval diapause is induced at
higher temperatures than her reproductive diapause"), and local temperature is
already in hand at that line. It does not work. Under the default season
(`TMEAN 16, TAMP 9, PEAK -25`) the larval halt falls on doy 5.2 at **23.81 °C**,
only 29 days past midsummer and 46.8 days ahead of the queen's own dormancy at
18.19 °C. 23.8 °C is crossed **twice a year** — doy 311 rising, doy 4 falling —
so a thermal threshold would arrest the spring cohort as readily as the autumn
one. Disambiguating needs a temperature derivative, which is not a clean local
cue. The sand-glass that replaced the thermal gate in v1.5 stays; only the
ownership of the clock changes.

**What changed.**

- Brood carries `glass`, `chill` and `diap` per item. The seasonal phase is
  inherited from the mother at laying (`addBrood(x,y,type,glass)`) — maternal
  induction of diapause is well attested in insects, marked `[C]` in source —
  and the larva runs its own clock afterwards, reading nothing of hers.
- Termination mirrors the queen's two-condition rule but reads locally:
  `chill >= CHILL_NEED && tempAt(larva) >= WAKE_T`. Chilling arms it, local
  warmth fires it. A larva orphaned mid-winter still gets a spring.
- `termRate()` hoisted from inside `QUEEN_PROGRAM` to module scope, so the queen
  and every diapausing larva terminate on **one** curve. Two copies on different
  curves is the `tScale` mistake; not repeating it.
- `LARVA_WINTER_DRAIN: 0.004/day`, labelled a **free parameter**. A diapausing
  larva was previously free — "no development, no hunger, no cost" — for ~170
  days a year, every year, which is also a suspect in run 1's `fatMean` sitting
  at the 1.600 cap in 26% of samples. At 0.004 a normal 170-day winter costs
  0.68 hunger, under the 1.0 that blocks development, while a larva left in
  permanent diapause starves in about four years. Not swept yet.
- Logging extended to 28 columns: `diap`, `laid`, `bDied`, `bEaten`. Run 1
  logged 3,140 emerged against ~5,900 eggs implied by integrating `qRate`, and
  the missing ~2,800 brood appeared nowhere in the file. The recruitment budget
  now closes, which is what run 1 needed to explain its own decline and could
  not.

**Failed first attempt: chilling read from the larva's own location.** The
obvious move — the larva is local, so accumulate its chilling from
`tempAt(brood.x, brood.y)` — is wrong, and the run caught it where the analysis
did not. Nurses hold brood in the `BROOD_T_LO..HI` (23–26 °C) band, so a larva
sits about **4 °C above ambient**, not below it: measured 23.7–24.2 °C against
ambient 19.9 °C. At that temperature `termRate()` pins to `CHILL_WARM_FLOOR`
(0.10/day), so chilling crawls. A cohort halted on day 67 was **still halted on
day 640** — 573 days across two winters, having reached only 48 of the 55 chill
it needed. The v1.7 bug made larvae immortal; this would have given them
two-year diapause instead.

The analytic pre-check missed it because it assumed a nest offset of −0.8 to
+1.2 °C from the `tempAt` expression, and never checked what the brood-placement
rules actually do with it. Rule 5 in CLAUDE.md, earned again.

Chilling is a property of the season, not of the chamber the larva is lying in,
and the queen already reads it that way. Both the accumulator and the spring
trigger now use `ambient`, exactly as she does. The larva owns its clock; the
weather is shared. Keeping the trigger on local temperature would also have
disarmed the safeguard her own comment names — brood held at ambient + 5 crosses
`WAKE_T` at an ambient of 7 °C, which is the annual minimum, so chill alone
would have woken the cohort in midwinter.

**Measured, in-browser.** No JS runtime on this machine (`node`, `bun`, `deno`
all absent), so the eval-with-stubbed-DOM harness in CLAUDE.md could not run.
It was not needed: formica is a browser app, so `probe-v18-diapause.js` drives
`step()` directly in the page, which tests the real environment rather than a
stub. Edge managed ~39,000 ticks/sec, about 46 sim-days/sec — roughly 4× the
documented headless rate. Worth keeping as a harness option.

- **A, matched control (queen alive, 800 days).** Halt and wake transitions at
  doy 6.0 / amb 23.7 °C and doy 222.0 / amb 12.0 °C, repeating exactly across
  years. That is v1.7 timing reproduced to the sample: the predicted halt was
  doy 5.2 at 23.81 °C, and run 1's logged reactivation was doy 222.0 at 12.0 °C.
  Recruitment budget closes exactly — laid 513 = emerged 153 + starved 62 +
  eaten 64 + alive 234, residual 0. (`laid` counts trophic eggs too, so that it
  balances and so that it matches `qRate`, which does not distinguish them.)
- **B, orphan with the cohort active.** Queen killed day 300 with 65 brood and
  21 workers. Brood reached zero on day 370, 95 starved, `endRun("colony
  extinct")` fired on day 1024.3.
- **C, orphan with the cohort halted — the actual run-1 failure mode.** Queen
  killed on day 403, doy 38, **qGlass 181** against run 1's 181.6, with **130
  larvae in diapause**. Those 130 are precisely the ones v1.7 made immortal.
  They **woke on day 587, doy 222.0, ambient 12.0 °C** — the normal reactivation
  day, with no queen alive anywhere in the model. Brood reached zero on day 701,
  207 starved, `endRun("colony extinct")` fired on day 1364.3.

`probe-v18-diapause.js` then ran end to end as a single paste: **ALL PASS, 0 of
11 checks failed**, with the halted-cohort orphan waking on day 587, doy 222.0,
12 °C and the marathon terminating on day 1153.2. Re-run after the reproducibility
work below: ALL PASS again, orphan waking day 587 doy 222.0, endRun day 1198.2.

All 21 source hunks applied under assertion; column count, brace balance and the
absence of any remaining `broodHalted` reference verified against the file text.

## v1.8a — reproducible runs

An in-passing claim in the v1.8 notes above was **wrong**: `rnd()` was described
as unseeded. It was never unseeded — it is mulberry32 driven by a fixed
`seed = 20260828`. What actually varied was that `reset()` did not touch the
seed, so each successive run continued the stream wherever the last one stopped.
The probe's own phases were what made counts differ between runs.

Fixing that exposed a second and more interesting problem. Forcing the same seed
twice still did **not** reproduce a run:

    reset(999001) -> 300 days -> pop 16, cells 200, centroid 426.90, 231.56
    reset(999001) -> 300 days -> pop  2, cells 231, centroid 399.15, 284.11

`reset()` rebuilds terrain, pheromone fields, ants, brood, queen, larder, food
and the aphid patches — but it left the cached shortlists and the batch phases
alone. `sortList`, `hungryList`, the brood centroid `broodC`, `misplacedTick`
(the 15-tick shortlist cadence) and `evapTick` (the evaporation batch phase) all
carried one colony into the next. Those are simulation state, not scratch.
Clearing them in `reset()` is what actually made runs reproducible.

- `BASE_SEED` with `seedFor(runId)`, so marathon colony 2 differs from colony 1
  while every run stays replayable. `seedFor(1) === BASE_SEED`, so the historical
  default trajectory — everything measured up to and including v1.7 run 1 — still
  reproduces exactly.
- `reset(forceSeed)` sets the stream **before** `buildWorld()`. A probe cannot
  fix the seed by assigning after `reset()` returns; world generation has already
  consumed it.
- The seed is written into the log header (`# formica run 1  seed 20260828 ...`),
  so any logged run can be replayed from the file that recorded it.
- The reset button no longer hard-codes the seed; `reset()` derives it.

**Measured.** `reset(999001)` twice, with a differently-seeded run in between to
disturb the stream, now gives byte-identical results across population, brood,
cells, all six cumulative counters, queen fat and age, summed worker fat and the
ant centroid to six decimals. Identical at 300 days and again at 600 days, zero
differing keys. The no-argument default is likewise identical run to run, and
`seedFor` is collision-free over the first 49 runs. `probe-v18-diapause.js` now
forces an explicit seed per phase.

This is what CLAUDE.md's "run the matched control" rule needs to actually mean
what it says: before this, a control and a treatment differed by the change
*plus* wherever the PRNG happened to be *plus* whatever the previous colony left
in the shortlists.

---

## v1.7 — run logging and marathon mode

- 24-column TSV sample every 10 sim-days: population, foragers out, nest cells,
  cells/ant, brood by stage, stalled larvae, larder units, crop sum, mean fat,
  queen age/glass/chill/dormancy/rate, cumulative emerged/died/digs/fills/meals.
- Event lines for dormancy onset, reactivation and queen death, each stamped
  with the temperature at which it happened.
- **Marathon mode** (default on): on colony extinction the log downloads itself
  and a fresh run starts, so an unattended machine produces one file per colony
  lifetime. Manual "Save log" button; Reset now closes the log instead of
  discarding it.
- Verified headless end-to-end: forced queen death → wind-down → finalize →
  restart → run two reaching day 50 with brood present.

Standing rule from here: when a new measurable quantity appears, the logging is
extended to capture it without being asked.

## v1.6 — diapause termination as a rate curve

- Replaced the flat `CHILL_WARM` constant with `termRate(T)`: reduced below
  1 °C, maximal across a 1–6 °C optimum, decaying exponentially above it to a
  declared floor. Shape follows the *Pieris* quantitative diapause model
  (termination slows as temperature rises above 1 °C while metabolic rate
  climbs — a twofold cost of warmth).
- `CHILL_NEED: 55` now double-sourced: keeper practice (8–10 weeks) and
  *P. melete* chilling experiments (50–60 days at 1–10 °C).
- `CHILL_WARM_FLOOR` is labelled in source as a **free parameter**, swept
  rather than defended.

**Sweep result, and a correction.** Three-year matched runs:

| | emerged | pop | dormant days | queen metabolic age |
|---|---|---|---|---|
| seasonal | 266 | 205 | 482 | 636 |
| warm, floor 0.03 | 15 | 0 | 1018 | 935 |
| warm, floor 0.10 | 142 | 71 | 823 | 935 |
| warm, floor 0.25 | 581 | 245 | 628 | 935 |

At floor 0.25 the warm colony *beats* the seasonal one. My earlier claim that
"direction is robust, magnitude is parameter-dependent" is **falsified** on a
three-year horizon. What survives: the queen-ageing cost is invariant at
935 vs 636 metabolic days (47% faster burn) across every floor, and the
un-floored curve itself gives ~0.04 at 22 °C, so 0.25 means overriding the
measured shape. Converting the ageing cost into lost production needs a full
~15-year run — the open experiment.

## v1.5 — nurse fetch-and-deliver

- New states 8 and 9: a nurse who finds a hungry larva with no cache within
  `LARDER_R` but one within `FETCH_R` walks to it, takes one meal, carries it
  back, feeds whoever is hungriest on arrival, and banks the meal if nobody is.
- Probe first, build second. The headline 98.3% "no cache in reach" figure was
  **misleading**: the run was bit-identical to the pre-fetch build, proving the
  larder was globally empty at every miss. Famine, not distance.
- Equilibrium stalling measured at **1.9%** time-averaged. The historical 15%
  predated the sand-glass, when larvae hungered year-round. The item's premise
  had expired.
- Fetch retained anyway and unit-tested (hunger 1.40 → 0.40, pile 5 → 1). In
  normal running it is nearly always idle — now a measured fact.
- Also settled: low day-420 population was seed variance (53/80/115 across
  three seeds), not role-split damage.

**Mistakes:** a failed patch left the behaviour in but the CFG constants out, so
`FETCH_R` was `undefined` and every distance check silently failed — hidden
because `undefined === undefined` counted as a match. The first unit test placed
the cache inside solid soil, making a correct timeout look like a bug.

## v1.4 — backfill churn brought under control

Traced-sediment benchmark (*P. badius* in layered coloured sand): ~2.5% of
excavated sediment is redeposited below ground. v1.3 was undoing **92%**.

Five mechanisms, in the order they were found, with the churn after each:

1. **Seasonal memory gate** — winter vacancy no longer reads as abandonment. 92 → 40%.
2. **Unified slow signal** — dig and fill read the same weeks-averaged
   occupancy. Made it *worse* (46%) but exposed the disease: the trigger fires
   where the crowd is, the dig lands at the frontier where nobody goes.
3. **Density cap on everyone** — churn collapsed and so did the colony
   (peak 163, declining). Trophallaxis needs contact; contact needs density.
4. **Role-split aggregation** — nurses on the brood, off-duty foragers resting
   through the galleries. Colony recovered to 402; churn back to 54%.
5. **Cell commitment** (240 days) — freshly dug space cannot be reconsidered.
   Every earlier scheme leaked at this joint: a cell is always momentarily
   unused right after it is dug. **20% cumulative, 7% in construction phases.**

Verdict: closer, not there. 3–8× over benchmark instead of 37×. Remaining gap
believed structural — real galleries hold middens, caches and resting chambers
this model lacks. Cranking `CELL_COMMIT` further would fake the number and break
shrink-tracking; cells/ant already drifted to 7.75 late-run from that tension.

## v1.3 — backfilling

- Nest volume previously only ratcheted upward, so any population decline
  inflated cells/ant permanently. The volume law broke under a seasonal cycle.
- Fill trigger is the mirror of digging, with wide hysteresis so neither chases
  the other.
- **Topological simple-point test**: a cell may be filled only if its excavated
  neighbours form exactly one connected run around the 3×3 ring. Cannot sever a
  gallery, orphan a chamber, or seal the entrance.
- First attempt required a dead-end tip (≤1 neighbour) — provably safe but fired
  **5 times in 1,100 days**. Same guarantee, no false negatives, after the
  rewrite: 14,151 fills.
- Connectivity verified by flood-fill from the entrance on every sample: `n/n`
  throughout. Ants refuse to bury brood, larder, queen or nestmate.

## v1.2 — Kipyatkov's sand-glass (endogenous dormancy)

Research overturned the planned design. *L. niger* is endogenous-heterodynamic:
after spring reactivation the colony runs a fixed period and enters dormancy on
its own schedule regardless of temperature. **Winter cannot be skipped, only
spent warm.**

- `queen.glass` accrues per active day; at 195 days she stops. Larvae commit to
  diapause earlier (larval diapause is induced at higher temperatures than the
  queen's reproductive diapause). Late eggs are eaten, not wasted.
- Reactivation needs chilling **and** spring warmth. Chill alone would wake her
  in January.
- **Ageing runs on metabolism**, not the calendar — diapausing insects live
  ~3× longer via metabolic suppression. `Q_LIFE_DAYS` rescaled to 3400
  metabolic-days to preserve ~15 calendar years.
- **Discarded: the strain accumulator.** The plan had strain accruing with
  laying effort. Ant literature says the opposite — experimentally increasing
  fecundity in *Temnothorax* queens *co-activates* body-maintenance genes, and
  caloric restriction reduces both lifespan and reproduction. Queens break the
  fecundity–longevity tradeoff; a laying-cost term would encode a tradeoff they
  specifically do not have.

**Headline validation:** she stops at day 417 and 782, both at **18.2 °C** —
~60 days before ambient crosses 14 °C. A thermal gate cannot produce this.

**Also corrected mid-build:** the first version used a hard chill gate, so the
warm colony never reactivated and died by construction — which proves nothing.
Softened to slow warm accrual; the effect survived.

## v1.1 — seasonal clock, thermal scaling, overwintering

- `ambient = 16 + 9·cos(2π(day − peak)/365)`: 7 °C midwinter, 25 °C midsummer.
  A sinusoid moves ~0.17 °C/day near the equinoxes, inside the 0.2–2 °C/day
  ramping guidance, so no separate ramp mechanism is needed.
- `tempF` holds only the static gradient; ambient added at read time. Avoids
  rewriting 17,920 cells per sim-day and is faster than before.
- **One scalar into every rate.** Per Rathery et al., ants dig faster when warm
  purely because they move faster, and nest shape is unchanged — digging is not
  a seasonal behaviour. So no winter switches anywhere: locomotion, metabolism,
  larval hunger and `TRIP_MAX` all read `thermNow`.
- Worker **fat reserves**, banked hardest as it cools; **larval diapause** (too
  cold to develop is too cold to be hungry); **dormancy gate** below 10 °C.
- Three winters survived; nest growth stalls each winter and resumes in spring
  with no code that knows what winter is.

**Bug found:** the file already contained a second thermal scalar, `tScale`,
governing different rates on a different curve from the new `thermNow`.
Metabolism ran on one, locomotion on the other. Collapsed to one.

*(Performance work landed around here: `MAX_SUBSTEPS` 40 → 400 — the old value
silently capped speed at 16× — a 64× tier, Insane mode running to an 11 ms
per-frame wall-clock budget, and batched field evaporation, measured 1.17×.)*

## v1.0 — local-nutrition build promoted to main

The branch replaced the global-signal build. No ant reads a colony total:
carbohydrate lives in individual crops and moves by trophallaxis with volume set
by the receiver's empty space; larval hunger propagates nurse-by-nurse; the
queen begs when the larder runs dry.

Branch history leading here: meal-wastage threshold (v0.2), crowding-driven
**excavation** with spoil hauled to a mound (v0.3), larder-per-carry
granularity (v0.4), **brood sorting** by differential diffusion (v0.5).

Brood sorting is worth restating: there are no egg/larva/pupa rooms. An ant
carries an item a random direction by a type-specific distance, and isolated
items are likeliest to be picked up. That balance alone produces concentric
annuli. Pooled over ~19,000 item-observations: egg 34.8 < pupa 65.9 <
larva 70.3 — **PASS**, against a control showing all three at ~5.5 (one
undifferentiated heap).

---

## Recurring lessons

- **Assert every patch.** Silent anchor misses produced plausible-looking
  wrongness at least three times (`tScale`/`thermNow`, `FETCH_R` undefined, a
  batch that discarded six good edits when the seventh failed).
- **Snapshots lie.** A single-sample "0% stalled" hid a 42% time-averaged rate
  for several sessions. Time-averaged probes plus a matched control are the
  standard.
- **Measure the control before blaming the change.** Phase C looked like it
  broke feeding until the control showed the deficit predated it.
- **A mechanism that never fires is not safe, it is broken.** The tip-only fill
  rule and the `undefined` fetch radius both looked like restraint.

## Open items

- Lifetime-horizon (~15-year) matched pair, warm vs seasonal — needs hardware
  that can run it; the sandbox kills runs past ~day 1000.
- Late-year equilibrium population unconfirmed.
- Backfill churn 3–8× over benchmark; believed structural.
- `CELL_COMMIT` delays legitimate shrink-tracking.
- Absent biology: middens and corpse removal, depth/thermal stratification,
  tandem running and nest relocation, alates, pathogens.
