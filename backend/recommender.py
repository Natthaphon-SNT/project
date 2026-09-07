"""
IT-RECOMMEND — Hybrid Recommendation Layer

Pipeline:
  User intent → Budget/UseCase parsing (deterministic)
  → Candidate retrieval from Product DB (RAG, real prices)
  → LLM selection restricted to candidates (user-selected AI API)
  → Post-validation: map to real products + Compatibility Engine
  → Fallback: heuristic builder if LLM unavailable

The LLM only CHOOSES and EXPLAINS. Prices, availability and compatibility
are computed by code.
"""
import os
import re
import json
from typing import Optional

import httpx

import spec_parser as sp
import compat_engine as ce

# ─────────────────────────────────────────
PC_CATEGORIES = ["CPU", "Mainboard", "RAM", "GPU", "SSD", "PSU", "Case"]

# Budget allocation shares per use case (sum ≈ 1.0 over PC categories)
ALLOCATIONS = {
    "gaming":  {"CPU": .13, "Mainboard": .10, "RAM": .07, "GPU": .42, "SSD": .09, "PSU": .09, "Case": .07},
    "work":    {"CPU": .22, "Mainboard": .14, "RAM": .14, "GPU": .18, "SSD": .12, "PSU": .10, "Case": .07},
    "video":   {"CPU": .24, "Mainboard": .13, "RAM": .16, "GPU": .22, "SSD": .12, "PSU": .07, "Case": .05},
    "3d":      {"CPU": .23, "Mainboard": .13, "RAM": .16, "GPU": .23, "SSD": .12, "PSU": .07, "Case": .05},
    "ai":      {"CPU": .20, "Mainboard": .13, "RAM": .20, "GPU": .28, "SSD": .10, "PSU": .06, "Case": .03},
    "general": {"CPU": .22, "Mainboard": .14, "RAM": .12, "GPU": .15, "SSD": .14, "PSU": .12, "Case": .08},
}

USE_CASE_PATTERNS = [
    ("video", r"ตัดต่อ|premiere|davinci|วิดีโอ|video"),
    ("3d", r"3d|blender|maya|render|เรนเดอร์"),
    ("ai", r"\bai\b|machine learning|stable diffusion|ml\b|เทรนโมเดล"),
    ("gaming", r"เล่นเกม|เกม|gaming|game|aaa|esports"),
    ("work", r"ทำงาน|office|ออฟฟิศ|work"),
    ("general", r"ทั่วไป|general|ดูหนัง|ท่องเน็ต|เรียน"),
]

COOLER_KEYWORDS = r"AIR COOLER|LIQUID COOLER|SE-214|PA120|AS-120|FLOE|CASTLE|FORZA"


def detect_use_case(text: str) -> str:
    t = text.lower()
    for key, pat in USE_CASE_PATTERNS:
        if re.search(pat, t):
            return key
    return "general"


def detect_budget_thb(text: str) -> Optional[int]:
    """Extract upper budget bound from Thai text like '20,000–30,000 บาท'."""
    nums = [int(n.replace(",", "")) for n in re.findall(r"\d{1,3}(?:,\d{3})+|\d{4,7}", text)]
    if not nums:
        return None
    return max(nums)


def best_price(p) -> int:
    vals = [v for v in (p.p_price, p.price_advice, p.price_jib, p.price_ihavecpu) if v and v > 0]
    return int(min(vals)) if vals else 0


