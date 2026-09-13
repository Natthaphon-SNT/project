"""Scraper QA on temporary SQLite; optional bounded real network probes."""
import asyncio
import contextlib
import gc
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
from unittest.mock import AsyncMock, patch

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'backend'))
import full_scraper as fs
import scraper as quick
import httpx
from run_api_audit import record,RESULTS

def fixture(path):
    source=sqlite3.connect((ROOT/'backend/shop.db').as_uri()+'?mode=ro',uri=True)
    ddl=source.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name IN ('products','price_history','categories')").fetchall()
    source.close()
    conn=sqlite3.connect(path)
    for (sql,) in ddl: conn.execute(sql)
    fs.setup_db(conn)
    return conn

async def live(root):
    # Same run_all path as CLI. Bound each full run, cancel inside asyncio so
    # Playwright context managers close their own child browsers.
    for id,pages,details in [('S01',3,False),('S02',2,True)]:
        dbpath=root/(id+'.db');conn=fixture(dbpath);conn.close();fs.DB_PATH=str(dbpath)
        logpath=OUT/(id+'-live.log')
        start=time.perf_counter(); state='Pass';actual={}
        with logpath.open('w',encoding='utf8') as log,contextlib.redirect_stdout(log):
            try:
                await asyncio.wait_for(fs.run_all(['advice','jib','ihavecpu'],pages,details),timeout=120)
            except TimeoutError:
                state='Blocked';actual['reason']='QA wall-clock deadline 120s; full three-store run incomplete'
            except Exception as exc:
                state='Blocked';actual['reason']=type(exc).__name__+': '+str(exc)[:200]
        gc.collect()
        conn=sqlite3.connect(dbpath)
        actual.update(elapsed_seconds=round(time.perf_counter()-start,1),counts={s:conn.execute(f'SELECT count(*) FROM products WHERE price_{s}>0').fetchone()[0] for s in ('advice','jib','ihavecpu')},details=conn.execute("SELECT count(*) FROM products WHERE coalesce(desc_advice,'')<>'' OR coalesce(desc_jib,'')<>'' OR coalesce(desc_ihavecpu,'')<>''").fetchone()[0],log=logpath.name)
        conn.close()
        if state=='Pass' and not all(actual['counts'].values()):
            network_failure=any(t in logpath.read_text(encoding='utf8') for t in ('All connection attempts failed','ERR_NETWORK_ACCESS_DENIED','ERR_INTERNET_DISCONNECTED'))
            state='Blocked' if network_failure else 'Fail'
            if network_failure: actual['reason']='Network access unavailable; zero rows cannot establish source/parser failure'
        record(id,8,f'run_all stores=all pages={pages} details={details}; DB ว่างแยก; timeout120s','จบครบ 3 ร้าน มีสินค้า; details run ต้องมีรายละเอียด',actual,state=='Pass','backend/full_scraper.py:run_all','ตรวจ log และทดสอบซ้ำโดยให้เวลาครบทุกหมวด')
        RESULTS[-1]['status']=state
        (OUT/'scraper-results.json').write_text(json.dumps(RESULTS,ensure_ascii=False,indent=2),encoding='utf8')

