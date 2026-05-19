import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, interval } from 'rxjs';
import { switchMap } from 'rxjs/operators';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private baseUrl = 'http://localhost/pc_part/api';

  constructor(private http: HttpClient) {}

  getProducts(category: string = '', search: string = ''): Observable<any> {
    let url = `${this.baseUrl}/get_product.php?`;
    if (category) url += `category=${encodeURIComponent(category)}&`;
    if (search)   url += `search=${encodeURIComponent(search)}`;
    return this.http.get(url);
  }

  // ✅ เปลี่ยน id จาก number → string รองรับ product_id แบบ varchar
  getProductDetail(id: string | number): Observable<any> {
    return this.http.get(`${this.baseUrl}/product_detail.php?id=${id}`);
  }

  // 🔄 ดึงข้อมูลสินค้าแบบ live ทุก 30 วินาที
  getProductsLive(category: string = '', search: string = '', interval_ms: number = 30000): Observable<any> {
    return interval(interval_ms).pipe(
      switchMap(() => this.getProducts(category, search))
    );
  }
}