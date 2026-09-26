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
BASE_MANDATORY_CATEGORIES = tuple(PC_CATEGORIES)

# Budget allocation shares per use case (sum ≈ 1.0 over PC categories)
ALLOCATIONS = {
    "gaming":  {"CPU": .13, "Mainboard": .10, "RAM": .07, "GPU": .42, "SSD": .09, "PSU": .09, "Case": .07},
    "work":    {"CPU": .22, "Mainboard": .14, "RAM": .14, "GPU": .18, "SSD": .12, "PSU": .10, "Case": .07},
    "video":   {"CPU": .24, "Mainboard": .13, "RAM": .16, "GPU": .22, "SSD": .12, "PSU": .07, "Case": .05},
    "3d":      {"CPU": .23, "Mainboard": .13, "RAM": .16, "GPU": .23, "SSD": .12, "PSU": .07, "Case": .05},
    "ai":      {"CPU": .20, "Mainboard": .13, "RAM": .20, "GPU": .28, "SSD": .10, "PSU": .06, "Case": .03},
    "virtualization": {"CPU": .24, "Mainboard": .13, "RAM": .22, "GPU": .12, "SSD": .14, "PSU": .08, "Case": .05},
    "general": {"CPU": .22, "Mainboard": .14, "RAM": .12, "GPU": .15, "SSD": .14, "PSU": .12, "Case": .08},
}

USE_CASE_PATTERNS = [
    ("video", r"ตัดต่อ|premiere|davinci|วิดีโอ|video"),
    ("3d", r"3d|blender|maya|render|เรนเดอร์"),
    ("ai", r"\bai\b|machine learning|stable diffusion|ml\b|เทรนโมเดล"),
    ("virtualization", r"virtuali[sz]ation|virtual machine|\bvm\b|เครื่องเสมือน"),
    ("gaming", r"เล่นเกม|เกม|gaming|game|aaa|esports"),
    ("work", r"ทำงาน|office|ออฟฟิศ|work"),
    ("general", r"ทั่วไป|general|ดูหนัง|ท่องเน็ต|เรียน"),
]

COOLER_KEYWORDS = (
    r"AIR COOL(?:ER|ING)|LIQUID COOL(?:ER|ING)|WATER COOL(?:ER|ING)|CPU COOL|AIO COOLER|"
    r"SE-214|PA120|AS-120|FLOE|CASTLE|FORZA"
)


def detect_use_case(text: str) -> str:
    t = text.lower()
    for key, pat in USE_CASE_PATTERNS:
        if re.search(pat, t):
            return key
    return "general"


def detect_budget_thb(text: str) -> Optional[int]:
    """Extract upper budget bound from Thai text like '20,000–30,000 บาท'."""
    ranges = re.findall(
        r"([0-9][0-9,]{0,9})\s*[-–—]\s*([0-9][0-9,]{0,9})\s*(?:บาท|฿|thb)?",
        text,
        re.IGNORECASE,
    )
    if ranges:
        return max(int(high.replace(",", "")) for _, high in ranges)
    explicit = re.findall(
        r"(?:งบ(?:ประมาณ)?|budget)\s*(?:ไม่เกิน|ประมาณ|ราว|=|:)?\s*([0-9][0-9,]{0,9})"
        r"|([0-9][0-9,]{0,9})\s*(?:บาท|฿|thb)",
        text,
        re.IGNORECASE,
    )
    nums = [int((left or right).replace(",", "")) for left, right in explicit]
    if not nums:
        # A bare GPU model such as "4060" is not a 4,060-baht budget. Bare
        # values are only treated as PC budgets from 10,000 THB upward; smaller
        # budgets still work when introduced by "งบ" / "budget" above.
        nums = [value for n in re.findall(r"\d{1,3}(?:,\d{3})+|\d{4,7}", text)
                if (value := int(n.replace(",", ""))) >= 10000]
    if not nums:
        return None
    return max(nums)


def detect_requested_gpu(text: str) -> str:
    """Return an explicitly requested GPU model from the current request."""
    # Conversation context can mention several compared GPUs, so only inspect
    # the final request section when the API supplied one.
    current = (text or "").rsplit("Current request:\n", 1)[-1]
    qualified = re.findall(
        r"\b(?:RTX|GTX|RX)\s*[- ]?\s*\d{3,4}(?:\s*(?:TI|SUPER|XT|XTX))?\b",
        current,
        re.IGNORECASE,
    )
    if qualified:
        return re.sub(r"\s+", " ", qualified[-1].replace("-", " ")).strip().upper()
    bare = re.findall(
        r"(?<!\d)(?:[345]0[5-9]0|6[5-9]00|7[5-9]00)(?:\s*(?:TI|SUPER|XT|XTX))?(?!\d)",
        current,
        re.IGNORECASE,
    )
    return re.sub(r"\s+", " ", bare[-1]).strip().upper() if bare else ""


def gpu_name_matches_request(name: str, requested_gpu: str) -> bool:
    """Match a catalogue GPU to a requested model without mixing variants."""
    request = re.search(r"(RTX|GTX|RX)?\s*(\d{3,4})(?:\s*(TI|SUPER|XT|XTX))?", requested_gpu, re.I)
    if not request:
        return False
    family, model, suffix = request.groups()
    family_pattern = re.escape(family) + r"\W*" if family else r"(?:RTX|GTX|RX)\W*"
    found = re.search(
        family_pattern + re.escape(model) + r"(?:\W*(TI|SUPER|XT|XTX))?\b",
        name or "",
        re.IGNORECASE,
    )
    if not found:
        return False
    found_suffix = (found.group(1) or "").upper()
    return found_suffix == (suffix or "").upper()


def budget_is_lower_bound(text: str) -> bool:
    """A '100,000 ฿ and up' choice is a target floor, not a spending cap."""
    return bool(re.search(
        r"\d[\d,]*\s*(?:฿|บาท|THB)\s*(?:ขึ้นไป|\+)"
        r"|(?:at\s+least|minimum|อย่างน้อย)\s*\d[\d,]*\s*(?:฿|บาท|THB)"
        r"|(?:budget|งบ)\s*\d[\d,]*\s*\+",
        text, re.I,
    ))


def best_price(p) -> int:
    vals = [v for v in (p.p_price, p.price_advice, p.price_jib, p.price_ihavecpu) if v and v > 0]
    return int(min(vals)) if vals else 0


def cpu_requires_aftermarket_cooler(cpu: dict | None) -> bool:
    """True only when catalogue evidence says the selected CPU has no cooler."""
    if not cpu:
        return False
    included = cpu.get("stock_cooler_included")
    if included is None:
        included = sp.parse_part(
            "CPU", cpu.get("name", ""), specs=cpu.get("specs", "")
        ).get("stock_cooler_included")
    return included is False


def mandatory_categories_for_cpu(cpu: dict | None) -> list[str]:
    categories = list(BASE_MANDATORY_CATEGORIES)
    if cpu_requires_aftermarket_cooler(cpu):
        categories.append("Cooler")
    return categories


def ram_floor_gb(use_case: str) -> int:
    return 32 if use_case in {"3d", "video", "ai", "virtualization"} else 16


def _ram_is_single_channel(parsed_ram: dict) -> bool:
    return parsed_ram.get("module_count") == 1


