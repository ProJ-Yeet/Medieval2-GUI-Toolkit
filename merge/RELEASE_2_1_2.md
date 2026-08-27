# v2.1.2

## Added

* **Port a trait or ancillary from another installed mod.** Available on both
  lists. Transfers the block, the triggers that grant it and its text keys
  together, and reports anything the record references that the destination does
  not have. It reports rather than guesses.
* **M2EX support.** Mark a mod as M2EX on its Home card, or in Settings for the
  whole list, and the toolkit stops reporting the five engine limits M2EX
  removes: 31 factions, 500 units, 9 trait levels, 8 ancillary effects, 32
  recruitment slots. All other checks continue to run.
* **The 3D model viewer docks beside the Unit Editor and the BMDB list** instead
  of replacing the screen. Enabled by default in the editor; per-row control in
  BMDB.

## Fixed

* A new trait or ancillary no longer writes blank required fields. Leaving
  Image, Description or EffectsDescription untouched wrote an empty line instead
  of the default value, which crashed the game at the first character screen
  that referenced it.
* Entering a new key and its wording at the same time no longer discards the
  wording, in Traits, Ancillaries and Minor Files.
* Native folder and file pickers no longer open behind the browser window.
* A unit card added during a session is now found reliably, including when a
  file replacement leaves the folder's modification time unchanged.
* Clicking inside a text field and releasing over the backdrop no longer closes
  the dialog.
