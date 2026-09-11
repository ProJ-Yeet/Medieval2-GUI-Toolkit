"""The raw text editor: the bytes, the path guard, the save and its undo (21, D11).

Run:  python -m tests.test_rawtext

The one promise the module makes is that a raw save is byte-exact outside the
lines it changed, in whatever encoding and line endings the file already had.
So most of this suite is that promise, over the shapes real game files come in:
CRLF, LF, a file that mixes them (Third Age Reforged's descr_projectile.txt is
3,353 CRLF lines and five lone LFs), no final newline, UTF-16 with its mark,
UTF-8 with and without one, and Latin-1 bytes that are not UTF-8 at all. Then
the write itself, through the toolkit's own undo, and every text file in every
installed mod read and put back unchanged.
"""
import random
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests import _tmp  # noqa: E402
from unittransfer import cleaner, config, rawtext as rt, transfer   # noqa: E402
from unittransfer.mod import Mod                                     # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return bool(cond)


def roundtrip(raw: bytes, edit=None) -> bytes:
    """What a save of ``raw`` writes, with ``edit`` applied to the page's view."""
    codec = rt.sniff(raw)
    text = rt.decode(raw, codec)
    view = text.replace("\r\n", "\n").replace("\r", "\n")
    if edit:
        view = edit(view)
    out, _ = rt.splice(text, view)
    return rt.encode(out, codec)


def lines_of(raw: bytes):
    return raw.split(b"\n")


print("=== 1. the line endings stay the file's ===")
SHAPES = {
    "CRLF": b"a\r\nb\r\nc\r\n",
    "LF": b"a\nb\nc\n",
    "no final newline": b"a\r\nb\r\nc",
    "mixed": b"a\r\nb\nc\r\nd\r\n",
    "lone CR": b"a\rb\r\nc\r\n",
    "empty": b"",
    "one line": b"only",
}
for name, raw in SHAPES.items():
    check(f"{name}: unchanged is byte for byte", roundtrip(raw) == raw)


def upper_line(i):
    def f(view):
        ls = view.split("\n")
        if i < len(ls):
            ls[i] = ls[i].upper() + "!"
        return "\n".join(ls)
    return f


got = roundtrip(SHAPES["mixed"], upper_line(1))
check("mixed: an edited LF line keeps its LF, every CRLF line keeps its CRLF",
      got == b"a\r\nB!\nc\r\nd\r\n")
got = roundtrip(SHAPES["no final newline"], lambda v: v + "\nd")
check("no final newline: a line added at the end gets the file's ending before it"
      " and none after", got == b"a\r\nb\r\nc\r\nd")
got = roundtrip(SHAPES["CRLF"], lambda v: v.replace("b\n", ""))
check("a deleted line takes its own ending with it", got == b"a\r\nc\r\n")
got = roundtrip(SHAPES["LF"], lambda v: v.replace("b", "b\nnew"))
check("an inserted line in an LF file is LF", got == b"a\nb\nnew\nc\n")
got = roundtrip(b"a\r\nb\r\n", lambda v: v.rstrip("\n"))
check("taking the final newline away is honoured", got == b"a\r\nb")

# fuzz: random edits to a mixed file never change a line nobody touched
rnd = random.Random(21)
base = [f"line {i}".encode() for i in range(200)]
ends = [rnd.choice([b"\r\n", b"\r\n", b"\r\n", b"\n"]) for _ in base]
raw = b"".join(l + e for l, e in zip(base, ends))
bad = 0
for trial in range(60):
    pick = sorted(rnd.sample(range(200), 3))
    def edit(view, pick=pick):
        ls = view.split("\n")
        for i in pick:
            ls[i] = ls[i] + " edited"
        return "\n".join(ls)
    out = roundtrip(raw, edit)
    olds = raw.split(b"\n")
    news = out.split(b"\n")
    for i in range(200):
        if i in pick:
            continue
        if olds[i] != news[i]:
            bad += 1
            break
check(f"60 random three-line edits to a mixed-ending file: no untouched line moved "
      f"({bad} did)", bad == 0)

big = b"".join(f"row {i}\t{i * 7}\r\n".encode() for i in range(60000))
started = time.perf_counter()
out = roundtrip(big, upper_line(30000))
ms = (time.perf_counter() - started) * 1000
check(f"a one-line edit in a 60,000-line file is spliced in {ms:.0f} ms",
      ms < 3000 and out.count(b"\r\n") == 60000 and b"ROW 30000" in out)


