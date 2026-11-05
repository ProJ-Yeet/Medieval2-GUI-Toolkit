"""M18, the map in 3D: the mesh, and the one rule it turns on.

`web/js/map3d.js` reads the heights layer and hands WebGL a surface. Almost all
of it is state, uniforms and buffer calls that only a GPU can answer for, and
those are not what this tests. What it tests is the arithmetic between the
layer's bytes and the buffer, which is pure and which is where the reference
tool got it wrong twice:

  * **which tiles are sea.** His rule is "the heights pixel is blue OR the
    ground type is one of the four water colours", ours is
    :func:`unittransfer.mapvocab.is_sea_height` - not greyscale, or black.
    `cm3Build` mirrors that rule in JavaScript, and a mirror is a thing that
    drifts, so this runs BOTH on the real installed maps and fails on the
    first tile they disagree about.
  * **how much of the map survives.** His mesh caps at 2048 steps and the 512
    it capped at before dropped one-pixel islands. Ours has one vertex per
    tile with no cap at all, because `descr_terrain.txt` caps a map below it -
    so this checks the vertex count IS the tile count on every installed map,
    and that the thinning fallback only ever appears where a 16-bit index
    would actually run out.

Node runs the real file; nothing here is a re-implementation. No browser, and
no game install needed for the first half.

    python -m tests.test_map3d
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests import _webtext  # noqa: E402

from unittransfer import mapvocab  # noqa: E402

JS = ROOT / "web" / "js" / "map3d.js"
WEB = ROOT / "web"

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


src = _webtext.read(JS)

# ---------------------------------------------------------------------------
print("\n== 1) the file is loaded, and loaded after the one it borrows from ==")

html = _webtext.read((WEB / "index.html"))
tags = re.findall(r'<script src="js/([^"]+)"></script>', html)
check("index.html loads map3d.js", "map3d.js" in tags)
check("after viewer3d.js, whose matrix helpers it calls",
      "viewer3d.js" in tags and "map3d.js" in tags
      and tags.index("viewer3d.js") < tags.index("map3d.js"))
check("and after campmap.js, whose state it reads",
      "campmap.js" in tags and tags.index("campmap.js") < tags.index("map3d.js"))
check("v3Program, v3Perspective and v3LookAt are viewer3d's, not copied here",
      "v3Program(" in src and "v3Perspective(" in src and "v3LookAt(" in src
      and "function v3Program" not in src and "function v3Perspective" not in src)

# ---------------------------------------------------------------------------
print("\n== 2) the screen reaches it the way it reaches every other late file ==")

cm = _webtext.read((ROOT / "web" / "js" / "campmap.js"))
check("campmap.js asks whether the mode is up through a typeof guard",
      "typeof cm3On === 'function'" in cm)
check("and the one texture hook is in cmapPaint, the funnel, not per caller",
      "typeof cm3Retexture === 'function'" in cm)
check("a stroke on the HEIGHTS remeshes rather than only retexturing",
      "cm3Remesh" in cm and "codes.indexOf('heights')" in cm)
check("the one way back turns the mode off and gives the context up",
      "cm3Stop" in cm and "c.d3 = null" in cm)
check("the height scale and the water ride in cmapLayerState, so a view keeps them",
      re.search(r"m\.d3 = \{height: c\.d3\.height, water:", cm) is not None)
check("but `on` does not - a saved view must not open a WebGL context",
      "m.d3 = {height" in cm and "on: c.d3.on" not in cm)
core = _webtext.read((ROOT / "web" / "js" / "core.js"))
check("a mode switch drops the orphaned scene, beside the model viewer's",
      "cm3DropOrphan" in core and "v3DropOrphan" in core)

# ---------------------------------------------------------------------------
print("\n== 3) the two faults this mode is written against, still guarded ==")

check("the build yields through cm3Yield, not a bare requestAnimationFrame",
      "function cm3Yield" in src
      and "await new Promise(ok => requestAnimationFrame(ok))" not in src)
check("  and cm3Yield races the frame against a timer, for a hidden tab",
      re.search(r"function cm3Yield\(\)\{.*?requestAnimationFrame\(go\).*?setTimeout\(go",
                src, re.S) is not None)
check("cm3Stop replaces the canvas after losing the context",
      "loseContext()" in src and "cm3FreshCanvas" in src)
check("  because a lost context is handed back to the next getContext",
      "cloneNode(false)" in src)

# ---------------------------------------------------------------------------
print("\n== 4) the mesh, run for real in node ==")

node = shutil.which("node")

HARNESS = r"""
const fs = require('fs');
const vm = require('vm');
const ctx = {console, document: {createElement: () => ({getContext: () => ({})})},
             state: {cmap: null}};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), ctx);