# ─────────────────────────────────────────
# Candidate retrieval (RAG from Product DB)
# ─────────────────────────────────────────
def select_candidates(db, budget: int, use_case: str, k_per_cat: int = 4,
                      requested_gpu: str = "") -> list:
    from shop_api import Product
    alloc = ALLOCATIONS.get(use_case, ALLOCATIONS["general"])
    candidates = []
    seen_ids = set()

    def compat_specs(row) -> str:
        blocks = []
        for field in ("specs", "desc_advice", "desc_jib", "desc_ihavecpu", "p_description"):
            value = (getattr(row, field, "") or "").strip()
            if value and value not in blocks:
                blocks.append(value)
        return "\n".join(blocks)

    def workload_ram_rows(priced_rows: list) -> list:
        floor = ram_floor_gb(use_case)
        eligible = []
        for row, price in priced_rows:
            parsed = sp.parse_part("RAM", row.p_name or "", specs=compat_specs(row))
            if (parsed.get("capacity_gb") or 0) < floor or _ram_is_single_channel(parsed):
                continue
            eligible.append((row, price, parsed.get("dual_channel") is True))
        # Prefer confirmed multi-module kits, but keep unknown kit layouts as a
        # catalogue fallback. Explicit 1-DIMM products are never candidates.
        eligible.sort(key=lambda item: not item[2])
        return [(row, price) for row, price, _ in eligible]

    def fetch_cat(cat: str, target: int, k: int) -> list:
        rows = db.query(Product).filter(Product.category == cat).all()
        priced = [(r, best_price(r)) for r in rows]
        priced = [(r, pr) for r, pr in priced if pr > 0]
        if cat == "GPU" and requested_gpu:
            requested = [(r, pr) for r, pr in priced
                         if gpu_name_matches_request(r.p_name or "", requested_gpu)]
            if requested:
                # Pin the GPU pool to the requested model. Other component
                # categories still go through the normal compatibility checks.
                priced = requested
        # nearest-to-target first; keep some cheaper options too
        if cat == "RAM":
            priced = workload_ram_rows(priced)
        priced.sort(key=lambda item: (
            sp.parse_part("RAM", item[0].p_name or "", specs=compat_specs(item[0])).get("dual_channel") is not True,
            abs(item[1] - target),
        ) if cat == "RAM" else (False, abs(item[1] - target)))
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
                "specs": compat_specs(r),
                "category": cat,
                "name": r.p_name,
                "price": best_price(r),
                "prices": {"advice": int(r.price_advice or 0),
                           "jib": int(r.price_jib or 0),
                           "ihavecpu": int(r.price_ihavecpu or 0)},
                "urls": {"advice": r.url_advice or "", "jib": r.url_jib or "", "ihavecpu": r.url_ihavecpu or ""},
                "url": r.url_advice or r.url_jib or r.url_ihavecpu or "",
            })

    # Cooler candidates are optional at pool creation time; assemble_build
    # promotes one to a mandatory part when its selected CPU has no stock cooler.
    for cat in ("Air Cooler", "Liquid Cooler"):
        rows = db.query(Product).filter(Product.category == cat).all()
        rows = [r for r in rows
                if best_price(r) > 0 and re.search(COOLER_KEYWORDS, (r.p_name or "").upper())]
        rows.sort(key=lambda r: abs(best_price(r) - max(300, int(budget * .04))))
        for r in rows[:2]:
            if r.product_id not in seen_ids:
                seen_ids.add(r.product_id)
                candidates.append({
                    "product_id": r.product_id,
                    "specs": compat_specs(r),
                    "category": cat,
                    "name": r.p_name,
                    "price": best_price(r),
                    "prices": {"advice": int(r.price_advice or 0),
                               "jib": int(r.price_jib or 0),
                               "ihavecpu": int(r.price_ihavecpu or 0)},
                    "urls": {"advice": r.url_advice or "", "jib": r.url_jib or "", "ihavecpu": r.url_ihavecpu or ""},
                    "url": r.url_advice or r.url_jib or r.url_ihavecpu or "",
                })

    # ── Compatibility coverage guarantee ─────────────────────────────
    # Ensure the pool contains a mainboard matching every CPU socket present
    # in the candidate set, and RAM matching every supported DDR gen.
    cpu_sockets = {sp.parse_part("CPU", c["name"], specs=c.get("specs", "")).get("socket")
                   for c in candidates if c["category"] == "CPU"}
    cpu_sockets.discard(None)

    def add_extra(cat: str, matcher, target: int):
        from shop_api import Product  # already imported above via closure
        rows = db.query(Product).filter(Product.category == cat).all()
        priced = [(r, best_price(r)) for r in rows]
        priced = [(r, pr) for r, pr in priced if pr > 0 and matcher(r)]
        if cat == "RAM":
            priced = workload_ram_rows(priced)
        priced.sort(key=lambda item: (
            sp.parse_part("RAM", item[0].p_name or "", specs=compat_specs(item[0])).get("dual_channel") is not True,
            abs(item[1] - target),
        ) if cat == "RAM" else (False, abs(item[1] - target)))
        for r, pr in priced[:2]:
            if r.product_id not in seen_ids:
                seen_ids.add(r.product_id)
                candidates.append({
                    "product_id": r.product_id,
                    "specs": compat_specs(r),
                    "category": cat,
                    "name": r.p_name,
                    "price": pr,
                    "prices": {"advice": int(r.price_advice or 0),
                               "jib": int(r.price_jib or 0),
                               "ihavecpu": int(r.price_ihavecpu or 0)},
                    "urls": {"advice": r.url_advice or "", "jib": r.url_jib or "", "ihavecpu": r.url_ihavecpu or ""},
                    "url": r.url_advice or r.url_jib or r.url_ihavecpu or "",
                })

    mb_target = max(1000, int(budget * alloc["Mainboard"]))
    ram_target = max(800, int(budget * alloc["RAM"]))
    for soc in sorted(cpu_sockets):
        add_extra("Mainboard",
                  lambda r, s=soc: sp.parse_part(
                      "Mainboard", r.p_name or "", specs=r.specs or ""
                  ).get("socket") == s,
                  mb_target)
        ddr = {"AM4": ["DDR4"], "LGA1200": ["DDR4"], "LGA1700": ["DDR4", "DDR5"],
               "LGA1851": ["DDR5"], "AM5": ["DDR5"]}.get(soc, [])
        for gen in ddr:
            add_extra("RAM",
                      lambda r, g=gen: sp.parse_part(
                          "RAM", r.p_name or "", specs=r.specs or ""
                      ).get("ddr_gen") == g,
                      ram_target)
            # Keep explicit lower-capacity steps in the pool so an initially
            # over-budget 128GB selection can fall back to 64GB then 32GB
            # without ever crossing DDR generation.
            capacity_steps = (64, 32) if ram_floor_gb(use_case) >= 32 else (64, 32, 16)
            for capacity_limit in capacity_steps:
                add_extra(
                    "RAM",
                    lambda r, g=gen, limit=capacity_limit: (
                        lambda parsed: parsed.get("ddr_gen") == g
                        and 0 < (parsed.get("capacity_gb") or 0) <= limit
                    )(sp.parse_part("RAM", r.p_name or "", specs=compat_specs(r))),
                    max(800, int(budget * alloc["RAM"] * capacity_limit / 128)),
                )
        cooler_target = max(300, int(budget * .04))
        for cooler_category in ("Air Cooler", "Liquid Cooler"):
            add_extra(
                cooler_category,
                lambda r, s=soc, cat=cooler_category: (
                    lambda parsed: parsed.get("is_cpu_cooler")
                    and s in (parsed.get("sockets") or [])
                )(sp.parse_part(cat, r.p_name or "", specs=compat_specs(r))),
                cooler_target,
            )

    # Likewise retain common SSD downgrade points (1TB and roughly 500GB).
    for capacity_limit in (1024, 640):
        add_extra(
            "SSD",
            lambda r, limit=capacity_limit: (
                lambda capacity: capacity is not None and 0 < capacity <= limit
            )(sp.parse_part("SSD", r.p_name or "", specs=compat_specs(r)).get("capacity_gb")),
            max(500, int(budget * alloc["SSD"] * capacity_limit / 1024)),
        )

    return candidates


