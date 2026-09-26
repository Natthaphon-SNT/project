import {
  AfterViewInit,
  ChangeDetectorRef,
  Component,
  ElementRef,
  OnDestroy,
  OnInit,
  QueryList,
  ViewChildren
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { Subscription } from 'rxjs';

import { ApiService } from '../../services/api';
import { stripEmojiText } from '../../utils/strip-emoji';

interface ShowcaseCategory {
  slug: string;
  label: string;
}

interface ShowcaseCard {
  productId: string;
  name: string;
  category: string;
  image: string;
  originalImage: string;
  minPrice: number;
  storeCount: number;
}

const SHOWCASE_CATEGORIES: ShowcaseCategory[] = [
  { slug: 'gpu', label: 'GPU' },
  { slug: 'cpu', label: 'CPU' },
  { slug: 'mainboard', label: 'Mainboard' },
  { slug: 'ram', label: 'RAM' },
  { slug: 'monitor', label: 'Monitor' },
  { slug: 'case', label: 'Case' },
  { slug: 'keyboard', label: 'Keyboard' },
  { slug: 'mouse', label: 'Mouse' },
  { slug: 'air cooler', label: 'Air Cooler' }
];

const PAGE_SIZE = 8;

@Component({
  selector: 'app-product-showcase',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './product-showcase.html',
  styleUrls: ['./product-showcase.scss']
})
export class ProductShowcaseComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChildren('card', { read: ElementRef })
  private cardRefs!: QueryList<ElementRef<HTMLElement>>;

  readonly categories = SHOWCASE_CATEGORIES;
  readonly placeholderImage = '/product-placeholder.svg';

  activeCategory = SHOWCASE_CATEGORIES[0];
  cards: ShowcaseCard[] = [];
  isLoading = true;
  loadError = false;

  private requestId = 0;
  private sub: Subscription | null = null;
  private observer: IntersectionObserver | null = null;
  private revealAll = false;

  constructor(private api: ApiService, private cdr: ChangeDetectorRef) {}

  ngOnInit(): void {
    this.load(this.activeCategory);
  }

  ngAfterViewInit(): void {
    if (this.prefersReducedMotion() || typeof IntersectionObserver === 'undefined') {
      this.revealAll = true;
      this.observeCards();
      return;
    }
    this.observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-in');
            this.observer?.unobserve(entry.target);
          }
        });
      },
      { rootMargin: '0px 0px -8% 0px', threshold: 0.18 }
    );
    this.observeCards();
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
    this.observer?.disconnect();
  }

  select(category: ShowcaseCategory): void {
    if (category.slug === this.activeCategory.slug) {
      return;
    }
    this.activeCategory = category;
    this.load(category);
  }

  private load(category: ShowcaseCategory): void {
    const requestId = ++this.requestId;
    this.isLoading = true;
    this.loadError = false;
    this.sub?.unsubscribe();
    this.sub = this.api.getProducts(category.slug, '', 1, PAGE_SIZE).subscribe({
      next: (res) => {
        if (requestId !== this.requestId) {
          return;
        }
        const rows: any[] = res?.data ?? [];
        this.cards = rows
          .filter((row) => this.isDisplayable(row))
          .map((row) => this.toCard(row));
        this.isLoading = false;
        this.cdr.detectChanges();
        // ตัด target เก่าของหมวดก่อนหน้าทิ้ง แล้ว observe เฉพาะการ์ดชุดใหม่
        this.observer?.disconnect();
        this.observeCards();
      },
      error: () => {
        if (requestId !== this.requestId) {
          return;
        }
        this.cards = [];
        this.isLoading = false;
        this.loadError = true;
        this.cdr.detectChanges();
      }
    });
  }

  private isDisplayable(row: any): boolean {
    const name = stripEmojiText(row?.p_name ?? '').trim();
    if (name.length < 3) {
      return false;
    }
    const image = row?.img_url ?? '';
    // รูปจาก search-engine thumbnail ไม่ใช่ภาพสินค้าจริง แสดงแล้วจะเป็นภาพจิ๋ว
    if (!image || image.includes('gstatic.com')) {
      return false;
    }
    return this.minPrice(row) > 0;
  }

  private toCard(row: any): ShowcaseCard {
    const prices = [row.price_advice, row.price_jib, row.price_ihavecpu];
    return {
      productId: row.product_id,
      name: stripEmojiText(row.p_name ?? '').trim(),
      category: row.category ?? '',
      image: this.api.resolveProductImage(row.img_url, this.placeholderImage),
      originalImage: row.img_url,
      minPrice: this.minPrice(row),
      storeCount: prices.filter((value) => Number(value) > 0).length
    };
  }

  onImageError(event: Event, card: ShowcaseCard): void {
    this.api.handleProductImageError(event, card.originalImage, this.placeholderImage);
  }

  private minPrice(row: any): number {
    const candidates = [row?.price_advice, row?.price_jib, row?.price_ihavecpu, row?.p_price]
      .map((value) => Number(value))
      .filter((value) => value > 0);
    return candidates.length ? Math.min(...candidates) : 0;
  }

  private prefersReducedMotion(): boolean {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
      return true;
    }
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  private observeCards(): void {
    this.cardRefs?.forEach((ref) => {
      const element = ref.nativeElement;
      if (element.classList.contains('is-in')) {
        return;
      }
      if (this.revealAll) {
        element.classList.add('is-in');
        return;
      }
      this.observer?.observe(element);
    });
  }
}
