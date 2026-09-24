"""Phase 55b: a battle model that moves - the chain, and the skin.

    python -m tests.test_v3anim

`web/js/v3anim.js` samples an animation and skins the model in the page. Its
GL calls are only answerable by a GPU; the arithmetic between the files and the
buffer is not, and that is what this holds, by running the real file under node:

1. The page loads v3anim.js after viewer3d.js, and the viewer calls it.
2. The geometry payload carries the skin: two weights a vertex, and the two
   bone bytes unpacked from the file's BGRA order (the first weight's bone is
   the THIRD byte), on a fixture and on a real soldier.
3. descr_skeleton.txt: the parse, the loose/packed split, and the cache.
4. v3aSample against casanim.sample - on fixtures, and on real files at many
   times - so the page's mirror cannot drift from the reference. And
   v3aTravel: a walk is a cycle that travels and is played in place, a death
   is not a cycle.
5. The whole skin of a real DaC soldier in his idle, against a reference skin
   written here in Python: the same vertices to within float rounding, and a
   man who stands - arms down out of the T, feet on the ground.
"""
import json
import math
import re
import shutil
import struct
import subprocess
import sys
from array import array
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from unittransfer import casanim, mesh  # noqa: E402

MODS = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition/mods")
DAC = MODS / "Divide_and_Conquer_EUR" / "data"
ROCSS = MODS / "ROCSS" / "data"
JS = ROOT / "web" / "js" / "v3anim.js"
ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


# ---- 1) wiring -----------------------------------------------------------------
print("\n1) the page loads it, and the viewer calls it")
html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
tags = re.findall(r'<script src="js/([^"]+)"></script>', html)
check("index.html loads v3anim.js after viewer3d.js",
      "v3anim.js" in tags and tags.index("v3anim.js") > tags.index("viewer3d.js"))
v3src = (ROOT / "web" / "js" / "viewer3d.js").read_text(encoding="utf-8")
check("the viewer parses the skin, steps the pose each frame and asks for the actions",
      "head.joints" in v3src and "v3AnimStep()" in v3src and "v3AnimInit()" in v3src
      and 'id="v3anim"' in v3src)

# ---- 2) the payload ------------------------------------------------------------
print("\n2) the geometry payload carries the skin")


def parse_payload(raw: bytes):
    """What v3Parse does, in Python."""
    assert raw[:4] == b"M2GT"
    hlen, = struct.unpack_from("<I", raw, 4)
    head = json.loads(raw[8:8 + hlen])
    at, n = 8 + hlen, head["vertices"]
    at += n * 12
    if head["has_normals"]:
        at += n * 12
    if head["has_uvs"]:
        at += n * 8
    w = None
    if head["skinned"]:
        w = array("f")
        w.frombytes(raw[at:at + n * 8])
        at += n * 8
    at += sum(g["count"] for g in head["groups"]) * 2
    j = None
    if head["skinned"]:
        j = raw[at:at + n * 2]
        at += n * 2
    return head, w, j, at == len(raw)


m = mesh.MeshFile(source="fixture.mesh", format="mesh")
m.positions = array("f", [0.0] * 9)
m.groups = [mesh.MeshGroup("Body", "b", array("H", [0, 1, 2]))]
m.bones = ["bone_pelvis", "bone_head", "bone_Rhand"]
m.weights = array("f", [1.0, 0.0, 0.7, 0.3, 0.5, 0.5])
m.bone_ids = bytes([0, 0, 0, 0,  0, 1, 2, 0,  0, 2, 1, 0])
head, w, j, whole = parse_payload(mesh.geometry_payload(m))
check("a skinned fixture says so, and the payload is exactly as long as it says",
      head["skinned"] and whole)
check("the bones are unpacked first-weight-first: the file's third byte, then its second",
      list(j) == [0, 0, 2, 1, 1, 2])
check("the weights come through as written", [round(x, 3) for x in w] == [1, 0, 0.7, 0.3, 0.5, 0.5])
m.weights, m.bone_ids = array("f"), b""
head, w, j, whole = parse_payload(mesh.geometry_payload(m))
check("a model with no skin streams is not skinned, and nothing extra is sent",
      not head["skinned"] and whole and w is None)

