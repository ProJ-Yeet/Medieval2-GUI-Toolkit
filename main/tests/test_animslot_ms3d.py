"""128f: a MilkShape animation dropped on a slot, and a weapon bone hidden, saved into the pack.

    python -m tests.test_animslot_ms3d

The mod is small: packs holding DaC's MTW2_Mace and the weapon skeleton
mtw2_2hswordsman_primary (bone_Rhand, bone_weapon01) with every animation they
play, so nothing copies DaC's 356 MB pack.

1. An .ms3d of the weapon skeleton's idle, bone_weapon01 moved 0.25 up, saved
   into that slot: bone_weapon01 is kept (GOAT drops it) and the pack entry
   read back moves it by 0.25 at every key; the bones it does not move stay.
2. An .ms3d missing a bone of the body: saved, with a note naming the bone,
   which holds its bind pose.
3. Refused: an .ms3d of another skeleton, a file that is not an .ms3d.
4. Hide: the ``hide`` edit moves bone_weapon01 100 m down at every key of the
   weapon idle, and nothing else; a bone the skeleton has not got is refused.
5. Written: the hidden idle is appended and the slot pointed there; Undo puts
   the pack files back byte for byte.
6. The API routes: pack_preview with an .ms3d (base64) plays its bones,
   pack_plan with ``hide`` writes nothing, pack_apply writes, Undo takes it out.
"""
import base64
import hashlib
import math
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod, _tmp  # noqa: E402
from unittransfer import animconvert, animloose, animpack, animslot, casanim, config, skelslots, transfer  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402

MODS = _realmod.mods()
DAC = MODS / "Divide_and_Conquer_EUR"
REL = ("export_descr_unit.txt", "text/export_units.txt", "unit_models/battle_models.modeldb",
       "descr_mount.txt", "descr_skeleton.txt")
BODY, WEAPON = "MTW2_Mace", "mtw2_2hswordsman_primary"
ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return bool(cond)


if not (DAC / "data" / "animations" / "pack.dat").is_file():
    print("SKIPPED: needs Divide_and_Conquer_EUR installed")
    sys.exit(0)

cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"
animpack.game_running = lambda: []


def mini(name: str, src_data: Path, skeletons) -> Mod:
    """A mod whose packs hold ``skeletons`` and every animation they play."""
    root = Path(_tmp.mkdtemp(prefix=f"ut_ms3d_{name}_")) / "mods" / name
    for rel in REL:
        f = src_data / rel
        if f.is_file():
            (root / "data" / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, root / "data" / rel)
    out = root / "data" / "animations"
    out.mkdir(parents=True)
    packs = animpack.for_data(src_data)
    skel_rows, anim_rows, seen = [], [], set()
    for s in skeletons:
        skel_rows.append(packs.skels.first(s))
        sk = packs.skeleton(s)
        for _i, slot in sk.filled():
            hit = animpack.resolve_slot(packs.anims, slot.path, sk.scale)
            if hit is not None and id(hit) not in seen:
                seen.add(id(hit))
                anim_rows.append(hit)
    animpack._write_pack(packs.anims, anim_rows, out / "pack.dat", out / "pack.idx")
    animpack._write_pack(packs.skels, skel_rows, out / "skeletons.dat", out / "skeletons.idx")
    return Mod(root)


def shas(m: Mod) -> dict:
    d = Path(m.data)
    files = [d / "animations" / n for n in animpack.FILES] + [d / "descr_skeleton.txt"]
    return {f.name: hashlib.sha1(f.read_bytes()).hexdigest() for f in files}


def as_cas(m: Mod, skel: str, slot: int):
    """The slot's pack entry as the .cas it was packed from, and the skeleton."""
    packs = animpack.for_data(m.data)
    sk = packs.skeleton(skel)
    e = animpack.resolve_slot(packs.anims, sk.slots[slot].path, sk.scale)
    return animloose.to_cas(packs.anims.read_entry(e), sk.bone_table(), e.scale, sk.slots[slot].path,
                            bone_scale=sk.scale), sk


def played(m: Mod, plan, skel: str):
    """The plan's bytes read back as the game would play them."""
    sk = animpack.for_data(m.data).skeleton(skel)
    return casanim.read_packed_bytes(plan.data, plan.new_path or "x.cas", sk.bone_table(), skel)


def track(a, name):
    return next(i for i, t in enumerate(a.tracks) if t.name.lower() == name.lower())


