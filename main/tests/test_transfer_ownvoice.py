"""96f: Unit Transfer bringing a unit's OWN voice, its name call with it.

Run:  python -m tests.test_transfer_ownvoice

Two small mods. The source's ``Khans Guard`` has its own Unit_Select entry
naming three sounds: one loose in the source, one only in the source's
SND.PACK, one nowhere. The destination has the same accent and class with a
unit of its own, a sound the entry shares already in its pack, and a compiled
``events.dat``. What has to hold:

* **the entry lands in the destination's block** under the unit's new name,
  in the destination's indent, and the EDU is pinned to its accent and class;
* **the sounds the destination lacks come**, the loose one and the packed one,
  each at the path the entry names; the one it already plays does not;
* **one missing everywhere is said**, and the compiled events files are listed
  to go;
* **a unit with no entry of its own** warns and writes nothing.
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests import _tmp  # noqa: E402
from unittransfer import sounds, transfer                          # noqa: E402
from unittransfer.mod import Mod                                   # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


def wav(n=8):
    data = b"\1" * n
    fmt = struct.pack("<HHIIHH", 1, 1, 22050, 44100, 2, 16)
    body = b"WAVE" + b"fmt " + struct.pack("<I", 16) + fmt + b"data" + struct.pack("<I", len(data)) + data
    return b"RIFF" + struct.pack("<I", len(body)) + body


def pack(folder: Path, name: str, items):
    dat, recs = b"", b""
    for rel, raw in items:
        recs += struct.pack("<6I", len(dat), len(raw), 22050, 16, 1, 1) + rel.encode("latin-1") + b"\0" + b"\0\0\0"
        dat += raw
    head = b"SND.PACK" + struct.pack("<4I", 5, len(items), len(items), len(dat))
    (folder / f"{name}.idx").write_bytes(head + recs)
    (folder / f"{name}.dat").write_bytes(dat)


VF = "data/sounds/Voice/Human/Localized/Battle_Map"


def bank(units):
    out = "BANK: unit_voice\n\n\taccent Mongol\n\t\tclass Heavy\n\t\t\tvocal Unit_Select\n"
    for name, files in units:
        out += f"\t\t\t\tunit {name}\n\t\t\t\t\tevent\n\t\t\t\t\t\tfolder {VF}\n"
        out += "".join(f"\t\t\t\t\t\t{f}\n" for f in files) + "\t\t\t\t\tend\n"
    return out


def mod_at(root: Path, units, edu_types) -> Path:
    data = root / "data"
    (data / "sounds").mkdir(parents=True)
    (data / "export_descr_sounds_units_voice.txt").write_text(bank(units), encoding="latin-1")
    (data / "export_descr_unit.txt").write_text("".join(
        f"type             {t}\ndictionary       {t.replace(' ', '_')}\ncategory         cavalry\n"
        f"class            heavy\nvoice_type       Heavy\naccent           Mongol\n\n" for t in edu_types),
        encoding="latin-1")
    return data


tmp = Path(_tmp.mkdtemp(prefix="ut_ownvoice_"))
sdata = mod_at(tmp / "Src", [("Khans Guard", ["khans_guard_1.wav", "khans_guard_2.wav",
                                              "shared_horn.wav", "lost_call.wav"])],
               ["Khans Guard", "Silent Riders"])
ddata = mod_at(tmp / "Dst", [("Keshig", ["keshig_1.wav"])], ["Keshig"])
loose = sdata / "sounds" / "Voice" / "Human" / "Localized" / "Battle_Map"
loose.mkdir(parents=True)
(loose / "khans_guard_1.wav").write_bytes(wav(4))
pack(sdata / "sounds", "Voice1", [(f"{VF}/khans_guard_2.wav", wav(6)), (f"{VF}/shared_horn.wav", wav(2))])
pack(ddata / "sounds", "Voice1", [(f"{VF}/shared_horn.wav", wav(2)), (f"{VF}/keshig_1.wav", wav(3))])
(ddata / "sounds" / "events.dat").write_bytes(b"compiled")
(ddata / "sounds" / "events.idx").write_bytes(b"compiled")
src, dst = Mod(tmp / "Src"), Mod(tmp / "Dst")


def planned(unit, new):
    p = transfer.TransferPlan(unit_type=unit, dictionary=unit.replace(" ", "_"), source=src,
                              dest=dst, options=transfer.TransferOptions(sound_mode="own"))
    p.resolved_type = new
    transfer._resolve_sound(p, dst)
    return p


print("\n1) its own entry")
p = planned("Khans Guard", "Khans Guard")
after = sounds.parse_text(p.sound_text)
e = after.get("Khans Guard")
check("copied, into the destination's Mongol / Heavy block",
      p.sound_action == "copy" and e is not None and (e.accent, e.voice_class) == ("Mongol", "Heavy"))
check("the destination's own unit is still there", after.get("Keshig") is not None)
check("  and the EDU is pinned to the same pair",
      (p.sound_accent, p.sound_class) == ("Mongol", "Heavy"))
first = after.lines[e.start]
check("written in the destination's indent", first.startswith("\t\t\t\tunit Khans Guard"))

print("\n2) the sounds")
got = {rel: raw for rel, raw in p.sound_files}
base = VF[5:]
check("the loose one and the packed one come",
      set(got) == {f"{base}/khans_guard_1.wav", f"{base}/khans_guard_2.wav"})
check("  with the source's bytes", got[f"{base}/khans_guard_1.wav"] == wav(4)
      and got[f"{base}/khans_guard_2.wav"] == wav(6))
check("the one the destination already plays does not", f"{base}/shared_horn.wav" not in got)
check("the one nowhere is said", any("lost_call.wav" in w for w in p.warnings))
check("the compiled events files are to go",
      sorted(p.sound_compiled) == ["sounds/events.dat", "sounds/events.idx"])

print("\n3) a new name, and a unit with no voice")
q = planned("Khans Guard", "Khans Guard Copy")
check("a renamed copy gets the entry under its new name",
      sounds.parse_text(q.sound_text).get("Khans Guard Copy") is not None)
r = planned("Silent Riders", "Silent Riders")
check("no entry of its own warns and writes nothing",
      r.sound_action == "missing" and not r.sound_text and not r.sound_files and r.warnings)

print(f"\n{sum(ok)}/{len(ok)} passed")
sys.exit(0 if all(ok) else 1)
