# v2.2.4

One fix, from a beta report: a mod that writes `descr_regions.txt` without
indenting it was being read as gibberish, and a faction rename quietly skipped
the file because of it. The campaign map editor is not in this build's menu; it
is a beta, and the larger half of this work went to the dated **beta**
pre-release.

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

## Where the rest of it went

The same fix is what puts the provinces of such a mod back on the campaign map
screen - they were all reading as painted and declared nowhere, with no name in
the hover and nothing to click - and it ships with a second one for map layers
that Pillow would not open at all. Both are on **beta 2026-09-11b**.
