"""96e1: scripts - the ready-made add-ons and the no-code Module builder.

What each part is here to catch:

  * **the builder's recipe is read back and written as a script**: an example
    reads in plain words, has nothing wrong with it, and its script names the
    engine event it hangs on; a recipe missing what it needs says so.
  * **a script add-on goes where M2EX runs it**: the game's script/modules when
    the game's script/main.nut loads every module; Undo takes it away again,
    outside the mod's data/ as it is.
  * **Upkeep x 2** doubles every unit's upkeep and Take it out puts back exactly
    the old numbers; **One Recruitment Grid** sets the campaign constant and
    takes it back.
  * **a module of one's own** is saved into the toolkit's own folder and shows
    as an add-on.

    python -m tests.test_scripts
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp
from unittransfer import config, scripts, transfer
from unittransfer.mod import Mod

cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
if config.SETTINGS_PATH.is_file():
    shutil.copy2(config.SETTINGS_PATH, cfg / "settings.json")
config.CONFIG_DIR = cfg; config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"; config.LOG_PATH = cfg / "transfers.json"

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


game = Path(_tmp.mkdtemp(prefix="ut_sx_")) / "Medieval II Total War"
root = game / "mods" / "T"
data = root / "data"
data.mkdir(parents=True)
(game / "medieval2.exe").write_bytes(b"MZ")
(game / "script" / "modules").mkdir(parents=True)
(game / "script" / "main.nut").write_text('scripting.listModules("modules")\n', encoding="utf-8")
EDU = ("type             Peasants\r\ndictionary       Peasants\r\ncategory         infantry\r\nclass            light\r\n"
       "stat_cost        1, 120, 75, 20, 20, 120, 4, 100\r\n\r\n"
       "type             Spearmen\r\ndictionary       Spearmen\r\ncategory         infantry\r\nclass            spearmen\r\n"
       "stat_cost        1, 300, 150, 40, 40, 300, 4, 100\r\n")
(data / "export_descr_unit.txt").write_bytes(EDU.encode("latin-1"))
(data / "descr_sm_factions.txt").write_text("faction\tengland\nculture\tnorthern_european\n", encoding="latin-1")
(data / "descr_campaign_db.xml").write_text(
    "<campaign_db>\n   <recruitment>\n      <recruitment_sort_simple bool=\"false\"/>\n   </recruitment>\n</campaign_db>\n",
    encoding="latin-1")
mod = Mod(root)

print("the builder")
ov = scripts.overview(mod)
voc = ov["vocab"]
check("the vocabulary is there", voc["events"] and voc["conditions"] and voc["actions"] and voc["examples"])
check("the add-ons for Medieval II are listed, the file ones among them",
      {"upkeep_x2", "one_recruit_grid"} <= {a["key"] for a in ov["addons"]})
r = scripts.example(mod, voc["examples"][0]["title"])
pv = scripts.preview(mod, r)
check("an example reads back in plain words", pv["words"].startswith("When "))
check("and has nothing wrong with it", pv["problems"] == [])
check("its script hangs on the engine's event", "FactionTurnStart" in pv["script"])
bad = scripts.new_recipe("Empty")
check("a recipe with nothing to do says so", scripts.preview(mod, bad)["problems"])

print("\na script add-on")
p = scripts.plan_addon(mod, "avoid_growth", "install", {})
dest = game / "script" / "modules" / "avoid_growth.nut"
check("it goes where M2EX runs every module", str(dest.resolve()).lower() in {k.lower() for k in p.writes})
rec = p.run("addon", "avoid_growth", "test")
check("written", dest.is_file())
transfer.undo(rec["id"])
check("and Undo takes it away, outside data/ as it is", not dest.exists())

print("\nthe file add-ons")
p = scripts.plan_addon(mod, "upkeep_x2", "install", {"FACTOR": "2.0"})
rec = p.run("addon", "upkeep_x2", "test")
text = (data / "export_descr_unit.txt").read_bytes().decode("latin-1")
check("Upkeep x 2 doubles every upkeep", "1, 120, 150, 20" in text and "1, 300, 300, 40" in text)
check("and keeps its line endings", "\r\n" in text and text.count("\r\n") == EDU.count("\r\n"))
p = scripts.plan_addon(Mod(root), "upkeep_x2", "remove", {})
p.run("addon", "upkeep_x2", "test")
check("Take it out puts back exactly the old numbers",
      (data / "export_descr_unit.txt").read_bytes() == EDU.encode("latin-1"))
p = scripts.plan_addon(Mod(root), "one_recruit_grid", "install", {})
p.run("addon", "one_recruit_grid", "test")
check("One Recruitment Grid sets the constant",
      'recruitment_sort_simple bool="true"' in (data / "descr_campaign_db.xml").read_text(encoding="latin-1"))
p = scripts.plan_addon(Mod(root), "one_recruit_grid", "remove", {})
p.run("addon", "one_recruit_grid", "test")
check("and takes it back", 'recruitment_sort_simple bool="false"'
      in (data / "descr_campaign_db.xml").read_text(encoding="latin-1"))

print("\na module of one's own")
saved = scripts.save_module(r)
check("saved into the toolkit's own folder", (cfg / "script_modules").is_dir()
      and any((cfg / "script_modules").glob("*.nut")))
check("and listed as an add-on and as one of yours",
      any(a["key"] == saved["key"] for a in scripts.overview(Mod(root))["addons"])
      and scripts.overview(Mod(root))["mine"])

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
