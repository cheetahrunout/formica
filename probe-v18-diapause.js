// Throwaway probe for v1.8 larval diapause.
//
// This machine has no JS runtime (node/bun/deno all absent), so the CLAUDE.md
// eval-with-stubbed-DOM harness cannot run. It is not needed here: formica is a
// browser app, so the probe runs in the real environment instead of a stub.
//
//   open formica.html, then paste this whole file into the devtools console.
//
// Measured ~39,000 ticks/sec in Edge, about 46 sim-days/sec — roughly 4x the
// documented headless rate. It self-chunks against a wall-clock budget so it
// never trips a devtools timeout; call again until it prints DONE.
//
// Three tests, all aimed at the v1.7 orphan bug:
//   A  matched control — with the queen alive, larval diapause must still halt
//      near doy 5 and wake near doy 222, and the recruitment budget must close.
//   B  orphan, cohort ACTIVE  — queen killed mid-season, brood must die out and
//      endRun must fire.
//   C  orphan, cohort HALTED  — the actual run-1 failure mode: queen killed on
//      doy ~38 with qGlass ~181 and the cohort in diapause. Under v1.7 those
//      larvae were immortal and the marathon never terminated.
(function () {
  // Explicit per-phase seeds: reset(s) forces the stream before buildWorld(),
  // so each phase is byte-reproducible and independent of the ones before it.
  const SEED_A = 20260828, SEED_B = 31415926, SEED_C = 27182818;
  const TPD = 60 * 14;                  // ticks per sim-day: 1/60 s steps, DAY_SECONDS 14
  const freshLog = () => ({ emerged:0, died:0, digs:0, fills:0, meals:0, laid:0, bDied:0, bEaten:0 });
  const countDiap = () => {
    let n = 0;
    for (let k = 0; k < CFG.MAX_BROOD; k++)
      if (brood.alive[k] && brood.stage[k] === 1 && brood.diap[k]) n++;
    return n;
  };
  const aliveBrood = () => {
    let n = 0;
    for (let k = 0; k < CFG.MAX_BROOD; k++) if (brood.alive[k]) n++;
    return n;
  };

  if (!window.__probe) {
    running = false;                    // stop the rAF loop; we drive step() ourselves
    reset(SEED_A);
    logC = freshLog();
    window.__probe = { phase: 'A', day: 0, trans: [], prev: false, res: {}, ended: null };
    // Record instead of resetting + triggering a file download.
    window.__probeOrigEndRun = endRun;
    endRun = function (r) {
      const P = window.__probe;
      if (!P.ended) P.ended = { reason: r, day: +simDay.toFixed(1) };
    };
  }
  const P = window.__probe;

  const t0 = performance.now();
  while (performance.now() - t0 < 20000 && P.phase !== 'done') {
    for (let i = 0; i < TPD; i++) step(1 / 60);
    P.day++;
    const doy = simDay % 365;

    if (P.phase === 'A') {
      const on = countDiap() > 0;
      if (on !== P.prev) {
        P.trans.push({ day: +simDay.toFixed(1), doy: +doy.toFixed(1), on: on, amb: +ambient.toFixed(1) });
        P.prev = on;
      }
      if (P.day >= 800) {
        P.res.A = {
          transitions: P.trans, queenAlive: queen.alive, pop: antCount,
          laid: logC.laid, emerged: logC.emerged, bDied: logC.bDied,
          bEaten: logC.bEaten, aliveBrood: aliveBrood(),
        };
        reset(SEED_B); logC = freshLog(); P.ended = null; P.phase = 'Bwarm'; P.day = 0;
      }

    } else if (P.phase === 'Bwarm') {
      if (P.day >= 300) {
        P.res.Bkill = { day: +simDay.toFixed(1), doy: +doy.toFixed(1), pop: antCount,
                        brood: countBrood(), diap: countDiap() };
        queen.alive = false; queen.phase = 2; queen.rate = 0;
        P.phase = 'B'; P.day = 0; P.broodZero = null;
      }

    } else if (P.phase === 'B') {
      if (P.broodZero === null && countBrood() === 0) P.broodZero = +simDay.toFixed(1);
      if (P.ended || P.day >= 3000) {
        P.res.B = { broodZeroDay: P.broodZero, broodLeft: countBrood(), popLeft: antCount,
                    bDied: logC.bDied, ended: P.ended };
        reset(SEED_C); logC = freshLog(); P.ended = null; P.phase = 'Cwarm'; P.day = 0;
      }

    } else if (P.phase === 'Cwarm') {
      // Wait for the run-1 configuration: past the first winter, doy ~38, cohort halted.
      if (simDay > 400 && doy > 37 && doy < 39 && countDiap() > 0) {
        P.res.Ckill = { day: +simDay.toFixed(1), doy: +doy.toFixed(1), pop: antCount,
                        brood: countBrood(), diap: countDiap(),
                        qGlass: +queen.glass.toFixed(1), amb: +ambient.toFixed(1) };
        queen.alive = false; queen.phase = 2; queen.rate = 0;
        P.phase = 'C'; P.day = 0; P.woke = null; P.broodZero = null;
      }
      if (P.day >= 1200) { P.res.Cerr = 'never found a halted cohort'; P.phase = 'done'; }

    } else if (P.phase === 'C') {
      if (P.woke === null && countDiap() === 0)
        P.woke = { day: +simDay.toFixed(1), doy: +doy.toFixed(1), amb: +ambient.toFixed(1) };
      if (P.broodZero === null && countBrood() === 0) P.broodZero = +simDay.toFixed(1);
      if (P.ended || P.day >= 3000) {
        P.res.C = { wokeAfterQueenDeath: P.woke, broodZeroDay: P.broodZero,
                    broodLeft: countBrood(), popLeft: antCount,
                    bDied: logC.bDied, ended: P.ended };
        P.phase = 'done';
      }
    }
  }

  if (P.phase !== 'done') {
    console.log('... still running: phase %s, sim day %s, pop %d, brood %d, diapausing %d — run again',
      P.phase, simDay.toFixed(0), antCount, countBrood(), countDiap());
    return P.phase;
  }

  /* ------------------------------------------------------------ verdict */
  let fail = 0;
  const check = (ok, msg) => { console.log((ok ? 'PASS  ' : 'FAIL  ') + msg); if (!ok) fail++; };
  const A = P.res.A, B = P.res.B, C = P.res.C;

  console.log('\n--- A  matched control, queen alive, 800 days ---');
  console.table(A.transitions);
  const halts = A.transitions.filter(t => t.on).map(t => t.doy);
  const wakes = A.transitions.filter(t => !t.on).map(t => t.doy);
  // The first halt is the founding cohort, which inherits glass = GLASS_LEN-45.
  check(halts.slice(1).length > 0 && halts.slice(1).every(d => Math.abs(d - 5.2) < 8),
    'steady-state halt near doy 5 (v1.7 timing preserved): ' + JSON.stringify(halts));
  check(wakes.length > 0 && wakes.every(d => Math.abs(d - 222) < 8),
    'wake near doy 222, the queen reactivation day: ' + JSON.stringify(wakes));
  check(A.queenAlive, 'queen still alive at day 800');
  const acct = A.emerged + A.bDied + A.bEaten + A.aliveBrood;
  check(A.laid === acct, 'recruitment budget closes: laid ' + A.laid + ' = emerged ' +
    A.emerged + ' + died ' + A.bDied + ' + eaten ' + A.bEaten + ' + alive ' + A.aliveBrood);

  console.log('\n--- B  orphan, cohort ACTIVE (killed doy %s, %d brood, %d diapausing) ---',
    P.res.Bkill.doy, P.res.Bkill.brood, P.res.Bkill.diap);
  check(B.broodZeroDay !== null, 'orphaned brood dies out (day ' + B.broodZeroDay + ')');
  check(B.bDied > 0, 'brood starvation path fires (' + B.bDied + ' starved)');
  check(!!B.ended, 'endRun fires: ' + (B.ended ? B.ended.reason + ' at day ' + B.ended.day : 'NEVER'));

  console.log('\n--- C  orphan, cohort HALTED — the run-1 failure mode ---');
  console.log('    queen killed day %s (doy %s), qGlass %s, %d larvae in diapause',
    P.res.Ckill.day, P.res.Ckill.doy, P.res.Ckill.qGlass, P.res.Ckill.diap);
  check(!!C.wokeAfterQueenDeath,
    'halted cohort still gets a spring with no queen: woke day ' +
    (C.wokeAfterQueenDeath ? C.wokeAfterQueenDeath.day + ' (doy ' + C.wokeAfterQueenDeath.doy +
     ', ' + C.wokeAfterQueenDeath.amb + 'C)' : 'NEVER — v1.7 bug present'));
  check(C.wokeAfterQueenDeath && Math.abs(C.wokeAfterQueenDeath.doy - 222) < 8,
    'and wakes on the normal reactivation day, not late');
  check(C.broodZeroDay !== null, 'then dies out (day ' + C.broodZeroDay + ')');
  check(!!C.ended, 'endRun fires: ' + (C.ended ? C.ended.reason + ' at day ' + C.ended.day : 'NEVER'));

  console.log('\nDONE — %s (%d check%s failed)', fail ? 'FAILED' : 'ALL PASS', fail, fail === 1 ? '' : 's');
  endRun = window.__probeOrigEndRun;
  return fail ? 'FAILED' : 'ALL PASS';
})()
