import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { ApiService } from '../../services/api';

type NoticeType = 'success' | 'error';

@Component({
  selector: 'app-admin-products',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './admin-products.html',
  styleUrls: ['./admin-products.scss']
})
export class AdminProductsComponent implements OnInit {
  readonly fallbackImage = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96"%3E%3Crect width="96" height="96" fill="%23f4f4f5"/%3E%3Cpath d="M25 33 48 20l23 13v29L48 76 25 62Z" fill="%2318181b"/%3E%3Cpath d="m25 33 23 14 23-14M48 47v29" fill="none" stroke="%23ef2929" stroke-width="5" stroke-linejoin="round"/%3E%3C/svg%3E';
  products: any[] = [];
  totalProducts = 0;
  page = 1;
  readonly pageSize = 20;
  searchQuery = '';
  loadError = false;
  isLoading = false;
  isSubmitting = false;
  editMode = false;
  editingId: string | null = null;
  notice = '';
  noticeType: NoticeType = 'success';

  formProduct = this.emptyForm();

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
    this.isLoading = true;

    // The admin token is required here. Without it, manually entered products
    // are filtered out because they have no retailer-specific price columns.
    this.api.getAdminProducts('', this.searchQuery.trim(), this.page, this.pageSize).subscribe({
      next: res => {
        this.products = res.data || [];
        this.totalProducts = res.pagination?.total ?? this.products.length;
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.products = [];
        this.totalProducts = 0;
        this.loadError = true;
        this.isLoading = false;
        this.cdr.detectChanges();
      }
    });
  }

  applySearch() {
    this.loadProducts(1);
  }

  clearSearch() {
    this.searchQuery = '';
    this.loadProducts(1);
  }

  submitForm() {
    const productName = this.formProduct.name.trim();
    const price = Number(this.formProduct.price);
    const stock = Number(this.formProduct.stock);

    if (!productName || !Number.isFinite(price) || price <= 0) {
      this.showNotice('กรุณากรอกชื่อสินค้าและราคาที่มากกว่า 0', 'error');
      return;
    }
    if (!Number.isInteger(stock) || stock < 0) {
      this.showNotice('จำนวนสินค้าต้องเป็นเลขจำนวนเต็มตั้งแต่ 0 ขึ้นไป', 'error');
      return;
    }

    const description = this.formProduct.description.trim();
    const payload = {
      p_name: productName,
      p_price: price,
      p_stock: stock,
      cid: this.formProduct.category,
      category: this.getCategoryName(this.formProduct.category),
      p_description: description,
      specs: description,
      img_url: this.formProduct.image.trim()
    };
    const wasEditing = this.editMode;
    const request = wasEditing && this.editingId
      ? this.api.updateProduct(this.editingId, payload)
      : this.api.createProduct({ product_id: `admin-${Date.now()}`, ...payload });

    this.isSubmitting = true;
    this.notice = '';
    request.subscribe({
      next: res => {
        this.isSubmitting = false;
        if (res.status !== 'success') {
          this.showNotice(res.detail || res.message || 'บันทึกสินค้าไม่สำเร็จ', 'error');
          return;
        }

        this.resetForm();
        this.searchQuery = productName;
        this.showNotice(
          wasEditing
            ? `บันทึกการแก้ไข “${productName}” แล้ว`
            : `เพิ่ม “${productName}” แล้ว และแสดงในผลค้นหาด้านล่าง`,
          'success'
        );
        this.loadProducts(1);
      },
      error: err => {
        this.isSubmitting = false;
        this.showNotice(err.error?.detail || 'เชื่อมต่อ API ไม่ได้ กรุณาลองอีกครั้ง', 'error');
        this.cdr.detectChanges();
      }
    });
  }

  editProduct(product: any) {
    this.editMode = true;
    this.editingId = product.product_id;
    this.notice = '';
    this.formProduct = {
      name: product.p_name || '',
      price: Number(product.p_price) || 0,
      stock: Number(product.p_stock) || 0,
      category: product.cid || 'c01',
      description: product.p_description || product.specs || '',
      image: product.img_url || ''
    };
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  cancelEdit() {
    this.resetForm();
    this.notice = '';
  }

  deleteProduct(product: any) {
    if (!confirm(`ยืนยันการลบ “${product.p_name}” หรือไม่?`)) return;

    this.api.deleteProduct(product.product_id).subscribe({
      next: () => {
        this.showNotice(`ลบ “${product.p_name}” แล้ว`, 'success');
        this.loadProducts(this.page);
      },
      error: err => this.showNotice(err.error?.detail || 'ลบสินค้าไม่สำเร็จ', 'error')
    });
  }

  resetForm() {
    this.editMode = false;
    this.editingId = null;
    this.formProduct = this.emptyForm();
  }

  imageFallback(event: Event) {
    const image = event.target as HTMLImageElement;
    image.onerror = null;
    image.src = this.fallbackImage;
  }

  trackProduct(_: number, product: any): string {
    return product.product_id;
  }

  getCategoryName(cid: string): string {
    const map: Record<string, string> = {
      c01: 'CPU', c02: 'Mainboard', c03: 'GPU',
      c04: 'RAM', c05: 'M.2/SSD', c06: 'PSU',
      c07: 'Case', c08: 'Liquid Cooler', c09: 'Air Cooler'
    };
    return map[cid] || cid || 'ไม่ระบุ';
  }

  private emptyForm() {
    return {
      name: '',
      price: 0,
      stock: 1,
      category: 'c01',
      description: '',
      image: ''
    };
  }

  private showNotice(message: string, type: NoticeType) {
    this.notice = message;
    this.noticeType = type;
    this.cdr.detectChanges();
  }
}
