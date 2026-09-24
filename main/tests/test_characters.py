"""Phase 69: descr_character.txt.

    python -m tests.test_characters

1. Both installed mods, as measured: twelve types each; every strat model,
   battle model and faction real; DaC's two england inquisitor blocks the only
   finding; every line read back as it was; and the join - a strat model's
   users named by type, faction and slot.
2. The rules on a fixture: a strat model, battle model and faction the mod
   lacks, a named character short of its three models, a general with no
   battle model, a faction twice in a type, a number that is not one.
3. Saves on a temp copy of DaC's file: a value changed keeping its comment,
   a strat model added and one removed, a block copied for another faction
   and one removed; the rest of the file byte for byte; a stale signature and
   bad values refused; one Undo.
4. The Strat models card: the entry route now carries the characters.
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from unittransfer import characters as ch  # noqa: E402
from unittransfer import transfer  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402

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
for path, name in ((ROC, "ROCSS"), (DAC, "DaC")):
    if not (path / "data" / ch.REL).is_file():
        continue
    mod = Mod(path)
    ov = ch.overview(mod)
    check(f"{name}: the twelve types, in the order of the file",
          [t["type"] for t in ov["types"]] == list(ch.TYPES))
    fs = ov["findings"]
    if name == "ROCSS":
        check("ROCSS: no finding at all", not fs)
    else:
        check("DaC: the only finding is england's two inquisitor blocks",
              [(f["code"], f["severity"]) for f in fs] == [("duplicate", "warn")]
              and "england" in fs[0]["message"] and "inquisitor" in fs[0]["message"])
    text = (path / "data" / ch.REL).read_bytes().decode("latin-1")
    check(f"{name}: every line read back as it was", "\n".join(ch.parse(text).lines) == text)
    named = next(t for t in ov["types"] if t["type"] == "named character")
    b0 = named["blocks"][0]
    model = next(r["value"] for r in b0["rows"] if r["key"] == "strat_model").split()[0]
    users = ch.users_of(mod, model)
    check(f"{name}: {model} is drawn by {len(users)} block slot(s), named by type, faction and slot",
          users and users[0]["type"] == "named character" and users[0]["key"] == f"block/{b0['line']}"
          and users[0]["faction"] == ", ".join(b0["factions"]))
if (DAC / "data" / ch.REL).is_file():
    ov = ch.overview(Mod(DAC))
    scripts = next(b for b in next(t for t in ov["types"] if t["type"] == "named character")["blocks"]
                   if b["factions"] == ["scripts"])
    labels = [r["label"] for r in scripts["rows"] if r["key"] == "strat_model"]
    check("DaC: a strat model's comment is its label (0 (Default), 1 (Heir), 2 (Leader)...)",
          labels[:3] == ["0 (Default)", "1 (Heir)", "2 (Leader)"])

print("\n2) the rules")
FIX = """type			named character
actions			moving_normal, garrison
wage_base		250
starting_action_points	x

faction			england
dictionary		2
strat_model		good_model ; 0 (Default)
battle_model		good_battle
battle_equip		gladius

faction			nowhere
dictionary		2
strat_model		good_model
strat_model		missing_model
strat_model		good_model
battle_model		missing_battle

type			general
actions			moving_normal

faction			england
dictionary		2
strat_model		good_model