def candidates_to_text(candidates: list) -> str:
    lines = []
    for i, c in enumerate(candidates):
        parsed = sp.parse_part(c["category"], c["name"], specs=c.get("specs", ""))
        facts = []
        for field, label, unit in (
            ("socket", "socket", ""), ("ram_support", "RAM", ""),
            ("ddr_gen", "DDR", ""), ("capacity_gb", "capacity", "GB"),
            ("form_factor", "form factor", ""),
            ("vram_gb", "VRAM", "GB"), ("tdp", "board power", "W"),
            ("recommended_psu_watt", "minimum system PSU", "W"),
            ("watt", "PSU output", "W"),
            ("power_connectors_required", "GPU power input", ""),
            ("power_connectors", "PSU connectors", ""),
            ("supports_ff", "case supports", ""),
            ("radiator_support_mm", "case radiator sizes", "mm"),
            ("sockets", "cooler sockets", ""),
            ("rating_watt", "cooling capacity", "W"),
        ):
            value = parsed.get(field)
            if value in (None, "", [], {}):
                continue
            if isinstance(value, list):
                value = "/".join(map(str, value))
            elif isinstance(value, dict):
                value = ", ".join(f"{name} x{count}" for name, count in value.items())
            facts.append(f"{label}={value}{unit}")
        fact_text = f" | FACTS: {'; '.join(facts)}" if facts else " | FACTS: insufficient"
        sources = list(dict.fromkeys(
            source.get("url", "") for source in parsed.get("power_sources", [])
            if source.get("url")
        ))
        source_text = f" | power source: {sources[0]}" if sources else ""
        lines.append(
            f"[{c['product_id']}] ({c['category']}) {c['name']} — {c['price']:,} THB"
            f"{fact_text}{source_text}"
        )
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
    "google":     "gemini-3-flash-preview",
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


async def answer_spec_question(
    prompt: str,
    spec_context: str,
    provider: str = "google",
    model: str = "",
    api_key: str = "",
) -> str:
    """Answer a free-form question about a PC spec build already shown to the user.

    The AI is constrained to *only* answer about the provided spec — it must not
    recommend alternative products or change the build. Answers are in Thai,
    concise, and understandable to general consumers.

    Args:
        prompt:       The user's question.
        spec_context: Plain-text summary of the build (parts + prices).
        provider / model / api_key: forwarded directly to llm_chat().

    Returns:
        Plain-text answer string (not JSON).
    """
    if not spec_context.strip():
        spec_context = "(ไม่มีข้อมูลสเปค — โปรดถามพร้อมส่งสเปคมาด้วย)"

    system_prompt = (
        "คุณเป็นผู้เชี่ยวชาญด้านสเปคคอมพิวเตอร์สำหรับผู้บริโภคทั่วไป "
        "ผู้ใช้มีชุดสเปคที่ระบบแนะนำไปแล้ว และต้องการถามคำถามเพิ่มเติมเกี่ยวกับสเปคชุดนั้น\n\n"
        "กฎ (ห้ามละเมิด):\n"
        "1. ตอบเฉพาะคำถามที่ถาม ไม่แนะนำสินค้าอื่นหรือเปลี่ยนแปลงสเปค\n"
        "2. ใช้ภาษาไทยที่เข้าใจง่าย สั้นกระชับ ไม่เกิน 200 คำ\n"
        "3. ถ้าคำตอบขึ้นกับการตั้งค่าในเกม/ซอฟต์แวร์ ให้ระบุเงื่อนไขนั้นด้วย\n"
        "4. ถ้าไม่แน่ใจให้บอกว่าไม่แน่ใจ อย่าแต่งตัวเลขขึ้นมาเอง\n\n"
        f"สเปคที่แนะนำไปแล้ว:\n{spec_context}"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": prompt},
    ]
    return await llm_chat(
        messages,
        provider=provider,
        model=model,
        api_key=api_key,
        temperature=0.3,
        max_tokens=512,
    )


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
    """Find a complete JSON object even when the model adds fences or prose."""
    decoder = json.JSONDecoder()
    first_object = None
    for match in re.finditer(r"\{", text):
        try:
            value, _ = decoder.raw_decode(text[match.start():])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            if isinstance(value.get("parts"), list):
                return value
            first_object = first_object or value
    return first_object


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


def build_final_result(llm_result: dict, candidates: list, budget: Optional[int], use_case: str,
                       budget_ceiling: bool = True) -> dict:
    """Attach real products/prices + run deterministic compatibility engine."""
    parts_out, parsed_parts = [], []
    proposed_parts = llm_result.get("parts", [])
    unmatched_categories = []
    for part in proposed_parts:
        label = sp.normalize_label(str(part.get("type", "")))
        cand = map_part_to_candidate(part, candidates)
        if not cand:
            category = label or str(part.get("type") or "ไม่ทราบหมวดหมู่")
            unmatched_categories.append(category)
            continue

        entry = {
            "type": part.get("type", ""),
            "name": cand["name"],
            "price": f"{cand['price']:,} ฿",
            "reason": part.get("reason", ""),
            "product_id": cand["product_id"],
            "real_price": cand["price"],
            "shop_prices": cand["prices"],
            "shop_urls": cand.get("urls", {}),
            "url": cand["url"],
            "matched_real_product": True,
        }
        parts_out.append(entry)

        db_cat = label if label in PC_CATEGORIES or label in ("Air Cooler", "Liquid Cooler") else None
        if db_cat and entry["name"]:
            parsed = sp.parse_part(db_cat, entry["name"], specs=cand.get("specs", ""))
            parsed["price"] = cand["price"]
            parsed_parts.append(parsed)

    total = sum(p.get("price") or 0 for p in parsed_parts)
    compat = ce.check_build(parsed_parts, budget if budget_ceiling else None)
    warnings = list(llm_result.get("warnings") or [])
    warnings.extend(
        f"ไม่พบสินค้าที่ตรงในฐานข้อมูลสำหรับ {category}"
        for category in dict.fromkeys(unmatched_categories)
    )
    all_parts_matched = bool(proposed_parts) and not unmatched_categories
    total_label = f"{total:,} ฿"
    if all_parts_matched:
        total_label += " (ราคาจริงจากฐานข้อมูล)"
    elif parts_out:
        total_label += " (รวมเฉพาะสินค้าที่ตรงกับฐานข้อมูล)"

    result = {
        "summary": llm_result.get("summary", ""),
        "totalBudget": total_label,
        "tier": llm_result.get("tier", ""),
        "useCase": use_case,
        "budgetInput": budget,
        "parts": parts_out,
        "warnings": warnings,
        "performance": llm_result.get("performance", {}),
        "pros": llm_result.get("pros", []),
        "cons": llm_result.get("cons", []),
        "compat": compat,
        "_meta": {
            "engine": "hybrid-rag-v1",


            "compatibility": "deterministic-engine",
            "candidates_offered": len(candidates),
            "parts_matched_to_db": len(parts_out),
            "parts_rejected_not_in_db": len(unmatched_categories),
        },
    }
    return result


# ─────────────────────────────────────────
# Heuristic builder (no LLM needed)
# Compatibility-aware: CPU → matching MB → matching RAM → sized PSU → fitting Case
# ─────────────────────────────────────────
def _nearest(rows: list, target: int):
    return min(rows, key=lambda c: abs(c["price"] - target)) if rows else None


def _parse_candidate(category: str, candidate: dict) -> dict:
    """Parse the selected row, including a GPU PSU minimum stated in shop prose."""
    category = candidate.get("category") or category
    specs = candidate.get("specs", "") or ""
    parsed = sp.parse_part(category, candidate["name"], specs=specs)
    if category == "GPU" and not parsed.get("recommended_psu_watt"):
        # Some catalogue rows say "PSU Require 350w" or "Power Supply: 350W"
        # instead of a normalized spec key. Feed that *same product's* stated
        # system minimum back through the existing parser; do not infer watts.
        match = re.search(
            r"\b(?:PSU\s*Requir(?:e|ement)|Power\s*Supply)\s*:?\s*(\d{3,4})\s*W\b",
            specs, re.IGNORECASE,
        )
        if match:
            parsed = sp.parse_part(
                category, candidate["name"],
                specs=f"{specs}\nRecommended PSU: {match.group(1)} W",
            )
    return parsed


def _parse_picked_parts(picked: dict) -> list[dict]:
    return [
        _parse_candidate(category, candidate) | {"price": candidate["price"]}
        for category, candidate in picked.items()
    ]


def _picked_total(picked: dict) -> int:
    return sum(int(candidate.get("price") or 0) for candidate in picked.values())


def _has_confirmed_critical_failure(compat: dict) -> bool:
    return any(
        check.get("severity") != "PASS" and check.get("score_severity") == "critical"
        for check in compat.get("checks", [])
    )


