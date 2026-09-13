import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http'; // ✅ 1. เพิ่มสิ่งนี้เพื่อแก้ Error HttpClient
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { AiRecommendComponent } from './ai-recommend'; 

describe('AiRecommendComponent', () => { // ตั้งชื่อ describe ให้ตรงกับ Component
  let component: AiRecommendComponent;
  let fixture: ComponentFixture<AiRecommendComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      // ✅ 2. Import Component ที่ถูกต้อง (HomeComponent)
      imports: [AiRecommendComponent], 
      // ✅ 3. ต้อง Provide HttpClient เพราะใน Component คุณมีการเรียกใช้
      providers: [
        provideHttpClient(),
        provideHttpClientTesting() 
      ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(AiRecommendComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('allows an in-flight AI request to be cancelled', async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = ((_input: RequestInfo | URL, init?: RequestInit) =>
      new Promise<Response>((_resolve, reject) => {
        init?.signal?.addEventListener('abort', () =>
          reject(new DOMException('Aborted', 'AbortError')));
      })) as typeof fetch;

    try {
      component.selectedUseCase = 'gaming';
      component.selectedBudget = '30k';
      const request = component.handleRecommend();
      await Promise.resolve();
      expect(component.step).toBe(2);
      component.cancelAiRequest();
      await request;
      expect(component.step).toBe(3);
      expect(component.resultType).toBe('error');
      expect(component.errorMessage).toBeTruthy();
    } finally {
      globalThis.fetch = originalFetch;
    }
  });
});
