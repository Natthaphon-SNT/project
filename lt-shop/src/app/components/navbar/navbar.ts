import { Component, OnInit } from '@angular/core';
import { AuthService } from '../../services/auth';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './navbar.html',
  styleUrls: ['./navbar.scss']
})
export class NavbarComponent implements OnInit {
  currentUser: any = null;

  constructor(public auth: AuthService) {}

  ngOnInit() {
    this.auth.currentUserSubject.subscribe(user => {
      this.currentUser = user;
    });
  }

  logout() {
    this.auth.logout();
  }
}