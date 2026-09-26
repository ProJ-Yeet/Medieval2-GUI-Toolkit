"""Phase 80b: the unit as the game assembles it, in the Models viewer.

    python -m tests.test_animunit

1. The weapon skeletons: a ROCSS javelin man's walk with his weapon and
   shield skeletons hung off his hands, held there at every key, and the slot
   each weapon skeleton plays.
2. The mount: a DaC rider's mounts out of the EDU and descr_mount.txt, the
   ridden one first, and rider_offset read the ways the files write it.
3. A strat .cas: its skeleton from descr_model_strat.txt, its skin in the
   payload, a settlement's payload untouched.
4. Side by side: the same slot in the other mod, byte for byte or not.
5. The routes, on the installed mods.
6. The page's arithmetic under node: a pose carried by the mount's root bone,
   and the mount's action for the rider's slot.
"""
import json
import math
import shutil
import struct
import subprocess
import sys
import threading
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from unittransfer import animpack, animview, cas, casanim, config, mesh  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402

GAME = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition")
DAC, ROCSS = GAME / "mods" / "Divide_and_Conquer_EUR", GAME / "mods" / "ROCSS"
JS = ROOT / "web" / "js" / "v3anim.js"
ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


def world(anim, t):
    """Every track's world position at ``t``, chained the way the page does."""
    local = casanim.sample(anim, t)
    out = []
    for i, tr in enumerate(anim.tracks):
        q, p = local[i]["rot"], local[i]["pos"]
        m = quat_mat(q)
        if tr.parent < 0 or tr.parent >= i:
            out.append((m, p))
            continue
        pm, pp = out[tr.parent]
        d = mat_apply(pm, p)
        out.append((mat_mul(pm, m), tuple(a + b for a, b in zip(pp, d))))
    return out


def quat_mat(q):
    x, y, z, w = q
    return (1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w),
            2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w),
            2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y))


def mat_mul(a, b):
    return tuple(sum(a[r * 3 + k] * b[k * 3 + c] for k in range(3)) for r in range(3) for c in range(3))


def mat_apply(m, v):
    return tuple(m[r * 3] * v[0] + m[r * 3 + 1] * v[1] + m[r * 3 + 2] * v[2] for r in range(3))


if not (GAME / "data").is_dir() or not ROCSS.is_dir() or not DAC.is_dir():
    print("SKIPPED: vanilla, ROCSS and DaC are not all installed here")
    sys.exit(0)

ro, dac = Mod(ROCSS), Mod(DAC)
rpacks = animpack.for_data(ro.data)

# ---- 1) the weapon skeletons --------------------------------------------------------
print("\n1) a javelin man's weapon and shield")
entry = ro.modeldb.by_name()["duukunasi"]
st = entry.animations[0]
view = animview.entry_view(ro.data, entry)
walk = next(r for r in view["skeletons"][st.primary_skeleton.lower()]["actions"] if r["action"] == "walk")
bare = animview.read(ro.data, st.primary_skeleton, path=walk["path"])
full = animview.read(ro.data, st.primary_skeleton, path=walk["path"],
                     weapons=st.pri_weapons, slot=walk["slot"])
names = [t.name.lower() for t in full.tracks]
check(f"{st.primary_skeleton} with {', '.join(st.pri_weapons)}: two bones added, "
      f"{len(bare.tracks)} tracks to {len(full.tracks)}",
      len(full.tracks) == len(bare.tracks) + 2 and names[-2:] == ["bone_weapon01", "bone_shield"])
w1, sh = full.tracks[-2], full.tracks[-1]
check("bone_weapon01 hangs off the right hand, bone_shield off the left",
      full.tracks[w1.parent].name.lower() == "bone_rhand" and full.tracks[sh.parent].name.lower() == "bone_lhand")
check("each keyed once for every key of the body's action",
      w1.rot_keys == sh.rot_keys == len(full.key_times) and w1.pos_keys == len(full.key_times))
check("the body's own tracks are untouched",
      all(a.name == b.name and a.parent == b.parent and list(a.rot) == list(b.rot)
          for a, b in zip(bare.tracks, full.tracks)))
rep = {r["skeleton"]: r for r in full.weapons}
check("the report names each weapon skeleton, the slot it played and the bone it hangs off",
      rep[st.pri_weapons[0]]["hangs_off"].lower() == "bone_rhand"
      and rep[st.pri_weapons[0]]["slot"] == animview.DEFAULT_SLOT
      and rep[st.pri_weapons[0]]["bones"] == ["bone_weapon01"])
