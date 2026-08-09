import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router'; // 🌟 1. นำเข้า RouterModule ตรงนี้

@Component({
  selector: 'app-home',
  standalone: true,

  imports: [CommonModule, RouterModule], 
  templateUrl: './home.html',
  styleUrls: ['./home.scss']
})
export class Home {
  constructor() {}
}