"""Phase 57b: a model out of the game's formats, and .texture to and from .dds.

    python -m tests.test_modelexport

1. ``.texture`` <-> ``.dds`` on real files: the DDS inside is the file past its
   48-byte header, a bare DDS passes through, anything else is refused.
2. A DaC soldier and two of his actions as a ``.glb``, read back: every
   accessor inside its buffer view, the skin's joints and weights, one inverse
   bind matrix a joint, the mirror applied (x negated, winding reversed), and
   each action's samplers the length of their keys.
3. The same soldier as an ``.obj`` zip: one v, vt and vn a vertex, the faces of
   the parts asked for and no others.
4. **Blender**, when it is installed: the ``.glb`` imported by stock Blender
   (``--factory-startup``), posed in its idle, against the reference skin in
   ``tests/_skinref.py`` - the same man, mirrored, to the millimetre.
"""
import glob
import io
import json
import shutil
import subprocess
import sys
import zipfile
from array import array
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from unittransfer import casanim, mesh  # noqa: E402
from unittransfer import modelexport as mx  # noqa: E402

MODS = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition/mods")
DAC = MODS / "Divide_and_Conquer_EUR" / "data"
SOLDIER = DAC / "unit_models" / "_Units" / "GAW" / "lamedon_clansmen_ug0_lod0.mesh"
ANIMS = DAC / "animations" / "MTW2_Mace"
ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return bool(cond)


# ---- 1) textures ------------------------------------------------------------------
print("\n1) .texture and .dds")
tex = next(iter(sorted((DAC / "unit_models").rglob("*.texture"))), None) if DAC.is_dir() else None
if tex is None:
    print("  -- no .texture installed; SKIPPED")
else:
    raw = tex.read_bytes()
    dds = mx.texture_to_dds(raw)
    check(f"{tex.name}: the DDS inside is the file past its 48-byte header", dds == raw[48:] and dds[:4] == b"DDS ")
    check("and wrapping it again gives a .texture that unwraps to the same DDS",
          mx.texture_to_dds(mx.dds_to_texture(dds)) == dds)
    check("a bare DDS named .texture comes back as it is", mx.texture_to_dds(dds) == dds)
for bad, fn, what in ((b"not an image at all" * 5, mx.texture_to_dds, ".texture"),
                      (b"PNG....", mx.dds_to_texture, "DDS")):
    try:
        fn(bad)
        check(f"something that is not a {what} is refused", False)
    except mx.ExportError:
        check(f"something that is not a {what} is refused", True)

if not SOLDIER.is_file():
    print("\nDaC's soldier is not installed - the model half is SKIPPED")
    print(f"\n{sum(ok)}/{len(ok)} checks passed")
    sys.exit(0 if all(ok) else 1)

# ---- 2) the .glb -----------------------------------------------------------------
print("\n2) a DaC soldier and two actions, as a .glb")
m = mesh.read_mesh(SOLDIER)


def mace(action, fname):
    """One of MTW2_Mace's actions, loose where the mod ships it loose, else out
    of the pack DaC had unpacked in place on 2026-09-23 (read with the
    skeleton's bones)."""
    loose = ANIMS / fname
    if loose.is_file() and casanim.packed_counts(loose.read_bytes()) is None:
        return casanim.read_anim(loose)
    rows = casanim.actions_view(DAC, ["MTW2_Mace"])["skeletons"][0]["actions"]
    row = next(r for r in rows if r["action"].lower() == action and r["rel"])
    return casanim.read_anim(DAC / row["rel"], "MTW2_Mace", DAC)


base = mace("default", "MTW2_Mace_basepose.cas")
idle = mace("stand_a_idle", "MTW2_Mace_stand_A_idle.cas")
walk = mace("walk", "MTW2_Mace_walk.cas")
parts = [0, 1, 2, 3, 5, 8]
glb = mx.export_glb(m, name="lamedon", groups=parts, skeleton=base,
                    animations=[("stand_a_idle", idle), ("walk", walk)])
js, binary = mx.read_glb(glb)
sizes = {5126: 4, 5121: 1, 5123: 2}
comps = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
inside = all(
    js["bufferViews"][a["bufferView"]]["byteLength"] >= a["count"] * comps[a["type"]] * sizes[a["componentType"]]
    and js["bufferViews"][a["bufferView"]]["byteOffset"] + js["bufferViews"][a["bufferView"]]["byteLength"] <= len(binary)
    for a in js["accessors"])
check(f"{len(js['accessors'])} accessors, every one inside its buffer view and the buffer", inside)


def acc(i, fmt):
    a = js["accessors"][i]
    v = js["bufferViews"][a["bufferView"]]
    out = array(fmt)
    out.frombytes(binary[v["byteOffset"]:v["byteOffset"] + v["byteLength"]])
    return out


prims = js["meshes"][0]["primitives"]
check(f"one primitive a part asked for ({len(prims)} of {len(parts)})", len(prims) == len(parts))
at = prims[0]["attributes"]
pos = acc(at["POSITION"], "f")
check("positions are mirrored in x", pos[0] == -m.positions[0] and pos[1] == m.positions[1])
idx = acc(prims[0]["indices"], "H")
g0 = m.groups[parts[0]].indices
check("and every triangle's winding is reversed", list(idx[:3]) == [g0[0], g0[2], g0[1]])
sk = js["skins"][0]
check(f"the skin has a joint a bone of the skeleton ({len(sk['joints'])}) and an inverse bind each",
      len(sk["joints"]) == len(base.tracks) == js["accessors"][sk["inverseBindMatrices"]]["count"])
