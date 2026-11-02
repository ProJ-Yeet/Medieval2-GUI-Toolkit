"""Which strat model stands for each thing on the campaign map - Phase 97d.

`unittransfer/stratscene.py` joins three files into the table the 3D map
draws from: descr_character.txt (a character type's strat models per
faction), descr_model_strat.txt (each as a mesh, a scale and a texture per
faction) and descr_cultures.txt (a model per settlement level, fort and
watchtower). It is checked on a mod written here, where every answer is
known, and then on DaC when it is installed. The browser half is checked by
what it calls, since what it draws needs a GPU.

    python -m tests.test_stratscene
"""
import re
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests import _realmod, _tmp, _webtext  # noqa: E402
from unittransfer import stratscene  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


root = Path(_tmp.mkdtemp(prefix="ut_stratscene_"))
data = root / "mods" / "Scene" / "data"
(data / "models_strat" / "textures").mkdir(parents=True)
(data / "models_strat" / "residences").mkdir(parents=True)
(data / "descr_character.txt").write_text("""\
; a comment line
type            named character
faction         england, france
dictionary      x
strat_model     eng_general  ; 0 (Default)
strat_model     eng_heir     ; 1 (Heir)
strat_model     eng_king     ; 2 (Leader)

faction         slave
strat_model     rebel_general

type            spy
faction         england
strat_model     eng_spy
strat_model     no_such_block
""", encoding="utf-8")
(data / "descr_model_strat.txt").write_text("""\
type            eng_general
skeleton        strat_named_with_army
scale           0.7
texture         england, models_strat/textures/eng_general.tga
texture         france, models_strat/textures/FRA_general.tga
texture         scotland, models_strat/textures/not_shipped.tga
model_flexi_m   models_strat/eng_general.cas, max
shadow_model_flexi models_strat/shadow.cas, max

type            eng_heir
model_flexi_m   models_strat/missing.cas, max

type            eng_spy
scale           1.1
model_flexi_m   models_strat/eng_spy.cas, max
""", encoding="utf-8")
for f in ("eng_general.cas", "shadow.cas", "eng_spy.cas"):
    (data / "models_strat" / f).write_bytes(b"x")
# the packer's shape: a .tga.dds beside an empty stub, and a bare .tga in caps
(data / "models_strat" / "textures" / "eng_general.tga.dds").write_bytes(b"x")
(data / "models_strat" / "textures" / "eng_general.tga").write_bytes(b"")
(data / "models_strat" / "textures" / "fra_general.TGA").write_bytes(b"x")
(data / "models_strat" / "residences" / "e_village.cas").write_bytes(b"x")
(data / "models_strat" / "residences" / "e_fort.cas").write_bytes(b"x")
(data / "descr_cultures.txt").write_text("""\
culture             northern_european
{
village
{
    normal          data/models_strat/residences/e_village.cas, settlement_level_1
    card            data/ui/x.tga
}
town
{
    normal          data/models_strat/residences/not_there.cas, settlement_level_2
}
}
fort                data\\models_strat\\residences\\e_fort.cas, fort_plan
watchtower          data/models_strat/residences/none.cas
""", encoding="utf-8")

print("\n== 1) descr_character.txt, read the way the game reads it ==")
chars = stratscene.characters(Mod(data.parent))
nc = chars.get("named character", {})
check("a faction line names every faction it lists",
      nc.get("england") == nc.get("france") == ["eng_general", "eng_heir", "eng_king"])
check("  in file order: the default, the heir's, the leader's",
      nc.get("england", [""])[0] == "eng_general" and nc["england"][2] == "eng_king")
check("a second faction line starts a new list", nc.get("slave") == ["rebel_general"])
check("a new type starts again", chars.get("spy", {}).get("england") == ["eng_spy", "no_such_block"])
check("the comment after a name is not part of it", "eng_general" in nc.get("england", []))

print("\n== 2) the table ==")
t0 = time.perf_counter()
d = stratscene.scene(Mod(data.parent))
ms = (time.perf_counter() - t0) * 1000
g = d["models"].get("eng_general", {})
check("a model's mesh is the first one on disk, never its shadow",
      g.get("mesh") == "models_strat/eng_general.cas")
