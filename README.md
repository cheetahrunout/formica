# Formica

A biologically grounded *Lasius niger* (black garden ant) colony simulator, in a
single self-contained HTML file. Open `formica.html` in a browser — no build
step, no dependencies.

## The rule the project is built around

**No ant may read a colony total.** Colony-level behaviour has to emerge from
individual local rules, or it doesn't count. There is one shared worker program
and one queen program; everything else follows.

That constraint is what makes the results interesting. The nest sizes itself,
the brood sorts itself into rings, and a colony denied a winter underperforms —
none of it scripted, all of it measured against a matched control.

## What emerges

- **Nutrition** — carbohydrate lives in individual crops and moves by
  trophallaxis, with transfer volume set by the *receiver's* empty space. Larval
  hunger propagates nurse-by-nurse. The queen begs when the larder runs dry.
- **Nest volume** — ants dig when crowded and backfill when space stands
  unused. Volume tracks population at ~3 cells per ant across a 15× range,
  because enlarging the nest spreads everyone out and stops the digging.
- **Brood sorting** — no egg/larva/pupa rooms. An ant carries an item a random
  direction by a distance that depends only on what it is, and isolated items
  are likeliest to be picked up. Concentric annuli fall out of that balance:
  egg 34.8 < pupa 65.9 < larva 70.3, pooled over ~19,000 observations, against
  a control showing all three at ~5.5.
- **The year** — dormancy is endogenous, not thermal. The queen stops in late
  summer at ~18 °C because her internal period elapsed, ~60 days before it turns
  cold. Chilling arms reactivation; spring warmth triggers it. Winter cannot be
  skipped, only spent warm.

## Files

| | |
|---|---|
| `formica.html` | current build (v1.7) |
| `CHANGELOG.md` | version history, research basis, measured results, and the failed attempts |
| `lasius_niger_knowledge_base.md` | biology reference the design draws on |
| `formica-v1.1-legacy.html` | thermal-gate predecessor, kept as the control the endogenous-cycle build was measured against |
| `formica-global-legacy.html` | original global-signal build, kept as the baseline |

## Long runs

Marathon mode is on by default. Every run logs itself — a 24-column TSV sample
every 10 sim-days plus event lines for dormancy, reactivation and queen death.
When a colony goes extinct the log downloads and a fresh run starts, so a
machine left overnight produces one file per colony lifetime.

Insane mode runs to a wall-clock budget per frame rather than a fixed
multiplier, so throughput scales with the hardware.

## On the numbers

Claims here are measured, not asserted, and the changelog records where they
failed. Two worth knowing up front: backfill churn sits 3–8× above the only
quantified benchmark I could find (~2.5% of excavated sediment redeposited,
traced in *Pogonomyrmex badius*), and the size of the warm-winter penalty
depends on a free parameter that no study pins down for an ant — the sweep is
in the changelog, including the case where the effect reverses.