jts = acc(at["JOINTS_0"], "B")
wts = acc(at["WEIGHTS_0"], "f")
check("every joint index names a joint", max(jts) < len(sk["joints"]))
check("every vertex's weights sum to one",
      all(abs(sum(wts[v * 4:v * 4 + 4]) - 1) < 1e-4 for v in range(m.vertices)))
names = [a["name"] for a in js["animations"]]
check(f"both actions are in it ({names})", names == ["stand_a_idle", "walk"])
good = all(js["accessors"][s["input"]]["count"] == js["accessors"][s["output"]]["count"]
           for a in js["animations"] for s in a["samplers"])
check("each sampler's times and values are the same length", good)
still = mx.export_glb(m, name="still")
check("without a skeleton the model goes out static: no skin, no joints",
      "skins" not in mx.read_glb(still)[0])

# ---- 3) the .obj ------------------------------------------------------------------
print("\n3) the same soldier as an .obj zip")
z = zipfile.ZipFile(io.BytesIO(mx.export_obj_zip(m, name="lamedon", groups=parts,
                                                 texture_png=b"\x89PNG fake")))
obj = z.read("lamedon.obj").decode().splitlines()
count = lambda tag: sum(1 for l in obj if l.startswith(tag + " "))
check(f"one v, vt and vn a vertex ({m.vertices:,})",
      count("v") == count("vt") == count("vn") == m.vertices)
check("the faces of the parts asked for and no others",
      count("f") == sum(len(m.groups[g].indices) // 3 for g in parts))
check("with its .mtl and texture beside it", set(z.namelist()) == {"lamedon.obj", "lamedon.mtl", "lamedon.png"})

# ---- 4) Blender ---------------------------------------------------------------------
print("\n4) the .glb in Blender")
blender = shutil.which("blender") or next(iter(sorted(glob.glob("D:/Blender-*/blender.exe")
                                                      + glob.glob("C:/Program Files/Blender Foundation/*/blender.exe"),
                                                      reverse=True)), None)
if not blender:
    print("  -- Blender is not installed; SKIPPED")
else:
    tmp = Path(_tmp.mkdtemp(prefix="ut_modelexport_"))
    whole = mx.export_glb(m, name="lamedon", skeleton=base,
                          animations=[("stand_a_idle", idle), ("walk", walk)])
    (tmp / "m.glb").write_bytes(whole)
    (tmp / "check.py").write_text(r'''
import bpy, sys, json
path, out = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=path)
arm = [o for o in bpy.data.objects if o.type == "ARMATURE"][0]
body = [o for o in bpy.data.objects if o.type == "MESH" and o.find_armature()][0]
act = bpy.data.actions["stand_a_idle"]
arm.animation_data_create()
arm.animation_data.action = act
if hasattr(arm.animation_data, "action_slot") and getattr(act, "slots", None):
    arm.animation_data.action_slot = act.slots[0]
bpy.context.scene.frame_set(1)
dg = bpy.context.evaluated_depsgraph_get()
e = body.evaluated_get(dg); me = e.to_mesh()
pts = [list(e.matrix_world @ v.co) for v in me.vertices]
json.dump({"bones": len(arm.data.bones), "actions": sorted(a.name for a in bpy.data.actions),
           "verts": len(pts), "lo": [min(p[k] for p in pts) for k in range(3)],
           "hi": [max(p[k] for p in pts) for k in range(3)]}, open(out, "w"))
''', encoding="utf-8")
    r = subprocess.run([blender, "-b", "--factory-startup", "--python", str(tmp / "check.py"),
                        "--", str(tmp / "m.glb"), str(tmp / "out.json")],
                       capture_output=True, text=True, timeout=600)
    got = json.loads((tmp / "out.json").read_text()) if (tmp / "out.json").is_file() else None
    check(f"stock Blender imports it ({Path(blender).parent.name})", got is not None)
    if got:
        check(f"an armature of {got['bones']} bones and both actions",
              got["bones"] == len(base.tracks) and got["actions"] == ["stand_a_idle", "walk"])
        # the reference: test_v3anim's skin of the same idle at t=0, lift 0.
        # Blender turns glTF's Y-up into Z-up: its (x, y, z) is glTF (x, -z, y),
        # and glTF's x is the game's -x.
        from tests._skinref import reference_skin  # noqa: E402
        ref, _ = reference_skin(m, idle, 0.0, 0.0)
        lo = [min(-p[0] for p in ref), min(-p[2] for p in ref), min(p[1] for p in ref)]
        hi = [max(-p[0] for p in ref), max(-p[2] for p in ref), max(p[1] for p in ref)]
        worst = max(max(abs(a - b) for a, b in zip(lo, got["lo"])),
                    max(abs(a - b) for a, b in zip(hi, got["hi"])))
        check(f"posed in its idle, Blender's man is the viewer's man, mirrored: the box within "
              f"{worst * 1000:.1f} mm (height {got['hi'][2]:.3f})", worst < 0.002)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
