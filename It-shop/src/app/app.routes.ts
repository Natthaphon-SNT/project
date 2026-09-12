import { Routes } from '@angular/router';
import { Home } from './pages/home/home';
import { ProductsComponent } from './pages/products/products';
import { ProductDetail } from './pages/product-detail/product-detail';
import { LoginComponent } from './pages/login/login';
import { RegisterComponent } from './pages/register/register';
import { AdminProductsComponent } from './pages/admin-products/admin-products';
import { AdminUsersComponent } from './pages/admin-users/admin-users';
import { ProfileComponent } from './pages/profile/profile';
import { AiRecommendComponent } from './pages/ai-recommend/ai-recommend';
import { HistoryComponent } from './pages/history/history';
import { PcBuilderComponent } from './pages/pc-builder/pc-builder';
import { authGuard } from './guards/auth.guard';
import { adminGuard } from './guards/admin.guard';

export const routes: Routes = [
  { path: '', component: Home },

  // ✅ ลูกค้าทั่วไป (ต้องล็อกอิน)
  { path: 'products', component: ProductsComponent, canActivate: [authGuard] },
  { path: 'category/:type', component: ProductsComponent, canActivate: [authGuard] },
  { path: 'product/:id', component: ProductDetail, canActivate: [authGuard] },
  { path: 'profile', component: ProfileComponent, canActivate: [authGuard] },
  { path: 'ai-recommend', component: AiRecommendComponent },
  { path: 'pc-builder',   component: PcBuilderComponent,   canActivate: [authGuard] },
  { path: 'history', component: HistoryComponent, canActivate: [authGuard] },

  // ✅ Admin เท่านั้น
  { path: 'admin/products', component: AdminProductsComponent, canActivate: [adminGuard] },
  { path: 'admin/users',    component: AdminUsersComponent,    canActivate: [adminGuard] },

  // สาธารณะ
  { path: 'login',    component: LoginComponent },
  { path: 'register', component: RegisterComponent },
  { path: '**', redirectTo: '' }
];
