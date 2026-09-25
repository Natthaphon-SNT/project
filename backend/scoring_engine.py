"""
IT-RECOMMEND — Recommendation Scoring Engine

Weighted multi-criteria scoring (deterministic, no LLM):

    Score = 0.40 × Performance
          + 0.25 × Budget Efficiency
          + 0.20 × Compatibility
          + 0.10 × User Preference Alignment
          + 0.05 × Availability

Produces Top-3 ranked builds under different strategies:
    #1 Performance-focused   (max hardware capability)
    #2 Value-focused         (best score-per-baht)
    #3 Upgrade-path-focused  (newest platform + PSU headroom)

The LLM only EXPLAINS the ranking afterwards — every number here is
computed by code and reproducible.

Compatibility uses a severity-based policy: every failed/unknown rule lowers
the score proportionally, and a confirmed critical failure caps that component
at 50/100 regardless of how many other rules pass.
"""
import re
from typing import Optional

import spec_parser as sp
import compat_engine as ce

# ── Weights (sum = 1.00) ────────────────────────────────────────────
WEIGHTS = {
    "performance":      0.40,
    "budget":           0.25,
    "compatibility":    0.20,
    "preference":       0.10,
    "availability":     0.05,
}

STRATEGIES = [
    ("performance", "#1 Performance", "ประสิทธิภาพสูงสุดภายในงบ"),
    ("value",       "#2 Best Value",  "คุ้มค่าที่สุดเมื่อเทียบราคา"),
    ("upgrade",     "#3 Upgrade Path", "รองรับการอัปเกรดในอนาคต"),
]

COMPATIBILITY_SCORE_POLICY = {
    "method": "severity-based",
    "critical_failure_cap": 50,
    "warning_formula": "100 * passed_rules / total_rules",
}
COMPATIBILITY_SCORE_DESCRIPTION = (
    "Severity-based compatibility score: failed or unknown checks reduce the "
    "score in proportion to total checks; a confirmed critical failure caps "
    "the compatibility score at 50/100."
)

# ── Deterministic performance tables ───────────────────────────────
GPU_PERF_TABLE = [
    (r"RTX\s*5090", 100), (r"RTX\s*4090", 98), (r"RX\s*7900\s*XTX", 92),
    (r"RTX\s*5080", 90), (r"RTX\s*4080", 88), (r"RX\s*7900\s*XT", 85),
    (r"RTX\s*5070\s*TI", 82), (r"RTX\s*4070\s*TI", 78),
    (r"RX\s*7800\s*XT", 76), (r"RTX\s*5070", 74), (r"RTX\s*4070", 70),
    (r"RX\s*7700\s*XT", 68), (r"RX\s*9060\s*XT", 62), (r"RX\s*6800", 62),
    (r"RTX\s*5060\s*TI", 60), (r"RTX\s*4060\s*TI", 55),
    (r"RTX\s*5060", 52), (r"RTX\s*4060", 50), (r"RX\s*7600", 48),
    (r"RTX\s*3050", 32), (r"RX\s*6600", 38), (r"RX\s*6500\s*XT", 22),
]

CPU_PERF_TABLE = [
    (r"RYZEN\s*9", 95), (r"I9\b", 95), (r"CORE\s*ULTRA\s*9", 95),
    (r"THREADRIPPER", 100),
    (r"RYZEN\s*7", 82), (r"I7\b", 82), (r"CORE\s*ULTRA\s*7", 82),
    (r"RYZEN\s*5", 66), (r"I5\b", 66), (r"CORE\s*ULTRA\s*5", 64),
    (r"I3\b", 46), (r"RYZEN\s*3", 42),
]


def _gpu_perf(name_upper: str) -> int:
    for pat, score in GPU_PERF_TABLE:
        if re.search(pat, name_upper):
            return score
    return 35


def _cpu_perf(name_upper: str) -> int:
    for pat, score in CPU_PERF_TABLE:
        if re.search(pat, name_upper):
            return score
    return 50


def _clamp(v, lo=0, hi=100):
    return max(lo, min(hi, v))


# ── Component scores ────────────────────────────────────────────────
def score_performance(parsed_parts: list) -> float:
    gpu = next((p for p in parsed_parts if p.get("category") == "GPU"), None)
    cpu = next((p for p in parsed_parts if p.get("category") == "CPU"), None)
    g = _gpu_perf(gpu["name"].upper()) if gpu else 0
    c = _cpu_perf(cpu["name"].upper()) if cpu else 0
    if gpu and cpu:
        return round(0.6 * g + 0.4 * c, 1)
    if gpu:
        return float(g)
    return float(c)


def score_budget(total: float, budget: Optional[float]) -> float:
    """Peak efficiency at ~92% budget utilization; penalize both waste & overrun."""
    if not budget or budget <= 0 or total <= 0:
        return 50.0
    util = total / budget
    return round(_clamp(100 - abs(util - 0.92) * 250), 1)