print("\n=== 2. the encoding is the file's ===")
CODECS = {
    "UTF-16 LE with BOM": "\ufeff{SICILY}\tSicilia \u00e8\r\n".encode("utf-16-le"),
    "UTF-8 with BOM": b"\xef\xbb\xbffaction sicily\r\n",
    "UTF-8 without": "Ad\u00fbn\u00e2im\r\n".encode("utf-8"),
    "Latin-1": b"Ad\xfbn\xe2im\r\n",
}
for name, raw in CODECS.items():
    codec = rt.sniff(raw)
    check(f"{name} is read as {codec.label} and written back unchanged",
          codec.label.startswith(name.split(" with")[0].split(" without")[0].strip())
          and roundtrip(raw) == raw)
got = roundtrip(CODECS["UTF-16 LE with BOM"], lambda v: v.replace("Sicilia", "Trinacria"))
check("a UTF-16 edit keeps the mark and the byte order",
      got.startswith(b"\xff\xfe") and got.decode("utf-16-le").startswith("\ufeff{SICILY}\tTrinacria"))
check("Latin-1 bytes that are not UTF-8 are not mistaken for it",
      rt.sniff(CODECS["Latin-1"]).name == "latin-1")


print("\n=== 3. the path guard ===")
for rel, want in [("export_descr_unit.txt", True),
                  ("text/expanded.txt", True),
                  ("world/maps/base/descr_regions.txt", True),
                  ("world/maps/campaign/imperial_campaign/descr_strat.txt", True),
                  ("world/maps/campaign/custom/Fellowship/descr_faction_movies.xml", True),
                  ("unit_models/battle_models.modeldb", False),
                  ("../mods.txt", False),
                  ("world/maps/base/../../../x.txt", False),
                  ("C:/Windows/win.ini", False),
                  ("/etc/passwd.txt", False),
                  ("animations/descr_skeleton_extra.txt", False),
                  ("export_descr_unit.bak", False)]:
    check(f"{rel!r} is {'allowed' if want else 'refused'}", rt._allowed(rel) == want)


print("\n=== 4. read, plan, write, undo - on a synthetic mod ===")
tmp = Path(_tmp.mkdtemp(prefix="ut_rawtext_"))
root = tmp / "RawMod"
data = root / "data"
CAMP = "world/maps/campaign/imperial_campaign"
files = {
    "descr_sm_factions.txt": b"faction\tsicily\r\nculture\tsouthern_european\r\n",
    "export_descr_unit.txt": b"type Spearmen\r\ndictionary Spearmen\r\nownership sicily\r\n",
    f"{CAMP}/descr_strat.txt": (
        b"campaign\timperial_campaign\r\nplayable\r\n\tsicily\r\nend\r\n"
        b"unlockable\r\nend\r\nnonplayable\r\nend\r\n\r\n"
        b"faction\tsicily, balanced smith\r\ndenari\t5000\r\n"
        b"character\tRoger, named character, male, leader, age 40, x 10, y 10\r\n"),
    "descr_projectile.txt": b"a\r\nb\nc\r\n",
    "unit_models/battle_models.modeldb": b"22 serialization::archive 3 0 0 0 0 1 0\n",
}
for rel, raw in files.items():
    (data / rel).parent.mkdir(parents=True, exist_ok=True)
    (data / rel).write_bytes(raw)
exp = data / "text" / "expanded.txt"
exp.parent.mkdir(parents=True, exist_ok=True)
exp.write_bytes("\ufeff{SICILY}\tKingdom of Sicily\r\n".encode("utf-16-le"))
cleaner.refresh_strings_bin(root, "data/text/expanded.txt.strings.bin")
mod = Mod(root)

listing = rt.files(mod)
rels = [f["rel"] for g in listing["groups"] for f in g["files"]]
check(f"the listing has every text file and no modeldb ({len(rels)})",
      "descr_projectile.txt" in rels and f"{CAMP}/descr_strat.txt" in rels
      and "text/expanded.txt" in rels and not any(r.endswith(".modeldb") for r in rels))
check("the campaign's files come first, under the campaign's name",
      listing["groups"][0]["label"] == "Campaign: imperial_campaign")
screens = {f["rel"]: f["screen"] for g in listing["groups"] for f in g["files"]}
check("each file names the screen that edits it properly",
      screens["descr_sm_factions.txt"] == "Factions"
      and screens["export_descr_unit.txt"] == "Unit Editor"
      and screens[f"{CAMP}/descr_strat.txt"] == "Campaign Map"
      and screens["text/expanded.txt"] == "Strings")

doc = rt.read(mod, "descr_projectile.txt")
check("a mixed file reads with \\n only and says it is mixed",
      doc["text"] == "a\nb\nc\n" and doc["mixed"] and not doc["readonly"])
try:
    rt.read(mod, "../outside.txt")
    check("a path out of data/ is refused on read", False)
except rt.RawError:
    check("a path out of data/ is refused on read", True)