# held in the hand: the weapon bone keeps its distance from the hand at every key
hand = names.index("bone_rhand")
far = []
for t in [full.length * k / 6 for k in range(7)]:
    wd = world(full, t)
    far.append(math.dist(wd[hand][1], wd[len(full.tracks) - 2][1]))
pivot = math.hypot(*w1.pivot)
check(f"the weapon stays in the hand as the man walks ({min(far):.3f} to {max(far):.3f} from it, "
      f"its pivot {pivot:.3f})", max(abs(d - pivot) for d in far) < 0.02)
bow = rpacks.skeleton("MTW2_HR_Bow_Primary")
check("a weapon skeleton plays the body's slot when it fills it (the bow's release, 83), "
      "else its default", animview.weapon_slot(bow, 83) == 83 and animview.weapon_slot(bow, 11) == 686)
# a horse's skeleton is rooted on bone_H_Saddle, which no soldier has
nag = next(n for n in rpacks.skeleton_names()
           if rpacks.skeleton(n).bones[0].name.lower() == "bone_h_saddle")
odd = animview.read(ro.data, st.primary_skeleton, path=walk["path"],
                    weapons=["no_such_weapon", nag], slot=walk["slot"])
errs = {r["skeleton"]: r.get("error", "") for r in odd.weapons}
check(f"a weapon skeleton the pack has not got, or one rooted on a bone the body lacks ({nag}), "
      "is reported and skipped", "not in the skeleton pack" in errs["no_such_weapon"]
      and "hangs off" in errs[nag] and len(odd.tracks) == len(bare.tracks))
loose_rider = animview.read(ro.data, st.primary_skeleton, path=walk["path"], weapons=[])
check("no weapons asked for, none added", len(loose_rider.tracks) == len(bare.tracks)
      and loose_rider.weapons == [])

# ---- 2) the mount ---------------------------------------------------------------------
print("\n2) a rider's mounts")
rider = dac.modeldb.get("ghash_rider_upg0")
mv = animview.mounts_for(dac, rider)
first = mv["mounts"][0]
check(f"the mount its unit rides first: {first['type']} ({first['entry']}), ridden by "
      f"{', '.join(first['units'])}", first["units"] and not any(r["units"] for r in mv["mounts"][1:2]))
check("every mount offered is a horse, with a modeldb entry and a skeleton",
      mv["classes"] == ["horse"] and all(r["class"].lower() == "horse" and r["skeleton"] for r in mv["mounts"]))
check("its rider_offset is its descr_mount.txt block's", first["offset"] == [0.0, 0.38, 0.7]
      and first["offset_given"])
check("rider_offset read as the files write it: tabs, a comment, a leading point, the first of several",
      animview.rider_offset("rider_offset\t\t0.0, 0.38, 0.70") == [0.0, 0.38, 0.7]
      and animview.rider_offset("rider_offset 0.8, 0.2, -0.1 ;y was 1.54") == [0.8, 0.2, -0.1]
      and animview.rider_offset("rider_offset -.35, 1.22, .4") == [-0.35, 1.22, 0.4]
      and animview.rider_offset("rider_offset 0, 1, 2\nrider_offset 3, 4, 5") == [0.0, 1.0, 2.0]
      and animview.rider_offset(";rider_offset 1, 2, 3") is None)
foot = ro.modeldb.by_name()["duukunasi"]
check("a man on foot has no mount to offer", animview.mounts_for(ro, foot)["mounts"] == [])
horse = dac.modeldb.get(first["entry"])
hv = animview.entry_view(dac.data, horse)
hsk = hv["skeletons"][first["skeleton"].lower()]
check(f"the mount's skeleton {first['skeleton']} plays out of the pack ({hsk['playable']} actions), "
      "its walk in the rider's walk slot", hsk["packed"] and any(r["slot"] == 11 for r in hsk["actions"]))

# ---- 3) a strat .cas --------------------------------------------------------------
print("\n3) a strat model")
cv = animview.cas_view(ro, "models_strat/assassin.cas")
check("the assassin's skeleton is its descr_model_strat.txt entry's",
      [s["primary"] for s in cv["sets"]] == ["strat_assassin"] and not cv["guessed"]
      and cv["skeletons"]["strat_assassin"]["packed"])
check("a backslashed, data/-led path finds the same entry",
      animview.cas_view(ro, "data\\models_strat\\Assassin.cas")["sets"] == cv["sets"])
gv = animview.cas_view(ro, "models_strat/nobody_draws_this.cas")
check(f"a model no entry draws is offered every strat skeleton ({len(gv['sets'])}), marked a guess",
      gv["guessed"] and gv["sets"] and all(s["primary"].lower().startswith("strat_") for s in gv["sets"]))
