"""Three layers, read properly - Phase 20a: D8, T2 and T11.

    D8   the rivers lifted out of map_features.tga as their own overlay
    T2   the heights drawn as transparency instead of as grey
    T11  the number keys tick a layer, ten layers and ten keys

Two of the three are drawn in the browser, and that is why this suite has a
node half. `campmap.py` decodes and projects; the mask pass in `campmap.js`
punches, whitelists and ramps, and it is the only arithmetic 20a added. So the
real functions are loaded into a bare V8 context with a stubbed canvas and
handed pixels this file wrote - no browser, no DOM library, and no second copy
of the maths to test instead of the one that ships.

Four claims:

    one list of what a river is    mapvocab owns RIVER_CODES and mapcheck reads
                                   it. The overlay draws exactly the tiles the
                                   validator walks, because they are the same
                                   three colours from the same table
    ten layers, ten keys, and the  the digit travels with the layer in the
    server says which is which     manifest, so the panel cannot print a key
                                   the handler does not answer to
    a linear height ramp does not  the reason T2's ramp is the land's own
    work, measured                 distribution. Half the land on both installed
                                   maps is under 32 of 255, so alpha = the grey
                                   draws the continent at under 13%
    the mask pass does what the    the whitelist supersedes the hide set, the
    panel says it does             three river colours become one, and the count
                                   on the row is the tiles it drew

Four parts:

    1  the vocabulary both ends read a river out of
    2  the ten keys
    3  the browser's own arithmetic, in node, on pixels written here
    4  the same arithmetic on every installed map's real heights layer

    python -m tests.test_maplayers
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod
from unittransfer import campmap, mapcheck, mapvocab
from unittransfer.mod import Mod

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


JS = ROOT / "web" / "js" / "campmap.js"


# ---- 1) one list of what a river is made of ---------------------------------

print("\n== the vocabulary both ends read a river out of ==")

check("mapvocab owns the three river codes",
      mapvocab.RIVER_CODES == ("river", "river_crossing", "river_source"))
check("mapcheck reads that one rather than keeping a second",
      mapcheck.RIVER_CODES is mapvocab.RIVER_CODES)
check("every river code is a real feature in the table",
      all(mapvocab.feature(c) for c in mapvocab.RIVER_CODES))
check("a cliff, a volcano, a land bridge and `none` are not rivers",
      not any(c in mapvocab.RIVER_CODES
              for c in ("cliff", "volcano", "land_bridge", "none")))

rgbs = mapvocab.river_rgbs()
check("river_rgbs is the table's own colours, in code order",
      rgbs == [(0, 0, 255), (0, 255, 255), (255, 255, 255)])
check("is_river says yes to those three and no to the other four",
      all(mapvocab.is_river(c) for c in rgbs)
      and not any(mapvocab.is_river(mapvocab.feature(c)["rgb"])
                  for c in ("none", "cliff", "volcano", "land_bridge")))
check("a colour no table knows is not a river either - DaC's stray (1,1,1)",
      not mapvocab.is_river((1, 1, 1)))


# ---- 2) ten layers, ten keys ------------------------------------------------

print("\n== the number keys, and which layer each one ticks ==")

keys = campmap.HOTKEYS
check(f"one key per layer, and there are {len(campmap.LAYERS)} layers",
      len(keys) == len(campmap.LAYERS) == 10)
check("the ten digits, each used once",
      sorted(keys.values()) == sorted("1234567890"))
check("in declaration order, so 1 is the region layer and 0 is the last one",
      [keys[ly["code"]] for ly in campmap.LAYERS] == list("1234567890"))
check("the required layers are the five easiest keys",
      {keys[ly["code"]] for ly in campmap.LAYERS if ly["required"]} == set("12345"))


# ---- 3) the browser's own arithmetic ----------------------------------------

print("\n== the mask pass, run for real in node on pixels written here ==")

node = shutil.which("node")

#: The stubs `campmap.js` needs to run its pixel passes outside a browser: a
#: canvas that is a byte array, and an image that is the same. Everything else
#: in the file is untouched - these are the real functions.
HARNESS = r"""
const fs = require('fs');
const vm = require('vm');

