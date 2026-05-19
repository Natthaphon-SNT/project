import pandas as pd
import itertools

def generate_infinity_catalog():
    data = []
    
    # ฟังก์ชันช่วยเพิ่มข้อมูล
    def add_item(cat, brand, model, price, socket="-", mem_type="-", watt=0, tdp=0, igpu=0, score_g=0, score_e=0, m2=0):
        data.append([cat, brand, model, price, price-100, price+100, socket, mem_type, watt, tdp, igpu, score_g, score_e, m2])

    # ==========================================
    # 1. CPU (เจาะลึกทุกรหัสย่อย)
    # ==========================================
    # Intel Ultra
    ultra_models = [("Ultra 9", ["285K", "285", "285T"]), ("Ultra 7", ["265K", "265KF", "265", "265F", "265T"]), ("Ultra 5", ["245K", "245KF", "245", "235", "225", "225F"])]
    for fam, mods in ultra_models:
        for m in mods:
            add_item("CPU", "Intel", f"Core {fam} {m}", 15000, "LGA1851", "-", 0, 125 if "K" in m else 65, 0 if "F" in m else 1, 95, 95)
    
    # Intel Gen 12, 13, 14
    for gen in ["14", "13", "12"]:
        for suf in ["900KS", "900K", "900KF", "900F", "900", "700K", "700KF", "700", "700F", "600K", "600KF", "500", "400", "400F", "100", "100F"]:
            fam = "i9" if suf.startswith("9") else "i7" if suf.startswith("7") else "i5" if suf.startswith(("6","5","4")) else "i3"
            add_item("CPU", "Intel", f"Core {fam}-{gen}{suf}", 10000, "LGA1700", "-", 0, 125 if "K" in suf else 65, 0 if "F" in suf else 1, 85, 85)

    # AMD Ryzen 9000, 8000, 7000, 5000
    amd_series = [
        ("AM5", "9", ["9950X", "9900X", "9900", "9700X", "9600X", "9600"]),
        ("AM5", "8", ["8700G", "8600G", "8500G", "8400F", "8700F"]),
        ("AM5", "7", ["7950X3D", "7950X", "7900X3D", "7900X", "7900", "7800X3D", "7700X", "7700", "7600X", "7600", "7500F"]),
        ("AM4", "5", ["5950X", "5900X", "5800X3D", "5800X", "5700X3D", "5700X", "5700G", "5600X3D", "5600X", "5600G", "5600", "5500", "4500", "4600G"])
    ]
    for socket, _, models in amd_series:
        for m in models:
            fam = "Ryzen 9" if m.startswith(("9","59","79")) else "Ryzen 7" if m.startswith(("7","87","57","58")) else "Ryzen 5" if m.startswith(("5","6","86","85","84","75","76","56","46","45")) else "Ryzen 3"
            add_item("CPU", "AMD", f"{fam} {m}", 12000, socket, "-", 0, 105 if "X" in m else 65, 1 if "G" in m else 0, 85, 80)

    # ==========================================
    # 2. GPU (แยกย่อยทุก Series ของทุกแบรนด์)
    # ==========================================
    nvidia_chips = [
        "RTX 4090 24GB", "RTX 4080 SUPER 16GB", "RTX 4080 16GB", "RTX 4070 Ti SUPER 16GB", "RTX 4070 Ti 12GB", 
        "RTX 4070 SUPER 12GB", "RTX 4070 12GB", "RTX 4060 Ti 16GB", "RTX 4060 Ti 8GB", "RTX 4060 8GB",
        "RTX 3090 24GB", "RTX 3080 10GB", "RTX 3070 Ti 8GB", "RTX 3070 8GB", "RTX 3060 Ti 8GB", "RTX 3060 12GB", "RTX 3050 8GB", "RTX 3050 6GB"
    ]
    amd_chips = [
        "RX 7900 XTX 24GB", "RX 7900 XT 20GB", "RX 7900 GRE 16GB", "RX 7800 XT 16GB", "RX 7700 XT 12GB", 
        "RX 7600 XT 16GB", "RX 7600 8GB", "RX 6800 XT 16GB", "RX 6700 XT 12GB", "RX 6600 8GB"
    ]

    gpu_variants = {
        "ASUS": ["ROG Strix Gaming", "TUF Gaming", "Dual", "ProArt", "Noctua Edition"],
        "MSI": ["Suprim X", "Gaming X Trio", "Gaming X Slim", "Ventus 3X", "Ventus 2X"],
        "Gigabyte": ["AORUS Master", "AORUS Elite", "Gaming OC", "Aero", "Eagle", "Windforce"],
        "Zotac": ["AMP Extreme AIRO", "Trinity", "Twin Edge"],
        "Galax": ["HOF", "SG", "EX Gamer"],
        "Sapphire": ["Nitro+", "Pulse", "Pure"],
        "PowerColor": ["Red Devil", "Hellhound", "Fighter"],
        "ASRock": ["Taichi", "Phantom Gaming", "Steel Legend", "Challenger"]
    }

    for brand, series_list in gpu_variants.items():
        # กำหนดว่าแบรนด์นี้ทำชิปค่ายไหน
        chips_to_make = []
        if brand in ["ASUS", "MSI", "Gigabyte", "ASRock"]: chips_to_make.extend([("GeForce", c) for c in nvidia_chips])
        if brand in ["Zotac", "Galax"]: chips_to_make.extend([("GeForce", c) for c in nvidia_chips])
        if brand in ["ASUS", "MSI", "Gigabyte", "Sapphire", "PowerColor", "ASRock"]: chips_to_make.extend([("Radeon", c) for c in amd_chips])
        
        for prefix, chip in set(chips_to_make):
            for series in series_list:
                # ลดขยะ: ตัวเล็กๆ (เช่น Dual, Ventus 2X) ไม่ควรไปคู่กับชิปเรือธง (เช่น 4090)
                if ("4090" in chip or "7900 XTX" in chip) and ("Dual" in series or "Ventus 2X" in series or "Twin Edge" in series or "Fighter" in series):
                    continue
                # รุ่น HOF/Suprim X มักจะทำแต่ตัวท็อป
                if ("HOF" in series or "Suprim" in series) and ("4060" in chip or "3050" in chip):
                    continue
                
                watt = 350 if "90" in chip or "80" in chip else 200
                add_item("GPU", brand, f"{prefix} {chip} {series}", 25000, "-", "-", watt, 0, 0, 90, 85, 0)

    # ==========================================
    # 3. Mainboard (แยกย่อยทุกชิปเซ็ต ทุก Series)
    # ==========================================
    mb_chipsets = [
        ("Intel", "Z890", ["DDR5"]), ("Intel", "B860", ["DDR5"]), ("Intel", "Z790", ["DDR4", "DDR5"]), ("Intel", "B760", ["DDR4", "DDR5"]), ("Intel", "H610", ["DDR4"]),
        ("AMD", "X870E", ["DDR5"]), ("AMD", "X870", ["DDR5"]), ("AMD", "B650E", ["DDR5"]), ("AMD", "B650", ["DDR5"]), ("AMD", "A620", ["DDR5"]),
        ("AMD", "X570", ["DDR4"]), ("AMD", "B550", ["DDR4"]), ("AMD", "A520", ["DDR4"])
    ]

    mb_variants = {
        "ASUS": ["ROG Maximus", "ROG Crosshair", "ROG Strix", "TUF Gaming", "ProArt", "Prime"],
        "Gigabyte": ["AORUS Xtreme", "AORUS Master", "AORUS Elite", "AERO G", "Gaming X", "UD"],
        "MSI": ["MEG", "MPG", "MAG", "PRO"],
        "ASRock": ["Taichi", "Nova", "Steel Legend", "Phantom Gaming", "Riptide", "PRO RS", "HDV"]
    }

    for brand, series_list in mb_variants.items():
        for cpu_brand, chip, ram_types in mb_chipsets:
            for series in series_list:
                # ป้องกันขยะ: ROG Maximus มีแค่ใน Intel Z, ROG Crosshair มีแค่ใน AMD X
                if series == "ROG Maximus" and ("Z" not in chip): continue
                if series == "ROG Crosshair" and ("X" not in chip): continue
                if series in ["MEG", "AORUS Xtreme", "Taichi"] and chip.startswith(("H", "A", "B")): continue # บอร์ดเทพไม่ทำชิปเซ็ตต่ำ
                
                for size in ["", "-M", "-I"]: # ATX, mATX, ITX
                    for ram in ram_types:
                        suffix = " WIFI" if chip.startswith(("Z", "X", "B")) else ""
                        ddr_suffix = f" {ram}" if ram == "DDR4" else "" # ปกติบอร์ด DDR5 มักไม่เขียนบอก แต่ DDR4 จะเขียน
                        add_item("Mainboard", brand, f"{series} {chip}{size}{ddr_suffix}{suffix}", 5000, chip, ram, 0, 0, 0, 0, 0, 2 if size=="-M" else 1 if size=="-I" else 3)

    # ==========================================
    # 4. RAM (แยกทุกซีรีส์)
    # ==========================================
    ram_series = {
        "Corsair": ["Dominator Titanium RGB", "Dominator Platinum RGB", "Vengeance RGB", "Vengeance LPX", "Vengeance"],
        "Kingston": ["FURY Renegade RGB", "FURY Renegade", "FURY Beast RGB", "FURY Beast"],
        "G.SKILL": ["Trident Z5 Royal", "Trident Z5 RGB", "Trident Z5 Neo RGB", "Ripjaws S5", "Flare X5"],
        "TeamGroup": ["T-Force Delta RGB", "T-Create Expert", "T-Force Vulcan Z"],
        "ADATA": ["XPG Lancer RGB", "XPG Lancer Blade", "XPG Hunter"]
    }
    ram_configs = [
        ("DDR4", ["3200MHz", "3600MHz"], ["16GB (8GBx2)", "32GB (16GBx2)", "64GB (32GBx2)"]),
        ("DDR5", ["5200MHz", "5600MHz", "6000MHz", "6400MHz", "7200MHz"], ["32GB (16GBx2)", "48GB (24GBx2)", "64GB (32GBx2)", "96GB (48GBx2)"])
    ]
    for brand, s_list in ram_series.items():
        for series in s_list:
            for r_type, speeds, caps in ram_configs:
                # DDR5 Series ควรคู่กับ DDR5 เท่านั้น
                if ("Z5" in series or "Titanium" in series) and r_type == "DDR4": continue
                if "LPX" in series and r_type == "DDR5": continue
                for speed in speeds:
                    for cap in caps:
                        add_item("RAM", brand, f"{series} {cap} {r_type} {speed}", 3500, "-", r_type)

    # ==========================================
    # 5. SSD (ระบุชื่อรุ่นตรงๆ เลย เพราะ SSD มีรุ่นตายตัว)
    # ==========================================
    ssds = [
        ("Samsung", ["990 PRO", "990 EVO", "980 PRO", "970 EVO Plus", "870 EVO (SATA)"]),
        ("WD", ["Black SN850X", "Black SN770", "Blue SN580", "Green SN350"]),
        ("Kingston", ["FURY Renegade", "KC3000", "NV3", "NV2", "A400 (SATA)"]),
        ("Crucial", ["T705 (Gen5)", "T700 (Gen5)", "T500", "P3 Plus", "BX500 (SATA)"]),
        ("Corsair", ["MP700 PRO (Gen5)", "MP600 PRO", "MP600 CORE"])
    ]
    for brand, models in ssds:
        for model in models:
            for cap in ["250GB", "500GB", "1TB", "2TB", "4TB"]:
                if "Gen5" in model and cap in ["250GB", "500GB"]: continue # Gen5 ไม่มีตัวเล็ก
                if "PRO" in model and cap == "250GB": continue
                add_item("SSD", brand, f"{model} {cap}", 3000)

    # ==========================================
    # 6. PSU (แยกตาม Series สายพรีเมียม / สายประหยัด)
    # ==========================================
    psu_series = {
        "Corsair": ["AX", "HX", "RMx", "RMe", "CX", "CV"],
        "Seasonic": ["Prime TX", "Prime PX", "Vertex GX", "Focus GX", "B12"],
        "Thermaltake": ["Toughpower GF3", "Toughpower GF1", "Smart BM2", "Litepower"],
        "FSP": ["Hydro Ti PRO", "Hydro G PRO", "Hydro PTM", "HV PRO"],
        "Cooler Master": ["V Platinum", "V Gold", "MWE Gold", "MWE Bronze"]
    }
    for brand, s_list in psu_series.items():
        for series in s_list:
            for watt in [450, 550, 650, 750, 850, 1000, 1200, 1600]:
                # ซีรีส์เทพ มักไม่ทำวัตต์น้อย
                if series in ["AX", "Prime TX", "Hydro Ti PRO", "V Platinum"] and watt < 850: continue
                # ซีรีส์ประหยัด มักไม่ทำวัตต์สูง
                if series in ["CV", "B12", "Litepower", "HV PRO"] and watt > 750: continue
                
                cert = "80+ Titanium" if "Ti" in series or "TX" in series or "AX" in series else \
                       "80+ Platinum" if "PX" in series or "Platinum" in series else \
                       "80+ Gold" if "Gold" in series or "G" in series or "RM" in series else \
                       "80+ Bronze" if "Bronze" in series or "B" in series or "CX" in series else "80+ White"
                
                atx_type = " ATX 3.0" if watt >= 750 and "Gold" in cert else ""
                add_item("PSU", brand, f"{series} {watt}W ({cert}{atx_type})", 4000, "-", "-", watt)

    # ==========================================
    # 7. Cooler (ชุดน้ำ AIO และ ซิงค์ลม) - **ใหม่!**
    # ==========================================
    coolers = {
        "NZXT": ["Kraken Elite 360", "Kraken Elite 280", "Kraken 360", "Kraken 240"],
        "Corsair": ["iCUE Link H150i LCD", "iCUE H150i ELITE CAPELLIX", "H100i", "A115"],
        "ASUS": ["ROG Ryujin III 360", "ROG Strix LC III 360", "TUF Gaming LC II 360"],
        "Thermalright": ["Peerless Assassin 120 SE", "Phantom Spirit 120", "Frozen Notte 360", "Aqua Elite 240"],
        "Deepcool": ["LS720", "LS520", "LT720", "AK620", "AK400", "AG400"],
        "Noctua": ["NH-D15 chromax.black", "NH-U12A", "NH-U12S"],
        "Cooler Master": ["MasterLiquid 360L", "MasterLiquid 240L", "Hyper 212 Halo"]
    }
    for brand, models in coolers.items():
        for model in models:
            add_item("Cooler", brand, model, 3000)

    # ==========================================
    # 8. Case (อิงตามชื่อรุ่นยอดฮิต)
    # ==========================================
    cases = {
        "NZXT": ["H9 Elite", "H9 Flow", "H7 Flow", "H6 Flow", "H5 Flow"],
        "Corsair": ["1000D", "7000D Airflow", "5000D Airflow", "4000D Airflow", "3500X", "2500X"],
        "Lian Li": ["O11 Dynamic EVO", "O11 Vision", "Lancool III", "Lancool 216", "A4-H2O"],
        "Montech": ["King 95 Pro", "Sky Two", "AIR 903 Max", "AIR 100 ARGB"],
        "Fractal Design": ["North", "Torrent", "Meshify 2", "Pop Air", "Terra"],
        "Phanteks": ["NV9", "NV7", "NV5", "Eclipse G500A", "Eclipse G360A"]
    }
    for brand, models in cases.items():
        for model in models:
            add_item("Case", brand, model, 3500)

    # สรุปผล
    cols = ['category', 'brand', 'model', 'price_jib', 'price_advice', 'price_ihavecpu', 'socket', 'memory_type', 'wattage', 'tdp', 'has_igpu', 'score_gaming', 'score_editing', 'max_m2_slots']
    df = pd.DataFrame(data, columns=cols)
    df.to_csv('hardware_latest.csv', index=False)
    print(f"🔥 สร้างไฟล์ hardware_latest.csv สำเร็จ! จำนวนทั้งหมด: {len(df):,} รายการ")
    print(f"✅ ครอบคลุม: {len(df[df['category']=='GPU'])} GPUs | {len(df[df['category']=='Mainboard'])} Mainboards | {len(df[df['category']=='RAM'])} RAMs | {len(df[df['category']=='CPU'])} CPUs")

if __name__ == "__main__":
    generate_infinity_catalog()