# -*- coding: utf-8 -*-
import sqlite3, sys, io, re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

conn = sqlite3.connect('shop.db')
cur = conn.cursor()

# 1. Check Corsair Warthog case
print("--- Corsair Warthog Case ---")
rows = cur.execute("SELECT product_id, p_name, p_price, price_advice, price_jib, price_ihavecpu, url_ihavecpu FROM products WHERE p_name LIKE '%WARTHOG%'").fetchall()
for r in rows:
    print(r)

# 2. Check Flash Drives / SD Cards
print("\n--- Flash Drives / SD Cards in DB ---")
fd_rows = cur.execute("SELECT product_id, p_name, category FROM products WHERE p_name LIKE '%FLASH DRIVE%' OR p_name LIKE '%SD CARD%' OR p_name LIKE '%MICRO SD%' OR p_name LIKE '%THUMB DRIVE%' OR p_name LIKE '%DVD TRAY%' OR p_name LIKE '%EXT SSD%' OR p_name LIKE '%EXTERNAL SSD%' OR p_name LIKE '%PORTABLE SSD%'").fetchall()
print(f"Count: {len(fd_rows)}")
for r in fd_rows[:10]:
    print(r)

# 3. Check PSU junk (Power Bank, Power Track, Power Station, Games, Consoles, Joy, Wheel)
print("\n--- PSU Junk in DB ---")
psu_junk = cur.execute("""
    SELECT product_id, p_name, category FROM products 
    WHERE p_name LIKE '%POWER BANK%' OR p_name LIKE '%POWER TRACK%' OR p_name LIKE '%POWER STATION%'
       OR p_name LIKE '%เต้ารับ%' OR p_name LIKE '%รางไฟ%' OR p_name LIKE '%ปลั๊ก%'
       OR p_name LIKE '%PS5%' OR p_name LIKE '%PS4%' OR p_name LIKE '%PLAYSTATION%'
       OR p_name LIKE '%XBOX%' OR p_name LIKE '%NINTENDO%' OR p_name LIKE '%SWITCH%'
       OR p_name LIKE '%JOY%' OR p_name LIKE '%GAMEPAD%' OR p_name LIKE '%CONTROLLER%'
       OR p_name LIKE '%WHEEL%' OR p_name LIKE '%พวงมาลัย%' OR p_name LIKE '%ALLY%'
       OR p_name LIKE '%SMART GUARD%' OR p_name LIKE '%CHARGER%' OR p_name LIKE '%ADAPTER%'
       OR p_name LIKE '%GAME SONY%' OR p_name LIKE '%แผ่นเกม%'
""").fetchall()
print(f"Count: {len(psu_junk)}")
for r in psu_junk[:10]:
    print(r)

# 4. Check Case Junk (Phone cases, Soundcards, Prebuilts, Tablets, TVs, Racks)
print("\n--- Case Junk / General Junk in DB ---")
case_junk = cur.execute("""
    SELECT product_id, p_name, category FROM products
    WHERE p_name LIKE '%IPHONE%' OR p_name LIKE '%IPAD%' OR p_name LIKE '%GALAXY%'
       OR p_name LIKE '%SOUND CARD%' OR p_name LIKE '%SOUNDCARD%'
       OR p_name LIKE '%DESKTOP ASUS%' OR p_name LIKE '%DESKTOP LENOVO%' OR p_name LIKE '%AIO ASUS%' OR p_name LIKE '%ALL-IN-ONE%'
       OR p_name LIKE '%MINI PC%' OR p_name LIKE '%NVIDIA DGX%'
       OR p_name LIKE '%TABLET%' OR p_name LIKE '%SURFACE%' OR p_name LIKE '%LED TV%' OR p_name LIKE '%SMART TV%'
       OR p_name LIKE '%ขาแขวน TV%' OR p_name LIKE '%WALL RACK%' OR p_name LIKE '%RACK SERVER%' OR p_name LIKE '%ตู้ RACK%'
       OR p_name LIKE '%คีม%' OR p_name LIKE '%FACE PLATE%' OR p_name LIKE '%WALL SCREEN%' OR p_name LIKE '%TOUCH SCREEN%'
""").fetchall()
print(f"Count: {len(case_junk)}")
for r in case_junk[:10]:
    print(r)

conn.close()
