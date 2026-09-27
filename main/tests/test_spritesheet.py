"""A faction's shield and the interface's sprite sheets (Phase 91).

Run:  python -m tests.test_spritesheet

Reported 2026-09-26: a faction made with Add a faction showed no faction button
on the campaign map. The engine resolves ``logo_index`` by name in
``ui/strategy.sd`` (``small_logo_index`` in ``ui/shared.sd``) and draws sprite 0
for a name that is not there. Four parts:

1. **The sheet itself**, built here byte by byte: read to its last byte, an
   alias appended with every other sprite keeping its position, and the refusals.
2. **The checks**, on a synthetic mod with one good faction and three bad ones:
   the roster's findings (the editor and Health), the audit's row, the editor's
   box, and the repair written and undone byte for byte.
3. **The clone**: a new faction gets shields of its own name, drawn as the
   donor's; a batch of two lands both; a name already drawn is used as it is; a
   mod whose sheets are packed keeps the donor's value, as it always did.
4. **The installed mods**, read-only: every sheet parses, and no faction's
   shield is reported - the baseline a check has to keep.
"""
import shutil
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests import _tmp  # noqa: E402
from unittransfer import config                                    # noqa: E402
from unittransfer import factionaudit as fa                        # noqa: E402
from unittransfer import factionclone as fc                        # noqa: E402
from unittransfer import factions as fac                           # noqa: E402
from unittransfer import keyblock as kb                            # noqa: E402
from unittransfer import spritesheet as ss                         # noqa: E402
from unittransfer import transfer                                  # noqa: E402
from unittransfer.mod import Mod                                   # noqa: E402

# a config of its own, as test_factionaudit keeps: never the real undo log
cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
if config.SETTINGS_PATH.is_file():
    shutil.copy2(config.SETTINGS_PATH, cfg / "settings.json")
config.CONFIG_DIR = cfg; config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"; config.LOG_PATH = cfg / "transfers.json"

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return bool(cond)


def pascal(b: bytes) -> bytes:
    return struct.pack("<I", len(b)) + b


