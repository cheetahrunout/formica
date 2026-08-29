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

## Testing

No JS runtime here (`node`/`bun`/`deno` absent). Drive `step()` in the browser:
open `formica.html`, set `running=false`, paste a probe into the console. Edge
does ~39k ticks/sec (~46 sim-days/sec), ~4× the old headless rate, and tests the
real environment rather than a stub. `probe-v18-diapause.js` is a worked example
and self-chunks so it never trips a devtools timeout. If a runtime appears, the
original harness still works: extract the `<script>`, stub document/ctx/
performance, `eval(src + probe)`.

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
a flag means go and look. Run it before reading any raw TSV.

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

- Bump the header version string and add a `CHANGELOG.md` entry with every
  change. Record failed attempts — often the informative part.
- Extend the TSV run logging whenever a new measurable appears. Don't ask first.
- Keep legacy builds as named controls, relabelled so nobody mistakes them for
  current.

## Current state (v1.8b)

Emergent and measured: local trophallactic nutrition; brood annuli (egg 34.8 <
pupa 65.9 < larva 70.3, ~19k observations; control shows all ~5.5).

Nest volume is **not** the ~3 cells/ant previously claimed here — run 1 gives ~3
only in years 0–2, 5–6 at steady state, ratcheting to 86 after the population
peak as the nest fails to shrink with the colony.

## Open items

- **Lifetime (~15-year) matched pair, warm vs seasonal** — the experiment the
  model owes. Run 1 reached day 12705, so the ~day-1000 wall is gone, but it is
  not the pair: extinction on day 6531.6, half the file post-extinction padding
  from the v1.8 bug. Rerun on v1.8a, the first build where both arms can share a
  seed.
- **Dormancy may not be endogenous.** Run 1's onset is invariant to 0.1 °C over
  15 years (18.2 °C, doy 52.0, interval exactly 365.00), but the ambient curve
  is noiseless and exactly annual — so an endogenous clock and a thermal gate
  are observationally identical there. Phase-shift or rescale the thermal year
  to tell them apart. Cheap, and it tests a headline claim.
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
