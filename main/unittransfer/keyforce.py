"""Keyforce Tools' pre-rendered bake, run from the toolkit in a hidden Blender.

The bake (a lit colour texture per source texture, Cycles) is the Keyforce
Tools Blender add-on's own code, shipped in ``vendor/keyforce/`` and run
unchanged, so it looks exactly as the add-on bakes it. This module finds
Blender, starts one hidden, below-normal-priority Blender per job on
``vendor/keyforce/kf_job.py``, and reads back its progress and result:

* :func:`find_blender` - the ``blender_path`` setting, else the newest
  ``Blender Foundation/Blender <version>/blender.exe`` under Program Files;
* :func:`start` - a TpacTool gallery export folder, an LOD and a size in, a
  job id out; the textures land in ``<folder>/Pre-rendered`` unless told;
* :func:`status` - ``{running, fraction, status}`` while it runs, then
  ``{done, results}`` or ``{done, error}``; :func:`stop` kills it.

Not the Blender-free bake: :mod:`armlit` (project objects) needs no Blender.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from PIL import Image

from . import config
from . import i18n as _i18n

VENDOR = Path(__file__).resolve().parents[1] / "vendor" / "keyforce"
JOB_SCRIPT = VENDOR / "kf_job.py"
OBJECTS_SCRIPT = VENDOR / "kf_objects.py"
SIZES = (512, 1024, 2048, 4096)
OUT_NAME = "Pre-rendered"
CREATE_NO_WINDOW = 0x08000000
BELOW_NORMAL_PRIORITY_CLASS = 0x00004000

#: Manual Bake's settings the toolkit offers, in the add-on's own names and
#: defaults (``KeyforceSettings`` in keyforce_tools.py; a test holds the two
#: together): ``(key, kind, default, low, high, step, group)``. Angles are in
#: degrees here, radians in Blender. Blender checks every value again
#: against the add-on's own limits.
WORLDS = ("PREVIEW", "CITY", "COURTYARD", "FOREST", "INTERIOR", "NIGHT", "STUDIO", "SUNRISE", "SUNSET")
MATCHES = ("UV", "SHAPE", "EXACT")
ADVANCED = (
    ("world", "enum", "PREVIEW", WORLDS, None, None, "light"),
    ("bake_ambient", "float", 0.05, 0.0, 5.0, 0.01, "light"),
    ("bake_world", "float", 0.6, 0.0, 1.0, 0.01, "light"),
    ("bake_surround", "float", 1.0, 0.0, 20.0, 0.05, "light"),
    ("bake_surround_diffuse", "float", 0.0, 0.0, 1.0, 0.01, "light"),
    ("bake_tilt", "angle", 15.0, -45.0, 45.0, 1, "light"),
    ("bake_key", "float", 0.0, 0.0, 20.0, 0.05, "light"),
    ("bake_azimuth", "angle", 30.0, -180.0, 180.0, 1, "light"),
    ("bake_elevation", "angle", 50.0, -90.0, 90.0, 1, "light"),
    ("bake_soft", "angle", 40.0, 0.0, 180.0, 1, "light"),
    ("bake_shadows", "float", 1.0, 0.0, 1.0, 0.01, "light"),
    ("bake_floor", "float", 0.2, 0.0, 1.0, 0.01, "light"),
    ("bake_samples", "int", 32, 1, 4096, 1, "quality"),
    ("bake_margin", "int", 0, 0, 64, 1, "quality"),
    ("bake_denoise", "bool", True, None, None, None, "quality"),
    ("bake_indirect", "bool", True, None, None, None, "quality"),
    ("bake_view", "bool", True, None, None, None, "quality"),
    ("match", "enum", "UV", MATCHES, None, None, "parts"),
    ("precision", "int", 3, 1, 8, 1, "parts"),
    ("tolerance", "float", 10.0, 0.0, 50.0, 0.5, "parts"),
    ("into_tile", "bool", True, None, None, None, "parts"),
)


def settings_of(raw: Optional[dict]) -> dict:
    """Only the offered settings, each inside its range; the rest dropped
    (the add-on's recommended value is used for them)."""
    out = {}
    for key, kind, default, lo, hi, _step, _group in ADVANCED:
        if not raw or key not in raw:
            continue
        v = raw[key]
        try:
            if kind == "enum":
                if v in lo:
                    out[key] = v
            elif kind == "bool":
                out[key] = bool(v)
            elif kind == "int":
                out[key] = min(hi, max(lo, int(v)))
            else:
                out[key] = min(hi, max(lo, float(v)))
        except (TypeError, ValueError):
            pass
    return out


def schema() -> List[dict]:
    """ADVANCED for the page."""
    return [{"key": k, "kind": kind, "default": d, "low": lo, "high": hi, "step": st, "group": g}
            for k, kind, d, lo, hi, st, g in ADVANCED]


#: running and finished jobs: id -> {process, folder, out, log}
JOBS: Dict[str, dict] = {}


class KeyforceError(ValueError):
    pass


def _version(path: Path):
    m = re.search(r"Blender\s+(\d+(?:\.\d+)*)", str(path.parent.name))
    return tuple(int(x) for x in m.group(1).split(".")) if m else ()


def find_blender(setting: Optional[str] = None, roots: Optional[List[str]] = None) -> str:
    """The Blender to run: ``setting`` (or the ``blender_path`` setting) when
    that file is there, else the newest Blender under ``roots`` (Program
    Files by default). ``""`` when there is none."""
    if setting is None:
        setting = str(config.load_settings().get("blender_path") or "")
    if setting and Path(setting).is_file():
        return setting
    if roots is None:
        roots = [os.environ.get(k) for k in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)")]
    found = []
    for root in filter(None, roots):
        base = Path(root) / "Blender Foundation"
        if base.is_dir():
            found += [p for p in base.glob("Blender*/blender.exe") if p.is_file()]
    found.sort(key=_version)
    return str(found[-1]) if found else ""


def start(root: str, lod: int = 0, size: int = 2048, out: Optional[str] = None,
          blender: Optional[str] = None, settings: Optional[dict] = None, glb: bool = False) -> dict:
    """Start a hidden Blender baking the export folder ``root``: ``{job, out, blender}``.

    ``settings``: Manual Bake's (:data:`ADVANCED`), else the recommended ones.
    ``glb``: afterwards the meshes wear the baked textures (and the Medieval 2
    ``_m2_norm`` normal where there is one) and are written to
    ``<out>/<folder name>.glb``, for Armory Studio to import."""
    folder = Path(root or "")
    if not root or not folder.is_dir():
        raise KeyforceError(_i18n.msg("eng.keyforce.no_folder", "choose an existing export folder first"))
    lod, size = int(lod), int(size)
    if size not in SIZES:
        raise KeyforceError(_i18n.msg("eng.keyforce.bad_size", "size must be one of {sizes}",
                                      sizes=", ".join(map(str, SIZES))))
    exe = _blender(blender)
    target = Path(out) if out else folder / OUT_NAME
    work = Path(tempfile.mkdtemp(prefix="keyforce_job_"))
    key = _launch(exe, JOB_SCRIPT, work, {"root": str(folder), "lod": lod, "size": size, "out": str(target),
                                         "settings": settings_of(settings), "glb": bool(glb)}, {"out": str(target)})
    return {"job": key, "out": str(target), "blender": exe}


def _blender(blender: Optional[str]) -> str:
    exe = blender or find_blender()
    if not exe:
        raise KeyforceError(_i18n.msg("eng.keyforce.no_blender",
                                      "Blender was not found: install Blender 5.2, or set its path"))
    return exe


def _launch(exe: str, script: Path, work: Path, job: dict, keep: dict) -> str:
    """``job.json`` written into ``work``, one hidden, below-normal Blender
    started on ``script``; its job id. ``keep`` rides on the job."""
    (work / "job.json").write_text(json.dumps(job), encoding="utf-8")
    log = open(work / "log.txt", "w", encoding="utf-8", errors="replace")
    try:
        process = subprocess.Popen(
            [exe, "-b", "--factory-startup", "--python", str(script), "--", str(work / "job.json")],
            stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW | BELOW_NORMAL_PRIORITY_CLASS if os.name == "nt" else 0)
    finally:
        log.close()
    key = uuid.uuid4().hex[:12]
    JOBS[key] = dict(keep, process=process, folder=work)
    return key


#: what Blender reads itself, as the add-on does: these go to it as they are
BLENDER_READS = (".dds", ".png", ".tga", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp")


def _map_file(path: str, img: np.ndarray, decoded: Path, normal: bool = False) -> str:
    """The job's copy of a map, named as ``decoded`` (``c<k>``, ``_s``, ``_n``
    or ``_m2_norm``: what the add-on reads a map as): the source file itself
    when Blender reads that kind, so it is decoded exactly as in the add-on's
    own bake; else the toolkit's decoding of it (a game ``.texture``). A
    normal map other than a ``.dds`` is written decoded too: Blender puts a
    two-channel map's blue back only when it reads the ``.dds`` itself."""
    p = Path(path)
    if p.suffix.lower() in BLENDER_READS and p.is_file() and not (normal and p.suffix.lower() != ".dds"):
        target = decoded.with_suffix(p.suffix.lower())
        shutil.copyfile(p, target)
        return target.name
    Image.fromarray(_full_normal(img) if normal else img, "RGBA").save(decoded)
    return decoded.name


def _full_normal(img: np.ndarray) -> np.ndarray:
    """A two-channel normal map (BC5: red and green only, blue empty) with
    its blue put back: z from x and y, as Blender's own DDS reading gives it.
    A blue of 0 lit every face from the side and baked about three times too
    dark."""
    if img[..., 2].max() > 8:
        return img
    out = img.copy()
    x = img[..., 0] / 127.5 - 1.0
    y = img[..., 1] / 127.5 - 1.0
    z = np.sqrt(np.clip(1.0 - x * x - y * y, 0.0, 1.0))
    out[..., 2] = np.round((z + 1.0) * 127.5).astype(np.uint8)
    return out


def _bake_size(w: int, h: int) -> int:
    """The square bake for a texture: its longer side, as one of :data:`SIZES`."""
    side = max(w, h)
    return next((s for s in SIZES if s >= side), SIZES[-1])


def start_objects(project: dict, obj_ids, mod_of, settings: Optional[dict] = None,
                  blender: Optional[str] = None, image_of=None, out_dir: Optional[str] = None) -> dict:
    """Start a hidden Blender baking Armory Studio's objects with the add-on's
    bake, one lit texture per colour texture they wear (as
    :func:`armlit.bake_objects` does without Blender): ``{job, skipped}``.
    When it is done, :func:`status` gives ``baked`` in that function's shape."""
    from . import armbake, armlit, armory
    exe = _blender(blender)
    jobs, skipped, sheets = armlit.gather(project, obj_ids, mod_of, image_of or armbake.default_image_of)
    if not jobs:
        raise KeyforceError(_i18n.msg("eng.keyforce.nothing", "none of these objects wears a texture to bake"))
    work = Path(tempfile.mkdtemp(prefix="keyforce_objects_"))
    entries, keep = [], []
    for k, job in enumerate(jobs.values()):
        colour = sheets.image(job["path"])
        h, w = colour.shape[:2]
        maps = {"colour": _map_file(job["path"], colour, work / f"c{k}.png")}
        spec_path = armlit.sibling(job["path"], "s")
        spec = sheets.image(spec_path) if spec_path else None
        if spec is not None:
            maps["spec"] = _map_file(spec_path, spec, work / f"c{k}_s.png")
        normal = sheets.image(job["normal"]) if job["normal"] else None
        if normal is not None:
            # a Bannerlord _n is DirectX; the game's own normal sheets are read
            # as TpacTool's _m2_norm, as the add-on reads those
            bannerlord = Path(job["normal"]).stem.lower().endswith("_n")
            maps["normal"] = _map_file(job["normal"], normal,
                                       work / (f"c{k}_n.png" if bannerlord else f"c{k}_m2_norm.png"), normal=True)
            # what the export finds beside the lit sheet, as armlit writes it
            Image.fromarray(normal, "RGBA").save(work / f"n{k}.png")
        uv = np.concatenate(job["uv"]) / np.array([w, h], float)
        uv[:, 1] = 1.0 - uv[:, 1]
        np.savez(work / f"entry{k}.npz", pos=np.concatenate(job["pos"]), nrm=np.concatenate(job["nrm"]), uv=uv,
                 tris=np.array(job["tris"], np.int64), obj=np.array(job["obj"], np.int64))
        entries.append({"arrays": f"entry{k}.npz", "maps": maps, "size": _bake_size(w, h),
                        "name": Path(job["path"]).name})
        keep.append({"source": job["path"], "objects": job["objects"], "size": [w, h],
                     "normal": normal is not None, "spec": spec is not None})
    target = Path(out_dir) if out_dir else armory.SHEETS_DIR / "lit"
    key = _launch(exe, OBJECTS_SCRIPT, work, {"out": str(work / "out"), "entries": entries,
                                              "settings": settings_of(settings)},
                  {"out": str(target), "objects_of": keep, "skipped": skipped})
    return {"job": key, "skipped": skipped}


def _finish_objects(j: dict, result: dict) -> dict:
    """The object bake's PNGs moved beside the Armory's lit sheets, each at
    its source's size and named after it, its normal map beside it (the
    export looks for a sheet's normal there, as for armlit's)."""
    import hashlib
    target = Path(j["out"])
    target.mkdir(parents=True, exist_ok=True)
    baked = []
    for r in result.get("results") or []:
        k = r["entry"]
        info = j["objects_of"][k]
        src = Path(info["source"])
        tag = hashlib.blake2b((str(src).lower() + "|cycles|" + ",".join(str(i) for i in sorted(info["objects"])))
                              .encode("utf-8"), digest_size=4).hexdigest()
        out = target / f"{src.stem}_cycles_{tag}.png"
        im = Image.open(r["path"]).convert("RGBA")
        if list(im.size) != list(info["size"]):
            im = im.resize(tuple(info["size"]), Image.LANCZOS)
        im.save(out)
        if (j["folder"] / f"n{k}.png").is_file():
            shutil.copyfile(j["folder"] / f"n{k}.png", out.with_name(out.stem + "_norm.png"))
        baked.append({"source": info["source"], "path": str(out), "objects": info["objects"],
                      "spec": info["spec"], "normal": info["normal"]})
    return {"baked": baked, "skipped": j["skipped"]}


def _read(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def status(key: str) -> dict:
    """Where job ``key`` stands."""
    j = JOBS.get(key)
    if j is None:
        raise KeyforceError(_i18n.msg("eng.keyforce.no_job", "no such bake"))
    if "result" in j:
        return j["result"]
    progress = _read(j["folder"] / "progress.json") or {"fraction": 0.0, "status": "starting"}
    code = j["process"].poll()
    if code is None:
        return {"running": True, "out": j["out"], **progress}
    result = _read(j["folder"] / "result.json")
    if result is None:
        tail = ""
        try:
            tail = "\n".join((j["folder"] / "log.txt").read_text(encoding="utf-8", errors="replace").splitlines()[-8:])
        except OSError:
            pass
        result = {"error": _i18n.msg("eng.keyforce.stopped", "Blender stopped (exit code {code})", code=code),
                  "log": tail}
    if "objects_of" in j and "error" not in result:
        try:
            result = _finish_objects(j, result)
        except OSError as e:
            result = {"error": str(e)}
    result = dict(result, done=True, running=False, out=j["out"])
    j["result"] = result
    shutil.rmtree(j["folder"], ignore_errors=True)
    return result


def stop(key: str) -> dict:
    """Kill job ``key``; textures it already finished stay on disk."""
    j = JOBS.get(key)
    if j is not None and j["process"].poll() is None:
        j["process"].kill()
        j["process"].wait()
    return status(key) if j is not None else {"done": True}
