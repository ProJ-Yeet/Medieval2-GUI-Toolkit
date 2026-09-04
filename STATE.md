# STATE - Medieval 2 GUI Toolkit V2 and V3
_Updated: 2026-09-04 · **v2.1.11 released** · V3 under way: 16a-16g done, 16h next_

## Next up
Start **16h** - `descr_strat.txt`, write: settlements and buildings. The screen
can now read the map, edit a region record, paint the pixels, say whether it
will load and ask it which provinces are which; 16h is where the campaign file
itself becomes editable. Level, city or castle, population, `plan_set`,
`faction_creator`, year founded, and the building list with EDB-driven level
compatibility. Owner reassignment moves the whole settlement block between
faction blocks, and the capital must be the faction's first region in the file.

Most of the reading is already standing and none of it should be written twice.
`campstrat.StratFile` holds every settlement block as a span with its fields
indexed by line, which is what a splice needs; `mapquery.Facts` already joins
each of those blocks to the province it is in, its owner, its buildings and the
tree each building belongs to, so "which levels may this settlement have" is a
lookup rather than a second read of `export_descr_buildings.txt`. Owner
reassignment is a move of a `[start, end]` slice between two other spans and
nothing else, and `mapcheck` already owns the rule that a faction block may not
come after the diplomacy section.

Three rulings from 16g carry into it. **One fact table, read by everything** -
16h's forms should read `Facts` rather than open `descr_strat.txt` again, and
whatever it adds belongs on `RegionFacts` where the query engine can filter by
it for free. **A rule with no evidence reports nothing** - a level picker with
no EDB on disk offers what the campaign file itself already writes rather than
an empty list. And **Python owns the bytes**: the browser posts what a person
typed and nothing about what to change.

Run `python tools/upstream_sync.py sync` first, as before every sub-phase.

## 16g - query, themes and information maps (2026-09-04)
`mapquery.py` (1,934 lines), `web/js/mapquery.js` (581), four routes on
`server.py`, and `tests/test_mapquery.py` at **90 checks, all passing**.
**24 filters**, three themes with political borders, and **93 colourings on
Third Age Reforged** - Geomod's nine fixed information maps plus one per hidden
resource, religion and trade resource that is actually on the map.

**One fact table, read by everything.** A filter, a theme, an information map
and an export are four views of the same handful of sentences about a province,
so they are joined once and nothing below `Facts` opens a file: 199 provinces
in 384 ms on Third Age Reforged and 108 ms on vanilla, cached per (mod,
campaign) on the registry and dropped when a campaign file changes on disk.
Every filter after that is a dictionary lookup, so a two-filter query over 199
provinces is 0 ms. Three small files nobody else in the toolkit read are read
here: `descr_sounds_music_types.txt`, `descr_mercenaries.txt` and
`descr_win_conditions.txt`.

**A rule with no evidence reports nothing**, carried over from 16f and measured
on the same map. The stock game keeps `descr_sm_factions.txt` and
`export_descr_buildings.txt` inside its packed data, so on vanilla the culture
filter is off *with that file named* rather than empty, and a query holding it
does not run it at all: under `all` it would empty the result and under `any` it
would quietly widen it. The building-tree filter survives the same absence,
because `descr_strat.txt` writes `type <line> <level>` and the line name is
already in the campaign file - 48 provinces on vanilla with no EDB on disk.

**A theme and an information map are the same object.** One `Colouring` builds
the payload, one function writes the TGA and one draws it. The browser
recolours the region layer it is already holding through a table keyed by the
region's map colour, which is the same operation 16d's `cmapMask` does, and the
border pass compares the GROUP a region is in rather than its colour - two
provinces of one faction get no line between them, and the screen and the
exported file agree about where a frontier is.

**Two colour rulings, both measured.** A faction keeps the colour
`descr_sm_factions.txt` gives it unless something on the map is already using
it: Third Age Reforged declares `england` as `0 0 0`, which is exactly the
settlement marker, and `france` as `37 37 37`, which at map size is the border
line. Nine of its twenty-nine factions are swapped for the fallback palette and
the legend says which and what each clashed with. And every magnitude map runs
along a three-stop ramp rather than two, because the mod uses farming levels 0
to 2 and a two-stop ramp put the whole picture inside a few units of the sea
behind it.

Exports land in the cache, never in the mod, in the shape of the mod's own
`map_regions.tga`, round-tripping pixel for pixel. Geomod's batch writes one
file per faction plus the map they are all on, from one fact table in one call.

**Two things found by building it.** `values_of` counted occurrences rather than
provinces, so a province with two vineyards made the count beside a filter's
value disagree with the answer that filter gave. And a resource is allowed to
stand **on** a settlement or port pixel, which the index does not answer for,
so the region that owns the marker answers instead.

## 16f - the validator (2026-09-04)
`mapcheck.py` (1,567 lines), `web/js/mapcheck.js` (387), four routes on
`server.py`, and `tests/test_mapcheck.py` at **82 checks, all passing**.
**30 rules**, each carrying the tool, manual or measurement that says it is a
rule, and each with a deliberately broken map under test that only it may
catch. The whole set runs on DaC in 609 ms and on vanilla in 120 ms.

**A rule with no evidence reports nothing.** The stock game's `data/` is packed:
`descr_climates.txt` is not on disk and neither is the region and settlement
name file. A checker that reads "no climate is declared" as "every climate
colour is undeclared" reports 11 faults, 55,755 tiles and 112 missing name keys
against the map that ships with the game and works. So a rule that needs a
vocabulary asks for it first and, when it is not there, puts a line in
`skipped` naming the file that would let it run.

**A finding is identified by what it is about, never by where it is written** -
the rule, the file and the thing, so inserting a comment above a finding does
not make it a new one. That is what makes the baseline real: `take_baseline`
stamps what a mod already had, those rows stay visible and counted, and only
what appears afterwards blocks a save.

**Vanilla found the bug the fix is named after.** Its `map_heights.tga` has 55
tiles painted pure black where `map_ground_types.tga` says land, and two of
them have a port standing on them: Nottingham's, and **Ragusa's** - the port bug
Geomod's manual names its debugger action after, shipped in the stock game.
`heights_black` is Geomod's own fix, 77 pixels over 55 tiles, and the picture
does not change.

Every fix writes through one backup set and one log entry, so the Log's Undo
puts it back byte-exact. The four marker rules exist once, in
`mapcheck.marker_faults`, which the paint wizard calls rather than copies.

## 16e - the paint tool (2026-09-04)
`campaint.py` (1,381 lines), `web/js/campaint.js` (871), nine routes on
`server.py`, `repixel` on `CampaignMap`, and `tests/test_campaint.py` at
**95 checks, all passing** on a map the suite writes itself and on vanilla's,
with six more per additional installed map. The map stops being a picture here.

**Python owns the bytes, and there is one set of them.** The browser draws a
provisional trail under the cursor and posts the pointer samples, once per
stroke rather than per pointer event; `campaint` expands them, snaps the colour,
refuses what must not be written, applies it to *the layer image the whole
server is already serving from*, and answers with the tiles that actually moved.
The browser throws its trail away and writes that answer into its own copy. So
the probe, the legend and the layer PNGs all show the unsaved map, and a
disagreement between the preview and the file cannot outlive one pointer-up.
`repixel` is the other half: the decoded image and its header stay, everything
derived from them goes, and the index, the sea mask and the adjacency are
dropped only when a layer that feeds them moved.

**Snapping is a name, not a colour.** A stroke on `map_regions.tga` sends the
region's NAME and the server writes that record's own RGB, so a province cannot
drift a channel, the palette for that layer is the region list, and the two
marker colours cannot come out of a brush at all. They are placed one tile at a
time by the wizard, and a stroke that would cover one skips it and says how many
it protected.

**A tile owns a rectangle, and the rectangles partition the layer exactly.**
`block()` is that rule, asserted pixel by pixel on all three grids - the `2W+1`
layers' leading row and column included, or nothing owns them and a painted
coastline keeps a one-pixel seam of the old map along two edges. The pixel the
engine samples is always inside its own tile's block, so what the tile view
shows after a stroke is what was painted.

**Unlimited undo, because a stroke is one colour.** Every tool writes a single
value per layer, so a stroke is a tile list plus one RGB rather than a bitmap
and the stack is pixel deltas in an `array("i")`. Undo is not "paint the old
colour back": the covered pixels were not all one colour, so the old value is
stored and restored per pixel, which is what makes it byte-exact rather than
plausible. Geomod has one level, Mylae one snapshot, Demir none.

**The water brush measures.** Demir hard-codes a triple per layer; the sea
colour on `map_regions.tga` is declared in no record, so it is whatever the
author used and vanilla and DaC do not agree. It is the commonest colour among
the tiles the engine calls sea, per layer, with the count on screen - vanilla
measures `(41,140,233)` / `(0,0,253)` / `(196,0,0)` from 20,012 sea tiles.

**Closed palettes where a table exists, open where a rule does.** Regions,
ground types, features and climates refuse a colour outside their vocabulary by
name; heights, roughness, fog and trade routes are magnitudes, so their palette
is the map's own colours and the rule is said on the screen.

**The wizard's steps are questions about the pixels.** How many tiles carry this
colour, is there a settlement pixel this region owns, is there a port - counted
every time. Marker ownership is Gigantus's cardinal rule, the same one the index
uses, with the pending region counted as a region; proximity would have reported
the city next door as this one's. Every painted layer, the new record and
`map.rwm` go into ONE backup set, so the Log's Undo reverses the whole save, and
a plan compares BYTES rather than stroke counts - paint and undo back to the
start and there is nothing to save.

**Two things found by building it.** A session holds the `CampaignMap` it
painted and the registry drops that object when a file the map was read from
changes on disk, so a layer edited in Photoshop under unsaved strokes ends the
session and every answer from then on says so - better than a fresh one
appearing silently. And vanilla's `map_fog.tga` does **not** re-encode byte for
byte: whatever packed it wrote a five-pixel literal where `_rle_row` starts a
run, so ours is 11,327 bytes against 12,009, pixel for pixel identical and
settled on a second pass. RLE has more than one legal packing of a row; the
guarantee is the shape and the picture, and `maptga`'s docstring and
`test_campmap` now both say that instead of claiming the packing.

## 16d - layers, legend, inspector (2026-09-04)
`campmap.py` (+560), `web/js/campmap.js` (834 to 1,455), a `regions` kind in
`codeview.py`, four routes in `server.py`, and `tests/test_campedit.py` at
**85 checks, all passing** over vanilla's map and DaC's. The screen stops being
a viewer here.

**The layer stack is remembered**, in `map_layers` on `/api/settings` - the
`pane_sizes` road. Per user rather than per mod: the ten layer codes are the
engine's own and mean the same thing in every mod there is. A saved order is
reconciled with the manifest rather than trusted, so a layer this build no
longer lists is dropped and a new one goes where the server put it.

**16c's one deferred item, answered by the legend.** `map_features.tga` is 97.7%
black on DaC and 96.5% on vanilla, black there means "nothing here", and ticking
it at full opacity therefore hid the map under a black sheet with a few rivers
on it. `layer_legend` censuses the layer the browser was served, names every
colour from the vocabularies and flags the one that means nothing; the browser
punches that colour out of its own copy in one 4.4 ms pass, cached by the hide
set, and features and trade routes become overlays. **The claim and its source
live together in `BLANK`, and each entry says which it is.** `features` is the
arbiter's own `none`. `trade_routes` is black because vanilla marks 995 tiles
out of 54,760 and DaC marks none at all. `roughness` is black because the layer
is a greyscale magnitude. `fog` is white because that is 87% of vanilla's layer
and 98% of DaC's - and **nothing in the four references says which way round the
engine reads that layer**, so the panel says "the colour most of the map is" and
claims nothing more. The four layers with a real vocabulary have no blank colour
and are not offered the checkbox: black ground is `wilderness`, black heights is
sea, and a black region pixel is a settlement marker.

**The legend is the region list too.** The cap is 48 colours for a magnitude and
the engine's own 200 for `map_regions.tga`, so DaC's 202 all list with province
name, tile count and share of the map. A colour no table knows is listed as
that, which puts DaC's stray `(1,1,1)` feature pixel on the screen rather than
only in 16f's future report.

**The probe names one tile on all ten layers** - localised name first, code name
in brackets - in **0.17 ms warm on vanilla and 0.80 ms on DaC**. One small
request on the CLICK: the hover readout stays where 16c put it, answered in the
browser off the region layer it already has, because that one runs per pointer
event. The two pictures say they have no value at a tile rather than being
sampled at coordinates that mean nothing in them.

**The region record is editable, and an edit is one line.** Legion, creator
faction, rebel type, resources, triumph value, base farming level, religions -
spliced into the line each field came from. Asserted rather than claimed: **all
198 of DaC's records and all 112 of vanilla's re-render byte-exact with no
edits**, and one field edited changes exactly one line of a 1,990-line file,
CRLF, tabs and the modder's own trailing comments intact. A missing `legion:` or
resource line is inserted where the format puts it, at the indent its neighbours
use. Three fields refuse a rename with the reason - in the form, in the text
pane and at the plan: the region's name and the settlement's are keys
`descr_strat.txt`, the win conditions, the campaign script and every `legion:`
line point at, and the colour is the map's own pixels, which is 16e's.

**The religion rule is enforced twice** - live in the form and again at the plan
- because it is the one that crashes the game on load. A set that does not total
100 says by how much and is refused before a byte is written. Warnings are kept
apart from refusals and carry their sources: Geomod's "leave it at 5" for the
triumph value, "4 is average, 6-7 highly fertile" for farming, and 16f's rule
about a resource that is neither hidden nor a trade resource, brought forward to
where somebody can fix it.