def _capacity_label(category: str, capacity_gb: int | None) -> str:
    if not capacity_gb:
        return "ไม่ทราบความจุ"
    if category == "SSD" and capacity_gb >= 1024 and capacity_gb % 1024 == 0:
        return f"{capacity_gb // 1024}TB"
    return f"{capacity_gb}GB"


def _adjustment_prose(component_adjustments: list[dict],
                      budget_adjustments: list[dict]) -> str:
    """Explain a cooler upgrade and its budget tradeoff as one decision."""
    cooler_upgrade = next(
        (item for item in component_adjustments if item.get("category") == "Cooler"), None
    )
    gpu_changes = [item for item in budget_adjustments if item.get("category") == "GPU"]
    messages = []
    if cooler_upgrade and gpu_changes:
        steps = "หนึ่งขั้น" if len(gpu_changes) == 1 else f"{len(gpu_changes)} ขั้น"
        messages.append(
            f"{cooler_upgrade['message']} และปรับ GPU ลง{steps}เพื่อให้อยู่ในงบ"
        )
    elif cooler_upgrade:
        messages.append(cooler_upgrade["message"])
    messages.extend(item["message"] for item in component_adjustments
                    if item is not cooler_upgrade)
    messages.extend(item["message"] for item in budget_adjustments
                    if not (cooler_upgrade and gpu_changes and item.get("category") == "GPU"))
    return " · ".join(messages)


def _select_cooler_for_cpu(cpu_spec: dict, coolers: list,
                           target_price: int) -> tuple[dict | None, list[dict]]:
    """Return the initial cooler and socket/R4 passing upgrades by price."""
    cpu_socket = cpu_spec.get("socket")
    parsed_by_id = {}
    matching = []
    for candidate in coolers:
        parsed = sp.parse_part(
            candidate.get("category", "Cooler"),
            candidate["name"],
            specs=candidate.get("specs", ""),
        )
        parsed_by_id[candidate.get("product_id")] = parsed
        if parsed.get("is_cpu_cooler") and cpu_socket in (parsed.get("sockets") or []):
            matching.append(candidate)
    if not matching:
        return None, []

    initial = _nearest(matching, target_price)
    initial_parsed = parsed_by_id[initial.get("product_id")]
    initial_r4 = ce.check_cooler_tdp([cpu_spec, initial_parsed])
    if not initial_r4 or initial_r4.get("severity") != "WARNING":
        return initial, []

    passing = []
    for candidate in matching:
        parsed = parsed_by_id[candidate.get("product_id")]
        socket_check = ce.check_cooler_socket([cpu_spec, parsed])
        tdp_check = ce.check_cooler_tdp([cpu_spec, parsed])
        if (socket_check and socket_check.get("severity") == "PASS"
                and tdp_check and tdp_check.get("severity") == "PASS"):
            passing.append(candidate)

    return initial, sorted(passing, key=lambda candidate: candidate["price"])


def _downgrade_options(category: str, current: dict, pool: list,
                       picked: dict, use_case: str) -> list[dict]:
    """Return one-step-at-a-time cheaper replacements in downgrade order."""
    current_price = int(current.get("price") or 0)
    candidates = [candidate for candidate in pool
                  if candidate.get("product_id") != current.get("product_id")
                  and 0 < int(candidate.get("price") or 0) < current_price]
    if not candidates:
        return []

    current_parsed = sp.parse_part(
        current.get("category") or category,
        current["name"],
        specs=current.get("specs", ""),
    )

    if category == "RAM":
        floor = ram_floor_gb(use_case)
        current_capacity = current_parsed.get("capacity_gb")
        if current_capacity is None or current_capacity <= floor:
            return []
        current_gen = current_parsed.get("ddr_gen")
        current_speed = current_parsed.get("speed_mhz")
        mainboard = picked.get("Mainboard")
        supported = sp.parse_part(
            "Mainboard", mainboard["name"], specs=mainboard.get("specs", "")
        ).get("ram_support") if mainboard else None

        parsed_candidates = []
        for candidate in candidates:
            parsed = sp.parse_part("RAM", candidate["name"], specs=candidate.get("specs", ""))
            capacity = parsed.get("capacity_gb")
            generation = parsed.get("ddr_gen")
            if (not current_capacity or not capacity or capacity >= current_capacity
                    or capacity < floor or _ram_is_single_channel(parsed)):
                continue
            if current_gen and generation != current_gen:
                continue
            if supported and generation not in supported:
                continue
            parsed_candidates.append((candidate, capacity))
        if not parsed_candidates:
            return []
        next_capacity = max(capacity for _, capacity in parsed_candidates)
        return sorted(
            [candidate for candidate, capacity in parsed_candidates if capacity == next_capacity],
            key=lambda candidate: (
                sp.parse_part("RAM", candidate["name"], specs=candidate.get("specs", "")).get("dual_channel") is not True,
                sp.parse_part("RAM", candidate["name"], specs=candidate.get("specs", "")).get("speed_mhz") != current_speed,
                -candidate["price"],
            ),
        )

    if category == "SSD":
        current_capacity = current_parsed.get("capacity_gb")
        current_interface = current_parsed.get("interface")
        parsed_candidates = []
        for candidate in candidates:
            parsed = sp.parse_part("SSD", candidate["name"], specs=candidate.get("specs", ""))
            capacity = parsed.get("capacity_gb")
            if not current_capacity or not capacity or capacity >= current_capacity:
                continue
            if current_interface and parsed.get("interface") != current_interface:
                continue
            parsed_candidates.append((candidate, capacity))
        if not parsed_candidates:
            return []
        next_capacity = max(capacity for _, capacity in parsed_candidates)
        return sorted(
            [candidate for candidate, capacity in parsed_candidates if capacity == next_capacity],
            key=lambda candidate: candidate["price"],
            reverse=True,
        )

    # GPU fallback: the next cheaper catalogue item is the next tier when no
    # explicit tier ordering is available for the product name.
    return sorted(candidates, key=lambda candidate: candidate["price"], reverse=True)


def _fit_picked_to_budget(picked: dict, by_cat: dict, budget: int,
                          use_case: str) -> tuple[list[dict], dict]:
    """Downgrade RAM → GPU → SSD until the selected set fits the hard budget."""
    adjustments = []
    if _picked_total(picked) <= budget:
        return adjustments, ce.check_build(_parse_picked_parts(picked), budget)

    for category in ("RAM", "GPU", "SSD"):
        pool_category = category
        while _picked_total(picked) > budget and picked.get(category):
            current = picked[category]
            accepted = None
            for replacement in _downgrade_options(
                category, current, by_cat.get(pool_category, []), picked, use_case
            ):
                trial = {**picked, category: replacement}
                compat = ce.check_build(_parse_picked_parts(trial), budget)
                if compat.get("overall") == "error" or _has_confirmed_critical_failure(compat):
                    continue
                accepted = replacement
                break
            if not accepted:
                break

            before = sp.parse_part(
                current.get("category") or category,
                current["name"],
                specs=current.get("specs", ""),
            )
            after = sp.parse_part(
                accepted.get("category") or category,
                accepted["name"],
                specs=accepted.get("specs", ""),
            )
            if category in ("RAM", "SSD"):
                message = (
                    f"ปรับ {category} จาก {_capacity_label(category, before.get('capacity_gb'))} "
                    f"เป็น {_capacity_label(category, after.get('capacity_gb'))} เพื่อให้อยู่ในงบที่กำหนด"
                )
            else:
                message = (
                    f"ปรับ GPU จาก {current['name']} เป็น {accepted['name']} "
                    "เพื่อให้อยู่ในงบที่กำหนด"
                )
            picked[category] = accepted
            adjustments.append({
                "category": category,
                "from_product_id": current.get("product_id"),
                "to_product_id": accepted.get("product_id"),
                "from_name": current["name"],
                "to_name": accepted["name"],
                "message": message,
            })

    # Never return a verdict from an intermediate trial. The final selected
    # snapshot may have changed RAM, GPU and SSD in separate loop iterations.
    return adjustments, ce.check_build(_parse_picked_parts(picked), budget)


