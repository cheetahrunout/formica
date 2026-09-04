# Formica — changelog

A *Lasius niger* colony simulator. Colony-level behaviour must emerge from
individual local rules; no ant may read a colony total. Every claim is measured
against a matched control rather than asserted.

Entries record what changed, the research basis, the measured result, and —
where relevant — what went wrong on the way. Failed attempts are kept because
several of them were more informative than the fix.

---

## v1.9.2 — the dormancy clock, separated from the thermometer

The README has claimed since v1.7 that dormancy here is endogenous: she stops in
late summer because her internal period elapsed, not because it got cold. Run 1
was offered as the evidence — onset invariant to 0.1 °C over fifteen years, 18.2
°C on day-of-year 52.0, interval exactly 365.00.

That was never evidence. The ambient curve is noiseless and exactly annual, so
"195 days after reactivation" and "the day the falling limb reaches 18.2 °C" name
the same date every year forever. `summarise-runs.py` had said as much in a NOTE
since v1.8b and told the reader to go and perturb the thermal year. This entry is
that experiment.

### The harness runs here now

`CLAUDE.md` said there was no JS runtime and probes had to be driven from the
browser console. That is stale: node 22 and bun are both present. `harness.mjs`
extracts the `<script>` from a build, evaluates it inside a function wrapper
behind DOM stubs, and returns live getters into its scope — so a probe is an
ordinary script and a sweep is `xargs -P4`.

Throughput is ~17k ticks/sec against Edge's ~39k, so the browser is still the
faster single run. What the harness buys is parallel matched arms and no
devtools timeout, which is what an experiment with twelve arms needs.

**It is the same simulator, and that is checked, not assumed.** Headless from
seed 20260828 the queen goes dormant on days 417.0, 782.0 and 1147.0 at 18.19 °C
and reactivates on 587.0, 952.0 and 1317.0 — matching, to the sample, the event
lines recorded by run 1 in a real browser.

Two things the harness needed and one it caught:

- Getters, not values, for everything the simulator declares with `let`.
  `reset()` rebuilds `ants`, `brood`, `larder` and `logC` outright, so a
  reference captured before `reset()` keeps pointing at the previous colony and
  reads as plausible, empty data. Found by inspection before it produced a
  number; it is exactly the shape of failure rule 5 is about.
- A `transform` hook, so a legacy control can be given a handle the current
  build has and it does not, without editing a file kept precisely so it cannot
  drift.
- `indexedDB` is deliberately left undefined. The v1.8b log path detects that
  and falls back to the in-memory mirror, which is what the probe reads.

### `CFG.SEASON.YEAR`

The period of the thermal cycle, in sim-days. 365 for every normal run; it
exists as an experimental handle, and it is now written into the run-log header
alongside the season triple, so a rescaled run can never be mistaken for a
normal one.

### The manipulation, and one that would not have worked

Rescaling the environmental year separates the two hypotheses because only one
of them moves:

- an endogenous clock keeps the **interval** and gives up the temperature;
- a thermal gate keeps the **temperature** and gives up the interval.

A pure phase shift does not work, and it is worth recording why, because it was
the other half of the open item. Reactivation in this build is thermally
triggered — chilling arms it, spring warmth fires it — so the whole cycle is
entrained to the curve. Translating the curve translates everything with it and
both hypotheses predict the identical shift. Only rescaling breaks the tie.

### Result — a double dissociation

Six thermal years (200, 250, 300, 365, 450, 550 days) × two builds, seed 20260828
forced in every arm, 1500 sim-days each. Control is `formica-v1.1-legacy.html`,
kept since v1.2 as the thermal-gate predecessor, driven through the same probe.
Founding year excluded throughout: she founds mid-year with a part-season, so her
first onset differs by design. Full table in `logs/thermal-year-sweep-v192.tsv`.

| build | onset temperature | reactivation → onset |
|---|---|---|
| v1.9.2 sand-glass | **17.53 °C spread — 97% of the entire 18 °C annual swing** | **196.0 d in all 18 events, spread 0.0** |
| v1.1 thermal gate | 1.87 °C spread — 10% of the swing | 131–405 d, spread 274 (124% of its own mean) |

Per arm, current build: onset at 11.66 °C under a 300-day year, 18.19 under 365,
22.89 under 450, 24.81 under 550 — she stops progressively earlier in the
thermal year as the year lengthens, because 195 days is 195 days. The control
does the opposite: 9.8–11.9 °C at every year length, with the interval sliding
131 → 148 → 184 → 222 → 268 → 330 days, close to a constant 0.73 of the year.

