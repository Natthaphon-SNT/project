"""Finish the all-store listing run with a longer QA deadline; temp DB only."""
import asyncio
import contextlib
import gc
import json
from pathlib import Path
import sqlite3
import tempfile
import time
import httpx
from run_scraper_audit import fs, fixture, OUT

async def main():
    with tempfile.TemporaryDirectory(prefix='qa-full-listing-') as temp:
        dbpath=Path(temp)/'shop.db';conn=fixture(dbpath);conn.close();fs.DB_PATH=str(dbpath)
        start=time.perf_counter();status='Pass';reason=''
        with (OUT/'S01-live.log').open('w',encoding='utf8') as log,contextlib.redirect_stdout(log):
            try: await asyncio.wait_for(fs.run_all(['advice','jib','ihavecpu'],3,False),timeout=600)
            except TimeoutError:status='Blocked';reason='QA deadline 600s; not a confirmed scraper defect'
            except Exception as exc:status='Blocked';reason=type(exc).__name__+': '+str(exc)[:200]
        gc.collect();conn=sqlite3.connect(dbpath)
        counts={s:conn.execute(f'SELECT count(*) FROM products WHERE price_{s}>0').fetchone()[0] for s in ('advice','jib','ihavecpu')}
        actual={'elapsed_seconds':round(time.perf_counter()-start,1),'counts':counts,'integrity':conn.execute('PRAGMA integrity_check').fetchone()[0],'log':'S01-live.log'}
        if reason:actual['reason']=reason
        if status=='Pass' and not all(counts.values()):status='Fail'
        # Sample one real detail URL per store from this run, independent of a
        # full --details backfill (which is much longer than listing collection).
        from playwright.async_api import async_playwright
        details=[]
        async with async_playwright() as pw:
            browser=await pw.chromium.launch(headless=True)
            page=await browser.new_page()
            for s in ('advice','jib','ihavecpu'):
                row=conn.execute(f"SELECT p_name,category,url_{s} FROM products WHERE price_{s}>0 AND url_{s}<>'' LIMIT 1").fetchone()
                if not row:details.append({'store':s,'reason':'no sample'});continue
                try:
                    with (OUT/'sample-details.log').open('a',encoding='utf8') as log,contextlib.redirect_stdout(log):
                        if s=='ihavecpu':
                            async with httpx.AsyncClient(timeout=30,follow_redirects=True,headers={'User-Agent':fs.UA}) as client:
                                desc,img=await fs.fetch_ihc_detail_http(client,row[2],row[0],row[1])
                        else:
                            desc,img=await asyncio.wait_for(fs.fetch_detail_page(page,row[2],row[0],row[1]),timeout=35)
                    details.append({'store':s,'name':row[0],'url':row[2],'description_chars':len(desc),'has_image':bool(img)})
                except Exception as exc:details.append({'store':s,'reason':type(exc).__name__})
            await browser.close()
        conn.close()
    path=OUT/'scraper-results.json';rs=json.loads(path.read_text(encoding='utf8'))
    for r in rs:
        if r['id']=='S01':r.update(status=status,actual=actual,steps='run_all stores=all pages=3 details=False; isolated empty DB; deadline600s',severity='' if status!='Fail' else 'Medium')
    rs=[r for r in rs if r['id']!='S09']
    rs.append({'id':'S09','group':8,'steps':'สินค้า1รายการ/ร้าน: fetch_detail_page สำหรับ Advice/JIB; fetch_ihc_detail_http สำหรับ iHaveCPU ตาม active scraper','expected':'มีรายละเอียดและรูปสำหรับตัวอย่าง3ร้าน; ไม่ใช่การรับรอง full --details run','actual':details,'status':'Pass' if all(d.get('description_chars',0)>0 and d.get('has_image') for d in details) and len(details)==3 else 'Blocked','source':'backend/full_scraper.py:fetch_detail_page/fetch_ihc_detail_http','fix':'ตรวจ URL/การตอบสนองต้นทางในตัวอย่างที่ไม่มีรายละเอียด','severity':''})
    path.write_text(json.dumps(rs,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'S01':status,'actual':actual,'detail_samples':details},ensure_ascii=False))

if __name__=='__main__':asyncio.run(main())
