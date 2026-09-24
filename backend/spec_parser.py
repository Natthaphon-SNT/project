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
    if "DDR5" in u and "DDR4" in u:
        # Board supports both (e.g. B660 with dual-gen slots)
        ram_support = {"DDR4", "DDR5"}
    elif "DDR5" in u:
        ram_support.add("DDR5")
    elif "DDR4" in u:
        ram_support.add("DDR4")

    # Fallback: infer from socket / chipset when name has no explicit DDR token
    if not ram_support:
        if socket in ("AM5", "LGA1851"):
            ram_support = {"DDR5"}          # AM5 / Intel 800-series = DDR5 only
        elif socket == "LGA1700":
            ram_support = {"DDR4", "DDR5"}  # LGA1700 boards ship as both DDR4 and DDR5 variants (e.g. Z690/B660)
        elif socket in ("AM4", "LGA1200"):
            ram_support = {"DDR4"}          # AM4 / Intel 10th-11th gen = DDR4 only
        # else: truly unknown (e.g. very old or no chipset found)

    ff = "mATX"
    if re.search(r"\bE[- ]?ATX\b", u): ff = "E-ATX"
    elif re.search(r"\bMINI[- ]?ITX\b|\(ITX\)|\bITX\b", u): ff = "ITX"
    elif re.search(r"\(ATX\)|\bATX\b", u) and "MATX" not in u.replace("M-ATX", "MATX"): ff = "ATX"
    elif re.search(r"M[- ]?ATX|MICRO[- ]?ATX|\(MATX\)", u): ff = "mATX"
    # explicit ATX token check (avoid mATX false positive handled above)
    if re.search(r"\(ATX\)", u): ff = "ATX"

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
    result = {"category": "GPU", "chipset": chipset, "tdp": gpu_tdp,
              "tdp_estimated": gpu_tdp is not None,
              "vram_gb": int(vram_m.group(1)) if vram_m else None}
    connectors = _parse_power_connectors(u)
    if connectors:
        result["power_connectors_required"] = connectors
    from gpu_power_reference import lookup_gpu_power, evidence
    reference = lookup_gpu_power(name)
    if reference:
        result["chipset"] = reference["model"]
        result["power_sources"] = []
        for field in ("tdp", "recommended_psu_watt"):
            if field in reference:
                result[field] = reference[field]
                result["power_sources"].append(evidence(reference, field))
        if "power_connectors_required" in reference:
            result["power_connectors_required"] = dict(reference["power_connectors_required"])
        result["tdp_estimated"] = False
    return result


def parse_psu(name: str) -> dict:
    u = name.upper()
    watt = None
    m = re.search(r"\b(\d{3,4})\s*W\b", u)
    if m: watt = int(m.group(1))
    grade = None
    gm = re.search(r"80\+\s*(GOLD|SILVER|BRONZE|WHITE)", u)
    if gm: grade = gm.group(1)
    result = {"category": "PSU", "watt": watt, "efficiency": grade}
    connectors = _parse_power_connectors(u)
    if connectors:
        result["power_connectors"] = connectors
    return result


FORM_FACTOR_ORDER = ("E-ATX", "ATX", "mATX", "ITX")


def extract_form_factors(value: str) -> list[str]:
    """Read motherboard sizes without treating E-ATX or Micro-ATX as ATX."""
    u = (value or "").upper()
    found = set()
    if re.search(r"\bE[- ]?ATX\b", u):
        found.add("E-ATX")
    if re.search(r"(?<![A-Z-])ATX\b", u):
        found.add("ATX")
    if re.search(r"\b(?:MICRO[- ]?ATX|M[- ]?ATX|MATX)\b", u):
        found.add("mATX")
    if re.search(r"\b(?:MINI[- ]?ITX|ITX)\b", u):
        found.add("ITX")
    return [factor for factor in FORM_FACTOR_ORDER if factor in found]


def parse_case(name: str) -> dict:
    u = name.upper()
    factors = extract_form_factors(u)
    ff = factors[0] if factors else None
    if not ff and re.search(r"\b(?:FULL|MID)\s*TOWER\b", u):
        ff = "ATX"
    supported_by_size = {
        "E-ATX": list(FORM_FACTOR_ORDER),
        "ATX": ["ATX", "mATX", "ITX"],
        "mATX": ["mATX", "ITX"],
        "ITX": ["ITX"],
    }
    return {"category": "Case", "form_factor": ff,
            "supports_ff": supported_by_size.get(ff)}


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


