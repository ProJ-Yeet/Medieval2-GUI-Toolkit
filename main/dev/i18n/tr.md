# Turkish (tr)

Phase 88l started 2026-10-28 after Simplified Chinese, on the user's request.

## Workflow

Keep the partial draft in dev/i18n/tr.json. Export current missing/stale IDs
with i18n_todo.py tr --batch, translate bounded batches, and merge using
--merge. Resolve every refusal. Source hashes are maintained by the merger.
Do not promote until the whole catalogue passes, no hashes are stale, and
the required desktop/narrow screen review is complete.

## Style

- Use clear Turkish for Medieval II modders, with short imperative buttons
  (Ekle, Kaydet, Kapat). Prefer impersonal instructions or polite plural
  imperatives for longer guidance.
- Follow the termbase: birim, fraksiyon, mod, kampanya, yerleşim yeri,
  savaş modeli, strateji modeli, iskelet, doku, özellik, yuva, günlük.
  The game term ancillary and campaign script retain the glossary spelling.
- Preserve literal file names, paths, keywords, HTML attributes, placeholders,
  product names and symbols. Explain literal tokens in Turkish around them.
- Preserve Turkish dotted/dotless I and use natural suffixes. Never attach a
  guessed suffix to unknown names or paths: use a colon or restructure.
- Turkish plural objects require one/other. Numerals take a singular noun:
  both forms can read {count} mod or {count} öğe.
- Keep unknown placeholders grammatically independent. Boot error fragments
  are concatenated in a fixed order; check the whole assembled sentence.
- Draft until reviewed by a Turkish-speaking Medieval II modder.

## First checkpoint, 2026-10-28

243/9,633 entries translated; 9,390 missing, zero stale or extra.
Complete namespaces: app (67), boot (7), common (85), home (82), i18n (2).
All translated entries pass the full checker against their English source.
Both plural objects preserve one/other and use singular nouns after counts.
Boot fragments checked against their join order in web/js/boot.js.

Source/answer: .cache/tr-foundation.json and .cache/tr-foundation-answer.json.
Final checked merge accepted all 243 with zero refusals. Initial refusals
were Turkish consonant alternations, now accepted by narrowly expanded stems:
record kayıt|kayd (kaydı), save kaydet|kayded (kaydedildi).
The preferred terms themselves are unchanged. Termbase tests: 27/27.

Exact glossary exceptions: app.shared_cards_title uses tiles as UI cards,
home.mounted_pack means attaching an archive rather than a riding animal,
home.pick_your_medieval_ii_folder_it preserves the literal mods folder name.

Next: export settings (174), then core, transfer, editor and edrecruit.
The partial catalogue remains outside Settings. No Turkish UI review,
promotion, native review or release is claimed. Five-hour usage at checkpoint:
90% remaining; the user explicitly authorized going past the guard this run.
