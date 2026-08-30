# v2.1.6

Fixes the M2EX mark, which did not survive being read back. Adds the projectile
effect import that mark now unlocks, and stops a unit added to a building
disappearing off the bottom of the list.

## Fixed

* **The M2EX mark did not stick.** Ticking "Runs on M2EX" on a mod's Home card
  looked right and then came undone: switching away from Home and back, or
  anything else that re-read the mod list, showed the box clear again.

  The mark is stored per mod folder. Reading it back accepted either a mod or a
  bare path, and the bare-path case took `Path.root` — which is the path's
  *anchor* (`\` on Windows), not the mod's folder. So every read that started
  from a path keyed to the drive root of the working directory instead: one
  shared row for every mod on the machine. `/api/mods`, which answers the header
  dropdown before anything has been parsed, is exactly such a read, so that is
  the one that came back wrong.

  Ticking the box still looked correct because that response is answered from a
  parsed mod, which has a real folder. The next fetch of the mod list is where it
  went.

* **`effect_set < 3 4 > name` is now read correctly.** An effect set can be
  declared once per graphics-detail band, and the name follows the brackets. The
  scanner took the token straight after the keyword, so it recorded seven sets
  per stock mod as being named `<` and left out the sets they actually name. A
  transferred projectile pointing at one of those had its effect line replaced by
  a placeholder even when the destination did define it.

* Effect files whose braces do not balance are now read to the end. Divide and
  Conquer leaves an `effect` block open, and a reader that trusted the brace
  depth swallowed the next two sets with it.

## Added

* **Projectile effects are imported for an M2EX destination.** Transferring a
  missile unit into a mod marked as M2EX now carries the projectile's effect sets
  across instead of replacing them with `invisible_placeholder_set`: the
  `effect_set` block, every `effect` it lists, and the `.CAS` models and textures
  those name. Each block is written back into the file of the same name it came
  from, appended below whatever that file already said.

  Effects are still not imported for anything else, and that is deliberate. They
  live in files shared by every projectile in the mod, and how many the engine
  will load is one of its hardcoded tables — what sits past the end is dropped
  with no message. M2EX replaces that table, which is what makes this safe there
  and not elsewhere.

  A set the source mod does not define itself is still left as a placeholder. It
  comes from vanilla, the source was relying on the engine's own copy, and that
  copy is not the toolkit's to move.

  The probe says which sets travelled and which were left, and the transfer is
  undoable like any other — including removing an effect file the import had to
  create.

## Changed

* **A unit added to a building's recruitment appears at the top of the list.** It
  used to go on the end, which on a level training thirty units meant scrolling
  to find the row you had just added. Several units added at once keep the order
  they were ticked in.

  This is display order only. The file is written exactly as before: new lines
  are appended above the block's closing brace, and existing lines are edited in
  place by the line they came from.

* The README links the video walkthrough, and credits FeatherLeaf as sponsor.
