import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, interval } from 'rxjs';
import { switchMap } from 'rxjs/operators';

@Injectable({ providedIn: 'root' })
export class ApiService {
  // ✅ FastAPI backend - ไม่ต้องใช้ XAMPP อีกต่อไป!
  readonly baseUrl = 'http://localhost:3000';

  constructor(private http: HttpClient) {}

  private authHeaders(): HttpHeaders {
    const token = localStorage.getItem('lt_token') || '';
    return new HttpHeaders({ Authorization: `Bearer ${token}` });
  }

  getProducts(category: string = '', search: string = ''): Observable<any> {
    let url = `${this.baseUrl}/api/products?`;
    if (category) url += `category=${encodeURIComponent(category)}&`;
    if (search)   url += `search=${encodeURIComponent(search)}`;
    return this.http.get(url);
  }

  getProductDetail(id: string | number): Observable<any> {
    return this.http.get(`${this.baseUrl}/api/products/${id}`);
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

  // Orders
  placeOrder(data: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/api/orders`, data);
  }
  getAllOrders(): Observable<any> {
    return this.http.get(`${this.baseUrl}/api/orders`, { headers: this.authHeaders() });
  }
  getOrderDetail(id: number): Observable<any> {
    return this.http.get(`${this.baseUrl}/api/orders/${id}`);
  }
  updateOrderStatus(id: number, status: string): Observable<any> {
    return this.http.put(`${this.baseUrl}/api/orders/${id}/status`, { status }, { headers: this.authHeaders() });
  }

  // 🔄 ดึงข้อมูลสินค้าแบบ live ทุก 30 วินาที
  getProductsLive(category: string = '', search: string = '', interval_ms: number = 30000): Observable<any> {
    return interval(interval_ms).pipe(
      switchMap(() => this.getProducts(category, search))
    );
  }
}