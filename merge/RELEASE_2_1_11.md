# v2.1.11

Every panel in the tool takes the size you drag it to, the strings list says
what it is warning you about, and the em dash is gone from the codebase.

## Added

* **Resizable panels, everywhere.** Every scrolling list in the tool, every
  dialog that holds one, and the unit drawer now have a grab corner. Drag it and
  the box takes the height you gave it; the dialog takes width as well.
  Double-click the corner to hand a box back to its default.

  The one that prompted this is the **Recruitment list in the buildings
  browser**, which was 340px whether a level trained two units or sixty, inside
  a dialog capped at 92% of the window, so reading a long roster meant scrolling
  a list inside a scrolling dialog. It is now as tall as you want it, and so is
  the Other capabilities list under it, the unit-upgrade list, the faction
  lists, the strings file list, the model lists, the log, the previews and every
  other box of the same kind.

  Sizes are **remembered** (`pane_sizes` in `config/settings.json`), per box and
  per dialog, because how tall the recruitment list should be is a fact about
  your screen rather than about the building you happen to have open. A size
  saved on a bigger monitor is clamped to the window you open it in next.

  Nothing is changed until you drag it: a box you have never touched lays out
  exactly as it did before.

## Changed

* **"<name>.txt is newer" now says what it means.** The strings list warns when
  a mod's plain-text file was saved after the `.strings.bin` beside it was
  built, and that wording read like an accusation without naming the fault. The
  row now reads "…is newer than this .bin" and carries a **?** that explains the
  whole thing: the game reads the `.bin`, not the `.txt`, so anything the `.txt`
  has been made to say since then is not on screen in the game yet. It is
  usually just how the mod was written rather than a fault, the rows on the
  right are the `.bin`'s real contents, and ⟳ Rebuild from .txt is for when the
  `.txt` is the version you want to keep.

* **No em dashes, anywhere.** All 4176 of them across 171 files - code,
  comments, docs, release notes, UI strings - are now plain hyphens, and
  `tools/prose_check.py` reports any that come back.

## Fixed

* **The folder picker comes to the front.** Choosing a mod folder could open the
  OS dialog behind the browser window, where it looked like the button had done
  nothing. Its owner window is now created visible-but-transparent and the
  dialog is raised on its own account once it appears, from a watcher thread,
  because the call that opens it does not return until you have answered.

## Also in this build

Work that landed alongside the above:

* **Battle-model entries only.** A transfer mode that copies a unit's
  `battle_models.modeldb` entries and their files without writing a unit at all,
  ticked off per entry. New `GET /api/unit_models`, and the log row says
  "battle models only" rather than naming a unit that was never written.
* **A colour picker for faction colours.** The two colours on a faction are a
  swatch and a hex box that drive each other, with the file's own
  `red 55, green 75, blue 48` still shown underneath, which is what is written
  to disk. The row no longer repaints while the OS picker is open, which used to
  close it on every drag through the gradient.
* **A new unit gets a new player-visible name.** Cloning a unit left it called
  whatever the original was called, because the localisation record is copied
  with everything else. It now arrives as "<name> (new)", editable before you
  write it.
