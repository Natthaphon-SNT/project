# GPU Domain Knowledge

## Chipset detection from names
- NVIDIA: `RTX 50xx/40xx/30xx`, `GTX 16xx`
- AMD: `RX 7000/9000`, `RX 6xxx`

## TDP tiers (approximate, used for PSU sizing)
| Class | Examples | Est. TDP |
|---|---|---|
| Entry | RTX 3050 6GB, RX 6500 XT | 75–130W |
| Mid | RTX 4060, RTX 5060, RX 7600 | 115–165W |
| Upper-mid | RTX 4060 Ti/4070, RX 7700 XT | 160–245W |
| High | RTX 4070 Ti/4080(S)/5070 Ti+, RX 7800 XT/7900 | 250W+ |

## Guidance
- Gaming builds: allocate 35–45% of total budget to GPU
- Avoid pairing entry CPU with high GPU (bottleneck) and vice versa
