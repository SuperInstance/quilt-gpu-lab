import { QuiltEngine } from '/home/eileen/projects/quilt-arcade/engine/index.js';
import { buildSheet } from '/home/eileen/projects/quilt-arcade/games/pong/sheet.mjs';
const boot = () => { const e = new QuiltEngine('x',{eager:true}); e.loadSheet(buildSheet()); return e; };
const get=(e,id)=>e.get(id).then(r=>r.data);
let tot=0,n=0,pts=[];
for (let seed=1; seed<=8; seed++){
  const e=boot(); await e.call('new_game',{seed});
  let last=null; let i=0;
  for (; i<3000; i++){ last=(await e.call('match.step')).data; if(last.over) break; }
  const sl=await get(e,'score.left'), sr=await get(e,'score.right');
  console.log(`seed ${seed}: ticks=${i} over=${last.over} winner=${await get(e,'winner.current')} score=${sl}-${sr}`);
  tot+=i;n++;pts.push(i);
}
console.log('mean ticks',(tot/n).toFixed(1),'max',Math.max(...pts));
