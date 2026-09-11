/* mappin.js - Campaign Map: pick a tile off the map into a form field

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   THE PIN - Phase 20c, M8.

   Every name here starts `cpin`, and there was no `cpin` name anywhere in the
   tree before this phase.

   WHAT IT REPLACES. Every coordinate on this screen was typed, or taken from
   "the picked tile": the people panel's `Here` and the events panel's
   `＋ from the picked tile` both read `state.cmap.pick`. That works, and it has
   a cost nobody asked for - picking a tile is a CLICK on the map, and a click on
   the map selects the province under it, opens its record, its settlement and
   its people, and throws away the panel you were filling in to put the
   province's own there. So the order had to be: click the map, re-open the
   form, press the button.

   WHAT IT IS. A button beside a coordinate pair. Pressing it arms the map: the
   cursor changes, a banner says what is being picked and how to stop, and the
   tile under the pointer is read out in the file's own coordinates. The next
   click on the map is taken by the pin - nothing is selected, no panel moves -
   its tile is written into the field, and the map goes back to normal. Esc, or
   the banner's own button, stops it with nothing written.

   ONE CONTROL, ANY FIELD. A caller hands `cpinButton` a sentence and the name
   of its own function, and that function is called with the picked tile in the
   coordinates descr_strat.txt writes (y counted up from the bottom). The flip is
   made here, once, which is the rule `cevPicked` states about who owns it.
   Phase 22's object dialogs are the next callers, and they need nothing but
   that one line.

   WHAT IT DOES NOT DO. It does not judge the tile. Whether a general may stand
   in the sea is the server's question, and the plan beside the field asks it
   the moment the numbers change - the preview here is only whether the tile is
   on the map at all, which is the one thing the browser knows exactly.
   ===================================================================== */

/* Arm the map. `what` is the sentence the banner says; `fn` is the NAME of a
   global function to call with ([x, y] in game coordinates, [x, y] image), and
   `args` go in front of those two. A name rather than a closure so that the
   button it came from can be plain HTML, like every other button on this
   screen. */
function cpinArm(what, fn, args){
  if(!state.cmap) return;
  state.cpin = {what: String(what || 'a tile'), fn: String(fn || ''),
                args: Array.isArray(args) ? args.slice() : []};
  activity('map pin', `picking ${state.cpin.what}`);
  cpinPaint();
  cmapPaint();
}

function cpinArmed(){ return !!(state.cpin && state.cmap); }

function cpinCancel(){
  if(!state.cpin) return;
  state.cpin = null;
  cpinPaint();
  if(state.cmap){ state.cmap.saidRead = null; cmapPaint(); }
}

/* The tile, in the coordinates the file writes, or null when it is off the map.
   Pure apart from the height - node runs it. */
function cpinGame(tile, width, height){
  if(!tile || !(tile[0] >= 0 && tile[1] >= 0 && tile[0] < width && tile[1] < height))
    return null;
  return [tile[0], height - 1 - tile[1]];
}

/* A click, while armed. Returns true when the pin took it, so the pick the
   click would otherwise have been does not happen as well. A click off the map
   is taken too - and says so - because letting it through would select nothing
   and disarm nothing, which is a click that appears to have been ignored. */
function cpinTake(tile){
  const p = state.cpin, c = state.cmap;
  if(!p || !c) return false;
  const game = cpinGame(tile, c.man.width, c.man.height);
  if(!game){
    toast(`That is off the ${c.man.width}×${c.man.height} map - pick a tile on it, `
      + 'or press Esc', 4000);
    return true;
  }
  state.cpin = null;
  cpinPaint();
  c.saidRead = null;
  cmapPaint();
  const fn = typeof window !== 'undefined' ? window[p.fn] : null;
  if(typeof fn !== 'function'){
    toast(`✗ nothing is listening for ${p.what} any more`, 5000);
    return true;
  }
  activity('map pin', `${p.what} -> ${game[0]},${game[1]}`);
  fn(...p.args, game, tile.slice());
  return true;
}

/* The button, for a caller's HTML. `fn` and `args` as `cpinArm` takes them;
   `args` must be numbers or plain strings, because they are written into an
   onclick attribute. Pressed a second time while it is the thing being picked,
   it stops. */
function cpinButton(what, fn, args){
  const a = JSON.stringify(Array.isArray(args) ? args : []);
  const on = state.cpin && state.cpin.fn === fn
    && JSON.stringify(state.cpin.args) === a;
  // A double-quoted attribute with the JSON's own quotes escaped, so a sentence
  // with an apostrophe in it - "Denethor's position" - cannot end it early:
  // `esc` turns `"` into `&quot;`, which the attribute gives back to the script.
  return `<button class="cpinbtn${on ? ' on' : ''}" onclick="cpinToggle(${
    esc(JSON.stringify(String(what)))}, ${esc(JSON.stringify(fn))}, ${esc(a)})"
    title="Pick ${esc(what)} on the map: the next click writes its tile here.
Nothing on the map is selected by it. Esc stops.">⌖</button>`;
}

function cpinToggle(what, fn, args){
  const p = state.cpin;
  if(p && p.fn === fn && JSON.stringify(p.args) === JSON.stringify(args || []))
    cpinCancel();
  else cpinArm(what, fn, args);
}

/* The banner over the map, and the cursor. The tile under the pointer is said
   by the corner readout, which is already written on every move - see
   `cmapReadout` - so this is static and only rebuilt when the pin changes. */
function cpinPaint(){
  const stage = document.getElementById('cmStage');
  if(stage) stage.classList.toggle('cpinning', !!state.cpin);
  const el = document.getElementById('cmPin');
  if(el){
    const p = state.cpin;
    el.hidden = !p;
    el.innerHTML = p ? `⌖ Click the tile for <b>${esc(p.what)}</b>
      <button onclick="cpinCancel()" title="Esc">Cancel</button>` : '';
  }
  // the buttons that armed it light up, wherever they are
  if(typeof cxPaint === 'function') cxPaint();
  if(typeof cevPaint === 'function' && state.cev) cevPaint();
}
