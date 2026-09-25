import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable, interval } from 'rxjs';
import { switchMap } from 'rxjs/operators';

@Injectable({ providedIn: 'root' })
export class ApiService {
  // ✅ FastAPI backend
  readonly baseUrl = 'http://localhost:3000';

  constructor(private http: HttpClient) {}

  resolveProductImage(imageUrl = '', fallback = ''): string {
    const raw = imageUrl.trim();
    if (!raw) return fallback;

    // Local assets entered by an admin do not need the retailer proxy.
    if (raw.startsWith('/') || raw.startsWith('assets/')) return raw;

    try {
      const parsed = new URL(raw);
      if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') return fallback;

      const retailerHosts = [
        'jib.co.th',
        'ihavecpu.com',
        'advice.co.th',
        'ihcupload-bkk.s3.ap-southeast-7.amazonaws.com'
      ];
      const hostname = parsed.hostname.toLowerCase();
      const needsProxy = parsed.protocol === 'https:' && retailerHosts.some(host =>
        hostname === host || hostname.endsWith(`.${host}`)
      );

      // Retailer CDNs need the backend cache/proxy. An image URL entered by an
      // admin is loaded directly, matching the behaviour in product management.
      return needsProxy
        ? `${this.baseUrl}/api/image-proxy?url=${encodeURIComponent(raw)}`
        : raw;
    } catch {
      return fallback;
    }
  }

  private authHeaders(): HttpHeaders {
    const token = localStorage.getItem('lt_token') || '';
    return new HttpHeaders({ Authorization: `Bearer ${token}` });
  }

  // Products
  getProducts(category = '', search = '', page = 1, limit = 20): Observable<any> {
    let params = new HttpParams().set('page', page).set('limit', limit);
    if (category) params = params.set('category', category);
    if (search) params = params.set('search', search);
    return this.http.get(`${this.baseUrl}/api/products`, { params });
  }

  getAdminProducts(category = '', search = '', page = 1, limit = 20): Observable<any> {
    let params = new HttpParams().set('page', page).set('limit', limit);
    if (category) params = params.set('category', category);
    if (search) params = params.set('search', search);
    return this.http.get(`${this.baseUrl}/api/products`, {
      params,
      headers: this.authHeaders()
    });
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
    return this.http.get(`${this.baseUrl}/api/spec-history?limit=${limit}`, { headers: this.authHeaders() });
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
