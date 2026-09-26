import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';

import { describe, expect, it } from 'vitest';
import { ProductShowcaseComponent } from './product-showcase';

function product(overrides: Record<string, unknown> = {}) {
  return {
    product_id: 'adv_A0186689',
    p_name: 'VGA ASUS RADEON RX 9060XT 16G - 16GB GDDR6',
    category: 'GPU',
    img_url: 'https://img.advice.co.th/images_nas/pic_product4/A0186689/A0186689OK_BIG_1.jpg',
    p_price: 15880,
    price_advice: 15880,
    price_jib: 0,
    price_ihavecpu: 0,
    ...overrides
  };
}

async function setup() {
  await TestBed.configureTestingModule({
    imports: [ProductShowcaseComponent],
    providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()]
  }).compileComponents();

  const fixture = TestBed.createComponent(ProductShowcaseComponent);
  const http = TestBed.inject(HttpTestingController);
  await fixture.whenStable();
  return { fixture, component: fixture.componentInstance, http };
}

describe('ProductShowcaseComponent', () => {
  it('loads real products for the default category and shows the cheapest price', async () => {
    const { fixture, component, http } = await setup();

    const req = http.expectOne((r) => r.url.includes('/api/products'));
    expect(req.request.params.get('category')).toBe('gpu');
    req.flush({ status: 'success', data: [product()] });
    fixture.detectChanges();

    expect(component.cards.length).toBe(1);
    expect(component.cards[0].minPrice).toBe(15880);
    expect(component.cards[0].storeCount).toBe(1);
    http.verify();
  });

  it('takes the cheapest price across the three retailers and the list price', async () => {
    const { fixture, component, http } = await setup();
    http
      .expectOne((r) => r.url.includes('/api/products'))
      .flush({
        status: 'success',
        data: [
          product({
            p_price: 17000,
            price_advice: 16500,
            price_jib: 15900,
            price_ihavecpu: 16200
          })
        ]
      });
    fixture.detectChanges();

    expect(component.cards[0].minPrice).toBe(15900);
    expect(component.cards[0].storeCount).toBe(3);
    http.verify();
  });

  it('drops records that have no real product image or no price', async () => {
    const { fixture, component, http } = await setup();
    http.expectOne((r) => r.url.includes('/api/products')).flush({
      status: 'success',
      data: [
        product({ product_id: 'thumb', img_url: 'https://encrypted-tbn0.gstatic.com/x.jpg' }),
        product({ product_id: 'noimg', img_url: '' }),
        product({
          product_id: 'noprice',
          p_price: 0,
          price_advice: 0,
          price_jib: 0,
          price_ihavecpu: 0
        }),
        product()
      ]
    });
    fixture.detectChanges();

    expect(component.cards.length).toBe(1);
    http.verify();
  });

  it('reports an error instead of rendering an empty grid', async () => {
    const { fixture, component, http } = await setup();
    http
      .expectOne((r) => r.url.includes('/api/products'))
      .flush('boom', { status: 500, statusText: 'Server Error' });
    fixture.detectChanges();

    expect(component.loadError).toBe(true);
    expect(component.cards.length).toBe(0);
    http.verify();
  });

  it('writes a distinct --stagger index onto every card so the cascade is real', async () => {
    const { fixture, http } = await setup();
    http.expectOne((r) => r.url.includes('/api/products')).flush({
      status: 'success',
      data: [
        product({ product_id: 'p1' }),
        product({ product_id: 'p2' }),
        product({ product_id: 'p3' }),
        product({ product_id: 'p4' })
      ]
    });
    fixture.detectChanges();

    const cards = Array.from(
      fixture.nativeElement.querySelectorAll('.showcase-card')
    ) as HTMLElement[];

    expect(cards.length).toBe(4);
    // ใบที่ 1 = 0, ใบที่ 2 = 1 ... ถ้าได้ค่าเดียวกันหมดแปลว่า index ไม่ถูกส่งเข้ามา
    expect(cards.map((c) => c.style.getPropertyValue('--stagger'))).toEqual([
      '0',
      '1',
      '2',
      '3'
    ]);
    http.verify();
  });

  it('leaves opacity to the stylesheet so cards cannot flash visible before JS runs', async () => {
    const { fixture, http } = await setup();
    http.expectOne((r) => r.url.includes('/api/products')).flush({
      status: 'success',
      data: [product()]
    });
    fixture.detectChanges();

    const card = fixture.nativeElement.querySelector('.showcase-card') as HTMLElement;
    // ถ้ามี inline opacity/transform แปลว่า visibility ถูกคุมด้วย JS และจะเกิด flash
    expect(card.style.opacity).toBe('');
    expect(card.style.transform).toBe('');
    // ตัวคุม visibility ต้องเป็น class เท่านั้น
    expect(card.className).toContain('showcase-card');
    http.verify();
  });
});
