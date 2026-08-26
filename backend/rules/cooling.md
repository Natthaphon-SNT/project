# Cooling Domain Knowledge

## Categories in DB
- `Air Cooler`: tower heatsink + fan (e.g. ID-COOLING SE-214-XT)
- `Liquid Cooler`: AIO (e.g. FLOE 240). Note: many `FAN ...` rows are case fans,
  not CPU coolers — treat plain `FAN` without cooler keywords as UNKNOWN.

## Rating estimation
- SE-214-XT / AS-120 class single-tower: ~120–150W TDP rating
- Dual-tower (PA120 class): ~180–220W
- 240mm AIO: ~200W+, 360mm AIO: ~250W+

## Rule
cooler_rating >= cpu_tdp else WARNING (throttling risk).
