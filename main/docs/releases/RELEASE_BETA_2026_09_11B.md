# beta 2026-09-11b

Two bugs off beta reports, both of them the same shape: a file the game reads
perfectly well that this toolkit would not read at all. Everything on beta
2026-09-11 is here, and so is everything in v2.2.4.

This is still a **beta** for the reason the first one was: the campaign map
editor is the first thing this toolkit does that WRITES to a campaign, and a
campaign is the one part of a mod where a bad write shows up ten turns in rather
than the moment you load it. Everything it writes is backed up and one Undo
away. Read the plan before you press Apply.

## Fixed

### Every province reading as one nobody declared

A mod whose `descr_regions.txt` is written flush left - no tab or space in front
of the settlement, the faction, the colour or any of it - came out of the reader
as one record per line, with a colour on none of them. What that looked like on
the screen:

* the findings panel listing **every province on the map** as "painted and
  declared nowhere in descr_regions.txt", biggest first
* **hovering a province saying it is one the file never declares**, and clicking
  it selecting nothing
* the province still being **findable in the Query panel**, because that table is
  built from the records rather than from the pixels, so it filled up with rows
  that were single lines of the file - `spain`, `brigands`, `5`. Going to one
  highlighted the province and then there was no way to select it again, because
  the map itself had no region under the pointer to select.

One cause, all three. The reader took the indent as the signal for where a
record starts, because vanilla, Divide and Conquer and Third Age Reforged all
write one - but the indent was never part of the format, and the engine's own
parser ignores whitespace, which is why the mod plays. It now falls back to the
record's own grammar when there is no indent to read it off: the `R G B` line
was already the anchor, and the settlement, the creator faction and the rebel
type are the three lines in front of it. The wasteland short form, which has no
settlement line, comes out of the same walk.

Measured on the mod that reported it: **0 records with a colour before, 209
after, none of them with anything left to report.** Measured the other way, on
Third Age Reforged's own file with the indentation stripped out: 199 provinces
undeclared before, 0 after. And on the three real mods as they actually ship,
every record reads field for field and line for line identical to before.

A byte-order mark in front of the first province is no longer read as part of
its name either. The same file had one.

### Four layers that would not open

`map_fog.tga`, `map_features.tga`, `map_trade_routes.tga` and
`map_roughness.tga` on another mod each came back as `buffer overrun when
reading image file`, and the layer panel hid them.

The files are fine and the game reads all four. TGA compresses a row as packets,
and nothing in the format says a packet has to stop at the end of a row - only
the 2.0 revision asks writers to avoid it, and plenty do not. The image library
this toolkit decodes with works a scanline at a time and treats such a packet as
a corrupt file. Nothing vanilla, Divide and Conquer or Third Age Reforged ships
is packed that way, which is why this had never come up.

There is now a decoder here for exactly the files it refuses. It is the second
reading, not the first: 37,879 real TGAs on one machine decode identically
either way, so the fast path is untouched and only the refusals come here. A
file that really is truncated now says so in pixels - "the pixel data ends 4,095
pixel(s) short of the 4,096 the header asks for" - rather than in buffers.

## Not fixed, and worth knowing if you are creating a province

A province made with the New region wizard is written into `descr_regions.txt`
and painted onto `map_regions.tga`, and that is all. It does **not** get a
settlement block in `descr_strat.txt`, so no faction starts there and nothing
owns it, and the creator faction you type is not checked against the factions
your mod actually has. A region the engine cannot give an owner is a crash at
the end of a turn. Until that is closed, add the settlement block by hand on the
campaign screen after creating the province, and check the name against your
`descr_sm_factions.txt`.
