"""Phase 86: animations on their own.

    python -m tests.test_animslot

1. An action packed for its skeleton: on the engine's frames, and every filled
   slot of three ROCSS skeletons packs back, unedited, to the entry it plays.
2. An edit saved into a copy of ROCSS's pack: appended under a new path, the
   skeleton's slot pointed there and nothing else in the skeleton pack
   changed, the counts in step; the preview is the bytes written; kept
   rebuildable (a loose .cas and descr_skeleton.txt's line). A second edit of
   the same slot, and Undo newest first, back to ROCSS's four files byte for
   byte.
3. Another mod's animation put in one slot: its own bytes when the skeletons
   share their bones, carried across by bone name when they do not.
4. A skeleton ported alone, renamed because the name is taken, and a model
   entry pointed at it; Undo.
5. Refused: the game running; the packs changed since the plan; a mod that
   plays vanilla's packs; an empty slot; a bad name; nothing to change.
"""
import hashlib
import shutil
import sys
from array import array
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from unittransfer import animloose, animpack, animslot, casanim, config, skelslots, transfer  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402

MODS = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition/mods")
ROCSS = MODS / "ROCSS"
DAC = MODS / "Divide_and_Conquer_EUR"
REL = ("export_descr_unit.txt", "text/export_units.txt", "unit_models/battle_models.modeldb",
       "descr_mount.txt", "descr_skeleton.txt")
ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


def shas(d: Path) -> dict:
    return {n: hashlib.sha1((d / n).read_bytes()).hexdigest() for n in animpack.FILES}


def fresh(tag, packs=True):
    root = Path(_tmp.mkdtemp(prefix=f"ut_slot_{tag}_")) / "mods" / "Dest"
    for rel in REL:
        (root / "data" / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROCSS / "data" / rel, root / "data" / rel)
    if packs:
        (root / "data" / "animations").mkdir(parents=True)
        for n in animpack.FILES:
            shutil.copy2(ROCSS / "data" / "animations" / n, root / "data" / "animations" / n)
    return Mod(root)


def refused(fn, *words):
    try:
        fn()
    except (animslot.SlotError, animpack.PackError) as e:
        return all(w in str(e) for w in words) or print("     said:", e)
    return False


if not ROCSS.is_dir():
    print("SKIPPED: needs ROCSS installed")
    sys.exit(0)

cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"
animpack.game_running = lambda: []

SKEL = "MTW2_Spear"
IDLE = skelslots.slots_of("stand_a_idle")[0]
WALK = skelslots.slots_of("walk")[0]

# ---- 1) packing ---------------------------------------------------------------------
print("\n1) an action packed for its skeleton")
rp = animpack.for_data(ROCSS / "data")
_e, sk = animslot._skeleton(rp, SKEL)
e = animpack.resolve_slot(rp.anims, sk.slots[WALK].path, sk.scale)
walk = animloose.to_cas(rp.anims.read_entry(e), sk.bone_table(), e.scale, e.name, bone_scale=sk.scale)
check("an action on the engine's frames is left as it is", animslot.on_frames(walk) is walk)
fast = casanim.Animation(source="x", length=walk.length / 2, key_times=array("f", [t / 2 for t in walk.key_times]),
                         tracks=walk.tracks)
ff = animslot.on_frames(fast)
check("a sped-up one is sampled onto them, an odd number, 0.05 s apart",
      len(ff.key_times) % 2 == 1 and abs(ff.key_times[1] - 0.05) < 1e-6
      and abs(ff.key_times[-1] - round(walk.length / 2 / 0.05) * 0.05) < 0.051)
check("holding each moving bone's keys on the new frames",
      all(t.rot_keys in (0, len(ff.key_times)) for t in ff.tracks))
bad = 0
count = 0
for name in ("MTW2_Spear", "MTW2_Mace", "MTW2_2HSwordsman"):
    _x, s = animslot._skeleton(rp, name)
    for i, slot in s.filled():
        en = animpack.resolve_slot(rp.anims, slot.path, s.scale)
        raw = rp.anims.read_entry(en)
        loose = animloose.to_cas(raw, s.bone_table(), en.scale, en.name, bone_scale=s.scale)
        if en.scale != s.scale:
            continue
        count += 1
        if not animloose.floats_close(animslot.pack_for(rp, s, i, loose), raw):
            bad += 1
check(f"every slot of three skeletons packs back, unedited, to the entry it plays ({count} slots, {bad} not)",
      count > 200 and bad == 0)