async def main():
    with tempfile.TemporaryDirectory(prefix='it-recommend-scraper-qa-') as temp:
        root=Path(temp)
        conn=fixture(root/'quick.db')
        p={'store':'advice','name':'CPU AMD RYZEN 5 7500F','category':'CPU','price':5000,'url':'https://www.advice.co.th/product/qa-cpu'}
        quick.CLEANED_CACHE.clear()
        for price in (5000,5100,5200): quick.upsert_product(conn.cursor(),dict(p,price=price))
        rows=conn.execute('SELECT p_price,price_advice FROM products').fetchall()
        record('S03',8,'เรียก quick upsert 3 รอบ สินค้าเดิม ราคา5000→5100→5200','หนึ่งแถว; ราคาของร้าน=5200',rows,len(rows)==1 and rows[0][1]==5200,'backend/scraper.py:upsert_product')
        record('S04',8,'ตรวจ p_price หลัง quick update ราคาเพิ่ม','p_price ตรงราคาต่ำสุดที่ยังมีอยู่จริง',rows,rows[0][0]==rows[0][1],'backend/scraper.py:upsert_product','คำนวณ p_price ใหม่จากราคาทุกร้านหลัง UPDATE; ปัจจุบันแก้เฉพาะเมื่อ p_price=0','High')
        conn.close()
        for id,a,b,expected in [('S05','MONITOR AOC 22B40HM 21.45 120Hz','Monitor AOC 22B40HM/67 21.45 Inch FHD 120Hz',True),('S06','VGA ASUS DUAL GEFORCE RTX 4070 12GB','VGA ASUS DUAL GEFORCE RTX 4070 TI 12GB',False)]:
            cat='Monitor' if id=='S05' else 'GPU'; got=fs.is_same_product(a,cat,b,cat)
            record(id,8,'is_same_product: '+a+' vs '+b,str(expected),got,got==expected,'backend/full_scraper.py:is_same_product')
        # Simulate the real source HTTP call failing, restricted to one category.
        conn=fixture(root/'offline.db'); matcher=fs.SmartMatcher(conn.cursor())
        fake=AsyncMock();fake.get.side_effect=httpx.ConnectError('QA simulated network outage')
        fake.__aenter__.return_value=fake
        logs=io.StringIO()
        with patch.object(fs,'IHC_CATS',fs.IHC_CATS[:1]),patch.object(fs.httpx,'AsyncClient',return_value=fake),contextlib.redirect_stdout(logs):
            result=await fs.scrape_ihavecpu(conn,matcher,1,False)
        integrity=conn.execute('PRAGMA integrity_check').fetchone()[0]
        record('S07',8,'จำลอง ConnectError ใน HTTP iHaveCPU CPU category','ไม่ crash; log error และ SQLite integrity ok',{'result':result,'integrity':integrity,'log':logs.getvalue()[:500]},integrity=='ok' and bool(logs.getvalue()),'backend/full_scraper.py:scrape_ihavecpu')
        # Changed HTML: successful HTTP with neither products nor Next.js payload.
        fake=AsyncMock(); fake.get.return_value=httpx.Response(200,text='<html><main>New layout without product data</main></html>',request=httpx.Request('GET','https://ihavecpu.com/category/processor'))
        fake.__aenter__.return_value=fake;logs=io.StringIO()
        with patch.object(fs,'IHC_CATS',fs.IHC_CATS[:1]),patch.object(fs.httpx,'AsyncClient',return_value=fake),contextlib.redirect_stdout(logs):
            result=await fs.scrape_ihavecpu(conn,matcher,1,False)
        logtext=logs.getvalue()
        record('S08',8,'จำลอง HTTP200 แต่ HTML เปลี่ยนและไม่มี payload','ไม่เพิ่มสินค้าผิด; log อธิบายว่า payload/selector ขาด',{'result':result,'log':logtext[:700]},result==(0,0) and any(w in logtext.lower() for w in ('missing','payload','not found','no next','no product','no structured products','no items','ไม่มี')),'backend/full_scraper.py:scrape_ihavecpu','แยก parser failure ออกจากสินค้าหมด/หน้าว่าง; ส่งสัญญาณให้ผู้ดูแล')
        conn.close()
        source=sqlite3.connect((ROOT/'backend/shop.db').as_uri()+'?mode=ro',uri=True)
        samples=[]
        for store,domain in [('advice','advice.co.th'),('jib','jib.co.th'),('ihavecpu','ihavecpu.com')]:
            row=source.execute(f"SELECT p_name,url_{store} FROM products WHERE price_{store}>0 AND url_{store} LIKE ? ORDER BY product_id LIMIT 1",('%'+domain+'%',)).fetchone()
            if row: samples.append((store,row[0],row[1]))
        source.close()
        async with httpx.AsyncClient(timeout=25,follow_redirects=True,headers={'User-Agent':fs.UA}) as client:
            for store,name,url in samples:
                try:
                    response=await client.get(url)
                    actual={'store':store,'product':name,'url':url,'status':response.status_code,'final_url':str(response.url),'bytes':len(response.content)}
                    passed=response.status_code==200 and len(response.content)>1000
                    record('L-'+store,2,'GET direct URL ของสินค้า DB 1 รายการ/ร้าน','HTTP200 หน้าสินค้า; ทดสอบ reachability เท่านั้น ยังไม่ยืนยัน SKU ด้วยสายตา',actual,passed,'backend/full_scraper.py/source URLs','ตรวจหน้าเว็บต้นทางและ URL ที่บันทึก')
                    if response.status_code in (403,429,503): RESULTS[-1]['status']='Blocked'
                except Exception as exc:
                    record('L-'+store,2,'GET direct URL ของสินค้า DB 1 รายการ/ร้าน','เปิดหน้าสินค้าได้',{'store':store,'error':type(exc).__name__+': '+str(exc)[:150]},False)
                    RESULTS[-1]['status']='Blocked'
        await live(root)
    (OUT/'scraper-results.json').write_text(json.dumps(RESULTS,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'cases':len(RESULTS),'statuses':{s:sum(r['status']==s for r in RESULTS) for s in ('Pass','Fail','Blocked')}}))

if __name__=='__main__': asyncio.run(main())
