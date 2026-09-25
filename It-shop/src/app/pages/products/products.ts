import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { combineLatest, Subscription } from 'rxjs';
import { ApiService } from '../../services/api';
import { AuthService } from '../../services/auth';
import { API_BASE_URL } from '../../services/api-base-url';

interface Product {
  product_id: string;
  p_name: string;
  p_price: number;
  price_advice: number;
  price_jib: number;
  price_ihavecpu: number;
  img_url: string;
  p_description: string;
  category: string;
  cid?: string;
  specs?: string;
}

const CATEGORY_ICONS: Record<string, string> = {
  'CPU':           'https://cdn-icons-png.flaticon.com/512/2991/2991100.png',
  'Mainboard':     'https://cdn-icons-png.flaticon.com/512/2091/2091665.png',
  'GPU':           'https://cdn-icons-png.flaticon.com/512/4429/4429085.png',
  'GPU Accessories': 'https://cdn-icons-png.flaticon.com/512/4429/4429085.png',
  'RAM':           'https://cdn-icons-png.flaticon.com/512/984/984196.png',
  'M.2':           'https://cdn-icons-png.flaticon.com/512/2740/2740832.png',
  'SSD':           'https://cdn-icons-png.flaticon.com/512/2740/2740832.png',
  'HDD':           'https://cdn-icons-png.flaticon.com/512/2740/2740832.png',
  'External Storage': 'https://cdn-icons-png.flaticon.com/512/2740/2740832.png',
  'Storage Accessories': 'https://cdn-icons-png.flaticon.com/512/2740/2740832.png',
  'PSU':           'https://cdn-icons-png.flaticon.com/512/1048/1048328.png',
  'Case':          'https://cdn-icons-png.flaticon.com/512/3034/3034157.png',
  'Case Fan':      'https://cdn-icons-png.flaticon.com/512/814/814975.png',
  'Case Accessories': 'https://cdn-icons-png.flaticon.com/512/3034/3034157.png',
  'Liquid Cooler': 'https://cdn-icons-png.flaticon.com/512/814/814970.png',
  'Air Cooler':    'https://cdn-icons-png.flaticon.com/512/814/814975.png',
  'Cooling Accessories': 'https://cdn-icons-png.flaticon.com/512/814/814975.png',
  'PC Components': 'https://cdn-icons-png.flaticon.com/512/2091/2091665.png',
  'Mouse':         'https://cdn-icons-png.flaticon.com/512/2948/2948088.png',
  'Keyboard':      'https://cdn-icons-png.flaticon.com/512/2977/2977807.png',
  'Keypad':        'https://cdn-icons-png.flaticon.com/512/2977/2977807.png',
  'Graphic Tablet': 'https://cdn-icons-png.flaticon.com/512/2977/2977807.png',
  'Keyboard Accessories': 'https://cdn-icons-png.flaticon.com/512/2977/2977807.png',
  'Headset':       'https://cdn-icons-png.flaticon.com/512/3074/3074767.png',
  'Gaming Headset': 'https://cdn-icons-png.flaticon.com/512/3074/3074767.png',
  'Wireless Headset': 'https://cdn-icons-png.flaticon.com/512/3074/3074767.png',
  'In-Ear Headphone': 'https://cdn-icons-png.flaticon.com/512/3074/3074767.png',
  'True Wireless Earbuds': 'https://cdn-icons-png.flaticon.com/512/3074/3074767.png',
  'Microphone':    'https://cdn-icons-png.flaticon.com/512/906/906794.png',
  'Monitor':       'https://cdn-icons-png.flaticon.com/512/2093/2093156.png',
  'Dual Mode Monitor': 'https://cdn-icons-png.flaticon.com/512/2093/2093156.png',
  'Portable Monitor': 'https://cdn-icons-png.flaticon.com/512/2093/2093156.png',
  'Curved Monitor': 'https://cdn-icons-png.flaticon.com/512/2093/2093156.png',
  'Monitor Accessories': 'https://cdn-icons-png.flaticon.com/512/2093/2093156.png',
  'Gaming Chair':  'https://cdn-icons-png.flaticon.com/512/4099/4099711.png',
  'Gaming Desk':   'https://cdn-icons-png.flaticon.com/512/1034/1034659.png',
};
const DEFAULT_ICON = 'https://cdn-icons-png.flaticon.com/512/2991/2991100.png';

@Component({
  selector: 'app-products',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './products.html',
  styleUrls: ['./products.scss']
})
export class ProductsComponent implements OnInit, OnDestroy {
  products: Product[] = [];
  category: string = '';
  searchQuery: string = '';
  isLoading = true;
  loadError = false;
  page = 1;
  readonly pageSize = 20;
  totalProducts = 0;
  isAdmin = false;

  // Toast notification
  toastMessage = '';
  toastType: 'success' | 'error' | '' = '';
  private toastTimer: any;
  private routeSub?: Subscription;

  // Modal แก้ไข
  showEditModal = false;
  editingId: string = '';
  editForm = { name: '', price: 0, category: 'c01', description: '', image: '' };
  isSaving = false;

  private readonly API = API_BASE_URL;

  constructor(
    private route: ActivatedRoute,
    private api: ApiService,
    private auth: AuthService,
    private http: HttpClient,
    private cdr: ChangeDetectorRef
  ) {}

  private getHeaders(): HttpHeaders {
    const token = localStorage.getItem('lt_token') || '';
    return new HttpHeaders({ Authorization: `Bearer ${token}` });
  }

  private readonly FALLBACK_ICON = 'https://cdn-icons-png.flaticon.com/512/2991/2991100.png';

