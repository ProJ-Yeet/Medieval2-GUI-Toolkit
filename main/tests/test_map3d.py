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

from unittransfer import mapvocab  # noqa: E402

JS = ROOT / "web" / "js" / "map3d.js"
WEB = ROOT / "web"

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


src = JS.read_text(encoding="utf-8")

# ---------------------------------------------------------------------------
print("\n== 1) the file is loaded, and loaded after the one it borrows from ==")

html = (WEB / "index.html").read_text(encoding="utf-8")
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

cm = (ROOT / "web" / "js" / "campmap.js").read_text(encoding="utf-8")
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
core = (ROOT / "web" / "js" / "core.js").read_text(encoding="utf-8")
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
print(f"\n{sum(ok)}/{len(ok)} checks - "
      f"{'ALL PASSED' if all(ok) else f'{len(ok) - sum(ok)} FAILED'}")
sys.exit(0 if all(ok) else 1)
