import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule, DecimalPipe } from '@angular/common';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { RouterModule } from '@angular/router';
import { finalize } from 'rxjs/operators';
import { AuthService } from '../../services/auth';
import { API_BASE_URL } from '../../services/api-base-url';
import { stripEmojiDeep } from '../../utils/strip-emoji';

export interface SpecHistoryItem {
  id: number;
  uid: string;
  username: string;
  type: 'ai' | 'manual';
  mode: 'recommend' | 'compare' | 'compat' | 'manual';
  title: string;
  inputSummary: string;
  createdAt: string;
  result_data: any;
}

interface HistoryShop {
  key: 'advice' | 'jib' | 'ihavecpu';
  label: string;
}

@Component({
  selector: 'app-history',
  standalone: true,
  imports: [CommonModule, RouterModule, DecimalPipe],
  templateUrl: './history.html',
  styleUrls: ['./history.scss']
})
export class HistoryComponent implements OnInit {
  historyList: SpecHistoryItem[] = [];
  isLoading = true;
  loadError = false;
  expandedId: number | null = null;
  filterMode: 'all' | 'manual' | 'recommend' | 'compare' | 'compat' = 'all';
  /** Ids with a DELETE in flight. Guards against duplicate clicks. */
  readonly deletingIds = new Set<number>();

  readonly shops: HistoryShop[] = [
    { key: 'advice', label: 'Advice' },
    { key: 'jib', label: 'JIB' },
    { key: 'ihavecpu', label: 'iHaveCPU' },
  ];

  private readonly API = API_BASE_URL;

  constructor(private http: HttpClient, private cdr: ChangeDetectorRef,
              private auth: AuthService) {}

  ngOnInit() {
    this.fetchHistory();
  }

  private getHeaders(): HttpHeaders {
    const token = this.auth.getToken();
    return new HttpHeaders({ Authorization: `Bearer ${token}` });
  }

  private getCurrentUid(): string {
    try {
      const raw = localStorage.getItem('lt_user');
      if (raw) {
        const u = JSON.parse(raw);
        return u.uid || u.u_id || u.id || '';
      }
    } catch {}
    return '';
  }

  fetchHistory() {
    this.isLoading = true;
    this.loadError = false;
    const uid = this.getCurrentUid();
    if (!uid) {
      this.isLoading = false;
      this.cdr.detectChanges();
      return;
    }

    this.http.get<any>(`${this.API}/api/spec-history?limit=50`, { headers: this.getHeaders() })
      .subscribe({
        next: (res) => {
          this.isLoading = false;
          if (res.status === 'success') {
            this.historyList = res.data.map((item: any) => {
              let parsed: any = {};
              try {
                parsed = typeof item.result_data === 'string'
                  ? JSON.parse(item.result_data)
                  : item.result_data;
              } catch {}
              return {
                id: item.id,
                uid: item.uid,
                username: item.username,
                type: item.type || 'manual',
                mode: item.mode || 'manual',
                title: item.title || '',
                inputSummary: item.inputSummary || '',
                createdAt: item.createdAt || '',
                result_data: stripEmojiDeep(parsed)
              };
            });
            // Automatically expand the first (latest) item if present
            if (this.historyList.length > 0) {
              this.expandedId = this.historyList[0].id;
            }
          }
          this.cdr.detectChanges();
        },
        error: (err) => {
          if (err.status === 401) {
            this.auth.handleUnauthorized('/history');
            return;
          }
          this.isLoading = false;
          this.loadError = true;
          this.historyList = [];
          this.cdr.detectChanges();
        }
      });
  }

  deleteItem(id: number) {
    // Second click while the first DELETE is still open: drop it. Without this
    // the row stays rendered (and clickable) until the response arrives, so
    // every extra click fired another independent request for the same id.
    if (this.deletingIds.has(id)) return;
    if (!confirm('ยืนยันการลบประวัตินี้?')) return;

    this.deletingIds.add(id);
    this.cdr.detectChanges();

    this.http.delete<any>(`${this.API}/api/spec-history/${id}`, { headers: this.getHeaders() })
      .pipe(
        // Runs on success, error and unsubscribe, so the button can never get
        // stuck disabled if the request fails.
        finalize(() => {
          this.deletingIds.delete(id);
          this.cdr.detectChanges();
        })
      )
      .subscribe({
        next: (res) => {
          if (res.status === 'success') {
            this.historyList = this.historyList.filter(h => h.id !== id);
            if (this.expandedId === id) this.expandedId = null;
          }
          this.cdr.detectChanges();
        },
        error: (err) => {
          if (err.status === 401) this.auth.handleUnauthorized('/history');
        }
      });
  }

