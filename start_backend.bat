@echo off
echo =============================================
echo   🚀 T.A.K Tech Shop - FastAPI Backend Setup
echo   (ไม่ต้องใช้ XAMPP อีกต่อไป!)
echo =============================================
echo.

cd /d "%~dp0backend"

echo [1/3] ตรวจสอบ Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ ไม่พบ Python! กรุณาติดตั้ง Python 3.11+ จาก https://python.org
    pause
    exit /b 1
)

echo [2/3] ติดตั้ง dependencies...
pip install -r requirements.txt

echo.
echo [3/3] เริ่ม API Server...
echo.
echo ✅ API พร้อมใช้งาน!
echo 🌐 URL:      http://localhost:3000
echo 📄 API Docs: http://localhost:3000/docs
echo.
echo กด Ctrl+C เพื่อหยุดเซิร์ฟเวอร์
echo.

python shop_api.py
pause