function canvas(){
  const cv = {width: 0, height: 0, data: null};
  cv.getContext = () => ({
    imageSmoothingEnabled: true,
    drawImage(img){ cv.data = Uint8ClampedArray.from(img.data); },
    getImageData(){ return {data: cv.data}; },
    putImageData(im){ cv.data = im.data; },
  });
  return cv;
}
const ctx = {console, document: {createElement: () => canvas()}};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), ctx);

//: an <img> as this file's pixel passes read one
function image(w, h, px){
  const data = new Uint8ClampedArray(w * h * 4);
  for(let i = 0; i < w * h; i++){
    data[i * 4] = px[i][0]; data[i * 4 + 1] = px[i][1];
    data[i * 4 + 2] = px[i][2]; data[i * 4 + 3] = 255;
  }
  return {naturalWidth: w, naturalHeight: h, data};
}

const out = [];
const check = (label, cond) => out.push([!!cond, label]);
const job = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));

// ---- the manifest the screen is given -------------------------------------
const FEATURES = job.features, RIVERS = job.rivers;
const man = {width: 0, height: 0, vocab: {features: FEATURES, rivers: RIVERS}};

function screen(w, h, code, px, opts){
  const L = {def: {present: true, aligned: true, fit: 'tile'},
             on: true, opacity: 1, img: image(w, h, px), cv: null, px: null,
             hide: new Set((opts && opts.hide) || []),
             masked: null, maskKey: '', rivertiles: 0, ramp: null};
  const c = {man: Object.assign({}, man, {width: w, height: h}), layers: {},
             rivers: !!(opts && opts.rivers), riverRgb: (opts && opts.riverRgb) || [86, 180, 255],
             heightAlpha: !!(opts && opts.heightAlpha)};
  c.layers[code] = L;
  ctx.state = {cmap: c};
  return c;
}
const packed = rgb => (rgb[0] << 16) | (rgb[1] << 8) | rgb[2];

// ---- 3a) which colours are a river ----------------------------------------
{
  screen(1, 1, 'features', [[0, 0, 0]], {});
  const got = [...ctx.cmapRiverKeys()].sort((a, b) => a - b);
  const want = FEATURES.filter(f => RIVERS.includes(f.code))
    .map(f => packed(f.rgb)).sort((a, b) => a - b);
  check('cmapRiverKeys is exactly the manifest\'s river codes, and only those',
        got.length === 3 && JSON.stringify(got) === JSON.stringify(want));
}

// ---- 3b) the river overlay -------------------------------------------------
{
  // one row of every feature colour there is, twice over
  const table = FEATURES.map(f => f.rgb);
  const px = table.concat(table);
  const c = screen(px.length, 1, 'features', px,
                   {rivers: true, riverRgb: [10, 20, 30]});
  ctx.cmapMask(c, 'features');
  const L = c.layers.features, d = L.masked.data;
  let drawn = 0, wrong = 0;
  for(let i = 0; i < px.length; i++){
    const p = i * 4, isriver = RIVERS.includes(FEATURES[i % FEATURES.length].code);
    if(!isriver){ if(d[p + 3] !== 0) wrong++; continue; }
    drawn++;
    if(d[p + 3] !== 255 || d[p] !== 10 || d[p + 1] !== 20 || d[p + 2] !== 30) wrong++;
  }
  check('the river overlay draws the three river colours and punches the rest through',
        wrong === 0 && drawn === 6);
  check('and the count on the layer row is the tiles it drew',
        L.rivertiles === 6);
  check('the three colours become one - a crossing is not told from a source',
        new Set([...Array(px.length).keys()]
          .filter(i => d[i * 4 + 3] === 255)
          .map(i => `${d[i * 4]},${d[i * 4 + 1]},${d[i * 4 + 2]}`)).size === 1);
}
{
  // the whitelist supersedes the hide set: hiding the river colour itself must
  // not take it out of the overlay, because the overlay is not the hide set
  const table = FEATURES.map(f => f.rgb);
  const c = screen(table.length, 1, 'features', table,
                   {rivers: true, hide: [packed([0, 0, 255])]});
  ctx.cmapMask(c, 'features');
  check('a hidden colour decides nothing while the river overlay is on',
        c.layers.features.rivertiles === 3);
}
{
  const table = FEATURES.map(f => f.rgb);
  const c = screen(table.length, 1, 'features', table, {});
  check('with nothing on, the mask pass makes no copy at all',
        ctx.cmapModeKey(c, 'features') === '' &&
        (ctx.cmapMask(c, 'features'), c.layers.features.masked === null));
  c.rivers = true;
  const k1 = ctx.cmapModeKey(c, 'features');
  c.riverRgb = [1, 2, 3];
  check('and the composite\'s key changes with the colour, so a recolour redraws',
        k1 !== '' && ctx.cmapModeKey(c, 'features') !== k1);
}

