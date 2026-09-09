# beta 2026-09-09

Six campaign files nothing here could edit, and the text that names the things
you create. It is **everything in v2.2.2 with the campaign map switched on**, so
the Guilds editor and the `descr_names.txt` correction are in this build too.

This is still a **beta** for the reason the first one was: the campaign map
editor is the first thing this toolkit does that WRITES to a campaign, and a
campaign is the one part of a mod where a bad write shows up ten turns in rather
than the moment you load it. Everything it writes is backed up and one Undo
away. Read the plan before you press Apply.

## New since beta 2026-09-06b

### Four files nobody could edit

* **What the new-game menu calls a campaign, and each faction in it.**
  `campaign_descriptions.txt` holds the title and the blurb the menu shows, per
  campaign and per faction. A faction the campaign has never named shows its
  **code name** there and nothing on disk says so, so the screen lists every
  faction the campaign starts whether it has text or not, and saving creates the
  keys rather than refusing because they are absent.

* **Faction movies.** `descr_faction_movies.xml` and its four slots - intro,
  victory, defeat, death - on the same faction screen. Neither installed mod's
  copy ends with a newline, which is exactly why this is a line splice rather
  than a serialiser: a tool that rebuilt the file from its own model would
  rewrite both of them on the first save of either.

* **Which mercenaries a province sells.** `descr_mercenaries.txt` groups
  provinces into pools and sells a different roster in each. It has been read
  since the map editor's second session and the picker has been deferred ever
  since. Measured across both mods: 84 pools over 341 provinces, and **not one
  province is in two pools** - which is what lets this be a single choice on the
  region panel rather than a set of tick boxes.

* **Guilds.** See the v2.2.2 notes; it is on the menu in both builds.

### Events, and disasters

* **`descr_events.txt` and `descr_disasters.txt`**, the two files that make
  something happen without anybody doing it - the Black Death, an earthquake, a
  volcano - with their dates, their positions and their text keys. Both installed
  mods ship an empty `descr_disasters.txt`, so this was measured against the
  game's own copy, which documents its keys in its own header.

* **They are drawn on the map.** An event's and a disaster's positions are two
  more categories of the marker layer rather than a layer of their own, because
  two overlays that each know half of what stands on a tile is how a tooltip
  ends up telling half the truth. Events are amber six-pointed bursts, disasters
  red eight-pointed ones.

* There is no drag, and that is deliberate: a character stands on exactly one
  tile and an event has a *list* of positions - the Black Death's third wave has
  seventeen - so dragging one has no obvious subject. **`＋ from the picked
  tile`** is what replaces it: click the map, click the button, and the
  coordinate is written in the file's own convention with nobody doing the
  arithmetic.

* One thing the validator found in the game's own data: `black_death_3` has a
  position at 102,74, which is sea.

### The words the player actually reads

* **Name a province and its settlement.** A province is named twice in a mod - a
  code name every file points at, and a line in
  `imperial_campaign_regions_and_settlement_names.txt` the game shows. Miss the
  second and the campaign map reads `Anorien_Province`. The region panel edits
  both lines now, and the check that has been reporting a missing one since the
  validator was written finally has something that can fix it.

* **The paint tool names a province as you create it.** The new-region wizard
  has two more boxes, and the name goes into the same backup set as the record
  and the pixels - so one Undo takes back the whole creation rather than leaving
  a text key pointing at a province that is gone. Leave them blank and it warns
  in the words the validator will use, because a province deliberately called by
  its code name is legal.

* **Add a character's name to their faction's pool, from the warning that says
  it is in no pool.** It turned out to be two files rather than one: 3,583 of
  Divide and Conquer's 3,583 pool names have a key in `text/names.txt`, and a
  pool entry without one shows the raw token in game. Both are written together,
  in one save with one Undo, and there is a second warning now for the case
  nothing here could see before - the name is in the pool and has no text key.

* Every one of these writes rebuilds the compiled `.strings.bin` beside the text
  file, because that is the file the game reads.

## The campaign map, unchanged from beta 2026-09-06b

Ten TGA layers, `descr_regions.txt` and `descr_strat.txt` on one screen: paint a
province and every file that names it follows, drag a general onto a tile, place
a settlement, and check the whole map against what the engine will accept before
the game ever sees it. See `RELEASE_BETA_2026_09_06.md` for the full account of
what it reads and what it writes.

## Known limits of this beta

* Renaming a region, a settlement or a faction is still refused, with the reason:
  the name is a key that `descr_strat.txt`, the win conditions, the campaign
  script and every `legion:` line point at. The rename engine is the next thing
  being built.
* Forts, watchtowers and resources are **read and drawn, not placed**.
* The terrain render is flat colour, not textured.
* Deleting a region and creating a campaign from scratch are not in this build.
* Nine lines of Divide and Conquer's `descr_strat.txt` do not parse, and all
  nine are the mod's own defects. They are read as far as they can be, kept, and
  reported by line number rather than silently dropped.
