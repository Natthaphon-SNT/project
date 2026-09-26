import { Component, OnDestroy, OnInit, ChangeDetectorRef, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminFilterPipe } from './admin-filter.pipe';
import { HttpClient } from '@angular/common/http';
import { finalize } from 'rxjs/operators';
import { API_BASE_URL } from '../../services/api-base-url';
import { stripEmojiDeep, stripEmojiText } from '../../utils/strip-emoji';

// ─── Interfaces ────────────────────────────────────────────────────────────────

interface Part {
  type: string;
  name: string;
  price: string | number;
  reason: string;
  product_id?: string;
  real_price?: number;
  shop_prices?: Record<string, number>;
  shop_urls?: Record<string, string>;
  matched_real_product?: boolean;
}

interface BudgetAdjustment {
  category: string;
  from_name: string;
  to_name: string;
  message: string;
}

interface RecommendResult {
  summary: string;
  totalBudget: string;
  tier: string;
  parts: Part[];
  performance: { gaming: string; productivity: string; upgrade: string };
  pros: string[];
  cons: string[];
  warnings?: string[];
  ranking_explanation?: string;
  budget_adjustments?: BudgetAdjustment[];
  component_adjustments?: BudgetAdjustment[];
  adjustments?: BudgetAdjustment[];
  compat?: { overall: string; summary: string; checks: CompatCheck[] };
  alternatives?: AltBuild[];
  _meta?: { provider_fallback?: boolean; fallback_reason?: string; requested_provider?: string; llm_provider?: string; llm_model?: string };
}

interface AltBuild {
  strategy: string;
  label: string;
  description: string;
  score: number;
  breakdown: Record<string, number>;
  weights?: Record<string, number>;
  total_price: number;
  compat_overall: string;
  parts: Part[];
  budget_adjustments?: BudgetAdjustment[];
  component_adjustments?: BudgetAdjustment[];
  adjustments?: BudgetAdjustment[];
}

interface CompareResult {
  spec1Name: string;
  spec2Name: string;
  winner: string;
  verdict: string;
  categories: { name: string; spec1: string; spec2: string; winner: string }[];
  spec1Pros: string[];
  spec2Pros: string[];
  recommendation: string;
  compatibilityWarnings?: { spec: string; message: string }[];
}

interface CompatCheck {
  item: string;
  ok: boolean;
  detail: string;
}

interface CompatResult {
  overall: 'ok' | 'warning' | 'error';
  summary: string;
  checks: CompatCheck[];
  warnings: string[];
  suggestions: string[];
}

// ─── AI Provider Settings ────────────────────────────────────────────────────
export interface AiProviderSettings {
  provider: 'google' | 'openai' | 'openrouter' | 'opencode_zen';
  model: string;
  api_key: string;
  custom_model: string;
}

export interface AiModel {
  id: string;
  name: string;
  badge: 'FREE' | 'PAID' | 'BEST' | 'FAST';
  description?: string;
}

export interface ChatSession {
  id: number;
  uid: string;
  title: string;
  mode: string;
  provider: string;
  model: string;
  messages: string; // JSON
  created_at: string;
  updated_at: string;
}

// ─── ประวัติการจัดสเปค (เก็บใน localStorage) ──────────────────────────────────
export interface SpecHistory {
  id: string;
  uid: string;
  username: string;
  type: 'ai' | 'manual';
  mode: 'recommend' | 'compare' | 'compat' | 'ask';
  title: string;
  createdAt: string;
  recommendData?: RecommendResult;
  compareData?: CompareResult;
  compatData?: CompatResult;
  inputSummary: string;
}

@Component({
  selector: 'app-ai-recommend',
  standalone: true,
  imports: [CommonModule, FormsModule, AdminFilterPipe],
  templateUrl: './ai-recommend.html',
  styleUrls: ['./ai-recommend.scss'],
})
export class AiRecommendComponent implements OnInit, OnDestroy {

  // ─── State หลัก ──────────────────────────────────────────────────────────────
  step: 1 | 2 | 3 = 1;
  mode: 'recommend' | 'compare' | 'compat' = 'recommend';
  activeTab: 'form' | 'history' | 'admin' = 'form';
  /** Ids with a DELETE in flight. Guards against duplicate clicks. */
  readonly deletingIds = new Set<string>();

  // ─── User Info (อ่านจาก localStorage ของ LT PC BUILD) ───────────────────────
  currentUser: { uid: string; username: string; role: string } = {
    uid: 'guest',
    username: 'Guest',
    role: 'user',
  };
  get isAdmin(): boolean { return this.currentUser.role === 'admin'; }

  // ─── ฟอร์มแนะนำสเปค ──────────────────────────────────────────────────────────
  selectedUseCase = '';
  selectedBudget  = '';
  extraDetail     = '';

  // ─── ฟอร์มเปรียบเทียบ ─────────────────────────────────────────────────────────
  spec1 = '';
  spec2 = '';

  // ─── ฟอร์มเช็คความเข้ากัน ────────────────────────────────────────────────────
  compatText = '';

  // ─── ผลลัพธ์ ──────────────────────────────────────────────────────────────────
  loadingText  = 'กำลังวิเคราะห์...';
  resultType: 'recommend' | 'compare' | 'compat' | 'ask' | 'error' | null = null;
  recommendData: RecommendResult | null = null;
  compareData:   CompareResult   | null = null;
  compatData:    CompatResult    | null = null;
  askAnswer:     string | null = null;   // plain-text answer for mode=ask
  visibleCards:  boolean[] = [];

  // ask-mode: question input shown below recommend result
  askQuestion = '';
  askLoading  = false;

