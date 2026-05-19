import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { CartService, CartItem } from '../../services/cart';

@Component({
  selector: 'app-cart',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './cart.html',
  styleUrls: ['./cart.scss']
})
export class CartComponent implements OnInit {
  cartItems: CartItem[] = [];
  totalAmount: number = 0;

  constructor(private cartService: CartService, private cdr: ChangeDetectorRef) { }

  ngOnInit() {
    // โหลดข้อมูลตะกร้ามาแสดง และคอยจับตาดูถ้ามีการเปลี่ยนแปลง
    this.cartService.cartSubject.subscribe(items => {
      this.cartItems = items;
      this.calculateTotal();
      this.cdr.detectChanges();
    });
  }

  calculateTotal() {
    this.totalAmount = this.cartItems.reduce((sum, item) => sum + (Number(item.p_price) * item.quantity), 0);
  }

  increaseQty(item: CartItem) {
    if (item.product_id) {
      this.cartService.updateQuantity(item.product_id, item.quantity + 1);
    }
  }

  decreaseQty(item: CartItem) {
    if (item.product_id && item.quantity > 1) {
      this.cartService.updateQuantity(item.product_id, item.quantity - 1);
    }
  }

  removeItem(id: string | number) {
    if (confirm('ต้องการลบสินค้านี้ใช่หรือไม่?')) {
      this.cartService.removeFromCart(id);
    }
  }

  loadCart() {
    this.cartService.getCartItems().subscribe(items => {
      this.cartItems = items;
      // 🌟 2. เรียกฟังก์ชันคำนวณเงินเมื่อโหลดข้อมูลเสร็จ
      this.calculateTotal();
      this.cdr.detectChanges();
    });
  }
}