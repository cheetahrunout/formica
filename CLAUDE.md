# CLAUDE.md — working context for Formica

Read this before touching anything. It encodes conventions that were learned
expensively; the changelog records what it cost to learn them.

## The one rule

**No ant may read a colony total.** Colony-level behaviour must emerge from
individual local rules. One shared `WORKER_PROGRAM`, one `QUEEN_PROGRAM`.
`colony.sugar`, `colony.larvae` etc. are *derived readouts for the UI only* —
nothing in the model may read them back. If a fix requires an ant to know a
global, the fix is wrong.

Costs of "wrong" strategies must emerge from mechanics. Never script a penalty.

## Architecture

Single file, `formica.html`. No dependencies, no build step. Open it directly.

- Structure-of-arrays for agents (`ants`, `brood`), fixed capacity
- Occupancy grid rebuilt per tick for O(1) neighbour queries
- Cached shortlists (`hungryList`, `sortList`, brood centroid) refreshed every
  15 ticks
- **Two clocks**: motion in real seconds, development in sim-days via
  `DAY_SECONDS`. Keep them decoupled.
- `thermNow` is the single thermal scalar. Everything temperature-dependent
  multiplies by it. There must never be a second one — there was once
  (`tScale`), governing different rates on a different curve, and it went
  unnoticed for a long time.

Worker states: 0 nest, 1 brood-carry, 2 explore, 3 follow trail, 4 recall
memory, 5 return, 6 haul spoil, 7 seek dig face, 8 fetch meal, 9 deliver meal.

## Testing

Headless harness pattern — extract and eval the script with a stubbed DOM:

```js
const src = fs.readFileSync('formica.html','utf8').match(/<script>([\s\S]*)<\/script>/)[1];
// stub document/ctx/performance, then: eval(src + probeString)
```

~10,000 ticks/sec. Probes are throwaway; `.gitignore` covers `*.out`/`*.log`.

**Non-negotiables, each learned the hard way:**

1. **Assert every patch.** A `str_replace`/regex that silently misses produces
   plausible-looking wrongness, not an error. This has caused at least three
   real bugs. If a batch asserts, note that a failed assert discards the whole
   batch — re-apply the good hunks.
2. **Time-average, never snapshot.** A single-sample "0% stalled" hid a 42%
   real rate for several sessions.
3. **Run the matched control before blaming your change.** Brood sorting looked
   like it broke feeding until the control showed the deficit predated it.
4. **A mechanism that never fires is broken, not safe.** Two separate features
   looked like restraint and were bugs.
5. **Verify against the actual file text.** Assumptions about what's in the
   file have been wrong repeatedly.

## Research posture

Biology claims get web-searched and cited in source comments. Confidence is
marked: literature-backed vs `[C]` keeper-consensus. Research before building —
it has overturned planned designs more than once (the endogenous sand-glass
replaced a thermal gate; a planned queen "strain" accumulator was discarded
after finding ant queens break the fecundity–longevity tradeoff).

Invented constants are labelled as free parameters in source and swept, not
defended.

## Housekeeping

- Bump the version string in the header, and add a `CHANGELOG.md` entry, with
  every change. Record failed attempts — they're often the informative part.
- Extend the TSV run logging whenever a new measurable quantity appears. Don't
  ask first.
- Keep legacy builds as named controls, relabelled so nobody mistakes them for
  current.

## Current state (v1.8)

Emergent and measured: local trophallactic nutrition; nest volume ~3 cells/ant
across a 15× population range; brood annuli (egg 34.8 < pupa 65.9 < larva 70.3,
~19k observations, control shows all ~5.5); endogenous dormancy stopping at
18.2 °C some 60 days before it turns cold.

## Open items

- **Lifetime (~15-year) matched pair, warm vs seasonal** — the experiment the
  model owes. Run 1 (v1.7) reached day 12705, so the ~day-1000 wall is gone, but
  it is not the pair: the colony went extinct on day 6531.6 and half the file is
  post-extinction padding from the v1.8 diapause bug. Rerun on v1.8.
- No JS runtime on this machine (`node`/`bun`/`deno` absent). The eval harness
  above cannot run here; drive `step()` in the browser instead — open
  `formica.html` and paste `probe-v18-diapause.js` into the console. Edge does
  ~39k ticks/sec, about 4x the documented headless rate.
- Runs are reproducible: `reset(seed)` forces the PRNG stream before
  `buildWorld()`, and the seed is written into the log header. Use it for every
  matched control. Setting `seed` after `reset()` returns is too late.
- Run 1 contradicts the ~3 cells/ant claim below: ~3 holds only for years 0-2,
  steady state is 5-6, and after the population peak it ratchets to 86 as the
  nest fails to shrink. The `CELL_COMMIT` item is understated.
- Dormancy onset in run 1 is invariant to 0.1 °C across 15 years (18.2 °C,
  doy 52.0, interval exactly 365.00). The ambient curve is noiseless and exactly
  annual, so an endogenous 365-day clock and a thermal gate are observationally
  identical in that run — it is not evidence for the sand-glass. Phase-shift or
  rescale the thermal year to tell them apart.
- Late-year equilibrium population unconfirmed
- Backfill churn 3–8× above the ~2.5% traced-sediment benchmark; believed
  structural (model lacks middens, caches, resting chambers)
- `CELL_COMMIT` delays legitimate shrink-tracking
- Absent biology: middens/corpse removal, depth stratification, tandem running
  and relocation, alates, pathogens

`docs/session-2026-08-28-transcript.txt` has the full reasoning history if you
need to know *why* something is the way it is.
