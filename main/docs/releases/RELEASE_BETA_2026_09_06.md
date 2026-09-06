# beta 2026-09-06

The campaign map is editable. Ten TGA layers, `descr_regions.txt` and
`descr_strat.txt` are one screen: paint a province and every file that names it
follows, drag a general onto a tile, place a settlement, and check the whole map
against what the engine will accept before the game ever sees it.

This is a **beta**. The map editor is feature-complete and its data layer is
covered by the suite, but it is the first build in anyone's hands that writes to
a campaign, and a campaign is the one part of a mod where a bad write shows up
ten turns in rather than the moment you load it. Everything it writes is backed
up and one Undo away, the same as the rest of the toolkit. Read the plan before
you press Apply.

## Added

* **Campaign Map, a whole new module.** It reads the ten layers under
  `data/world/maps/base` through Pillow, `descr_terrain.txt`,
  `descr_regions.txt` in every form the game accepts, and the whole of
  `descr_strat.txt` - Divide and Conquer's parses in one pass in 144 ms into
  6,100 nodes and comes back byte for byte, which is the gate everything else
  here stands on. Both of vanilla's campaigns round-trip too.

  What you can do with it:

  * **Look at it properly.** Every layer as its own toggle, a legend that names
    the colour under the pointer from the mod's own vocabularies rather than
    from a guess, and a hover tooltip giving the tile in both coordinate systems
    with a swatch and a named value for each aligned layer. A colour no table
    claims is reported as unclaimed instead of being nearest-matched onto the
    wrong province.
  * **Paint.** Regions, climates, ground types, features and heights, with the
    brush constrained to what the layer allows, and `descr_regions.txt` kept in
    step with what the picture now says.
  * **See what is standing on the map.** A markers layer for everything
    `descr_strat.txt` puts on a tile: settlements by level and kind, characters
    by type, forts, watchtowers and trade resources - 855 of them on Third Age
    Reforged, 2,035 on Divide and Conquer, drawn in under 3 ms. Off by default,
    with its five categories toggling separately, because 1,131 resources over
    the provinces is not a map any more.
  * **Move a character by dragging him.** The drop runs the same plan, the same
    confirmation and the same undo as the panel beside it, and the drag itself
    previews only what the browser can answer exactly - on the grid, and sea by
    the measured `map_heights` rule with river crossings excluded.
  * **Edit the campaign.** Settlements and their building lists, characters,
    armies and the family tree, the campaign's own settings, a faction's
    campaign entry and the win conditions, each with its own plan and its own
    Undo entry.
  * **Check it.** A validator that reads the map and the campaign together and
    reports what the engine would refuse: regions painted but never declared,
    settlements no region claims, ports attached to nothing, layers whose sizes
    do not agree. It reports rather than repairs; the four faults found while
    building it are test cases now, including a genuine 517-pixel hole in Divide
    and Conquer that no `descr_regions.txt` record declares.
  * **Query it.** Find a region, a faction or a settlement by name and go to it,
    with information maps over the answer - the way to reach a province too
    small to click, like Reforged's two-tile `Edhellond_Province`.
  * **See the strat models.** A 3D preview of what the campaign map draws, off
    a `.cas` decoder written for it.

* **A faction on one screen, over two files.** `descr_sm_factions.txt` says what
  a faction is and `descr_strat.txt` says what it starts the campaign with.
  They are one screen now, with two engines, two Save buttons and two Undo
  entries, because they are two files. The picker lists every faction either
  file knows and says which of the two is missing a slot.

* **A new battle-model entry can be given its own attachment skin.** An
  attachment is a second texture group with its own files per faction - the
  horse under a rider, a shield sheet - and the new-entry form could only hand
  it the main texture. It has its own texture and normal-map slots now, shown
  when the entry being cloned actually has an attachment group, with the old
  checkbox left as the fallback for whichever slot you leave empty.

* **Replacing a unit card asks where it goes.** A card is a file per owning
  faction, and the old button had one answer: all of them. The dialog now lists
  every folder the card is looked up under - each owning faction plus the
  mercs/merc fallback - with a thumbnail of what that folder holds today and a
  tick box. **Replace for all** is one button; untick the two that should keep
  their own art and they are left exactly as they were.

* **...and which picture.** A unit whose folders really do hold several
  different cards has the art already, and the question is only which one the
  ticked folders should get - so those pictures are offered as pictures, above
  "Choose a file from disk...". Where every folder already shares one picture
  there is nothing to standardise, and that half of the dialog is not drawn.

## Changed

