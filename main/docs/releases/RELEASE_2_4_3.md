# v2.4.3

**The toolkit in Spanish, and German that no longer leaks English.** The
second translation of the interface: every one of its 8,120 strings in
Spanish, offered in Settings as a draft for a native speaker to read over.
Translating it turned up places where the code put English words into a
translated sentence; those are fixed for German too, along with one that
wrote German into a trigger file.

## New

* **Español.** Settings > Interface language now offers *Español (Spanish) -
  borrador*. Every screen, button, finding and message is in Spanish (Spain),
  with the game's own words where the Spanish release has them (*séquito*
  for ancillaries, *turno* for a turn). It is marked a draft until a Spanish
  speaker has read it; anything that reads wrong is worth reporting. Mod
  content, unit names and file names stay as the mod has them.

## Fixed

* **The trigger editor wrote its joiner in your language.** With the
  interface in German, choosing *oder* between two conditions wrote `oder`
  into the trigger file instead of `or`. The joiner is now always written as
  the file spells it, whatever the interface language.

* **No English left inside translated sentences.** Nearly thirty messages
  took a word from the code in English (a plural ending, "wider", "summer or
  winter", "(nobody)", a module name). Each is now a whole sentence or a
  translated word in every language.

* **German is complete again.** The eight strings the transfer fixes of
  v2.4.2 added are in German.

* **My Changes no longer goes blank** when it is reopened before it has
  finished reading the first time.
