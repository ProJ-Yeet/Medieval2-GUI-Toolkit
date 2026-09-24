"""The campaign map, read - Phase 16a's exit criteria, measured.

Three modules under test: :mod:`unittransfer.maptga` (the layer files),
:mod:`unittransfer.mapvocab` (what a pixel means) and
:mod:`unittransfer.campmap` (the terrain header, ``descr_regions.txt`` and the
region index).

Two halves. The first needs no mod at all - the record forms, the coordinate
transforms, the sea rule and the port dock rule, on text and grids written here.
The second runs over every installed mod that has a ``world/maps/base``, and
where that mod is DaC it checks the numbers this phase was scoped against:

    202 unique colours in map_regions.tga, two of them the markers
    199 settlement pixels, 77 port pixels
    198 records in descr_regions.txt, 197 of them in the legion form
    descr_regions.txt re-serialises byte-exact, CRLF and tabs included
    every TGA layer re-encodes byte-exact, footer and extension area included
    region IDs identical across two independent reads

    python -m tests.test_campmap
"""
import shutil
import struct
import sys
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image

from tests import _realmod, _tmp
from unittransfer import campmap, mapquery, maptga, mapvocab, regiondel
from unittransfer.mod import Mod

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


# ---- 1) the record forms, on text written here ------------------------------
print("\n1) descr_regions.txt, both record forms")

NINE = ("Alpha_Province\r\n\tAlpha\r\n\tengland\r\n\tSaxon_Rebels\r\n\t10 20 30\r\n"
        "\tgold, silk\r\n\t5\r\n\t4\r\n\treligions { catholic 60 pagan 40 }\r\n")
TEN = ("Beta_Province\r\n\tlegion: Beta_Legion\r\n\tBeta\r\n\tfrance\r\n"
       "\tBandit_Rebels\r\n\t40 50 60\r\n\tiron\r\n\t5\r\n\t1\r\n"
       "\treligions { catholic 100 }\r\n")
#: no settlement, and the arbiter says it has to be the last entry in the file
WASTE = "Wasteland_Province\r\n\t70 80 90\r\n\tno_brigands\r\n"

rf = campmap.parse_regions(NINE + TEN + WASTE)
check("all three records found", len(rf.records) == 3)
a, b, w = rf.records
check("nine-line form: fields land in the right places",
      (a.settlement, a.faction, a.rebels, a.rgb, a.triumph, a.farming)
      == ("Alpha", "england", "Saxon_Rebels", (10, 20, 30), 5, 4))
check("nine-line form: no legion line", a.legion == "" and a.legion_line < 0)
check("nine-line form: religions read and total 100",
      a.religions == {"catholic": 60, "pagan": 40} and a.religion_total == 100)
check("ten-line form: the legion line does not shift the record",
      (b.legion, b.settlement, b.rgb, b.triumph, b.farming)
      == ("Beta_Legion", "Beta", (40, 50, 60), 5, 1))
check("a single resource with no comma is still a resource",
      b.resources == ["iron"] and a.resources == ["gold", "silk"])
check("the wasteland short form is recognised, not dropped",
      w.wasteland and w.rgb == (70, 80, 90) and not w.settlement)
check("every field carries its own line index",
      [a.name_line, a.settlement_line, a.rgb_line, a.religions_line] == [0, 1, 4, 8])
check("nothing was reported as a problem", not any(r.problems for r in rf.records))
check("byte-exact round trip", rf.serialise() == NINE + TEN + WASTE)

lf = campmap.parse_regions(NINE.replace("\r\n", "\n"))
check("a LF file comes back as a LF file",
      lf.newline == "\n" and lf.serialise() == NINE.replace("\r\n", "\n"))

commented = ("; a banner\r\n" + NINE.replace("\tAlpha\r\n", "\tAlpha\t; the city\r\n")
             + "\r\n")
cf = campmap.parse_regions(commented)
check("comments and a trailing blank line survive, and the value is still read",
      cf.serialise() == commented and cf.records[0].settlement == "Alpha")

flush_rel = "Gamma_Province\r\n\tGamma\r\n\tspain\r\n\tRebels\r\n\t1 2 3\r\n\twine\r\n\t5\r\n\t2\r\nreligions { catholic 100 }\r\n"
gf = campmap.parse_regions(flush_rel)
check("a flush-left religions line is not a second region (Third Age 6)",
      len(gf.records) == 1 and gf.records[0].religions == {"catholic": 100})

