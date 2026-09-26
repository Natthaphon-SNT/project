import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { vi } from 'vitest';
import { ApiService } from '../../services/api';

import { ProductsComponent } from './products';

describe('ProductsComponent', () => {
  let component: ProductsComponent;
  let fixture: ComponentFixture<ProductsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ProductsComponent],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()]
    })
      .compileComponents();

    fixture = TestBed.createComponent(ProductsComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('loads store-specific brands and filters results on the server', () => {
    const api = TestBed.inject(ApiService);
    const brands = vi.spyOn(api, 'getProductFilters').mockReturnValue(of({
      status: 'success', data: { brands: ['LOGITECH', 'RAZER'] }
    }));
    const products = vi.spyOn(api, 'getProducts').mockReturnValue(of({
      status: 'success', data: [], pagination: { total: 0 }
    }));
    component.category = 'mouse';
    component.selectedStore = 'jib';
    component.onStoreChange();
    expect(brands).toHaveBeenCalledWith('mouse', '', 'jib');
    expect(component.availableBrands).toEqual(['LOGITECH', 'RAZER']);
    component.selectedBrand = 'LOGITECH';
    component.onBrandChange();
    expect(products).toHaveBeenLastCalledWith('mouse', '', 1, 20, 'jib', 'LOGITECH');
  });
});
