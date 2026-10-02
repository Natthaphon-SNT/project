import assert from 'node:assert/strict';
import { test, afterEach } from 'node:test';
import proxy from '../api/proxy.mjs';

const originalFetch = globalThis.fetch;
const originalSecret = process.env.ACCESS_LOG_PROXY_SECRET;
afterEach(() => {
  globalThis.fetch = originalFetch;
  if (originalSecret === undefined) delete process.env.ACCESS_LOG_PROXY_SECRET;
  else process.env.ACCESS_LOG_PROXY_SECRET = originalSecret;
});

test('forwards JSON/auth, replaces spoofed metadata, and never follows redirects', async () => {
  process.env.ACCESS_LOG_PROXY_SECRET = 'synthetic-proxy-secret-for-testing-only';
  let outgoing;
  globalThis.fetch = async (url, options) => {
    outgoing = { url, options, body: await new Response(options.body).text() };
    return new Response('denied', { status: 401, headers: { 'content-type': 'text/plain' } });
  };
  const response = await proxy.fetch(new Request('https://test/api/proxy?__proxy_path=login&keep=value', {
    method: 'POST', body: '{"password":"synthetic"}', headers: {
      'content-type': 'application/json', authorization: 'Bearer synthetic-token',
      'x-forwarded-for': '198.51.100.10, 192.0.2.10',
      'x-vercel-forwarded-for': '203.0.113.99', 'x-real-ip': '203.0.113.98',
      'cf-connecting-ip': '203.0.113.97', 'x-vercel-ip-country': 'TH',
      'x-access-log-proxy-secret': 'attacker-supplied',
    },
  }));
  assert.equal(response.status, 401);
  assert.equal(await response.text(), 'denied');
  assert.equal(outgoing.url.href, 'https://api-production-8990.up.railway.app/api/login?keep=value');
  assert.equal(outgoing.body, '{"password":"synthetic"}');
  assert.equal(outgoing.options.headers.get('authorization'), 'Bearer synthetic-token');
  assert.equal(outgoing.options.headers.get('x-vercel-forwarded-for'), '198.51.100.10');
  assert.equal(outgoing.options.headers.get('x-vercel-ip-country'), 'TH');
  assert.equal(outgoing.options.headers.get('x-access-log-proxy-secret'), process.env.ACCESS_LOG_PROXY_SECRET);
  for (const header of ['x-real-ip', 'x-forwarded-for', 'cf-connecting-ip']) {
    assert.equal(outgoing.options.headers.get(header), null);
  }
  assert.equal(outgoing.options.redirect, 'manual');
});

test('preserves binary multipart bytes and response cookies', async () => {
  const bytes = new Uint8Array([0, 255, 13, 10, 127]);
  globalThis.fetch = async (_url, options) => {
    assert.deepEqual(new Uint8Array(await new Response(options.body).arrayBuffer()), bytes);
    assert.equal(options.headers.get('content-type'), 'multipart/form-data; boundary=test');
    return new Response('ok', { headers: { 'set-cookie': 'synthetic=ok; HttpOnly' } });
  };
  const response = await proxy.fetch(new Request('https://test/api/proxy?__proxy_path=profile/upload-image', {
    method: 'POST', body: bytes, headers: { 'content-type': 'multipart/form-data; boundary=test' },
  }));
  assert.equal(response.headers.get('set-cookie'), 'synthetic=ok; HttpOnly');
});

test('keeps target origin fixed and rejects path traversal', async () => {
  globalThis.fetch = async () => { throw new Error('must not forward'); };
  for (const path of ['', '../private', 'profile/../admin', '%2e%2e/private', '%invalid']) {
    const response = await proxy.fetch(new Request('https://test/api/proxy?__proxy_path=' + encodeURIComponent(path)));
    assert.equal(response.status, 400);
  }
});

test('drops malformed metadata and strips compression/connection response headers', async () => {
  delete process.env.ACCESS_LOG_PROXY_SECRET;
  globalThis.fetch = async (_url, options) => {
    assert.equal(options.headers.get('x-vercel-forwarded-for'), null);
    assert.equal(options.headers.get('x-access-log-proxy-secret'), null);
    assert.equal(options.headers.get('x-vercel-ip-country'), null);
    assert.equal(options.body, undefined);
    return new Response('decoded', { headers: { 'content-encoding': 'gzip', 'content-length': '100' } });
  };
  const response = await proxy.fetch(new Request('https://test/api/proxy?__proxy_path=profile', {
    headers: { 'x-forwarded-for': 'bad-ip', 'x-vercel-ip-country': 'invalid', 'x-access-log-proxy-secret': 'fake' },
  }));
  assert.equal(response.headers.get('content-encoding'), null);
  assert.equal(response.headers.get('content-length'), null);
});

test('upstream failures return a generic 502 without reflecting sensitive errors', async () => {
  globalThis.fetch = async () => { throw new Error('synthetic-secret-error'); };
  const response = await proxy.fetch(new Request('https://test/api/proxy?__proxy_path=login'));
  assert.equal(response.status, 502);
  assert.equal(await response.text(), 'Backend unavailable');
});
