from google import genai

# แนะนำให้สร้าง API Key ใหม่นะครับ เพราะอันเดิมถูกเปิดเผยแล้ว
client = genai.Client(api_key="AIzaSyB4uc7nBU9aK-DBolVnNWfVVwnwSQnfAGo")

print("กำลังค้นหาโมเดลที่ใช้ได้ (โดยใช้ google-genai)...")

try:
    # ดึงโมเดลทั้งหมดออกมาดูก่อนโดยไม่กรอง เพื่อเช็คว่าเชื่อมต่อได้จริงไหม
    models = client.models.list()
    
    count = 0
    for m in models:
        # ตรวจสอบเงื่อนไขการใช้งาน (SDK ตัวนี้จะเก็บใน supported_methods หรือ supported_actions)
        # ลองพิมพ์ออกมาทั้งหมดเพื่อดูรายชื่อ
        print(f"พบโมเดล: {m.name}")
        count += 1
            
    if count == 0:
        print("เชื่อมต่อสำเร็จ แต่ไม่พบโมเดลในรายการ (โปรดตรวจสอบโควตา API Key)")

except Exception as e:
    print(f"เกิดข้อผิดพลาด: {e}")