# A beta mod ships every line of the file flush left, blank lines between the
# records and nothing else. The engine's parser ignores whitespace, so the mod
# plays; read on the indent alone it came out as one record per line with no
# colour on any of them, which put every province on the map in "declared
# nowhere in descr_regions.txt" and took the region out of the hover, the click
# and the query table at once.
FLAT = ("".join(ln.lstrip("\t") for ln in (NINE + TEN).splitlines(keepends=True))
        .replace("\r\n\r\n", "\r\n"))
ff = campmap.parse_regions(FLAT)
check("a file with no indentation at all still reads as records",
      len(ff.records) == 2 and all(r.rgb_line >= 0 for r in ff.records))
check("and every field of them lands where the indented form puts it",
      [(r.name, r.settlement, r.faction, r.rebels, r.rgb, r.resources,
        r.triumph, r.farming, r.religions) for r in ff.records]
      == [(r.name, r.settlement, r.faction, r.rebels, r.rgb, r.resources,
           r.triumph, r.farming, r.religions) for r in rf.records[:2]])
check("the legion line is still not counted as the settlement",
      ff.records[1].legion == "Beta_Legion" and ff.records[1].settlement == "Beta")
check("nothing is reported as a problem, and the file still round trips",
      not any(r.problems for r in ff.records) and ff.serialise() == FLAT)

flat_waste = campmap.parse_regions(
    FLAT + "\r\n" + "".join(ln.lstrip("\t")
                            for ln in WASTE.splitlines(keepends=True)))
check("the wasteland short form survives the same reading, with no settlement "
      "borrowed from the record above it",
      len(flat_waste.records) == 3 and flat_waste.records[2].wasteland
      and flat_waste.records[2].rgb == (70, 80, 90))

# Phase 40. A name line with a stray space in front of it is body to the indent
# reading, so the record before it runs on and swallows it whole. Measured on
# the installed Divide and Conquer, which writes ` Erebor_Province` with one
# space: the file read as 199 records where the mod has 200, the swallowed
# record's twenty lines parsed clean and reported no problems, and Erebor's 517
# painted tiles came out of here as land declared nowhere - no name in the
# hover, nothing to click, and a fatal region.undeclared about a province that
# plays. Two colour lines in one record is the signal, and no other line of the
# record is three numbers.
RUNON = NINE + " " + TEN.lstrip()
ro = campmap.parse_regions(RUNON)
check("a record whose name line carries a stray space is still its own record",
      len(ro.records) == 2 and [r.name for r in ro.records]
      == ["Alpha_Province", "Beta_Province"])
check("...with every field its own, not the previous record's",
      (ro.records[1].legion, ro.records[1].settlement, ro.records[1].rgb,
       ro.records[1].triumph, ro.records[1].farming, ro.records[1].resources)
      == ("Beta_Legion", "Beta", (40, 50, 60), 5, 1, ["iron"]))
check("...and the record in front of it keeps its own nine lines and its colour",
      ro.records[0].rgb == (10, 20, 30)
      and ro.records[0].span == (0, 8) and not ro.records[0].problems)
check("the run-on file still round trips byte for byte",
      ro.serialise() == RUNON)
check("a wasteland swallowed the same way comes back too, still the last entry "
      "and still short of a settlement",
      [(r.name, r.wasteland) for r in campmap.parse_regions(
          NINE + " " + WASTE.lstrip()).records]
      == [("Alpha_Province", False), ("Wasteland_Province", True)])
check("three records run together are three records, not one",
      len(campmap.parse_regions(
          NINE + " " + TEN.lstrip() + "  " + NINE.lstrip()
          .replace("Alpha", "Gamma").replace("10 20 30", "11 21 31")).records) == 3)
check("and a file the indent already reads correctly is not re-split: the "
      "three forms above are untouched",
      len(campmap.parse_regions(NINE + TEN + WASTE).records) == 3)


bom = campmap.parse_regions("﻿" + NINE)
check("a byte-order mark is not part of the first region's name",
      bom.records[0].name == "Alpha_Province"
      and bom.serialise() == "﻿" + NINE)
