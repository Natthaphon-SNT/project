import unittest
if __name__ != "__main__":
    raise unittest.SkipTest("manual built-UI browser diagnostic")

import functools
import http.server
import json
from pathlib import Path
import threading
from playwright.sync_api import sync_playwright, expect

root = Path(__file__).resolve().parents[1] / 'It-shop/dist/lt-shop/browser'
class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.split('?')[0] in ('/ai-recommend', '/pc-builder'):
            self.path = '/index.html'
        super().do_GET()
    def log_message(self, *args): pass

server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=str(root)))
threading.Thread(target=server.serve_forever, daemon=True).start()
base = 'http://127.0.0.1:' + str(server.server_port)
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        errors=[]
        page.on('pageerror', lambda e: errors.append(str(e)))
        session={'id':1,'uid':'alice','title':'Saved conversation','mode':'recommend','provider':'google','model':'gemini-2.0-flash','messages':json.dumps([{'role':'user','content':'Budget 30000'},{'role':'assistant','content':json.dumps({'summary':'Saved answer','parts':[],'performance':{},'pros':[],'cons':[]})}]),'created_at':'2026-09-07T10:00:00','updated_at':'2026-09-07T10:00:00'}
        sessions=[session]
        saved=[]
        requests=[]
        expired=[False]
        def api(route):
            req=route.request
            path=req.url.split('/api/')[-1]
            requests.append(path)
            data=[]
            if path=='profile':
                if expired[0]:
                    route.fulfill(status=401,content_type='application/json',body='{}'); return
                data={'uid':'alice','u_name':'Alice','u_role':'customer'}
            elif path=='ai/settings':
                if req.method=='PUT': saved.append(req.post_data_json)
                data={'provider':'google','model':'gemini-2.0-flash','api_key':'alice-key','custom_model':''}
            elif path=='ai/sessions': data=sessions
            elif path=='ai/sessions/1':
                if req.method=='DELETE': sessions.clear()
                data=session
            route.fulfill(status=200,content_type='application/json',body=json.dumps({'status':'success','data':data}))
        page.route('**/api/**',api)
        page.goto(base+'/ai-recommend')
        page.get_by_role('button',name='Settings',exact=True).click()
        page.locator('.provider-tabs')
        page.get_by_role('button',name='Google',exact=True).click()
        page.locator('#provider-key').fill('guest-key')
        page.get_by_role('button',name='Openai',exact=True).click()
        expect(page.locator('#provider-key')).to_have_value('')
        page.get_by_role('button',name='Google',exact=True).click()
        expect(page.locator('#provider-key')).to_have_value('guest-key')
        page.get_by_role('button',name='Show key',exact=True).click()
        expect(page.locator('#provider-key')).to_have_attribute('type','text')
        page.get_by_role('button',name='Openrouter',exact=True).click()
        page.locator('#custom-model').fill('custom/model')
        expect(page.get_by_role('button',name='Free (Zen)',exact=True)).to_have_count(0)
        page.get_by_role('button',name='Close',exact=True).click()
        page.evaluate("localStorage.setItem('lt_token','test-token');localStorage.setItem('lt_user', JSON.stringify({uid:'alice',u_name:'Alice',u_role:'customer'}))")
        page.reload()
        page.get_by_role('button',name='Settings',exact=True).click()
        expect(page.locator('#provider-key')).to_have_value('alice-key')
        page.locator('#provider-key').fill('new-key')
        page.get_by_role('button',name='Save',exact=True).click()
        page.get_by_role('status').wait_for()
        assert saved[-1]['api_key']=='new-key'
        page.get_by_role('button',name='Close',exact=True).click()
        page.get_by_role('button',name='History',exact=True).click()
        page.get_by_role('button',name='Saved conversation',exact=False).click()
        page.get_by_text('Saved answer',exact=True).first.wait_for()
        page.get_by_role('button',name='+ New chat',exact=True).click()
        expect(page.locator('.chat-transcript')).to_have_count(0)
        page.get_by_role('button',name='History',exact=True).click()
        page.on('dialog',lambda dialog:dialog.accept())
        page.locator('.session-row').get_by_role('button',name='Delete',exact=True).click()
        page.get_by_text('No conversations yet.',exact=True).wait_for()
        expired[0]=True
        requests.clear()
        page.evaluate("localStorage.setItem('lt_user',JSON.stringify({uid:'alice',u_role:'admin'}))")
        page.reload()
        page.get_by_role('link',name='\u0e40\u0e02\u0e49\u0e32\u0e2a\u0e39\u0e48\u0e23\u0e30\u0e1a\u0e1a\u0e43\u0e2b\u0e21\u0e48',exact=True).wait_for()
        assert 'ai/spec-history/all' not in requests
        assert 'spec-history/all' not in requests
        assert 'ai/settings' not in requests
        assert not errors, errors
        browser.close()
        print('PASS: guest access, three provider tabs, key isolation/toggle, save, history load, new chat, delete, expired login')
finally:
    server.shutdown()
    server.server_close()
