import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { ApiService } from '../../services/api';

@Component({
  selector: 'app-admin-products',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './admin-products.html',
  styleUrls: ['./admin-products.scss']
})
export class AdminProductsComponent implements OnInit {
  products: any[] = [];
  totalProducts = 0;
  page = 1;
  readonly pageSize = 20;
  searchQuery = '';
  loadError = false;
  editMode = false;
  editingId: string | null = null;

  // ฟอร์มเดียวใช้ได้ทั้ง เพิ่ม และ แก้ไข
  formProduct = {
    name: '', price: 0, category: 'c01',
    description: '', image: ''
  };

  constructor(private api: ApiService, private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    this.loadProducts();
  }

  get totalPages(): number {
    return Math.max(1, Math.ceil(this.totalProducts / this.pageSize));
  }

  get visibleProducts(): any[] {
    return this.products.slice(0, this.pageSize);
  }

  loadProducts(page = this.page) {
    this.page = page;
    this.loadError = false;
    this.api.getProducts('', this.searchQuery.trim(), this.page, this.pageSize).subscribe({
      next: res => {
        this.products = res.data || [];
        this.totalProducts = res.pagination?.total ?? this.products.length;
        this.cdr.detectChanges();
      },
      error: () => {
        this.products = [];
        this.totalProducts = 0;
        this.loadError = true;
        this.cdr.detectChanges();
      }
    });
  }

  applySearch() {
    this.loadProducts(1);
  }

  // ✅ เพิ่มหรือแก้ไข ขึ้นอยู่กับ editMode
  submitForm() {
    if (!this.formProduct.name || !this.formProduct.price) {
      alert('กรุณากรอกชื่อและราคาสินค้า');
      return;
    }

    const payload = {
      p_name: this.formProduct.name.trim(),
      p_price: Number(this.formProduct.price),
      cid: this.formProduct.category,
      category: this.getCategoryName(this.formProduct.category),
      p_description: this.formProduct.description,
      img_url: this.formProduct.image
    };
    const request = this.editMode && this.editingId
      ? this.api.updateProduct(this.editingId, payload)
      : this.api.createProduct({
          product_id: `admin-${Date.now()}`,
          ...payload
        });

    request.subscribe({
      next: res => {
        if (res.status === 'success') {
          alert(this.editMode ? '✅ แก้ไขสินค้าสำเร็จ' : '✅ เพิ่มสินค้าสำเร็จ');
          this.resetForm();
          this.loadProducts(this.page);
        } else {
          alert('❌ เกิดข้อผิดพลาด: ' + (res.detail || res.message));
        }
      },
      error: err => {
        alert('❌ เกิดข้อผิดพลาด: ' + (err.error?.detail || 'เชื่อมต่อ API ไม่ได้'));
      }
    });
  }

  // ✅ กดปุ่มแก้ไข → โหลดข้อมูลเข้าฟอร์ม
  editProduct(p: any) {
    this.editMode   = true;
    this.editingId  = p.product_id;
    this.formProduct = {
      name:        p.p_name,
      price:       p.p_price,
      category:    p.cid,
      description: p.p_description || '',
      image:       p.img_url || ''
    };
    // เลื่อนขึ้นไปที่ฟอร์ม
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  cancelEdit() {
    this.resetForm();
  }

  deleteProduct(id: string) {
    if (!confirm('⚠️ ยืนยันการลบสินค้านี้?')) return;
    this.api.deleteProduct(id).subscribe({
      next: () => this.loadProducts(this.page),
      error: err => alert('❌ ลบสินค้าไม่สำเร็จ: ' + (err.error?.detail || 'เชื่อมต่อ API ไม่ได้'))
    });
  }

  resetForm() {
    this.editMode  = false;
    this.editingId = null;
    this.formProduct = { name: '', price: 0, category: 'c01', description: '', image: '' };
  }

  // แปลง cid → ชื่อหมวดหมู่
  getCategoryName(cid: string): string {
    const map: Record<string, string> = {
      c01: 'CPU', c02: 'Mainboard', c03: 'GPU',
      c04: 'RAM', c05: 'M.2/SSD',  c06: 'PSU',
      c07: 'Case', c08: 'Liquid Cooler', c09: 'Air Cooler'
    };
    return map[cid] || cid;
  }
}