  // ─── ประวัติ ──────────────────────────────────────────────────────────────────
  myHistory:    SpecHistory[] = [];
  allHistory:   SpecHistory[] = [];   // admin เท่านั้น
  historyFilter: 'all' | 'ai' | 'manual' = 'all';
  adminSearch   = '';
  viewingDetail: SpecHistory | null = null;

  currentUserEmail = '';
  errorMessage = '';

  // ─── AI Provider Settings ─────────────────────────────────────────────────────
  showSettingsPanel = false;
  settingsTab: AiProviderSettings['provider'] = 'openai';
  aiSettings: AiProviderSettings = {
    provider: 'openai', model: 'gpt-4o-mini', api_key: '', custom_model: ''
  };
  settingsSaving = false;
  settingsSaved  = false;
  showApiKey: Record<string, boolean> = {};

  // ─── Chat Sessions ────────────────────────────────────────────────────────────
  showHistorySidebar = false;
  overlayTop = 80;
  chatSessions: ChatSession[] = [];
  activeSessionId: number | null = null;
  loadingSessions = false;

  // ─── Provider model catalogs ─────────────────────────────────────────────────
  readonly PROVIDER_MODELS: Record<string, AiModel[]> = {
    google: [
      { id: 'gemini-3-flash-preview', name: 'Gemini 3 Flash Preview', badge: 'FAST', description: 'ค่าเริ่มต้นที่ตรวจสอบกับ API แล้ว' },
      { id: 'gemini-3.1-pro-preview', name: 'Gemini 3.1 Pro Preview', badge: 'PAID', description: 'รุ่น Pro; ความพร้อมใช้งานขึ้นกับบัญชีและโควตา' },
    ],
    openai: [
      { id: 'gpt-4o',             name: 'GPT-4o (Flagship)',                       badge: 'BEST', description: 'ฉลาดที่สุด วิเคราะห์สเปคคอมได้แม่นยำสูง' },
      { id: 'gpt-4o-mini',        name: 'GPT-4o mini',                             badge: 'FAST', description: 'เร็ว ประหยัดค่า Token' },
      { id: 'o1-mini',            name: 'o1-mini (Reasoning)',                     badge: 'PAID', description: 'โมเดลคิดวิเคราะห์เชิงลึก' },
      { id: 'gpt-3.5-turbo',      name: 'GPT-3.5 Turbo',                           badge: 'PAID', description: 'รุ่นประหยัด ราคาถูก' },
    ],
    openrouter: [
      { id: 'openai/gpt-4o',               name: 'GPT-4o (via OpenRouter)',        badge: 'BEST', description: 'OpenRouter Flagship' },
      { id: 'anthropic/claude-3.5-sonnet', name: 'Claude 3.5 Sonnet',              badge: 'BEST', description: 'Claude Sonnet 3.5' },
      { id: 'google/gemini-2.0-flash',     name: 'Gemini 2.0 Flash (via OR)',      badge: 'FAST', description: 'Google Flash via OpenRouter' },
      { id: 'meta-llama/llama-3.1-8b-instruct:free', name: 'Llama 3.1 8B Free',    badge: 'FREE', description: 'OpenRouter Free Model' },
    ],
    opencode_zen: [
      { id: 'minimax-m2.5',     name: 'MiniMax M2.5',       badge: 'PAID', description: 'OpenCode Zen Chat Completions' },
      { id: 'glm-5.3-flash',   name: 'GLM 5.3 Flash',      badge: 'FAST', description: 'OpenCode Zen Chat Completions' },
      { id: 'deepseek-v4-flash', name: 'DeepSeek V4 Flash', badge: 'PAID', description: 'OpenCode Zen Chat Completions' },
      { id: 'gpt-6-luna',     name: 'GPT 6 Luna',         badge: 'PAID', description: 'OpenCode Zen Responses API' },
    ],
  };

  providerTabLabel(provider: AiProviderSettings['provider']): string {
    return provider === 'opencode_zen' ? 'OpenCode Zen' : provider === 'openai' ? 'OpenAI' : provider === 'openrouter' ? 'OpenRouter' : 'Google';
  }

  providerLabel(provider: string): string {
    return provider === 'opencode_zen' ? 'OpenCode Zen' : provider === 'openai' ? 'OpenAI' : provider === 'openrouter' ? 'OpenRouter' : 'Google AI';
  }

  fallbackDescription(reason?: string): string {
    if (!reason || reason === 'no_api_key') return 'ยังไม่มี API key สำหรับผู้ให้บริการนี้';
    if (reason.includes('quota_exhausted')) return 'เครดิตหรือวงเงินการใช้งาน API หมด กรุณาตรวจ Billing และ Limits ของบัญชี';
    if (reason.includes('timed out') || reason.includes('ReadTimeout')) return 'หมดเวลารอคำตอบจากผู้ให้บริการ';
    if (reason.includes('Auth/Credits')) return 'ตรวจสอบ API key หรือเครดิตของบัญชี';
    if (reason.includes('rate_limit')) return 'คำขอเกินโควตาชั่วคราว';
    return 'ผู้ให้บริการ AI ตอบกลับไม่สำเร็จ';
  }

  get currentProviderModels(): AiModel[] {
    return this.PROVIDER_MODELS[this.settingsTab] || [];
  }

  get providerBadgeLabel(): string {
    const p = this.aiSettings.provider || 'google';
    switch (p) {
      case 'google':     return 'GOOGLE AI';
      case 'openai':     return 'OPENAI';
      case 'openrouter': return 'OPENROUTER';
      case 'opencode_zen': return 'OPENCODE ZEN';
      default:           return String(p).toUpperCase();
    }
  }

