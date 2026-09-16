# beta 2026-09-16

**Everything in v2.3.3 with the campaign map switched on**, and the map screen
is the reason this build exists: its right-hand panel has been rebuilt, and the
brush's colours have moved to the other side of the map.

This is still a **beta** for the reason the first one was: the campaign map
editor is the first thing this toolkit does that WRITES to a campaign, and a
campaign is the one part of a mod where a bad write shows up ten turns in
rather than the moment you load it. Everything it writes is backed up and one
Undo away. Read the plan before you press Apply.

## New

* **The panel beside the map is two strips, and shows one screen at a time.**
  There were six tabs across the top - Map, Validate, Query, Paint, Province,
  Campaign - and everything inside the one you picked was stacked underneath
  it. Province was seven panels in a column: the region record, its rebels, its
  settlement, its characters, its forts, and the delete and recolour forms
  under all of that.

  Each of those six now has a row of its own under it, and one of them is up at
  a time. Province is `Region / Rebels / Settlement / Characters / Forts`. Map
  is `Campaigns / Find / Views / Front end`. Paint is `Brush / Climates /
  Markers / Events`. Validate is `Findings / Rules`.

  **Clicking one opens it.** Most of these panels used to read nothing until
  you pressed their own button, which was right when they were all on screen at
  once and wrong the moment one of them is a tab: clicking `Forts` and getting
  a button that says `Forts` is a click the screen owes you. Nothing is read
  until you choose the tab, so opening the map still costs what it did.

  Which row you were on is remembered per section, across sessions, and it
  rides in a saved view like the layers and the tab already did. **Reset** puts
  it back with the rest.

* **The colours are on the left of the map now, not behind a tab on the right.**
  A palette is something you reach for on every single stroke, and it was two
  clicks away - and getting to it took the right-hand column away from whatever
  else you had up, the region record or the validator.

  Arm the brush and a column appears on the other side of the map with the
  three things a stroke needs: which layer, which colour, and what is about to
  be written. Put the brush down and it goes away, and the map gets the width
  back.

* **The layer you are painting is a toggle, not a dropdown.** It was a
  `<select>` on the toolbar, which made the one thing a stroke is about to
  change a word you had to open a menu to read. It is eight buttons at the top
  of the new column - Regions, Heights, Ground types, Climates, Features, Trade
  routes, Roughness, Fog - with the one you are on lit, sitting directly on top
  of that layer's own colours, which is what changes when you switch. A layer
  this map has a problem with is greyed with the reason on its tooltip rather
  than left out of the list.

## Moved

* **Strat models are in the Models Editor now.** The 3D browser that was
  Campaign Map → Strat models is on Models Editor → Strat map, beside the
  entries from `descr_model_strat.txt` that it draws. It never edited anything
  on the map screen, and it is the only place in the toolkit that could show
  you a settlement - so it now sits with the rest of a mod's models rather than
  four panels down a column about painting provinces.

  It gained the entry list on the way: see v2.3.3's notes, which are in this
  build too.

## What has not changed

Nothing about what the brush writes, what the validator checks, or what any
panel saves. This is where those panels are, not what they do.
