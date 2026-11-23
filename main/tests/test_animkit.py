"""Kitbash a skeleton: a new one from a base, slots taken from others, slots cleared.

    python -m tests.test_animkit

The mods here are small: packs holding three of DaC's skeletons and every
animation they play (MTW2_Spear, MTW2_Mace, lotr_troll), and a second mod
holding vanilla's MTW2_Swordsman, so nothing copies DaC's 356 MB pack.

1. A plan: a slot from a skeleton with the same bones (its own bytes, nothing
   appended), a slot from another slot of it (cross slot), a slot cleared, a
   troll's slot forced on with a bone map (bone_E_platform -> bone_pelvis), a
   slot from another mod; the notes say what was carried and what holds still.
2. Refused: default cleared, a name taken, a bad name, a bone map naming bones
   that are not there, a mod that is not there, no changes.
3. The preview is the bytes the plan writes, on the base's bones.
4. Written: the new skeleton is in the pack with the slots pointed where the
   plan said, the cleared slot empty and every other slot the base's; each
   appended animation reads back; descr_skeleton.txt has its block. Undo puts
   the four pack files and the text back byte for byte.
5. The API routes: kit_plan writes nothing, kit_preview gives the viewer's
   shape (a cleared slot refused), kit_apply writes and Undo takes it out.
"""
import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod, _tmp  # noqa: E402
from unittransfer import animkit, animpack, casanim, config, skelslots, transfer  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402

MODS = _realmod.mods()
GAME = _realmod.game()
DAC = MODS / "Divide_and_Conquer_EUR"
REL = ("export_descr_unit.txt", "text/export_units.txt", "unit_models/battle_models.modeldb",
       "descr_mount.txt", "descr_skeleton.txt")
ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return bool(cond)


if not (DAC / "data" / "animations" / "pack.dat").is_file() or not (GAME / "data" / "animations").is_dir():
    print("SKIPPED: needs Divide_and_Conquer_EUR and vanilla's packs installed")
    sys.exit(0)

cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"
animpack.game_running = lambda: []


def mini(name: str, src_data: Path, skeletons, text_from: Path) -> Mod:
    """A mod whose packs hold ``skeletons`` and every animation they play."""
    root = Path(_tmp.mkdtemp(prefix=f"ut_kit_{name}_")) / "mods" / name
    for rel in REL:
        f = text_from / rel
        if f.is_file():
            (root / "data" / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, root / "data" / rel)
    out = root / "data" / "animations"
    out.mkdir(parents=True)
    packs = animpack.for_data(src_data)
    skel_rows, anim_rows, seen = [], [], set()
    for s in skeletons:
        e = packs.skels.first(s)
        skel_rows.append(e)
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


def slot(name):
    return skelslots.slots_of(name)[0]


dest = mini("Dest", DAC / "data", ["MTW2_Spear", "MTW2_Mace", "lotr_troll"], DAC / "data")
other = mini("Other", GAME / "data", ["MTW2_Swordsman"], DAC / "data")
sources = {"Other": other}
WALK, IDLE, DEFAULT = slot("walk"), slot("stand_a_idle"), animkit.DEFAULT_SLOT
packs = animpack.for_data(dest.data)
spear, mace, troll = (packs.skeleton(n) for n in ("MTW2_Spear", "MTW2_Mace", "lotr_troll"))
oth = animpack.for_data(other.data).skeleton("MTW2_Swordsman")
filled_spear = [i for i, _s in spear.filled() if i not in (WALK, IDLE, DEFAULT)]
CLEAR = filled_spear[0]
TROLL = next(i for i, _s in troll.filled() if i not in (WALK, IDLE, DEFAULT, CLEAR))
MACE_X = next(i for i, _s in mace.filled() if i not in (WALK, IDLE, DEFAULT, CLEAR, TROLL))
OTHER = next(i for i, _s in oth.filled()
             if i not in (WALK, IDLE, DEFAULT, CLEAR, TROLL, MACE_X) and spear.slots[i] is not None)
print(f"\n  slots: walk {WALK}, idle {IDLE}, clear {skelslots.label(CLEAR)}, troll {skelslots.label(TROLL)}, "
      f"mace {skelslots.label(MACE_X)} -> idle, other mod {skelslots.label(OTHER)}")

