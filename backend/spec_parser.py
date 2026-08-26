"""
IT-RECOMMEND — Spec Parser
Extract structured hardware attributes from Thai retail product names.
Deterministic only: returns None when a value cannot be derived (never guesses).
"""
import re
from typing import Optional

# ─────────────────────────────────────────
# Socket maps
# ─────────────────────────────────────────
AMD_SOCKET_TOKENS = {"AM4": "AM4", "AM5": "AM5"}
INTEL_CHIPSET_MAP = {
    "H510": "LGA1200", "B560": "LGA1200", "Z590": "LGA1200",
    "H610": "LGA1700", "B660": "LGA1700", "B760": "LGA1700",
    "Z690": "LGA1700", "Z790": "LGA1700", "1700": "LGA1700",
    "B860": "LGA1851", "Z890": "LGA1851", "W880": "LGA1851", "1851": "LGA1851",
}
AMD_CHIPSET_MAP = {
    "A320": "AM4", "B450": "AM4", "X470": "AM4", "A520": "AM4",
    "B550": "AM4", "X570": "AM4",
    "A620": "AM5", "B650": "AM5", "X670": "AM5", "X870": "AM5",
}

GPU_TDP_TABLE = [
    (re.compile(r"RTX\s*50[9]0", re.I), 575), (re.compile(r"RTX\s*5080", re.I), 360),
    (re.compile(r"RTX\s*5070\s*TI", re.I), 300), (re.compile(r"RTX\s*5070", re.I), 250),
    (re.compile(r"RTX\s*5060\s*TI", re.I), 180), (re.compile(r"RTX\s*5060", re.I), 145),
    (re.compile(r"RTX\s*5050", re.I), 130),
    (re.compile(r"RTX\s*4090", re.I), 450), (re.compile(r"RTX\s*4080", re.I), 320),
    (re.compile(r"RTX\s*4070\s*TI", re.I), 285), (re.compile(r"RTX\s*4070", re.I), 200),
    (re.compile(r"RTX\s*4060\s*TI", re.I), 165), (re.compile(r"RTX\s*4060", re.I), 115),
    (re.compile(r"RTX\s*3090", re.I), 350), (re.compile(r"RTX\s*3080", re.I), 320),
    (re.compile(r"RTX\s*3070", re.I), 220), (re.compile(r"RTX\s*3060", re.I), 170),
    (re.compile(r"RTX\s*3050", re.I), 130),
    (re.compile(r"RX\s*7900\s*XTX", re.I), 355), (re.compile(r"RX\s*7900\s*XT", re.I), 315),
    (re.compile(r"RX\s*7800\s*XT", re.I), 263), (re.compile(r"RX\s*7700\s*XT", re.I), 245),
    (re.compile(r"RX\s*7600", re.I), 165),
    (re.compile(r"RX\s*6950", re.I), 335), (re.compile(r"RX\s*6800", re.I), 250),
    (re.compile(r"RX\s*6750\s*XT", re.I), 250), (re.compile(r"RX\s*6700\s*XT", re.I), 230),
    (re.compile(r"RX\s*6650\s*XT", re.I), 180), (re.compile(r"RX\s*6600", re.I), 132),
    (re.compile(r"RX\s*6500\s*XT", re.I), 107),
]


def _cpu_tdp_estimate(name_upper: str) -> Optional[int]:
    """Estimate CPU TDP from model tier. Returns None only if brand unknown."""
    if "RYZEN" in name_upper:
        if "RYZEN 9" in name_upper or "THREADRIPPER" in name_upper:
            return 170 if "THREADRIPPER" in name_upper else 125
        if "RYZEN 7" in name_upper:
            return 105 if re.search(r"\d{4}X", name_upper) else 65
        return 65
    if "CORE ULTRA" in name_upper:
        if "ULTRA 9" in name_upper: return 125
        if "ULTRA 7" in name_upper: return 125
        return 65
    if "INTEL" in name_upper or re.search(r"\bI[3579]", name_upper):
        if "I9" in name_upper: return 125
        if "I7" in name_upper: return 125 if re.search(r"I7-\d{4,5}K", name_upper) else 65
        return 65
    return None


