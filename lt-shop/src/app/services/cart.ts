import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

export interface CartItem {
  product_id: string | number;
  p_name: string;
  p_price: number;
  quantity: number;
  img_url: string;
  category?: string;
  id?: number; // kept for compatibility if needed
}

@Injectable({ providedIn: 'root' })
export class CartService {
  getCartItems() {
    return this.cartSubject.asObservable();
  }
  // ตัวแปรเก็บข้อมูลตะกร้า
  private cartItems: CartItem[] = [];

  // BehaviorSubject ช่วยกระจายข้อมูลไปยัง Component อื่นๆ (เช่น Navbar ให้ตัวเลขเปลี่ยน)
  public cartSubject = new BehaviorSubject<CartItem[]>([]);

  constructor() {
    // โหลดตะกร้าเดิมจาก LocalStorage (เผื่อผู้ใช้ปิดเว็บแล้วเปิดใหม่)
    const savedCart = localStorage.getItem('lt_cart');
    if (savedCart) {
      try {
        this.cartItems = JSON.parse(savedCart);
        this.cartSubject.next(this.cartItems);
      } catch (e) {
        console.error('Failed to parse cart data from LocalStorage:', e);
        this.cartItems = [];
        localStorage.removeItem('lt_cart');
      }
    }
  }

  addToCart(product: any): { success: boolean, message: string } {
    const productId = product.product_id || product.id;
    const productCategory = (product.category || '').toLowerCase();
    
    // 💡 กฎการตรวจสอบ: ชิ้นส่วนพวกนี้ควรมีแค่ 1 ชิ้นในสเปคคอม 1 เครื่อง
    const singleItemCategories = ['cpu', 'mb', 'gpu', 'case', 'psu'];
    
    // เช็คว่าถ้าหมวดหมู่นี้มีในตะกร้าอยู่แล้ว ห้ามใส่รุ่นอื่นเพิ่ม (ต้องลบของเก่าก่อน)
    if (singleItemCategories.includes(productCategory)) {
       const existingCategory = this.cartItems.find(item => (item.category || '').toLowerCase() === productCategory);
       if (existingCategory && (existingCategory.product_id || existingCategory.id) !== productId) {
          return { 
            success: false, 
            message: `คุณมี ${productCategory.toUpperCase()} ในสเปคอยู่แล้ว!\nกรุณาลบของเดิมออกก่อนหากต้องการเปลี่ยนรุ่นครับ` 
          };
       }
    }

    const existingItem = this.cartItems.find(item => (item.product_id || item.id) === productId);

    if (existingItem) {
      // ถ้าเป็นชิ้นส่วนหลัก ไม่ให้กดบวกจำนวนเพิ่ม
      if (singleItemCategories.includes(productCategory)) {
          return { success: false, message: `คุณได้เลือก ${productCategory.toUpperCase()} ชิ้นนี้ไปแล้วครับ` };
      }
      // ถ้าเป็นพวก RAM หรือพัดลม ให้บวกจำนวนได้
      existingItem.quantity += 1;
    } else {
      const newItem: CartItem = {
        product_id: productId,
        p_name: product.p_name || product.name,
        p_price: Number(product.p_price || product.price),
        img_url: product.img_url || product.image,
        category: productCategory, // เซฟ Category เก็บไว้
        quantity: 1
      };
      this.cartItems.push(newItem);
    }
    
    this.updateCart();
    return { success: true, message: `เพิ่ม ${product.p_name || product.name} ลงในสเปคเรียบร้อย! ➕` };
  }

  removeFromCart(productId: string | number) {
    this.cartItems = this.cartItems.filter(item => (item.product_id || item.id) !== productId);
    this.updateCart();
  }

  updateQuantity(productId: string | number, newQuantity: number) {
    const item = this.cartItems.find(i => (i.product_id || i.id) === productId);
    if (item && newQuantity > 0) {
      item.quantity = newQuantity;
      this.updateCart();
    }
  }

  private updateCart() {
    this.cartSubject.next(this.cartItems);
    localStorage.setItem('lt_cart', JSON.stringify(this.cartItems));
  }

  clearCart() {
    this.cartItems = [];
    this.updateCart();
  }
}