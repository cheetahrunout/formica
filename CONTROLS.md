# Frozen controls

Three kinds of file in this repo are **deliberately dead**: they are never
developed, fixed, tidied or refactored. They are not unfinished work and they
are not clutter. They are the things current results are measured *against*,
and the only property that makes them useful is that they do not change.

Deleting or "modernising" any of them does not tidy the repo. It silently
converts a measured claim into an assertion.

## The frozen builds

| File | Frozen at | What it is the control for |
|---|---|---|
| `formica-v1.1-legacy.html` | v1.1 | Dormancy is a **pure thermal gate** here — she stops when it gets cold, with no clock. That is what makes it the matched control for the endogenous sand-glass in the current build. The v1.9.2 result (interval invariant at 196.0 d while onset temperature ranges over 97% of the annual swing) is a *comparison* against this file; without it there is only one arm. |
| `formica-global-legacy.html` | v0.1 | The build from **before the governing rule**, in which ants read colony totals directly. The baseline for every "this emerges from local rules" claim — the brood-sorting result in particular, whose control shows all three stages at ~5.5 rather than sorted into annuli. |

Both open in a browser and both load under `harness.mjs`, so a control can be
re-run at any time rather than trusted from a changelog entry.

## The rule

**Do not edit a frozen build.** Not to fix a bug, not to bring it in line with
the current build, not to silence a linter. A bug in a control is part of the
control.

When a control needs a handle the current build has and it does not, rewrite the
source *at load time* instead — `harness.mjs` takes a `transform` for exactly
this, and `probe-v192-thermal-year.js` shows it giving v1.1 the `CFG.SEASON.YEAR`
parameter without the file on disk changing.

The one exception is presentation. Each frozen build carries a `<title>` and a
banner marking it dead, added in the same commit that recorded the SHA-256 of its
`<script>` block before and after, unchanged:

```
formica-v1.1-legacy.html      37afe0be28763d3d…
formica-global-legacy.html    17da37608dfce88b…
```

Re-check with the snippet at the bottom of this file before and after any future
presentation change. If a hash moves, revert — the mark is not worth the control.

> **A trap, found the first time this was done.** The banner's own CSS comment
> contained the literal opening tag of a script element. `harness.mjs` extracts
> a build by matching that tag, so it began reading from inside the comment and
> fed the simulator the wrong text. The page still looked perfect. Only the hash
> check caught it. Never write that tag anywhere in these files outside the real
> one.

## The run logs are fixtures, not leftovers

`summarise-runs.py` is tested against real logs, so the ones in the repo are kept
on purpose and cover paths that are awkward to synthesise:

- `formica-run001-*.tsv` (root) — the 24- and 28-column header paths.
- `logs/formica-run001-manual_reset-day1.tsv` — a run with no live worker ever,
  which the tool must report as unreadable rather than as a colony.
- `logs/thermal-year-v192/` — the twelve arms behind the v1.9.2 dormancy result.
- `logs/thermal-year-sweep-v192.tsv` — the dormancy spells from both builds,
  including the v1.1 control, which has no logger of its own.

`.gitattributes` marks `*.tsv` as binary so a clone cannot rewrite their line
endings; a fixture that comes back different is not a fixture.

## Verifying a frozen build

```sh
python3 - <<'PY'
import io, re, hashlib
for f in ("formica-v1.1-legacy.html", "formica-global-legacy.html"):
    s = io.open(f, encoding="utf8").read()
    m = re.search(r"<scr" + r"ipt>([\s\S]*)</script>", s)
    print(f, hashlib.sha256(m.group(1).encode()).hexdigest()[:16])
PY
```