SOLDIER = DAC / "unit_models" / "_Units" / "GAW" / "lamedon_clansmen_ug0_lod0.mesh"
soldier = None
if SOLDIER.is_file():
    soldier = mesh.read_mesh(SOLDIER)
    head, w, j, whole = parse_payload(mesh.geometry_payload(soldier))
    n = soldier.vertices
    check(f"a DaC soldier: {n:,} vertices, skinned, and the payload adds up", head["skinned"] and whole)
    check("his weights sum to one on every vertex",
          all(abs(w[i * 2] + w[i * 2 + 1] - 1) < 1e-3 for i in range(n)))
    check("and every bone byte names one of his 26 bones",
          len(soldier.bones) == 26 and max(j) < 26)
else:
    print("  -- DaC is not installed; the real soldier is SKIPPED")

# ---- 3) descr_skeleton.txt ----------------------------------------------------
print("\n3) the chain: descr_skeleton.txt, loose and packed")
tmp = Path(_tmp.mkdtemp(prefix="ut_v3anim_")) / "data"
(tmp / "animations" / "Mine").mkdir(parents=True)
(tmp / "animations" / "Mine" / "Mine_Walk.cas").write_bytes(b"x")
(tmp / "descr_skeleton.txt").write_text(
    "; comment\nVersion 14\n\ntype   Mine_Skel   ; a note\nscale  1.30\n"
    "anim  stand   mods/Other/data/animations/mine/mine_stand.cas  -fr\n"
    "anim  walk    mods/Other/data/animations/MINE/mine_walk.CAS  -fr -evt:x.evt\n",
    encoding="latin-1")
v = casanim.actions_view(tmp, ["MINE_SKEL", "nobody"])
s0, s1 = v["skeletons"]
check("a type is found case-blind, with its scale", s0["found"] and s0["scale"] == 1.3)
check("an action whose file is loose gets its real path; one that is not gets none",
      [a["rel"] for a in s0["actions"]] == ["", "animations/Mine/Mine_Walk.cas"]
      and s0["loose"] == 1)
check("a skeleton the file does not have is said to be missing", not s1["found"])
(tmp / "animations" / "Mine" / "Mine_Stand.cas").write_bytes(b"x")
check("a file added since the last look is found (the index notices its folder changed)",
      casanim.actions_view(tmp, ["Mine_Skel"])["skeletons"][0]["loose"] == 2)

if DAC.is_dir():
    sk = casanim.actions_view(DAC, ["MTW2_Mace"])["skeletons"][0]
    if sk.get("unpacked"):
        # 2026-09-23: DaC's pack unpacked in place, every file nested under
        # animations/mods/<mod>/data/animations, replacing the loose tree
        check(f"DaC's MTW2_Mace: {sk['loose']} of {len(sk['actions'])} actions found, "
              f"{sk['unpacked']} of them in the unpacked pack (measured 195 of 195)",
              sk["loose"] == sk["unpacked"] == 195 and len(sk["actions"]) == 195)
    else:
        check(f"DaC's MTW2_Mace: {sk['loose']} of {len(sk['actions'])} actions loose "
              f"(measured 156 of 195)", sk["loose"] == 156 and len(sk["actions"]) == 195)
if ROCSS.is_dir():
    sk = casanim.actions_view(ROCSS, ["MTW2_Fast_Bowman"])["skeletons"][0]
    check(f"ROCSS's MTW2_Fast_Bowman: all {len(sk['actions'])} packed, none loose",
          sk["found"] and sk["loose"] == 0 and sk["actions"])

# ---- 4) and 5) under node -----------------------------------------------------
HARNESS = r"""
const fs = require('fs');
const vm = require('vm');
const ctx = {console, Math, Float32Array, Uint8Array, Map, Set};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), ctx);
const job = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const out = {samples: [], skin: null, travel: job.travel.map(a => ctx.v3aTravel(a))};
for(const s of job.samples){
  out.samples.push(s.times.map(t => ctx.v3aSample(s.anim, t)));
}
if(job.skin){
  const k = job.skin, g = k.geo;
  g.positions = Float32Array.from(g.positions);
  g.normals = Float32Array.from(g.normals);
  g.weights = Float32Array.from(g.weights);
  g.joints = Uint8Array.from(g.joints);
  const bm = ctx.v3aBoneMap(g.bones, k.anim);
  const pos = new Float32Array(g.vertices * 3), nrm = new Float32Array(g.vertices * 3);
  ctx.v3aSkin(g, ctx.v3aPose(k.anim, k.t), ctx.v3aBind(k.anim), bm.map, pos, nrm, [0, k.lift, 0]);
  out.skin = {pos: Array.from(pos), nrm: Array.from(nrm), missing: bm.missing};
}
fs.writeFileSync(process.argv[4], JSON.stringify(out));
"""