# a save whose signature is old is refused - somebody else wrote in between
p = rt.plan(mod, {"rel": "descr_projectile.txt", "sig": "0" * 40, "text": "x"})
check("a stale signature is refused, and says to reload",
      p.errors and "changed on disk" in p.errors[0])
p = rt.plan(mod, {"rel": "descr_projectile.txt", "sig": doc["sig"], "text": doc["text"]})
check("saving what was read is 'nothing to change'", p.errors == ["nothing to change"])
p = rt.plan(mod, {"rel": "descr_projectile.txt", "sig": doc["sig"],
                  "text": "a\nb \u2603\nc\n"})
check("a character the file's encoding cannot hold is refused with its line",
      p.errors and p.errors[0].startswith("line 2"))

# the reader's view: descr_strat before and after
sdoc = rt.read(mod, f"{CAMP}/descr_strat.txt")
p = rt.plan(mod, {"rel": f"{CAMP}/descr_strat.txt", "sig": sdoc["sig"],
                  "text": sdoc["text"].replace("age 40, ", "")})
check("a strat edit the campaign reader objects to is warned about, not refused",
      not p.errors and any("no age" in w for w in p.warnings))
check("…and the plan names the one line it changes",
      p.counts == {"changed": 1, "added": 0, "removed": 0} and p.hunks[0]["at"] == 12)

before = {x.relative_to(root).as_posix(): x.read_bytes()
          for x in root.rglob("*") if x.is_file()}

p = rt.plan(mod, {"rel": "descr_projectile.txt", "sig": doc["sig"],
                  "text": "a\nB\nc\n"})
res = rt.apply(p)
check("the write keeps the edited line's own LF and the others' CRLF",
      (data / "descr_projectile.txt").read_bytes() == b"a\r\nB\nc\r\n")
entry = next(e for e in config.load_log() if e.get("id") == res["id"])
check("the log entry is a raw edit, with its counts",
      entry["mode"] == "rawtext" and entry["unit_type"] == "descr_projectile.txt"
      and entry["options"]["counts"]["changed"] == 1)

edoc = rt.read(mod, "text/expanded.txt")
bin_before = (data / "text/expanded.txt.strings.bin").read_bytes()
p = rt.plan(mod, {"rel": "text/expanded.txt", "sig": edoc["sig"],
                  "text": edoc["text"].replace("Kingdom of Sicily", "Regno di Sicilia")})
check("a text/ save says the .strings.bin is recompiled",
      any(".strings.bin" in n for n in p.notes))
res2 = rt.apply(p)
check("…and it is: the compiled file changed with the text",
      res2["strings_bin"].get("rebuilt")
      and (data / "text/expanded.txt.strings.bin").read_bytes() != bin_before)
check("the UTF-16 file kept its mark",
      (data / "text/expanded.txt").read_bytes().startswith(b"\xff\xfe"))

for tid in (res2["id"], res["id"]):
    transfer.undo(tid)
    config.update_log(tid, note="test_rawtext - synthetic mod, discarded")
after = {x.relative_to(root).as_posix(): x.read_bytes()
         for x in root.rglob("*") if x.is_file()}
check("undo restored every file byte for byte, the compiled one included",
      all(after.get(k) == v for k, v in before.items()))
extra = sorted(set(after) - set(before))
check(f"undo left no file behind{': ' + ', '.join(extra) if extra else ''}", not extra)
shutil.rmtree(tmp, ignore_errors=True)


print("\n=== 5. every text file in every installed mod ===")
from tests import _realmod                                           # noqa: E402

mods = _realmod.installed()
if not mods:
    print("  [skip] no installed mod")
for path in mods:
    real = Mod(path)
    started = time.perf_counter()
    lst = rt.files(real)
    ms = (time.perf_counter() - started) * 1000
    check(f"{path.name}: {lst['count']} files listed in {ms:.0f} ms, "
          f"{len(lst['groups'])} groups", lst["count"] and ms < 2000)
    changed, refused, big = [], [], []
    for g in lst["groups"]:
        for f in g["files"]:
            d = rt.read(real, f["rel"])
            if f["too_big"]:
                big.append(f["rel"])
                continue
            if d["readonly"]:
                refused.append(f["rel"])
                continue
            raw = (real.data / f["rel"]).read_bytes()
            codec = rt.sniff(raw)
            out, _ = rt.splice(rt.decode(raw, codec), d["text"])
            if rt.encode(out, codec) != raw:
                changed.append(f["rel"])
    check(f"  every file read and saved unchanged is byte for byte"
          + (f" (not {changed[:3]})" if changed else ""), not changed)
    check(f"  no file under the size limit is refused"
          + (f" ({refused[:3]})" if refused else ""), not refused)
    check(f"  the one kind too large to open is listed, not hidden ({len(big)})",
          all(f["too_big"] for g in lst["groups"] for f in g["files"]
              if f["rel"] in big))

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
