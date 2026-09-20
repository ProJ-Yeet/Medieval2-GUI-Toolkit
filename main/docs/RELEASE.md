# RELEASE - the rules for cutting one

> The single prose copy of how a release is done here. These rules were split
> out of `HANDOFF.md` on 2026-09-13, verbatim; that file is now
> `HANDOFF_ARCHIVE.md` and holds the stage-by-stage history only.
>
> **The live numbers are not here.** Which version is current, which beta is
> current, and which line a phase goes out on live in `STATE.md` under
> *THE TWO RELEASE LINES*. This file is the procedure and the reasoning; that
> one is the state.

## STRICT RULES — read these before cutting a release

These are not guidance. Each one is here because it was got wrong repeatedly, and
each cost the user real time cleaning up after it.

### 1. "release" / "subrelease" means DO the release. All of it.

When the user says **release** or **subrelease**, that is the instruction — not
an opening for a confirmation question. There is nothing to check back about.

**SUSPENDED 2026-09-12: somebody has to say it.** The user, right after Phase
29 was cut: *"from now on unless i mention it dont move to releasing it and
just commit to master"*. A session now ends at **commit to master** - no build,
no zip, no tag, no `gh release create`, no Discord post - and says in one
clause that the work is committed and not released.

This is the second suspension. The first (2026-09-11, hold everything for the
end of the roadmap) was spent by the end-of-roadmap cut on 2026-09-12; the
2026-09-09 rule came back for one session, Phase 29 went out under it as v2.3.2
and beta 2026-09-12c, and it was suspended again the same day. **Do not read
2026-09-09 as live again unless the user revives it in as many words.**

**Everything below still applies the moment they do say it.** The change picks
the lines: work that touches nothing outside the campaign map is **the beta
alone** - do not cut a 2.x that carries no visible difference - and anything
touching the rest of the toolkit is a subrelease, which is both lines.
`STATE.md`'s two-release-lines section is where the current numbers live.

Carry out every step, in order, and report at the end:

1. bump `__version__` in `unittransfer/__init__.py`
2. write `docs/releases/RELEASE_<x>_<y>_<z>.md` in the voice of the ones before it
3. update `STATE.md` (the `_Updated:_` header line and the **Next up** section)
   and `README.md` where behaviour changed
4. run the suite
5. `python dev/release/build_release.py --version v<x.y.z>`
6. **verify the zip** — size, and that `vanilla_ui/` is in it (see rule 2)
7. commit
8. **upload it** — `gh release create v<x.y.z> <zip> --title … --notes-file …`.
   The release is not done until the artefact is on GitHub.
9. delete the previous build out of `dist/` — see rule 3

Do not stop after the build and wait to be told to publish.

### 2. NEVER ship a release without `vanilla_ui/`

**v2.1.1, 2.1.2, 2.1.3 and 2.1.4 all went out without it** — ~19 MB instead of
~51 MB — because bundling it was an opt-in flag (`--with-vanilla-ui`) that was
forgotten four times running. Buildings mode falls back to that art for every
icon a mod does not ship, which is most of them, so those releases looked broken
to whoever unzipped them.

As of v2.1.5 the build ships it **by default** (`BUNDLED_DIRS` in
`dev/release/build_release.py`), a missing `vanilla_ui/` folder is a hard `SystemExit`, and
`assert_bundled()` reads the finished zip back and refuses to hand over a file
that does not contain it. `--no-vanilla-ui` exists for a deliberately slim build;
**never pass it for a release.**

Sanity check by eye as well as by code: **a portable release zip is ~50–55 MB.**
If the build prints ~19 MB, the UI is missing and the artefact is wrong.

### 3. Don't hoard builds in `dist/`

`dist/` is gitignored and every build is reproducible with
`python dev/release/build_release.py --version v<x.y.z>`. Delete the previous version's
folder and zip as each new one lands, rather than letting four of them sit there
at 19–54 MB each.

## Three traps the steps above do not spell out

These were carried in a memory file rather than here until 2026-09-13, and that
copy had gone stale on the paths. This is the corrected version.

**Check `gh release list` FIRST.** `__version__` and the newest
`docs/releases/RELEASE_*.md` are the version that already **shipped**, not the
one being cut. v2.1.6 was tagged and uploaded hours before the next fix landed,
and notes written into `RELEASE_2_1_6.md` would have gone nowhere.

**Merge and push `master` before tagging.** `gh release create` with no
`--target` tags the **default branch**, so a release cut off an unmerged branch
tags a commit that does not contain the work, and it fails silently. It happened
on 2026-09-09: v2.2.2 and beta-2026-09-09 both tagged `25908fd`, three days old,
with no `guilds.py` or `namekeys.py` in it. The zips were right, because they are
built from the working tree, so nothing looked wrong until the releases page put
an older beta above both.

**Verify the tag points at the right commit**, as the last step:

```
gh api repos/ProJ-Yeet/Medieval2-GUI-Toolkit/git/ref/tags/<tag> -q .object.sha
```

against `git rev-parse HEAD`. A tag already pushed to the wrong commit is moved
with `gh api -X PATCH .../git/refs/tags/<tag> -f sha=<right> -F force=true`,
which leaves the release, its notes and its uploaded zip untouched.

**Why that last one matters:** the releases page sorts by the **tag's commit
date**, not the publish date. A release tagged at an old commit sinks down the
page under things cut before it, which is the symptom that exposes a missed
merge.

The repo is `ProJ-Yeet/Medieval2-GUI-Toolkit`. The release title's exact
spelling is its own trap and is recorded in memory as
`release-title-is-m2-gui-kit`: "M2 GUI-Kit V2.2.0", hyphenated, capital V, and
it was got wrong on v2.2.0.


## Where the rest of it lives

- `STATE.md`, *THE TWO RELEASE LINES* - the current 2.x, the current beta, and
  which of the two a given phase goes out on.
- `.claude/agents/release-check.md` - the agent that verifies a cut against
  these rules, before the build, after the build and after the upload. It cites
  this file rather than restating it.
- `docs/releases/` - every release's own notes, which are the voice to copy.
- `dev/release/build_release.py` - the build itself, and `BUNDLED_DIRS` is
  where rule 2 is enforced in code.
