"""Shared by kf_job.py and kf_objects.py (inside Blender): the settings a bake
runs with, and writing its progress."""
import json
import math
from pathlib import Path


def writer(folder: Path):
    def write(name, data):
        temp = folder / (name + ".tmp")
        temp.write_text(json.dumps(data), encoding="utf-8")
        temp.replace(folder / name)
    return write


def bake_settings(kt, scene, overrides):
    """Automatic Bake's settings (the recommended ones), with Manual Bake's
    where ``overrides`` sets them, each checked against the add-on's own
    property (its items, its limits; angles come in degrees). The World they
    name is set on the scene."""
    settings = kt.recommended_settings(scene.keyforce)
    props = scene.keyforce.bl_rna.properties
    for key, value in (overrides or {}).items():
        prop = props.get(key) if key in kt.RECOMMENDED_KEYS else None
        if prop is None:
            continue
        if prop.type == "ENUM":
            if value in {item.identifier for item in prop.enum_items}:
                setattr(settings, key, value)
        elif prop.type == "BOOLEAN":
            setattr(settings, key, bool(value))
        elif prop.type in ("INT", "FLOAT"):
            value = math.radians(float(value)) if prop.subtype == "ANGLE" else float(value)
            value = min(prop.hard_max, max(prop.hard_min, value))
            setattr(settings, key, int(round(value)) if prop.type == "INT" else value)
    kt.apply_world(settings)
    return settings


def run_steps(steps, write, share=(0.0, 1.0)):
    """The bake's generator to its end, its progress written as it goes
    (scaled into ``share``); returns its results."""
    lo, hi = share
    while True:
        try:
            fraction, status = next(steps)
        except StopIteration as stop:
            return stop.value
        write("progress.json", {"fraction": lo + (hi - lo) * fraction, "status": status})
