"""Texture-only PBR bake: a lit colour texture from any PBR texture set.

    python -m tests.test_pbrbake

Nothing installed is needed: the maps are made here.

1. the settings: defaults, and every number held inside its range
2. names: every common naming of a set's maps is found, from any one of them
3. the light: ambient alone is even; the key light brightens the side of a
   bump facing it; AO darkens; metal takes its colour from its reflection
4. the maps: separate and packed metal/roughness give the same answer;
   opacity becomes the alpha; emission adds light
5. normal green: a map named OpenGL is flipped, DirectX is not, else the setting
6. files: <name>_lit.png written beside the colour map; a preview writes nothing
"""
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unittransfer import pbrbake  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


S = 32


def flat(r, g=None, b=None, a=255):
    img = np.zeros((S, S, 4), np.uint8)
    img[..., 0] = r
    img[..., 1] = r if g is None else g
    img[..., 2] = r if b is None else b
    img[..., 3] = a
    return img


def lum(img):
    return img[..., :3].astype(float).mean()


NO_KEY = {"key": False}

print("1. settings")
d = pbrbake.settings_of(None)
check("defaults", d["ambient"] == 0.7 and d["key"] and not d["flip_green"])
c = pbrbake.settings_of({"ambient": 99, "height": -5, "shine": "x"})
check("clamped and repaired", c["ambient"] == 2.0 and c["height"] == 5.0 and c["shine"] == 1.0)

print("2. names")
cases = {
    "Helmet_BaseColor": ("helmet", "colour"), "helmet-normal": ("helmet", "normal"),
    "helm_d": ("helm", "colour"), "helm_s": ("helm", "spec"), "helm_n": ("helm", "normal"),
    "Sword_Metallic": ("sword", "metal"), "Sword_Roughness": ("sword", "rough"),
    "rock_ORM": ("rock", "orm"), "rock_AO": ("rock", "ao"), "rock_Normal_GL": ("rock", "normal"),
    "ShieldAlbedo": ("shield", "colour"), "cape_opacity": ("cape", "opacity"),
    "plain": ("plain", None), "d": ("d", None),
}
for stem, want in cases.items():
    got = pbrbake.split_name(stem)[:2]
    check(f"{stem} -> {want}", got == want)
with tempfile.TemporaryDirectory() as t:
    t = Path(t)
    for n in ("Helmet_BaseColor.png", "Helmet_Normal.png", "Helmet_Roughness.png", "Helmet_Metallic.tga",
              "Helmet_AO.png", "Other_BaseColor.png", "Helmet_notes.txt"):
        (t / n).write_bytes(b"x")
    m = pbrbake.find_maps(str(t / "Helmet_Roughness.png"))
    check("a set found from any of its maps", sorted(m) == ["ao", "colour", "metal", "normal", "rough"]
          and Path(m["colour"]).name == "Helmet_BaseColor.png")
    (t / "statue.png").write_bytes(b"x")
    check("an unmarked file is the colour", pbrbake.find_maps(str(t / "statue.png")) == {"colour": str(t / "statue.png")})