  get providerKeyName(): string {
    switch (this.settingsTab) {
      case 'google':     return 'Google AI API Key';
      case 'openai':     return 'OpenAI API Key';
      case 'openrouter': return 'OpenRouter API Key';
      case 'opencode_zen': return 'OpenCode Zen API Key';
      default:           return 'API Key';
    }
  }

  get providerKeyPlaceholder(): string {
    switch (this.settingsTab) {
      case 'google':     return 'AIzaSy... (จาก Google AI Studio)';
      case 'openai':     return 'sk-... (จาก platform.openai.com)';
      case 'openrouter': return 'sk-or-v1-... (จาก openrouter.ai)';
      case 'opencode_zen': return 'API key จาก opencode.ai/zen';
      default:           return 'ใส่ API Key ของคุณ';
    }
  }

  get providerKeyHelpUrl(): string {
    switch (this.settingsTab) {
      case 'google':     return 'https://aistudio.google.com/app/apikey';
      case 'openai':     return 'https://platform.openai.com/api-keys';
      case 'openrouter': return 'https://openrouter.ai/keys';
      case 'opencode_zen': return 'https://opencode.ai/zen';
      default:           return '#';
    }
  }

  get providerModelHeader(): string {
    switch (this.settingsTab) {
      case 'google':     return 'GEMINI MODEL';
      case 'openai':     return 'OPENAI MODEL';
      case 'openrouter': return 'OPENROUTER MODEL';
      case 'opencode_zen': return 'OPENCODE ZEN MODEL';
      default:           return 'AI MODEL';
    }
  }

  get providerModelsHelpUrl(): string {
    switch (this.settingsTab) {
      case 'google':     return 'https://ai.google.dev/gemini-api/docs/models/gemini';
      case 'openai':     return 'https://platform.openai.com/docs/models';
      case 'openrouter': return 'https://openrouter.ai/models';
      case 'opencode_zen': return 'https://opencode.ai/docs/zen';
      default:           return '#';
    }
  }

  // ─── Data constants ──────────────────────────────────────────────────────────
  useCases = [
    { id: 'gaming',  icon: 'gamepad', label: 'เล่นเกม',      desc: 'AAA / Esports / Streaming' },
    { id: 'work',    icon: 'briefcase', label: 'ทำงานออฟฟิศ',   desc: 'Excel / Zoom / เอกสาร' },
    { id: 'video',   icon: 'video', label: 'ตัดต่อวิดีโอ',  desc: 'Premiere / DaVinci / After Effects' },
    { id: '3d',      icon: 'cube', label: '3D / Render',   desc: 'Blender / Maya / Cinema4D' },
    { id: 'ai',      icon: 'spark', label: 'AI / ML',        desc: 'Training / Stable Diffusion' },
    { id: 'general', icon: 'monitor', label: 'ใช้งานทั่วไป',  desc: 'ท่องเน็ต / ดูหนัง / เรียน' },
  ];

  budgets = [
    { id: '10k',  label: 'ต่ำกว่า 10,000 ฿' },
    { id: '15k',  label: '10,000 – 15,000 ฿' },
    { id: '20k',  label: '15,000 – 20,000 ฿' },
    { id: '30k',  label: '20,000 – 30,000 ฿' },
    { id: '50k',  label: '30,000 – 50,000 ฿' },
    { id: '100k', label: '50,000 - 100,000 ฿' },
    { id: '200k', label: '100,000 ฿ ขึ้นไป' },
  ];

  shops = [
    { key: 'advice',   label: 'Advice' },
    { key: 'jib',      label: 'JIB' },
    { key: 'ihavecpu', label: 'iHaveCPU' },
  ];

  getPartShopUrl(part: Part, shop: { key: string }): string {
    return part.shop_urls?.[shop.key] || '';
  }

  getPartShopPrice(part: Part, shopKey: string): number {
    return Number(part.shop_prices?.[shopKey] || 0);
  }

  formatPartPrice(price: string | number): string {
    if (typeof price === 'number') return `${price.toLocaleString('th-TH')} ฿`;
    const trimmed = String(price || '').trim();
    if (/^\d+(?:,\d{3})*(?:\.\d+)?$/.test(trimmed)) {
      return `${Number(trimmed.replace(/,/g, '')).toLocaleString('th-TH')} ฿`;
    }
    return trimmed;
  }

  private loadingInterval: any;
  private activeRequestController: AbortController | null = null;
  readonly requestTimeoutMs = 150_000;
  loadingElapsedSeconds = 0;
  get requestTimeoutSeconds(): number { return this.requestTimeoutMs / 1000; }
  get loadingProgressPercent(): number {
    return Math.min(100, this.loadingElapsedSeconds / this.requestTimeoutSeconds * 100);
  }

  constructor(private cdr: ChangeDetectorRef, private http: HttpClient) {}

  // ─── Lifecycle ────────────────────────────────────────────────────────────────
  ngOnInit() {
    const token = localStorage.getItem('lt_token');
    if (!token) return;
    this.http.get<any>(`${API_BASE_URL}/api/profile`, {headers: {Authorization: `Bearer ${token}`}}).subscribe({
      next: res => {
        localStorage.setItem('lt_user', JSON.stringify(res.data));
        this.loadCurrentUser();
        this.loadAiSettings();
        this.loadSessions();
        this.loadHistory();
        this.cdr.detectChanges();
      },
      error: err => {
        this.authError = err.status === 401 ? 'การเข้าสู่ระบบหมดอายุหรือ token ไม่ถูกต้อง กรุณาเข้าสู่ระบบใหม่' : 'ตรวจสอบการเข้าสู่ระบบไม่สำเร็จ กรุณาตรวจว่า Backend เปิดอยู่';
        this.cdr.detectChanges();
      }
    });
  }

