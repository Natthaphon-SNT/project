import { isIP } from 'node:net';

const BACKEND_ORIGIN = 'https://api-production-8990.up.railway.app';
const FORWARDED_HEADERS = [
  'x-forwarded-for', 'x-real-ip', 'x-vercel-forwarded-for', 'cf-connecting-ip',
  'x-vercel-ip-country', 'x-access-log-proxy-secret',
];
const HOP_HEADERS = [
  'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
  'te', 'trailer', 'transfer-encoding', 'upgrade', 'host', 'content-length',
];

export default {
  async fetch(request) {
    const incoming = new URL(request.url);
    const path = incoming.searchParams.get('__proxy_path') || '';
    let invalidPath = !path;
    try {
      invalidPath ||= path.split('/').some(part => ['.', '..'].includes(decodeURIComponent(part)));
    } catch {
      invalidPath = true;
    }
    if (invalidPath) {
      return new Response('Invalid API path', { status: 400 });
    }
    incoming.searchParams.delete('__proxy_path');
    const target = new URL(BACKEND_ORIGIN);
    target.pathname = '/api/' + path;
    target.search = incoming.searchParams.toString();

    // Vercel overwrites XFF at its Function boundary. External rewrites alone
    // do not protect the incoming x-vercel-forwarded-for header (tested live).
    const visitor = (request.headers.get('x-forwarded-for') || '').split(',')[0].trim();
    const country = (request.headers.get('x-vercel-ip-country') || '').trim().toUpperCase();
    const headers = new Headers(request.headers);
    for (const name of [...FORWARDED_HEADERS, ...HOP_HEADERS]) headers.delete(name);
    if (isIP(visitor)) headers.set('x-vercel-forwarded-for', visitor);
    if (/^[A-Z]{2}$/.test(country)) headers.set('x-vercel-ip-country', country);
    const secret = process.env.ACCESS_LOG_PROXY_SECRET || '';
    if (secret.length >= 32) headers.set('x-access-log-proxy-secret', secret);

    try {
      const upstream = await fetch(target, {
        method: request.method, headers,
        body: ['GET', 'HEAD'].includes(request.method) ? undefined : request.body,
        duplex: 'half', redirect: 'manual', signal: AbortSignal.timeout(240_000),
      });
      if (upstream.status === 413) {
        return Response.json({
          code: 'PAYLOAD_TOO_LARGE',
          detail: path === 'profile/upload-image'
            ? 'ไฟล์ใหญ่เกินไป กรุณาเลือกรูปไม่เกิน 4 MB'
            : 'ข้อมูลที่ส่งมีขนาดใหญ่เกินกำหนด',
        }, { status: 413 });
      }
      const responseHeaders = new Headers(upstream.headers);
      for (const name of [...HOP_HEADERS, 'content-encoding']) responseHeaders.delete(name);
      return new Response(upstream.body, {
        status: upstream.status, statusText: upstream.statusText, headers: responseHeaders,
      });
    } catch {
      // Do not log URLs, request content, credentials, or fetch errors.
      return new Response('Backend unavailable', { status: 502 });
    }
  },
};
