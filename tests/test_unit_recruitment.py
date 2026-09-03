"""The unit editor's Recruitment tab: the payload it sends, planned for real.

The tab itself is `web/js/edrecruit.js` and adds no Python - on purpose. Where
a unit can be hired is `recruit_pool` lines in the EDB, and those already have
a reader (`buildings.unit_instances`) and a writer (`buildings.plan_edit`); the
tab is a second FRONT for them, not a second implementation, so a pool edited
from the unit and one edited from the building cannot drift apart.

What that leaves worth testing is the seam - the request shape the tab sends,
which no other screen sends:

  * the tab reaches into several building lines at once and belongs to none of
    them, so **every** edit rides in ``also`` and the main body carries a line
    name with an empty ``levels``. The building editor always has one line it is
    really editing and puts that one in the body, so this arrangement had never
    been planned before.
  * a level payload lists only the pools the tab touched. The rest of the
    level's capabilities are not sent, and must be left exactly where they are.
  * the three ops the tab can produce - rewrite, delete, append - go in one
    request, so one Save is one 🕑 Log entry and one undo.

Nothing here writes: `plan_edit` computes the whole new file as text
(``plan.edb_text``) without touching the disk, so the assertions are made
against real mods, at real scale, with no fixture and no copy.

    python -m tests.test_unit_recruitment
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _realmod
from unittransfer import buildings
from unittransfer.mod import Mod

ok = fail = 0


def check(cond, label, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  [OK ] {label}")
    else:
        fail += 1
        print(f"  [BAD] {label}" + (f" - {detail}" if detail else ""))


def note(text):
    print(f"  ---- {text}")


#: The keys `edRecRowHtml` and `edRecOps` read off every row. A row missing one
#: of them does not render a number box, or renders one that saves to nowhere.
ROW_KEYS = ("line", "line_label", "settlement", "level", "level_label",
            "level_index", "level_count", "faction", "cap_line",
            "initial", "per_turn", "maximum", "experience",
            "requires", "conditions")

POOL_KEYS = ("initial", "per_turn", "maximum", "experience")


def args_for(unit, nums):
    """`edRecOps`'s `args`, character for character."""
    return (f'"{unit}"  {nums["initial"]}  {nums["per_turn"]}  '
            f'{nums["maximum"]}  {nums["experience"]}')


def payload(mod, lines):
    """`edRecPayload`: a line name in the body, every real edit in ``also``."""
    return {"mod": mod.name, "line": lines[0]["line"], "levels": [],
            "fix_ownership": False, "also": lines}


def pick_unit(mod, want_lines=2):
    """A unit trained in at least ``want_lines`` different building lines."""
    best = ("", [])
    for u in mod.edu.units:
        rows = buildings.unit_instances(mod, u.type)["instances"]
        if len({r["line"] for r in rows}) >= want_lines:
            return u.type, rows
        if len(rows) > len(best[1]):
            best = (u.type, rows)
    return best


def free_level(mod, unit):
    """A (line, level) this unit is NOT trained at - what ＋ Add offers."""
    key = unit.strip().lower()
    for bl in mod.edb.buildings:
        for blk in bl.blocks:
            if blk.cap_span == (0, 0):
                continue
            if not any(p.unit.strip().lower() == key for p in blk.recruits):
                return bl.name, blk.name
    return "", ""


