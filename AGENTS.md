# Standing working preferences

- Check live Codex account usage at task start, before substantial work or
  delegation, and at work checkpoints. Check more frequently below 60% remaining
  in the five-hour window.
- At 50% or less remaining in the five-hour window, stop starting new work,
  checkpoint and stop any subagents, save a clear handoff, and pause for the user.
  Recheck usage before resuming. Do not spend credits or reset limits automatically.
- These thresholds apply to the five-hour window only, not weekly usage. Checks
  are periodic and account-wide; do not promise an exact continuous cutoff. If
  live limits are unavailable, report that limitation.

## Mark changes for Claude

- Whenever Codex changes this repository, add or update a dated entry in
  `main/docs/CODEX_HANDOFF.md` before finishing or pausing.
- Record what changed and why, affected files, checks actually run and their
  results, and any remaining work or limitations. Distinguish verified behavior
  from assumptions. State commit/release status without implying either happened.
- Preserve previous entries and other contributors' work. The handoff is a change
  record for Claude, not a replacement for STATE.md, ROADMAP.md, or RELEASE.md.

## Active EDB/sheets run override (2026-11-06)

For the implementation run authorized by "go past guard and work till 90% usage
is gone", the user explicitly replaces the 50%-remaining pause with a stop at
90% used (10% remaining) in the five-hour window. Check periodically and more
frequently below 60% remaining, checkpoint each phase and stop by the new limit.
Do not reset limits or spend credits. This is an exception for this authorized
run/its continuations; the normal standing threshold applies to unrelated work.
The user authorized progressing through the EDB/sheet phases in sequence during
this run, with verification and a handoff at phase boundaries.
