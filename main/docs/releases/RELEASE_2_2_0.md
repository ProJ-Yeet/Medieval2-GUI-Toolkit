# v2.2.0

Ten faults in the Unit Editor's new-entry and unit-card work, all found by
testers against 2.1.11 and all fixed against a running mod. The campaign map
editor is not in this build's menu - it is a beta, and it lives on the
**beta 2026-09-06** pre-release instead.

## Fixed

* **An imported unit card actually saves.** Staging a card or an info card left
  the editor thinking nothing had changed, so Save answered "Nothing to save"
  and nothing ever reached the mod. It counts as a change now.

* **...and the picture you replaced stops being the picture you see.** Two
  faults on top of each other. `shutil.copy2` carries the SOURCE file's
  timestamps onto the copy, and a mod's files come out of one archive stamped
  to the same second - so copying one of Third Age Reforged's unit cards over
  another left the destination with the very mtime it already had, and the icon
  cache, whose key is the path and that mtime, went on handing out the picture
  that had just been overwritten. A file this tool writes is now stamped with
  the time it wrote it, which is both true and what every cache downstream
  reads, and the file size joins the key as a backstop. The second half was in
  the page: the stamp that told the browser to re-fetch was painted onto the
  `<img>` tags that happened to be on screen, and a save closes the editor and
  rebuilds the whole unit grid, whose fresh URLs went straight back to the
  browser cache. The stamp lives in the page's state now, so every URL built
  after a write is one the cache has never seen.

* **Replacing a unit card asks where it goes.** A card is a file per owning
  faction, and the old button had one answer: all of them. The dialog now lists
  every folder the card is looked up under - each owning faction plus the
  mercs/merc fallback - with a thumbnail of what that folder holds today and a
  tick box. **Replace for all** is one button; untick the two that should keep
  their own art and they are left exactly as they were. Folder names are
  sanitised before they become a path, and a folder outside the unit's
  ownership is written but warned about rather than silently obeyed.

* **...and which picture.** A unit whose folders really do hold several
  different cards has the art already, and the question is only which one the
  ticked folders should get - so those pictures are offered as pictures, above
  "Choose a file from disk...". Where every folder already shares one picture
  there is nothing to standardise, and that half of the dialog is not drawn.

* **A new model entry adds an armour tier instead of eating one.** "Point EDU
  slot at it" listed only the slots the unit already had and opened on the first
  one the cloned entry filled, so a new entry cloned from an armour upgrade
  wrote straight over it. Every choice now says what it would replace
  (`armour_ug_models#1 (replace numenor_axemen)`), the list ends with the tier
  after the unit's last, and that is what it opens on. The entry is named to
  match, and appending a tier grows `armour_ug_levels` with it - a tier past the
  end of that list is one the game can never reach.

* **A new battle-model entry can be given its own attachment skin.** An
  attachment is a second texture group with its own files per faction - the
  horse under a rider, a shield sheet - and the new-entry form could only hand
  it the main texture. It has its own texture and normal-map slots now, shown
  when the entry being cloned actually has an attachment group, with the old
  checkbox left as the fallback for whichever slot you leave empty. No sprite is
  written into an attachment record any more: that field is the bare `0`.

* **A staged model entry is no longer called missing.** The field checks ask
  what a save is about to create, and the unit editor answered "nothing" while
  holding a list of pending entries - so naming one in `armour_ug_models` was
  flagged "not an entry in this mod's battle_models.modeldb", which was true of
  the mod as it stood and false of the mod that same save would leave behind.

* **The entry list refreshes after you add an entry.** The model picker's table
  and the field editor's vocabulary were read once per mod and kept for the
  whole session, so an entry created here stayed invisible until the page was
  reloaded. A save drops both, and an entry staged but not yet saved is offered
  by both, marked as staged.

* **Renaming a staged model entry takes the unit's lines with it.** The armour
  tier menu writes the new tier into `armour_ug_models` the moment it is added
  and only then opens the form, so renaming the entry there left the unit
  pointing at a name that was never going to exist. The lines that name it
  follow the rename, and the form says which ones they are before you type.

## Changed

* **The menu's hints are sentences.** Every module's one-line description in the
  burger menu reads as a sentence now, and `dev/checks/prose_check.py` has the rule
  that catches the next one.

* **The credits name who this was built on.** Four works this toolkit took
  reference from, with thanks for the permission: Mylae's M2TW Editor, Fynn's
  Medieval II Total War Modding Tool, Bare Geomod by Sinople and Gigantus, and
  Withwnar's TWMapReader. Three testers who joined since 2.1.11 are credited too.

## About the campaign map

The campaign map editor is **not on this build's menu**. It is feature-complete
but it is the first thing this toolkit does that WRITES to a campaign, so it
ships as a beta rather than to everyone: it is on the **beta 2026-09-06**
pre-release, which is the same toolkit with the map switched on. Betas are named
by the date they were cut rather than by a version number. Everything in
the notes above is in both builds.

Nothing else moved. Unit Editor, Unit Transfer, Buildings, BMDB + Sprites, Unit
Sounds and Minor Files are exactly where 2.1.11 left them, and the Factions tab
in Minor Files opens the same faction screen it always did.
