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

print("\n" + ("ALL PASSED" if all(ok) else "SOME FAILED"))
print(f"{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
