import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-admin-products',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './admin-products.html',
  styleUrls: ['./admin-products.scss']
})
export class AdminProductsComponent implements OnInit {
  products: any[] = [];
  editMode = false;
  editingId: string | null = null;

  // ฟอร์มเดียวใช้ได้ทั้ง เพิ่ม และ แก้ไข
  formProduct = {
    name: '', price: 0, category: 'c01',
    description: '', image: ''
  };

  private api = 'http://localhost/pc_part/api/admin_product_manage.php';

  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.loadProducts();
  }

  loadProducts() {
    this.http.get<any>('http://localhost/pc_part/api/get_product.php')
      .subscribe(res => this.products = res.data || []);
  }

  // ✅ เพิ่มหรือแก้ไข ขึ้นอยู่กับ editMode
  submitForm() {
    if (!this.formProduct.name || !this.formProduct.price) {
      alert('กรุณากรอกชื่อและราคาสินค้า');
      return;
    }

    const action = this.editMode ? 'edit' : 'add';
    const payload: any = { action, data: this.formProduct };
    if (this.editMode) payload.id = this.editingId;

    this.http.post<any>(this.api, payload).subscribe(res => {
      if (res.status === 'success') {
        alert(this.editMode ? '✅ แก้ไขสินค้าสำเร็จ' : '✅ เพิ่มสินค้าสำเร็จ');
        this.resetForm();
        this.loadProducts();
      } else {
        alert('❌ เกิดข้อผิดพลาด: ' + res.message);
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
    this.http.post<any>(this.api, { action: 'delete', id })
      .subscribe(() => this.loadProducts());
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