def parse_cpu(name: str) -> dict:
    u = name.upper()
    socket = None
    m = re.search(r"\b(AM4|AM5)\b", u)
    if m:
        socket = m.group(1)
    elif re.search(r"\b1851\b", u) or "CORE ULTRA" in u:
        socket = "LGA1851"
    elif re.search(r"\b1700\b", u):
        socket = "LGA1700"
    elif re.search(r"(I[3579]|CORE)", u):
        gen_m = re.search(r"\b(?:I[3579]-?)?(\d{4,5})[FKS]*\b", u)
        if gen_m:
            n = int(gen_m.group(1))
            socket = "LGA1700" if 12000 <= n <= 14999 else ("LGA1200" if 10000 <= n <= 11999 else None)
    if not socket and "RYZEN" in u:
        # Infer platform from Ryzen model number: 7000+ = AM5, older = AM4
        ry_m = re.search(r"RYZEN\s*\d\s*(\d{4})", u)
        if ry_m:
            n = int(ry_m.group(1))
            if 7000 <= n <= 9999:
                socket = "AM5"
            elif 1000 <= n <= 5999:
                socket = "AM4"
    tdp = _cpu_tdp_estimate(u)
    return {"category": "CPU", "socket": socket, "tdp": tdp}


def parse_mainboard(name: str) -> dict:
    u = name.upper()
    socket = None
    m = re.search(r"\((AM4|AM5)\)|\b(AM4|AM5)\b", u)
    if m:
        socket = next(g for g in m.groups() if g)
    if not socket:
        for chip, soc in INTEL_CHIPSET_MAP.items():
            if re.search(rf"\b{chip}M?\b", u):
                socket = soc; break
    if not socket:
        for chip, soc in AMD_CHIPSET_MAP.items():
            if re.search(rf"\b{chip}M?\b", u):
                socket = soc; break

    ram_support = set()
    if "DDR5" in u: ram_support.add("DDR5")
    if "DDR4" in u and "DDR5" not in u: ram_support.add("DDR4")
    if not ram_support and socket in ("AM5", "LGA1851"):
        ram_support = {"DDR5"}

    ff = "mATX"
    if re.search(r"\bMINI[- ]?ITX\b|\(ITX\)|\bITX\b", u): ff = "ITX"
    elif re.search(r"\(ATX\)|\bATX\b", u) and "MATX" not in u.replace("M-ATX", "MATX"): ff = "ATX"
    elif re.search(r"M[- ]?ATX|MICRO[- ]?ATX|\(MATX\)", u): ff = "mATX"
    # explicit ATX token check (avoid mATX false positive handled above)
    if re.search(r"\(ATX\)|\bE[- ]?ATX\b", u): ff = "ATX"

    return {"category": "Mainboard", "socket": socket,
            "ram_support": sorted(ram_support) or None, "form_factor": ff}


def parse_ram(name: str) -> dict:
    u = name.upper()
    ddr = None
    if "DDR5" in u: ddr = "DDR5"
    elif "DDR4" in u: ddr = "DDR4"
    elif "DDR3" in u: ddr = "DDR3"
    cap_m = re.search(r"(\d{1,2})GB", u)
    speed_m = re.search(r"(\d{3,5})\s*MHZ", u)
    return {"category": "RAM", "ddr_gen": ddr,
            "capacity_gb": int(cap_m.group(1)) if cap_m else None,
            "speed_mhz": int(speed_m.group(1)) if speed_m else None}


def parse_gpu(name: str) -> dict:
    u = name.upper()
    chipset, gpu_tdp = None, None
    for rx, watt in GPU_TDP_TABLE:
        if rx.search(u):
            chipset = re.sub(r"[^A-Z0-9 ]", "", rx.pattern.upper().replace(r"\S*", " "))
            gpu_tdp = watt
            break
    vram_m = re.search(r"(\d{1,2})GB\s*(GDDR\d)?", u)
    return {"category": "GPU", "chipset": chipset, "tdp": gpu_tdp,
            "vram_gb": int(vram_m.group(1)) if vram_m else None}


def parse_psu(name: str) -> dict:
    u = name.upper()
    watt = None
    m = re.search(r"\b(\d{3,4})\s*W\b", u)
    if m: watt = int(m.group(1))
    grade = None
    gm = re.search(r"80\+\s*(GOLD|SILVER|BRONZE|WHITE)", u)
    if gm: grade = gm.group(1)
    return {"category": "PSU", "watt": watt, "efficiency": grade}


