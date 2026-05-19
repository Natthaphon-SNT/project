import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { ApiService } from '../../services/api';
import { CartService } from '../../services/cart';

@Component({
  selector: 'app-product-detail',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './product-detail.html',
  styleUrls: ['./product-detail.scss']
})
export class ProductDetail implements OnInit {
  product: any = null;
  isLoading = true;

  constructor(
    private route: ActivatedRoute,
    private api: ApiService,
    private cart: CartService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit() {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.api.getProductDetail(id).subscribe({
        next: (res) => {
          if (res.status === 'success') {
            this.product = res.data;
          }
          this.isLoading = false;
          this.cdr.detectChanges();
        },
        error: () => {
          this.isLoading = false;
          this.cdr.detectChanges();
        }
      });
    }
  }

  addToCart() {
    if (this.product) {
      const result = this.cart.addToCart(this.product);
      alert(result.message);
    }
  }
}