def _parse_power_connectors(value: str) -> dict:
    """Normalize common GPU/PSU connector descriptions into connector counts."""
    text = re.sub(r"\s+", " ", value.upper().replace("×", "X")).strip()
    # Advice summaries put the count before PCIe, while its specification
    # table puts the count after the pin type. Canonicalize both forms before
    # applying the ordinary connector patterns below.
    text = re.sub(
        r"\b(\d+)\s*X\s*PCI[ -]?E\s*\(\s*((?:6\s*\+\s*2|8|6|16)\s*[- ]?PIN)\s*\)",
        r"\1 X \2", text,
    )
    text = re.sub(
        r"\(\s*((?:6\s*\+\s*2|8|6|16)\s*[- ]?PIN)\s*\)\s*X\s*(\d+)(?:\s+CONNECTORS?)?",
        r"\2 X \1", text,
    )
    found = {}
    patterns = [
        ("12V-2x6", r"12V\s*[- ]?2X6|12V2X6"),
        ("12VHPWR", r"12VHPWR|12V\s*HIGH\s*POWER|(?<!\d)16\s*[- ]?PIN"),
        ("PCIe 8-pin", r"(?:PCI[ -]?E|PCIE)?\s*(?<!\d)8\s*[- ]?PIN|(?<!\d)6\s*\+\s*2\s*[- ]?PIN|(?<!\d)8\s*\+\s*2\s*[- ]?PIN"),
        ("PCIe 6-pin", r"(?:PCI[ -]?E|PCIE)?\s*(?<!\d)6\s*[- ]?PIN"),
    ]
    for label, pattern in patterns:
        match = re.search(r"(\d+)\s*[X ]\s*(?:" + pattern + r")", text)
        if match:
            found[label] = max(found.get(label, 0), int(match.group(1)))
        elif re.search(pattern, text):
            found[label] = max(found.get(label, 0), 1)
    return {label: count for label, count in found.items() if count > 0}


_DETAIL_LABELS = {
    "socket": (
        "socket", "cpu socket", "processor socket", "platform", "ซ็อกเก็ต",
    ),
    "ram": (
        "memory type", "memory standard", "max memory type", "supported memory",
        "ram type", "ddr", "ประเภทหน่วยความจำ", "หน่วยความจำที่รองรับ",
    ),
    "recommended_psu": (
        "recommended psu", "recommended power supply", "required system power",
        "minimum system power", "minimum psu", "psu requirement",
        "power supply requirement", "power requirement", "need power supply", "suggested psu",
        "พาวเวอร์ซัพพลายที่แนะนำ", "กำลังเพาเวอร์ซัพพลายที่แนะนำ",
    ),
    "tdp": (
        "tdp", "thermal design power", "power consumption", "rated tdp",
        "processor tdp", "total graphics power", "total board power",
        "maximum turbo power", "อัตราการกินไฟ", "การใช้พลังงาน",
    ),
    "connector": (
        "power connector", "power connectors", "power input", "pci-e connector",
        "pcie connector", "pci ex connector", "pci express connector",
        "vga connector", "gpu connector", "external power",
        "supplementary power", "ขั้วต่อไฟ", "หัวต่อไฟ",
    ),
    "form_factor": (
        "form factor", "form-factor", "supported motherboard", "mainboard support",
        "motherboard support", "รองรับเมนบอร์ด",
    ),
    "psu_watt": (
        "wattage", "watt", "total power", "total output", "power output",
        "rated power", "continuous power", "output wattage", "กำลังไฟสูงสุด",
        "กำลังจ่ายสูงสุด",
    ),
    "cooler": (
        "cooler tdp", "socket support", "compatible socket", "max cooler height",
        "cooler clearance", "height", "ความสูงฮีตซิงก์",
    ),
}


def _detail_label_kind(label: str) -> Optional[str]:
    """Map a retail-page label to one compatibility field family."""
    key = re.sub(r"\s+", " ", label.strip().lower().rstrip(":")).strip()
    if not key:
        return None
    if "source url" in key or "source store" in key:
        return None
    for kind, aliases in _DETAIL_LABELS.items():
        if key in aliases:
            return kind
        if any(len(alias) >= 8 and alias in key for alias in aliases):
            return kind
    return None