def positions(a, name):
    i = track(a, name)
    return [casanim.sample(a, float(t))[i]["pos"] for t in a.key_times]


dest = mini("Dest", DAC / "data", [BODY, WEAPON])
IDLE = skelslots.slots_of("stand_a_idle")[0]
DEFAULT = animslot.DEFAULT_SLOT
packs = animpack.for_data(dest.data)
check(f"{WEAPON} has bone_weapon01 and an idle", [b.name for b in packs.skeleton(WEAPON).bones]
      == ["bone_Rhand", "bone_weapon01"] and packs.skeleton(WEAPON).slots[IDLE] is not None)

# ---- 1) an .ms3d of the weapon skeleton ------------------------------------------------
print("\n1) an .ms3d dropped on the weapon skeleton's idle")
orig, wsk = as_cas(dest, WEAPON, IDLE)
ms = animconvert.cas_to_ms3d(orig)
jw = next(j for j in ms.joints if j.name == "bone_weapon01")
if not jw.pos_keys:
    jw.pos_keys = [(float(t), 0.0, 0.0, 0.0) for t in orig.key_times]
jw.pos_keys = [(k[0], k[1], k[2] + 0.25, k[3]) for k in jw.pos_keys]
saber = animconvert.write_ms3d(ms)
p = animslot.plan_edit(dest, WEAPON, IDLE, {}, ms3d=saber, ms3d_name="saber_idle.ms3d")
check("planned without errors", p.ok and not p.errors)
check("named after the .ms3d, under animations/edited/<skeleton>/",
      p.new_path.lower().endswith(f"edited/{WEAPON}/saber_idle.cas".lower()))
check("its source says the .ms3d", p.source == "saber_idle.ms3d")
got = played(dest, p, WEAPON)
check("the pack entry has bone_weapon01 (GOAT would have dropped it)",
      any(t.name == "bone_weapon01" for t in got.tracks))
before_w = positions(orig, "bone_weapon01")
after_w = positions(got, "bone_weapon01")
n = min(len(before_w), len(after_w))
moved = [math.dist(a, b) for a, b in zip(before_w[:n], after_w[:n])]
check(f"bone_weapon01 moved 0.25 at every key ({min(moved):.3f} to {max(moved):.3f})",
      n > 0 and all(abs(d - 0.25) < 0.02 for d in moved))
hand = [math.dist(a, b) for a, b in zip(positions(orig, "bone_Rhand")[:n], positions(got, "bone_Rhand")[:n])]
check("bone_Rhand did not move", max(hand or [0]) < 1e-3)
p2 = animslot.plan_edit(dest, WEAPON, IDLE, {}, ms3d=saber, ms3d_name="saber_idle.ms3d", name="lightsaber_on")
check("a name given wins over the .ms3d's", p2.new_path.lower().endswith("/lightsaber_on.cas"))

# ---- 2) an .ms3d missing a bone ------------------------------------------------------
print("\n2) an .ms3d of the body missing bone_jaw")
body, bsk = as_cas(dest, BODY, IDLE)
bm = animconvert.cas_to_ms3d(body)
for j in bm.joints:
    if j.name == "bone_head" and j.rot_keys:
        j.rot_keys = [(k[0], k[1] + 0.2, k[2], k[3]) for k in j.rot_keys]
    if j.parent == "bone_jaw":
        j.parent = "bone_head"
bm.joints = [j for j in bm.joints if j.name != "bone_jaw"]
p = animslot.plan_edit(dest, BODY, IDLE, {}, ms3d=animconvert.write_ms3d(bm), ms3d_name="head_turn.ms3d")
check("planned without errors", p.ok)
check("a note names bone_jaw, holding its bind pose", any("bone_jaw" in x for x in p.notes))
check("the entry plays the skeleton's 20 bones", len(played(dest, p, BODY).tracks) - 1 == 20)

# ---- 3) refused ------------------------------------------------------------------------
print("\n3) refused")
other = animconvert.cas_to_ms3d(orig)
for j in other.joints:
    j.name, j.parent = "horse_" + j.name, ("horse_" + j.parent if j.parent else "")
