"""Combine reproducible QA evidence into the Thai report and coverage matrix."""
import collections
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]; OUT=Path(__file__).resolve().parent
NAMES={1:'Auth & Users',2:'Products & Pricing',3:'PC Builder & Compatibility',4:'AI Recommend',5:'Spec History',6:'Cart / Checkout / Orders',7:'Admin Panel',8:'Scraper & Database',9:'Non-Functional'}

def extra(id,group,steps,expected,actual,status='Pass',source='',fix='',severity=''):
    return dict(id=id,group=group,steps=steps,expected=expected,actual=actual,status=status,source=source,fix=fix,severity=severity)

def main():
    rs=[]
    files=['api-results.json','browser-results.json','supplemental-results.json','scraper-results.json','crossbrowser-results.json']
    for file in files:rs+=json.loads((OUT/file).read_text(encoding='utf8'))
    rs += [
        extra('REG01',4,'python -B -m unittest discover -s backend -p test_ai_sessions.py -v','tests ผ่าน','7/7 ผ่าน: settings isolation, session CRUD/ownership, provider HTTP mocks, migration, removed provider, DB identity'),
        extra('REG02',3,'python -B -m unittest discover -s backend -p test_power_compatibility.py -v','tests ผ่าน','14/14 ผ่าน: PSU minimum, board draw, rails, connector, UNKNOWN, sourced facts'),
        extra('REG03',4,'python -B -m unittest discover -s backend -p test_recommender_knowledge.py -v','tests ผ่าน','1/1 ผ่าน: candidate prompt contains sourced normalized power facts'),
        extra('REG04',8,'python -B -m unittest discover -s backend -p test_product_matching.py -v','tests ผ่าน','9/9 ผ่าน: SKU/brand/wattage conflicts, same-retail alias, relevant descriptions'),
        extra('REG05',8,'python -B -m unittest discover -s backend -p test_scraper_source_data.py -v','tests ผ่าน','7/7 ผ่าน: Advice price/URL, iHaveCPU Next payload, installments, category repair, variant matching'),
        extra('REG06',4,'python -B backend/test_ai_ui.py หลัง development build','browser regression ผ่าน','ผ่าน guest access, provider tabs, key isolation/toggle, save settings, history load/new/delete, expired login; mock API'),
        extra('BUILD',9,'npm --prefix It-shop run build -- --configuration development','build สำเร็จ','exit0; main 2.31MB; total 2.32MB; 4 Angular NG8107 warnings'),
        extra('UNITUI',9,'npm --prefix It-shop test -- --watch=false','ทุก test ผ่าน ไม่มี unhandled rejection','14/14 tests ผ่าน; 13/13 test files ผ่าน; เพิ่ม Router/ActivatedRoute และ HTTP testing providers','Pass','It-shop/src/app/**/*.spec.ts'),
        extra('NA01',6,'ตรวจ app.routes.ts สำหรับ /cart และ /checkout','เทียบขอบเขตกับระบบปัจจุบัน','ไม่มีหน้า cart/checkout; wildcard redirect หน้าแรก จึงไม่มี UI ให้ทดสอบเพิ่มหลายหน้า/แก้จำนวน/checkout','N/A','It-shop/src/app/app.routes.ts'),
        extra('NA02',7,'ตรวจ app.routes.ts สำหรับ /admin/orders','เทียบขอบเขตกับระบบปัจจุบัน','ไม่มีหน้า admin/orders; ทดสอบคำสั่งซื้อผ่าน API แทน','N/A','It-shop/src/app/app.routes.ts'),
    ]
    # Keep every result distinct and reproducible.
    assert len({r['id'] for r in rs})==len(rs)
    for r in rs:
        if r['status']!='Fail': r['severity']=''
    (OUT/'all-results.json').write_text(json.dumps(rs,ensure_ascii=False,indent=2),encoding='utf8')
    index={r['id']:r for r in rs}
    counts=collections.Counter(r['status'] for r in rs)
    perf=index['N06']['actual']
    def cell(value):
        if not isinstance(value,str):value=json.dumps(value,ensure_ascii=False,separators=(',',':'))
        return value.replace('|','&#124;').replace('\n','<br>').replace('\r','')
    lines=[
        '# รายงาน QA — IT-RECOMMEND',
        '',
        'วันที่ทดสอบ: 12 กันยายน 2026 (Asia/Bangkok) · revision เริ่มต้น `343b314` พร้อม README ที่แก้ในงานก่อนหน้า',
        '',
        '**ผลประเมินรอบแก้ไข: application ผ่าน regression; เหลือ SEC01 ที่ต้องดำเนินการภายนอก repository** — ต้อง revoke/rotate Google key เดิมและประเมินล้าง public Git history ก่อนปิดงาน',
        '',
        'รายงานนี้สร้างใหม่หลังแก้ application code และรัน checklist; สถานะ Fail ที่เหลือมาจากหลักฐาน secret ใน Git history ซึ่งแก้จาก workspace อย่างเดียวไม่ได้',
        '',
        '## ขอบเขตและวิธีทดสอบ',
        '',
        '- ระบบจริงใช้ Angular 21.1 และ FastAPI; providers ปัจจุบันคือ Google/OpenAI/OpenRouter ไม่มี Zen และไม่มีหน้า cart/checkout/admin-orders ใน router ปัจจุบัน',
        '- API ใช้ FastAPI TestClient กับ SQLite ชั่วคราว สร้างจาก schema จริงและสำเนาเฉพาะ catalog สินค้า 2,294 รายการ บัญชี/ออเดอร์/ประวัติที่ทดสอบเป็น fixture ไม่เขียนข้อมูลผู้ใช้จริง บัญชี admin ตามคำขอตรวจด้วย hash/role ที่อ่านแบบ read-only และ login บน fixture',
        '- Browser ใช้ Angular development build ที่ serve บนพอร์ตชั่วคราวและ intercept API ทั้งหมด การคลิกเลือกชิ้นส่วน การนำทาง และ render เป็นหน้าเว็บจริง; provider responses และข้อมูล UI เป็น fixture จึงแยกจาก API integration tests อย่างชัดเจน',
        '- AI เรียกผ่าน mock HTTP/LLM responses ไม่ใช้ key จริง ไม่เรียกบริการเสียเงิน ผล Pass ในเคส AI ยืนยัน logic ตาม fixture เท่านั้น ยังไม่รับรองคุณภาพภาษา/benchmark/ความถูกต้องของคำตอบโมเดลจริง',
        '- Scraper ใช้ฐานข้อมูลชั่วคราวและเข้าร้านค้าจริง ตรวจลิงก์ตัวอย่าง 1 รายการต่อร้าน ไม่ได้เปิดตรวจ SKU และสต็อกของสินค้าทั้ง 2,294 รายการ; ดูข้อจำกัดของรอบ details ใน S02 และผลตัวอย่าง S09',
        '- ทดสอบ desktop 1440×1000, mobile 390×844, tablet 768×1024; Chromium ทดสอบ flow พร้อมสินค้าจำลอง ส่วน Firefox/WebKit ทดสอบการแสดงหน้าและ overflow ด้วย empty fixtures ไม่ใช่อุปกรณ์มือถือจริงหรือ Safari ตัวจริง',
        '- Pass/Fail ประเมินเฉพาะ Expected ของแต่ละเคส; Blocked หมายถึงยังสรุปไม่ได้ (เช่น รอบ full details เกินเวลาที่กำหนด) ไม่ใช่หลักฐานว่าระบบเสีย; N/A หมายถึงไม่มีฟีเจอร์ UI นั้นในรุ่นปัจจุบัน',
        '- จำนวนในตารางคือ QA scenarios รวม regression suiteเป็นหนึ่ง scenario ต่อ suite; ภายใน Python regression suites เดิมมี 38 tests ผ่านทั้งหมด และ Angular ผ่าน 14/14 tests',
        '',
        '## สรุป 9 ระบบ',
        '',
        '| # | ระบบ | จำนวนเคส | Pass | Fail | Blocked | N/A | Critical (บั๊กไม่ซ้ำ) |',
        '| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |',
    ]
    for g,name in NAMES.items():
        sub=[r for r in rs if r['group']==g]; c=collections.Counter(r['status'] for r in sub)
        critical='0'
        lines.append(f'| {g} | {name} | {len(sub)} | {c["Pass"]} | {c["Fail"]} | {c["Blocked"]} | {c["N/A"]} | {critical} |')
    lines += [f'| | **รวม** | **{len(rs)}** | **{counts["Pass"]}** | **{counts["Fail"]}** | **{counts["Blocked"]}** | **{counts["N/A"]}** | **0** |','',
        '## Top 5 บั๊กจากรายงานตั้งต้น (แก้แล้ว ยกเว้น SEC01)', '',
        '| ลำดับ | ความรุนแรง | บั๊ก / หลักฐาน | ต้นเหตุและแนวแก้ |',
        '| --- | --- | --- | --- |',
        '| 1 | Critical | **อ่าน ปลอม และลบประวัติสเปกข้ามบัญชีได้**: guest GET `?uid=alice` และ POST `uid=bob` ได้200; bob DELETE ของ alice ได้200 (H04–H07) | `backend/shop_api.py:get_spec_history/save_spec_history/delete_spec_history` ไม่มี auth/owner check และลงทะเบียนซ้ำสองชุด ต้องเหลือชุดเดียว ใช้ uid จาก JWT และตรวจเจ้าของก่อนอ่าน/ลบ |',
        '| 2 | Critical | **รายละเอียดคำสั่งซื้อเปิดสาธารณะ**: guest และ bob อ่าน order ของ alice ได้200 พร้อมชื่อ เบอร์ และที่อยู่ (O03–O04) | `get_order_detail` ไม่มี dependency ตรวจผู้ใช้ เพิ่ม JWT และอนุญาตเฉพาะเจ้าของหรือ admin |',
        '| 3 | High | **key เคยอยู่ใน Git history**: commit `46c14cea` มี `.env` พร้อม `GOOGLE_API_KEY` ที่ไม่ว่าง แม้ปัจจุบัน `.env` ไม่ tracked (SEC01) | เพิกถอน/หมุน key และประเมินล้างประวัติ/สำเนาที่เผยแพร่ การเพิ่ม `.gitignore` อย่างเดียวไม่พอ ไม่ได้ทดสอบว่า key เก่ายังใช้ได้ และรายงานไม่เปิดเผยค่า |',
        '| 4 | High | **ปลอมยอดและเจ้าของคำสั่งซื้อได้**: ราคา1บาท จำนวน0/ติดลบ ที่อยู่ว่างถูกยอมรับ; alice ส่ง uid=admin แล้วบันทึกในบัญชี admin (O05–O08, O16) | `PlaceOrderBody/OrderItemSchema/place_order` เชื่อ payload และไม่มี auth ต้อง validate quantity/customer/payment, อ่านราคาจาก DB และผูก owner จาก JWT |',
        '| 5 | High | **AI post-validation ยังปล่อยสินค้าปลอม**: endpoint เต็มคืน `QA INVENTED GPU` ราคา999,999 พร้อม `matched_real_product=false` แต่เรียกยอดว่า “ราคาจริงจากฐานข้อมูล” (I14) | `recommender.py:build_final_result` เก็บ unmatched part และใช้ราคาจาก LLM ต้อง reject/filter unmatched และตรวจงบ/ความครบก่อนตอบ |',
        '',
        '## ข้อค้นพบอื่นที่ต้องวางแผนแก้', '',
        '- **Admin Products ยังชี้ PHP เก่า**: browser ส่ง GET `/pc_part/api/get_product.php` และ POST `/pc_part/api/admin_product_manage.php` แทน FastAPI; endpoint จัดการ PHP ที่อ้างถึงไม่มีในไฟล์ที่ตรวจ (UI16) จึงยังใช้งานหน้า admin กับ stack หลักไม่ได้ ต้องเปลี่ยนไปใช้ ApiService พร้อม JWT',
        '- **ไม่มี backend validation ตอนสมัครสมาชิก**: email ผิดและรหัส1ตัวอักษรได้200 (A03–A04) ขณะที่ frontend validateForm ป้องกันได้ (UI03); หลังเปลี่ยนรหัส JWT เก่ายังใช้ได้ (A13)',
        '- **Cooler ไม่ตรวจ socket**: R4 ตรวจเพียงกำลังระบายความร้อน ทำให้ CPU AM5 + cooler ที่ระบุ LGA1700 ผ่าน R4 (C09); payload compat name เป็นตัวเลข/price เป็น object ทำให้500 (C14–C15)',
        '- **งบ500ถูกมองว่าไม่มีงบ** และใช้ default25000; ระบบยอมงบเกิน10% และ compare ส่งคำตอบ LLM โดยไม่ตรวจฐานข้อมูล (I02/I10/I13/I15) ส่วน verdict compatibility ถูก engine คุมไว้ แต่คำแนะนำเสริมจาก AI ยังขัดกับ verdict ได้ (I16)',
        '- **Quick scraper เก็บราคาต่ำสุดเก่า**: update5000→5200 อัปเดต price_advice แต่ p_price ยัง5000 (S04) ทำให้การคำนวณที่ใช้ p_price เสี่ยงแสดงราคาล้าสมัย',
        '- **Pagination ยังไม่มี**: GET products คืน catalog ทั้งหมดราว11.8MB และเพิกเฉย page/limit (P01–P04); admin table render2,700แถวและไม่มีช่องค้นหา/แบ่งหน้า (UI17)',
        '- **ถอดสิทธิ์ admin คนสุดท้ายได้** (D06); status order ที่ไม่มีใน CHECK constraint ทำให้500 แทน400/422 (O13); การข้าม pending→completed อนุญาตตาม implementation ปัจจุบัน (O14) ไม่มีการสมมติว่าเป็นบั๊กจนกว่าจะกำหนด business policy',
        '- **มือถือ overflow**: document กว้าง540px บน viewport390px ใน Chromium; screenshot แสดง navbar/search ล้นขอบ ทั้ง PC Builder และ AI; tablet768px ผ่าน (UI09/UI13 และ CB-* สำหรับอีกสอง engines)',
        '- **AI fetch ไม่มี client timeout**: จำลอง request ค้างแล้วเดิน browser clock180วินาทียัง step2/errorว่าง (UI18); mock HTTP502 หยุด loading และแสดงข้อความได้ (UI12) จึงเป็นคนละกรณีกัน',
        '- **Backend offline UX**: products/category แจ้งโหลดไม่ได้ แต่ detail แสดงเหมือนสินค้าไม่มี และ builder/history/profile/admin หลายหน้าเงียบหรือแสดง empty state ต้องแยก error จากข้อมูลว่าง (UI14-*)',
        '',
        '## ผลประสิทธิภาพและข้อจำกัด', '',
        f'ใช้ catalog สำเนา {perf["catalog_count"]:,} รายการ ยิง 3 sequential และ10 requests ที่ concurrency5 ผ่าน ASGI TestClient: sequential {perf["serial_seconds"]} วินาที; concurrent {perf["concurrent_seconds"]} วินาที; p95 แบบ nearest-rank {perf["p95_seconds"]} วินาที; response {perf["response_bytes"]:,} bytes ทุกคำขอ200 เกณฑ์ smoke ชั่วคราวคือ p95<5s ไม่ใช่ SLA ที่ผู้ใช้กำหนด และยังไม่ใช่ HTTP/network production load test',
        '',
        'รอบก่อนหน้าที่มีงานทดสอบอื่นร่วมกันวัด p95=5.668s ส่วนรอบล่าสุด=4.455s แสดงว่าตัวเลขไวต่อโหลดเครื่อง ไม่ควรอ้างว่าประสิทธิภาพผ่าน production SLA จากการรันนี้',
        '',
        'การใช้ SQLite read-only ใน WAL mode อาจเปลี่ยน reader metadata ของ `backend/shop.db-shm` ซึ่งปรากฏใน git status ระหว่างตรวจ ไม่มีการแก้แถวในฐานข้อมูลจริง และไม่ได้เขียนทับ/restore ไฟล์ shared-memory ขณะอาจมีโปรเซสอื่นใช้งาน',
        '',
        '## เคสที่ยังสรุปไม่ได้ / ไม่อยู่ในรุ่นนี้', '',
    ]
    for r in rs:
        if r['status'] in ('Blocked','N/A'):
            lines.append(f'- **{r["id"]} ({r["status"]})**: {cell(r["actual"])}')
    lines += ['','ยังไม่ได้ทดสอบ live LLM semantic quality, SKU/stock/ลิงก์ทุกชิ้น, full payment flow (ไม่มี UI), real-device browsers หรือการตัดเครือข่ายกลางทุก category ของทุกร้าน จึงไม่ให้สถานะ Pass แทนสิ่งเหล่านี้ การอ่าน history จาก client ใหม่ทดสอบ persistence ฝั่ง server แต่ไม่ได้ทดสอบสองเครื่องจริงพร้อมกัน','',
        '## รายละเอียดแต่ละเคสตามลำดับระบบ','',
        'Actual แบบละเอียดและ fixture payload ฉบับเต็มอยู่ใน [all-results.json](qa/all-results.json) สำหรับเคสที่ mock หรือทดสอบฟังก์ชันโดยตรงจะระบุไว้ใน Steps ไม่ควรตีความเป็น live end-to-end test','']
    for group,name in NAMES.items():
        lines += [f'### {group}. {name}','','| ID | Steps | Expected | Actual | สถานะ | ต้นเหตุ / ข้อเสนอแนะเมื่อ Fail |','| --- | --- | --- | --- | --- | --- |']
        for r in rs:
            if r['group']!=group:continue
            actual=cell(r['actual'])
            if len(actual)>950:actual=actual[:950]+' … (ดู JSON เต็ม)'
            cause=(r['severity']+'; '+r['source']+'; '+r['fix']) if r['status']=='Fail' else r['source']
            lines.append('| '+' | '.join(map(cell,[r['id'],r['steps'],r['expected'],actual,r['status'],cause]))+' |')
        lines.append('')
    lines += ['## วิธีรันทดสอบซ้ำ','','รันจากราก repository ด้วย Python ใน venv; browser scripts ต้องมี development build และ Playwright browsers ก่อน ทุก audit script ใช้ฐานข้อมูลชั่วคราวและ mock AI','',
        '```powershell',
        'npm --prefix It-shop run build -- --configuration development',
        '.\\venv\\Scripts\\python.exe -B docs\\qa\\run_api_audit.py',
        '.\\venv\\Scripts\\python.exe -B docs\\qa\\run_supplemental_audit.py',
        '.\\venv\\Scripts\\python.exe -B docs\\qa\\run_browser_audit.py',
        '.\\venv\\Scripts\\python.exe -B docs\\qa\\run_crossbrowser_audit.py',
        '# ต้องมี network access; scraper เขียนเฉพาะ DB ชั่วคราว',
        '.\\venv\\Scripts\\python.exe -B docs\\qa\\run_scraper_audit.py',
        '.\\venv\\Scripts\\python.exe -B docs\\qa\\run_live_listing.py',
        '.\\venv\\Scripts\\python.exe -B docs\\qa\\build_report.py',
        '```','',
        'สคริปต์ audit บันทึกสถานะ Fail ลง JSON แต่ process exit0 หมายถึง audit รันจบ ไม่ได้หมายความว่าระบบผ่านทั้งหมด `secret-metadata.json` เป็น metadata ที่เก็บในวันทดสอบนี้ ไม่มีค่า key; build_report ใช้ผล regression ที่รันในรอบนี้ หากรัน regression ใหม่ต้องอัปเดตผล REG/UNITUI ก่อนสร้างรายงานใหม่','',
        '## หลักฐานแนบ','',
        '- [ผลทั้งหมด JSON](qa/all-results.json) · [API](qa/api-results.json) · [Browser](qa/browser-results.json) · [Cross-browser](qa/crossbrowser-results.json) · [Supplemental](qa/supplemental-results.json) · [Scraper](qa/scraper-results.json)',
        '- [PC Builder มือถือ](qa/builder-390.png) · [PC Builder แท็บเล็ต](qa/builder-768.png) · [AI Settings มือถือ](qa/ai-settings-390.png) · [AI Settings แท็บเล็ต](qa/ai-settings-768.png)',
        '- [Listing log](qa/S01-live.txt) · [Details log](qa/S02-live.txt) · [ตัวอย่างรายละเอียด](qa/sample-details.txt)',
        '- [Coverage checklist จากคำขอ](qa/coverage.md)',
    ]
    for name in ('S01-live','S02-live','sample-details'):
        log=OUT/(name+'.log')
        if log.exists():(OUT/(name+'.txt')).write_text(log.read_text(encoding='utf8'),encoding='utf8')
    (ROOT/'docs/QA_REPORT_2026-09-12.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    print(json.dumps({'scenarios':len(rs),'counts':counts},ensure_ascii=False))

if __name__=='__main__':main()
