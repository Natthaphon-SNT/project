import re

# Read log from task-697 log file
log_path = r"C:\Users\Acer\.gemini\antigravity-ide\brain\cb30041f-dc6a-449b-a5cc-c917b04ebe68\.system_generated\tasks\task-697.log"

with open(log_path, "r", encoding="utf-8", errors='ignore') as f:
    text = f.read()

# Find all lines containing "product_list"
keywords = ["CPU", "MAINBOARD", "MOTHERBOARD", "VGA", "GRAPHIC", "RAM", "SSD", "SOLID STATE", "HARDDISK", "POWER SUPPLY", "CASE", "COOLER", "COOLING", "WATER"]
matches = []
for line in text.splitlines():
    if "product_list/" in line:
        line_up = line.upper()
        # Find if it has keyword or is a category
        matches.append(line.strip())

# Write matching links to a text file for review
with open("jib_all_categories.txt", "w", encoding="utf-8") as f:
    for m in matches:
        f.write(m + "\n")

print(f"Written {len(matches)} links to jib_all_categories.txt")
