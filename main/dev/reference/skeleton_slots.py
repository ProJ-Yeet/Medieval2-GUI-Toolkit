"""Name the 687 slots of a packed skeleton, so the table is data and not code.

    python dev/reference/skeleton_slots.py            # rebuild unittransfer/data/skeleton_slots.json
    python dev/reference/skeleton_slots.py --check    # say what would change, write nothing

A packed skeleton (``skeletons.dat``) holds its animations in 687 slots in the
engine's fixed order, and a slot has no name in the pack: only its position.
``descr_skeleton.txt`` has the names (``anim stand_a_idle <path>``) and no
positions. So the two are aligned wherever they agree: in a skeleton whose
text names exactly as many animations as its pack fills, a slot's name is one
of the names the text gives that slot's path. Across every such skeleton the
candidates are intersected, and a name settled for one slot is struck from
every other slot's candidates, until nothing more settles.

What is left are **groups**: a few slots that share as many names, where every
skeleton on this machine gives each name of the group the same path and the
same flags (``die_to_back_right_2`` and ``die_to_back_left_2`` on 91 and 93).
Nothing on disk tells those apart, and nothing needs to: whichever slot holds
which name, each holds that path. The table keeps the group as it is.

Sources, in the order they are tried: vanilla's packs with the vanilla
``descr_skeleton.txt`` kept under ``Reference/UnitEditor11/vanilla`` (the game
ships none loose, and this copy is not the one the Definitive Edition's pack
was built from: 52 of its skeletons fill more slots than it names, so those
are left out), then every installed mod that has both a pack and the text.

**Then the list.** ``m2_slot_names.json`` beside this script is the engine's
687 slot names in order, shared by the user's friend on 2026-09-26. Measured,
it agrees with every one of the 455 slots the packs name (the 21 grouped ones
included), so it names the 232 slots no installed skeleton fills and says which
slot of a group is which. It is used only after the measurement, and the build
stops if the two ever disagree on a measured slot. The table records which
slots were measured.

The output ``skeleton_slots.json`` ships; this script does not.
"""
from __future__ import annotations

import collections
import json
import sys
import time
from pathlib import Path

MAIN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(MAIN))

from unittransfer import animpack, casanim  # noqa: E402

GAME = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition")
OUT = MAIN / "unittransfer" / "data" / "skeleton_slots.json"
VANILLA_TEXT = MAIN / "Reference" / "UnitEditor11" / "vanilla"


def sources():
    """``(label, packs, types)`` for vanilla and each installed mod."""
    out = []
    van = animpack.for_data(GAME / "data")
    if van and (VANILLA_TEXT / "descr_skeleton.txt").is_file():
        out.append(("vanilla", van, casanim.skeleton_types(VANILLA_TEXT)))
    mods = GAME / "mods"
    for mod in sorted(mods.iterdir()) if mods.is_dir() else ():
        packs = animpack.for_data(mod / "data")
        types = casanim.skeleton_types(mod / "data")
        if packs and packs.skels and types:
            out.append((mod.name, packs, types))
    return out


def observations(srcs):
    """Per skeleton that agrees in count: ``{slot: {names its path has}}``."""
    obs, used = [], collections.Counter()
    for label, packs, types in srcs:
        for e in packs.skels.entries:
            t = types.get(e.name.lower())
            if t is None:
                continue
            sk = packs.skeleton(e.name)
            names = {a.lower() for a, _p in t.anims}
            filled = sk.filled()
            if len(filled) != len(names):
                continue
            by_path = collections.defaultdict(set)
            for a, p in t.anims:
                by_path[animpack._key(p)].add(a.lower())
            obs.append({i: by_path.get(animpack._key(s.path), set()) for i, s in filled})
            used[label] += 1
    return obs, used


def solve(obs):
    slot_of, name_of = {}, {}
    while True:
        cand = {}
        for m in obs:
            for i, names in m.items():
                if i in name_of or not names:
                    continue
                left = {n for n in names if n not in slot_of}
                cand[i] = left if i not in cand else cand[i] & left
        settled = [(i, next(iter(c))) for i, c in cand.items() if len(c) == 1]
        settled = [(i, n) for i, n in settled if n not in slot_of]
        if not settled:
            break
        for i, n in settled:
            if n not in slot_of:
                slot_of[n], name_of[i] = i, n
    # the rest: slots whose candidates are the same k names on k slots
    groups = collections.defaultdict(list)
    for i, c in cand.items():
        if c:
            groups[tuple(sorted(c))].append(i)
    shared = [(sorted(slots), list(names)) for names, slots in groups.items()
              if len(slots) == len(names)]
    return name_of, sorted(shared)


LIST = Path(__file__).resolve().parent / "m2_slot_names.json"


def with_list(measured):
    """The measured slots, checked against the list, and every slot named by it.
    Stops on the first measured slot the list does not agree with."""
    listed = json.loads(LIST.read_text(encoding="utf-8"))["slots"]
    if len(listed) != animpack.SKELETON_SLOTS:
        raise SystemExit(f"{LIST.name} has {len(listed)} names, not {animpack.SKELETON_SLOTS}")
    for i, m in enumerate(measured):
        if m is None:
            continue
        ok = (listed[i].lower() == m.lower()) if isinstance(m, str) \
            else listed[i].lower() in {x.lower() for x in m}
        if not ok:
            raise SystemExit(f"slot {i}: measured {m!r}, {LIST.name} says {listed[i]!r}")
    return list(listed)


def build():
    srcs = sources()
    obs, used = observations(srcs)
    name_of, shared = solve(obs)
    measured = [None] * animpack.SKELETON_SLOTS
    for i, n in name_of.items():
        measured[i] = n
    for group_slots, names in shared:
        for i in group_slots:
            measured[i] = names
    slots = with_list(measured)
    filled = collections.Counter()
    for label, packs, _types in srcs:
        for _e, sk in animpack.iter_skeletons(packs):
            filled.update(i for i, _s in sk.filled())
    return {
        "about": "The 687 slots of a packed skeleton, by position, each by its "
                 "descr_skeleton.txt anim name. `measured` are the slots the installed packs "
                 "name (aligned with their descr_skeleton.txt); the rest, and which slot of a "
                 "measured group is which, come from dev/reference/m2_slot_names.json, which "
                 "agrees with every measured slot. Built by dev/reference/skeleton_slots.py.",
        "built": time.strftime("%Y-%m-%d"),
        "skeletons_used": dict(used),
        "slots": slots,
        "measured": sorted(i for i, m in enumerate(measured) if m is not None),
        "groups_settled_by_list": [g for g, _n in shared],
        "unnamed_but_filled": sorted(i for i in filled if measured[i] is None),
    }


def main(argv):
    table = build()
    text = json.dumps(table, indent=1) + "\n"
    named = len(table["measured"])
    print(f"{named} of {animpack.SKELETON_SLOTS} slots measured, the list agreeing on all, from "
          f"{sum(table['skeletons_used'].values())} skeletons {table['skeletons_used']}; "
          f"filled but unnamed: {table['unnamed_but_filled']}")
    if "--check" in argv:
        old = OUT.read_text(encoding="utf-8") if OUT.is_file() else ""
        strip = lambda s: {k: v for k, v in json.loads(s or "{}").items() if k != "built"}  # noqa: E731
        print("unchanged" if strip(old) == strip(text) else "would change")
        return 0
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(MAIN)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