moved, missing = animslot.onto(walk, sk, len(walk.tracks) - 1)
check("put onto its own skeleton, every bone is found", not missing)
walk.tracks[3].name = "not_a_bone"
moved, missing = animslot.onto(walk, sk, len(walk.tracks) - 1)
check("a bone the animation does not name holds its bind pose, and is reported",
      missing == [sk.bones[2].name] and moved.tracks[3].rot_keys == 0)

# ---- 2) an edit saved into the pack ---------------------------------------------------
print("\n2) an edit saved into a copy of ROCSS's pack")
original = shas(ROCSS / "data" / "animations")
mod = fresh("edit")
ad = mod.data / "animations"
before = animpack.open_packs(ad)
dat_len = (ad / "pack.dat").stat().st_size
skels_before = {e.name: before.skels.read_entry(e) for e in before.skels.entries}
edits = {"speed": 2.0, "offsets": [{"bone": sk.bones[1].name, "euler": [0, 0, 15]}]}
p = animslot.plan_edit(mod, SKEL, WALK, edits, name="spear_walk_fast")
check("planned clean, under animations/edited/<skeleton>/, not over the old path",
      p.ok and p.new_path == f"mods/Dest/data/animations/edited/{SKEL}/spear_walk_fast.cas"
      and p.old_path == sk.slots[WALK].path)
check("half the frames of the walk it was made from",
      abs(animpack.PackedAnimation(p.data).frames - (e.frames + 1) / 2) <= 1)
prev = animslot.preview_edit(mod, SKEL, WALK, edits)
check("the preview is the bytes the save writes, read back",
      len(prev.key_times) == animpack.PackedAnimation(p.data).frames
      and prev.tracks[1].rot[:4] == array("f", p.data[5:21]))
check("kept rebuildable: a loose .cas and descr_skeleton.txt's walk line",
      p.loose and p.loose[0] == f"animations/edited/{SKEL}/spear_walk_fast.cas" and p.text_edit)
res = animslot.apply(p)
after = animpack.open_packs(ad)
check("pack.dat grew by the entry, and nothing before its old end moved",
      (ad / "pack.dat").stat().st_size == dat_len + len(p.data))
ne = after.anims.first(p.new_path)
check("pack.idx lists it once, at the skeleton's scale, its bytes the plan's",
      ne is not None and len(after.anims.find(p.new_path)) == 1 and ne.scale == sk.scale
      and after.anims.read_entry(ne) == p.data)
nsk = after.skeleton(SKEL)
check("the skeleton's walk names it, and its slot's timing is kept but for the frames",
      nsk.slots[WALK].path == p.new_path and nsk.slots[WALK].min_turn == sk.slots[WALK].min_turn)
check("the game resolves the slot to the new entry",
      animpack.resolve_slot(after.anims, nsk.slots[WALK].path, nsk.scale).offset == ne.offset)
others = {e.name: after.skels.read_entry(e) for e in after.skels.entries}
check("every other skeleton is byte for byte what it was, in the same order",
      [e.name for e in after.skels.entries] == list(skels_before)
      and all(others[n] == b for n, b in skels_before.items() if n != SKEL))
c = animpack.check(ad)
check("both .dat headers equal their .idx, and the checks pass",
      not c["problems"] and c["anim .dat header = .idx header"] == 1 and c["skel .dat header = .idx header"] == 1)
check("the loose file is there and packs back to the entry",
      animloose.floats_close(animslot.pack_for(after, nsk, WALK,
                                               casanim.read_anim(mod.data / p.loose[0])), p.data))
text = (mod.data / "descr_skeleton.txt").read_bytes().decode("latin-1")
check("descr_skeleton.txt's MTW2_Spear walk names the new file, the rest of the file as it was",
      f"mods/Dest/data/animations/edited/{SKEL}/spear_walk_fast.cas" in text
      and len(text.splitlines()) == len((ROCSS / "data" / "descr_skeleton.txt").read_bytes().decode("latin-1").splitlines()))
p2 = animslot.plan_edit(mod, SKEL, WALK, {"in_place": True}, name="spear_walk_fast")
check("a second edit of the slot starts from the first, and takes a name of its own",
      p2.ok and p2.old_path == p.new_path and p2.new_path.endswith("spear_walk_fast_2.cas"))
