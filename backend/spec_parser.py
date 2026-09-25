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


def detect_stock_cooler_included(product_name: str, specs: str = "") -> Optional[bool]:
    """Return True/False only when the CPU cooling bundle can be determined.

    Retailers expose this inconsistently as a table field, Thai prose, a name
    suffix, or a tray/K-series model marker. Unknown is intentionally None so
    the recommender does not invent a mandatory part without evidence.
    """
    name = product_name or ""
    combined = f"{name}\n{specs or ''}"
    normalized = re.sub(r"\s+", " ", combined).upper()

    excluded_patterns = (
        r"CPU\s*COOLER\s*(?:[:：-]\s*)?(?:NO|NONE|NOT\s+INCLUDED)",
        r"(?:CPU\s*)?COOLER\s+(?:IS\s+)?NOT\s+INCLUDED",
        r"WITHOUT\s+(?:A\s+)?(?:CPU\s+)?COOLER",
        r"ระบบระบายความร้อน\s*ไม่(?:ได้)?รวม(?:อยู่ในสินค้า)?",
        r"ไม่รวมระบบระบายความร้อน",
        r"ซีพียูคูลเลอร์\s*[:：-]?\s*(?:ไม่มี|ไม่รวม)",
    )
    if any(re.search(pattern, normalized, re.I) for pattern in excluded_patterns):
        return False
    if re.search(r"\(\s*TRAY\s*\)|\bTRAY\s*(?:CPU|PROCESSOR)?\b", name, re.I):
        return False
    # Intel unlocked desktop K/KF/KS SKUs normally require an aftermarket
    # thermal solution even when a retailer omits the bundle field.
    if re.search(
        r"\b(?:I[3579][ -]?\d{4,5}|CORE(?:\s+ULTRA)?\s+[3579]\s+\d{3,5})"
        r"K(?:F|S)?\b",
        name,
        re.I,
    ):
        return False

    included_patterns = (
        r"CPU\s*COOLER\s*(?:[:：-]\s*)?(?:YES|INCLUDED)",
        r"(?:WITH|INCLUDES?)\s+(?:AMD\s+|INTEL\s+)?(?:STOCK\s+)?(?:CPU\s+)?COOLER",
        r"\bWRAITH\s+(?:STEALTH|SPIRE|PRISM)\b",
        r"ซีพียูคูลเลอร์\s*[:：-]?\s*(?:มี|แถม)",
        r"(?:แถม|รวม)\s*(?:พัดลม|ฮีตซิงก์|ชุดระบายความร้อน)",
    )
    if any(re.search(pattern, normalized, re.I) for pattern in included_patterns):
        return True
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
    return {
        "category": "CPU",
        "socket": socket,
        "tdp": tdp,
        "stock_cooler_included": detect_stock_cooler_included(name),
    }


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
    cap_m = re.search(r"(\d{1,3})\s*GB", u)
    speed_m = re.search(r"(\d{3,5})\s*MHZ", u)
    capacity_gb = int(cap_m.group(1)) if cap_m else None
    module_count = None
    kit_m = re.search(r"\(\s*\d{1,3}\s*[X×]\s*([1-8])\s*\)", u)
    if kit_m:
        module_count = int(kit_m.group(1))
    else:
        count_first = re.search(r"\b([1-8])\s*[X×]\s*\d{1,3}\s*GB\b", u)
        count_after = re.search(r"\b\d{1,3}\s*GB\s*[X×]\s*([1-8])\b", u)
        kit_words = re.search(r"(?:KIT\s*(?:OF)?|DUAL\s*CHANNEL)\s*([1-8])?", u)
        if count_first:
            module_count = int(count_first.group(1))
            module_size = re.search(r"\b[1-8]\s*[X×]\s*(\d{1,3})\s*GB\b", u)
            if module_size:
                capacity_gb = module_count * int(module_size.group(1))
        elif count_after:
            module_count = int(count_after.group(1))
            module_size = re.search(r"\b(\d{1,3})\s*GB\s*[X×]\s*[1-8]\b", u)
            if module_size:
                capacity_gb = module_count * int(module_size.group(1))
        elif "DUAL CHANNEL" in u:
            module_count = 2
        elif kit_words and kit_words.group(1):
            module_count = int(kit_words.group(1))
    return {"category": "RAM", "ddr_gen": ddr,
            "capacity_gb": capacity_gb,
            "speed_mhz": int(speed_m.group(1)) if speed_m else None,
            "module_count": module_count,
            "dual_channel": module_count is not None and module_count >= 2}


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


