# dev/

Scripts for working **on** the toolkit. None of this ships: the release zip
carries `app.py`, `transfer_cli.py`, `unittransfer/`, `web/`, `vendor/` and the
vanilla art, and nothing else.

They used to live in a folder called `tools/`, next to `vendor/nvtt/` - which
meant every release zip carried seven developer scripts along with the one
binary the tool actually needs at runtime, because the build shipped the folder
whole. Splitting them is what stopped that.

Each script is standalone: run it with the repo's Python, from anywhere.

## release/ - what goes out

| | |
|---|---|
| `build_release.py` | Builds the shareable zip: the tool plus Python's embeddable runtime with Pillow in it, so the person you send it to installs nothing. Reads `Launch-Medieval2-GUI-Toolkit.bat` and `Install-Dependencies.bat` from the top of the repo and writes them into the zip's flat layout. Verifies the finished archive really contains the vanilla art before handing it over. |
| `pack_vanilla_ui.py` | Turns ~300 MB of TGA unpacked from the game's own `.pack` files into `main/vanilla_ui/`: deduplicated lossless WebP, about six times smaller. That output is what is committed and what ships; the raw input stays local. |

```bash
python main/dev/release/build_release.py --version v2.2.0
python main/dev/release/pack_vanilla_ui.py unpackaded_vanilla_ui main/vanilla_ui
```

## reference/ - the saved modding material, and what is made from it

`main/Reference/` holds several gigabytes of saved TWCenter tutorials, guides
and tool dumps, kept locally to read and not ours to redistribute. These three
are what turn it into something the repo can use.

| | |
|---|---|
| `twc_index.py` | Walks the archive and writes `Reference/TWCenter/INDEX.md` - which is the one part of it that IS committed, because it is ours, it is small, and it is what a later phase greps to find the tutorial for a file format. |
| `upstream_sync.py` | Fetches the upstream editor this toolkit takes reference from, reports what changed, and records the disposition in `docs/upstream/PORT_MANIFEST.json` and `docs/upstream/SYNC_LOG.md`. Run it before every sub-phase. |
| `trigger_vocab.py` | Reads the Docudemons spreadsheet out of the archive and generates `unittransfer/data/trigger_vocab.json`, the vocabulary the traits and ancillaries editors validate against. |

## docs/ - the pictures the README shows

| | |
|---|---|
| `screenshots.py` | Starts the toolkit on a port of its own, drives a headless Chromium through each major screen, and writes a PNG per screen into `main/docs/images/`. Reads only: no mod is written to. Needs `pip install playwright` and `python -m playwright install chromium`. |

```bash
python main/dev/docs/screenshots.py --mod Third_Age_Reforged
python main/dev/docs/screenshots.py --only home bmdb-3d     # just these two
```

Re-run it after anything that changes a screen. A README carrying a picture of a
version that no longer exists is worse than one carrying no picture, because a
reader cannot tell which they are looking at.

## checks/ - holding the repo to its own standards

| | |
|---|---|
| `prose_check.py` | Reads the repository's own prose, in comments, docstrings and Markdown, and reports the habits this project has decided against. |

## diagnose/ - when a file will not read

| | |
|---|---|
| `meshdump.py` | Decodes one `.mesh` and prints what is in it: vertices, groups, bones, UV ranges. The first thing to reach for when the 3D viewer answers with the decoder's error instead of a model. |
