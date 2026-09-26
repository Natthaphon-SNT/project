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

  it('uses matching custom menus for store and brand without a native select', () => {
    const api = TestBed.inject(ApiService);
    vi.spyOn(api, 'getProductFilters').mockReturnValue(of({
      status: 'success', data: { brands: ['LOGITECH', 'RAZER'] }
    }));
    const products = vi.spyOn(api, 'getProducts').mockReturnValue(of({
      status: 'success', data: [], pagination: { total: 0 }
    }));
    fixture.detectChanges();
    component.category = 'gaming chair';
    fixture.changeDetectorRef.markForCheck();
    fixture.detectChanges(false);
    expect(component.category).toBe('gaming chair');
    expect(component.showRetailFilters).toBe(true);

    const root = fixture.nativeElement as HTMLElement;
    expect(root.querySelector('.retail-filters select')).toBeNull();
    const storeTrigger = root.querySelector<HTMLButtonElement>('#store-filter-trigger')!;
    const brandTrigger = root.querySelector<HTMLButtonElement>('#brand-filter-trigger')!;
    expect(brandTrigger.disabled).toBe(true);

    storeTrigger.click();
    fixture.detectChanges();
    expect(storeTrigger.getAttribute('aria-expanded')).toBe('true');
    const jib = root.querySelector<HTMLButtonElement>('#store-filter-options [data-value="jib"]')!;
    jib.click();
    fixture.detectChanges();

    expect(component.selectedStore).toBe('jib');
    expect(storeTrigger.textContent).toContain('JIB');
    expect(brandTrigger.disabled).toBe(false);
    expect(products).toHaveBeenLastCalledWith('gaming chair', '', 1, 20, 'jib', '');

    brandTrigger.click();
    fixture.detectChanges();
    root.querySelector<HTMLButtonElement>('#brand-filter-options [data-value="RAZER"]')!.click();
    fixture.detectChanges();
    expect(component.selectedBrand).toBe('RAZER');
    expect(products).toHaveBeenLastCalledWith('gaming chair', '', 1, 20, 'jib', 'RAZER');
  });

  it('supports arrow navigation and closes an open filter with Escape', () => {
    fixture.detectChanges();
    component.category = 'mouse';
    fixture.changeDetectorRef.markForCheck();
    fixture.detectChanges(false);
    expect(component.category).toBe('mouse');
    expect(component.showRetailFilters).toBe(true);
    const root = fixture.nativeElement as HTMLElement;
    const trigger = root.querySelector<HTMLButtonElement>('#store-filter-trigger')!;
    trigger.focus();
    trigger.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true }));
    fixture.detectChanges();
    expect(component.openFilter).toBe('store');
    expect(document.activeElement?.textContent).toContain('ทุกร้านค้า');

    (document.activeElement as HTMLElement).dispatchEvent(
      new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true })
    );
    expect(document.activeElement?.textContent).toContain('Advice');

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    fixture.detectChanges();
    expect(component.openFilter).toBeNull();
    expect(document.activeElement).toBe(trigger);
  });
});