**The claim survives, and it is now measured rather than asserted.** 196.0 rather
than 195 is the daily sampling grid, not a discrepancy: `queen.glass += dtDay`
with no thermal scaling, so the onset is `GLASS_LEN` sim-days after reactivation
by construction, and the sweep confirms nothing else got in the way.

### Entrainment fails below ~300 days, and it is not free

At 300 days and above the colony locks 1:1 — realised cycle 300.0, 365.0, 450.0,
550.0, exactly the year. At 250 and 200 it cannot: 195 active days plus the
chilling the queen needs do not fit inside the year, so she misses springs. The
realised cycle wanders (341–409 d at 250, 356–398 at 200) and the onset
temperature stops settling at all — 7.28 °C one cycle and 23.41 the next.

The thermal-gate control has no such failure mode. It cannot: it has no period
of its own to mismatch. It locks 1:1 at 200 days as readily as at 550.

That is a cost of the mechanism, and it emerges from it rather than being
scripted anywhere — which is what the project asks of a cost.

---

## Housekeeping — the page deploys itself

`.github/workflows/pages.yml` publishes `formica.html` to GitHub Pages on every
push to `main`. No build step and no version bump: the simulator is one
standalone file, the workflow only copies it to `index.html` (with the two
legacy builds alongside, so they stay reachable as named controls) and uploads
that as the Pages artifact. The header version string identifies the simulator
build, and this changed no simulator code, so it stays at v1.9.1.

Pages must be sourced from *GitHub Actions* in the repository settings; on a
private repo that requires a paid plan, so on the free plan the repo has to be
public for the deploy step to succeed. Until then the workflow runs and fails at
`configure-pages` — a failure that means "Pages is off", not "the workflow is
wrong".

---

## v1.9.1 — two projections over one plane

v1.9 drew the whole world side-on, which meant foragers appeared to fly around
in an air band above the stone. A cross-section and a foraging surface are
different projections and one drawing cannot serve both.

Both regions are now drawn in the projection that suits them, and the operator
picks which is on screen. **Nothing in the physics changed to do this.** It is
still a single 2D grid with a seam through the cap; an ant walking down through
that seam already moved from one region to the other. Only the drawing and the
size of the outworld changed, so both regions always run and switching costs
nothing and misses nothing.

- **Nest view** — side-on, cap down to the bottom of the world, plus 16 rows of
  ground above the cap so the spoil heap is in frame. Scrolls with depth.
- **Outworld view** — the foraging region seen from above, 78 rows deep, so
  distance from the mouth is true ground distance in both axes rather than a
  strip to walk along.

The outworld grew from 22 rows to 78 and food spawns across the whole plane
instead of along one line. That has a real cost: the colony starts more slowly,
because there is much more ground to search. Day 300 gives 18 workers against
35 in the strip version. It recovers — day 600 is 171 workers with 709 digs, day
850 is 332 with 1,920 digs — so this is the foraging problem being genuinely
harder, not a fault.

**The spoil heap, which is the point of keeping sky in the nest view.**

- Haulers aimed at the homing target, which sits *inside* the passage, and the
  seam itself is `OPEN` — so every ant dropped her pellet the moment she entered
  the hole and the heap built up inside it. State 6 now aims at a point out on
  the ground and will not deposit until it is clear of the cap.
- Then it stopped growing at four cells: everyone aimed at one point, those
  cells hit the per-cell cap of 6, and that was that. Spoil is now dropped on
  the least-loaded spot within reach, so it spreads.
- Measured at day 500: 114 cells, 8 rows tall and 16 wide, sitting above the
  cap with none left in the seam — and **625 mound units against 625 digs**, so
  every excavated cell is accounted for on the surface.

**Measured, seed 20260828.** Day 850: 332 workers, 199 brood, queen alive, 2,940
meals, 1,920 digs, 1,883 nest cells at 5.67 per ant, deepest gallery 0.46m below
the cap with 188 rows of soil still under it. 25 ants out on the plane, 4 in the
seam, 303 underground. Integrity unchanged from v1.9: **0 cap cells excavated,
0 nest cells in the outworld**. Both views render and toggle cleanly, verified
by sampling composited pixels in each.

**Still not verified here.** The preview pane reports zero stage height, so the
scrollbar in nest view remains untested; the draw path falls back to rendering
the whole region and was tested that way.

---