def parse_case_radiator_support(specs: str) -> list[int] | None:
    """Read only an explicitly labelled radiator table, never case fan sizes."""
    lines = (specs or "").splitlines()
    for index, line in enumerate(lines):
        label = re.search(r"(?:Radiator Support|Liquid Cooling Support|รองรับหม้อน้ำ)\s*:?(.*)$", line, re.I)
        if not label:
            continue
        section = [label.group(1)]
        for next_line in lines[index + 1:index + 8]:
            value = next_line.strip()
            if re.match(r"^(?:[-•]\s*)?(?:top|right|bottom|front|rear|side)\s*[:：]", value, re.I):
                section.append(value)
            else:
                break
        sizes = {int(value) for value in re.findall(
            r"(?<!\d)(?:120|140|240|280|360|420)(?!\d)", " ".join(section)
        )}
        if sizes:
            return sorted(sizes)
    return None


COOLER_TDP_SKIP_REASON = "ข้ามการตรวจ (ประเมิน TDP/cooler rating ไม่ได้จากชื่อสินค้า)"

COOLER_SOCKET_ORDER = (
    "LGA115X", "LGA1150", "LGA1151", "LGA1155", "LGA1156",
    "LGA1200", "LGA1700", "LGA1851", "LGA2011", "LGA2066",
    "AM4", "AM5",
)


def extract_cooler_sockets(text: str) -> list[str]:
    """Extract every CPU socket explicitly listed in cooler specifications."""
    u = re.sub(r"\s+", " ", (text or "").upper())
    found = set(re.findall(r"\bAM[45]\b", u))

    for token in re.findall(
        r"\bLGA[\s-]*(115X|1150|1151|1155|1156|1200|1700|1851|2011|2066)\b",
        u,
    ):
        found.add(f"LGA{token}")

    # Retailer tables sometimes write one LGA prefix followed by a list,
    # for example "Intel LGA 115x/1200/1700/1851".
    for match in re.finditer(r"\b(?:INTEL\s*:?[\s]*)?LGA[\s-]*([0-9X,\s/|-]{3,80})", u):
        for token in re.findall(r"\b(?:115X|1150|1151|1155|1156|1200|1700|1851|2011|2066)\b", match.group(1)):
            found.add(f"LGA{token}")

    # Advice can omit LGA before the Intel list after this explicit label.
    for match in re.finditer(r"(?:CPU\s*)?SOCKET(?:\s+SUPPORT)?\s*:?[\s]*(.{0,180})", u):
        segment = match.group(1).split("AMD", 1)[0]
        for token in re.findall(r"\b(?:1150|1151|1155|1156|1200|1700|1851|2011|2066)\b", segment):
            found.add(f"LGA{token}")

    return [socket for socket in COOLER_SOCKET_ORDER if socket in found]


