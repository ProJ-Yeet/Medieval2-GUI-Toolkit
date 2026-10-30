# Polish (pl): repair pass complete, 2026-10-30

The repaired catalogue remains an unoffered draft in `dev/i18n/pl.json`, under
the user's earlier instruction not to ship Polish. No release or promotion was
made. The translation repair and direct semantic review are complete; this is
not native-speaker certification.

Coverage: 9,739/9,739 IDs, including 382 plural objects; zero missing, stale or
extra IDs. All IDs and plural forms received a direct semantic read. Three
parallel reviewers covered disjoint groups of 3,044, 3,070 and 2,603 IDs. The
remaining 1,016 IDs received the primary editor's pass and an independent audit;
six final UI-discovered entries were authored and checked separately.

4,875 IDs differ from the parked draft. This includes literal/format repairs,
semantic rewrites and 106 newly catalogued messages, rather than 4,875 wholly
new translations. The previous bulk machine translation was not trusted merely
because coverage and automated checks were clean.

Use concise Polish buttons and complete explanatory sentences. Preserve file
paths, code, engine keywords, product names, placeholders and internal keys.
Use one/few/many/other (and explicit zero where provided). Count-label wording
is allowed when it stays grammatical for all counts. The termbase is authoritative;
record narrowly justified alternate senses in `_exempt`, not broad bypasses.

Future edits go through the checked merger. Run from `main/`:

```text
python dev/checks/i18n_todo.py pl
python dev/checks/i18n_integrity.py pl
python -m tests.test_i18n_integrity
python -m tests.test_termbase
python -m tests.test_i18n
python -m tests.test_web_modules
```

For the full glossary check, pass `i18n_todo.target('pl')` to
`i18n_termbase.check_catalogue`; the termbase CLI alone checks shipped catalogues.
Source hashes live in `dev/i18n/pl.source.json`. Keep this catalogue parked until
the user changes the no-shipping instruction. See `pl-review.md` for evidence,
functional fixes and remaining limits.
