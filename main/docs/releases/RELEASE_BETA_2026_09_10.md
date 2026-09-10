# beta 2026-09-10

Three layers on the campaign map that you could draw and could not read: the
rivers, the heights, and the ten layers themselves. Everything on the earlier
betas is here, and so is everything in v2.2.3.

This is still a **beta** for the reason the first one was: the campaign map
editor is the first thing this toolkit does that WRITES to a campaign, and a
campaign is the one part of a mod where a bad write shows up ten turns in rather
than the moment you load it. Everything it writes is backed up and one Undo
away. Read the plan before you press Apply.

Nothing in this build writes anything. All three of its changes are ways of
looking at a layer.

## New since beta 2026-09-09b

### Rivers only, in a colour you pick

`map_features.tga` holds the river network, and on Divide and Conquer **97.7% of
that layer is black**, which means *nothing here*. Ticking it drops a black
sheet over the map with a few rivers in it. There is now a **Rivers only** box
on the Features row: it draws the river network and nothing else, in one colour
of your own choosing, over whatever you have underneath. The row tells you how
many tiles it drew - **5,466** on Divide and Conquer.

The three colours a river is made of in the file - a river, a crossing and a
source - become that one colour, which is the point: two of the three are almost
invisible against the ground types, and a river source is the same white as a
port marker. The tooltip still names each tile exactly, because it reads the
layer rather than the picture.

It is the same three colours the map checker walks when it complains about a
river that loops, ends nowhere, or joins only at a corner, so the overlay is a
picture of what it is talking about.

### The heights drawn as transparency

A **Height as transparency** box on the Heights row: high ground stays solid,
low ground lets what is under it show through, and the sea is not drawn at all.
Turn it on over the ground types and you get relief.

**The obvious version of this does not work, and that is worth saying because it
is what the reference tool does.** "Darker is more transparent" taken literally
means a tile's transparency is its grey value, and on a real map that draws
about half the continent at under 13% opacity: the median land tile on Divide
and Conquer is **32 of 255**, and on Third Age Reforged 31. So the scale here is
spread over the heights your map actually has - a tile is as solid as the share
of the land that is no higher than it. Darker is still more transparent, nothing
swaps places, and the middle of your map is now in the middle of the scale.

If something opaque is still drawn over the heights, the row says which layer
and offers a **Put it on top** button. It will not rearrange your layer order by
itself.

### A number key for every layer

Ten layers, ten number keys, **1 to 0**, and the key is printed on the layer's
own row so there is nothing to memorise. `1` is the regions, `2` the heights,
`3` the ground types, and so on down the list the map is made of.

The point is what it does not disturb. Press a key with the pointer resting on a
tile and the layer goes on or off underneath it - the tile, the readout and the
panel naming that tile on all ten layers stay exactly where they were. Comparing
two layers over one province is now two keypresses rather than two trips to the
side panel and back.

**Fit and 1:1 moved to Shift+0 and Shift+1** to make room. The buttons in the
toolbar say so, and everything else on the keyboard is where it was.

## Also

* All three are remembered between sessions, beside the rest of your layer
  settings: which layers are on, how transparent each one is, the order they
  draw in, and now the river colour and the two switches.
* None of it costs a frame. A pan is 0.0093 to 0.0159 ms with all three on, and
  the panel's own ms-per-frame readout is still there to check it with.