def _looks_like_detail_value(kind: str, value: str) -> bool:
    u = value.upper()
    if kind == "socket":
        return bool(re.search(r"\b(?:AM[45]|LGA\s*\d{3,4})\b", u))
    if kind == "ram":
        return bool(re.search(r"\bDDR[345]\b", u))
    if kind in ("recommended_psu", "tdp", "psu_watt"):
        return bool(re.search(r"(?:≈|~)?\s*\d{2,4}\s*(?:W|WATT)", u))
    if kind == "connector":
        return bool(re.search(r"PIN|6\s*\+\s*2|12VHPWR|12V\s*[- ]?2X6", u))
    if kind == "form_factor":
        return bool(re.search(r"(?:E[- ]?)?ATX|M[- ]?ATX|MICRO[- ]?ATX|MINI[- ]?ITX", u))
    if kind == "cooler":
        return bool(re.search(r"\d{2,3}\s*(?:W|MM)|\b(?:AM[45]|LGA\s*\d{3,4})\b", u))
    return False


def _iter_detail_pairs(specs: str):
    """Yield facts from Key: Value and stacked retail table layouts."""
    # Keep tabs because iHaveCPU renders detail tables as ``label<TAB>value``.
    # Collapsing all whitespace first would erase that delimiter.
    lines = [re.sub(r"[ \r\f\v]+", " ", line).strip() for line in specs.splitlines()]
    lines = [line for line in lines if line]
    for index, line in enumerate(lines):
        inline = re.split(r"\s*:\s*|\t+", line, maxsplit=1)
        if len(inline) == 2:
            kind = _detail_label_kind(inline[0])
            if kind and _looks_like_detail_value(kind, inline[1]):
                yield kind, inline[0], inline[1]
                continue
        kind = _detail_label_kind(line)
        if not kind:
            continue
        values = []
        for candidate in lines[index + 1:index + 5]:
            if _detail_label_kind(candidate):
                break
            if _looks_like_detail_value(kind, candidate):
                values.append(candidate)
                if kind != "connector":
                    break
        if values:
            yield kind, line, " ".join(values)


