# v2.3.0

Two new screens over files this toolkit already read, and a fix off a beta
report that had a faction rename quietly skipping a whole file. The campaign map
editor is not in this build's menu; it is a beta, and the far larger half of the
work since v2.2.3 went to the dated **beta** pre-release, which closes the
campaign map editor's roadmap outright.

## New

* **Is this faction finished? A screen that answers it.** Cloning a faction
  touches twenty files, and until now the only way to know whether the twenty-
  first had been missed was to load the game and find out. The Factions screen
  now audits one: every file a faction has to appear in, whether it is in that
  one, and what is missing where. A missing record is offered as a copy from a
  faction that has one.

  **The list is measured on your mods, not copied from a reference.** A **gap**
  is a record that every real faction in the file has; a **note** is one that
  working factions go without - shown, never counted against you. That
  distinction moved three checks and dropped a fourth outright: it turns out
  there are records that look mandatory in every tutorial and that half the
  factions in a shipping mod simply do not have.

* **Raw text: any file the toolkit reads, as plain text.** A parser that meets a
  line it does not model has always had one honest answer, which is to refuse
  and say so. Now it can point somewhere: every file this toolkit knows how to
  read can be opened as plain text and edited directly, with the same backup and
  the same one-click Undo as any other save.

  **It refuses on the bytes and never on the parser.** A save is stopped by
  three things and three things only: the file changed on disk since you opened
  it, a character the file's encoding cannot hold, or a file that would not
  survive being written and read back unchanged. What the toolkit's own reader
  thinks of your edit is a **warning** - an escape hatch that closes the moment
  the parser disagrees with you is not an escape hatch.

## Fixed

* **A faction rename now follows `descr_regions.txt` in mods that write it flush
  left.** Every province record names the faction that starts holding it, and a
  rename has to rewrite that line in each one. The reader assumed the body of a
  record is indented, because vanilla, Divide and Conquer and Third Age Reforged
  all indent theirs - so a mod that writes the same records hard against the
  left margin came out as one record per line with nothing in any of them. On
  the mod that reported it, a faction rename found **0 creator-faction lines
  where there are 209**. It was not an error message; the file was simply
  skipped, and the rename came back saying it had rewritten everything else.

  The indent was never part of the format. The engine's own parser ignores
  whitespace, which is why the mod plays. The reader now falls back to the
  record's own grammar when there is no indent to read it off, and a byte-order
  mark in front of the first province is no longer treated as part of its name.

  Nothing changes for a mod that does indent: vanilla, Divide and Conquer and
  Third Age Reforged all re-read field for field and line for line identical to
  before.

* **The browser console stays usable when the toolkit's server is not there.**
  The page sends a heartbeat every four seconds, and a heartbeat to a server
  that has stopped was logging an uncaught error every time. Measured while the
  server was away: **500 buffered console messages, every one of them that**,
  with every real error pushed out of the buffer behind them. Five requests that
  are deliberately sent and deliberately forgotten now swallow their own
  failures, which is what the code around them always meant to do.

## Where the rest of it went

Everything on the campaign map since v2.2.3 - and that is the bulk of it, eleven
sessions - is on **beta 2026-09-12**, which is also where this build's two new
screens live. See that note for the whole list.
