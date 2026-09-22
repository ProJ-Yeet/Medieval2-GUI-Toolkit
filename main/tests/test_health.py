"""Phase 54: one door to every check.

`unittransfer.health` owns no rule; it adapts each validator's answer to one
shape. So this holds the adapters, not the rules:

  1) every source runs on every installed mod, none fails, and every finding
     is in the shape the page reads
  2) the severity reader ranks by the checkers' own sentences - held to real
     messages the checkers write, so a rewording that drops "crash" shows here
  3) a source that throws is a failed source, not an empty one and not a crash
  4) the map source is off without a map, and on with one
  5) the recruitment notes fold to one per building line

    python -m tests.test_health
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unittransfer import campmap, health  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402

MODS = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition/mods")
CANDIDATES = ("Divide_and_Conquer_EUR", "ROCSS", "Third_Age_Reforged")

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


FIELDS = {"source", "code", "severity", "message", "file", "line", "what", "when",
          "count", "baseline", "open"}

# ---- 2) the severity reader, on sentences the checkers really write ---------
print("\n2) severity from the checker's own words")
real = [
    ("fatal", "this trait has no `Characters` line - the game stops loading the file "
              "here with \"Unknown identifier ... when expecting characters\""),
    ("fatal", "12 antitraits - more than 8 crashes the game"),
    ("fatal", "no `Image` line - the game will not load this ancillary"),
    ("warn", "the engine reads only the first type in a `Characters` list, so only spy "
             "can ever get this trait"),
    ("warn", "trigger `SupplyShip1` affects `Trait`, which this file does not define"),
]
for want, msg in real:
    check(f"{want}: {msg[:60]}...", health.severity_of({"message": msg}) == want)
check("an explicit severity wins over the words",
      health.severity_of({"severity": "note", "message": "crashes the game"}) == "note")
check("fatal: True is fatal whatever it says",
      health.severity_of({"fatal": True, "message": "odd"}) == "fatal")
check("a panel in the sentence moves it to 'panel'",
      health.when_of("crashes the character detail screen", "launch") == "panel")
check("a battle in the sentence moves it to 'battle'",
      health.when_of("the game crashes when the battle loads", "campaign") == "battle")
check("otherwise the source's own stage", health.when_of("a typo", "launch") == "launch")

# ---- 3) a source that throws --------------------------------------------------
print("\n3) a broken source is reported, not swallowed")


@health.source("zz_broken", "A broken check", "home", "nothing", "launch")
def _broken(mod, ctx):
    raise ValueError("on purpose")


try:
    r = health.run(object(), only=("zz_broken",))
    row = r["sources"][0]
    check("the run returns", True)
    check("the source is marked failed", row["state"] == "failed")
    check("with the error it raised", "on purpose" in row["error"])
    check("and no findings are invented for it", r["findings"] == [])
except Exception as e:                                  # noqa: BLE001
    check(f"the run returns (raised {e!r})", False)
finally:
    health.SOURCES[:] = [s for s in health.SOURCES if s.id != "zz_broken"]

# ---- 1), 4), 5) over the installed mods ---------------------------------------
installed = [m for m in CANDIDATES if (MODS / m / "data").is_dir()]
if not installed:
    print(f"\nno mod installed under {MODS} - the real-mod half is SKIPPED")
for name in installed:
    print(f"\n1) {name}")
    mod = Mod(MODS / name)
    r = health.run(mod)
    check("every source ran or was off",
          all(s["state"] in ("ok", "off") for s in r["sources"]))
    for s in r["sources"]:
        if s["state"] == "failed":
            print(f"      {s['id']}: {s['error']}")
    check("without a map the map source is off",
          next(s for s in r["sources"] if s["id"] == "map")["state"] == "off")
    fs = r["findings"]
    check(f"{len(fs)} findings, every one in the shape the page reads",
          all(set(f) == FIELDS for f in fs))
    check("every severity is fatal/warn/note",
          all(f["severity"] in health.SEVERITIES for f in fs))
    check("every when is one the page groups by",
          all(f["when"] in health.WHEN_IDS for f in fs))
    check("every finding says which screen opens it",
          all(f["open"].get("mode") for f in fs))
    check("the counts add up", sum(r["counts"].values()) == len(fs))
    order = [health.SEVERITIES.index(f["severity"]) for f in fs]
    check("fatal comes first", order == sorted(order))
    check("no line number in any identity",
          not any(f"|{f['line']}|" in f"|{f['what']}|" for f in fs if f["line"]))
    gaps = [f for f in fs if f["code"] == "recruit.gap"]
    check(f"5) recruitment gaps fold to one per building line ({len(gaps)})",
          len(gaps) == len({f["open"]["name"] for f in gaps}))
    check("the cleanup audits are listed and not run",
          [s["id"] for s in r["slow"]] == ["bmdb", "dupes", "stratmap", "cards"])

    print(f"\n4) {name} with its map")
    rm = health.run(mod, map_for=lambda c, m=mod: campmap.CampaignMap(m), only=("map",))
    row = rm["sources"][0]
    check("with a map the map source runs", row["state"] == "ok")
    check("its findings keep the map screen's key to jump to",
          all(f["open"].get("key") for f in rm["findings"] if f["source"] == "map"
              and not f["code"].startswith("failed")))

# ---- 6) 54b: the crash guides' rules, a fixture each ---------------------------
print("\n6) the crash guides' rules")
from tests import _tmp  # noqa: E402
from unittransfer import crashrules  # noqa: E402

fx = Path(_tmp.mkdtemp(prefix="ut_crash_")) / "Fixture"
data = fx / "data"
camp = data / "world/maps/campaign/imperial_campaign"
camp.mkdir(parents=True)
(data / "text").mkdir()
(data / "unit_models").mkdir()
(camp / "descr_strat.txt").write_text(
    "faction england, balanced smith\nai_label catholic\n"
    "faction france, balanced smith\nai_label nobody_declared_me\n"
    "faction papal_states, balanced smith\nai_label papal_faction\n", encoding="latin-1")
(data / "descr_campaign_ai_db.xml").write_text(
    '<root>\n<faction_ai_label name="catholic">\n</faction_ai_label>\n</root>\n',
    encoding="latin-1")
(camp / "campaign_script.txt").write_text(
    "script\n    historic_event Keyed_In_Lower_Case\n    historic_event no_text_at_all\n"
    "    ; historic_event only_in_a_comment\nend_script\n", encoding="latin-1")
(data / "text/historic_events.txt").write_bytes(
    b"\xff\xfe" + "{KEYED_IN_LOWER_CASE_TITLE}Title\r\n".encode("utf-16-le"))
(data / "export_descr_character_traits.txt").write_text(
    "Trait Brave\n    Characters family\n    ExcludeCultures eastern_european\n"
    "    AntiTraits Coward\n\n    Level Brave_1\n        Description Brave_1_desc\n"
    "        EffectsDescription Brave_1_effects_desc\n        Threshold 1\n\n"
    "Trait Coward\n    Characters family\n    AntiTraits Brave\n\n    Level Coward_1\n"
    "        Description Coward_1_desc\n        EffectsDescription Coward_1_effects_desc\n"
    "        Threshold 1\n", encoding="latin-1")
(data / "descr_banners_new.xml").write_text(
    '<banner texture="C:\\Games\\M2TW\\mods\\x\\data\\banners\\a.tga"/>\n', encoding="latin-1")
(data / "unit_models/battle_models.modeldb").write_bytes(
    b"22 serialization::archive 3 0 0 0 0 1 0 0\n1 a   b\n")
found, failed = crashrules.run(Mod(fx))
codes = [f.code for _, f in found]
check("no rule failed on the fixture", not failed)
check("ai.label_unknown: the undeclared label, and not the engine's own papal_faction",
      [f.message.split(" has ")[0] for _, f in found if f.code == "ai.label_unknown"]
      == ["imperial_campaign: france"])
ev = [f.what for _, f in found if f.code == "event.no_text"]
check("event.no_text: case-blind, so only the event with no key at all, not the comment",
      ev == ["imperial_campaign|no_text_at_all"])
check("trait.antitrait_cultures: the pair once, not twice",
      codes.count("trait.antitrait_cultures") == 1)
check("path.absolute: the drive path in the banner file", codes.count("path.absolute") == 1)
check("modeldb.spaces: the line with three spaces", codes.count("modeldb.spaces") == 1)
check("every rule has a source and a severity Health knows",
      all(r.source and r.severity in health.SEVERITIES for r in crashrules.RULES))
check("the refused claims say what was measured",
      all(x["measured"] and x["source"] for x in crashrules.REFUSED))
no_ai = Path(_tmp.mkdtemp(prefix="ut_crash_")) / "NoAi"
(no_ai / "data/world/maps/campaign/imperial_campaign").mkdir(parents=True)
(no_ai / "data/world/maps/campaign/imperial_campaign/descr_strat.txt").write_text(
    "faction england\nai_label anything\n", encoding="latin-1")
check("a mod with no AI file of its own uses the game's, and is not flagged",
      not [f for _, f in crashrules.run(Mod(no_ai))[0] if f.code == "ai.label_unknown"])
for name in installed:
    fs, fl = crashrules.run(Mod(MODS / name))
    check(f"{name}: no crash rule fails, and none reports a fatal on a shipping mod",
          not fl and not [f for _, f in fs if f.severity == "fatal"])

print("\n" + ("ALL PASSED" if all(ok) else "SOME FAILED"))
print(f"{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
