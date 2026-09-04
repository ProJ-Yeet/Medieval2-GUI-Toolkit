"""The campaign map's TGA layers, read and written as the game actually ships them.

Pillow decodes the pixels; **the 18-byte header is ours**. That split is the
whole point of this module, and it exists because of one field.

TWMapReader's ``Utils.writeTGA`` carries a field note that M2TW *crashed* on
descriptor byte ``0x18`` and on ``0x20``, and that ``0x08`` is what works. Its
author left both alternatives in the source as dead comments rather than delete
the evidence. Measured against DaC's real ``world/maps/base``::

    map_regions       type 10  32-bit  desc 0x08   510x487
    map_features      type 10  32-bit  desc 0x08   510x487
    map_trade_routes  type 10  24-bit  desc 0x00   510x487
    map_roughness     type 10  24-bit  desc 0x00  1020x974
    map_heights       type 10  32-bit  desc 0x08  1021x975
    map_climates      type 10  32-bit  desc 0x08  1021x975
    map_ground_types  type 10  32-bit  desc 0x08  1021x975
    map_fog           type 10  24-bit  desc 0x00  1021x975
    water_surface     type  2  24-bit  desc 0x20  1021x975, and a 1-byte ID field

Nine of the ten are run-length encoded (type 10), one is not, one carries a
top-left origin, one carries an ID field, and every one of them ends with the
26-byte TGA v2.0 footer. ``water_surface.tga`` goes further and carries a
495-byte v2.0 extension area between its pixels and that footer, pointed at by
an **absolute file offset** inside the footer - which means a layer whose
compressed size changes has to have that offset moved or the file it writes is
quietly broken. Demir's writer flattens all of that to uncompressed
24-bit ``0x00``: the pixels survive and the file the game reads is a different
file. So a layer written here goes back **in the shape it arrived in** - same
image type, same depth, same descriptor, same ID field, same footer - and the
only thing that changes is the pixels the user painted.

That promise is the shape and the pixels, and **not** byte-for-byte, because RLE
has more than one legal packing of the same row. Byte-for-byte is what usually
falls out of it - all ten of DaC's layers, and nine of vanilla's ten - and there
is one case in the wild where it does not: vanilla's ``map_fog.tga`` writes a
five-pixel literal packet where :func:`_rle_row` starts a run, so what comes
back out is 11,327 bytes against 12,009, pixel for pixel identical, and settled
(a second pass produces the same bytes again). Both files are valid TGA and the
engine reads either. Said here rather than left for somebody to find as a failing
test: the guarantee is the picture and the header, not the packing.

The other half of the split is orientation. TGA stores rows bottom-up unless
descriptor bit 5 says otherwise, and columns right-to-left if bit 4 is set.
Everything above this module works in **image coordinates** (0,0 top-left,
y down), so :func:`read` hands back an image already the right way up and
:func:`write` puts it back the way the header says. Pillow's own TGA writer
cannot emit bit 4 at all and drops the footer, which is the second reason the
header is ours.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image

#: id, colour-map type, image type, cmap first/len/depth, x/y origin, w, h, depth, descriptor
_HEADER = struct.Struct("<BBBHHBHHHHBB")
HEADER_SIZE = _HEADER.size          # 18
FOOTER_SIZE = 26
#: bytes 8..24 of a TGA v2.0 footer, then a full stop and a NUL
FOOTER_SIGNATURE = b"TRUEVISION-XFILE"
#: the footer's first two fields: absolute offsets to the extension area and the
#: developer directory, both zero when there is neither
_FOOTER_OFFSETS = struct.Struct("<II")

#: image types this module understands: uncompressed and RLE true-colour
TYPE_RAW = 2
TYPE_RLE = 10

#: what the game is known to be happy with, for a layer created from nothing
DEFAULT_DESCRIPTOR_32 = 0x08
DEFAULT_DESCRIPTOR_24 = 0x00


class TgaError(ValueError):
    """Not a TGA this module will touch, or a write that would corrupt one."""


@dataclass
class TgaInfo:
    """Every header field of one layer, so the file can be put back as it was."""

    image_type: int
    width: int
    height: int
    depth: int
    descriptor: int
    id_field: bytes = b""
    colour_map_type: int = 0
    colour_map_first: int = 0
    colour_map_length: int = 0
    colour_map_depth: int = 0
    x_origin: int = 0
    y_origin: int = 0
    #: everything after the pixels: extension area, developer directory and the
    #: 26-byte footer, carried verbatim
    trailer: bytes = b""
    #: where the trailer started in the file it came from, so the footer's
    #: absolute offsets can be moved when the pixels re-encode to a new length
    trailer_start: int = 0
    path: Optional[Path] = None
    #: file size when it was read, so a caller can report growth after a write
    size_bytes: int = 0

    @property
    def rle(self) -> bool:
        return bool(self.image_type & 8)

    @property
    def alpha_bits(self) -> int:
        return self.descriptor & 0x0F

    @property
    def top_origin(self) -> bool:
        """Rows run top-to-bottom (descriptor bit 5). Bottom-up when clear."""
        return bool(self.descriptor & 0x20)

    @property
    def right_origin(self) -> bool:
        """Columns run right-to-left (descriptor bit 4). Rare, and DaC has none."""
        return bool(self.descriptor & 0x10)

    @property
    def mode(self) -> str:
        return "RGBA" if self.depth == 32 else "RGB"

    @property
    def has_footer(self) -> bool:
        return (len(self.trailer) >= FOOTER_SIZE
                and self.trailer[-FOOTER_SIZE:][8:24] == FOOTER_SIGNATURE)

    @property
    def extension_bytes(self) -> int:
        """How much sits between the pixels and the footer. 495 on water_surface."""
        return max(0, len(self.trailer) - FOOTER_SIZE) if self.has_footer else 0

    def describe(self) -> str:
        """One line for a log or a warning - the shape, not the contents."""
        kind = "RLE" if self.rle else "uncompressed"
        return (f"{self.width}x{self.height} {self.depth}-bit {kind} "
                f"desc 0x{self.descriptor:02x}"
                + (" +footer" if self.has_footer else "")
                + (f" +{self.extension_bytes}b ext" if self.extension_bytes else "")
                + (f" +{len(self.id_field)}b id" if self.id_field else ""))


def probe(path: Path) -> TgaInfo:
    """Read the header, the ID field and the footer - never the pixels.

    Cheap enough to run over every layer just to check the size relationships,
    which is what :mod:`unittransfer.campmap` does before it decodes anything.
    """
    path = Path(path)
    try:
        size = path.stat().st_size
        with path.open("rb") as fh:
            head = fh.read(HEADER_SIZE)
            if len(head) < HEADER_SIZE:
                raise TgaError(f"{path.name}: too short to be a TGA")
            (id_len, cmap_type, img_type, cmap_first, cmap_len, cmap_depth,
             x0, y0, w, h, depth, desc) = _HEADER.unpack(head)
            id_field = fh.read(id_len) if id_len else b""
            trailer, trailer_start = b"", size
            if size >= HEADER_SIZE + FOOTER_SIZE:
                fh.seek(-FOOTER_SIZE, 2)
                tail = fh.read(FOOTER_SIZE)
                if tail[8:24] == FOOTER_SIGNATURE:
                    ext, dev = _FOOTER_OFFSETS.unpack(tail[:8])
                    # an extension area or developer directory sits between the
                    # pixels and the footer; the earliest of them is where the
                    # pixels stop
                    starts = [o for o in (ext, dev) if 0 < o <= size - FOOTER_SIZE]
                    trailer_start = min(starts) if starts else size - FOOTER_SIZE
                    fh.seek(trailer_start)
                    trailer = fh.read()
    except OSError as exc:
        raise TgaError(f"{path.name}: {exc}") from exc

    if img_type not in (TYPE_RAW, TYPE_RLE):
        raise TgaError(f"{path.name}: image type {img_type} is not a true-colour TGA")
    if depth not in (24, 32):
        raise TgaError(f"{path.name}: {depth}-bit is neither 24 nor 32")
    if cmap_type:
        raise TgaError(f"{path.name}: has a colour map, which no map layer does")
    if w <= 0 or h <= 0:
        raise TgaError(f"{path.name}: header says {w}x{h}")

    return TgaInfo(image_type=img_type, width=w, height=h, depth=depth,
                   descriptor=desc, id_field=id_field, colour_map_type=cmap_type,
                   colour_map_first=cmap_first, colour_map_length=cmap_len,
                   colour_map_depth=cmap_depth, x_origin=x0, y_origin=y0,
                   trailer=trailer, trailer_start=trailer_start,
                   path=path, size_bytes=size)


def read(path: Path) -> Tuple[Image.Image, TgaInfo]:
    """``(image, info)`` - the image in **image coordinates**, y down.

    Pillow honours both origin bits on the way in, so the image handed back is
    already the right way up whatever the header said; ``info`` remembers what
    it said so :func:`write` can undo it.
    """
    info = probe(path)
    try:
        with Image.open(path) as im:
            im.load()
            out = im.convert(info.mode)
    except (OSError, ValueError) as exc:
        raise TgaError(f"{Path(path).name}: {exc}") from exc
    if out.size != (info.width, info.height):
        raise TgaError(f"{Path(path).name}: header says {info.width}x{info.height}, "
                       f"decoded {out.size[0]}x{out.size[1]}")
    return out, info


def encode(image: Image.Image, info: TgaInfo) -> bytes:
    """The whole file as bytes, in the shape ``info`` describes.

    Kept separate from :func:`write` so a caller can size the result, hash it or
    hand it to a backup before anything on disk changes.
    """
    if image.size != (info.width, info.height):
        raise TgaError(f"image is {image.size[0]}x{image.size[1]}, "
                       f"header says {info.width}x{info.height}")
    if info.image_type not in (TYPE_RAW, TYPE_RLE):
        raise TgaError(f"cannot write image type {info.image_type}")

    src = image if image.mode == info.mode else image.convert(info.mode)
    raw = "BGRA" if info.depth == 32 else "BGR"
    stride = info.depth // 8
    pixels = src.tobytes("raw", raw)
    row_bytes = info.width * stride

    rows = [pixels[y * row_bytes:(y + 1) * row_bytes] for y in range(info.height)]
    if info.right_origin:
        rows = [b"".join(r[x * stride:(x + 1) * stride]
                         for x in range(info.width - 1, -1, -1)) for r in rows]
    if not info.top_origin:
        rows.reverse()

    body = b"".join(_rle_row(r, stride) for r in rows) if info.rle else b"".join(rows)

    head = _HEADER.pack(len(info.id_field), info.colour_map_type, info.image_type,
                        info.colour_map_first, info.colour_map_length,
                        info.colour_map_depth, info.x_origin, info.y_origin,
                        info.width, info.height, info.depth, info.descriptor)
    return head + info.id_field + body + _moved_trailer(
        info, HEADER_SIZE + len(info.id_field) + len(body))


def _moved_trailer(info: TgaInfo, new_start: int) -> bytes:
    """The trailer with its footer offsets pointed at where it now sits.

    The extension area and developer directory are named by absolute file
    offsets, so re-encoding an RLE layer to a different length invalidates them.
    Everything in the trailer keeps its position *relative* to the trailer, so
    shifting each non-zero offset by the same delta is the whole fix.
    """
    if not info.trailer:
        return b""
    if not info.has_footer:
        return info.trailer
    delta = new_start - info.trailer_start
    if not delta:
        return info.trailer
    out = bytearray(info.trailer)
    ext, dev = _FOOTER_OFFSETS.unpack(out[-FOOTER_SIZE:][:8])
    moved = _FOOTER_OFFSETS.pack(ext + delta if ext else 0, dev + delta if dev else 0)
    out[-FOOTER_SIZE:-FOOTER_SIZE + 8] = moved
    return bytes(out)


def write(path: Path, image: Image.Image, info: TgaInfo) -> int:
    """Write the layer back in its own shape. Returns the byte count written.

    The write is atomic in the one sense that matters here: the bytes are built
    in full first, so a failure to encode leaves the file on disk untouched.
    Backups are the caller's business - this module does not decide policy.
    """
    data = encode(image, info)
    Path(path).write_bytes(data)
    return len(data)


def _rle_row(row: bytes, stride: int) -> bytes:
    """One scanline, run-length encoded. Runs never cross a row, per the spec.

    A packet is at most 128 pixels: ``0x80 | n-1`` then one pixel for a run,
    ``n-1`` then n pixels for a literal.
    """
    out = bytearray()
    n = len(row) // stride
    i = 0
    while i < n:
        px = row[i * stride:(i + 1) * stride]
        run = 1
        while (run < 128 and i + run < n
               and row[(i + run) * stride:(i + run + 1) * stride] == px):
            run += 1
        if run > 1:
            out.append(0x80 | (run - 1))
            out += px
            i += run
            continue
        # a literal packet runs until a pair repeats, because two identical
        # pixels are cheaper as a run packet than as two more literal ones
        start = i
        i += 1
        while i < n and i - start < 128:
            here = row[i * stride:(i + 1) * stride]
            if i + 1 < n and row[(i + 1) * stride:(i + 2) * stride] == here:
                break
            i += 1
        out.append(i - start - 1)
        out += row[start * stride:i * stride]
    return bytes(out)
