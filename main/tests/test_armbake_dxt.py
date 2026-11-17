"""The bake's DXT5 encoding keeps a painted emblem's edge clean.

    python -m tests.test_armbake_dxt

Nothing installed is needed. Saturated red paint on near-black cloth is the
hardest case for DXT: a 4x4 block on the edge holds red, black and the weave.
Pillow's quick encoder broke such edges into ragged steps with dark specks in
game (Black Numenor capes and shields, 2026-11-17); the bundled nvcompress
searches each block's colours and keeps them.

1. a red stroke's edge survives encoding (mean error on the edge pixels)
2. the whole chain is DXT5 with one level per halving down to 1x1
3. alpha stays on or off where the art has it on or off
"""
import io
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unittransfer import armbake, sprites  # noqa: E402

ok = []


def check(name, cond):
    ok.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + name)


rng = np.random.default_rng(7)
N = 128
cloth = 18 + rng.integers(0, 22, (N, N))                       # near-black weave
img = np.dstack([cloth, cloth, cloth, np.full((N, N), 255)]).astype(float)
yy, xx = np.mgrid[0:N, 0:N]
dist = np.abs((yy - 0.6 * xx - 20) / np.hypot(1, 0.6))          # a slanted stroke
paint = np.clip(6.5 - dist, 0, 1)[..., None]                    # 1 px soft edge
red = np.array([138, 16, 18, 255], float) * (0.9 + 0.2 * rng.random((N, N, 1)))
img = img * (1 - paint) + red * paint
img[100:, :20, 3] = 0                                           # a torn hole
art = img.round().astype(np.uint8)

dds = armbake.dds_with_mipmaps(Image.fromarray(art, "RGBA"))
dec = np.asarray(Image.open(io.BytesIO(dds)).convert("RGBA")).astype(int)
edge = (paint[..., 0] > 0.05) & (paint[..., 0] < 0.95) | (np.abs(dist - 6.5) < 2)
err = np.abs(dec[..., :3] - art[..., :3].astype(int))[edge].mean()
print(f"  edge error {err:.2f} (nvcompress {'bundled' if sprites.NVCOMPRESS.is_file() else 'MISSING'})")
check("a red stroke's edge on black cloth survives DXT5 (mean edge error under 5)", err < 5)

four_cc = dds[84:88]
mips, = struct.unpack_from("<I", dds, 28)
size = 128 + sum(max(1, (N >> i + 2)) ** 2 * 16 for i in range(8))   # 128 .. 1: eight levels
check("DXT5, eight levels from 128 to 1, and nothing more", four_cc == b"DXT5" and mips == 8 and len(dds) == size)
check("alpha is on and off where the art has it", ((dec[..., 3] > 127) == (art[..., 3] > 127)).all())

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
