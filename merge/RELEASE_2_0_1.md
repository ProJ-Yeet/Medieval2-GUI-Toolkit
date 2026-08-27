# v2.0.1

Extends image replacement from unit cards only to every picture the tool
displays. No other changes.

## Added

* **Replace any image.** Right-click any picture for **Replace image** and
  **Open file location**. Screens where the image is the subject also get an
  edit control on the image itself: unit card variants, the ancillary editor,
  faction art, building icons, and the pips and cards in Minor Files.
* **Resolution warning before writing.** The engine does not rescale UI art, so
  a 512x512 file used for an 80x24 card is drawn stretched. The confirmation
  dialog shows both images at actual size, their dimensions and file sizes, and
  lists every path that will be written, marked as overwritten or created. It is
  a warning, not a restriction.
* **Unit cards are copied to every faction folder that holds one.** The engine
  resolves a card under the player's faction folder, so one card is typically
  duplicated across several folders. Replacing only the one found first would
  leave the rest stale.
* **Art inherited from the base game is identified as such.** Replacing one
  writes the mod's first copy at the path the engine looks for, rather than
  reporting an overwrite of a file the mod does not contain.
* **`.png` and `.jpg` are converted to `.tga` on import.** The engine reads no
  other format.
* Every write is backed up and undoable. A created file is deleted on undo
  rather than restored.
