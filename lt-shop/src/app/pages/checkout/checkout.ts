import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { CartService, CartItem } from '../../services/cart';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-checkout',
  templateUrl: './checkout.html',
  standalone: true,
  imports: [FormsModule, CommonModule]
})
export class CheckoutComponent implements OnInit {
  orderData: {
    total_price: number;
    cart_items: CartItem[];
  } = { total_price: 0, cart_items: [] };

  buildName: string = '';
  buildNotes: string = '';

  constructor(private cartService: CartService, private http: HttpClient, private router: Router, private cdr: ChangeDetectorRef) { }

  ngOnInit() {
  this.cartService.getCartItems().subscribe(items => {
    this.orderData.cart_items = items;
    this.orderData.total_price = items.reduce((s, i) => s + (i.p_price * i.quantity), 0);
    if (items.length === 0) {        // ✅ เช็คข้างใน subscribe
      this.router.navigate(['/cart']);
    }
    this.cdr.detectChanges();
  });
}

  saveBuild() {
    if (!this.buildName) {
      alert('กรุณาตั้งชื่อสเปคของคุณก่อนบันทึกครับ');
      return;
    }

    console.log("Saving Build: ", { name: this.buildName, notes: this.buildNotes, items: this.orderData.cart_items });
    
    alert(`🎉 บันทึกสเปค "${this.buildName}" สำเร็จ!\nระบบได้จำลองการบันทึกข้อมูลเรียบร้อยแล้ว`);
    this.cartService.clearCart();
    this.router.navigate(['/profile']); 
  }

  exportText() {
    let text = `🖥️ สเปคคอมพิวเตอร์: ${this.buildName || 'ยังไม่ตั้งชื่อ'}\n`;
    text += `📝 หมายเหตุ: ${this.buildNotes || '-'}\n`;
    text += `━━━━━━━━━━━━━━━━━━━━━\n`;
    
    this.orderData.cart_items.forEach(item => {
      text += `🔸 ${item.p_name} (x${item.quantity}) - ${(item.p_price * item.quantity).toLocaleString()} ฿\n`;
    });
    
    text += `━━━━━━━━━━━━━━━━━━━━━\n`;
    text += `💰 ราคารวมประเมิน: ${this.orderData.total_price.toLocaleString()} บาท\n`;
    text += `จัดสเปคโดย: IT PC BUILD`;

    navigator.clipboard.writeText(text).then(() => {
      alert('📋 คัดลอกรายละเอียดสเปคลง Clipboard เรียบร้อยแล้ว!\nสามารถนำไปวางในแชทให้ร้านประกอบได้เลย');
    });
  }
}