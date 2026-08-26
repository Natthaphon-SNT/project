# PSU Domain Knowledge

## Wattage detection
- Pattern `\d{3,4}W` in name (e.g. `600W`, `550W`)
- Efficiency grade: `80+ WHITE/BRONZE/GOLD` — prefer Bronze minimum

## Sizing rule
required_watt = cpu_tdp + gpu_tdp + 80 (base system)
recommended_watt = required_watt * 1.2 (headroom)

## Guidance
- Never cheap out below required draw: random shutdowns under load
- High-end GPUs need >= 750W
