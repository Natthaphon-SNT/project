# Compatibility Rules — IT-RECOMMEND

Knowledge base for deterministic PC compatibility validation.
Each rule below is ENFORCED BY CODE in `compat_engine.py` — the LLM is never
allowed to decide compatibility. This file is the human-readable source of truth.

---

## R1: CPU Socket ↔ Mainboard Socket

### Rule
CPU socket MUST equal mainboard socket.

### Facts
- AMD AM4 → Ryzen 1000/3000/5000 series (e.g. Ryzen 5 5600, Ryzen 7 5800X)
- AMD AM5 → Ryzen 7000/8000/9000 series (e.g. Ryzen 5 7500F, Ryzen 7 7800X3D)
- Intel LGA1700 → Core 12th/13th/14th gen (i3/i5/i7/i9-12xxx/13xxx/14xxx)
- Intel LGA1851 → Core Ultra 200S series (e.g. Core Ultra 5 225F)

### Severity
ERROR

### Validation
Deterministic (spec_parser extracts socket from product name)

---

## R2: RAM Generation ↔ Mainboard Memory Type

### Rule
RAM DDR generation MUST be supported by the mainboard.

### Facts
- AM4 / LGA1700 boards ship with DDR4 or DDR4+DDR5 (chipset dependent)
- AM5 / LGA1851 boards are DDR5 ONLY
- A520/B450 boards are typically DDR4 only

### Severity
ERROR

### Validation
Deterministic

---

## R3: PSU Wattage ↔ System Power Draw

### Rule
PSU wattage MUST be >= total system draw (CPU TDP + GPU TDP + 80W base) and
should have >= 20% headroom.

### Severity
- Below required draw: ERROR
- Below recommended headroom: WARNING

### Validation
Deterministic

---

## R4: CPU Cooler ↔ CPU Socket and TDP

### Rule
The cooler MUST explicitly support the CPU socket. A known socket mismatch is
an ERROR. Separately, cooler TDP rating SHOULD be >= CPU TDP.

### Facts
- Stock-style tower coolers (SE-214, AS-120 class) ≈ 120–150W rating
- CPU TDP estimated by tier: 65W default, 105W for X/X3D high tiers,
  125W+ for i9/Ryzen 9

### Severity
WARNING (thermal throttling risk, not a hard incompatibility)

### Validation
Deterministic (estimated)

---

## R5: Case Form Factor ↔ Mainboard Form Factor

### Rule
Case supported motherboard sizes MUST include the mainboard form factor.
Ordering: ATX case fits ATX/mATX/ITX; mATX case fits mATX/ITX; ITX case fits ITX only.

### Severity
ERROR for a known socket mismatch; WARNING for insufficient thermal rating.

### Validation
Deterministic

---

## R6: GPU ↔ PSU Power Connectors / Tier

### Rule
High-tier GPUs (approximately 240W+ board power or a manufacturer PSU
recommendation of 750W+) require PSU >= 750W. The GPU's explicit connector
requirements must also be present on the PSU.

### Severity
WARNING

### Validation
Deterministic (tier table)

---

## R8: GPU <-> PSU Power Connector

### Rule
For every known GPU connector requirement, the PSU must expose at least the
same connector count. PCIe 6+2-pin satisfies PCIe 8-pin. A missing connector
specification is `UNKNOWN`, never PASS.

### Severity
- Known mismatch: ERROR
- Missing connector evidence: UNKNOWN

### Validation
Deterministic (manufacturer/product specs)

---

## R7: Budget Adherence

### Rule
Total real price (min across Advice/JIB/iHaveCPU) MUST NOT exceed the user's
stated budget. Any excess is reported explicitly and is never marked PASS.

### Severity
WARNING

### Validation
Deterministic

---

## LLM Boundary

The verdict and every compatibility claim from `compat_engine.py` are the
highest-priority truth. LLM output may add neutral usage advice, but it MUST NOT
claim that parts are compatible/incompatible, override a verdict, or contradict
any deterministic check. Conflicting LLM suggestions are discarded by code.
