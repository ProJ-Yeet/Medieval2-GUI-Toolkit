/* i18n.js - the interface language (Phase 88)

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it.

   This one is loaded first, after i18n/catalogue.js, which the server writes:
   English (the source and the fallback), the chosen locale's catalogue, and
   the locales on offer. Every string a person reads comes out of tt(id), so it
   is there from the first line of the first module.

   Two languages, never confused: this is the toolkit's own. A mod's text is
   the mod's, whatever is chosen here, and nothing written to a mod goes
   through this file. Display is localised (fmtNum, fmtDate); a value typed
   into a field that is written to a file is parsed and written in the file's
   own format, ASCII digits and a `.`, in every locale.

   tt(id,params)   the string for id, {name} filled from params as written
   ttA(id,params)  the same, safe inside an HTML attribute
   ttN(id,n,params) a plural: the catalogue holds a form per CLDR category
   A name missing from params stays as written, so a literal { } in a
   message is safe. English with no params is returned exactly as in en.json:
   the English interface is the same text, byte for byte, as before 88. */

const I18N=(()=>{
  let boot=typeof window!=='undefined'?window.I18N_BOOT:undefined;
  if(!boot){
    /* catalogue.js did not arrive (a dropped request, see core.js's
       uiFailedFiles). Without English every label would be its ID, so fetch
       English alone, once, synchronously: the one place a blocking request
       is worth its cost. */
    boot={lang:'en',dir:'ltr',status:'source',base:'',en:{},cat:{},offered:[]};
    try{
      // (outside a browser, a test running a module in Node, there is no
      // request to make, and English comes from the test's own copy)
      const x=new XMLHttpRequest(); x.open('GET','i18n/en.json',false); x.send();
      if(x.status===200)boot.en=JSON.parse(x.responseText);
    }catch(e){}
  }
  const lang=boot.lang||'en';
  const pseudo=boot.base?lang:'';
  return {lang,dir:boot.dir||'ltr',status:boot.status||'',pseudo,
    en:boot.en||{},cat:boot.cat||{},offered:boot.offered||[],missing:new Set(),
    isSource:lang==='en'};
})();
if(typeof document!=='undefined'&&document.documentElement){
  document.documentElement.lang=I18N.lang;
  document.documentElement.dir=I18N.dir;
}

/* ---- the pseudo-locales ----
   en-XA: every letter accented, a third longer, in brackets, so a string left
   in the code (plain ASCII) and a label that clips (the longer text) both
   show. ar-XB: English drawn right to left, and the page mirrored, for
   everything that must or must not flip. Neither is ever picked by itself. */
const I18N_ACCENT={a:'á',b:'ƀ',c:'ç',d:'ð',e:'é',f:'ƒ',g:'ĝ',h:'ĥ',i:'î',j:'ĵ',k:'ķ',l:'ļ',m:'ɱ',
  n:'ñ',o:'ö',p:'þ',q:'ǫ',r:'ŕ',s:'š',t:'ţ',u:'û',v:'ṽ',w:'ŵ',x:'ẋ',y:'ý',z:'ž',
  A:'Å',B:'Ɓ',C:'Ç',D:'Ð',E:'É',F:'Ƒ',G:'Ĝ',H:'Ĥ',I:'Î',J:'Ĵ',K:'Ķ',L:'Ļ',M:'Ṁ',N:'Ñ',
  O:'Ö',P:'Þ',Q:'Ǫ',R:'Ŕ',S:'Š',T:'Ţ',U:'Û',V:'Ṽ',W:'Ŵ',X:'Ẋ',Y:'Ý',Z:'Ž'};