  ngOnDestroy() {
    this.activeRequestController?.abort();
    this.stopLoadingAnimation();
  }

  // ─── User ─────────────────────────────────────────────────────────────────────
  private loadCurrentUser() {
    try {
      const raw = localStorage.getItem('lt_user');
      if (raw) {
        const u = JSON.parse(raw);
        this.currentUser = {
          uid:      u.uid || u.u_id || u.id || 'guest',
          username: u.username || u.u_name || u.name || 'Guest',
          role:     u.role    || u.u_role || 'user',
        };
        this.currentUserEmail = u.email || u.u_email || '';
      }
    } catch { /* ใช้ default */ }
  }

  // ─── AI Provider Settings API ─────────────────────────────────────────────────
  settingsError = '';
  authError = '';
  readonly providerTabs = ['google', 'openai', 'openrouter', 'opencode_zen'] as const;
  private providerDrafts: Partial<Record<AiProviderSettings['provider'], AiProviderSettings>> = {};
  loadAiSettings() {
    localStorage.removeItem('ai_provider_settings');
    const token = localStorage.getItem('lt_token');
    if (!token || this.currentUser.uid === 'guest') return;
    this.http.get<any>(`${API_BASE_URL}/api/ai/settings`, {headers: {Authorization: `Bearer ${token}`}}).subscribe({
      next: res => {
        this.aiSettings = {provider: res.data.provider, model: res.data.model, api_key: res.data.api_key || '', custom_model: res.data.custom_model || ''};
        this.settingsTab = this.aiSettings.provider; this.cdr.detectChanges();
      }, error: () => { this.settingsError = 'Unable to load settings'; this.cdr.detectChanges(); }
    });
  }
  saveAiSettings() {
    this.settingsError = ''; this.settingsSaved = false;
    const token = localStorage.getItem('lt_token');
    if (!token || this.currentUser.uid === 'guest') { this.settingsSaved = true; return; }
    this.settingsSaving = true;
    this.http.put<any>(`${API_BASE_URL}/api/ai/settings`, this.aiSettings, {headers: {Authorization: `Bearer ${token}`}}).subscribe({
      next: () => {
        this.settingsSaving = false;
        this.settingsSaved = true;
        this.showSettingsPanel = false;
        this.cdr.detectChanges();
      },
      error: () => { this.settingsSaving = false; this.settingsError = 'Unable to save settings. Please retry.'; this.cdr.detectChanges(); }
    });
  }
  private updateOverlayTop() {
    const navbar = document.querySelector<HTMLElement>('.navbar-main');
    this.overlayTop = Math.max(0, Math.ceil(navbar?.getBoundingClientRect().bottom ?? 80));
  }

  @HostListener('window:resize')
  @HostListener('window:scroll')
  syncOverlayWithNavbar() {
    if (this.showSettingsPanel || this.showHistorySidebar) {
      this.updateOverlayTop();
    }
  }

  toggleSettingsPanel() {
    const opening = !this.showSettingsPanel;
    if (opening) this.updateOverlayTop();
    this.showSettingsPanel = opening;
  }
  selectProviderTab(tab: AiProviderSettings['provider']) {
    this.providerDrafts[this.aiSettings.provider] = {...this.aiSettings};
    this.aiSettings = {...(this.providerDrafts[tab] || {provider: tab, model: this.PROVIDER_MODELS[tab][0].id, api_key: '', custom_model: ''})};
    this.settingsTab = tab; this.settingsSaved = false; this.settingsError = '';
  }

  loadSessions() {
    const token = localStorage.getItem('lt_token') || '';
    if (!token || this.currentUser.uid === 'guest') {
      this.chatSessions = [];
      return;
    }

    this.loadingSessions = true;
    this.http.get<any>(`${API_BASE_URL}/api/ai/sessions`, {
      headers: { Authorization: `Bearer ${token}` }
    }).subscribe({
      next: (res) => {
        this.loadingSessions = false;
        if (res.status === 'success') {
          this.chatSessions = res.data || [];
          this.cdr.detectChanges();
        }
      },
      error: (err) => {
        this.loadingSessions = false;
        console.warn('Load sessions error:', err);
      }
    });
  }

  toggleHistorySidebar() {
    const opening = !this.showHistorySidebar;
    if (opening) this.updateOverlayTop();
    this.showHistorySidebar = opening;
    if (this.showHistorySidebar) {
      this.loadSessions();
    }
    this.cdr.detectChanges();
  }

  startNewChat() {
    if (this.step === 2) return;
    this.chatMessages = []; this.followUp = ''; this.extraDetail = ''; this.spec1 = ''; this.spec2 = ''; this.compatText = ''; this.activeTab = 'form';
    this.activeSessionId = null;
    this.mode = 'recommend';
    this.reset();
    this.showHistorySidebar = false;
    this.cdr.detectChanges();
  }

  clearCurrentChat() {
    if (this.activeSessionId !== null) this.deleteSession(this.activeSessionId);
    else this.startNewChat();
  }

