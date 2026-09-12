# beta 2026-09-12

**The campaign map editor's roadmap is finished.** Eleven sessions since beta
2026-09-11, and this is all of them at once: the map drawn with the game's own
ground textures in summer and winter, forts, watchtowers and resources placed
and moved on it, settlement names on the map, a campaign browser that finds the
campaigns the engine's own menu never lists, a province that can now be deleted
as well as created, and a whole new campaign made from one that works.
Everything in **v2.3.0** is here too.

This is still a **beta** for the reason the first one was: the campaign map
editor is the first thing this toolkit does that WRITES to a campaign, and a
campaign is the one part of a mod where a bad write shows up ten turns in rather
than the moment you load it. Everything it writes is backed up and one Undo
away. Read the plan before you press Apply.

## New

### The map, drawn the way the game draws it

**Terrain textures**, on the Ground types row: the mod's own aerial-map textures
out of `data/terrain/aerial_map/ground_types`, one per climate and ground type,
tiled so that neighbouring tiles of one texture continue each other rather than
each showing a copy of it. **Summer or winter**, from two buttons beside it -
two fifths of Divide and Conquer's map and two thirds of Third Age Reforged's
are drawn with a different texture under snow. It is built once a season, so
panning and zooming over it costs nothing, and it goes under the whole stack, so
the provinces, the markers and the names still read on top of it.

**A tile whose texture cannot be found is drawn pink and counted, never quietly
skipped.** That is the arbiter's own rule, taken as it stands, and widened by
one case: a tile can have no texture because the file names one that is missing
*or* because nothing names one at all. Both are pink, both are counted, and
✓ Check names the file and a tile to go and look at for each one, in either
season. The second case found fifteen tiles of Divide and Conquer whose height
says land and whose ground type says sea, which nothing had ever reported.

**A colouring can now be tinted into the map instead of laid over it.** A tint
takes the colour of your theme and the light of what is already drawn, so the
terrain's hills, forests and rivers still read under a faction map instead of
being painted out. Frontiers can sit **on the edge** between two provinces or
**inside** them, where they still read once a hairline has vanished into the
zoom, and they can be drawn between the colouring's **groups** or round **every
province**. All of it goes into an exported TGA exactly as it is on screen.

### Things that stand on the map

**Forts, watchtowers and resources** can be placed, moved, edited and deleted:
click a tile, or drag the thing itself and drop it where it goes. Where a new
record is filed is derived from the map and the file rather than typed - a new
fort goes under the province its tile is in, because 393 of Divide and Conquer's
400 already are, and a new section goes where that file says sections go.
**Localize** draws a shrinking circle onto an item so that you can find it on a
large map.

**A refusal now names the nearest tile that would do.** One search over four
different rules - where a settlement or a port may stand, which side of the
shore a character belongs on, where an object may go, and what counts as sea -
each rule still living where it did. "No" with no way forward leaves you
clicking round a coastline one tile at a time.

**Settlement names on the map** (`L`), placed so that no name covers another
name or another settlement. The font does not grow with the zoom, and a name
with no room is left off rather than drawn over its neighbour - the toolbar says
how many are named, and zooming in finds room for the rest. From 8 pixels a tile
every settlement on all three installed maps is named.

**A ⌖ beside every x, y** on the people and events panels: press it, click the
map, and that tile is written into the field in the coordinates
`descr_strat.txt` uses, without selecting anything on the way.

### Getting to the thing you want

**Find** takes a province, a settlement or a region ID and goes to it, matching
the words the player reads as well as the code name the files use, out of the
map already on screen and with nothing fetched per keystroke.

**Views** saves what the map looks like - which layers, in what order, at what
opacity, the colours punched out of each, the colouring over the top, the season
and the border style - under a name you can come back to, on any mod.

**Campaign** lists every campaign the mod ships with what is in each one, and
opens it. This turned out to be more than a convenience: a mod routinely keeps a
whole second campaign in a subfolder that the engine's own new-game menu never
lists, and **both mods this was measured against have one** - Divide and
Conquer's Shattered Alliances (30 factions, 199 settlements) and Third Age
Reforged's Fellowship Campaign (16 factions, 129 settlements, and ten map layers
of its own). Every panel on this screen had been working on one campaign and no
other. Pick one and the whole screen re-reads it.

**A campaign that ships its own map files is now drawn and judged on those.**
Reforged's Fellowship campaign has its own ten layers; before this it was being
shown the base map's. The brush still paints `world/maps/base` and is now
refused - with the reason, and with the campaigns that do read the base - rather
than painting a map nobody can see.

### Making and unmaking

**A province can be deleted**, which is the other half of the wizard that makes
one. Its land goes whole to a neighbour it shares a border with - every one is
offered, longest border first - and everything that named it goes with it: the
record, the settlement block in each campaign, the win conditions, the mercenary
pool, the music type, the lookup pair, the custom battle tiles. Its seat becomes
ground, because a province has one, and you are asked what happens to its port,
because the heir may already have one.

