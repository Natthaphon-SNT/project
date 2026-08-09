import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open("jib_all_categories.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()

keywords = ["ซีพียู", "CPU", "เมนบอร์ด", "MAINBOARD", "การ์ดจอ", "VGA", "GRAPHIC", "แรม", "RAM", "SSD", "M.2", "POWER SUPPLY", "เคส", "CASE", "COOLER", "COOLING", "ชุดน้ำ"]
for line in lines:
    line_up = line.upper()
    if any(kw.upper() in line_up for kw in keywords):
        print(line.strip())