* **A new model entry adds an armour tier instead of eating one.** "Point EDU
  slot at it" listed only the slots the unit already had and opened on the first
  one the cloned entry filled, so a new entry cloned from an armour upgrade
  wrote straight over it. Every choice now says what it would replace
  (`armour_ug_models#1 (replace numenor_axemen)`), the list ends with the tier
  after the unit's last, and that is what it opens on. The entry is named to
  match, and appending a tier grows `armour_ug_levels` with it - a tier past the
  end of that list is one the game can never reach.

* **Home shows the Campaign Map card.** `campmap` was missing from the module
  readiness table, so the card was dropped with no error on every mod. It
  declares its fourteen files now - the map half and the campaign half
  separately, so a map-only mod reports what it is short of - and the suite
  asserts that every module in the menu has an entry, which is the class of bug
  rather than this instance of it.

## Fixed

* **An imported unit card actually saves.** Staging a card or an info card left
  the editor thinking nothing had changed, so Save answered "Nothing to save"
  and nothing ever reached the mod. It counts as a change now.

* **...and the picture you replaced stops being the picture you see.** Two
  faults on top of each other. `shutil.copy2` carries the SOURCE file's
  timestamps onto the copy, and a mod's files come out of one archive stamped
  to the same second - so copying one of Third Age Reforged's unit cards over
  another left the destination with the very mtime it already had, and the icon
  cache, whose key is the path and that mtime, went on handing out the picture
  that had just been overwritten. A file this tool writes is now stamped with
  the time it wrote it, which is both true and what every cache downstream reads.
  The second half was in the page: the stamp that told the browser to re-fetch
  was painted onto the `<img>` tags that happened to be on screen, and a save
  closes the editor and rebuilds the whole unit grid, whose fresh URLs went
  straight back to the browser cache. The stamp lives in the page's state now,
  so every URL built after a write is one the cache has never seen.

* **Renaming a staged model entry takes the unit's lines with it.** The armour
  tier menu writes the new tier into `armour_ug_models` the moment it is added
  and only then opens the form, so renaming the entry there left the unit
  pointing at a name that was never going to exist. The lines that name it
  follow the rename, and the form says which ones they are before you type.

* **A staged model entry is no longer called missing.** The field checks ask
  what a save is about to create, and the unit editor answered "nothing" while
  holding a list of pending entries - so naming one in `armour_ug_models` was
  flagged "not an entry in this mod's battle_models.modeldb", which was true of
  the mod as it stood and false of the mod that same save would leave behind.

* **The entry list refreshes after you add an entry.** The model picker's table
  and the field editor's vocabulary were read once per mod and kept for the
  whole session, so an entry created here stayed invisible until the page was
  reloaded. A save drops both, and an entry staged but not yet saved is offered
  by both, marked as staged.

* **The hover box no longer leaves a trail.** Dirty rectangles were worked out
  in CSS pixels on a canvas backed at `devicePixelRatio`, so at 150% Windows
  scaling every edge landed half way through a device pixel: 1,330 residue
  pixels over two pointer sweeps, and none once the rectangle is snapped
  outwards to whole device pixels.

* **Every region is clickable.** A settlement pixel is black and a port pixel
  white, and neither is a region colour, so clicking a city said "no region
  record on this tile" while the pointer was on Minas Tirith - 199 of Reforged's
  200 settlements behaved that way. A marker now answers with the region that
  owns it.

* **The resource art loads.** The markers layer asked `/api/icon` for a mod's
  resource pictures, and the image routes are the one family that predates the
  `/api` prefix, so every request 404ed silently and the drawn glyph stood in
  for art the mod ships.

* **The menu's hints are sentences**, and `dev/checks/prose_check.py` has the rule
  that catches the next one.

## Also

The credits name the four works this toolkit took reference from, with thanks
for the permission: Mylae's M2TW Editor, Fynn's Medieval II Total War Modding
Tool, Bare Geomod by Sinople and Gigantus, and Withwnar's TWMapReader.

## Known limits of this beta

* Forts, watchtowers and resources are **read and drawn, not placed**. The map
  shows Divide and Conquer's 105 forts, 295 watchtowers and 1,131 resources;
  nothing here writes a new one yet.
* The terrain render is flat colour, not textured.
* Deleting a region and creating a campaign from scratch are not in this build.
* Nine lines of Divide and Conquer's `descr_strat.txt` do not parse, and all
  nine are the mod's own defects (a trailing comma, `rmour` for `armour`, a
  settlement called `tyuiop`). They are read as far as they can be, kept, and
  reported by line number rather than silently dropped.
