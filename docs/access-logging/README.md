# Access logging สำหรับ Railway backend

โค้ดและเอกสารอ้างอิงวันที่ 2 ตุลาคม 2026 ใช้ Supabase project
[`uervyttvxzqsctwyogso`](https://supabase.com/dashboard/project/uervyttvxzqsctwyogso)
เพื่อเก็บ access logs เท่านั้น ข้อมูลหลักและ schema ของ SQLite ไม่เปลี่ยน

## สิ่งที่ทำแล้วและสิ่งที่ยังไม่ได้ยืนยัน

- เพิ่ม `backend/access_log.py` และติดตั้ง middleware หลัง CORS/slowapi ใน `shop_api.py`
- ใช้ `httpx` ที่มีใน requirements อยู่แล้ว ไม่เพิ่ม dependencies
- บันทึกเฉพาะ method, path, status, IP, country, User-Agent และ user ID
- ไม่อ่าน/เก็บ body, query string, incoming Authorization header หรือ cookie
- ใช้ AsyncClient ตัวเดียวต่อ app lifespan, timeout 5 วินาที; ไม่ตาม redirect
- ส่งด้วย `asyncio.create_task`, เก็บ reference ใน set และ discard เมื่อเสร็จ
- ทดสอบด้วย requests/DB ชั่วคราวและ Supabase MockTransport รวมถึง HTTP 401/403/200,
  IP fallback, User-Agent, การตัดความยาว, การไม่บันทึก products และ Supabase ล่ม
- ผลล่าสุด: 62 tests ผ่าน (logging, verifier, routes/ownership และ DB isolation audit)
  และเรียก Uvicorn ผ่าน HTTP จริงกับ SQLite ชั่วคราวผ่าน: รหัสผิด 401, ไม่มี token 401,
  สมาชิกเข้า admin 403, admin 200, products/health 200 แม้ Supabase URL ติดต่อไม่ได้
  server ทดสอบหยุดแล้วและลบ DB/uploads ชั่วคราวแล้ว
- ตรวจ Railway production ผ่านบัญชี CLI เดิมแล้ว: JWT/encryption key มีค่าและรูปแบบถูกต้อง,
  volume `/data` อยู่ในสถานะ READY, DB `/data/shop.db`, uploads `/data/uploads`
  และ `REQUIRE_EXISTING_DB=1` โดยไม่เปิดเผย secret
- ตรวจ Vercel project `recommend` แล้ว: root `It-shop`, Angular, Node 24.x,
  build `npm run build`, output `dist/lt-shop/browser`; production build ผ่าน
  (มี warnings เรื่องขนาด bundle/CSS) และ recommendation regressions เพิ่มอีก 100 tests ผ่าน
- ยังไม่ได้ apply migration, ตรวจ RLS จริง, ทดสอบ anon key จริง หรือตั้ง Supabase variables
  บน Railway เพราะยังไม่มี Supabase connection/credentials;
  `SUPABASE_URL` และ `SUPABASE_SERVICE_KEY` ยังไม่อยู่ใน backend variables ตอนตรวจ
- Dashboard URL ระบุ project ได้ แต่ไม่แทนสิทธิ์เข้าถึงบัญชี
  มี Supabase plugin ให้ติดตั้ง/เชื่อม; หากเชื่อมแล้วสามารถ apply และตรวจต่อได้

## Routes และสิทธิ์ที่ตรวจจาก backend

Routes จริงใช้ `/api/login`, `/api/register` และ `/api/admin/users/...`;
ไม่มี route `/login` หรือ `/admin/...` ใน backend ปัจจุบัน และการเรียกชื่อเหล่านั้นจะได้ 404
ยังเก็บ prefix เหล่านั้นไว้ตามข้อกำหนด เพื่อบันทึกการลองเข้าหรือรองรับ routes ภายหลัง

| กลุ่ม | บันทึก | สิทธิ์ฝั่งเซิร์ฟเวอร์ |
| --- | --- | --- |
| `/admin`, `/api/admin`, `/auth`, `/api/auth`, `/login`, `/api/login`, `/register`, `/api/register` และ paths ที่ขึ้นต้นด้วยค่าเหล่านี้ | ทุก method/status | Login/register เปิดให้สมัคร/ยืนยันตัวตน; admin routes จริงใช้ `require_admin` |
| `/api/profile` และ endpoints ย่อย | ทุก method/status | `get_current_user`; ใช้บัญชีจาก JWT |
| `/api/ai/settings`, `/api/ai/sessions` และ endpoints ย่อย | ทุก method/status | JWT + การกรอง uid เจ้าของ; admin ไม่มีสิทธิ์อ่าน key ของคนอื่นผ่าน owner API |
| `/api/ai/recommend` | ทุก method/status | `get_current_user`; ไม่เปลี่ยน logic AI |
| `/api/spec-history` และ endpoints ย่อย | ทุก method/status | เจ้าของใช้ JWT/uid; `/api/spec-history/all` ต้อง `require_admin` |
| `/api/scrape` และ endpoints ย่อย | ทุก method/status | POST สั่ง scrape ต้อง `require_admin`; GET status เดิมคืนเฉพาะสถิติสินค้า เป็น public |
| `/api/products`, `/api/promotions` และ endpoints ย่อย | เฉพาะ POST/PUT/PATCH/DELETE | Routes ที่มีจริงสำหรับการแก้ข้อมูลใช้ `require_admin` |
| GET products, categories, images, uploads, `/health` และ paths อื่น | ไม่บันทึก | คงสิทธิ์เดิม |

ตรวจแล้วว่า `require_admin` เรียก `get_current_user` และตรวจ role จาก DB
API จัดการผู้ใช้ทั้ง GET list/detail/specs, PUT detail/role และ DELETE มี dependency ครบ
รวมทั้ง GET `/api/spec-history/all`, การแก้สินค้า/โปรโมชั่น และ POST `/api/scrape`
**ไม่มี endpoint ที่ต้องเพิ่ม `require_admin` ใหม่**

ข้อมูลส่วนตัวของเจ้าของใช้ JWT และตรวจ ownership ตามคำยืนยันของผู้ใช้
`get_current_user` เซ็ต `request.state.user_id` หลังตรวจ JWT, ผู้ใช้ และ token_version สำเร็จ
Login สำเร็จเซ็ต uid หลังตรวจรหัสผ่าน การล็อกอินล้มเหลวหรือ token ไม่ถูกต้องไม่อ้าง uid
ลูกค้าที่ล็อกอินแล้วแต่ถูกปฏิเสธ admin ได้ status 403 และ uid ของบัญชีนั้น

## สร้างตารางใน Supabase

เปิด SQL Editor ของ project ที่ระบุและรัน
[`20261002000000_access_logs.sql`](../../supabase/migrations/20261002000000_access_logs.sql)
ครั้งเดียว หากมีตารางอยู่แล้ว ให้ตรวจ schema/สิทธิ์ก่อน ห้ามลบตารางเดิมเพื่อรันซ้ำ

Migration สร้างเฉพาะตาราง/index ใน Supabase, เปิด RLS, **ไม่สร้าง policy**,
revoke สิทธิ์ table/identity sequence จาก PUBLIC, anon และ authenticated
และให้ service_role ใช้อ่าน/เพิ่ม/ลบ log โดยมี assertion ตรวจ RLS และ policy ภายใน transaction
ถ้า assertion ล้มเหลว transaction ไม่ commit การตรวจในไฟล์ยังไม่ใช่ผลตรวจฐานข้อมูลจริง
การใช้ service_role bypass RLS เป็นพฤติกรรมของ Supabase จึงต้องรักษา key ฝั่ง backend
([เอกสาร Supabase](https://supabase.com/docs/guides/database/postgres/row-level-security))

รันส่วนแรกของ [`queries.sql`](queries.sql) หลัง migration ต้องได้
`rls_enabled=true`, `policy_count=0` และ `can_read=false`, `can_write=false`
สำหรับทั้ง anon และ authenticated
ไฟล์เดียวกันมี query ดูล่าสุด, IP ที่ได้ 401/403 ใน 7 วัน,
admin API ที่ตอบ 200 และ SQL ลบเก่ากว่า 90 วัน
ให้รันส่วนลบแยกต่างหากหลังดูจำนวนแถว; ไม่ได้ตั้ง scheduled deletion อัตโนมัติ

## Environment และการ deploy

ใน Railway **backend service เท่านั้น** ตั้ง:

```dotenv
SUPABASE_URL=https://uervyttvxzqsctwyogso.supabase.co
SUPABASE_SERVICE_KEY=<service_role-key-from-this-project>
```

URL เป็นข้อมูล project ไม่ใช่ secret ส่วน key ต้องใช้ `service_role` ของ project นี้
ไม่ใช่ anon/publishable key ห้ามพิมพ์ key ใน terminal/log/report
อย่าวาง key ใน Angular, Vercel, source code หรือ Git
`.env.example` มีชื่อและค่าว่าง; `.gitignore` ignore `.env*` แต่ยกเว้น `.env.example`
JWT/encryption key เดิมยังจำเป็นต่อ startup และต้องคงค่าเดิมของ DB

Backend สร้าง client ใน lifespan ตอน startup ต้อง restart/redeploy หลังตั้ง variables
เมื่อ env ขาด/URL ไม่ถูกต้องจะปิด logging; URL ต้องเป็น HTTPS origin ไม่มี credentials/query
ความผิดพลาดการส่ง Supabase ถูกข้ามเงียบ ๆ และไม่เปลี่ยน HTTP response ของ API
ไม่มี log error ที่อาจพิมพ์ service key

## ตรวจ IP เมื่อผ่าน Vercel

`It-shop/vercel.json` rewrite `/api/:path*` ไป Railway และ production Angular ใช้ same-origin
Vercel ระบุว่า `x-forwarded-for`/`x-real-ip` เป็น public IP ของผู้เรียก
และ `x-vercel-ip-country` เป็นรหัสประเทศ
([เอกสาร request headers](https://vercel.com/docs/headers/request-headers))
External rewrites เป็น reverse proxy
([เอกสาร rewrites](https://vercel.com/kb/guide/vercel-reverse-proxy-rewrites-external))

จากเอกสารคาดว่า IP ผู้ใช้ควรถูกส่งต่อ แต่ **ยังไม่ได้ยืนยัน header chain จริงระหว่าง
Vercel กับ Railway ของ deployment นี้** Railway หรือ proxy อีกชั้นอาจเขียน header ทับ
middleware ทำตามลำดับที่กำหนด: ค่าแรก X-Forwarded-For → X-Real-IP → request.client.host
เมื่อไม่มี country header เก็บ null; ไม่เดาประเทศ

หลัง deploy ให้เทียบ IP ในแถวที่เกิดจาก browser เรียก same-origin `/api/admin/users`
กับ IP ของผู้ใช้ขณะนั้น แล้วเทียบการเรียก Railway โดยตรงจากเครือข่ายเดียวกัน
ทำซ้ำจากอีกเครือข่าย ถ้าทั้งสองเครือข่ายเห็น IP คงที่ของ Vercel ให้ถือว่ายังระบุผู้ใช้ไม่ได้

ทางแก้ที่เลือกได้หากยืนยันว่า IP เป็นของ Vercel:

1. ให้ Angular เรียก Railway URL โดยตรง และตั้ง CORS_ORIGINS สำหรับโดเมน frontend
   วิธีนี้ตัด Vercel rewrite ออกจากเส้นทาง API โดย service key ยังอยู่ backend เท่านั้น
2. ใช้ proxy ที่อ่าน client IP ของ Vercel และส่งต่ออย่างชัดเจน พร้อมจำกัด origin backend
   หรือยืนยัน proxy ด้วย signed header เพื่อป้องกันการปลอมค่า forwarded headers

ยังไม่ได้เปลี่ยน proxy หรือค่าความปลอดภัย/DB/volume ของ production
Forwarded IP/country เป็นข้อมูลที่ proxy อ้าง ไม่ใช่หลักฐานยืนยันตัวตน;
ถ้าเปิด Railway origin ให้เรียกตรง ผู้เรียกอาจปลอม headers ได้

## ทดสอบจริงหลังสร้างตาราง

สำหรับ local ให้ตั้ง variables อย่างเป็นส่วนตัวและเริ่ม backend กับ DB/uploads ชั่วคราว
ตาม README หลัก ห้ามใช้ DB จริงสำหรับการทดสอบนี้
จากรากโปรเจกต์รัน:

```powershell
.\venv\Scripts\python.exe -B backend\verify_access_logs.py --api-base http://127.0.0.1:3000
```

สคริปต์อ่าน URL/service key จาก environment หรือ root `.env`
และถาม anon key แบบซ่อน input (หรืออ่าน `SUPABASE_ANON_KEY` เฉพาะ process ทดสอบ)
ตรวจว่า anon key ใช้ได้จริงผ่าน `/auth/v1/settings` ก่อนทดสอบสิทธิ์ตาราง
แล้วตรวจว่า service_role อ่านได้ ส่วน anon อ่าน/เขียนต้องได้ 401/403
ถ้าตารางไม่ปลอดภัย อาจมีแถวสังเคราะห์ `anon-permission-test` ถูกเพิ่มจากการทดสอบเขียน
ให้แก้สิทธิ์และลบเฉพาะแถวนั้นผ่าน SQL Editor

เมื่อมี `--api-base` จะเรียก `/api/login` ด้วยบัญชีสังเคราะห์ที่ไม่มีอยู่และ `/api/admin/users`
โดยไม่มี token แล้วรอ log ไม่เกิน 8 วินาที ตรวจว่ามี 401, IP และ User-Agent ที่ตรง marker
และไม่มีแถว products จาก marker เดียวกัน ไม่พิมพ์ key หรือข้อมูล response
ไม่ใส่ `--api-base` จะตรวจสิทธิ์ Supabase อย่างเดียว

ตรวจเพิ่มใน browser หลัง deploy:

- เข้า login ด้วยรหัสผิด: log `/api/login` ต้องมี 401
- ไม่ล็อกอินเรียก `/api/admin/users`: 401, user_id null
- สมาชิกเรียก `/api/admin/users`: 403, user_id สมาชิก
- Admin เรียก `/api/admin/users`: 200, user_id admin
- Profile/settings/sessions/history ของเจ้าของยังใช้ได้ และเข้าถึงของคนอื่นไม่ได้
- เรียก products: ไม่ควรมีแถว log
- ทดสอบ local ด้วย `SUPABASE_URL=https://unreachable.invalid`: API ยังตอบตามสิทธิ์เดิม

## ข้อจำกัดของการส่งเบื้องหลัง

Fire-and-forget ไม่รับประกันว่าเก็บครบทุก request: process ถูก kill, Supabase ล่ม,
หรือมี task ค้างครบ 256 รายการ จะข้าม log โดยไม่รบกวน API
ตอน shutdown รอ task ไม่เกิน 5 วินาที จากนั้น cancel และปิด client
ไม่มี retry/persistent queue และไม่เก็บสำเนาใน SQLite
หลัง deploy จึงต้องตรวจว่ามีแถวจริงเข้าตาราง ไม่ใช่ดูเพียงว่า API ยังตอบได้

## ส่งมอบไฟล์ฉบับเต็ม

[`full-files.md`](full-files.md) เป็น snapshot เนื้อหาทุกไฟล์ที่เพิ่ม/แก้สำหรับงานนี้
ทั้งไฟล์ รวม `shop_api.py` ฉบับเต็ม ไม่ใช่ diff (ไม่รวม snapshot ตัวมันเองเพื่อไม่ให้วนซ้ำ)
ไฟล์ที่เปลี่ยนในงานก่อนหน้ายังคงอยู่และไม่ได้ย้อนการแก้เหล่านั้น