Also here: neighbours from the label image (27 ms on DaC, four-connected,
markers skipped, and the panel says land bridges and river crossings are 16f's),
Code View over `descr_regions.txt` with a span per field, Ctrl+Z over the
working copy, and a save that backs the file up, writes the Log entry that
undoes it, and **deletes `map.rwm`** - or the game loads the compiled map and
shows none of the edit.

**Two faults found by building it, both 16c's, both browser-side.**
`cmapRepanel` re-ran the canvas's wiring as well as the panel's, so every layer
ticked added another set of pointer listeners to the same canvas: measured at
eleven, where a 10-pixel drag moved the map 110 pixels. 16c ticked rarely enough
to hide it; 16d ticks on every legend opened and every colour hidden. And the
probe's row class `cmprow` was already the compare screen's, four hundred lines
further down the same stylesheet, so its four-column grid silently won - **a CSS
class name is as global as a top-level JS name in this page, and now gets
checked the same way.**

Measured in the browser after both fixes, on DaC: a pan frame is 0.010 to
0.023 ms from zoom 0.4x to 64x, a hover step 0.18 ms, the composite rebuild
0.015 ms, the hide-set mask 4.4 ms and a region outline 8.2 ms - the last two on
a click, once, cached.

## 16c - the renderer (2026-09-04)
`web/js/campmap.js` (834 lines), the view half of `campmap.py`, two routes in
`server.py`, and `tests/test_campview.py` at **50 checks, all passing** over
vanilla's map and DaC's. The first screen in V3.

**Python decodes, the browser draws.** `/api/map` is one manifest and
`/api/map/layer` is one layer as PNG. Every layer with a relationship to the
tile grid is served at **one pixel per tile**, sampled the way the engine
samples it, so the composite is one canvas and a picked pixel is a tile;
`water_surface` and `map_FE` have no such relationship and come back at their
own size, saying so, rather than being quietly stretched by the server. Layer
PNGs are cached on disk keyed by mtime, through the icons' never-torn route.

**The numbers, measured in the browser on DaC.** A pan frame is 0.02 to 0.18 ms
across zoom 0.4x to 64x, against 16.7 ms for 60 fps. A hover step - the cell the
cursor left and the cell it entered, and nothing else - is 0.046 ms. Building a
region's outline, the one per-pixel pass in the file, is 5.2 ms on a 74,000-tile
region and it runs on the click, once, cached. First read 588 ms cold, 1.1 ms
warm.

**The picked pixel is the pixel under the cursor**, and that is asserted rather
than claimed: 792 checks over eleven zooms, four origins and both edges of a
tile; the zoom-about-a-point invariant in all twenty cases tried; and, read back
off the canvas at 24x, the centre of a settlement tile is `(0,0,0)` to the byte
with the region's own colour on either side.

**Picking costs no round trip, and the test says why that is sound.** The
browser reads the colour under the cursor off its own copy of
`map_regions.tga` and looks it up in the manifest by packed key. That works only
if the served PNG and the Python index agree pixel for pixel, so every region on
every installed map is checked at its own anchor: 116 of 116 on vanilla, 200 of
200 on DaC.

**Vanilla's map is a second real map, and 16a never saw it** - it is under the
game root, not under `mods/`, so `_realmod.installed()` misses it. 295x189
against DaC's 510x487, 116 regions against 200. Both are now under test.

**The sea heuristic, measured.** One pass over the label image and the sea mask
- 6 ms on vanilla, 43 ms on DaC - counts each colour's sea tiles, and it is what
tells the ocean from a hole in the mod. Vanilla has four colours
`descr_regions.txt` never declares and **all four are 100% sea**; three are
one-channel misses of the ocean's own `(41,140,233)`, the same lossy-paint slips
16a found in the climates layer. DaC's ocean is 73,904 of 73,950 tiles sea, and
its undeclared 517-tile province has **not one** sea tile in it - 16a's
inference, now a measurement. 16f owns the rule; this is its count.

**Two faults the tests found.** A layer the wrong shape came out of
`_owner_of_port` as an `IndexError` and a 500, because the sea mask and the
label image are one byte per tile and index each other; `require_grid` refuses
by name now and the manifest degrades to the layer list, which is the only thing
that says which file to fix. And the map was read through `Registry.get`, which
warms the unit databases first, so a mod that ships only a map could not have
its map read at all - `describe` now, the same fix Home's readiness report got.

**A dropped layer request is retried before it is believed.** One of three
layers asked for at once came back `ERR_CONNECTION_REFUSED` and the same URL
answered 200 two milliseconds later. After three tries the server is asked for
its sentence, and that answer is read as JSON only when the status says it is an
error.

## V3 planned (2026-09-03)
The Campaign Map Editor is scoped and written into ROADMAP.md as **Phase 16,
sessions 16a-16k**, plus V3.1 to V3.3 as future releases. Four references were
read end to end: `Reference/Map/Demir.html` (the validation rule set and the
campaign database editor), Mylae's `src/components/map/` at
`refs/upstream/editor/main` (the paint tool), `Reference/Map/TWMapReader_source/`
(the reverse-engineered engine behaviour) and Geomod's manual plus the TWCenter
mapping tutorial (the format arbiter).

**The rewrite is Pillow, not C++, and that is measured, not assumed.** On DaC's
real map all ten TGA layers decode in under 100 ms, the unique-colour census is
6 ms for 202 colours, the region label image 5 ms and the per-region pixel
counts 9 ms. `descr_terrain.txt` caps a map at 510x510, so the biggest layer any
mod can have is about a megapixel. Demir's tool lags because it repeats the work
- a full-image `putImageData` per Bresenham pixel of a drag, ~5.7 M array
allocations per painted water pixel, an O(lines x objects) validator after every
edit, and the whole of `descr_strat.txt` re-parsed eight to ten times to save one
faction detail. Ported to C++ that is still wrong. The fix is a label image built
once, dirty rectangles, parse-once-splice-after, and nothing O(pixels) on the
interaction path.

**Two names are already wrong and 16a corrects them.**
`unittransfer/stratmap.py` is the `descr_model_strat.txt` cleaner, not the
campaign map, so the map modules are new files; and Mylae's `parseDescrRegions`
silently drops **every DaC region**, because DaC's records carry a `legion:`
line and his parser hard-codes RGB at line offset 4.

The format facts banked from the read - layer size rules, the sea-is-not-
greyscale test, the `(2t+1, 2t+1)` centre sampling, the TGA descriptor byte M2TW
crashes on, port ownership, region ID derivation, the 200-region cap - are all
in Phase 16's preamble in ROADMAP.md rather than repeated here.

## 16b - descr_strat.txt, read (2026-09-03)
`unittransfer/campstrat.py` and `tests/test_campstrat.py` at **75 checks, all
passing** over vanilla's two campaigns and DaC's. The file the whole campaign is
defined in, as a tree of line spans.

**Lines plus an index, never objects plus a serialiser.** Every node carries the
line it starts on, the line it ends on and the line each field came from;
`serialise()` joins the lines back. All three real files round-trip byte-exact,
DaC's included, and DaC's has no trailing newline, which a serialiser that
rebuilt the file would have quietly added. Demir's tool re-parses the whole file
after every edit, eight to ten times to save one faction detail, and it can
afford to only because it throws the formatting away.

**One pass, 144 ms, 6,100 nodes**, and every scoped count matches: 31 factions,
199 settlements, 1,044 buildings, 305 characters, 286 armies, 1,468 units, 161
character_records, 79 relatives, 812 standings, 57 relationships, 126 regions,
105 forts, 295 watchtowers, 1,131 resources. Every settlement and every
character resolves to a faction, 199 of 199 and 305 of 305.

**The interval index needs no sort at all.** A node is appended the moment its
first line is read, so the node list comes out of the parse already in document
order and a block plus its contents is contiguous in it. `node_at` is a bisect
plus a walk up the parents; `descendants_of` is a bisect plus a slice.

**Three pieces of format knowledge added.** `undiscovered` is a faction flag,
found in vanilla on the Aztecs. `character sub_faction <faction>, <name>, …` is
a real character form, and it is why reading that line positionally fails.
And brace depth must be counted on the line **with its comment stripped**:
Mylae's `factionBlockOps.js` has the depth rule, which is the right rule, but
counts braces on the raw line, so a commented-out brace shifts it. Depth is what
tells a settlement's own `region` field from the regions section at the bottom
of the file, and nothing else can.

**Nine lines in DaC do not parse and all nine are the mod's own.** A trailing
comma (3747), Sauron with no `age` (5376), `settlement tyuiop` (8464),
`named character, general` twice (9703, 10438), `rmour` for `armour` three times
(9983, 10947, 10948) and a truncated `weapon_lv` (10581). Vanilla has none. Each
is read as far as it can be, kept in the tree, and reported by line number,
because a parser that refused any of them would refuse DaC.

**One caveat.** Neither vanilla campaign contains a single `fort`, so the short
`fort <x> <y>` form is covered only by the synthetic half of the suite. DaC's
105 forts are all the long form.

## 16a - the map files, read (2026-09-03)
`unittransfer/maptga.py`, `mapvocab.py` and `campmap.py`, plus
`tests/test_campmap.py` at **62 checks, all passing** on DaC (61 in 16a; 16d
widened the probe's). The read half of
the map editor's engine: nothing paints, saves or validates yet, and everything
that will stands on the index built here.

**The header is ours, the pixels are Pillow's.** `maptga.py` parses the 18-byte
TGA header itself and hands only the pixel data to Pillow, because the header is
where the game is fussy: TWMapReader's author recorded that M2TW *crashed* on
descriptor `0x18` and `0x20` and that `0x08` is what works. DaC's ten layers are
nine RLE and one uncompressed, two descriptors, one with an ID field, and every
one with a v2.0 footer. All ten now **re-encode byte for byte identically**,
RLE included, which was not a design goal so much as the proof that nothing is
being quietly reshaped. `water_surface.tga` also carries a 495-byte extension
area addressed by an *absolute file offset* in the footer, so a layer that
re-encodes to a different length has that offset moved; without that the file is
broken in a way nothing would notice until the game read it.

**`descr_regions.txt` is positional, and the anchor is the RGB line.** Mylae's
parser hard-codes the RGB at line offset 4, so its resync guard silently drops
**every DaC region** - DaC writes the ten-line `legion:` form. Here the `R G B`
line is found by shape, the three lines before it are settlement, creator and
rebel type, and what follows is resources, triumph value, base farming level and
religions. 198 records read, 197 of them in the legion form, the file
re-serialises byte-exact with its CRLF and tabs, and every field carries the
index of the line it came from so an edit in 16d is a one-line splice.
`edbvocab.regions()` now delegates here rather than keeping a second parser: its
own copy found the resource line by looking for the first comma, which is right
until a region carries a single resource.

**The index, and the two rules nobody else implements.** Region IDs are the
order a colour is first met scanning row-major, skipping settlement and port
pixels *and* skipping tiles that `map_regions` calls land while `map_heights`
calls sea; ports belong to the land opposite their dock, by the cardinal rule
Gigantus established. On DaC: 202 unique colours, 199 settlement pixels, 77 port
pixels, ids contiguous 0-199 and identical across two independent reads, every
port resolving to an owner. About 450 ms for the whole read, once, at load,
and nothing O(pixels) anywhere near an interaction.

**Two of the scoping numbers were wrong and measuring corrected them.**
`Image.quantize` with a fixed palette builds the label image in 3 ms and is
approximate - it put 1,320 of DaC's 248,370 pixels on the wrong region even with
every colour of the image in the palette exactly - so the label image is an
exact dictionary pass at 61 ms instead. And the sea rule's evidence was
misstated: 165 of DaC's 420 height colours are non-greyscale, of which only 19
are `(0,0,B)` blues. At tile centres, where the rule is actually applied, it
agrees with ground types on 99.9% of tiles.

**Four defects found in DaC, all now 16f's test cases.** The stray `(1,1,1)`
pixel in `map_features.tga`; five colours in `map_climates.tga` that no climate
declares (10 pixels, each a one-channel miss of a real climate); a 517-pixel
region painted `(100,160,100)`, one channel off `Dunland_Province`'s
`100 150 100`, that `descr_regions.txt` never declares; and the settlement pixel
standing inside it at image (339,65). The index reports each of them rather than
rounding it to the nearest sensible answer.

**One inference is ours and says so in the source.** DaC's port at image
(75,107) has a settlement pixel on its land side, so the dock rule returns black.
It is resolved through the marker to that settlement's region; no source states
this, but 77 of 77 ports find an owner with it and 76 without.

## v2.1.11
**A subrelease, same standing as 2.1.2 through 2.1.10.** One ask with a long
reach, one piece of wording, and a sweep.

**Every panel resizes** (`web/js/core.js`, the `rsz*` block beside
`splitInstall`; `::-webkit-resizer` and `.drawergrip` in index.html). Every
scroll box on the page gets `resize:vertical`, the dialog gets `resize:both`,
and the drawer gets a hand-rolled left-edge bar because its right edge is
pinned and the browser's own corner would drag it off the screen. Sizes live
in `pane_sizes` on `/api/settings`, keyed by a box's `id` or its classes and a
dialog's class, clamped to the window on the way back in.

**The boxes find themselves.** A scroll box in this stylesheet is a rule that
sets `max-height` and `overflow:auto` together and there is no second kind, so
`rszSelectors` reads `document.styleSheets` once at startup and collects the
31 selectors that do - which means a list written next month is resizable the
day it is written. `.wpop` is skipped (a menu that closes on the next click
must not carry a remembered height) and `.modal` is skipped because
`rszModal` sizes it in both directions instead.

**Two things the browser gets wrong on its own, and the whole of the code is
undoing them.** A `max-height` outranks the `height` a drag writes, so the
ceiling is cleared on `mousedown` in the corner, in the capture phase, which
is the last moment before the browser starts its own drag - without that the
first drag on any box did nothing and only the second appeared to work. And
these screens rebuild wholesale (a keystroke in the pool filter replaces every
row), so a `MutationObserver` on `document.body` puts the size back on the
element that replaced the one that was dragged. That observer coalesces on a
**`setTimeout`, not `requestAnimationFrame`**: a window the OS considers
occluded is given no frames at all, and a dialog opened behind another window
came up with none of its boxes wired. Nothing is touched until it is dragged,
so an untouched screen lays out exactly as before.

**"<name>.txt is newer"** (`web/js/strings.js`) was a comparison of two file
dates presented as a warning, with no statement of what was wrong. It now
reads "…is newer than this .bin" and carries a `qm()` card: the game reads the
`.bin`, the `.txt` was saved after it was built, so what the `.txt` has been
made to say since is not on screen in the game - which is usually how the mod
was written and not a fault at all.

**No em dashes.** 4176 of them across 171 tracked files, swept to plain
hyphens in one pass - every occurrence was ` - `, a dash left at the end of a
wrapped line, or a lone dash standing for "nothing here", and a hyphen is
right for all three. `tools/prose_check.py` grew `ANY_EM`, which scans whole
files rather than UI strings, so one that comes back is a reported hit.

**Also in the build:** battle-model-entries-only transfers (`models_only`,
`GET /api/unit_models`, `transfer.unit_model_index`), a swatch-plus-hex colour
picker on the faction editor that no longer closes the OS picker on every
drag, a player-visible name for a newly cloned unit, and the OS folder dialog
raised to the front from a watcher thread instead of opening behind the
browser.

## v2.1.10
**A subrelease, same standing as 2.1.2 through 2.1.9.** Three asks: the model
beside a transfer, the building's art beside a recruit pool, and that pool's
row laid out as two halves instead of four columns.

**The 3D column, over the composer** (`web/js/transfer.js`, `cmpPrev*`; the
`#cmpSplit` wrapper in `renderComposer`). The third host for `v3Mount` after the
unit editor's and BMDB's, and a copy of the editor's shape rather than a
refactor of it: the three differ in what they list, which mod they draw it from
and which setting turns them off, and the shared part is already `v3Mount`
itself. The three careful things are the editor column's three - the canvas is
DETACHED across a re-render rather than rebuilt (`renderComposer` runs on every
tick box, so rebuilding would refetch a 30 MB mesh per click), there is only
ever one viewer on the page, and folding pauses the draw loop without giving up
the mesh.

**What it lists is BOTH MODS.** A transfer is the one screen where the models on
the page belong to two different mods: the source unit's entries, and - once a
base or replaced unit is picked - that unit's own out of the destination, each
`<optgroup>` labelled with where it came from and `v3Mount` handed the mod per
entry, not per screen. "Is this the unit I meant to overwrite" is what the
replace mode exists to get wrong. The entry list is derived from the UNIT LIST's
fields (`models`, `soldier_model`, `armour_ug_models`, `officers`) rather than
the editor's payload - the composer never loads a unit detail - and it applies
the editor's own rule about `armour_ug_models` on top, plus one the editor does
not: the men before their officers, since `model_names()` reads the soldier line
first and a unit whose soldier line was dropped would otherwise open on its
standard bearer.

The composer goes `modal wide` whenever the column is on (a model squeezed
beside a 640px dialog is not a model), the choice rides on
`state.settings.transfer_preview`, and the column is given up - context, loop
and node - by `closeModal`, by `doApply` before the progress card takes the
modal, and by `openComposer` before it rewrites the modal for the next unit.
`v3Open`'s markup stash detaches it for the same reason it detaches the
editor's.

**Building art on the Recruitment tab**, and the culture question it opens.
A tier's picture is `/building_icon`, which is keyed by CULTURE - and this tab
is not showing a culture: its rows come from every building line in the mod. So
the row's own `requires` answers it, through `ov.faction_cultures`: a pool gated
to `factions { aztecs, }` wears what those factions build. Measured on DaC,
that alone was not enough - a mod-invented level like `ancestral_dun` is drawn
for exactly ONE culture, and every other row would have been a placeholder.

`buildings.find_icon` gained `any_culture`, off by default: after the picked
culture's own art and its vanilla fallback, it sweeps the mod's other culture
folders. It stays OFF for the building browser, which is showing one culture on
purpose - a level that culture has no art for is a fact about that culture, and
the grid says so - and the Recruitment tab and its ＋ picker pass `&any=1`.
Verified against DaC: all six of a Dunlending unit's tiers answer `mod` where
`greek` (the browser's last culture) answered `placeholder` for every one.

**The pool row is two halves, not four columns.** WHAT it sits on - the art, the
line's name, the tier - is the left of the top line, touching, because "a
barracks" and "which barracks" are one answer; the numbers hold the right,
pushed there by a new `.ernums` wrapper and still at a fixed width. WHO may use
it is the second line, right-aligned to end where the numbers and the row's
buttons do, growing back leftwards across the full width when a clause needs it.
`.erb` stopped being `flex:1 1 150px` - a growing name column is what put the
tier at the far end of the row's slack. The header's own `.eract` now reserves a
button's width, which is what it takes for "the header labels sit over the boxes
they name" to be true; they had been 33px to the right of them since the tab was
written.

`tests/test_buildings.py` grew section 11 - four checks on the sweep against a
planted two-culture art tree: off, a culture with no art for the level is a
placeholder; on, the one culture that draws it supplies the art; the culture's
own art still wins when it has any; and a level nobody draws is still a
placeholder. `test_buildings_http` checks `&any=1` is accepted. Suite: 72 of 72
modules, all green.

## v2.1.9
**A subrelease, same standing as 2.1.2 through 2.1.8.** One ask and the tail of
the session before it: recruitment reachable from the unit, and the UV layout
beside the model.

**Recruitment is a tab on the unit** (`web/js/edrecruit.js`, new; the
`?building=&lvl=&unit=` route in `core.js`; `.erpool` and the ＋ picker's styles
in `web/index.html`). Everything a unit IS was on four tabs; where it can be
HIRED was in another module, reached by leaving the unit, finding one of the
four or five building lines that train it, and reading its numbers off a row
among sixty. The building browser already had the panel that puts those rows
side by side (`bldShowUnit`) - this is that view from the unit's side, and
editing: all four pool numbers, the `requires` clause, a 🗑 that takes the pool
off the building, and a ＋ that puts the unit on a new one.

**No Python.** A `recruit_pool` line already had a reader
(`buildings.unit_instances`) and a writer (`buildings.plan_edit`), and this is a
second FRONT for them rather than a second implementation - the same capability
ops, the same clause dialog, the same plan → apply road - so a pool edited from
the unit and one edited from the building cannot drift apart. The one shape that
had never been sent before is the request: this tab reaches into several
building lines at once and belongs to none of them, so **every** edit rides in
`also` and the main body carries a line name with an empty `levels`. That is
also the right way round for the recruitment-limit check, which merges the
file's existing pools for an `also` line and would otherwise count a payload of
three rows as the whole level. Measured against both installed mods, one Save
over three building lines wrote exactly its three edits, moved nothing else, and
one Undo restored the EDB byte for byte.

**The clause dialog is borrowed, not copied** (`kind:'edrec'` in
`bldClauseApply` / `bldClauseCancel`). It could not take the usual route: it
stashes the modal as MARKUP, and the unit editor holds a live WebGL column
inside that modal, so putting the string back would install a dead copy of the
canvas and orphan the real one. The two `edrec` branches re-render the editor
from state instead, which hands the column over the way a tab switch does. Same
reason the ＋ picker keeps no stash. `loadBuildings` also stopped writing
"Reading …'s buildings…" into `main` when a dialog is open over it - this tab
asks for the overview from behind one, and the message was what you found on
screen the moment you closed the editor.

**A building is one click away, in its own tab.** `?building=&lvl=&unit=` opens
the Buildings module on that line, at the tier the pool sits on, and flashes the
unit's rows (`bldJumpPool`) - a barracks trains sixty units and scrolling for
the one you came for is the step the link exists to skip. And because a
recruitment save moves EDB line numbers, a building left open behind the editor
has its working copy dropped rather than carried back into it: its capability
rows are numbered against the file as it was, and `backToBuilding`'s comment
that "a unit edit never touches the EDB" stopped being true the moment this tab
could write one.

`tests/test_unit_recruitment.py`, 42/42 across DaC and Reforged: the row payload
carries every field the tab keys on, `cap_line` is unique, an `also`-only request
plans, a rewrite moves no line and leaves the 173 capability lines it never
mentions byte-identical, and rewrite + delete + append across three lines come
back as three changes with the other two lines named.

**The UV layout, beside the model** (`web/js/viewer3d.js`, `.v3uvpane` in
`web/index.html`). `Show UVs` paints the coordinate onto the MODEL; this is the
other half of the same question - the SHEET, with the mesh's islands drawn over
the art they sit on, which is what a UV editor shows and what a retexture is
actually done against. A 2D canvas, not a second WebGL context: the drawing is
one image and a few thousand lines, and a second context is a second copy of the
mesh on the GPU for a picture the CPU draws in a millisecond.

**It is drawn in the BOUND IMAGE's own space**, not in the mesh's u: one square
per sheet, at the aspect the art really is, with the UVs put through the same
scaling the sampler puts them through to land on it. A pair is two squares side
by side; a mount's lone sheet is ONE square, and the two units of u its mesh is
written in are half a square each. Framing on the mesh's u instead drew a 1024
square sheet across two tiles - a picture of the coordinate rather than a
picture of the art, and stretched art is exactly what this view exists to catch.
**v goes down**, because M2TW is Direct3D and the texture is bound unflipped, so
the sheet is drawn from its top-left at (0,0) and an island sits over the art it
names rather than its mirror. Nothing is folded into 0..1: an island running
past the sheet is drawn where it lands, on a repeat dimmed to 30% so that
leaving the sheet reads as leaving it.

One colour per part, on the island and on that part's row in the list, so the
two can be read off each other; only the groups the viewer is DRAWING are drawn,
so a variant swap or a hidden slot changes the map with it (three heads laid
over one sheet is not a UV map). Click picks by testing every drawn triangle -
exact, where a nearest-island guess is wrong on overlapping shells - and names
the part, its u/v box, and whether it leaves the sheet it was authored in; the
cursor readout gives u, v, which sheet, and the pixel. Side by side with the
model when there is room for two; docked, or under 1100px, the layout takes the
stage and the button is the way back. `v3Draw` now returns on a zero-size canvas
rather than sizing to a made-up 640, which is what that takeover leaves behind.

Verified in-browser against DaC: `lossarnach_ug0` (a real pair - picking
returned `hair`, `head`, `eyes`, `clap` from their own centroids, zoom held its
anchor to 4e-4 of u, and the caption read `head u 1.33–1.55 · v 0.73–0.87`), and
`mount_naru_horse` (one texture, and the case below).

**Every mount in every mod was drawn with its texture tiled twice** (`v3Apply`,
`v3TexCase`). Chasing the UV layout's framing of a horse turned up a bug in the
RENDERER, not the drawing: the layout was faithfully showing a space the shader
had wrong. There are **three** shapes an entry's texture set comes in and the
viewer knew two:

  * a real pair, glued here - u halved, as always;
  * an entry that **names** an attachment and it is the main file again (which
    mods write constantly - it is what the Blender addon exports for an empty
    slot) or one the mod does not ship. The game glues two sheets, so the art
    repeats every unit and binding the one sheet at FULL u reproduces
    main-glued-to-main exactly. This is the case the old comment described, and
    it stays;
  * an entry naming **no** attachment texture at all - every ordinary mount.
    There is nothing to glue and no far half to reach, so its one sheet spans
    the whole two-unit space and u must be halved TOO. It was not, and that
    tiles the sheet twice across the model.

The two were collapsed into "one sheet or two", and the empty slot took the
wrong branch. With `uUScale` telling the truth again, `Show UVs` needed no new
period after all - its dimming and its red line go back to keying off that one
uniform, and the only thing it gained is `uPair`, because "how far was u scaled"
and "are there two sheets to tell apart" had quietly become different questions. **Measured, not reasoned**: map each triangle's texel-space edges
onto its own 3D plane and the singular values of that Jacobian say how far from
square its texels are. Whole models, median -

| entry | attachment slot | full u | half u |
|---|---|---|---|
| `lossarnach_ug0`, `ox_mount`, `crag_warg_riders` | real pair | **1.21–1.24** | 2.02–2.04 |
| `mount_naru_horse` | empty | 2.00 | **1.08** |
| `anorien_barded_horse` | empty | 2.02 | **1.18** |
| `mount_eastern_armoured_horse_grey` | empty | 2.22 | **1.47** |

The pairs are the control and they answer the way they must; the mounts invert,
and the 2.0 is the factor of two standing up to be counted. Confirmed against the
art as well: `mount_naru_horse`'s groups, halved, land exactly on it - Body
0.005–0.662 on flanks painted across x 0–0.66, `armor` 0.017–0.463 on barding at
x 0–0.47 (and its v 0.271–0.567 matches that band untouched, which is what pins
the axis that was never wrong). On screen the barding stops being striped and
becomes plates, and the layout's islands sit on the art they name.

So `uUScale` is 0.5 whenever what is bound SPANS the two units and 1.0 only for
the glue-it-to-itself case, and the parts list stops labelling half of a lone
sheet an "attach sheet" when the entry carries no such texture - it says "right
half" instead. Those labels are repainted from `v3Apply` as well as from the
render, because a skin arrives after the panel is drawn and the panel would
otherwise be describing a pair as a lone sheet. v2.1.8's "a lone sheet's pair
boundary is every integer u" was true only of the case that names one.

**The unit editor's preview picker drops the `soldier` line's model when the
unit has `armour_ug_models`** (`edPrevEntries`). The engine draws the upgrade
list, one model per armour level, and never that entry: Uruk-hai Bodyguards
names `heavy_uruk_sword` on its soldier line and puts `isengard_bodyguard` in
both upgrade slots, so the picker was offering a model the unit is never seen
in. The test is per MODEL, not per unit - Uruk Bodyguard's
`mordor_uruk_bodyguards` is the soldier line AND upgrade 1, and an entry earns
its place by any slot that is not the soldier line. A unit with no upgrade list
is the other way round and keeps it, and the list can never come back empty.

**The docked viewer's canvas is resizable** (`v3GripDown`, `.v3grip`). The column
already had a draggable left edge; inside it the canvas sat at the stylesheet's
240px floor and took whatever a twenty-one-row parts list left, which on a tall
model is a letterbox. The bar under the canvas drags that boundary and the height
persists (`v3_dock_px`), double-click restores the default. It sizes the STAGE,
not the controls: the docked column is as tall as its contents, so giving the
controls a height grows the panel and leaves the model exactly where it was -
measured, after the obvious way round moved nothing.

## v2.1.8
**A subrelease, same standing as 2.1.2 through 2.1.7.** Two asks in one session,
both extending a module that already existed, and neither of them a bug.

**A faction can be added, by cloning one that works** (`unittransfer/factionclone.py`,
new; `/api/factions/clone_plan|clone_apply`; the **＋ Add a faction** dialog in
`web/js/factions.js`). Phase 11 shipped the Factions editor with a written
refusal - a slot lives in nine files, so one that exists only in
`descr_sm_factions.txt` is a mod that will not load, therefore no create. Right
about the problem, wrong about the conclusion: the answer is to write them all.
**Twelve, as it turned out.** Grepping the installed mods for a slot found
`export_descr_buildings` (the `requires factions { … }` clauses that let a
faction build and recruit at all), `descr_sounds_accents` and
`descr_faction_standing` on top of the nine that docstring listed - a plausible
number nobody had measured, which is the kind this project does not keep. Every
surface that said nine now says twelve.

TWCenter's own step-by-step (`Reference/TWCenter/Creating a world - adding a new
faction/`) is the spec, and its method is why this is safe: **it never invents a
value.** Every step is "find where the donor is named and name the clone too,
with the same value", so there is no question of what colour or roster the new
faction gets. Nine cloners rather than one search-and-replace, because the
donor's name is doing something different in each file - a record to re-head, a
section to copy, a braced block, a shared comma list to join, length-prefixed
texture records. Art is **found, not listed**: anything under `ui`, `menu` or
`banners` carrying the slot as a token. One transfer id covers the lot, so undo
puts the whole faction back out of existence in one go.

**Three files name the donor as a judgement** - a trait named after it, an
ancillary's `FactionType` operand, a prebattle speech - and are counted and
reported, never appended to. `descr_strat` is reported and not written for the
same class of reason: two factions cannot start in the same settlement, so there
is no donor answer that would still be right. **Deleting stays refused**, and
now for a sharper reason than phase 11's: a clone copies the donor's answer, a
delete would have to invent one.

Four bugs the tests caught, each worth remembering: the game files are **CRLF**
and `$` sits after the `
` (three cloners matched nothing, two ate the `
`);
`_` is a word character in a data file and a **separator** in a text key (one
boundary found `{SICILY}` and none of the sixty `EMT_` keys); `add_texture_factions`
reads **one entry's** raw text, not the file (handed the whole modeldb it finds
no groups - a clone with no skins); and a file may spell the same list two ways
(`descr_faction_standing` writes both `factions { … }` and `exclude_factions
{ … }`, and DaC has 164 of the first and **none** of the second, so matching only
the second would have cloned nothing at all in one of the two installed mods).
`tests/test_factionclone.py` 64/64 against the real mods, read-only;
`tests/test_factionclone_apply.py` 30/30 writes a synthetic mod and undoes it
byte-exact. That second suite exists because `transfer.undo` deletes a created
path with `unlink()`, which raises on a directory and is swallowed - so copied
art is listed in the manifest one file at a time, never as a folder.

**Show UVs in the 3D viewer** (`web/js/viewer3d.js`). Paints the UV coordinate
instead of the art in the same space the sampler uses, so the tiling the shader
comment has always described is visible: blue main sheet, amber attachment
sheet, dark for the repeats, red where the pair restarts. 32 checker cells to a
sheet is **measured, not picked** - real parts span 0.07 to 0.33 of u each, so a
coarser grid gives a head less than one whole cell and says nothing about it.
Verified in-browser on a real pair (body main, bow and quiver attachment) and on
a lone-sheet mount, which correctly shows no amber and drops that row from the
legend.

## Previously (v2.1.7)
**A subrelease, same standing as 2.1.2 through 2.1.6.** Both halves are the
modeldb reader being wrong about a file that was not, and they arrived together
from two mods on one evening.

**An attachment texture's sprite slot can hold a name** (`modeldb.get_attach_sprite`).
It is a bare `0` on very nearly every entry of every mod, and the reader had that
written down as the only value the field could take - a number there was "not a
length, because there is no name for it to be the length of". Thera_Redux and
BOTET each put a real `unit_sprites/....spr` in one. Read as names, both files run
to a clean EOF and round-trip byte-exact, which a desynced read does not do across
another eight hundred entries; the TWCenter syntax checker in `Reference/` walks
attachment groups with the same routine it walks body groups, for the same reason.
Worth noting where the old rule was NOT enforced: every span walker in this file
already read that slot with plain `get_string`, so the entry reader was the odd one
out and this puts it back in line with them rather than away.

The `01` case the guard was written for is real and still refused. The two are told
apart by looking rather than by rule: a sprite is a `.spr` path that fills exactly
the characters its length claims and stops on whitespace, and a stray digit's
"name" is none of those three. `tests/test_modeldb_attach_sprite.py` carries both
mods' real sprites as fixtures, plus `5 horse` - a self-consistent name that is not
a sprite - so the discriminator is pinned as "it is a sprite path", not "the
arithmetic works out".

**Evidence outranks inference in the desync message** (`modeldb._desync_message`).
A wrong count and a wrong length land the reader in the same place, and the message
led with the count in both cases: `e.note or _suspect(...)`. `_suspect` reports a
length the reader WATCHED overrun its own name; the note is worked out from where
the read stopped. So the sighting goes first now. BOTET's `mount_elephant_rocket`
is why: its count of 2 is honest and a normal map's length is written 64 for a
61-character name, and the old sentence sent its owner to delete a texture group.
`_suspect` also measures the rest of the line when a name ran off the end of one,
which is the number to type - hedged deliberately, because paths in this file
contain spaces (`Final European Light_hre_diff`) and that measurement is where the
name probably ends, not where it certainly does.

A third thing fell out of pointing the suite at a real file:
`tests/test_modeldb_header.py` asserted `entries + 1 == header count`
unconditionally, and a modeldb with no leading `blank` sentinel counts every entry
as real. Thera_Redux is one, so the check failed on the mod rather than on the
tool. It now uses the same rule `ModelDb.to_text` writes back with.

## Earlier still (v2.1.6)
**A subrelease, same standing as 2.1.2 through 2.1.5.** Three things, and the
first two are one thread.

**The M2EX mark did not survive being read back.** `modflags` stores it per mod
folder and accepted either a Mod or a bare path; the bare-path branch was
`getattr(mod, "root", mod)`, and a `Path` HAS a `.root` - its anchor, `\` on
Windows. So every path-shaped read keyed to the drive root of the working
directory: one shared row for every mod on the machine. `/api/mods` is exactly
that read, which is why ticking the box looked right (answered from a Mod) and
the next fetch of the mod list showed it clear. `modflags._root_of` now only
treats `.root` as a mod root when the thing is not a path. The regression test is
in `tests/test_modflags.py`, and it is the two-readers-agree shape: off a Mod,
off a Path, off a string, and no row keyed to a drive root.

**Projectile effects now travel to an M2EX destination** (`unittransfer/effects.py`,
`transfer._plan_effects`). Effects were never ported, for a good reason: they live
in four files shared by every projectile in the mod, and how many the engine loads
is another hardcoded table - what is past the end is dropped silently. M2EX
replaces that table, so for a destination marked for it the set block, the effects
it lists and the `.CAS`/texture files those name are copied, each block back into
the file of the same name it came from (which file a set lives in is what it MEANS
to the engine). A set the SOURCE does not declare is still placeholdered - it is
vanilla's and not ours to move.

Two things about real effect files that the old scanner got wrong, and that any
future reader of them must not: `effect_set < 3 4 > name` declares one body of a
set per graphics-detail band and the NAME follows the brackets (the old regex
recorded seven sets per stock mod as `<` and dropped the real names, so a
projectile pointing at a set the destination DID define was blanked anyway); and
DaC's impacts file leaves a brace open, so a block ends at the next header or at
depth zero, whichever comes first.

**A unit added to a building's recruitment lands at the top** (`bldAddPoolRow`).
Display order only: the server appends every new capability above the block's
closing brace whatever order the list is in, and edits existing lines in place by
the EDB line they came from, so the file is byte-identical to what the old push
produced. A batch keeps its pick order.

## Before that (v2.1.5)
**v2.1.5 IS A SUBRELEASE, same standing as 14j, 2.1.2, 2.1.3 and 2.1.4 - real
features, not folded into Phase 16 because Phase 16 (the Campaign Map Editor) is
a different program.** All of it is the modeldb cleanup deciding what is dead,
and being wrong about it. It came out of a mod that stopped launching after a
clean-up; chasing that turned up three separate places where a model the game
genuinely needs was invisible to the scan.

**`change_battle_model` is read** (`bmdb.script_models` /
`_BATTLE_MODEL_KEYWORD_RE`). The script command that swaps a character's model
mid-campaign broke both existing patterns at once: the bare-word one never fired
because the character before `battle_model` is `_` rather than a space or comma,
and loosening it to fire would have captured `turks` - the faction, because this
form puts the model on the END. So the keyword is matched with whatever prefix it
carries and the prefix decides where the model sits; taking the LAST argument
rather than the third also keeps a two-argument variant working and reads an
unknown future `*_battle_model` command as a command instead of ignoring it. An
entry named only this way is invisible to every other net here - no unit fields
it, no mount or `descr_character.txt` names it - so it reads as textbook dead
weight. 17 occurrences on Divide and Conquer, naming three models, one of which
exists nowhere else in the mod.

**Campaign files are found where mods actually put them** (`bmdb.campaign_files`,
`luascan.mod_files`). The old walk listed the immediate children of
`data/world/maps/campaign/`, which misses a custom campaign (`campaign/custom/<name>/`,
one folder deeper), a custom battle (`world/maps/battle/custom/<name>/descr_battle.txt`,
a file kind never opened at all), and an installer's alternate trees (`Activate/`,
`extra/`) - copies now, the live mod the second somebody runs the mod's own
switcher. The whole mod root is walked instead: 2 campaign files became 15. Each
is labelled by its path inside the mod, because the parent folder stopped
identifying a file once those two filenames turned up in six trees.

**One tree walk, not four** (`Mod.scanned_files`). `lua_files` already walked a
hundred thousand files and kept only the `.lua`; it now keeps the campaign
scripts and the text files too, and three callers take three slices of one cached
answer.

**🧹 Clean up BMDB → Recheck past cleanups** (`bmdb.recheck` /
`revert_recheck`, `GET /api/bmdb/recheck`, `POST /api/bmdb/recheck_revert`).
Every other net answers "may this go?" before anything moves; this answers the
question that only comes up afterwards, with the game already refusing to launch.
It cannot be part of the audit and that IS the point: the audit describes the mod
as it is, and a file that is gone is not in the mod to be described - the only
surviving record it ever existed is the cleanup's own log entry. So it reads the
log, re-derives what each run removed, re-tests all of it against today's nets,
and says whether a copy survives to put back. Reverts go through the same
backup-and-log machinery as every other write here, so a wrong revert is itself
undoable. A run whose backup AND export folder are both gone is still reported -
the log remembers - but marked unrecoverable, with no button that would fail.
A cleanup now also **writes down which entries it removed**, so that stays
answerable after the backups are gone; older runs are recovered from the export
folder's `removed_battle_models.modeldb`, or by diffing the backed-up modeldb.

**The mod's other `battle_models.modeldb` files stay ignored, on purpose.**
`battle_models.modeldb.bak`, `battle_models_og.modeldb`, a working copy under
`from_modeldb/` - they look like a second opinion about which meshes are alive
and are not one: each is a snapshot of an OLDER state of the same file, so
honouring them would hold alive every file the mod has ever used and no cleanup
could free anything again. Never read, never token-scanned as text either (a
modeldb names thousands of files, so reading one as text makes every file in the
mod "mentioned somewhere"). New is that the reasoning is written at the skip, the
Recheck dialog states it on screen, and a test pins it.

**The text scan streams** (`bmdb.unit_model_refs`). Holding a whole file plus a
lower-cased copy of it is a `MemoryError` on a mod carrying
`data/sounds/Music.dat` - two gigabytes - and the server returned a 500 with the
scan half done. `.dat` was the mistake and is out of `TEXT_SUFFIXES` (in M2TW
that suffix is the engine's binary containers), but the fix is the scan: a line
at a time, so no file can double itself whatever its suffix claims, with a
NUL-byte sniff skipping anything else binary. Line numbers fall out for free.
292s → 22s; the whole recheck 356s → 26s.

Also **`app.py --no-browser`**: serve without throwing a tab at the system
default browser, for anything driving the UI itself. The "no browser loaded the
page" warning is suppressed under it, because there that is the expected outcome.

**The release zip has the vanilla building art in it again.** v2.1.1 to v2.1.4
all shipped WITHOUT `vanilla_ui/` - ~19 MB instead of ~54 MB - so Buildings mode
showed a placeholder for every icon a mod doesn't ship its own copy of, which is
most of them. The cause was that bundling it was an opt-in flag
(`--with-vanilla-ui`) and it was forgotten four releases running. It now ships by
default (`BUNDLED_DIRS` in `build_release.py`), a missing `vanilla_ui/` stops the
build with a `SystemExit` instead of logging a shrug, and `assert_bundled()`
reads the FINISHED ZIP back and refuses to hand over one without the art -
because every earlier step can be right and the artefact still wrong.
`--no-vanilla-ui` remains for a deliberately slim build; nothing routine passes
it. **A portable release zip is ~50–55 MB; ~19 MB means the UI is missing.**
The rule is written down in `HANDOFF.md` under STRICT RULES, along with "release
means do the release, all of it, including the upload".

Notes: `merge/RELEASE_2_1_5.md`. `tests/test_bmdb.py` 104 → 143 checks.
Suite: 68 of 68 modules.

**The one rule that carries the risk in this release:** the recheck is only as
good as the nets behind it, so a clean verdict must never read as more than it
is - it means nothing a past cleanup removed is named by anything THIS BUILD
reads. The dialog lists exactly what it read and how much of it, so the verdict
can be checked rather than believed.

**v2.1.4 IS A SUBRELEASE, same standing as 14j, 2.1.2 and 2.1.3 - real features,
not folded into Phase 16 because Phase 16 (the Campaign Map Editor) is a
different program.** All of it is the tool getting out of the way.

**The browser's Back button steps back through the toolkit's own screens** rather
than out of the page (`web/js/core.js`, `NAV_LAYERS` / `uiBack`). No recorded
history is replayed: every layer already knows how to close itself, so a press
asks the layers innermost-first "are you what is on top?" and the first that says
yes goes back exactly as its own on-screen button would - a press and a click can
never become two different ways out of one screen. One spare history entry sits
ahead of the page and each press spends it; a press that closed something puts it
back. At Home with nothing open the spare is left spent, so a second press leaves
the page: the tool does not trap you in itself.

**The four numbers in "City and castle, side by side" are editable on both
sides**, with **Copy city → castle** under each half. This half's row is already
in the working copy; the twin's is staged in `work.also` against the EDB line it
already occupies - an in-place rewrite, not a second copy of the unit - which is
why `variant_compare` now sends `cap_line` and `faction` per side (`_pool_side`
in `unittransfer/buildings.py`). A row that comes into step as you type is not
pulled out from under the caret.

**Unit cards on disk / Info cards on disk** show each picture at the size the
slot above shows it, and that slot drops its own picture as soon as there IS a
list - it was only whichever faction folder resolved first, i.e. a copy of the
first row below. It keeps what only it has: the import that fans one picture into
every faction folder that owns the unit. **The 3D viewer opens closer**: a unit's
height fills the frame (92% on Gondor Spearmen, up from 48%) instead of a
horizontal spear deciding how far away the man stands. And **Preview is called
Probe** everywhere the word is on screen - the word only: function names, CSS
classes, `/preview_image` and the `model_preview` setting are untouched, and the
3D viewer's own "3D preview" keeps its name, because it is a picture, not a plan.

**A modeldb whose read died on an innocent line now names the character that did
it.** An attachment texture group's fourth field is the sprite slot, and an
attachment has no sprite, so it is always the bare `0` that means "no name
follows". A digit left glued to it by a hand edit (`... .texture 01`) made the
reader eat the next field and die two lines lower on a word that was fine -
reported from the wild on Tsardoms MP, entry #333, and now refused AT the
character with the fix in the sentence (`_Reader.get_attach_sprite`). It refuses
rather than assuming the 0: the span walkers in `modeldb.py` re-walk the same
bytes to place an edit, and one of them reading a file differently from the
others is how a save writes at the wrong offset.

Notes: `merge/RELEASE_2_1_4.md`. New: `tests/test_back_button.py` (21),
`tests/test_variant_edits.py` (46), `tests/test_modeldb_attach_sprite.py` (23).
Suite: 68 of 68 modules.

**The one rule that carries the risk in this release:** an edit typed on the
twin's side is staged by the **EDB line that row already occupies**, so a row the
panel mirrored a moment ago - which has no line in the file yet - must not
inherit the *other* building's line number. `bldVarTake` clears `cap_line` on the
copy for exactly that reason, and `tests/test_variant_edits.py` pins it.

**v2.1.3 IS A SUBRELEASE, same standing as 14j and 2.1.2 - real features, not
folded into Phase 16 because Phase 16 (the Campaign Map Editor) is a different
program.** It is about disk, and about gaps nothing else can see. BMDB mode goes
from two tabs to four: **Strat map** (`unittransfer/stratmap.py`,
`web/js/stratmap.js`) audits and cleans `descr_model_strat.txt` +
`data/models_strat`, and **Unit cards** (`unittransfer/cards.py`,
`web/js/cards.js`) hashes every unit and info card, removes the art of
dictionaries no unit claims and folds the identical copies into the merc folder
the engine already falls back to. Together, **700 MB** off Divide and Conquer.
Beside 🧹 Clean up BMDB there are now **🛡 Fix ownership** and **🌐 All factions**
(`bmdb.ownership_audit` / `ownership_edits`), which give a model entry a texture
record for every faction that fields a unit drawn with it - or for every faction
in the mod. The **3D viewer's divider is draggable** on both docks
(`core.js` `splitInstall`, width saved per screen), in BMDB mode the panel opens
at half the window already showing, and an entry that names ONE texture is no
longer glued to a copy of itself - every ordinary mount. Notes:
`merge/RELEASE_2_1_3.md`. New: `tests/test_stratmap.py` (43),
`tests/test_cards.py` (39), `tests/test_ownership.py` (41). Suite: 65 of 65
modules. Committed, pushed, tagged `v2.1.3` and released with the portable zip:
<https://github.com/ProJ-Yeet/medieval2-gui-toolkit/releases/tag/v2.1.3>

**Three rules are the whole safety of this release, and two of them came out of
running a scan against a real mod before writing any UI:**

1. `stratmap`: **`models_strat/residences` is skipped entirely** - the game picks
   a faction's settlement variant out of that tree by folder, so nothing names
   the file and "nothing names it" would be wrong about all 2,443 of them.
2. `stratmap`: **`x.tga` / `x.tga.dds` / `x.dds` are ONE texture.** M2TW prefers
   the DDS for a line that says `.tga`. Without this the first run reported
   387 MB of Divide and Conquer's *live* art as unnamed; with it, 54 MB.
3. `cards`: the merc folder is the fallback for **any** unit, not only
   mercenaries - which is what makes one copy able to replace thirty. DaC already
   keeps 1,181 of its 1,554 unit cards there and nowhere else, and `edu.py`
   `_icon_dirs` has encoded the same rule since long before this. If that ever
   turns out to be wrong for some engine build, cards go blank and 🕑 Log → Undo
   is the way back - which is why the whole feature moves files rather than
   deleting them.

`cards.py` refuses three things by design and says so on the page: a file not
shaped like a card (the agent pictures), a unit that pins `*_pic_dir`, and a
dictionary only a `.lua` script names. `bmdb.ownership_*` refuses a fourth: an
ownership token the faction roster does not define, since an `ownership` line
may name a culture.

**v2.1.2 IS A SUBRELEASE, same standing as 14j - real features, not folded
into Phase 16 because Phase 16 (the Campaign Map Editor) is a different
program.** Three things: **porting a trait or an ancillary out of another
installed mod** (`unittransfer/portrecords.py` + `web/js/portui.js`) - the
block, the triggers that grant it and its text keys, together, because that is
what a trait or an ancillary actually is; **the M2EX per-mod flag**
(`unittransfer/modflags.py`) so a mod that runs on it stops being told about
the five engine ceilings M2EX replaces, while every other check keeps running;
and **the 3D viewer docked beside the Unit Editor and the BMDB list** instead
of taking the screen over. Alongside those, a dozen bugs found by using the
tool - the sharpest was silent: typing a brand-new trait/ancillary/minor-file
text key and its wording in the same sitting threw the wording away, because
the words box was bound to the key's value at render time rather than to the
field itself. Notes: `merge/RELEASE_2_1_2.md`. New: `tests/test_modflags.py`
(18), `tests/test_port.py` (50). Committed, pushed, tagged `v2.1.2` and
released with the portable zip:
<https://github.com/ProJ-Yeet/medieval2-gui-toolkit/releases/tag/v2.1.2>

**v2.1.1 was a fix subrelease - no phase, no features.** It came out of one
user's log: a stock install lists the four Kingdoms campaign folders as mods
(they have a `data/`, their files are inside `data/packs/*.pack`), the header
auto-picked the first one alphabetically - `americas` - and every read of it
answered HTTP 500 with a traceback. The same log carried a second one: a mod
whose `battle_models.modeldb` has an entry claiming two textures and listing
one, which desynced the reader and died 400 characters later on an innocent
word. Both now answer with a sentence naming the file, and the modeldb one names
the entry, the line of the *bad count*, and what it says versus what is there.
Notes: `merge/RELEASE_2_1_1.md`. New: `tests/test_broken_mod_files.py` (22).
Committed, pushed, tagged `v2.1.1` and released with the portable zip:
<https://github.com/ProJ-Yeet/medieval2-gui-toolkit/releases/tag/v2.1.1>

The rule that came out of it: **a mod's own missing or damaged file is a
`ModDataError` and a 409, never a 500.** It subclasses `OSError` *and*
`ValueError` on purpose - the best-effort guards in `factions`, `minorfiles` and
the checks already say `except (OSError, AttributeError, ValueError)`, and a
plain `Exception` subclass walks straight past all of them.

**PHASE 15 IS COMPLETE - 15a, 15b, 15c and 15d - and v2.1.0 IS PUBLISHED.**
The 3D model viewer works end to end, is committed, pushed, tagged `v2.1.0` and
released with the portable zip. Notes: `merge/RELEASE_2_1_0.md`.

**Phase 16 is the Campaign Map Editor**, the flagship, and it gates 3.0.0. Run
the upstream sync before 16a - `map/` is where he is actively working.

**PHASE 14 IS COMPLETE - 14a through 14j - and v2.0.1 IS PUBLISHED.**
The suite is green: **58 of 58 modules** (15b added `test_viewer3d_http`,
22 checks after 15c; 15a added `test_mesh`, 38 checks after 15d;
14j added `test_images`, 53 checks; 14i added `test_variants_and_marks`, 82;
14f added `test_unit_view`, 25 over 8233 real pool rows; 14e added `test_edusort`,
56).

Phases 0–14 are committed, pushed, tagged `v2.0.1` and released with the
portable zip:
<https://github.com/ProJ-Yeet/medieval2-gui-toolkit/releases/tag/v2.0.1>

**14j is a SUBRELEASE of its own** (`v2.0.1`, `merge/RELEASE_2_0_1.md`), unlike
14i which was folded into 2.0.0. The user asked for it as one: it is a feature,
not a correction. Read memory `release-numbering` before picking the next number.

**The repo is `medieval2-gui-toolkit` now** (14i). GitHub forwards the old
address, so an existing clone or release link still resolves, but write the new
one down anywhere it is typed fresh.

**14i is a CORRECTION PASS folded into 2.0.0, not a point release.** The user
asked for it that way: the tag, the version string and the release page all stay
2.0.0, and `merge/RELEASE_2_0_0.md` carries the new work as a "The correction
pass" section rather than a changelog of its own. If a future round is asked for
as a version of its own, that is 2.0.1 - read memory `release-numbering` first.

**The 2.0.0 numbering overrode a locked decision, on purpose.** The old rule
reserved 2.0.0 for the Campaign Map Editor; the user was shown the conflict and
chose to override, because 1.9.9 shipped a unit-transfer tool and 2.0.0 is a
different program. **The Campaign Map Editor is now 3.0.0.** ROADMAP.md's Locked
decisions section carries the reasoning; don't re-propose the old rule.

**Phase 15's upstream sync is done** (2026-08-20, reviewed SHA `e6e6982`): all
19 of his new commits are campaign-map and New Map Editor work, none of it in
Phase 15's file set. One `descr_regions` correction came out of the sync and is
applied. See Upstream below.

### What 15c did - the viewer against the addon
15b's viewer drew models, and drew several of them wrong. Every fault here was
settled against `Reference/Medieval-2-Toolkit/` (Mylae's Blender addon) and
against the mods' own bytes, not by eye.

**A model is painted from the two textures GLUED SIDE BY SIDE, and the UVs
address the pair.** A modeldb entry names a main texture and an attachment
texture per faction, and the game treats them as **one image twice as wide** -
main on the left, attachment on the right - which is what the mesh's single UV
set is written against. u 0..1 is the main sheet, u 1..2 is the attachment
sheet, and the pair **tiles infinitely** outside that.

**15c got the SPACE right and the STORAGE wrong - see 15d.** The file does not
store `u` in that range: it normalises over the pair (main 0..0.5, attachment
0.5..1) and IWTE doubles it on the way into Blender. 15c passed the file's own
`u` through to a shader that halves it again, so every model sampled a squeezed
stripe of one sheet. `_read_streams` doubles `u` on read now.

So the viewer glues the two into one texture (`v3Atlas`, a 2048x1024 canvas for
the usual 1024 skins, power-of-two so WebGL will repeat it), samples at
`u * 0.5` with REPEAT on both axes, and that is the whole of it. **No code
chooses a sheet for a part and nothing is normalised into 0..1.**

This corrects a wrong first attempt in this same session, and the corrections
are worth keeping because both mistakes are easy to make again:

- **Choosing a sheet per group is wrong**, even though the addon's material
  split (`__main` / `__attach`) makes it look right. One group's art can CROSS
  the boundary - 124 groups in TATR do, e.g. `mount_eastern_armoured_horse`'s
  `Body` at u 0.41..1.38 - and any per-group rule has to put the whole of it
  on one sheet and be wrong about the rest.
- **Shifting an attachment group's u by -1 to sample a separate texture is
  also wrong**, for the same reason and because it throws the tiling away.
  UVs really do run outside the two tiles: in TATR alone **112 groups have
  u below zero and 268 have v outside 0..1**. The atlas handles all of it for
  free; a per-group shift cannot.

An entry with no attachment sheet, or one the mod does not ship, gets the main
sheet in both halves - the same fallback the addon's exporter uses for an empty
attach slot (`attach_name = plan['attach'][1] or main_name`).

`mesh._classify_sheets` still records `"main"` / `"attach"` / `"both"` per
group, but it is a LABEL for the part list, not a rendering instruction, and it
is computed the way the shader samples (`u mod 2`) so it cannot disagree with
the picture. Verified by drawing a model's UV mesh onto the glued pair at
`u * 0.5`: every triangle lands on its own art, face on face in the left half
and shoulder cape on cape cloth in the right.

**Models were mirrored - shield arm and sword arm swapped.** M2TW is
**left-handed** (right +X, up +Y, forward +Z; Direct3D), and 15b handed those
coordinates straight to a right-handed camera. Measured from the models: a
horse's head sits at +Z and its tail at -Z, and on a soldier `shield0` sits at
-X with `primaryactive0` at +X - shield in the left hand, weapon in the right,
so the model's own right is +X and a figure facing the camera was showing its
right side on the viewer's right. `uModel` negates X. For a mirror the
inverse-transpose normals want is the matrix itself, so `mat3(uModel)` stays.

**What the two group name strings ARE, settled rather than guessed.** One TATR
mesh has a group type that is IWTE's own unanswered prompt, saved verbatim into
the file: _"enter a group type: cloak"_ / _"enter a group flag (0 for required,
1 for optional.)"_. So the first string is the group TYPE, the second is the
MESH NAME, and the uint32 15b called a variant marker is **required/optional**.
That is exactly the addon's `objectname__comment__opt` - IWTE joins the two
with `__` and appends `__opt` when the flag is 1. The parts panel now folds by
type (case-folded: nineteen meshes across the two mods spell the same part
`Arms` and `arms` in ONE file), spells the engine's fixed equipment vocabulary
out from the addon's `PART_PREFIXES` ("Secondary weapon - drawn", not
`secondaryactive0`), tags parts the mesh flags optional, and starts with
`shieldpassive*` and `secondaryactive*` switched off - the same call the
addon's importer makes in `hideVariations`.

**Randomize variations**, a button at the top of the panel: a variant per part
and a coin toss on the optional ones, which is what the game does filling a
unit out of one model.

**The V axis was NOT wrong** - 15b had it right, and this was checked properly
this time rather than by a luminance heuristic: drawing the head groups' UV
boxes on a Lossarnach noble's sheet puts them exactly on the faces painted
along the sheet's TOP edge (v 0.00..0.10), and the same for every body and
skirt group. `v=0` is the top. Flipped, the model renders as garbage.

**The backdrop is an environment, not a flat near-black.** One `v3Env()`
function - sky above, warm ground below, a bright band at the horizon - paints
the background AND lights the model, which is the part of an HDRI that matters
for an inspection viewer without shipping a megabyte of `.hdr` and a decoder.
Plus a mid-tone curve, because unit art is sRGB and a linear multiply of 0.5
lands far darker than half-lit looks: dark armour on a dark field was a viewer
of silhouettes. **Turntable is now "Rotate" and starts OFF.**

`test_viewer3d_http` is 22/22 (the payload now has to say which sheet each
group draws from and whether it is optional); `test_mesh` was 34/34 here, with
its UV assertion widened from `[0,1]` to the two u tiles - which passed
vacuously, because nothing was reaching the second tile yet. 15d is what made
that assertion bite.

### What 15d did - two decode bugs the user caught in Blender
Both were found the same way and it is the way to find the next one: the user
opened the same models in Blender through Mylae's addon and put its picture
beside the viewer's. Neither bug was visible as "broken" - both looked like a
viewer that sort of worked.

**The UVs were squeezed into one sheet, and every part wore the wrong art.**
The file normalises `u` over the two-sheet PAIR: main is 0..0.5, attachment is
0.5..1, tiling with period 1. Everyone downstream of IWTE speaks the DOUBLED
version of that (main 0..1, attachment 1..2), which is the space the addon
enforces in `export_checks.checkUVSpace` and the space 15c wrote the viewer
against - so the file's own `u` met the shader's `u * 0.5` and halved twice.
`mesh._read_streams` doubles `u` on read, so everything this tool hands out is
in the addon's space and nothing else had to change. Measured before believing
it: across 900 TATR models, **1,092 of the 1,179 weapon and shield groups sit
in u 0.5..1** - the half an attachment sheet exists for - with bodies, heads
and beards packed into 0..0.5. Verified by drawing each group's triangles onto
the glued pair: face on face, scabbard on scabbard.

Side effect worth knowing: `_classify_sheets` was labelling **every** group
`"main"` before this, because nothing ever passed u 1. The part list's "attach
sheet" / "both sheets" tags only started telling the truth here.

**The packed normals are `D3DCOLOR`, not signed bytes.** Unsigned, biased around
127.5 (`b / 255 * 2 - 1`), stored **z-y-x** with a pad byte last. Read as signed
bytes over 127 in x-y-z order - 15a's guess, and the obvious one - the vectors
come back 0.74..1.43 long with **half of them pointing away from their own
faces** (mean dot -0.11). That is what the dark blotches and hard seams were.
Decoded properly: unit length to within 0.004, mean dot **+0.897** against the
face normals computed from the positions, 4 of 6,783 opposed.

`test_mesh`'s normal-length bound was **0.9..1.2, which the broken decode passed
at 1.08** - it is 0.98..1.02 now. Also added: the reference horse must use both
u tiles (catches forgetting to double, and doubling twice), and its saddle must
classify `main`, its rear barding cloth `attach`, its body `both`.

**The lesson for the next format bug:** a plausible decode that renders
something is the dangerous case. Both of these were settled by measuring the
decode against a second source - the face normals the positions imply, and the
addon's own UV convention - not by looking at the canvas.

### What 15b did
**`web/js/viewer3d.js` draws the model, in plain WebGL, with no library.** The
user chose that over vendoring three.js: a static textured model needs one
shader, an orbit camera and a texture bind, and 600 KB of someone else's dist/
in a project whose whole point is that it has no build step is a bad trade.
About 400 lines, and the only maths in it is perspective and look-at.

**Three routes, all in `server._model_route`:** `/api/model` (the picker - LODs
and skins, and which of them the mod actually ships), `/api/model/geometry`
(one LOD as a binary payload) and `/model_texture` (one skin as a PNG).

**The geometry goes over as ONE binary blob, not JSON.** `mesh.geometry_payload`
writes `"M2GT"`, a JSON header for the structure, then the arrays raw, padded so
the floats stay 4-byte aligned - the page views each one in place with no copy
and no parse. JSON would have been about six times the bytes.

**Two real bugs were found by looking at pixels rather than at the screen**, and
both would have shipped as "the viewer sort of works":

- **The V axis was upside down.** WebGL's habit is to flip an uploaded image
  because OpenGL puts v=0 at the bottom; M2TW is a Direct3D game and puts it at
  the top. Flipping sent 62% of a real horse's vertices onto empty black space.
  Measured by sampling the texture at the mesh's own UVs: mean luminance 48
  against 16, pure black 2% against 62%.
- **The camera orbited the wrong axis.** I had assumed Z-up. **Models are
  Y-up** - across six DaC soldiers the `Head` group's centroid sits ~1.4 above
  the `Legs` group's in Y and level in X and Z. Orbiting Z lays every man in
  the game on his side. Now written into `mesh.py`'s docstring so nobody
  re-derives it.

**The variant problem is the thing that makes this UI worth having.** A model
carries several heads, helmets and shields and the game picks one per soldier;
drawing them all puts nine helmets on one orc. `gundabad_pale_uruk_new2` has 27
groups and the viewer draws **12** - one per part, the rest offered in
drop-downs. Verified in the browser against the real DOM.

**Skins are deduplicated rather than listed per faction** (`mesh.entry_view`).
Entries routinely list 29 factions against one texture; 29 identical rows told
you nothing. One row per distinct skin, labelled "portugal (Remnants of Angmar)
+28 more". _15c changed what a "skin" is - see below._

**`icons.py` grew two things** both of which everything else can now use:
`.texture` files unwrap to DDS through `sprites.texture_to_dds` before Pillow
sees them, and `png_bytes(src, max_side)` shrinks on the way out (a 2048 skin
served at 1024 is 4 MB instead of 16, and `max_side` is part of the cache key).

Verified in the real app, not just in tests: the button on a real DaC model
card, the viewer opening from it, 4 distinct skins each loading a different
1024² texture, wireframe drawing with no GL error, and the model card restored
on close.

### What 15a did
**`unittransfer/mesh.py` reads a battle model, and the read is falsifiable.**
`read_mesh(path)` returns a `MeshFile`: one shared vertex pool (positions,
normals, UVs), the groups that index into it, the bone names, and the LOD block's
name. `probe(path)` tells a `.mesh` from a `.cas` without decoding either.

**Two things ROADMAP.md said about this phase were wrong, and the plan followed
the files instead.** There is no loader to port: the Blender addon in
`Reference/Medieval-2-Toolkit/` never parses a model, it writes an IWTE task
file and shells out to `IWTE.exe` (`tasks/iwte_run.py`). And upstream's
`src/lib/casCodec.js` - the "port-concept" entry in the manifest - documents
`.mesh` as "uint32 version, uint32 submesh count, 32-byte vertices", which
matches no real file and cannot parse one. **A `.mesh` is a
boost::serialization binary archive**, which is why: boost writes a class
descriptor the first time it meets a type and only the class id afterwards, so
the same record is two bytes longer on its first appearance and no fixed-stride
reader can work. The format is written up in full at the top of `mesh.py` -
group table, the eleven vertex stream types with their strides, the bone table -
and that docstring is the spec now, because nothing else is.

**What proves it: reaching the bone table.** One wrong stride anywhere before it
puts the table outside the short window it is looked for in, and the count read
there lands on nonsense. **4,700 of the 4,702 `.mesh` files in the two test mods
decode** - every unit model, mount, settlement piece and siege engine in Divide
and Conquer (3,500 of 3,500) and Third Age Reforged (1,200 of 1,202) - plus the
seven reference templates. The two exceptions are sky domes that hold SEVERAL
models one after another; they are refused by name rather than half-read.

**There are two vertex formats, and finding the second one cost the most time.**
A skinned model (soldiers, mounts, settlements) packs normal, tangent and
binormal into three signed bytes and a pad; a static one (siege engines, sky
domes) writes them as three floats - same stream type numbers, four bytes a
vertex against twelve. The archive header is four words in the first and three
in the second. Neither is announced anywhere, so `_read_header` and
`_resolve_stride` both try the alternatives and keep whichever leaves the rest
of the file readable. **A sweep of one folder will not find this**: everything
under `unit_models` is the skinned form, and `data/siege_engines` is the only
place in either mod that is not.

**What is NOT decoded** is the block that closes the file: a per-LOD material and
attachment record, 519 bytes in every unit model. Its name is read
(`characterlod0`), its length is on `MeshFile.trailer`, and nothing the viewer
draws is inside it.

**`.cas` was asked for and did not land, and that was the agreed fallback.**
`probe` identifies one and `read_mesh` refuses it by name, but there is no `.cas`
geometry reader. It is not a variant of `.mesh` - it opens with the float `3.2`
and is a whole 3ds-max scene export: frame rate, key times, a node hierarchy
(`Scene Root`, then bones), animation tracks, then the mesh, then the material,
with `textures\…\.tga` in the last 60 bytes. That is a second job the size this
one was, and it belongs to **16e**, where the roadmap always had the strat
preview. The reconnaissance is written down at the bottom of `mesh.py` so 16e
starts from something.

**For 15b:** the geometry is renderer-ready as it stands. Indices are GLOBAL
into one pool, so a group is a face range, not a mesh of its own - draw the pool
once and issue one index range per group. Several groups share a group TYPE
(`Body`/`horse_body_01`, `_02`, `_03`) and are variants of one part, and drawing
all of them at once stacks three heads on one soldier: pick one variant per part.
`MeshGroup.flag` is not that - 15c showed it is required/optional - and
`MeshGroup.sheets` LABELS which of the entry's two textures a group's art
lands on, without being a rendering instruction: the two are glued into one
image and the UVs pick by themselves.
Textures need no new code - `sprites.texture_to_dds()` then Pillow reads DXT1,
DXT3 and DXT5 out of a real `.texture` at 1024² and 2048², which is the whole
texture path. `tools/meshdump.py` is the debugging tool: `--sweep <folder>` over
a mod, `--raw <file>` on one that will not open.

### What 14i did
The list that came back from actually using 2.0.0. Ten items, no new direction.

**Two of them were real defects with a single cause each.** "Open file location"
opened Documents, every time, for everyone: `explorer /select,<path>` was passed
as an argument LIST, and `subprocess.list2cmdline` quotes the whole
`/select,C:\…` token the moment the path has a space in it - Explorer then fails
to parse the switch and falls back to the default folder. Every real mod path has
a space in it. It is one command STRING now, with the path quoted inside the
switch. And Ctrl+Z did nothing in the Code View, because undo.js takes the
keystroke whenever an editor is open and restores a snapshot of the BOXES; the
pane keeps its own stack now, and an empty stack hands the keystroke back to the
editor so undo walks out of the text and into the form.

**The freeze report was `bldRenderBody` throwing on a null.** Every panel that
takes the dialog over leaves `#bldBody` out of the document, and the throw came
out of an onclick - so it killed that click and everything after it. `bldTouched`
now returns early for any stashed panel, `bldRenderBody` returns early with no
body at all, and the stale-`state.bld` paths around the settlement filter, the
level list and the faction picker are closed with it.

The rest: the sidebars fold (every `<h3>` in every `aside.filters`, wrapped by
reading the markup rather than by hand), a ＋ on the tier Variant, Abilities
merged into **Weapons & abilities**, the cleanup dialog's banner format made
editable with a live sample, the ordering screen rebuilt as a list of units with
tier / variant / **classification** drop-downs filled in from what was detected,
**⇄ Compare city / castle** on the building editor with per-unit and whole-line
mirroring, one set of names for the three recruitment numbers (**Initial Pool /
Replenish Rate / Max Pool**), the recruitment row split over two lines so the
`requires` clause has room, the building Code View following field edits at last,
the faction sort lifted out of the drop-down it sorts, unit cards on the voice
rows, and a prose sweep that took ~300 clause-joining em dashes to zero.

New server surface: `GET /api/buildings/variants` (one line beside its twin,
tier by tier) and `marks` / `style` on `/api/edu/sort/plan|apply`. New marker
key `special=` on `;@m2gt`, read by `edusort.special_of`.

### What 14j did
**Every picture the tool draws can be replaced in place, and every picture can
say where it lives on disk.** Before this, one picture in the whole toolkit
could be swapped: the unit card, through the editor's own staged import.

**What made it small is that the page hands back the `<img>`'s own `src`.**
Every picture on every screen is painted through `/icon` or `/building_icon`,
and that URL is a complete description of the question the server answered - so
one engine (`unittransfer/images.py`) and one dialog (`web/js/images.js`) cover
unit cards, info cards, ancillary pictures, faction art, the Minor Files pips
and settlement cards, and building icons.

Two ways in: a delegated **right-click** menu on any `<img>` served by those two
routes (which is what reaches the thumbnails in lists and grids), and a **✎ plus
a button pair** on the screens where the picture is the subject.

The **resolution warning** is the thing that was asked for: the confirm dialog
puts both pictures side by side at the size each really is and names both sizes
when they differ. A warning, never a refusal. Three more rules fall out of the
formats: a `.png`/`.jpg` is re-encoded as a 32-bit `.tga`; a same-stem sibling
in the other native extension is removed so two files cannot answer to one name;
and **a unit card fans out to every faction folder that holds one**, because the
game looks it up under the *player's* faction folder.

**Borrowed art creates rather than overwrites.** A building icon or ancillary
picture the mod does not own is served out of the vanilla UI, so a replacement
writes the mod's *first* copy at the path the game looks for - which is the
"drop a .tga in to override it" the building browser had only ever said in a
tooltip.

New server surface: `POST /api/image/plan | /replace | /reveal`. The write goes
through the same backup + log record as every other job, so it is in the log and
undoes like a transfer. `tests/test_images.py`, 53 checks, builds its own folder
of pictures - only the fan-out section needs a mod installed.

### What 14f did
The unit view was already the screen that gathered every building line training
one unit; what it could not do was any of the things you go there to do.
Requires is editable from the unit's side now, through the same dialog and into
the same save. A **Twin** column says whether the city/castle counterpart trains
the unit **at the facing tier**, with a `⇄` that stages the pool across -
**239 rows in DaC diverge and none in Reforged do**, which is what makes the
column worth its width. The panel got a **read-only Code View**, the three
recruitment numbers got **names** (Immediate recruitment, Replenish rate, Max
pool), the BMDB Editor became the **BMDB + Sprites Editor**, and Minor Files
finally shows the pips, icons and cards it had only ever shown as file paths.

Two bugs in shared machinery came out of it, both ours: `bldTouched()` re-drew a
form that was not on screen, and the clause dialog shared one stash slot with
the unit view that can open it - so a clause edit wiped the building editor
underneath. Both fixed; see ROADMAP.md's 14f outcome.

## Phase status
| Phase | Status | Note |
|---|---|---|
| 16 - Campaign Map Editor (V3.0.0) | **16a-16f done, 16g next** | Scoped 2026-09-03 from four references into eleven sessions, 16a-16k, with V3.1-V3.3 as future releases. Pillow only, no numpy and no C extension - measured, see ROADMAP.md Phase 16. **16a and 16b landed 2026-09-03**: `maptga.py`, `mapvocab.py`, `campmap.py` (62/62) and `campstrat.py` (75/75). The whole read half of the engine is done and every file it touches round-trips byte-exact. **16c landed 2026-09-04**: `web/js/campmap.js`, the manifest and PNG half of `campmap.py`, `/api/map` and `/api/map/layer`, `test_campview.py` (50/50) over vanilla's map as well as DaC's; a pan frame is 0.02 to 0.18 ms and the picked pixel is exact. **16d landed 2026-09-04**: the layer stack remembered on `/api/settings`, `layer_legend` and the `BLANK` table that turns a layer into an overlay, `probe_pixel` over all ten layers, region adjacency, and the editable `descr_regions.txt` record with its Code View, its religion rule and its undo - `test_campedit.py` (85/85) over both maps, and every record of both re-renders byte-exact. Each is written up in its own section above. **16e landed 2026-09-04**: `campaint.py` and `web/js/campaint.js` - five tools, region-colour snapping, closed palettes, the measured water brush, unlimited undo over pixel deltas, and Mylae's three-step new-region wizard; `test_campaint.py` (95/95 here, six more per
additional installed map), every painted layer byte-identical outside the painted tiles and an undo that restores it byte-exact. **16f landed 2026-09-04**: `mapcheck.py` and `web/js/mapcheck.js` - 30 rules each carrying its source and each with a broken map under test that only it may catch, fingerprinted findings so a baseline survives an edit above them, and Geomod's three debugger actions written through one backup set; `test_mapcheck.py` (82/82), 609 ms on DaC and 120 ms on vanilla, and it reports the Ragusa port bug in the stock game. Still to come: 16g-16k; **not** `stratmap.py`, which is a different concern |
| 15j - resizable panels, the strings warning, no em dashes | **done** | **v2.1.11.** `rsz*` in `core.js`: `resize:vertical` on every scroll box the stylesheet declares (found by reading `document.styleSheets`, 31 selectors, `.wpop` and `.modal` skipped), `resize:both` on `#modal`, a `.drawergrip` bar on the right-pinned drawer, sizes in `pane_sizes` on `/api/settings`. The two real problems are `max-height` outranking a dragged `height` (cleared on capture-phase `mousedown` at the corner) and wholesale re-renders throwing the result away (a `MutationObserver`, coalesced on `setTimeout` rather than `requestAnimationFrame`, because an occluded window gets no frames). Nothing is pinned until it is dragged. Plus the strings list's stale-`.txt` warning rewritten with a `qm()` card, and 4176 em dashes swept out of 171 files with `ANY_EM` added to `prose_check` to keep them out. `test_web_modules` 10/10; verified in-browser (pin, save, survive re-render, reopen at the saved size, double-click reset) |
| 15i - the model beside a transfer, art beside a pool | **done** | **v2.1.10.** The 3D column docks into the transfer composer (`transfer.js` `cmpPrev*`, `#cmpSplit`), listing the source unit's battle-model entries AND the base/replaced unit's out of the destination mod, grouped by mod and drawn from it - the third `v3Mount` host, same detach-across-render / one-viewer / fold-pauses rules as the editor's. Entries come off the unit LIST's fields, with the `armour_ug_models` rule and men-before-officers ordering. The Recruitment tab's rows and its ＋ picker carry the tier's art, keyed by the pool's OWN `requires` through `ov.faction_cultures`, with a new opt-in `any_culture` sweep in `buildings.find_icon` (`&any=1`) for the levels a mod draws for one culture only - OFF for the building browser, which is showing one culture on purpose. Row layout re-cut as two halves: tier against the name, `requires` right-aligned on its own line, and the header finally aligned with the boxes it names. `test_buildings` §11 + `test_buildings_http`; 72 of 72 modules |
| 15h - recruitment on the unit, UV layout | **done** | **v2.1.9.** `web/js/edrecruit.js` (new) - a Recruitment tab in the unit editor listing every building line that trains it, with the four pool numbers, the `requires` clause, a delete and a ＋ that adds the unit to any line and tier. **No Python**: `buildings.unit_instances` reads and `buildings.plan_edit` writes, so this is a second FRONT rather than a second implementation. The one new request shape is `also`-only - every edit in `also`, the body carrying a line name and no levels - which is also what makes `_check_recruit_limit` merge the file instead of counting three rows as a level. The clause dialog is borrowed with `kind:'edrec'`, which re-renders the editor instead of unstashing markup, because the modal holds a live WebGL column. `?building=&lvl=&unit=` opens a building in its own tab, on the tier, with the unit’s rows flashed. A save now moves EDB line numbers, so a building left open behind the editor drops its working copy and `backToBuilding` re-reads it. `test_unit_recruitment` 42/42; verified in-browser, three pools over two lines written and undone byte-exact. Plus the viewer’s **UV layout** and the mount-texture bug it found |
| 15g - add a faction, viewer UV mode | **done** | **v2.1.8.** `unittransfer/factionclone.py` (new) + `/api/factions/clone_plan\|clone_apply` + the **＋ Add a faction** dialog in `web/js/factions.js`. Clones a donor into all **twelve** files that name a slot - nine plus `export_descr_buildings` (the `requires factions { … }` clauses that let it build and recruit), `descr_sounds_accents` and `descr_faction_standing`, found by grepping the mods rather than trusting phase 11's unmeasured "nine" - plus convention-named art (`ui`/`menu`/`banners`), one transfer id for the lot. Three more files name the donor as a *judgement* (a trait named after it, an ancillary's `FactionType` operand, a prebattle speech) and are counted and reported, never appended to. Phase 11's "no create" refusal is retired; **delete stays refused** - a clone copies the donor's answer, a delete would have to invent one. `descr_strat` is reported, never written: two factions cannot start in the same settlement. Four bugs the tests caught - the mods are **CRLF** and `$` sits after the `\r` (three cloners matched nothing, two ate the `\r`); `_` is a word character in a data file and a **separator** in a text key (one boundary found 1 of 61 keys); `add_texture_factions` takes **one entry's** raw text, not the file; and a file may spell the same list two ways (`descr_faction_standing` writes `factions { … }` *and* `exclude_factions { … }`, and DaC has none of the second). `test_factionclone` 64/64 (real mods, read-only), `test_factionclone_apply` 30/30 (synthetic mod, written then undone byte-exact). Viewer **Show UVs**: paints the coordinate in the sampler's own space, 32 cells/sheet because real parts span 0.07–0.33 of u |
| 15e - port, M2EX, docked viewer | **done** | **v2.1.2.** `unittransfer/portrecords.py` + `web/js/portui.js`: copy a trait/ancillary between installed mods (block + triggers + text keys, one job); `unittransfer/modflags.py`: per-mod M2EX flag drops only the five engine-ceiling finding kinds, everything else still checked; the 3D viewer (`v3Mount`/`v3Unmount`) docks beside the Unit Editor and BMDB list instead of taking the modal over. Plus a dozen fixes, the sharpest being a silent one: a brand-new text key's wording was discarded if typed in the same sitting as the key (Traits/Ancillaries/Minor Files), because the words box was bound to the key's value at render time rather than to the field. `test_modflags` 18/18, `test_port` 50/50 |
| 0–12 | done | see ROADMAP.md for each phase's exit criteria |
| UX correction pass | done | 17 of 18 items; the 18th (prose sweep) is now finished |
| Prose sweep | done | 19 note blocks in `buildings/transfer/editor/sprites.js` rewritten as lead + points via a shared `docPoints()` in core.js |
| 13 - EDU + Sounds audit | done | `merge/audit-edu-sounds.md`; measured over 1756 real units; **nothing adopted from their code**, banners rederived from the mod's own file, two silent rewrites of ours fixed |
| EDB corpus follow-up | done | `#` annotation lines no longer read as capabilities (3 parsers + regression case); the `plugins` and upgrade-clause sweeps no longer depend on which mods are installed; `merge/audit-edb.md` corrected |
| 15a - the model decoder | **done** | `unittransfer/mesh.py` + `tools/meshdump.py`. A `.mesh` is a **boost::serialization archive**, reverse-engineered from the files: neither the Blender addon (it shells out to IWTE) nor upstream's `casCodec.js` (its spec matches no real file) could be ported. **4,700 of 4,702 models decode** (the 2 are multi-model sky domes, refused by name), proven by reaching the bone table. Two vertex formats: skinned packs normals to bytes, static writes floats. `.cas` NOT decoded - a whole 3ds-max scene format, handed to 16e. `test_mesh` 34/34 |
| 15b - the viewer | **done** | `web/js/viewer3d.js`, hand-rolled WebGL (no three.js, user's call). `/api/model`, `/api/model/geometry` (binary payload, not JSON), `/model_texture`. **View model** on the shared model card. Parts, variant pickers, skins, LODs. Models are **Y-up**, not Z-up - caught by measuring group centroids. `test_viewer3d_http` 21/21 |
| 15c - the viewer against the addon | **done** | Four faults, all settled against Mylae's Blender addon and the mods' bytes. The main and attachment textures are **glued side by side into one image** and the UVs address the pair - sample at `u * 0.5` with REPEAT, never choose a sheet per group (124 groups straddle the boundary) and never normalise into 0..1 (112 groups have u < 0, 268 have v outside 0..1). Models were **mirrored** - M2TW is left-handed, so `uModel` negates X. The two group strings are **type** and **mesh name** and the uint32 is **required/optional**, proven by an IWTE prompt left in a TATR mesh; parts fold by type with the addon's equipment vocabulary. Procedural-HDRI backdrop and lighting, **Randomize variations**, Turntable renamed **Rotate** and off by default. The V axis was already right. `test_viewer3d_http` 22/22 |
| 14 - bug-fix and polish pass | **done** | 14a–14j |
| 14j - replace any picture | done | **v2.0.1.** `unittransfer/images.py` + `web/js/images.js`; `POST /api/image/plan\|replace\|reveal`. Right-click any image anywhere, or the ✎ where a picture is the subject. Resolution mismatch warned (never refused), `.png` → `.tga`, unit cards fanned out to every faction folder, borrowed vanilla art creating the mod's first copy. `test_images` 53/53 |
| 14i - the post-release correction pass | done | repo renamed to `medieval2-gui-toolkit`; Code View Ctrl+Z/Y; folding sidebars; "Open file location" fixed (Explorer arg quoting); ＋ on tier Variant; Abilities folded into **Weapons & abilities**; editable banner format + the ordering screen as a unit list with tier/variant/**classification**; **⇄ Compare city / castle** (`/api/buildings/variants`); **Initial Pool / Replenish Rate / Max Pool** everywhere; two-line recruit rows; building Code View follows field edits; faction sort as a toggle; unit cards on voice rows; ~300 em dashes → 0. Folded into the 2.0.0 release notes, not a new version |
| 14f - EDB unit view, twin compare | done | Requires editable from the unit side, a per-TIER **Twin** column (239 divergences in DaC, 0 in Reforged) with `⇄` to close one, a read-only `pools` code view, the recruitment numbers named, BMDB → **BMDB + Sprites Editor**, Minor Files art. Two shared-machinery bugs fixed. `test_unit_view` 25/25 |
| 14g - the second prose sweep | done | 21 clause-joining dashes → **0**, four documented keeps. 6 of the old 115 hits' causes were defects in `tools/prose_check.py` itself, not in the writing |
| 14e - EDU cleanup and unit tiers | done | `unittransfer/edusort.py` + the `;@m2gt` marker in `edu.py`. Tiers are READ from the mod's own banners (907 of DaC's 916 sit under one). DaC: 15% of the roster moves, and a second run is byte-identical. `test_edusort` 56/56 |
| Release check (14h) | done | `merge/audit-codebase-2.md`. A BOM cost the EDU and factions parsers their first record SILENTLY (DaC really lost a faction); mixed line endings no longer normalised; cache invalidation derived from `Mod`; the 56 "missing ancillary picture" findings were ours, not the mod's; three suites that could not run, run. **52/52 green.** |
| 14a - loading, switching, Transfer | done | one bug, four masks: the watchdog was killing a live server. Cache out of OneDrive, any request counts as liveness, 224k globs and a per-request folder scan gone, abort + generation on every load, loading bar. `test_liveness_and_cache` 21/21 |
| 14c - launcher, Home, prose | done | launcher exit code 2 + no more guessing, restart-in-place for the console setting, `port_free` asks by binding, Home steps 1 and 3. Its prose item became **14g**, now finished. `test_startup` 48/48 |
| 14d - guided view + Code View | done | seven paired rows, tidy on open without making the dialog dirty, the sticky bug (it was `align-items:start`, not sticky), comment hiding as a hide/show PAIR so nothing is lost, raw lines side by side to 1 px, "Open file location", the dead click on the card, folding headings + an Era group-by. `test_codeview` 141/141 |
| 14b - log and undo/redo | done | log paging (571 ms → 51 ms, 1.1 MB → 29 KB), mode filter, diagnostic button moved in, Ctrl+Z/Ctrl+Y wired for the five editors that never had a scope, and the log now records what the user did beside what the tool did. `test_log_and_activity` 26/26 |

## In-progress detail
Clean. 14a, 14b, 14d and 14e are finished and verified in a running browser;
14c is part-done. Phases 0–13, both passes, 14a, 14b, 14d and 14e are in the
working tree, **not committed or released**.

**The EDU cleanup is the widest single write in the toolkit** - it rewrites
every block of a 35 000-line file - so `edusort.plan` refuses to hand over a
text that is not purely a reordering: same units, same fields, every comment
still present, checked before a byte reaches disk. Measured on both mods: DaC
916 units / 15% moved, Reforged 427 / 39%, both byte-identical on a second run,
no comment lost, and Undo restores the original exactly.

The icon cache lives at `%LOCALAPPDATA%\UnitTransfer\cache\icons` (14a). The old
`.cache/icons/` next to the app is dead weight and can be deleted whenever.

**The Code View's `text` is no longer its bytes.** With comment hiding on,
`cv.text` is the record MINUS its comment-only lines and `cv.base` is the real
thing. Anything that saves must read `base`; four adopters (`traits.js`,
`ancillaries.js`, `factions.js`, `minorfiles.js`) were saving `text` and would
have deleted every comment in the record. Check this on any new adopter.

**Green: 52 of 52 modules, 2156 checks.** The six that used to fail are closed -
one was a real defect of ours (the ancillary image check, see the audit) and the
rest were tests asserting something the code never promised. Detail per suite is
in `merge/audit-codebase-2.md` §3.

A test no longer hardcodes a mod NAME: `tests/_realmod.pick()` takes the
preferred mod if it is installed, any other installed mod otherwise, and prints
SKIPPED with status 0 when there is none. Three suites used to die on a
`FileNotFoundError` for `Third_Age_6` instead - and a suite that cannot run looks
exactly like one that passes. Still check the installed mod set before blaming a
failure on a regression (memory `unit-transfer-test-mods`).

`/api/log` answers with a page now, not an array: `test_edit_http` and
`test_bmdb_http` were updated for it.

## Read first
- ROADMAP.md - phases, exit criteria, locked decisions.
- `unittransfer/flatrecord.py` - **check here before writing any parser.** Phase 11
  needed no code at all, which is why it exists.
- `unittransfer/buildings.py` - the biggest module and the only one that CREATES a
  record. Everything else in it is a SPLICE of verbatim lines; 7203 of its real
  input lines carry a comment and a re-emitting serialiser loses all of them.
- `unittransfer/edusort.py` - the whole-file EDU cleanup, and the one module that
  decides where a unit BELONGS rather than what it says. Read its docstring
  before changing any grouping rule: every one of them is a measurement over the
  two installed mods, and the obvious rule was wrong in all four cases.
- `unittransfer/vocab.py` - what a drop-down may offer: engine sets hardcoded, and
  everything a mod DEFINES read from the file that defines it, with a `defined`
  map behind the broken-reference warnings. Phase 13 moved banners onto that rule.
- `web/js/core.js` - `MODES` in `wire()`, and `docPoints()`, which every note in
  the UI is written through. One global scope, no build step; adding a module means
  a new file + a `<script>` tag + a MODES entry, all three guarded by
  `tests/test_web_modules.py`.

## Upstream
reference tool reviewed SHA **ac503ac** (2026-09-03), 27 commits and 31 files on
from e6e6982. **The 16a sync is done** and the write-up is the newest entry in
`merge/SYNC_LOG.md`.

**Nothing in that batch touches 16a.** His three changed `map/` files are
`stratParser.jsx`, `FactionsCampaignTab.jsx` and a new `factionBlockOps.js`, all
of them `descr_strat.txt` faction blocks, which is 16b and 16j; no layer, no
`descr_regions.txt`, no coordinate rule. Ten new files were triaged by hand:
`factionBlockOps.js` is the one worth reading before 16b, because it finds
faction block boundaries with brace-depth tracking so a settlement's own
`region` and `faction_creator` lines are not mistaken for headers, which is
exactly what `campstrat.py`'s interval index has to get right. The other nine
are two faction-clone helpers and a clone dialog (port-concept, compare with
`factionclone.py`), a UTF-16 encoder (audit; ours already writes the BOM, and
his splits astral characters), the New Map Editor's rotated-bbox resampler
(out-of-scope, and OSM besides) and four pieces of cloud and browser-storage
plumbing (skip). The manifest also had five `phases` lists written as numbers
rather than strings, which crashed `sync --accept`; they are strings now.

All 19 of his commits since b4768d5 land in the campaign map editor or the New
Map Editor, so **nothing had to be ported to keep 2.0.0 correct**, and Phase 15
(the 3D model viewer) can start without waiting on anything of his. One
correction came out of it and is applied: `descr_regions`' two bare numbers are
**triumph value then base farming level**, not farming level then unknown -
measured over vanilla's 112 regions, not taken on his word, because both test
mods write 5 and 1 everywhere and cannot tell the two apart. Three facts for
Phase 16 are banked in the manifest's `notes`.

**Phase numbers in the manifest were off by one and are fixed.** It was written
before the 2026-08-18 renumber, so 46 map files said 15 (they are 16) and 10
model/texture files said 14 (they are 15). `upstream_sync.py`'s RULES table is
corrected too, so new files land on the right number.

`merge/PORT_MANIFEST.json` is authoritative; all 12 phase-13 files carry their
audit verdict in `notes`.

## Open questions for the user
- ~~`OsmBackground.jsx` / `OsmRegionSearch.jsx` - port or drop?~~ **Answered
  2026-09-03: ported, deferred to V3.1**, opt-in and off by default, together
  with `CoastlineTracer`. The generators go to V3.3. The Locked-decisions rule
  that swept them into permanent out-of-scope is amended in ROADMAP.md; the
  three AI assistants are not reclassified.
- `descr_sounds_*.txt` (32 files in DaC) is a real coverage gap this audit
  measured and did not close - the engine's sound scripts, a grammar of its own.
  Its own phase later, or out of scope for V2?

## Decisions
- 2026-09-04: **A rule with no evidence reports nothing.** The validator's
  rules that need a vocabulary ask for it first and, when the file is not on
  disk, say which file would let them run instead of reporting everything as
  missing. The stock game's data is packed, and reading "no climate is
  declared" as "every climate colour is undeclared" reports 11 faults and
  55,755 tiles against a map that ships with the game and works.
- 2026-09-04: **A finding is identified by what it is about, never by where it
  is written.** `mapcheck.Finding.key` hashes the rule, the file and the thing
  (a region's name, a tile's coordinates, a resource's name and position) and
  never a line number, which is what lets a stamped baseline survive an edit
  above it. Without that, one inserted comment would make every finding below
  it new and the baseline worthless.
- 2026-09-04: **A baseline shows and stops blocking; it never hides.** A mod is
  somebody else's work with somebody else's bugs in it - vanilla's own map has
  62 findings - and a tool that refuses to save until 40 inherited faults are
  fixed is one nobody uses twice. A tool that hides them is one nobody believes.
- 2026-09-04: **A rejoin is a loop, not a junction.** Vanilla has 26 river tiles
  with three cardinal neighbours and every one is an ordinary tributary, so
  counting neighbours is not the rule. The rule is a cycle in the four-connected
  river graph, found as the edge that closes it, and vanilla has none.
- 2026-09-04: **A rule the paint tool also enforces exists once.**
  `mapcheck.marker_faults` is the only copy of the four marker rules; the
  new-province wizard calls it. Where the two differ - an inland port is a
  warning while the pixel can still be moved and a fatal once it is on the map -
  the difference is written at the place it is made.
- 2026-09-03: **The map editor is Python with Pillow, and the reason is a
  measurement.** All ten of DaC's TGA layers decode in under 100 ms, the
  unique-colour census is 6 ms and the region label image 5 ms; a map is capped
  at 510x510 by `descr_terrain.txt`. The reference tool's lag is repeated work,
  not a slow language, so numpy and a C extension both buy nothing and cost the
  zero-build-step rule, a second dependency and release-zip size.
- 2026-09-03: **The browser never parses a TGA.** Python decodes, serves PNG and
  owns the canonical pixel buffer; the browser paints a local preview and posts
  stroke operations. That is the "one engine" rule, and it is what makes undo,
  backups and server-side validation possible at all.
- 2026-09-03: **A reference tool's parser is evidence, not truth.** Mylae's
  `parseDescrRegions` drops every DaC region, because DaC writes a `legion:`
  line and he hard-codes RGB at line offset 4. Every format rule taken from the
  references was re-measured against DaC before it went into the roadmap.
- 2026-08-19: **A twin is compared per TIER, never per building.** A city/castle
  counterpart that trains the unit five levels up is not the same building, and
  a column that said "yes, somewhere" would be worse than none. `unit_instances`
  pairs the blocks once per line (`pair_levels`) rather than once per row.
- 2026-08-19: **A finding is only worth showing if it can come out zero.** The
  Twin column earns its width because DaC has 239 divergent rows and Third Age
  Reforged has none - the same check over both mods is what proves it is reading
  the file rather than describing its own assumptions.
- 2026-08-19: **The one code view that is not a record is read-only BY
  CONSTRUCTION.** `pools` gathers `recruit_pool` lines from a dozen building
  blocks, so no `parse`/`render` pair is registered for it at all - the pane
  cannot be saved from because the machinery to do so does not exist for that
  kind, not because a flag says no. Its `; building` headings are the module's
  own, so it is deliberately absent from `COMMENT_MARKS`.
- 2026-08-19: **One stash slot per LAYER.** The clause dialog used to borrow the
  slot the add-unit picker and the unit view also use, and the unit view can
  open the clause dialog on top of itself - so the two took turns clearing one
  slot and the building form underneath was lost. The dialog has its own now
  (`bldClauseStash`), and how deep the nesting goes stops mattering.
- 2026-08-19: **A redrawing helper checks that its target is on screen.**
  `bldTouched()` re-rendered the building body unconditionally, which is a null
  dereference the moment anything stages an edit from the unit view. Staging
  from another panel marks the working copy and lets that panel draw itself.
- 2026-08-19: **Two files may disagree about a path prefix and both be right.**
  A resource icon is written `data/ui/…` and a religion's pip `ui/pips/…`. The
  redundant half is dropped where the picture is requested, never in a parser -
  neither file is wrong about its own format, and a parser that "corrected" one
  of them would stop round-tripping.
- 2026-08-19: **A unit tier is `;@m2gt tier=3 variant=aor`, on the line above
  the unit's `type`** (user-confirmed). One owned prefix, invisible to the
  engine, skipped by every parser the way `#` is skipped in the EDB.
- 2026-08-19: **A `;@m2gt` line directly above a `type` line starts that unit's
  block.** Otherwise a comment above `type` belongs to the PREVIOUS unit, so the
  marker would describe one unit while living inside another and be left behind
  by every transfer, replace and sort. The change is safe precisely because the
  marker is ours - no real file contains one, so no existing byte-exact
  round-trip can be affected by it.
- 2026-08-19: **The mod's own EDU banners are read before the user is asked for
  anything.** A tier is in no game file, but a hand-organised EDU has already
  written one: **907 of DaC's 916 units sit under a `;--- X TIER N CAT ---`
  banner.** The tier is harvested from there and RECORDED on the unit, which is
  also what breaks a circle - the cleanup rewrites the banners, so a tier living
  only in a banner would be regenerated from itself.
- 2026-08-19: **A table of contents is not a layout.** DaC's TOC names a
  GENERALS section and MERCENARIES / SIEGE / SHIPS sections; the file has none
  of them. All 31 generals sit at the head of their own faction's run and the
  127 mercenaries are spread from unit 11 to unit 891. Faction first, kind
  second, and only the 13 units nobody owns fall through to a shared section.
- 2026-08-19: **A section is the author's own word for it, kept as text and
  never resolved to a faction slot.** Only 146 of DaC's 916 banner names match a
  localised faction name (a modder writes `CRAG`, `DORWINION`), and `ownership`
  cannot stand in because most units list a dozen factions and the line is a
  set, not a ranking. Section ORDER is likewise taken from where it is expressed
  - the median position of each section's units - not from
  `descr_sm_factions.txt`, which is a genuinely different order. Together these
  took DaC from 44% of the roster moving to 15%.
- 2026-08-19: **An untiered unit is never handed a tier by the banner written
  above it.** Its banner is written without a `TIER N`, because reading one back
  would move it out of the untiered group on the second run and cost the sorter
  its idempotence.
- 2026-08-19: **A hand placement is recorded, not just applied.** The ordering
  screen writes `order=N` onto the units it places so the NEXT cleanup honours
  them. A placement the following run silently undoes is a screen that wasted
  the user's time.
- 2026-08-19: **The tier is on the identity tab and deliberately NOT in the
  guided view.** The guided view is a view of real EDU field lines; a value the
  engine never reads does not belong among them, and putting it there would
  blur the distinction the "toolkit only" badge exists to make.
- 2026-08-19: **A byte-order mark is skipped for reading and KEPT for writing.**
  `keyblock.BOMS` / `without_bom` is the one definition, and `code_of` - the only
  function that turns a line into a keyword - drops it, which is safe precisely
  because nothing splices `code_of`'s result back. Stripping it on READ would
  have quietly rewritten the first three bytes of the user's file; this tool
  reads a file, it does not repair it behind their back.
- 2026-08-19: **"Not shipped here" is not the same as "missing".** A check may
  only assert the harsh reading when it can see the thing that would disprove it.
  The ancillary image check asserted a blank slot against a store of BUILDING art
  that could never hold an ancillary picture - 58 false findings across the two
  mods. When the evidence is not there the tool says so once, with the count and
  the way to get the check back, not 56 times.
- 2026-08-19: **A parser reads line endings the way its writer writes them, and
  the two are stated together.** `projectiles`, `mounts` and `engines` read exact
  (`keyblock.read_text`) and write exact (`write_text(..., exact=True)`); the rest
  read and write translating. Mixing the two turns every CRLF into CRCRLF. A block
  appended from a SOURCE mod is rewritten to the DESTINATION file's own ending
  (`keyblock.newline_of` / `to_newline`).
- 2026-08-19: **What must be forgotten is derived, never listed.**
  `Mod.drop_caches()` walks the class's own `cached_property` set. The two
  hand-written lists it replaces had drifted to 17 and 14 of 23, and
  `ownership_factions` was answering out of an EDU that had already been replaced.
- 2026-08-19: **A test names the mod it PREFERS, never the mod it requires**
  (`tests/_realmod.pick`). A suite that dies because a mod is not installed tells
  you nothing, and its silence is indistinguishable from a pass - three suites
  had been hiding two real defects that way.
- 2026-08-19: **The audit's two mention maps are not interchangeable, and no
  longer share a name.** `name_mentions` is keyed by modeldb ENTRY name with a
  row per name; `_mount_mentions` is keyed by MOUNT name with a bare filename.
  `mount_audit` took the first as a parameter and then shadowed it with the
  second, so its two model-keyed lookups read the mount map - wrong answers for
  `frees_model`, and a hard `TypeError` out of `mention_file` the moment a mount
  and an entry shared a name (four do in DaC, which is why `test_eop_and_lua`
  could not get past its first audit). The mount map is now `by_mount` and each
  lookup takes the map its key belongs to. `mention_file` reads either shape,
  because both maps are legitimately passed to it.
- 2026-08-19: **Hiding is a pair, not a filter.** The code view drops the
  comment-only lines from what it SHOWS, and the server rebuilds the real bytes
  from the view plus an opaque `hidden` list before anything parses or saves.
  The page still never learns what a comment looks like in a game file, and
  `buildings.py`'s rule - every one of the 7203 commented lines goes back byte
  for byte - is kept by construction rather than by care.
- 2026-08-19: **A hidden line is anchored to the KEYWORD of the line it sat
  above**, then to that line's exact text, then to its index. Anything else and
  typing a new value into the line below a comment moves the comment.
- 2026-08-19: **The tool's own layout pass is not the user's change.** The code
  view lines a record up as it opens; that is remembered separately (`cv.auto`)
  so the dialog is not "dirty" for having been looked at, while a save that
  happens for any other reason still writes the tidied block. A view that
  reports unsaved work you did not do is worse than a ragged file.
- 2026-08-19: **A paired row is written in the pair's order, not the file's.**
  `GF_PAIRS` decides which cards share a line; the group is emitted where its
  first member appears. It is the only place in the guided view where a card's
  position comes from anything but the file, so it is guarded by name.
- 2026-08-19: **Rows are placed from spans, never by counting.** Raw-lines mode
  lines each box up with the file line the SERVER says it came from. Counting
  rows drifts the moment a block has a `type` line, a hidden comment or a repeat
  - which every real block does.
- 2026-08-19: **A reveal is mod-relative.** `POST /api/reveal` takes a mod and a
  path under that mod's data folder and resolves it there; it never accepts an
  absolute path from the page.
- 2026-08-18: A startup check failing exits **2**, not 1, so the launcher points
  at the printed checks instead of guessing at a cause.
- 2026-08-18: "Could a server bind this port?" is asked by **binding** it. A
  connect cannot answer it: with a timeout set `connect_ex` returns the same code
  for a closed port and a wedged listener, and a closed loopback port can time out
  rather than refuse.
- 2026-08-18: A restart in place spawns the replacement FIRST (with `--wait-port`)
  and lets go of the port after. Stopping first ends the process before it can
  spawn anything.
- 2026-08-18: `config._read_json` tells **gone** from **busy**: the last-read
  fallback is for the moment `os.replace` makes a file unopenable, not for a file
  that has been deleted (audit §1.5).
- 2026-08-18: The log is **paged** - `/api/log` answers with a window plus the
  counts a filter needs, and computes `newer_count` itself, because "revert to
  here" was the only reason the page ever wanted the whole file.
- 2026-08-18: **The log records the user's actions too**, batched through
  `/api/activity` and written as untrusted text. A record of effects with no
  causes cannot be read back.
- 2026-08-18: An editor takes an undo baseline (`undoReset()`) at the point its
  working copy exists. Without one the first edit becomes the baseline, which is
  how five editors ended up looking as if Ctrl+Z was broken.
- 2026-08-18: **A cache never lives next to the app.** `config.cache_dir()` puts
  derived data in `%LOCALAPPDATA%`, because the app can be unzipped into OneDrive
  and a synced cache file can take 79 seconds to read or fail outright.
  `config/` stays put - it is the user's own data, not derived.
- 2026-08-18: **Traffic is liveness.** Any request keeps the server up; the
  heartbeat only still proves that a page really rendered. A heartbeat can be
  starved by the page's own requests, and the watchdog was killing live sessions.
- 2026-08-18: A resolved mod is trusted for one second before its files are
  re-checked (our own writes call `invalidate()`), and every load takes a
  generation and an abort signal - a superseded load is dropped, never painted.
- 2026-08-13: V2 architecture locked - vanilla-UI ports only; shared 2-way Code View widget built once (Phase 4); rebrand everywhere except GitHub repo name; version stays 1.x until Campaign Map lands (=2.0.0).
- 2026-08-13: Author permission obtained for reference-tool reuse; no licensing blocker.
- 2026-08-18: Every note in the UI is a lead line plus points (`docPoints()`), not prose joined by em dashes. Em dashes stay in code comments and in short appositives.
- 2026-08-19: **A measurement is fixed before the thing it measures.** 14g opened
  on "115 hits"; six of them were writing and the rest were
  `tools/prose_check.py` failing to stitch the `+` continuations its own
  docstring promised to stitch, reading `\'` as the end of a string, and taking
  inline CSS for prose. Rewriting 90 correct sentences to please a broken reader
  would have made the code worse and the next count meaningless.
- 2026-08-19: **A list is not a sentence, and neither is a fragment.** The `syn:`
  lines name a record's value slots in file order and every word in them is an
  EDU term that is lower case by definition; a string spliced into a sentence
  built at render time cannot be judged on its own first letter. Both are now
  rules in the checker, alongside the older "a label is not a sentence".
- 2026-08-18: A vocabulary the mod's own file declares is read from that file, never hardcoded - banners were the last EDU list breaking that rule.
- 2026-08-18: A test that measures a shipped mod reports the finding and asserts only OUR behaviour; it never fails because a mod has a bug.
- 2026-08-18: `#` at the start of an EDB line is a modder's annotation, not a keyword (the file's comment marker is `;`) - skipped by every parser in buildings.py, preserved verbatim on write.
- 2026-08-18: A count measured over installed mods is load-bearing only when the code leans on it. `plan_new_tree` writes an empty `plugins { }` because every real one is empty, NOT because every line has one - Third Age Reforged omits it on 45 of 112 and runs.
