"""Phase 80a: every animation a model has, in the Models viewer, from the packs.

    python -m tests.test_animview

1. The view of a DaC horse rider: its skeleton set, and every filled slot of
   each skeleton in skeletons.dat as an action, named, in a family, with its
   frames, duration, distance and speed and its slot's events.
2. A mod with no pack of its own plays vanilla's, and says so.
3. A packed action and the same action written out loose read the same keys,
   and the loose one is the one offered.
4. Every filled slot of a soldier, a horse, a rider and a weapon skeleton
   reads out of the pack on vanilla, ROCSS and DaC.
5. The page's arithmetic under node: a three-step sequence with and without
   overlap, the blend halfway through it, the pelvis pinned, a rider known.
"""
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from unittransfer import animpack, animview, casanim, skelslots  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402

GAME = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition")
DAC, ROCSS = GAME / "mods" / "Divide_and_Conquer_EUR", GAME / "mods" / "ROCSS"
JS = ROOT / "web" / "js" / "v3anim.js"
ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


def same_keys(a, b, tol=1e-5):
    if len(a.tracks) != len(b.tracks) or len(a.key_times) != len(b.key_times):
        return False
    for t in (0.0, a.length * 0.37, a.length * 0.81):
        for x, y in zip(casanim.sample(a, t), casanim.sample(b, t)):
            if any(abs(p - q) > tol for p, q in zip(x["rot"] + x["pos"], y["rot"] + y["pos"])):
                return False
    return True


if not (GAME / "data").is_dir():
    print("SKIPPED: vanilla is not installed here")
    sys.exit(0)

# ---- 1) a rider --------------------------------------------------------------------
print("\n1) a DaC horse rider")
if DAC.is_dir():
    dac = Mod(DAC)
    entry = dac.modeldb.get("ghash_rider_upg0")
    v = animview.entry_view(dac.data, entry)
    s0 = v["sets"][0]
    check("its set: horse, MTW2_HR_Spear / MTW2_HR_Non_Shield, a weapon skeleton each",
          (s0["mount"], s0["primary"], s0["secondary"], s0["primary_weapons"], s0["secondary_weapons"])
          == ("horse", "MTW2_HR_Spear", "MTW2_HR_Non_Shield", ["MTW2_HR_spear_Primary"],
              ["MTW2_Sword_Primary"]) and v["packs"] == "mod")
    packs = animpack.for_data(dac.data)
    sp = v["skeletons"]["mtw2_hr_spear"]
    filled = packs.skeleton("MTW2_HR_Spear").filled()
    check(f"MTW2_HR_Spear: {len(sp['actions'])} actions, one per filled slot, every one playable",
          len(sp["actions"]) == len(filled) == sp["playable"])
    check("each named by the slot table and put in a family",
          all(r["action"] == skelslots.label(r["slot"]) for r in sp["actions"])
          and {r["family"] for r in sp["actions"]} >= {"stand", "move", "attack", "die"})
    walk = next(r for r in sp["actions"] if r["action"] == "walk")
    e = packs.anims.first(walk["path"])
    a = packs.animation(walk["path"])
    check(f"the walk's stats are its pack entry's: {walk['frames']} frames, {walk['duration']} s",
          walk["frames"] == e.frames == a.frames and abs(walk["duration"] - a.duration) < 1e-3
          and abs(walk["distance"] - a.distance) < 1e-3)
    idle = next(r for r in sp["actions"] if r["action"] == "stand_a_idle")
    slot = packs.skeleton("MTW2_HR_Spear").slots[idle["slot"]]
    check("the slot's impact frame, turn limits and events come with it",
          idle["impact_frame"] == slot.impact_frame and len(idle["events"]) == len(slot.events)
          and idle["events"][0]["type"] == "sound"
          and idle["turn"] == [round(slot.min_turn * 180 / 32768, 1), round(slot.max_turn * 180 / 32768, 1)])
    check("the weapon skeletons are listed with their few actions",
          v["skeletons"]["mtw2_hr_spear_primary"]["packed"]
          and 1 <= len(v["skeletons"]["mtw2_hr_spear_primary"]["actions"]) <= 5)
    anim = animview.read(dac.data, "MTW2_HR_Spear", path=walk["path"])
    check(f"its keys straight out of pack.dat: {len(anim.tracks) - 1} bones, {len(anim.key_times)} keys",
          len(anim.tracks) == len(packs.skeleton("MTW2_HR_Spear").bones) + 1
          and len(anim.key_times) == walk["frames"])
    try:
        animview.read(dac.data, "no_such_skeleton", path=walk["path"])
        refused = False
    except casanim.AnimError as err:
        refused = "no_such_skeleton" in str(err)
    check("a skeleton the pack has not got is refused, by name", refused)

