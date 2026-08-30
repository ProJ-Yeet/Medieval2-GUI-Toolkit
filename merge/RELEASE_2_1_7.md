# v2.1.7

Opens two mods whose `battle_models.modeldb` the toolkit had been refusing to
read, and stops it naming the wrong number when a modeldb really is damaged.

## Fixed

* **An attachment's sprite may be a sprite.** The fourth field of an attachment
  texture group is a bare `0` — meaning no sprite — on very nearly every entry of
  every mod, and the reader had been told that 0 was the *only* thing that field
  could hold. Thera_Redux and BOTET each write a real `unit_sprites/....spr`
  there, so both mods were refused outright, and the sentence asked their owner to
  delete a line that was doing its job.

  A name that fills exactly the characters its length claims and then stops on
  whitespace is now read as the name it is, and travels with the unit like any
  other file. Read that way both mods run to the end of the file and come back out
  byte for byte, which is the only reading under which they do.

  The thing that is genuinely broken in that slot still is. A digit left glued to
  the 0 by a hand edit — `... .texture 01`, what deleting a faction's skin leaves
  behind — is refused at the character with the fix in the sentence, because
  reading it as a length eats the next field and kills the read two lines further
  down on a word that is perfectly fine where it sits.

* **A wrong length is no longer blamed on an honest count.** When the read fell
  out of step inside a texture list, the message led with the list's count. That
  is the right answer when a faction's skin was deleted without lowering it, and
  the wrong one for BOTET's `mount_elephant_rocket`, where the count of 2 is
  honest and a normal map's length is written 64 for a 61-character name. Both
  faults land the reader in the same place, and following that advice would have
  deleted a texture group that was never the problem.

  A length the reader actually watched overrun its own line now leads instead,
  naming the line that number sits on and how long the rest of that line measures
  — so the message says "line 4625, that 64, the rest of the line is 61" rather
  than sending you to a count that was never wrong. The count still leads when it
  is the one at fault.