const job = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const out = [];

for(const m of job.maps){
  const raw = {w: m.w, h: m.h, data: Uint8ClampedArray.from(Buffer.from(m.rgba, 'base64'))};
  const mesh = ctx.cm3Build(raw, job.scale);
  // Which tiles the JS rule called sea, read back off the y it wrote.
  // BY THE SIGN and not by comparing against the floor value: the buffer is a
  // Float32Array and the floor is computed in float64, so `=== scale * -0.12`
  // is false for every tile on the map and the check would pass or fail for a
  // reason that has nothing to do with the rule. Land is `(r/255) * scale`,
  // which is never negative, and sea is the only thing put below zero.
  const sea = [];
  for(let i = 0; i < m.w * m.h; i++) if(mesh.pos[i * 3 + 1] < 0) sea.push(i);
  // every normal a unit vector, which is the one thing a bad central
  // difference silently would not be
  let worst = 0;
  for(let i = 0; i < m.w * m.h; i++){
    const p = i * 3;
    const L = Math.hypot(mesh.nrm[p], mesh.nrm[p + 1], mesh.nrm[p + 2]);
    worst = Math.max(worst, Math.abs(L - 1));
  }
  out.push({name: m.name, verts: mesh.pos.length / 3, count: mesh.count,
            big: mesh.big, sea, worstNormal: worst,
            uv0: [mesh.uv[0], mesh.uv[1]],
            maxIdx: mesh.idx.length ? Math.max(mesh.idx[0], mesh.idx[mesh.idx.length - 1]) : 0});
}

// the thinning fallback, on a map that would overflow a 16-bit index
const big = {w: 300, h: 300, data: new Uint8ClampedArray(300 * 300 * 4)};
for(let i = 0; i < 300 * 300; i++){ const p = i * 4;
  big.data[p] = big.data[p + 1] = big.data[p + 2] = 40; big.data[p + 3] = 255; }
const stride = Math.ceil(Math.sqrt(300 * 300 / 65535));
const thin = ctx.cm3Thin(big, stride);
out.push({thin: {stride, w: thin.w, h: thin.h,
                 verts: ctx.cm3Build(thin, 10).pos.length / 3}});

