"""Phase 59: descr_settlement_mechanics.xml.

    python -m tests.test_settlemech

1. Both installed mods: 42 live factors in three families, the six city and
   five castle levels, no findings - and DaC's commented-out factor is not read.
2. Each rule on a fixture: a value that is not a number, pip_min over pip_max,
   min over max, an upgrade the capped population never reaches, and (as a
   note) an upgrade that is not the next level's base.
3. A save: a value changed, a modifier added on its own line with the file's
   indent and CRLF, one taken out, a bad value and the pip modifier's removal
   refused - and every byte not asked about kept. Then written and undone on a
   temp copy of ROCSS's file.
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from unittransfer import settlemech as sm  # noqa: E402
from unittransfer import transfer  # noqa: E402
from unittransfer import config  # noqa: E402

# Every save and undo here goes to a config of its own, never the real undo log
# and backups: a suite run beside others would race them on transfers.json. It
# starts from a copy of the real settings, so the game root and the M2EX marks
# read the same, and nothing is written back to them.
cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
if config.SETTINGS_PATH.is_file():
    shutil.copy2(config.SETTINGS_PATH, cfg / "settings.json")
config.CONFIG_DIR = cfg; config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"; config.LOG_PATH = cfg / "transfers.json"

MODS = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition/mods")
ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return bool(cond)


class FakeMod:
    def __init__(self, root: Path):
        self.root, self.data, self.name = root, root / "data", root.name


# ---- 1) the installed mods ----------------------------------------------------------
print("\n1) the installed mods")
for name in ("Divide_and_Conquer_EUR", "ROCSS"):
    if not (MODS / name / "data" / sm.REL).is_file():
        continue
    ov = sm.overview(FakeMod(MODS / name))
    fam = {f["id"]: len(f["factors"]) for f in ov["families"]}
    lv = [len(l["levels"]) for l in ov["levels"]]
    check(f"{name}: {sum(fam.values())} factors {fam}, levels {lv}, {len(ov['findings'])} findings",
          fam == {"SPF": 11, "SOF": 20, "SIF": 11} and lv == [6, 5] and not ov["findings"])
dac = MODS / "Divide_and_Conquer_EUR" / "data" / sm.REL
if dac.is_file():
    raw = dac.read_bytes().decode("latin-1")
    check("DaC's commented-out factor is in the text and not in what is read",
          raw.count("<factor name") == 43 and len(sm.parse_text(raw).factors) == 42)

# ---- 2) the rules -------------------------------------------------------------------
print("\n2) each rule")
FIX = """<?xml version="1.0"?>\r
<root>\r
\t<factor_modifiers>\r
\t\t<factor name="SIF_MINING">\r
\t\t\t<pip_modifier value="1.25"/>\r
\t\t</factor>\r
\t\t<factor name="SOF_SQUALOUR">\r
\t\t\t<pip_modifier value="0.4"/>\r
\t\t\t<pip_min value="0"/>\r
\t\t\t<pip_max value="16"/>\r
\t\t</factor>\r
\t\t<!-- <factor name="SOF_OLD"><pip_modifier value="x"/></factor> -->\r
\t</factor_modifiers>\r
\t<population_levels>\r
\t\t<level name="village" base="500" upgrade="1500" min="500" max="2000"/>\r
\t\t<level name="town" base="1500" min="500" max="6000"/>\r
\t</population_levels>\r
</root>\r
"""
clean = sm.parse_text(FIX)
check("a comment's factor is not read, and the fixture has no findings",
      [f.name for f in clean.factors] == ["SIF_MINING", "SOF_SQUALOUR"] and not sm.check_file(clean))
codes = lambda t: sorted((f["code"], f["severity"]) for f in sm.check_file(sm.parse_text(t)))
check("a value that is not a number is fatal",
      ("value", "fatal") in codes(FIX.replace('"1.25"', '"lots"')))
check("pip_min above pip_max is a warning",
      ("pip_range", "warn") in codes(FIX.replace('pip_min value="0"', 'pip_min value="20"')))
check("min above max is a warning", ("min_max", "warn") in codes(FIX.replace('min="500" max="2000"', 'min="2500" max="2000"')))
over = codes(FIX.replace('upgrade="1500"', 'upgrade="2500"'))
check("an upgrade above max is a warning - the level is never outgrown",
      ("upgrade_max", "warn") in over)
check("and an upgrade that is not the next level's base is a note, not a fault",
      ("chain", "note") in over and ("chain", "note") in codes(FIX.replace('upgrade="1500"', 'upgrade="1400"')))

# ---- 3) the save ----------------------------------------------------------------------
print("\n3) a save")
root = Path(_tmp.mkdtemp(prefix="ut_settlemech_")) / "FixMod"
(root / "data").mkdir(parents=True)
(root / "data" / sm.REL).write_bytes(FIX.encode("latin-1"))
mod = FakeMod(root)
p = sm.plan(mod, {"values": {"factor/SIF_MINING/pip_modifier": "1.5",
                             "factor/SIF_MINING/castle_modifier": "0.5",
                             "factor/SOF_SQUALOUR/pip_min": "",
                             "level/town/max": "7000"}})
check(f"four changes plan clean ({len(p.changes)})", not p.errors and len(p.changes) == 4)
t = p.text
check("the value is changed where it was",
      '\t\t\t<pip_modifier value="1.5"/>\r\n' in t)
check("an added modifier is its own line, with the file's indent and CRLF, after the last one",
      '<pip_modifier value="1.5"/>\r\n\t\t\t<castle_modifier value="0.5"/>\r\n\t\t</factor>' in t)
check("a modifier cleared is taken out, line and all", "pip_min" not in t)
check("the level's max is changed", 'max="7000"' in t)
check("every other byte is kept - the comment, the other lines, the endings",
      t.replace('value="1.5"', 'value="1.25"').replace('\r\n\t\t\t<castle_modifier value="0.5"/>', "")
       .replace('max="7000"', 'max="6000"')
      == FIX.replace('\t\t\t<pip_min value="0"/>\r\n', ""))
for vals, why in (({"factor/SIF_MINING/pip_modifier": "a lot"}, "a value that is not a number"),
                  ({"factor/SIF_MINING/pip_modifier": ""}, "taking out the pip modifier"),
                  ({"level/town/base": "1.5"}, "a fraction of a person"),
                  ({"factor/SIF_NOPE/pip_modifier": "1"}, "a factor the file does not have")):
    check(f"{why} is refused", sm.plan(mod, {"values": vals}).errors)
res = sm.apply(p)
check("written", (root / "data" / sm.REL).read_bytes().decode("latin-1") == t)
transfer.undo(res["id"])
check("and one undo puts the file back byte for byte",
      (root / "data" / sm.REL).read_bytes() == FIX.encode("latin-1"))

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
