# v2.3.9

**Walls, agents, and whole things brought across.** Everything since v2.3.8:
screens for `descr_walls.txt` and `descr_character.txt`; a building tree, a
settlement model and any `data/` zip brought in from somewhere else; campaign
models drawn standing up rather than piled on the ground; and animations played
out of a pack that was unpacked in place.

## New

* **Walls, gates and towers.** A tab edits `descr_walls.txt`, which is per wall
  level (0 to 4), not per culture: the wall, the gateway and its gate types, the
  tower's firing levels and the gatehouse. It is held against the buildings
  file: every `wall_level` has a block, and every building's `tower_level` has
  enough firing levels on its wall. It found ROCSS's three empty `shot_gfx`
  lines.

* **Agents and generals.** A tab edits `descr_character.txt`: each agent type's
  actions, wage and action points, and each faction's strat models, battle
  model and kit, with a grid of which faction has which type. A strat model's
  card in the Models Editor lists every character block it stands in for, as
  links, and each model on the tab links back to its card. It found DaC's two
  `england` inquisitor blocks.

* **A building tree from another mod.** *From another mod…* on the Buildings
  screen brings one or more building lines of another installed mod across
  whole: the block, its text (per faction and per culture, carried to the new
  name) and its building cards. Every faction and culture this mod lacks is
  mapped or left out, a recruit this mod lacks is left out and listed, a hidden
  resource it lacks is added, and a level that needs a line, resource or
  religion it lacks is refused with a one-click *add that line*. A same-named
  line can be replaced in place. One backup, one Undo.

* **A settlement model imported and put on a culture's level.** *Import…*
  beside each level's model on the Cultures screen (and the fort, fort wall,
  fishing village and watchtower lines) copies a settlement `.cas` from another
  mod or from disk, with the textures it names, into a folder where nothing is
  written over, and puts it on that line, keeping its settlement plan.

* **Any `data/` zip loaded back.** *My changes* takes any zip laid out under
  `data/` (the changed files, a faction's files, a whole campaign) and plans
  each file: new, the same, replacing (with the records named) or refused. Stale
  compiled maps are deleted, and one Undo takes it all back.

## Fixed

* **Campaign models drawn in their pose.** A skinned strat model is now placed
  by its skeleton, each piece where its bone puts it, instead of piled on the
  ground. All 296 characters in both mods stand. 53 ROCSS models with a baked
  animation, its diplomat among them, decode at all.

* **Strat textures in the game's order.** A material named `x.tga` is looked for
  as `x.tga.dds`, then `x.tga`, and never as `x.dds`. DaC's Amroth general
  paints, and 864 materials that have both a real `.tga` and a `.tga.dds` now
  show the `.tga.dds`, as the game does.

* **Animations from an unpacked pack play.** A `pack.dat` unpacked in place keeps
  each file under the path it was packed from, and the viewer found none of
  them. It now looks where the game reads, then under the nested path, and reads
  those entries with the unpacked skeleton's bones: 40,460 of DaC's 41,501. An
  edit saves as a loose `.cas` beside the entry, never over it.

## Also

* A mod's layers save faster where numpy is installed. The release runs as
  before without it.
