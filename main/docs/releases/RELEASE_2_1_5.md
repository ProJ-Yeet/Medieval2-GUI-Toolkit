# v2.1.5

Fixes three cases where the battle model cleanup deleted models the campaign
still uses, and adds a way to recover from earlier cleanups that did.

**This build also restores the vanilla building art to the download.** Versions
2.1.1 through 2.1.4 shipped without it. See "Packaging" below.

## Fixed

* `change_battle_model` is now read. This script command swaps a character's
  model mid-campaign and places the model name last on the line, so neither
  existing pattern matched it. A model referenced only this way was reported as
  unused and offered for deletion.
* Custom battle maps are now read. `descr_battle.txt` was not scanned at all.
* Campaign folders are scanned recursively. Custom campaigns sit one level below
  where the scan previously stopped.
* Installer variant trees (`Activate\`, `extra\`) are now scanned. These become
  the live mod when the mod's own configuration switcher runs.
* Fixed a crash (`MemoryError`) when scanning a mod containing very large files.
  The text scan now streams instead of loading whole files into memory.

On one large mod this took the number of campaign files scanned from 2 to 15.

## Added

* **Clean up BMDB > Recheck past cleanups.** Re-reads the cleanup log, re-tests
  everything previous runs removed against the current reference checks, and
  lists anything that should not have been removed, with the reason and whether
  a copy is still available. Selected rows can be restored; the restore is
  itself undoable.

  A run whose backup and export folder have both been deleted is still listed,
  marked as unrecoverable rather than offering a restore that would fail.
* Cleanups now record which entries they removed, so this remains answerable
  after the backups are gone.
* `app.py --no-browser` starts the server without opening a browser tab.

## Performance

* Cleanup scan on a large mod: 292s to 22s.

## Packaging

**If you are running 2.1.1, 2.1.2, 2.1.3 or 2.1.4, your copy is missing the
vanilla building art.** Those builds are ~19 MB; this one is ~54 MB. The
difference is the packed vanilla building icons that Buildings mode falls back
to for any icon a mod does not ship itself, so without them most building slots
in most mods render a placeholder.

Bundling that folder was an opt-in build flag and was missed for four releases.
It now ships by default, a missing folder fails the build, and the build
verifies the finished archive contains it before publishing.

Upgrading is the only action required. Settings and backups are unaffected.
