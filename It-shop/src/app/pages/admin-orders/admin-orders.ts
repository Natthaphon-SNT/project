import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-admin-orders',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './admin-orders.html',
  styleUrls: ['./admin-orders.scss']
})
export class AdminOrdersComponent implements OnInit {
  orders: any[] = [];
  filteredOrders: any[] = [];
  isLoading = true;
  searchQuery = '';
  statusFilter = '';
  expandedOrderId: number | null = null;

  message = '';
  messageType: 'success' | 'error' | '' = '';

  private readonly API = 'http://localhost:3000';

  statusOptions = [
    { value: 'pending',   label: '⏳ รอดำเนินการ' },
    { value: 'shipping',  label: '🚚 กำลังจัดส่ง' },
    { value: 'completed', label: '✅ สำเร็จ' },
    { value: 'cancelled', label: '❌ ยกเลิก' },
  ];

  constructor(private http: HttpClient, private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    this.loadOrders();
  }

  private getHeaders(): HttpHeaders {
    const token = localStorage.getItem('lt_token') || '';
    return new HttpHeaders({ Authorization: `Bearer ${token}` });
  }

  loadOrders() {
    this.isLoading = true;
    this.http.get<any>(`${this.API}/api/orders`, { headers: this.getHeaders() }).subscribe({
      next: (res) => {
        this.isLoading = false;
        if (res.status === 'success') {
          this.orders = res.data;
          this.applyFilters();
        }
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.isLoading = false;
        this.showMessage('❌ โหลดข้อมูลไม่ได้: ' + (err.error?.detail || err.message), 'error');
        this.cdr.detectChanges();
      }
    });
  }

  applyFilters() {
    let result = this.orders;
    if (this.searchQuery.trim()) {
      const q = this.searchQuery.toLowerCase();
      result = result.filter(o =>
        String(o.order_id).includes(q) ||
        o.customer_name?.toLowerCase().includes(q) ||
        o.u_name?.toLowerCase().includes(q) ||
        o.phone?.includes(q)
      );
    }
    if (this.statusFilter) {
      result = result.filter(o => o.status === this.statusFilter);
    }
    this.filteredOrders = result;
  }

  toggleExpand(orderId: number) {
    this.expandedOrderId = this.expandedOrderId === orderId ? null : orderId;
  }

  updateStatus(orderId: number, newStatus: string) {
    if (!newStatus) return;
    if (!confirm(`ต้องการเปลี่ยนสถานะเป็น "${newStatus}" ใช่หรือไม่?`)) return;

    this.http.put<any>(
      `${this.API}/api/orders/${orderId}/status`,
      { status: newStatus },
      { headers: this.getHeaders() }
    ).subscribe({
      next: (res) => {
        if (res.status === 'success') {
          this.showMessage(`✅ อัปเดตสถานะ Order #${orderId} สำเร็จ`, 'success');
          this.loadOrders();
        } else {
          this.showMessage('❌ ' + (res.detail || res.message), 'error');
        }
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.showMessage('❌ ' + (err.error?.detail || 'เกิดข้อผิดพลาด'), 'error');
        this.cdr.detectChanges();
      }
    });
  }

  getStatusClass(status: string): string {
    const map: Record<string, string> = {
      pending:   'badge-pending',
      shipping:  'badge-shipping',
      completed: 'badge-completed',
      cancelled: 'badge-cancelled',
    };
    return map[status] || 'badge-pending';
  }

  getStatusLabel(status: string): string {
    const map: Record<string, string> = {
      pending:   '⏳ รอดำเนินการ',
      shipping:  '🚚 กำลังจัดส่ง',
      completed: '✅ สำเร็จ',
      cancelled: '❌ ยกเลิก',
    };
    return map[status] || status;
  }

  getPaymentLabel(method: string): string {
    const map: Record<string, string> = {
      cod:      '💵 เก็บเงินปลายทาง',
      transfer: '🏦 โอนเงิน',
      credit:   '💳 บัตรเครดิต',
    };
    return map[method] || method;
  }

  get totalRevenue(): number {
    return this.orders
      .filter(o => o.status === 'completed')
      .reduce((sum, o) => sum + (o.total_price || 0), 0);
  }

  get pendingCount(): number {
    return this.orders.filter(o => o.status === 'pending').length;
  }

  private showMessage(msg: string, type: 'success' | 'error') {
    this.message = msg;
    this.messageType = type;
    setTimeout(() => {
      this.message = '';
      this.messageType = '';
      this.cdr.detectChanges();
    }, 4000);
  }
}