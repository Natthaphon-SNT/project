import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router, type Routes } from '@angular/router';

import { describe, expect, it } from 'vitest';
import { matchedRoutePattern } from './vercel-insights';

@Component({ standalone: true, template: '' })
class Stub {}

const routes: Routes = [
  { path: '', component: Stub },
  { path: 'products', component: Stub },
  { path: 'category/:type', component: Stub },
  { path: 'product/:id', component: Stub }
];

async function patternFor(url: string): Promise<string> {
  TestBed.resetTestingModule();
  TestBed.configureTestingModule({ providers: [provideRouter(routes)] });
  const router = TestBed.inject(Router);
  await router.navigateByUrl(url);
  return matchedRoutePattern(router);
}

describe('matchedRoutePattern', () => {
  it('collapses a dynamic segment so every product shares one route', async () => {
    expect(await patternFor('/product/17')).toBe('/product/:id');
    expect(await patternFor('/product/942')).toBe('/product/:id');
  });

  it('collapses category segments', async () => {
    expect(await patternFor('/category/gpu')).toBe('/category/:type');
  });

  it('keeps static routes as they are', async () => {
    expect(await patternFor('/products')).toBe('/products');
  });

  it('reports the home route as a single slash', async () => {
    expect(await patternFor('/')).toBe('/');
  });
});
