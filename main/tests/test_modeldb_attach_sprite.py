"""The field in a modeldb that almost always holds 0 - and sometimes does not.

An attachment texture group is four names - faction, texture, normal, sprite -
and the fourth is nearly always the bare ``0`` that means *no name follows*,
because attachments are drawn with the model and rarely carry a sprite of their
own. Nearly always is not always: Thera_Redux and BOTET each write a real
``unit_sprites/….spr`` into one, and read as names those files run to a clean EOF
and round-trip byte-exact. Refusing them cost a user a line of their own mod,
deleted on this tool's advice.

What is genuinely broken is the other thing that turns up in that slot. A modder
deletes a faction's skin by hand and the digit from the removed line is left glued
to the 0, giving ``... .texture 01``. Take 1 as a length and the reader eats the
next field as a one-character name and dies two lines further down on a word that
is perfectly fine where it is - the single worst kind of error this format can
produce, because the line it names has nothing wrong with it.

So the reader looks before it decides: a sprite is a ``.spr`` path that fills
exactly the characters its length claims and stops on whitespace, and a stray
digit's "name" is none of those. A name that holds up is read; anything else is
refused AT the stray character with the fix in the sentence - refused rather than
assumed away, because half a dozen span walkers in ``modeldb.py`` re-walk the same
bytes to place an edit, and one of them reading a file differently from the others
is how a save writes at the wrong offset.

    python -m tests.test_modeldb_attach_sprite
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unittransfer import modeldb

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


#: One entry with the shape the reader walks: name, scale, one LOD, one main
#: texture (which DOES carry a sprite), one attachment texture (whose sprite slot
#: is the field under test), one animation, and the torch line. Every name is emitted
#: through `nm`, so no length in here can be wrong by hand - the file is about
#: ONE wrong number and it must be the one the test put there.
def nm(v: str) -> str:
    return f"{len(v)} {v}"


ATT_NORM = "attachments/guard_at_norm.texture"


def entry(attach_sprite: str) -> str:
    return "\n".join([
        nm("guard"),                                 # name
        "1 1",                                       # scale + lod count
        nm("units/guard.mesh") + " 6400",            # lod path + distance
        "1",                                         # main texture count
        nm("bulgaria"),
        nm("textures/guard.texture"),
        nm("textures/guard_norm.texture"),
        nm("unit_sprites/guard.spr"),
        "1",                                         # attachment texture count
        nm("bulgaria"),
        nm("attachments/guard_at.texture"),
        nm(ATT_NORM) + " " + attach_sprite,
        "1",                                         # animation count
        nm("None"),                                  # mount type
        nm("MTW2_Fast_2H_Axe") + " 0",               # primary skeleton, no secondary
        "1",
        nm("MTW2_2H_Axe_primary"),
        "0",
        "16 -0.09 0 0 -0.35 0.8 0.6",                # torch index + six floats
        "",
    ])


def file_with(attach_sprite: str) -> str:
    head = f"{len(modeldb.ARCHIVE_MAGIC)} {modeldb.ARCHIVE_MAGIC} 0 0 0 0 0 2 0 0\n"
    blank = nm("blank") + " " + " ".join(["0"] * 39) + "\n"
    return head + blank + entry(attach_sprite)


#: which line of the whole file the stray character sits on: the header and the
#: blank sentinel are one line each, and `entry` counts from 0
def stray_line(stray: str) -> int:
    return entry(stray).split("\n").index(nm(ATT_NORM) + " " + stray) + 3


print("\n== the 0 that means 'no sprite on an attachment' ==")
db = modeldb.parse_text(file_with("0"))
check("a well-formed entry parses", len(db.entries) == 1)
check("...and its attachment sprite is empty",
      db.entries[0].attach_textures[0].sprite == "")
check("...while the main texture's sprite is the real one",
      db.entries[0].main_textures[0].sprite == "unit_sprites/guard.spr")
check("...and the entry round-trips byte-exact",
      db.to_text() == file_with("0"))

print("\n== a digit left glued to that 0 ==")
#: `01` is the one seen in the wild; `1` and `12` are the same mistake, and the
#: point of all three is that the sentence must be about THIS character.
for stray in ("01", "1", "12"):
    try:
        modeldb.parse_text(file_with(stray))
        check(f"{stray!r} is refused", False)
        continue
    except ValueError as e:
        msg = str(e)
    check(f"{stray!r} is refused", True)
    check(f"{stray!r}: the sentence names the value it found",
          repr(stray) in msg)
    check(f"{stray!r}: ...says what the slot can legally hold",
          "neither the 0 that says this attachment has no sprite" in msg)
    check(f"{stray!r}: ...and says what to do about it",
          "Delete what follows the 0" in msg)
    # The generic "the number that did this is somewhere above you" explanation
    # is for a read that died away from the mistake. Here it did not, and saying
    # both things at once is how a good error message stops being one.
    check(f"{stray!r}: it does not then send you looking elsewhere",
          "shifts every field that follows" not in msg)
    # and the line it names is the line the stray character is ON - the whole
    # point, since the old failure named the innocent line two below it
    line = msg.split("line ")[1].split(",")[0]
    want = str(stray_line(stray))
    check(f"{stray!r}: it points at the line the character is on"
          f" (says {line}, want {want})", line == want)

print("\n== and a real sprite in that slot is read, not refused ==")
#: The two mods this came from. A length that fits a `.spr` path exactly, with
#: whitespace after it, is a name - the only reading under which those files
#: reach EOF at all.
for spr in ("9 guard.spr", "44 unit_sprites/france_Elector_count_sprite.spr",
            "52 unit_sprites/teutonic_order_Dummy_NE_Crew_sprite.spr"):
    want = spr.split(" ", 1)[1]
    src = file_with(spr)
    try:
        db = modeldb.parse_text(src)
    except ValueError as e:
        check(f"{want!r} is read as the sprite it is ({e})", False)
        continue
    check(f"{want!r} is read as the sprite it is",
          db.entries[0].attach_textures[0].sprite == want)
    check(f"{want!r}: ...and the entry round-trips byte-exact",
          db.to_text() == src)
    check(f"{want!r}: ...and it is named among the files a transfer must carry",
          want in db.entries[0].texture_files())

print("\n== a length that fits, on something that is not a sprite, still is not ==")
#: The discriminator is not "the arithmetic works out" - `01` in this fixture
#: lands a one-character slice that also ends on whitespace. It is that a sprite
#: is a `.spr` path, and nothing else belongs in this slot.
try:
    modeldb.parse_text(file_with("5 horse"))
    check("a self-consistent name that is not a sprite is refused", False)
except ValueError as e:
    check("a self-consistent name that is not a sprite is refused",
          "Delete what follows the 0" in str(e))

print()
print(f"{sum(ok)}/{len(ok)} checks - "
      + ("ALL PASSED" if all(ok) else f"{len(ok) - sum(ok)} FAILED"))
sys.exit(0 if all(ok) else 1)