// ---- 3c) the heights as transparency ---------------------------------------
{
  // a flat histogram: 1..250 once each, plus sea of both kinds
  const px = [];
  for(let v = 1; v <= 250; v++) px.push([v, v, v]);
  px.push([0, 0, 0]);            // sea, pure black
  px.push([41, 140, 233]);       // sea, not greyscale
  const c = screen(px.length, 1, 'heights', px, {heightAlpha: true});
  ctx.cmapMask(c, 'heights');
  const d = c.layers.heights.masked.data;
  let mono = true, last = -1;
  for(let v = 0; v < 250; v++){
    if(d[v * 4 + 3] < last) mono = false;
    last = d[v * 4 + 3];
  }
  check('darker is more transparent - the ramp never goes backwards', mono);
  check('sea is not on the ramp at all, greyscale or not',
        d[250 * 4 + 3] === 0 && d[251 * 4 + 3] === 0);
  const mid = d[124 * 4 + 3];
  check(`over an even spread the middle height is about half-opaque (${mid})`,
        Math.abs(mid - 128) <= 2);
  check('the lowest land is visible and the highest is nearly solid',
        d[0 * 4 + 3] > 0 && d[249 * 4 + 3] >= 250);
  check('the grey itself is left alone - it is the alpha that carries the height',
        d[124 * 4] === 125 && d[124 * 4 + 1] === 125 && d[124 * 4 + 2] === 125);
}

// ---- 3d) a real map's heights ----------------------------------------------
for(const m of job.maps){
  const raw = fs.readFileSync(m.path);
  const px = [];
  for(let i = 0; i < raw.length; i += 3) px.push([raw[i], raw[i + 1], raw[i + 2]]);
  const ramp = ctx.cmapHeightRamp(image(px.length, 1, px));
  const hist = new Float64Array(256);
  let land = 0, dim = 0;
  for(const [r, g, b] of px){
    if(r === 0 || r !== g || g !== b) continue;
    land++; hist[r]++;
    if(r < 33) dim++;                 // what a linear ramp would draw under 13%
  }
  let cum = 0, median = 0;
  for(let v = 1; v < 256 && !median; v++){ cum += hist[v]; if(cum * 2 >= land) median = v; }
  check(`${m.name}: the ramp counts the same land this file does, and the same `
        + `median off it (${median} of 255)`,
        ramp.land === land && ramp.median === median);
  check(`${m.name}: half its land is no higher than ${median} of 255, so a linear `
        + `ramp draws ${(dim * 100 / land).toFixed(0)}% of it under 13% alpha`,
        dim * 2 >= land);
  check(`${m.name}: this ramp puts that median tile at `
        + `${(ramp.alpha[median] * 100 / 255).toFixed(0)}% instead`,
        ramp.alpha[median] >= 108 && ramp.alpha[median] <= 148);
  let mono = true;
  for(let v = 2; v < 256; v++) if(ramp.alpha[v] < ramp.alpha[v - 1]) mono = false;
  check(`${m.name}: and it is still monotonic, so no two heights swap places`, mono);
}

