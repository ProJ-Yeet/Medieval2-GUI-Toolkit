"""Phase 81: append to a pack, and take it back.

    python -m tests.test_packport

1. The plan, on a small built pair where every rule has a case: an animation
   reused by path, reused by its bytes under another path, shared inside the
   port, appended, and appended renamed; a skeleton renamed because its name
   is taken.
2. Written, and read back: the four files pass every structural check, the
   ported skeleton is the source's but for its rewritten slot paths, and
   planning it again finds nothing left to bring.
3. Undone: all four files byte for byte as before.
4. A real port on a copy of ROCSS: DaC's MTW2_2HSwordsman and its weapon
   skeleton, through the transfer log, checked, and undone byte for byte;
   an undo refused when the .dat is no longer the file it appended to.
5. Refused: the game running, the packs changed since the plan, a
   destination with no packs, an unknown skeleton; an exception midway
   leaves the files as they were.
6. The dry run: every DaC skeleton into ROCSS, against the table measured on
   2026-09-23.
"""
import hashlib
import shutil
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from unittransfer import animpack, config, transfer  # noqa: E402

GAME = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition")
DAC, ROCSS = GAME / "mods" / "Divide_and_Conquer_EUR", GAME / "mods" / "ROCSS"
ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


def shas(anim_dir: Path) -> dict:
    return {n: hashlib.sha1((anim_dir / n).read_bytes()).hexdigest() for n in animpack.FILES}


def write_pack(folder, stem, magic, items, v1, v2):
    """``items``: (name, template entry or None, bytes)."""
    entries, at, blobs = [], animpack.HEADER_SIZE, []
    for name, tmpl, data in items:
        if tmpl is not None and tmpl.is_anim:
            entries.append(animpack.PackEntry(name, at, len(data), tmpl.scale, tmpl.frames,
                                              tmpl.rot_bones, tmpl.pos_bones))
        else:
            entries.append(animpack.PackEntry(name, at, len(data)))
        blobs.append(data)
        at += len(data)
    idx = animpack.PackIndex(magic, entries, v1, v2)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{stem}.idx").write_bytes(idx.to_bytes())
    (folder / f"{stem}.dat").write_bytes(idx.header() + b"".join(blobs))


def refused(fn, *words):
    try:
        fn()
    except animpack.PackError as e:
        return all(w in str(e) for w in words)
    return False


if not (GAME / "data").is_dir():
    print("SKIPPED: vanilla is not installed here")
    sys.exit(0)

cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"
real_running = animpack.game_running
animpack.game_running = lambda: []          # the suite never waits on a real game

# ---- 1) the plan, every rule --------------------------------------------------------
print("\n1) the plan, on a built pair")
van = animpack.for_data(GAME / "data")
NAME = "MTW2_2HSwordsman"
vs = van.skeleton(NAME)
p = {i: vs.slots[i].path for i in (0, 11, 20, 686)}
vb = {i: van.animation_bytes(p[i]) for i in p}
other = next(s.path for i, s in vs.filled() if i not in p and van.animation_bytes(s.path) != vb[11])
ob = van.animation_bytes(other)
other2 = next(s.path for i, s in van.skeleton("MTW2_Mace").filled()
              if van.animation_bytes(s.path) not in (ob, *vb.values()))
o2b = van.animation_bytes(other2)
tmpl = lambda path: van.anims.first(path)
DUP, CLASH, Q = "mods/src/data/animations/x/dup.cas", "mods/src/data/animations/x/clash.cas", \
    "mods/src/data/animations/x/q_run.cas"
sk = animpack.PackedSkeleton(van.skels.read_entry(van.skels.first(NAME)))
keep = {0: p[0], 11: p[11], 12: DUP, 13: CLASH, 20: Q, 686: p[686]}
for i in range(animpack.SKELETON_SLOTS):
    if i in keep:
        if sk.slots[i] is None:
            sk.slots[i] = animpack.PackedSkeleton(van.skels.read_entry(van.skels.first(NAME))).slots[11]
        sk.slots[i].path = keep[i]
    else:
        sk.slots[i] = None
src_bytes = sk.to_bytes()
built = Path(_tmp.mkdtemp(prefix="ut_packport_"))
src_data = built / "mods" / "Src" / "data"
dst_data = built / "mods" / "Dest" / "data"
write_pack(src_data / "animations", "skeletons", animpack.SKEL_MAGIC, [(NAME, None, src_bytes)], 14, 24)
write_pack(src_data / "animations", "pack", animpack.ANIM_MAGIC, [
    (p[0], tmpl(p[0]), vb[0]), (p[11], tmpl(p[11]), vb[11]), (DUP, tmpl(p[11]), vb[11]),
    (CLASH, tmpl(other), ob), (Q, tmpl(p[20]), vb[20]), (p[686], tmpl(p[686]), vb[686])], 9, 0)
