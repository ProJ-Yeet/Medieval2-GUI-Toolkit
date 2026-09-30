# beta 2026-09-30

**Everything in v2.4.1 with the campaign map switched on**, plus four changes
on the map from users' reports: a watchtower's line of sight drawn on the map,
a region rename that no longer takes seconds, painting that survives saving a
settlement, and a way back to the brush from the province itself.

This is still a **beta** for the reason the first one was: the campaign map
editor is the first thing this toolkit does that WRITES to a campaign, and a
campaign is the one part of a mod where a bad write shows up ten turns in rather
than the moment you load it. Everything it writes is backed up and one Undo
away. Read the plan before you press Apply.

## On the map

* **A watchtower's line of sight.** Every watchtower's reach, 10 tiles, drawn
  filled or as an outline (`w`, or the box in the markers panel), and drawn
  under the pointer while one is being placed or dragged, so its spot can be
  chosen by what it covers.

* **Paint its tiles.** The region's own panel has a button that picks up the
  brush with that province as its colour, for adding tiles to it or redrawing
  its border.

## Fixed on the map

* **Painting is no longer lost to a settlement save.** Painting a province and
  then making a settlement its faction's capital threw the unsaved painting
  away. It now carries on where it was, unless a map image it painted was
  changed outside the tool.

* **Renaming a region is quick.** The first rename planned in 11 seconds on
  Divide and Conquer, and every save after it paid that again; it now takes
  about one.
