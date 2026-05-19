import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
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

  constructor(private auth: AuthService, private router: Router) {}

  onLogin() {
    if(!this.credentials.email || !this.credentials.password) {
      this.errorMessage = 'กรุณากรอกข้อมูลให้ครบถ้วน';
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';

    this.auth.login(this.credentials).subscribe({
      next: (res) => {
        if(res.status === 'success') {
          this.auth.saveUser(res.user);
          this.router.navigate(['/']); // ล็อกอินเสร็จเด้งไปหน้าแรก
        } else {
          this.errorMessage = res.message;
        }
        this.isLoading = false;
      },
      error: () => {
        this.errorMessage = 'ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้';
        this.isLoading = false;
      }
    });
  }
}