# beta 2026-09-25

**Everything in v2.3.9 with the campaign map switched on**, plus the rest of
the map roadmap: the real world behind the map, a map resized or made from
nothing, layers generated from the real world, every tile as text, a campaign
brought in from another mod, a horde start, and a validator that listens to the
people who fix these maps by hand.

This is still a **beta** for the reason the first one was: the campaign map
editor is the first thing this toolkit does that WRITES to a campaign, and a
campaign is the one part of a mod where a bad write shows up ten turns in rather
than the moment you load it. Everything it writes is backed up and one Undo
away. Read the plan before you press Apply.

## On the map

* **Resize the map.** The new *Size* tab under Map grows or shrinks it by any
  number of tiles on each edge. New ground is the map's own sea. Every
  coordinate the game's files hold moves with it: the strat, the events, the
  custom battle tiles, the custom battles and the campaign scripts (DaC: 7,149
  coordinates in 9 files). A shrink that would leave a settlement, character or
  resource standing nowhere is refused, naming the file and line of each.

* **A new campaign on a map made from nothing.** *New map* on the same tab makes
  a campaign with its own map: an island of the size and number of provinces
  you ask for, a city in each, one province and a leader per faction you pick,
  the rest held by rebels. It loads and validates clean, and your base map is
  not touched.

* **Layers from the real world.** The new *Generate* tab makes heights from the
  real ground under the map's box, at the game's own scale; ground types from
  the heights; climates from the ground types; and rivers, cliffs and volcanoes
  from OpenStreetMap, drawn the way the game can build a river (no diagonal
  steps, no loops, one source each, never under a city). Each shows its picture
  before it writes.

* **The real world behind the map.** The *Real world* tab aligns the map to a
  box (typed, or a `bbox_coords.txt`), draws OpenStreetMap over it, fetches the
  real coastline and marks every land tile on its water side, and finds places
  by name. It is **off until Settings turns it on**, and nothing is sent until
  then.

* **Every tile as text, and a campaign as a zip.** The Export tab writes a
  `.tsv` with a row per tile (region, owner, ground, feature, climate,
  height…), and downloads one campaign at its `data/` paths.

* **A campaign from another mod.** *From another mod* under *New campaign*
  brings another installed mod's campaign in as a new one. Its factions are
  mapped onto your slots, and what your mod lacks is substituted, left out and
  counted.

* **A horde start for a faction that holds nothing.** The people panel's *Horde
  start* either puts leaders and armies on the map from turn one, or has them
  arrive later the way vanilla's Mongols do.

## Validator

From a modder's feedback, and checked against the game itself:

* **Ports are drawn on their dock**, the sea tile the game shows the port on,
  not one tile inland.
* **The same resource twice on a tile is no longer a finding.** The game loads
  every copy and the province trades all of them, so modders stack them on
  purpose, and the old Fix deleted lines the game uses.
* **A settlement on dense forest** is now fatal: a battle there can crash.
* **A river crossing on uneven ground** warns. A battle map averages the 5x5
  tiles around the fight, so a bridge under a mountain ends up in mid-air.
  **Smooth**, on each crossing, levels the ground around it and eases it back
  into the hills.

## Also in this build

Everything in **v2.3.9**: walls, gates and towers; agents and generals; a
building tree, a settlement model and any `data/` zip brought in from
elsewhere; campaign models drawn in their pose; strat textures in the game's
order; and animations from a pack unpacked in place. See `RELEASE_2_3_9.md`.
