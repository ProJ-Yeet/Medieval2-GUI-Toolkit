# Portable builder projects

Phase 105 adds data-only import/export to the Guided designer. Import project
or presets JSON is available before choosing a profile. A successful import
replaces the working design, with normal designer Undo/Redo. Save draft uses
the existing per-mod sheet project store, revisions and source checks. Import
does not save, stage stats or write into a mod. The target unit stays the one
whose designer is open; a portable project cannot select an installed unit.

## Native version 1

The complete project file is exactly:

```json
{
  "schema": "m2-builder-project",
  "version": 1,
  "design": {}
}
```

`design` is the complete `m2-unit-design` v1 packet documented in
[UNIT_BUILDER_CONTRACT.md](UNIT_BUILDER_CONTRACT.md). It includes the explicit
profile/revision, original inputs, edited preset snapshots, input overrides,
native pins and metadata. JSON property order/indentation is not significant;
all packet values round-trip unchanged. Use native projects for lossless
toolkit save/load, including native profiles and additions upstream cannot use.

Preset files use `schema: m2-builder-presets`, `version: 1`, `profile` and
`presets`, with no other top-level keys. They merge supplied rows by family/ID
into a current design of the exact same profile/revision. Other rows and all
inputs/pins/metadata remain. They require an existing design. Unknown family
data is retained, not executed. Native projects and presets reject unknown
top-level keys so future data cannot silently disappear.

## Combat Reforged version 1 adapter

The source is lupinemaverick's Stainless Steel: Reforged Unit Builder revision
`d4ed9368d0db3da2000bc895e96f52a83b93cb67`, especially `projectFields`,
`exportProject`, `importProjectData` in `src/reforged.js`. Its credits include
MUG Unit Builder v1.5 / MUG Unit Creation Guide and work for King Siegfried.
See [source notes](upstream/SSR_UNIT_BUILDER.md) for permission and provenance.
Source was read as text from the existing pinned cache, never executed.

Accepted shape: `schema: combat-reforged-builder`, integer `version: 1`, object
`fields`, optional object `presets` and object `weapon_categories`. All source
JSON, including unknown properties and cached `unit`, is retained under
`design.metadata.upstream`. Cached `unit` never supplies calculated values.
Fields become explicit input overrides, including false and zero. Blank
selects resume inheritance; blank `sec_base_atk` explicitly disables the
secondary weapon. Legacy quality `Standard` normalizes to `Average`, matching
the upstream restore helper. Custom preset rows survive; top-level weapon
categories override corresponding nested category rows, matching upstream order.

No historical default migration scripts run. Import retains explicit values
and uses the toolkit's pinned calculator for supported fields. Original values
stay in metadata for inspection. Unknown fields, preset properties and custom
ability proposals are inert JSON. Unsupported known choices or invalid active
values are rejected before replacing the draft. This is interchange with the
toolkit's documented rules, not a claim of matching every upstream revision.

Upstream JSON export is offered for Combat Reforged profiles. It retains
unknown original top-level metadata, replaces `fields` with effective inputs
and emits the current presets/categories. It omits the stale cached `unit`.
An `m2_toolkit` extension stores the validated native packet without the raw
upstream copy; toolkit reimport restores native pins/metadata. Upstream ignores
that extension, so its own recalculation cannot honor native pins or toolkit
rule changes. Use the native file for an exact toolkit round trip.

## Output and failure semantics

- All five formats have Download and Copy actions: native project JSON,
  native presets JSON, upstream JSON, EDU preview and CSV. Clipboard failure
  leaves the draft intact and offers downloading through the normal buttons.
- EDU is the existing designer preview through `sheet_ops` and `edu`, with
  donor comments/untouched tuple members or detached scaffold placeholders.
  It is not a complete new-unit definition. This phase adds no donor planner,
  model/localization resolution or Apply action. Custom runtime proposals and
  `sp` are omitted by the existing contract. Engine upgrade values remain
  preview metadata, accompanied in the designer by the unit-card +1 note.
- CSV uses `sheet_interchange.write_csv`, the same value writer used by sheets,
  with canonical `id` and native column names and JSON list cells. Existing-unit
  exports keep the exact unit ID; detached exports use `builder_preview`, which
  must be mapped to a real identity before sheet import. Import CSV/XLSX through
  the sheets' existing mapping/preview/staging workflow. There is no second
  spreadsheet importer in the designer, and CSV cannot reconstruct a design.
- CSV quotes commas, quotes and newlines. Formula-like text beginning with
  `=`, `+`, `-` or `@` after whitespace receives a leading apostrophe. Finite
  numeric strings remain numbers. This deliberate escaping also applies to
  sheet CSV exports; the protective apostrophe is literal on CSV reimport.
- JSON is bounded to 1,000,000 characters, the design contract's depth/size
  limits and finite JSON values. Duplicate keys, unknown schemas and unsupported
  versions are refused. Both native and upstream imports validate the complete
  candidate with the contract/calculator before returning it. No project-store
  mutation occurs on import/export, even on failure.
- Failed requests retain the working and saved drafts. Imports that finish
  after another import, closing the designer, editing the design or changing
  the preset filter/selection are ignored or ask the user to retry. Typing and
  status updates never rebuild the active input. Export responses for changed
  designs are refused, preventing a stale download.

Automated coverage is fixture-only Python service/HTTP and Node VM tests in
`tests/test_builder_projects.py` and `tests/test_builder_projects_ui.js`.
Human browser checks remain: file picker, actual clipboard permissions,
downloaded file names/content, import Undo/Redo, narrow layout, keyboard use
and typing during delayed requests. No upstream browser or in-game parity is
claimed.
