# v2.4.11

**Armory Studio's export you can steer, the base game read out of its packs,
and errors in plain words.** Everything since v2.4.10: the UV step of the
Armory export rebuilt, Blender and IWTE models read the right way round, the
checks and tools taken from Mylae's and Pfad's editors, WalhallaZ's bulk
tools, and the fixes from ports out of Crusades and Kirsi's Bigger Map.

## New

* **Armory export, the UV step (beta):**
  * **Bigger sheets**, two side by side once *Hide objects* folds the list
    away, and **Textures** draws each sheet with the art the bake will write.
  * **Live** packs after every change; off, *Refresh* waits for you.
  * **Pick an island** on a sheet: its object lights up, and the texture it
    came from shows beside the sheets with the island outlined.
  * **Scale one island alone**, from 5% to 1000%, with the slider, a typed
    number, a corner handle, or **S** then a factor (0.5 halves it) and
    Enter, as in Blender. Esc cancels.
  * **Undo and Redo** (Ctrl+Z, Ctrl+Y) for every change on the step.
  * An island that did not fit is marked red in the list and on its sheet.
* **Armory export, Bake and Install (beta):**
  * **A progress bar** while the bake runs.
  * **Show the baked images** before anything is written, and a normal-map
    mode **From the source models** that packs each part's own normal map.
  * **An export already on disk is found**, so you can go straight to
    Install without baking again.
  * **Browse** for the install folder inside the mod's data, or pick one of
    the unit's own model folders or a recent one.
* **Armory Studio (beta):** a folder's models listed as rows or tiles, a
  mod's skeleton and its actions with nothing loaded, the library inside the
  import dialog, a *Simple* or *Blender* navigation, a *Save* button, and an
  import that tries four times before it gives up.
* **The card maker (beta)** takes framing, grounds, the game's own frame, a
  painted look and the mod's own card sizes.
* **Errors in plain words.** *Health > Game log* says whether the game
  crashed and why, with a button to the unit, building or file to fix. The
  messages at the bottom stay long enough to read, and a screen that fails
  shows *Draw again* and *Report it*.
* **Delete a unit and everything naming it**: its recruit, garrison,
  starting-army, mercenary and rebel lines go with it, in one Undo.
  **Delete selected units** does the same for many.
* **Find unused units** and **Find unrecruitable units** in the Unit Editor.
* **Bulk region edit** on the campaign map (Shift+click provinces), **Fill
  rebel settlements**, map generation inside a rectangle, and the brush
  overwriting markers.
* **New checks:** a family tree that loops or has a father too young, every
  EDB `requires` against the mod's factions, resources and religions, every
  settlement at once, and recruit pools naming a unit the mod no longer has.
* **Attributes explained** beside each box, with M2EX and REX words in their
  own fold.
* **Recruitment:** a tier ticked takes every tier above it, as the game does.
* **Every folder picker** is the Explorer window the file pickers are, and
  opens where you were.
* "Probe" is "Preview" everywhere, and the Unit Editor's tabs say what is in
  them.

## Fixed

* **A Blender or IWTE `.glb` came apart in Armory** as soon as an action
  played: left and right were swapped. It now reads the right way round, and
  the skeleton overlay stands in the model instead of a hip-height above it.
* **Normal maps lost their colour** wherever their alpha was zero, when a
  bake scaled or resized them. Each channel is now filtered on its own.
* **The base game showed 0 of 413 unit cards**, and no mounts, projectiles or
  siege engines, because it keeps its data in packs. They are read out of
  the packs now, for the Kingdoms campaigns too.
* **"Invalid ownership type"** on a mod with no `descr_sm_factions.txt`: the
  base game's factions count, as they do in the game.
* A unit ported out of Crusades came without its sprite sheets, packed
  effects or engine files.
* Deleting a unit left the base game's comma-less mercenary lines behind, and
  a rename turned each line ending into a double one.
* Undoing a banner, building or map paint no longer parses the whole mod.
* Armory Studio's button did nothing when a script arrived late, and a model
  could load with one part bare after a refused connection.
* Sorting the EDU on a faction name with accents, an edited projectile or
  mount on transfer, and an empty era line.
* German, Spanish and French cover every new string.
