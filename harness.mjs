/* Headless harness for formica.html.
   Loads the simulator's <script> into this process behind DOM stubs and hands
   back live references to its internals. See CHANGELOG "the harness runs here". */
import { readFileSync } from "node:fs";

function stubCtx(){
  const noop=()=>{};
  const g=new Proxy({}, { get:(t,k)=>{
    if(k==="createImageData") return (w,h)=>({width:w,height:h,data:new Uint8ClampedArray(w*h*4)});
    if(k==="getImageData")    return (x,y,w,h)=>({width:w,height:h,data:new Uint8ClampedArray(w*h*4)});
    if(k==="measureText")     return ()=>({width:0});
    if(k in t) return t[k];
    return noop;
  }, set:(t,k,v)=>{ t[k]=v; return true; } });
  return g;
}
function stubEl(tag="div"){
  const e={ tagName:(tag||"div").toUpperCase(), style:{}, dataset:{}, children:[],
    width:0, height:0, textContent:"", value:"", checked:false, className:"",
    getContext:()=>stubCtx(), appendChild(c){this.children.push(c);return c;},
    remove(){}, click(){}, setAttribute(){}, getAttribute(){return null;},
    addEventListener(){}, removeEventListener(){}, focus(){}, blur(){},
    querySelector(){return stubEl();}, querySelectorAll(){return [];},
    getBoundingClientRect:()=>({x:0,y:0,width:800,height:600,top:0,left:0,right:800,bottom:600}),
    scrollTo(){}, scrollHeight:0, clientHeight:0 };
  return e;
}

/** Load the simulator.
 *  `expose`   — body of the object literal handed back (build-specific).
 *  `transform`— optional rewrite of the source before it is evaluated. This is
 *  how a legacy control gets a handle the current build has and it does not,
 *  without editing a file that is kept precisely so it cannot drift. Assert
 *  inside the transform: a regex that silently misses is this project's
 *  most expensive recurring bug. */
export function load(file="formica.html", expose=EXPOSE_CURRENT, transform=null){
  const html=readFileSync(file,"utf8");
  const m=html.match(/<script>([\s\S]*)<\/script>/);
  if(!m) throw new Error("no <script> block in "+file);
  const src=transform ? transform(m[1]) : m[1];

  const doc={ getElementById:()=>stubEl(), querySelector:()=>stubEl(),
    querySelectorAll:()=>[], createElement:t=>stubEl(t), body:stubEl("body"),
    addEventListener(){}, removeEventListener(){}, hidden:false };
  const win={ showDirectoryPicker:undefined, addEventListener(){}, devicePixelRatio:1 };
  const G=globalThis;
  G.document=doc; G.window=win; G.self=G; try{ G.navigator ??= {userAgent:"formica-harness"}; }catch{}
  G.requestAnimationFrame=()=>0;          // the render loop must never start
  G.cancelAnimationFrame=()=>{};
  G.performance ??= { now:()=>Date.now() };
  G.alert=()=>{}; G.confirm=()=>false;
  G.URL ??= {}; G.URL.createObjectURL=()=>"blob:stub"; G.URL.revokeObjectURL=()=>{};
  G.Blob ??= class { constructor(p){ this.parts=p; } };
  G.localStorage ??= { getItem:()=>null, setItem(){}, removeItem(){} };
  // indexedDB deliberately left undefined: the log path detects that and
  // falls back to the in-memory mirror, which is what we read here.

  // Everything the simulator declares is function-scoped inside this wrapper,
  // so the epilogue closure is the only way in and nothing leaks to globals.
  // `expose` is the body of that object literal: it is build-specific because
  // the legacy controls do not have all of the current build's names, and a
  // bare reference to a missing one throws at return time.
  const epilogue = ";return {"+expose+"};";
  return new Function(src+epilogue)();
}

/* Getters, not values, for everything that is a `let`. `simDay` and friends are
   rebound every tick, and reset() rebuilds `ants`, `brood`, `larder` and `logC`
   outright — a plain reference captured before reset() would keep pointing at
   the previous colony and read as plausible, empty data. Only `CFG` and the
   functions are safe to hand out directly. */
export const EXPOSE_CURRENT = `
  CFG, step, reset, countBrood, countLarvae, therm, termRate, tempAt,
  logText, logName, LOG_COLS, logSample,
  get ants(){return ants;}, get brood(){return brood;},
  get larder(){return larder;}, get logC(){return logC;},
  get queen(){return queen;}, get simDay(){return simDay;},
  get ambient(){return ambient;}, get thermNow(){return thermNow;},
  get antCount(){return antCount;}, get runLog(){return runLog;},
  get runEvents(){return runEvents;}, get nestCells(){return nestCells;},
  get terrain(){return terrain;},
  set marathon(v){marathon=v;}, get marathon(){return marathon;},
  set seasons(v){seasons=v;}, get seasons(){return seasons;},
  setAmbient(v){ ambient=v; },
`;

/* v1.1-legacy: no sand-glass, no marathon logger, no ROCK. Its dormancy is a
   pure thermal gate, which is exactly why it is kept as a control. */
export const EXPOSE_V11 = `
  CFG, step, reset, countBrood, countLarvae, tempAt,
  get ants(){return ants;}, get brood(){return brood;}, get larder(){return larder;},
  get queen(){return queen;}, get simDay(){return simDay;},
  get ambient(){return ambient;}, get antCount(){return antCount;},
  set seasons(v){seasons=v;}, get seasons(){return seasons;},
`;
