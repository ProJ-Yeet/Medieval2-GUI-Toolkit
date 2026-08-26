# Medieval 2 GUI Toolkit v2.1.4

A small one, and all of it is about the tool getting out of your way.

Back now means back — through the toolkit's own screens rather than out of it.
The city/castle panel, which could only ever *say* that a building's two halves
disagreed, now lets you fix it where you found it. Two pictures that were too
small to compare are shown at the size you can compare them at. And a unit in the
3D viewer fills the frame instead of standing in the middle distance.

A subrelease: same standing as 14j, 2.1.2 and 2.1.3 — real features, not folded
into Phase 16 because Phase 16 (the Campaign Map Editor) is a different program.

---

## The short list

- **The browser's Back button steps back through the tool**, not out of it — and
  so do the mouse's back button and Alt+←.
- **The four numbers in “City and castle, side by side” are editable, on both
  sides**, with **Copy city → castle** under each half to put all four across at
  once.
- **Unit cards on disk / Info cards on disk** show each picture at the size the
  slot above shows it, and the slot above no longer repeats one of them.
- **The 3D viewer opens closer**: a unit's height fills the frame.
- **Preview is called Probe**, everywhere the word is on screen.
- **A modeldb that dies on an innocent line now names the character that did
  it** — the attachment sprite slot, which can only ever hold `0`.

---

## Everything in this release

### Back goes back through the tool

`web/js/core.js`, `NAV_LAYERS` / `uiBack`.

The whole toolkit is one page, so pressing Back left it — usually to the blank
tab the launcher opened it in, with a dialog full of unsaved edits gone with it.

There is no recorded history of screens being replayed, and deliberately so:
every layer already knows how to close itself, and its on-screen Back / Cancel /
✕ is the call that does it. A press asks the layers, innermost first, *are you
what is on top?*, and the first one that says yes goes back exactly as its own
button would — including whatever that button stops to ask first. A press and a
click can never become two different ways out of one screen.

The order, innermost out: the burger menu, the unit drawer, the model picker, the
image picker, the requirements dialog, a panel stacked inside a dialog (the
add-unit picker, the unit view, the city/castle comparison), the dialog itself,
the trip back to a building you hopped into the Unit Editor from, and then the
modules in the order you opened them.

One spare history entry sits ahead of the page and each press spends it; a press
that closed something puts it back. At Home with nothing open there is nothing
left to close, so the spare is left spent and a second press leaves the page the
way it always did — the tool does not trap you in itself.

`tests/test_back_button.py` pins the order, pins that a layer whose module never
loaded is simply *not open* rather than an exception that takes the Back button
down with it, and pins that the trail of modules runs out at Home.

### The city and castle numbers, editable where you find them

`web/js/buildings.js` + `unittransfer/buildings.py`.

The panel that puts a building's two halves side by side existed to find the
drift between them. Having found it, the fix was two more trips into two separate
building forms — one of them for a line that is not even the one you have open.

Now the four numbers on each side are boxes, and **Copy city → castle** (and the
same the other way) under each half puts all four across in one click.

Where the edit goes is decided by which side it was typed on, and both answers
already existed in this editor:

* **this half** is the line the form behind the panel has open, so its row is
  already in the working copy — found by the EDB line it came from;
* **the twin** is a building that is not on screen, so its row is staged in
  `work.also` against the line it already occupies. That is an in-place rewrite,
  not a second copy of the unit, and it appears under **Also changing** like
  every other edit made to a building from somewhere else.

For that the server had to start saying which line each side's pool sits on:
`variant_compare` now sends `cap_line` and `faction` per side (`_pool_side`).

A row that comes into step as you type is **not** pulled out from under the
caret; the mark beside it and the tier's tally repaint in place, and the row only
leaves a filtered list on the next full draw. A side that does not train the unit
at all has nothing to copy and nothing to overwrite — that is a gap, and ⇄ Mirror
is still what closes it.

`tests/test_variant_edits.py` pins the staging: a number typed on this half
rewrites the row already in the working copy rather than adding a second pool;
two typed on the twin land on **one** staged row; and a row the panel mirrored a
moment ago does not inherit the *other* building's line number. It then checks,
against every installed mod, that every side of every pair really does name the
`recruit_pool` line it claims.