  selectSession(s: ChatSession) {
    if (this.step === 2) return;
    const token = localStorage.getItem('lt_token');
    this.http.get<any>(`${API_BASE_URL}/api/ai/sessions/${s.id}`, {headers: {Authorization: `Bearer ${token}`}}).subscribe({
      next: res => this.displaySession(res.data),
      error: () => { this.errorMessage = 'Unable to load session'; this.cdr.detectChanges(); }
    });
  }
  private displaySession(s: ChatSession) {
    this.reset(); this.activeTab = 'form';
    this.activeSessionId = s.id;
    this.showHistorySidebar = false;
    this.mode = (s.mode as any) || 'recommend';

    try {
      const msgs = typeof s.messages === 'string' ? JSON.parse(s.messages) : s.messages;
      this.chatMessages = msgs.map((message: { role: string; content: string }) => message.role === 'assistant'
        ? { ...message, content: stripEmojiText(message.content) }
        : message);
      const source = [...msgs].reverse().find(m => m.spec1 && m.spec2);
      this.spec1 = source?.spec1 || ''; this.spec2 = source?.spec2 || '';
      if (Array.isArray(msgs) && msgs.length > 0) {
        const lastUser = [...msgs].reverse().find(m => m.role === 'user');
        const assistantMessages = [...msgs].reverse().filter(m => m.role === 'assistant');

        if (lastUser && lastUser.content) {
          if (s.mode === 'recommend') this.extraDetail = lastUser.content;
          else if (s.mode === 'compat') this.compatText = lastUser.content;
        }

        const buildMessage = assistantMessages.find(m => {
          try {
            const parsed = this.parseJson(m.content);
            return s.mode !== 'recommend' || Array.isArray(parsed.parts);
          } catch { return false; }
        });
        if (s.mode === 'recommend' && assistantMessages.length && assistantMessages[0] !== buildMessage) {
          this.askAnswer = stripEmojiText(assistantMessages[0].content);
        }
        if (buildMessage && buildMessage.content) {
          const parsed = this.parseJson(buildMessage.content);
          this.resultType = s.mode as any;
          if (s.mode === 'recommend') {
            this.recommendData = parsed;
            if (this.recommendData?.parts) {
              this.visibleCards = Array(this.recommendData.parts.length).fill(true);
            }
          } else if (s.mode === 'compare') {
            this.compareData = parsed;
          } else if (s.mode === 'compat') {
            this.compatData = parsed;
          }
          this.step = 3;
          this.cdr.detectChanges();
          return;
        }
      }
    } catch (e) {
      console.warn('Failed to parse session messages:', e);
    }
    this.step = 1;
    this.cdr.detectChanges();
  }

  deleteSession(id: number, event?: Event) {
    if (event) event.stopPropagation();
    if (this.step === 2) return;
    if (!confirm('ยืนยันการลบประวัติการแชทนี้?')) return;

    const token = localStorage.getItem('lt_token') || '';
    if (!token || this.currentUser.uid === 'guest') {
      this.chatSessions = this.chatSessions.filter(s => s.id !== id);
      localStorage.setItem('ai_guest_sessions', JSON.stringify(this.chatSessions));
      if (this.activeSessionId === id) this.startNewChat();
      this.cdr.detectChanges();
      return;
    }

    this.http.delete<any>(`${API_BASE_URL}/api/ai/sessions/${id}`, {
      headers: { Authorization: `Bearer ${token}` }
    }).subscribe({
      next: (res) => {
        if (res.status === 'success') {
          this.chatSessions = this.chatSessions.filter(s => s.id !== id);
          if (this.activeSessionId === id) this.startNewChat();
          this.cdr.detectChanges();
        }
      },
      error: (err) => console.error('Delete session error:', err)
    });
  }

  // ─── History ──────────────────────────────────────────────────────────────────
  private loadHistory() {
    const token = localStorage.getItem('lt_token') || '';
    const uid = this.currentUser.uid;
    
    if (uid === 'guest' || !token) return;

    // โหลดประวัติของ user
    const url = `${API_BASE_URL}/api/spec-history?limit=50`;
    this.http.get<any>(url, {
      headers: { Authorization: `Bearer ${token}` }
    }).subscribe({
      next: (res) => {
        if (res.status === 'success') {
          this.myHistory = res.data.map((h: any) => this.parseHistoryItem(h));
          this.cdr.detectChanges();
        }
      },
      error: (err) => console.error('Load history error:', err)
    });

    // ถ้า admin โหลดทั้งหมด
    if (this.isAdmin && this.activeTab === 'admin') {
      this.http.get<any>(`${API_BASE_URL}/api/spec-history/all`, {
        headers: { Authorization: `Bearer ${token}` }
      }).subscribe({
        next: (res) => {
          if (res.status === 'success') {
            this.allHistory = res.data.map((h: any) => this.parseHistoryItem(h));
            this.cdr.detectChanges();
          }
        },
        error: (err) => {
          this.allHistory = [];
          this.authError = err.status === 401 ? 'กรุณาเข้าสู่ระบบใหม่เพื่อดูประวัติ Admin' : err.status === 403 ? 'บัญชีนี้ไม่มีสิทธิ์ดูประวัติทั้งหมด' : 'โหลดประวัติ Admin ไม่สำเร็จ';
          this.cdr.detectChanges();
        }
      });
    }
  }

  private parseHistoryItem(h: any): SpecHistory {
    let parsed: any = {};
    try { parsed = stripEmojiDeep(typeof h.result_data === 'string' ? JSON.parse(h.result_data) : h.result_data); } catch {}
    return {
      id: String(h.id),
      uid: h.uid,
      username: h.username || '',
      type: h.type || 'ai',
      mode: h.mode || 'recommend',
      title: h.title || '',
      createdAt: h.createdAt || '',
      inputSummary: h.inputSummary || '',
      recommendData: h.mode === 'recommend' ? parsed : undefined,
      compareData:   h.mode === 'compare'   ? parsed : undefined,
      compatData:    h.mode === 'compat'    ? parsed : undefined,
    };
  }