  getProductImage(p: Product): string {
    return this.api.resolveProductImage(
      p.img_url,
      CATEGORY_ICONS[p.category] || this.FALLBACK_ICON
    );
  }

  getMinPrice(p: Product): number {
    const prices = [p.price_advice, p.price_jib, p.price_ihavecpu, p.p_price].filter(x => x && x > 0);
    return prices.length ? Math.min(...prices) : (p.p_price || 0);
  }

  onImgError(event: Event, p: Product) {
    const img = event.target as HTMLImageElement;
    if (!img.src.includes('flaticon')) {
      img.src = CATEGORY_ICONS[p.category] || this.FALLBACK_ICON;
    }
    img.style.padding = '10px';
    img.style.objectFit = 'contain';
  }

  ngOnInit() {
    const user = this.auth.currentUserSubject.value;
    this.isAdmin = user?.role === 'admin';

    // ใช้ combineLatest เพื่อให้ category และ search ถูก set พร้อมกัน
    // ก่อน loadProducts ถูกเรียก — แก้ bug ที่ category ถูก set ช้ากว่า
    this.routeSub = combineLatest([
      this.route.paramMap,
      this.route.queryParamMap,
    ]).subscribe(([params, qp]) => {
      this.category    = params.get('type') || '';
      this.searchQuery = qp.get('search') || '';
      // Angular reuses this component when navigating between categories.
      // Always reset pagination so a page from the previous category cannot
      // request an out-of-range page and make the new category look empty.
      this.loadProducts(1);
    });
  }

  ngOnDestroy() {
    this.routeSub?.unsubscribe();
    if (this.toastTimer) clearTimeout(this.toastTimer);
  }

  get totalPages(): number {
    return Math.max(1, Math.ceil(this.totalProducts / this.pageSize));
  }

  loadProducts(page = this.page) {
    this.page = page;
    this.isLoading = true;
    this.loadError = false;
    this.api.getProducts(this.category, this.searchQuery, this.page, this.pageSize).subscribe({
      next: (res) => {
        this.products = res.status === 'success' ? res.data : [];
        this.totalProducts = res.pagination?.total ?? this.products.length;
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.isLoading = false;
        this.loadError = true;
        this.products = [];
        this.totalProducts = 0;
        this.showToast('ไม่สามารถโหลดสินค้าได้', 'error');
        this.cdr.detectChanges();
      }
    });
  }

  onSearch() {
    // ไม่ clear category เพื่อให้ค้นหาภายในหมวดหมู่ปัจจุบันได้
    this.loadProducts(1);
  }

  showToast(msg: string, type: 'success' | 'error') {
    this.toastMessage = msg;
    this.toastType = type;
    if (this.toastTimer) clearTimeout(this.toastTimer);
    this.toastTimer = setTimeout(() => {
      this.toastMessage = '';
      this.toastType = '';
      this.cdr.detectChanges();
    }, 3000);
    this.cdr.detectChanges();
  }

  // ===== Admin Functions =====
  editProduct(p: any) {
    this.editingId = p.product_id;
    this.editForm = {
      name:        p.p_name,
      price:       p.p_price,
      category:    p.cid || 'c01',
      description: p.p_description || '',
      image:       p.img_url || ''
    };
    this.showEditModal = true;
    this.cdr.detectChanges();
  }

  saveEdit() {
    if (!this.editForm.name || !this.editForm.price) {
      this.showToast('กรุณากรอกชื่อและราคาสินค้า', 'error');
      return;
    }
    this.isSaving = true;
    this.http.put<any>(
      `${this.API}/api/products/${this.editingId}`,
      {
        p_name:        this.editForm.name,
        p_price:       this.editForm.price,
        cid:           this.editForm.category,
        p_description: this.editForm.description,
        img_url:       this.editForm.image
      },
      { headers: this.getHeaders() }
    ).subscribe({
      next: (res) => {
        this.isSaving = false;
        if (res.status === 'success') {
          this.showToast('แก้ไขสินค้าสำเร็จ', 'success');
          this.closeModal();
          this.loadProducts();
        } else {
          this.showToast(res.message || 'เกิดข้อผิดพลาด', 'error');
        }
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.isSaving = false;
        this.showToast(err?.error?.detail || 'ไม่สามารถแก้ไขสินค้าได้', 'error');
        this.cdr.detectChanges();
      }
    });
  }

  deleteProduct(id: string) {
    if (!confirm('ยืนยันการลบสินค้านี้?')) return;
    this.http.delete<any>(`${this.API}/api/products/${id}`, { headers: this.getHeaders() })
      .subscribe({
        next: (res) => {
          if (res.status === 'success') {
            this.showToast('ลบสินค้าสำเร็จ', 'success');
            this.loadProducts();
          } else {
            this.showToast(res.message || 'เกิดข้อผิดพลาด', 'error');
          }
          this.cdr.detectChanges();
        },
        error: (err) => {
          this.showToast(err?.error?.detail || 'ไม่สามารถลบสินค้าได้', 'error');
          this.cdr.detectChanges();
        }
      });
  }

  getPageNumbers(): number[] {
    const total = this.totalPages;
    if (total <= 7) {
      return Array.from({ length: total }, (_, i) => i + 1);
    }
    const pages: number[] = [];
    const current = this.page;

    pages.push(1);

    if (current > 3) pages.push(-1); // ellipsis

    const start = Math.max(2, current - 1);
    const end = Math.min(total - 1, current + 1);
    for (let i = start; i <= end; i++) pages.push(i);

    if (current < total - 2) pages.push(-1); // ellipsis

    pages.push(total);

    return pages;
  }

  closeModal() {
    this.showEditModal = false;
    this.cdr.detectChanges();
  }
}