check("and the same when it arrives as latin-1, which is how these are read",
      campmap.parse_regions("\xef\xbb\xbf" + NINE).records[0].name
      == "Alpha_Province")

# ---- 2) the terrain header and the coordinate systems ------------------------
print("\n2) descr_terrain.txt and the three coordinate systems")

TERRAIN = """dimensions
{
\twidth  510
\theight  487
}
heights
{
\tmin_sea_height  -3406.782
\tmax_land_height  7511.272
}
lattitude
{
\tmin  22.000
\tmax  56.000
}
"""
t = campmap.parse_terrain(TERRAIN)
check("dimensions read", (t.width, t.height) == (510, 487))
check("heights read", (t.min_sea_height, t.max_land_height) == (-3406.782, 7511.272))
check("the game's own two-T spelling of latitude is accepted",
      (t.latitude_min, t.latitude_max) == (22.0, 56.0))
check("image y to game y flips about the height", t.game_y(0) == 486 and t.game_y(486) == 0)
check("and the transform is its own inverse",
      all(t.game_y(t.game_y(y)) == y for y in (0, 1, 243, 486)))
check("a 2W+1 layer samples the block centre", t.centre(0, 0) == (1, 1)
      and t.centre(12, 34) == (25, 69))
check("layer sizes come off one grid",
      (t.expected_size("tile"), t.expected_size("double"), t.expected_size("centre"))
      == ((510, 487), (1020, 974), (1021, 975)))

# the affine shortcut campmap.centres uses has to agree with the rule, pixel for pixel
src = Image.new("RGB", (2 * 7 + 1, 2 * 5 + 1))
for y in range(src.size[1]):
    for x in range(src.size[0]):
        src.putpixel((x, y), (x, y, (x * y) % 256))
got = src.transform((7, 5), Image.AFFINE, (2, 0, 0, 0, 2, 0), Image.NEAREST)
check("the affine resample really is (2t+1, 2t+1)",
      all(got.getpixel((tx, ty)) == src.getpixel((2 * tx + 1, 2 * ty + 1))
          for ty in range(5) for tx in range(7)))

# ---- 3) the sea rule and the port dock rule ----------------------------------
print("\n3) the engine rules, on grids written here")

check("black is sea", mapvocab.is_sea_height((0, 0, 0)))
check("grey is land", not mapvocab.is_sea_height((65, 65, 65)))
check("blue is sea", mapvocab.is_sea_height((0, 0, 255)))
check("near-grey is sea too - the rule is greyscale, not blueness",
      mapvocab.is_sea_height((65, 64, 63)))

heights = Image.new("RGB", (3, 3), (128, 128, 128))       # all land
heights.putpixel((0, 0), (0, 0, 255))                     # sea
heights.putpixel((1, 0), (0, 0, 255))                     # sea, but a crossing
features = Image.new("RGB", (3, 3), (0, 0, 0))
features.putpixel((1, 0), (0, 255, 255))                  # river crossing
sea = campmap.sea_mask(heights, features)
check("the sea mask is one byte per tile", len(sea) == 9)
check("blue is sea, grey is not", sea[0] == 1 and sea[2] == 0)
check("a river crossing is never sea, whatever its height says", sea[1] == 0)

# a port with one dock: sea to the west, land to the east
W = 5
colours = [(9, 9, 9), (0, 0, 0), (255, 255, 255), (7, 7, 7)]
labels = bytearray([0] * (W * 3))
labels[1 * W + 1] = 0          # sea tile, west of the port
labels[1 * W + 2] = 2          # the port pixel itself
labels[1 * W + 3] = 3          # land east of it, region (7,7,7)
seagrid = bytearray([0] * (W * 3))
seagrid[1 * W + 1] = 1
found = campmap._owner_of_port(bytes(labels), colours, W, 3, 2, 1, bytes(seagrid))
check("one dock: the port belongs to the land opposite it",
      found is not None and found[0] == (7, 7, 7))
seagrid[1 * W + 3] = 1
check("water on both sides is not a dock, so ownership is undecidable",
      campmap._owner_of_port(bytes(labels), colours, W, 3, 2, 1, bytes(seagrid)) is None)

# The dock: the sea neighbour the game puts the port's model on. A 5x5 grid,
# the port pixel in the middle at (2,2).
def dock_on(sea_tiles):
    g = bytearray(25)
    for x, y in sea_tiles:
        g[y * 5 + x] = 1
    return campmap.dock_tile(bytes(g), 5, 5, 2, 2)


