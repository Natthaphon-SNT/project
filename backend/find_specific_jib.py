import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open("jib_all_categories.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()

keywords = ["การ์ดแสดงผล", "พาวเวอร์ซัพพลาย", "ระบายความร้อน", "ฮาร์ดดิสก์", "โซลิดสเตต"]
for line in lines:
    line_up = line.upper()
    if any(kw in line_up for kw in keywords):
        print(line.strip())
