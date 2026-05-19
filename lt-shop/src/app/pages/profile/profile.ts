import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { AuthService } from '../../services/auth';
import { Router } from '@angular/router';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './profile.html'
})
export class ProfileComponent implements OnInit {
  currentUser: any = null;
  myOrders: any[] = [];
  isLoading = true;

  constructor(private http: HttpClient, private auth: AuthService, private router: Router) {}

  ngOnInit() {
    this.currentUser = this.auth.currentUserSubject.value;
    
    // ถ้ายังไม่ล็อกอิน ให้เด้งไปหน้า Login
    if (!this.currentUser) {
      this.router.navigate(['/login']);
      return;
    }

    this.loadMyOrders();
  }

  loadMyOrders() {
    this.isLoading = true;
    // ส่งชื่อผู้ใช้ไปหาประวัติออเดอร์
    this.http.post('http://localhost/pc_part/api/my_orders.php', { 
      user_id: this.currentUser.id 
    }).subscribe({
      next: (res: any) => {
        if (res.status === 'success') {
          this.myOrders = res.data;
        }
        this.isLoading = false;
      },
      error: () => {
        this.isLoading = false;
      }
    });
  }

  logout() {
    this.auth.logout();
  }
}