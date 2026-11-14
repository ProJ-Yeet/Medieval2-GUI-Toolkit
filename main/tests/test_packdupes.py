"""Duplicate animations: found, compared, chosen, merged, undone (101h).

Run:  python -m tests.test_packdupes

A small mod built here, so nothing installed is needed:
  * ``a.cas`` twice at scale 1, different bytes: the first plays; choosing the
    second puts it in the first one's place and the first goes;
  * ``b.cas`` and ``c.cas``, the same bytes: merged into ``b``, the skeleton
    slot and the ``descr_skeleton.txt`` line that named ``c`` now name ``b``;
  * ``d.cas`` twice, the same bytes: counted, left to Phase 85's compaction;
  * Undo puts every file back byte for byte.
"""
import hashlib
import struct
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests import _tmp  # noqa: E402
from unittransfer import animpack, config, packdupes, transfer  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


def anim(frames, turn):
    """``frames`` frames of 2 bones, the second turned by ``turn`` radians
    about z: a real PackedAnimation's bytes."""
    nq = 2
    out = struct.pack("<HHB", frames, nq, 0)
    q = (0.0, 0.0, 0.0, 1.0)
    t = (0.0, 0.0, __import__("math").sin(turn / 2), __import__("math").cos(turn / 2))
    for _f in range(frames):
        out += struct.pack("<4f", *q) + struct.pack("<4f", *t)
    out += struct.pack(f"<{frames * 2}f", *([0.0] * frames * 2))      # steps
    out += struct.pack(f"<{frames}f", *([0.0] * frames))              # distance left
    out += struct.pack(f"<{frames * 3}f", *([0.0] * frames * 3))      # control
    out += struct.pack("<8f", *([0.0] * 8)) + (0).to_bytes(8, "little")
    assert len(out) == animpack.anim_size(frames, nq, 0)
    return out


def skeleton_bytes(slots):
    out = struct.pack("<fHf", 1.0, 1, 0.0)
    out += struct.pack("<i3fi4si12f", 9, 0, 0, 0, -1, b"\0" * 4, -1, *([0.0] * 12)) + b"bone_pelvis\0"
    for i in range(animpack.SKELETON_SLOTS):
        path = slots.get(i)
        if path is None:
            out += b"\0"
            continue
        out += path.encode() + b"\0" + struct.pack("<h3fhfhfhh3f", *([0] * 13))
        out += struct.pack("<I", 0) + struct.pack("<ih", 0, 0)
    return out + struct.pack("<3f", 1, 2, 3) + b"\0" * 20


def write_pack(folder, stem, magic, items, v1, v2):
    """``items``: (name, bytes, scale or None)."""
    entries, at = [], animpack.HEADER_SIZE
    for name, data, scale in items:
        if scale is None:
            entries.append(animpack.PackEntry(name, at, len(data)))
        else:
            nf, nq, npb = struct.unpack_from("<HHB", data, 0)
            entries.append(animpack.PackEntry(name, at, len(data), scale, nf, nq, npb))
        at += len(data)
    idx = animpack.PackIndex(magic, entries, v1, v2)
    (folder / f"{stem}.idx").write_bytes(idx.to_bytes())
    (folder / f"{stem}.dat").write_bytes(idx.header() + b"".join(d for _n, d, _s in items))


tmp = Path(_tmp.mkdtemp(prefix="ut_packdupes_"))
config.CONFIG_DIR = tmp / "cfg"; config.BACKUP_DIR = tmp / "cfg" / "backups"
config.SETTINGS_PATH = tmp / "cfg" / "settings.json"; config.LOG_PATH = tmp / "cfg" / "transfers.json"
config.CONFIG_DIR.mkdir(parents=True)

root = tmp / "Mod"
data = root / "data"
adir = data / "animations"
adir.mkdir(parents=True)
A1, A2, BC, D = anim(10, 0.0), anim(12, 1.0), anim(8, 0.5), anim(6, 0.2)
P = "data/animations/x/"
write_pack(adir, "pack", animpack.ANIM_MAGIC, [
    (P + "a.cas", A1, 1.0), (P + "b.cas", BC, 1.0), (P + "a.cas", A2, 1.0),
    (P + "c.cas", BC, 1.0), (P + "d.cas", D, 1.0), (P + "d.cas", D, 1.0)], 9, 0)