def assemble_build(candidates: list, budget: Optional[int], use_case: str,
                   alloc: Optional[dict] = None, *, enforce_budget: bool = True,
                   fit_budget: Optional[int] = None) -> dict:
    """
    Deterministically assemble one compatible build from candidates.
    alloc: optional custom category share overrides (for strategy variants).
    Returns the picked components plus compatibility-safe budget adjustments.
    """
    budget = budget or 25000
    base = ALLOCATIONS.get(use_case, ALLOCATIONS["general"])
    if alloc:
        base = {**base, **alloc}
    by_cat: dict = {}
    for c in candidates:
        by_cat.setdefault(c["category"], []).append(c)
    picked: dict = {}
    component_adjustments = []
    cooler_upgrades = []
    mandatory_categories = list(BASE_MANDATORY_CATEGORIES)

    cpu = _nearest(by_cat.get("CPU", []), int(budget * base["CPU"]))
    total_draw, need_watt = 80, 0
    if cpu:
        picked["CPU"] = cpu
        cpu_spec = sp.parse_part("CPU", cpu["name"], specs=cpu.get("specs", ""))
        mandatory_categories = mandatory_categories_for_cpu(cpu | {
            "stock_cooler_included": cpu_spec.get("stock_cooler_included")
        })
        total_draw += cpu_spec.get("tdp") or 65

        mbs = by_cat.get("Mainboard", [])
        mbs_match = [c for c in mbs
                     if sp.parse_part("Mainboard", c["name"], specs=c.get("specs", "")).get("socket") == cpu_spec.get("socket")]
        mb = _nearest(mbs_match or mbs, int(budget * base["Mainboard"]))
        if mb:
            picked["Mainboard"] = mb

        rams = by_cat.get("RAM", [])
        supported = sp.parse_part(
            "Mainboard", mb["name"], specs=mb.get("specs", "")
        ).get("ram_support") if mb else None
        rams_match = [c for c in rams
                      if sp.parse_part("RAM", c["name"], specs=c.get("specs", "")).get("ddr_gen") in (supported or [])]
        floor = ram_floor_gb(use_case)
        workload_rams = []
        for candidate in rams_match if rams_match else (rams if not supported else []):
            parsed_ram = sp.parse_part("RAM", candidate["name"], specs=candidate.get("specs", ""))
            if (parsed_ram.get("capacity_gb") or 0) >= floor and not _ram_is_single_channel(parsed_ram):
                workload_rams.append(candidate)
        confirmed_dual = [candidate for candidate in workload_rams
                          if sp.parse_part("RAM", candidate["name"], specs=candidate.get("specs", "")).get("dual_channel")]
        ram = _nearest(confirmed_dual or workload_rams, int(budget * base["RAM"]))
        if ram:
            picked["RAM"] = ram

        if "Cooler" in mandatory_categories:
            coolers = by_cat.get("Air Cooler", []) + by_cat.get("Liquid Cooler", [])
            cooler, cooler_upgrades = _select_cooler_for_cpu(
                cpu_spec, coolers, max(300, int(budget * .04))
            )
            if cooler:
                picked["Cooler"] = cooler

    gpu = _nearest(by_cat.get("GPU", []), int(budget * base["GPU"]))
    if gpu:
        picked["GPU"] = gpu
        total_draw += _parse_candidate("GPU", gpu).get("tdp") or 150
    gpu_min = _parse_candidate("GPU", gpu).get("recommended_psu_watt", 0) if gpu else 0
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
    mb_ff = sp.parse_part(
        "Mainboard", picked["Mainboard"]["name"], specs=picked["Mainboard"].get("specs", "")
    ).get("form_factor") \
        if picked.get("Mainboard") else None
    cases_fit = [c for c in cases
                 if not mb_ff or mb_ff in (sp.parse_part(
                     "Case", c["name"], specs=c.get("specs", "")
                 ).get("supports_ff") or [])]
    case = _nearest(cases_fit or cases, int(budget * base["Case"]))
    if case:
        picked["Case"] = case

    hard_budget = (fit_budget if fit_budget is not None else budget) if enforce_budget else None
    budget_adjustments = []
    post_downgrade_compat = None
    upgrade_selected = False
    initial_cooler = picked.get("Cooler")
    for upgrade in cooler_upgrades:
        trial = {**picked, "Cooler": upgrade}
        trial_adjustments = []
        if hard_budget and hard_budget > 0 and _picked_total(trial) > hard_budget:
            trial_adjustments, trial_compat = _fit_picked_to_budget(
                trial, by_cat, int(hard_budget), use_case
            )
            if _picked_total(trial) > hard_budget:
                continue
        else:
            trial_compat = ce.check_build(
                _parse_picked_parts(trial),
                int(hard_budget) if hard_budget and hard_budget > 0 else None,
            )
        if trial_compat.get("overall") == "error" or _has_confirmed_critical_failure(trial_compat):
            continue
        picked = trial
        budget_adjustments = trial_adjustments
        post_downgrade_compat = trial_compat
        component_adjustments.append({
            "category": "Cooler",
            "from_product_id": initial_cooler.get("product_id"),
            "to_product_id": upgrade.get("product_id"),
            "from_name": initial_cooler["name"],
            "to_name": upgrade["name"],
            "message": "ปรับ cooler เป็นรุ่นที่ระบายความร้อนแรงขึ้นเพื่อรองรับ CPU ตัวนี้",
        })
        upgrade_selected = True
        break

    if not upgrade_selected and hard_budget and hard_budget > 0:
        budget_adjustments, post_downgrade_compat = _fit_picked_to_budget(
            picked, by_cat, int(hard_budget), use_case
        )

    parsed = _parse_picked_parts(picked)
    # Recheck the exact final set after every downgrade/upgrade path. R3 and
    # the PSU rationale must read the replacement GPU, not a pre-downgrade one.
    post_downgrade_compat = ce.check_build(
        parsed, int(hard_budget) if hard_budget and hard_budget > 0 else None,
    )
    r3 = next((check for check in post_downgrade_compat["checks"]
               if check["rule"].startswith("R3 ")), None)
    total_draw = (r3 or {}).get("estimated_draw_watt") or 80
    need_watt = (r3 or {}).get("required_watt") or 0
    return {"picked": picked, "parsed": parsed,
            "total_draw": total_draw, "need_watt": need_watt,
            "mandatory_categories": mandatory_categories,
            "budget_adjustments": budget_adjustments,
            "component_adjustments": component_adjustments,
            "adjustments": component_adjustments + budget_adjustments,
            "adjustment_prose": _adjustment_prose(component_adjustments, budget_adjustments),
            "post_downgrade_compat": post_downgrade_compat}


def heuristic_build(candidates: list, budget: Optional[int], use_case: str,
                    budget_ceiling: bool = True) -> dict:
    built = assemble_build(candidates, budget, use_case,
                           enforce_budget=budget_ceiling, fit_budget=budget)
    picked = built["picked"]
    reason_map = {
        "CPU": "สมดุลกับงบและการใช้งาน",
        "Mainboard": "socket ตรงกับ CPU — เลือกโดย compatibility engine",
        "RAM": "generation ตรงกับที่ mainboard รองรับ",
        "GPU": "ตัวขับประสิทธิภาพหลักภายใต้งบ",
        "SSD": "NVMe เพียงพอสำหรับ OS และโปรแกรม",
        "PSU": f"เลือกตามเกณฑ์ประมาณการ ≥{built['need_watt']}W; ดูผลตรวจ PSU และแหล่งอ้างอิงประกอบ",
        "Case": "รองรับ form factor ของ mainboard",
        "Cooler": "CPU ไม่มีชุดระบายความร้อนแถมมาและรุ่นนี้รองรับ socket เดียวกัน",
    }
    adjustment_reasons = {}
    for adjustment in built.get("adjustments", []):
        adjustment_reasons.setdefault(adjustment["category"], []).append(adjustment["message"])
    parts = [{"type": cat, "product_id": c["product_id"], "name": c["name"],
              "price": c["price"],
              "reason": " · ".join(adjustment_reasons.get(cat, [])) or reason_map.get(cat, "")}
             for cat, c in picked.items()]
    adjustment_summary = built.get("adjustment_prose", "")
    llm_like = {"summary": "จัดสเปคโดย heuristic engine และตรวจ compatibility แบบ deterministic "
                           "(โหมด offline — AI provider ไม่พร้อมใช้งาน)"
                           + (f" — {adjustment_summary}" if adjustment_summary else ""),
                "tier": "", "performance": {}, "pros": [], "cons": [], "parts": parts}
    return build_final_result(llm_like, candidates, budget, use_case, budget_ceiling)