res2 = animslot.apply(p2)
check("it plays now", animpack.open_packs(ad).skeleton(SKEL).slots[WALK].path == p2.new_path)
transfer.undo(res2["id"])
check("Undo of the second: the first plays again", animpack.open_packs(ad).skeleton(SKEL).slots[WALK].path == p.new_path)
transfer.undo(res["id"])
check("Undo of the first: all four pack files are ROCSS's own, byte for byte", shas(ad) == original)
check("the loose file and its folders are gone, descr_skeleton.txt is ROCSS's",
      not (mod.data / "animations" / "edited").exists()
      and (mod.data / "descr_skeleton.txt").read_bytes() == (ROCSS / "data" / "descr_skeleton.txt").read_bytes())
p3 = animslot.plan_edit(mod, SKEL, WALK, {}, name="same", keep_rebuildable=False)
check("an unedited save is refused: the slot would play what it plays now",
      not p3.ok and any("nothing is edited" in x for x in p3.errors))

# ---- 3) another mod's animation in one slot -------------------------------------------
print("\n3) another mod's animation put in one slot")
if DAC.is_dir():
    dac = Mod(DAC)
    dp = animpack.for_data(DAC / "data")
    pick = None
    for i, s in sk.filled():
        _d, dsk = animslot._skeleton(dp, SKEL)
        ds = dsk.slots[i]
        if ds is None:
            continue
        de = animpack.resolve_slot(dp.anims, ds.path, dsk.scale)
        re_ = animpack.resolve_slot(rp.anims, s.path, sk.scale)
        if de is not None and re_ is not None and dp.anims.read_entry(de) != rp.anims.read_entry(re_) \
                and animpack.content_index(rp, "anims").find(dp.anims.read_entry(de)) is None:
            pick = (i, de)
            break
    check("DaC has an MTW2_Spear action ROCSS plays other bytes for", pick is not None)
    i, de = pick
    b = animslot.plan_bring(mod, SKEL, i, dac)
    check("same bones: DaC's own bytes, at their own scale, under ported/<dac>/",
          b.ok and b.data == dp.anims.read_entry(de) and b.scale == de.scale
          and b.new_path.startswith("mods/Dest/data/animations/ported/divideandconquer/"))
    r = animslot.apply(b)
    now = animpack.open_packs(ad)
    check("the slot plays it", now.anims.read_entry(animpack.resolve_slot(
        now.anims, now.skeleton(SKEL).slots[i].path, sk.scale)) == b.data)
    transfer.undo(r["id"])
    check("Undo: ROCSS's four files", shas(ad) == original)
    other = next(n for n in ("MTW2_Mace", "MTW2_Swordsman", "MTW2_2HSwordsman")
                 if dp.skels.first(n) is not None)
    _o, osk = animslot._skeleton(dp, other)
    b2 = animslot.plan_bring(mod, SKEL, WALK, dac, source_skeleton=other)
    same = animslot._same_bones(osk, sk, 20)
    check(f"another skeleton's walk ({other}): {'its bytes as they are' if same else 'carried across by bone name'}",
          b2.ok and (b2.data == dp.anims.read_entry(animpack.resolve_slot(dp.anims, osk.slots[WALK].path, osk.scale))
                     if same else b2.scale == sk.scale))
else:
    print("  (DaC not installed: skipped)")

# ---- 4) a skeleton on its own -----------------------------------------------------------
print("\n4) a skeleton ported alone, renamed, and a model pointed at it")
if DAC.is_dir():
    entry = next(e for e in mod.modeldb.entries if SKEL.lower() in [x.lower() for x in e.skeletons()])
    sp = animslot.plan_skeleton(mod, dac, SKEL, entry=entry.name, entry_skeleton=SKEL)
    check("DaC's MTW2_Spear is not ROCSS's, so it comes in renamed",
          not sp.errors and sp.dest_name == f"{SKEL}_divideandconquer")
    check("and is kept rebuildable (its loose files and a descr_skeleton.txt block)",
          sp.loose is not None and sp.loose.blocks and sp.loose.files)
    mdb = (mod.data / "unit_models/battle_models.modeldb").read_bytes()
    r = animslot.apply_skeleton(sp, mod, dac)
    mod2 = Mod(mod.root)
    check("the model entry names the new skeleton, and only it changed",
          sp.dest_name in mod2.modeldb.by_name()[entry.name.lower()].skeletons()
          and len(mod2.modeldb.entries) == len(mod.modeldb.entries))
    check("the pack has it", animpack.open_packs(ad).skels.first(sp.dest_name) is not None)
    transfer.undo(r["id"])
    check("Undo: ROCSS's four files and its modeldb, byte for byte",
          shas(ad) == original and (mod.data / "unit_models/battle_models.modeldb").read_bytes() == mdb
          and not (mod.data / "animations" / "ported").exists())
