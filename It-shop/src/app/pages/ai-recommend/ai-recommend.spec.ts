import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { vi } from 'vitest';
import { AiRecommendComponent } from './ai-recommend'; 

describe('AiRecommendComponent', () => {
  let component: AiRecommendComponent;
  let fixture: ComponentFixture<AiRecommendComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      // Import the component under test.
      imports: [AiRecommendComponent], 
      // Provide HttpClient for the component.
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

  it('offers OpenCode Zen with models routed by the backend', () => {
    component.selectProviderTab('opencode_zen');
    component.showSettingsPanel = true;
    fixture.detectChanges();

    expect(component.aiSettings.provider).toBe('opencode_zen');
    expect(component.aiSettings.model).toBe('minimax-m2.5');
    expect(component.PROVIDER_MODELS['opencode_zen'].some(model => model.id === 'gpt-6-luna')).toBe(true);
    expect(component.providerKeyHelpUrl).toBe('https://opencode.ai/zen');
    expect(fixture.nativeElement.textContent).toContain('OpenCode Zen');
  });

  it('routes a build follow-up after a comparison to recommendation mode', async () => {
    component.mode = 'compare';
    component.resultType = 'compare';
    component.followUp = 'จัดสเปกที่ใช้ 4060 มาให้หน่อย';
    component.chatMessages = [{ role: 'assistant', content: '{"winner":"1"}' }];
    const runPrompt = vi.spyOn(component as any, 'runPrompt').mockResolvedValue(undefined);

    await component.sendFollowUp();

    expect(component.mode).toBe('recommend');
    expect(runPrompt).toHaveBeenCalledWith('จัดสเปกที่ใช้ 4060 มาให้หน่อย');
    expect(component.followUp).toBe('');
  });

  it('allows typing and sending the first message after starting a new chat', async () => {
    component.mode = 'compare';
    component.chatMessages = [{ role: 'assistant', content: 'old chat' }];
    component.startNewChat();
    fixture.detectChanges();

    const composer = fixture.nativeElement.querySelector('#followup') as HTMLTextAreaElement;
    expect(composer.disabled).toBe(false);
    expect(component.mode).toBe('recommend');

    composer.value = 'จัดสเปกคอมงบ 50000 บาท';
    composer.dispatchEvent(new Event('input', { bubbles: true }));
    await fixture.whenStable();
    fixture.detectChanges();
    const sendButton = fixture.nativeElement.querySelector('.chat-composer button') as HTMLButtonElement;
    expect(sendButton.disabled).toBe(false);

    const runPrompt = vi.spyOn(component as any, 'runPrompt').mockResolvedValue(undefined);
    await component.sendFollowUp();
    expect(runPrompt).toHaveBeenCalledWith('จัดสเปกคอมงบ 50000 บาท');
  });

  it('treats a new build request after a recommendation as another build', async () => {
    component.resultType = 'recommend';
    component.recommendData = { parts: [] } as any;
    component.followUp = 'จัดสเปกคอมอีกชุดงบ 30000 บาท';
    const ask = vi.spyOn(component, 'sendAskQuestion').mockResolvedValue(undefined);
    const runPrompt = vi.spyOn(component as any, 'runPrompt').mockResolvedValue(undefined);

    await component.sendFollowUp();

    expect(runPrompt).toHaveBeenCalledWith('จัดสเปกคอมอีกชุดงบ 30000 บาท');
    expect(ask).not.toHaveBeenCalled();
  });

  it('sends chat text on Enter and keeps Shift+Enter for a new line', () => {
    const send = vi.spyOn(component, 'sendFollowUp').mockResolvedValue(undefined);
    const enter = new KeyboardEvent('keydown', { key: 'Enter', cancelable: true });
    component.onFollowUpEnter(enter);
    expect(enter.defaultPrevented).toBe(true);
    expect(send).toHaveBeenCalledTimes(1);

    const shifted = new KeyboardEvent('keydown', { key: 'Enter', shiftKey: true, cancelable: true });
    component.onFollowUpEnter(shifted);
    expect(shifted.defaultPrevented).toBe(false);
    expect(send).toHaveBeenCalledTimes(1);
  });
});