# ---- 1) a plan --------------------------------------------------------------------
print("\n1) a plan")
C = animkit.Change
changes = [C(WALK, skeleton="MTW2_Mace"),
           C(IDLE, skeleton="MTW2_Mace", source_slot=MACE_X),
           C(CLEAR, clear=True),
           C(TROLL, skeleton="lotr_troll", bone_map={"bone_E_platform": "bone_pelvis"}),
           C(OTHER, source="Other", skeleton="MTW2_Swordsman")]
p = animkit.plan_kit(dest, "MTW2_Spear", "Kit_Spear", changes, sources)
check("it plans with no errors: " + "; ".join(p.payload()["errors"]), p.ok)
rows = {r.slot: r for r in p.rows}
w = rows.get(WALK)
check("walk from MTW2_Mace (the same bones): its own bytes, already in the pack, nothing appended",
      w and w.reuse and w.data == packs.anims.read_entry(
          animpack.resolve_slot(packs.anims, mace.slots[WALK].path, mace.scale)))
i = rows.get(IDLE)
check("stand_a_idle takes MTW2_Mace's other slot: its bytes, at its path",
      i and i.reuse and animpack._key(i.new_path) == animpack._key(mace.slots[MACE_X].path))
t = rows.get(TROLL)
check("the troll's slot is carried bone by bone with the map, and appended under animations/kit/",
      t and not t.reuse and "/animations/kit/kitspear/" in t.new_path
      and any("bone by bone" in n for n in t.notes))
cas_t = casanim.read_packed_bytes(t.data, "t", spear.bone_table(), "MTW2_Spear") if t else None
src_t = casanim.read_packed_bytes(packs.anims.read_entry(animpack.resolve_slot(
    packs.anims, troll.slots[TROLL].path, troll.scale)), "s", troll.bone_table(), "lotr_troll")
check("bone_pelvis turns as the troll's bone_E_platform did",
      cas_t is not None and len(cas_t.tracks[1].rot) == len(src_t.tracks[1].rot)
      and all(abs(a - b) < 1e-4 for a, b in zip(cas_t.tracks[1].rot, src_t.tracks[1].rot)))
nomap = animkit.plan_kit(dest, "MTW2_Spear", "Kit_Spear2",
                         [C(TROLL, skeleton="lotr_troll")], sources)
nr = nomap.rows[0] if nomap.rows else None
check("without the map bone_pelvis is named as holding still",
      nr and any("bone_pelvis" in n for n in nr.notes))
o = rows.get(OTHER)
check("a slot from the other mod's MTW2_Swordsman is planned, named as from there",
      o and o.data and o.source.startswith("Other:"))
check("the cleared slot is a row of its own", rows.get(CLEAR) and rows[CLEAR].clear)

# ---- 2) refused --------------------------------------------------------------------
print("\n2) refused")


def errs(plan):
    return " ".join(plan.payload()["errors"])


check("default cleared", "default" in errs(animkit.plan_kit(dest, "MTW2_Spear", "K2", [C(DEFAULT, clear=True)])))
check("a name the pack has", "already" in errs(animkit.plan_kit(dest, "MTW2_Spear", "MTW2_Mace", [C(CLEAR, clear=True)])))
check("a bad name", "name" in errs(animkit.plan_kit(dest, "MTW2_Spear", "bad name!", [C(CLEAR, clear=True)])))
check("a bone map naming bones that are not there", "bone map" in errs(animkit.plan_kit(
    dest, "MTW2_Spear", "K3", [C(TROLL, skeleton="lotr_troll", bone_map={"bone_nope": "bone_pelvis"})])))
check("a mod that is not there", "no mod" in errs(animkit.plan_kit(
    dest, "MTW2_Spear", "K4", [C(OTHER, source="Nope", skeleton="x")], sources)))
check("no changes", "no slot" in errs(animkit.plan_kit(dest, "MTW2_Spear", "K5", [])))
check("a slot the source leaves empty", "empty" in errs(animkit.plan_kit(
    dest, "MTW2_Spear", "K6", [C(CLEAR, skeleton="MTW2_Mace", source_slot=next(
        n for n in range(animpack.SKELETON_SLOTS) if mace.slots[n] is None))])))

# ---- 3) preview ---------------------------------------------------------------------
print("\n3) preview")
pv = animkit.preview(dest, "MTW2_Spear", C(TROLL, skeleton="lotr_troll",
                                          bone_map={"bone_E_platform": "bone_pelvis"}), sources)
