import { Component, OnInit } from '@angular/core';
import { AuthService } from '../../services/auth';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './navbar.html',
  styleUrls: ['./navbar.scss']
})
export class NavbarComponent implements OnInit {
  currentUser: any = null;
  searchQuery: string = '';

  constructor(public auth: AuthService, private router: Router) {}

  ngOnInit() {
    this.auth.currentUserSubject.subscribe(user => {
      this.currentUser = user;
    });
  }

  logout() {
    this.auth.logout();
  }

  onSearch() {
    const q = this.searchQuery.trim();
    if (q) {
      this.router.navigate(['/products'], { queryParams: { search: q } });
    } else {
      this.router.navigate(['/products']);
    }
  }
}