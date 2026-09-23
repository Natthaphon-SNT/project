"""Manual Gemini smoke test; credentials come from the environment."""

import os

from google import genai


api_key = os.getenv("GOOGLE_API_KEY", "").strip()
if not api_key:
    raise SystemExit("Set GOOGLE_API_KEY in the environment before running this diagnostic.")

client = genai.Client(api_key=api_key)
model = "gemini-2.5-flash"
print(f"กำลังทดสอบ API ด้วยโมเดล: {model}...")

try:
    response = client.models.generate_content(
        model=model,
        contents="สวัสดี ทดสอบระบบ 123",
    )
    print("✅ สำเร็จ! API ทำงานได้ปกติ ข้อความจาก AI:")
    print(response.text)
except Exception as exc:
    print(f"❌ Error: {exc}")
