#!/usr/bin/env python3
"""
summarise-runs.py — triage a pile of formica run logs into something readable.

    python summarise-runs.py                 # every *.tsv beside the script
    python summarise-runs.py logs/           # a directory
    python summarise-runs.py a.tsv b.tsv     # named files
    python summarise-runs.py --detail        # add per-run checkpoint tables
    python summarise-runs.py --json out.json # machine-readable alongside

Marathon mode writes one file per colony lifetime, so a night's run is a pile.
Reading them raw is not practical. This produces three tiers:

    1. ONE LINE PER RUN     — the whole pile at a glance
    2. FLAGGED RUNS         — detail only where a check tripped
    3. ACROSS ALL RUNS      — aggregates, and dormancy-timing variance

The flags are not generic anomaly detection. Each one encodes a failure this
project has actually shipped, so a flag means "go and look", not "unusual":

    PADDING     rows logged after the colony died (v1.7 marathon could not
                terminate, and 49% of run 1 was post-extinction padding)
    IMMORTAL    brood present but no emergence, death or consumption for a
                long stretch — the v1.7 orphaned-brood bug, 6853 days
    FROZEN      a cumulative counter stopped moving while ants were alive
    BUDGET      laid != emerged + bDied + bEaten + alive; brood unaccounted for
    RATCHET     cells/ant climbed far above its early-run value; the nest
                failed to shrink with the colony
    FATCAP      mean worker fat sat at its cap for most of the run, i.e. the
                starvation mechanism was effectively idle (rule 4)
    STALL       time-weighted stalled-larva fraction above threshold
    NODIAP      no larva ever entered diapause in a seasonal run
    LARDER      workers starving with a stocked larder they never drew on
    SHORT       colony died before it established

All rates here are time-weighted, never snapshots (rule 2).
Requires only the standard library.
"""

import sys, os, glob, json, re, statistics
from collections import defaultdict

# ---------------------------------------------------------------- thresholds
FATCAP_VAL   = 1.60   # CFG.FAT_MAX; "at cap" means within 0.5% of it
FATCAP_FRAC  = 0.50   # flag if mean fat sits at cap in more than half of samples
STALL_FRAC   = 0.25   # flag time-weighted stalled/larvae above this
RATCHET_MULT = 3.0    # flag if end cells/ant exceeds early-run median by this
IMMORTAL_DAYS = 400   # brood alive, nothing happening to it, for this long
FROZEN_DAYS   = 400   # a counter not moving while pop > 0
SHORT_DAYS    = 400   # colony dead before this is a failed founding

CUM = ["emerged", "died", "digs", "fills", "meals", "laid", "bDied", "bEaten"]


# ------------------------------------------------------------------ parsing
def parse(path):
    """Read one run log. Returns a dict, or None if the file is not one."""
    try:
        raw = open(path, encoding="utf8", errors="replace").read().splitlines()
    except OSError as e:
        return {"path": path, "error": str(e)}

    head, events, rows, cols = None, [], [], None
    for line in raw:
        if not line.strip():
            continue
        if line.startswith("#"):
            body = line[1:].strip()
            if body.startswith("formica run"):
                head = body
            elif "\t" in body:
                d, _, tag = body.partition("\t")
                try:
                    events.append((float(d), tag.strip()))
                except ValueError:
                    pass
            continue
        parts = line.split("\t")
        if cols is None:
            if parts[0] == "day":
                cols = parts
            continue
        if len(parts) != len(cols):
            continue
        try:
            rows.append([float(x) for x in parts])
        except ValueError:
            continue

    if cols is None or len(rows) < 2:
        return {"path": path, "error": "no usable data rows"}

    run = seed = None
    reason = "?"
    if head:
        m = re.search(r"formica run\s+(\d+)", head)
        if m: run = int(m.group(1))
        m = re.search(r"seed\s+(-?\d+)", head)
        if m: seed = int(m.group(1))
        m = re.search(r"ended:\s*(.*?)\s+at day", head)
        if m: reason = m.group(1).strip()

    return {"path": path, "run": run, "seed": seed, "reason": reason,
            "partial": reason == "in progress" or "-partial" in os.path.basename(path),
            "cols": cols, "I": {c: i for i, c in enumerate(cols)}, "rows": rows,
            "events": events, "error": None}


