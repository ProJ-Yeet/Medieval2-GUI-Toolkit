"""Phase 57a: the animation writer, the edits, and saving one.

    python -m tests.test_animedit

1. write_anim puts every loose animation of both installed mods back byte for
   byte - including the 230 siege engine files that have no chunk list - and
   an animation made from nothing reads back.
2. Euler angles: quat_from_euler and euler_from_quat undo each other.
3. Each edit, on a real walk: trim, speed, in place, scale, a turn at every
   key, and a key set outright - in the file's own key numbering even when a
   trim runs with it - and what is written re-reads to what was asked for.
4. Saving, on a temp mod: a new file beside the old, descr_skeleton.txt's line
   repointed with its flags and its other-mod prefix kept, the guards, and one
   Undo putting both files back.
"""
import math
import random
import shutil
import sys
from array import array
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from unittransfer import animedit as ae  # noqa: E402
from unittransfer import casanim, transfer  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402

MODS = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition/mods")
DAC = MODS / "Divide_and_Conquer_EUR" / "data"
WALK = DAC / "animations" / "MTW2_Mace" / "MTW2_Mace_walk.cas"
ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return bool(cond)


# ---- 1) the writer ----------------------------------------------------------------
print("\n1) write_anim, back byte for byte")
for name in ("Divide_and_Conquer_EUR", "ROCSS"):
    folder = MODS / name / "data" / "animations"
    if not folder.is_dir():
        continue
    same, diff, bare = 0, [], 0
    for f in folder.rglob("*.cas"):
        raw = f.read_bytes()
        try:
            a = casanim.read_anim_bytes(raw, str(f))
        except casanim.AnimError:
            continue
        bare += a.tail == b""
        if casanim.write_anim(a) == raw:
            same += 1
        else:
            diff.append(f.name)
    check(f"{name}: all {same} readable files written back byte for byte"
          + (f" ({bare} of them with no chunk list)" if bare else ""), not diff and same)

made = casanim.Animation(source="made.cas", version=3.2, length=1.0,
                         key_times=array("f", [0.0, 0.5, 1.0]))
made.tracks = [casanim.Track("Scene Root", -1, (0.0, 0.0, 0.0)),
               casanim.Track("bone_pelvis", 0, (0.0, 0.0, 0.0),
                             rot=array("f", [0, 0, 0, 1] * 3), pos=array("f", [0, 1, 0] * 3))]
back = casanim.read_anim_bytes(casanim.write_anim(made), "made")
check("an animation made from nothing is written, and reads back with its keys",
      back.tracks[1].rot_keys == 3 and back.tracks[1].pos[1] == 1.0 and back.tail)

# ---- 2) angles ---------------------------------------------------------------------
print("\n2) Euler angles")
rng = random.Random(55)
worst = 0.0
for _ in range(500):
    e = [rng.uniform(-179, 179), rng.uniform(-89, 89), rng.uniform(-179, 179)]
    worst = max(worst, max(abs(x - y) for x, y in zip(e, ae.euler_from_quat(ae.quat_from_euler(e)))))
check(f"500 random angles come back (worst {worst:.1e} degrees)", worst < 1e-3)
q = ae.quat_from_euler([0, 0, 90])
check("90 about Z is the quaternion (0, 0, sin 45, cos 45)",
      max(abs(x - y) for x, y in zip(q, (0, 0, math.sqrt(0.5), math.sqrt(0.5)))) < 1e-9)

# ---- 3) the edits ------------------------------------------------------------------
if not WALK.is_file():
    print("\nDaC's MTW2_Mace walk is not installed - the edits and the save are SKIPPED")