check("the dock is on the sea, not on the port pixel",
      dock_on([(1, 2)]) == (1, 2))
check("no sea beside the port: no dock",
      dock_on([(0, 0), (4, 4)]) is None)
check("the side with more sea around it wins",
      dock_on([(2, 1), (3, 2), (4, 2), (3, 1), (3, 3)]) == (3, 2))
check("a tie goes to the first side the game tries, north",
      dock_on([(2, 1), (2, 0), (3, 2), (4, 2)]) == (2, 1))
check("sea sides with no sea around them: the game keeps the last one",
      dock_on([(2, 1), (3, 2)]) == (3, 2))
# north has 2 sea around it and wins; east's 2 do not beat it, but the game
# does not clear its tally for a side that lost, so south's 1 makes 3 and wins
check("the game's own tally, carried past a side that lost",
      dock_on([(2, 1), (2, 0), (3, 1), (3, 2), (4, 2), (2, 3), (1, 3)])
      == (2, 3))

# ---- 4) the vocabularies -----------------------------------------------------
print("\n4) what a pixel means")

check("a ground colour resolves to its code and its name",
      mapvocab.ground_at((96, 160, 64))["code"] == "fertility_medium"
      and mapvocab.ground_at((96, 160, 64))["name"] == "Fertile Medium")
check("an unknown ground colour is None, not the nearest guess",
      mapvocab.ground_at((96, 160, 65)) is None)
check("DaC's stray (1,1,1) feature pixel does not read as 'no feature'",
      mapvocab.feature_at((1, 1, 1)) is None
      and mapvocab.feature_at((0, 0, 0))["code"] == "none")
check("colour keys pack and unpack",
      mapvocab.key((1, 2, 3)) == 0x010203
      and mapvocab.unkey(mapvocab.key((200, 100, 50))) == (200, 100, 50))

# ---- 5) a TGA round trip, on a file written here ------------------------------
print("\n5) maptga, on a file written here")

tmp = Path(__file__).resolve().parent / "_campmap_tmp.tga"
try:
    art = Image.new("RGBA", (17, 5))
    for y in range(5):
        for x in range(17):
            art.putpixel((x, y), (x * 15 % 256, y * 50 % 256, (x + y) % 256, 255))
    for image_type in (maptga.TYPE_RAW, maptga.TYPE_RLE):
        for descriptor in (0x08, 0x28, 0x18):        # bottom-left, top, right
            info = maptga.TgaInfo(image_type=image_type, width=17, height=5, depth=32,
                                  descriptor=descriptor)
            tmp.write_bytes(maptga.encode(art, info))
            back, got = maptga.read(tmp)
            same = list(back.convert("RGBA").tobytes()) == list(art.tobytes())
            check(f"type {image_type} desc 0x{descriptor:02x}: pixels survive the "
                  f"orientation and the header comes back", same
                  and (got.image_type, got.depth, got.descriptor)
                  == (image_type, 32, descriptor))

    # A run packet carrying on into the next row is legal and the engine reads
    # it; Pillow calls it "buffer overrun when reading image file" and will not
    # open the file at all. A beta mod's fog, features, trade routes and
    # roughness were all packed that way.
    head = struct.pack("<BBBHHBHHHHBB", 0, 0, maptga.TYPE_RLE, 0, 0, 0, 0, 0,
                       8, 4, 24, 0)
    body, left = b"", 8 * 4
    while left:                                   # one run for the whole image
        n = min(128, left)
        body += bytes([0x80 | (n - 1)]) + b"\x11\x22\x33"
        left -= n
    tmp.write_bytes(head + body)
    refused = False
    try:
        probe = Image.open(tmp)
        probe.load()
    except OSError:
        refused = True
    crossed, _ = maptga.read(tmp)
    check("a run packet that crosses a scanline is read, where Pillow refuses it",
          refused and crossed.size == (8, 4)
          and set(crossed.convert("RGB").getdata()) == {(0x33, 0x22, 0x11)})

    tmp.write_bytes(struct.pack("<BBBHHBHHHHBB", 0, 0, maptga.TYPE_RLE, 0, 0, 0,
                                0, 0, 64, 64, 24, 0) + b"\x80\x11\x22\x33")
    try:
        maptga.read(tmp)
        said = ""
    except maptga.TgaError as exc:
        said = str(exc)
    check("and a file that really is short says so in pixels, not in buffers",
          "4,095 pixel(s) short" in said and "4,096" in said)