mace = van.skels.read_entry(van.skels.first("MTW2_Mace"))
write_pack(dst_data / "animations", "skeletons", animpack.SKEL_MAGIC, [(NAME, None, mace)], 14, 24)
write_pack(dst_data / "animations", "pack", animpack.ANIM_MAGIC, [
    (p[686], tmpl(p[686]), vb[686]), (CLASH, tmpl(other2), o2b),
    ("mods/dest/data/animations/y/run_elsewhere.cas", tmpl(p[20]), vb[20])], 9, 0)
before = shas(dst_data / "animations")

plan = animpack.plan_port(src_data, dst_data, [NAME], tag="src")
act = {a.path: (a.action, a.dest_path) for a in plan.anims}
check("the plan is sound and names its source's own packs", plan.ok and plan.source_packs == "mod")
check("the default, there with the same bytes: reused", act[p[686]] == ("reuse", p[686]))
check("the run, there under another path: reused by its bytes, the slot pointed there",
      act[Q] == ("reuse_content", "mods/dest/data/animations/y/run_elsewhere.cas"))
check("two paths with the same bytes: the second shares the first's append",
      act[p[11]] == ("append", p[11]) and act[DUP] == ("shared", p[11]))
check("a path the destination has with other bytes: appended under ported/<tag>/",
      act[CLASH] == ("append_renamed", "mods/Dest/data/animations/ported/src/x/clash.cas"))
check("the rest appended under their own paths", act[p[0]] == ("append", p[0]))
s = plan.skeletons[0]
check(f"its name taken by another skeleton: renamed {s.dest_name}",
      s.action == "rename" and s.dest_name == f"{NAME}_src" and plan.renames == {NAME: f"{NAME}_src"})
check("three slot paths rewritten, and the totals say so",
      s.rewrites == 3 and plan.totals()["slot paths rewritten"] == 3
      and plan.totals()["anim bytes appended"] == len(vb[0]) + len(vb[11]) + len(ob))
check("planning wrote nothing", shas(dst_data / "animations") == before)

# ---- 2) written, and read back ------------------------------------------------------
print("\n2) written")
rec = animpack.port(plan, "Dest", dst_data.parent, "Src")
c = animpack.check(dst_data / "animations")
dp = animpack.open_packs(dst_data / "animations")
# (the destination's own skeleton here is a stand-in whose slots this small
# pack never held, so only the ported one's paths are held to the index)
check("every structural check passes on the result, and every slot path of the ported skeleton is indexed",
      c["problems"] == [] and c["skel reads"] == c["skel round-trips"] == 2
      and all(c[f"{k} contiguous to the end"] == 1 and c[f"{k} .dat header = .idx header"] == 1
              and c[f"{k} index round-trips"] == 1 for k in ("anim", "skel"))
      and all(s_.path in dp.anims for _i, s_ in dp.skeleton(f"{NAME}_src").filled()))
back = dp.skeleton(f"{NAME}_src")
orig = animpack.PackedSkeleton(src_bytes)
diff = [i for i in range(animpack.SKELETON_SLOTS) if (back.slots[i] is None) != (orig.slots[i] is None)
        or (back.slots[i] and back.slots[i].to_bytes() != orig.slots[i].to_bytes())]
check("the ported skeleton reads back the source's, but for the three rewritten slot paths",
      diff == [12, 13, 20] and back.tail == orig.tail
      and [b.to_bytes() for b in back.bones] == [b.to_bytes() for b in orig.bones])
for i in (12, 13, 20):
    orig.slots[i].path = back.slots[i].path
check("  ... and with those put in, byte for byte", back.to_bytes() == orig.to_bytes())
check("every appended animation reads back its source bytes",
      dp.animation_bytes(p[0]) == vb[0] and dp.animation_bytes(p[11]) == vb[11]
      and dp.animation_bytes(act[CLASH][1]) == ob and dp.animation_bytes(CLASH) == o2b)
check("the destination's own entries are where they were",
      dp.skels.entries[0].name == NAME and dp.skels.read_entry(dp.skels.entries[0]) == mace)
again = animpack.plan_port(src_data, dst_data, [NAME], tag="src")
t = again.totals()
check("planned again, nothing is left to bring: the skeleton is reused under its new name",
      again.skeletons[0].action == "reuse_as" and again.skeletons[0].dest_name == f"{NAME}_src"
      and t["anim bytes appended"] == 0 and t["skeleton bytes appended"] == 0)
