"""Keyforce Tools' bake of a TpacTool export, run in a hidden Blender.

    python -m tests.test_keyforce

1. finding Blender: the setting first, else the newest under Program Files
2. start: a missing folder, a wrong size and no Blender are refused
3. a Blender that dies without a result is reported with its exit code
4. the add-on shipped in vendor/keyforce is the Keyforce source's (when that
   folder is on this machine)
5. a real bake (only with KEYFORCE_REAL=<export folder>): Blender runs,
   one PNG per colour texture lands in <folder>/Pre-rendered
"""
import filecmp
import json
import re
import struct
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unittransfer import keyforce  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


def refused(fn):
    try:
        fn()
    except keyforce.KeyforceError as e:
        return str(e)
    return ""


print("1. finding Blender")
with tempfile.TemporaryDirectory() as t:
    t = Path(t)
    for v in ("Blender 4.5", "Blender 5.2", "Blender 5.10"):
        (t / "Blender Foundation" / v).mkdir(parents=True)
        (t / "Blender Foundation" / v / "blender.exe").write_bytes(b"")
    found = keyforce.find_blender("", [str(t)])
    check("the newest version (5.10 over 5.2)", Path(found).parent.name == "Blender 5.10")
    mine = t / "my blender.exe"
    mine.write_bytes(b"")
    check("the setting wins when the file is there", keyforce.find_blender(str(mine), [str(t)]) == str(mine))
    check("a setting that is gone falls back", Path(keyforce.find_blender(str(t / "gone.exe"), [str(t)])).parent.name
          == "Blender 5.10")
    check("none: empty", keyforce.find_blender("", [str(t / "nothing")]) == "")

print("2. start refuses")
with tempfile.TemporaryDirectory() as t:
    check("no folder", refused(lambda: keyforce.start(str(Path(t) / "gone"), 0, 2048, blender="x")))
    check("a size that is not offered", refused(lambda: keyforce.start(t, 0, 1000, blender="x")))
    real = keyforce.find_blender

    keyforce.find_blender = lambda *a, **k: ""
    try:
        check("no Blender", "Blender" in refused(lambda: keyforce.start(t, 0, 2048)))
    finally:
        keyforce.find_blender = real

print("3. a Blender that dies")
with tempfile.TemporaryDirectory() as t:
    # Python standing in for Blender: it refuses Blender's own arguments at once
    j = keyforce.start(t, 0, 512, blender=sys.executable)
    check("the job starts, writing to <folder>/Pre-rendered", Path(j["out"]) == Path(t) / "Pre-rendered")
    for _ in range(100):
        s = keyforce.status(j["job"])
        if s.get("done"):
            break
        time.sleep(0.1)
    check("reported done, with the exit code and the log's tail",
          s.get("done") and "exit code" in s.get("error", "") and s.get("log"))
    check("asked again: the same answer", keyforce.status(j["job"]) == s)
    check("an unknown job is refused", refused(lambda: keyforce.status("nope")))

print("4. the shipped add-on")
source = Path(r"C:\Users\projy\OneDrive - pcampus.edu.np\Models\EUR\Units\Keyforce\Scripts\keyforce_tools.py")
if source.is_file():
    check("vendor/keyforce/keyforce_tools.py is the Keyforce source", filecmp.cmp(
        source, keyforce.VENDOR / "keyforce_tools.py", shallow=False))
else:
    print("  (the Keyforce source is not on this machine: skipped)")
check("the job script is there", keyforce.JOB_SCRIPT.is_file())

print("5. Manual Bake's settings")
src = (keyforce.VENDOR / "keyforce_tools.py").read_text(encoding="utf-8")
mismatch = []
for key, kind, default, lo, hi, _step, _group in keyforce.ADVANCED:
    m = re.search(rf"\n    {key}: bpy\.props\.\w+Property\((.*?)\)\n    \w+: bpy\.props|\n    {key}: bpy\.props\.\w+Property\((.*?)\)\n\n",
                  src, re.S)
    body = (m.group(1) or m.group(2)) if m else ""
    d = re.search(r"default=(math\.radians\(([-\d.]+)\)|\"(\w+)\"|True|False|[-\d.]+)", body)
    if not d:
        mismatch.append((key, "no default"))
        continue
    raw = d.group(1)
    theirs = (float(d.group(2)) if d.group(2) else d.group(3) if d.group(3) else raw == "True" if raw in ("True", "False")
              else float(raw))
    if theirs != default:
        mismatch.append((key, theirs, default))
    rk = re.search(r"RECOMMENDED_KEYS = \((.*?)\)", src, re.S).group(1)
    if f'"{key}"' not in rk:
        mismatch.append((key, "not a recommended key"))
check(f"every default is the add-on's own, every key one Automatic Bake sets {mismatch}", not mismatch)
st = keyforce.settings_of({"bake_samples": 99999, "bake_tilt": -400, "world": "MARS", "bake_denoise": 0,
                           "bake_ambient": "x", "gap": 4})
check("held inside their ranges, unknowns and bad values dropped",
      st == {"bake_samples": 4096, "bake_tilt": -45.0, "bake_denoise": False})
check("the page's schema has every one", [f["key"] for f in keyforce.schema()] == [a[0] for a in keyforce.ADVANCED])

print("6. the Armory's own objects")
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
from unittransfer import armory  # noqa: E402

flat = np.zeros((4, 4, 4), np.uint8)
flat[..., 0] = flat[..., 1] = 128
flat[..., 3] = 255
check("a two-channel normal map gets its blue back (flat: 255)", (keyforce._full_normal(flat)[..., 2] == 255).all())
full = flat.copy()
full[..., 2] = 200
check("a full one is left as it is", keyforce._full_normal(full) is full)
check("bake sizes: the longer side, as an offered size",
      keyforce._bake_size(1000, 600) == 1024 and keyforce._bake_size(512, 512) == 512
      and keyforce._bake_size(9000, 10) == 4096)