# ─────────────────────────────────────────
# Main entry points
# ─────────────────────────────────────────
SYSTEM_PROMPT_TEMPLATE = """คุณคือ IT-RECOMMEND AI ผู้เชี่ยวชาญฮาร์ดแวร์คอมพิวเตอร์ในประเทศไทย

== กฎเหล็ก ==
1. เลือกสินค้าได้ "เฉพาะ" จากรายการ candidate ด้านล่างเท่านั้น — ห้ามแต่งชื่อสินค้าขึ้นมาเอง
2. อ้าง product_id ของสินค้าที่เลือกกลับมาใน field "product_id" ของแต่ละ part
3. ใช้ราคาที่ระบุใน candidate list เท่านั้น ห้ามประเมินราคาเอง
4. ต้องเข้ากันได้จริง: socket CPU ↔ Mainboard, DDR gen ↔ Mainboard, PSU watt ≥ ระบบ, form factor ↔ case
5. ถ้าผู้ใช้กำหนดงบแบบเพดาน ราคารวมต้องไม่เกินงบ; ถ้าระบุ "ขึ้นไป" ให้ถือเป็นงบขั้นต่ำ ไม่ใช่เพดาน
6. ตอบเป็น JSON เท่านั้น ห้ามมี text อื่นนอก JSON
7. FACTS ใน candidate มาจากรายละเอียดสินค้าที่ระบบแปลงเป็นข้อมูลมาตรฐานแล้ว ต้องใช้ค่านี้ก่อนข้อมูลจากความจำของโมเดล
8. ถ้า FACTS ระบุ insufficient ห้ามเดาว่าผ่าน ให้บอกว่าต้องตรวจเพิ่ม และห้ามเขียนคำอธิบายที่ขัดกับ compatibility engine
9. ห้ามอ้างว่า CPU/GPU "แรงที่สุดในโลก" หรือ "รุ่นใหม่ล่าสุด" โดยไม่มีข้อมูลยืนยันปัจจุบัน; สำหรับเครื่องเล่นเกมระดับ 100,000 บาทขึ้นไปให้พยายามเลือก RAM อย่างน้อย 32GB หากมีใน candidates
10. ถ้าเลือกชุดน้ำ ต้องตรวจขนาดหม้อน้ำกับสเปกเคสที่ระบุชัดเจน; ถ้าไม่มีข้อมูล ให้บอกว่ายังยืนยันไม่ได้

== Domain Rules ของระบบ (enforced โดย compatibility engine หลังจากนี้) ==
{rules}

== Power validation reminder ==
- Treat GPU board power and the manufacturer's minimum system PSU as separate values.
- RTX 5050 reference data is 130W board power with a 550W minimum system PSU; never call a 450W PSU sufficient for that reference.
- High-tier GPUs (about 240W+ board power or a 750W+ manufacturer recommendation) need at least a 750W PSU.
- When GPU/PSU connector data is present, match connector type and count. Missing connector data is UNKNOWN, not PASS.

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
            temperature=0.4, max_tokens=8192,
        )
        llm_result = extract_json(text)
        if not llm_result or not llm_result.get("parts"):
            raise RuntimeError("LLM returned invalid JSON")
        result = build_final_result(llm_result, candidates, budget, use_case,
                                    budget_ceiling=not budget_is_lower_bound(prompt))
        result["_meta"].update(llm_provider=provider, llm_model=model or DEFAULT_MODELS[provider])
        return result
    except RuntimeError:
        raise
    except Exception:
        # Graceful degradation: deterministic heuristic build, still validated
        return heuristic_build(candidates, budget, use_case,
                               budget_ceiling=not budget_is_lower_bound(prompt))


def deterministic_compatibility_from_text(parts_text: str) -> tuple[dict | None, list[str], int]:
    """Parse a pasted build and run the shared deterministic engine."""
    lines = [line.strip() for line in (parts_text or "").splitlines() if line.strip()]
    parsed = []
    unmatched = []
    for line in lines:
        part = sp.parse_free_text_line(line)
        if part:
            parsed.append(part)
        elif len(line) > 3:
            unmatched.append(line)
    return (ce.check_build(parsed) if parsed else None), unmatched, len(parsed)


async def compat_check_hybrid(parts_text: str, provider: str = "google", model: str = "", api_key: str = "") -> dict:
    """
    Deterministic-first compatibility check.
    Parses pasted spec lines into parts via spec_parser, validates with the
    engine, then asks the LLM only for extra suggestions (optional).
    """
    result, unmatched, parsed_count = deterministic_compatibility_from_text(parts_text)
    result = result or ce.check_build([])

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
                    # LLM enrichment may add neutral advice, but compatibility
                    # assertions belong exclusively to the deterministic engine.
                    assertions = re.compile(
                        r"compatible|compatibility|incompatible|not compatible|"
                        r"เข้ากัน|ไม่เข้ากัน|ใช้ร่วมกันไม่ได้|ผ่านทั้งหมด|ไม่ผ่าน|ไม่มีปัญหา|ทุกอย่าง",
                        re.IGNORECASE,
                    )
                    safe_suggestions = [
                        str(s) for s in extra_suggestions
                        if isinstance(s, str) and not assertions.search(s)
                    ]
                    result["suggestions"] = list(dict.fromkeys(
                        result["suggestions"] + safe_suggestions))[:8]
        except Exception:
            pass

    result["_engine"]["input_lines_parsed"] = parsed_count
    result["_engine"]["deterministic"] = True
    return result


async def compare_specs(spec1: str, spec2: str,
                        provider: str = "google", model: str = "", api_key: str = "", context: str = "") -> str:
    """Compare specs while suppressing unsupported numeric market claims."""
    compatibility1, _, _ = deterministic_compatibility_from_text(spec1)
    compatibility2, _, _ = deterministic_compatibility_from_text(spec2)
    deterministic_context = json.dumps(
        {"spec1": compatibility1, "spec2": compatibility2}, ensure_ascii=False
    )
    prompt = (
        "คุณคือผู้เชี่ยวชาญคอมพิวเตอร์ในประเทศไทย เปรียบเทียบสเปค 2 ชุดนี้อย่างละเอียดและตรงไปตรงมา:\n\n"
        f"ชุดที่ 1: {spec1}\nชุดที่ 2: {spec2}\n\n"
        "== กฎการเปรียบเทียบ ==\n"
        "1. ห้ามระบุตัวเลข benchmark/FPS ถ้าไม่มีตัวเลขพร้อมแหล่งอ้างอิงในข้อมูลนำเข้า\n"
        "2. ห้ามระบุราคาตลาดหรือความคุ้มค่าเชิงราคา ถ้าไม่มีราคาจากฐานข้อมูลในข้อมูลนำเข้า\n"
        "3. บอกชัดเจนว่าแต่ละ category อันไหนชนะและทำไม\n\n"
        "== ผล compatibility จาก deterministic engine (ห้ามเขียนขัดแย้ง) ==\n"
        f"{deterministic_context}\n\n"
        "ตอบเป็น JSON เท่านั้น ห้ามมี text นอก JSON:\n"
        '{"spec1Name":"...","spec2Name":"...","winner":"1|2|tie","verdict":"...",'
        '"categories":[{"name":"...","spec1":"...","spec2":"...","winner":"..."}],'
        '"spec1Pros":["..."],"spec2Pros":["..."],"recommendation":"..."}'
    )
    raw = await llm_chat(
        [{"role": "system", "content": "คุณคือ IT-RECOMMEND AI ตอบเป็น JSON เท่านั้น"},
         {"role": "user", "content": prompt + "\n" + context}],
        provider=provider, model=model, api_key=api_key,
        temperature=0.4,
    )
    try:
        data = json.loads(raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip())
    except (TypeError, ValueError):
        return raw

    unsupported = re.compile(
        r"(?:\b(?:price|cost|baht|thb|fps|cinebench|benchmark)\b|ราคา|บาท|฿)",
        re.IGNORECASE,
    )

    def scrub(value):
        if isinstance(value, str) and unsupported.search(value):
            return "ละเว้นข้อมูลราคา/benchmark ที่ไม่มีแหล่งข้อมูลยืนยัน"
        if isinstance(value, list):
            return [scrub(item) for item in value]
        if isinstance(value, dict):
            return {key: scrub(item) for key, item in value.items()}
        return value

    data = scrub(data)
    compatibility_warnings = []
    for label, compatibility in (("1", compatibility1), ("2", compatibility2)):
        if not compatibility:
            continue
        compatibility_warnings.extend({"spec": label, "message": warning}
                                      for warning in compatibility.get("warnings", []))
    data["compatibility"] = {"spec1": compatibility1, "spec2": compatibility2}
    data["compatibilityWarnings"] = compatibility_warnings
    return json.dumps(data, ensure_ascii=False)


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
        "Cooler": "CPU ไม่มีชุดระบายความร้อนแถมมาและรุ่นนี้รองรับ socket เดียวกัน",
    }
    adjustment_reasons = {}
    for adjustment in built.get("adjustments", []):
        adjustment_reasons.setdefault(adjustment["category"], []).append(adjustment["message"])
    cand_by_id = {c["product_id"]: c for c in candidates}
    parts = []
    for cat, c in picked.items():
        full = cand_by_id.get(c["product_id"], c)
        parts.append({
            "type": cat, "product_id": c["product_id"], "name": c["name"],
            "price": c["price"], "real_price": c["price"],
            "reason": " · ".join(adjustment_reasons.get(cat, [])) or reason_map.get(cat, ""),
            "shop_prices": full.get("prices", {}),
            "shop_urls": full.get("urls", {}),
            "url": full.get("url", ""),
            "matched_real_product": True,
        })
    return {
        "parts": parts,
        "budget_adjustments": built.get("budget_adjustments", []),
        "component_adjustments": built.get("component_adjustments", []),
        "adjustments": built.get("adjustments", []),
        "adjustment_prose": built.get("adjustment_prose", ""),
    }


def top3_builds(candidates: list, budget: Optional[int], use_case: str,
                budget_ceiling: bool = True,
                target_budget: Optional[int] = None) -> list:
    """
    Rank complete, compatible deterministic builds. A build within a hard
    budget always precedes an over-budget build, regardless of score.
    """
    import scoring_engine as se

    strategies = [
        ("balanced", "Balanced", "สมดุลสำหรับการใช้งานที่ระบุ", None),
        ("performance", "Gaming Performance", "เน้นงบไปที่การ์ดจอ", {"GPU": .48, "CPU": .10}),
        ("cpu_ram", "CPU/RAM Focus", "เน้น CPU และหน่วยความจำ", {"GPU": .28, "CPU": .27, "RAM": .18}),
        ("balanced_plus", "Balanced Plus", "สมดุลการ์ดจอและพื้นที่จัดเก็บ", {"GPU": .38, "CPU": .16, "SSD": .12}),
    ]

    variants = []
    seen_pids = set()
    for key, label, desc, alloc in strategies:
        built = assemble_build(
            candidates,
            target_budget or budget or 25000,
            use_case,
            alloc=alloc,
            enforce_budget=budget_ceiling,
            fit_budget=budget,
        )
        mandatory_categories = built.get("mandatory_categories", list(BASE_MANDATORY_CATEGORIES))
        if not all(cat in built["picked"] for cat in mandatory_categories):
            continue
        scores = se.score_build(built["parsed"], list(built["picked"].values()),
                                budget, use_case, budget_ceiling=budget_ceiling)
        if scores["compat"]["overall"] == "error":
            continue
        formatted = _format_variant(built, use_case, candidates)
        pids = tuple(sorted(p.get("product_id", "") for p in formatted["parts"]))
        if pids in seen_pids:
            continue
        seen_pids.add(pids)
        total = sum(p["price"] for p in formatted["parts"])
        adjustment_text = built.get("adjustment_prose", "")
        variants.append({
            "strategy": key,
            "label": label,
            "description": f"{desc} · {adjustment_text}" if adjustment_text else desc,
            "score": scores["score"],
            "breakdown": {k: round(x, 1) for k, x in scores["breakdown"].items()},
            "weights": se.WEIGHTS,
            "compatibility_score_policy": scores.get(
                "compatibility_score_policy", se.COMPATIBILITY_SCORE_POLICY
            ),
            "compatibility_score_description": scores.get(
                "compatibility_score_description", se.COMPATIBILITY_SCORE_DESCRIPTION
            ),
            "total_price": total,
            "compat_overall": scores["compat"]["overall"],
            "compat": scores["compat"],
            **formatted,
        })

    if not variants:
        return []
    within_budget = lambda item: not budget_ceiling or not budget or item["total_price"] <= budget
    matches_budget = lambda item: (item["total_price"] >= budget if not budget_ceiling and budget
                                   else within_budget(item))
    affordable = [item for item in variants if within_budget(item)]
    meets_floor = [item for item in variants if budget and item["total_price"] >= budget]
    if not budget_ceiling and meets_floor:
        primary = max(meets_floor, key=lambda item: item["score"])
    elif affordable:
        primary = max(affordable, key=lambda item: item["score"])
    else:
        primary = min(variants, key=lambda item: (item["total_price"] - (budget or 0), -item["score"]))

    ordered = [primary]
    remaining = [item for item in variants if item is not primary]
    if primary["breakdown"].get("availability", 100) < 50:
        higher_availability = [item for item in remaining
                               if item["breakdown"].get("availability", 0) > primary["breakdown"].get("availability", 0)]
        if higher_availability:
            backup = max(higher_availability,
                         key=lambda item: (matches_budget(item), item["breakdown"]["availability"], item["score"]))
            ordered.append(backup)
            remaining.remove(backup)
    remaining.sort(key=lambda item: (matches_budget(item), item["score"]), reverse=True)
    return (ordered + remaining)[:3]


def _scored_recommendation_result(alternatives: list, prompt: str,
                                  provider_fallback: bool = False,
                                  fallback_reason: str = "") -> dict:
    """The primary recommendation is literally alternatives[0], including its parts."""
    import scoring_engine as se

    if not alternatives:
        raise RuntimeError("No complete compatible catalogue build available")
    safe = alternatives[0]
    budget = detect_budget_thb(prompt)
    use_case = detect_use_case(prompt)
    total = sum(part["price"] for part in safe["parts"])
    if total != safe["total_price"]:
        raise RuntimeError("Scoring total does not match selected products")

    warnings = []
    if budget and not budget_is_lower_bound(prompt) and total > budget:
        warnings.append(f"⚠️ ชุดนี้เกินงบที่ตั้งไว้ {total - budget:,} บาท")
    if budget and budget_is_lower_bound(prompt) and total < budget:
        warnings.append(f"⚠️ ชุดที่มีข้อมูลครบและผ่านการตรวจในขณะนี้ต่ำกว่างบเริ่มต้น {budget:,} บาท")
    if safe["breakdown"].get("availability", 100) < 50:
        warnings.append("⚠️ อุปกรณ์บางชิ้นอาจหาซื้อได้ยากในขณะนี้")
        if len(alternatives) > 1 and alternatives[1]["breakdown"].get("availability", 0) > safe["breakdown"].get("availability", 0):
            warnings.append(f"ตัวเลือกสำรองที่หาซื้อได้มากกว่า: {alternatives[1]['label']} (อันดับ 2)")

    summary = f"ชุด {safe['label']} รวม {total:,} บาท จากสินค้าในฐานข้อมูลและผลตรวจความเข้ากันได้"
    if provider_fallback:
        summary += " (ไม่สามารถใช้คำอธิบายจาก AI ภายนอกได้)"
    if warnings and warnings[0].startswith("⚠️ ชุดนี้เกินงบ"):
        summary = f"{warnings[0]} — {summary}"

    if budget and not budget_is_lower_bound(prompt) and total > budget:
        ranking = (f"ไม่มีชุดที่ครบและผ่านความเข้ากันได้ภายในงบ {budget:,} บาท; "
                   f"ชุด {safe['label']} เป็นชุดที่เกินงบน้อยที่สุด ({safe['score']}/100)")
    else:
        ranking = f"ชุด {safe['label']} เป็นอันดับ 1 ตามเงื่อนไขงบและความเข้ากันได้ ได้คะแนน {safe['score']}/100"
    ranking += f" จากสินค้าในชุดเดียวกับที่แสดงด้านบน รวม {total:,} บาท"
    adjustment_text = safe.get("adjustment_prose") or " · ".join(
        adjustment["message"] for adjustment in safe.get("adjustments", [])
    )
    if adjustment_text:
        ranking += "\n" + adjustment_text

    return {
        "summary": summary,
        "totalBudget": f"{total:,} ฿ (ราคาจริงจากฐานข้อมูล)",
        "tier": safe["label"],
        "useCase": use_case,
        "budgetInput": budget,
        "parts": safe["parts"],
        "warnings": warnings,
        "performance": {"gaming": "ยังไม่ได้ประเมิน FPS", "productivity": "ยังไม่ได้ประเมิน", "upgrade": "ดูสเปกชิ้นส่วน"},
        "pros": ["สินค้า ราคา และผลตรวจความเข้ากันได้มาจากชุดเดียวกัน"],
        "cons": warnings[:] if warnings else ["ตรวจสต็อกและราคากับร้านอีกครั้งก่อนซื้อ"],
        "compat": safe["compat"],
        "budget_adjustments": safe.get("budget_adjustments", []),
        "component_adjustments": safe.get("component_adjustments", []),
        "adjustments": safe.get("adjustments", []),
        "adjustment_prose": adjustment_text,
        "alternatives": alternatives,
        "ranking_explanation": ranking,
        "_meta": {"engine": "deterministic-scoring-v2", "compatibility": "deterministic-engine",
                  "provider_fallback": provider_fallback, "fallback_reason": fallback_reason,
                  "scoring_engine": "weighted-v2 (P40/B25/C20/Pref10/A5; severity-based compatibility)",
                  "compatibility_score": safe.get(
                      "compatibility_score_description", se.COMPATIBILITY_SCORE_DESCRIPTION
                  ),
                  "compatibility_score_policy": safe.get(
                      "compatibility_score_policy", se.COMPATIBILITY_SCORE_POLICY
                  ),
                  "alternatives_count": len(alternatives)},
    }


def recommend_without_provider(db, prompt: str, reason: str = "provider_unavailable") -> dict:
    """Return the same top-ranked catalogue build, without AI prose."""
    budget = detect_budget_thb(prompt)
    use_case = detect_use_case(prompt)
    budget_eff = budget or 25000
    lower_bound = budget_is_lower_bound(prompt)
    target = round(budget_eff * 1.1) if lower_bound else budget_eff
    requested_gpu = detect_requested_gpu(prompt)
    alternatives = top3_builds(select_candidates(db, target, use_case,
                                                   requested_gpu=requested_gpu),
                               budget_eff, use_case, budget_ceiling=not lower_bound,
                               target_budget=target)
    return _scored_recommendation_result(alternatives, prompt, True, reason)


async def recommend_with_alternatives(db, prompt: str, extra: str = "",
                                      provider: str = "google", model: str = "", api_key: str = "") -> dict:
    """Score first; AI may explain the chosen build but cannot select products."""
    budget = detect_budget_thb(prompt)
    use_case = detect_use_case(prompt)
    budget_eff = budget or 25000
    lower_bound = budget_is_lower_bound(prompt)
    target = round(budget_eff * 1.1) if lower_bound else budget_eff
    requested_gpu = detect_requested_gpu(prompt)
    candidates = select_candidates(db, target, use_case,
                                   requested_gpu=requested_gpu)
    alternatives = top3_builds(candidates, budget_eff, use_case,
                               budget_ceiling=not lower_bound, target_budget=target)
    result = _scored_recommendation_result(alternatives, prompt)
    safe = alternatives[0]

    if not api_key:
        result["_meta"].update(provider_fallback=True, fallback_reason="no_api_key")
        return result

    parts_text = "\n".join(
        f"- {part['type']}: {part['name']} ({part['price']:,} ฿)"
        for part in safe["parts"]
    )
    try:
        text = await llm_chat(
            [{"role": "system", "content":
              "คุณคือ IT-RECOMMEND AI ทำหน้าที่อธิบายชุดคอมที่ระบบเลือกแล้วเท่านั้น "
              "ห้ามเลือก เพิ่ม เปลี่ยน หรือแนะนำสินค้าอื่น ห้ามใส่ตัวเลขราคาในคำอธิบาย "
              "ห้ามอ้างว่าอุปกรณ์ดีที่สุดในโลกหากไม่มีหลักฐาน และห้ามขัดกับผลตรวจความเข้ากันได้ "
              "ตอบ JSON เท่านั้นในรูปแบบ "
              '{"summary":"...","performance":{"gaming":"...","productivity":"...","upgrade":"..."},'
              '"pros":["..."],"cons":["..."]}'},
             {"role": "user", "content":
              f"ความต้องการผู้ใช้: {prompt}\n{extra}\n"
              f"ชุดอันดับ 1: {safe['label']}\nสินค้าในชุดนี้เท่านั้น:\n{parts_text}\n"
              f"ผลตรวจ: {safe['compat']['summary']}\n"
              f"คะแนน: {safe['score']}/100; Availability: {safe['breakdown'].get('availability', 0)}/100\n"
              "อธิบายข้อดีและข้อควรรู้ของชุดนี้เท่านั้น โดยไม่กล่าวถึงสินค้าใหม่หรือยอดเงิน"}],
            temperature=0.3, max_tokens=2000, provider=provider, model=model, api_key=api_key,
        )
        enrich = extract_json(text)
        if not isinstance(enrich, dict):
            raise ValueError("AI explanation was not valid JSON")

        def clean_prose(value):
            if not isinstance(value, str):
                return ""
            value = value.strip()
            if re.search(r"\d[\d,]*(?:\.\d+)?\s*(?:฿|บาท|THB)|\d{1,3}(?:,\d{3})+|(?:total|รวม|ราคา|งบ)\D{0,12}\d[\d,]*|แรงที่สุดในโลก|ดีที่สุดในโลก|รุ่นใหม่ล่าสุด", value, re.I):
                return ""
            return value[:700]

        summary = clean_prose(enrich.get("summary"))
        performance = enrich.get("performance")
        clean_performance = ({key: cleaned for key in ("gaming", "productivity", "upgrade")
                              if (cleaned := clean_prose(performance.get(key)))}
                             if isinstance(performance, dict) else {})
        clean_lists = {}
        for field in ("pros", "cons"):
            items = enrich.get(field)
            cleaned = [clean_prose(item) for item in items[:5]] if isinstance(items, list) else []
            clean_lists[field] = [item for item in cleaned if item]
        if not (summary or clean_performance or clean_lists["pros"] or clean_lists["cons"]):
            raise ValueError("AI explanation did not contain usable prose")

        if summary:
            result["summary"] = summary
            if result["warnings"] and result["warnings"][0].startswith("⚠️ ชุดนี้เกินงบ"):
                result["summary"] = f"{result['warnings'][0]} — {summary}"
        result["performance"].update(clean_performance)
        for field in ("pros", "cons"):
            if clean_lists[field]:
                result[field] = clean_lists[field]
    except Exception as exc:
        result["_meta"].update(provider_fallback=True, fallback_reason=type(exc).__name__)
    return result
