import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';

import { AdminProductsComponent } from './admin-products';

describe('AdminProducts', () => {
  let component: AdminProductsComponent;
  let fixture: ComponentFixture<AdminProductsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AdminProductsComponent],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()]
    })
    .compileComponents();

    fixture = TestBed.createComponent(AdminProductsComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('renders at most one server-sized page', () => {
    component.products = Array.from({ length: 2700 }, (_, index) => ({ product_id: index }));
    expect(component.visibleProducts.length).toBe(20);
  });
});
