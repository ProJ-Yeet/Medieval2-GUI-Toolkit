"""Problem reports and ideas through the relay, as the Pfadfinder editor sends them.

Run:  python -m tests.test_report_relay

A local HTTP server stands in for the Cloudflare Worker. What has to hold:

* nothing private leaves: the Windows user name (in paths too), the computer's
  name, e-mail addresses, Steam IDs, IP addresses and the reporter's own words
  are out of every text in the zip; the loopback address stays;
* a long game log is cut to its start, the errors and warnings of the middle,
  and its end;
* the zip carries the words, the screenshots, the page and server logs, the
  transfers, the settings without addresses, a picture of each mod and its
  game log; an idea without logs carries the words alone;
* a report goes to the relay as the toolkit (its user agent), comes back with
  a number that is kept, its answers are read back by that number with the new
  ones counted until seen, and a reply goes to the same report.
"""
import base64
import io
import json
import os
import socket
import sys
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests import _tmp  # noqa: E402
from unittransfer import config, report                          # noqa: E402
from unittransfer.mod import Mod                                 # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


tmp = Path(_tmp.mkdtemp(prefix="ut_report_"))
report.REPORTS = tmp / "reports"
report.SENT = report.REPORTS / "sent.json"
user = os.environ.get("USERNAME") or Path.home().name
pc = os.environ.get("COMPUTERNAME") or socket.gethostname()

print("\n1) scrubbing")
raw = (f"C:\\Users\\{user}\\Downloads\\kit on {pc}, mail me at someone@example.com, "
       f"steam 76561198012345678, from 192.168.1.20 to 127.0.0.1, I am NickName")
s = report.scrub(raw, ["NickName"])
check("the user name is out, paths too", user.lower() not in s.lower() and "C:\\Users\\<user>\\Downloads" in s)
check("the computer's name is out", pc.lower() not in s.lower())
check("e-mail, Steam ID and IP are out",
      "<email>" in s and "<steamid>" in s and "<ip>" in s and "192.168" not in s)
check("the loopback address stays", "127.0.0.1" in s)
check("the reporter's own word is out", "NickName" not in s and "<hidden>" in s)

print("\n2) a long game log")
lines = [f"line {i}" for i in range(2000)]
lines[1000] = "12:00 [data.invalid] [error] could not find unit Foo"
lines[1001] = "12:00 [game.script] [warning] slow"
cut = report.cut_game_log("\n".join(lines), edge=50).splitlines()
check("its start and end whole", cut[0] == "line 0" and cut[-1] == "line 1999")
check("the middle's error and warning kept", any("could not find unit Foo" in ln for ln in cut)
      and any("slow" in ln for ln in cut))
check("the rest of the middle cut", "line 600" not in cut and len(cut) < 120)

print("\n3) the zip")
root = tmp / "mods" / "Kirsi"
(root / "data" / "unit_models").mkdir(parents=True)
(root / "data" / "export_descr_unit.txt").write_text("type a\ndictionary a\n", encoding="latin-1")
(root / "data" / "unit_models" / "battle_models.modeldb").write_text(
    "22 serialization::archive 3 0 0 0 0 1 0 0\n5 blank " + " ".join(["0"] * 39) + "\n", encoding="latin-1")
(root / "logs").mkdir()
(root / "logs" / "system.log.txt").write_text(
    f"12:00 [system.io] [info] mount C:\\Users\\{user}\\game\n12:01 [data.invalid] [error] bad\n", encoding="utf-8")
mod = Mod(root)
png = "data:image/png;base64," + base64.b64encode(b"\x89PNG\r\n\x1a\nfake").decode()
saved = config.load_settings
config.load_settings = lambda: {"report_relay": "", "report_webhook": "https://secret", "report_contact": "me",
                                "med2_root": f"C:\\Users\\{user}\\M2"}
