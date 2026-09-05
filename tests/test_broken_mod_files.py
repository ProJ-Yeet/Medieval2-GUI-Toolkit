"""A mod whose files are missing or damaged, and what the tool says about it.

Two of these arrived from one person's log on the same evening, both as HTTP 500
with a traceback in the server's log and nothing on screen but "HTTP 500":

  * a folder under ``mods/`` with a ``data/`` in it and no
    ``export_descr_unit.txt`` - which every stock install has four of, because
    the Kingdoms campaigns keep their files inside ``data/packs/*.pack``. The
    toolkit lists them (they look exactly like mods), and the first one is
    alphabetically ``americas``, so it was auto-picked and died before the page
    had finished drawing. Worse, ``/api/mod_files`` - the report whose entire job
    is to say WHICH of a mod's files are missing - died on the same read, so the
    Home card could not explain what the header had just tripped over.

  * a ``battle_models.modeldb`` with one entry whose texture list says it holds
    two and holds one. The reader fell a field out of step and died 400
    characters later on the word ``france``, and the message named that word - a
    word that is perfectly fine where it sits, in a line nobody needs to touch.

So: a mod's own broken or absent file is a :class:`ModDataError` carrying a
sentence, the server answers it with a 409 and that sentence, and the parser's
sentence says which entry, which line, and which number to doubt.

    python -m tests.test_broken_mod_files
"""
import json, sys, threading, urllib.error, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp
from unittransfer import config, modeldb
from unittransfer.mod import Mod, ModDataError
from unittransfer.server import Handler, Registry, _Server

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


def get(path):
    """GET, returning (status, body) - a refusal is an answer here, not a raise."""
    try:
        with urllib.request.urlopen(BASE + path, timeout=60) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def post(path, body):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


# ---- the fixtures ------------------------------------------------------
EDU = ("type\t\t\tPeasant Archers\n"
       "dictionary\t\tPeasant_Archers\n"
       "category\t\tinfantry\n"
       "class\t\t\tmissile\n"
       "soldier\t\t\tpeasant_archer, 48, 0, 1\n"
       "ownership\t\tsicily\n"
       "stat_pri\t\t7, 1, arrow, 120, 30, missile, archery, piercing, none, 25, 1\n")


def entry(name, tex, main_count=1):
    """One modeldb entry: 1 LOD, 1 main texture written out, 0 attach, 1 anim.

    ``main_count`` is written into the file as given - the whole point of the
    fixture is that it can disagree with what actually follows it.
    """
    return (
        f"\n{len(name)} {name} \n1.0 \n1 "
        f"\n{len('m/' + name + '.mesh')} m/{name}.mesh 121 "
        f"\n{main_count} \n4 ever \n{len(tex)} {tex} \n{len(tex)} {tex} \n0 "
        f"\n0 "
        f"\n1 \n5 horse \n3 pri \n3 sec \n0 \n0 "
        f"\n-1 0.0 0.0 0.0 0.0 0.0 0.0 "
    )


BLANK = "\n5 blank " + " ".join(["0"] * 39) + " "
HEADER = "22 serialization::archive 3 0 0 0 0 2 0 0"
GOOD_MDB = HEADER + BLANK + entry("peasant_archer", "unit_models/x/pa.texture")
# the shape from the log: the count says two textures, one is written
BAD_MDB = HEADER + BLANK + entry("peasant_archer", "unit_models/x/pa.texture",
                                 main_count=2)
#: the line the bad count sits on, counted the way a text editor does
BAD_COUNT_LINE = BAD_MDB[:BAD_MDB.index("\n2 \n4 ever")].count("\n") + 2

TEX = "unit_models/x/pa.texture"
SPR = "unit_sprites/pa.spr"


def group(faction, norm_len=None):
    """One faction's four names. ``norm_len`` overrides the normal map's length."""
    return (f"\n{len(faction)} {faction} \n{len(TEX)} {TEX} "
            f"\n{norm_len if norm_len is not None else len(TEX)} {TEX} "
            f"\n{len(SPR)} {SPR} ")


def two_texture_entry(name, norm_len=None):
    """An entry whose texture count of 2 is HONEST and holds two groups.

    BOTET's ``mount_elephant_rocket`` reduced to its bones: nothing is wrong with
    the count, and one normal map's length is written too long.
    """
    return (f"\n{len(name)} {name} \n1.0 \n1 "
            f"\n{len('m/' + name + '.mesh')} m/{name}.mesh 121 "
            f"\n2 " + group("ever", norm_len) + group("also") +
            f"\n0 "
            f"\n1 \n5 horse \n3 pri \n3 sec \n0 \n0 "
            f"\n-1 0.0 0.0 0.0 0.0 0.0 0.0 ")


#: the same shape with the length written three characters too long, so the name
#: it takes runs off the end of its own line
LONG_LEN = len(TEX) + 3
LONG_MDB = HEADER + BLANK + two_texture_entry("peasant_archer", norm_len=LONG_LEN)
LONG_LINE = LONG_MDB[:LONG_MDB.index(f"\n{LONG_LEN} {TEX}")].count("\n") + 2

med2 = Path(_tmp.mkdtemp(prefix="ut_broken_"))


