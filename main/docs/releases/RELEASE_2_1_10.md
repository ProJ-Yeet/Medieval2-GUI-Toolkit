# v2.1.10

Puts the model beside a transfer, and the building's own art beside a recruit
pool.

## Added

* **The 3D viewer in the transfer composer.** The same docked column the unit
  editor and the BMDB browser carry, over the dialog that decides which models
  cross between mods. A transfer is a decision about models - which soldier
  entry goes, whether the officers come with it, which destination unit is the
  right one to replace - and every one of those was being taken off a name in a
  dropdown.

  It draws **both sides**: the source unit's battle-model entries, and, once a
  base or replaced unit is picked, that unit's own entries out of the
  destination mod, grouped by which mod they come from. "Is this the unit I
  meant to overwrite" is the question the replace mode exists to get wrong, and
  it is a question about two mods at once.

  It opens on the unit's own soldier model rather than its standard bearer, and
  a unit drawn from `armour_ug_models` does not offer the model on its `soldier`
  line, which the game never shows. Fold it away, drag it wider, take it full
  screen, or close it - the choice is remembered, the same way the unit editor's
  is, and the button at the top of the dialog brings it back.

* **Building art on the Recruitment tab.** Every recruit pool now carries the
  picture of the tier it sits on, and so does the ＋ picker - on each building
  line and on every tier button in it. A barracks and a stable are two clicks
  apart in a list of nineteen rows that all say "Barracks", and the art is what
  tells them apart at a glance.

  The art follows the **pool's own `requires`**: a pool gated to
  `factions { aztecs, }` wears the buildings those factions build, not whichever
  culture the Buildings module was last left on. Where a level is drawn for only
  one culture - which is normal for a mod-invented building - that culture's art
  is used rather than a placeholder, because this tab lists pools from every
  line in the mod and is not showing a culture at all. The Buildings module is
  unchanged: it *is* showing one culture on purpose, and a level that culture has
  no art for stays a placeholder there.

## Changed

* **A recruit pool's row is laid out as two halves.** The tier now sits directly
  against the building's name and art, because "a barracks" and "which barracks"
  are one answer and not two, and the `requires` clause has moved to the right of
  its own line, ending where the numbers and the row's buttons do. The clause
  keeps a line to itself - a real one names half a dozen factions and a
  settlement level - and still spreads back across the full width when it needs
  to.

* The Recruitment tab's column headings now sit over the boxes they name. They
  were a button's width to the right of them, because the header row carries no
  🗑 and nothing was reserving its column.
