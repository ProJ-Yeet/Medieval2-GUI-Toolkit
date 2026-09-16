# beta 2026-09-16

**Everything in v2.3.3 with the campaign map switched on** - and this is the
biggest map build so far. Fifteen phases have landed since beta 2026-09-12c and
twelve of them are this editor: a rebuilt panel, the brush's colours moved
beside the map, climate zones, region recolouring, rebel pools, the campaign
script's spawns, the front-end picture, and four bugs that stopped whole maps
being read at all.

This is still a **beta** for the reason the first one was: the campaign map
editor is the first thing this toolkit does that WRITES to a campaign, and a
campaign is the one part of a mod where a bad write shows up ten turns in rather
than the moment you load it. Everything it writes is backed up and one Undo
away. Read the plan before you press Apply.

## The panel, rebuilt

* **Two strips, and one screen at a time.** There were six tabs across the top -
  Map, Validate, Query, Paint, Province, Campaign - and everything inside the
  one you picked was stacked underneath it. Province was seven panels in a
  column.

  Each of those six now has a row of its own under it. Province is
  `Region / Rebels / Settlement / Characters / Forts`. Map is
  `Campaigns / Find / Views / Front end`. Paint is
  `Brush / Climates / Markers / Events`. Validate is `Findings / Rules`.

  **Clicking one opens it.** Most of these panels used to read nothing until you
  pressed their own button, which was right when they were all on screen at once
  and wrong the moment one of them is a tab: clicking `Forts` and getting a
  button that says `Forts` is a click the screen owes you. Nothing is read until
  you choose the tab, so opening the map costs what it did.

  Which row you were on is remembered per section, across sessions, and rides in
  a saved view. **Reset** puts it back with the rest.

* **The colours are on the left of the map, not behind a tab on the right.** A
  palette is something you reach for on every single stroke, and getting to it
  took the right-hand column away from whatever you had up. Arm the brush and a
  column appears on the other side of the map with the three things a stroke
  needs: which layer, which colour, and what is about to be written. Put the
  brush down and the map gets the width back.

* **The layer you are painting is a toggle, not a dropdown.** Eight buttons -
  Regions, Heights, Ground types, Climates, Features, Trade routes, Roughness,
  Fog - sitting directly on top of that layer's own colours, which is what
  changes when you switch. A layer this map has a problem with is greyed with
  the reason on its tooltip rather than left out.

* **The brush's tools are on a toolbar over the map.** A stroke is made with
  your eyes on the map, and a control you look away from to reach is a control
  you lose the stroke to. The five tools, the size and the shape are a second
  row on the toolbar that already carried Fit, 1:1, the zooms, Names, Labels and
  Reset. It folds away and keeps the brush armed.

* **The tooltip holds still.** It changed width and height as you moved, under a
  pointer that was also moving. Fixed width, a row per layer whatever that layer
  says, a fixed number of marker lines, and a head that reserves its two lines
  whether or not it has them.

## New on the map

* **Add a climate zone.** All four installed mods declare exactly the twelve
  climates the engine ships, in the engine's order, and not one added a
  thirteenth - Divide and Conquer took `unused1` over as "Harondor" (18,970
  tiles) and `unused2` as "Lorien" (192), and Reforged did the same at 5,466 and
  182. So a take-over is offered first and a new name second, and it writes four
  files. Painting the climate map stays the brush's job.

* **Change a region's colour.** And the measurement that makes it safe: **a
  recolour does not renumber.** A region ID is the order a colour is first met
  in a scan of `map_regions.tga`, and a recolour moves no pixel - measured at
  **0 IDs moved** on both installed maps and again off disk after a real save.
  The one case that does renumber is a **merge** into a colour another province
  already uses, which moves 51 IDs on DaC and takes `Celebrant_Province` off the
  map, and that is refused.

  It is every tile of the colour, not a bucket fill: 8 of DaC's 200 regions are
  not one connected blob, and a bucket from Forodwaith's anchor would leave
  13,912 of its 40,995 tiles behind.

* **Rebels, both ways round.** Every rebel faction a mod declares and the
  provinces that name it, with bulk assignment - the reverse of the per-province
  box that was already there. The number that matters is on every row:
  **Reforged sets `chance 0` on all 27 blocks its provinces name**, so all 199
  of its provinces point at a faction that never spawns.