  private saveHistory(entry: Omit<SpecHistory, 'id' | 'uid' | 'username' | 'createdAt'>) {
    const token = localStorage.getItem('lt_token') || '';
    let resultData: any = null;
    if (entry.mode === 'recommend') resultData = entry.recommendData;
    else if (entry.mode === 'compare') resultData = entry.compareData;
    else if (entry.mode === 'compat') resultData = entry.compatData;

    const payload = {
      uid:          this.currentUser.uid,
      username:     this.currentUser.username,
      type:         entry.type,
      mode:         entry.mode,
      title:        entry.title,
      inputSummary: entry.inputSummary,
      result_data:  JSON.stringify(resultData || {})
    };

    this.http.post<any>(`${API_BASE_URL}/api/spec-history`, payload, {
      headers: { Authorization: `Bearer ${token}` }
    }).subscribe({
      next: (res) => {
        if (res.status === 'success') {
          this.loadHistory();
        } else {
          console.error('Save history error:', res.message);
        }
      },
      error: (err) => console.error('Save history HTTP error:', err)
    });
  }

  deleteHistory(id: string) {
    // Drop repeat clicks while a DELETE for this id is still open, otherwise
    // each click through the confirm dialog fires another request.
    if (this.deletingIds.has(id)) return;
    if (!confirm('ยืนยันการลบประวัตินี้?')) return;

    const token = localStorage.getItem('lt_token') || '';
    this.deletingIds.add(id);
    this.cdr.detectChanges();

    this.http.delete<any>(`${API_BASE_URL}/api/spec-history/${id}`, {
      headers: { Authorization: `Bearer ${token}` }
    }).pipe(
      // Clears the flag on success, error and unsubscribe alike.
      finalize(() => {
        this.deletingIds.delete(id);
        this.cdr.detectChanges();
      })
    ).subscribe({
      next: (res) => {
        if (res.status === 'success') {
          if (this.viewingDetail?.id === id) this.viewingDetail = null;
          this.loadHistory();
        } else {
          alert('ไม่สามารถลบประวัติได้: ' + res.message);
        }
      },
      error: (err) => console.error('Delete history HTTP error:', err)
    });
  }

  isDeletingHistory(id: string): boolean {
    return this.deletingIds.has(id);
  }

  get filteredMyHistory(): SpecHistory[] {
    if (this.historyFilter === 'all') return this.myHistory;
    return this.myHistory.filter(h => h.type === this.historyFilter);
  }

  get filteredAdminHistory(): SpecHistory[] {
    const q = this.adminSearch.toLowerCase().trim();
    return this.allHistory.filter(h => {
      if (!q) return true;
      return h.username.toLowerCase().includes(q) ||
             h.title.toLowerCase().includes(q) ||
             h.uid.toLowerCase().includes(q);
    });
  }

