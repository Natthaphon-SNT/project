"""Headless browser QA against the built Angular app; API is locally mocked."""
import functools
import http.server
import json
from pathlib import Path
import sys
import threading
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'backend'))
import compat_engine as ce
from run_api_audit import record, RESULTS

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if not Path(self.path.split('?')[0]).suffix:
            self.path='/index.html'
        super().do_GET()
    def log_message(self,*args): pass


def main():
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(ROOT/'It-shop/dist/lt-shop/browser')))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base='http://127.0.0.1:'+str(server.server_port)
    facts=[('CPU','Intel Core i5 LGA1700',{'socket':'LGA1700','tdp':65}),('Mainboard','ASUS B760 ATX DDR5',{'socket':'LGA1700','ram_support':['DDR5'],'form_factor':'ATX'}),('GPU','RTX 5050 8GB',{'tdp':130,'recommended_psu_watt':550}),('RAM','DDR5 32GB',{'ddr_gen':'DDR5'}),('SSD','NVMe 1TB',{}),('PSU','PSU 750W',{'watt':750}),('Case','Case ATX',{'supports_ff':['ATX']}),('Liquid Cooler','CPU Cooler 150W',{'is_cpu_cooler':True,'rating_watt':150})]
    products=[dict(product_id='qa-'+str(i),p_name=name,category=cat,p_price=(i+1)*100,price_advice=(i+1)*100,price_jib=(i+1)*100+10,price_ihavecpu=(i+1)*100+20,url_advice='https://www.advice.co.th/product/qa-'+str(i),url_jib='https://www.jib.co.th/web/product/readProduct/'+str(i),url_ihavecpu='https://ihavecpu.com/product/'+str(i),img_url='data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==',p_description='QA fixture',specs='',compatibility=f) for i,(cat,name,f) in enumerate(facts)]
    alternate=dict(products[0],product_id='qa-alt',p_name='AMD Ryzen AM5',compatibility={'socket':'AM5','tdp':65})
    all_products=products+[alternate]
    requests=[]; histories=[]; state={'offline':False,'admin':False,'stall':False,'ai_ok':False}; errors=[]; pending=[]
    def api(route):
        req=route.request
        path=urlparse(req.url).path.removeprefix('/api/')
        requests.append((req.method,path))
        if state['offline']:
            route.abort('connectionrefused'); return
        data=[]; status=200
        if path=='profile': data={'uid':'alice','u_name':'QA Alice','u_email':'alice@example.com','u_role':'admin' if state['admin'] else 'customer'}
        elif path=='products':
            category=parse_qs(urlparse(req.url).query).get('category',[''])[0].lower()
            data=[p for p in all_products if not category or p['category'].lower()==category]
        elif path.startswith('products/'):
            data=next((p for p in all_products if p['product_id']==path.split('/')[1]),None)
            if data is None: status=404
        elif path.startswith('price-history/'):
            data={'history':{},'current_prices':[],'last_updated':'','trend':None}
        elif path=='compatibility/check-parts':
            selected=[]
            for item in req.post_data_json['parts']:
                p=next(p for p in all_products if p['product_id']==item['product_id'])
                selected.append({'category':'Cooler' if 'Cooler' in p['category'] else p['category'],**p['compatibility']})
            data=ce.check_build(selected)
        elif path=='spec-history':
            if req.method=='POST':
                histories.append({'id':len(histories)+1,'createdAt':'2026-09-12',**req.post_data_json})
                data=histories[-1]
            else: data=histories
        elif path=='ai/settings': data={'provider':'google','model':'gemini-2.0-flash','api_key':'qa-mock','custom_model':''}
        elif path=='ai/recommend':
            if state['stall']:
                pending.append(route); return
            if state['ai_ok']:
                result={'summary':'QA successful AI build','totalBudget':'100 THB','parts':[{'type':'CPU','name':'QA CPU','price':'100 THB','real_price':100,'shop_prices':{'advice':100,'jib':110,'ihavecpu':120},'shop_urls':{},'matched_real_product':True}],'performance':{},'pros':[],'cons':[]}
                route.fulfill(status=200,content_type='application/json',body=json.dumps({'status':'success','data':json.dumps(result),'session_id':1}));return
            route.fulfill(status=502,content_type='application/json',body=json.dumps({'detail':'AI provider request failed. Check model and quota.'})); return
        route.fulfill(status=status,content_type='application/json',body=json.dumps({'status':'success' if status==200 else 'error','data':data,'detail':'ไม่พบสินค้า' if status==404 else ''},ensure_ascii=False))
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True)
            context=browser.new_context(viewport={'width':1440,'height':1000})
            page=context.new_page(); page.set_default_timeout(10000)
            page.on('dialog',lambda d:d.accept())
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.route('**/api/**',api)
            def goto(path):
                page.goto(base+path); page.wait_for_timeout(350)
            def login(role='customer'):
                state['admin']=role=='admin'
                page.evaluate('(role)=>{localStorage.setItem("lt_token","qa-mock-token");localStorage.setItem("lt_user",JSON.stringify({id:"alice",uid:"alice",name:"QA Alice",role,u_role:role}));}',role)
            goto('/admin/products')
            record('UI01',1,'Guest เปิด /admin/products โดยตรง','redirect login',page.url,page.url.startswith(base+'/login'),'It-shop/src/app/guards/admin.guard.ts')
            login(); goto('/admin/users')
            record('UI02',1,'customer เปิด /admin/users โดยตรง','redirect หน้าแรก',page.url,page.url.rstrip('/')==base,'It-shop/src/app/guards/admin.guard.ts')
            goto('/register')
            validation=page.evaluate('''()=>{const c=ng.getComponent(document.querySelector('app-register'));c.user={name:'Alice',email:'invalid',phone:'0800000000',dob:'2000-01-01',password:'x',confirmPassword:'x'}; const valid=c.validateForm();return {valid,errors:c.fieldErrors};}''')
            record('UI03',1,'เรียก validateForm ใน component จริง: email invalid,password x','block ทั้งสอง field',validation,not validation['valid'] and 'email' in validation['errors'] and 'password' in validation['errors'],'It-shop/src/app/pages/register/register.ts:validateForm')
            goto('/product/qa-missing')
            text=page.locator('app-product-detail').inner_text()
            record('UI04',2,'เปิด product ที่ mock API คืน 404','แสดงไม่พบสินค้า ไม่หน้าขาว',text,'ไม่พบสินค้านี้' in text,'It-shop/src/app/pages/product-detail/product-detail.html')
            goto('/product/qa-0')
            text=page.locator('app-product-detail').inner_text()
            record('UI05',2,'เปิด product fixture ราคา 100/110/120','ราคา 3 ร้านแสดงตรง fixture และมี href',{'prices_present':[str(n) in text for n in (100,110,120)],'hrefs':page.locator('app-product-detail a[href^="https://"]').evaluate_all('(els)=>els.map(e=>e.href)')},all(str(n) in text for n in (100,110,120)),'It-shop/src/app/pages/product-detail/product-detail.html')
            goto('/history')
            text=page.locator('app-history').inner_text()
            record('UI06',5,'เปิด history เมื่อ API คืน []','แสดง empty state',text[:500],('ยังไม่มี' in text or 'ไม่พบ' in text) and len(text)>30,'It-shop/src/app/pages/history/history.html')
            goto('/pc-builder')
            for i in range(8):
                page.locator('.slot-card').nth(i).locator('.slot-empty').click()
                page.locator('.picker-item').first.click()
            page.wait_for_timeout(300)
            calc=page.evaluate('''()=>{const c=ng.getComponent(document.querySelector('app-pc-builder')); return {selected:c.getSelectedCount(),mixed:c.getTotalPrice(),advice:c.getStoreTotal('advice'),jib:c.getStoreTotal('jib'),ihavecpu:c.getStoreTotal('ihavecpu'),best:c.getBestStoreInfo(),compat:c.compatResult};}''')
            record('UI07',2,'คลิกเลือก 8 ชิ้น fixture ราคา Advice 100..800; JIB +10; IHC +20','Mixed=3600; Advice=3600,JIB=3680,IHC=3760; Best=Advice',calc,calc['mixed']==3600 and calc['advice']==3600 and calc['jib']==3680 and calc['ihavecpu']==3760 and calc['best']['bestStore']=='Advice','It-shop/src/app/pages/pc-builder/pc-builder.ts:getBestStoreInfo/getTotalPrice')
            before=len([r for r in requests if r[1]=='compatibility/check-parts'])
            page.locator('.slot-card').first.locator('.btn-change').click()
            page.locator('.picker-item').filter(has_text='AMD Ryzen AM5').click()
            page.wait_for_timeout(300)
            text=page.locator('.compat-banner').inner_text()
            after=len([r for r in requests if r[1]=='compatibility/check-parts'])
            record('UI08',3,'เลือกครบ 8 ชิ้นแล้วคลิกสลับ CPU เป็น AM5','ส่ง compat request อัตโนมัติและขึ้น socket error',{'requests_before':before,'requests_after':after,'banner':text},after>before and page.locator('.compat-error').count()>0,'It-shop/src/app/pages/pc-builder/pc-builder.ts:selectProduct/checkCompatibility')
            for width,height in [(390,844),(768,1024)]:
                page.set_viewport_size({'width':width,'height':height})
                page.wait_for_timeout(200)
                dims=page.evaluate('({width:innerWidth,document:document.documentElement.scrollWidth,body:document.body.scrollWidth})')
                filename=f'builder-{width}.png'; page.screenshot(path=str(OUT/filename),full_page=True)
                record('UI09-'+str(width),9,'PC Builder 8 ชิ้น+socket warning; Chromium viewport '+str(width),'ไม่มี horizontal overflow ของหน้า; screenshot แนบ',dict(dims,screenshot=filename),dims['document']<=width+1 and dims['body']<=width+1,'It-shop/src/app/components/navbar/navbar.scss:.nav-container/.nav-search','ปรับ navbar/search ให้ wrap หรือย่อได้บนมือถือ')
            page.set_viewport_size({'width':1440,'height':1000})
            page.locator('.slot-card').nth(7).locator('.btn-remove').click(); page.wait_for_timeout(200)
            count=page.evaluate("ng.getComponent(document.querySelector('app-pc-builder')).getSelectedCount()")
            record('UI10',3,'ลบ Cooler หลังเลือกครบ','แสดง 7/8 และไม่ crash; Cooler optional ตาม slots',{'selected':count,'counter_visible':'7' in page.locator('.summary-card').inner_text()},count==7 and page.locator('.summary-card').is_visible(),'It-shop/src/app/pages/pc-builder/pc-builder.ts:slots/removeProduct')
            page.evaluate("ng.getComponent(document.querySelector('app-pc-builder')).saveAndNavigateToHistory()")
            page.wait_for_url('**/history'); page.wait_for_timeout(250)
            record('UI11',5,'บันทึก PC Builder ผ่าน component จริง; mock persist แล้วเปิด history','เห็น manual history และราคาตาม snapshot',{'history_rows':len(histories),'page':page.locator('app-history').inner_text()[:600]},len(histories)==1 and 'จัดสเปกเอง' in page.locator('app-history').inner_text(),'It-shop/src/app/pages/pc-builder/pc-builder.ts:saveAndNavigateToHistory')
            goto('/ai-recommend');state['ai_ok']=True
            page.evaluate("()=>{const c=ng.getComponent(document.querySelector('app-ai-recommend'));c.mode='recommend';c.runPrompt('QA budget 25000');}")
            page.wait_for_function("ng.getComponent(document.querySelector('app-ai-recommend')).step===3");page.wait_for_timeout(200)
            goto('/history')
            types=[h['type'] for h in histories]
            record('UI20',5,'Mock AI success ผ่านหน้า AI จริง แล้วเปิด history ที่มี manual เดิม','ทั้ง manual และ ai ถูกบันทึกและแสดงร่วมกัน',{'types':types,'text':page.locator('app-history').inner_text()[:700]},set(types)=={'manual','ai'},'It-shop/src/app/pages/ai-recommend/ai-recommend.ts:saveHistory','ตรวจ payload ของ AI history และ schema ให้ตรงกับ backend')
            state['ai_ok']=False
            goto('/ai-recommend')
            page.evaluate("()=>{const c=ng.getComponent(document.querySelector('app-ai-recommend')); c.mode='compat'; c.compatText='CPU: AMD Ryzen 5 7500F'; c.handleCompat();}")
            page.wait_for_function("ng.getComponent(document.querySelector('app-ai-recommend')).step===3")
            error=page.evaluate("()=>{const c=ng.getComponent(document.querySelector('app-ai-recommend'));return {step:c.step,type:c.resultType,error:c.errorMessage};}")
            record('UI12',4,'ส่ง AI แล้ว mock HTTP 502','หยุด loading และแสดง error',error,error['step']==3 and error['type']=='error' and bool(error['error']),'It-shop/src/app/pages/ai-recommend/ai-recommend.ts:runPrompt')
            for width,height in [(390,844),(768,1024)]:
                page.set_viewport_size({'width':width,'height':height}); goto('/ai-recommend')
                page.get_by_role('button',name='Settings',exact=True).click()
                dims=page.evaluate('({width:innerWidth,document:document.documentElement.scrollWidth,body:document.body.scrollWidth})')
                filename=f'ai-settings-{width}.png'; page.screenshot(path=str(OUT/filename),full_page=True)
                record('UI13-'+str(width),9,'AI Settings; Chromium viewport '+str(width),'ไม่มี horizontal overflow; screenshot แนบ',dict(dims,screenshot=filename),dims['document']<=width+1 and dims['body']<=width+1,'It-shop/src/app/components/navbar/navbar.scss:.nav-container/.nav-search','ปรับ navbar/search ให้ wrap หรือย่อได้บนมือถือ')
            page.set_viewport_size({'width':1440,'height':1000})
            state['offline']=True
            for n,path in enumerate(['/','/products','/category/CPU','/product/qa-0','/pc-builder','/history','/profile','/ai-recommend','/admin/products','/admin/users','/login','/register']):
                login('admin'); goto(path)
                text=page.locator('app-root').inner_text()
                relevant=[word for word in ['ไม่สามารถ','เชื่อมต่อ','ผิดพลาด','error','failed','unable','หมดอายุ','ปิดอยู่'] if word in text.lower()]
                component_state = page.evaluate("()=>{const el=document.querySelector('app-admin-products');return el?{loadError:ng.getComponent(el).loadError}:null}") if path=='/admin/products' else None
                public_form=path in ('/','/login','/register')
                record('UI14-'+str(n+1),9,'จำลอง API connection refused แล้วเปิด '+path,'หน้าที่โหลด API แสดง error ที่เข้าใจได้; login/register ยังแสดง form',{'url':page.url,'text_excerpt':text[-650:],'error_terms':relevant,'component_state':component_state,'recent_requests':requests[-8:]},len(text)>30 and (bool(relevant) or public_form),'It-shop/src/app/pages/'+path.strip('/'),'เพิ่ม error state แยกจาก empty/not-found และปุ่มลองใหม่')
            state['offline']=False
            login('admin'); requests.clear(); goto('/admin/products')
            page.evaluate("()=>{const c=ng.getComponent(document.querySelector('app-admin-products')); c.formProduct={name:'QA Browser Product',price:1234,category:'c01',description:'fixture',image:''}; c.submitForm();}")
            page.wait_for_timeout(250)
            record('UI16',7,'เปิด admin products และ submit สินค้า fixture; บันทึก request destinations','ใช้ GET/POST /api/products ของ FastAPI พร้อม JWT',{'requests':list(requests)},any(method=='POST' and path=='products' for method,path in requests),'It-shop/src/app/pages/admin-products/admin-products.ts:api/loadProducts/submitForm','เปลี่ยน PHP URL เดิมเป็น ApiService และแนบ JWT','High')
            table=page.evaluate("()=>{const c=ng.getComponent(document.querySelector('app-admin-products')); c.products=Array.from({length:2700},(_,i)=>({product_id:'q'+i,p_name:'QA item '+i,p_price:100,cid:'c01'})); ng.applyChanges(c); return {rows:document.querySelectorAll('app-admin-products tbody tr').length,inputs:[...document.querySelectorAll('app-admin-products input')].map(e=>e.placeholder)};}")
            record('UI17',7,'ใส่2700 fixture rows ใน component จริงแล้ว render','มี search/pagination จำกัดจำนวนแถวบนหน้า',table,table['rows']<2700,'It-shop/src/app/pages/admin-products/admin-products.ts/html','เพิ่ม search/pagination และรับข้อมูลแบบแบ่งหน้าจาก API')
            goto('/ai-recommend'); page.clock.install(); state['stall']=True
            page.evaluate("()=>{const c=ng.getComponent(document.querySelector('app-ai-recommend')); c.mode='compat';c.compatText='CPU AM5';c.handleCompat();}")
            page.wait_for_function("ng.getComponent(document.querySelector('app-ai-recommend')).step===2")
            page.wait_for_timeout(150)
            page.clock.fast_forward(180000)
            stalled=page.evaluate("()=>{const c=ng.getComponent(document.querySelector('app-ai-recommend'));return {step:c.step,error:c.errorMessage};}")
            record('UI18',9,'ปล่อย AI fetch ค้าง แล้วเดิน browser clock 180วินาที','frontend timeout/cancel พร้อม error',stalled,stalled['step']!=2,'It-shop/src/app/pages/ai-recommend/ai-recommend.ts:callGemini','เพิ่ม AbortController deadline และปุ่มยกเลิก; timeout ของ backend ไม่แทน client timeout','High')
            state['stall']=False
            for route in pending: route.fulfill(status=502,content_type='application/json',body='{"detail":"QA released stalled request"}')
            page.wait_for_timeout(100)
            for name in ('firefox','webkit'):
                try:
                    other=getattr(pw,name).launch(headless=True)
                    op=other.new_page(viewport={'width':390,'height':844});op.route('**/api/**',api);op.goto(base+'/ai-recommend');op.wait_for_timeout(250)
                    visible=op.locator('app-ai-recommend').is_visible();other.close()
                    record('UI19-'+name,9,'เปิด AI guest บน '+name,'หน้าแสดงได้',{'visible':visible},visible,'It-shop/src/app/pages/ai-recommend')
                except Exception as exc:
                    record('UI19-'+name,9,'launch '+name,'มี browser runtime สำหรับ cross-browser smoke',str(exc).splitlines()[0],False)
                    RESULTS[-1]['status']='Blocked';RESULTS[-1]['severity']=''
            record('UI15',9,'รวบรวม pageerror ระหว่าง browser scenarios','ไม่มี uncaught pageerror',errors,not errors,'It-shop/src/app','ตรวจ handler และ async errors')
            browser.close()
    finally:
        server.shutdown();server.server_close()
        (OUT/'browser-results.json').write_text(json.dumps(RESULTS,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'cases':len(RESULTS),'pass':sum(r['status']=='Pass' for r in RESULTS),'fail':sum(r['status']=='Fail' for r in RESULTS)}))

if __name__=='__main__': main()
