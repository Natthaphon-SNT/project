# Mainboard Domain Knowledge

## Socket detection from names
- `(AM4)` / `A520` / `B450` / `B550` / `X570` → AM4
- `(AM5)` / `A620` / `B650` / `B650E` / `X670` → AM5
- `H610` / `B660` / `B760` / `Z690` / `Z790` → LGA1700
- `W8` / `B860` / `Z890` / board sold as "1851" → LGA1851

## Memory support
- AM5 & LGA1851 chipsets → DDR5 ONLY
- A520/B550/H610/B660/B760 → usually DDR4 (verify per model)

## Form factor detection
- `ITX` / `Mini-ITX` in name → ITX
- `mATX` / `Micro-ATX` / `M-ATX` or missing size marker → mATX (default in Thai market)
- `ATX` explicitly stated → ATX
