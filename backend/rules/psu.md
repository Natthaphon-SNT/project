# PSU Domain Knowledge

## Wattage detection
- Pattern `\d{3,4}W` in name (e.g. `600W`, `550W`)
- Efficiency grade: `80+ WHITE/BRONZE/GOLD` — prefer Bronze minimum

## Sizing rule
estimated_draw = cpu_power + gpu_board_power + 80 (base system allowance)
estimated_psu = ceil(estimated_draw * 1.25)
required_psu = max(manufacturer_recommended_system_psu, estimated_psu)

GPU board consumption is not the system PSU requirement. RTX 5050 desktop:
130W board power and 550W required system PSU, per NVIDIA reference specification.
https://www.nvidia.com/en-us/geforce/graphics-cards/50-series/rtx-5050/

Leadtek RTX PRO 5000 Blackwell desktop: 300W board consumption. Do not invent a
manufacturer system PSU recommendation when the source does not specify it.
https://www.leadtek.com/eng/products/workstation_graphics(2)/nvidia_rtx_pro_5000_blackwell(51030)/detail

## Guidance
- Fail the wattage check below the stricter requirement. Do not predict certain shutdowns.
- Missing GPU/CPU power, PSU wattage or GPU PSU recommendation must not produce PASS.
- Cite manufacturer values separately from the system/headroom estimate.
- Verify exact desktop model and board; exclude laptop variants and mismatched store URLs.
- Wattage alone does not validate connectors, PSU quality, or full-load CPU turbo consumption.
