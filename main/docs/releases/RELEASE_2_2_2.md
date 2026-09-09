# v2.2.2

Two files nothing here could open before, and a section of a third that has been
read wrong since Phase 11. The campaign map editor is not in this build's menu -
it is a beta, and it lives on the dated **beta** pre-release instead, which is
where most of the work since v2.2.1 has gone.

## New

* **A Guilds editor.** `export_descr_guilds.txt` is two files pretending to be
  one: the top half says what each guild grants and where its tier thresholds
  sit, and hundreds of lines below, a second half awards the points that reach
  those thresholds. Reading either half on its own tells you almost nothing, so
  both are on one screen, and every point line is listed against the trigger it
  comes from with its scope letter spelled out rather than left as a letter.

  It also answers a question the Buildings module could only ask. A building
  with a `guild_` requirement it refused had nowhere to go; now the requirement
  can be fixed where it lives. The fault in the other direction is reported too,
  and it is real: **Divide and Conquer awards guild points to two guilds it
  never declares**, and every one of those points goes nowhere.

* **`descr_names.txt` has a fourth section, and Minor Files was reading it as
  names.** The file's sections are `settlements`, `characters`, `women` and
  **`surnames`**, and only the first three were known. Exactly one faction in
  one installed mod uses the fourth - Third Age Reforged's `dolguldur` - so the
  heading and the single name under it were both being listed as characters.

  This was invisible to every test the project has, because a line the parser
  files under the wrong heading is still a line it writes back unchanged: the
  file always came back byte for byte, it was just described wrong. Two
  independent references name all four sections, and the tab now offers the
  fourth when a faction has not got it.

## Fixed

* A text key written into a `data/text/*.txt` file now **recompiles the
  `.strings.bin` beside it** in every case rather than most of them. The game
  reads the compiled archive, not the text, so a write that left the cache stale
  showed the old words and looked like the tool had done nothing. That is the
  whole reason "just delete the .bin" is folklore.

## Where the rest of it went

Most of what has been built since v2.2.1 is campaign-map work and is on **beta
2026-09-09**: the historical events a campaign fires, the natural disasters its
map allows, faction movies, campaign menu titles and blurbs, which mercenary
pool a province hires from, and the names the player reads for a province, its
settlement and a character. None of that is in this build's menu.
