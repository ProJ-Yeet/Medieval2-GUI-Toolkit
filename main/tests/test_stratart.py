"""Phase 29 - the strat model viewer, and the art that is there but unreadable.

The viewer was reported as flickering and then turning into a bare cube, or
into nothing. Four faults in a row, each wrong on its own, and this suite holds
each of the four to its own behaviour:

  0. **the root.** ``cas.texture_path`` took the first candidate name that
     existed, and a mod's packer converts each ``.tga`` to a DDS named
     ``<name>.tga.dds`` and truncates the original rather than deleting it. So
     the stub won and the real art, sitting beside it, was never looked at.
     Measured on the installed set: Divide and Conquer has 1,172 zero-byte
     ``.tga`` files under ``data/models_strat`` and Third Age Reforged two,
     and 1,171 of the 1,174 have their real DDS beside them under exactly that
     name. The three that do not are all named ``XXXX...``, which is the
     modders' own mark for a file they have switched off - so every stub that
     was meant to be art has art beside it, and the three that are not are
     exactly the "present and unreadable" case the layers above now report.
  1. **``icons``** answered "there is no such file" and "this file will not
     decode" with the same 1x1 transparent PNG.
  2. **``/model_texture``** therefore answered 200 with a valid picture in it,
     and the viewer's ``onerror`` path never ran.
  3. **``V3_FRAG``** then discarded the model: ``if(base.a < 0.35) discard;``
     is a ``.mesh`` cut-out rule, and against a degenerate sheet it deletes
     every group that names a texture. The survivor is whichever mesh had no
     material at all, which is the cube.

B4 rides along at the end, because it is the same shape of mistake in another
file: ``descr_sm_factions.txt`` is inside the game's ``.pack`` archives, and
every faction was refused with *there is no faction slot called X*, which is a
claim about the faction and is untrue.

The last two faults are in the browser and are checked against the source
rather than a GL context - a shader constant and which format it belongs to.
That is a weaker check than the rest of the suite and is labelled as one.

    python -m tests.test_stratart
"""
import io
import json
import shutil
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image

from unittransfer import cas, config, factions as fac, icons, renames
from unittransfer.mod import Mod
from unittransfer.server import Registry, Handler, _Server
from tests import _realmod, _tmp

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


BASE = ""


def enc(s):
    return urllib.parse.quote(str(s))


def raw(path):
    """``(code, body)`` - a refusal is a result here, not an exception."""
    try:
        with urllib.request.urlopen(BASE + path, timeout=300) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

#: A real, tiny DDS: 4x4 uncompressed BGRA, which Pillow reads. Built rather
#: than shipped so the suite has a picture with genuine bytes in it on a
#: machine with no game installed.
def _dds_bytes(w=4, h=4, rgba=(200, 80, 40, 255)):
    head = bytearray(128)
    head[0:4] = b"DDS "
    head[4:8] = (124).to_bytes(4, "little")          # header size
    head[8:12] = (0x0000100F).to_bytes(4, "little")  # caps|height|width|pitch|pixelformat
    head[12:16] = h.to_bytes(4, "little")
    head[16:20] = w.to_bytes(4, "little")
    head[20:24] = (w * 4).to_bytes(4, "little")      # pitch
    head[76:80] = (32).to_bytes(4, "little")         # pixelformat size
    head[80:84] = (0x41).to_bytes(4, "little")       # RGB | ALPHAPIXELS
    head[88:92] = (32).to_bytes(4, "little")         # bit count
    head[92:96] = (0x00FF0000).to_bytes(4, "little")  # R mask
    head[96:100] = (0x0000FF00).to_bytes(4, "little")  # G
    head[100:104] = (0x000000FF).to_bytes(4, "little")  # B
    head[104:108] = (0xFF000000).to_bytes(4, "little")  # A
    head[108:112] = (0x1000).to_bytes(4, "little")   # caps: texture
    r, g, b, a = rgba
    return bytes(head) + bytes([b, g, r, a]) * (w * h)


# =====================================================================
print("== 0. the root: a stub never wins over the file beside it ==")

