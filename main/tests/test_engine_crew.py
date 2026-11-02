"""96f: a crew's siege engine, for the unit preview to draw beside them.

Run:  python -m tests.test_engine_crew

A made-up mod with three engines in descr_engines.txt and one in
descr_mounted_engines.txt:

* ``ut_catapult`` has a ``dying`` group first and a ``normal`` group of two
  LODs, whose lod0 has three textures baked in (the sheet, its normal map and
  a shared dirt overlay), and a second block for another culture;
* ``ut_ram`` has only a ``dying`` group, with its mesh;
* ``ut_tower`` names a mesh the mod does not ship;
* ``ut_elephant_gun`` is a mounted engine.

What has to hold:

* the catapult's ``normal`` group's first mesh is the one drawn, not ``dying``'s,
  and both blocks are counted;
* its baked textures are listed, each found, and the sheet picked to paint it
  with is neither the normal map nor the overlay;
* with no ``normal`` group, the first group that has a mesh is used;
* a mesh the mod lacks is said missing, with no textures;
* a mounted engine comes back ``mounted``, and an unknown name with nothing.
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests import _tmp  # noqa: E402
from unittransfer import engines                                    # noqa: E402
from unittransfer.mod import Mod                                    # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


def block(name, culture, groups):
    out = f"type                {name}\nculture             {culture}\nclass               catapult\n\n"
    for g, meshes in groups:
        out += f"engine_model_group  {g}\nengine_skeleton     {name}_skel\n"
        out += "".join(f"engine_mesh         {m}, {40 * (i + 1)}.0\n" for i, m in enumerate(meshes))
    return out + "\n"


def mesh_with(textures):
    blob = b"\x00" * 16
    for t in textures:
        s = t.encode("latin-1")
        blob += struct.pack("<I", len(s)) + s + b"\x00" * 8
    return blob


tmp = Path(_tmp.mkdtemp(prefix="ut_enginecrew_"))
data = tmp / "M" / "data"
(data / "siege_engines" / "textures").mkdir(parents=True)
(data / "OverlayTextures").mkdir(parents=True)
(data / "descr_engines.txt").write_text(
    block("ut_catapult", "northern_european", [("dying", ["siege_engines/ut_catapult_dying.mesh"]),
                                               ("normal", ["siege_engines/ut_catapult_lod0.mesh",
                                                           "siege_engines/ut_catapult_lod1.mesh"])])
    + block("ut_catapult", "eastern_european", [("normal", ["siege_engines/ut_catapult_lod0.mesh"])])
    + block("ut_ram", "all", [("dying", ["siege_engines/ut_ram.mesh"])])
    + block("ut_tower", "all", [("normal", ["siege_engines/ut_tower_nowhere.mesh"])]),
    encoding="latin-1")
(data / "descr_mounted_engines.txt").write_text(
    "type                ut_elephant_gun\nclass               rocket_launcher\n", encoding="latin-1")
(data / "siege_engines" / "ut_catapult_lod0.mesh").write_bytes(mesh_with(
    ["data/siege_engines/textures/ut_catapult_norm.texture", "data\\OverlayTextures\\dirt_02.texture",
     "data/siege_engines/textures/ut_catapult.texture"]))
(data / "siege_engines" / "ut_catapult_dying.mesh").write_bytes(mesh_with([]))
(data / "siege_engines" / "ut_ram.mesh").write_bytes(mesh_with(["data/siege_engines/textures/ut_ram.texture"]))
for t in ("ut_catapult_norm", "ut_catapult", "ut_ram"):
    (data / "siege_engines" / "textures" / f"{t}.texture").write_bytes(b"x")
(data / "OverlayTextures" / "dirt_02.texture").write_bytes(b"x")
mod = Mod(tmp / "M")

c = engines.crew_scene(mod, "ut_catapult")
check("the catapult's normal group's first mesh is drawn",
      c["group"] == "normal" and c["mesh"] == "siege_engines/ut_catapult_lod0.mesh" and c["mesh_exists"])
check("  both of its blocks are counted, the first one's culture given",
      c["blocks"] == 2 and c["culture"] == "northern_european")
check("  its three baked textures are listed, each found",
      [t["rel"] for t in c["textures"]] == ["siege_engines/textures/ut_catapult_norm.texture",
                                            "OverlayTextures/dirt_02.texture",
                                            "siege_engines/textures/ut_catapult.texture"]
      and all(t["exists"] for t in c["textures"]))
check("  painted with the sheet, not the normal map or the overlay",
      c["main"] == "siege_engines/textures/ut_catapult.texture")
check("  and it is not a mounted engine", not c["mounted"])

r = engines.crew_scene(mod, "ut_ram")
check("with no normal group, the first group with a mesh is used",
      r["group"] == "dying" and r["mesh"] == "siege_engines/ut_ram.mesh"
      and r["main"] == "siege_engines/textures/ut_ram.texture")

t = engines.crew_scene(mod, "UT_TOWER")
check("a mesh the mod lacks is said missing (the name in any case)",
      t["mesh"] == "siege_engines/ut_tower_nowhere.mesh" and not t["mesh_exists"]
      and t["textures"] == [] and t["main"] == "")

m = engines.crew_scene(mod, "ut_elephant_gun")
check("a mounted engine comes back mounted, with no mesh", m["mounted"] and not m["mesh"])
n = engines.crew_scene(mod, "ut_nothing")
check("an unknown engine comes back with nothing", not n["mounted"] and not n["mesh"] and n["blocks"] == 0)
check("an empty name too", engines.crew_scene(mod, "")["blocks"] == 0)

print(f"\n{sum(ok)}/{len(ok)} passed")
sys.exit(0 if all(ok) else 1)