# ─────────────────────────────────────────
# Candidate retrieval (RAG from Product DB)
# ─────────────────────────────────────────
def select_candidates(db, budget: int, use_case: str, k_per_cat: int = 4) -> list:
    from shop_api import Product
    alloc = ALLOCATIONS.get(use_case, ALLOCATIONS["general"])
    candidates = []
    seen_ids = set()

    def fetch_cat(cat: str, target: int, k: int) -> list:
        rows = db.query(Product).filter(Product.category == cat).all()
        priced = [(r, best_price(r)) for r in rows]
        priced = [(r, pr) for r, pr in priced if pr > 0]
        # nearest-to-target first; keep some cheaper options too
        priced.sort(key=lambda x: abs(x[1] - target))
        out = []
        for r, pr in priced[:k]:
            if r.product_id not in seen_ids:
                seen_ids.add(r.product_id)
                out.append(r)
        return out

    for cat in PC_CATEGORIES:
        share = alloc.get(cat, .08)
        target = max(500, int(budget * share))
        for r in fetch_cat(cat, target, k_per_cat):
            candidates.append({
                "product_id": r.product_id,
                "specs": r.specs or "",
                "category": cat,
                "name": r.p_name,
                "price": best_price(r),
                "prices": {"advice": int(r.price_advice or 0),
                           "jib": int(r.price_jib or 0),
                           "ihavecpu": int(r.price_ihavecpu or 0)},
                "url": r.url_advice or r.url_jib or r.url_ihavecpu or "",
            })

    # Cooler candidates (Air/Liquid) as bonus options
    for cat in ("Air Cooler", "Liquid Cooler"):
        rows = db.query(Product).filter(Product.category == cat).all()
        rows = [r for r in rows if re.search(COOLER_KEYWORDS, (r.p_name or "").upper())]
        rows.sort(key=lambda r: abs(best_price(r) - max(300, int(budget * .04))))
        for r in rows[:2]:
            if r.product_id not in seen_ids:
                seen_ids.add(r.product_id)
                candidates.append({
                    "product_id": r.product_id,
                "specs": r.specs or "",
                    "category": cat,
                    "name": r.p_name,
                    "price": best_price(r),
                    "prices": {"advice": int(r.price_advice or 0),
                               "jib": int(r.price_jib or 0),
                               "ihavecpu": int(r.price_ihavecpu or 0)},
                    "url": r.url_advice or r.url_jib or r.url_ihavecpu or "",
                })

    # ── Compatibility coverage guarantee ─────────────────────────────
    # Ensure the pool contains a mainboard matching every CPU socket present
    # in the candidate set, and RAM matching every supported DDR gen.
    cpu_sockets = {sp.parse_part("CPU", c["name"]).get("socket")
                   for c in candidates if c["category"] == "CPU"}
    cpu_sockets.discard(None)

    def add_extra(cat: str, matcher, target: int):
        from shop_api import Product  # already imported above via closure
        rows = db.query(Product).filter(Product.category == cat).all()
        priced = [(r, best_price(r)) for r in rows]
        priced = [(r, pr) for r, pr in priced if pr > 0 and matcher(r)]
        priced.sort(key=lambda x: abs(x[1] - target))
        for r, pr in priced[:2]:
            if r.product_id not in seen_ids:
                seen_ids.add(r.product_id)
                candidates.append({
                    "product_id": r.product_id,
                "specs": r.specs or "",
                    "category": cat,
                    "name": r.p_name,
                    "price": pr,
                    "prices": {"advice": int(r.price_advice or 0),
                               "jib": int(r.price_jib or 0),
                               "ihavecpu": int(r.price_ihavecpu or 0)},
                    "url": r.url_advice or r.url_jib or r.url_ihavecpu or "",
                })

    mb_target = max(1000, int(budget * alloc["Mainboard"]))
    ram_target = max(800, int(budget * alloc["RAM"]))
    for soc in sorted(cpu_sockets):
        add_extra("Mainboard",
                  lambda r, s=soc: sp.parse_part("Mainboard", r.p_name or "").get("socket") == s,
                  mb_target)
        ddr = {"AM4": ["DDR4"], "LGA1200": ["DDR4"], "LGA1700": ["DDR4", "DDR5"],
               "LGA1851": ["DDR5"], "AM5": ["DDR5"]}.get(soc, [])
        for gen in ddr:
            add_extra("RAM",
                      lambda r, g=gen: sp.parse_part("RAM", r.p_name or "").get("ddr_gen") == g,
                      ram_target)

    return candidates


def candidates_to_text(candidates: list) -> str:
    lines = []
    for i, c in enumerate(candidates):
        lines.append(f"[{c['product_id']}] ({c['category']}) {c['name']} — {c['price']:,} THB")
    return "\n".join(lines)


# ─────────────────────────────────────────
# Multi-provider LLM router
PROVIDER_BASE_URLS = {
    "openai":     "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "google":     "https://generativelanguage.googleapis.com/v1beta/openai",
}

DEFAULT_MODELS = {
    "openai":     "gpt-4o-mini",
    "openrouter": "openai/gpt-4o-mini",
    "google":     "gemini-2.0-flash",
}


