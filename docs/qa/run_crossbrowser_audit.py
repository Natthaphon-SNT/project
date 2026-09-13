"""Firefox/WebKit rendering and responsive probes after runtime installation."""
import functools
import http.server
import json
from pathlib import Path
import threading
from playwright.sync_api import sync_playwright
from run_browser_audit import Handler,ROOT,OUT
from run_api_audit import record,RESULTS

def main():
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(ROOT/'It-shop/dist/lt-shop/browser')))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base='http://127.0.0.1:'+str(server.server_port)
    def api(route):
        path=route.request.url.split('/api/')[-1];data=[]
        if path=='profile':data={'uid':'alice','u_name':'QA Alice','u_role':'customer'}
        elif path=='ai/settings':data={'provider':'google','model':'gemini-2.0-flash','api_key':'qa-mock','custom_model':''}
        route.fulfill(status=200,content_type='application/json',body=json.dumps({'status':'success','data':data}))
    original=json.loads((OUT/'browser-results.json').read_text(encoding='utf8'))
    try:
        with sync_playwright() as pw:
            for name in ('firefox','webkit'):
                errors=[];views=[]
                print('Starting '+name,flush=True)
                try:
                    browser=getattr(pw,name).launch(headless=True,timeout=20000)
                except Exception as exc:
                    for r in original:
                        if r['id']=='UI19-'+name:r.update(status='Blocked',actual=str(exc).splitlines()[0],severity='')
                    continue
                context=browser.new_context()
                context.route('**/*',lambda route:route.continue_() if route.request.url.startswith(base) else route.abort())
                context.route('**/api/**',api)
                context.add_init_script("localStorage.setItem('lt_token','qa-mock');localStorage.setItem('lt_user',JSON.stringify({uid:'alice',id:'alice',role:'customer'}));")
                page=context.new_page();page.set_default_timeout(10000);page.on('pageerror',lambda e:errors.append(str(e)))
                for path in ('pc-builder','ai-recommend'):
                    for width,height in ((390,844),(768,1024)):
                        page.set_viewport_size({'width':width,'height':height});page.goto(base+'/'+path,wait_until='domcontentloaded')
                        page.locator('app-'+path).wait_for();page.wait_for_timeout(300)
                        dims=page.evaluate('({width:innerWidth,document:document.documentElement.scrollWidth,body:document.body.scrollWidth})')
                        views.append({'path':path,'width':width,'visible':page.locator('app-'+path).is_visible()})
                        record(f'CB-{name}-{path}-{width}',9,f'{name}: {path} viewport {width}; fixture empty catalog','page ไม่ล้นแนวนอน',dims,dims['document']<=width+1 and dims['body']<=width+1,'It-shop/src/app/components/navbar/navbar.scss:.nav-container/.nav-search','ปรับ navbar สำหรับมือถือ')
                browser.close()
                for r in original:
                    if r['id']=='UI19-'+name:
                        r.update(status='Pass' if all(v['visible'] for v in views) and not errors else 'Fail',actual={'views':views,'pageerrors':errors},steps='เปิด PC Builder และ AI บน '+name+' ที่390/768px พร้อม mock API',expected='components แสดงได้ ไม่มี uncaught error',severity='')
    finally:
        server.shutdown();server.server_close()
        (OUT/'browser-results.json').write_text(json.dumps(original,ensure_ascii=False,indent=2),encoding='utf8')
        (OUT/'crossbrowser-results.json').write_text(json.dumps(RESULTS,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'cases':len(RESULTS),'pass':sum(r['status']=='Pass' for r in RESULTS),'fail':sum(r['status']=='Fail' for r in RESULTS)}))

if __name__=='__main__':main()
