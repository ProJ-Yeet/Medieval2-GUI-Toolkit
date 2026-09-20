# beta 2026-09-20

**Everything in v2.3.5 with the campaign map switched on**, plus the map's own
side of this build, which is the largest it has had: **the map in 3D**, and a
**campaign map editor pass from a second contributor** - the first work on this
toolkit by somebody other than its author.

This is still a **beta** for the reason the first one was: the campaign map
editor is the first thing this toolkit does that WRITES to a campaign, and a
campaign is the one part of a mod where a bad write shows up ten turns in rather
than the moment you load it. Everything it writes is backed up and one Undo
away. Read the plan before you press Apply.

## The map in 3D

* **⛰ 3D on the map toolbar, or the `D` key.** The heights as a surface, with
  this map's own ground drawn on it, turned with the mouse: drag to orbit,
  right-drag to pan, wheel to zoom.

  **It is a mode, not a second map.** It has no layer controls, no opacity
  sliders, no season switch and no texture loader of its own, because the
  surface is painted with the map you already have on screen: the ground under
  the stack, every layer you have ticked at the opacity you set it to, and any
  colouring over the top. Tick a layer off, drag an opacity, flip to winter or
  colour the map by faction, and the 3D changes with it. There is nothing to
  keep in step because there is only one picture.

* **One vertex per tile, and no guessing about the sea.** The whole map is in
  the mesh at the resolution the engine reads it - 248,370 tiles on Divide and
  Conquer - with nothing thinned out, so a one-tile island is a one-tile island.
  A tile is sea by the rule the rest of this toolkit uses, read off
  `map_heights.tga` rather than guessed from the ground types, which is what
  keeps the coastline where the coastline is.

* **Height and water.** One slider for how tall the highest land stands, and
  the water surface on or off. Both are remembered, and a saved view carries
  them. The mode itself is not remembered between sessions - it opens a 3D
  context, and the next mod you open should not.

* Settlement markers, names and the tile tooltip stay on the flat map. `D`
  again, or the button, puts you back.

## The campaign map workspace, from a second contributor

Demircan's first commit, and it is all on the campaign map. The highlights:

* **The workspace bar moved to the bottom**, the toolbar is more compact, and
  painting controls expand only when painting is on. Editing status, undo and
  redo, and Review & save stay reachable while you switch inspector tabs.
* **A searchable region browser** with alphabetical results and keyboard
  access, opening on the Regions shortcut even before you type.
* **Right-clicking a province** now picks it as the paint target as well as the
  one being inspected, without turning painting on if it was off.
* **A + Create panel**: regions, settlements, ports, characters and armies,
  forts, watchtowers and resources, all placed by clicking the map, with Escape
  to cancel.
* **Character editing on the map.** The character's own form, traits,
  ancillaries, army composition and unit upgrades, reached from the marker, with
  hover cards showing name, type, faction, age, rank, army size and the units
  in it.
* **Bigger, clearer map icons** with character-type symbols, faction colours, a
  legend, and distinct port anchors. A tile holding several editable things
  offers a chooser.
* **Saving a character no longer reloads the whole map** or throws away your
  zoom and pan.

## Also in this build

Everything in **v2.3.5**: the EDB tree validator on the Buildings screen with
its nine rules and the three it refuses, the launcher name the zip was getting
wrong, a blocked port that now moves instead of stopping, and strings archives
that would not open. See `RELEASE_2_3_5.md`.
