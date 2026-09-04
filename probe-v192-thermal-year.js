/* probe-v192-thermal-year.js — does dormancy onset follow an internal clock or
   the thermometer?

   Under the default season the two are indistinguishable: the ambient curve is
   noiseless and exactly annual, so "195 days after reactivation" and "the day
   the falling limb reaches T" name the same date every year forever. Rescaling
   the environmental year breaks the tie, because only one of them moves.

   Run:  node probe-v192-thermal-year.js --build=current --year=250 --days=1500
   Emits one TSV row per dormancy spell on stdout, plus a "#" header.

   The v1.1 control has the thermal year hard-coded; `transform` gives it the
   same YEAR handle at load time rather than editing a file that is kept
   unchanged on purpose. */
import { load, EXPOSE_CURRENT, EXPOSE_V11 } from "./harness.mjs";
import { writeFileSync } from "node:fs";

const arg=(k,d)=>{ const a=process.argv.find(x=>x.startsWith("--"+k+"=")); 
                   return a===undefined?d:a.split("=").slice(1).join("="); };
const BUILD=arg("build","current"), YEAR=+arg("year",365),
      DAYS=+arg("days",1500), SEED=+arg("seed",20260828),
      LOGDIR=arg("logdir","");   // if set, also write the build's own run TSV

// Give the legacy build the YEAR handle the current build now has in CFG.
function yearHandle(src){
  const old="/365);", nw="/CFG.SEASON.YEAR);";
  if(src.indexOf(old)<0) throw new Error("v1.1 season anchor missed");
  return src.replace(old,nw);
}

let m, halted;
if(BUILD==="current"){
  m=load("./formica.html", EXPOSE_CURRENT);
  // The build's own definition of dormancy: her sand-glass ran out.
  halted=()=>m.queen.dormant;
}else if(BUILD==="v11"){
  m=load("./formica-v1.1-legacy.html", EXPOSE_V11, yearHandle);
  m.CFG.SEASON.YEAR=365;                       // the value it had hard-coded
  // The build's own definition of dormancy: it is too cold where she sits.
  halted=()=>m.tempAt(m.queen.x,m.queen.y) < m.CFG.DIAPAUSE_T;
}else throw new Error("unknown build "+BUILD);

m.reset(SEED);                 // forces the PRNG BEFORE buildWorld()
m.CFG.SEASON.YEAR=YEAR;
if(m.marathon!==undefined) m.marathon=false;

// Daily samples. A dormancy spell is >=5 consecutive halted days, which drops
// the one-tick jitter the thermal build shows as the queen drifts across the
// gradient without saying anything about a real spell.
const MIN_SPELL=5;
const rows=[]; let next=1;
while(m.simDay<DAYS && m.queen.alive){
  m.step(1/60);
  if(m.simDay>=next){ rows.push([m.simDay, m.ambient, halted()?1:0]); next=Math.floor(m.simDay)+1; }
}

const spells=[]; let i=0;
while(i<rows.length){
  if(!rows[i][2]){ i++; continue; }
  let j=i; while(j<rows.length && rows[j][2]) j++;
  if(j-i>=MIN_SPELL) spells.push({on:rows[i], off:rows[j-1], len:j-i});
  i=j;
}
const phase=d=>{ const p=((d-m.CFG.SEASON.PEAK)%YEAR+YEAR)%YEAR; return p/YEAR; };
console.log("# build="+BUILD+" year="+YEAR+" seed="+SEED+" days="+DAYS
  +" queenAlive="+m.queen.alive+" endDay="+m.simDay.toFixed(1)+" ants="+m.antCount);
console.log(["build","year","spell","onDay","onAmb","onPhase","offDay","offAmb",
             "spellLen","prevOffToOn","onToOn"].join("\t"));
if(LOGDIR && m.logText){
  // The simulator's own 28-column log, so summarise-runs.py can read this run
  // exactly as it reads an overnight marathon file. logSample() runs from
  // step() regardless of marathon mode, so runLog is already complete.
  const reason = m.antCount===0 ? "colony extinct" : "year sweep";
  writeFileSync(LOGDIR+"/formica-year"+YEAR+"-seed"+SEED+"-"
                +reason.replace(/\W+/g,"_")+"-day"+m.simDay.toFixed(0)+".tsv",
                m.logText(reason));
}
spells.forEach((s,k)=>{
  const prev=k?spells[k-1]:null;
  console.log([BUILD,YEAR,k+1,s.on[0].toFixed(1),s.on[1].toFixed(2),
    phase(s.on[0]).toFixed(4), s.off[0].toFixed(1), s.off[1].toFixed(2), s.len,
    prev?(s.on[0]-prev.off[0]).toFixed(1):"", prev?(s.on[0]-prev.on[0]).toFixed(1):""
  ].join("\t"));
});