else:
    print("\n3) each edit, on MTW2_Mace's walk")
    walk = casanim.read_anim(WALK)
    keys = len(walk.key_times)
    check("no edits is the file itself", casanim.write_anim(ae.apply_edits(walk, {})) == WALK.read_bytes())
    t = ae.apply_edits(walk, {"trim": [2, 10]})
    check(f"trim keeps keys 2 to 10: 9 keys, starting at 0 ({len(t.key_times)} keys)",
          len(t.key_times) == 9 and t.key_times[0] == 0
          and all(tr.rot_keys in (0, 1, 9) for tr in t.tracks))
    check("and the trimmed pelvis is the original's keys 2 to 10",
          list(t.tracks[1].rot) == list(walk.tracks[1].rot[8:44]))
    s = ae.apply_edits(walk, {"speed": 2})
    check(f"speed 2 halves the length ({walk.length:g} s to {s.length:g} s)",
          abs(s.length - walk.length / 2) < 1e-6 and abs(s.key_times[-1] - walk.key_times[-1] / 2) < 1e-6)
    ip = ae.apply_edits(walk, {"in_place": True})
    p0, p1 = walk.tracks[1].pos, ip.tracks[1].pos
    check(f"in place: the pelvis ends where it began ({p0[(keys - 1) * 3 + 2]:.2f} forward before, "
          f"{p1[(keys - 1) * 3 + 2]:.2f} after), its height untouched",
          abs(p1[(keys - 1) * 3 + 2] - p1[2]) < 1e-5
          and all(p0[k * 3 + 1] == p1[k * 3 + 1] for k in range(keys)))
    sc = ae.apply_edits(walk, {"scale": [1, 0.5, 1]})
    check("scale: every pivot and position key, per axis",
          abs(sc.tracks[3].pivot[1] - walk.tracks[3].pivot[1] * 0.5) < 1e-6
          and abs(sc.tracks[1].pos[1] - walk.tracks[1].pos[1] * 0.5) < 1e-6
          and sc.tracks[3].pivot[0] == walk.tracks[3].pivot[0])
    off = ae.apply_edits(walk, {"offsets": [{"bone": "bone_head", "euler": [0, 0, 30]}]})
    h0, h1 = walk.tracks[7], off.tracks[7]
    turned = [ae._qmul(tuple(h0.rot[k * 4:k * 4 + 4]), ae.quat_from_euler([0, 0, 30]))
              for k in range(h0.rot_keys)]
    check("a turn is the key times the turn, at every key",
          max(abs(a - b) for k, qq in enumerate(turned)
              for a, b in zip(ae._norm(qq), h1.rot[k * 4:k * 4 + 4])) < 1e-5)
    jaw = next(i for i, tr in enumerate(walk.tracks) if tr.name == "bone_jaw")
    kset = ae.apply_edits(walk, {"trim": [2, 10], "keys": [{"bone": "bone_jaw", "key": 5, "euler": [25, 0, 0]}]})
    check("a key set is numbered as the file has it, whatever the trim: key 5 is the trimmed key 3",
          ae.euler_from_quat(kset.tracks[jaw].rot[12:16]) == [25.0, 0.0, 0.0])
    lone = casanim.read_anim_bytes(casanim.write_anim(made), "lone")
    lone.tracks[1].rot = array("f", [0, 0, 0, 1])          # one key, held for the whole file
    grown = ae.apply_edits(lone, {"keys": [{"bone": "bone_pelvis", "key": 2, "euler": [0, 90, 0]}]})
    g = grown.tracks[1]
    check("a bone with one rotation key, set at a later key, is given every key, holding the one it had",
          g.rot_keys == 3 and list(g.rot[0:4]) == [0, 0, 0, 1] and list(g.rot[4:8]) == [0, 0, 0, 1]
          and ae.euler_from_quat(g.rot[8:12]) == [0.0, 90.0, 0.0])
    for bad, why in (({"trim": [5, 99]}, "trim past the end"), ({"speed": 0}, "a speed of zero"),
                     ({"offsets": [{"bone": "bone_tail", "euler": [1, 0, 0]}]}, "a bone it does not have")):
        try:
            ae.apply_edits(walk, bad)
            check(f"{why} is refused", False)
        except ae.EditError:
            check(f"{why} is refused", True)
    raw = casanim.write_anim(ae.apply_edits(walk, {"trim": [0, 12], "speed": 1.5, "in_place": True,
                                                   "offsets": [{"bone": "bone_Rupperarm", "euler": [0, 0, 45]}]}))
    re_read = casanim.read_anim_bytes(raw, "edited")
    check("everything at once is written as a file the reader passes", len(re_read.key_times) == 13)

    # ---- 4) saving -------------------------------------------------------------------
    print("\n4) saving, on a temp mod")
    root = Path(_tmp.mkdtemp(prefix="ut_animedit_")) / "AnimMod"
    (root / "data" / "animations" / "MTW2_Mace").mkdir(parents=True)
    shutil.copy2(WALK, root / "data" / "animations" / "MTW2_Mace" / "MTW2_Mace_walk.cas")
    sk_text = ("Version 14\r\n\r\ntype            MTW2_Mace\r\n\r\n"
               "anim\t\twalk\t\tmods/Third_Age_3/data/animations/MTW2_Mace/MTW2_Mace_walk.cas\t\t-fr\t\t-evt:x.evt\r\n"
               "anim\t\trun\t\tmods/Third_Age_3/data/animations/MTW2_Mace/MTW2_Mace_run.cas\t\t-fr\r\n"
               "\r\ntype            Other\r\n\r\n"
               "anim\t\twalk\t\tdata/animations/other/walk.cas\r\n")
    (root / "data" / "descr_skeleton.txt").write_bytes(sk_text.encode("latin-1"))
    mod = Mod(root)
    before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    rel = "animations/MTW2_Mace/MTW2_Mace_walk.cas"
    edits = {"speed": 2}
    for target, why in (("../../evil.cas", "outside animations/"), ("text/x.cas", "outside animations/"),
                        ("animations/MTW2_Mace/MTW2_Mace_walk.cas.bak", None)):
        p = ae.plan_save(mod, rel, edits, target)
        if why:
            check(f"a save {why} is refused ({target})", p.errors)
    p = ae.plan_save(mod, rel, edits, "animations/MTW2_Mace/fast_walk",
                     {"skeleton": "mtw2_mace", "action": "walk"})
    check("a new name gets .cas, and the plan is clean", p.target.endswith("fast_walk.cas") and not p.errors)
    check("the save says the game reads a pack, and how it is rebuilt",
          any("pack.dat" in n and "xidx" in n for n in p.notes))
    res = ae.apply_save(p)
    new = root / "data" / "animations" / "MTW2_Mace" / "fast_walk.cas"
    check("the new file is written and reads as the edit", new.is_file()
          and abs(casanim.read_anim(new).length - casanim.read_anim(WALK).length / 2) < 1e-6)
    sk = (root / "data" / "descr_skeleton.txt").read_bytes().decode("latin-1")
    check("descr_skeleton.txt's walk now names it, keeping the other mod's prefix and the flags",
          "anim\t\twalk\t\tmods/Third_Age_3/data/animations/MTW2_Mace/fast_walk.cas\t\t-fr\t\t-evt:x.evt\r\n" in sk)
    check("and nothing else in the file moved: the run line and the other type's walk",
          sk.replace("animations/MTW2_Mace/fast_walk.cas", "animations/MTW2_Mace/MTW2_Mace_walk.cas") == sk_text)
    clash = ae.plan_save(mod, rel, edits, "animations/MTW2_Mace/fast_walk.cas")
    check("saving over a DIFFERENT file that exists is refused", clash.errors)
    same = ae.plan_save(mod, rel, edits, rel)
    check("saving over the file that was opened is allowed, and says it overwrites",
          not same.errors and same.payload()["overwrites"])
    missing = ae.plan_save(mod, rel, edits, "animations/x.cas", {"skeleton": "MTW2_Mace", "action": "fly"})
    check("pointing an action the skeleton does not have is refused", missing.errors)
    transfer.undo(res["id"])
    after = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    check("one undo puts descr_skeleton.txt back and takes the new file away",
          after == before)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
