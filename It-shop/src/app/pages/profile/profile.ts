import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { AuthService } from '../../services/auth';
import { API_BASE_URL } from '../../services/api-base-url';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './profile.html',
  styleUrls: ['./profile.scss']
})
export class ProfileComponent implements OnInit {
  currentUser: any = null;
  profileData: any = null;
  isLoading = true;
  loadError = false;
  isEditMode = false;
  isSaving = false;
  isChangingPassword = false;
  uploadingImage = false;

  // ฟอร์มแก้ไขโปรไฟล์
  editForm = {
    u_name: '',
    u_phone: '',
    u_address: ''
  };

  // ฟอร์มเปลี่ยนรหัสผ่าน
  passwordForm = {
    current_password: '',
    new_password: '',
    confirm_password: ''
  };

  showPasswordForm = false;
  message = '';
  messageType: 'success' | 'error' | '' = '';

  private readonly API = API_BASE_URL;

  constructor(
    private http: HttpClient,
    private auth: AuthService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit() {
    this.currentUser = this.auth.currentUserSubject.value;
    if (!this.auth.isLoggedIn()) {
      this.auth.handleUnauthorized('/profile');
      return;
    }
    this.loadProfile();
  }

  private getHeaders(): HttpHeaders {
    const token = this.auth.getToken();
    return new HttpHeaders({ Authorization: `Bearer ${token}` });
  }

  loadProfile() {
    this.isLoading = true;
    this.loadError = false;
    this.http.get<any>(`${this.API}/api/profile`, { headers: this.getHeaders() }).subscribe({
      next: (res) => {
        if (res.status === 'success') {
          this.profileData = res.data;
          this.editForm = {
            u_name:    res.data.u_name    || '',
            u_phone:   res.data.u_phone   || '',
            u_address: res.data.u_address || ''
          };
        }
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        if (err.status === 401) {
          this.auth.handleUnauthorized('/profile');
          return;
        }
        this.isLoading = false;
        this.loadError = true;
        this.profileData = null;
        this.cdr.detectChanges();
      }
    });
  }

  enableEdit() {
    this.isEditMode = true;
    this.editForm = {
      u_name:    this.profileData?.u_name    || '',
      u_phone:   this.profileData?.u_phone   || '',
      u_address: this.profileData?.u_address || ''
    };
  }

  cancelEdit() {
    this.isEditMode = false;
    this.message = '';
    this.messageType = '';
  }

  saveProfile() {
    if (!this.editForm.u_name.trim()) {
      this.showMessage('กรุณากรอกชื่อผู้ใช้', 'error');
      return;
    }
    this.isSaving = true;
    this.http.put<any>(`${this.API}/api/profile`, this.editForm, { headers: this.getHeaders() }).subscribe({
      next: (res) => {
        this.isSaving = false;
        if (res.status === 'success') {
          this.profileData = res.data || { ...this.profileData, ...this.editForm };
          this.isEditMode = false;
          // อัปเดต localStorage
          const saved = JSON.parse(localStorage.getItem('lt_user') || '{}');
          saved.name = res.data?.u_name || this.editForm.u_name;
          localStorage.setItem('lt_user', JSON.stringify(saved));
          this.auth.currentUserSubject.next(saved);
          this.showMessage('✅ อัปเดตโปรไฟล์สำเร็จ!', 'success');
          this.loadProfile();
        } else {
          this.showMessage('❌ ' + (res.detail || res.message || 'เกิดข้อผิดพลาด'), 'error');
        }
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.isSaving = false;
        if (err.status === 401) {
          this.auth.handleUnauthorized('/profile');
          return;
        }
        this.showMessage('❌ ' + (err.error?.detail || 'ไม่สามารถบันทึกได้'), 'error');
        this.cdr.detectChanges();
      }
    });
  }

  changePassword() {
    if (!this.passwordForm.current_password || !this.passwordForm.new_password) {
      this.showMessage('กรุณากรอกข้อมูลให้ครบถ้วน', 'error');
      return;
    }
    if (this.passwordForm.new_password !== this.passwordForm.confirm_password) {
      this.showMessage('รหัสผ่านใหม่ไม่ตรงกัน', 'error');
      return;
    }
    if (this.passwordForm.new_password.length < 6) {
      this.showMessage('รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร', 'error');
      return;
    }
    this.isChangingPassword = true;
    this.http.put<any>(`${this.API}/api/profile/password`, this.passwordForm, { headers: this.getHeaders() }).subscribe({
      next: (res) => {
        this.isChangingPassword = false;
        if (res.status === 'success') {
          if (res.token) this.auth.updateToken(res.token);
          this.showMessage('✅ เปลี่ยนรหัสผ่านสำเร็จ!', 'success');
          this.passwordForm = { current_password: '', new_password: '', confirm_password: '' };
          this.showPasswordForm = false;
        } else {
          this.showMessage('❌ ' + (res.detail || res.message || 'เกิดข้อผิดพลาด'), 'error');
        }
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.isChangingPassword = false;
        if (err.status === 401) {
          this.auth.handleUnauthorized('/profile');
          return;
        }
        this.showMessage('❌ ' + (err.error?.detail || 'รหัสผ่านปัจจุบันไม่ถูกต้อง'), 'error');
        this.cdr.detectChanges();
      }
    });
  }

  onImageUpload(event: Event) {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    this.uploadingImage = true;
    this.http.post<any>(`${this.API}/api/profile/upload-image`, formData, { headers: this.getHeaders() }).subscribe({
      next: (res) => {
        this.uploadingImage = false;
        if (res.status === 'success') {
          this.profileData.u_image = res.image_url;
          this.showMessage('✅ อัปโหลดรูปโปรไฟล์สำเร็จ!', 'success');
        } else {
          this.showMessage('❌ อัปโหลดไม่สำเร็จ', 'error');
        }
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.uploadingImage = false;
        if (err.status === 401) {
          this.auth.handleUnauthorized('/profile');
          return;
        }
        this.showMessage('❌ ' + (err.error?.detail || 'อัปโหลดไม่สำเร็จ'), 'error');
        this.cdr.detectChanges();
      }
    });
  }

  getProfileImage(): string {
    if (this.profileData?.u_image) {
      return `${API_BASE_URL}/${this.profileData.u_image}`;
    }
    return '';
  }

  getStatusClass(status: string): string {
    const map: Record<string, string> = {
      pending: 'status-pending',
      shipping: 'status-shipping',
      completed: 'status-completed',
      cancelled: 'status-cancelled'
    };
    return map[status] || 'status-pending';
  }

  getStatusLabel(status: string): string {
    const map: Record<string, string> = {
      pending: '⏳ รอดำเนินการ',
      shipping: '🚚 กำลังจัดส่ง',
      completed: '✅ สำเร็จ',
      cancelled: '❌ ยกเลิก'
    };
    return map[status] || status;
  }

  private showMessage(msg: string, type: 'success' | 'error') {
    this.message = msg;
    this.messageType = type;
    setTimeout(() => {
      this.message = '';
      this.messageType = '';
      this.cdr.detectChanges();
    }, 4000);
  }

  logout() {
    this.auth.logout();
  }
}
