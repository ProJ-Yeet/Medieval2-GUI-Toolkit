/* v3Close puts the dialog it opened over back, and the unit editor's preview
   remounts the docked viewer while that happens. The remount clears v3Back, so
   v3Close must not read it afterwards (report R-20261106-701EB2). */
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const el=()=>({className:'',innerHTML:'',classList:{add(){},remove(){},contains:()=>true}});
const els={modal:el(),overlay:el(),prev:el()};
let after=0, mounted=0;
const c={console,Promise,setTimeout,clearTimeout,cancelAnimationFrame(){},
  document:{getElementById:id=>els[id]||null},
  state:{ed:{}}, tt:k=>k, esc:s=>s, stashPlace:()=>0, usePlace(){},
  edRenderTab(){}, edPrevAttach(){ mounted++; c.v3Mount('prev','m','e'); }};
vm.createContext(c);
vm.runInContext(fs.readFileSync('web/js/viewer3d.js','utf8'),c);
c.v3Begin=async()=>{};
vm.runInContext("v3Back={html:'<p>editor</p>',cls:'modal wide',scroll:0,after:()=>{globalThis.__after=1}}; v3={}",c);
c.v3Close();
assert.equal(els.modal.innerHTML,'<p>editor</p>');
assert.equal(mounted,1);
assert.equal(c.__after,1,'the opener repaints itself');
console.log('PASS: v3Close survives the preview remounting while the editor is restored');