try:
    name, data = report.build("It crashed for NickName", [{"kind": "error", "what": f"C:\\Users\\{user}"}], None,
                              "transfer", kind="bug", contact="Discord: nick", mods=[mod], pictures=[png],
                              hide=["NickName"])
    z = zipfile.ZipFile(io.BytesIO(data))
    names = set(z.namelist())
    check("words, about, screenshot, logs, transfers, settings, the mod and its game log",
          {"report.txt", "about.json", "screenshot_1.png", "page_log.json", "server_log_tail.txt",
           "transfers.json", "settings.json", "mod_Kirsi.txt", "game_log_Kirsi.txt"} <= names)
    every = "".join(z.read(n).decode("utf-8", "replace") for n in names if n.endswith((".txt", ".json")))
    check("no text in it names the user", user.lower() not in every.lower())
    check("  nor the reporter's hidden word", "NickName" not in every)
    sett = json.loads(z.read("settings.json"))
    check("the settings without the addresses and the contact",
          "report_webhook" not in sett and "report_contact" not in sett and "med2_root" in sett)
    check("the mod's picture names its files", "EDU" in z.read("mod_Kirsi.txt").decode())
    check("the game log rides along", "[error] bad" in z.read("game_log_Kirsi.txt").decode())
    _n, idea = report.build("Add a map of rivers", [], None, "", kind="idea", logs=False)
    check("an idea without logs is the words alone",
          set(zipfile.ZipFile(io.BytesIO(idea)).namelist()) == {"report.txt", "about.json"})
    shown = report.show(data)
    check("Show what is sent lists each file with its text",
          any(f["name"] == "report.txt" and "Discord: nick" in f["text"] for f in shown))
finally:
    config.load_settings = saved

print("\n4) through the relay")
got = []
COMMENTS = []


class Relay(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        got.append((self.path, self.headers.get("User-Agent"), body))
        if self.path == "/":
            out = {"id": "R-20261103-ABC123", "issue": 7}
        elif self.path == "/answers":
            out = {"answers": {"R-20261103-ABC123": {"issue": 7, "state": "closed", "reason": "completed",
                                                     "messages": COMMENTS}}}
        else:
            COMMENTS.append({"from": "you", "text": body["message"], "at": ""})
            out = {"ok": True}
        raw = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


srv = HTTPServer(("127.0.0.1", 0), Relay)
threading.Thread(target=srv.serve_forever, daemon=True).start()
report.RELAY = f"http://127.0.0.1:{srv.server_address[1]}"
config.load_settings = lambda: {}
try:
    check("the relay counts as an address", report.can_send() and report.relay() == report.RELAY)
    out = report.send_relay(data, "It crashed for NickName", "bug", "Discord: nick", "transfer", ["Kirsi"], ["NickName"])
    path, agent, body = got[-1]
    check("sent as the toolkit", agent.startswith("M2-GUI-Kit/") and path == "/")
    check("  with the zip, the kind and the scrubbed words",
          base64.b64decode(body["zip"]) == data and body["kind"] == "bug" and "NickName" not in body["message"])
    check("its number comes back and is kept",
          out["id"] == "R-20261103-ABC123" and report.sent_list()[0]["issue"] == 7)
    COMMENTS.append({"from": "author", "text": "Fixed in the next build", "at": "2026-11-03T10:00:00Z"})
    a = report.answers()
    check("the answer is read back by number, one new", a[0]["new"] == 1 and a[0]["state"] == "closed"
          and got[-1][2]["reports"] == [{"id": "R-20261103-ABC123", "issue": 7}])
    report.mark_seen("R-20261103-ABC123")
    check("  and none new once seen", report.answers()[0]["new"] == 0)
    report.reply("R-20261103-ABC123", "Thanks, it works")
    check("a reply goes to the same report", got[-1][0] == "/reply" and got[-1][2]["issue"] == 7
          and "zip" not in got[-1][2])
    try:
        report.reply("R-20990101-000000", "?")
        refused = False
    except report.ReportError:
        refused = True
    check("a number this copy did not send is refused", refused)
finally:
    config.load_settings = saved
    srv.shutdown()

print(f"\n{sum(ok)}/{len(ok)} passed")
sys.exit(0 if all(ok) else 1)
