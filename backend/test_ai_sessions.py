
import asyncio
import contextlib
import importlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

class AiSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = os.getcwd()
        cls.temp = tempfile.TemporaryDirectory()
        os.chdir(cls.temp.name)
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        os.environ.setdefault(
            "JWT_SECRET", "qa-ai-sessions-secret-012345678901234567890123"
        )
        with contextlib.redirect_stdout(io.StringIO()):
            cls.api = importlib.import_module('shop_api')
        cls.api.Base.metadata.create_all(cls.api.engine)
        cls.rec = importlib.import_module('recommender')
        cls.client = TestClient(cls.api.app)
        with cls.api.SessionLocal() as db:
            db.add_all([cls.api.User(uid=u, u_name=u, u_email=u+'@example.com', u_password='unused') for u in ('alice','bob')])
            db.commit()

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        cls.api.engine.dispose()
        os.chdir(cls.original)
        cls.temp.cleanup()

    def auth(self, user='alice'):
        return {'Authorization': 'Bearer '+self.api.create_token({'uid': user})}

    def test_settings_isolation_and_validation(self):
        c=self.client
        self.assertEqual(c.get('/api/ai/settings').status_code,401)
        for u,p in [('alice','google'),('bob','openai')]:
            r=c.put('/api/ai/settings', headers=self.auth(u), json={'provider':p,'model':'test-model','api_key':u+'-key'})
            self.assertEqual(r.status_code,200)
        for u in ('alice','bob'):
            self.assertEqual(c.get('/api/ai/settings', headers=self.auth(u)).json()['data']['api_key'],u+'-key')
        self.assertEqual(c.put('/api/ai/settings',headers=self.auth(),json={'provider':'invalid'}).status_code,422)

    def test_session_crud_and_ownership(self):
        c=self.client; h=self.auth()
        item=c.post('/api/ai/sessions',headers=h,json={'title':'Test'}).json()['data']
        url='/api/ai/sessions/'+str(item['id'])
        for method,body in [('get',None),('put',{'title':'hacked'}),('delete',None)]:
            kwargs={'headers':self.auth('bob')}
            if body: kwargs['json']=body
            self.assertEqual(getattr(c,method)(url,**kwargs).status_code,404)
        ids=[x['id'] for x in c.get('/api/ai/sessions',headers=self.auth('bob')).json()['data']]
        self.assertNotIn(item['id'],ids)
        self.assertEqual(c.put(url,headers=h,json={'messages':'{}'}).status_code,422)
        messages=json.dumps([{'role':'user','content':'hello'}])
        self.assertEqual(c.put(url,headers=h,json={'messages':messages,'title':'Renamed'}).status_code,200)
        self.assertEqual(c.get(url,headers=h).json()['data']['title'],'Renamed')
        self.assertEqual(c.delete(url,headers=h).status_code,200)
        self.assertEqual(c.get(url,headers=h).status_code,404)

    def test_recommend_resolution_append_guest_and_failure(self):
        c=self.client;h=self.auth()
        c.put('/api/ai/settings',headers=h,json={'provider':'google','model':'saved','custom_model':'custom','api_key':'alice-key'})
        with patch.object(self.rec,'recommend_with_alternatives',new_callable=AsyncMock,return_value={'summary':'ok','parts':[]}) as call:
            first=c.post('/api/ai/recommend',headers=h,json={'prompt':'Budget 30000'}).json()
            self.assertEqual(first['status'],'success')
            self.assertEqual(call.call_args.kwargs,{'provider':'google','model':'custom','api_key':'alice-key'})
            sid=first['session_id']
            second=c.post('/api/ai/recommend',headers=h,json={'prompt':'Prefer AMD','session_id':sid,'provider':'openai','api_key':'override-key'}).json()
            self.assertEqual(second['session_id'],sid)
            self.assertEqual(call.call_args.kwargs['provider'],'openai')
            self.assertEqual(call.call_args.kwargs['api_key'],'override-key')
            self.assertIn('Budget 30000',call.call_args.args[1])
            messages=json.loads(c.get('/api/ai/sessions/'+str(sid),headers=h).json()['data']['messages'])
            self.assertEqual(len(messages),4)
            count=call.await_count
            self.assertEqual(c.post('/api/ai/recommend',headers=self.auth('bob'),json={'prompt':'x','session_id':sid,'provider':'openai','api_key':'override-key'}).status_code,404)
            self.assertEqual(call.await_count,count)
            self.assertEqual(c.post('/api/ai/recommend',json={'prompt':'guest','provider':'openai','api_key':'override-key'}).json()['session_id'],None)
            self.assertEqual(c.post('/api/ai/recommend',json={'prompt':'x','session_id':sid,'api_key':'guest-key'}).status_code,401)
            with patch.dict(os.environ, {'GOOGLE_API_KEY': '', 'GEMINI_API_KEY': ''}, clear=False):
                self.assertEqual(c.post('/api/ai/recommend',json={'prompt':'x','provider':'google'}).status_code,200)
                self.assertEqual(call.call_args.kwargs['api_key'], '')

    def test_retired_google_model_uses_verified_default(self):
        self.assertEqual(self.api.normalize_ai_model('google', 'gemini-2.5-pro'), 'gemini-3-flash-preview')
        self.assertEqual(self.api.normalize_ai_model('google', 'custom-model'), 'custom-model')
        self.assertEqual(self.api.normalize_ai_model('openai', 'gemini-2.5-pro'), 'gemini-2.5-pro')

    def test_extract_json_accepts_fenced_response_with_trailing_text(self):
        parsed = self.rec.extract_json('Here is the build:\n```json\n{"parts":[{"type":"CPU"}]}\n```\nDone.')
        self.assertEqual(parsed['parts'][0]['type'], 'CPU')

    def test_provider_failure_returns_labelled_build_and_saves_history(self):
        fallback = {'summary': 'catalogue build', 'parts': [], '_meta': {'provider_fallback': True}}
        with patch.object(self.rec, 'recommend_with_alternatives', new_callable=AsyncMock, side_effect=RuntimeError('provider down')):
            with patch.object(self.rec, 'recommend_without_provider', return_value=fallback):
                response = self.client.post('/api/ai/recommend', headers=self.auth(), json={
                    'prompt': 'Budget 30000', 'provider': 'google', 'model': 'gemini-2.5-pro', 'api_key': 'test-key'
                })
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(json.loads(payload['data'])['_meta']['provider_fallback'])
        saved = self.client.get(f"/api/ai/sessions/{payload['session_id']}", headers=self.auth()).json()['data']
        self.assertEqual(len(json.loads(saved['messages'])), 2)
        self.assertEqual(saved['model'], 'gemini-3-flash-preview')

    def test_legacy_fk_migration_preserves_rows(self):
        from sqlalchemy import create_engine, text
        engine=create_engine('sqlite://')
        with engine.begin() as db:
            db.execute(text('CREATE TABLE users (uid TEXT PRIMARY KEY)'))
            db.execute(text("INSERT INTO users VALUES ('alice')"))
            db.execute(text('CREATE TABLE user_ai_settings (uid TEXT PRIMARY KEY, api_key TEXT)'))
            db.execute(text("INSERT INTO user_ai_settings VALUES ('alice', 'test-key')"))
            db.execute(text('CREATE INDEX legacy_ai_idx ON user_ai_settings(uid)'))
        self.api.migrate_ai_foreign_keys(engine)
        self.api.migrate_ai_foreign_keys(engine)
        with engine.connect() as db:
            self.assertEqual(db.execute(text('SELECT api_key FROM user_ai_settings')).scalar(),'test-key')
            self.assertEqual(db.execute(text('PRAGMA foreign_key_list(user_ai_settings)')).first()[2],'users')
            self.assertTrue(db.execute(text("SELECT name FROM sqlite_master WHERE name='legacy_ai_idx'")).first())
        engine.dispose()

    def test_product_power_uses_database_identity(self):
        with self.api.SessionLocal() as db:
            db.add(self.api.Product(product_id='gpu-power-test',p_name='ASUS RTX 5050',category='GPU',specs='Recommended PSU: 650 W',p_price=1))
            db.commit()
        res=self.client.post('/api/compatibility/check-parts',json={'parts':[
            {'category':'CPU','name':'Ryzen 5 5500'},
            {'product_id':'gpu-power-test','name':'RTX 3050','category':'PSU'},
            {'category':'PSU','name':'PSU 450W'}]}).json()['data']
        check=next(c for c in res['checks'] if c['item'].startswith('R3'))
        self.assertEqual(check['required_watt'],650)
        self.assertEqual(res['overall'],'error')
        self.assertTrue(check['sources'])
        self.assertEqual(self.client.post('/api/compatibility/check-parts',json={'parts':[{'product_id':'missing'}]}).status_code,404)

    def test_removed_provider_rejected(self):
        for url in ('/api/ai/settings', '/api/ai/sessions', '/api/ai/recommend'):
            method = self.client.put if url.endswith('settings') else self.client.post
            self.assertEqual(method(url, headers=self.auth(), json={'provider':'zen','prompt':'test'}).status_code,422)

    def test_provider_http_requests(self):
        import httpx
        for provider,model in [('google','gemini-2.0-flash'),('openai','gpt-4o-mini'),('openai','o1-mini'),('openrouter','custom/model')]:
            response=httpx.Response(200,json={'choices':[{'message':{'content':'ok'}}]})
            fake=AsyncMock()
            fake.__aenter__.return_value=fake
            fake.post.return_value=response
            with patch.object(self.rec.httpx,'AsyncClient',return_value=fake):
                result=asyncio.run(self.rec.llm_chat([{'role':'user','content':'hello'}],provider=provider,model=model,api_key='user-key'))
                self.assertEqual(result,'ok')
                args=fake.post.call_args
                self.assertTrue(args.args[0].startswith(self.rec.PROVIDER_BASE_URLS[provider]))
                self.assertEqual(args.kwargs['headers']['Authorization'],'Bearer user-key')
                self.assertEqual(args.kwargs['json']['model'],model)
                if model=='o1-mini':
                    self.assertIn('max_completion_tokens',args.kwargs['json'])
                    self.assertNotIn('temperature',args.kwargs['json'])

if __name__ == '__main__':
    unittest.main()