### Cards on disk, at a size you can compare

`web/js/editor.js`.

**Unit cards on disk** and **Info cards on disk** list every *distinct* picture a
mod ships for one unit, because the game looks a card up under the *player's*
faction folder and a mod may ship one picture for ten factions or ten different
ones. They were 56px thumbnails — too small to tell two of them apart, which is
the only reason the list is there.

Each is now shown at the size the slot above shows it: a unit card as a portrait,
an info card as the full-width banner, its caption stacked underneath. They also
stopped being `loading="lazy"`: an info card is sized by the picture itself, so
an unloaded one is a zero-high box, and a zero-high box never scrolls into view
to be loaded.

And the slot above drops its own picture as soon as there **is** a list, because
that picture is only whichever faction folder resolved first — a copy of the
first row below, at the same size. The slot keeps what only it has: the import
that renames one file and copies it into **every** faction folder that owns the
unit, which is a different job from replacing one file where it lies. A staged
import brings the picture back, since that one is not a repeat of anything.

### The 3D viewer opens closer

`web/js/viewer3d.js`, `v3Frame`.

A unit is a standing figure, and its **height** is what should fill the frame.
Fitting the largest extent instead let a spear held straight out — two metres of
it, and not the subject — decide how far away the man stood, so every unit sat in
the middle distance with most of the panel empty.

Height leads now; the width only takes the framing back on something genuinely
wide rather than long-armed. A spear roughly doubles a man's width, which is
where the halving comes from; a siege engine is wide all the way through and
still gets fitted. A weapon that runs off the sides is the intended trade — the
wheel zooms out, and **Recentre** comes back here.

Measured on Gondor Spearmen: the figure now fills 92% of the panel's height
instead of 48%, about 1.9× larger on screen.

### The one modeldb field that can only hold 0

`unittransfer/modeldb.py`, `_Reader.get_attach_sprite`.

An attachment texture group is four names — faction, texture, normal, sprite —
and an attachment has no sprite, so its fourth field is the bare `0` that means
*no name follows*. A number other than 0 there is not a length: there is no name
for it to be the length of.

It happens anyway. Delete a faction's skin by hand and the digit from a removed
line can end up glued to the 0, giving `... .texture 01`. The reader then took
the 1 as a length, ate the next field as a one-character name, and died two lines
lower on a word that was perfectly fine where it was — the worst error this
format can produce, because the line it names has nothing wrong with it. Reported
from the wild on Tsardoms Multiplayer Edition, entry #333:

```
was:  Reading model entry #333 ('bulgarian_guards_ug2') it stopped making sense
      at line 14401, column 3: expected the length of a name here and found 'None'…
now:  Reading model entry #333 ('bulgarian_guards_ug2') it stopped at line 14399,
      column 81: an attachment texture's sprite length is written as '01' here,
      and 0 is the only value it can be — an attachment has no sprite, and the 0
      is what says so. Delete what follows the 0 at this spot and the file reads.
```

It refuses rather than assuming the 0 and reading on. Half a dozen span walkers
further down that file re-walk the same bytes to place an edit, and one of them
reading a file differently from the others is how a save writes at the wrong
offset. A refusal that names the character costs one keystroke to act on; a
recovery that only one walker knows about costs a file.

`tests/test_modeldb_attach_sprite.py` builds a modeldb of its own and pins all of
it: the good `0`, three shapes of stray digit, and a name in that slot that is
internally consistent and still wrong.

### Preview is called Probe

Every button, heading, note and tooltip that said *Preview* says **Probe**. This
is the word only: function names, CSS classes, `/preview_image` and the
`model_preview` setting are untouched, so nothing anyone has saved changes
meaning. The 3D viewer's own **3D preview** keeps its name — it is a picture, not
a plan.

---

## Not in this release

The historical records — `ROADMAP.md`, `HANDOFF.md` and the older
`merge/RELEASE_*.md` — still say *Preview* where they record what a past release
shipped. Rewriting a changelog would misreport what was written at the time.
