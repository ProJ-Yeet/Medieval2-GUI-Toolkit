"""Phase 62 (B3): one file out of a mod, or one file into it.

    python -m tests.test_fileswap

On a temp mod: a download is the file's bytes; a path that climbs out of
data/ is refused however it is spelled; a put adds a new file or, only when
told to, replaces one, backed up, and one Undo puts either back; the same
bytes are refused; an encoding change and a non-UTF-16 text/ file are named;
a DDS put onto a .texture is wrapped; and a text/ file's .strings.bin is
recompiled with it.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp  # noqa: E402
from unittransfer import fileswap as fs  # noqa: E402
from unittransfer import modelexport, stringsbin, transfer  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
    return bool(cond)


class TinyMod:
    name = "SwapMod"

    def __init__(self, root):
        self.root, self.data = root, root / "data"


root = Path(_tmp.mkdtemp(prefix="ut_swap_")) / "SwapMod"
(root / "data" / "text").mkdir(parents=True)
(root / "data" / "unit_models").mkdir(parents=True)
TEXT = "\ufeff{GREETING}\tHello\r\n{FAREWELL}\tGoodbye\r\n".encode("utf-16-le")
(root / "data" / "text" / "greet.txt").write_bytes(TEXT)
(root / "data" / "descr_x.txt").write_bytes(b"alpha 1\r\nbeta 2\r\n")
def dds(pixels: bytes, fourcc: bytes = b"DXT5") -> bytes:
    head = bytearray(128)
    head[0:4] = b"DDS "
    head[84:88] = fourcc
    return bytes(head) + pixels


DDS = dds(b"pixels")
(root / "data" / "unit_models" / "skin.texture").write_bytes(modelexport.dds_to_texture(DDS))
mod = TinyMod(root)
snap = lambda: {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
start = snap()

print("\n1) out")
check("a download is the file's bytes", fs.export(mod, "descr_x.txt") == b"alpha 1\r\nbeta 2\r\n")
check("with data/ in front, or backslashes, it is the same file",
      fs.export(mod, "data\\descr_x.txt") == fs.export(mod, "descr_x.txt"))
for bad in ("../outside.txt", "text/../../x.txt", "C:/Windows/win.ini", "/etc/passwd", "", "text/a:b.txt"):
    try:
        fs.export(mod, bad)
        check(f"{bad!r} is refused", False)
    except fs.SwapError:
        check(f"{bad!r} is refused", True)

print("\n2) in")
p = fs.plan_put(mod, "ui/units/england/#new_card.tga", b"TGA-card")
check("a new file plans as an add", not p.errors and not p.replaces and any("new file" in c for c in p.changes))
res = fs.apply_put(p)
check("and is written, folders and all", (root / "data/ui/units/england/#new_card.tga").read_bytes() == b"TGA-card")
transfer.undo(res["id"])
check("one undo takes it away again", not (root / "data/ui/units/england/#new_card.tga").exists())

p = fs.plan_put(mod, "descr_x.txt", b"alpha 9\r\n")
check("a file that is there is not written over unless told to", p.errors and p.replaces)
p = fs.plan_put(mod, "descr_x.txt", b"alpha 1\r\nbeta 2\r\n", replace=True)
check("the same bytes are refused", p.errors)
p = fs.plan_put(mod, "descr_x.txt", b"alpha 9\r\n", replace=True)
res = fs.apply_put(p)
check("told to, it replaces it", (root / "data/descr_x.txt").read_bytes() == b"alpha 9\r\n")
transfer.undo(res["id"])
check("and one undo puts the old one back", (root / "data/descr_x.txt").read_bytes() == b"alpha 1\r\nbeta 2\r\n")

utf8 = "{GREETING}\tHi there\n{FAREWELL}\tBye\n".encode("utf-8")
p = fs.plan_put(mod, "text/greet.txt", utf8, replace=True)
check("a text file that changes encoding is named: UTF-16 LE to Latin-1",
      any("UTF-16 LE" in w and "Latin-1" in w for w in p.warnings))
check("and its .strings.bin is said to be recompiled", any("strings.bin" in c for c in p.changes))
p = fs.plan_put(mod, "text/new.txt", utf8)
check("a new text/ file that is not UTF-16 is named", any("UTF-16" in w for w in p.warnings))

good = "\ufeff{GREETING}\tHi there\r\n{FAREWELL}\tBye\r\n".encode("utf-16-le")
p = fs.plan_put(mod, "text/greet.txt", good, replace=True)
check("the same encoding says nothing about encoding", not any("encoding" in w for w in p.warnings))
res = fs.apply_put(p)
sb = root / "data/text/greet.txt.strings.bin"
check("written, with the .strings.bin compiled beside it",
      sb.is_file() and stringsbin.read(sb).get("GREETING") == "Hi there")
transfer.undo(res["id"])

new_dds = dds(b"other pixels")
p = fs.plan_put(mod, "unit_models/skin.texture", new_dds, replace=True)
check("a DDS put onto a .texture is wrapped in the 48-byte header",
      not p.errors and p.data[48:] == new_dds and any("48-byte" in c for c in p.changes))
check("a DDS the game's .texture cannot hold is refused, and says why",
      any("cannot go into a .texture" in e for e in
          fs.plan_put(mod, "unit_models/skin.texture", dds(b"x", b"NONE"), replace=True).errors))
check("nothing ends up anywhere it was not put: the mod is as it started", snap() == start)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
