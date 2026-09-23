# beta 2026-09-23

**Everything in v2.3.8 with the campaign map switched on**, plus settlements
deleted, created and copied, and a fix for typing in the map's side panels.

This is still a **beta** for the reason the first one was: the campaign map
editor is the first thing this toolkit does that WRITES to a campaign, and a
campaign is the one part of a mod where a bad write shows up ten turns in rather
than the moment you load it. Everything it writes is backed up and one Undo
away. Read the plan before you press Apply.

## On the map

* **Delete a settlement, create one, copy one across mods.** The settlement
  panel deletes a settlement (the province stays, as vanilla's Durazzo does; a
  capital that moves and a faction left with nothing are both said), creates a
  village in a province nobody holds, and copies a settlement into the same
  province of another mod's campaign, leaving out and naming the buildings
  that mod lacks.
* **The people panel knows the hero abilities.** The Hero ability field offers
  what `descr_hero_abilities.xml` declares, not only what the campaign already
  writes, warns on a name the file lacks, and links to the ability's screen.
  Every ability a character names in either installed mod is declared.

## Fixed

* **Typing in a side-panel box dropped out after one character.** Every
  campaign-map panel (region, settlement, people, campaign, events, forts,
  find, pins, query, views, climates, rebels, mercenaries) rebuilt itself on
  each keystroke and threw the box you were typing in away. They keep it now.

## Also in this build

Everything in **v2.3.8**: animations played, edited and exported; several
factions at once and the faction zip; the Launch row on Home; settlement
mechanics; religions across every region; one file in or out; populace and
off-map models; animals, standards and advice; battle banners; hero abilities;
area effects; addresses and a trail for every screen; and the fixes to
projectile effects on transfer, textures imported during a folder move, and
Health. See `RELEASE_2_3_8.md`.