node = shutil.which("node")


def fixture_anim():
    a = casanim.Animation(source="fixture.cas", length=1.0,
                          key_times=array("f", [0.0, 0.5, 1.0]))
    q0, q1 = (0.0, 0.0, 0.0, 1.0), (0.0, 0.0, math.sin(math.pi / 4), math.cos(math.pi / 4))
    a.tracks = [
        casanim.Track("Scene Root", -1, (0.0, 0.0, 0.0)),
        casanim.Track("bone_pelvis", 0, (0.0, 0.0, 0.0), rot=array("f", q0 + q1 + q0),
                      pos=array("f", [0, 1, 0, 0, 2, 0, 0, 1, 0])),
        casanim.Track("bone_head", 1, (0.0, 0.5, 0.0), rot=array("f", q1)),
        # 3.02 engines: a track that keys fewer times than the file, last one holds
        casanim.Track("bone_arm", 1, (0.3, 0.0, 0.0), rot=array("f", q1 + (0.0, 0.0, 0.0, 2.0))),
    ]
    return a


def mace(fname):
    """One of DaC's MTW2_Mace files: loose where the mod ships it loose, else out
    of the pack DaC had unpacked in place on 2026-09-23, read with the
    skeleton's bones. None when the mod has neither."""
    loose = DAC / "animations" / "MTW2_Mace" / fname
    if loose.is_file() and casanim.packed_counts(loose.read_bytes()) is None:
        return casanim.read_anim(loose)
    if not DAC.is_dir():
        return None
    rows = casanim.actions_view(DAC, ["MTW2_Mace"])["skeletons"][0]["actions"]
    row = next((r for r in rows if r["rel"].lower().endswith("/" + fname.lower())), None)
    return casanim.read_anim(DAC / row["rel"], "MTW2_Mace", DAC) if row else None


samples = [("fixture", fixture_anim(), [0.0, 0.1, 0.25, 0.5, 0.8, 1.0, 1.3, 2.75])]
for fname in ("MTW2_Mace_stand_A_idle.cas", "MTW2_Mace_walk.cas", "MTW2_Mace_die_forward_1.cas"):
    a = mace(fname)
    if a is not None:
        end = a.key_times[-1]
        samples.append((fname, a, [end * f for f in (0, 0.013, 0.31, 0.5, 0.77, 0.999, 1.4)]))


from tests._skinref import reference_skin  # noqa: E402


# a cycle closes and travels; a death does not close (measured on MTW2_Mace:
# the walk carries the pelvis 1.62 forward, the charge 2.58)
travel = [(f, a) for f, a in ((f, mace(f)) for f in ("MTW2_Mace_walk.cas", "MTW2_Mace_charge.cas",
                                                      "MTW2_Mace_stand_A_idle.cas",
                                                      "MTW2_Mace_die_forward_1.cas"))
          if a is not None]

idle = mace("MTW2_Mace_stand_A_idle.cas")
skin_job = None
if soldier is not None and idle is not None:
    head = json.loads(mesh.geometry_payload(soldier)[8:8 + struct.unpack_from(
        "<I", mesh.geometry_payload(soldier), 4)[0]])
    ids = soldier.bone_ids
    joints = [0] * (soldier.vertices * 2)
    joints[0::2] = list(ids[2::4])
    joints[1::2] = list(ids[1::4])
    skin_job = {"t": 0.37, "lift": head["min"][1], "anim": idle.view(),
                "geo": {"vertices": soldier.vertices, "bones": soldier.bones,
                        "positions": list(soldier.positions), "normals": list(soldier.normals),
                        "weights": list(soldier.weights), "joints": joints}}

print("\n4) v3aSample, run in node, against casanim.sample")
if not node:
    print("  -- node is not on PATH, so the page's arithmetic is SKIPPED")