src = ro.data / "models_strat" / "assassin.cas"
scene = cas.read_cas(src)
skel, _how = cas.pose_of(src, scene)
geo = cas.as_mesh(scene, skel)
pl = mesh.geometry_payload(geo)
n, = struct.unpack_from("<I", pl, 4)
head = json.loads(pl[8:8 + n])
ids = geo.bone_ids
used = {geo.bones[ids[v * 4 + 2]] for v in range(geo.vertices)}
check(f"its payload is skinned: one bone a vertex at weight 1, {len(used)} bones used",
      head["skinned"] and set(geo.weights[0::2]) == {1.0} and set(geo.weights[1::2]) == {0.0})
walk_c = next(r for r in cv["skeletons"]["strat_assassin"]["actions"] if r["action"] == "walk")
ca = animview.read(ro.data, "strat_assassin", path=walk_c["path"])
check("every bone its vertices use is a bone the skeleton's actions move",
      used <= {t.name for t in ca.tracks})
check("posed, as Phase 75 placed it: the positions are what they were",
      geo.positions.tobytes() == cas.as_mesh(scene, skel).positions.tobytes()
      and len(geo.positions) == 3 * geo.vertices)
town = next((p for p in (ro.data / cas.STRAT_MODELS / "residences").rglob("*.cas")
             if not cas.is_skinned(cas.read_cas(p))), None)
if town is not None:
    tg = cas.as_mesh(cas.read_cas(town))
    check(f"a settlement ({town.name}) carries no skin, as before", not tg.weights and not tg.bone_ids)

# ---- 4) side by side --------------------------------------------------------------
print("\n4) the same action in the other mod")
c = animview.compare(dac.data, ro.data, "MTW2_HR_Spear", 11)
check("DaC's HR_Spear walk in ROCSS: the same bytes, under another path",
      c["has_skeleton"] and c["has_slot"] and c["same_bytes"] and not c["same_path"] and c["frames"] > 0)
c2 = animview.compare(ro.data, dac.data, st.primary_skeleton, 81)
check(f"ROCSS's {st.primary_skeleton} missile ready in DaC: a different animation, and different bones",
      c2["has_slot"] and not c2["same_bytes"] and not c2["same_bones"] and c2["playable"])
dpacks = animpack.for_data(dac.data)
rnames = {x.lower() for x in rpacks.skeleton_names()}
only = next(x for x in dpacks.skeleton_names() if x.lower() not in rnames)
c3 = animview.compare(dac.data, ro.data, only, 0)
check(f"a skeleton ROCSS has not got ({only}) says so, and nothing else",
      c3["has_skeleton"] is False and "path" not in c3)

# ---- 5) the routes ----------------------------------------------------------------
print("\n5) the routes")
from unittransfer.server import Handler, Registry, _Server  # noqa: E402

cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"
config.save_settings(med2_root=str(GAME), run_full_cleaner=False)
Handler.registry = Registry(cfg / "icons")
httpd = _Server(("127.0.0.1", 0), Handler)
BASE = f"http://127.0.0.1:{httpd.server_address[1]}"
threading.Thread(target=httpd.serve_forever, daemon=True).start()


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=300) as r:
        return json.loads(r.read())


q = urllib.parse.quote
a = get(f"/api/model/anim?mod=ROCSS&pack={q(walk['path'])}&skel={st.primary_skeleton}"
        f"&slot={walk['slot']}&weapons={q(','.join(st.pri_weapons))}")
check("/api/model/anim hangs the weapons on and reports them",
      [b["name"] for b in a["bones"]][-2:] == ["bone_weapon01", "bone_shield"] and len(a["weapons"]) == 2)
a0 = get(f"/api/model/anim?mod=ROCSS&pack={q(walk['path'])}&skel={st.primary_skeleton}")
check("  ... and without `weapons`, the body alone", len(a0["bones"]) == len(a["bones"]) - 2
      and a0["weapons"] == [])
m = get("/api/model/mounts?mod=Divide_and_Conquer_EUR&entry=ghash_rider_upg0")
check("/api/model/mounts", m["mounts"][0]["entry"] == first["entry"])
cc = get(f"/api/model/compare?mod=Divide_and_Conquer_EUR&other=ROCSS&skel=MTW2_HR_Spear&slot=11")
check("/api/model/compare", cc["same_bytes"] is True)
try:
    get("/api/model/compare?mod=ROCSS&other=nope&skel=x&slot=0")
    refused = False
except urllib.error.HTTPError as e:
    refused = e.code == 404
