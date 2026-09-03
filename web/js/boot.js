/* boot.js - start the app. Last on purpose: everything else must be defined

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */

/* startUi() lives in core.js rather than here, and window's load event calls
   it too: this file is one of the two dozen the browser has to fetch, and a
   dropped one is a real thing that happens (see core.js's uiFailedFiles). If
   THIS is the file that goes missing, load still starts the app. Both paths
   run at most once between them.

   The one failure left is core.js itself not arriving, and then there is no
   startUi to call - no state, no api, no esc(), nothing. So the message below
   is built out of plain DOM, and it offers the only fix there is. */
if(typeof startUi==='function')startUi();
else uiRescue();

function uiRescue(){
  const el=document.createElement('div');
  el.style.cssText='padding:2rem;font:15px/1.7 system-ui,sans-serif';
  el.innerHTML='<h2>The tool did not finish loading.</h2>'+
    '<p>The server is running - it answered for the rest of this page - but the '+
    'browser never received <code>js/core.js</code>, which the rest of the '+
    'interface is built on.</p>'+
    '<p>Reloading fetches it again. If it keeps happening, '+
    '<code>config\\server.log</code> is worth sending on.</p>'+
    '<p><button>Reload the page</button></p>';
  el.querySelector('button').onclick=()=>location.reload();
  document.body.replaceChildren(el);
}
