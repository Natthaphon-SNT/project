import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-admin-users',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './admin-users.html',
  styleUrls: ['./admin-users.scss']
})
export class AdminUsersComponent implements OnInit {
  users: any[] = [];
  filteredUsers: any[] = [];
  isLoading = true;
  searchQuery = '';
  roleFilter = '';

  // Selected user detail panel
  selectedUser: any = null;
  userSpecs: any[] = [];
  activeDetailTab: 'info' | 'specs' = 'info';
  isLoadingDetail = false;

  // Edit modal
  showEditModal = false;
  editForm: any = {};
  isSaving = false;

  // Role change
  showRoleModal = false;
  roleForm = { role: '' };

  message = '';
  messageType: 'success' | 'error' | '' = '';

  private readonly API = 'http://localhost:3000';

  get adminCount(): number {
    return this.users.filter(u => u.u_role === 'admin').length;
  }

  constructor(private http: HttpClient, private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    this.loadUsers();
  }

  private getHeaders(): HttpHeaders {
    const token = localStorage.getItem('lt_token') || '';
    return new HttpHeaders({ Authorization: `Bearer ${token}` });
  }

  loadUsers() {
    this.isLoading = true;
    this.http.get<any>(`${this.API}/api/admin/users`, { headers: this.getHeaders() }).subscribe({
      next: (res) => {
        this.isLoading = false;
        if (res.status === 'success') {
          this.users = res.data;
          this.applyFilters();
        }
        this.cdr.detectChanges();
      },
      error: () => {
        this.isLoading = false;
        this.cdr.detectChanges();
      }
    });
  }

  applyFilters() {
    let result = this.users;
    if (this.searchQuery.trim()) {
      const q = this.searchQuery.toLowerCase();
      result = result.filter(u =>
        u.u_name?.toLowerCase().includes(q) ||
        u.u_email?.toLowerCase().includes(q) ||
        u.uid?.toLowerCase().includes(q)
      );
    }
    if (this.roleFilter) {
      result = result.filter(u => u.u_role === this.roleFilter);
    }
    this.filteredUsers = result;
  }

  selectUser(user: any) {
    this.selectedUser = user;
    this.activeDetailTab = 'info';
    this.userSpecs = [];
    this.loadUserSpecs(user.uid);
  }

  loadUserSpecs(uid: string) {
    this.http.get<any>(`${this.API}/api/admin/users/${uid}/specs`, { headers: this.getHeaders() }).subscribe({
      next: (res) => {
        if (res.status === 'success') this.userSpecs = res.data;
        this.cdr.detectChanges();
      }
    });
  }

  openEditModal(user: any) {
    this.editForm = {
      u_name:    user.u_name || '',
      u_email:   user.u_email || '',
      u_phone:   user.u_phone || '',
      u_address: user.u_address || '',
      u_role:    user.u_role || 'customer',
    };
    this.showEditModal = true;
  }

  saveEdit() {
    if (!this.editForm.u_name || !this.editForm.u_email) {
      this.showMessage('กรุณากรอกชื่อและอีเมล', 'error');
      return;
    }
    this.isSaving = true;
    this.http.put<any>(
      `${this.API}/api/admin/users/${this.selectedUser.uid}`,
      this.editForm,
      { headers: this.getHeaders() }
    ).subscribe({
      next: (res) => {
        this.isSaving = false;
        this.showEditModal = false;
        if (res.status === 'success') {
          this.showMessage('✅ แก้ไขข้อมูลสำเร็จ', 'success');
          this.loadUsers();
        } else {
          this.showMessage('❌ ' + (res.detail || res.message), 'error');
        }
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.isSaving = false;
        this.showMessage('❌ ' + (err.error?.detail || 'เกิดข้อผิดพลาด'), 'error');
        this.cdr.detectChanges();
      }
    });
  }

  openRoleModal(user: any) {
    this.roleForm.role = user.u_role;
    this.showRoleModal = true;
  }

  saveRole() {
    this.http.put<any>(
      `${this.API}/api/admin/users/${this.selectedUser.uid}/role`,
      this.roleForm,
      { headers: this.getHeaders() }
    ).subscribe({
      next: (res) => {
        this.showRoleModal = false;
        if (res.status === 'success') {
          this.showMessage(`✅ เปลี่ยน role เป็น "${this.roleForm.role}" สำเร็จ`, 'success');
          this.loadUsers();
          this.selectedUser.u_role = this.roleForm.role;
        } else {
          this.showMessage('❌ ' + (res.detail || res.message), 'error');
        }
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.showRoleModal = false;
        this.showMessage('❌ ' + (err.error?.detail || 'เกิดข้อผิดพลาด'), 'error');
        this.cdr.detectChanges();
      }
    });
  }

  deleteUser(user: any) {
    if (!confirm(`⚠️ ยืนยันการลบบัญชี "${user.u_name}"?\nการลบนี้ไม่สามารถย้อนกลับได้`)) return;
    this.http.delete<any>(`${this.API}/api/admin/users/${user.uid}`, { headers: this.getHeaders() }).subscribe({
      next: (res) => {
        if (res.status === 'success') {
          this.showMessage(`✅ ลบบัญชี "${user.u_name}" สำเร็จ`, 'success');
          if (this.selectedUser?.uid === user.uid) this.selectedUser = null;
          this.loadUsers();
        } else {
          this.showMessage('❌ ' + (res.detail || res.message), 'error');
        }
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.showMessage('❌ ' + (err.error?.detail || 'เกิดข้อผิดพลาด'), 'error');
        this.cdr.detectChanges();
      }
    });
  }

  getAvatarLetter(name: string): string {
    return name?.charAt(0)?.toUpperCase() || '?';
  }

  getRoleClass(role: string): string {
    const map: Record<string, string> = {
      admin: 'role-admin',
      staff: 'role-staff',
      customer: 'role-customer'
    };
    return map[role] || 'role-customer';
  }

  getModeIcon(mode: string): string {
    const map: Record<string, string> = { recommend: '🤖', compare: '⚖️', compat: '🔗' };
    return map[mode] || '📋';
  }

  private showMessage(msg: string, type: 'success' | 'error') {
    this.message = msg;
    this.messageType = type;
    setTimeout(() => { this.message = ''; this.messageType = ''; this.cdr.detectChanges(); }, 4000);
  }
}
