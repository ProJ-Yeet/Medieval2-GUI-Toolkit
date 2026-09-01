# v2.1.9

Puts recruitment on the unit, and shows a model's UV islands over the art they
sit on.

## Added

* **Recruitment, from the unit.** A tab in the unit editor listing every
  building line in the mod that trains it. All four pool numbers and the
  `requires` clause are editable in place, so answering "where can this unit be
  hired, and on what terms" no longer means leaving the unit, finding one of the
  four or five buildings that train it, and reading its row off a list of sixty.

  A value that disagrees with what most of the other pools use is marked, which
  is usually why the tab gets opened: the same unit is typically trained from
  several buildings whose numbers drifted apart over years of edits.

  Clicking a building's name opens that line in a **new browser tab**, on the
  tier the pool sits on, with the unit's rows flashed — so going to look at the
  building does not close the unit you were editing.

* **＋ Add a building**, in that tab. Every line in the mod and every tier in it;
  the tiers that already train the unit are shown as such and cannot be picked
  twice. Making a unit recruitable somewhere new never leaves the unit — and
  neither does taking it off a building, which is the 🗑 on each row.

  These are the same `recruit_pool` lines the Buildings module writes, through
  the same planner, so a pool edited from the unit and one edited from the
  building cannot disagree. Everything staged here is written with the unit's
  own save: one entry in the log, and one undo takes the lot back, however many
  building lines it touched.

* **UV layout** in the 3D viewer, beside the model, the way a UV editor shows
  it: the texture sheet — both squares of it where the entry names a pair — with
  this model's islands drawn over the art they cover. One colour per part, the
  same colour beside that part in the list. Pan, zoom, and click an island to be
  told which part wears it, which pixels of which sheet it covers, and whether
  it runs off the sheet it was authored in.

  It draws only the parts actually on the soldier, so switching a variant or
  hiding a slot changes the map with it — three heads laid over one sheet is not
  a UV map. Where **Show UVs** answers "is this shell stretched", this answers
  "where on the art does this part live", which is the view a retexture is done
  against.

* **The docked viewer's canvas is resizable.** The bar under it drags the
  boundary between the model and its controls, and the height is remembered;
  double-click restores the default. The column's own width was already
  draggable.

## Fixed

* **Every mount in every mod was drawn with its texture tiled twice.** An entry
  that names no attachment texture at all — which is every ordinary mount — has
  one sheet spanning the whole space its UVs are written in, and the viewer was
  treating it as the case where a sheet is glued to itself. Measured rather than
  reasoned: mapping each triangle's texel-space edges onto its own plane says
  how far from square its texels are, and whole-model medians invert exactly
  where they should — real pairs read 1.2 at half-width and 2.0 at full, lone
  sheets the other way round. Barding stops being striped and becomes plates.

* **The unit editor's 3D preview no longer offers a model the unit is never seen
  in.** When a unit carries `armour_ug_models` the engine draws those, one per
  armour level, and never the model on its `soldier` line — Uruk-hai Bodyguards
  names one model there and puts another in both upgrade slots. The test is per
  model, so an entry that is the soldier line *and* an upgrade still appears, and
  a unit with no upgrade list is unaffected.

* `v3Draw` returns on a zero-size canvas instead of sizing to a made-up 640,
  which is what the UV layout taking the stage used to leave behind.

* `loadBuildings` no longer writes "Reading …'s buildings…" into the page
  behind an open dialog. The Recruitment tab asks for the building overview from
  behind one, and that message was what you found on screen the moment you closed
  the editor.
