# v2.3.0

Two things the BMDB editor could not do before, a repository laid out so you can
find anything in it, and a README that shows the tool instead of describing it.
The campaign map editor is not in this build's menu - it is a beta, and it lives
on the dated **beta** pre-release instead.

## New

* **The entries your modeldb lists twice, and the two ways out.**
  `battle_models.modeldb` is a flat stream of entry blocks and nothing in the
  format stops the same name appearing in it twice. Real mods are full of it:
  Third Age Reforged ships eight such names, Divide and Conquer five. **M2TW
  reads the first block with a name and walks past every later one**, so a
  second block is a model the mod is carrying and cannot reach, and there is no
  error anywhere saying so. A modder who pasted a fixed model in at the bottom
  of the file is looking at a mod that ignores it.

  BMDB mode has a **Duplicates** button now, and it offers exactly the two
  things worth doing to a block that is not the first of its name:

  * **Rename it.** It stops being dead and becomes a real entry a unit can be
    pointed at. The plan says out loud that nothing names the new entry yet, so
    it does not read as a finished job.
  * **Remove it.** The file loses that block and the header's count follows.

  Which one is right depends entirely on whether the block is a copy of the
  first or a different model, so that is the loudest thing on every row. An
  exact copy says so, and dropping it loses nothing at all. A different one is
  listed field by field, off the parsed entry rather than the raw text so that
  whitespace never reads as a difference: *"skins for 5 factions vs 3 (adds
  england, russia); different attachment skins"*, with the line number of each
  block so you can go and look. Two bulk buttons cover the decisions people
  actually arrive with: drop everything that is only a copy, keep everything
  that is a real model.

  The first block of a name is never touched by either action. It is the one the
  game reads and every reference in the mod resolves to it. Only the modeldb is
  written, it is backed up first, and 🕑 Log → Undo puts it back.

* **HD textures in the 3D viewer.** The viewer has always halved any skin over
  1024 pixels, because the ordinary errand in front of a list of two thousand
  entries is "which model is this", and a soldier on screen a few hundred pixels
  tall gains nothing from a 2048 sheet that costs four times the bytes and the
  video memory. The other errand is checking a skin's own detail - a seam, a
  badge, whether a face is painted or just noise - and for that the halving was
  the whole problem: the game draws the full sheet, and the viewer was showing
  something the game never shows.

  There is a **HD textures** button next to Wireframe now. It draws the sheet at
  the size the mod ships it, which is the size the game draws. It is remembered
  between sessions, it reloads only the skins and never the geometry, and both
  sizes are cached separately, so switching back and forth converts each sheet
  once and never again. The facts panel says which you are looking at - *"drawn
  at 2048 × 2048 - the size the mod ships, as the game draws it"* - read off the
  loaded image, so it cannot claim a size the viewer is not drawing.

## The repository

Nothing in the tool changed for this, but everything is somewhere else, and
anyone who has cloned it will notice.

* **The top of the repository holds three things**, which are the three a person
  opens: `Install-Dependencies.bat`, `Launch-Medieval2-GUI-Toolkit.bat` and
  `README.md`. Everything else is under **`main/`**, which is now the code root.
* **`tools/` is gone.** It held one binary the tool needs at runtime and seven
  scripts no release has any use for, and the build shipped the folder whole -
  so every zip so far has quietly carried the repository's own prose checker.
  The binary is `main/vendor/nvtt/`; the scripts are under `main/dev/`, grouped
  by what they do: `release/`, `reference/`, `docs/`, `checks/`, `diagnose/`.
  None of it ships any more.
* **`merge/` is gone too**, because it held two unrelated things: the release
  notes are `main/docs/releases/` and the reference-tool audits, port manifest
  and sync log are `main/docs/upstream/`.
* ROADMAP, STATE and their archives are in `main/docs/`.

The launcher works in both layouts from one file: it steps into `main/` when
that is where `app.py` is, and runs from beside itself when it is not, which is
what the release zip looks like. **If you are running from a download, nothing
about this changes for you.**

## The README

* **The install order is the one that works**, said plainly in both the download
  and the from-source sections: run **`Install-Dependencies.bat` first**, then
  **`Launch-Medieval2-GUI-Toolkit.bat`**. It used to mention the installer as an
  aside about what to do when the launcher failed.
* **Ten screenshots of the real tool**, one per major screen. They are generated
  by a script that starts the toolkit, drives a headless browser through each
  screen and takes the picture, so re-taking them after a change is one command
  and they cannot quietly go a version out of date.
* **The credits are in it**, the same ones as the tool's own Credits screen.

## Fixed

* **Three test suites that were never runnable on their own.**
  `test_unit_view`, `test_unit_recruitment` and `test_kinds_and_sprites` put
  only their own folder on the import path, so `import unittransfer` failed
  unless the interpreter happened to be started from exactly the right place.
  The README has always said each suite runs individually; now they do.

## About the campaign map

The campaign map editor is **not on this build's menu**. It is feature-complete
but it is the first thing this toolkit does that WRITES to a campaign, so it
ships as a beta rather than to everyone: it is on the dated **beta** pre-release,
which is the same toolkit with the map switched on. Betas are named by the date
they were cut rather than by a version number. Everything in the notes above is
in both builds.

Nothing else moved. Unit Editor, Unit Transfer, Buildings, Unit Sounds, Sprites,
Strings, Traits, Ancillaries, Factions and Minor Files are exactly where 2.2.0
left them.