def score_compatibility(compat_result: dict) -> float:
    """Score existing compatibility results without changing any rule verdict."""
    checks = compat_result.get("checks") or []
    if not checks:
        return 100.0

    failed = [check for check in checks
              if str(check.get("severity") or "UNKNOWN").upper() != "PASS"]
    score = 100.0 * (len(checks) - len(failed)) / len(checks)
    has_critical_failure = any(
        (check.get("score_severity") or ce.score_severity_for(check)) == "critical"
        for check in failed
    )
    if has_critical_failure:
        score = min(score, COMPATIBILITY_SCORE_POLICY["critical_failure_cap"])
    return round(_clamp(score), 1)


def score_preference(parsed_parts: list, budget: Optional[float], use_case: str) -> float:
    """Alignment between actual category spend and ideal allocation."""
    from recommender import ALLOCATIONS
    alloc = ALLOCATIONS.get(use_case, ALLOCATIONS["general"])
    b = budget or sum(p.get("price") or 0 for p in parsed_parts) or 1
    diff_sum = 0.0
    for cat, share in alloc.items():
        actual = sum((p.get("price") or 0) for p in parsed_parts if p.get("category") == cat) / b
        diff_sum += abs(actual - share)
    # diff_sum ranges 0 (perfect) .. ~1.5 (worst)
    return round(_clamp(100 - diff_sum * 180), 1)


def score_availability(candidates_used: list) -> float:
    """Average fraction of the 3 tracked stores that carry each chosen part."""
    if not candidates_used:
        return 50.0
    fracs = []
    for c in candidates_used:
        stores = sum(1 for v in c.get("prices", {}).values() if v and v > 0)
        fracs.append(stores / 3.0)
    return round(100 * sum(fracs) / len(fracs), 1)


def score_upgrade_path(parsed_parts: list) -> float:
    """Platform modernity + PSU headroom (used for strategy ranking, not main score)."""
    s = 40.0
    mb = next((p for p in parsed_parts if p.get("category") == "Mainboard"), None)
    ram = next((p for p in parsed_parts if p.get("category") == "RAM"), None)
    psu = next((p for p in parsed_parts if p.get("category") == "PSU"), None)
    cpu = next((p for p in parsed_parts if p.get("category") == "CPU"), None)
    if mb and mb.get("socket") in ("AM5", "LGA1851"):
        s += 30
    elif mb and mb.get("socket") in ("LGA1700",):
        s += 15
    if ram and ram.get("ddr_gen") == "DDR5":
        s += 15
    if psu and psu.get("watt"):
        total_draw = 80
        if cpu and cpu.get("tdp"): total_draw += cpu["tdp"]
        gpu = next((p for p in parsed_parts if p.get("category") == "GPU"), None)
        if gpu and gpu.get("tdp"): total_draw += gpu["tdp"]
        headroom = psu["watt"] / max(1, total_draw)
        s += _clamp((headroom - 1.2) * 100, 0, 15)
    return round(_clamp(s), 1)


# ── Full scoring ────────────────────────────────────────────────────
def score_build(parsed_parts: list, candidates_used: list,
                budget: Optional[float], use_case: str,
                budget_ceiling: bool = True) -> dict:
    """Returns full breakdown + weighted total (all deterministic)."""
    from recommender import heuristic_build  # circular-safe import inside fn

    compat = ce.check_build(parsed_parts, budget if budget_ceiling else None)
    total = sum(p.get("price") or 0 for p in parsed_parts)

    breakdown = {
        "performance":   score_performance(parsed_parts),
        "budget":        score_budget(total, budget),
        "compatibility": score_compatibility(compat),
        "preference":    score_preference(parsed_parts, budget, use_case),
        "availability":  score_availability(candidates_used),
    }
    total_score = round(sum(breakdown[k] * w for k, w in WEIGHTS.items()), 1)

    return {
        "score": total_score,
        "breakdown": breakdown,
        "weights": WEIGHTS,
        "total_price": total,
        "compat": compat,
        "compatibility_score_policy": COMPATIBILITY_SCORE_POLICY,
        "compatibility_score_description": COMPATIBILITY_SCORE_DESCRIPTION,
    }


def rank_strategies(builds: list) -> dict:
    """
    builds: list of dicts {strategy_key, parts(parsed), candidates_used, ...}
    Returns best build per strategy.
    """
    winners = {}
    for key, label, desc in STRATEGIES:
        pool = [b for b in builds if b.get("_strategy") == key] or builds
        if key == "performance":
            best = max(pool, key=lambda b: (b["scores"]["breakdown"]["performance"], b["scores"]["score"]))
        elif key == "value":
            best = max(pool, key=lambda b: b["scores"]["breakdown"]["budget"])
        else:
            best = max(pool, key=lambda b: (b.get("_upgrade", 0), b["scores"]["score"]))
        winners[key] = {"label": label, "desc": desc, **best}
    return winners