# ------------------------------------------------------------------ helpers
def tw_mean(rows, day_i, get):
    """Time-weighted mean of get(row) over the sample interval. Rule 2."""
    num = den = 0.0
    for a, b in zip(rows, rows[1:]):
        dt = b[day_i] - a[day_i]
        if dt <= 0:
            continue
        num += (get(a) + get(b)) / 2 * dt
        den += dt
    return num / den if den else 0.0


def tw_ratio(rows, day_i, top, bot):
    """Time-weighted sum(top)/sum(bot) — not the mean of per-row ratios."""
    n = d = 0.0
    for a, b in zip(rows, rows[1:]):
        dt = b[day_i] - a[day_i]
        if dt <= 0:
            continue
        n += (top(a) + top(b)) / 2 * dt
        d += (bot(a) + bot(b)) / 2 * dt
    return n / d if d else 0.0


def last_change(rows, i):
    """Day of the final change in a monotone counter."""
    k = 0
    for j in range(1, len(rows)):
        if rows[j][i] != rows[j - 1][i]:
            k = j
    return rows[k][0]


# ---------------------------------------------------------------- analysis
def analyse(f):
    if f.get("error"):
        return f
    I, R = f["I"], f["rows"]
    day, pop = I["day"], I["pop"]
    has = lambda c: c in I
    g = lambda c: (lambda r: r[I[c]]) if has(c) else (lambda r: 0.0)

    a = dict(f)
    a["days"] = R[-1][day]
    a["samples"] = len(R)
    a["cols_n"] = len(f["cols"])

    live = [r for r in R if r[pop] > 0]
    a["live"] = bool(live)
    if not live:
        a["error"] = "colony never had a live worker"
        return a

    a["last_alive"] = live[-1][day]
    a["extinct"] = None if live[-1] is R[-1] else a["last_alive"]
    a["padding_days"] = round(a["days"] - a["last_alive"], 1) if a["extinct"] else 0.0

    pk = max(R, key=lambda r: r[pop])
    a["peak_pop"], a["peak_day"] = int(pk[pop]), pk[day]
    a["end_pop"] = int(R[-1][pop])

    # --- queen ---------------------------------------------------------
    a["queen_death"] = next((d for d, t in f["events"] if "QUEEN DIED" in t), None)
    a["dormancies"] = [(d, float(m.group(1)))
                       for d, t in f["events"] if "DORMANCY" in t
                       for m in [re.search(r"at ([\d.]+)C", t)] if m]
    a["reactivations"] = [(d, float(m.group(1)))
                          for d, t in f["events"] if "REACTIV" in t
                          for m in [re.search(r"at ([\d.]+)C", t)] if m]

    # --- vitals (time-weighted over live rows) --------------------------
    a["fat_mean"] = tw_mean(live, day, g("fatMean"))
    fats = [r[I["fatMean"]] for r in live] if has("fatMean") else []
    a["fat_at_cap"] = (sum(1 for x in fats if x >= FATCAP_VAL * 0.995) / len(fats)) if fats else 0.0
    a["stall"] = tw_ratio(live, day, g("stalled"), g("larvae"))
    a["cpa_end"] = R[-1][I["cPerAnt"]] if has("cPerAnt") and a["end_pop"] else None

    # cells/ant early baseline: the first third of the live run, populated rows
    early = [r for r in live if r[day] <= a["last_alive"] / 3 and r[pop] > 5]
    a["cpa_early"] = statistics.median(
        [r[I["cells"]] / r[pop] for r in early]) if early and has("cells") else None
    # Measured at the last sample where the colony was still a colony. The final
    # rows of a dying run give cells/pop ratios in the hundreds, which says
    # nothing about the nest and swamps the real ratchet.
    floor = max(5, a["peak_pop"] * 0.10)
    substantial = [r for r in live if r[pop] >= floor]
    a["cpa_ref_pop"] = int(substantial[-1][pop]) if substantial else None
    a["cpa_ref_day"] = substantial[-1][day] if substantial else None
    a["cpa_last"] = (substantial[-1][I["cells"]] / substantial[-1][pop])         if substantial and has("cells") else None

    # --- recruitment budget --------------------------------------------
    a["budget"] = None
    if all(has(c) for c in ("laid", "bDied", "bEaten", "eggs", "larvae", "pupae")):
        e = R[-1]
        alive_brood = e[I["eggs"]] + e[I["larvae"]] + e[I["pupae"]]
        acct = e[I["emerged"]] + e[I["bDied"]] + e[I["bEaten"]] + alive_brood
        a["budget"] = {"laid": e[I["laid"]], "accounted": acct,
                       "residual": e[I["laid"]] - acct}
    if has("emerged") and has("laid") and R[-1][I["laid"]]:
        a["survival"] = R[-1][I["emerged"]] / R[-1][I["laid"]]
    else:
        a["survival"] = None

    a["diap_max"] = max((r[I["diap"]] for r in R), default=None) if has("diap") else None
    a["seasonal"] = len(a["dormancies"]) > 0

    # --- flags ----------------------------------------------------------
    F = []
    if a["padding_days"] > 100:
        F.append(("PADDING", f"{a['padding_days']:.0f} d logged after extinction"))

    for c in CUM:
        if not has(c):
            continue
        lc = last_change(R, I[c])
        if a["last_alive"] - lc > FROZEN_DAYS and R[-1][I[c]] > 0:
            F.append(("FROZEN", f"{c} stopped at day {lc:.0f}, {a['last_alive'] - lc:.0f} d before the last ant died"))

    # brood alive but nothing happening to it
    if has("larvae"):
        quiet_from = None
        worst = 0.0
        for j in range(1, len(R)):
            broodn = R[j][I["eggs"]] + R[j][I["larvae"]] + R[j][I["pupae"]]
            moved = any(R[j][I[c]] != R[j - 1][I[c]]
                        for c in ("emerged", "bDied", "bEaten") if has(c))
            if broodn > 0 and not moved:
                if quiet_from is None:
                    quiet_from = R[j - 1][0]
                worst = max(worst, R[j][0] - quiet_from)
            else:
                quiet_from = None
        if worst > IMMORTAL_DAYS:
            F.append(("IMMORTAL", f"brood present but static for {worst:.0f} d"))

    if a["budget"] and abs(a["budget"]["residual"]) > 0.5:
        F.append(("BUDGET", f"{a['budget']['residual']:+.0f} brood unaccounted for"))
    if a["fat_at_cap"] > FATCAP_FRAC:
        F.append(("FATCAP", f"mean fat at cap in {a['fat_at_cap'] * 100:.0f}% of live samples"))
    if a["stall"] > STALL_FRAC:
        F.append(("STALL", f"{a['stall'] * 100:.0f}% of larva-days stalled"))
    if (a["cpa_early"] and a["cpa_last"]
            and a["cpa_last"] > a["cpa_early"] * RATCHET_MULT):
        F.append(("RATCHET", f"cells/ant {a['cpa_early']:.1f} -> {a['cpa_last']:.1f}"))
    if a["seasonal"] and a["diap_max"] == 0:
        F.append(("NODIAP", "seasonal run, no larva ever entered diapause"))
    if has("larderU") and has("fatMean"):
        bad = [r for r in live if r[I["larderU"]] > 0 and r[I["fatMean"]] < 1.0]
        if len(bad) > 2:
            F.append(("LARDER", f"{len(bad)} samples starving on a stocked larder "
                                f"(max {max(r[I['larderU']] for r in bad):.0f} units)"))
    if a["extinct"] and a["extinct"] < SHORT_DAYS:
        F.append(("SHORT", f"dead by day {a['extinct']:.0f}"))

    a["flags"] = F
    return a


