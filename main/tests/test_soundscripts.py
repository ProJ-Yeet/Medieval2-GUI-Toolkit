"""The sound scripts, ``descr_sounds_*.txt`` - Phase 47b.

Four claims under test:

    the files come back     parse_text(t).to_text() == t for every script on
                            every installed mod, every event inside a block
    the lines are typed     DEFAULT:, BANK:, source, settings and selectors are
                            told apart, and an attribute is a number, a flag or
                            pref and a word
    an edit is a splice     an event, a DEFAULT:, a setting or a selector's
                            values change one line or one event, comments kept
    the save is undoable    backup byte for byte, a log record, undo restores

    python -m tests.test_soundscripts
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod, _tmp  # noqa: E402
from unittransfer import config, keyblock as kb, soundscripts as ss  # noqa: E402
from unittransfer.mod import Mod  # noqa: E402
from unittransfer.transfer import undo  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return cond


def use_temp_config():
    tmp = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
    config.CONFIG_DIR = tmp
    config.BACKUP_DIR = tmp / "backups"
    config.SETTINGS_PATH = tmp / "settings.json"
    config.LOG_PATH = tmp / "transfers.json"


W = ("DEFAULT: 3d mindist 3 priority 90 volume -10 probability 1\r\n"
     "required_samples_cutoff 10\r\n"
     "\r\n"
     "event WEAPON_SAP_DIGGING mindist 2 volume 0\r\n"
     "\tfolder data/sounds/SFX/Mining_Tunnel\r\n"
     "\tSiege_Mining_Tunnel_Digging_04\r\n"
     "end\r\n"
     "\r\n"
     "BANK: weapon_hit\r\n"
     ";##### Creatures\r\n"
     "\tunit Ents:sec, Harad Mumakil:sec\r\n"
     "\t\thit building, flesh\r\n"
     "\t\t\tevent volume -5 mindist 4 priority 130\r\n"
     "\t\t\t\tfolder data/sounds/SFX/Melee/Elephant\r\n"
     "\t\t\t\tKick_Body_Low\r\n"
     "\t\t\t\tPunch_Body_1 probability .2\r\n"
     "\t\t\tend\r\n"
     "\triver_max_dist_apart 250\t; maximum distance (metres)\r\n"
     "\t\t\tlooped\r\n"
     "\t\t\t\tevent looped\r\n"
     "\t\t\t\t\tfolder data/sounds/SFX/Wind\r\n"
     "\t\t\t\tend\r\n")

print("\n1  a script written here")
sc = ss.parse_text("descr_sounds_weapons.txt", W)
check("it comes back byte for byte", sc.to_text() == W)
kinds = [(it.kind, it.key) for it in sc.root.items]
check("DEFAULT: and a file-level setting are the file's",
      kinds == [("default", "DEFAULT:"), ("setting", "required_samples_cutoff")])
named = [n for n in sc.nodes if n.kind == "named"]
check("an event at the top with a name is a block of its own",
      [n.value for n in named] == ["WEAPON_SAP_DIGGING"]
      and sc.events[0].name == "WEAPON_SAP_DIGGING")
bank = next(n for n in sc.nodes if n.kind == "bank")
unit = next(n for n in sc.nodes if n.kw == "unit")
hit = next(n for n in sc.nodes if n.kw == "hit")
check("selectors nest under their bank and each other",
      unit.parent is bank and hit.parent is unit
      and hit.path() == ["BANK: weapon_hit", "unit Ents:sec, Harad Mumakil:sec",
                         "hit building, flesh"])
check("an event under a selector has no name, and belongs to it",
      sc.events[1].name == "" and sc.events[1] in hit.events)
check("a setting belongs to the block left of it: level with unit, so the bank's",
      [(it.key, it.value) for it in bank.items] == [("river_max_dist_apart", "250")]
      and not unit.items)
check("a selector with nothing after it (looped) is still a selector",
      any(n.kw == "looped" and n.kind == "selector" for n in sc.nodes))
pairs, bad = ss._pairs("WEAPON_SAP_DIGGING mindist 2 3d streamed pref SFX loudness")
check("attributes are typed: number, flag, pref and a word, and an unknown one",
      pairs == [("mindist", "2"), ("3d", ""), ("streamed", ""), ("pref", "SFX"),
                ("loudness", "?")] and not bad)
check("a number key with no number after it is a problem",
      ss._pairs("volume priority 3")[1] == ["volume needs a number after it"])


print("\n2  every installed mod")
seen = 0
for root in _realmod.installed():
    mod = Mod(root)
    for f in ss.files(mod):
        seen += 1
        t = kb.read_text(Path(mod.data) / f["rel"], ss.ENCODING)
        s2 = ss.parse_text(f["rel"], t)
        owned = sum(len(n.events) for n in s2.nodes)
        check(f"{root.name} {f['id']}: byte for byte, {len(s2.events)} events in "
              f"blocks, no warnings",
              s2.to_text() == t and owned == len(s2.events) and not s2.warnings)
check("the family was found (31 scripts and music types on each mod)", seen >= 32)


print("\n3  plan, apply and undo on a copy of a real mod")
use_temp_config()
src = _realmod.pick("Divide_and_Conquer_EUR", need="descr_sounds_weapons.txt")
tmp = Path(_tmp.mkdtemp(prefix="ut_sscr_"))
dest = tmp / src.name
(dest / "data").mkdir(parents=True)
for p in (src / "data").glob("descr_sounds_*.txt"):
    shutil.copy2(p, dest / "data" / p.name)
(dest / "data" / "descr_sounds_weapons.txt").write_bytes(W.encode("latin-1"))
mod = Mod(dest)
rel = "descr_sounds_weapons.txt"
before = (dest / "data" / rel).read_bytes()
ov = ss.overview(mod, "weapons")
root_n = ov["nodes"][0]
dflt, cut = root_n["items"]
hit_n = next(n for n in ov["nodes"] if n["kw"] == "hit")
bank_n = next(n for n in ov["nodes"] if n["kind"] == "bank")
river = bank_n["items"][0]
ev = hit_n["events"][0]
sap = next(n for n in ov["nodes"] if n["kind"] == "named")
op = lambda **k: k  # noqa: E731
pl = ss.plan(mod, {"file": "weapons", "ops": [
    op(op="default", at=dflt["at"], head=dflt["head_text"],
       value="3d mindist 3 priority 95 volume -10 probability 1"),
    op(op="setting", at=river["at"], head=river["head_text"], value="300"),
    op(op="event", at=ev["at"], head=ev["head_text"], attrs="volume -8 mindist 4 priority 130",
       lines=ev["lines"] + ["Punch_Body_2"]),
    op(op="rename", at=hit_n["head"], head=hit_n["head_text"], value="building, flesh, wood"),
    op(op="duplicate", at=sap["head"], head=sap["head_text"], value="WEAPON_SAP_COLLAPSE"),
]})
check("five edits of five kinds plan together", pl.payload()["ok"] and len(pl.changes) == 5)
want = (W.replace("priority 90 volume", "priority 95 volume")
         .replace("river_max_dist_apart 250\t;", "river_max_dist_apart 300\t;")
         .replace("event volume -5 mindist 4", "event volume -8 mindist 4")
         .replace("Punch_Body_1 probability .2\r\n",
                  "Punch_Body_1 probability .2\r\n\t\t\t\tPunch_Body_2\r\n")
         .replace("hit building, flesh\r\n", "hit building, flesh, wood\r\n")
         .replace("end\r\n\r\nBANK:", "end\r\nevent WEAPON_SAP_COLLAPSE mindist 2 volume 0\r\n"
                  "\tfolder data/sounds/SFX/Mining_Tunnel\r\n"
                  "\tSiege_Mining_Tunnel_Digging_04\r\nend\r\n\r\nBANK:"))
check("  and change exactly those lines: the comment after the setting kept, "
      "the copy straight after its source", pl.text == want)
res = ss.apply(pl)
check("apply writes it, backs the old file up, logs its own mode",
      (dest / "data" / rel).read_bytes() == want.encode("latin-1")
      and (Path(res["backup_root"]) / "data" / rel).read_bytes() == before
      and res["mode"] == "soundscripts")
undo(res["id"])
check("undo puts the file back byte for byte", (dest / "data" / rel).read_bytes() == before)

bad = ss.plan(mod, {"file": "weapons", "ops": [
    op(op="setting", at=cut["at"], head=cut["head_text"], value="ten")]})
check("a setting's value is a number", not bad.payload()["ok"])
bad = ss.plan(mod, {"file": "weapons", "ops": [
    op(op="default", at=dflt["at"], head=dflt["head_text"], value="3d volume loud")]})
check("a number key followed by a word is refused", not bad.payload()["ok"])
warn = ss.plan(mod, {"file": "weapons", "ops": [
    op(op="event", at=ev["at"], head=ev["head_text"], attrs="volume -5 shimmer",
       lines=ev["lines"])]})
check("an attribute no script writes is a warning, not a refusal",
      warn.payload()["ok"] and any("shimmer" in w for w in warn.warnings))
warn = ss.plan(mod, {"file": "weapons", "ops": [
    op(op="rename", at=hit_n["head"], head=hit_n["head_text"], value="building, jelly")]})
check("a selector value no script in the mod names is a warning",
      warn.payload()["ok"] and any("jelly" in w for w in warn.warnings))
bad = ss.plan(mod, {"file": "weapons", "ops": [
    op(op="remove", at=hit_n["head"], head=hit_n["head_text"])]})
check("a selector's block is not removed: its extent is not certain",
      not bad.payload()["ok"] and "indentation" in bad.errors[0])
bad = ss.plan(mod, {"file": "weapons", "ops": [
    op(op="rename", at=bank_n["head"], head="BANK: weapon_hit", value="x")]})
check("a bank is not renamed", not bad.payload()["ok"])
bad = ss.plan(mod, {"file": "weapons", "ops": [
    op(op="duplicate", at=sap["head"], head=sap["head_text"], value="WEAPON_SAP_DIGGING")]})
check("a copy under a name already taken is refused", not bad.payload()["ok"])
rm = ss.plan(mod, {"file": "weapons", "ops": [
    op(op="remove", at=sap["head"], head=sap["head_text"])]})
check("removing a named event takes event to end and warns who loses it",
      rm.payload()["ok"] and "WEAPON_SAP" not in rm.text and rm.warnings)
check("music types is shown, not written",
      not ss.plan(mod, {"file": "music_types", "ops": []}).payload()["ok"])
check("a file name that is not a script's is refused",
      not ss.plan(mod, {"file": "../x", "ops": []}).payload()["ok"])

acc = next(f for f in ss.files(mod) if f["id"] == "accents")
ova = ss.overview(mod, "accents")
fl = [n for n in ova["nodes"] if n["kw"] == "factions" and n["value"]]
if len(fl) >= 2:
    other = ss._values(fl[1]["value"])[0]
    w2 = ss.plan(mod, {"file": "accents", "ops": [
        op(op="rename", at=fl[0]["head"], head=fl[0]["head_text"],
           value=fl[0]["value"].rstrip(", ") + ", " + other)]})
    check("a faction put under a second accent is said to be under the first too",
          w2.payload()["ok"] and any("also under" in w for w in w2.warnings))

print(f"\n{sum(ok)}/{len(ok)} checks"
      + (" - ALL PASSED" if all(ok) else f" - {ok.count(False)} FAILED"))
sys.exit(0 if all(ok) else 1)