## v1.9 — the world is layered, not a disc

The world was a disc of diggable soil floating in open space, and that disc had
a rim. A gallery driven near it broke through into open air, and the colony
ended up living in an open pit rather than a nest — the reported symptom, and
an artefact of the geometry rather than of any rule.

Replaced with three bands: outworld on top, an impenetrable cap, then soil all
the way down. A gallery can now only reach open air through the seam in the
cap, because there is nothing else to break out into.

- `ROCK`, a fourth terrain type. Never diggable, never fillable. `move()` and
  trail sensing both had to learn it, because `SOIL` and `WALL` are the same
  constant and everything solid was previously tested as `=== WALL`.
- `GH` 112 → 260. At ~1cm per cell that is a 2.35m soil column, against the ~2m
  depth reported for mature *L. niger* nests. The founding chamber sits ~10
  cells under the cap and the colony digs down from there.
- The stage scrolls: an 800×1300 canvas in a `max-height` container, so depth is
  followed with a real scrollbar rather than by shrinking the world to fit.
- `SOIL_R` is gone. `NEST_MIN` is gone too, replaced by `nestMin` captured from
  the chamber `buildWorld()` actually cuts — the hard-coded 200 was tied to the
  old disc, and under the new layout it sat **above** the 142-cell founding
  nest, which would have blocked backfilling outright until a colony had dug
  past it.

**Temperature was held fixed on purpose.** The old gradient ramped linearly over
the whole world, so making the world deeper would have silently warmed the
brood. It is now an exponential decay from the surface, calibrated so the
founding chamber sits where it did before: **ambient +2.14 against +2.08**, a
0.06 °C difference. Seasonal *damping* with depth — real soil flattens the
annual swing, which would make a deep nest thermally stable — is a genuinely
interesting mechanism and is deliberately **not** in this change. It feeds
straight into the sand-glass, and bundling it with a geometry change would make
any resulting difference impossible to attribute.

**Three bugs, all found by running it rather than reading it.**

1. **The founding cohort starved holding full crops.** Food spawned anywhere in
   the 110px air column while foragers hug the surface, so they walked
   underneath every patch: 16 patches out, zero meals taken. Food now spawns on
   the ground, in the strip just above the stone.
2. **Every returning forager parked at the mouth and died there.** `entranceY`
   was set one row *above* the cap, on the sky side. A forager in state 5 heads
   for it, arrives, is still not `inNest`, has nothing further to steer towards,
   and stops. The trace is unambiguous: from day 46 all fifteen workers sat in
   state 5 with y pinned between 99 and 111, against the stone, until they died.
   The old world hid this because its entrance point was itself a nest cell, so
   arriving *was* entering. The homing target is now inside the passage.
3. **Every scout set off due east.** The outbound heading is
   `atan2(dy, x - entranceX)`, and at the mouth that is `atan2(0, 0)`, which is
   0. Falls back to whichever way she is already facing.

`ENTRANCE_W` is 4 cells and is a **free parameter**: a pinhole in an 800px wall
is not findable by a deflecting random walk, so this is a funnel width, not a
biological claim about seam size.

**Measured, seed 20260828.** At day 860: 538 workers, 203 brood, queen alive,
4,819 meals, 2,636 digs, 307 fills, 2,481 nest cells at 4.61 per ant, deepest
gallery 52 cells (0.52m) below the cap with 183 rows of soil still beneath it.
Integrity, the whole point of the change: **0 cap cells excavated, 0 nest cells
in the sky band**. 53 ants on the surface against 485 underground. Terrain
renders as three clean bands, verified by sampling the cached canvas.

**Performance.** ~27–36 sim-days/sec against ~46 before, on a world 2.3× larger.
Two mitigations carry it: pheromone evaporation stops at the deepest excavated
row, since fields below a gallery are identically zero and multiplying two
metres of untouched soil by a decay constant every few ticks is pure waste; and
the per-frame field composite covers only rows on screen, which was most of the
render budget once the canvas was 1300px tall. That one has a guard — an
unsettled layout measures zero viewport height, which would clip the visible
band to nothing and draw a blank canvas.

**Not verified here.** The preview pane used for testing reports zero client
height for the stage, so the scrollbar itself could not be exercised; the draw
path falls back to full-world rendering and was tested that way. Confirm in a
real browser that the stage scrolls and follows the nest downward.

**Comparability.** Colonies grown in this world are not comparable with the
v1.8 logs. The existing runs become a separate baseline, not a control.

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
