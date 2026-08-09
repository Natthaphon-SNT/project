import re

# Read log from find_jib_cats
with open(r"C:\Users\Acer\.gemini\antigravity-ide\brain\cb30041f-dc6a-449b-a5cc-c917b04ebe68\.system_generated\tasks\task-697.log", "r", encoding="utf-8") as f:
    text = f.read()

keywords = ["CPU", "MAINBOARD", "MOTHERBOARD", "VGA", "GRAPHIC", "RAM", "SSD", "SOLID STATE", "HARDDISK", "POWER SUPPLY", "CASE", "COOLER", "COOLING", "WATER"]
matches = []
for line in text.splitlines():
    if "product_list/" in line:
        line_up = line.upper()
        if any(kw in line_up for kw in keywords):
            matches.append(line)

print(f"Filtered {len(matches)} matching DIY components categories on JIB:")
for m in matches[:100]:
    print(m)
