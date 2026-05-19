import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../services/auth';
import { Router } from '@angular/router';

@Component({
  selector: 'app-admin-orders',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './admin-orders.html'
})
export class AdminOrdersComponent implements OnInit {
  orders: any[] = [];
  isLoading = true;

  constructor(private http: HttpClient, private auth: AuthService, private router: Router) {}

  ngOnInit() {
    // เช็คสิทธิ์ก่อนว่าใช่ Admin ไหม ถ้าไม่ใช่ให้เตะกลับหน้าแรก
    const user = this.auth.currentUserSubject.value;
    if (!user || user.role !== 'admin') {
      alert('คุณไม่มีสิทธิ์เข้าถึงหน้านี้!');
      this.router.navigate(['/']);
      return;
    }
    
    this.loadOrders();
  }

  loadOrders() {
    this.isLoading = true;
    this.http.get('http://localhost/pc_part/api/admin_orders.php').subscribe({
      next: (res: any) => {
        if(res.status === 'success') {
          this.orders = res.data;
        }
        this.isLoading = false;
      },
      error: () => {
        console.error('โหลดข้อมูลไม่สำเร็จ');
        this.isLoading = false;
      }
    });
  }

  updateStatus(orderId: number, newStatus: string) {
    if(!confirm(`ต้องการเปลี่ยนสถานะเป็น "${newStatus}" ใช่หรือไม่?`)) return;

    this.http.post('http://localhost/pc_part/api/admin_orders.php', { 
      order_id: orderId, 
      status: newStatus 
    }).subscribe({
      next: (res: any) => {
        if(res.status === 'success') {
          this.loadOrders();
        } else {
          alert('เกิดข้อผิดพลาด: ' + res.message);
        }
      }
    });
  }
}