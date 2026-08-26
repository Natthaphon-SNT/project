"""
IT-RECOMMEND — Deterministic Compatibility Engine
Enforces rules defined in rules/*.md. The LLM NEVER decides compatibility.
All checks return ok / severity / detail so the UI can display ✓/✗ per rule.
"""
import os
from typing import Optional
import spec_parser as sp

RULES_DIR = os.path.join(os.path.dirname(__file__), "rules")

# ─────────────────────────────────────────
# Rule knowledge loading (.md files)
# ─────────────────────────────────────────
def load_rule_files(max_chars_per_file: int = 1200) -> dict:
    """Load rules/*.md as human-readable domain knowledge (for LLM context)."""
    rules = {}
    if not os.path.isdir(RULES_DIR):
        return rules
    for fn in sorted(os.listdir(RULES_DIR)):
        if not fn.endswith(".md"):
            continue
        try:
            with open(os.path.join(RULES_DIR, fn), encoding="utf-8") as f:
                rules[fn] = f.read()[:max_chars_per_file]
        except Exception:
            continue
    return rules


def rule_summary_for_prompt() -> str:
    """Compact rule digest injected into the LLM system prompt."""
    parts = []
    for fn, content in load_rule_files(max_chars_per_file=700).items():
        parts.append(f"### {fn}\n{content}")
    return "\n".join(parts)


# ─────────────────────────────────────────
# Individual checks
# ─────────────────────────────────────────
def _get(parts, cat):
    for p in parts:
        if p.get("category") == cat:
            return p
    return None


def check_socket(parts) -> Optional[dict]:
    cpu, mb = _get(parts, "CPU"), _get(parts, "Mainboard")
    if not cpu or not mb:
        return None
    cs, ms = cpu.get("socket"), mb.get("socket")
    if not cs or not ms:
        return {"rule": "R1 CPU ↔ Mainboard Socket", "ok": True,
                "severity": "UNKNOWN",
                "detail": f"ข้ามการตรวจ (ไม่ทราบ socket จากชื่อสินค้า: CPU={cs}, MB={ms})"}
    ok = cs == ms
    return {
        "rule": "R1 CPU ↔ Mainboard Socket", "ok": ok,
        "severity": "ERROR" if not ok else "PASS",
        "detail": f"CPU socket = {cs} / Mainboard socket = {ms}" + ("" if ok else " → เข้ากันไม่ได้"),
    }


def check_ram_gen(parts) -> Optional[dict]:
    ram, mb = _get(parts, "RAM"), _get(parts, "Mainboard")
    if not ram or not mb:
        return None
    gen, support = ram.get("ddr_gen"), mb.get("ram_support")
    if not gen or not support:
        return {"rule": "R2 RAM ↔ Mainboard DDR Gen", "ok": True, "severity": "UNKNOWN",
                "detail": "ข้ามการตรวจ (ไม่ทราบ DDR generation)"}
    ok = gen in support
    return {
        "rule": "R2 RAM ↔ Mainboard DDR Gen", "ok": ok,
        "severity": "ERROR" if not ok else "PASS",
        "detail": f"RAM = {gen} / Mainboard รองรับ {', '.join(support)}" + ("" if ok else " → ใส่เข้ากันไม่ได้ทางกายภาพ"),
    }


def check_psu_watt(parts) -> Optional[dict]:
    psu = _get(parts, "PSU")
    if not psu or not psu.get("watt"):
        return None
    total_draw = 80
    known = []
    cpu, gpu = _get(parts, "CPU"), _get(parts, "GPU")
    if cpu and cpu.get("tdp"):
        total_draw += cpu["tdp"]; known.append(f"CPU {cpu['tdp']}W")
    if gpu and gpu.get("tdp"):
        total_draw += gpu["tdp"]; known.append(f"GPU {gpu['tdp']}W")
    watt = psu["watt"]
    required = int(total_draw * 1.0)
    recommended = int(total_draw * 1.25)
    if watt < required:
        return {"rule": "R3 PSU Wattage", "ok": False, "severity": "ERROR",
                "detail": f"PSU {watt}W < กำลังกินขั้นต่ำ ~{required}W ({', '.join(known) or 'ประมาณการ'}) → เครื่องจะดับ under load"}
    if watt < recommended:
        return {"rule": "R3 PSU Wattage", "ok": True, "severity": "WARNING",
                "detail": f"PSU {watt}W พอใช้ (ต้องการ ≥{required}W) แต่ควรมี headroom ≥{recommended}W"}
    return {"rule": "R3 PSU Wattage", "ok": True, "severity": "PASS",
            "detail": f"PSU {watt}W เพียงพอ (draw ~{required}W, headroom แนะนำ {recommended}W)"}


def check_high_gpu_psu(parts) -> Optional[dict]:
    gpu, psu = _get(parts, "GPU"), _get(parts, "PSU")
    if not gpu or not gpu.get("tdp") or not psu or not psu.get("watt"):
        return None
    if gpu["tdp"] >= 240 and psu["watt"] < 750:
        return {"rule": "R6 High-tier GPU PSU", "ok": False, "severity": "WARNING",
                "detail": f"GPU ระดับสูง (~{gpu['tdp']}W) ควรใช้ PSU ≥750W (ปัจจุบัน {psu['watt']}W)"}
    return None


