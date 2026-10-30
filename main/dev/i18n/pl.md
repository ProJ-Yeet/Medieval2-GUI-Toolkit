# Polish (pl)

Phase 88i completed as a draft on 2026-10-28. All 9,633 English IDs are
translated, including 379 plural objects.

**Pulled 2026-10-30, not shipped** (the user: "dont ship polish for now"). An
audit found the machine draft unfit, so the catalogue is back in
`dev/i18n/pl.json`, not offered. It needs a real translation pass before
`--promote`.
Source hashes remain in `dev/i18n/pl.source.json`.

Use concise imperative buttons and direct, helpful instructions. Follow the
Polish termbase, allowing normal inflection. Preserve engine keywords,
filenames, paths, code examples, placeholders and product names exactly.
Use one/few/many/other plural forms; 21 takes many, 22 takes few and fractions
use other. Explicit zero forms are retained where the English supplies them.

This is a machine-assisted draft with direct corrections, not a native-speaker
reviewed translation. Native review remains pending. See `pl-review.md` for
provenance, verification, limitations and exact glossary exceptions.

Continue future updates through the checked merger:

```text
python dev/checks/i18n_todo.py pl
python dev/checks/i18n_todo.py pl --merge ANSWER.json
python dev/checks/i18n_termbase.py pl
```

No release was cut. Saved language preferences and mod files were not changed.
