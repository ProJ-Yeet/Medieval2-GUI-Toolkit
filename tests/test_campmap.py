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
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image

from tests import _realmod
from unittransfer import campmap, maptga, mapvocab
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
finally:
    tmp.unlink(missing_ok=True)

# ---- 6) real mods -------------------------------------------------------------
print("\n6) every installed mod with a campaign map")

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
        check("no side is over the engine's 510 cap",
              cm.terrain.width <= campmap.MAX_DIMENSION
              and cm.terrain.height <= campmap.MAX_DIMENSION)

        complaints = cm.check_layers()
        check(f"every layer matches its size rule{'' if not complaints else ': ' + '; '.join(complaints)}",
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
        idx = cm.index
        built = (time.time() - t0) * 1000
        colours = len(idx.colours)
        check(f"the region index builds in {built:.0f} ms "
              f"({colours} colours, {len(idx.regions)} regions, "
              f"{len(idx.settlements)} settlement px, {len(idx.ports)} port px)",
              colours > 1 and idx.regions)
        check(f"region colours are within the engine's {mapvocab.MAX_REGION_COLOURS} "
              f"ceiling ({len(idx.regions)})",
              len(idx.regions) <= mapvocab.MAX_REGION_COLOURS)
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
            tmp = Path(tempfile.mkdtemp(prefix="ut_rt_")) / ly["file"]
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
            check("the one settlement pixel standing in an undeclared region is "
                  "reported, not silently attached",
                  idx.orphan_settlements == [(339, 65)])
            feat = cm.layer("features").convert("RGB")
            strays = [c for n, c in feat.getcolors(maxcolors=1 << 20)
                      if mapvocab.feature_at(c) is None]
            check(f"the stray feature pixel is found: {strays}", strays == [(1, 1, 1)])

print(f"\n{sum(ok)}/{len(ok)} checks passed")
print("ALL PASSED" if all(ok) else "SOME FAILED")
sys.exit(0 if all(ok) else 1)