check("  ... an unknown mod to compare with is a 404", refused)
ma = get("/api/map/model/anims?mod=ROCSS&rel=models_strat/assassin.cas")
check("/api/map/model/anims", ma["sets"][0]["primary"] == "strat_assassin")
httpd.shutdown()

# ---- 6) under node ----------------------------------------------------------------
print("\n6) the page's arithmetic, under node")
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
const out = {};
const I = [1,0,0, 0,1,0, 0,0,1];
const pose = [{m: I, p: [0, 0, 0]}, {m: I, p: [0.1, 0.2, 0.3]}];
out.still = ctx.v3aCarry(pose, {m: I, p: [0, 1, 0]}, [0, 0.38, 0.7], [0, -1, 0]);
// the root turned 90 degrees about y: x goes to -z
const s = Math.SQRT1_2, R = ctx.v3aMat([0, s, 0, s]);
out.turned = ctx.v3aCarry(pose, {m: R, p: [0, 0, 0]}, [1, 0, 0], [0, 0, 0]);
out.R = R;
const acts = [{slot: 0, playable: true, action: 'stand'}, {slot: 11, playable: true, action: 'walk'},
              {slot: 686, playable: true, action: 'default'}, {slot: 90, playable: false, action: 'x'}];
out.same = ctx.v3aMountRow(acts, 11);
out.idle = ctx.v3aMountRow(acts, 81);
out.none = ctx.v3aMountRow(acts, 90);
out.dflt = ctx.v3aMountRow([acts[2]], 81);
// a real rider on a real horse: the rider's pelvis sits at the saddle plus the offset
const [ride, horse] = job.anims;
const hp = ctx.v3aPose(horse, 0.3), hub = horse.bones.findIndex(b => b.parent === 0);
const rp = ctx.v3aPose(ride, 0.3), rhub = ride.bones.findIndex(b => b.parent === 0);
const carried = ctx.v3aCarry(rp, hp[hub], job.offset, [0, 0, 0]);
out.pelvis = carried[rhub].p;
out.saddle = hp[hub];
out.riderLocal = rp[rhub].p;
fs.writeFileSync(process.argv[4], JSON.stringify(out));
"""
    hr = dpacks.skeleton("MTW2_HR_Spear")
    hrow = next(s for i, s in hr.filled() if i == 11)
    ride = animview.read(dac.data, "MTW2_HR_Spear", path=hrow.path)
    hsk2 = dpacks.skeleton(first["skeleton"])
    horse_walk = animview.read(dac.data, first["skeleton"], path=hsk2.slots[11].path)
    t = Path(_tmp.mkdtemp(prefix="ut_animunit_node_"))
    (t / "h.js").write_text(HARNESS, encoding="utf-8")
    (t / "job.json").write_text(json.dumps({"anims": [ride.view(), horse_walk.view()],
                                            "offset": first["offset"]}), encoding="utf-8")
    r = subprocess.run([node, str(t / "h.js"), str(JS), str(t / "job.json"), str(t / "out.json")],
                       capture_output=True, text=True)
    check("the harness runs", r.returncode == 0)
    if r.returncode:
        print(r.stderr[-1200:])
    else:
        o = json.loads((t / "out.json").read_text(encoding="utf-8"))
        near = lambda a, b: all(abs(x - y) < 1e-6 for x, y in zip(a, b))
        check("an unturned root moves the pose by its place, the offset and the lift",
              near(o["still"][0]["p"], [0, 0.38, 0.7]) and near(o["still"][1]["p"], [0.1, 0.58, 1.0]))
        check("a turned root turns the pose with it, offset and all",
              near(o["turned"][0]["p"], [0, 0, -1]) and near(o["turned"][0]["m"], o["R"]))
        check("the mount plays the rider's slot when it fills it, else its idle, else its default",
              o["same"]["row"]["slot"] == 11 and o["same"]["same"]
              and o["idle"]["row"]["slot"] == 0 and not o["idle"]["same"]
              and o["none"]["row"]["slot"] == 0 and o["dflt"]["row"]["slot"] == 686)
        # the pelvis in world = saddle + R (offset + rider's own local pelvis)
        sm, sp = o["saddle"]["m"], o["saddle"]["p"]
        want = [sp[k] + sum(sm[k * 3 + j] * (first["offset"][j] + o["riderLocal"][j]) for j in range(3))
                for k in range(3)]
        check(f"a DaC rider on {first['entry']}: his pelvis {', '.join(f'{v:.2f}' for v in o['pelvis'])} "
              f"sits on the saddle at {', '.join(f'{v:.2f}' for v in sp)} plus the offset",
              near(o["pelvis"], want) and o["pelvis"][1] > sp[1])

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