check("the log has one job with the two packs appended and their indexes backed up",
      [r["rel"] for r in rec["manifest"]["appended"]] == ["animations/pack.dat", "animations/skeletons.dat"]
      and rec["manifest"]["backed_up"] == ["animations/pack.idx", "animations/skeletons.idx"])

# ---- 3) undone ----------------------------------------------------------------------
print("\n3) undone")
transfer.undo(rec["id"])
check("all four files byte for byte as before", shas(dst_data / "animations") == before)
check("and no .tmp is left beside them", not list((dst_data / "animations").glob("*.tmp")))

# ---- 4) a real port on a copy of ROCSS -------------------------------------------
print("\n4) DaC into a copy of ROCSS")
if not (DAC.is_dir() and ROCSS.is_dir()):
    print("  SKIPPED: DaC and ROCSS are not both installed")
else:
    game = Path(_tmp.mkdtemp(prefix="ut_packport_ro_"))
    ro_data = game / "mods" / "ROCSS" / "data"
    (ro_data / "animations").mkdir(parents=True)
    for n in animpack.FILES:
        shutil.copy2(ROCSS / "data" / "animations" / n, ro_data / "animations" / n)
    ro_before = shas(ro_data / "animations")
    dsk = animpack.for_data(DAC / "data").skeleton("MTW2_2HSwordsman")
    real = animpack.plan_port(DAC / "data", ro_data, ["MTW2_2HSwordsman", "MTW2_2HSwordsman_Primary"])
    t = real.totals()
    check(f"planned: tag {real.tag!r}, {t['animations']} animations, {t['animations reuse_content']} "
          f"reused by their bytes, {t['anim bytes appended'] / 1e6:.2f} MB to append",
          real.ok and real.tag == "divideandconquer" and t["animations reuse_content"] > 0
          and t["animations"] == len(dsk.animation_paths()) + len({s.path.lower() for _i, s in
              animpack.for_data(DAC / "data").skeleton("MTW2_2HSwordsman_Primary").filled()} - {
              x.lower() for x in dsk.animation_paths()}))
    rrec = animpack.port(real, "ROCSS", ro_data.parent, "Divide_and_Conquer_EUR")
    c = animpack.check(ro_data / "animations")
    n_a, n_s = len(animpack.open_packs(ro_data / "animations").anims), len(
        animpack.open_packs(ro_data / "animations").skels)
    check(f"every structural check passes: {n_a:,} animations and {n_s} skeletons, every slot path indexed",
          c["problems"] == [] and c["anim reads"] == c["anim entries"] == n_a
          and c["skel reads"] == c["skel entries"] == c["skel round-trips"] == n_s
          and c["skel slot paths"] == c["skel slot paths in pack.idx"]
          and c["anim contiguous to the end"] == c["skel contiguous to the end"] == 1)
    grown = (ro_data / "animations" / "pack.dat").stat().st_size - (ROCSS / "data" / "animations" / "pack.dat").stat().st_size
    check(f"pack.dat grew by exactly what was planned ({grown:,} bytes)",
          grown == t["anim bytes appended"])
    rp = animpack.open_packs(ro_data / "animations")
    name = real.skeletons[0].dest_name
    got = rp.skeleton(name)
    check(f"{name} reads back and every one of its animations plays out of the pack",
          got is not None and all(rp.animation_bytes(s.path) is not None for _i, s in got.filled()))
    transfer.undo(rrec["id"])
    check("undone: ROCSS's four files byte for byte as before", shas(ro_data / "animations") == ro_before)
    # an undo is refused when the .dat is no longer the file it appended to
    real = animpack.plan_port(DAC / "data", ro_data, ["MTW2_2HSwordsman"])
    rrec = animpack.port(real, "ROCSS", ro_data.parent, "Divide_and_Conquer_EUR")
    with open(ro_data / "animations" / "pack.dat", "ab") as f:
        f.write(b"\0" * 16)                 # another tool wrote to it since
    mid = shas(ro_data / "animations")
    check("an undo after another tool wrote to pack.dat is refused, saying why",
          refused(lambda: transfer.undo(rrec["id"]), "no longer the file"))
    check("  ... and touches nothing, the indexes included", shas(ro_data / "animations") == mid
          and not next(e for e in config.load_log() if e["id"] == rrec["id"]).get("undone"))
    with open(ro_data / "animations" / "pack.dat", "r+b") as f:
        f.truncate(f.seek(0, 2) - 16)
    transfer.undo(rrec["id"])
    check("put right, the undo goes through, byte for byte", shas(ro_data / "animations") == ro_before)