  viewDetail(h: SpecHistory) {
    this.viewingDetail = h;
    // โหลดข้อมูลผลลัพธ์จาก history มาแสดง
    this.resultType    = h.mode;
    this.recommendData = h.recommendData || null;
    this.compareData   = h.compareData   || null;
    this.compatData    = h.compatData    || null;
    this.step = 3;
    if (h.recommendData) {
      this.visibleCards = Array(h.recommendData.parts.length).fill(false);
      this.cdr.detectChanges();
      this.animateCards(h.recommendData.parts.length);
    }
    this.activeTab = 'form';
    this.cdr.detectChanges();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  formatDate(iso: string): string {
    try {
      const d = new Date(iso);
      return d.toLocaleDateString('th-TH', {
        day: '2-digit', month: 'short', year: 'numeric',
        hour: '2-digit', minute: '2-digit'
      });
    } catch { return iso; }
  }

  getModeLabel(mode: string): string {
    const map: Record<string, string> = {
      recommend: 'แนะนำสเปค',
      compare:   'เปรียบเทียบ',
      compat:    'เช็คความเข้ากัน',
    };
    return map[mode] || mode;
  }

  partIcon(type: string): string {
    const name = (type || '').toLowerCase();
    if (/cpu|processor/.test(name)) return 'cpu';
    if (/mainboard|motherboard/.test(name)) return 'motherboard';
    if (/gpu|vga|graphics/.test(name)) return 'gpu';
    if (/ram|memory/.test(name)) return 'ram';
    if (/ssd|hdd|storage|m\.2/.test(name)) return 'storage';
    if (/psu|power/.test(name)) return 'power';
    if (/cooler|cooling|fan/.test(name)) return 'cooler';
    if (/case/.test(name)) return 'case';
    return 'package';
  }

  // ─── Navigation ───────────────────────────────────────────────────────────────
  setMode(m: 'recommend' | 'compare' | 'compat') {
    if (this.step === 2) return;
    if (this.mode !== m) this.startNewChat();
    this.mode = m;
    this.reset();
  }

  setTab(t: 'form' | 'history' | 'admin') {
    this.activeTab = t;
    if (t === 'history' || t === 'admin') {
      this.loadHistory();
    }
    this.cdr.detectChanges();
  }

  reset() {
    this.step          = 1;
    this.resultType    = null;
    this.recommendData = null;
    this.compareData   = null;
    this.compatData    = null;
    this.askAnswer     = null;
    this.askQuestion   = '';
    this.askLoading    = false;
    this.visibleCards  = [];
    this.viewingDetail = null;
    this.cdr.detectChanges();
  }

  // ─── Loading Animation ────────────────────────────────────────────────────────
  private startLoadingAnimation() {
    this.stopLoadingAnimation();
    this.loadingElapsedSeconds = 0;
    this.loadingText = this.mode === 'recommend' ? 'กำลังรอผลจัดสเปกจาก AI' :
      this.mode === 'compare' ? 'กำลังรอผลเปรียบเทียบสเปกจาก AI' : 'กำลังตรวจความเข้ากันได้';
    this.loadingInterval = setInterval(() => {
      this.loadingElapsedSeconds++;
      this.cdr.detectChanges();
    }, 1000);
  }

  private stopLoadingAnimation() {
    if (this.loadingInterval) clearInterval(this.loadingInterval);
    this.loadingInterval = null;
  }

  // ─── AI API ผ่าน FastAPI Proxy (Multi-Provider Support) ──────────────────────
  chatMessages: {role: string; content: string}[] = [];
  readonly suggestedPrompts: ReadonlyArray<{
    label: string;
    prompt: string;
    mode: 'recommend' | 'compare' | 'compat';
  }> = [
    {
      label: 'แนะนำคอมเล่นเกมงบ 30,000',
      prompt: 'แนะนำคอมสำหรับเล่นเกม งบประมาณ 30,000 บาท ตอบเป็นภาษาไทย',
      mode: 'recommend',
    },
    {
      label: 'เช็คว่าซีพียูนี้ใช้กับเมนบอร์ดได้ไหม',
      prompt: 'ช่วยเช็คว่าซีพียูกับเมนบอร์ดที่ฉันกำลังเลือกใช้ร่วมกันได้ไหม และบอกข้อมูลที่ต้องส่งเพิ่ม',
      mode: 'compat',
    },
    {
      label: 'เทียบ RTX 4060 กับ RX 7600',
      prompt: 'Spec 1: NVIDIA GeForce RTX 4060 | Spec 2: AMD Radeon RX 7600',
      mode: 'compare',
    },
  ];
  formatChatContent(message: {role: string; content: string}): string {
    if (message.role !== 'assistant') return message.content;
    try {
      const d = this.parseJson(message.content);
      return [d.summary || d.verdict, d.totalBudget,
        Array.isArray(d.parts) ? `เลือก ${d.parts.length} ชิ้นส่วน — ดูรายละเอียดตรงกลางหน้า` : '',
        d.recommendation || d.compat?.summary,
      ].filter(Boolean).join('\n') || JSON.stringify(d, null, 2);
    } catch { return stripEmojiText(message.content); }
  }
  followUp = '';
  private buildSpecContext(): string {
    if (!this.recommendData) return '';
    const lines: string[] = [];
    for (const p of this.recommendData.parts || []) {
      lines.push(`- ${p.type}: ${p.name} (${p.price})`);
    }
    if (this.recommendData.totalBudget) {
      lines.push(`\nงบประมาณรวม: ${this.recommendData.totalBudget}`);
    }
    return lines.join('\n');
  }

  async sendAskQuestion() {
    const q = this.askQuestion.trim();
    if (!q || this.askLoading || this.step === 2) return;
    this.errorMessage = '';
    this.askLoading = true;
    this.cdr.detectChanges();
    try {
      const token = localStorage.getItem('lt_token') || '';
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.requestTimeoutMs);
      try {
        const res = await fetch(`${API_BASE_URL}/api/ai/recommend`, {
          method: 'POST',
          signal: controller.signal,
          headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
          body: JSON.stringify({
            prompt: q,
            mode: 'ask',
            spec_context: this.buildSpecContext(),
            ...this.aiSettings,
            model: this.aiSettings.custom_model.trim() || this.aiSettings.model,
            session_id: this.activeSessionId,
          }),
        });
        const data = await res.json();
        if (!res.ok || data.status !== 'success') {
          throw new Error(data.detail || data.message || 'Ask request failed');
        }
        this.askAnswer = data.data as string;
        this.activeSessionId = data.session_id ?? this.activeSessionId;
        this.chatMessages = [...this.chatMessages,
          { role: 'user', content: q },
          { role: 'assistant', content: data.data },
        ];
        this.askQuestion = '';
        this.loadSessions();
      } finally {
        clearTimeout(timeoutId);
      }
    } catch (e: any) {
      this.errorMessage = e.message || 'ไม่สามารถส่งคำถามได้';
    } finally {
      this.askLoading = false;
      this.cdr.detectChanges();
    }
  }