check("the troll slot's preview is the plan's bytes, on MTW2_Spear's 20 bones",
      [x.name for x in pv.tracks[1:]] == [b.name for b in spear.bones]
      and len(pv.key_times) == animpack.PackedAnimation(t.data).frames
      and all(list(a.rot) == list(b.rot) for a, b in zip(pv.tracks, cas_t.tracks)))
pv2 = animkit.preview(dest, "MTW2_Spear", C(OTHER, source="Other", skeleton="MTW2_Swordsman"), sources)
check("the other mod's slot previews", len(pv2.key_times) > 1)

# ---- 4) written, and undone ---------------------------------------------------------------
print("\n4) written, and Undo")
before = shas(dest)
n_anims = len(packs.anims.entries)
res = animkit.apply_kit(p)
after = animpack.for_data(dest.data)
kit = after.skeleton("Kit_Spear")
check("the pack has Kit_Spear, and MTW2_Spear is as it was",
      kit is not None and after.skeleton("MTW2_Spear").to_bytes() == spear.to_bytes())
check("its slots point where the plan said, the cleared one empty",
      kit and all((kit.slots[r.slot] is None) if r.clear else
                  animpack._key(kit.slots[r.slot].path) == animpack._key(r.new_path) for r in p.rows))
changed = {r.slot for r in p.rows}
check("every other slot is the base's, path and settings",
      kit and all((a is None and b is None) or (a and b and a.to_bytes() == b.to_bytes())
                  for n, (a, b) in enumerate(zip(kit.slots, spear.slots)) if n not in changed))
check("the bones are the base's", kit and [b.name for b in kit.bones] == [b.name for b in spear.bones])
check(f"{len(p.appends)} animation(s) appended, each read back",
      len(after.anims.entries) == n_anims + len(p.appends)
      and all(after.anims.read_entry(animpack.resolve_slot(after.anims, r.new_path, r.scale)) == r.data
              for r in p.appends))
text = (Path(dest.data) / "descr_skeleton.txt").read_bytes().decode("latin-1")
check("descr_skeleton.txt has a type block for Kit_Spear", "Kit_Spear" in text)
check("loose copies were written for the rebuild", any("kit" in f.lower() for f in res["files"]))
transfer.undo(res["id"])
check("Undo: the packs and descr_skeleton.txt are back byte for byte", shas(dest) == before)

# ---- 5) the API ------------------------------------------------------------------------
print("\n5) the API routes")
from unittransfer import server  # noqa: E402


class _Reg:
    def get(self, name):
        return {"Dest": dest, "Other": other}[name]

    def invalidate(self, name):
        pass


h = server.Handler.__new__(server.Handler)
h.registry = _Reg()
body = {"mod": "Dest", "base": "MTW2_Spear", "name": "Kit_Api",
        "changes": [{"slot": TROLL, "skeleton": "lotr_troll", "bone_map": {"bone_E_platform": "bone_pelvis"}},
                    {"slot": CLEAR, "clear": True},
                    {"slot": OTHER, "source": "Other", "skeleton": "MTW2_Swordsman"}]}
r = h._anim_kit("kit_plan", body)
check("kit_plan: a plan of three rows, nothing written", r.get("plan", {}).get("ok") and len(r["plan"]["rows"]) == 3
      and animpack.for_data(dest.data).skeleton("Kit_Api") is None)
r = h._anim_kit("kit_preview", {"mod": "Dest", "base": "MTW2_Spear",
                                "change": {"slot": OTHER, "source": "Other", "skeleton": "MTW2_Swordsman"},
                                "weapons": ["MTW2_Spear_primary"]})
check("kit_preview: the viewer's shape, the base's bones and keys",
      "error" not in r and len(r.get("bones", [])) == 21 and len(r.get("times", [])) > 1)
r = h._anim_kit("kit_preview", {"mod": "Dest", "base": "MTW2_Spear", "change": {"slot": CLEAR, "clear": True}})
check("kit_preview of a cleared slot says there is nothing to play", "nothing to play" in r.get("error", ""))
before = shas(dest)
r = h._anim_kit("kit_apply", body)
check("kit_apply writes Kit_Api", r.get("name") == "Kit_Api" and animpack.for_data(dest.data).skeleton("Kit_Api"))
transfer.undo(r["id"])
check("and Undo takes it out again", shas(dest) == before)
r = h._anim_kit("kit_apply", dict(body, name="MTW2_Mace"))
check("kit_apply refuses a plan with errors and writes nothing",
      "already" in r.get("error", "") and shas(dest) == before)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
