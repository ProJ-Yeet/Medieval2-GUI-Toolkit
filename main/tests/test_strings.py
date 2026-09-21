"""Strings mode's add and remove, over HTTP - Phase 48.

The backend has taken ``adds`` and ``removes`` since Phase 6; the page only
ever sent ``edits``. This drives the calls the page makes now against a real
server and a throwaway mod holding one tagged archive and one addressed by
position:

    /api/strings/entries -> refused sentences for the untagged one, none for
                            the tagged one
    /api/strings/plan    -> an add and a remove, the count before and after,
                            the tag checks
    /api/strings/apply   -> written, read back, undone byte for byte

    python -m tests.test_strings
"""
import json
import shutil
import sys
import threading
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _realmod, _tmp  # noqa: E402
from unittransfer import config, strings, stringsbin  # noqa: E402
from unittransfer.server import Registry, Handler, _Server  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def post(path, body):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


TAGGED = "text/religions.txt.strings.bin"
BYPOS = "text/battle.txt.strings.bin"
src = _realmod.pick("Divide_and_Conquer_EUR", "ROCSS", need=TAGGED)
if not (src / "data" / BYPOS).exists():
    print("SKIPPED: no archive addressed by position to test against")
    sys.exit(0)

cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"
med2 = Path(_tmp.mkdtemp(prefix="ut_med2_"))
data = med2 / "mods" / "TestMod" / "data"
(data / "text").mkdir(parents=True)
for rel in ("export_descr_unit.txt", "text/export_units.txt", TAGGED, BYPOS):
    if (src / "data" / rel).exists():
        shutil.copy2(src / "data" / rel, data / rel)
config.save_settings(med2_root=str(med2))
before = (data / TAGGED).read_bytes()
bypos_before = (data / BYPOS).read_bytes()

Handler.registry = Registry(cfg / "icons")
httpd = _Server(("127.0.0.1", 0), Handler)
BASE = f"http://127.0.0.1:{httpd.server_address[1]}"
threading.Thread(target=httpd.serve_forever, daemon=True).start()

try:
    files = get("/api/strings?mod=TestMod")["files"]
    rel_t = next(f["rel"] for f in files if f["rel"].endswith("religions.txt.strings.bin"))
    rel_p = next(f["rel"] for f in files if f["rel"].endswith("battle.txt.strings.bin"))

    print("\n1  what the page is told before anyone asks")
    et = get(f"/api/strings/entries?mod=TestMod&file={rel_t}&limit=0")
    ep = get(f"/api/strings/entries?mod=TestMod&file={rel_p}&limit=5")
    check("a tagged archive refuses nothing", et["tagged"] and et["refused"] == {})
    check("one addressed by position says both refusals, in the plan's own words",
          not ep["tagged"] and ep["refused"] == {"add": strings.NO_ADD,
                                                 "remove": strings.NO_REMOVE})

    print("\n2  add and remove on the tagged archive")
    first = et["rows"][0]
    body = {"mod": "TestMod", "file": rel_t,
            "adds": [{"tag": "IRON_HILLS_FAITH", "value": "The faith of the Iron Hills"}],
            "removes": [first["id"]]}
    pl = post("/api/strings/plan", body)["plan"]
    check("one add and one remove plan cleanly, count unchanged",
          pl["ok"] and pl["before"] == pl["after"] == et["count"]
          and "+ IRON_HILLS_FAITH: The faith of the Iron Hills" in pl["changes"]
          and f"- {first['tag']}" in pl["changes"])
    only_add = post("/api/strings/plan", {"mod": "TestMod", "file": rel_t,
                                         "adds": body["adds"]})["plan"]
    check("an add alone moves the count by one", only_add["after"] == et["count"] + 1)
    if et["index"]:
        check("  and says the trailing tag index is carried through",
              any("trailing tag index" in w for w in only_add["warnings"]))
    for tag, why in [("", "needs a tag"), ("TWO WORDS", "no spaces or braces"),
                     ("{BRACED}", "no spaces or braces"), (first["tag"], "already has")]:
        r = post("/api/strings/plan", {"mod": "TestMod", "file": rel_t,
                                       "adds": [{"tag": tag, "value": "x"}]})
        check(f"a new tag {tag!r} is refused ({why})",
              not r["plan"]["ok"] and why in r.get("error", ""))

    res = post("/api/strings/apply", body)
    check("apply writes it", "record" in res and not res.get("error"))
    sb = stringsbin.read(data / TAGGED)
    check("  the new entry is in the archive and the removed one is not",
          sb.index_of("IRON_HILLS_FAITH") >= 0 and sb.index_of(first["tag"]) < 0
          and sb.values[sb.index_of("IRON_HILLS_FAITH")] == "The faith of the Iron Hills")
    back = get(f"/api/strings/entries?mod=TestMod&file={rel_t}&q=IRON_HILLS")
    check("  and the page is served it back", [r["tag"] for r in back["rows"]]
          == ["IRON_HILLS_FAITH"])
    post("/api/undo", {"id": res["record"]["id"]})
    check("undo puts the archive back byte for byte", (data / TAGGED).read_bytes() == before)

    print("\n3  the archive addressed by position")
    r = post("/api/strings/plan", {"mod": "TestMod", "file": rel_p,
                                   "adds": [{"tag": "X", "value": "y"}]})
    check("an add is refused with the sentence the page already showed",
          not r["plan"]["ok"] and r["error"] == strings.NO_ADD)
    r = post("/api/strings/plan", {"mod": "TestMod", "file": rel_p, "removes": ["#0"]})
    check("so is a remove", not r["plan"]["ok"] and r["error"] == strings.NO_REMOVE)
    r = post("/api/strings/apply", {"mod": "TestMod", "file": rel_p, "removes": ["#0"]})
    check("  and apply writes nothing", (data / BYPOS).read_bytes() == bypos_before
          and "record" not in r)
finally:
    httpd.shutdown()

print(f"\n{sum(ok)}/{len(ok)} checks"
      + (" - ALL PASSED" if all(ok) else f" - {ok.count(False)} FAILED"))
sys.exit(0 if all(ok) else 1)
