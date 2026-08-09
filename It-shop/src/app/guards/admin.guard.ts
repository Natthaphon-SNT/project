import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth';

export const adminGuard: CanActivateFn = () => {
  const auth   = inject(AuthService);
  const router = inject(Router);
  const user   = auth.currentUserSubject.value;

  if (user && user.role === 'admin') {
    return true;
  }

  // ถ้าไม่ได้ล็อกอิน → ไปหน้า login
  if (!user) {
    router.navigate(['/login']);
    return false;
  }

  // ล็อกอินแล้วแต่ไม่ใช่ admin → ไปหน้าแรก
  alert('⛔ คุณไม่มีสิทธิ์เข้าถึงหน้านี้');
  router.navigate(['/']);
  return false;
};