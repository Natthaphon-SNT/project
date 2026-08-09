import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { RouterModule } from '@angular/router';

interface SpecHistoryItem {
  id: number;
  uid: string;
  username: string;
  type: 'ai' | 'manual';
  mode: 'recommend' | 'compare' | 'compat';
  title: string;
  inputSummary: string;
  createdAt: string;
  result_data: any; // parsed JSON
}

@Component({
  selector: 'app-history',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './history.html',
  styleUrls: ['./history.scss']
})
export class HistoryComponent implements OnInit {
  historyList: SpecHistoryItem[] = [];
  isLoading = true;
  expandedId: number | null = null;
  filterMode: 'all' | 'recommend' | 'compare' | 'compat' = 'all';

  private readonly API = 'http://localhost:3000';

  constructor(private http: HttpClient, private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    this.fetchHistory();
  }

  private getHeaders(): HttpHeaders {
    const token = localStorage.getItem('lt_token') || '';
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
    const uid = this.getCurrentUid();
    if (!uid) {
      this.isLoading = false;
      this.cdr.detectChanges();
      return;
    }

    this.http.get<any>(`${this.API}/api/spec-history?uid=${uid}&limit=50`, { headers: this.getHeaders() })
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
                type: item.type || 'ai',
                mode: item.mode || 'recommend',
                title: item.title || '',
                inputSummary: item.inputSummary || '',
                createdAt: item.createdAt || '',
                result_data: parsed
              };
            });
          }
          this.cdr.detectChanges();
        },
        error: () => {
          this.isLoading = false;
          this.cdr.detectChanges();
        }
      });
  }

  deleteItem(id: number) {
    if (!confirm('ยืนยันการลบประวัตินี้?')) return;
    this.http.delete<any>(`${this.API}/api/spec-history/${id}`, { headers: this.getHeaders() })
      .subscribe({
        next: (res) => {
          if (res.status === 'success') {
            this.historyList = this.historyList.filter(h => h.id !== id);
            if (this.expandedId === id) this.expandedId = null;
          }
          this.cdr.detectChanges();
        },
        error: () => {}
      });
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
      recommend: '🤖 แนะนำสเปค',
      compare:   '⚖️ เปรียบเทียบ',
      compat:    '🔗 เช็คความเข้ากัน',
    };
    return map[mode] || mode;
  }

  getModeClass(mode: string): string {
    const map: Record<string, string> = {
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
    if (item.mode === 'recommend' && item.result_data?.parts) {
      return item.result_data.parts;
    }
    return [];
  }

  getCategories(item: SpecHistoryItem): any[] {
    if (item.mode === 'compare' && item.result_data?.categories) {
      return item.result_data.categories;
    }
    return [];
  }

  getChecks(item: SpecHistoryItem): any[] {
    if (item.mode === 'compat' && item.result_data?.checks) {
      return item.result_data.checks;
    }
    return [];
  }

  getTotalBudget(item: SpecHistoryItem): string {
    return item.result_data?.totalBudget || '';
  }

  getSummary(item: SpecHistoryItem): string {
    if (item.mode === 'recommend') return item.result_data?.summary || '';
    if (item.mode === 'compare') return item.result_data?.verdict || '';
    if (item.mode === 'compat') return item.result_data?.summary || '';
    return '';
  }

  getCompatOverall(item: SpecHistoryItem): string {
    return item.result_data?.overall || 'ok';
  }
}