def make_mod(name, edu=EDU, mdb=GOOD_MDB):
    root = med2 / "mods" / name
    (root / "data" / "unit_models").mkdir(parents=True)
    if edu is not None:
        (root / "data" / "export_descr_unit.txt").write_text(edu, encoding="latin-1")
    if mdb is not None:
        (root / "data" / "unit_models" / "battle_models.modeldb").write_text(
            mdb, encoding="latin-1")
    return root


packed = make_mod("packed_only", edu=None, mdb=None)   # a Kingdoms campaign folder
broken = make_mod("BadModels", mdb=BAD_MDB)
fine = make_mod("GoodMod")

print("== the parser says where it lost the thread ==")
try:
    modeldb.parse_text(BAD_MDB)
    check("a count that does not match its list is refused", False)
except ValueError as e:
    msg = str(e)
    check("a count that does not match its list is refused", True)
    check("it names the entry", "'peasant_archer'" in msg)
    check("it names the count and what really followed it",
          "says it holds 2" in msg and "only 1 read cleanly" in msg)
    check("it gives the line of that count, not of the field it died on",
          f"line {BAD_COUNT_LINE}," in msg)
    check("and never says 'invalid literal' at anyone", "invalid literal" not in msg)
check("the same file with an honest count still parses",
      len(modeldb.parse_text(GOOD_MDB).entries) == 1)

# A wrong length inside a texture list lands the reader in exactly the place a
# wrong count does, so the count is the easy thing to blame and it is the wrong
# thing: told to lower an honest 2, you delete a texture group that was fine.
# The reader WATCHED the length overrun its own line, so that sighting leads.
print("\n== ...and when the count is honest, it says so about the length ==")
try:
    modeldb.parse_text(LONG_MDB)
    check("a length that overruns its own line is refused", False)
except ValueError as e:
    msg = str(e)
    check("a length that overruns its own line is refused", True)
    check("it names the line that length is on, not the line it died on",
          f"line {LONG_LINE} column 1" in msg)
    check("it names the number written there", f"is {LONG_LEN} characters long" in msg)
    check("and measures what the line actually holds",
          f"the rest of that line measures {len(TEX)}" in msg)
    check("it does not send you to delete a group the count honestly holds",
          "texture list says it holds" not in msg)
check("the same entry with an honest length parses",
      len(modeldb.parse_text(HEADER + BLANK + two_texture_entry("peasant_archer"))
          .entries) == 1)

print("\n== a missing file is a sentence, not a traceback ==")
try:
    Mod(packed).edu
    check("a mod with no roster refuses to be read", False)
except ModDataError as e:
    check("a mod with no roster refuses to be read", True)
    check("naming the file", "data/export_descr_unit.txt" in str(e))
    check("and saying what to do about a mod that is still packed",
          "data/packs" in str(e))
check("it is still an OSError and a ValueError, so every best-effort guard "
      "still catches it",
      issubclass(ModDataError, OSError) and issubclass(ModDataError, ValueError))

# the guard pattern used in factions.py and minorfiles.py, verbatim
try:
    units = {u.type for u in Mod(packed).edu.units} or None
except (OSError, AttributeError, ValueError):
    units = None
check("a checker that skips what it cannot read still skips it", units is None)

# ---- and over HTTP, which is where the 500s were -----------------------
cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"
config.save_settings(med2_root=str(med2), run_full_cleaner=False)
Handler.registry = Registry(cfg / "icons")
httpd = _Server(("127.0.0.1", 0), Handler)
BASE = f"http://127.0.0.1:{httpd.server_address[1]}"
threading.Thread(target=httpd.serve_forever, daemon=True).start()

try:
    print("\n== over HTTP, which is where the 500s were ==")
    code, body = get("/api/units?mod=packed_only")
    check("a mod with no roster is refused, not a 500", code == 409)
    check("and the refusal carries the sentence",
          "export_descr_unit.txt" in (body.get("error") or ""))

    code, body = get("/api/mod_files?mod=packed_only")
    check("the readiness report itself still answers", code == 200)
    roster = next(f for f in body["files"] if f["rel"] == "export_descr_unit.txt")
    check("and says the roster is the thing that is missing",
          roster["state"] == "missing")
    check("so the card can grey out the modules that need it",
          not body["modules"]["transfer"]["ready"]
          and not body["modules"]["edit"]["ready"])
    check("a mod that has its files is still ready",
          get("/api/mod_files?mod=GoodMod")[1]["modules"]["edit"]["ready"])

    code, body = post("/api/eop_dirs", {"mod": "packed_only"})
    check("the EOP panel still lists folders for it", code == 200 and "dirs" in body)
    check("with the reason in place of the two counts it cannot have",
          "export_descr_unit.txt" in (body.get("note") or ""))

    code, body = get("/api/units?mod=BadModels")
    check("a mod whose modeldb is damaged still lists its units", code == 200)
    code, body = get("/api/edit/unit?mod=BadModels&type=Peasant%20Archers")
    check("opening a unit is refused with the located sentence", code == 409)
    check("naming the file and the entry inside it",
          "battle_models.modeldb" in (body.get("error") or "")
          and "peasant_archer" in (body.get("error") or ""))
finally:
    httpd.shutdown()

print(f"\n{sum(ok)}/{len(ok)} checks - " + ("ALL PASSED" if all(ok) else "SOME FAILED"))
sys.exit(0 if all(ok) else 1)
