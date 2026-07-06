"""
Script สำหรับจัดการ database เบื้องต้น
รัน: python db_tools.py
"""
import sys
sys.path.insert(0, '.')
from shop_api import SessionLocal, User, Base, engine

def set_admin(uid_or_name: str):
    """เปลี่ยน role ของ user เป็น admin"""
    db = SessionLocal()
    user = db.query(User).filter(
        (User.uid == uid_or_name) | (User.u_name == uid_or_name)
    ).first()
    if not user:
        print(f"[ERROR] ไม่พบผู้ใช้ '{uid_or_name}'")
        return
    user.u_role = 'admin'
    db.commit()
    print(f"[OK] '{user.u_name}' ได้รับสิทธิ์ Admin แล้ว")
    db.close()

def list_users():
    """แสดงรายชื่อผู้ใช้ทั้งหมด"""
    db = SessionLocal()
    users = db.query(User).all()
    print(f"\n{'UID':<12} {'Username':<20} {'Email':<30} {'Role'}")
    print("-" * 70)
    for u in users:
        print(f"{u.uid:<12} {u.u_name:<20} {u.u_email:<30} {u.u_role}")
    db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python db_tools.py list")
        print("  python db_tools.py admin <uid_or_username>")
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd == "list":
        list_users()
    elif cmd == "admin" and len(sys.argv) >= 3:
        set_admin(sys.argv[2])
    else:
        print("คำสั่งไม่ถูกต้อง ดู Usage ด้านบน")
