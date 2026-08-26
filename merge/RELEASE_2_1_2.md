# Medieval 2 GUI Toolkit v2.1.2

Two things this needed for a while did not fit in the same file as anything
else — copying a trait or an ancillary out of another mod, and telling the
toolkit a mod runs on M2EX so it stops flagging the engine ceilings M2EX
replaces — so they got their own release rather than waiting on Phase 16. The
3D viewer also stopped being a thing you leave the unit for: it docks beside
the fields now, in both the Unit Editor and the BMDB browser. The rest is a
dozen bugs the tool found by being used, the same way 14 was.

A subrelease: real features, same as 14j, not folded into the next phase
because Phase 16 (the Campaign Map Editor) is a different program entirely.

---

## The short list

- **Port a trait or an ancillary out of another installed mod.** ⇩ button on
  both lists. Brings the block, the triggers that grant it and its text keys
  together, because those three are what a trait or an ancillary actually is,
  and reports — never guesses — anything the record names that the
  destination has not got.
- **Mark a mod as M2EX** (Home card, or Settings for the whole list) and the
  toolkit stops reporting the five engine ceilings M2EX replaces — 31
  factions, 500 units, 9 trait levels, 8 ancillary effects, 32 recruitment
  slots. Every other check keeps running.
- **The 3D model viewer docks beside the Unit Editor and the BMDB list**
  instead of taking over the screen. On by default in the editor; a 🧊 button
  per row in BMDB.
- **A new trait or ancillary no longer ships with blank required fields.**
  Leaving Image, Description or EffectsDescription untouched used to write an
  empty line instead of the usual default — a crash the first character
  screen it reached.
- **Typing a brand-new key's wording at the same time as the key itself no
  longer throws the wording away**, in Traits, Ancillaries and Minor Files.
- **Native folder/file pickers stop hiding behind the browser window.**
- **A unit card that appears mid-session is found reliably now**, even the
  ~3.5% of the time a file replace leaves its folder's mtime exactly where it
  was.
- **Clicking inside a text box and letting go over the backdrop no longer
  closes the dialog underneath you.**

---

## Everything in this release

### Porting a trait or an ancillary between mods

`unittransfer/portrecords.py` + `web/js/portui.js`. Every other editor in the
toolkit works on one mod; this is the one that reads two.

A trait or an ancillary is **three things in two files**, and a port that
brings one of them is worse than none: the definition block, the triggers
that grant it (`Affects <trait>` / `AcquireAncillary <name>`, hundreds of
lines below in the same file), and its text keys
(`export_VnVs.txt` / `export_ancillaries.txt` — left behind, the character
screen crashes the moment anyone has it). All three move together, in one
job, with one backup set and one undo.

What it deliberately will not do: rewrite what the block refers to. A ported
trait keeps its `Characters`, `ExcludeCultures` and `AntiTraits`; a ported
ancillary keeps its `Image` and `ExcludedAncillaries`; the triggers keep
every condition. Those name cultures, religions, other records and picture
files the destination may not have, and guessing a substitution is how a
port silently becomes a different record — so every one of them is checked
against the destination and listed in the preview instead. It does not copy
pictures either; the port says when the destination has not got one, and the
Images tool (14j) is what puts one there.

The two record types share a module because they share a format: the EDA is
the EDCT with the level ladder removed, same header keywords, same trigger
language, same "its name is a key in a text file" — which is already why
`triggers.py` serves both. A name the destination already has is skipped and
said so unless "replace what is already there" is ticked, and a trigger
whose *name* collides is skipped the same way rather than silently renamed —
a trigger name is what the destination's own file already points at.

Two mods, `Divide_and_Conquer_EUR` and `Third_Age_Reforged`, offer 799 traits
and 703 ancillaries between them in the test — every one of them plans
without an error and round-trips both files byte-identical outside the
spliced ranges.

### M2EX: telling the toolkit which engine tables are not there

`unittransfer/modflags.py`. Nothing under `data/` says whether a mod runs on
M2EX, and M2EX exists specifically to remove the ceilings the vanilla
executable hardcodes — so a mod built for it sits over several of them by
design, and the toolkit reported all of them as findings. The mark is stored
per mod root (the same way the M2TWEOP folder setting is), ticked on the
Home card or from a list in Settings, and it is deliberately narrow:

- **only the five finding kinds that are engine ceilings go** —
  `too-many-factions`, `too-many-levels`, `too-many-antitraits`,
  `too-many-excluded`, `too-many-effects`, `recruit-limit(-always)`;
- **everything else still runs.** A missing text key, a header line in the
  wrong order, an `AntiTraits` naming a trait the file does not define — none
  of those are things M2EX makes legal, and `modflags.uncapped` only ever
  drops the six kinds above, checked in `test_modflags.py` against a trait
  and an ancillary built to be over *every* ceiling plus one ordinary
  mistake each, to prove the mistake survives.

This is not the M2TWEOP per-mod setting — that one says where a mod keeps
extra unit files. A mod can be either, both or neither, and the UI says so
in both places it appears.

### The 3D viewer, docked

`web/js/editor.js`, `web/js/bmdb.js`, `web/js/viewer3d.js`. Reaching a unit's
model used to mean leaving the unit — BMDB mode, find the entry among two
thousand, open it, look, come back. `viewer3d.js` already knew how to paint
into any element it was handed; it just never had anywhere but the modal to
do it.

