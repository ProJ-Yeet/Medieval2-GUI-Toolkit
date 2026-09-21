# v2.3.6

**The Buildings screen, from somebody using it on a big mod.** Feedback from
an editor working through AGO's EDB named four things, and all four are in: the
order of a level's units can be changed, a new line can go where it belongs
instead of at the bottom, the code view stops chasing the mouse, and a
`requires` clause says which regions can satisfy it. Building the last one found
that every `requires resource` in every mod had been reported as unplaced.

## New

* **Recruit pools and capabilities keep the order you give them.** Every row
  has a grip to drag it by and ▲ ▼ to move it one step, and the file is written
  in the order the list shows - which is the order the game's recruitment panel
  lists units in. Until now there was no way to move a line at all, and a unit
  added to a level could only ever go to the bottom of it.

  The file is still touched only where it has to be. A save that moves nothing
  writes exactly what it wrote before, line for line. A moved line is copied as
  the file has it, trailing comment and all, and **the comment lines above it
  go with it**: a `;; Gondor` header over a run of pools stays over those
  pools, rather than ending up labelling somebody else's. A row only moves
  inside its own block, so nothing slides between `capability` and
  `faction_capability` by accident.

* **`＋` on any row puts the new line directly under it.** On a recruit pool it
  opens the unit picker, and the units you tick land under that row in the
  order you ticked them. On any other capability it adds one under it. For a
  level with eighty lines, that is the difference between adding a unit where
  it belongs and dragging it the length of the list.

* **Every gate at once.** Beside each `requires` clause, **📍 N regions pass**
  lists the regions that carry every hidden and trade resource the clause asks
  for, each with the faction that starts holding it and a ★ on the ones a
  faction in the clause starts with. The clause dialog shows the same list as
  you edit, of how many regions in all. Each resource term already said where
  that one resource is; nothing said where *all* of them are, so a pool gated
  on two hidden resources meant working out the overlap by hand.

  **`∅ no region passes every gate` is the one to look for.** It means no
  region anywhere carries the whole set, so nobody can ever recruit from that
  pool, and the game will never say so. Divide and Conquer has three: two Snow
  Troll pools that ask for `Rhudaur` and `ResD`, and one that asks for
  `Cardolan` and `ResF`.

  Terms are read left to right the way the engine reads them, with no
  brackets. Only resources are a fact about a region that the files settle;
  who owns it, an event, the religion it has drifted to and what is built there
  are decided during play, so they do not narrow the list, and they are named
  under it as what the answer assumes.

## Changed

* **The code view scrolls when you click, not when you hover.** Moving the
  mouse down the form used to drag the file along underneath it, and passing
  over the gap between two rows threw the text back to the top of the record.
  A hover now only lights the line; a click on a box scrolls the text to it.
  **⇕ Follow hover** on the code view's bar puts the old behaviour back, and the
  choice is remembered. It is one setting for every editor that has a code
  view.

* **Units added from the picker go where they are written.** They used to be
  shown at the top of the list and saved at the bottom, which is how the list
  and the file came to disagree in the first place. They are added at the end
  now, the list scrolls to them, and the first one flashes.

## Fixed

* **Trade resources were never found in any region.** A trade resource is
  placed on the map by `descr_strat.txt` - `resource sulfur, 344, 333` - and
  belongs to the province that tile is in, but the toolkit only read
  `descr_regions.txt`, which carries hidden resources. So the "📍 N
  settlements" marker on a `requires resource` term has said **∅ nowhere** for
  every trade resource in every mod since it was added. It now reads the
  placements: ROCSS places sulfur in nine regions, and Divide and Conquer
  places chocolate in two.

* **The code view shows units the moment the picker adds them.** It used to
  go on showing the level without them until the next keystroke.

## Notes

Across the two installed mods, 674 `requires` clauses on a recruit pool or a
capability have a resource gate. Every one of them that is made only of `and`
was checked against a plain intersection of the regions, and they agree.