fs.writeFileSync(process.argv[4], JSON.stringify(out));
"""


def heights_raw(cm: campmap.CampaignMap, into: Path) -> int:
    """This map's heights layer at tile fit, as raw RGB for the node half.

    Through :func:`campmap.tile_view`, so they are the pixels the browser is
    served rather than a second sampling of the file.
    """
    img = campmap.tile_view(cm, "heights").convert("RGB")
    into.write_bytes(img.tobytes())
    return img.width * img.height


if not node:
    print("  [skip] node is not on PATH, and the mask pass runs in it")
else:
    with tempfile.TemporaryDirectory(prefix="ut_layers_") as td:
        tmp = Path(td)
        maps = []
        for m in _realmod.installed():
            if not (m / "data/world/maps/base/map_heights.tga").exists():
                continue
            try:
                cm = campmap.CampaignMap(Mod(m))
                raw = tmp / f"{m.name}.rgb"
                heights_raw(cm, raw)
            except Exception as exc:                     # a mod with a broken map
                print(f"  [skip] {m.name}: {exc}")
                continue
            maps.append({"name": m.name, "path": str(raw)})
        job = tmp / "job.json"
        job.write_text(json.dumps({
            "features": [{"code": f["code"], "rgb": list(f["rgb"])}
                         for f in mapvocab.FEATURES],
            "rivers": list(mapvocab.RIVER_CODES),
            "maps": maps,
        }), encoding="utf-8")
        run = tmp / "harness.js"
        run.write_text(HARNESS, encoding="utf-8")
        res = tmp / "out.json"
        p = subprocess.run([node, str(run), str(JS), str(job), str(res)],
                           capture_output=True, text=True)
        if p.returncode != 0:
            check("the harness runs", False)
            print((p.stderr or p.stdout).strip()[:2000])
        else:
            for passed, label in json.loads(res.read_text(encoding="utf-8")):
                check(label, passed)
            if not maps:
                print("  [skip] no installed map to measure a real height ramp on")


# ---- 4) the manifest carries both of 20a's facts ----------------------------

print("\n== what the manifest hands the screen ==")

mod = _realmod.pick("Divide_and_Conquer_EUR", need="world/maps/base/descr_terrain.txt")
cm = campmap.CampaignMap(Mod(mod))
man = campmap.view(cm, mod.name)

check(f"{mod.name}: every layer travels with the key that ticks it",
      all(l["hotkey"] == campmap.HOTKEYS[l["code"]] for l in man["layers"]))
check("the ten keys arrive whole, none of them empty",
      sorted(l["hotkey"] for l in man["layers"]) == sorted("1234567890"))
check("the river codes travel with the vocabulary",
      man["vocab"]["rivers"] == list(mapvocab.RIVER_CODES))
check("and the feature table beside them, so the colours are looked up not guessed",
      all(any(f["code"] == c for f in man["vocab"]["features"])
          for c in man["vocab"]["rivers"]))

# the overlay's own claim, on this map: 16d says map_features.tga is nearly all
# black, and D8 exists because of it
leg = campmap.layer_legend(cm, "features")
riv = sum(k["count"] for k in leg["colours"]
          if k["code_name"] in mapvocab.RIVER_CODES)
blank = next((k["count"] for k in leg["colours"] if k["blank"]), 0)
print(f"  ... {mod.name}: {riv:,} river tiles of {leg['total']:,}, "
      f"and {blank * 100 / leg['total']:.1f}% of the layer means nothing")
check("the river tiles are a small part of a layer that is mostly nothing",
      riv > 0 and blank * 10 > leg["total"] * 9)


print(f"\n{sum(ok)}/{len(ok)} checks"
      + (" - ALL PASSED" if all(ok) else f" - {ok.count(False)} FAILED"))
sys.exit(0 if all(ok) else 1)
