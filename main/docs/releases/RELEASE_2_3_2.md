# v2.3.2

Two fixes, and both are the same mistake in different places: **the toolkit
could not tell a file it cannot read from a file that is not there**, and it
said the wrong thing about both.

## Fixed

* **"There is no faction slot called england in this mod" - when there is.**
  Open Minor Files → Factions on a mod that has never been unpacked, and the
  whole screen refused. Try Rename slot on one and every faction was refused
  the same way, by name, as though you had invented it.

  The slot list comes out of `descr_sm_factions.txt`, and the stock game keeps
  that file **inside its `.pack` archives** - vanilla ships no loose copy at
  all. The tool read the file, found nothing, and reported the only thing it
  could see: an empty list. An empty list and a name that is not in one look
  identical from there, and the tool guessed wrong about which it was looking
  at, every time.

  It now says what is actually wrong: the file is not loose, how many archives
  it can see beside the mod, and that unpacking it into `data/` makes every
  faction editable. One sentence, written in one place, so the Factions screen
  and the Rename box can no longer disagree about the same absence. A slot that
  genuinely is not in a file that **is** there still gets the old message,
  which was the half that was right.

* **A picture that would not load stayed broken until you cleared the cache.**
  Every picture the toolkit draws - unit cards, info cards, faction symbols,
  model textures - is converted once and kept. When a file could not be
  decoded, the blank it drew instead was kept too. So fixing the file changed
  nothing: the tool went on serving the blank it had cached before you fixed
  it, and the only way out was clearing the cache.

  A blank drawn for a file that could not be read is no longer cached. Replace
  the file and it appears. Art a mod simply does not ship is unaffected and
  still costs nothing - that is the ordinary case, mods ship the art they
  changed and leave the rest to the game.

## Under it

The two share a cause. `png_bytes`, which is the route behind every picture in
the toolkit, answered "there is no such file" and "this file is there and will
not decode" with the same 1x1 transparent image. The first is normal and should
stay silent. The second is a fault and now says so - in the log always, and on
screen wherever a screen can show it.

Nothing here got noisier about art a mod does not ship. That case was checked
first and deliberately left exactly as it was.

## Where the rest of it went

The same work fixes a much more visible bug on the campaign map side, where the
strat model viewer was drawing settlements as a single bare cube. That screen
is not in the 2.x line. **beta 2026-09-12c** is this same build with the
campaign map editor switched on, and its notes cover it.
