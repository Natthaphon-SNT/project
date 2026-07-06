import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable } from 'rxjs';
import { Router } from '@angular/router';

@Injectable({ providedIn: 'root' })
export class AuthService {
  // ✅ FastAPI backend - ไม่ต้องใช้ XAMPP อีกต่อไป!
  private baseUrl = 'http://localhost:3000';

  public currentUserSubject = new BehaviorSubject<any>(null);

  constructor(private http: HttpClient, private router: Router) {
    const savedUser = localStorage.getItem('lt_user');
    if (savedUser) {
      this.currentUserSubject.next(JSON.parse(savedUser));
    }
  }

  login(credentials: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/api/login`, credentials);
  }

  register(userData: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/api/register`, userData);
  }

  getProfile(): Observable<any> {
    const token = localStorage.getItem('lt_token') || '';
    return this.http.get(`${this.baseUrl}/api/profile`, {
      headers: { Authorization: `Bearer ${token}` }
    });
  }

  updateProfile(data: any): Observable<any> {
    const token = localStorage.getItem('lt_token') || '';
    return this.http.put(`${this.baseUrl}/api/profile`, data, {
      headers: { Authorization: `Bearer ${token}` }
    });
  }

  // เซฟข้อมูลเมื่อล็อกอินผ่าน (เก็บ JWT token ด้วย)
  saveUser(userData: any, token?: string) {
    localStorage.setItem('lt_user', JSON.stringify(userData));
    if (token) localStorage.setItem('lt_token', token);
    this.currentUserSubject.next(userData);
  }

  logout() {
    localStorage.removeItem('lt_user');
    localStorage.removeItem('lt_token');
    this.currentUserSubject.next(null);
    this.router.navigate(['/login']);
  }

  isLoggedIn(): boolean {
    return !!this.currentUserSubject.value;
  }

  getToken(): string {
    return localStorage.getItem('lt_token') || '';
  }
}