async def llm_chat(
    messages: list,
    provider: str = "google",
    model: str = "",
    api_key: str = "",
    temperature: float = 0.4,
    max_tokens: int = 4096,
) -> str:
    """
    Universal LLM chat that routes to the appropriate provider.
    Supported: google | openai | openrouter
    Requires a supported provider and its API key.
    """
    import asyncio as _asyncio

    provider = (provider or "google").lower()

    if provider not in PROVIDER_BASE_URLS:
        raise RuntimeError("Unsupported AI provider")
    if not api_key:
        raise RuntimeError("API key required for selected provider")

    base_url = PROVIDER_BASE_URLS[provider]
    model    = model or DEFAULT_MODELS.get(provider, "gpt-4o-mini")
    headers  = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
    }
    if provider == "openrouter":
        headers["HTTP-Referer"] = "https://it-recommend.app"
        headers["X-Title"]      = "IT-RECOMMEND"

    payload = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
    if provider == "openai" and model.startswith(("o1", "o3", "o4")):
        payload.pop("temperature")
        payload["max_completion_tokens"] = payload.pop("max_tokens")
        if model.startswith("o1-mini"):
            payload["messages"] = [{**m, "role": "user" if m["role"] == "system" else m["role"]} for m in messages]

    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                res = await client.post(
                    f"{base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                return _parse_chat_completions(res)
        except RuntimeError as e:
            if "Auth/Credits" in str(e) or "rate_limit" in str(e):
                raise
            if attempt == 1:
                raise
            await _asyncio.sleep(2)
    raise RuntimeError(f"LLM provider '{provider}' failed")


def _check_http(res: httpx.Response):
    if res.status_code == 429:
        raise RuntimeError("rate_limit")
    if res.status_code == 401 or res.status_code == 403:
        try:
            msg = res.json().get("error", {}).get("message", "")
        except Exception:
            msg = res.text[:200]
        raise RuntimeError(f"Auth/Credits error ({res.status_code}): {msg}")
    if res.status_code != 200:
        raise RuntimeError(f"AI provider error {res.status_code}: {res.text[:300]}")


def _parse_chat_completions(res: httpx.Response) -> str:
    _check_http(res)
    data = res.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise RuntimeError(f"Unexpected AI response: {json.dumps(data)[:300]}")
    if not content or not content.strip():
        # reasoning models can exhaust max_tokens before emitting content
        raise RuntimeError("LLM returned empty content (increase max_tokens)")
    return content


def _parse_responses(res: httpx.Response) -> str:
    _check_http(res)
    data = res.json()
    # convenience field first
    text = data.get("output_text")
    if text:
        return text
    chunks = []
    for item in data.get("output", []):
        if item.get("type") == "message":
            for part in item.get("content", []):
                if part.get("type") == "output_text":
                    chunks.append(part.get("text", ""))
    result = "".join(chunks)
    if not result.strip():
        raise RuntimeError("LLM returned empty output (increase max_output_tokens)")
    return result


def extract_json(text: str) -> Optional[dict]:
    """Robust JSON extraction from LLM output."""
    m = re.search(r"\{.*\}", text, re.DOTALL)
    raw = m.group(0) if m else text
    raw = re.sub(r"```json|```", "", raw).strip()
    try:
        return json.loads(raw)
    except Exception:
        return None


# ─────────────────────────────────────────
# Post-validation: map LLM parts → real products
# ─────────────────────────────────────────
def _norm(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def map_part_to_candidate(part: dict, candidates: list) -> Optional[dict]:
    pid = str(part.get("product_id") or part.get("id") or "").strip()
    if pid:
        for c in candidates:
            if c["product_id"] == pid:
                return c
    name = _norm(str(part.get("name", "")))
    if not name:
        return None
    # score by token overlap on normalized names
    best, best_score = None, 0.0
    for c in candidates:
        cname = _norm(c["name"])
        inter = len(set(re.findall(r"[A-Z0-9]+", name)) & set(re.findall(r"[A-Z0-9]+", cname)))
        score = inter / max(1, len(set(re.findall(r"[A-Z0-9]+", name))))
        if score > best_score:
            best, best_score = c, score
    return best if best_score >= 0.5 else None


def build_final_result(llm_result: dict, candidates: list, budget: Optional[int], use_case: str) -> dict:
    """Attach real products/prices + run deterministic compatibility engine."""
    parts_out, parsed_parts = [], []
    for part in llm_result.get("parts", []):
        label = sp.normalize_label(str(part.get("type", "")))
        cand = map_part_to_candidate(part, candidates)
        price = part.get("price", 0)
        if isinstance(price, str):
            digits = re.sub(r"[^\d]", "", price)
            price = int(digits) if digits else 0
        entry = {
            "type": part.get("type", ""),
            "name": cand["name"] if cand else part.get("name", ""),
            "price": f"{(cand['price'] if cand else price):,} ฿",
            "reason": part.get("reason", ""),
        }
        if cand:
            entry.update({
                "product_id": cand["product_id"],
                "real_price": cand["price"],
                "shop_prices": cand["prices"],
                "url": cand["url"],
                "matched_real_product": True,
            })
            price_for_calc = cand["price"]
        else:
            entry["matched_real_product"] = False
            price_for_calc = price
        parts_out.append(entry)

        db_cat = label if label in PC_CATEGORIES else (
            "Air Cooler" if label in ("Air Cooler", "Liquid Cooler") else None)
        if db_cat and entry["name"]:
            parsed = sp.parse_part(db_cat, entry["name"], specs=cand.get("specs", "") if cand else "")
            parsed["price"] = price_for_calc
            parsed_parts.append(parsed)

    total = sum(p.get("price") or 0 for p in parsed_parts)
    compat = ce.check_build(parsed_parts, budget)

    result = {
        "summary": llm_result.get("summary", ""),
        "totalBudget": f"{total:,} ฿ (ราคาจริงจากฐานข้อมูล)",
        "tier": llm_result.get("tier", ""),
        "useCase": use_case,
        "budgetInput": budget,
        "parts": parts_out,
        "performance": llm_result.get("performance", {}),
        "pros": llm_result.get("pros", []),
        "cons": llm_result.get("cons", []),
        "compat": compat,
        "_meta": {
            "engine": "hybrid-rag-v1",


            "compatibility": "deterministic-engine",
            "candidates_offered": len(candidates),
            "parts_matched_to_db": sum(1 for p in parts_out if p.get("matched_real_product")),
        },
    }
    return result


# ─────────────────────────────────────────
# Heuristic builder (no LLM needed)
# Compatibility-aware: CPU → matching MB → matching RAM → sized PSU → fitting Case
# ─────────────────────────────────────────
def _nearest(rows: list, target: int):
    return min(rows, key=lambda c: abs(c["price"] - target)) if rows else None


def assemble_build(candidates: list, budget: Optional[int], use_case: str,
                   alloc: Optional[dict] = None) -> dict:
    """
    Deterministically assemble one compatible build from candidates.
    alloc: optional custom category share overrides (for strategy variants).
    Returns {"picked": {cat: candidate}, "parsed": [...], "total_draw": int, "need_watt": int}
    """
    budget = budget or 25000
    base = ALLOCATIONS.get(use_case, ALLOCATIONS["general"])
    if alloc:
        base = {**base, **alloc}
    by_cat: dict = {}
    for c in candidates:
        by_cat.setdefault(c["category"], []).append(c)
    picked: dict = {}

    cpu = _nearest(by_cat.get("CPU", []), int(budget * base["CPU"]))
    total_draw, need_watt = 80, 0
    if cpu:
        picked["CPU"] = cpu
        cpu_spec = sp.parse_part("CPU", cpu["name"])
        total_draw += cpu_spec.get("tdp") or 65

        mbs = by_cat.get("Mainboard", [])
        mbs_match = [c for c in mbs
                     if sp.parse_part("Mainboard", c["name"]).get("socket") == cpu_spec.get("socket")]
        mb = _nearest(mbs_match or mbs, int(budget * base["Mainboard"]))
        if mb:
            picked["Mainboard"] = mb

        rams = by_cat.get("RAM", [])
        supported = sp.parse_part("Mainboard", mb["name"]).get("ram_support") if mb else None
        rams_match = [c for c in rams
                      if sp.parse_part("RAM", c["name"]).get("ddr_gen") in (supported or [])]
        ram = _nearest(rams_match, int(budget * base["RAM"])) if rams_match else (
            _nearest(rams, int(budget * base["RAM"])) if not supported else None)
        if ram:
            picked["RAM"] = ram

    gpu = _nearest(by_cat.get("GPU", []), int(budget * base["GPU"]))
    if gpu:
        picked["GPU"] = gpu
        total_draw += sp.parse_part("GPU", gpu["name"], specs=gpu.get("specs", "")).get("tdp") or 150
    gpu_min = sp.parse_part("GPU", gpu["name"], specs=gpu.get("specs", "")).get("recommended_psu_watt", 0) if gpu else 0
    import math
    need_watt = max(math.ceil(total_draw * 1.25), gpu_min)

    psus = by_cat.get("PSU", [])
    psu_fit = [c for c in psus
               if (sp.parse_part("PSU", c["name"], specs=c.get("specs", "")).get("watt") or 0) >= need_watt]
    psu = _nearest(psu_fit, need_watt * 1.15)
    if psu:
        picked["PSU"] = psu

    ssd = _nearest(by_cat.get("SSD", []), int(budget * base["SSD"]))
    if ssd:
        picked["SSD"] = ssd

    cases = by_cat.get("Case", [])
    mb_ff = sp.parse_part("Mainboard", picked["Mainboard"]["name"]).get("form_factor") \
        if picked.get("Mainboard") else None
    cases_fit = [c for c in cases
                 if not mb_ff or mb_ff in (sp.parse_part("Case", c["name"]).get("supports_ff") or [])]
    case = _nearest(cases_fit or cases, int(budget * base["Case"]))
    if case:
        picked["Case"] = case

    parsed = [sp.parse_part(cat, c["name"], specs=c.get("specs", "")) | {"price": c["price"]}
              for cat, c in picked.items()]
    return {"picked": picked, "parsed": parsed,
            "total_draw": total_draw, "need_watt": need_watt}


def heuristic_build(candidates: list, budget: Optional[int], use_case: str) -> dict:
    built = assemble_build(candidates, budget, use_case)
    picked = built["picked"]
    reason_map = {
        "CPU": "สมดุลกับงบและการใช้งาน",
        "Mainboard": "socket ตรงกับ CPU — เลือกโดย compatibility engine",
        "RAM": "generation ตรงกับที่ mainboard รองรับ",
        "GPU": "ตัวขับประสิทธิภาพหลักภายใต้งบ",
        "SSD": "NVMe เพียงพอสำหรับ OS และโปรแกรม",
        "PSU": f"เลือกตามเกณฑ์ประมาณการ ≥{built['need_watt']}W; ดูผลตรวจ PSU และแหล่งอ้างอิงประกอบ",
        "Case": "รองรับ form factor ของ mainboard",
    }
    parts = [{"type": cat, "product_id": c["product_id"], "name": c["name"],
              "price": c["price"], "reason": reason_map.get(cat, "")}
             for cat, c in picked.items()]
    llm_like = {"summary": "จัดสเปคโดย heuristic engine และตรวจ compatibility แบบ deterministic "
                           "(โหมด offline — AI provider ไม่พร้อมใช้งาน)",
                "tier": "", "performance": {}, "pros": [], "cons": [], "parts": parts}
    return build_final_result(llm_like, candidates, budget, use_case)


# ─────────────────────────────────────────
# Main entry points
# ─────────────────────────────────────────
SYSTEM_PROMPT_TEMPLATE = """คุณคือ IT-RECOMMEND AI ผู้เชี่ยวชาญฮาร์ดแวร์คอมพิวเตอร์ในประเทศไทย

== กฎเหล็ก ==
1. เลือกสินค้าได้ "เฉพาะ" จากรายการ candidate ด้านล่างเท่านั้น — ห้ามแต่งชื่อสินค้าขึ้นมาเอง
2. อ้าง product_id ของสินค้าที่เลือกกลับมาใน field "product_id" ของแต่ละ part
3. ใช้ราคาที่ระบุใน candidate list เท่านั้น ห้ามประเมินราคาเอง
4. ต้องเข้ากันได้จริง: socket CPU ↔ Mainboard, DDR gen ↔ Mainboard, PSU watt ≥ ระบบ, form factor ↔ case
5. ราคารวมต้องไม่เกินงบที่ผู้ใช้กำหนดเกิน ~10%
6. ตอบเป็น JSON เท่านั้น ห้ามมี text อื่นนอก JSON

== Domain Rules ของระบบ (enforced โดย compatibility engine หลังจากนี้) ==
{rules}

== รูปแบบ JSON ==
{{
  "summary": "สรุปสเปคโดยรวม 2 ประโยค",
  "totalBudget": "ประมาณการรวม เช่น 27,500 ฿",
  "tier": "Entry-level / Mid-range / High-end / Enthusiast",
  "parts": [
    {{"type":"CPU","product_id":"...","name":"...","price":"...","reason":"..."}},
    {{"type":"Mainboard","product_id":"...","name":"...","price":"...","reason":"..."}},
    {{"type":"RAM","product_id":"...","name":"...","price":"...","reason":"..."}},
    {{"type":"GPU","product_id":"...","name":"...","price":"...","reason":"..."}},
    {{"type":"Storage","product_id":"...","name":"...","price":"...","reason":"..."}},
    {{"type":"PSU","product_id":"...","name":"...","price":"...","reason":"..."}},
    {{"type":"Case","product_id":"...","name":"...","price":"...","reason":"..."}},
    {{"type":"Cooler","product_id":"...","name":"...","price":"...","reason":"..."}}
  ],
  "performance": {{"gaming":"...","productivity":"...","upgrade":"..."}},
  "pros": ["..."], "cons": ["..."]
}}"""


async def recommend_build(db, prompt: str, extra: str = "", candidates: Optional[list] = None,
                          provider: str = "google", model: str = "", api_key: str = "") -> dict:
    budget = detect_budget_thb(prompt)
    use_case = detect_use_case(prompt)
    budget_eff = budget or 25000
    if candidates is None:
        candidates = select_candidates(db, budget_eff, use_case)

    rules_digest = ce.rule_summary_for_prompt()
    system = SYSTEM_PROMPT_TEMPLATE.format(rules=rules_digest)
    user = (
        f"== ความต้องการผู้ใช้ ==\n{prompt}\n"
        + (f"รายละเอียดเพิ่มเติม: {extra}\n" if extra else "")
        + f"\n== Candidates จากฐานข้อมูลสินค้าจริง (งบเป้าหมาย {budget_eff:,} THB, usage={use_case}) ==\n"
        + candidates_to_text(candidates)
    )

    try:
        text = await llm_chat(
            [{"role": "system", "content": system},
             {"role": "user", "content": user}],
            provider=provider, model=model, api_key=api_key,
            temperature=0.4,
        )
        llm_result = extract_json(text)
        if not llm_result or not llm_result.get("parts"):
            raise RuntimeError("LLM returned invalid JSON")
        result = build_final_result(llm_result, candidates, budget, use_case)
        result["_meta"].update(llm_provider=provider, llm_model=model or DEFAULT_MODELS[provider])
        return result
    except RuntimeError:
        raise
    except Exception:
        # Graceful degradation: deterministic heuristic build, still validated
        return heuristic_build(candidates, budget, use_case)


async def compat_check_hybrid(parts_text: str, provider: str = "google", model: str = "", api_key: str = "") -> dict:
    """
    Deterministic-first compatibility check.
    Parses pasted spec lines into parts via spec_parser, validates with the
    engine, then asks the LLM only for extra suggestions (optional).
    """
    lines = [ln.strip() for ln in parts_text.splitlines() if ln.strip()]
    parsed = []
    unmatched = []
    for ln in lines:
        p = sp.parse_free_text_line(ln)
        if p:
            parsed.append(p)
        elif len(ln) > 3:
            unmatched.append(ln)

    result = ce.check_build(parsed)

    if unmatched:
        result["warnings"].append("ไม่สามารถระบุหมวดหมู่ของ: " + ", ".join(unmatched[:5]))

    # Optional LLM enrichment of suggestions (never overrides verdict)
    if api_key:
        try:
            verdict = json.dumps(result, ensure_ascii=False)
            text = await llm_chat(
                [{"role": "system", "content":
                  "คุณเป็นผู้เชี่ยวชาญ PC hardware ช่วยเสนอคำแนะนำเพิ่มเติมจากผลตรวจ deterministic "
                  "ตอบเป็น JSON array ของ string เท่านั้น ไม่เกิน 4 ข้อ สั้น ๆ ภาษาไทย"},
                 {"role": "user", "content": f"ผลตรวจ:\n{verdict}\n\nรายการ input:\n{parts_text}"}],
                temperature=0.3, max_tokens=2000, provider=provider, model=model, api_key=api_key,
            )
            arr_m = re.search(r"\[.*\]", text, re.DOTALL)
            if arr_m:
                extra_suggestions = json.loads(arr_m.group(0))
                if isinstance(extra_suggestions, list):
                    result["suggestions"] = list(dict.fromkeys(
                        result["suggestions"] + [str(s) for s in extra_suggestions]))[:8]
        except Exception:
            pass

    result["_engine"]["input_lines_parsed"] = len(parsed)
    result["_engine"]["deterministic"] = True
    return result


async def compare_specs(spec1: str, spec2: str,
                        provider: str = "google", model: str = "", api_key: str = "", context: str = "") -> str:
    """LLM passthrough comparison (returns raw text for frontend parseJson)."""
    prompt = (
        "คุณคือผู้เชี่ยวชาญคอมพิวเตอร์ในประเทศไทย เปรียบเทียบสเปค 2 ชุดนี้อย่างละเอียดและตรงไปตรงมา:\n\n"
        f"ชุดที่ 1: {spec1}\nชุดที่ 2: {spec2}\n\n"
        "== กฎการเปรียบเทียบ ==\n"
        "1. อ้างอิง benchmark จริง เช่น FPS, Cinebench R23, Blender time\n"
        "2. คำนึงถึงราคาตลาดไทยปัจจุบัน\n"
        "3. บอกชัดเจนว่าแต่ละ category อันไหนชนะและทำไม\n\n"
        "ตอบเป็น JSON เท่านั้น ห้ามมี text นอก JSON:\n"
        '{"spec1Name":"...","spec2Name":"...","winner":"1|2|tie","verdict":"...",'
        '"categories":[{"name":"...","spec1":"...","spec2":"...","winner":"..."}],'
        '"spec1Pros":["..."],"spec2Pros":["..."],"recommendation":"..."}'
    )
    return await llm_chat(
        [{"role": "system", "content": "คุณคือ IT-RECOMMEND AI ตอบเป็น JSON เท่านั้น"},
         {"role": "user", "content": prompt + "\n" + context}],
        provider=provider, model=model, api_key=api_key,
        temperature=0.4,
    )


# ─────────────────────────────────────────
# Top-3 scored alternatives (deterministic + LLM explanation)
# ─────────────────────────────────────────
def _format_variant(built: dict, use_case: str, candidates: list) -> dict:
    picked, built_info = built["picked"], built
    reason_map = {
        "CPU": "สมดุลกับงบและการใช้งาน",
        "Mainboard": "socket ตรงกับ CPU",
        "RAM": "generation ตรงกับ mainboard",
        "GPU": "ตัวขับประสิทธิภาพหลัก",
        "SSD": "NVMe สำหรับ OS และโปรแกรม",
        "PSU": f"เลือกตามเกณฑ์ประมาณการ ≥{built_info['need_watt']}W; ดูผลตรวจ PSU ประกอบ",
        "Case": "รองรับ form factor",
    }
    cand_by_id = {c["product_id"]: c for c in candidates}
    parts = []
    for cat, c in picked.items():
        full = cand_by_id.get(c["product_id"], c)
        parts.append({
            "type": cat, "product_id": c["product_id"], "name": c["name"],
            "price": c["price"], "reason": reason_map.get(cat, ""),
            "shop_prices": full.get("prices", {}),
            "url": full.get("url", ""),
            "matched_real_product": True,
        })
    return {"parts": parts}


def top3_builds(candidates: list, budget: Optional[int], use_case: str) -> list:
    """
    Generate deterministic build variants → score each with the weighted
    scoring engine → return the best build per strategy (max 3).
    """
    import scoring_engine as se

    alloc_variants = [
        None,                                  # base allocation
        {"GPU": .48, "CPU": .10},              # GPU-heavy
        {"GPU": .28, "CPU": .27, "RAM": .18},  # CPU/RAM-heavy
        {"GPU": .38, "CPU": .16, "SSD": .12},  # balanced+
    ]

    scored_variants = []
    for alloc in alloc_variants:
        built = assemble_build(candidates, budget or 25000, use_case, alloc=alloc)
        if not built["picked"]:
            continue
        scores = se.score_build(built["parsed"], list(built["picked"].values()),
                                budget, use_case)
        upgrade = se.score_upgrade_path(built["parsed"])
        scored_variants.append({"built": built, "scores": scores, "_upgrade": upgrade})

    if not scored_variants:
        return []

    picks = {
        "performance": max(scored_variants,
                           key=lambda v: (v["scores"]["breakdown"]["performance"],
                                          v["scores"]["score"])),
        "value":       max(scored_variants,
                           key=lambda v: (v["scores"]["breakdown"]["budget"],
                                          v["scores"]["score"])),
        "upgrade":     max(scored_variants,
                           key=lambda v: (v["_upgrade"], v["scores"]["score"])),
    }

    strategy_labels = {
        "performance": ("Gaming Performance", "ประสิทธิภาพสูงสุดภายในงบ"),
        "value":       ("Best Value", "คุ้มค่าที่สุดเมื่อเทียบระดับราคา"),
        "upgrade":     ("Upgradeability", "แพลตฟอร์มใหม่ + PSU headroom สำหรับอัปเกรด"),
    }

    alternatives = []
    seen_pids = set()
    for key in ("performance", "value", "upgrade"):
        v = picks[key]
        label, desc = strategy_labels[key]
        formatted = _format_variant(v["built"], use_case, candidates)
        pids = tuple(sorted(p.get("product_id", "") for p in formatted["parts"]))
        if pids in seen_pids:
            continue
        seen_pids.add(pids)
        total = sum(p["price"] for p in formatted["parts"])
        alternatives.append({
            "strategy": key,
            "label": label,
            "description": desc,
            "score": v["scores"]["score"],
            "breakdown": {k: round(x, 1) for k, x in v["scores"]["breakdown"].items()},
            "weights": se.WEIGHTS,
            "total_price": total,
            "compat_overall": v["scores"]["compat"]["overall"],
            "compat": v["scores"]["compat"],
            **formatted,
        })
    alternatives.sort(key=lambda a: -a["score"])
    return alternatives


async def recommend_with_alternatives(db, prompt: str, extra: str = "",
                                      provider: str = "google", model: str = "", api_key: str = "") -> dict:
    """Full pipeline: primary LLM build + Top-3 deterministic scored builds."""
    budget = detect_budget_thb(prompt)
    use_case = detect_use_case(prompt)
    budget_eff = budget or 25000
    candidates = select_candidates(db, budget_eff, use_case)

    result = await recommend_build(db, prompt, extra=extra, candidates=candidates,
                                   provider=provider, model=model, api_key=api_key)
    alternatives = top3_builds(candidates, budget_eff, use_case)

    # ── Auto-repair: if the LLM primary build failed compatibility, promote
    # the best verified alternative instead (LLM never overrides the engine).
    if result["compat"]["overall"] == "error" and alternatives:
        safe = next((a for a in alternatives if a["compat_overall"] != "error"), None)
        if safe:
            rejected = {
                "summary": result.get("summary", ""),
                "parts_count": len(result.get("parts", [])),
                "compat": result["compat"],
                "reason": "LLM build ไม่ผ่าน compatibility engine — ระบบส่งต่อชุดที่ผ่านการตรวจแล้ว",
            }
            total = sum(p["price"] for p in safe["parts"])
            result = {
                "summary": f"[auto-corrected] {safe['description']} — "
                           f"build จาก LLM ถูก engine ปฏิเสธ ระบบจึงส่งชุดที่ผ่านการตรวจแล้ว",
                "totalBudget": f"{total:,} ฿ (ราคาจริงจากฐานข้อมูล)",
                "tier": "",
                "useCase": use_case,
                "budgetInput": budget,
                "parts": safe["parts"],
                "performance": {}, "pros": [], "cons": [],
                "compat": safe["compat"],
                "_meta": {"engine": "hybrid-rag-v1",
                           "compatibility": "deterministic-engine",
                          "auto_corrected": True},
                "_rejected_primary": rejected,
            }

    result["alternatives"] = alternatives

    # AI explains the ranking — numbers come from the scoring engine, not the LLM
    ranking_summary = "\n".join(
        f"- {a['label']} ({a['description']}): score {a['score']}/100, "
        f"breakdown={a['breakdown']}, total {a['total_price']:,} THB"
        for a in alternatives)
    explanation_text = ""
    if (api_key) and alternatives:
        try:
            explanation_text = await llm_chat(
                [{"role": "system", "content":
                  "คุณคือ IT-RECOMMEND AI อธิบายเหตุผลการจัดอันดับ build อย่างสั้น กระชับ ภาษาไทย "
                  "(4-6 ประโยค) อ้างอิงเฉพาะตัวเลข score/breakdown/ราคาที่ให้ไว้เท่านั้น ห้ามเดาตัวเลขเอง"},
                 {"role": "user", "content":
                  f"ผู้ใช้: {prompt}\nงบ: {budget_eff} THB\n"
                  f"ผลการจัดอันดับจาก Scoring Engine (Performance 40% / Budget 25% / "
                  f"Compatibility 20% / Preference 10% / Availability 5%):\n{ranking_summary}\n"
                  "อธิบายว่าทำไมชุดแรกเหมาะกับผู้ใช้มากที่สุด และ trade-off ของแต่ละชุด"}],
                temperature=0.4, max_tokens=2000, provider=provider, model=model, api_key=api_key,
            )
        except Exception:
            explanation_text = ""
    if not explanation_text:
        if alternatives:
            best = alternatives[0]
            explanation_text = (
                f"ชุด \"{best['label']}\" ได้คะแนนรวมสูงสุด {best['score']}/100 "
                f"(Performance {best['breakdown']['performance']}, Budget efficiency "
                f"{best['breakdown']['budget']}, Compatibility {best['breakdown']['compatibility']}) "
                f"ที่ราคารวม {best['total_price']:,}฿ — คำนวณโดย Scoring Engine "
                f"(Performance 40%, Budget 25%, Compatibility 20%, Preference 10%, Availability 5%)")
        else:
            explanation_text = "ไม่สามารถสร้างทางเลือกเพิ่มเติมได้จากข้อมูลสินค้าปัจจุบัน"
    result["ranking_explanation"] = explanation_text.strip()
    result["_meta"]["scoring_engine"] = "weighted-v1 (P40/B25/C20/Pref10/A5)"
    result["_meta"]["alternatives_count"] = len(alternatives)
    return result