def kit(t):
    """test_armlit's two quads on one texture, plus one with none."""
    armory.ARMORY_DIR = t / "armory"
    armory.SHEETS_DIR = armory.ARMORY_DIR / "sheets"
    grey = np.full((64, 64, 4), 128, np.uint8)
    grey[..., 3] = 255
    Image.fromarray(grey, "RGBA").save(t / "plate_d.png")
    nm = np.zeros((64, 64, 4), np.uint8)
    nm[..., :2], nm[..., 3] = 128, 255           # Bannerlord-style: blue empty
    Image.fromarray(nm, "RGBA").save(t / "plate_n.png")
    (t / "kit.obj").write_text("v 0 0 0\nv 1 0 0\nv 1 0 1\nv 0 0 1\nvt 0 0\nvt 0.5 0\nvt 0.5 1\nvt 0 1\nvn 0 1 0\n"
                               "o top\nf 1/1/1 2/2/1 3/3/1 4/4/1\no bare\nf 1/1/1 2/2/1 3/3/1 4/4/1\n", encoding="utf-8")
    asset = {"kind": "external", "path": str(t / "kit.obj"),
             "textures": {"0": str(t / "plate_d.png"), "1": str(t / "nothing.png")}}
    key = armory.asset_key(asset)
    return {"assets": [asset], "objects": [{"id": i + 1, "name": n, "mesh": n, "src": [{"asset": key, "group": i}]}
                                           for i, n in enumerate(("top", "bare"))]}


with tempfile.TemporaryDirectory() as t:
    t = Path(t)
    proj = kit(t)
    check("objects with no texture: refused", refused(lambda: keyforce.start_objects(proj, [2], None, blender="x")))
    j = keyforce.start_objects(proj, [1, 2], None, blender=sys.executable)
    J = keyforce.JOBS[j["job"]]
    files = sorted(p.name for p in J["folder"].iterdir())
    check(f"the job: the maps under the add-on's names, the mesh arrays ({files})",
          {"c0.png", "c0_n.png", "entry0.npz", "n0.png", "job.json"} <= set(files)
          and j["skipped"] == [{"id": 2, "why": "no_texture"}])
    check("a two-channel .png normal map gets its blue back (Blender rebuilds it only for a .dds)",
          (np.asarray(Image.open(J["folder"] / "c0_n.png"))[..., 2] == 255).all())
    arr = np.load(J["folder"] / "entry0.npz")
    check("UVs in Blender's 0-1, v up", np.allclose(sorted(set(np.round(arr["uv"][:, 1], 3))), [0.0, 1.0])
          and arr["uv"][:, 0].max() <= 0.5 + 1e-6)
    J["process"].wait()
    # what a finished Blender leaves: its PNG, at the bake's size
    (J["folder"] / "out").mkdir()
    Image.new("RGBA", (128, 128), (200, 10, 10, 255)).save(J["folder"] / "out" / "c0.png")
    (J["folder"] / "result.json").write_text(json.dumps({"results": [
        {"entry": 0, "path": str(J["folder"] / "out" / "c0.png"), "layers": 1, "skipped": 0}]}))
    s = keyforce.status(j["job"])
    b = (s.get("baked") or [{}])[0]
    out = Path(b.get("path", "x"))
    check("done: the lit texture at the source's size, under the armory's sheets",
          out.is_file() and Image.open(out).size == (64, 64) and armory.texture_allowed(str(out))
          and b["objects"] == [1] and b["normal"])
    check("its normal map beside it, for the export", out.with_name(out.stem + "_norm.png").is_file())

real_root = os.environ.get("KEYFORCE_REAL")
if real_root:
    print("7. the kit's object through Blender")
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        proj = kit(t)
        j = keyforce.start_objects(proj, [1], None, settings={"bake_samples": 8})
        while not (s := keyforce.status(j["job"])).get("done"):
            time.sleep(1)
        b = (s.get("baked") or [{}])[0]
        out = Path(b.get("path", "x"))
        img = np.asarray(Image.open(out).convert("RGBA")) if out.is_file() else None
        check(f"baked, no error ({s.get('error', '')})", img is not None and img.shape[:2] == (64, 64))
        check("the quad's texels lit, not black", img is not None and img[32, 10, :3].mean() > 40)
if real_root:
    print("8. a real bake of", real_root)
    with tempfile.TemporaryDirectory() as t:
        j = keyforce.start(real_root, 0, 512, out=t, glb=True, settings={"bake_samples": 8})
        while not (s := keyforce.status(j["job"])).get("done"):
            time.sleep(2)
        pngs = sorted(Path(t).glob("*.png"))
        check(f"no error ({s.get('error', '')})", not s.get("error"))
        check(f"one PNG per result ({len(pngs)})", pngs and len(pngs) == len(s.get("results") or []))
        glb = Path(s.get("glb") or "")
        if glb.is_file():
            data = glb.read_bytes()
            gl = json.loads(data[20:20 + struct.unpack_from("<I", data, 12)[0]])
            baked = {Path(r["path"]).stem for r in s["results"]}
            used = {i.get("name") for i in gl.get("images", [])}
            check(f"the .glb wears the baked textures ({len(baked & used)}/{len(baked)})", baked <= used)
        else:
            check("a .glb written", False)

print(f"\n{sum(ok)}/{len(ok)} passed")
sys.exit(0 if all(ok) else 1)
