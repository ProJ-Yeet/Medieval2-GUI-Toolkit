# beta 2026-09-09b

Renaming a province, its settlement, or a faction. It is **everything in v2.2.3
with the campaign map switched on**, so the faction half of it is in this build
too, and so is everything on the earlier betas.

This is still a **beta** for the reason the first one was: the campaign map
editor is the first thing this toolkit does that WRITES to a campaign, and a
campaign is the one part of a mod where a bad write shows up ten turns in rather
than the moment you load it. Everything it writes is backed up and one Undo
away. Read the plan before you press Apply.

## New since beta 2026-09-09

### Rename a province, or its settlement

The region panel's Region name and Settlement boxes stay read-only and each has
a **Rename** button beside it. The name is a key, and renaming it in
`descr_regions.txt` alone is worse than not renaming it: the province is also
named in every campaign's `descr_strat.txt`, the win conditions, the mercenary
pools, the campaign music types, the custom battle tiles, the region-and-
settlement lookup, the file the player reads the name out of, and every
`legion:` line pointing at it. All of those are followed in one save.

**It never guesses from the word alone**, and that is measured rather than
careful. Divide and Conquer's province `Eregion_Province` has the settlement
`Eregion`, and `Eregion` is *also a hidden resource* on twenty other provinces'
flags line in the same file. `Dunland` is a settlement, a sound folder, the
first word of eleven unit types, a custom battle location and a climate comment.
Settlement names turn up in **sixty files** across the two installed mods and
most of those are coincidences. So every file is asked which of its *lines* can
hold a name of this kind, and nothing else in it is touched. Everywhere else the
word appears is counted and shown to you.

**`descr_strat.txt` does not name a settlement, and this toolkit used to say it
did.** The refusal on the settlement box has claimed since the map editor was
written that the campaign start position points at a settlement's name. It does
not: a settlement block carries `region <province>` and never its own name, and
every whole-word hit in either installed mod's `descr_strat.txt` is a unit type,
a portrait, a character label or a comment. A settlement lives in exactly three
files. The wording is corrected everywhere it appeared.

### The campaign script is reported, never edited

A campaign script is a scripting grammar this toolkit does not parse, and a
wrong edit to one is a campaign that fails to start. Every occurrence of the old
name comes back with its file and its line number, listed in the dialog before
there is a button to press, and none of them is rewritten. Silently leaving the
script pointing at a name that no longer exists would be worse than not renaming
at all.

### Renaming a faction

See the v2.2.3 notes; it is the same engine and it is in both builds. Twenty-four
files on Divide and Conquer, the length-prefixed texture records in
`battle_models.modeldb`, and the art the engine finds from the slot itself, which
moves with it.

## Also

* **A rename renumbers nothing.** Region IDs are first-appearance order in a scan
  of `map_regions.tga`; a rename moves no record and repaints no pixel, so every
  `IsRegionOneOf` operand still means what it did.
* **A second campaign is not skipped.** Divide and Conquer keeps Shattered
  Alliances under `custom/` and Third Age Reforged keeps the Fellowship campaign
  there, and both are whole campaigns with their own start position, win
  conditions, mercenaries and script. Reforged's also ships its own
  `descr_regions.txt`. All of them are followed.
* **A province cannot be renamed to a settlement's name.** The two are keyed in
  one file, so a second `Anorien` would quietly take over the first one's line on
  the campaign map, which is a rename that looks like it worked. Refused before
  anything is written.