  private parseJson(raw: string): any {
    const cleaned = raw.trim().replace(/^```(?:json)?\s*/, '').replace(/\s*```$/, '');
    const firstBrace = cleaned.indexOf('{');
    const lastBrace = cleaned.lastIndexOf('}');
    const json = firstBrace >= 0 && lastBrace > firstBrace
      ? cleaned.slice(firstBrace, lastBrace + 1)
      : cleaned;
    try {
      return stripEmojiDeep(JSON.parse(json));
    } catch {
      throw new Error('AI ส่งข้อมูลกลับมาไม่ครบถ้วน กรุณาลองใหม่อีกครั้ง');
    }
  }
  private async callGemini(prompt: string): Promise<string> {
    if (this.authError) throw new Error(this.authError);
    const token = localStorage.getItem('lt_token') || '';
    const controller = new AbortController();
    this.activeRequestController = controller;
    let timedOut = false;
    const timeoutId = setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, this.requestTimeoutMs);
    try {
      const res = await fetch(`${API_BASE_URL}/api/ai/recommend`, {
        method: 'POST', signal: controller.signal,
        headers: {'Content-Type': 'application/json', ...(token ? {Authorization: `Bearer ${token}`} : {})},
        body: JSON.stringify({prompt, mode: this.mode, ...this.aiSettings,
          model: this.aiSettings.custom_model.trim() || this.aiSettings.model,
          session_id: this.activeSessionId, spec1: this.spec1, spec2: this.spec2})
      });
      const data = await res.json();
      if (res.status === 401) {
        this.authError = 'การเข้าสู่ระบบหมดอายุหรือ token ไม่ถูกต้อง กรุณาเข้าสู่ระบบใหม่';
        throw new Error(this.authError);
      }
      if (!res.ok || data.status !== 'success') {
        if (res.status === 400 && (data.detail || '').includes('API Key')) this.showSettingsPanel = true;
        throw new Error(data.detail || data.message || 'AI request failed');
      }
      this.activeSessionId = data.session_id;
      this.chatMessages = [...this.chatMessages, {role: 'user', content: prompt}, {role: 'assistant', content: data.data}];
      this.loadSessions();
      return data.data;
    } catch (error: any) {
      if (error?.name === 'AbortError') {
        throw new Error(timedOut
          ? `คำขอ AI หมดเวลาหลัง ${this.requestTimeoutSeconds} วินาที กรุณาลองใหม่`
          : 'ยกเลิกคำขอ AI แล้ว');
      }
      throw error;
    } finally {
      clearTimeout(timeoutId);
      if (this.activeRequestController === controller) this.activeRequestController = null;
    }
  }

  cancelAiRequest() {
    this.activeRequestController?.abort();
  }
  async handleRecommend() {
    if (!this.selectedUseCase || !this.selectedBudget) return;
    const budget = this.budgets.find(b => b.id === this.selectedBudget)?.label;
    const detail = this.extraDetail.trim();
    await this.runPrompt(`Recommend a PC for ${this.selectedUseCase}, budget ${budget}.${detail ? ` ${detail}.` : ''} Answer in Thai.`);
  }
  async handleCompare() {
    if (this.spec1.trim() && this.spec2.trim()) await this.runPrompt(`Compare spec 1: ${this.spec1} with spec 2: ${this.spec2}`);
  }
  async handleCompat() { if (this.compatText.trim()) await this.runPrompt(this.compatText); }
  async sendFollowUp() {
    const prompt = this.followUp.trim();
    if (!prompt || this.step === 2 || this.askLoading) return;

    // A new build request should create another recommendation even when the
    // preceding assistant message was already a build, not enter ask-only mode.
    if (this.isBuildRequest(prompt)) {
      this.mode = 'recommend';
      await this.runPrompt(prompt);
      if (this.resultType !== 'error') this.followUp = '';
      return;
    }
    if (this.resultType === 'recommend' && this.recommendData) {
      this.askQuestion = prompt;
      await this.sendAskQuestion();
      if (!this.askQuestion) this.followUp = '';
      return;
    }

    await this.runPrompt(prompt);
    if (this.resultType !== 'error') this.followUp = '';
  }
  private isBuildRequest(prompt: string): boolean {
    return /จัด\s*(?:สเป[กค]|ชุด)|ประกอบ\s*(?:คอม|pc)|แนะนำ\s*(?:สเป[กค]|คอม|ชุด)|(?:build|recommend)\s+(?:a\s+)?pc/i.test(prompt);
  }
  onFollowUpEnter(event: Event) {
    const keyEvent = event as KeyboardEvent;
    if (keyEvent.shiftKey || keyEvent.isComposing) return;
    keyEvent.preventDefault();
    void this.sendFollowUp();
  }
  onAskQuestionEnter(event: Event) {
    const keyEvent = event as KeyboardEvent;
    if (keyEvent.shiftKey || keyEvent.isComposing) return;
    keyEvent.preventDefault();
    void this.sendAskQuestion();
  }
  async sendSuggestedPrompt(prompt: string, mode: 'recommend' | 'compare' | 'compat') {
    if (this.step === 2) return;
    this.startNewChat();
    this.mode = mode;
    await this.runPrompt(prompt);
  }
  private async runPrompt(prompt: string) {
    if (this.step === 2) return;
    this.errorMessage = ''; this.step = 2; this.startLoadingAnimation();
    try {
      const parsed = this.parseJson(await this.callGemini(prompt));
      this.resultType = this.mode;
      if (this.mode === 'recommend') { this.recommendData = parsed; this.visibleCards = Array(parsed.parts?.length || 0).fill(true); }
      else if (this.mode === 'compare') this.compareData = parsed;
      else this.compatData = parsed;
      this.saveHistory({type: 'ai', mode: this.mode, title: prompt.slice(0, 60), inputSummary: prompt,
        ...(this.mode === 'recommend' ? {recommendData: parsed} : this.mode === 'compare' ? {compareData: parsed} : {compatData: parsed})});
    } catch (e: any) { this.errorMessage = e.message || 'AI request failed'; this.resultType = 'error'; }
    finally { this.stopLoadingAnimation(); this.step = 3; this.cdr.detectChanges(); }
  }

  isBadDetail(detail: string): boolean { return !detail || /unknown|not available|\?{3}/i.test(detail); }
  breakdownList(alt: AltBuild) { return Object.entries(alt.breakdown).map(([key, value]) => ({key, label: key, value, score: value, weight: alt.weights?.[key] || 0})); }
  private animateCards(count: number) {
    for (let i = 0; i < count; i++) {
      setTimeout(() => {
        this.visibleCards[i] = true;
        this.cdr.detectChanges();
      }, i * 150);
    }
  }
}
