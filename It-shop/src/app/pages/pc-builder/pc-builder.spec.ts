import { ChangeDetectorRef } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { vi } from 'vitest';
import { of } from 'rxjs';

import { AuthService } from '../../services/auth';
import { PcBuilderComponent, Product } from './pc-builder';

describe('PcBuilderComponent session recovery', () => {
  const auth = {
    isLoggedIn: vi.fn(() => false),
    handleUnauthorized: vi.fn()
  } as unknown as AuthService;
  const cdr = { detectChanges: vi.fn() } as unknown as ChangeDetectorRef;

  beforeEach(() => {
    sessionStorage.removeItem('lt_pending_manual_build');
    vi.clearAllMocks();
  });

  afterEach(() => {
    sessionStorage.removeItem('lt_pending_manual_build');
    vi.useRealTimers();
  });

  it('preserves selected parts when login is required to save', () => {
    const builder = new PcBuilderComponent(
      {} as HttpClient, auth, {} as Router, cdr
    );
    const selected = {
      product_id: 'cpu-1', p_name: 'CPU TEST', p_price: 1000,
      category: 'CPU'
    } as Product;
    builder.slots[0].selected = selected;

    builder.saveAndNavigateToHistory();

    expect(auth.handleUnauthorized).toHaveBeenCalledWith('/pc-builder');
    const draft = JSON.parse(sessionStorage.getItem('lt_pending_manual_build') || '[]');
    expect(draft).toEqual([{ key: 'cpu', product: selected }]);

    vi.useFakeTimers();
    const restored = new PcBuilderComponent({} as HttpClient, auth, {} as Router, cdr);
    (restored as any).restorePendingBuild();
    expect(restored.slots[0].selected?.product_id).toBe('cpu-1');
    expect(sessionStorage.getItem('lt_pending_manual_build')).toBeNull();
  });

  it('loads every catalog page and shows Advice, JIB and iHaveCPU in the picker', () => {
    const shops = ['advice', 'jib', 'ihavecpu'] as const;
    const pages = shops.map((shop) => Array.from({ length: 100 }, (_, index) => ({
      product_id: `${shop}-${index}`,
      p_name: `${shop.toUpperCase()} Mainboard ${index}`,
      category: 'Mainboard',
      price_advice: shop === 'advice' ? 1000 : 0,
      price_jib: shop === 'jib' ? 1000 : 0,
      price_ihavecpu: shop === 'ihavecpu' ? 1000 : 0,
    } as Product)));
    const http = {
      get: vi.fn((url: string) => {
        const page = Number(new URL(url, 'https://example.test').searchParams.get('page'));
        return of({ status: 'success', data: pages[page - 1], pagination: { total_pages: 3 } });
      })
    } as unknown as HttpClient;
    const builder = new PcBuilderComponent(http, auth, {} as Router, cdr);
    const slot = builder.slots.find(item => item.key === 'mb')!;

    builder.openPicker(slot);

    expect(slot.catalogLoaded).toBe(true);
    expect(slot.products).toHaveLength(300);
    expect(slot.products.slice(0, 3).map(product => product.product_id)).toEqual([
      'advice-0', 'jib-0', 'ihavecpu-0'
    ]);
    slot.search = 'JIB Mainboard 99';
    expect(builder.filteredProducts(slot).map(product => product.product_id)).toEqual(['jib-99']);
  });
});
