import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { ApiService } from '../../services/api';
import { CartService } from '../../services/cart';
import { AuthService } from '../../services/auth';

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
  'RAM':           'https://cdn-icons-png.flaticon.com/512/984/984196.png',
  'M.2':           'https://cdn-icons-png.flaticon.com/512/2740/2740832.png',
  'SSD':           'https://cdn-icons-png.flaticon.com/512/2740/2740832.png',
  'PSU':           'https://cdn-icons-png.flaticon.com/512/1048/1048328.png',
  'Case':          'https://cdn-icons-png.flaticon.com/512/3034/3034157.png',
  'Liquid Cooler': 'https://cdn-icons-png.flaticon.com/512/814/814970.png',
  'Air Cooler':    'https://cdn-icons-png.flaticon.com/512/814/814975.png',
  'Mouse':         'https://cdn-icons-png.flaticon.com/512/2948/2948088.png',
  'Keyboard':      'https://cdn-icons-png.flaticon.com/512/2977/2977807.png',
  'Headset':       'https://cdn-icons-png.flaticon.com/512/3074/3074767.png',
  'Microphone':    'https://cdn-icons-png.flaticon.com/512/906/906794.png',
  'Monitor':       'https://cdn-icons-png.flaticon.com/512/2093/2093156.png',
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
  isAdmin = false;

  // Toast notification
  toastMessage = '';
  toastType: 'success' | 'error' | '' = '';
  private toastTimer: any;

  // Modal แก้ไข
  showEditModal = false;
  editingId: string = '';
  editForm = { name: '', price: 0, category: 'c01', description: '', image: '' };
  isSaving = false;

  private readonly API = 'http://localhost:3000';

  constructor(
    private route: ActivatedRoute,
    private api: ApiService,
    private cart: CartService,
    private auth: AuthService,
    private http: HttpClient,
    private cdr: ChangeDetectorRef
  ) {}

  private getHeaders(): HttpHeaders {
    const token = localStorage.getItem('lt_token') || '';
    return new HttpHeaders({ Authorization: `Bearer ${token}` });
  }

  getProductImage(p: Product): string {
    if (p.img_url && p.img_url.startsWith('http')) return p.img_url;
    return CATEGORY_ICONS[p.category] || DEFAULT_ICON;
  }

  getMinPrice(p: Product): number {
    const prices = [p.price_advice, p.price_jib, p.price_ihavecpu, p.p_price].filter(x => x && x > 0);
    return prices.length ? Math.min(...prices) : (p.p_price || 0);
  }

  onImgError(event: Event, p: Product) {
    const img = event.target as HTMLImageElement;
    img.src = CATEGORY_ICONS[p.category] || DEFAULT_ICON;
    img.style.padding = '20px';
    img.style.objectFit = 'contain';
  }

  ngOnInit() {
    const user = this.auth.currentUserSubject.value;
    this.isAdmin = user?.role === 'admin';

    // รับทั้ง route param (category) และ query param (search จาก navbar)
    this.route.paramMap.subscribe(params => {
      this.category = params.get('type') || '';
    });

    this.route.queryParamMap.subscribe(qp => {
      this.searchQuery = qp.get('search') || '';
      this.loadProducts();
    });
  }

  ngOnDestroy() {}

  loadProducts() {
    this.isLoading = true;
    this.api.getProducts(this.category, this.searchQuery).subscribe({
      next: (res) => {
        this.products = res.status === 'success' ? res.data : [];
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.isLoading = false;
        this.showToast('ไม่สามารถโหลดสินค้าได้', 'error');
        this.cdr.detectChanges();
      }
    });
  }

  onSearch() {
    this.category = '';
    this.loadProducts();
  }

  addToCart(product: any) {
    const result = this.cart.addToCart(product);
    this.showToast(result.message, result.success ? 'success' : 'error');
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

  closeModal() {
    this.showEditModal = false;
    this.cdr.detectChanges();
  }
}