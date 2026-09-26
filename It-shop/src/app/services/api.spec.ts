import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { ApiService } from './api';
import { API_BASE_URL } from './api-base-url';

describe('Api', () => {
  let service: ApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()]
    });
    service = TestBed.inject(ApiService);
    http = TestBed.inject(HttpTestingController);
    localStorage.setItem('lt_token', 'admin-test-token');
  });

  afterEach(() => {
    http.verify();
    localStorage.removeItem('lt_token');
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('sends the admin token when loading products for product management', () => {
    service.getAdminProducts('', 'keyboard', 2, 20).subscribe();

    const request = http.expectOne(req =>
      req.url === `${API_BASE_URL}/api/products` &&
      req.params.get('search') === 'keyboard' &&
      req.params.get('page') === '2'
    );
    expect(request.request.headers.get('Authorization')).toBe('Bearer admin-test-token');
    request.flush({ status: 'success', data: [], pagination: { total: 0 } });
  });

  it('only proxies retailer images and keeps admin image URLs unchanged', () => {
    const adminImage = 'https://images.example.com/products/apple.jpg';
    const retailerImage = 'https://www.jib.co.th/img/product.jpg';

    expect(service.resolveProductImage(adminImage, 'fallback.png')).toBe(adminImage);
    expect(service.resolveProductImage('assets/apple.png', 'fallback.png')).toBe('assets/apple.png');
    expect(service.resolveProductImage('', 'fallback.png')).toBe('fallback.png');
    expect(service.resolveProductImage(retailerImage, 'fallback.png')).toBe(
      `${API_BASE_URL}/api/image-proxy?url=${encodeURIComponent(retailerImage)}`
    );
  });

  it('retries a failed proxy image directly before using the local placeholder', () => {
    const retailerImage = 'https://img.advice.co.th/images_nas/item.jpg';
    const image = document.createElement('img');
    image.src = service.resolveProductImage(retailerImage, '/product-placeholder.svg');
    service.handleProductImageError({ target: image } as unknown as Event, retailerImage);
    expect(image.src).toBe(retailerImage);
    service.handleProductImageError({ target: image } as unknown as Event, retailerImage);
    expect(image.src).toContain('/product-placeholder.svg');
  });
});