def checkpoints(a, n=8):
    """A few evenly spaced samples across the live part of the run."""
    I, R = a["I"], a["rows"]
    live = [r for r in R if r[I["pop"]] > 0] or R
    step = max(1, (len(live) - 1) // (n - 1))
    picks = live[::step][:n]
    if picks[-1] is not live[-1]:
        picks.append(live[-1])
    return picks


# ------------------------------------------------------------------ output
def fmt(v, spec="", dash="-"):
    return dash if v is None else format(v, spec)


def _tally(flags):
    t = {}
    for k, _ in flags:
        t[k] = t.get(k, 0) + 1
    return t


def report(runs, detail=False):
    # An in-progress checkpoint is a snapshot of a colony still running, not
    # a colony. Counting it would double every run that has one on disk and
    # drag the lifespan and peak-population aggregates down.
    part = [a for a in runs if not a.get("error") and a.get("partial")]
    ok = [a for a in runs if not a.get("error") and not a.get("partial")]
    bad = [a for a in runs if a.get("error")]
    out = []
    P = out.append

    P("FORMICA RUN SUMMARY")
    P(f"{len(runs)} file(s), {len(ok)} completed run(s)"
      + (f", {len(part)} in progress" if part else "")
      + (f", {len(bad)} unreadable" if bad else ""))
    for a in part:
        P("  in progress: %s  run %s  day %.0f, pop %s"
          "  (excluded from the aggregates below)"
          % (os.path.basename(a["path"]), a.get("run"),
             a.get("days", 0), a.get("end_pop", 0)))
    P("All rates time-weighted. Flags mark known failure modes; see script header.")
    P("")

    # ---- tier 1 -------------------------------------------------------
    P("=" * 118)
    P("PER RUN")
    P("=" * 118)
    hdr = (f"{'file':<26} {'run':>3} {'seed':>11} {'days':>7} {'peak':>5} "
           f"{'@day':>7} {'extinct':>7} {'queen':>7} {'emrg':>6} {'surv':>5} "
           f"{'c/ant':>10} {'stall':>5} {'fat@cap':>7}  flags")
    P(hdr)
    P("-" * 118)
    for a in sorted(ok, key=lambda x: (x["run"] is None, x["run"], x["path"])):
        cpa = "-"
        if a["cpa_early"] and a["cpa_last"]:
            cpa = f"{a['cpa_early']:.1f}->{a['cpa_last']:.0f}"
        P(f"{os.path.basename(a['path'])[:26]:<26} "
          f"{fmt(a['run'], 'd'):>3} {fmt(a['seed'], 'd'):>11} "
          f"{a['days']:>7.0f} {a['peak_pop']:>5d} {a['peak_day']:>7.0f} "
          f"{fmt(a['extinct'], '.0f'):>7} {fmt(a['queen_death'], '.0f'):>7} "
          f"{fmt(a['rows'][-1][a['I']['emerged']], '.0f'):>6} "
          f"{(f'{a['survival'] * 100:.0f}%' if a['survival'] else '-'):>5} "
          f"{cpa:>10} "
          f"{a['stall'] * 100:>4.0f}% {a['fat_at_cap'] * 100:>6.0f}%  "
          + ",".join(f"{k}x{n}" if n > 1 else k
                      for k, n in _tally(a["flags"]).items()))
    for a in bad:
        P(f"{os.path.basename(a['path'])[:26]:<26}  !! {a['error']}")
    P("")

    # ---- tier 2 -------------------------------------------------------
    flagged = [a for a in ok if a["flags"]]
    P("=" * 118)
    P(f"FLAGGED RUNS ({len(flagged)} of {len(ok)})")
    P("=" * 118)
    if not flagged:
        P("None. No run tripped a known failure mode.")
    for a in flagged:
        P("")
        P(f"--- {os.path.basename(a['path'])}  (run {fmt(a['run'], 'd')}, "
          f"seed {fmt(a['seed'], 'd')}, ended: {a['reason']})")
        for k, why in a["flags"]:
            P(f"    {k:<9} {why}")
        if a["budget"]:
            b = a["budget"]
            P(f"    budget    laid {b['laid']:.0f} vs accounted {b['accounted']:.0f} "
              f"(residual {b['residual']:+.0f})")
    P("")

    # ---- optional detail ----------------------------------------------
    if detail:
        P("=" * 118)
        P("CHECKPOINTS")
        P("=" * 118)
        for a in ok:
            I = a["I"]
            P("")
            P(f"--- {os.path.basename(a['path'])}")
            P(f"    {'day':>8} {'amb':>6} {'pop':>6} {'cells':>7} {'c/ant':>7} "
              f"{'eggs':>5} {'larv':>5} {'diap':>5} {'stall':>5} {'fat':>6} {'larder':>6}")
            for r in checkpoints(a):
                cell = r[I["cells"]] if "cells" in I else 0
                P(f"    {r[0]:>8.0f} {r[I['amb']]:>6.1f} {r[I['pop']]:>6.0f} "
                  f"{cell:>7.0f} "
                  f"{(cell / r[I['pop']] if r[I['pop']] else 0):>7.1f} "
                  f"{r[I['eggs']]:>5.0f} {r[I['larvae']]:>5.0f} "
                  f"{(r[I['diap']] if 'diap' in I else 0):>5.0f} "
                  f"{r[I['stalled']]:>5.0f} {r[I['fatMean']]:>6.3f} "
                  f"{r[I['larderU']]:>6.0f}")
        P("")

    # ---- tier 3 -------------------------------------------------------
    P("=" * 118)
    P("ACROSS ALL RUNS")
    P("=" * 118)
    if ok:
        peaks = [a["peak_pop"] for a in ok]
        ends = [a["extinct"] for a in ok if a["extinct"]]
        P(f"peak population   n={len(peaks)}  min {min(peaks)}  "
          f"median {statistics.median(peaks):.0f}  max {max(peaks)}"
          + (f"  spread {max(peaks) / max(1, min(peaks)):.1f}x" if min(peaks) else ""))
        if ends:
            P(f"lifespan (days)   n={len(ends)}  min {min(ends):.0f}  "
              f"median {statistics.median(ends):.0f}  max {max(ends):.0f}")
        surv = [a["survival"] for a in ok if a["survival"]]
        if surv:
            P(f"egg->adult        n={len(surv)}  median {statistics.median(surv) * 100:.0f}%"
              f"  range {min(surv) * 100:.0f}-{max(surv) * 100:.0f}%")
        qd = [a["queen_death"] for a in ok if a["queen_death"]]
        if qd:
            P(f"queen death (day) n={len(qd)}  median {statistics.median(qd):.0f}"
              f"  range {min(qd):.0f}-{max(qd):.0f}")

        # dormancy timing — the identifiability question needs the variance
        # Skip each run's first dormancy: the queen founds mid-year with a
        # part-season, so her first onset is different by design. The
        # identifiability question is about steady state.
        temps = [t for a in ok for _, t in a["dormancies"][1:]]
        doys = [d % 365 for a in ok for d, _ in a["dormancies"][1:]]
        first = [(a.get("run"), a["dormancies"][0]) for a in ok if a["dormancies"]]
        if temps:
            P("")
            P(f"dormancy onset    n={len(temps)} steady-state events over {len(ok)} run(s)"
              f"  (founding year excluded)")
            P("  founding yr     " + ", ".join(
                f"run {r}: day {d:.0f} at {t:.1f}C" for r, (d, t) in first[:4]))
            P(f"  trigger temp    {min(temps):.1f}-{max(temps):.1f} C  "
              f"(spread {max(temps) - min(temps):.2f})")
            P(f"  day-of-year     {min(doys):.1f}-{max(doys):.1f}  "
              f"(spread {max(doys) - min(doys):.1f})")
            if max(temps) - min(temps) < 0.15 and max(doys) - min(doys) < 1.0:
                P("  NOTE: zero variance in both. Under a noiseless annual temperature")
                P("        curve an endogenous clock and a thermal gate are")
                P("        observationally identical - this is not evidence for the")
                P("        sand-glass. Perturb the thermal year to separate them.")
        rt = [t for a in ok for _, t in a["reactivations"]]
        if rt:
            P(f"reactivation temp {min(rt):.1f}-{max(rt):.1f} C over {len(rt)} events")

        allflags = defaultdict(int)
        for a in ok:
            for k, _ in a["flags"]:
                allflags[k] += 1
        P("")
        if allflags:
            P("flag tally        " + "  ".join(
                f"{k} {v}/{len(ok)}" for k, v in sorted(allflags.items(),
                                                        key=lambda x: -x[1])))
        else:
            P("flag tally        clean")
    P("")
    return "\n".join(out)


# ------------------------------------------------------------------ main
def main(argv):
    args = [x for x in argv[1:] if not x.startswith("--")]
    detail = "--detail" in argv
    jsonpath = None
    if "--json" in argv:
        k = argv.index("--json")
        if k + 1 < len(argv):
            jsonpath = argv[k + 1]
            args = [x for x in args if x != jsonpath]

    paths = []
    if not args:
        paths = sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                              "*.tsv")))
    for a in args:
        if os.path.isdir(a):
            paths += sorted(glob.glob(os.path.join(a, "*.tsv")))
        else:
            paths += sorted(glob.glob(a)) or [a]
    paths = list(dict.fromkeys(paths))

    if not paths:
        print("No .tsv run logs found. Pass a directory or file glob.")
        return 1

    runs = [analyse(parse(p)) for p in paths]
    text = report(runs, detail)
    print(text)

    if jsonpath:
        slim = []
        for a in runs:
            if a.get("error"):
                slim.append({"path": a["path"], "error": a["error"]})
                continue
            slim.append({k: v for k, v in a.items()
                         if k not in ("rows", "cols", "I", "events")}
                        | {"flags": [{"flag": k, "detail": d} for k, d in a["flags"]],
                           "dormancies": a["dormancies"],
                           "reactivations": a["reactivations"]})
        with open(jsonpath, "w", encoding="utf8") as fh:
            json.dump(slim, fh, indent=1)
        print(f"[json written to {jsonpath}]")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
