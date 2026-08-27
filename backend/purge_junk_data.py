# -*- coding: utf-8 -*-
"""
1. Fix Corsair Warthog case price (6,650 Baht)
2. Purge all unrelated junk products from shop.db:
   - Flash drives, SD Cards, Micro SD cards, DVD trays
   - Power banks, Power tracks (รางไฟ/เต้ารับ), Power stations, Smart guards
   - Consoles, PS4/PS5, Xbox, Switch, ROG Ally, Gamepads/Joys, Steering wheels, Game discs
   - Phone cases (iPhone/iPad/Galaxy), Screen protectors
   - Sound cards, Audio interfaces (not PC components)
   - Pre-built OEM PCs, All-in-One PCs, Mini PCs, Server/Wall Racks, Rack shelves, Lan pliers, Faceplates, TVs, TV mounts, Tablets
3. Fix HDD/RAM classification
"""
import sqlite3
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DB_PATH = "shop.db"

# Patterns of products that MUST be deleted entirely from shop.db
PURGE_PATTERNS = [
    # Flash drives & Memory cards
    "%FLASH DRIVE%", "%SD CARD%", "%MICRO SD%", "%THUMB DRIVE%", "%DVD TRAY%",
    "%CARD READER%", "%EXT SSD%", "%EXTERNAL SSD%", "%PORTABLE SSD%", "%EXTERNAL HDD%",
    
    # Power junk & Consoles & Games
    "%POWER BANK%", "%POWER TRACK%", "%POWER STATION%", "%เต้ารับ%", "%รางไฟ%", "%ปลั๊ก%",
    "%PS5%", "%PS4%", "%PLAYSTATION%", "%XBOX%", "%NINTENDO%", "%SWITCH%",
    "%GAMEPAD%", "%CONTROLLER%", "%WHEEL%", "%พวงมาลัย%", "%ROG ALLY%", "%XBOX ALLY%",
    "%SMART GUARD%", "%CHARGER%", "%แผ่นเกม%", "%GAME SONY%", "%ADAPTER%",
    "%CAMERA%", "%กล้อง%",
    
    # Phone cases & non-PC cases
    "%IPHONE%", "%IPAD%", "%GALAXY%", "%เคสโทรศัพท์%", "%เคสมือถือ%", "%ซอง%", "%ฟิล์ม%",
    "%AIRSUIT%", "%FORCEGUARD%",
    
    # Sound cards
    "%SOUND CARD%", "%SOUNDCARD%", "%DAC%", "%AUDIO INTERFACE%",
    
    # Pre-builts, AIO, Mini PC, TVs, Tablets, Racks, Tools
    "%DESKTOP ASUS%", "%DESKTOP LENOVO%", "%AIO ASUS%", "%ALL-IN-ONE%",
    "%MINI PC%", "%NVIDIA DGX%", "%TABLET%", "%SURFACE%", "%LED TV%", "%SMART TV%",
    "%ขาแขวน TV%", "%ขาแขวน%", "%WALL RACK%", "%RACK SERVER%", "%ตู้ RACK%",
    "%คีม%", "%FACE PLATE%", "%WALL SCREEN%", "%TOUCH SCREEN%", "%INTERACTIVE LED%",
    "%VACUUM%", "%เครื่องดูดฝุ่น%", "%ROBOT VACUUM%", "%DUST MITE%"
]

def clean_database():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Fix Corsair Warthog Case price & img
    cur.execute("""
        UPDATE products 
        SET p_price = 6650, price_ihavecpu = 6650,
            img_url = 'https://ihcupload-bkk.s3.ap-southeast-7.amazonaws.com/img/product/products180087_800.jpg',
            category = 'Case', cid = 'c07'
        WHERE p_name LIKE '%WARTHOG%'
    """)
    print("[1] Fixed Corsair Warthog Case price to 6,650 Baht & image.")

    # 2. Purge junk products
    deleted_total = 0
    for pat in PURGE_PATTERNS:
        rows = cur.execute("SELECT product_id, p_name FROM products WHERE p_name LIKE ?", (pat,)).fetchall()
        if rows:
            for pid, name in rows:
                cur.execute("DELETE FROM products WHERE product_id = ?", (pid,))
                deleted_total += 1
                print(f"Deleted: [{name[:50]}]")

    print(f"\n[2] Deleted {deleted_total} non-relevant / junk products.")

    # 3. Clean up HDD from RAM category -> move to SSD/Storage
    cur.execute("""
        UPDATE products
        SET category = 'SSD', cid = 'c05'
        WHERE (p_name LIKE '%HDD%' OR p_name LIKE '%HARD DISK%' OR p_name LIKE '%SEAGATE BARRACUDA%' OR p_name LIKE '%WD BLUE%' OR p_name LIKE '%WD PURPLE%')
          AND category = 'RAM'
    """)
    print("[3] Moved HDDs out of RAM category.")

    # 4. Clean up any remaining Case category products that are not PC cases
    # Valid PC Case must not be a bracket/cable/fan
    cur.execute("""
        DELETE FROM products
        WHERE category = 'Case' AND (
            p_name LIKE '%CABLE%' OR p_name LIKE '%สาย%' OR p_name LIKE '%BRACKET%' OR p_name LIKE '%FAN%'
            OR p_name LIKE '%STAND%' OR p_name LIKE '%ขาตั้ง%'
        )
    """)

    conn.commit()

    # Final DB counts by category
    print("\n--- Final Category Counts in DB ---")
    rows = cur.execute("SELECT category, cid, COUNT(*) FROM products GROUP BY category, cid ORDER BY category").fetchall()
    for cat, cid, count in rows:
        print(f"  {cat:15} ({cid}): {count} products")

    cur.execute("SELECT COUNT(*) FROM products")
    total = cur.fetchone()[0]
    print(f"\nTotal clean products remaining in DB: {total}")
    conn.close()

if __name__ == "__main__":
    clean_database()