check("  and its scale is read", g.get("scale") == 0.7)
check("a faction's texture is found as the packer shipped it, .tga.dds first",
      g.get("textures", {}).get("england") == "models_strat/textures/eng_general.tga.dds")
check("  case ignored, as the game ignores it",
      g.get("textures", {}).get("france") == "models_strat/textures/fra_general.TGA")
check("  and one the mod does not ship is left out",
      "scotland" not in g.get("textures", {}))
check("a block with no scale is 1", d["models"].get("eng_spy", {}).get("scale") == 1.1
      and stratscene._scale(type("E", (), {"raw": "type x\n"})()) == 1.0)
check("a block whose mesh is missing is left out", "eng_heir" not in d["models"])
check("  and so is a name with no block at all", "no_such_block" not in d["models"])
cul = d["cultures"].get("northern_european", {})
check("a culture's level model, with data/ taken off the front",
      cul.get("village") == "models_strat/residences/e_village.cas")
check("  a level whose model is not on disk is left out", "town" not in cul)
check("the fort's line, backslashes and all",
      cul.get("fort") == "models_strat/residences/e_fort.cas")
check("  and a watchtower that is not on disk is not offered", "watchtower" not in cul)
check(f"built in well under a second ({ms:.0f} ms)", ms < 1000)

print("\n== 3) on DaC, when it is installed ==")
dac = next((r for r in _realmod.installed() if r.name == "Divide_and_Conquer_EUR"), None)
if dac is None:
    print("  -- DaC is not installed")
else:
    t0 = time.perf_counter()
    D = stratscene.scene(Mod(dac))
    ms = (time.perf_counter() - t0) * 1000
    gg = D["models"].get("gondor_general", {})
    check(f"Gondor's general is its own mesh at 0.7 ({gg.get('mesh')})",
          gg.get("mesh") == "models_strat/gondor_general1.cas" and gg.get("scale") == 0.7)
    check("  dressed in Gondor's texture, as the .tga.dds it ships",
          gg.get("textures", {}).get("sicily", "").endswith("gondor_general1.tga.dds"))
    # Four of DaC's cultures ship no huge city on disk; the 3D view steps to
    # the nearest level they do have (cm3LevelModel), so what matters is that
    # every culture a faction has can draw some city at all
    used = set(D["faction_culture"].values())
    check(f"every culture a faction has can draw a city ({len(used)} cultures)",
          all(any(D["cultures"].get(c, {}).get(l) for l in
                  ("village", "town", "large_town", "city", "large_city", "huge_city"))
              for c in used))
    check(f"and the whole table is quick enough to ask for on opening the view ({ms:.0f} ms)",
          ms < 5000)

print("\n== 4) the browser half ==")
js = _webtext.read(ROOT / "web" / "js" / "map3d.js")
check("the models come from the markers layer's own index",
      "for(const g of k.groups)" in js and "cmkShown(g)" in js)
check("  and obey the Icons switch", re.search(r"function cm3Things\(\)\{.*?cmapIconsOn\(\)", js, re.S) is not None)
check("one load per mesh, however many tiles name it",
      "if(me.models[rel]) return;" in js)
check("drawn through the Strat models tab's own routes",
      "/api/map/model/geometry?" in js and "/api/map/model?" in js)
check("a figure is stood by the viewer's own skinning, not a copy of it",
      "v3aSkin(geo, v3aPose(anim, 0)" in js and "function v3aSkin" not in js)
check("a model too small to see is skipped", "CM3_THING_MIN_PX" in js)
check("a castle's level is the castle's model, not the city's",
      "CM3_CASTLE_LEVEL" in js and "'moot_and_bailey'" in js)
check("a level a culture ships no model for takes the nearest it has",
      "function cm3LevelModel" in js and "place(cm3LevelModel(rows, want, castle)" in js)
srv = _webtext.read(ROOT / "unittransfer" / "server.py")
check("the route is in the server", '"/api/map/strat_scene"' in srv and "stratscene.scene(" in srv)

shutil.rmtree(root, ignore_errors=True)
print(f"\n{sum(ok)}/{len(ok)} checks - "
      f"{'ALL PASSED' if all(ok) else f'{len(ok) - sum(ok)} FAILED'}")
sys.exit(0 if all(ok) else 1)
