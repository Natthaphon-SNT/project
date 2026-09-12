import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, interval } from 'rxjs';
import { switchMap } from 'rxjs/operators';

@Injectable({ providedIn: 'root' })
export class ApiService {
  // ✅ FastAPI backend
  readonly baseUrl = 'http://localhost:3000';

  constructor(private http: HttpClient) {}

  private authHeaders(): HttpHeaders {
    const token = localStorage.getItem('lt_token') || '';
    return new HttpHeaders({ Authorization: `Bearer ${token}` });
  }

  // Products
  getProducts(category: string = '', search: string = ''): Observable<any> {
    let url = `${this.baseUrl}/api/products?`;
    if (category) url += `category=${encodeURIComponent(category)}&`;
    if (search)   url += `search=${encodeURIComponent(search)}`;
    return this.http.get(url);
  }

  getProductDetail(id: string | number): Observable<any> {
    return this.http.get(`${this.baseUrl}/api/products/${id}`);
  }

  getPriceHistory(id: string | number): Observable<any> {
    return this.http.get(`${this.baseUrl}/api/price-history/${id}`);
  }

  getPromotions(): Observable<any> {
    return this.http.get(`${this.baseUrl}/api/promotions`);
  }

  getCategories(): Observable<any> {
    return this.http.get(`${this.baseUrl}/api/categories`);
  }

  // Admin: Products
  createProduct(data: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/api/products`, data, { headers: this.authHeaders() });
  }
  updateProduct(id: string, data: any): Observable<any> {
    return this.http.put(`${this.baseUrl}/api/products/${id}`, data, { headers: this.authHeaders() });
  }
  deleteProduct(id: string): Observable<any> {
    return this.http.delete(`${this.baseUrl}/api/products/${id}`, { headers: this.authHeaders() });
  }

  // Admin: Promotions
  createPromo(data: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/api/promotions`, data, { headers: this.authHeaders() });
  }
  updatePromo(id: number, data: any): Observable<any> {
    return this.http.put(`${this.baseUrl}/api/promotions/${id}`, data, { headers: this.authHeaders() });
  }
  deletePromo(id: number): Observable<any> {
    return this.http.delete(`${this.baseUrl}/api/promotions/${id}`, { headers: this.authHeaders() });
  }

  // Admin: User Management
  getAdminUsers(): Observable<any> {
    return this.http.get(`${this.baseUrl}/api/admin/users`, { headers: this.authHeaders() });
  }
  getAdminUser(uid: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/api/admin/users/${uid}`, { headers: this.authHeaders() });
  }
  updateAdminUser(uid: string, data: any): Observable<any> {
    return this.http.put(`${this.baseUrl}/api/admin/users/${uid}`, data, { headers: this.authHeaders() });
  }
  deleteAdminUser(uid: string): Observable<any> {
    return this.http.delete(`${this.baseUrl}/api/admin/users/${uid}`, { headers: this.authHeaders() });
  }
  changeUserRole(uid: string, role: string): Observable<any> {
    return this.http.put(`${this.baseUrl}/api/admin/users/${uid}/role`, { role }, { headers: this.authHeaders() });
  }
  getUserSpecs(uid: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/api/admin/users/${uid}/specs`, { headers: this.authHeaders() });
  }
  // AI Recommend
  aiRecommend(prompt: string, mode: string = 'recommend'): Observable<any> {
    return this.http.post(`${this.baseUrl}/api/ai/recommend`, { prompt, mode }, { headers: this.authHeaders() });
  }

  // Spec History
  getSpecHistory(uid: string, limit = 50): Observable<any> {
    return this.http.get(`${this.baseUrl}/api/spec-history?uid=${uid}&limit=${limit}`, { headers: this.authHeaders() });
  }
  getAllSpecHistory(): Observable<any> {
    return this.http.get(`${this.baseUrl}/api/spec-history/all`, { headers: this.authHeaders() });
  }
  saveSpecHistory(data: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/api/spec-history`, data, { headers: this.authHeaders() });
  }
  deleteSpecHistory(id: number): Observable<any> {
    return this.http.delete(`${this.baseUrl}/api/spec-history/${id}`, { headers: this.authHeaders() });
  }

  // 🔄 Live polling
  getProductsLive(category: string = '', search: string = '', interval_ms: number = 30000): Observable<any> {
    return interval(interval_ms).pipe(
      switchMap(() => this.getProducts(category, search))
    );
  }
}