# ---- 5) refused -------------------------------------------------------------------
print("\n5) refused")
plan = animpack.plan_port(src_data, dst_data, [NAME], tag="src")
animpack.game_running = lambda: ["medieval2.exe"]
check("with the game running", refused(lambda: animpack.apply_port(plan, cfg / "b1"), "medieval2.exe is running"))
animpack.game_running = lambda: []
dat = dst_data / "animations" / "pack.dat"
st = dat.stat()
import os  # noqa: E402
os.utime(dat, ns=(st.st_atime_ns, st.st_mtime_ns + 10**9))
check("when the packs changed since the plan", refused(lambda: animpack.apply_port(plan, cfg / "b2"),
                                                       "changed since"))
nopack = built / "mods" / "NoPack" / "data"
nopack.mkdir(parents=True)
check("into a mod with no packs of its own",
      not animpack.plan_port(src_data, nopack, [NAME]).ok
      and "no animation packs of its own" in animpack.plan_port(src_data, nopack, [NAME]).errors[0])
check("a skeleton the source has not got",
      "has no 'nobody'" in animpack.plan_port(src_data, dst_data, ["nobody"]).errors[0])
plan = animpack.plan_port(src_data, dst_data, [NAME], tag="src")
before = shas(dst_data / "animations")
real_replace = animpack.os.replace
calls = []


def fail_second(a, b):
    calls.append(a)
    if len(calls) == 2:                     # the skeletons' .idx, after the animations went in
        raise OSError("disk full, as it were")
    return real_replace(a, b)


animpack.os.replace = fail_second
try:
    animpack.apply_port(plan, cfg / "b3")
    raised = False
except OSError:
    raised = True
animpack.os.replace = real_replace
check("an exception midway (the second index) is raised, and all four files are as they were",
      raised and shas(dst_data / "animations") == before
      and not list((dst_data / "animations").glob("*.tmp")))
animpack.game_running = real_running
check("game_running answers on this machine without a game open", isinstance(real_running(), list))

# ---- 6) the dry run -----------------------------------------------------------------
print("\n6) every DaC skeleton into ROCSS, planned")
if DAC.is_dir() and ROCSS.is_dir():
    dpk, rpk = animpack.for_data(DAC / "data"), animpack.for_data(ROCSS / "data")
    names, seen = [], set()
    for e in dpk.skels.entries:
        if e.name.lower() not in seen:
            seen.add(e.name.lower())
            names.append(e.name)
    rows, refs, reused = [], 0, 0
    for n in names:
        pl = animpack.plan_port(DAC / "data", ROCSS / "data", [n])
        refs += len(pl.anims)
        reused += sum(1 for a in pl.anims if a.action in ("reuse", "reuse_content"))
        rows.append((len(pl.anims), sum(a.size for a in pl.anims), pl.appended()[0], pl.skeletons[0].action))
    renamed = sum(1 for r in rows if r[3] == "rename")
    taken = sum(1 for n in names if rpk.skels.first(n) is not None)
    med = lambda k: statistics.median(r[k] for r in rows)
    check(f"{len(names)} skeletons; {taken} names ROCSS has, all with other data (the table: 134 of 410)",
          len(names) == 410 and taken == 134
          and all(dpk.skels.read_entry(dpk.skels.first(n)) != rpk.skels.read_entry(rpk.skels.first(n))
                  for n in names if rpk.skels.first(n) is not None))
    check(f"  ... {renamed} of them renamed, the rest reused once their slots point at ROCSS's own copies",
          renamed + sum(1 for r in rows if r[3] in ("reuse", "reuse_as")) >= taken - 1)
    check(f"animations per skeleton: median {med(0):g}, max {max(r[0] for r in rows)} (the table: 145, 219)",
          med(0) == 145 and max(r[0] for r in rows) == 219)
    check(f"bytes per skeleton: median {med(1) / 1e6:.2f} MB, {med(2) / 1e6:.2f} MB after content dedup, "
          f"max {max(r[1] for r in rows) / 1e6:.2f} (the table: 3.3, 1.6, 5.1)",
          round(med(1) / 1e6, 1) == 3.3 and round(med(2) / 1e6, 1) == 1.6
          and round(max(r[1] for r in rows) / 1e6, 1) == 5.1)
    check(f"slot paths: {refs:,}, {reused:,} already in ROCSS byte for byte (the table: 45 784 and 9 736, "
          "the second re-measured 11 133 two ways, then 10 979 once Phase 86 took each slot's copy at "
          "its skeleton's scale, as the game does)", refs == 45784 and reused == 10979)
    allp = animpack.plan_port(DAC / "data", ROCSS / "data", names)
    ta = allp.totals()
    check(f"all 410 in one plan: {(ta['anim bytes appended'] + ta['skeleton bytes appended']) / 1e6:.0f} MB "
          f"to append, {ta['slot paths rewritten']:,} slot paths rewritten, no error", allp.ok)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
