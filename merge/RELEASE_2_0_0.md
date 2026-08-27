# v2.0.0

Unit Transfer is now the Medieval 2 GUI Toolkit. Previous versions moved units
between mods; this release adds editors for most of the rest of a mod.

Settings, backups and the transfer log carry over. The old launcher still works
and forwards to the new one.

## Added

New modules:

* **Home.** A card per detected mod showing which game files it has, per module.
* **Strings.** Reads and writes `.strings.bin` directly, removing the need to
  delete the compiled file and rely on the game rebuilding it.
* **Traits** and **Ancillaries.** Full editors covering both the definitions and
  the triggers, saved as one operation. Deleting a trait removes its triggers.
* **Trigger builder.** Shared by both editors. One field per token, populated
  from the mod's own traits, ancillaries, factions, cultures and buildings.
  Warns when a condition can never fire on its event.
* **Minor Files.** Rebel factions, religions, cultures, resources and character
  names in one tabbed module.
* **Factions.** All factions, with map colours shown as swatches and edited with
  a colour picker.
* **Building trees.** Create a complete tree, the building block plus its text
  keys, in one operation.

Other additions:

* **Code View** in every editor: the raw game file beside the form, with
  hover-to-highlight both ways and live two-way editing. Can hide comment-only
  lines and restore them exactly.
* **Clean up the unit file.** Group, tier and reorder `export_descr_unit.txt` as
  a whole file, repeatably. Running it twice produces no further change.
* **Unit tiers**, stored in a comment the engine ignores.
* **City/castle twin check** on the unit view, with a button to copy a
  recruitment pool across.
* **Replace image** and **Open file location** on any picture, via right-click.

## Fixed

* The tool was shutting down its own server during use. Black unit cards,
  `Failed to fetch`, the grey screen on Transfer and the unresponsive Settings
  button were all the same fault: the icon cache was written next to the
  application, which for most users is inside OneDrive. It now lives in
  `%LOCALAPPDATA%`.
* A byte order mark caused the unit and faction parsers to drop their first
  record.
* `settings.json` was written non-atomically, so a request arriving mid-write
  reported no Medieval II installation.
* Ctrl+Z / Ctrl+Y now work in all editors, including inside Code View.
* Sidebar filter groups can be collapsed, and a collapsed group with an active
  filter shows a count.
* "Open file location" opens the file's folder rather than Documents.
* Switching mods mid-load no longer renders the previous mod.

## Performance

| | Before | After |
|---|---|---|
| `/api/units`, 916-unit mod | 4189 ms | 350-420 ms |
| Opening the log | 571 ms | 51 ms |
| 427 unit cards, warm cache | 6.0 s, 137 failures | 3.3 s, 0 failures |

## Known limitations

* `descr_sounds_*.txt` is not yet supported.
