import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, Router, RouterStateSnapshot } from '@angular/router';
import { vi } from 'vitest';
import { routes } from '../app.routes';
import { AuthService } from '../services/auth';
import { adminGuard } from './admin.guard';
import { authGuard } from './auth.guard';

describe('Feature authentication', () => {
  it('protects every feature route and keeps home, login and registration accessible', () => {
    const publicPaths = new Set(['', 'login', 'register', '**']);
    for (const route of routes) {
      if (publicPaths.has(route.path!)) continue;
      expect(route.canActivate?.some(guard => guard === authGuard || guard === adminGuard)).toBe(true);
    }
    expect(routes.find(route => route.path === 'ai-recommend')?.canActivate).toContain(authGuard);
  });

  it.each([false, true])('checks the session before opening a feature (logged in: %s)', loggedIn => {
    const navigate = vi.fn();
    TestBed.configureTestingModule({ providers: [
      { provide: AuthService, useValue: { isLoggedIn: () => loggedIn } },
      { provide: Router, useValue: { navigate } },
    ] });
    const result = TestBed.runInInjectionContext(() => authGuard(
      {} as ActivatedRouteSnapshot, { url: '/ai-recommend' } as RouterStateSnapshot,
    ));
    expect(result).toBe(loggedIn);
    if (!loggedIn) expect(navigate).toHaveBeenCalledWith(['/login'], {
      queryParams: { redirect: '/ai-recommend' },
    });
    else expect(navigate).not.toHaveBeenCalled();
  });
});
