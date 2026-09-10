# beta 2026-09-11

Three ways of getting to the thing you want on the campaign map: a box you type
a province into, a name you save the whole look of the map under, and a list of
the campaigns your mod actually has. Everything on the earlier betas is here,
and so is everything in v2.2.3.

This is still a **beta** for the reason the first one was: the campaign map
editor is the first thing this toolkit does that WRITES to a campaign, and a
campaign is the one part of a mod where a bad write shows up ten turns in rather
than the moment you load it. Everything it writes is backed up and one Undo
away. Read the plan before you press Apply.

Nothing new in this build writes anything either. What it changes is what you
can reach.

## New since beta 2026-09-10

### Your mod probably has a campaign this tool could not open

There is a **Campaign** panel now, listing every campaign in the mod with what
is in each one, and an Open button on each. That sounds like a convenience. It
was a hole:

* **Divide and Conquer** ships `imperial_campaign` and, in a subfolder,
  **Shattered Alliances** - 30 factions, 199 settlements, 25 of them playable.
* **Third Age Reforged** ships `imperial_campaign` and, in a subfolder, **The
  Fellowship Campaign** - 16 factions, 129 settlements, and ten map layers of
  its own.
* **The stock game** ships the Grand Campaign and the **Norman prologue**.

Every one of those subfolder campaigns was invisible to this screen, so all the
work it does on a campaign - the settlements, the characters and their armies,
the family trees, the diplomacy matrix, the win conditions, the events, the
mercenary pools, the menu titles - was being done on the one campaign the
engine's own new-game menu lists and on no other. Pick one in the panel and the
whole screen re-reads it: every panel over the campaign follows, and your zoom
and your layer settings stay where they were.

What each row tells you before you open it: its title on the new-game menu, when
it runs and how long a turn is, how many factions are playable, unlockable and
not playable, and what stands in it - settlements, characters, forts,
watchtowers, resources. Plus three things you would otherwise find out much
later:

* **when the folder and the file disagree.** Divide and Conquer's second
  campaign lives in a folder called `Shattered_Alliances` and its first line
  says `campaign imperial_campaign`. Both names are real and different files in
  the mod point at each. The row shows both.
* **when a campaign has map layers of its own.** The Fellowship campaign ships
  all ten and the Norman prologue seven. This screen draws
  `world/maps/base`, always, so the row tells you those pixels are not the ones
  you are looking at.
* **when there is no file to have a title in.** The stock game keeps
  `campaign_descriptions.txt` inside its packed data, so the panel says the file
  is missing rather than implying nobody named the campaigns.

### Find

A **Find** box. Type a province, a settlement or a region ID and go to it -
`F` opens it with the cursor already in it, and Enter goes to the first hit.

It matches **the words the player reads as well as the code name in the files**,
which is the difference between finding Anórien and having to remember it is
`Anorien_Province`. Exact matches first, then names that start with what you
typed, then names that contain it, and each row says which of a province's four
names it matched - handy when a settlement and the province round it are called
the same thing.

Nothing is fetched while you type. Every name it searches came down with the map
when the screen opened.

### Views

A **Views** panel: save what the map looks like under a name, and click the name
to get it back. Which layers are drawn, in what order, at what opacity, which
colours are punched out of each, the rivers-only and heights-as-transparency
switches, and the colouring over the top. Update, rename and delete each.

They are yours rather than the mod's, so a view you set up for reading terrain
works on every mod you open. A saved view that names a layer a mod has not got
loads anyway and says so, and the layer order is reconciled rather than trusted
- nothing is dropped or invented.

## Also

* **Going to a province now selects it.** Jumping to a province from Find, from
  the Query panel or from the map checker used to centre on the tile and select
  nothing at all if you had the Regions layer switched off - which is a normal
  way to read a map. All three now open the province's record when they arrive,
  without switching a layer on behind your back.
* The campaign descriptions editor keyed a campaign by the path it was reached
  through rather than by its own folder name, which was invisible until a
  subfolder campaign could be opened at all. Fixed, and checked against Divide
  and Conquer's own file.
