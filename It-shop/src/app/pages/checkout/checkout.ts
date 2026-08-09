import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Router, RouterModule } from '@angular/router';
import { CartService, CartItem } from '../../services/cart';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-checkout',
  templateUrl: './checkout.html',
  styleUrls: ['./checkout.scss'],
  standalone: true,
  imports: [FormsModule, CommonModule, RouterModule]
})
export class CheckoutComponent implements OnInit {
  cartItems: CartItem[] = [];
  totalPrice = 0;

  // Customer Info Form
  customerForm = {
    name: '',
    phone: '',
    address: '',
    payment_method: 'cod'
  };

  isSubmitting = false;
  message = '';
  messageType: 'success' | 'error' | '' = '';
  orderSuccess = false;
  orderId: number | null = null;

  paymentOptions = [
    { value: 'cod',      label: '💵 เก็บเงินปลายทาง (COD)' },
    { value: 'transfer', label: '🏦 โอนเงินผ่านธนาคาร' },
    { value: 'credit',   label: '💳 บัตรเครดิต / เดบิต' },
  ];

  private readonly API = 'http://localhost:3000';

  constructor(
    private cartService: CartService,
    private http: HttpClient,
    private router: Router,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit() {
    this.cartService.getCartItems().subscribe(items => {
      this.cartItems = items;
      this.totalPrice = items.reduce((s, i) => s + (i.p_price * i.quantity), 0);
      if (items.length === 0 && !this.orderSuccess) {
        this.router.navigate(['/cart']);
      }
      this.cdr.detectChanges();
    });

    // Pre-fill from saved profile
    try {
      const raw = localStorage.getItem('lt_user');
      if (raw) {
        const u = JSON.parse(raw);
        this.customerForm.name = u.name || u.u_name || '';
      }
    } catch {}
  }

  private getHeaders(): HttpHeaders {
    const token = localStorage.getItem('lt_token') || '';
    return new HttpHeaders({ Authorization: `Bearer ${token}` });
  }

  private getCurrentUid(): string | null {
    try {
      const raw = localStorage.getItem('lt_user');
      if (raw) {
        const u = JSON.parse(raw);
        return u.uid || u.u_id || u.id || null;
      }
    } catch {}
    return null;
  }

  placeOrder() {
    if (!this.customerForm.name.trim()) {
      this.showMessage('กรุณากรอกชื่อ-นามสกุล', 'error');
      return;
    }
    if (!this.customerForm.phone.trim()) {
      this.showMessage('กรุณากรอกเบอร์โทรศัพท์', 'error');
      return;
    }
    if (!this.customerForm.address.trim()) {
      this.showMessage('กรุณากรอกที่อยู่จัดส่ง', 'error');
      return;
    }

    this.isSubmitting = true;
    const payload = {
      uid: this.getCurrentUid(),
      customer: {
        name: this.customerForm.name,
        phone: this.customerForm.phone,
        address: this.customerForm.address,
      },
      items: this.cartItems.map(item => ({
        product_id: item.product_id,
        p_name: item.p_name,
        quantity: item.quantity,
        price: item.p_price,
      })),
      total_price: this.totalPrice,
      payment_method: this.customerForm.payment_method,
    };

    this.http.post<any>(`${this.API}/api/orders`, payload, { headers: this.getHeaders() }).subscribe({
      next: (res) => {
        this.isSubmitting = false;
        if (res.status === 'success') {
          this.orderId = res.order_id;
          this.orderSuccess = true;
          this.cartService.clearCart();
        } else {
          this.showMessage('❌ เกิดข้อผิดพลาด: ' + (res.message || ''), 'error');
        }
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.isSubmitting = false;
        this.showMessage('❌ ' + (err.error?.detail || 'ไม่สามารถสั่งซื้อได้ กรุณาลองใหม่'), 'error');
        this.cdr.detectChanges();
      }
    });
  }

  exportText() {
    let text = `🖥️ รายการสั่งซื้อ IT-RECOMMEND\n`;
    text += `━━━━━━━━━━━━━━━━━━━━━━━━\n`;
    text += `👤 ชื่อ: ${this.customerForm.name}\n`;
    text += `📱 เบอร์: ${this.customerForm.phone}\n`;
    text += `📦 ที่อยู่: ${this.customerForm.address}\n`;
    text += `💳 ชำระ: ${this.customerForm.payment_method}\n`;
    text += `━━━━━━━━━━━━━━━━━━━━━━━━\n`;
    this.cartItems.forEach(item => {
      text += `🔸 ${item.p_name} (x${item.quantity}) — ${(item.p_price * item.quantity).toLocaleString()} ฿\n`;
    });
    text += `━━━━━━━━━━━━━━━━━━━━━━━━\n`;
    text += `💰 ยอดรวม: ${this.totalPrice.toLocaleString()} บาท\n`;
    text += `จัดสเปคโดย IT-RECOMMEND`;

    navigator.clipboard.writeText(text).then(() => {
      this.showMessage('📋 คัดลอกรายละเอียดสำเร็จ!', 'success');
    });
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