sand = Path(_tmp.mkdtemp(prefix="ut_stratart_"))
folder = sand / "residences"
tex = folder / "textures"
tex.mkdir(parents=True)
model = folder / "town.cas"
model.write_bytes(b"not a real cas, and this test never decodes it")

# exactly what a packer leaves: the named .tga at zero bytes, the art beside it
(tex / "walls.tga").write_bytes(b"")
(tex / "walls.tga.dds").write_bytes(_dds_bytes())
# a texture the mod genuinely does not ship
# (nothing written for "gone.tga")
# a texture that is there, has bytes, and is the named file
(tex / "roof.tga").write_bytes(_dds_bytes())
# and the case where the stub is the ONLY thing there
(tex / "lost.tga").write_bytes(b"")

hit = cas.texture_path(model, r"textures\walls.tga")
check("a zero-byte .tga loses to the .tga.dds the packer left beside it",
      hit is not None and hit.name == "walls.tga.dds")
check("...and the winner has bytes in it", hit is not None and hit.stat().st_size > 0)

check("a texture the mod does not ship is still None - that is not a fault",
      cas.texture_path(model, r"textures\gone.tga") is None)

hit = cas.texture_path(model, r"textures\roof.tga")
check("a named file that is readable is still the one chosen",
      hit is not None and hit.name == "roof.tga")

hit = cas.texture_path(model, r"textures\lost.tga")
check("an empty file with nothing beside it IS still returned - present and "
      "unreadable is a fault the layers above report, and absent is not",
      hit is not None and hit.name == "lost.tga")

check("no material at all is None, and always was",
      cas.texture_path(model, "") is None)


# =====================================================================
print("\n== 1. icons: absent and unreadable stop being the same answer ==")

stub, art = tex / "walls.tga", tex / "walls.tga.dds"
empty, gone = tex / "lost.tga", tex / "gone.tga"

check("a file that is not there is not a fault", icons.fault(gone) is None)
check("nor is None itself", icons.fault(None) is None)
why = icons.fault(stub)
check("a zero-byte file with its art beside it says so, and names the file",
      bool(why) and "0 bytes" in why and "walls.tga.dds" in why)
why = icons.fault(empty)
check("a zero-byte file with nothing beside it claims only what was measured",
      bool(why) and "0 bytes" in why and ".dds" not in why)
check("a file that decodes is not a fault", icons.fault(art) is None)

junk = tex / "junk.dds"
junk.write_bytes(b"DDS " + b"\x00" * 400)   # right magic, nothing behind it
why = icons.fault(junk)
check("a file with bytes that Pillow cannot open says it will not decode",
      bool(why) and "will not decode" in why)

cache = icons.IconCache(sand / "cache")
check("absent still comes back as the blank PNG, quietly - mods ship the art "
      "they changed and the unit grids must not get noisier",
      cache.png_bytes(gone)[:8] == PNG_MAGIC and len(cache.png_bytes(gone)) < 200)
check("unreadable comes back blank too when the caller cannot say otherwise",
      len(cache.png_bytes(stub)) < 200)

raised = None
try:
    cache.png_bytes(stub, strict=True)
except icons.ArtUnreadable as e:
    raised = e
check("...and raises ArtUnreadable when the caller can", raised is not None)
check("the exception carries the path and the measured sentence, not a traceback",
      raised is not None and raised.src == stub and "0 bytes" in raised.reason)
raised = None
try:
    cache.png_bytes(gone, strict=True)
except icons.ArtUnreadable as e:
    raised = e
check("strict does NOT turn an absent file into a fault", raised is None)

real = cache.png_bytes(art)
check("a real sheet still decodes to a real PNG",
      real[:8] == PNG_MAGIC and Image.open(io.BytesIO(real)).size == (4, 4))

# the blank stand-in must not outlive the day the file is fixed
before = len(cache.png_bytes(empty))
empty.write_bytes(_dds_bytes(8, 8))
after = cache.png_bytes(empty)
check("the blank served for an unreadable file is never cached, so replacing "
      "the file with a real one is enough to fix it",
      before < 200 and Image.open(io.BytesIO(after)).size == (8, 8))
