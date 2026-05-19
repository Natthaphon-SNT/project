import { Routes } from '@angular/router';
import { Home } from './pages/home/home';
import { ProductsComponent } from './pages/products/products';
import { ProductDetail } from './pages/product-detail/product-detail';
import { CartComponent } from './pages/cart/cart';
import { CheckoutComponent } from './pages/checkout/checkout';
import { LoginComponent } from './pages/login/login';
import { RegisterComponent } from './pages/register/register';
import { AdminOrdersComponent } from './pages/admin-orders/admin-orders';
import { AdminProductsComponent } from './pages/admin-products/admin-products';
import { ProfileComponent } from './pages/profile/profile';
import { AiRecommendComponent } from './pages/ai-recommend/ai-recommend';
import { HistoryComponent } from './pages/history/history';
import { authGuard } from './guards/auth.guard';
import { adminGuard } from './guards/admin.guard';  // ✅ import adminGuard

export const routes: Routes = [
  { path: '', component: Home },

  // ✅ ลูกค้าทั่วไป (ต้องล็อกอิน)
  { path: 'products', component: ProductsComponent, canActivate: [authGuard] },
  { path: 'category/:type', component: ProductsComponent, canActivate: [authGuard] },
  { path: 'product/:id', component: ProductDetail, canActivate: [authGuard] },
  { path: 'cart', component: CartComponent, canActivate: [authGuard] },
  { path: 'checkout', component: CheckoutComponent, canActivate: [authGuard] },
  { path: 'profile', component: ProfileComponent, canActivate: [authGuard] },
  { path: 'ai-recommend', component: AiRecommendComponent, canActivate: [authGuard] },
  { path: 'history', component: HistoryComponent, canActivate: [authGuard] },

  // ✅ Admin เท่านั้น (ต้องมี role = 'admin')
  { path: 'admin/orders', component: AdminOrdersComponent, canActivate: [adminGuard] },
  { path: 'admin/products', component: AdminProductsComponent, canActivate: [adminGuard] },

  // สาธารณะ
  { path: 'login', component: LoginComponent },
  { path: 'register', component: RegisterComponent },
  { path: '**', redirectTo: '' }
];