  isDeleting(id: number): boolean {
    return this.deletingIds.has(id);
  }

  toggleExpand(id: number) {
    this.expandedId = this.expandedId === id ? null : id;
  }

  get filteredHistory(): SpecHistoryItem[] {
    if (this.filterMode === 'all') return this.historyList;
    return this.historyList.filter(h => h.mode === this.filterMode);
  }

  getModeLabel(mode: string): string {
    const map: Record<string, string> = {
      manual:    'จัดสเปกเอง',
      recommend: 'แนะนำสเปค',
      compare:   'เปรียบเทียบ',
      compat:    'เช็คความเข้ากัน',
    };
    return map[mode] || mode;
  }

  partIcon(type: string): string {
    const name = (type || '').toLowerCase();
    if (/cpu|processor/.test(name)) return 'cpu';
    if (/mainboard|motherboard/.test(name)) return 'motherboard';
    if (/gpu|vga|graphics/.test(name)) return 'gpu';
    if (/ram|memory/.test(name)) return 'ram';
    if (/ssd|hdd|storage|m\.2/.test(name)) return 'storage';
    if (/psu|power/.test(name)) return 'power';
    if (/cooler|cooling|fan/.test(name)) return 'cooler';
    if (/case/.test(name)) return 'case';
    return 'package';
  }

  getModeClass(mode: string): string {
    const map: Record<string, string> = {
      manual:    'mode-manual',
      recommend: 'mode-recommend',
      compare:   'mode-compare',
      compat:    'mode-compat',
    };
    return map[mode] || '';
  }

  formatDate(iso: string): string {
    try {
      const d = new Date(iso);
      return d.toLocaleDateString('th-TH', {
        day: '2-digit', month: 'short', year: 'numeric',
        hour: '2-digit', minute: '2-digit'
      });
    } catch { return iso; }
  }

  getParts(item: SpecHistoryItem): any[] {
    if (item.result_data?.parts) {
      return item.result_data.parts;
    }
    return [];
  }

  getPartShopUrl(part: any, shop: HistoryShop): string {
    return part.shop_urls?.[shop.key] || '';
  }

  getPartShopPrice(part: any, shopKey: string): number {
    return Number(part.shop_prices?.[shopKey] || 0);
  }

  getCategories(item: SpecHistoryItem): any[] {
    if (item.mode === 'compare' && item.result_data?.categories) {
      return item.result_data.categories;
    }
    return [];
  }

  getChecks(item: SpecHistoryItem): any[] {
    if (item.result_data?.compatibility?.checks) {
      return item.result_data.compatibility.checks;
    }
    if (item.mode === 'compat' && item.result_data?.checks) {
      return item.result_data.checks;
    }
    return [];
  }

  getTotalBudget(item: SpecHistoryItem): string {
    if (item.mode === 'manual') {
      const total = item.result_data?.totals?.min || 0;
      return total > 0 ? `${total.toLocaleString()} ฿` : '';
    }
    return item.result_data?.totalBudget || '';
  }

  getSummary(item: SpecHistoryItem): string {
    if (item.mode === 'manual') return item.result_data?.compatibility?.summary || '';
    if (item.mode === 'recommend') return item.result_data?.summary || '';
    if (item.mode === 'compare') return item.result_data?.verdict || '';
    if (item.mode === 'compat') return item.result_data?.summary || '';
    return '';
  }

  getCompatOverall(item: SpecHistoryItem): string {
    if (item.mode === 'manual') {
      return item.result_data?.compatibility?.overall || 'ok';
    }
    return item.result_data?.overall || 'ok';
  }

  openUrl(url?: string) {
    if (url) {
      window.open(url, '_blank');
    }
  }
}
