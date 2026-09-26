import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { ProductShowcaseComponent } from '../../components/product-showcase/product-showcase';

@Component({
  selector: 'app-home',
  standalone: true,

  imports: [CommonModule, RouterModule, ProductShowcaseComponent],
  templateUrl: './home.html',
  styleUrls: ['./home.scss']
})
export class Home {
  constructor() {}
}
