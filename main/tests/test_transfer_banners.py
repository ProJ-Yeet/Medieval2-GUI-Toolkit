"""A banner the destination does not have - Phase 92d.

A unit whose ``banner`` line names a banner missing from the destination's
``descr_banners_new.xml`` used to be copied as it was, for Health to find
afterwards. Now the transfer plans it: ``port`` brings the source's banner
across (65's reader), ``swap`` uses ``main_cavalry`` / ``main_infantry``.

    1  port_banner on text: the banner lands in the right list, its rows cut to
       the destination's factions, a row added for each owner that has none,
       and the destination's check has nothing to say about it afterwards
    2  swap_for: faction by category, holy to crusade, unit dropped
    3  a real plan: Third Age Reforged's Bomb Platforms carries
       `banner faction main_none`, which DaC does not declare (and nor does
       Reforged: port falls back to the swap and says why)

    python -m tests.test_transfer_banners
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unittransfer import banners  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


def xml(unit_banners: str, factions=("england", "france")) -> str:
    tex = "".join(f'\t\t\t<Texture Faction="{f}" DiffuseMap="banners/textures/{f}.texture"/>\r\n'
                  for f in factions)
    return ("<Banners>\r\n\t<Settings/>\r\n\t<FactionBanners>\r\n"
            '\t\t<Banner Name="main_infantry" MainMesh="banners/a.mesh">\r\n' + tex +
            "\t\t</Banner>\r\n"
            '\t\t<Banner Name="main_cavalry" MainMesh="banners/b.mesh">\r\n' + tex +
            "\t\t</Banner>\r\n\t</FactionBanners>\r\n"
            "\t<UnitSpecificBanners>\r\n" + unit_banners + "\t</UnitSpecificBanners>\r\n"
            "\t<HolyBanners>\r\n"
            '\t\t<Banner Name="crusade">\r\n' + tex.replace("Texture ", "MeshAndTexture Mesh=\"banners/c.mesh\" ")
            + "\t\t</Banner>\r\n\t</HolyBanners>\r\n</Banners>\r\n")


HOSP = ('\t\t<Banner Name="Hospitaller">\r\n'
        '\t\t\t<MeshAndTexture Faction="hospitallers" Mesh="banners/hosp.mesh" DiffuseMap="banners/textures/hosp.texture"/>\r\n'
        '\t\t\t<MeshAndTexture Faction="england" Mesh="banners/hosp.mesh" DiffuseMap="banners/textures/hosp_en.texture"/>\r\n'
        '\t\t</Banner>\r\n')
SRC = xml(HOSP, ("england", "france", "hospitallers"))
DST = xml("", ("england", "france", "milan"))

print("\n1) port_banner")
out, paths = banners.port_banner(SRC, DST, "unit", "Hospitaller", ["milan", "england"],
                                 ["england", "france", "milan"])
d = banners.declared(out)
check("the banner lands in the destination's unit list", d["unit"] == ["Hospitaller"])
doc = banners.parse(out)
b = next(x for x in banners.banners(doc) if x["name"] == "Hospitaller")
facs = [r["faction"] for r in b["rows"]]
check(f"its rows: the destination's factions only, each owner covered ({facs})",
      sorted(facs) == ["england", "milan"])
check("the file is still well formed and ends where it did",
      not doc.errors and out.endswith("</Banners>\r\n") and "\r\n" in out and "\n\t\t<Ban" not in out.replace("\r\n", ""))
check(f"the files it names are handed back for the copy ({paths})",
      "banners/hosp.mesh" in paths and "banners/textures/hosp_en.texture" in paths)
edu = [("Knights", "unit", "Hospitaller", ["milan", "england"])]
found = [f for f in banners.check(doc, ["england", "france", "milan"], edu)
         if "Hospitaller" in f["message"] or f["kind"] in ("undeclared", "coverage", "stale")]
check("and the destination's own check finds nothing about it", not found)
check("a banner the destination already has is left alone",
      banners.port_banner(SRC, out, "unit", "Hospitaller", ["milan"], ["milan"]) == (out, []))
try:
    banners.port_banner(SRC, DST, "unit", "Templar", ["milan"], ["milan"])
    check("a banner the source does not declare is refused", False)
except banners.BannerError as e:
    check("a banner the source does not declare is refused, with the reason", "Templar" in e.message)

print("\n2) swap_for")
have = banners.declared(DST)
check("faction: main_cavalry for cavalry", banners.swap_for("faction", "cavalry", have) == "main_cavalry")
check("faction: main_infantry for everything else",
      banners.swap_for("faction", "infantry", have) == "main_infantry"
      and banners.swap_for("faction", "siege", have) == "main_infantry")
check("holy: the crusade banner", banners.swap_for("holy", "cavalry", have) == "crusade")
check("unit: the line goes", banners.swap_for("unit", "cavalry", have) == "")

print("\n3) a real plan")
from tests._realmod import MODS  # noqa: E402
ref, dac = MODS / "Third_Age_Reforged", MODS / "Divide_and_Conquer_EUR"
if not (ref.is_dir() and dac.is_dir()):
    print("  [skip] needs Third_Age_Reforged and Divide_and_Conquer_EUR")
else:
    from unittransfer import transfer as tr
    from unittransfer.mod import Mod
    src, dst = Mod(ref), Mod(dac)
    unit = next(u for u in src.edu.units if u.type == "Bomb Platforms")
    for mode in ("swap", "port"):
        p = tr.plan_transfer(src, "Bomb Platforms", dst, tr.TransferOptions(banner_mode=mode))
        block = tr._build_unit_block(p, unit)
        lines = [ln.split()[2] for ln in block.splitlines() if ln.startswith("banner faction")]
        acts = [(a[1], a[2]) for a in p.banner_actions]
        check(f"{mode}: main_none, which DaC has not got, is planned and swapped ({acts})",
              acts == [("main_none", "swap")] and lines == [
                  "main_cavalry" if (unit.category or "").lower() == "cavalry" else "main_infantry"])
        if mode == "port":
            check("  port says why it fell back: the source does not declare it either",
                  "has no faction banner main_none" in p.banner_actions[0][3])
        check("  and the destination's banner file is not rewritten for it", not p.banner_text)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
print("ALL PASSED" if all(ok) else "SOME FAILED")
sys.exit(0 if all(ok) else 1)