empty.write_bytes(b"")


# =====================================================================
print("\n== 2. /model_texture answers the fault instead of a picture ==")

cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
config.CONFIG_DIR = cfg
config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"
config.LOG_PATH = cfg / "transfers.json"

med2 = Path(_tmp.mkdtemp(prefix="ut_med2_"))
data = med2 / "mods" / "ArtMod" / "data"
(data / "models_strat" / "textures").mkdir(parents=True)
# The registry warms a mod's light databases before any route runs, so a folder
# with nothing but art in it is refused before /model_texture is reached. An
# empty roster is a real mod as far as this section is concerned, and it keeps
# the section running on a machine with no game on it.
(data / "text").mkdir(parents=True)
(data / "export_descr_unit.txt").write_bytes(b"")
(data / "text" / "export_units.txt").write_bytes(b"")
(data / "models_strat" / "textures" / "walls.tga").write_bytes(b"")
(data / "models_strat" / "textures" / "walls.tga.dds").write_bytes(_dds_bytes(16, 16))
config.save_settings(med2_root=str(med2), run_full_cleaner=False)

Handler.registry = Registry(cfg / "icons")
httpd = _Server(("127.0.0.1", 0), Handler)
BASE = f"http://127.0.0.1:{httpd.server_address[1]}"
threading.Thread(target=httpd.serve_forever, daemon=True).start()

try:
    code, body = raw("/model_texture?mod=ArtMod&rel="
                     + enc("models_strat/textures/walls.tga.dds"))
    check(f"a sheet that decodes is a 200 with a picture in it ({code})",
          code == 200 and Image.open(io.BytesIO(body)).size == (16, 16))

    code, body = raw("/model_texture?mod=ArtMod&rel="
                     + enc("models_strat/textures/walls.tga"))
    said = json.loads(body.decode("utf-8")).get("error", "") if code != 200 else ""
    check(f"a sheet that is there and will not decode is a refusal, not a "
          f"picture ({code})", code == 415)
    check("...carrying the measured sentence, so the panel can say which file "
          "and why", "walls.tga" in said and "0 bytes" in said)
    print(f"          it said: {said[:100]}")

    code, body = raw("/model_texture?mod=ArtMod&rel="
                     + enc("models_strat/textures/nothing_here.tga"))
    check(f"a sheet the mod simply does not ship is STILL a blank 200 - that is "
          f"ordinary, and strict must not change it ({code})",
          code == 200 and body[:8] == PNG_MAGIC and len(body) < 200)

    code, body = raw("/model_texture?mod=ArtMod&rel=../../../../windows/win.ini")
    check("a path climbing out of the mod is still a blank, never the file "
          "and never a 415 naming it",
          code == 200 and body[:8] == PNG_MAGIC and len(body) < 200)
finally:
    httpd.shutdown()


# =====================================================================
print("\n== 3. the cut-out rule belongs to the format it was measured on ==")
print("   (read off the source - there is no GL context in this suite)")

js = (ROOT / "web" / "js" / "viewer3d.js").read_text(encoding="utf-8")
check("the discard is gated rather than unconditional",
      "if(uCutout > 0.5 && base.a < 0.35) discard;" in js
      and "\n  if(base.a < 0.35) discard;" not in js)
check("uCutout is declared in the fragment shader", "uCutout" in js.split("V3_FRAG")[1][:600])
check("and is set from which format is loaded - 0 for a .cas, 1 for a .mesh",
      "gl.uniform1f(v3.loc.uCutout, v3.cas ? 0 : 1);" in js)
check("the viewer refuses a degenerate sheet even on a 200",
      "function v3Degenerate(" in js
      and "const bad = v3Degenerate(img);" in js
      and js.count("const bad = v3Degenerate(img);") == 2)  # .mesh and .cas
check("both 1x1 and wholly-transparent are refused",
      "a placeholder, not a sheet" in js and "transparent everywhere" in js)