def _parse_specs_text(specs: str, category: str = "") -> dict:
    """
    Parse the 'Key: Value' specs text extracted from product pages.
    Returns a flat dict of compat-relevant fields.
    """
    if not specs:
        return {}
    result = {}
    for line in specs.splitlines():
        line = line.strip()
        parts = re.split(r":\s*", line, maxsplit=1)
        if len(parts) != 2:
            continue
        key, val = parts[0].strip().lower(), parts[1].strip().upper()
        if "source url" in key or "source store" in key:
            continue

        # Socket
        if any(k in key for k in ("socket", "platform", "cpu socket")):
            m = re.search(r"\b(AM4|AM5|LGA\d{3,4})\b", val)
            if m:
                result["socket"] = m.group(1)

        # DDR generation
        if any(k in key for k in ("memory type", "memory standard", "max memory type",
                                   "supported memory", "ddr")):
            if "DDR5" in val and "DDR4" in val:
                result["ram_support"] = ["DDR4", "DDR5"]
            elif "DDR5" in val:
                result["ram_support"] = ["DDR5"]
            elif "DDR4" in val:
                result["ram_support"] = ["DDR4"]
            elif "DDR3" in val:
                result["ram_support"] = ["DDR3"]
            # RAM ddr_gen
            if "DDR5" in val and "DDR4" not in val:
                result["ddr_gen"] = "DDR5"
            elif "DDR4" in val and "DDR5" not in val:
                result["ddr_gen"] = "DDR4"

        # System PSU requirement must never become GPU consumption or PSU output.
        if any(k in key for k in ("recommended psu", "recommended power supply",
                                   "required system power", "minimum system power",
                                   "minimum psu", "psu requirement", "power requirement",
                                   "suggested psu")):
            m = re.search(r"\b(\d{3,4})\s*(?:W(?:ATTS?)?)\b", val)
            if m:
                target = "watt" if category == "PSU" and key == "power requirement" else "recommended_psu_watt"
                result[target] = max(result.get(target, 0), int(m.group(1)))
            continue

        # GPU/PSU external power connectors. Keep this separate from wattage.
        if any(k in key for k in ("power connector", "power connectors", "pci-e connector",
                                   "pcie connector", "pci express connector", "vga connector",
                                   "gpu connector", "external power", "supplementary power")):
            connectors = _parse_power_connectors(val)
            if connectors:
                # Keep this generic until parse_part knows whether the row
                # belongs to a GPU (required inputs) or a PSU (available outputs).
                result["power_connectors"] = connectors
            continue

        # TDP / graphics board power (not system PSU recommendation)
        if any(k in key for k in ("tdp", "thermal design power", "power consumption",
                                   "rated tdp", "processor tdp", "total graphics power", "total board power", "maximum turbo power")):
            m = re.search(r"\b(\d{2,4})\s*(?:W(?:ATTS?)?)\b", val)
            if m:
                result["tdp"] = max(result.get("tdp", 0), int(m.group(1)))

        # Form factor
        if any(k in key for k in ("form factor", "form-factor", "supported motherboard",
                                    "mainboard support", "motherboard support")):
            factors = extract_form_factors(val)
            if factors:
                if category == "Case":
                    result["supports_ff"] = factors
                else:
                    result["form_factor"] = factors[0]

        # PSU Wattage
        if key in ("wattage", "watt", "total power", "total output", "power output", "rated power", "continuous power", "output wattage"):
            m = re.search(r"\b(\d{3,4})\s*(?:W(?:ATTS?)?)?\b", val)
            if m:
                result["watt"] = int(m.group(1))

        # Cooler TDP rating
        if any(k in key for k in ("cooler tdp", "rated tdp", "socket support",
                                   "compatible socket", "max cooler height", "height")):
            if "tdp" in key or "rated" in key:
                m = re.search(r"(\d{2,3})\s*W", val)
                if m:
                    result["rating_watt"] = int(m.group(1))
            if "height" in key:
                m = re.search(r"(\d{2,3})\s*MM", val)
                if m:
                    result["height_mm"] = int(m.group(1))

    # Retail tables are commonly scraped as a label on one line and the value
    # on a following line. Overlay those facts after ordinary Key: Value rows.
    for kind, label, raw_value in _iter_detail_pairs(specs):
        val = raw_value.upper()
        if kind == "socket":
            m = re.search(r"\b(AM4|AM5|LGA\s*\d{3,4})\b", val)
            if m:
                result["socket"] = m.group(1).replace(" ", "")
        elif kind == "ram":
            generations = [g for g in ("DDR3", "DDR4", "DDR5") if g in val]
            if generations:
                result["ram_support"] = generations
                if len(generations) == 1:
                    result["ddr_gen"] = generations[0]
        elif kind == "recommended_psu":
            m = re.search(r"\b(\d{3,4})\s*(?:W|WATT)", val)
            if m:
                target = "watt" if category == "PSU" and label.strip().lower() == "power requirement" else "recommended_psu_watt"
                result[target] = max(result.get(target, 0), int(m.group(1)))
        elif kind == "tdp":
            m = re.search(r"(?:≈|~)?\s*(\d{2,4})\s*(?:W|WATT)", val)
            if m:
                result["tdp"] = max(result.get("tdp", 0), int(m.group(1)))
        elif kind == "connector":
            connectors = _parse_power_connectors(val)
            if connectors:
                current = result.setdefault("power_connectors", {})
                for connector, count in connectors.items():
                    current[connector] = max(current.get(connector, 0), count)
        elif kind == "form_factor":
            supported = extract_form_factors(val)
            if category == "Case" and supported:
                result["supports_ff"] = supported
            elif supported:
                result["form_factor"] = supported[0]
        elif kind == "psu_watt" and category == "PSU":
            m = re.search(r"\b(\d{3,4})\s*(?:W|WATT)", val)
            if m:
                result["watt"] = int(m.group(1))
        elif kind == "cooler":
            if "TDP" in label.upper():
                m = re.search(r"(\d{2,3})\s*W", val)
                if m:
                    result["rating_watt"] = int(m.group(1))
            if "HEIGHT" in label.upper() or "ความสูง" in label:
                m = re.search(r"(\d{2,3})\s*MM", val)
                if m:
                    result["height_mm"] = int(m.group(1))

    # Older JIB records flattened specification tables into one long line.
    # Limit extraction to the PCIe row so CPU 4+4-pin plugs cannot be counted
    # as GPU power plugs.
    if category in ("PSU", "GPU"):
        flat = re.sub(r"\s+", " ", specs)
        legacy_pcie = re.search(
            r"\bPCI(?:E|[ -]?E| EX| EXPRESS)\s+CONNECTOR\b\s*:?[ \t]*"
            r"(.{0,160}?)\s+(?=(?:CPU|MAINBOARD|MOTHERBOARD|MOLEX|SATA)\s+CONNECTOR\b|"
            r"POWER FACTOR CORRECTION\b|FAN SIZE\b|กำลังไฟสูงสุด)",
            flat, re.I,
        )
        if legacy_pcie:
            connectors = _parse_power_connectors(legacy_pcie.group(1))
            if connectors:
                current = result.setdefault("power_connectors", {})
                for connector, count in connectors.items():
                    current[connector] = max(current.get(connector, 0), count)

    # Advice's saved short description is slash-separated rather than a
    # key/value table (for example "2xPCIe (6+2 Pin)"). Only inspect explicit
    # PCIe clauses so other pin counts cannot be mistaken for GPU power.
    if category == "PSU":
        for match in re.finditer(
            r"\b\d+\s*[X×]\s*PCI[ -]?E\s*\(\s*(?:6\s*\+\s*2|8|6|16)\s*[- ]?PIN\s*\)",
            specs, re.I,
        ):
            connectors = _parse_power_connectors(match.group())
            current = result.setdefault("power_connectors", {})
            for connector, count in connectors.items():
                current[connector] = max(current.get(connector, 0), count)

    return result


