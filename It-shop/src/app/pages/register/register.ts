import { Component, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../../services/auth';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './register.html',
  styleUrls: ['./register.scss']
})
export class RegisterComponent {
  user = {
    name: '',
    email: '',
    phone: '',
    dob: '',
    password: '',
    confirmPassword: ''
  };

  isLoading = false;
  errorMessage = '';
  successMessage = '';
  showPassword = false;
  showConfirmPassword = false;

  // Validation flags
  fieldErrors: Record<string, string> = {};

  constructor(
    private auth: AuthService,
    private router: Router,
    private cdr: ChangeDetectorRef
  ) {}

  togglePassword()        { this.showPassword = !this.showPassword; }
  toggleConfirmPassword() { this.showConfirmPassword = !this.showConfirmPassword; }

  get passwordStrength(): { level: number; label: string; color: string } {
    const pw = this.user.password;
    if (!pw) return { level: 0, label: '', color: '' };
    let score = 0;
    if (pw.length >= 8)  score++;
    if (pw.length >= 12) score++;
    if (/[A-Z]/.test(pw)) score++;
    if (/[0-9]/.test(pw)) score++;
    if (/[^a-zA-Z0-9]/.test(pw)) score++;
    if (score <= 1) return { level: 1, label: 'อ่อนมาก',      color: '#ef4444' };
    if (score <= 2) return { level: 2, label: 'อ่อน',          color: '#f97316' };
    if (score <= 3) return { level: 3, label: 'ปานกลาง',       color: '#eab308' };
    if (score <= 4) return { level: 4, label: 'แข็งแกร่ง',     color: '#22c55e' };
    return               { level: 5, label: 'แข็งแกร่งมาก',   color: '#10b981' };
  }

  validateForm(): boolean {
    this.fieldErrors = {};
    let valid = true;

    if (!this.user.name.trim()) {
      this.fieldErrors['name'] = 'กรุณากรอกชื่อผู้ใช้';
      valid = false;
    } else if (this.user.name.trim().length < 3) {
      this.fieldErrors['name'] = 'ชื่อผู้ใช้ต้องมีอย่างน้อย 3 ตัวอักษร';
      valid = false;
    }

    if (!this.user.email.trim()) {
      this.fieldErrors['email'] = 'กรุณากรอกอีเมล';
      valid = false;
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(this.user.email)) {
      this.fieldErrors['email'] = 'รูปแบบอีเมลไม่ถูกต้อง';
      valid = false;
    }

    if (!this.user.phone.trim()) {
      this.fieldErrors['phone'] = 'กรุณากรอกเบอร์โทรศัพท์';
      valid = false;
    } else if (!/^[0-9]{9,10}$/.test(this.user.phone.replace(/[-\s]/g, ''))) {
      this.fieldErrors['phone'] = 'เบอร์โทรศัพท์ต้องเป็นตัวเลข 9-10 หลัก';
      valid = false;
    }

    if (!this.user.dob) {
      this.fieldErrors['dob'] = 'กรุณาเลือกวันเกิด';
      valid = false;
    }

    if (!this.user.password) {
      this.fieldErrors['password'] = 'กรุณากรอกรหัสผ่าน';
      valid = false;
    } else if (this.user.password.length < 6) {
      this.fieldErrors['password'] = 'รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร';
      valid = false;
    }

    if (!this.user.confirmPassword) {
      this.fieldErrors['confirmPassword'] = 'กรุณายืนยันรหัสผ่าน';
      valid = false;
    } else if (this.user.password !== this.user.confirmPassword) {
      this.fieldErrors['confirmPassword'] = 'รหัสผ่านไม่ตรงกัน';
      valid = false;
    }

    return valid;
  }

  onRegister() {
    this.errorMessage = '';
    this.successMessage = '';

    if (!this.validateForm()) {
      this.errorMessage = '⚠️ กรุณาตรวจสอบข้อมูลให้ครบถ้วนและถูกต้อง';
      return;
    }

    this.isLoading = true;

    this.auth.register(this.user).subscribe({
      next: (res) => {
        this.isLoading = false;
        if (res.status === 'success') {
          this.successMessage = '🎉 สมัครสมาชิกสำเร็จ! กำลังพาไปหน้าล็อกอิน...';
          this.cdr.detectChanges();
          setTimeout(() => this.router.navigate(['/login']), 1800);
        } else {
          this.errorMessage = '❌ ' + (res.message || 'เกิดข้อผิดพลาด');
        }
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.isLoading = false;
        const detail = err?.error?.detail || '';
        if (detail.includes('อีเมล') || detail.toLowerCase().includes('email')) {
          this.errorMessage = '❌ อีเมลนี้ถูกใช้งานแล้ว กรุณาใช้อีเมลอื่น';
          this.fieldErrors['email'] = 'อีเมลนี้มีผู้ใช้งานแล้ว';
        } else if (detail.includes('ชื่อผู้ใช้') || detail.toLowerCase().includes('u_name') || detail.toLowerCase().includes('username')) {
          this.errorMessage = '❌ ชื่อผู้ใช้นี้ถูกใช้งานแล้ว กรุณาเลือกชื่ออื่น';
          this.fieldErrors['name'] = 'ชื่อผู้ใช้นี้มีผู้ใช้งานแล้ว';
        } else if (err.status === 0) {
          this.errorMessage = '⚠️ ไม่สามารถเชื่อมต่อกับเซิร์ฟเวอร์ได้ กรุณาลองใหม่ภายหลัง';
        } else {
          this.errorMessage = '❌ ' + (detail || 'เกิดข้อผิดพลาด กรุณาลองใหม่');
        }
        this.cdr.detectChanges();
      }
    });
  }
}