import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable } from 'rxjs';
import { Router } from '@angular/router';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private baseUrl = 'http://localhost/pc_part/api';

  // ใช้เก็บข้อมูลผู้ใช้ที่กำลังล็อกอิน
  public currentUserSubject = new BehaviorSubject<any>(null);

  constructor(private http: HttpClient, private router: Router) {
    // โหลดข้อมูลเก่าจาก LocalStorage ถ้าเคยล็อกอินไว้
    const savedUser = localStorage.getItem('lt_user');
    if (savedUser) {
      this.currentUserSubject.next(JSON.parse(savedUser));
    }
  }

  login(credentials: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/login.php`, credentials);
  }

  register(userData: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/register.php`, userData);
  }

  // เซฟข้อมูลเมื่อล็อกอินผ่าน
  saveUser(userData: any) {
    localStorage.setItem('lt_user', JSON.stringify(userData));
    this.currentUserSubject.next(userData);
  }

  // ออกจากระบบ
  logout() {
    localStorage.removeItem('lt_user');
    this.currentUserSubject.next(null);
    this.router.navigate(['/login']);
  }

  // เช็คว่าล็อกอินอยู่ไหม
  isLoggedIn(): boolean {
    return !!this.currentUserSubject.value;
  }
}