# beta 2026-09-21

**Everything in v2.3.6 with the campaign map switched on**, plus one fix on the
map's own side.

This is still a **beta** for the reason the first one was: the campaign map
editor is the first thing this toolkit does that WRITES to a campaign, and a
campaign is the one part of a mod where a bad write shows up ten turns in rather
than the moment you load it. Everything it writes is backed up and one Undo
away. Read the plan before you press Apply.

## Fixed on the map

* **The flat map pans and zooms again.** The 3D surface's canvas was hidden
  when the mode was off, but a style rule kept it in the layout. It sat over the
  flat map, invisible, and took every drag and every turn of the wheel. It is
  properly out of the way now whenever 3D is off.

## Also in this build

Everything in **v2.3.6**: recruit pools and capabilities that keep the order
you give them, `＋` to add a line under any row, a code view that scrolls on
click rather than on hover, the regions that pass every gate of a `requires`
clause, and trade resources found where the map places them. See
`RELEASE_2_3_6.md`.
