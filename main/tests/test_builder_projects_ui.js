const fs=require('fs'),vm=require('vm'),assert=require('assert');
const strings=JSON.parse(fs.readFileSync('web/i18n/en.json','utf8'));
const clone=x=>JSON.parse(JSON.stringify(x));
const esc=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function main(){
 let writes=0,downloads=[],copied=[],resolve;
 const els={modal:{set innerHTML(x){writes++;this.html=x;},get innerHTML(){return this.html;}},bdStatus:{},bdResults:{},bdEligibility:{}};
 const packet={schema:'m2-unit-design',version:1,profile:{id:'native',revision:'1'},inputs:{},presets:{},overrides:{inputs:{},native:{attack:0}},metadata:{text:'<script>bad</script>'}};
 const b={design:clone(packet),saved:JSON.stringify(packet),mod:'Fixture',unit:'Guard',seq:0,active:true,tables:{pri:{sword:{atk:1,roles:['any']}}},defaults:{}};
 const c={console,JSON,Set,Map,Promise,structuredClone,setTimeout,clearTimeout,Blob,
  state:{builder:b},document:{getElementById:id=>els[id]||null,createElement:()=>({click(){downloads.push(this.download);}})},
  URL:{createObjectURL:()=> 'blob:test',revokeObjectURL(){}},navigator:{clipboard:{writeText:async text=>copied.push(text)}},
  esc,ttA:k=>strings[k]||k,tt:(k,p={})=>(strings[k]||k).replace(/\{(\w+)\}/g,(_,n)=>p[n]??n),undoCapture(){},undoReset(){},
  api:{post:async(url,body)=>{
   if(url.endsWith('/import')){if(body.text==='bad')return {error:'bad',message_id:'builder.project_version'};return {design:clone(packet)};}
   if(url.endsWith('/export'))return {name:'design.json',mime:'application/json',text:'<script>export</script>'};
   throw Error(url);
  }} };
 vm.createContext(c);vm.runInContext(fs.readFileSync('web/js/builder.js','utf8'),c);
 c.bdCalculate=()=>{};
 c.bdRender();
 assert(els.modal.innerHTML.includes('bdImportFile'),'import action rendered even before a design exists');
 assert(els.modal.innerHTML.includes('bdExport('),'export actions rendered');
 b.design.presets={pri:{custom:{atk:2,roles:['any']}}};b.family='pri';b.filter='';b.editId='custom';
 assert(c.bdEditIds().includes('custom'),'imported custom presets are editable');
 assert(c.bdPresetFields().includes('bd_preset_atk'),'custom preset exposes known editable fields');
 assert(!c.bdPresetFields().includes('bd_preset_wtype'),'custom rows must not display unrelated preset defaults');
 assert(c.bdTableSelect('pri','pri_preset','sword').includes('value="custom"'),'custom rows are offered in selectors');
 b.design=clone(packet);
 let before=clone(b.design),n=writes;
 await c.bdImportText('bad');assert.deepEqual(b.design,before);assert.equal(writes,n);assert.equal(b.saved,JSON.stringify(packet));
 assert.equal(els.bdStatus.textContent,strings['builder.project_version']);
 await c.bdImportFile({files:[{size:20,text:async()=> 'valid'}],value:'file'});assert.deepEqual(b.design,packet);
 await c.bdExport('project',false);assert.equal(downloads.at(-1),'design.json');
 await c.bdExport('edu',true);assert.equal(copied.at(-1),'<script>export</script>');
 c.navigator.clipboard.writeText=async()=>{throw Error('denied');};n=writes;
 await c.bdExport('csv',true);assert.equal(writes,n);assert.equal(els.bdStatus.textContent,strings['builder.export_failed']);
 // Import/export responses cannot replace or download a design changed during a request.
 c.api.post=()=>new Promise(r=>resolve=r);
 const pending=c.bdImportText('valid');b.design.overrides.native.attack=22;resolve({design:clone(packet)});await pending;
 assert.equal(b.design.overrides.native.attack,22);assert.equal(els.bdStatus.textContent,strings['builder.import_changed']);
 const reading=c.bdImportText('valid');n=writes;b.filter='typed while loading';resolve({design:clone(packet)});await reading;
 assert.equal(writes,n,'a pending import must not repaint a filter being typed in');
 const count=downloads.length;const output=c.bdExport('project',false);b.design.overrides.native.attack=23;
 resolve({name:'stale.json',text:'stale',mime:'application/json'});await output;assert.equal(downloads.length,count);
 // Import text typing updates no form or input host.
 b.design=null;c.bdRender();assert(els.modal.innerHTML.includes('bdImportFile'));
 // Every completed import gets its own step in the real shared undo stack.
 c.document.addEventListener=()=>{};els.overlay={classList:{contains:()=>true}};
 vm.runInContext(fs.readFileSync('web/js/undo.js','utf8'),c);
 c.undoFocus=()=>null;c.scrollSnapshot=()=>[];c.scrollRestore=()=>{};c.undoRefocus=()=>{};
 c.paintDirty=()=>{};c.requestAnimationFrame=fn=>fn();c.toast=()=>{};c.ttN=k=>strings[k]||k;
 c.undoReset();let imported=0;
 c.api.post=async()=>{const d=clone(packet);d.overrides.native.attack=++imported;return {design:d};};
 await c.bdImportText('one');await c.bdImportText('two');
 assert(c.undoStep(false));assert.equal(b.design.overrides.native.attack,1,'Undo restores the preceding import');
 assert(c.undoStep(false));assert.equal(b.design,null,'Undo restores the empty draft');
 assert(c.undoStep(true));assert.equal(b.design.overrides.native.attack,1);
 console.log('Builder projects UI: all assertions passed');
}
main().catch(e=>{console.error(e);process.exit(1);});
