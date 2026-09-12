"""Reviewed manufacturer power specifications, not LLM-generated estimates.

System PSU recommendations and graphics board consumption are different fields.
Reference GPU values are a baseline; board-specific requirements may be higher.
"""
import re

REFERENCES = [
    {
        "pattern": r"\bRTX\s*5050\b(?!\s*(?:TI|SUPER))",
        "model": "GeForce RTX 5050 desktop (NVIDIA reference)",
        "tdp": 130,
        "recommended_psu_watt": 550,
        "power_connectors_required": {"PCIe 8-pin": 1},
        "url": "https://www.nvidia.com/en-us/geforce/graphics-cards/50-series/rtx-5050/",
        "title": "NVIDIA RTX 5050 specifications",
        "checked_at": "2026-09-07",
        "scope": "reference_gpu",
    },
    {
        "pattern": r"\bRTX\s*PRO\s*5000\s+BLACKWELL\b",
        "model": "RTX PRO 5000 Blackwell desktop",
        "tdp": 300,
        "url": "https://www.leadtek.com/eng/products/workstation_graphics(2)/nvidia_rtx_pro_5000_blackwell(51030)/detail",
        "title": "Leadtek RTX PRO 5000 Blackwell specifications",
        "checked_at": "2026-09-07",
        "scope": "desktop_gpu",
    },
]


def lookup_gpu_power(name):
    if re.search(r"\b(LAPTOP|MOBILE|NOTEBOOK)\b", name, re.I):
        return None
    return next((dict(r) for r in REFERENCES if re.search(r["pattern"], name, re.I)), None)


def evidence(reference, field):
    return {k: reference[k] for k in ("url", "title", "model", "checked_at", "scope")} | {
        "field": field, "value": reference[field], "unit": "W",
    }
