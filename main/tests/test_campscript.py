"""96f: a campaign's campaign_script.txt, piece by piece.

Run:  python -m tests.test_campscript

A small campaign script, CRLF like the game's: comments, two counters, a
monitor with an ``if`` and a stray ``and`` at column 0 inside it, a
``monitor_conditions``, a ``while``, and the frame. What has to hold:

* **the pieces are the top-level statements**, by keyword nesting and never by
  indent, each with the comment directly above it; the frame is marked;
* **taking pieces out** leaves every other byte as it was and no doubled blank;
* **the save** goes through the raw editor: refused on a stale signature,
  written with a backup, undone byte for byte;
* **a block that never closes** is said, and nothing after it offered.
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests import _tmp  # noqa: E402
from unittransfer import campscript, config, transfer               # noqa: E402
from unittransfer.mod import Mod                                    # noqa: E402

cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
if config.SETTINGS_PATH.is_file():
    shutil.copy2(config.SETTINGS_PATH, cfg / "settings.json")
config.CONFIG_DIR = cfg; config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"; config.LOG_PATH = cfg / "transfers.json"

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


SCRIPT = """; the campaign script
script

; counters
declare_counter seasons
set_counter seasons 0

; the player's turn
monitor_event FactionTurnStart FactionIsLocal
    if I_TurnNumber > 2
and I_TurnNumber < 9
        inc_counter seasons 1
    end_if
end_monitor

monitor_conditions I_TurnNumber = 5
    console_command add_money 500
    terminate_monitor
end_monitor

while I_TurnNumber < 0
end_while

wait_monitors
end_script
"""

tmp = Path(_tmp.mkdtemp(prefix="ut_campscript_"))
home = tmp / "M" / "data" / "world" / "maps" / "campaign" / "imperial_campaign"
home.mkdir(parents=True)
path = home / "campaign_script.txt"
path.write_bytes(SCRIPT.replace("\n", "\r\n").encode("latin-1"))
before = path.read_bytes()
mod = Mod(tmp / "M")

print("\n1) the pieces")
v = campscript.view(mod, "")
ps = v["pieces"]
kinds = [p["kind"] for p in ps]
check("read, no fault", v["have"] and not v["warnings"])
check("the top-level statements, in order",
      kinds == ["declare_counter", "set_counter", "monitor_event", "monitor_conditions",
                "while", "wait_monitors"])
check("the stray `and` at column 0 stays inside its monitor",
      ps[2]["lines"] == 7 and ps[2]["head"].startswith("monitor_event FactionTurnStart"))
check("a comment directly above is the piece's", ps[0]["comment"] == "counters"
      and ps[2]["comment"] == "the player's turn")
check("the frame is marked", ps[-1]["frame"] and not any(p["frame"] for p in ps[:-1]))

print("\n2) taking out")
text = SCRIPT
cut = campscript.without(text, ps, [2, 4])
check("the monitor and the while are gone, the rest is as it was",
      "FactionTurnStart" not in cut and "while" not in cut
      and "monitor_conditions I_TurnNumber = 5" in cut and "wait_monitors" in cut)
check("no doubled blank line is left", "\n\n\n" not in cut)
check("the frame cannot be taken out", "wait_monitors" in campscript.without(text, ps, [5]))

print("\n3) the save")
stale = campscript.plan(mod, {"campaign": "", "sig": "x", "drop": [2]})
check("a stale signature is refused", stale.errors and not stale.data)
p = campscript.plan(mod, {"campaign": "", "sig": v["sig"], "drop": [2]})
check("planned, its first line says what went", not p.errors and "took out 1 piece" in p.changes[0])
res = campscript.apply(p)
after = path.read_bytes()
check("written CRLF, the monitor gone", b"FactionTurnStart" not in after
      and b"\r\n" in after and b"\n" not in after.replace(b"\r\n", b""))
transfer.undo(res["record"]["id"] if "record" in res else res["id"])
check("Undo puts every byte back", path.read_bytes() == before)

print("\n4) a block that never closes")
pieces, warns = campscript.split("script\ndeclare_counter a\nmonitor_event X\n  if Y\nend_monitor\ndeclare_counter b\nend_script")
check("said", warns and "never closed" in warns[0])
check("  and only what came before it offered", [p["kind"] for p in pieces] == ["declare_counter"])

print(f"\n{sum(ok)}/{len(ok)} passed")
sys.exit(0 if all(ok) else 1)
