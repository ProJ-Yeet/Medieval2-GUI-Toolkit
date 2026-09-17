# beta 2026-09-17

**Everything in v2.3.4 with the campaign map switched on.** The map's side of
this build is one feature, asked for as the next big one: **mercenaries** -
which province sells which unit, who may hire it and, above all, why not - and a
map that opens the way it is actually read.

This is still a **beta** for the reason the first one was: the campaign map
editor is the first thing this toolkit does that WRITES to a campaign, and a
campaign is the one part of a mod where a bad write shows up ten turns in rather
than the moment you load it. Everything it writes is backed up and one Undo
away. Read the plan before you press Apply.

## Mercenaries

* **Province → Mercenaries.** Click a province and see every mercenary its pool
  sells, each with its card, its price, its pool size, how fast the pool refills
  and a verdict: **can hire**, **not yet**, **never**, or **depends on a
  script** - with the reason under it in plain words.

  Pick a faction at the top and the verdicts are for that faction. A unit line
  in `descr_mercenaries.txt` has up to five gates and none of them names a
  province: the unit has to exist in your EDU, the faction's religion has to be
  in `religions { }`, the faction has to be in `factions { }`, and then
  `crusading`, `events { }` and the two years hold it back until they are met.
  `factions { }` is not in the file's own header at all, and Third Age
  Reforged's Fellowship campaign uses it on 41 of its 51 lines.

* **An event is traced to what sets it.** `events { ND_BOH }` on a Divide and
  Conquer line is in no `descr_events.txt`; it is `set_event_counter ND_BOH 1` on
  line 10,765 of the campaign script, and the panel says exactly that. An event
  nothing in the campaign sets is **depends on a script** rather than **never**,
  because a script elsewhere may.

* **The other way round: pick a mercenary, see everywhere it is sold.** Every
  pool that offers it, at the price it costs there - mods really do price the same
  unit differently in two pools - and every province as a button that goes to
  it. **Picking one lights those provinces on the map straight away**; a toggle
  beside the ◉ button turns that off.

* **Edit a pool entry where you read it.** Cost, pool size, starting size,
  replenish, experience, the religion, faction and event lists, crusading and the
  two years - or remove the line, or sell another unit in the pool with your
  EDU's unit names offered as you type. Only the value you changed is rewritten:
  the tab columns, the commas after the names and the comments in the file stay
  exactly as they were.

* **Three more ways to colour the map**, on the Query tab with the rest:
  how many mercenaries a province sells, whether it sells any, and every
  province one unit is sold in. The legend, the tint and the TGA export come
  with them.

* **Six new rules on the Validate tab**, every one a warning rather than a
  refusal - it is somebody else's mod and it loads today. Measured on the
  installed mods:
  - a mercenary naming no unit in the EDU: **49 lines on Fellowship**, whose 28
    `… Mercs` names exist nowhere in the mod
  - a province in two pools, which the file's own header forbids:
    `Mt-Gram_Province` on Fellowship - fixed from the Mercenaries panel, with a
    **Keep in** button for each pool, because which one is your call
  - a pool naming no province, and a religion or faction nothing declares
  - an event nothing in the campaign sets: 4 lines on Divide and Conquer
  - a unit whose years fall outside the campaign: **Reforged's imperial
    campaign sells Anduin Bodyguard and Angmar Rhudaur Axemen from 2986, and the
    campaign ends in 2984**, so nobody ever hires either

## The map opens the way it is used

* **Settlement names and the terrain are on when the map opens.** The first
  thing anybody did on opening a map was switch both on, every session, on every
  mod. They open on now, in summer, with a gap in the textures drawn neutral
  rather than pink. Turning either off still sticks: this is what a mod with
  nothing saved gets, not a switch that flips back every time. A saved view
  opens exactly as it was saved.

* **The layer list is a button at the foot of the map.** It was pinned under
  the side column taking 45% of its height, and it vanished when the column was
  collapsed. `▤ Layers 2/10` opens it over the map - the count, so a closed list
  is not a hidden one - `s` opens it too, and the number keys still tick a
  layer with it shut.

## What has not changed

Every edit to `descr_mercenaries.txt` goes through one reader and one writer
now, including the pool picker on the Region tab and the province delete, and
both read every campaign file on the installed mods exactly as before. No other
campaign file is written differently.
