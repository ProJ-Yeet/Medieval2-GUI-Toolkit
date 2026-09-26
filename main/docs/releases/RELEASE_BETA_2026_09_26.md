# beta 2026-09-26

**Everything in v2.4.0 with the campaign map switched on**, plus the rest of
Mylae's New Map Editor brought into the map screen: the real world picked
anywhere on Earth, reference and historical maps, lakes and seas, ground types
and climates from real data, historic sites, a new campaign on any stretch of
the real world, and the layers exported as one bundle.

This is still a **beta** for the reason the first one was: the campaign map
editor is the first thing this toolkit does that WRITES to a campaign, and a
campaign is the one part of a mod where a bad write shows up ten turns in rather
than the moment you load it. Everything it writes is backed up and one Undo
away. Read the plan before you press Apply.

## On the map

* **A world picker.** *Pick it on a world map…* on the Real world tab opens the
  whole world before any box exists: search for a place, draw the map's box,
  move it, resize it and turn it, with the size of a tile in km shown as you
  go.

* **Reference and historical maps.** The backdrop can be OpenStreetMap,
  OpenTopoMap, OSM Humanitarian, a relief drawn from the real heights, or
  OpenHistoricalMap at any year from 500 to 1600.

* **Lakes, lagoons and seas.** The real outlines, an island in a lake kept dry,
  shown over the map and made sea in one stroke with the Paint tab's Undo.

* **Ground types and climates from the real world.** Ground types from
  OpenStreetMap land use or from ESA land cover, and climates from the
  Köppen-Geiger zones, each a preview and one Undo.

* **A new campaign on the real world.** The new-map form can start a campaign
  on any box picked on the world map, with its cities picked there too, a
  province round each. It loads and validates clean.

* **Historic sites.** Castles, towers, monasteries and the rest of 21 kinds of
  site from OpenStreetMap, marked on the map, any of them made a fort, a
  watchtower or a new region.

* **Every OpenStreetMap request shown chunk by chunk.** A stretch that never
  answers costs only that stretch, and can be asked again with a click.

* **The map bundle.** *Export the map bundle* puts the map's layers, its box
  and a list of its provinces with their cities and ports in one zip, in the
  shape Mylae's editor exports.

## Everywhere else

Everything in v2.4.0: animations played out of a mod's packs in the Models
viewer, a transfer bringing the unit's animations, an edit saved into the pack,
another mod's animation or skeleton brought across, the packs' housekeeping on
the Home screen, and the transfer and start-up fixes. See its notes.