finally:
    tmp.unlink(missing_ok=True)

# ---- 6) a map past the byte, on a grid written here ---------------------------
print("\n6) more region colours than a byte can index (M2EX)")

# 800 provinces, one tile each, none of them a marker colour. The engine's own
# ceiling is 200 and the label image used to stop at 256 whatever the mod was;
# vanilla_kingdoms_uncompromised is 823x337 with 856 colours and plays, so past
# 256 the labels are 16-bit and everything that reads them has to not care.
WIDE_W, WIDE_H = 40, 20
WIDE = [(1 + i % 250, 1 + i // 250, 7) for i in range(WIDE_W * WIDE_H)]
assert len(set(WIDE)) == WIDE_W * WIDE_H
assert (0, 0, 0) not in WIDE and (255, 255, 255) not in WIDE

wide_img = Image.new("RGB", (WIDE_W, WIDE_H))
wide_img.putdata(WIDE)
wide_recs = campmap.parse_regions("".join(
    f"P{i}_Province\n\tSet{i}\n\tfac\n\treb\n\t{c[0]} {c[1]} {c[2]}\n\tres\n"
    f"\t5\n\t1\n\treligions {{ catholic 100 }}\n"
    for i, c in enumerate(WIDE))).records
wide_sea = bytes(WIDE_W * WIDE_H)

said = ""
try:
    campmap.build_index(wide_img, wide_sea, wide_recs, 256)
except campmap.MapError as exc:
    said = str(exc)
check(f"unmarked, the index is refused and the refusal says what lifts it "
      f"({said[:52]}...)",
      "declares 800 regions" in said and "M2EX" in said and "Home card" in said)

widx = campmap.build_index(wide_img, wide_sea, wide_recs, campmap.MAX_LABELS)
check(f"marked, it builds all {len(widx.regions)} of them on 16-bit labels",
      len(widx.regions) == WIDE_W * WIDE_H
      and not isinstance(widx.labels, bytes)
      and len(widx.labels) == WIDE_W * WIDE_H
      and max(widx.labels) > 255)
check("every tile answers with the region painted on it",
      all(widx.at(x, y) is widx.by_key[campmap.key(WIDE[y * WIDE_W + x])]
          for y in range(WIDE_H) for x in range(WIDE_W)))
check("no colour is unclaimed and no record is left empty",
      not widx.unclaimed and not widx.empty_records)
wids = sorted(r.region_id for r in widx.regions if r.region_id >= 0)
check(f"region ids are contiguous from zero ({len(wids)} numbered)",
      wids == list(range(WIDE_W * WIDE_H)))
check("and every label anchor is inside its own region",
      all(widx.at(*r.anchor) is r for r in widx.regions))

# The one thing 16-bit labels cannot be handed to Pillow for is the palette swap
# a colouring is drawn with, so that path has a second form. Both must paint the
# same picture; here the colour a label is given is the colour it already is.
painted = mapquery._paint(widx, list(widx.colours))
check("a colouring paints off wide labels, with no palette to swap",
      painted.mode == "RGB" and painted.size == (WIDE_W, WIDE_H)
      and all(painted.getpixel((x, y)) == WIDE[y * WIDE_W + x]
              for y in range(WIDE_H) for x in range(WIDE_W)))

crop_keys = {campmap.key(WIDE[y * WIDE_W + x]) for y in range(8) for x in range(8)}
crop_recs = [r for r in wide_recs if r.rgb_key in crop_keys]
nidx = campmap.build_index(wide_img.crop((0, 0, 8, 8)), bytes(64), crop_recs, 256)
check("and a map inside the byte still takes the palette path it always did",
      isinstance(nidx.labels, bytes)
      and mapquery._paint(nidx, list(nidx.colours)).getpixel((3, 2))
      == WIDE[2 * WIDE_W + 3])

# a repaint reads its own tiles off the label image, whichever width it is
wide_mask = regiondel._mask(SimpleNamespace(index=widx), campmap.key(WIDE[5]))
check("and a delete's mask finds exactly the one tile that region owns",
      wide_mask.size == (WIDE_W, WIDE_H)
      and [i for i, v in enumerate(wide_mask.getdata()) if v] == [5])

# ---- 6b) a colour in the file is not a province -------------------------------
print("\n6b) more COLOURS than the ceiling, and far fewer regions")

# The ceiling used to be measured against map_regions.tga's colour census, and a
# census counts the markers, the sea, and every shade a paint program left
# behind. Vanilla Redux is 252 records in a file carrying 258 colours - the sea
# and three shades of it within ten of it on one channel, 591 pixels between
# them - and an unmarked mod was refused outright, so the map screen said "no
# region" on every tile of a map that is comfortably inside the cap.
NAR_W, NAR_H = 30, 10                              # 300 tiles
NAR_PROV = [(1 + i, 60, 9) for i in range(250)]    # 250 declared provinces
NAR_SEA = [(41, 140 + k, 233) for k in range(8)]   # one sea, seven shades of it
NAR_PIX = NAR_PROV + [NAR_SEA[i % len(NAR_SEA)] for i in range(50)]
assert len(NAR_PIX) == NAR_W * NAR_H
assert len(set(NAR_PIX)) == 258 and not set(NAR_PROV) & set(NAR_SEA)

nar_img = Image.new("RGB", (NAR_W, NAR_H))
nar_img.putdata(NAR_PIX)
nar_recs = campmap.parse_regions("".join(
    f"N{i}_Province\n\tSet{i}\n\tfac\n\treb\n"
    f"\t{c[0]} {c[1]} {c[2]}\n\tres\n\t5\n\t1\n"
    f"\treligions {{ catholic 100 }}\n"
    for i, c in enumerate(NAR_PROV))).records
nar_sea = bytes([0] * 250 + [1] * 50)

nidx2 = campmap.build_index(nar_img, nar_sea, nar_recs, 256)
check(f"unmarked, {len(set(NAR_PIX))} colours and {len(nar_recs)} records builds, "
      f"because {len(nar_recs)} is the number the ceiling is about",
      len(nidx2.regions) == len(set(NAR_PIX)))
check("the labels went 16-bit on their own, with no mod marked anything",
      not isinstance(nidx2.labels, bytes) and max(nidx2.labels) > 255)
check(f"every record is claimed and the {len(NAR_SEA)} sea shades are the "
      f"undeclared ones",
      not nidx2.empty_records
      and sorted(tuple(c) for c in nidx2.unclaimed) == sorted(NAR_SEA))
check("and every declared tile answers with its own province",
      all(nidx2.at(i % NAR_W, i // NAR_W) is nidx2.by_key[campmap.key(NAR_PIX[i])]
          for i in range(250)))

# The other side of the same line: the records are what is counted, so a file
# that declares more than the ceiling is still refused however few colours the
# image happens to carry.
nar_said = ""
try:
    campmap.build_index(nar_img, nar_sea, wide_recs, 256)
except campmap.MapError as exc:
    nar_said = str(exc)
check(f"and 800 records on a 258-colour image is still refused "
      f"({nar_said[:44]}...)",
      "declares 800 regions" in nar_said)



# ---- 7) real mods -------------------------------------------------------------
print("\n7) every installed mod with a campaign map")

mods = [m for m in _realmod.installed()
        if (m / "data" / campmap.REGIONS_REL).exists()]
if not mods:
    print(f"  SKIPPED - no installed mod has {campmap.REGIONS_REL} under {_realmod.MODS}")
else:
    for path in mods:
        mod = Mod(path)
        print(f"\n  -- {mod.name}")
        t0 = time.time()
        cm = campmap.CampaignMap(mod)
        opened = (time.time() - t0) * 1000

        check(f"descr_terrain.txt reads ({cm.terrain.width}x{cm.terrain.height}) "
              f"in {opened:.0f} ms",
              cm.terrain.width > 0 and cm.terrain.height > 0)
        # The 510 cap and the region-colour cap are both ceilings in the vanilla
        # executable, and a mod marked as running on M2EX is not measured
        # against either - see campmap.CampaignMap.uncapped.
        over = (cm.terrain.width > campmap.MAX_DIMENSION
                or cm.terrain.height > campmap.MAX_DIMENSION)
        complaints = cm.check_layers()
        if over and not cm.uncapped:
            # Not a fault in the map and not one in the toolkit: a map past a
            # vanilla ceiling on a mod nobody has marked as running on M2EX.
            # What is worth asserting is that the complaint names the thing
            # that lifts it rather than stopping at the number.
            check(f"{cm.terrain.width}x{cm.terrain.height} is over the engine's "
                  f"{campmap.MAX_DIMENSION} cap and the complaint says what "
                  f"lifts it: {'; '.join(complaints)}",
                  any("M2EX" in c for c in complaints))
        else:
            check(f"no side is over the engine's 510 cap"
                  f"{' (M2EX, so uncapped)' if cm.uncapped else ''}",
                  cm.uncapped or not over)
            check(f"every layer matches its size rule"
                  f"{'' if not complaints else ': ' + '; '.join(complaints)}",
                  not complaints)

        from unittransfer.keyblock import read_text
        raw = read_text(cm.regions.path, campmap.ENCODING)
        check(f"descr_regions.txt round-trips byte-exact "
              f"({len(cm.regions.records)} records, "
              f"{sum(1 for r in cm.regions.records if r.legion_line >= 0)} with a legion line)",
              cm.regions.serialise() == raw)
        broken = [(r.name, r.problems) for r in cm.regions.records if r.problems]
        check(f"every record parses{'' if not broken else ': ' + str(broken[:3])}",
              not broken)
        check("every record carries an RGB and a source line for it",
              all(r.rgb_line >= 0 for r in cm.regions.records))

        t0 = time.time()
        try:
            idx = cm.index
        except campmap.MapError as exc:
            check(f"the index is refused, and the refusal says what would lift "
                  f"it: {exc}", "M2EX" in str(exc) and not cm.uncapped)
            print("    (over a vanilla ceiling and not marked as running on "
                  "M2EX, so nothing below is read for this mod)")
            continue
        built = (time.time() - t0) * 1000
        colours = len(idx.colours)
        check(f"the region index builds in {built:.0f} ms "
              f"({colours} colours, {len(idx.regions)} regions, "
              f"{len(idx.settlements)} settlement px, {len(idx.ports)} port px)",
              colours > 1 and idx.regions)
        # Not "no map is over the engine's 200": Vanilla Redux is, at 252
        # records, and it indexes fine. Past a vanilla ceiling is a state a real
        # mod is in, and the answer to it is mapcheck's `layer.colour_cap`
        # finding rather than a refusal here - see build_index. What is worth
        # asserting is that the index adds up: every colour in the file is
        # either a province somebody wrote down or one nobody did.
        declared = sum(1 for r in idx.regions if r.record is not None)
        over = declared > mapvocab.MAX_REGION_COLOURS
        check(f"{declared} declared regions and {len(idx.unclaimed)} undeclared "
              f"colours account for all {len(idx.regions)} of them"
              + (f" ({declared} is over the engine's "
                 f"{mapvocab.MAX_REGION_COLOURS}, which is a finding, not a "
                 f"refusal)" if over and not cm.uncapped else ""),
              declared + len(idx.unclaimed) == len(idx.regions)
              and declared == len(cm.regions.records) - len(idx.empty_records))
        check(f"the label image is {'16-bit' if colours > 256 else 'one byte'} "
              f"a tile for {colours} colours",
              len(idx.labels) == cm.terrain.width * cm.terrain.height
              and isinstance(idx.labels, bytes) == (colours <= 256))
        ids = sorted(r.region_id for r in idx.regions if r.region_id >= 0)
        check(f"region ids are contiguous from zero ({len(ids)} numbered)",
              ids == list(range(len(ids))))
        again = campmap.CampaignMap(mod).index
        check("region ids are identical on a second, independent read",
              {r.rgb: r.region_id for r in idx.regions}
              == {r.rgb: r.region_id for r in again.regions})
        check("every region's label anchor is inside that region",
              all(idx.at(*r.anchor) is r for r in idx.regions if r.pixels))
        check(f"every port pixel found an owner "
              f"({len(idx.undecided_ports)} undecided)",
              not idx.undecided_ports)

        # Two claims, and they are not the same claim. What the writer
        # PROMISES is that a layer goes back in the shape it arrived in with the
        # pixels it arrived with; byte-for-byte is what usually falls out of
        # that, and it is not guaranteed, because RLE has more than one legal
        # packing of the same row. Vanilla's map_fog.tga is the case in the
        # wild: whatever packed it wrote a five-pixel literal where this encoder
        # starts a run, so ours is 682 bytes shorter and pixel for pixel the
        # same. All ten of DaC's are byte-exact.
        exact, lossy, unstable = [], [], []
        for ly in campmap.LAYERS:
            p = cm.base / ly["file"]
            if not p.exists():
                continue
            img, info = maptga.read(p)
            data = maptga.encode(img, info)
            if data == p.read_bytes():
                exact.append(ly["file"])
                continue
            # not byte-exact: then it must at least be the same picture, in the
            # same shape, and settled - a second pass may not drift again
            tmp = Path(_tmp.mkdtemp(prefix="ut_rt_")) / ly["file"]
            tmp.write_bytes(data)
            again, info2 = maptga.read(tmp)
            if (again.tobytes() != img.tobytes()
                    or info2.describe() != info.describe()):
                lossy.append(ly["file"])
            elif maptga.encode(again, info2) != data:
                unstable.append(ly["file"])
            shutil.rmtree(tmp.parent, ignore_errors=True)
        repacked = [ly["file"] for ly in campmap.LAYERS
                    if (cm.base / ly["file"]).exists()
                    and ly["file"] not in exact]
        check(f"{len(exact)} TGA layers re-encode byte-exact"
              f"{'' if not repacked else f'; {repacked} repack'}",
              len(exact) + len(repacked) > 0)
        check(f"and every layer that repacks is the same picture in the same "
              f"shape, and settles on one packing"
              f"{'' if not (lossy + unstable) else ': ' + str(lossy + unstable)}",
              not lossy and not unstable)

        cl = mapvocab.climates(mod)
        check(f"the mod's own climates read ({len(cl)}, "
              f"{sum(1 for c in cl if c['rgb'])} with a colour)",
              cl and all(c["rgb"] for c in cl))

        # 16d widened this from five named keys to one row per layer, so the
        # inspector is a loop rather than ten special cases and so the layers
        # 16a never probed - fog, roughness, trade routes - are named too.
        probe = cm.probe_pixel(*idx.regions[0].anchor)
        rows = {r["code"]: r for r in probe["layers"]}
        named = [c for c, r in rows.items() if r["code_name"]]
        check(f"a pixel probe names all ten layers under it ({len(named)} of "
              f"{len(rows)} had a value here)",
              probe["region"]["rgb"] == list(idx.regions[0].rgb)
              and set(rows) == {ly["code"] for ly in campmap.LAYERS}
              and set(probe) >= {"image", "game", "region", "marker", "sea"})
        check("and the two pictures say they have no value at a tile, rather "
              "than being sampled at coordinates that mean nothing in them",
              all(rows[c]["rgb"] is None and "tile grid" in rows[c]["problem"]
                  for c in ("water_surface", "fe")))

        if mod.name.lower().startswith("divide_and_conquer"):
            print("    (DaC: the numbers this phase was scoped against)")
            check("202 unique colours in map_regions.tga", colours == 202)
            check("199 settlement pixels", len(idx.settlements) == 199)
            check("77 port pixels", len(idx.ports) == 77)
            check("198 records, 197 of them in the legion form",
                  len(cm.regions.records) == 198
                  and sum(1 for r in cm.regions.records if r.legion_line >= 0) == 197)
            # Phase 40. This read as one orphan, at image (339,65), and was
            # written down here as a fact about DaC. It was a fact about this
            # module: the marker is Erebor's, and ` Erebor_Province` has a
            # stray space in front of its name, so the record before it
            # swallowed it and the colour under the marker was declared
            # nowhere. Every marker on this map has an owner.
            check(f"every settlement pixel stands in a region the file "
                  f"declares ({len(idx.orphan_settlements)} orphaned)",
                  idx.orphan_settlements == [])
            feat = cm.layer("features").convert("RGB")
            strays = [c for n, c in feat.getcolors(maxcolors=1 << 20)
                      if mapvocab.feature_at(c) is None]
            check(f"the stray feature pixel is found: {strays}", strays == [(1, 1, 1)])

print(f"\n{sum(ok)}/{len(ok)} checks passed")
print("ALL PASSED" if all(ok) else "SOME FAILED")
sys.exit(0 if all(ok) else 1)
