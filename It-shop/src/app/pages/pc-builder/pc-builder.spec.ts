import { ChangeDetectorRef } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { vi } from 'vitest';

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
});