def check_cooler_tdp(parts) -> Optional[dict]:
    cooler, cpu = _get(parts, "Cooler"), _get(parts, "CPU")
    if not cooler or not cpu:
        return None
    if not cooler.get("is_cpu_cooler"):
        return {"rule": "R4 CPU Cooler TDP", "ok": True, "severity": "UNKNOWN",
                "detail": "รายการนี้ดูเหมือนพัดลมเคส/อุปกรณ์เสริม ไม่ใช่ CPU cooler — ตรวจสอบว่ามี CPU cooler หรือไม่"}
    rating, tdp = cooler.get("rating_watt"), cpu.get("tdp")
    if rating is None or tdp is None:
        return {"rule": "R4 CPU Cooler TDP", "ok": True, "severity": "UNKNOWN",
                "detail": "ข้ามการตรวจ (ประเมิน TDP/cooler rating ไม่ได้จากชื่อสินค้า)"}
    ok = rating >= tdp
    return {"rule": "R4 CPU Cooler TDP", "ok": ok,
            "severity": "PASS" if ok else "WARNING",
            "detail": f"Cooler ~{rating}W vs CPU ~{tdp}W" + ("" if ok else " → เสี่ยง thermal throttling")}


def check_case_ff(parts) -> Optional[dict]:
    case, mb = _get(parts, "Case"), _get(parts, "Mainboard")
    if not case or not mb:
        return None
    supports, mff = case.get("supports_ff"), mb.get("form_factor")
    if not supports or not mff:
        return {"rule": "R5 Case ↔ Mainboard Form Factor", "ok": True, "severity": "UNKNOWN",
                "detail": "ข้ามการตรวจ"}
    ok = mff in supports
    return {"rule": "R5 Case ↔ Mainboard Form Factor", "ok": ok,
            "severity": "ERROR" if not ok else "PASS",
            "detail": f"Case รองรับ {', '.join(supports)} / Mainboard = {mff}" + ("" if ok else " → ใส่ไม่ลงเคส")}


def check_budget(parts_with_price, budget) -> Optional[dict]:
    if not budget:
        return None
    total = sum(p.get("price") or 0 for p in parts_with_price)
    limit = budget * 1.10
    ok = total <= limit
    return {"rule": "R7 Budget", "ok": ok,
            "severity": "PASS" if ok else "WARNING",
            "detail": f"ราคารวมจริง {total:,.0f}฿ vs งบ {budget:,.0f}฿ (เพดาน+10% = {limit:,.0f}฿)"}


ALL_CHECKS = [check_socket, check_ram_gen, check_psu_watt, check_high_gpu_psu,
              check_cooler_tdp, check_case_ff]

_SEV_ORDER = {"ERROR": 3, "WARNING": 2, "UNKNOWN": 1, "PASS": 0}

# ─────────────────────────────────────────
# Public API
# ─────────────────────────────────────────
def check_build(parts: list, budget: Optional[int] = None) -> dict:
    """
    parts: list of parsed part dicts (from spec_parser.parse_part) with optional 'price'.
    Returns frontend-compatible structure:
      {overall, summary, checks:[{item, ok, detail}], warnings, suggestions}
    overall: 'error' | 'warning' | 'ok'
    """
    checks = []
    for fn in ALL_CHECKS:
        result = fn(parts)
        if result:
            checks.append(result)

    if isinstance(budget, (int, float)) and budget > 0:
        b = check_budget(parts, budget)
        if b:
            checks.append(b)

    worst = "ok"
    for c in checks:
        sev = c.get("severity", "PASS")
        if sev == "ERROR":
            worst = "error"; break
        if sev == "WARNING":
            worst = "warning"

    errors = [c for c in checks if c.get("severity") == "ERROR"]
    warnings = [c for c in checks if c.get("severity") == "WARNING"]
    unknowns = [c for c in checks if c.get("severity") == "UNKNOWN"]
    passed = len([c for c in checks if c.get("severity") in ("PASS",)]) 

    if worst == "error":
        summary = f"❌ พบปัญหาความเข้ากันได้ {len(errors)} จุด ที่ต้องแก้ก่อนใช้งาน"
    elif worst == "warning":
        summary = f"⚠️ ใช้งานได้ แต่มีจุดควรระวัง {len(warnings)} จุด"
    else:
        summary = f"✅ ผ่านการตรวจ compatibility {passed}/{len(checks)} ข้อ"

    suggestions = []
    for e in errors + warnings:
        if e["rule"].startswith("R1"):
            suggestions.append("เปลี่ยน Mainboard ให้ตรง socket กับ CPU (หรือเปลี่ยน CPU)")
        elif e["rule"].startswith("R2"):
            suggestions.append("เปลี่ยน RAM ให้ตรง generation ที่ mainboard รองรับ")
        elif e["rule"].startswith("R3") or e["rule"].startswith("R6"):
            suggestions.append(f"อัปเกรด PSU เป็นอย่างน้อย 750W")
        elif e["rule"].startswith("R4"):
            suggestions.append("ใช้ CPU cooler ที่ rated TDP สูงกว่า CPU")

    # Frontend shape: item/ok/detail
    fe_checks = [{"item": c["rule"], "ok": bool(c["ok"]), "detail": c["detail"]} for c in checks]

    return {
        "overall": worst,
        "summary": summary,
        "checks": fe_checks,
        "warnings": [c["detail"] for c in warnings],
        "suggestions": list(dict.fromkeys(suggestions)),
        "_engine": {
            "rules_enforced": len(checks),
            "passed": passed,
            "errors": len(errors),
            "warnings": len(warnings),
            "unknown": len(unknowns),
            "deterministic": True,
        },
    }
