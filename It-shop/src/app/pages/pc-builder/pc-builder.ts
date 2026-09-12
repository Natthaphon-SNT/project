import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule, DecimalPipe } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { AuthService } from '../../services/auth';

export interface Product {
  product_id: string;
  p_name: string;
  p_price: number;
  price_advice: number;
  price_jib: number;
  price_ihavecpu: number;
  url_advice?: string;
  url_jib?: string;
  url_ihavecpu?: string;
  img_url: string;
  p_description: string;
  specs?: string;
  compatibility?: {
    socket?: string;
    ram_support?: string[];
    ddr_gen?: string;
    form_factor?: string;
    supports_ff?: string[];
    interface?: string;
    capacity_gb?: number;
    speed_mhz?: number;
    vram_gb?: number;
    watt?: number;
    tdp?: number;
    recommended_psu_watt?: number;
    power_connectors?: Record<string, number>;
    power_connectors_required?: Record<string, number>;
  };
  category: string;
  cid?: string;
}

export interface BuildSlot {
  key: string;
  label: string;
  icon: string;
  category: string;
  selected: Product | null;
  products: Product[];
  isLoading: boolean;
  showPicker: boolean;
  search: string;
  required: boolean;
}

export interface CompatibilityCheckItem {
  item: string;
  ok: boolean;
  detail: string;
  severity?: 'PASS' | 'WARNING' | 'ERROR' | 'UNKNOWN';
  sources?: {url: string; title: string; field: string; value: number; unit: string; checked_at?: string}[];
}