def estimate_cooler_tdp_tier(product_name: str, specs: dict) -> dict:
    """Estimate a cooler capacity tier without inventing an exact TDP rating.

    Product-name radiator tokens are the strongest signal. Structured facts
    parsed from retailer specifications are used only when the name does not
    contain a usable radiator size. Unknown inputs always return a safe skip
    result instead of raising an exception.
    """
    unknown = {
        "tdp_tier": None,
        "estimated_watt_range": None,
        "radiator_mm": None,
        "cooler_type": "unknown",
        "confidence": "unknown",
        "skip_reason": COOLER_TDP_SKIP_REASON,
    }
    try:
        facts = specs if isinstance(specs, dict) else {}
        name = product_name or ""
        upper_name = name.upper()
        category = str(facts.get("category") or "").upper()
        type_hint = str(facts.get("cooler_type") or "").lower()

        aio_by_text = bool(re.search(
            r"\b(?:AIO|LIQUID\s+COOL(?:ER|ING)|WATER\s+COOL(?:ER|ING))\b|ชุดน้ำ",
            name,
            re.I,
        ))
        air_by_text = bool(re.search(r"\bAIR\s+COOL(?:ER|ING)\b", name, re.I))
        tower_count = _safe_positive_int(facts.get("tower_count"))

        if type_hint in ("aio", "liquid") or "LIQUID COOLER" in category or aio_by_text:
            cooler_type = "aio"
        elif type_hint == "air" or "AIR COOLER" in category or air_by_text or tower_count:
            cooler_type = "air"
        else:
            cooler_type = "unknown"

        # Name priority: standard radiator numbers (including bare numbers used
        # by model names), L36/L24 shorthand, and RX360-style tokens.
        radiator_mm = None
        size_match = re.search(
            r"(?<!\d)(?:MM\s*[- ]*)?(240|280|360|420)(?:\s*MM)?(?!\d)",
            upper_name,
        )
        if size_match:
            radiator_mm = int(size_match.group(1))
        else:
            l_match = re.search(r"\bL\s*[- ]?(24|28|36|42)\b", upper_name)
            if l_match:
                radiator_mm = int(l_match.group(1)) * 10
            else:
                rx_match = re.search(r"\bRX\s*[- ]?(240|280|360|420)\b", upper_name)
                if rx_match:
                    radiator_mm = int(rx_match.group(1))

        if radiator_mm is not None and cooler_type != "air":
            cooler_type = "aio"
            tier = _aio_tdp_tier(radiator_mm)
            if tier:
                label, watt_range = tier
                return {
                    "tdp_tier": label,
                    "estimated_watt_range": watt_range,
                    "radiator_mm": radiator_mm,
                    "cooler_type": cooler_type,
                    "confidence": "name",
                    "skip_reason": None,
                }

        # Spec fallback for AIO products: derive nominal radiator length from
        # fan count and fan size (3 x 120 mm => approximately 360 mm).
        if cooler_type == "aio":
            fan_count = _safe_positive_int(facts.get("fan_count"))
            fan_size_mm = _safe_positive_int(facts.get("fan_size_mm"))
            if fan_count and fan_size_mm:
                estimated_radiator = fan_count * fan_size_mm
                tier = _aio_tdp_tier(estimated_radiator)
                if tier:
                    label, watt_range = tier
                    return {
                        "tdp_tier": label,
                        "estimated_watt_range": watt_range,
                        "radiator_mm": estimated_radiator,
                        "cooler_type": "aio",
                        "confidence": "spec",
                        "skip_reason": None,
                    }

        # Air products deliberately use broad ranges. A dual tower is only
        # promoted to medium when the heatsink is known to exceed 150 mm.
        if cooler_type == "air":
            height = _safe_positive_int(
                facts.get("heatsink_height_mm") or facts.get("height_mm")
            )
            if tower_count == 2 and height and height > 150:
                return {
                    "tdp_tier": "medium",
                    "estimated_watt_range": (150, 180),
                    "radiator_mm": None,
                    "cooler_type": "air",
                    "confidence": "spec",
                    "skip_reason": None,
                }
            if tower_count == 1:
                return {
                    "tdp_tier": "low",
                    "estimated_watt_range": (65, 95),
                    "radiator_mm": None,
                    "cooler_type": "air",
                    "confidence": "spec",
                    "skip_reason": None,
                }

        unknown["cooler_type"] = cooler_type
        unknown["radiator_mm"] = radiator_mm
        return unknown
    except (TypeError, ValueError, AttributeError):
        return unknown


def _safe_positive_int(value) -> Optional[int]:
    try:
        number = int(value)
        return number if number > 0 else None
    except (TypeError, ValueError):
        return None


def _aio_tdp_tier(radiator_mm: int) -> Optional[tuple[str, tuple[int, int]]]:
    if radiator_mm >= 360:
        return "high", (200, 280)
    if 240 <= radiator_mm <= 280:
        return "medium", (150, 200)
    return None