* **The campaign script's spawns are on the map.** Four fifths of what Divide
  and Conquer's imperial campaign puts on the map was invisible here: its script
  spawns **1,324 things - 1,317 armies carrying 3,822 units** - against the 305
  characters `descr_strat.txt` places. Shattered Alliances is another 1,131.
  `spawn` is the markers layer's eighth category and **the only one that opens
  off**, because switching it on quadruples what is drawn. There is a CSV export
  beside it, because a TGA is the right export for a picture and useless for
  1,324 rows.

  Every one of the 2,510 `spawn_army` blocks carries a coordinate, so the
  reading is complete rather than a sample: 1,322 of DaC's 1,324 land in a named
  province and both misses are admirals, which is correct, because an admiral is
  a fleet.

* **The front-end picture, over the map.** `map_FE.tga` is what the
  campaign-selection screen draws, and it can now be shown over the map and
  dragged into place. **Not one of the eight installed copies is its own map's
  shape** - the closest is 3.6% out - and two of them are not maps at all, so
  the frame carries the picture's aspect and you place it.

* **Pick what fills a tile with no terrain texture.** It was always pink.
  `vanilla_kingdoms_uncompromised` ships no texture folder at all, so **159,855
  tiles - all its land, 57.6% of the map** - came up pink; the choice is now
  pink, neutral or sea, and it rides in a saved view.

* **Three small wins in one:** copy the tile under the pointer to the clipboard
  in the game's own coordinate form, set which music type a province plays, and
  name its legion. DaC writes 199 legion lines of which only 80 name their own
  record.

* **Three new map rules**, on rivers and fords: a river on all four sides of a
  tile, a river network with no white source, and a ford in open sea. All three
  find **nothing on any of the five installed maps**, which is what they are
  for. Only the ford has a safe automatic repair; the other two need the map
  author's intent, and both refusals say so.

* **Playable, unlockable or not playable, per faction** - and the refusal that
  matters: a save that would leave a campaign with **no** playable faction is
  fatal, while a campaign that already has none stays editable, because a flat
  refusal would trap it on the one screen that repairs it.

## Fixed

* **An M2EX map read "no region" on every tile.** The engine's 200-region
  ceiling was being applied to the number of distinct colours in
  `map_regions.tga`, which is not the same number - and on a map with more than
  200 it refused to build the index at all, so nothing on the screen worked.

* **And then a map was refused over three shades of sea.** Same conflation, one
  level down: Vanilla Redux is 295×189 with 252 records and 258 colours, and
  three of those colours are **591 pixels of paint-program noise** within ten of
  the sea on one channel. It now indexes in 84 ms - and the eleven validator
  rules that could never run against it have **sixteen fatal findings** about a
  real map: five second settlement pixels, five provinces with no settlement
  pixel at all, four ports on sea tiles, one settlement on Impassable.

* **DaC's Erebor_Province was invisible: 200 regions read as 199.** One stray
  leading space on its name line, and with it 517 painted tiles declared
  nowhere and its settlement marker reported as an orphan. Three more defects in
  the same record: a province created with no resources reached the file as an
  eight-line record in a file of nine-line records, and `none` read as a
  resource name produced **931 false findings** across two mods.

* **A save ate a blank line out of `descr_regions.txt`.**

* **A region save wrote the base `descr_regions.txt` whatever campaign was on
  screen.** Reforged's Fellowship campaign ships its own copy and the two differ
  in **eleven records**. Its other half: only the base `map.rwm` was deleted on
  save, and that campaign ships its own, 14 KB apart.

* **The front-end picture was being squeezed and scaled back up.** DaC's 768×768
  picture was drawn into a canvas one pixel per *tile* - 510×487 - and scaled up
  from there. It reaches the screen byte for byte identical to the file now.

* **The Factions tab in Minor Files left the screen entirely.** With the map on
  it landed on the campaign map and left the tab unlit behind it - two different
  screens behind one button depending on a flag you cannot see. It goes to the
  factions mode on both lines now, which is what every public build has done.
  The combined faction screen is still there, inside the campaign map.

* **A 3D panel left over from another screen kept drawing to a page that was
  gone.** Carried up from v2.3.3, and it applies to the strat model viewer here
  as well.

## What has not changed

The rebuilt panel changes where things are, not what they do. No campaign file
is written differently for any of it.