print("3. light")
grey = flat(128)
amb = pbrbake.bake({"colour": grey}, NO_KEY)
check("ambient alone is even", amb[..., :3].std() == 0 and lum(amb) > 0)
check("alpha kept", (amb[..., 3] == 255).all())
lit = pbrbake.bake({"colour": grey}, {})
check("the key light adds light", lum(lit) > lum(amb))
# a normal map leaning to the right on the left half, to the left on the right half
nm = flat(128, 128, 255)
nm[:, :S // 2, 0] = 200
nm[:, S // 2:, 0] = 56
side = pbrbake.bake({"colour": grey, "normal": nm}, {"direction": 90, "height": 30})   # light from the right
check("the side facing the key light is brighter", lum(side[:, :S // 2]) > lum(side[:, S // 2:]))
dark = pbrbake.bake({"colour": grey, "ao": flat(60)}, {})
check("AO darkens", lum(dark) < lum(lit))
off = pbrbake.bake({"colour": grey, "ao": flat(60)}, {"ao": 0})
check("AO amount 0 ignores it", (off == lit).all())
red = flat(200, 40, 40)
metal = pbrbake.bake({"colour": red, "metal": flat(255), "rough": flat(60)}, {})
check("metal keeps its colour", metal[..., 0].mean() > 2 * metal[..., 1].mean())
nonmetal = pbrbake.bake({"colour": red, "metal": flat(0), "rough": flat(60)}, NO_KEY)
check("never black under ambient", nonmetal[..., :3].max() > 0)

print("4. maps")
separate = pbrbake.bake({"colour": red, "metal": flat(255), "rough": flat(60), "ao": flat(200)}, {})
orm = pbrbake.bake({"colour": red, "orm": flat(200, 60, 255)}, {})
spec = pbrbake.bake({"colour": red, "spec": flat(255, 195, 200)}, {})
mr = pbrbake.bake({"colour": red, "mr": flat(0, 60, 255), "ao": flat(200)}, {})
check("ORM packed = separate maps", (orm == separate).all())
check("Bannerlord _s (gloss) = separate maps", np.abs(spec.astype(int) - separate).max() <= 1)
check("metallicRoughness + AO = separate maps", (mr == separate).all())
op = pbrbake.bake({"colour": grey, "opacity": flat(64)}, {})
check("opacity becomes the alpha", (op[..., 3] == 64).all())
glow = pbrbake.bake({"colour": grey, "emit": flat(100)}, {})
check("emission adds light", lum(glow) > lum(lit))
big = pbrbake.bake({"colour": grey, "normal": np.asarray(Image.fromarray(nm).resize((S * 2, S * 2)))},
                   {"direction": 90, "height": 30})
check("maps of another size are fitted", big.shape == grey.shape)

print("5. normal green")
check("_normal_gl flipped", pbrbake.normal_flip("x/rock_normal_gl.png", False))
check("_normal_dx not flipped, whatever the setting", not pbrbake.normal_flip("x/rock_normal_dx.png", True))
check("_n follows the setting", pbrbake.normal_flip("x/helm_n.png", True) and not pbrbake.normal_flip("x/helm_n.png", False))

print("6. files")
with tempfile.TemporaryDirectory() as t:
    t = Path(t)
    Image.fromarray(grey).save(t / "Helmet_BaseColor.png")
    Image.fromarray(nm).save(t / "Helmet_Normal.png")
    Image.fromarray(flat(60)).save(t / "Helmet_Roughness.png")
    Image.fromarray(grey).save(t / "loose.png")
    r = pbrbake.bake_files([str(t / "Helmet_Normal.png"), str(t / "Helmet_BaseColor.png"), str(t / "loose.png")], {})
    names = sorted(Path(b["path"]).name for b in r["baked"])
    check("one file per set, named after it", names == ["Helmet_lit.png", "loose_lit.png"])
    check("the maps it used are listed", sorted(r["baked"][0]["maps"]) == ["colour", "normal", "rough"])
    back = np.asarray(Image.open(t / "Helmet_lit.png").convert("RGBA"))
    check("what was written is the bake", back.shape == grey.shape and lum(back) != lum(grey))
    (t / "Helmet_lit.png").unlink()
    pv = pbrbake.bake_files([str(t / "Helmet_BaseColor.png")], {}, preview=True)
    check("a preview writes nothing and returns an image",
          not (t / "Helmet_lit.png").exists() and pv["baked"][0]["image"].startswith("data:image/png;base64,"))
    Image.fromarray(nm).save(t / "only_normal.png".replace("only_normal", "lonely_n"))
    sk = pbrbake.bake_files([str(t / "lonely_n.png")], {})
    check("a set with no colour map is skipped", sk["skipped"] and sk["skipped"][0]["why"] == "no_colour")

print(f"\n{sum(ok)}/{len(ok)} passed")
sys.exit(0 if all(ok) else 1)