def sheet(pages, sprites) -> bytes:
    """A version-6 sheet: pages are (name, w, h), sprites (name, page, l, r, t, b)."""
    out = struct.pack("<3I", 6, len(pages), len(sprites))
    for name, w, h in pages:
        mask = bytes([0x5A]) * (w * h // 8)
        out += pascal(name.encode()) + b"\x00" + struct.pack("<2I", w, h) + pascal(mask)
    for name, page, left, right, top, bottom in sprites:
        out += pascal(name.encode()) + struct.pack("<5h", page, left, right, top, bottom)
        out += b"\x01\x00" + struct.pack("<2h", 0, 0)
    return out


STRAT = sheet([("stratpage_01.tga", 64, 64), ("stratpage_02.tga", 32, 32)], [
    ("BUILD_BUTTON_IMAGE", 0, 0, 20, 0, 20),
    ("FACTION_LOGO_SICILY", 1, 0, 15, 0, 15),
    ("FACTION_LOGO_GENOA", 1, 16, 31, 0, 15),
])
SHARED = sheet([("sharedpage_01.tga", 32, 32)], [
    ("NUMERAL_1", 0, 0, 4, 0, 4),
    ("SMALL_FACTION_LOGO_SICILY", 0, 8, 15, 8, 15),
])

# ---------------------------------------------------------------------------
print("=== 1. the sheet ===")
s = ss.parse(STRAT)
check("a sheet reads to its last byte: pages and sprites",
      s.pages == ["stratpage_01.tga", "stratpage_02.tga"]
      and s.names() == ["BUILD_BUTTON_IMAGE", "FACTION_LOGO_SICILY", "FACTION_LOGO_GENOA"])
check("a name is found by exact case, a number by position",
      s.find("FACTION_LOGO_SICILY").left == 0 and s.find("faction_logo_sicily") is None
      and s.find("2").name == "FACTION_LOGO_GENOA" and s.find("3") is None)
out = ss.add_alias(STRAT, "FACTION_LOGO_NAPLES", "FACTION_LOGO_SICILY")
t = ss.parse(out)
check("an alias is appended: every other sprite keeps its position",
      t.names()[:3] == s.names() and t.names()[3] == "FACTION_LOGO_NAPLES")
check("and draws exactly what its original draws",
      t.find("FACTION_LOGO_NAPLES").raw == t.find("FACTION_LOGO_SICILY").raw)
check("every byte before it is the sheet's own but the count",
      out[:8] == STRAT[:8] and out[12:len(STRAT)] == STRAT[12:])
for name, like, why in (("FACTION_LOGO_GENOA", "FACTION_LOGO_SICILY", "already in"),
                        ("FACTION_LOGO_X", "FACTION_LOGO_NOBODY", "not in the sheet"),
                        ("BAD NAME", "FACTION_LOGO_SICILY", "not a sprite name")):
    try:
        ss.add_alias(STRAT, name, like)
        check(f"refused: {why}", False)
    except ss.SheetError as e:
        check(f"refused: {why} ({e})", why in str(e))
for raw, why in ((STRAT[:-3], "ends early"), (STRAT + b"\x00", "after the last"),
                 (b"\x05" + STRAT[1:], "version 5")):
    try:
        ss.parse(raw)
        check(f"a broken sheet is refused: {why}", False)
    except ss.SheetError as e:
        check(f"a broken sheet is refused: {why}", why in str(e))


# ---------------------------------------------------------------------------
def rec(slot, logo, small):
    return (f"faction\t\t\t{slot}\nculture\t\t\tsouthern_european\nreligion\t\t\tcatholic\n"
            f"primary_colour\t\t\tred 245, green 245, blue 245\n"
            f"secondary_colour\t\t\tred 130, green 20, blue 30\nstandard_index\t\t\t6\n"
            f"logo_index\t\t\t{logo}\nsmall_logo_index\t\t\t{small}\n\n")


def build(root: Path, sheets=True, roster=None) -> Path:
    data = root / "data"
    (data / "ui").mkdir(parents=True, exist_ok=True)
    kb.write_text(data / fac.REL, roster or (
        rec("sicily", "FACTION_LOGO_SICILY", "SMALL_FACTION_LOGO_SICILY")
        + rec("milan", "FACTION_LOGO_MILAN", "SMALL_FACTION_LOGO_MILAN")
        + rec("venice", "Faction_Logo_Sicily", "SMALL_FACTION_LOGO_SICILY")
        + rec("genoa", "7", "SMALL_FACTION_LOGO_SICILY")), fc.ENCODING)
    if sheets:
        (data / ss.STRATEGY).write_bytes(STRAT)
        (data / ss.SHARED).write_bytes(SHARED)
    return root


print("\n=== 2. the checks ===")
tmp = Path(_tmp.mkdtemp(prefix="ut_sprites_"))
root = build(tmp / "ShieldMod")
mod = Mod(root)
data = root / "data"
found = [f for f in fac.check_file(fac.parse_file(fac.path_for(mod)), mod)
         if f["kind"] == "logo-not-in-sheet"]
by = {}
for f in found:
    by.setdefault(f["name"], []).append(f["message"])
check(f"the roster reports the three bad factions and not sicily ({sorted(by)})",
      sorted(by) == ["genoa", "milan", "venice"])
check("milan: both of its names, each against its own sheet",
      len(by["milan"]) == 2 and any("ui/strategy.sd" in m for m in by["milan"])
      and any("ui/shared.sd" in m for m in by["milan"]))
check("venice: a name that differs only in case says which one the sheet has",
      "FACTION_LOGO_SICILY" in by["venice"][0] and "case" in by["venice"][0])
check("genoa: a number past the end is a position, and says how many there are",
      "position" in by["genoa"][0] and "3 sprites" in by["genoa"][0])
check("each finding carries the line it is on",
      all(f["line"] > 1 for f in found))

a = fa.audit(mod)
rows = {f["slot"]: {r["id"]: r for r in f["rows"]} for f in a["factions"]}
check("the audit's shield row: ok for sicily, a gap for the other three",
      rows["sicily"]["logos"]["state"] == "ok"
      and all(rows[s]["logos"]["state"] == "missing" and rows[s]["logos"]["level"] == "gap"
              for s in ("milan", "venice", "genoa")))
d = fac.detail(mod, "milan")
check("the editor offers the sheet's shields, and the roster's finding",
      d["vocab"]["logo_sprites"] == ["FACTION_LOGO_GENOA", "FACTION_LOGO_SICILY"]
      and d["vocab"]["small_logo_sprites"] == ["SMALL_FACTION_LOGO_SICILY"]
      and sum(f["kind"] == "logo-not-in-sheet" for f in d["findings"]) == 2)

from unittransfer import health                                     # noqa: E402
rep = health.run(mod)
hits = [f for f in rep["findings"] if "logo" in f["code"]] if isinstance(rep, dict) else []
check(f"Health reports each once, from the Factions source ({len(hits)})",
      len(hits) == 4 and all(f["source"] == "factions" for f in hits))

before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
p = fa.repair_plan(mod, {"faction": "milan", "template": "sicily", "checks": ["logos"]})
check("the repair plans both sheets", not p.errors
      and sorted(e.rel for e in p.written()) == [ss.SHARED, ss.STRATEGY])
res = fc.apply(p)
tid = res["id"]
st, sh = ss.read(data, ss.STRATEGY), ss.read(data, ss.SHARED)
check("milan's names are in the sheets now, drawn as sicily's",
      st.find("FACTION_LOGO_MILAN").raw == st.find("FACTION_LOGO_SICILY").raw
      and sh.find("SMALL_FACTION_LOGO_MILAN").raw == sh.find("SMALL_FACTION_LOGO_SICILY").raw)
check("the roster is untouched", (data / fac.REL).read_bytes() == before["data/" + fac.REL])
rows = {f["slot"]: {r["id"]: r for r in f["rows"]} for f in fa.audit(Mod(root))["factions"]}
check("and the audit calls milan's shield ok", rows["milan"]["logos"]["state"] == "ok")
g = fa.repair_plan(Mod(root), {"faction": "genoa", "template": "sicily", "checks": ["logos"]})
check("a position is not repaired, and says to choose a name",
      any("position" in w for w in g.warnings) and not g.written())
transfer.undo(tid)
after = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
check("undo put both sheets back byte for byte", after == before)
config.update_log(tid, note="test_spritesheet - synthetic mod, discarded")


# ---------------------------------------------------------------------------
print("\n=== 3. the clone ===")
root = build(tmp / "CloneMod", roster=rec("sicily", "FACTION_LOGO_SICILY",
                                          "SMALL_FACTION_LOGO_SICILY"))
data = root / "data"
before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
p = fc.plan(Mod(root), {"source": "sicily", "new": "naples", "art": False})
check("the clone plans a shield of its own in each sheet",
      not p.errors and sorted(e.rel for e in p.written() if e.data) == [ss.SHARED, ss.STRATEGY])
res = fc.apply(p)
st, sh = ss.read(data, ss.STRATEGY), ss.read(data, ss.SHARED)
naples = fac.parse_file(fac.path_for(Mod(root))).get("naples")
check("FACTION_LOGO_NAPLES and SMALL_FACTION_LOGO_NAPLES, drawn as sicily's",
      st.find("FACTION_LOGO_NAPLES").raw == st.find("FACTION_LOGO_SICILY").raw
      and sh.find("SMALL_FACTION_LOGO_NAPLES").raw == sh.find("SMALL_FACTION_LOGO_SICILY").raw)
check("and the new record points at them",
      naples.get("logo_index") == "FACTION_LOGO_NAPLES"
      and naples.get("small_logo_index") == "SMALL_FACTION_LOGO_NAPLES")
roster = kb.read_text(data / fac.REL, fc.ENCODING)
check("sicily's own record still names sicily's shield",
      fac.parse_file(fac.path_for(Mod(root))).get("sicily").get("logo_index") == "FACTION_LOGO_SICILY"
      and roster.count("FACTION_LOGO_SICILY") == 2)
check("the new faction's findings are clean",
      not [f for f in fac.check_file(fac.parse_file(fac.path_for(Mod(root))), Mod(root))
           if f["kind"] == "logo-not-in-sheet"])
transfer.undo(res["id"])
after = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
check("undo put the clone's sheets back byte for byte", after == before)
config.update_log(res["id"], note="test_spritesheet - synthetic mod, discarded")

bp = fc.plan_many(Mod(root), {"source": "sicily", "art": False,
                              "rows": [{"new": "naples"}, {"new": "pisa"}]})
check("a batch of two plans", not bp.errors)
res = fc.apply_many(bp)
st = ss.read(data, ss.STRATEGY)
check("both rows' shields land in one sheet, each drawn as sicily's",
      st.names()[-2:] == ["FACTION_LOGO_NAPLES", "FACTION_LOGO_PISA"]
      and st.find("FACTION_LOGO_PISA").raw == st.find("FACTION_LOGO_SICILY").raw)
transfer.undo(res["id"])
config.update_log(res["id"], note="test_spritesheet - synthetic mod, discarded")

p = fc.plan(Mod(root), {"source": "sicily", "new": "genoa", "art": False})
check("a name already in the sheet is used, not added again, and said so",
      [e.rel for e in p.written() if e.data] == [ss.SHARED]
      and any("FACTION_LOGO_GENOA" in n for n in p.notes))

root = build(tmp / "PackedMod", sheets=False,
             roster=rec("sicily", "FACTION_LOGO_SICILY", "SMALL_FACTION_LOGO_SICILY"))
p = fc.plan(Mod(root), {"source": "sicily", "new": "naples", "art": False})
roster = next(e.text for e in p.written() if e.rel == fac.REL)
check("sheets that are packed: the donor's shield, as the clone always gave",
      not [e for e in p.written() if e.data]
      and fac.parse_text(roster).get("naples").get("logo_index") == "FACTION_LOGO_SICILY")
rows = {f["slot"]: {r["id"]: r for r in f["rows"]} for f in fa.audit(Mod(root))["factions"]}
check("and the audit's row says nothing was checked",
      rows["sicily"]["logos"]["state"] == "unknown")
shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
print("\n=== 4. the installed mods, read-only ===")
from tests import _realmod                                          # noqa: E402

mods = _realmod.installed()
if not mods:
    print("  [skip] no installed mod")
for path in mods:
    real = Mod(path)
    for rel in (ss.STRATEGY, ss.SHARED, "ui/battle.sd"):
        f = real.data / rel
        if not f.is_file():
            continue
        try:
            n = len(ss.parse(f.read_bytes()).sprites)
            check(f"{path.name}: {rel} reads to its last byte ({n} sprites)", n > 0)
        except ss.SheetError as e:
            check(f"{path.name}: {rel} reads ({e})", False)
    bad = [f for f in fac.check_file(fac.parse_file(fac.path_for(real)), real)
           if f["kind"] == "logo-not-in-sheet"]
    check(f"{path.name}: every faction's shield is in its sheet"
          + (f" (not {[f['name'] for f in bad][:3]})" if bad else ""), not bad)

print(f"\n{sum(ok)}/{len(ok)} passed")
sys.exit(0 if all(ok) else 1)
