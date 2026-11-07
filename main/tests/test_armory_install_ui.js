const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const c = {state:{src:'fixture'}, ARM:{mods:['fixture']}, armSave(){}, armProj:()=>({collections:[]}),
  document:{getElementById:()=>null}, window:{addEventListener(){},removeEventListener(){}},
  esc:String, enc:encodeURIComponent, tt:(id,args)=>id+JSON.stringify(args||{}), ttA:String};
vm.createContext(c);
vm.runInContext(fs.readFileSync(path.join(root,'web/js/armexport.js'),'utf8'), c);
c.armExportPaint=()=>{};
const m=c.armExpMod();
m.choice='add'; m.unit='Guard';
m.unitData={fields:[['soldier','old, 40, 0, 1'],['officer','captain'],['officer#2','standard'],['armour_ug_models','old, old_t1']]};
assert.deepEqual(Array.from(c.armExpAssignSlots(),x=>x.v),
  ['soldier','officer#1','officer#2','officer#3','armour_ug_models#1','armour_ug_models#2','armour_ug_models#3']);
assert.equal(c.armExpModBody().assign_to,'soldier');
m.assign_to='armour_ug_models#3';
assert.equal(c.armExpModBody().assign_to,'armour_ug_models#3');
m.choice='new'; assert.equal(c.armExpModBody().assign_to,'armour_ug_models#3');
m.characterTarget={kind:'leader',campaign:'imperial_campaign',faction:'england',character:'William',line:20};
assert.equal(c.armExpModBody().character_target.kind,'leader');
m.data={units:[],entries:[],templates:{}};
assert.match(c.armExpModHtml(),/armExpModSet\('assign_to'/);
assert.match(c.armExpModHtml(),/armExpCharacterKind/);
m.data.characters=[{campaign:'imperial_campaign',factions:[{name:'england',characters:[
  {name:'William',rank:'leader',line:20},{name:'Henry',rank:'heir',line:30}]}]}];
c.armExpCharacterKind('leader');c.armExpCharacterSet('campaign','imperial_campaign');
c.armExpCharacterSet('faction','england');
assert.match(c.armExpCharacterHtml(),/William/);
assert.doesNotMatch(c.armExpCharacterHtml(),/Henry/);
c.armExpCharacterSet('line','20');assert.equal(c.armExpModBody().character_target.character,'William');
vm.runInContext(fs.readFileSync(path.join(root,'web/js/armsess.js'),'utf8'),c);
const project={}; c.armExtrasInto(project);
assert.equal(project.extra.exportOutput.mod.unitData,undefined,'unit API cache is transient');
assert.equal(project.extra.exportOutput.mod.characterTarget.character,'William');
console.log('Armory install slots and payload passed');

