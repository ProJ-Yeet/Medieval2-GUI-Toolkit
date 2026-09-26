"""Phase 82's in-game kits for questions 5 and 6, built into an installed mod.

    python dev/checks/phase82_kit.py apply  [mod]   # default Third_Age_Reforged
    python dev/checks/phase82_kit.py status [mod]
    python dev/checks/phase82_kit.py undo   [mod]

Both kits ride on DaC EUR's Stewards Guards as Phase 83 brought it into
Reforged: its skeleton ``MTW2_Mace_no_stun`` plays animations stored only
inside the pack, under ``mods/<mod>/data/animations/ported/divi/...``, so
there is no doubt which folder a loose file would be looked for in.

* **5 - which of two duplicates wins.** A second ``pack.idx`` entry for the
  standing idle's path is appended, its bytes the skeleton's ``die_forward_2``.
  Idle Steward's Guards that keep falling dead: the LAST copy wins. Idling
  normally: the FIRST.
* **6 - does a loose ``.cas`` override the pack.** The walk's path is written
  as a loose ``.cas`` holding the skeleton's ``celebrate_1``. Cheering as they
  walk: the loose file wins. Walking normally: the pack does.

Before anything is written, the four pack files are copied whole into the
toolkit's backup folder; ``undo`` puts them back byte for byte and deletes the
loose file, whatever the game did in between (a rebuild included, which is
question 4). Refused while the game runs. Not shipped.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

MAIN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(MAIN))

from unittransfer import animpack, casanim, config, skelslots  # noqa: E402

GAME = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition")
SKEL = "MTW2_Mace_no_stun"
IDLE, DIE, WALK, CHEER = "stand_a_idle", "die_forward_2", "walk", "celebrate_1"


def sha(p: Path) -> str:
    return hashlib.sha1(p.read_bytes()).hexdigest()


def slot_path(sk, name: str) -> str:
    (i,) = skelslots.slots_of(name)
    s = sk.slots[i]
    if s is None:
        raise SystemExit(f"{SKEL} leaves {name} (slot {i}) empty")
    return s.path


def loose_target(data: Path, pack_path: str) -> Path:
    """Where the game would look for ``pack_path`` loose: the path is written
    from the game folder (``mods/<mod>/data/...``)."""
    p = pack_path.replace("\\", "/")
    at = p.lower().find("/data/")
    return data / p[at + len("/data/"):]


def manifest_path(mod: str) -> Path:
    return Path(config.CONFIG_DIR) / f"phase82_kit_{mod}.json"


def apply(mod: str) -> None:
    data = GAME / "mods" / mod / "data"
    if animpack.game_running():
        raise SystemExit("the game is running; close it first")
    if manifest_path(mod).is_file():
        raise SystemExit(f"a kit is already in {mod}; undo it first")
    packs = animpack.for_data(data)
    sk = packs.skeleton(SKEL) if packs else None
    if sk is None:
        raise SystemExit(f"{mod}'s pack has no {SKEL}: transfer DaC EUR's Stewards Guards first")
    idle, die, walk, cheer = (slot_path(sk, n) for n in (IDLE, DIE, WALK, CHEER))
    target = loose_target(data, walk)
    if target.exists():
        raise SystemExit(f"{target} exists already")

    # the whole four, first
    back = Path(config.BACKUP_DIR) / f"phase82_kit_{mod}_{time.strftime('%Y%m%d-%H%M%S')}"
    back.mkdir(parents=True)
    files = {}
    for n in animpack.FILES:
        src = packs.dir / n
        shutil.copy2(src, back / n)
        files[n] = {"size": src.stat().st_size, "sha": sha(src)}
    print(f"backed up the four pack files to {back}")

    # 5: a second entry under the idle's path, with the death's bytes
    e = packs.anims.first(die)
    blob = packs.animation_bytes(die)
    dup = animpack.PackEntry(packs.anims.first(idle).name, 0, len(blob), e.scale, e.frames,
                             e.rot_bones, e.pos_bones)
    rec = animpack._append(packs.anims, [(dup, blob)], "animations/pack.dat")
    print(f"5: pack.idx now lists {idle} twice; the second copy is {DIE} ({len(blob):,} bytes)")

    # 6: the walk's path as a loose .cas, with the cheer's keys
    packs = animpack.open_packs(packs.dir)
    anim = casanim.read_packed_bytes(packs.animation_bytes(cheer), cheer, sk.bone_table(), SKEL)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(casanim.write_anim(anim))
    print(f"6: wrote {target.relative_to(data.parent)} holding {CHEER}")

    manifest_path(mod).write_text(json.dumps({
        "mod": mod, "backup": str(back), "files": files, "appended": rec,
        "loose": str(target), "when": time.strftime("%Y-%m-%d %H:%M:%S")}, indent=1),
        encoding="utf-8")
    c = animpack.check(packs.dir)
    print("pack checks:", "pass" if not c["problems"] and c["anim contiguous to the end"] == 1
          and c["anim .dat header = .idx header"] == 1 else c)


def status(mod: str) -> None:
    m = manifest_path(mod)
    if not m.is_file():
        print(f"no kit in {mod}")
        return
    man = json.loads(m.read_text(encoding="utf-8"))
    d = GAME / "mods" / mod / "data" / "animations"
    for n, was in man["files"].items():
        now = (d / n).stat().st_size
        print(f"{n}: {now:,} bytes (before the kit {was['size']:,})")
    print("loose file there:", Path(man["loose"]).is_file())


def undo(mod: str) -> None:
    m = manifest_path(mod)
    if not m.is_file():
        raise SystemExit(f"no kit in {mod}")
    if animpack.game_running():
        raise SystemExit("the game is running; close it first")
    man = json.loads(m.read_text(encoding="utf-8"))
    d = GAME / "mods" / mod / "data" / "animations"
    back = Path(man["backup"])
    for n in man["files"]:
        shutil.copy2(back / n, d / n)
    loose = Path(man["loose"])
    if loose.is_file():
        loose.unlink()
    # the empty folders the loose file needed
    p = loose.parent
    while p != d and p.is_dir() and not any(p.iterdir()):
        p.rmdir()
        p = p.parent
    same = all(sha(d / n) == was["sha"] for n, was in man["files"].items())
    print("the four pack files byte for byte as before the kit:", same)
    if same:
        m.unlink()
        shutil.rmtree(back, ignore_errors=True)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "status"
    mod = sys.argv[2] if len(sys.argv) > 2 else "Third_Age_Reforged"
    {"apply": apply, "status": status, "undo": undo}[what](mod)