# ---- 2) vanilla's packs ------------------------------------------------------------
print("\n2) a mod with no pack plays vanilla's")
game = Path(_tmp.mkdtemp(prefix="ut_animview_"))
van = animpack.for_data(GAME / "data")
(game / "data" / "animations").mkdir(parents=True)
# a small "vanilla": one skeleton and its walk, not a copy of 2-50 MB packs
names = ["MTW2_2HSwordsman"]
sk_bytes = van.skels.read_entry(van.skels.first(names[0]))
walk_path = van.skeleton(names[0]).slots[11].path
an_bytes = van.animation_bytes(walk_path)


def write_pack(folder, stem, magic, items, v1, v2):
    entries, at, blobs = [], animpack.HEADER_SIZE, []
    for tmpl, data in items:
        entries.append(animpack.PackEntry(tmpl.name, at, len(data), tmpl.scale, tmpl.frames,
                                          tmpl.rot_bones, tmpl.pos_bones))
        blobs.append(data)
        at += len(data)
    idx = animpack.PackIndex(magic, entries, v1, v2)
    (folder / f"{stem}.idx").write_bytes(idx.to_bytes())
    (folder / f"{stem}.dat").write_bytes(idx.header() + b"".join(blobs))


write_pack(game / "data" / "animations", "skeletons", animpack.SKEL_MAGIC,
           [(van.skels.first(names[0]), sk_bytes)], 14, 24)
write_pack(game / "data" / "animations", "pack", animpack.ANIM_MAGIC,
           [(van.anims.first(walk_path), an_bytes)], 9, 0)
mod_data = game / "mods" / "NoPack" / "data"
mod_data.mkdir(parents=True)
packs, whose = animview.packs_for(mod_data)
check("the game's own packs, marked vanilla", whose == "vanilla" and packs.skeleton(names[0]) is not None)
sv = animview.skeleton_view(mod_data, names[0], packs, {})
check("its skeleton's filled slots are offered, the one in this small pack playable",
      sv["packed"] and sum(1 for r in sv["actions"] if r["playable"]) == 1)
check("and a data folder under no game has none", animview.packs_for(game / "loose")[1] == "")

# ---- 3) loose and packed -------------------------------------------------------------
print("\n3) the same action loose and packed")
packed = animview.read(mod_data, names[0], path=walk_path)
loose_at = mod_data / walk_path.split("data/", 1)[1]
loose_at.parent.mkdir(parents=True, exist_ok=True)
loose_at.write_bytes(casanim.write_anim(packed))
sv = animview.skeleton_view(mod_data, names[0], packs)
row = next(r for r in sv["actions"] if r["slot"] == 11)
check("a loose file at the slot's path is found and offered first", row.get("rel", "").endswith(
    Path(walk_path).name))
loose = animview.read(mod_data, names[0], rel=row["rel"])
check(f"{Path(walk_path).name}: the loose file and the pack entry give the same pose "
      "at three times, every bone", same_keys(packed, loose))
unpacked = mod_data / "animations" / "unpacked_copy.cas"
unpacked.write_bytes(an_bytes)
check("an unpacked pack entry under a .cas name is not taken for a loose file",
      not animview._truly_loose(unpacked) and animview._truly_loose(loose_at))

# ---- 4) the installs --------------------------------------------------------------
print("\n4) every filled slot reads, on the three installs")
kinds = {"soldier": ("MTW2_2HSwordsman", "MTW2_Swordsman", "MTW2_Mace"),
         "horse": ("fs_horse", "fs_fast_horse", "fs_horse_brawler"),
         "rider": ("MTW2_HR_Spear", "MTW2_HR_Lance"),
         "weapon": ("MTW2_Bow_Primary", "MTW2_Sword_Primary", "MTW2_HR_spear_Primary")}
for label, data in (("vanilla", GAME / "data"), ("ROCSS", ROCSS / "data"), ("DaC", DAC / "data")):
    if not data.is_dir():
        print(f"  SKIPPED: {label}")
        continue
    p, _w = animview.packs_for(data)
    done, bad = [], []
    for kind, cands in kinds.items():
        name = next((n for n in cands if p.skeleton(n) is not None), None)
        if name is None:
            continue
        sk = p.skeleton(name)
        for i, s in sk.filled():
            try:
                a = animview.read(data, name, path=s.path)
                if len(a.tracks) != len(sk.bones) + 1:
                    bad.append((name, i))
            except casanim.AnimError as err:
                bad.append((name, i, str(err)[:60]))
        done.append(f"{name} {len(sk.filled())}")
    check(f"{label}: {', '.join(done)}, every slot read with its skeleton's bones",
          len(done) == 4 and not bad)
    if bad:
        print("     ", bad[:4])

