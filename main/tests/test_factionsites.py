"""Phase 63: descr_lbc_db.txt and descr_offmap_models.txt.

    python -m tests.test_factionsites

1. Both installed mods: 30 populace blocks each, every one adding up to 100;
   the off-map tree's three sections; ROCSS clean, and DaC's one real defect
   found - `faction egypt` with no opening brace, which is why its navy section
   ends sixteen factions in.
2. The rules on fixtures: a share that is not a whole number, shares that do
   not add up to 100, a faction twice, and the roster mismatches as notes.
3. Saves on temp copies of ROCSS's two files: a faction's townsfolk changed,
   a model added and one dropped, a missing faction added, one removed, an
   off-map row changed, a navy faction added by copy and one removed; tabs and
   CRLF kept; a stale signature refused; one Undo for the lot.
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from unittransfer import factionsites as fs  # noqa: E402
from unittransfer import transfer  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402

MODS = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition/mods")
ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return bool(cond)


print("\n1) the installed mods")
for name in ("ROCSS", "Divide_and_Conquer_EUR"):
    if not (MODS / name / "data" / fs.LBC_REL).is_file():
        continue
    ov = fs.overview(Mod(MODS / name))
    tops = [b["path"] for b in ov["offmap"] if b["depth"] == 0]
    sums = {sum(int(m["share"]) for m in p["models"]) for p in ov["lbc"]}
    bad = [f for f in ov["findings"] if f["severity"] != "note"]
    check(f"{name}: {len(ov['lbc'])} populace blocks, every one adding up to {sums}",
          len(ov["lbc"]) == 30 and sums == {100})
    if name == "ROCSS":
        check(f"ROCSS: the three sections {tops}, and no findings at all",
              tops == ["navy", "settlement", "port"] and not ov["findings"])
    else:
        check("DaC: its one defect is found - faction egypt, line 115, has no opening brace",
              len(bad) == 1 and bad[0]["code"] == "unopened" and "egypt" in bad[0]["message"]
              and bad[0]["line"] == 115)
        check("and its roster mismatches are notes (gundabad and scripts with no populace, "
              "ents with one)", {"gundabad", "scripts"} <= {f["message"].split()[0] for f in ov["findings"]
                                                            if f["code"] == "absent" and f["key"].startswith("lbc/")}
              and any(f["code"] == "stale" and "ents" in f["message"] for f in ov["findings"]))

print("\n2) the rules")
LBC = "faction a\nmodel x 40\nmodel y 60\n\nfaction b\nmodel x 50\nmodel y 30\n\nfaction a\nmodel x 100\nfaction c\nmodel x lots\n"
_, pops = fs.parse_lbc(LBC)
got = {(f["code"], f["severity"]) for f in fs.check_lbc(pops, ["a", "b", "d"])}
check("shares that add up to 80 are a warning", ("sum", "warn") in got)
check("a faction twice is a warning", ("duplicate", "warn") in got)
check("a share that is not a whole number is fatal", ("share", "fatal") in got)
check("a roster faction with no block, and a block for no faction, are notes",
      ("absent", "note") in got and ("stale", "note") in got)

print("\n3) saves, on temp copies of ROCSS's two files")
REAL = MODS / "ROCSS" / "data"
if not (REAL / fs.OFFMAP_REL).is_file():
    print("  -- ROCSS is not installed; SKIPPED")
else:
    root = Path(_tmp.mkdtemp(prefix="ut_sites_")) / "SitesMod"
    (root / "data").mkdir(parents=True)
    for rel in (fs.LBC_REL, fs.OFFMAP_REL, "descr_sm_factions.txt"):
        shutil.copy2(REAL / rel, root / "data" / rel)
    mod = Mod(root)
    before = {rel: (root / "data" / rel).read_bytes() for rel in (fs.LBC_REL, fs.OFFMAP_REL)}
    ov = fs.overview(mod)
    first = ov["lbc"][0]["faction"]
    second = ov["lbc"][1]["faction"]
    navy = [b for b in ov["offmap"] if b["path"].startswith("navy/") and b["kind"] == "faction"]
    row = navy[0]["rows"][0]
    toks = list(row["tokens"])
    toks[-2] = "150"
    body = {"lbc": {first: [["roman_peasant", "30"], ["roman_female_peasant", "50"], ["greek_peasant", "20"]],
                    second: None,
                    "zz_new": [["roman_peasant", "100"]]},
            "offmap": {"rows": {str(row["line"]): toks},
                       "add": [{"section": "navy", "faction": "zz_new", "like": navy[0]["head"][1]}],
                       "remove": [{"section": "navy", "faction": navy[1]["head"][1]}]},
            "offmap_sig": ov["offmap_sig"]}
    p = fs.plan(mod, body)
    check(f"one plan, both files ({len(p.changes)} changes)", not p.errors and set(p.texts) == {fs.LBC_REL, fs.OFFMAP_REL})
    check("a faction not in the roster is warned about", any("zz_new" in w for w in p.warnings))
    res = fs.apply(p)
    ov2 = fs.overview(Mod(root))
    lb = {x["faction"]: [(m["model"], m["share"]) for m in x["models"]] for x in ov2["lbc"]}
    check("the first faction's townsfolk are the three asked for",
          lb.get(first) == [("roman_peasant", "30"), ("roman_female_peasant", "50"), ("greek_peasant", "20")])
    check("the second's block is gone, the new one is there", second not in lb and lb.get("zz_new") == [("roman_peasant", "100")])
    nv = {b["head"][1]: b for b in ov2["offmap"] if b["path"].startswith("navy/") and b["kind"] == "faction"}
    check("the navy row is changed, a faction added by copy, one removed",
          nv[navy[0]["head"][1]]["rows"][0]["tokens"][-2] == "150" and "zz_new" in nv
          and navy[1]["head"][1] not in nv)
    raw = (root / "data" / fs.OFFMAP_REL).read_bytes()
    check("the off-map file keeps its CRLF and its tabs", b"\r\n" in raw and b"\n" not in raw.replace(b"\r\n", b"")
          and b"\t\tlarge" in raw)
    stale = fs.plan(mod, {"offmap": body["offmap"], "offmap_sig": "0" * 16})
    check("an off-map edit made against an older copy is refused", any("changed on disk" in e for e in stale.errors))
    transfer.undo(res["id"])
    check("one undo puts both files back byte for byte",
          all((root / "data" / rel).read_bytes() == b for rel, b in before.items()))
    bad = fs.plan(mod, {"lbc": {first: [["two words", "10"]]}})
    check("a model name with a space in it is refused", bad.errors)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
