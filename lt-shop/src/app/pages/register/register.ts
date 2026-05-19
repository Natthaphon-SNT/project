import { Component } from '@angular/core';
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
  user = { name: '', email: '', phone: '', dob: '', password: '', confirmPassword: '' };
  isLoading = false;
  errorMessage = '';

  constructor(private auth: AuthService, private router: Router) {}

  onRegister() {
    if (!this.user.name || !this.user.email || !this.user.phone || !this.user.dob || !this.user.password || !this.user.confirmPassword) {
      this.errorMessage = 'กรุณากรอกข้อมูลให้ครบถ้วน';
      return;
    }
    if (this.user.password !== this.user.confirmPassword) {
      this.errorMessage = 'รหัสผ่านไม่ตรงกัน';
      return;
    }

    this.isLoading = true;
    this.auth.register(this.user).subscribe({
      next: (res) => {
        if (res.status === 'success') {
          alert('สมัครสมาชิกสำเร็จ! กรุณาเข้าสู่ระบบ');
          this.router.navigate(['/login']);
        } else {
          this.errorMessage = res.message;
        }
        this.isLoading = false;
      },
      error: () => {
        this.errorMessage = 'เชื่อมต่อเซิร์ฟเวอร์ไม่ได้';
        this.isLoading = false;
      }
    });
  }
}