from google import genai

# 1. ใส่ API KEY ใหม่ของคุณตรงนี้
API_KEY = "AIzaSyCcmlhOpMnL99ZA0Je0HWy4EKMrhVbvNnQ"
client = genai.Client(api_key=API_KEY)

# 2. ลองใช้โมเดล 1.5-flash หรือ 2.0-flash-lite
MODEL = 'gemini-2.5-flash' 

print(f"กำลังทดสอบ API ด้วยโมเดล: {MODEL}...")

try:
    response = client.models.generate_content(
        model=MODEL,
        contents='สวัสดี ทดสอบระบบ 123'
    )
    print("✅ สำเร็จ! API ทำงานได้ปกติ ข้อความจาก AI:")
    print(response.text)
except Exception as e:
    print(f"❌ Error: {e}")