"""A Blender export's models into a mod - folderimport.py and the unit step.

Built on a mod and an export this file writes from scratch, nothing installed:

* ``orc`` has an ``orc_bmdb.txt`` naming its files under
  ``unit_models/_units/reaper/``; ``orc_upg`` carries a copy of the same
  ``_bmdb.txt`` (an upgrade exported beside its unit), so the name is the
  folder's twice; ``clash`` is named ``shared``, which the mod has; ``plain``
  has no ``_bmdb.txt`` and is cloned from an entry of the mod;
* the folder also holds two cards, one named for the model and one not, and
  the models' own sheets, which are no cards.

Covers the scan (states, clashes, free names), the plan (a clone is needed, a
replace needs a ``_bmdb.txt``), the write (each file where the entry names it,
the clone's files in their own folder, the mod's entry replaced), a second scan
seeing the files as already in the mod, Undo, the card pictures, and a unit
made to wear an imported entry with a card copied in under its own name.

    python -m tests.test_folderimport
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp
from unittransfer import armunit, config, folderimport, meshfolder, modeldb
from unittransfer.mod import Mod
from unittransfer.transfer import undo

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


def _s(v: str) -> str:
    return f"{len(v)} {v}"


def entry_text(name, mesh, tex, factions=("england",)):
    """One entry: a LOD, main and attachment records per faction, one animation set."""
    norm = tex[:-8] + "_norm.texture"
    att = tex[:-8] + "_att.texture"
    lines = [_s(name), "1 1", f"{_s(mesh)} 6400", str(len(factions))]
    for f in factions:
        lines += [_s(f), _s(tex), _s(norm), _s("unit_sprites/x_sprite.spr")]
    lines.append(str(len(factions)))
    for f in factions:
        lines += [_s(f), _s(att), f"{_s(att[:-8] + '_norm.texture')} 0"]
    lines += ["1", _s("none"), f"{_s('MTW2_Spear')} {_s('MTW2_Spear_Secondary')}",
              "1", _s("MTW2_Spear_Primary"), "0", "-1", "0 0 0 0 0 0"]
    return "\n".join(lines) + "\n"


EDU = "\n".join([
    "type\t\talpha unit",
    "dictionary\talpha",
    "category\tinfantry",
    "class\t\tspearmen",
    "soldier\t\tshared, 60, 0, 1.2",
    "ownership\tengland",
    "",
]) + "\n"
ROSTER = "faction\t\tengland\nculture\t\tnorthern_european\n\nfaction\t\tslave\nculture\t\tnorthern_european\n"
BLANK = "5 blank " + " ".join(["0"] * 39) + "\n"
SHARED = entry_text("shared", "unit_models/x/x_lod0.mesh", "unit_models/x/textures/x.texture")
MODELDB = (f"{len(modeldb.ARCHIVE_MAGIC)} {modeldb.ARCHIVE_MAGIC} 3 0 0 0 0 2 0 0\n"
           + BLANK + "\n" + SHARED)

cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"

root = Path(_tmp.mkdtemp(prefix="ut_fimod_"))
data = root / "data"
(data / "unit_models").mkdir(parents=True)
(data / "text").mkdir()
(data / "export_descr_unit.txt").write_text(EDU, encoding="latin-1")
(data / "descr_sm_factions.txt").write_text(ROSTER, encoding="latin-1")
(data / "text" / "export_units.txt").write_text(
    "{alpha}Alpha\n{alpha_descr}A\n{alpha_descr_short}A\n", encoding="utf-16")
db_path = data / "unit_models" / "battle_models.modeldb"
db_path.write_text(MODELDB, encoding=modeldb.ENCODING)
before_db = db_path.read_bytes()

top = Path(_tmp.mkdtemp(prefix="ut_fiexp_"))


def plant(rel, body=b"sheet"):
    p = top / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(body if isinstance(body, bytes) else body.encode())
    return p


REAPER = "unit_models/_units/reaper"
ORC = entry_text("orc", f"{REAPER}/orc.mesh", f"{REAPER}/textures/orcskin.texture")
for folder in ("orc", "orc_upg"):
    plant(f"{folder}/{folder}.mesh", f"mesh of {folder}")
    plant(f"{folder}/textures/orcskin.texture", "orc skin")
    plant(f"{folder}/textures/orcskin_norm.texture", "orc normal")
    plant(f"{folder}/textures/orcskin_att.texture", "orc att")
    plant(f"{folder}/textures/orcskin_att_norm.texture", "orc att normal")
# the upgrade's bmdb is the unit's, mesh and all, as IWTE writes it beside a copy
plant("orc/orc_bmdb.txt", ORC.replace("\n", "\r\n"))
plant("orc_upg/orc_upg_bmdb.txt", entry_text("orc", f"{REAPER}/orc_upg.mesh", f"{REAPER}/textures/orcskin.texture"))
plant("clash/clash.mesh", "mesh of clash")
plant("clash/textures/clashskin.texture", "clash skin")
plant("clash/clash_bmdb.txt", entry_text("shared", f"{REAPER}/clash.mesh", f"{REAPER}/textures/clashskin.texture"))
plant("plain/plain.mesh", "mesh of plain")
plant("plain/textures/plain_main.texture", "plain main")
plant("plain/textures/plain_main_norm.texture", "plain main normal")
plant("plain/textures/plain_att.texture", "plain att")
plant("plain/mtw2_spear.cas", "cas")
plant("units/mercs/#orc.tga", "card")
plant("units/mercs/#somebody_else.tga", "card")
plant("unit_info/england/orc_info.tga", "info")
plant("units/mercs/#empty.tga", b"")

# ---------------------------------------------------------------------------
print("\nThe scan")
mod = Mod(root)
sc = folderimport.scan(mod, str(top))
by = {m["id"]: m for m in sc["models"]}
check(f"four models found ({', '.join(sorted(by))})", len(by) == 4)
orc = by["orc/orc.mesh"]
check("orc goes in by its _bmdb.txt, every file new", orc["bmdb"] == "orc_bmdb.txt"
      and all(f["state"] in ("new", "missing") for f in orc["files"]))
check("its files are where the entry names them, found in its own folder",
      {f["rel"]: Path(f["src"]).parent.parent.name for f in orc["files"] if f["src"]}
      .get(f"{REAPER}/textures/orcskin.texture") == "orc")
check("the sprite the entry names is in neither, and said so",
      any(f["rel"].endswith("x_sprite.spr") and f["state"] == "missing" for f in orc["files"]))
upg = by["orc_upg/orc_upg.mesh"]
check("a name twice in the folder: the model whose mesh is named so keeps it",
      orc["dup"] and upg["dup"] and "suggest" not in orc)
check(f"and the other is offered its mesh's name ({upg.get('suggest')})", upg.get("suggest") == "orc_upg")
check(f"a name the mod has is a clash, offered a free name ({by['clash/clash.mesh'].get('suggest')})",
      by["clash/clash.mesh"]["clash"] and by["clash/clash.mesh"].get("suggest") == "clash")
plain = by["plain/plain.mesh"]
slots = {f["slot"]: Path(f["src"]).name for f in plain["files"]}
check(f"no _bmdb.txt: the mesh, main, normal and attachment sheets ({slots})",
      slots == {"mesh_src": "plain.mesh", "texture_src": "plain_main.texture",
                "normal_src": "plain_main_norm.texture", "attach_texture_src": "plain_att.texture"})
check("and the .cas beside it named", plain["cas"] == ["mtw2_spear"])

# ---------------------------------------------------------------------------
print("\nThe plan")
try:
    folderimport.plan_import(mod, {"path": str(top), "models": [{"id": "plain/plain.mesh"}]})
    refused = ""
except folderimport.FolderImportError as e:
    refused = str(e)
check("a model with no _bmdb.txt needs a clone", "pick an entry" in refused)
try:
    folderimport.plan_import(mod, {"path": str(top), "models": [
        {"id": "plain/plain.mesh", "action": "replace", "clone_from": "shared"}]})
    refused = ""
except folderimport.FolderImportError as e:
    refused = str(e)
check("and cannot replace an entry", "cannot replace" in refused)
shown = folderimport.payload(folderimport.plan_import(mod, {"path": str(top), "models": [
    {"id": "orc/orc.mesh"}, {"id": "orc_upg/orc_upg.mesh"}]}))
check("the folder's name twice, both as new, is refused", not shown["ok"])

REQ = {"path": str(top), "models": [
    {"id": "orc/orc.mesh"},
    {"id": "orc_upg/orc_upg.mesh", "action": "rename", "name": "orc_upg"},
    {"id": "clash/clash.mesh", "action": "replace"},
    {"id": "plain/plain.mesh", "clone_from": "shared"}]}
shown = folderimport.payload(folderimport.plan_import(mod, REQ))
check(f"the four plan ({'; '.join(shown['errors'])})", shown["ok"] and shown["names"] == ["orc", "orc_upg", "shared", "plain"])
check("the shared sheets are copied once", sum("orcskin.texture ->" in ln for ln in shown["lines"]) == 1)

# ---------------------------------------------------------------------------
print("\nThe write")
out = folderimport.apply_import(mod, REQ)
after = Mod(root)
ents = after.modeldb.by_name()
check("orc, orc_upg and plain are entries, shared is still one", {"orc", "orc_upg", "plain", "shared"} <= set(ents)
      and len(after.modeldb.entries) == 4)
check("orc_upg is named so, and its mesh is its own", ents["orc_upg"].lods[0][0] == f"{REAPER}/orc_upg.mesh"
      and (data / REAPER / "orc_upg.mesh").read_bytes() == b"mesh of orc_upg")
check("each file where the entry names it", all((data / REAPER / r).is_file() for r in (
    "orc.mesh", "textures/orcskin.texture", "textures/orcskin_norm.texture",
    "textures/orcskin_att.texture", "textures/orcskin_att_norm.texture")))
check("the mod's 'shared' is replaced by the folder's", ents["shared"].lods[0][0] == f"{REAPER}/clash.mesh")
pl = ents["plain"]
check("plain is the clone, its mesh and sheets in a folder of its own",
      pl.lods[0][0] == "unit_models/_units/plain/plain.mesh"
      and pl.main_textures[0].texture == "unit_models/_units/plain/textures/plain_main.texture"
      and pl.main_textures[0].normal == "unit_models/_units/plain/textures/plain_main_norm.texture"
      and pl.attach_textures[0].texture == "unit_models/_units/plain/textures/plain_att.texture"
      and pl.animations[0].primary_skeleton == "MTW2_Spear")
again = {m["id"]: m for m in folderimport.scan(after, str(top), fresh=True)["models"]}
check("read again, the files are in the mod already", all(
    f["state"] in ("same", "missing") for f in again["orc/orc.mesh"]["files"]))
check("and orc now clashes", again["orc/orc.mesh"]["clash"])

# ---------------------------------------------------------------------------
print("\nThe cards")
pics = folderimport.card_pictures(str(top), ["orc", "alpha unit"])
cards1 = [p for p in pics if p["kind"] == "card"]
check(f"the card named for the model first ({cards1[0]['rel']}, {cards1[0]['score']})",
      cards1[0]["rel"] == "units/mercs/#orc.tga" and cards1[0]["score"] == 1.0
      and cards1[1]["score"] < 1.0)
check("the info card is an info card", any(p["rel"] == "unit_info/england/orc_info.tga" and p["kind"] == "info"
                                            and p["score"] == 1.0 for p in pics))
check("the models' sheets are not cards", not any("/textures/" in p["rel"] for p in pics))
check("an empty file is not offered", not any(p["rel"].endswith("#empty.tga") for p in pics))
check("a picture of the folder is served, nothing outside it",
      folderimport.picture_path(str(top), "units/mercs/#orc.tga") is not None
      and folderimport.picture_path(str(top), "../" + root.name + "/data/export_descr_unit.txt") is None
      and folderimport.picture_path(str(root), "data/x.tga") is None)

print("\nA unit wears it")
card = str(top / "units/mercs/#orc.tga")
try:
    armunit.plan_install(after, {"choice": "add", "entry": "nothing_here", "unit": "alpha unit"})
    refused = False
except armunit.InstallError:
    refused = True
check("an entry the mod has not got is refused", refused)
got = armunit.apply_install(lambda n: Mod(root), "mod", {
    "choice": "add", "entry": "orc", "unit": "alpha unit", "card_src": card,
    "info_src": str(top / "unit_info/england/orc_info.tga")})
worn = Mod(root)
check("alpha unit's soldier is orc, its count kept", worn.edu.by_type()["alpha unit"].soldier_model == "orc"
      and "orc, 60" in worn.edu.by_type()["alpha unit"].raw)
check("the card is copied in under the unit's own name, its faction's and the merc folder",
      (data / "ui/units/england/#alpha.tga").read_bytes() == b"card"
      and (data / "ui/units/mercs/#alpha.tga").is_file())
check("and the info card", (data / "ui/unit_info/england/alpha_info.tga").read_bytes() == b"info")

# ---------------------------------------------------------------------------
print("\nUndo")
undo(got["records"][0]["id"])
undo(out["record"]["id"])
check("the modeldb is as it was, byte for byte", db_path.read_bytes() == before_db)
check("and the copied files are gone", not (data / REAPER / "orc.mesh").exists()
      and not (data / "unit_models/_units/plain/plain.mesh").exists())
check("and the unit wears its old model", Mod(root).edu.by_type()["alpha unit"].soldier_model == "shared")

meshfolder._OPEN.clear()
print(f"\n{sum(ok)}/{len(ok)} passed")
sys.exit(0 if all(ok) else 1)
