"""Phase 65: descr_banners_new.xml.

    python -m tests.test_banners

1. Both installed mods, as measured: ROCSS's two broken texture paths (an
   extension twice, a letter too many) and nothing else above a note; DaC's
   thirteen lines after </Banners> found, its royal banner and its crusade
   gaps as notes; no faction in either lacking a banner its units carry; the
   multiplayer placeholder rows never reported.
2. The rules on a fixture: a faction owning a unit whose banner has no row
   for it, a banner the EDU names and the file lacks, a row twice, a colour
   past 255, a number that is not one, a tag closed out of order.
3. Saves on a temp copy of DaC's file: an attribute changed, a row added by
   copy and one removed, the trailing lines cut; the rest of the file byte
   for byte; a stale signature refused; one Undo.
4. The clone writes the new faction into every banner the donor is in, and
   the faction audit has the row.
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from unittransfer import banners as bn  # noqa: E402
from unittransfer import factionaudit as fau  # noqa: E402
from unittransfer import factionclone as fc  # noqa: E402
from unittransfer import transfer  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402
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
ROC, DAC = MODS / "ROCSS", MODS / "Divide_and_Conquer_EUR"
ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return bool(cond)


def codes(fs):
    return {(f["code"], f["severity"]) for f in fs}


print("\n1) the installed mods")
if (ROC / "data" / bn.REL).is_file():
    ov = bn.overview(Mod(ROC))
    bad = sorted(f["code"] for f in ov["findings"] if f["severity"] != "note")
    check("ROCSS: the two broken paths and nothing else above a note", bad == ["extension", "typo"])
    check("ROCSS: the typo names the file it meant",
          any("faction_banner_hospitaller_trans.texture is" in f["message"] for f in ov["findings"]))
    check(f"ROCSS: {len(ov['banners'])} banners, the four main ones carried by hundreds of units",
          all(b["units"] > 100 for b in ov["banners"] if b["name"] in ("main_spear", "main_infantry",
                                                                        "main_cavalry", "main_missile")))
    check("ROCSS: no multiplayer placeholder is reported", not any(f["code"] == "stale" for f in ov["findings"]))
if (DAC / "data" / bn.REL).is_file():
    ov = bn.overview(Mod(DAC))
    got = codes(ov["findings"])
    check("DaC: the thirteen lines after </Banners> are a warning, from line 391",
          ov["trailing_lines"] == 13 and any(f["code"] == "trailing" and f["line"] == 391 for f in ov["findings"]))
    check("DaC: the royal banner's three missing factions and the two crusade banners are notes",
          ("royal", "note") in got and sum(1 for f in ov["findings"] if f["code"] == "holy") == 2)
    check("DaC: nothing else above a note", [f["code"] for f in ov["findings"] if f["severity"] != "note"] == ["trailing"])
    check("DaC: settings read in full (13 elements with numbers)", len(ov["settings"]) == 13)

print("\n2) the rules")
XML = """<Banners>
  <Settings><RoutingColour R="300" G="x" B="0"/></Settings>
  <FactionBanners>
    <Banner Name="main_spear" MainMesh="a.mesh" EffectOffsetX="0">
      <Textures>
        <Texture Faction="England" DiffuseMap="t.texture"/>
        <Texture Faction="england" DiffuseMap="t.texture"/>
      </Textures>
    </Banner>
  </FactionBanners>
  <HolyBanners>
    <Banner Name="crusade"><MeshesAndTextures>
      <MeshAndTexture Faction="England" Mesh="m" DiffuseMap="d.texture.texture"/>
    </MeshesAndTextures></Banner>
  </HolyBanners>