`v3Mount`/`v3Unmount` let the same viewer — same shader, same load path —
paint into a panel instead of taking the dialog over, with one viewer alive
at a time (mounting a second drops the first, rather than running two WebGL
contexts and two 30 MB meshes at once). The Unit Editor's column is on by
default and survives a tab switch by being *detached* from the modal before
`renderEditor` replaces its markup and *reattached* after — otherwise every
tab switch would refetch the model into a fresh, dead canvas. It can be
folded (pauses the draw loop, keeps everything on the GPU so unfolding is
instant), hidden (remembered per session), or sent full screen. BMDB mode
gets the same column from a 🧊 button per row, or "🧊 View in 3D" to open it
on whatever is on screen.

### Where a new record's blank fields used to write nothing

`unittransfer/ancillaries.py`, `unittransfer/traits.py`. The editor posts
every field on every save, so a box left untouched arrives as an **empty
string**, not a missing key — and `setdefault` only fills in a *missing*
key. A new ancillary with an untouched Image/Description/EffectsDescription
box, or a new trait level with an untouched Description/EffectsDescription/
Threshold box, was written with that line blank: one of `REQUIRED`, so the
block crashed the character screen the moment anyone reached it, and this
module's own save-time check then refused to save it a second time. Blank
now means "give it the usual value", checked with `str(...).strip()` rather
than `setdefault`.

### A new key's wording, typed before the form knows about it

`web/js/ancillaries.js`, `web/js/traits.js`, `web/js/minorfiles.js`. The
words box beside a text key (`anLocText`/`trLocText`) used to be bound to the
**key's current value**, baked into its `oninput` handler at the moment the
form was last drawn. Typing a brand-new key does not repaint the form — it
would move the caret out of the box the user is typing into — so the words
box beside it kept the handler for the *old*, usually empty, key. Type both
in one sitting and the wording landed nowhere: saved under an empty tag that
`anLocBody`/`trLocBody` then drops.

The fix binds the words box to the **field itself** — which key on the form,
not which string that key currently holds — and resolves field → key only at
save time, in `anLocBody`/`trLocBody`/`mfLocBody`. That is also what makes
*renaming* an existing key carry its already-typed wording with it, rather
than orphaning it under the old tag. `trDelLevel` re-indexes the pending
edits for the same reason: they are keyed by level position, so removing a
level has to slide every edit below it up one slot or the next level would
inherit words that were never meant for it.

Minor Files had the same shape for a rebel faction's or a religion's shown
name (`mfSetLocName`/`mfLocTag`), plus a second bug in the same area: a
rebel faction's `unit` line is a unit *type* and the rest of the line is its
name, spaces included (`Mordor Orcs Invasion`), and the box was repainted
from a **trimmed** copy of its own value on every keystroke — cutting the
space bar back off before the next character landed. Trimming now happens
once, at save time.

### Also fixed

- **Native folder/file pickers no longer open behind the browser.**
  `unittransfer/folder_dialog.py` — every dialog here is opened by the server
  process, which owns no window and never had the foreground, so Windows'
  foreground lock left the dialog behind the browser with nothing but a
  flashing taskbar icon to show for it (indistinguishable from "Browse…
  stuck loading"). A hidden owner window, created and destroyed around each
  dialog, fixes both halves: an owned window always draws above its owner,
  and borrowing the foreground thread's input state
  (`AttachThreadInput`/`SetForegroundWindow`) for the moment it takes to
  raise it is the documented way out of the lock.
- **A unit card added or replaced mid-session is found reliably.**
  `unittransfer/mod.py` — the icon-folder cache keys on the folder's mtime,
  which is only as precise as the OS clock's tick (15.625 ms by default on
  Windows). Two changes inside one tick land on the same mtime, and
  measured on this machine, replacing a file in place (unlink, then create
  under a new name) left the folder's own mtime untouched **70 of 2000
  rounds — 3.5%**. An entry listed while its folder's mtime is still inside
  that window is now marked *racy* and re-listed next time — the same rule
  git uses for "racily clean" index entries — so the extra cost lands only on
  a folder something just wrote to.
- **Typing inside a dialog no longer closes it.** `web/js/core.js` — a
  `click` fires on the nearest ancestor the mousedown and the mouseup still
  share, so a press that begins inside a text box and a release that lands
  on the backdrop — because the box's own re-render (several dialogs redraw
  on every `input`/`change`) swapped what was under the pointer mid-press —
  dispatched as a click on `#overlay` and shut the dialog. Now only a press
  that *began* on the backdrop counts.
- **The BMDB cleanup dialog re-opens on today's cleanup, not the one from
  before you ran it**, and keeps the folder you typed and the sections you
  had open across the run instead of resetting them.
- **Ships no longer fill the "No voice entry" tab.** A naval unit has no
  `Unit_Select` bark to give it — the ship banks cover that — so every one of
  them sat in that tab permanently. They are counted and said
  (`ships_skipped`) rather than listed.
- **⧉ Clone, on Minor Files' rebel factions, religions, cultures and
  character-name sections.** Starts a new record holding everything the open
  one holds, under a free name, staged in the page and unsaved until Create
  — building the next rebel faction no longer means picking every unit out
  of the dropdown again.

---

## Under the hood

**Tests:** `tests/test_modflags.py` (18 checks) and `tests/test_port.py` (50
checks, including a real plan against the two installed mods' 799 traits and
703 ancillaries) are new. `tests/test_liveness_and_cache.py` gained a
deterministic reproduction of the racy-mtime window — pinning a folder's
mtime by hand rather than sampling for the 3.5% — and now counts real
`os.scandir` calls to assert the cache is actually served from, not merely
compared for equality.

**61 test modules**, run individually (`python -m tests.test_X`) rather than
through `unittest discover`, which does not fit this suite's shape — every
module is a script that runs its own checks at import time and calls
`sys.exit`, not a `TestCase`.

---

**Next:** Phase 16, the Campaign Map Editor — 3.0.0.
