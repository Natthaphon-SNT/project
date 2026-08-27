import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule, Location } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { ApiService } from '../../services/api';
import { CartService } from '../../services/cart';

@Component({
  selector: 'app-product-detail',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './product-detail.html',
  styleUrls: ['./product-detail.scss']
})
export class ProductDetail implements OnInit {
  product: any = null;
  isLoading = true;
  activeDescTab: 'advice' | 'jib' | 'ihavecpu' = 'advice';

  // Price history (data freshness / trend)
  priceHistory: any = null;
  sparkPoints = '';
  trendLabel = '';

  constructor(
    private route: ActivatedRoute,
    private api: ApiService,
    private cart: CartService,
    private location: Location,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit() {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.api.getProductDetail(id).subscribe({
        next: (res) => {
          if (res.status === 'success') {
            this.product = res.data;
            // Set default tab to the first available description
            if (this.product.desc_advice)       this.activeDescTab = 'advice';
            else if (this.product.desc_jib)     this.activeDescTab = 'jib';
            else if (this.product.desc_ihavecpu) this.activeDescTab = 'ihavecpu';
          }
          this.isLoading = false;
          this.cdr.detectChanges();
          this.loadPriceHistory(id);
        },
        error: () => {
          this.isLoading = false;
          this.cdr.detectChanges();
        }
      });
    }
  }

  loadPriceHistory(id: string) {
    this.api.getPriceHistory(id).subscribe({
      next: (res) => {
        if (res.status === 'success') {
          this.priceHistory = res.data;
          this.buildSparkline(res.data.history);
        }
        this.cdr.detectChanges();
      },
      error: () => {}
    });
  }

  buildSparkline(history: Record<string, { date: string; price: number }[]>) {
    if (!history) return;
    const points = Object.values(history)
      .flat()
      .sort((a, b) => a.date.localeCompare(b.date))
      .map(p => p.price);
    if (points.length < 2) { this.sparkPoints = ''; return; }
    const w = 260, h = 60, pad = 4;
    const min = Math.min(...points), max = Math.max(...points);
    const range = max - min || 1;
    this.sparkPoints = points.map((p, i) => {
      const x = pad + i * ((w - pad * 2) / (points.length - 1));
      const y = h - pad - ((p - min) / range) * (h - pad * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(' ');
    const change = points[points.length - 1] - points[0];
    this.trendLabel = change < 0
      ? `📉 แนวโน้มราคาลดลง ${Math.abs(change).toLocaleString()}฿`
      : change > 0 ? `📈 แนวโน้มราคาเพิ่มขึ้น ${change.toLocaleString()}฿`
      : '➖ ราคาคงที่';
  }

  formatLastUpdated(ts: string): string {
    if (!ts) return '';
    const d = new Date(ts.replace(' ', 'T'));
    if (isNaN(d.getTime())) return ts;
    return d.toLocaleDateString('th-TH', { day: 'numeric', month: 'short', year: 'numeric' })
      + ' ' + d.toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' }) + ' น.';
  }

  getMinPrice(): number {
    if (!this.product) return 0;
    const prices = [
      this.product.price_advice,
      this.product.price_jib,
      this.product.price_ihavecpu,
      this.product.p_price
    ].filter(x => x && x > 0);
    return prices.length ? Math.min(...prices) : (this.product.p_price || 0);
  }

  hasAnyPrice(): boolean {
    return !!(
      this.product?.price_advice ||
      this.product?.price_jib ||
      this.product?.price_ihavecpu
    );
  }

  hasDescription(): boolean {
    return !!(
      this.product?.desc_advice ||
      this.product?.desc_jib ||
      this.product?.desc_ihavecpu ||
      this.product?.p_description
    );
  }

  /**
   * คืน URL ตรงของสินค้าในแต่ละร้าน
   * ถ้ามี URL ที่ดึงมาจาก scraper → ใช้เลย
   * ถ้าไม่มี → สร้าง search URL fallback
   */
  getStoreUrl(store: 'advice' | 'jib' | 'ihavecpu'): string {
    if (!this.product) return '#';
    const name = encodeURIComponent(this.product.p_name || '');
    switch (store) {
      case 'advice':
        return this.product.url_advice ||
               `https://www.advice.co.th/search?keyword=${name}`;
      case 'jib':
        return this.product.url_jib ||
               `https://www.jib.co.th/web/product/search_product/0?q=${name}`;
      case 'ihavecpu':
        return this.product.url_ihavecpu ||
               `https://www.ihavecpu.com/search?keyword=${name}`;
    }
  }

  private readonly PROXY = 'http://localhost:3000/api/image-proxy?url=';
  private readonly FALLBACK = 'https://cdn-icons-png.flaticon.com/512/2991/2991100.png';

  getProductImage(): string {
    const raw = this.product?.img_url || '';
    if (raw && raw.startsWith('http')) {
      return this.PROXY + encodeURIComponent(raw);
    }
    return this.FALLBACK;
  }

  onImgError(event: Event) {
    const img = event.target as HTMLImageElement;
    // ถ้า proxy ล้มเหลว ให้ fallback icon
    if (!img.src.includes('flaticon')) {
      img.src = this.FALLBACK;
    }
    img.style.padding = '20px';
    img.style.objectFit = 'contain';
  }

  addToCart() {
    if (this.product) {
      const result = this.cart.addToCart(this.product);
      alert(result.message);
    }
  }

  goBack() {
    this.location.back();
  }
}