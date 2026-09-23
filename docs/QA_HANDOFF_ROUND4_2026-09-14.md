# IT-RECOMMEND — Round 4 Human/Infrastructure Handoff

วันที่จัดทำ: 14 กันยายน 2026 (Asia/Bangkok)  
ฐานอ้างอิง: revision `5722fd7a7e1a659fd924a74fa6d2989e5d5a3739` และ Closure รอบ 3  
ข้อควรระวัง: เอกสารและหลักฐานที่ส่งกลับต้องปิดบังค่า credential ทั้งหมด

## A1 — SEC01 (P0, ยังบล็อก QA Passed)

เจ้าของงาน: ผู้ดูแล Google Cloud project ที่มีสิทธิ์จัดการ Credentials  
สถานะปัจจุบัน: **Pending human evidence** — source working tree ไม่พบ key ในรูปแบบ Google แล้ว แต่ agent ไม่สามารถยืนยันสถานะฝั่ง Google Cloud ได้

สิ่งที่เจ้าของระบบต้องทำ:

- หา key ที่เคยอยู่ใน commit `46c14cea` ที่ Google Cloud Console → API & Services → Credentials
- Revoke/Delete key เดิม และบันทึก screenshot ที่เห็นสถานะกับ timestamp โดยปิดบังค่า key
- จากเครื่องของผู้ดูแล ทดสอบ key เดิมให้ได้ 401/403/`API_KEY_INVALID`; ส่งเฉพาะ status/error ที่ redacted แล้ว ห้ามส่งค่า key
- สร้าง key ใหม่และจำกัด API เฉพาะ Generative Language API, จำกัด application ตาม deployment จริง และกำหนด quota
- บันทึก owner และ timestamp ในระบบจัดการ secret ภายใน เช่น Vault/1Password—not Git
- ถ้า repository เคย public หรือมี fork/mirror ให้ประเมินและดำเนินการล้าง `.env` จาก history ด้วย `git filter-repo`, force-push และแจ้งผู้ร่วมงาน clone ใหม่

แบบฟอร์มหลักฐานส่งกลับ:

```text
SEC01 owner: <team/person>
Rotated/revoked at (ISO-8601 + timezone): <timestamp>
Old-key live result: <401|403|API_KEY_INVALID; redacted>
Revoke evidence: <redacted screenshot/file reference>
New-key API restriction: <redacted screenshot/file reference>
New-key application restriction: <redacted screenshot/file reference>
Quota restriction: <redacted screenshot/file reference>
Secret-manager record: <record reference; never paste secret>
History cleanup decision: <required/not required + reason>
Remote/fork notification: <reference or N/A>
```

เกณฑ์ปิด: ต้องมีครบทั้ง (1) live revoke evidence (2) new-key restriction evidence และ (3) owner/timestamp record ขาดส่วนใดส่วนหนึ่งให้คงสถานะ Open

## A2 — P2 ที่รอสิทธิ์หรือ infrastructure

| งาน | Owner/Prerequisite | หลักฐานที่ต้องกลับมา | บล็อก Round 4 หรือไม่ |
| --- | --- | --- | --- |
| AI provider จริง 5–10 prompt ไทย | key ใหม่หลัง SEC01 + ผู้อนุมัติค่าใช้จ่าย | prompt/response ที่ redacted, model, timestamp และผลตรวจความไม่มั่ว | ไม่บล็อก แต่ห้ามรันก่อน rotate |
| Android Chrome เครื่องจริง | ผู้มีอุปกรณ์ Android | รุ่น OS/browser, screenshot และผล PC Builder + AI Recommend | ไม่บล็อก |
| iOS Safari เครื่องจริง | ผู้มี iPhone/iPad | รุ่น OS/browser, screenshot และผล PC Builder + AI Recommend | ไม่บล็อก |
| HTTP load test ใกล้ production | deploy target + workload/SLA ที่ทีมอนุมัติ | k6/locust config, request rate, error rate, p50/p95/p99 | ไม่บล็อก |

## สถานะการส่งต่อ

- [ ] SEC01 revoke evidence ได้รับแล้ว
- [ ] SEC01 restriction evidence ได้รับแล้ว
- [ ] SEC01 owner/timestamp record ได้รับแล้ว
- [ ] AI provider test ได้รับอนุมัติและรันหลัง rotate
- [ ] Android Chrome physical-device evidence
- [ ] iOS Safari physical-device evidence
- [ ] Production-like load-test target/workload/SLA พร้อม

จนกว่า SEC01 สามรายการแรกจะครบ สถานะรวมสูงสุดคือ **Conditional** แม้งาน engineering ทั้งหมดผ่าน