def extract_detail_facts(category: str, details: str) -> dict:
    """Public deterministic extractor used by the offline knowledge builder."""
    return _parse_specs_text(details, category)


def parse_part(category: str, name: str, specs: str = "") -> dict:
    """
    Parse a product into compat-relevant fields.
    specs: optional 'Key: Value' text extracted from the product page (from DB).
           Fields from specs override name-based regex when both exist.
    """
    parser = PARSERS.get(category)
    base = {"category": category, "name": name}
    if parser:
        base.update(parser(name))

    # Overlay with richer data from DB specs column
    if specs:
        spec_data = _parse_specs_text(specs, category)
        for k, v in spec_data.items():
            if v is not None:
                if k == "watt" and category != "PSU":
                    continue
                if k == "recommended_psu_watt" and category != "GPU":
                    continue
                if k == "power_connectors":
                    if category == "GPU":
                        k = "power_connectors_required"
                    elif category != "PSU":
                        continue
                if k in ("tdp", "recommended_psu_watt") and base.get(k):
                    # Keep the stricter known requirement when sources disagree.
                    v = max(v, base[k])
                base[k] = v
        # Attribution covers only the explicitly sourced block, not earlier legacy fields.
        block = re.search(r"\[Verified GPU power\](.*?)\[/Verified GPU power\]", specs, re.S)
        sourced_text = block[1] if block else specs
        source = re.search(r"^Source URL:\s*(https?://\S+)\s*$", sourced_text, re.M)
        checked = re.search(r"^Source checked at:\s*(.+)$", sourced_text, re.M)
        if source:
            sourced_data = _parse_specs_text(sourced_text, category)
            sources = list(base.get("power_sources", []))
            for field in ("tdp", "recommended_psu_watt"):
                if field in sourced_data:
                    sources = [e for e in sources if not (e["url"] == source[1] and e["field"] == field)]
                    sources.append({"url": source[1], "title": "Product power specifications",
                                    "field": field, "value": sourced_data[field], "unit": "W",
                                    "checked_at": checked[1] if checked else None})
            base["power_sources"] = sources

        # The offline knowledge builder stores provenance per field because
        # two values on the same product may come from different shop pages.
        sources = list(base.get("power_sources", []))
        source_labels = {
            "tdp": "TDP",
            "recommended_psu_watt": "Recommended PSU",
        }
        for field, label in source_labels.items():
            if field not in base:
                continue
            field_url = re.search(
                rf"^{re.escape(label)} Source URL:\s*(https?://\S+)\s*$", specs, re.M
            )
            field_store = re.search(
                rf"^{re.escape(label)} Source Store:\s*(.+?)\s*$", specs, re.M
            )
            if not field_url:
                continue
            sources = [
                item for item in sources
                if not (item.get("url") == field_url[1] and item.get("field") == field)
            ]
            sources.append({
                "url": field_url[1],
                "title": f"{field_store[1] if field_store else 'Retailer'} product specifications",
                "field": field,
                "value": base[field],
                "unit": "W",
                "checked_at": None,
            })
        if sources:
            base["power_sources"] = sources

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