check("the failure path asks the server why, and the panel prints it",
      "function v3AskWhy(" in js and "function v3FaultRows(" in js
      and js.count("v3FaultRows()") == 3)       # the definition and both panels


# =====================================================================
print("\n== B4. the file is in a .pack, and nothing said so ==")

bare = Path(_tmp.mkdtemp(prefix="ut_bare_"))
(bare / "data").mkdir()
lonely = Mod(bare)
note = fac.no_file_note(lonely)
check("with no archives anywhere, the sentence claims nothing about packs",
      ".pack" not in note and "descr_sm_factions.txt" in note)

(bare / "packs").mkdir()
check("an EMPTY packs folder is not an archive - Third Age Reforged has one",
      fac.packs_beside(lonely) == [])
(bare / "packs" / "data_0.pack").write_bytes(b"PACK")
note = fac.no_file_note(lonely)
check("with one, the sentence names the archive and says what to do",
      "1 .pack archive" in note and "Unpack it" in note)
check("overview refuses the screen with that same sentence",
      fac.overview(lonely).get("error") == note)

p = renames.plan(lonely, {"subject": "faction", "old": "england", "new": "wessex"})
check("Rename slot refuses with it too, instead of claiming the faction is "
      "not there - one sentence, written in one place",
      p.errors == [note])

# and a name that really is absent must still be told so
(bare / "data" / fac.REL).write_bytes(
    b"faction\tengland, smith\nculture\tnorthern_european\n")
p = renames.plan(lonely, {"subject": "faction", "old": "atlantis", "new": "wessex"})
check("a slot that genuinely is not in a file that IS there keeps the old "
      "sentence", bool(p.errors) and "atlantis" in p.errors[0])


# =====================================================================
print("\n== the sweep: what this changes on the installed mods ==")

mods = _realmod.installed()
if not mods:
    print("  (no mod installed - the sweep is skipped, which is not a failure)")
else:
    for root in mods:
        strat = root / "data" / "models_strat"
        if not strat.is_dir():
            continue
        stubs = [p for p in strat.rglob("*.tga")
                 if p.is_file() and p.stat().st_size == 0]
        paired = [p for p in stubs if (p.with_name(p.name + ".dds").is_file()
                                       and p.with_name(p.name + ".dds").stat().st_size)]
        orphan = [p for p in stubs if p not in paired]
        print(f"  {root.name}: {len(stubs)} zero-byte .tga, "
              f"{len(paired)} with their art beside them as .tga.dds")
        # The ones with nothing beside them are not a counter-example, they are
        # the other half of the phase: `XXXX` is the modders' own mark for a
        # file they have switched off, and a stub with no partner is precisely
        # what "present and unreadable" is for.
        if orphan:
            print("    with nothing beside them: "
                  + ", ".join(sorted(q.name for q in orphan)))
        check(f"{root.name}: every stub that was meant to be art has art beside "
              f"it - the {len(orphan)} that do not are files the mod switched off",
              all(q.name.lower().startswith("xxxx") for q in orphan))

        models = sorted(strat.rglob("*.cas"))[:40]
        resolved = drawn = 0
        for m in models:
            try:
                scene = cas.read_cas(m)
            except Exception:
                continue
            for mat in scene.materials:
                if not mat.texture:
                    continue
                hit = cas.texture_path(m, mat.texture)
                if hit is None:
                    continue
                resolved += 1
                if icons.fault(hit) is None:
                    drawn += 1
        if resolved:
            print(f"    {drawn} of {resolved} resolved materials over "
                  f"{len(models)} models decode to a picture")
            check(f"{root.name}: a resolved material is one the viewer can "
                  f"actually paint with ({drawn}/{resolved})",
                  drawn == resolved)

shutil.rmtree(med2, ignore_errors=True)
shutil.rmtree(cfg, ignore_errors=True)

print(f"\n{sum(ok)}/{len(ok)} checks - {'ALL PASSED' if all(ok) else 'FAILURES'}")
sys.exit(0 if all(ok) else 1)