def run(mod):
    print(f"\n== {mod.name} ==")
    unit, rows = pick_unit(mod)
    if not rows:
        note("no unit in this mod is trained by any building - nothing to plan")
        return

    # ---- what the tab reads ----
    check(all(k in r for r in rows for k in ROW_KEYS),
          f"every row carries what the tab renders ({unit}, {len(rows)} pool(s))",
          str(sorted(set(ROW_KEYS) - set(rows[0]))))
    caps = [r["cap_line"] for r in rows]
    check(len(caps) == len(set(caps)),
          "cap_line is unique per row - it is the tab's whole row identity")

    lines = sorted({r["line"] for r in rows})
    note(f"{unit}: {len(rows)} pool(s) across {len(lines)} building line(s)")

    # ---- one number, changed ----
    row = rows[0]
    nums = {k: row[k] for k in POOL_KEYS}
    nums["maximum"] = str(int(float(row["maximum"] or 0)) + 7)
    body = payload(mod, [{"line": row["line"], "levels": [
        {"name": row["level"], ("faction_capabilities" if row["faction"]
                                else "capabilities"): [
            {"line": row["cap_line"], "keyword": "recruit_pool",
             "args": args_for(unit, nums), "requires": row["requires"],
             "delete": False}]}]}])
    plan = buildings.plan_edit(mod, body)
    check(not plan.errors, "an edit sent entirely through `also` plans",
          "; ".join(plan.errors))
    check(len(plan.changes) == 1,
          f"…and says exactly one thing changed ({len(plan.changes)})",
          " | ".join(plan.changes))
    check(bool(plan.edb_text), "…and produces a new EDB text")
    before, after = mod.edb.to_text().split("\n"), (plan.edb_text or "").split("\n")
    check(len(before) == len(after), "a rewrite moves no line in the file")
    moved = [i for i, (a, b) in enumerate(zip(before, after)) if a != b]
    check(moved == [row["cap_line"]],
          f"…and touches only line {row['cap_line']}", str(moved[:5]))
    check(nums["maximum"] in after[row["cap_line"]]
          and after[row["cap_line"]].lstrip().startswith("recruit_pool"),
          "…which is still a recruit_pool line, carrying the new number",
          after[row["cap_line"]].strip() if moved else "")

    # The rest of that level is not in the payload at all, and must survive.
    blk = mod.edb.get(row["line"]).blocks[row["level_index"]]
    others = [c.line for c in blk.capabilities if c.line != row["cap_line"]]
    check(all(before[i] == after[i] for i in others),
          f"the {len(others)} capability line(s) the payload never mentions are byte-identical")

    # ---- delete ----
    body = payload(mod, [{"line": row["line"], "levels": [
        {"name": row["level"], ("faction_capabilities" if row["faction"]
                                else "capabilities"): [
            {"line": row["cap_line"], "keyword": "recruit_pool",
             "args": args_for(unit, {k: row[k] for k in POOL_KEYS}),
             "requires": row["requires"], "delete": True}]}]}])
    plan = buildings.plan_edit(mod, body)
    gone = (plan.edb_text or "").split("\n")
    check(not plan.errors and len(plan.changes) == 1,
          "the delete toggle plans as one removal", "; ".join(plan.errors))
    check(len(gone) == len(before) - 1, "…and the file is one line shorter")
    check(unit.lower() not in gone[row["cap_line"]].lower(),
          "…with that pool no longer on its line")

    # ---- ＋ Add a building ----
    line, level = free_level(mod, unit)
    if not line:
        note("every level in this mod already trains this unit - nothing to add")
    else:
        new = {"initial": "1", "per_turn": "0.5", "maximum": "2", "experience": "0"}
        body = payload(mod, [{"line": line, "levels": [
            {"name": level, "capabilities": [
                {"line": None, "keyword": "recruit_pool",
                 "args": args_for(unit, new), "requires": "", "delete": False}]}]}])
        plan = buildings.plan_edit(mod, body)
        grown = (plan.edb_text or "").split("\n")
        check(not plan.errors, f"a new pool in {line} · {level} plans",
              "; ".join(plan.errors))
        check(len(plan.changes) == 1, "…as one addition", " | ".join(plan.changes))
        check(len(grown) == len(before) + 1, "…and the file is one line longer")
        check(any(unit in ln and "recruit_pool" in ln
                  for ln in grown if ln not in before),
              "…and the line that appeared is this unit's recruit_pool")

    # ---- all three at once, across two building lines ----
    other = next((r for r in rows if r["line"] != row["line"]), None)
    parts = [{"line": row["line"], "levels": [
        {"name": row["level"], ("faction_capabilities" if row["faction"]
                                else "capabilities"): [
            {"line": row["cap_line"], "keyword": "recruit_pool",
             "args": args_for(unit, nums), "requires": row["requires"],
             "delete": False}]}]}]
    want = 1
    if other:
        parts.append({"line": other["line"], "levels": [
            {"name": other["level"], ("faction_capabilities" if other["faction"]
                                      else "capabilities"): [
                {"line": other["cap_line"], "keyword": "recruit_pool",
                 "args": args_for(unit, {k: other[k] for k in POOL_KEYS}),
                 "requires": other["requires"], "delete": True}]}]})
        want += 1
    if line:
        parts.append({"line": line, "levels": [
            {"name": level, "capabilities": [
                {"line": None, "keyword": "recruit_pool",
                 "args": args_for(unit, {"initial": "1", "per_turn": "0.5",
                                         "maximum": "2", "experience": "0"}),
                 "requires": "", "delete": False}]}]})
        want += 1
    plan = buildings.plan_edit(mod, payload(mod, parts))
    check(not plan.errors,
          f"one request over {len({p['line'] for p in parts})} building line(s) plans",
          "; ".join(plan.errors))
    check(len(plan.changes) == want,
          f"…and reports all {want} of its edits ({len(plan.changes)})",
          " | ".join(plan.changes))
    # A note from a line other than the plan's own says WHICH line, or the
    # preview reads as if one building grew rows it never had.
    tagged = [c for c in plan.changes if " · " in c]
    check(len(tagged) == want - 1 or want == 1,
          "…each one but the first naming the line it belongs to",
          " | ".join(plan.changes))
    check(bool(plan.edb_text) and buildings.parse_text(plan.edb_text).get(parts[0]["line"]),
          "…and the file it would write still parses")

    # ---- the recruitment-limit check counts the file, not just the payload ----
    # An `also` payload carries only the rows the tab touched, so the level's
    # untouched pools have to come from disk or every add would look free. What
    # that means here is that a warning, when there is one, names a level that
    # really exists rather than one invented from a partial payload.
    note(f"recruit-limit warnings on this plan: {len(plan.warnings)}")
    levels = {blk.name for bl in mod.edb.buildings for blk in bl.blocks}
    check(all(any(n in w for n in levels) for w in plan.warnings),
          "every warning names a level that is really in the file",
          " | ".join(plan.warnings[:2]))


def main():
    mods = _realmod.installed()
    if not mods:
        print(f"SKIPPED - no installed mod to test against under {_realmod.MODS}")
        return 0
    for path in mods:
        run(Mod(path))
    print(f"\n{ok} passed, {fail} failed")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