else:
    job = {"samples": [{"anim": a.view(), "times": ts} for _, a, ts in samples],
           "skin": skin_job, "travel": [a.view() for _, a in travel]}
    t = Path(_tmp.mkdtemp(prefix="ut_v3anim_node_"))
    (t / "harness.js").write_text(HARNESS, encoding="utf-8")
    (t / "job.json").write_text(json.dumps(job), encoding="utf-8")
    r = subprocess.run([node, str(t / "harness.js"), str(JS), str(t / "job.json"),
                        str(t / "out.json")], capture_output=True, text=True)
    check("the harness runs", r.returncode == 0)
    if r.returncode:
        print(r.stderr[-1500:])
    res = json.loads((t / "out.json").read_text()) if r.returncode == 0 else {"samples": [], "skin": None}
    for (label, a, ts), got in zip(samples, res["samples"]):
        worst = 0.0
        for tm, frame in zip(ts, got):
            ref = casanim.sample(a, tm)
            for rb, gb in zip(ref, frame):
                # q and -q are one rotation, so compare up to sign
                dq = min(max(abs(x - y) for x, y in zip(rb["rot"], gb["q"])),
                         max(abs(x + y) for x, y in zip(rb["rot"], gb["q"])))
                dp = max(abs(x - y) for x, y in zip(rb["pos"], gb["p"]))
                worst = max(worst, dq, dp)
        check(f"{label}: {len(ts)} times x {len(a.tracks)} bones agree (worst {worst:.1e})",
              worst < 1e-5)

    got = dict(zip([f for f, _ in travel], res.get("travel", [])))
    if len(got) == 4:
        w, c = got["MTW2_Mace_walk.cas"], got["MTW2_Mace_charge.cas"]
        idle_t, die_t = got["MTW2_Mace_stand_A_idle.cas"], got["MTW2_Mace_die_forward_1.cas"]
        check(f"a walk and a charge are cycles that travel (walk {w}, charge {c}), "
              f"so they are played in place",
              w and abs(w[1] - 1.62) < 0.02 and c and abs(c[1] - 2.58) < 0.02)
        check(f"an idle is a cycle that goes nowhere ({idle_t}), and a death is "
              f"not a cycle ({die_t})",
              idle_t is not None and max(map(abs, idle_t)) < 0.01 and die_t is None)

    print("\n5) a real soldier skinned in his idle, against the skin written out here")
    if skin_job is None:
        print("  -- DaC's soldier or its idle is not installed; SKIPPED")
    elif res["skin"]:
        ref, ref_n = reference_skin(soldier, idle, skin_job["t"], skin_job["lift"])
        pos = res["skin"]["pos"]
        worst = max(abs(ref[v][c] - pos[v * 3 + c]) for v in range(len(ref)) for c in range(3))
        check(f"all {len(ref):,} vertices where the reference puts them (worst {worst:.1e})",
              worst < 1e-4)
        xs, ys = pos[0::3], pos[1::3]
        lo, hi = soldier.bounds()
        check(f"his arms come down out of the T: {hi[0] - lo[0]:.2f} wide as modelled, "
              f"{max(xs) - min(xs):.2f} in the idle", max(xs) - min(xs) < 0.6 * (hi[0] - lo[0]))
        check(f"he stands on the ground the still model stood on: lowest point "
              f"{min(ys):.3f} against {lo[1]:.3f}", abs(min(ys) - lo[1]) < 0.08)
        check(f"and is as tall as he was modelled: {max(ys) - min(ys):.2f} against "
              f"{hi[1] - lo[1]:.2f}", abs((max(ys) - min(ys)) - (hi[1] - lo[1])) < 0.1)
        # A normal between two bones is the blend of two turned unit vectors, so
        # it comes out SHORT where they disagree - the shader normalises it
        # (V3_FRAG), so only its direction is held here. How short is reported,
        # not judged: this soldier ships two vertices whose packed normal is
        # the zero vector (0.007 long unpacked), and no skin makes that longer.
        nrm = res["skin"]["nrm"]
        worst_n, shortest = 0.0, 9.0
        for v in range(len(ref)):
            a = nrm[v * 3:v * 3 + 3]
            la, lb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(x * x for x in ref_n[v]))
            shortest = min(shortest, la)
            if la > 0 and lb > 0:
                worst_n = max(worst_n, 1 - sum(x * y for x, y in zip(a, ref_n[v])) / (la * lb))
        check(f"every turned normal points where the reference turns it (worst 1-cos "
              f"{worst_n:.1e}; shortest blend {shortest:.2f})", worst_n < 1e-5)
        check("the bones the skeleton lacks are his weapon and shield bones, and only those",
              all("weapon" in b or "shield" in b for b in res["skin"]["missing"]))

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
