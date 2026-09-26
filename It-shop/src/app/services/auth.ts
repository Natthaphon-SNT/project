import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable } from 'rxjs';
import { Router } from '@angular/router';
import { environment } from '../../environments/environment';

@Injectable({ providedIn: 'root' })
export class AuthService {
// FastAPI backend - ไม่ต้องใช้ XAMPP อีกต่อไป
  private baseUrl = environment.apiUrl;

  public currentUserSubject = new BehaviorSubject<any>(null);

  constructor(private http: HttpClient, private router: Router) {
    const savedUser = localStorage.getItem('lt_user');
    const token = localStorage.getItem('lt_token') || '';
    if (savedUser && this.hasUsableToken(token)) {
      try {
        this.currentUserSubject.next(JSON.parse(savedUser));
      } catch {
        this.clearSession();
      }
    } else {
      this.clearSession();
    }
  }

  private hasUsableToken(token: string): boolean {
    try {
      const parts = token.split('.');
      if (parts.length !== 3) return false;
      const encoded = parts[1].replace(/-/g, '+').replace(/_/g, '/');
      const payload = JSON.parse(atob(encoded.padEnd(Math.ceil(encoded.length / 4) * 4, '=')));
      return typeof payload.exp === 'number' && payload.exp * 1000 > Date.now();
    } catch {
      return false;
    }
  }

  private clearSession(): void {
    localStorage.removeItem('lt_user');
    localStorage.removeItem('lt_token');
    this.currentUserSubject.next(null);
  }

  login(credentials: any): Observable<any> {
    // API รับ email หรือ u_name + password หรือ u_password
    const body = {
      email:      credentials.email || credentials.u_name || '',
      u_name:     credentials.email || credentials.u_name || '',
      password:   credentials.password || '',
      u_password: credentials.password || ''
    };
    return this.http.post(`${this.baseUrl}/api/login`, body);
  }

  register(userData: any): Observable<any> {
    // map field ชื่อ frontend -> API schema
    const uid = 'u_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7);
    const body = {
      uid:        uid,
      u_name:     userData.name     || userData.u_name    || '',
      u_email:    userData.email    || userData.u_email   || '',
      u_phone:    userData.phone    || userData.u_phone   || '',
      dob:        userData.dob      || '',
      u_password: userData.password || userData.u_password || '',
      confirm:    userData.confirmPassword || userData.confirm || userData.password || ''
    };
    return this.http.post(`${this.baseUrl}/api/register`, body);
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
  saveUser(userData: any, token: string) {
    if (!this.hasUsableToken(token)) {
      this.clearSession();
      return;
    }
    localStorage.setItem('lt_user', JSON.stringify(userData));
    localStorage.setItem('lt_token', token);
    this.currentUserSubject.next(userData);
  }

  updateToken(token: string): void {
    if (this.hasUsableToken(token)) {
      localStorage.setItem('lt_token', token);
    } else {
      this.handleUnauthorized();
    }
  }

  handleUnauthorized(redirect = this.router.url): void {
    this.clearSession();
    const safeRedirect = redirect.startsWith('/') && !redirect.startsWith('//')
      ? redirect : '/';
    this.router.navigate(['/login'], { queryParams: { redirect: safeRedirect } });
  }

  logout() {
    this.clearSession();
    this.router.navigate(['/login']);
  }

  isLoggedIn(): boolean {
    if (!this.currentUserSubject.value || !this.hasUsableToken(this.getToken())) {
      this.clearSession();
      return false;
    }
    return true;
  }

  getToken(): string {
    return localStorage.getItem('lt_token') || '';
  }
}
