const assert=require('assert'),fs=require('fs'),vm=require('vm'),path=require('path');
const root=path.join(__dirname,'..');
const strings=JSON.parse(fs.readFileSync(path.join(root,'.tmp/cards_strings.json'),'utf8'));
const c={state:{ed:{d:{},cardSrc:'',infoSrc:''}},
  esc:s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;'),
  tt:(id,p={})=>(strings[id]||id).replace(/\{(\w+)\}/g,(_,k)=>p[k]??k)};
vm.createContext(c);
vm.runInContext(fs.readFileSync(path.join(root,'web/js/editor.js'),'utf8'),c);
c.edOwnFolders=()=>['england','france'];
c.edIcoPayloadFolders=()=>[];
const e=c.state.ed;
assert.equal(c.edCardWarnings('card'),'');
e.d.icon_variants={card:[{factions:['england']}]};
e.d.icon_coverage={card:[{faction:'france',reasons:['ownership'],fallback:''}],info:[]};
let html=c.edCardWarnings('card');
assert(html.includes('count w-warn')&&html.includes('france')&&html.includes('generic'));
assert.equal(c.edCardVariants('card','Cards'),'');
e.d.icon_coverage.card=[
  {faction:'france',reasons:['ownership'],fallback:'ui/units/mercs/#spearmen.tga',severity:'note'},
  {faction:'spain',reasons:['ownership'],fallback:'ui/units/mercs/#spearmen.tga',severity:'note'}];
html=c.edCardWarnings('card');
assert(!html.includes('w-warn')&&!html.includes('Warning'));
assert(html.includes('france, spain')&&html.includes('ui/units/mercs/#spearmen.tga'));
assert.equal((html.match(/<div/g)||[]).length,1);

e.cardSrc='import.tga';
assert(!c.edCardWarnings('card').includes('france'));
assert(c.edCardWarnings('card').includes('spain'));
e.d.icon_coverage.card.push({faction:'denmark',reasons:['recruitment'],fallback:''});
assert(c.edCardWarnings('card').includes('denmark'));
c.edIcoPayloadFolders=()=>['england'];
assert(c.edCardWarnings('card').includes('france'));
e.cardSrc='';
e.d.icon_coverage.card[0].faction='<script>';
assert(c.edCardWarnings('card').includes('&lt;script>'));
assert.equal(c.edCardWarnings('info'),'');
e.d.icon_coverage.info=[{faction:'france',reasons:['ownership'],fallback:''}];
assert(c.edCardWarnings('info').includes('info card'));
e.infoSrc='info.tga';
c.edIcoPayloadFolders=()=>[];
assert.equal(c.edCardWarnings('info'),'');
e.infoSrc='';
e.d.icon_coverage.card=[{faction:'mercs',reasons:[],fallback:'',severity:'warning',shared:true}];
html=c.edCardWarnings('card');
assert(html.includes('Warning')&&html.includes('ui/units/mercs'));
e.cardSrc='import.tga';
c.edIcoPayloadFolders=()=>['england'];
assert(c.edCardWarnings('card').includes('Warning'));
c.edIcoPayloadFolders=()=>['mercs'];
assert.equal(c.edCardWarnings('card'),'');
const source=fs.readFileSync(path.join(root,'web/js/editor.js'),'utf8');
assert(source.indexOf("${edCardWarnings('card')}")<source.indexOf("${edCardVariants('card',"));
console.log('Card coverage UI: all assertions passed');
