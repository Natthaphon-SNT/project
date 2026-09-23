"""Manual Google model-list diagnostic; credentials come from the environment."""

import os

from google import genai


api_key = os.getenv("GOOGLE_API_KEY", "").strip()
if not api_key:
    raise SystemExit("Set GOOGLE_API_KEY in the environment before running this diagnostic.")

client = genai.Client(api_key=api_key)
print("กำลังค้นหาโมเดลที่ใช้ได้ (โดยใช้ google-genai)...")

try:
    models = client.models.list()
    count = 0
    for model in models:
        print(f"พบโมเดล: {model.name}")
        count += 1
    if count == 0:
        print("เชื่อมต่อสำเร็จ แต่ไม่พบโมเดลในรายการ (โปรดตรวจสอบโควตา API Key)")
except Exception as exc:
    print(f"เกิดข้อผิดพลาด: {exc}")