def parse_case(name: str) -> dict:
    u = name.upper()
    ff = "mATX"
    if re.search(r"\bMINI[- ]?ITX\b|\(ITX\)", u): ff = "ITX"
    elif re.search(r"\(ATX\)|\bFULL TOWER\b|\bMID TOWER\b|\bE[- ]?ATX\b", u): ff = "ATX"
    elif re.search(r"M[- ]?ATX|MICRO[- ]?ATX|\(MATX\)", u): ff = "mATX"
    supports = {"ITX": {"ITX"}, "mATX": {"mATX", "ITX"}, "ATX": {"ATX", "mATX", "ITX"}}[ff]
    return {"category": "Case", "form_factor": ff, "supports_ff": sorted(supports)}


COOLER_RATING_HINTS = [
    (r"SE-214|AS-120|GAMMA\b|AX120|RX120", 120),
    (r"PA120|PE120|DUAL TOWER|2 TOWER", 200),
    (r"240", 200), (r"360", 250),
]

def parse_cooler(name: str) -> dict:
    """Returns rating=None when the item is likely a case fan / accessory."""
    u = name.upper()
    is_cpu_cooler = bool(re.search(
        r"AIR COOLER|LIQUID COOLER|CPU COOL|AIO|\bSE-214|\bPA120|\bAS-120|FLOE|CASTLE|FORZA|LB240|LB360|LT240|LT360|DRP|HYPER\s?212|ASSASSIN", u))
    rating = None
    for pat, val in COOLER_RATING_HINTS:
        if re.search(pat, u):
            rating = val; break
    return {"category": "Cooler", "is_cpu_cooler": is_cpu_cooler, "rating_watt": rating}


def parse_storage(name: str) -> dict:
    u = name.upper()
    interface = "NVMe" if re.search(r"NVME|PCIE|M\.2|^M\.2", u) else ("SATA" if "SATA" in u else None)
    cap_m = re.search(r"(\d+(?:\.\d+)?)\s*(TB|GB)", u)
    capacity_gb = None
    if cap_m:
        capacity_gb = float(cap_m.group(1)) * (1024 if cap_m.group(2) == "TB" else 1)
    return {"category": "Storage", "interface": interface,
            "capacity_gb": int(capacity_gb) if capacity_gb else None}


PARSERS = {
    "CPU": parse_cpu,
    "Mainboard": parse_mainboard,
    "RAM": parse_ram,
    "GPU": parse_gpu,
    "PSU": parse_psu,
    "Case": parse_case,
    "Cooler": parse_cooler,
    "Storage": parse_storage,
    "SSD": parse_storage,
}

# Map AI/frontend part labels → DB categories
LABEL_ALIASES = {
    "CPU": "CPU", "PROCESSOR": "CPU",
    "MAINBOARD": "Mainboard", "MOTHERBOARD": "Mainboard", "MB": "Mainboard",
    "RAM": "RAM", "MEMORY": "RAM",
    "GPU": "GPU", "VGA": "GPU", "GRAPHIC": "GPU", "GRAPHICS CARD": "GPU", "VGA CARD": "GPU",
    "PSU": "PSU", "POWER SUPPLY": "PSU",
    "CASE": "Case",
    "STORAGE": "SSD", "SSD": "SSD", "M.2": "SSD", "HDD": "SSD", "NVME": "SSD",
    "COOLER": "Air Cooler", "AIR COOLER": "Air Cooler", "LIQUID COOLER": "Liquid Cooler",
    "FAN": "Air Cooler", "COOLING": "Air Cooler",
}


def normalize_label(label: str) -> str:
    return LABEL_ALIASES.get(label.strip().upper(), label.strip())


def parse_part(category: str, name: str) -> dict:
    parser = PARSERS.get(category)
    base = {"category": category, "name": name}
    if parser:
        base.update(parser(name))
    return base


def parse_free_text_line(line: str) -> Optional[dict]:
    """
    Parse a user-pasted spec line like:
      'CPU AMD Ryzen 5 7500F' or 'Mainboard MSI B650M...' into a parsed part.
    Returns None if no known category keyword found.
    """
    u = line.upper().strip()
    for key, cat in LABEL_ALIASES.items():
        if re.search(rf"\b{re.escape(key)}\b", u):
            db_cat = cat if cat in ("Liquid Cooler", "Air Cooler") else cat
            parsed = parse_part(db_cat, line)
            parsed["raw_line"] = line.strip()
            return parsed
    return None
