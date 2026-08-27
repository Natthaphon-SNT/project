# -*- coding: utf-8 -*-
import sqlite3, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

conn = sqlite3.connect('shop.db')
cur = conn.cursor()

# 1. Invalid img_url (data:image or corrupt base64)
bad_imgs = cur.execute("SELECT product_id, p_name, img_url FROM products WHERE img_url LIKE '%data:image%' OR img_url LIKE '%base64%' OR img_url LIKE '%.gif%'").fetchall()
print(f"Products with invalid placeholder img_url: {len(bad_imgs)}")
for b in bad_imgs:
    print(b)

# 2. Check category mismatches
cat_rules = [
    ('CPU', 'c01', r'\bCPU\b|RYZEN|INTEL CORE|CORE ULTRA'),
    ('Mainboard', 'c02', r'MAINBOARD|MOTHERBOARD'),
    ('GPU', 'c03', r'\bVGA\b|\bGPU\b|GEFORCE|RTX|RADEON|RX \d'),
    ('RAM', 'c04', r'\bRAM\b|DDR4|DDR5'),
    ('SSD', 'c05', r'\bSSD\b|M\.2 NVME|NVME M\.2|SN850|990 PRO'),
    ('PSU', 'c06', r'POWER SUPPLY|\bPSU\b'),
    ('Case', 'c07', r'CASE|เคส'),
    ('Liquid Cooler', 'c08', r'LIQUID COOLER|AIO COOLER|WATER COOLING'),
    ('Air Cooler', 'c09', r'AIR COOLER|CPU COOLER|HEAT SINK'),
    ('Mouse', 'c10', r'MOUSE|เมาส์'),
    ('Keyboard', 'c11', r'KEYBOARD|คีย์บอร์ด'),
    ('Headset', 'c12', r'HEADSET|HEADPHONE|หูฟัง'),
    ('Monitor', 'c14', r'MONITOR|จอภาพ|LED MONITOR|IPS MONITOR'),
    ('Gaming Chair', 'c15', r'GAMING CHAIR|CHAIR|เก้าอี้'),
    ('Gaming Desk', 'c16', r'GAMING DESK|DESK|โต๊ะ'),
]

mismatches = []
rows = cur.execute("SELECT product_id, p_name, category, cid FROM products").fetchall()
for pid, name, cat, cid in rows:
    n_up = name.upper()
    for true_cat, true_cid, pat in cat_rules:
        # If name strongly matches pattern but category is completely different
        if re.search(pat, n_up):
            # Check if current category is clearly wrong
            # e.g. Name starts with RAM, but category is Headset or Gaming Desk
            if (n_up.startswith('RAM ') or n_up.startswith('DDR4') or n_up.startswith('DDR5') or ' DDR4 ' in n_up or ' DDR5 ' in n_up) and cat not in ['RAM', 'PC Set']:
                mismatches.append((pid, name, cat, true_cat, true_cid))
                break
            elif n_up.startswith('CPU ') and cat not in ['CPU', 'PC Set', 'Liquid Cooler', 'Air Cooler']:
                mismatches.append((pid, name, cat, true_cat, true_cid))
                break
            elif (n_up.startswith('VGA ') or n_up.startswith('GPU ')) and cat not in ['GPU', 'PC Set']:
                mismatches.append((pid, name, cat, true_cat, true_cid))
                break
            elif (n_up.startswith('KEYBOARD ') or n_up.startswith('คีย์บอร์ด')) and cat != 'Keyboard':
                mismatches.append((pid, name, cat, true_cat, true_cid))
                break
            elif (n_up.startswith('MOUSE ') or n_up.startswith('เมาส์')) and cat != 'Mouse':
                mismatches.append((pid, name, cat, true_cat, true_cid))
                break

print(f"\nCategory mismatches found: {len(mismatches)}")
for m in mismatches[:10]:
    print(m)

conn.close()