def _extract_cooler_geometry(specs: str) -> dict:
    """Extract only physical cooler facts needed by the tier estimator."""
    text = specs or ""
    upper = re.sub(r"\s+", " ", text.upper())
    result = {}

    combined_fan = re.search(
        r"(?<!\d)([1-4])\s*[X×]\s*(80|92|120|140)\s*MM\b", upper
    )
    if combined_fan:
        result["fan_count"] = int(combined_fan.group(1))
        result["fan_size_mm"] = int(combined_fan.group(2))
    else:
        count_match = re.search(
            r"(?:NUMBER\s+OF\s+FANS?|FAN\s+(?:COUNT|QUANTITY)|จำนวนพัดลม)\s*[:：]?\s*([1-4])\b",
            upper,
        )
        size_match = re.search(
            r"(?:FAN\s+SIZE|ขนาดพัดลม)\s*[:：]?\s*(80|92|120|140)\s*MM\b",
            upper,
        )
        if count_match:
            result["fan_count"] = int(count_match.group(1))
        if size_match:
            result["fan_size_mm"] = int(size_match.group(1))

    if re.search(r"\b(?:DUAL|DOUBLE|2)\s*[- ]?TOWER\b|ฮีตซิงก์\s*2\s*(?:ตอน|ทาวเวอร์)", upper):
        result["tower_count"] = 2
    elif re.search(r"\b(?:SINGLE|1)\s*[- ]?TOWER\b|ฮีตซิงก์\s*1\s*(?:ตอน|ทาวเวอร์)", upper):
        result["tower_count"] = 1

    height_match = re.search(
        r"(?:HEATSINK\s+HEIGHT|COOLER\s+HEIGHT|MAX(?:IMUM)?\s+COOLER\s+HEIGHT|ความสูง(?:ฮีตซิงก์)?)"
        r"\s*[:：]?\s*(\d{2,3})\s*MM\b",
        upper,
    )
    if height_match:
        result["heatsink_height_mm"] = int(height_match.group(1))
    return result

def parse_cooler(name: str) -> dict:
    """Identify CPU coolers; capacity estimation is applied in parse_part."""
    u = name.upper()
    is_cpu_cooler = bool(re.search(
        r"AIR COOL(?:ER|ING)|LIQUID COOL(?:ER|ING)|WATER COOL(?:ER|ING)|CPU COOL|AIO|HEATSINK|"
        r"\bSE-214|\bPA120|\bAS-120|FLOE|CASTLE|FORZA|LB240|LB360|LT240|LT360|DRP|HYPER\s?212|ASSASSIN|"
        r"\bL\s*[- ]?(?:24|28|36|42)\b|(?<!\d)(?:240|280|360|420)(?:\s*MM)?(?!\d)", u))
    result = {"category": "Cooler", "is_cpu_cooler": is_cpu_cooler, "rating_watt": None}
    sockets = extract_cooler_sockets(name)
    if sockets:
        result["sockets"] = sockets
    if re.search(r"LIQUID COOL(?:ER|ING)|AIO|WATER COOL(?:ER|ING)", u):
        radiator = re.search(r"(?<!\d)(120|140|240|280|360|420)(?!\d)", u)
        if radiator:
            result["radiator_size_mm"] = int(radiator.group(1))
        elif re.search(r"\bL\s*[- ]?36\b", u):
            result["radiator_size_mm"] = 360
    return result


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
    "Air Cooler": parse_cooler,
    "Liquid Cooler": parse_cooler,
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

    if category in ("Cooler", "Air Cooler", "Liquid Cooler"):
        result.update(_extract_cooler_geometry(specs))
        sockets = extract_cooler_sockets(specs)
        if sockets:
            result["sockets"] = sockets
            result.pop("socket", None)
        # A cooler's TDP field is cooling capacity, not component power draw.
        if result.get("tdp") is not None:
            result["rating_watt"] = max(result.get("rating_watt", 0), result.pop("tdp"))
        if result.get("height_mm") and not result.get("heatsink_height_mm"):
            result["heatsink_height_mm"] = result["height_mm"]

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
        if category == "Case":
            radiator_sizes = parse_case_radiator_support(specs)
            if radiator_sizes:
                base["radiator_support_mm"] = radiator_sizes
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

    if category in ("Cooler", "Air Cooler", "Liquid Cooler"):
        estimate_specs = dict(base)
        # parse_cooler normalizes category to "Cooler"; keep the database
        # category as a stronger air/liquid type hint for the estimator.
        estimate_specs["category"] = category
        estimate = estimate_cooler_tdp_tier(name, estimate_specs)
        base.update(estimate)
        if estimate.get("radiator_mm") is not None:
            base["radiator_size_mm"] = estimate["radiator_mm"]

    if category == "CPU":
        stock_cooler = detect_stock_cooler_included(name, specs)
        if stock_cooler is not None:
            base["stock_cooler_included"] = stock_cooler

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