faction			england
dictionary		two
strat_model		good_model
battle_model		good_battle
"""
refs = ch.Refs(roster=["england"], strat={"good_model"}, battle={"good_battle"})
fs = ch.check(ch.parse(FIX), refs)
got = codes(fs)
check("a strat model and a battle model the mod lacks are warnings",
      ("strat", "warn") in got and ("battle", "warn") in got
      and any("missing_model" in f["message"] for f in fs) and any("missing_battle" in f["message"] for f in fs))
check("a faction not in the roster is a warning", ("roster", "warn") in got)
check("a named character with fewer than three strat models is a warning",
      any(f["code"] == "strat" and "default, heir and leader" in f["message"] for f in fs))
check("a general with no battle model is a warning",
      any(f["code"] == "battle" and "no battle_model" in f["message"] for f in fs))
check("a faction twice in one type is a warning", ("duplicate", "warn") in got)
check("a number that is not one is fatal", ("number", "fatal") in got)

print("\n3) saves, on a temp copy of DaC's file")
if not (DAC / "data" / ch.REL).is_file():
    print("  -- DaC is not installed; SKIPPED")
else:
    root = Path(_tmp.mkdtemp(prefix="ut_chars_")) / "CharMod"
    (root / "data").mkdir(parents=True)
    for rel in (ch.REL, "descr_sm_factions.txt", "descr_model_strat.txt"):
        shutil.copy2(DAC / "data" / rel, root / "data" / rel)
    mod = Mod(root)
    before = (root / "data" / ch.REL).read_bytes()
    ov = ch.overview(mod)
    by = {t["type"]: t for t in ov["types"]}
    spy = by["spy"]
    wage = next(r for r in spy["head"] if r["key"] == "wage_base")
    named = by["named character"]
    sicily = next(b for b in named["blocks"] if b["factions"] == ["sicily"])
    models = [r for r in sicily["rows"] if r["key"] == "strat_model"]
    donor = spy["blocks"][0]
    gone = spy["blocks"][-1]
    body = {"sig": ov["sig"], "values": {str(wage["line"]): "140", str(models[3]["line"]): "saxon_general"},
            "add_model": [{"block": sicily["line"], "model": "saxon_general"}],
            "remove": [models[-1]["line"], gone["line"]],
            "copy_block": [{"block": donor["line"], "faction": "zz_probe"}]}
    p = ch.plan(mod, body)
    check(f"the plan is clean ({len(p.changes)} changes)", not p.errors and p.text)
    check("a faction not in the roster is warned about", any("zz_probe" in w for w in p.warnings))
    res = ch.apply(p)
    ov2 = ch.overview(Mod(root))
    by2 = {t["type"]: t for t in ov2["types"]}
    new_text = (root / "data" / ch.REL).read_text(encoding="latin-1")
    check("the spy's wage changed, keeping its column",
          next(r for r in by2["spy"]["head"] if r["key"] == "wage_base")["value"] == "140"
          and "\nwage_base\t\t140" in new_text.replace("\r", ""))
    s2 = next(b for b in by2["named character"]["blocks"] if b["factions"] == ["sicily"])
    m2 = [r for r in s2["rows"] if r["key"] == "strat_model"]
    check("sicily's slot 3 now draws saxon_general and keeps its label",
          m2[3]["value"] == "saxon_general" and m2[3]["label"] == models[3]["label"])
    check("sicily lost its last strat model and gained saxon_general after its others, labelled Custom",
          len(m2) == len(models) and m2[-1]["value"] == "saxon_general" and "(Custom)" in m2[-1]["label"])
    facs = [b["factions"] for b in by2["spy"]["blocks"]]
    check("the spy's last block is gone, and zz_probe has a copy of the first, at the end",
          gone["factions"] not in facs and facs[-1] == ["zz_probe"]
          and [r["value"] for r in by2["spy"]["blocks"][-1]["rows"]] == [r["value"] for r in donor["rows"]])
    after = (root / "data" / ch.REL).read_bytes()
    check("everything above the first edit is byte for byte what it was",
          after.startswith(before[:before.index(b"faction\t\t\tsicily")]))
    stale = ch.plan(mod, dict(body, sig="0" * 16))
    check("an edit made against an older copy is refused", any("changed on disk" in e for e in stale.errors))
    for label, bad in (("a wage that is not a whole number", {"values": {str(wage["line"]): "lots"}}),
                       ("a copy for a faction the type already has",
                        {"copy_block": [{"block": donor["line"], "faction": donor["factions"][0]}]}),
                       ("removing a block's only strat model", {"remove": [next(
                           r["line"] for r in by2["spy"]["blocks"][0]["rows"] if r["key"] == "strat_model")]})):
        check(f"{label} is refused", ch.plan(mod, dict(bad, sig=ov2["sig"])).errors)
    warn = ch.plan(mod, {"sig": ov2["sig"], "add_model": [{"block": s2["line"], "model": "no_such_model"}]})
    check("a strat model descr_model_strat.txt lacks is warned about",
          not warn.errors and any("no_such_model" in w for w in warn.warnings))
    transfer.undo(res["id"])
    check("one undo puts the file back byte for byte", (root / "data" / ch.REL).read_bytes() == before)

print("\n4) the Strat models card")
if (ROC / "data" / ch.REL).is_file():
    from unittransfer import stratmap
    mod = Mod(ROC)
    e = next(x for x in stratmap.strat_file(mod).entries if ch.users_of(mod, x.name))
    got = ch.users_of(mod, e.name)
    check(f"{e.name}: its characters, each a block the Agents and generals screen opens",
          got and all(u["key"].startswith("block/") for u in got))

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
