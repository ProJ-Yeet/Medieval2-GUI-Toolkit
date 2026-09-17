# v2.3.4

Everything since v2.3.3 that is not the campaign map editor. **The campaign's
own settings are a tab of Minor Files**, **the unit editor says when a value is
past what the engine accepts**, and one bug on the Guilds screen goes with them.

## New

* **Campaign constants: `descr_campaign_db.xml`, as a form.** Minor Files →
  Campaign constants. Every number the game reads once for the whole campaign -
  recruitment slots, piety, bribery, ransom, autoresolve, settlements, forts,
  agents, the AI - one section at a time, or all of them at once through the
  search box.

  The file says what kind each value is, so the form does too: a tick box for a
  true/false, a checked box for a number, and a value of the wrong kind is
  marked red before you save and refused if you try. The comment a mod wrote
  beside a value is shown beside its box. Saving changes only the characters
  between the two quotes, so the comments, the spacing and the line endings of
  the file come back exactly as they were - and a save that would leave the XML
  unreadable is refused outright.

* **What the tutorials say a setting does, where they say it.** Fourteen values
  carry a line from the TWCenter archive with the tutorial named: the three fort
  switches (`destroy_empty_forts false` is what keeps a fort standing once its
  army leaves), the Kingdoms alternative piety mode and its three tuning values,
  and the AI's ransom and release chances. Nothing is guessed: a value no
  document explains has no text under it.

  **A documented setting your mod does not have can be added** where a tutorial
  prints its line whole. Third Age Reforged has none of the four alternative
  piety values; the tab offers them, with the values the tutorial gives.

* **The unit editor now says when a value is past the engine's ceiling.** The
  EDU fields tab carries a note for anything the game will not take as written,
  and the save preview warns when **your edit** crosses one - not every time you
  save a unit that was already past it. Nothing is refused; a mod over a ceiling
  is often over it on purpose.

  Every number comes from a Medieval II document in the archive, named on the
  note: 4 to 100 men, attack capped at 63, hit points 0 to 15 (both values),
  three officers, three mount effects, two formations - one square or horde and
  one shield wall, phalanx, schiltrom or wedge - and 500 units in the file,
  which a mod marked for M2EX is not held to.

  The list this was planned from turned out to be **Rome: Total War's**. Taken
  as written it said 60 men per unit, and it flagged 300 of Divide and
  Conquer's units and 113 of Third Age Reforged's, on two mods that play. Its
  numbers for charge, armour, defence, shield, turns to build and units per
  faction have no Medieval II source, so they are not checked. With Medieval
  II's own numbers it is 29 of Divide and Conquer's 924 units and 6 of Third
  Age Reforged's 427 - the Mumakil at 30 hit points, the Stone Giants at attack
  100.

## Fixed

* **Switching mod on the Guilds screen could leave the last mod's guilds on
  it.** Every other screen's data was dropped on a mod switch and the guilds
  were not, so the list could still be the previous mod's under the new mod's
  name. They are dropped with the rest now.

## Where the rest of it went

This build is the same tree as **beta 2026-09-17** with the campaign map editor
switched off. Most of what landed since v2.3.3 is that editor: the whole of
`descr_mercenaries.txt` - which province sells which mercenary, who may hire it
and why not, every province a unit is sold in lit on the map, six new rules -
and a map that opens with the settlement names and the terrain already on. The
beta's notes cover all of it.