// what is not text: a tag, an entity, a {placeholder}
const I18N_SKIP=/(<[^>]*>|&(?:#\d+|#x[0-9a-f]+|[a-z]+);|\{[A-Za-z_]\w*(?::[^{}]*)?\})/i;
function i18nPseudo(s){
  if(typeof s!=='string'||!s)return s;
  const parts=s.split(I18N_SKIP);
  if(I18N.pseudo==='ar-XB')
    return parts.map((p,i)=>i%2||!/\S/.test(p)?p:'‮'+p+'‬').join('');
  let letters=0;
  const out=parts.map((p,i)=>{
    if(i%2)return p;
    return p.replace(/[A-Za-z]/g,c=>{letters++;return I18N_ACCENT[c]||c;});
  }).join('');
  const pad=Math.ceil(letters*0.35);
  return letters?'['+out+(pad?' '+'·'.repeat(pad):'')+']':out;
}

/* ---- filling a message ----
   {name} is params[name] as written (String(v)), exactly what the template
   literal it came out of did, so English is unchanged. {name:spec} is an
   engine message's Python format spec: .2f, d, ',', ',.1f' - read here in the
   interface language, since only a translated message is filled on the page. */
function i18nFill(s,params){
  if(!params||typeof s!=='string')return s;
  return s.replace(/\{([A-Za-z_]\w*)(?::([^{}]*))?\}/g,(m,k,spec)=>{
    if(!Object.prototype.hasOwnProperty.call(params,k))return m;
    const v=params[k];
    if(spec===undefined)return String(v);
    return i18nSpec(v,spec);
  });
}
function i18nSpec(v,spec){
  const n=typeof v==='number'?v:parseFloat(v);
  const m=/^(,)?(?:\.(\d+))?([fd%])?$/.exec(spec||'');
  if(!m||!isFinite(n))return String(v);
  const o={useGrouping:!!m[1]};
  if(m[2]!==undefined){o.minimumFractionDigits=+m[2];o.maximumFractionDigits=+m[2];}
  if(m[3]==='d'){o.maximumFractionDigits=0;}
  if(m[3]==='%')return fmtNum(n*100,o)+'%';
  return fmtNum(n,o);
}

function i18nRaw(id){
  if(!I18N.pseudo&&!I18N.isSource&&Object.prototype.hasOwnProperty.call(I18N.cat,id))return I18N.cat[id];
  if(Object.prototype.hasOwnProperty.call(I18N.en,id)){
    const v=I18N.en[id];
    return I18N.pseudo?(typeof v==='string'?i18nPseudo(v):Object.fromEntries(
      Object.entries(v).map(([k,x])=>[k,i18nPseudo(x)]))):v;
  }
  if(!I18N.missing.has(id)){I18N.missing.add(id);console.warn('i18n: no string for',id);}
  return id;
}
function tt(id,params){
  const v=i18nRaw(id);
  return i18nFill(typeof v==='string'?v:(v&&v.other)||id,params);
}
// English is the page's own text, already safe where it stands; a
// translation may carry either quote, so both are escaped for it
function ttA(id,params){
  const s=tt(id,params);
  return I18N.isSource?s:s.replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}
let _i18nPlural=null;
function ttN(id,n,params){
  const v=i18nRaw(id);
  const p=Object.assign({count:fmtNum(n)},params||{});
  if(typeof v==='string')return i18nFill(v,p);
  if(!_i18nPlural)_i18nPlural=new Intl.PluralRules(I18N.pseudo?'en':I18N.lang);
  const cat=(n===0&&v.zero!==undefined)?'zero':_i18nPlural.select(n);
  return i18nFill(v[cat]!==undefined?v[cat]:v.other,p);
}

/* ---- numbers, dates, sorting ----
   For the screen only. A number written to a file never comes through here. */
const _i18nNum={};
function fmtNum(n,opts){
  const loc=I18N.pseudo?'en':I18N.lang;
  const k=JSON.stringify(opts||{});
  try{return (_i18nNum[k]||(_i18nNum[k]=new Intl.NumberFormat(loc,opts))).format(n);}
  catch(e){return String(n);}
}
function fmtDate(d,opts){
  try{return new Intl.DateTimeFormat(I18N.pseudo?'en':I18N.lang,opts||{dateStyle:'medium',timeStyle:'short'})
    .format(d instanceof Date?d:new Date(d));}
  catch(e){return String(d);}
}
const i18nCollator=new Intl.Collator(I18N.pseudo?'en':I18N.lang,{sensitivity:'base',numeric:true});
const i18nCompare=(a,b)=>i18nCollator.compare(String(a),String(b));

/* ---- index.html's own text ----
   data-i18n="id" on an element is its content; data-i18n-title (and
   -placeholder, -aria-label, -alt) an attribute. English is already in the
   page, so there is nothing to do in English. */
function i18nApplyDom(root){
  if(I18N.isSource||typeof document==='undefined'||!document.querySelectorAll)return;
  const r=root||document;
  r.querySelectorAll('[data-i18n]').forEach(el=>{el.innerHTML=tt(el.dataset.i18n);});
  for(const a of ['title','placeholder','aria-label','alt']){
    r.querySelectorAll(`[data-i18n-${a}]`).forEach(el=>
      el.setAttribute(a,tt(el.getAttribute('data-i18n-'+a))));
  }
  if(r===document&&I18N.en['app.title'])document.title=tt('app.title');
}

/* ---- the engine's messages ----
   A reply marks, under _i18n, which of its strings are engine messages and
   under which ID ({text: [id, params]}). In any language but English each one
   is swapped for the catalogue's, or kept in English when there is none. The
   log and server.log keep English whatever is chosen here. */
function i18nFromServer(obj){
  if(!obj||typeof obj!=='object'||!obj._i18n)return obj;
  const marks=obj._i18n; delete obj._i18n;
  if(I18N.isSource)return obj;
  const swap=s=>{
    const m=marks[s]; if(!m)return s;
    const [id,params]=m;
    const have=I18N.pseudo?Object.prototype.hasOwnProperty.call(I18N.en,id)
      :Object.prototype.hasOwnProperty.call(I18N.cat,id);
    return have?tt(id,params||{}):s;
  };
  const walk=(v,d)=>{
    if(d>12||!v||typeof v!=='object')return;
    for(const k of Object.keys(v)){
      const x=v[k];
      if(typeof x==='string'){if(marks[x])v[k]=swap(x);}
      else if(x&&typeof x==='object')walk(x,d+1);
    }
  };
  walk(obj,0);
  return obj;
}

/* ---- choosing one (Settings) ----
   The languages with a catalogue, a draft one marked as such, and the two
   pseudo-locales apart, for testing. Choosing saves and reloads: every screen
   is drawn again from the start in the new language, which is simpler and
   surer than redrawing each one in place. */
function i18nOptionsHtml(){
  const row=r=>{
    const label=r.native+(r.name&&r.name!==r.native?` (${r.name})`:'')
      +(r.status==='draft'?' - '+tt('i18n.draft'):'');
    return `<option value="${r.tag}"${r.tag===I18N.lang?' selected':''}>${esc(label)}</option>`;
  };
  const real=I18N.offered.filter(r=>r.status!=='test'), test=I18N.offered.filter(r=>r.status==='test');
  return real.map(row).join('')
    +(test.length?`<optgroup label="${ttA('i18n.for_testing')}">${test.map(row).join('')}</optgroup>`:'');
}
async function i18nChoose(tag){
  await api.post('/api/settings',{ui_lang:tag});
  location.reload();
}

// the scripts sit at the end of <body>, so the page's own markup is all there
// by now, and nothing has taken a reference to any of it yet
i18nApplyDom();