else:
    print("  (DaC not installed: skipped)")

# ---- 5) refusals ------------------------------------------------------------------------
print("\n5) refused")
p = animslot.plan_edit(mod, SKEL, WALK, {"speed": 1.5}, name="x")
animpack.game_running = lambda: ["medieval2.exe"]
check("the game running", refused(lambda: animslot.apply(p), "running"))
animpack.game_running = lambda: []
(ad / "pack.idx").touch()
import os, time  # noqa: E401,E402
os.utime(ad / "pack.idx", (time.time() + 5, time.time() + 5))
check("the packs changed since the plan", refused(lambda: animslot.apply(p), "changed since"))
check("and nothing was written", shas(ad) == original)
bare = fresh("bare", packs=False)
check("a mod that plays vanilla's packs", any("of its own" in x for x in
                                              animslot.plan_edit(bare, SKEL, WALK, {"speed": 2}).errors))
empty = next(i for i, s in enumerate(sk.slots) if s is None)
check("an empty slot", any("empty" in x for x in animslot.plan_edit(mod, SKEL, empty, {"speed": 2}).errors))
check("a name with a folder climb in it", any("name the file" in x for x in
                                              animslot.plan_edit(mod, SKEL, WALK, {"speed": 2}, name="a b?").errors))
check("a skeleton the pack has not got", any("no 'nope'" in x for x in
                                             animslot.plan_edit(mod, "nope", WALK, {"speed": 2}).errors))

# ---- 6) over HTTP ---------------------------------------------------------------------
print("\n6) the page's calls")
import json  # noqa: E402
import threading  # noqa: E402
import urllib.request  # noqa: E402

from unittransfer.server import Handler, Registry, _Server  # noqa: E402

med2 = mod.root.parent.parent
src = med2 / "mods" / "Src"
for rel in REL:
    (src / "data" / rel).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROCSS / "data" / rel, src / "data" / rel)
config.save_settings(med2_root=str(med2), run_full_cleaner=False)
Handler.registry = Registry(cfg / "icons")
httpd = _Server(("127.0.0.1", 0), Handler)
BASE = f"http://127.0.0.1:{httpd.server_address[1]}"
threading.Thread(target=httpd.serve_forever, daemon=True).start()


def call(path, body=None):
    req = urllib.request.Request(BASE + path, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode("utf-8"))


names = call("/api/model/skeleton_names?mod=Src")
check("a mod with no packs of its own lists vanilla's skeletons, or none, and says whose",
      names.get("packs") in ("vanilla", "") or names.get("names") == [])
names = call("/api/model/skeleton_names?mod=Dest")
check("Dest lists its own pack's skeletons", names["packs"] == "mod" and SKEL in names["names"])
body = {"mod": "Dest", "skeleton": SKEL, "slot": WALK, "edits": {"speed": 2}, "name": "http_walk"}
pv = call("/api/model/anim/pack_preview", body)
check("pack_preview: keys to play, with each bone's Euler angles for the editor",
      pv.get("times") and "euler" in pv["bones"][1] and not pv.get("error"))
pl = call("/api/model/anim/pack_plan", body)
check("pack_plan: the new path and what it keeps, nothing written",
      pl["plan"]["ok"] and pl["plan"]["new_path"].endswith("/http_walk.cas") and shas(ad) == original)
ap = call("/api/model/anim/pack_apply", body)
check("pack_apply: written, one job", ap.get("id") and shas(ad) != original)
call("/api/undo", {"id": ap["id"]})
check("and Undo over HTTP puts ROCSS's four files back", shas(ad) == original)
br = call("/api/model/anim/bring_plan", {"mod": "Dest", "skeleton": SKEL, "slot": WALK, "source": "Src"})
check("bring_plan from a mod playing the same animation: refused in a sentence", br.get("error"))
pp = call("/api/model/skeleton/port_plan", {"mod": "Dest", "skeleton": SKEL, "source": "Nope"})
check("an unknown source mod: a sentence, not a fault", pp.get("error"))
bad = call("/api/model/anim/pack_plan", {"mod": "Dest", "skeleton": SKEL, "slot": "x", "edits": {"speed": 2}})
check("a slot that is not a number: a sentence", bad.get("error"))
httpd.shutdown()

print(f"\n{sum(ok)}/{len(ok)} passed")
sys.exit(0 if all(ok) else 1)