write_pack(adir, "skeletons", animpack.SKEL_MAGIC, [
    ("fs_test", skeleton_bytes({0: P + "a.cas", 1: P + "b.cas", 2: P + "c.cas", 3: P + "d.cas"}), None)], 14, 24)
TEXT = ("type fs_test\nreference fs_test\n  anim stand " + P + "a.cas\r\n"
        "  anim walk " + P + "c.cas\r\n  anim run " + P + "b.cas\r\n")
(data / "descr_skeleton.txt").write_text(TEXT, encoding="latin-1", newline="")
before = {p.name: hashlib.sha1(p.read_bytes()).hexdigest() for p in list(adir.iterdir()) + [data / "descr_skeleton.txt"]}

print("\n1) found")
rep = packdupes.find(data)
check("no error", rep["error"] == "")
check("a.cas is one conflict, its first copy playing",
      len(rep["conflicts"]) == 1 and rep["conflicts"][0]["path"].endswith("a.cas")
      and [c["plays"] for c in rep["conflicts"][0]["copies"]] == [True, False])
check("  named by the skeleton", rep["conflicts"][0]["users"] == ["fs_test"])
check("b.cas and c.cas are one identical group",
      len(rep["identical"]) == 1
      and sorted(r["path"].rsplit("/", 1)[1] for r in rep["identical"][0]["paths"]) == ["b.cas", "c.cas"])
check("d.cas's second copy is the same bytes, counted", rep["same_bytes"] == 1)

print("\n2) compared")
cmp_ = packdupes.compare(data, P + "a.cas", 1.0)
check("two copies, frames and seconds read", [c["frames"] for c in cmp_["copies"]] == [10, 12]
      and cmp_["copies"][1]["seconds"] == 0.6)
diff = cmp_["copies"][1]["difference"]
check(f"the second moves about 57 degrees away from the first ({diff})",
      diff is not None and 56 < diff["max"] < 58)

print("\n3) chosen and merged, one job")
mod = SimpleNamespace(data=data, root=root, name="Mod")
offset2 = rep["conflicts"][0]["copies"][1]["offset"]
rec = packdupes.apply(mod, [{"path": P + "a.cas", "scale": 1.0, "offset": offset2}],
                      [{"paths": [P + "b.cas", P + "c.cas"], "keep": P + "b.cas"}])
packs = animpack.open_packs(adir)
names = [e.name.rsplit("/", 1)[1] for e in packs.anims.entries]
check(f"the pack holds a, b, d, d in order ({names})", names == ["a.cas", "b.cas", "d.cas", "d.cas"])
check("a.cas plays the chosen copy", packs.anims.read_entry(packs.anims.first(P + "a.cas")) == A2)
sk = animpack.PackedSkeleton(packs.skels.read_entry(packs.skels.first("fs_test")))
check("the slot that named c.cas names b.cas", sk.slots[2].path == P + "b.cas"
      and sk.slots[0].path == P + "a.cas" and sk.slots[3].path == P + "d.cas")
txt = (data / "descr_skeleton.txt").read_bytes().decode("latin-1")
check("descr_skeleton.txt's walk line follows, line ends kept",
      "anim walk " + P + "b.cas\r\n" in txt and "c.cas" not in txt)
check("nothing left to find but d's same bytes",
      packdupes.find(data)["conflicts"] == [] and packdupes.find(data)["identical"] == [])

print("\n4) undone")
transfer.undo(rec["id"])
after = {p.name: hashlib.sha1(p.read_bytes()).hexdigest() for p in list(adir.iterdir()) + [data / "descr_skeleton.txt"]}
check("every file back byte for byte", after == before)

print("\n5) a stale request is refused")
try:
    packdupes.apply(mod, [{"path": P + "a.cas", "scale": 1.0, "offset": 999999}], [])
    refused = False
except animpack.PackError:
    refused = True
check("an offset that is not a copy any more", refused)

import shutil  # noqa: E402
shutil.rmtree(tmp, ignore_errors=True)
print("\n" + ("ALL PASSED" if all(ok) else "SOME FAILED"))
sys.exit(0 if all(ok) else 1)