fs.writeFileSync(process.argv[4], JSON.stringify(out));
"""


def rgba_of(img):
    """A layer as the RGBA bytes `cmapRawOf` hands the browser."""
    import base64
    px = img.convert("RGB").tobytes()
    out = bytearray(len(px) // 3 * 4)
    for i in range(len(px) // 3):
        out[i * 4] = px[i * 3]
        out[i * 4 + 1] = px[i * 3 + 1]
        out[i * 4 + 2] = px[i * 3 + 2]
        out[i * 4 + 3] = 255
    return base64.b64encode(bytes(out)).decode("ascii")


maps = []
if node:
    from tests import _realmod
    from unittransfer import campmap
    from unittransfer.mod import Mod
    for root in _realmod.installed():
        try:
            cm = campmap.CampaignMap(Mod(root))
            img = campmap.tile_view(cm, "heights").convert("RGB")
        except Exception as e:                          # noqa: BLE001
            print(f"  -- {root.name}: [skip] {str(e)[:110]}")
            continue
        maps.append({"name": root.name, "w": img.width, "h": img.height,
                     "rgba": rgba_of(img), "img": img})

SCALE = 30.0

if not node:
    print("  -- node is not on PATH, so the mesh itself is not run")
elif not maps:
    print("  -- no installed map read, so the mesh is not run against one")
else:
    job = {"scale": SCALE,
           "maps": [{k: m[k] for k in ("name", "w", "h", "rgba")} for m in maps]}
    with tempfile.TemporaryDirectory(prefix="ut_map3d_") as tmp:
        t = Path(tmp)
        (t / "harness.js").write_text(HARNESS, encoding="utf-8")
        (t / "job.json").write_text(json.dumps(job), encoding="utf-8")
        r = subprocess.run([node, str(t / "harness.js"), str(JS),
                            str(t / "job.json"), str(t / "out.json")],
                           capture_output=True, text=True)
        check("the harness runs", r.returncode == 0)
        if r.returncode:
            print(r.stdout or "", r.stderr or "")
            got = []
        else:
            got = json.loads((t / "out.json").read_text(encoding="utf-8"))

    thin = next((g["thin"] for g in got if "thin" in g), None)
    by_name = {g["name"]: g for g in got if "name" in g}

    for m in maps:
        g = by_name.get(m["name"])
        if not g:
            continue
        w, h, img = m["w"], m["h"], m["img"]
        print(f"\n  -- {m['name']}  {w}x{h}")

        check(f"    one vertex per tile, no cap and no resampling ({w * h:,})",
              g["verts"] == w * h)
        check(f"    two triangles a quad ({6 * (w - 1) * (h - 1):,} indices)",
              g["count"] == 6 * (w - 1) * (h - 1))
        check("    a 32-bit index exactly when a 16-bit one would not reach",
              g["big"] == (w * h > 65535))
        check("    the last index names a real vertex",
              g["maxIdx"] < w * h)
        check("    a tile's UV is its centre, not its corner",
              abs(g["uv0"][0] - 0.5 / w) < 1e-9 and abs(g["uv0"][1] - 0.5 / h) < 1e-9)
        check("    every normal is a unit vector",
              g["worstNormal"] < 1e-5)

        # THE ONE THAT MATTERS: the JS sea rule against mapvocab's own.
        px = img.load()
        want = set()
        for y in range(h):
            for x in range(w):
                if mapvocab.is_sea_height(px[x, y]):
                    want.add(y * w + x)
        got_sea = set(g["sea"])
        extra = got_sea - want
        missing = want - got_sea
        check(f"    map3d.js and mapvocab.is_sea_height name the same "
              f"{len(want):,} sea tiles",
              not extra and not missing)
        if extra or missing:
            for i in sorted(extra)[:3]:
                print(f"       js says sea, python does not: "
                      f"({i % w},{i // w}) = {px[i % w, i // w]}")
            for i in sorted(missing)[:3]:
                print(f"       python says sea, js does not: "
                      f"({i % w},{i // w}) = {px[i % w, i // w]}")
        land = w * h - len(want)
        check(f"    and it is a real coastline, not all or nothing "
              f"({len(want):,} sea, {land:,} land)",
              0 < len(want) < w * h)

    if thin:
        print("\n  -- the 16-bit fallback, on a 300x300 map")
        check(f"    strided by {thin['stride']} rather than refused",
              thin["stride"] >= 2)
        check(f"    and the result fits a 16-bit index ({thin['verts']:,} vertices)",
              thin["verts"] <= 65535)

# ---------------------------------------------------------------------------
print("\n== 5) 97a: a click in 3D lands on the tile drawn under it ==")

cmjs = _webtext.read((ROOT / "web" / "js" / "campmap.js"))
check("the click goes through the flat map's own code, not a second copy",
      "cmapClickTile(tileOf(e), e.button, e.shiftKey)" in src
      and "function cmapClickTile" in cmjs
      and "cmapClickTile(cmapEventTile(cv, e), e.button, e.shiftKey)" in cmjs)
check("  and so do the hover, the marker drag and the brush",
      "cmapHover(tileOf(e))" in src and "cmkDragStart(tileOf(e))" in src
      and "cpaintDown(tileOf(e))" in src and "cmapMarkClick(tileOf(e), e.shiftKey)" in src)
check("the pick and the hover are redrawn from the one paint funnel",
      re.search(r"function cm3Retexture\(force\)\{.*?cm3Remark\(\);", src, re.S) is not None)

# Every tile of a synthetic map, projected to the screen through the very
# matrices cm3Draw uses and handed back to cm3Ray. The helpers are viewer3d's
# own text, cut out of the file rather than written again here.
v3src = _webtext.read(WEB / "js" / "viewer3d.js")
helpers = "\n".join(
    re.search(rf"function {n}\(.*?\n\}}", v3src, re.S).group(0)
    if n in ("v3Perspective", "v3LookAt", "v3Norm")
    else re.search(rf"function {n}\(.*?\}}\n", v3src).group(0)
    for n in ("v3Perspective", "v3LookAt", "v3Cross", "v3Dot", "v3Norm"))

RAY = r"""
const fs = require('fs');
const vm = require('vm');
const ctx = {console, document: {createElement: () => ({getContext: () => ({})})},
             state: {cmap: null}};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.argv[3], 'utf8'), ctx);
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), ctx);
const W = 120, H = 90, out = {};
// rolling land with a sea along the west edge
const raw = {w: W, h: H, data: new Uint8ClampedArray(W * H * 4)};
for(let y = 0; y < H; y++) for(let x = 0; x < W; x++){
  const p = (y * W + x) * 4;
  if(x < 14){ raw.data[p] = 0; raw.data[p + 1] = 0; raw.data[p + 2] = 255; }
  else { const v = 60 + Math.round(50 * Math.sin(x / 9) * Math.cos(y / 11));
         raw.data[p] = raw.data[p + 1] = raw.data[p + 2] = v; }
  raw.data[p + 3] = 255;
}
const run = (water, height) => {
  const d = {on: true, height, water, yaw: -0.6, pitch: 0.85, dist: 110, tx: 0, tz: 0};
  ctx.state.cmap = {man: {width: W, height: H}, d3: d};
  const mesh = ctx.cm3Build(raw, height);
  const canvas = {clientWidth: 800, clientHeight: 600, width: 800, height: 600};
  vm.runInContext('cm3 = __cm3', Object.assign(ctx, {__cm3: {gl: {canvas}, mesh, thinned: 0}}));
  const span = Math.hypot(W, H);
  const P = ctx.v3Perspective(0.96, 800 / 600, span / 500, span * 8);
  const V = ctx.v3LookAt(ctx.cm3Eye(d), [d.tx, 0, d.tz], [0, 1, 0]);
  const mul = (M, v) => [0, 1, 2, 3].map(i => M[i]*v[0] + M[4+i]*v[1] + M[8+i]*v[2] + M[12+i]*v[3]);
  let n = 0, exact = 0, near = 0, seaN = 0, seaNear = 0;
  for(let y = 2; y < H - 2; y += 3) for(let x = 2; x < W - 2; x += 3){
    const i = y * W + x;
    const c = mul(P, mul(V, [mesh.pos[i*3], mesh.pos[i*3+1], mesh.pos[i*3+2], 1]));
    const sx = (c[0] / c[3] + 1) / 2 * 800, sy = (1 - c[1] / c[3]) / 2 * 600;
    if(sx < 0 || sy < 0 || sx > 800 || sy > 600) continue;
    const t = ctx.cm3Ray(sx, sy), off = Math.abs(t[0] - x) + Math.abs(t[1] - y);
    if(x < 14){ seaN++; if(off <= 3) seaNear++; continue; }
    n++; if(off === 0) exact++; if(off <= 1) near++;
  }
  return {n, exact, near, seaN, seaNear, sky: ctx.cm3Ray(400, 1)};
};
out.flat = run(false, 0);
out.hills = run(false, 24);
out.water = run(true, 24);
fs.writeFileSync(process.argv[4], JSON.stringify(out));
"""

if not node:
    print("  -- node is not on PATH, so the ray is not run")
else:
    with tempfile.TemporaryDirectory(prefix="ut_map3d_ray_") as tmp:
        t = Path(tmp)
        (t / "ray.js").write_text(RAY, encoding="utf-8")
        (t / "v3.js").write_text(helpers, encoding="utf-8")
        r = subprocess.run([node, str(t / "ray.js"), str(JS), str(t / "v3.js"),
                            str(t / "out.json")], capture_output=True, text=True)
        check("the ray harness runs", r.returncode == 0)
        if r.returncode:
            print(r.stdout or "", r.stderr or "")
            ray = {}
        else:
            ray = json.loads((t / "out.json").read_text(encoding="utf-8"))
    for name, label in (("flat", "a flat map"), ("hills", "hills, no water")):
        g = ray.get(name)
        if not g:
            continue
        check(f"  {label}: every one of {g['n']} land tiles picks itself "
              f"({g['exact']} exact, {g['near']} within one)",
              g["n"] > 200 and g["near"] == g["n"] and g["exact"] >= g["n"] * 0.97)
        check(f"  {label}: the sky picks nothing", g["sky"] == [-1, -1])
    g = ray.get("water")
    if g:
        check(f"  with the water drawn, land still picks itself ({g['near']}/{g['n']})",
              g["near"] == g["n"])
        check(f"  and a sea tile is picked where the ray meets the surface, "
              f"a step or two short of the floor ({g['seaNear']}/{g['seaN']})",
              g["seaN"] > 0 and g["seaNear"] == g["seaN"])

# ---------------------------------------------------------------------------
print(f"\n{sum(ok)}/{len(ok)} checks - "
      f"{'ALL PASSED' if all(ok) else f'{len(ok) - sum(ok)} FAILED'}")
sys.exit(0 if all(ok) else 1)
