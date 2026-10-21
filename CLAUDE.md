# CLAUDE.md — working context for Formica

Conventions learned expensively. `CHANGELOG.md` records what each one cost —
read that entry before overriding the rule it produced.

## The one rule

**No ant may read a colony total.** Colony behaviour must emerge from local
rules. One shared `WORKER_PROGRAM`, one `QUEEN_PROGRAM`. `colony.sugar`,
`colony.larvae` etc. are *derived readouts for the UI only* — nothing in the
model may read them back. If a fix requires an ant to know a global, the fix is
wrong. Costs of "wrong" strategies must emerge from mechanics; never script a
penalty.

Not only sums: v1.8 deleted `broodHalted()`, which had every larva read the
queen's own state at any distance. Environment is fair game — `ambient` and
`tempAt()` are read by everyone, queen included.

## Architecture

Single file, `formica.html`. No dependencies, no build step. Open it directly.

- **Two clocks**: motion in real seconds, development in sim-days via
  `DAY_SECONDS`. Keep them decoupled.
- `thermNow` is the single thermal scalar; everything temperature-dependent
  multiplies by it. Never add a second — `tScale` once did, on a different
  curve, and hid for a long time. Same cost in v1.8, where `termRate()` had to
  be hoisted to module scope so queen and larvae share one curve.
- Worker states: 0 nest, 1 brood-carry, 2 explore, 3 follow trail, 4 recall
  memory, 5 return, 6 haul spoil, 7 seek dig face, 8 fetch meal, 9 deliver meal.
- **The world is three bands (v1.9)**: outworld on top, an impenetrable `ROCK`
  cap, then soil to the bottom of a 316-row world. The only way through is the
  seam at `entranceX`. Note `SOIL` and `WALL` are the same constant, so anything
  testing solidity as `=== WALL` will walk straight through stone — test both.
  `entranceY` must stay INSIDE the passage: put it on the sky side and homing
  foragers arrive, are still not `inNest`, and park at the mouth until they die.
- **One plane, two projections (v1.9.1).** The nest is drawn side-on and the
  outworld from above; `view` selects which, `viewRows()` gives the row band.
  Both always simulate — there is only one grid, and the seam is where an ant
  crosses between regions. Anything aimed at the entrance from below will act
  inside the seam, which is `OPEN`: that is how spoil ended up heaped in the
  hole instead of on the surface.

## Testing

Two ways, and they agree — checked, not assumed (v1.9.2).

**Headless (`harness.mjs`, node 22 or bun).** `load(file, expose, transform)`
pulls the `<script>` out of a build, evaluates it in a function wrapper behind
DOM stubs, and hands back live getters into its scope. ~17k ticks/sec, so a
single run is slower than the browser — what it buys is parallel matched arms
(`xargs -P4`) and no devtools timeout. `probe-v192-thermal-year.js` is the
worked example, and it drives `formica-v1.1-legacy.html` through the same code
path as the current build.

- **Getters, not values, for every `let`.** `reset()` rebuilds `ants`, `brood`,
  `larder` and `logC` outright; a reference captured before it keeps pointing at
  the previous colony and reads as plausible, empty data.
- `transform` rewrites the source before eval — that is how a legacy control
  gets a handle it does not have, without editing a file kept so it cannot
  drift. Assert inside it.
- `indexedDB` is left undefined on purpose: the log path detects that and falls
  back to the in-memory mirror, which is what a probe reads.

**Browser.** Open `formica.html`, set `running=false`, paste a probe into the
console. Edge does ~39k ticks/sec (~46 sim-days/sec) and tests the real
environment rather than a stub. `probe-v18-diapause.js` is the worked example
and self-chunks so it never trips a devtools timeout.

`reset(seed)` forces the PRNG *before* `buildWorld()` — assigning `seed`
afterwards is too late. The seed goes into the log header, so any logged run
replays. Use a forced seed for every matched control.

Probes are throwaway; `.gitignore` covers `*.out`, `*.log`, `*.tsv`.

**Run logs save themselves (v1.8b).** A download is not a save: the old path
fired an anchor click and cleared `runLog` on the next line, so a blocked
download lost the run silently. Now four tiers — an in-memory mirror written
synchronously before anything can fail, IndexedDB, a granted folder, then a
download as last resort. For an unattended night, grant the folder: the
`saving:` readout in the control strip names the live tier, and *session only*
means a reload will cost you the pile.

`summarise-runs.py` triages a pile of logs into one line per run plus detail
only where a flag trips. The flags encode failures this project has shipped, so
a flag means go and look. Run it before reading any raw TSV. It groups dormancy
timing by `CFG.SEASON.YEAR` and will name the invariant — interval or
temperature — when a pile spans more than one thermal year. Stdlib only, and
3.8+: it silently required 3.12 until v1.9.2, through one nested-quote f-string.

**Non-negotiables, each learned the hard way:**

