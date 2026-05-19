import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { ApiService } from '../../services/api';
import { CartService } from '../../services/cart';
import { AuthService } from '../../services/auth';

interface Product {
  product_id: string;
  p_name: string;
  p_price: string;
  img_url: string;
  p_description: string;
  category: string;
  cid?: string;
}

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

  // สำหรับ Modal แก้ไข
  showEditModal = false;
  editingId: string = '';
  editForm = { name: '', price: 0, category: 'c01', description: '', image: '' };

  private adminApi = 'http://localhost/pc_part/api/admin_product_manage.php';
  
  // ✅ WebSocket สำหรับ Price Updates
  private ws: WebSocket | null = null;

  constructor(
    private route: ActivatedRoute,
    private api: ApiService,
    private cart: CartService,
    private auth: AuthService,
    private http: HttpClient,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit() {
    // ✅ เช็คสิทธิ์ admin
    const user = this.auth.currentUserSubject.value;
    this.isAdmin = user?.role === 'admin';

    // ✅ เชื่อมต่อ WebSocket สำหรับ Real-time Price Updates
    this.connectWebSocket();

    this.route.paramMap.subscribe(params => {
      this.category = params.get('type') || '';
      this.loadProducts();
    });
  }

  // ✅ WebSocket Connection
  private connectWebSocket() {
    try {
      // ใช้ 127.0.0.1:8000 (หรือปรับได้ตามต้องการ)
      const wsUrl = 'ws://127.0.0.1:8000/ws/prices';
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('✅ WebSocket Connected: ' + wsUrl);
      };

      this.ws.onmessage = (event) => {
        try {
          const updated = JSON.parse(event.data);
          // อัปเดตราคาสินค้าแบบ Real-time
          this.products = this.products.map(p =>
            p.product_id === updated.id 
              ? { ...p, p_price: updated.price } 
              : p
          );
          this.cdr.detectChanges();
          console.log('💰 ราคา อัปเดต:', updated);
        } catch (e) {
          console.warn('Failed to parse WebSocket message:', e);
        }
      };

      this.ws.onerror = (error) => {
        console.warn('⚠️ WebSocket Error:', error);
      };

      this.ws.onclose = () => {
        console.log('❌ WebSocket disconnected - reconnecting in 3s...');
        // Reconnect after 3 seconds
        setTimeout(() => this.connectWebSocket(), 3000);
      };
    } catch (error) {
      console.warn('❌ WebSocket connection failed:', error);
    }
  }

  // ✅ Cleanup WebSocket when component destroys
  ngOnDestroy() {
    if (this.ws) {
      this.ws.close();
    }
  }

  loadProducts() {
    this.isLoading = true;
    this.api.getProducts(this.category, this.searchQuery).subscribe({
      next: (res) => {
        this.products = res.status === 'success' ? res.data : [];
        this.isLoading = false;
        this.cdr.detectChanges();
        
        // ✅ Subscribe ทุกสินค้าเพื่อรับการอัปเดตราคา
        this.products.forEach(p => {
          this.subscribeToProductPrice(p.p_name);
        });
      },
      error: () => {
        this.isLoading = false;
        this.cdr.detectChanges();
      }
    });
  }

  // ✅ Subscribe ราคาสินค้าเดี่ยว
  private subscribeToProductPrice(productName: string) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        action: 'subscribe',
        product_id: productName
      }));
      console.log(`🔔 Subscribed to: ${productName}`);
    }
  }

  onSearch() {
    this.category = '';
    this.loadProducts();
  }

  addToCart(product: any) {
    const result = this.cart.addToCart(product);
    alert(result.success ? '✅ ' + result.message : '⚠️ ' + result.message);
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
      alert('กรุณากรอกชื่อและราคาสินค้า');
      return;
    }
    this.http.post<any>(this.adminApi, {
      action: 'edit',
      id: this.editingId,
      data: this.editForm
    }).subscribe(res => {
      if (res.status === 'success') {
        alert('✅ แก้ไขสินค้าสำเร็จ');
        this.closeModal();
        this.loadProducts();
      } else {
        alert('❌ ' + res.message);
      }
    });
  }

  deleteProduct(id: string) {
    if (!confirm('⚠️ ยืนยันการลบสินค้านี้?')) return;
    this.http.post<any>(this.adminApi, { action: 'delete', id })
      .subscribe(res => {
        if (res.status === 'success') {
          this.loadProducts();
        } else {
          alert('❌ ' + res.message);
        }
      });
  }

  closeModal() {
    this.showEditModal = false;
    this.cdr.detectChanges();
  }
}