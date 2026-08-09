import { Component, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule, ActivatedRoute } from '@angular/router';
import { AuthService } from '../../services/auth';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './login.html',
  styleUrls: ['./login.scss']
})
export class LoginComponent {
  credentials = { email: '', password: '' };
  isLoading = false;
  errorMessage = '';
  showPassword = false;

  constructor(
    private auth: AuthService,
    private router: Router,
    private route: ActivatedRoute,
    private cdr: ChangeDetectorRef
  ) {}

  togglePassword() {
    this.showPassword = !this.showPassword;
  }

  onLogin() {
    this.errorMessage = '';

    // Validation
    if (!this.credentials.email.trim()) {
      this.errorMessage = '⚠️ กรุณากรอกอีเมลหรือชื่อผู้ใช้';
      return;
    }
    if (!this.credentials.password) {
      this.errorMessage = '⚠️ กรุณากรอกรหัสผ่าน';
      return;
    }

    this.isLoading = true;

    this.auth.login(this.credentials).subscribe({
      next: (res) => {
        this.isLoading = false;
        if (res.status === 'success') {
          this.auth.saveUser(res.user, res.token);
          // Redirect ไปหน้าที่พยายามเข้าก่อนหน้านี้ หรือหน้าแรก
          const redirect = this.route.snapshot.queryParams['redirect'] || '/';
          this.router.navigateByUrl(redirect);
        } else {
          this.errorMessage = '❌ ' + (res.message || 'เกิดข้อผิดพลาด กรุณาลองใหม่');
        }
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.isLoading = false;
        const detail = err?.error?.detail || '';
        if (err.status === 401 || detail.includes('รหัสผ่าน') || detail.includes('ผู้ใช้')) {
          this.errorMessage = '❌ อีเมล/ชื่อผู้ใช้ หรือรหัสผ่านไม่ถูกต้อง';
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