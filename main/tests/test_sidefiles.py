"""Phase 64: descr_animals.txt, descr_standards.txt, export_descr_advice.txt.

    python -m tests.test_sidefiles

1. Both installed mods, as measured: ROCSS's Princess carries `animal wardogs`
   and the file declares `wardog`, a warning; DaC's two animals point at models
   its modeldb lacks and nothing uses them, notes; both standards files read as
   six rectangles and their symbol sheets, all on disk; ROCSS's one advice
   thread and its trigger clean, DaC's advice file empty and clean.
2. The rules on fixtures: an animal's number that is not one, a class the
   header does not list, a rectangle that is not four numbers or covers
   nothing, a trigger firing a thread nobody declared, a thread nothing fires.
3. Saves on a temp mod built from DaC's animals and ROCSS's standards and
   advice: a field changed, x_radius dropped, an animal copied and one
   removed, DaC's missing final newline kept; a rectangle and a scale changed,
   a symbol sheet added and one removed; an advice priority and a trigger's
   score changed, then the thread removed with the trigger that only fired
   it; CRLF and tabs kept; a stale signature refused; one Undo for the lot.
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from unittransfer import sidefiles as sf  # noqa: E402
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
ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return bool(cond)


def codes(fs):
    return {(f["code"], f["severity"]) for f in fs}


print("\n1) the installed mods")
ROC, DAC = MODS / "ROCSS", MODS / "Divide_and_Conquer_EUR"
if (ROC / "data" / sf.ANIMALS_REL).is_file():
    ov = sf.overview(Mod(ROC))
    bad = [f for f in ov["findings"] if f["severity"] != "note"]
    check("ROCSS: one animal, wardog, with a model its modeldb has",
          [a["name"] for a in ov["animals"]] == ["wardog"] and ov["animals"][0]["model_known"])
    check("ROCSS: its one finding is the Princess's `animal wardogs`, a warning",
          len(bad) == 1 and bad[0]["code"] == "undeclared" and "Princess" in bad[0]["message"]
          and bad[0]["severity"] == "warn")
    rects = [r["key"] for r in ov["standards"] if r["kind"] == "rect"]
    sheets = [r for r in ov["standards"] if r["kind"] == "symbols"]
    check(f"ROCSS: six rectangles, {len(sheets)} symbol sheets (8 + 2), all on disk",
          rects == list(sf.BANNER_RECTS) and len(sheets) == 10 and all(r["on_disk"] for r in sheets)
          and [r["section"] for r in sheets].count("factions") == 8)
    adv = ov["advice"]
    check("ROCSS: the background-script thread, one item, one trigger firing it",
          [t["name"] for t in adv["threads"]] == ["BackgroundScriptThread"]
          and len(adv["threads"][0]["items"]) == 1
          and adv["triggers"][0]["fires"][0]["thread"] == "BackgroundScriptThread")
if (DAC / "data" / sf.ANIMALS_REL).is_file():
    ov = sf.overview(Mod(DAC))
    got = codes(ov["findings"])
    check("DaC: pig and wardog, each model missing from its modeldb and used by no unit - notes",
          [a["name"] for a in ov["animals"]] == ["pig", "wardog"]
          and sum(1 for f in ov["findings"] if f["code"] == "model" and f["severity"] == "note") == 2)
    check("DaC: nothing above a note anywhere", not [f for f in ov["findings"] if f["severity"] != "note"])
    check("DaC: standard_index runs to 30 and is not counted against the seven sheets",
          ov["standard_indexes"]["max"] == 30 and not any(c[0] == "sheets" for c in got))
    check("DaC: an advice file with no thread and nothing to say about it",
          ov["advice"]["threads"] == [] and not any(f["key"].startswith("advice/") for f in ov["findings"]))

print("\n2) the rules")
_, an = sf.parse_animals("type dog\nclass horse\nmodel m\nradius x\nheight 1\nmass 1\nwings 2\n"
                         "type dog\nclass pig\nmodel n\nradius 1\n")
got = codes(sf.check_animals(an, {"m"}, {"dog": ["Hounds"], "cat": ["Cats"]}))
check("a radius that is not a number is fatal", ("number", "fatal") in got)
check("a class the header does not list, a key it does not know, a name twice: warnings",
      {("class", "warn"), ("key", "warn"), ("duplicate", "warn")} <= got)
check("a missing model for an animal a unit uses is a warning; an undeclared animal too",
      ("model", "warn") in got and ("undeclared", "warn") in got)
check("a record with no height or mass is warned", ("missing", "warn") in got)
_, st = sf.parse_standards("file_scale 1.0x\nbanner_star 0, 0.5, 0.4\nbanner_flag 0.5, 0.5, 0.2, 0.9\n"
                           "banner_sail 0, 0, 1.5, 1\nsymbols a.tga\n")
got = codes(sf.check_standards(st, Path(".")))
check("a scale and a rectangle that are not numbers are fatal",
      ("number", "fatal") in got and ("rect", "fatal") in got)
check("a rectangle covering nothing, one off the texture, a sheet before any section: warnings",
      {("empty", "warn"), ("range", "warn"), ("section", "warn"), ("sheets", "warn")} <= got)
_, th, tf = sf.parse_advice("AdviceThread A\n GameArea Campaign\n Item i\n  Priority high\n"
                            "AdviceThread B\n GameArea Battle\n Item j\n  Priority 1\n"
                            "Trigger t\n WhenToTest BattleDeploymentPhaseCommenced\n AdviceThread C 1\n")
got = codes(sf.check_advice(th, tf, Path(".")))
check("a priority that is not a whole number is fatal", ("number", "fatal") in got)
check("a trigger firing an undeclared thread is a warning; threads nothing fires are notes",
      ("thread", "warn") in got and ("unfired", "note") in got)

print("\n3) saves, on a temp mod of DaC's animals and ROCSS's standards and advice")
if not ((DAC / "data" / sf.ANIMALS_REL).is_file() and (ROC / "data" / sf.ADVICE_REL).is_file()):
    print("  -- the mods are not installed; SKIPPED")
else:
    root = Path(_tmp.mkdtemp(prefix="ut_side_")) / "SideMod"
    (root / "data" / "text").mkdir(parents=True)
    shutil.copy2(DAC / "data" / sf.ANIMALS_REL, root / "data" / sf.ANIMALS_REL)
    for rel in (sf.STANDARDS_REL, sf.ADVICE_REL, sf.ADVICE_TEXT_REL):
        shutil.copy2(ROC / "data" / rel, root / "data" / rel)
    mod = Mod(root)
    before = {rel: (root / "data" / rel).read_bytes() for rel in sf.RELS}
    ov = sf.overview(mod)
    std = {r["key"] if r["kind"] != "symbols" else f"s{r['line']}": r for r in ov["standards"]}
    flag = std["banner_flag"]
    scale = next(r for r in ov["standards"] if r["kind"] == "scale")
    sheets = [r for r in ov["standards"] if r["kind"] == "symbols" and r["section"] == "rebels_factions"]
    item = ov["advice"]["threads"][0]["items"][0]
    prio = next(f for f in item["fields"] if f["key"] == "Priority")
    fire = ov["advice"]["triggers"][0]["fires"][0]
    body = {"sigs": ov["sigs"],
            "animals": {"edit": {"pig": {"mass": "0.75", "x_radius": ""}},
                        "add": [{"name": "bear", "like": "wardog"}], "remove": ["wardog"]},
            "standards": {"lines": {str(flag["line"]): ["0.6", "0.02", "0.98", "0.97"],
                                    str(scale["line"]): ["0.2f"]},
                          "symbols_add": [{"section": "rebels_factions", "path": "banners/symbols11.tga"}],
                          "symbols_remove": [sheets[0]["line"]]},
            "advice": {"fields": {str(prio["line"]): "7", str(fire["line"]): "2"}}}
    p = sf.plan(mod, body)
    check(f"one plan, all three files ({len(p.changes)} changes)",
          not p.errors and set(p.texts) == set(sf.RELS))
    check("a sheet that is not in the mod is said", any("symbols11" in w for w in p.warnings))
    res = sf.apply(p)
    ov2 = sf.overview(Mod(root))
    an = {a["name"]: a for a in ov2["animals"]}
    check("pig's mass changed and its x_radius gone; bear copied from wardog; wardog gone",
          an["pig"]["fields"]["mass"]["value"] == "0.75" and "x_radius" not in an["pig"]["fields"]
          and an["bear"]["fields"]["model"]["value"] == "wardogs" and "wardog" not in an)
    raw = (root / "data" / sf.ANIMALS_REL).read_bytes()
    check("the animals file still ends without a newline, as DaC's does, and keeps CRLF",
          not raw.endswith(b"\n") and b"\r\n" in raw and b"\n" not in raw.replace(b"\r\n", b""))
    st2 = {r["key"]: r for r in ov2["standards"] if r["kind"] == "rect"}
    check("banner_flag's four numbers changed, the others not",
          st2["banner_flag"]["values"] == ["0.6", "0.02", "0.98", "0.97"]
          and st2["banner_star"]["values"] == std["banner_star"]["values"])
    reb = [r["values"][0] for r in ov2["standards"] if r["kind"] == "symbols" and r["section"] == "rebels_factions"]
    check("the rebel sheets: the first taken out, the new one last",
          reb == [sheets[1]["values"][0], "banners/symbols11.tga"])
    sraw = (root / "data" / sf.STANDARDS_REL).read_bytes()
    check("the standards file keeps its spacing after the commas and its comment",
          b"0.6,    0.02," in sraw or b"0.6, 0.02," in sraw and b"can't have spaces" in sraw)
    it2 = ov2["advice"]["threads"][0]["items"][0]
    check("the item's priority and the trigger's score are changed",
          next(f["value"] for f in it2["fields"] if f["key"] == "Priority") == "7"
          and ov2["advice"]["triggers"][0]["fires"][0]["score"] == "2")
    stale = sf.plan(mod, {"sigs": {sf.ADVICE_REL: "0" * 16}, "advice": {"fields": {str(prio["line"]): "5"}}})
    check("an edit made against an older copy is refused", any("changed on disk" in e for e in stale.errors))
    gone = sf.plan(mod, {"sigs": ov2["sigs"], "advice": {"remove": ["BackgroundScriptThread"]}})
    check("removing the thread takes its one trigger with it",
          not gone.errors and "Trigger" not in gone.texts[sf.ADVICE_REL]
          and "AdviceThread" not in gone.texts[sf.ADVICE_REL].split("DATA STARTS HERE")[1].split(";")[0])
    transfer.undo(res["id"])
    check("one undo puts all three files back byte for byte",
          all((root / "data" / rel).read_bytes() == b for rel, b in before.items()))
    bad = sf.plan(mod, {"sigs": ov["sigs"], "animals": {"edit": {"pig": {"radius": "big"}}}})
    check("a radius that is not a number is refused", bad.errors)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