1. **Assert every patch.** A `str_replace`/regex that silently misses produces
   plausible-looking wrongness, not an error — three real bugs so far, plus two
   near-misses in one v1.8 session from mangled escaping. A failed assert
   discards the whole batch; re-apply the good hunks.
2. **Time-average, never snapshot.** A single-sample "0% stalled" hid a 42% real
   rate for several sessions.
3. **Run the matched control before blaming your change.** Brood sorting looked
   like it broke feeding until the control showed the deficit predated it.
4. **A mechanism that never fires is broken, not safe.** Three now: two features
   that looked like restraint, and v1.7's orphaned brood, which could neither
   develop nor die for 6,853 days.
5. **Verify against the file text — and against a run.** Assumptions about
   what's in the file have been wrong repeatedly, and so have assumptions about
   what the code does with it. v1.8's first larval-chill fix was derived from
   the `tempAt` expression and was wrong: nurses hold brood ~4 °C *above*
   ambient. The run caught it; the reasoning did not.

## Research posture

Biology claims get web-searched and cited in source comments, marked
literature-backed vs `[C]` keeper-consensus. Research before building — it has
overturned planned designs more than once. Invented constants are labelled free
parameters in source and swept, not defended.

## Housekeeping

**The Field Manual is the long-form reference and it is not in this repo.** It
lives as a published artifact — *Formica Field Manual*, currently v1.9.2 — and
covers the governing constraint, architecture, all fifteen subsystems, method,
measured results with their controls, free parameters and open items, at far
more length than anything here. Read it before redesigning a subsystem, and
update it in the same session you change one, or it silently goes stale: it sat
at v1.8a through two world-geometry versions. Find it with `/artifacts`, or the
gallery at claude.ai/code/artifacts.

- Bump the header version string and add a `CHANGELOG.md` entry with every
  change. Record failed attempts — often the informative part.
- Extend the TSV run logging whenever a new measurable appears. Don't ask first.
- **Frozen controls: never develop, fix or tidy them.** `formica-v1.1-legacy.html`
  and `formica-global-legacy.html` are dead on purpose and carry a banner saying
  so; a bug in a control is part of the control. Need a handle one lacks? Rewrite
  at load time with the harness `transform`, never on disk. Presentation-only
  edits must leave the `<script>` hash unchanged — and must not contain the
  literal opening script tag, which the harness matches on. `CONTROLS.md` has the
  policy, the hashes and the check.

## Current state (v1.9.2)

Emergent and measured: local trophallactic nutrition; brood annuli (egg 34.8 <
pupa 65.9 < larva 70.3, ~19k observations; control shows all ~5.5).

Dormancy onset is endogenous, and that is now *measured* rather than inferred
from an annual curve under which it was not identifiable. Rescale
`CFG.SEASON.YEAR` across 200–550 days and the reactivation→onset interval holds
at 196.0 in all 18 steady-state events while the onset temperature moves over
97% of the annual swing; the v1.1 thermal-gate control does the exact opposite
(1.87 °C, interval 131→405). Below ~300 days the colony cannot entrain — 195
active days plus the required chilling do not fit in the year — and at 200 it
fails to found at all. That failure mode is specific to having a clock; the
control locks 1:1 at every year length. The cost is not a penalty of its own:
where the colony entrains, the time-weighted active fraction sits on 195/year
and population tracks it; where it does not, a missed spring costs a whole
year's activity and population tracks *that*.

Nest volume is **not** the ~3 cells/ant previously claimed here — run 1 gives ~3
only in years 0–2, 5–6 at steady state, ratcheting to 86 after the population
peak as the nest fails to shrink with the colony.

## Open items

- **Lifetime (~15-year) matched pair, warm vs seasonal** — the experiment the
  model owes. Run 1 reached day 12705, so the ~day-1000 wall is gone, but it is
  not the pair: extinction on day 6531.6, half the file post-extinction padding
  from the v1.8 bug. Rerun on v1.8a, the first build where both arms can share a
  seed.
- **The thermal-year sweep is not a lifetime result.** 1500 days is 5 cycles at
  a 300-day year and 2.7 at 550, so the arms are not matched on seasons lived
  and none is near equilibrium. The population ordering it produces is a duty
  cycle (`GLASS_LEN` is a fixed 195 days, so a shorter year is more waking time
  per calendar day), *not* an optimum at 300 days — do not repeat it as one.
- Nest-size ratchet: population halved over 1530 days while cells retained 85%.
  `CELL_COMMIT` shrink-lag is the suspect and is understated.
- `LARVA_WINTER_DRAIN` (0.004/day, v1.8) not yet swept. Before it, diapausing
  larvae were free for ~170 days a year — a suspect in `fatMean` sitting at its
  1.600 cap in 26% of run-1 samples.
- Late-year equilibrium population unconfirmed.
- Backfill churn 3–8× above the ~2.5% traced-sediment benchmark; believed
  structural (no middens, caches, resting chambers).
- Absent biology: middens/corpse removal, depth stratification, tandem running
  and relocation, alates, pathogens.
