"""Mylae's HydroRIVERS import, as :mod:`unittransfer.hydrorivers`.

A small network written as a real shapefile (tests/_shp.py): a trunk of order
3 fed by a tributary of order 2 and a brook of order 1, one reach stored
upstream-first and one stored backwards.

    python -m tests.test_hydrorivers
"""
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _shp, _tmp
from unittransfer import hydrorivers, osmmap

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


#   brook (1) ->\
#                 trunk (3) -> sea          tributary (2) ->/
REACHES = [
    {"HYRIV_ID": 10, "NEXT_DOWN": 30, "ORD_STRA": 1, "parts": [[(1.0, 50.0), (2.0, 49.5)]]},
    # stored backwards: its first point is where it meets the trunk
    {"HYRIV_ID": 20, "NEXT_DOWN": 30, "ORD_STRA": 2, "parts": [[(2.0, 49.5), (2.0, 48.5)]]},
    {"HYRIV_ID": 30, "NEXT_DOWN": 0, "ORD_STRA": 3, "parts": [[(2.0, 49.5), (4.0, 49.0)]]},
    # far outside the box
    {"HYRIV_ID": 40, "NEXT_DOWN": 0, "ORD_STRA": 5, "parts": [[(40.0, 10.0), (41.0, 10.0)]]},
]
BOX = osmmap.Bbox(51.0, 48.0, 0.0, 5.0)
tmp = Path(_tmp.mkdtemp("ut_hydro_"))

print("\n1) the shapefile, loose and zipped")
_shp.write(tmp / "HydroRIVERS_v10_eu", REACHES)
got = hydrorivers.read(tmp / "HydroRIVERS_v10_eu.shp", BOX)
check(f"three reaches under the box, the far one left out: {sorted(r['HYRIV_ID'] for r in got)}",
      sorted(r["HYRIV_ID"] for r in got) == [10, 20, 30])
check("the folder holding them reads the same",
      len(hydrorivers.read(tmp, BOX)) == 3)
with zipfile.ZipFile(tmp / "eu.zip", "w") as z:
    z.write(tmp / "HydroRIVERS_v10_eu.shp", "HydroRIVERS_v10_eu_shp/HydroRIVERS_v10_eu.shp")
    z.write(tmp / "HydroRIVERS_v10_eu.dbf", "HydroRIVERS_v10_eu_shp/HydroRIVERS_v10_eu.dbf")
check("and the official ZIP, read without unpacking it",
      sorted(r["HYRIV_ID"] for r in hydrorivers.read(tmp / "eu.zip", BOX)) == [10, 20, 30])

print("\n2) the network")
riv = hydrorivers.rivers(got, 2)
check(f"order 2 and up: the tributary and the trunk, not the brook: {sorted(riv)}",
      sorted(riv) == ["20", "30"])
check("the tributary stored backwards is turned to end on the trunk",
      riv["20"][0] == (48.5, 2.0) and riv["20"][-1] == (49.5, 2.0))
check("the trunk runs from the confluence to the sea",
      riv["30"][0] == (49.5, 2.0) and riv["30"][-1] == (49.0, 4.0))
check("order 1 brings the brook in, ending at the confluence too",
      hydrorivers.rivers(got, 1)["10"][-1] == (49.5, 2.0))
check("a reach below the order is still taken when a chosen one flows into it",
      sorted(hydrorivers.select([dict(REACHES[0], ORD_STRA=4), dict(REACHES[2], ORD_STRA=1)], 3))
      == [10, 30])

print("\n3) what is refused")
_shp.write(tmp / "poly", REACHES[:1], shape_type=5)
try:
    hydrorivers.read(tmp / "poly.shp", BOX)
    check("polygons are refused", False)
except hydrorivers.HydroError as e:
    check(f"polygons are refused: {e}", True)
_shp.write(tmp / "other", REACHES[:1], fields=(("ID", 10), ("ORDER", 4)))
try:
    hydrorivers.read(tmp / "other.shp", BOX)
    check("a table without HydroRIVERS' fields is refused", False)
except hydrorivers.HydroError as e:
    check(f"a table without HydroRIVERS' fields is refused: {e}", True)
(tmp / "lonely.shp").write_bytes((tmp / "poly.shp").read_bytes())
try:
    hydrorivers.read(tmp / "lonely.shp", BOX)
    check("a .shp with no .dbf beside it is refused", False)
except hydrorivers.HydroError as e:
    check(f"a .shp with no .dbf beside it is refused: {e}", True)

print(f"\n{sum(ok)}/{len(ok)} passed")
sys.exit(0 if all(ok) else 1)
