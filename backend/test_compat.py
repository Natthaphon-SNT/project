"""Smoke test: spec_parser + compat_engine against real shop.db products."""
import sqlite3
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")
import spec_parser as sp
import compat_engine as ce

conn = sqlite3.connect("shop.db")

def find(cat, kw):
    row = conn.execute(
        "select p_name from products where category=? and p_name like ? limit 1",
        (cat, f"%{kw}%")).fetchone()
    return row[0] if row else None

print("=== PARSER SPOT CHECKS ===")
samples = [
    ("CPU", "CPU AMD AM4 RYZEN 5 5500 3.6GHz 6C 12T"),
    ("CPU", "CPU INTEL 1851 CORE ULTRA 5 225F 3.3GHz 10C 10T (3Y)"),
    ("CPU", "CPU AMD AM5 RYZEN 7 7800X3D 4.2GHz 8C 16T"),
    ("Mainboard", "MAINBOARD (AM5) MSI PRO B650M-P DDR5 (3Y)"),
    ("Mainboard", "MAINBOARD (AM4) ASROCK A520M-HVS (3Y)"),
    ("Mainboard", "MAINBOARD INTEL B760M GAMING PLUS WIFI DDR4 (3Y)"),
    ("RAM", "RAM KINGSTON FURY BEAST 16GB (8x2) DDR5 5200MHz BLACK (LT)"),
    ("GPU", "VGA GALAX GEFORCE RTX 4060 TI EX - 8GB GDDR6 (3Y)"),
    ("PSU", "PSU AEROCOOL UNITED POWER 600W (80+WHITE) (3Y)"),
    ("Case", "CASE ZALMAN M4 SE (BLACK)(mATX) (1Y)"),
    ("Air Cooler", "AIR COOLER ID-COOLING SE-214-XT RS (2Y)"),
]
for cat, name in samples:
    print(sp.parse_part(cat, name))

def build(cpu_kw, mb_kw, ram_kw, gpu_kw, psu_kw, case_kw):
    names = {
        "CPU": find("CPU", cpu_kw), "Mainboard": find("Mainboard", mb_kw),
        "RAM": find("RAM", ram_kw), "GPU": find("GPU", gpu_kw),
        "PSU": find("PSU", psu_kw), "Case": find("Case", case_kw),
    }
    parts = []
    for cat, n in names.items():
        if not n:
            print(f"!! no product for {cat}")
            continue
        p = sp.parse_part(cat, n)
        p["price"] = conn.execute("select min(nullif(p_price,0)) from products where p_name=?", (n,)).fetchone()[0] or 0
        parts.append(p)
        print(f"   {cat}: {n} | {p['price']}")
    return parts

print("\n=== BUILD A: good AM5 gaming build (budget 35000) ===")
parts = build("7500F", "(AM5)", "DDR5", "FIGHTER AMD RADEON RX 7600", "600W", "mATX")
result = ce.check_build(parts, budget=35000)
print(result["overall"], "|", result["summary"])
for c in result["checks"]:
    print(" -", c["item"], c["ok"], c["detail"])

print("\n=== BUILD B: incompatible (AM4 CPU + AM5 board + DDR4 RAM + weak PSU + high GPU) ===")
parts = build("5600", "(AM5)", "DDR4", "RX 7700 XT GAMING OC", "550W", "mATX")
result = ce.check_build(parts)
print(result["overall"], "|", result["summary"])
for c in result["checks"]:
    print(" -", c["item"], c["ok"], c["detail"])
print("suggestions:", result["suggestions"])
