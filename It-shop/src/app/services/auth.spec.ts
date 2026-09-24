import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { vi } from 'vitest';

import { AuthService } from './auth';

describe('AuthService', () => {
  const token = (exp: number) =>
    `header.${btoa(JSON.stringify({ exp }))}.signature`;
  const navigate = vi.fn();
  const router = {
    url: '/profile',
    navigate
  } as unknown as Router;

  beforeEach(() => {
    localStorage.removeItem('lt_user');
    localStorage.removeItem('lt_token');
    navigate.mockClear();
  });

  afterEach(() => {
    localStorage.removeItem('lt_user');
    localStorage.removeItem('lt_token');
  });

  it('rejects a cached user without a usable token', () => {
    localStorage.setItem('lt_user', JSON.stringify({ id: 'user-1' }));
    localStorage.setItem('lt_token', token(Math.floor(Date.now() / 1000) - 60));
    const auth = new AuthService({} as HttpClient, router);
    expect(auth.isLoggedIn()).toBe(false);
    expect(localStorage.getItem('lt_user')).toBeNull();
    expect(localStorage.getItem('lt_token')).toBeNull();
  });

  it('keeps a valid session and redirects after a server 401', () => {
    localStorage.setItem('lt_user', JSON.stringify({ id: 'user-1' }));
    localStorage.setItem('lt_token', token(Math.floor(Date.now() / 1000) + 3600));
    const auth = new AuthService({} as HttpClient, router);
    expect(auth.isLoggedIn()).toBe(true);
    auth.handleUnauthorized('/pc-builder');
    expect(auth.isLoggedIn()).toBe(false);
    expect(navigate).toHaveBeenCalledWith(['/login'], {
      queryParams: { redirect: '/pc-builder' }
    });
  });
});