**What the panel says before you commit is the point.** Bare Geomod's own manual
admits that after its delete "resources, forts and characters will remain",
which is a dangling reference it ships. Ours lists the whole set of files, says
what stands on the land and whose province it becomes, and lists every line of
the campaign script that names the province - which is shown and never edited,
because a script is a grammar this toolkit does not parse and a silent rewrite
of one would be worse than no rewrite.

**+ New campaign**, under the campaign list, makes a whole new campaign out of
one that already works: the folder copied, the compiled `map.rwm` deliberately
left behind so the game rebuilds it, the `campaign` line set to the new name,
and every menu title and blurb - the campaign's own and each faction's - written
again under the new campaign's key so the new-game menu has something to show.
It tells you the size first, and whether the name you have chosen is one the
engine's own menu will list.

### And everything in v2.3.0

The faction completeness audit and the Raw text editor are in this build too.
See that note.

## Fixed

### A new province now reaches every campaign that reads the map

**The biggest of these, and it was a crash.** A province made with the New
region wizard was written into `descr_regions.txt` and painted onto
`map_regions.tga`, and that was all: no settlement block in any
`descr_strat.txt`, no owner, no music type, no name on the menu. A beta user's
log opened with `cannot find this pixel colour(8,8,8) in the region_db` - and
8 8 8 is the first colour the wizard suggests.

The wizard now reaches every campaign that reads the base map, which is more
than one: a settlement block in each campaign's own start position under an
owner you pick, the record in whichever `descr_regions.txt` that campaign reads,
a music type (the neighbour's, where it shares the longest border, unless you
choose), the name lookup where the campaign ships one, and that campaign's
compiled map deleted. The two words the player reads are now **required** rather
than warned about, because the engine asserts on a name it cannot find instead
of falling back to the code name. The creator faction is checked against the
factions your mod actually defines.

### Every province reading as one nobody declared

A mod whose `descr_regions.txt` is written flush left - no tab or space in front
of the settlement, the faction, the colour or any of it - came out of the reader
as one record per line, with a colour on none of them: the findings panel
listing every province on the map as undeclared, hovering one saying the file
never declares it, clicking one selecting nothing.

The indent was never part of the format - the engine's own parser ignores
whitespace, which is why the mod plays. The reader falls back to the record's
own grammar when there is no indent to read it off. Measured on the mod that
reported it: **0 records with a colour before, 209 after.** Measured the other
way, on Third Age Reforged's file with the indentation stripped: 199 provinces
undeclared before, 0 after. On the three real mods as they ship, every record
reads field for field identical to before.

### Four layers that would not open

`map_fog.tga`, `map_features.tga`, `map_trade_routes.tga` and
`map_roughness.tga` on another mod each came back as `buffer overrun when
reading image file`. The files are fine and the game reads all four: TGA
compresses a row as packets, and nothing in the format says a packet has to stop
at the end of a row. There is now a decoder here for exactly the files the fast
path refuses - 37,879 real TGAs decode identically either way, so nothing that
already worked changed - and a file that really is truncated says so in pixels
rather than in buffers.

### The map said "no region" over most of the map, for some people

A user's browser read Third Age Reforged's dense forest, `0,64,0`, as `0,65,1`.
Canvas anti-fingerprinting - Brave's shields, Firefox's resist-fingerprinting,
several privacy extensions - adds noise to every pixel read back out of a
canvas, and the map screen was reading its layers back out of one. It never
does now: layers arrive as raw bytes and canvases are only ever written to.

### The drag that never dropped

Dragging a marker on the map had never once dropped it, because the pointer's
travel was only being counted while panning. Found by a check that dragged with
the pointer instead of calling the function the gesture ends in.

### Smaller, and worth knowing

* **Three map layers were being read wrong.** The heights, ground types and
  climates layers are sampled at tile centres rather than per tile, and the
  screen was reading them as if they were not.
* **↺ Reset** on the map toolbar puts everything about how the map is read back
  to how it first opens.
* **The screen and an exported TGA now draw the same frontiers.** The panel has
  said they were the same picture since the export was added; the screen was
  drawing a line round every province and the file frontiers between blocs.
* **The browser console stays usable when the toolkit's server is not there** -
  see the v2.3.0 note.

## Still worth knowing before you use it

A save on this screen writes to files the game reads at campaign start, and some
of what it writes shows up turns later rather than at load. Everything is backed
up into one set per save and 🕑 Log undoes the whole set in one go. The plan
before each save is the honest list of what it will write - read it.

Deleting a province renumbers every region the engine scans after it. Nothing in
your mod has to be edited for that, because names are the keys - but a script
that names a region by its number now names a different one, and the panel says
so with the count.
