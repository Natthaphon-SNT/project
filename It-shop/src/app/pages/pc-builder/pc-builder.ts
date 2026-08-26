import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule, DecimalPipe } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
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
}

interface BuildSlot {
  key: string;
  label: string;
  icon: string;
  category: string;       // category name to query API
  selected: Product | null;
  products: Product[];
  isLoading: boolean;
  showPicker: boolean;
  search: string;
  required: boolean;
}

const API = 'http://localhost:3000';

@Component({
  selector: 'app-pc-builder',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule, DecimalPipe],
  templateUrl: './pc-builder.html',
  styleUrls: ['./pc-builder.scss']
})
export class PcBuilderComponent implements OnInit {
  slots: BuildSlot[] = [
    { key: 'cpu',     label: 'CPU / Processor',  icon: '🔲', category: 'cpu',          selected: null, products: [], isLoading: false, showPicker: false, search: '', required: true },
    { key: 'mb',      label: 'Mainboard',         icon: '🟦', category: 'mainboard',    selected: null, products: [], isLoading: false, showPicker: false, search: '', required: true },
    { key: 'gpu',     label: 'GPU / VGA',         icon: '🎮', category: 'gpu',          selected: null, products: [], isLoading: false, showPicker: false, search: '', required: false },
    { key: 'ram',     label: 'RAM',               icon: '📊', category: 'ram',          selected: null, products: [], isLoading: false, showPicker: false, search: '', required: true },
    { key: 'ssd',     label: 'SSD / M.2',         icon: '💾', category: 'ssd',          selected: null, products: [], isLoading: false, showPicker: false, search: '', required: true },
    { key: 'psu',     label: 'Power Supply',      icon: '⚡', category: 'psu',          selected: null, products: [], isLoading: false, showPicker: false, search: '', required: true },
    { key: 'case',    label: 'Case',              icon: '🖥️', category: 'case',         selected: null, products: [], isLoading: false, showPicker: false, search: '', required: false },
    { key: 'cooler',  label: 'CPU Cooler',        icon: '❄️', category: 'liquid cooler', selected: null, products: [], isLoading: false, showPicker: false, search: '', required: false },
  ];

  toastMessage = '';
  toastType: 'success' | 'error' | '' = '';
  private toastTimer: any;

  constructor(
    private http: HttpClient,
    private cart: CartService,
    public auth: AuthService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit() {
    // Pre-load สินค้าทุก slot พร้อมกัน
    this.slots.forEach(slot => this.loadSlotProducts(slot));
  }

  // ─── Load products for a slot ───
  loadSlotProducts(slot: BuildSlot, search: string = '') {
    slot.isLoading = true;
    const params: any = { category: slot.category };
    if (search) params['search'] = search;

    const query = new URLSearchParams(params).toString();
    this.http.get<any>(`${API}/api/products?${query}`).subscribe({
      next: (res) => {
        let products: Product[] = res.status === 'success' ? res.data : [];
        // สำหรับ cooler รวม air + liquid
        if (slot.key === 'cooler') {
          // also fetch air cooler
          this.http.get<any>(`${API}/api/products?category=air+cooler`).subscribe({
            next: (res2) => {
              const extra = res2.status === 'success' ? res2.data : [];
              slot.products = [...products, ...extra];
              slot.isLoading = false;
              this.cdr.detectChanges();
            }
          });
          return;
        }
        slot.products = products;
        slot.isLoading = false;
        this.cdr.detectChanges();
      },
      error: () => {
        slot.isLoading = false;
        this.cdr.detectChanges();
      }
    });
  }

  // ─── Filtered products for search ───
  filteredProducts(slot: BuildSlot): Product[] {
    const q = slot.search.trim().toLowerCase();
    if (!q) return slot.products;
    return slot.products.filter(p => p.p_name.toLowerCase().includes(q));
  }

  // ─── Open picker modal ───
  openPicker(slot: BuildSlot) {
    this.slots.forEach(s => s.showPicker = false);
    slot.showPicker = true;
    slot.search = '';
  }

  closePicker(slot: BuildSlot) {
    slot.showPicker = false;
  }

  selectProduct(slot: BuildSlot, product: Product) {
    slot.selected = product;
    slot.showPicker = false;
    this.cdr.detectChanges();
  }

  removeProduct(slot: BuildSlot) {
    slot.selected = null;
    this.cdr.detectChanges();
  }

  // ─── Price helpers ───
  getMinPrice(p: Product): number {
    const prices = [p.price_advice, p.price_jib, p.price_ihavecpu, p.p_price].filter(x => x && x > 0);
    return prices.length ? Math.min(...prices) : (p.p_price || 0);
  }

  getTotalPrice(): number {
    return this.slots
      .filter(s => s.selected)
      .reduce((sum, s) => sum + this.getMinPrice(s.selected!), 0);
  }

  getSelectedCount(): number {
    return this.slots.filter(s => s.selected).length;
  }

  // ─── Add all to cart ───
  addAllToCart() {
    const selected = this.slots.filter(s => s.selected);
    if (selected.length === 0) {
      this.showToast('ยังไม่ได้เลือกสินค้าเลย', 'error');
      return;
    }
    let added = 0;
    for (const slot of selected) {
      const result = this.cart.addToCart(slot.selected!);
      if (result.success) added++;
    }
    this.showToast(`เพิ่ม ${added} ชิ้นลงสเปคสำเร็จ ✓`, 'success');
  }

  clearAll() {
    this.slots.forEach(s => s.selected = null);
    this.cdr.detectChanges();
  }

  getProductImage(p: Product): string {
    if (p.img_url && p.img_url.startsWith('http')) return p.img_url;
    return 'https://cdn-icons-png.flaticon.com/512/2991/2991100.png';
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
}