</Banners>
junk
"""
doc = bn.parse(XML)
edu = [("Spears", "faction", "main_spear", ["england", "france", "all"]),
       ("Pikes", "unit", "pikes", ["england"]),
       ("Knights", "holy", "crusade", ["france"])]
got = codes(bn.check(doc, ["england", "france"], edu))
check("a faction owning a unit whose banner has no row for it is a warning; `all` is not a faction",
      ("coverage", "warn") in got
      and not any("all owns" in f["message"] for f in bn.check(doc, ["england", "france"], edu)))
check("a banner the EDU names and the file lacks is a warning", ("undeclared", "warn") in got)
check("a row twice, a colour past 255, the lines after the root: warnings",
      {("duplicate", "warn"), ("colour", "warn"), ("trailing", "warn")} <= got)
check("a number that is not one is fatal, an extension twice a warning, a holy gap a note",
      ("number", "fatal") in got and ("extension", "warn") in got and ("holy", "note") in got)
got = codes(bn.check(bn.parse("<Banners><A></B></A></Banners>"), [], []))
check("a tag closed out of order is fatal", ("xml", "fatal") in got)

print("\n3) saves, on a temp copy of DaC's file")
if not (DAC / "data" / bn.REL).is_file():
    print("  -- DaC is not installed; SKIPPED")
else:
    root = Path(_tmp.mkdtemp(prefix="ut_ban_")) / "BanMod"
    (root / "data").mkdir(parents=True)
    for rel in (bn.REL, "descr_sm_factions.txt"):
        shutil.copy2(DAC / "data" / rel, root / "data" / rel)
    mod = Mod(root)
    before = (root / "data" / bn.REL).read_bytes()
    ov = bn.overview(mod)
    spear = next(b for b in ov["banners"] if b["name"] == "main_spear")
    eng = next(r for r in spear["rows"] if r["faction"] == "England")
    fra = next(r for r in spear["rows"] if r["faction"] == "France")
    body = {"sig": ov["sig"], "attrs": {str(spear["id"]): {"EffectOffsetY": "8.5"}},
            "add_rows": [{"like": eng["id"], "faction": "Zz_new"}],
            "remove_rows": [fra["id"]], "trim": True}
    p = bn.plan(mod, body)
    check(f"the plan is clean ({len(p.changes)} changes)", not p.errors and p.text)
    check("a faction not in the roster is warned about", any("Zz_new" in w for w in p.warnings))
    res = bn.apply(p)
    ov2 = bn.overview(Mod(root))
    sp2 = next(b for b in ov2["banners"] if b["name"] == "main_spear")
    facs = [r["faction"] for r in sp2["rows"]]
    check("the offset changed, the new row right under England's, France's row gone",
          sp2["attrs"]["EffectOffsetY"] == "8.5" and facs[facs.index("England") + 1] == "Zz_new"
          and "France" not in facs)
    check("the copy points at England's textures",
          next(r for r in sp2["rows"] if r["faction"] == "Zz_new")["attrs"]["DiffuseMap"] == eng["attrs"]["DiffuseMap"])
    check("the trailing lines are gone and the file ends at </Banners>",
          ov2["trailing_lines"] == 0 and (root / "data" / bn.REL).read_text(encoding="latin-1").rstrip().endswith("</Banners>"))
    after = (root / "data" / bn.REL).read_bytes()
    head = before[:before.index(b'<Banner Name="main_spear"')]
    check("everything above the first edit is byte for byte what it was", after.startswith(head))
    stale = bn.plan(mod, dict(body, sig="0" * 16))
    check("an edit made against an older copy is refused", any("changed on disk" in e for e in stale.errors))
    bad = bn.plan(mod, {"sig": ov2["sig"], "attrs": {str(sp2["id"]): {"EffectOffsetY": "high"}}})
    check("a number that is not one is refused", bad.errors)
    transfer.undo(res["id"])
    check("one undo puts the file back byte for byte", (root / "data" / bn.REL).read_bytes() == before)

print("\n4) the clone and the audit")
if (ROC / "data" / bn.REL).is_file():
    rmod = Mod(ROC)
    for art in (True, False):
        plan = fc.plan(rmod, {"source": "venice", "new": "zz_probe", "art": art})
        e = next(x for x in plan.edits if x.rel == bn.REL)
        rows = [r for b in bn.banners(bn.parse(e.text)) for r in b["rows"] if r["faction"] == "Zz_probe"]
        ven = [r for b in bn.banners(bn.parse(e.text)) for r in b["rows"] if r["faction"] == "Venice"]
        diffuse = rows[0]["attrs"]["DiffuseMap"].lower() if rows else ""
        check(f"art {'on' if art else 'off'}: a row in every banner Venice is in ({len(rows)}), pointing at "
              + ("the renamed copy" if art else "Venice's own art"),
              len(rows) == len(ven) == e.count and
              (("zz_probe" in diffuse) if art else ("venice" in diffuse)))
    c = fau.Census(rmod)
    missing = [s for s in c.slots if next(r for r in fau.evaluate(c, s) if r["id"] == "banners")["state"] != "ok"]
    check("the audit's Battle banners row: every ROCSS faction has one, and it is a gap", not missing
          and fau.BY_ID["banners"].level == "gap")

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