# ---- 5) under node ----------------------------------------------------------------
print("\n5) the page's arithmetic, under node")
node = shutil.which("node")
if not node:
    print("  -- node is not on PATH, so this is SKIPPED")
else:
    HARNESS = r"""
const fs = require('fs'), vm = require('vm');
const ctx = {console, Math, Float32Array, Uint8Array, Map, Set};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), ctx);
const job = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const [A, B, C] = job.anims;
const out = {};
out.over = ctx.v3aSeqPlan([A, B, C], 0.2);
out.flat = ctx.v3aSeqPlan([A, B, C], 0);
// end to end: at 0.3 s into the second, exactly the second's own pose
const segB = out.flat.segs[1];
out.flatB = ctx.v3aSeqSample([A, B, C], segB.start + 0.3, 0);
out.ownB = ctx.v3aSampleAt(B, 0.3);
// overlapped: halfway through the window, halfway between the two
const s1 = out.over.segs[1];
out.mid = ctx.v3aSeqSample([A, B, C], s1.start + s1.blend / 2, 0.2);
out.endA = ctx.v3aSampleAt(A, s1.start + s1.blend / 2);
out.startB = ctx.v3aSampleAt(B, s1.blend / 2);
out.slerp = out.endA.map((c, i) => ctx.v3aSlerp(c.q, out.startB[i].q, 0.5));
out.carried = job.anims.map(a => ctx.v3aCarried(a));
out.pose = ctx.v3aPoseOf(A.bones, ctx.v3aSample(A, 0.4)).length;
fs.writeFileSync(process.argv[4], JSON.stringify(out));
"""
    van_sk = van.skeleton("MTW2_2HSwordsman")
    rows = {skelslots.label(i): s.path for i, s in van_sk.filled()}
    trio = [animview.read(GAME / "data", "MTW2_2HSwordsman", path=rows[n])
            for n in ("stand_a_idle", "walk", "stand_a_idle")]
    rider_sk = next(n for n in kinds["rider"] if van.skeleton(n) is not None)
    rider = animview.read(GAME / "data", rider_sk,
                          path=dict((skelslots.label(i), s.path)
                                    for i, s in van.skeleton(rider_sk).filled())["stand_a_idle"])
    t = Path(_tmp.mkdtemp(prefix="ut_animview_node_"))
    (t / "h.js").write_text(HARNESS, encoding="utf-8")
    (t / "job.json").write_text(json.dumps({"anims": [x.view() for x in trio + [rider]]}),
                                encoding="utf-8")
    r = subprocess.run([node, str(t / "h.js"), str(JS), str(t / "job.json"), str(t / "out.json")],
                       capture_output=True, text=True)
    check("the harness runs", r.returncode == 0)
    if r.returncode:
        print(r.stderr[-1200:])
    else:
        o = json.loads((t / "out.json").read_text(encoding="utf-8"))
        lens = [x.length for x in trio]
        check(f"end to end the three last {sum(lens):.2f} s; overlapped, 0.4 s less",
              abs(o["flat"]["total"] - sum(lens)) < 1e-6
              and abs(o["over"]["total"] - (sum(lens) - 0.4)) < 1e-6)
        hub = 1
        same = all(all(abs(a - b) < 1e-6 for a, b in zip(x["q"], y["q"]))
                   for i, (x, y) in enumerate(zip(o["flatB"], o["ownB"])))
        check("without overlap, the second plays exactly as stored (every rotation)", same)
        check("  ... and the pelvis is pinned over the ground, its height kept",
              o["flatB"][hub]["p"][0] == 0 and o["flatB"][hub]["p"][2] == 0
              and abs(o["flatB"][hub]["p"][1] - o["ownB"][hub]["p"][1]) < 1e-6)
        mid_ok = all(all(abs(a - b) < 1e-5 for a, b in zip(x["q"], y))
                     for x, y in zip(o["mid"], o["slerp"]))
        check("with overlap, halfway through the window is halfway between the two", mid_ok)
        check("the rider's action is known as carried by its mount; the soldier's is not",
              o["carried"] == [False, False, False, True])
        check("a pose chained from a local one has every bone", o["pose"] == len(trio[0].tracks))

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
