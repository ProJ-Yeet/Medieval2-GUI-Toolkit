"""96e5: hear a unit's voices, and give it a name call of its own.

What each part is here to catch:

  * **a sound is found where the game finds it**: a loose file first, else
    the record of that name in a SND.PACK (a pack built here, byte for byte
    in the game's layout), the mod's pack over the game's.
  * **a unit's name calls are listed per accent**, each file marked found or
    not, and the orders of the accent asked for.
  * **a name call of one's own**: the wav goes in as a new loose file, the unit
    gets its own line written like its neighbours, a line it shared keeps the
    other units, the compiled events.dat goes, and Undo puts every byte back.
  * **what is not a wav is refused**, and an odd format is warned about.

    python -m tests.test_voices
"""
import shutil
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp
from unittransfer import config, transfer, voices
from unittransfer.mod import Mod

cfg = Path(_tmp.mkdtemp(prefix="ut_cfg_"))
if config.SETTINGS_PATH.is_file():
    shutil.copy2(config.SETTINGS_PATH, cfg / "settings.json")
config.CONFIG_DIR = cfg; config.BACKUP_DIR = cfg / "backups"
config.SETTINGS_PATH = cfg / "settings.json"; config.LOG_PATH = cfg / "transfers.json"

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


def wav(rate=22050, ch=1, bits=16, n=8):
    data = b"\0" * n
    fmt = struct.pack("<HHIIHH", 1, ch, rate, rate * ch * bits // 8, ch * bits // 8, bits)
    body = b"WAVE" + b"fmt " + struct.pack("<I", 16) + fmt + b"data" + struct.pack("<I", len(data)) + data
    return b"RIFF" + struct.pack("<I", len(body)) + body


def pack(folder: Path, name: str, sounds):
    """A SND.PACK the way the game writes one."""
    dat, recs = b"", b""
    for rel, raw in sounds:
        recs += struct.pack("<6I", len(dat), len(raw), 22050, 16, 1, 1) + rel.encode("latin-1") + b"\0" + b"\0\0\0"
        dat += raw
    head = b"SND.PACK" + struct.pack("<4I", 5, len(sounds), len(sounds), len(dat))
    (folder / f"{name}.idx").write_bytes(head + recs)
    (folder / f"{name}.dat").write_bytes(dat)


root = Path(_tmp.mkdtemp(prefix="ut_vx_")) / "T"
data = root / "data"
(data / "sounds").mkdir(parents=True)
VF = "data/sounds/Voice/Human/Localized/Battle_Map"
pack(data / "sounds", "Voice1", [(f"{VF}/peasant_1.wav", wav()), (f"{VF}/order_go.wav", wav(n=4))])
(data / "sounds" / "events.dat").write_bytes(b"compiled")
(data / "sounds" / "events.idx").write_bytes(b"compiled")
(data / "export_descr_unit.txt").write_text(
    "type             Peasants\ndictionary       Peasants\ncategory         infantry\nclass            light\n"
    "voice_type       Light\naccent           English\n\n"
    "type             Spearmen\ndictionary       Spearmen\ncategory         infantry\nclass            spearmen\n"
    "voice_type       Light\naccent           English\n", encoding="latin-1")
BANK = (
    "BANK: unit_voice\n\n"
    "\taccent English\n"
    "\t\tclass Light\n"
    "\t\t\tvocal Unit_Select\n"
    "\t\t\t\tunit Peasants, Spearmen\n"
    "\t\t\t\t\tevent\n"
    f"\t\t\t\t\t\tfolder {VF}\n"
    "\t\t\t\t\t\tpeasant_1.wav\n"
    "\t\t\t\t\tend\n\n"
    "\t\t\tvocal Group_Created\n"
    "\t\t\t\tevent\n"
    f"\t\t\t\t\tfolder {VF}\n"
    "\t\t\t\t\torder_go.wav\n"
    "\t\t\t\t\tmissing_one.wav\n"
    "\t\t\t\tend\n")
(data / "export_descr_sounds_units_voice.txt").write_text(BANK, encoding="latin-1")
mod = Mod(root)

print("where a sound is")
idx = voices.pack_index(mod)
check("a pack's records are read", f"{VF}/peasant_1.wav".lower() in idx)
check("and a record's bytes are the wav it holds", voices.sound_bytes(mod, f"{VF}/peasant_1.wav") == wav())
(data / "sounds" / "Voice" / "Human" / "Localized" / "Battle_Map").mkdir(parents=True)
(data / "sounds" / "Voice" / "Human" / "Localized" / "Battle_Map" / "peasant_1.wav").write_bytes(wav(n=2))
check("a loose file wins over the pack", voices.sound_bytes(mod, f"{VF}/peasant_1.wav") == wav(n=2))
check("a wav is told from what is not one",
      voices.wav_info(wav()) == (1, 1, 22050, 16) and voices.wav_info(b"ID3 mp3") is None)

print("\nwhat a unit says")
v = voices.unit_view(mod, "Peasants")
check("its name call, by accent, shared with Spearmen",
      [(c["accent"], c["shared"]) for c in v["calls"]] == [("English", True)])
check("its accent's orders, a missing file marked",
      [(f["rel"].split("/")[-1], f["found"]) for f in v["orders"][0]["files"]]
      == [("order_go.wav", True), ("missing_one.wav", False)])

print("\na name call of its own")
try:
    voices.plan_name_call(mod, "Peasants", "English", "Light", [("x.mp3", b"ID3")])
    check("what is not a wav is refused", False)
except voices.VoiceError:
    check("what is not a wav is refused", True)
before = {p: p.read_bytes() for p in data.rglob("*") if p.is_file()}
p = voices.plan_name_call(mod, "Peasants", "English", "Light", [("mine.wav", wav(rate=44100, ch=2))])
check("an odd format is warned about, not refused", p["warnings"] and "44100" in p["warnings"][0])
rec = voices.apply_name_call(mod, p)
text = (data / "export_descr_sounds_units_voice.txt").read_text(encoding="latin-1")
check("the shared line keeps the other unit", "unit Spearmen\n" in text and "unit Peasants, Spearmen" not in text)
check("and Peasants has its own, written like its neighbour",
      "\t\t\t\tunit Peasants\n\t\t\t\t\tevent\n" in text and "English_Light_name_peasants_custom_1.wav" in text)
new = data / "sounds/Voice/Human/Localized/Battle_Map/English_Light_name_peasants_custom_1.wav"
check("the wav is in as a loose file", new.read_bytes() == wav(rate=44100, ch=2))
check("the compiled events are gone", not (data / "sounds" / "events.dat").exists())
check("and the unit now says it", any("custom" in f["rel"] for c in voices.unit_view(Mod(root), "Peasants")["calls"]
                                         for f in c["files"]))
transfer.undo(rec["id"])
after = {p: p.read_bytes() for p in data.rglob("*") if p.is_file()}
check("Undo puts every byte back", before == after)

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
