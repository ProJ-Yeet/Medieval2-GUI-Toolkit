# v2.4.2

**The toolkit in German, and a transfer that lands files where you point
it.** The first translation of the interface: every one of its 8,112 strings
in German, offered in Settings as a draft for a native speaker to read over.
And two fixes to Unit Transfer from a tester's report.

## New

* **Deutsch.** Settings > Interface language now offers *Deutsch (German) -
  Entwurf*. Every screen, button, finding and message is in German, with the
  game's own words where the German release has them (*Gefolge* for
  ancillaries, *Runde* for a turn). It is marked a draft until a German
  speaker has read it; anything that reads wrong is worth reporting. Mod
  content, unit names and file names stay as the mod has them.

* **Room for longer words.** Every screen was measured in German at desktop
  width and on a phone with nothing clipped; the one squeeze, the Buildings
  view toggle, no longer shrinks.

## Fixed

* **Reroute lands files in the folder you pick.** Picking
  `unit_models/_units/umbar_swap` wrote the files a whole source tree deeper,
  under `umbar_swap/_Units/Umbar/`. They now land in the folder picked; only
  when two files would land on one path is the full structure kept.

* **A unit whose dictionary the destination already uses is a conflict.** A
  new unit type with a dictionary name the destination had (97 of Third Age
  Reforged's units against Divide and Conquer) became a second unit on the
  same dictionary, and overwrote the other unit's name, description and cards.
  It is now caught as a conflict: Rename keeps the type and gives it a new
  dictionary, and a rename never reuses a type or dictionary the destination
  already has.

* **The unit card choices say what they do.** *Keep* only fills the faction
  folders that have no card; the panel now says so, along with what
  *Overwrite* does.