p = animslot.plan_edit(dest, WEAPON, IDLE, {}, ms3d=animconvert.write_ms3d(other), ms3d_name="horse.ms3d")
check("an .ms3d of another skeleton: refused, named", not p.ok and "horse.ms3d" in "; ".join(p.errors))
p = animslot.plan_edit(dest, WEAPON, IDLE, {}, ms3d=b"not a milkshape file at all", ms3d_name="junk.ms3d")
check("not an .ms3d: refused", not p.ok and "MilkShape" in "; ".join(p.errors))

# ---- 4) hide ---------------------------------------------------------------------------
print("\n4) bone_weapon01 hidden")
p = animslot.plan_edit(dest, WEAPON, IDLE, {"hide": ["bone_weapon01"]}, name="w_idle_hidden")
check("planned without errors", p.ok)
got = played(dest, p, WEAPON)
after_w = positions(got, "bone_weapon01")
n = min(len(before_w), len(after_w))
drop = [b[1] - a[1] for a, b in zip(before_w[:n], after_w[:n])]
check(f"bone_weapon01 100 m lower at every key ({min(drop):.2f} to {max(drop):.2f})",
      n > 1 and all(abs(d + 100.0) < 0.05 for d in drop))
hand = [math.dist(a, b) for a, b in zip(positions(orig, "bone_Rhand")[:n], positions(got, "bone_Rhand")[:n])]
check("bone_Rhand did not move", max(hand or [0]) < 1e-3)
p = animslot.plan_edit(dest, WEAPON, IDLE, {"hide": ["bone_blade"]})
check("a bone it has not got: refused, named", not p.ok and "bone_blade" in "; ".join(p.errors))

# ---- 5) written, and undone ------------------------------------------------------------
print("\n5) written, and Undo")
before = shas(dest)
p = animslot.plan_edit(dest, WEAPON, IDLE, {"hide": ["bone_weapon01"]}, name="w_idle_hidden")
res = animslot.apply(p)
after = animpack.for_data(dest.data)
sk = after.skeleton(WEAPON)
check("the idle slot points at the new entry", animpack._key(sk.slots[IDLE].path) == animpack._key(p.new_path))
check("which reads back as the planned bytes",
      after.anims.read_entry(animpack.resolve_slot(after.anims, p.new_path, sk.scale)) == p.data)
check("default still plays what it did", sk.slots[DEFAULT].path == packs.skeleton(WEAPON).slots[DEFAULT].path)
transfer.undo(res["id"])
check("Undo: the packs and descr_skeleton.txt are back byte for byte", shas(dest) == before)

# ---- 6) the API ------------------------------------------------------------------------
print("\n6) the API routes")
from unittransfer import server  # noqa: E402


class _Reg:
    def get(self, name):
        return {"Dest": dest}[name]

    def invalidate(self, name):
        pass


h = server.Handler.__new__(server.Handler)
h.registry = _Reg()
b64 = base64.b64encode(saber).decode("ascii")
r = h._anim_pack("pack_preview", {"mod": "Dest", "skeleton": WEAPON, "slot": IDLE, "edits": {},
                                  "ms3d": b64, "ms3d_name": "saber_idle.ms3d"})
check("pack_preview with an .ms3d plays bone_weapon01",
      "error" not in r and any(b.get("name") == "bone_weapon01" for b in r.get("bones", [])))
r = h._anim_pack("pack_preview", {"mod": "Dest", "skeleton": WEAPON, "slot": IDLE, "ms3d": "!!not base64!!"})
check("pack_preview with bad base64 says so", bool(r.get("error")))
body_ = {"mod": "Dest", "skeleton": WEAPON, "slot": IDLE, "edits": {"hide": ["bone_weapon01"]},
         "name": "w_idle_api"}
r = h._anim_pack("pack_plan", body_)
check("pack_plan with hide: a plan, nothing written", r.get("plan", {}).get("ok") and shas(dest) == before)
r = h._anim_pack("pack_apply", body_)
check("pack_apply writes it", r.get("new_path", "").lower().endswith("/w_idle_api.cas"))
transfer.undo(r["id"])
check("and Undo takes it out again", shas(dest) == before)
r = h._anim_pack("pack_apply", {"mod": "Dest", "skeleton": WEAPON, "slot": IDLE, "ms3d": b64,
                                "ms3d_name": "saber_idle.ms3d"})
check("pack_apply with an .ms3d writes saber_idle.cas", r.get("new_path", "").lower().endswith("/saber_idle.cas"))
transfer.undo(r["id"])
check("and Undo takes it out again", shas(dest) == before)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