export interface CompatibilityResult {
  overall: 'ok' | 'warning' | 'error';
  summary: string;
  checks: CompatibilityCheckItem[];
  warnings: string[];
  suggestions: string[];
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
    { key: 'cpu',     label: 'CPU / Processor',  icon: '🔲', category: 'cpu',           selected: null, products: [], isLoading: false, showPicker: false, search: '', required: true },
    { key: 'mb',      label: 'Mainboard',         icon: '🟦', category: 'mainboard',     selected: null, products: [], isLoading: false, showPicker: false, search: '', required: true },
    { key: 'gpu',     label: 'GPU / VGA',         icon: '🎮', category: 'gpu',           selected: null, products: [], isLoading: false, showPicker: false, search: '', required: false },
    { key: 'ram',     label: 'RAM',               icon: '📊', category: 'ram',           selected: null, products: [], isLoading: false, showPicker: false, search: '', required: true },
    { key: 'ssd',     label: 'SSD / M.2',         icon: '💾', category: 'ssd',           selected: null, products: [], isLoading: false, showPicker: false, search: '', required: true },
    { key: 'psu',     label: 'Power Supply',      icon: '⚡', category: 'psu',           selected: null, products: [], isLoading: false, showPicker: false, search: '', required: true },
    { key: 'case',    label: 'Case',              icon: '🖥️', category: 'case',          selected: null, products: [], isLoading: false, showPicker: false, search: '', required: false },
    { key: 'cooler',  label: 'CPU Cooler',        icon: '❄️', category: 'liquid cooler', selected: null, products: [], isLoading: false, showPicker: false, search: '', required: false },
  ];

  toastMessage = '';
  toastType: 'success' | 'error' | '' = '';
  private toastTimer: any;

  compatResult: CompatibilityResult | null = null;
  private compatRequestId = 0;
  isCheckingCompat = false;
  isSaving = false;

  constructor(
    private http: HttpClient,
    public auth: AuthService,
    private router: Router,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit() {
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
        
        // Filter out non-hardware items
        products = products.filter(p => !p.p_name.toLowerCase().includes('vacuum') && !p.p_name.toLowerCase().includes('เครื่องดูดฝุ่น'));

        // สำหรับ cooler รวม air + liquid
        if (slot.key === 'cooler') {
          this.http.get<any>(`${API}/api/products?category=air+cooler`).subscribe({
            next: (res2) => {
              const extra = (res2.status === 'success' ? res2.data : []).filter(
                (p: Product) => !p.p_name.toLowerCase().includes('vacuum') && !p.p_name.toLowerCase().includes('เครื่องดูดฝุ่น')
              );
              slot.products = [...products, ...extra];
              slot.isLoading = false;
              this.cdr.detectChanges();
            },
            error: () => {
              slot.products = products;
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

  filteredProducts(slot: BuildSlot): Product[] {
    const q = slot.search.trim().toLowerCase();
    if (!q) return slot.products;
    return slot.products.filter(p => {
      const searchable = [p.p_name, ...this.getProductMetadata(p, slot)]
        .join(' ')
        .toLowerCase();
      return searchable.includes(q);
    });
  }

  /** Small, searchable facts shown below a product name in the picker. */
  getProductMetadata(product: Product, slot: BuildSlot): string[] {
    const facts = product.compatibility || {};
    const name = (product.p_name || '').toUpperCase();
    const result: string[] = [];
    const add = (value: string | number | undefined | null) => {
      if (value !== undefined && value !== null && String(value).trim()) {
        result.push(String(value));
      }
    };
    const list = (value?: string[]) => value?.filter(Boolean).join('/') || '';

    switch (slot.key) {
      case 'cpu':
        add(facts.socket ? `Socket ${facts.socket}` : undefined);
        break;
      case 'mb':
        add(facts.socket ? `Socket ${facts.socket}` : undefined);
        add(list(facts.ram_support) ? `RAM ${list(facts.ram_support)}` : undefined);
        add(facts.form_factor);
        break;
      case 'ram':
        add(facts.ddr_gen);
        add(facts.capacity_gb ? `${facts.capacity_gb}GB` : undefined);
        add(facts.speed_mhz ? `${facts.speed_mhz}MHz` : undefined);
        break;
      case 'ssd': {
        const storage = (facts.interface || '').toUpperCase();
        const isHdd = /\bHDD\b|HARD\s*DISK/.test(name);
        const isM2 = /M\.2|NVME|M2/.test(name) || storage === 'NVME';
        if (isHdd) add('HDD');
        else if (isM2) add(`M.2${storage ? ` ${storage}` : ''}`);
        else if (storage) add(storage === 'SATA' ? 'SSD SATA' : storage);
        else if (/\bSSD\b|SOLID\s*STATE/.test(name)) add('SSD');
        if (facts.capacity_gb) {
          const capacity = facts.capacity_gb >= 1024
            ? `${Math.round(facts.capacity_gb / 1024)}TB`
            : `${facts.capacity_gb}GB`;
          add(capacity);
        }
        break;
      }
      case 'psu':
        add(facts.watt ? `${facts.watt}W` : undefined);
        break;
      case 'gpu':
        add(facts.vram_gb ? `${facts.vram_gb}GB` : undefined);
        add(facts.recommended_psu_watt ? `PSU ≥${facts.recommended_psu_watt}W` : undefined);
        break;
      case 'case':
        add(facts.form_factor);
        break;
      default:
        break;
    }
    return result;
  }

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
    this.checkCompatibility();
    this.cdr.detectChanges();
  }

  removeProduct(slot: BuildSlot) {
    slot.selected = null;
    this.checkCompatibility();
    this.cdr.detectChanges();
  }

  // ─── Real-time Compatibility Check ───
  checkCompatibility() {
    const requestId = ++this.compatRequestId;
    this.compatResult = null;
    const selected = this.slots.filter(s => s.selected);
    if (selected.length < 2) {
      this.compatResult = null;
      this.isCheckingCompat = false;
      return;
    }

    this.isCheckingCompat = true;
    const parts = selected.map(s => ({
      product_id: s.selected!.product_id,
      category: s.label.includes('CPU') && !s.label.includes('Cooler') ? 'CPU' :
                s.label.includes('Mainboard') ? 'Mainboard' :
                s.label.includes('GPU') ? 'GPU' :
                s.label.includes('RAM') ? 'RAM' :
                s.label.includes('SSD') ? 'SSD' :
                s.label.includes('Power') ? 'PSU' :
                s.label.includes('Case') ? 'Case' :
                s.label.includes('Cooler') ? 'Liquid Cooler' : s.category,
      name: s.selected!.p_name,
      price: this.getMinPrice(s.selected!)
    }));

    this.http.post<any>(`${API}/api/compatibility/check-parts`, { parts }).subscribe({
      next: (res) => {
        if (requestId !== this.compatRequestId) return;
        this.isCheckingCompat = false;
        if (res.status === 'success' && res.data) {
          this.compatResult = res.data;
        }
        this.cdr.detectChanges();
      },
      error: () => {
        if (requestId !== this.compatRequestId) return;
        this.isCheckingCompat = false;
        this.compatResult = {overall: 'warning', summary: 'ตรวจสอบสเปกไม่สำเร็จ กรุณาลองใหม่', checks: [], warnings: [], suggestions: []};
        this.cdr.detectChanges();
      }
    });
  }

  // ─── Price & Store Calculations ───
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

  getStoreTotal(store: 'advice' | 'jib' | 'ihavecpu'): number {
    const key = store === 'advice' ? 'price_advice' : store === 'jib' ? 'price_jib' : 'price_ihavecpu';
    return this.slots
      .filter(s => s.selected && (s.selected[key] || 0) > 0)
      .reduce((sum, s) => sum + (s.selected![key] || 0), 0);
  }

  getStoreAvailableCount(store: 'advice' | 'jib' | 'ihavecpu'): number {
    const key = store === 'advice' ? 'price_advice' : store === 'jib' ? 'price_jib' : 'price_ihavecpu';
    return this.slots.filter(s => s.selected && (s.selected[key] || 0) > 0).length;
  }

  getBestStoreInfo(): { bestStore: string; bestTotal: number; isSingleStore: boolean } {
    const totalCount = this.getSelectedCount();
    if (totalCount === 0) return { bestStore: 'ยังไม่ได้เลือก', bestTotal: 0, isSingleStore: false };

    const advTotal = this.getStoreTotal('advice');
    const advCount = this.getStoreAvailableCount('advice');

    const jibTotal = this.getStoreTotal('jib');
    const jibCount = this.getStoreAvailableCount('jib');

    const ihcTotal = this.getStoreTotal('ihavecpu');
    const ihcCount = this.getStoreAvailableCount('ihavecpu');

    const candidates: Array<{ name: string; total: number; count: number }> = [
      { name: 'Advice', total: advTotal, count: advCount },
      { name: 'JIB', total: jibTotal, count: jibCount },
      { name: 'iHaveCPU', total: ihcTotal, count: ihcCount },
    ];

    // Single store with all parts available
    const fullStores = candidates.filter(c => c.count === totalCount && c.total > 0);
    if (fullStores.length > 0) {
      fullStores.sort((a, b) => a.total - b.total);
      return { bestStore: fullStores[0].name, bestTotal: fullStores[0].total, isSingleStore: true };
    }

    return { bestStore: 'แยกชิ้นราคาต่ำสุด (Mixed Best)', bestTotal: this.getTotalPrice(), isSingleStore: false };
  }

  // ─── Save Build & Navigate to History ───
  saveAndNavigateToHistory() {
    const selected = this.slots.filter(s => s.selected);
    if (selected.length === 0) {
      this.showToast('กรุณาเลือกสินค้าอย่างน้อย 1 ชิ้นก่อนบันทึก', 'error');
      return;
    }

    let uid = '';
    let username = '';
    try {
      const raw = localStorage.getItem('lt_user');
      if (raw) {
        const u = JSON.parse(raw);
        uid = u.uid || u.u_id || u.id || '';
        username = u.u_name || u.username || '';
      }
    } catch {}

    if (!uid) {
      this.showToast('กรุณาเข้าสู่ระบบก่อนบันทึกสเปค', 'error');
      this.router.navigate(['/login']);
      return;
    }

    this.isSaving = true;

    const partsData = selected.map(s => ({
      key: s.key,
      label: s.label,
      name: s.selected!.p_name,
      min_price: this.getMinPrice(s.selected!),
      price_advice: s.selected!.price_advice || 0,
      price_jib: s.selected!.price_jib || 0,
      price_ihavecpu: s.selected!.price_ihavecpu || 0,
      url_advice: s.selected!.url_advice || '',
      url_jib: s.selected!.url_jib || '',
      url_ihavecpu: s.selected!.url_ihavecpu || '',
      img_url: s.selected!.img_url || ''
    }));

    const bestInfo = this.getBestStoreInfo();

    const payload = {
      uid,
      username,
      type: 'manual',
      mode: 'manual',
      title: `จัดสเปกเอง (${this.getTotalPrice().toLocaleString()} ฿)`,
      inputSummary: `${selected.length}/${this.slots.length} ชิ้นส่วน | ราคาเริ่มต้น ${this.getTotalPrice().toLocaleString()} ฿`,
      result_data: JSON.stringify({
        parts: partsData,
        totals: {
          min: this.getTotalPrice(),
          advice: this.getStoreTotal('advice'),
          advice_count: this.getStoreAvailableCount('advice'),
          jib: this.getStoreTotal('jib'),
          jib_count: this.getStoreAvailableCount('jib'),
          ihavecpu: this.getStoreTotal('ihavecpu'),
          ihavecpu_count: this.getStoreAvailableCount('ihavecpu'),
          best_store: bestInfo.bestStore,
          best_total: bestInfo.bestTotal
        },
        compatibility: this.compatResult
      })
    };

    this.http.post<any>(`${API}/api/spec-history`, payload).subscribe({
      next: (res) => {
        this.isSaving = false;
        this.showToast('บันทึกสเปกเรียบร้อยแล้ว กำลังนำท่านไปยังหน้าประวัติ...', 'success');
        setTimeout(() => {
          this.router.navigate(['/history']);
        }, 1000);
      },
      error: () => {
        this.isSaving = false;
        this.showToast('เกิดข้อผิดพลาดในการบันทึกสเปก', 'error');
      }
    });
  }

  clearAll() {
    this.slots.forEach(s => s.selected = null);
    this.compatResult = null;
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
