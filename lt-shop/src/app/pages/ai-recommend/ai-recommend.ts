import { Component, OnDestroy, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminFilterPipe } from './admin-filter.pipe';
import { HttpClient } from '@angular/common/http';

// ─── Interfaces ────────────────────────────────────────────────────────────────

interface Part {
  type: string;
  name: string;
  price: string;
  reason: string;
}

interface RecommendResult {
  summary: string;
  totalBudget: string;
  tier: string;
  parts: Part[];
  performance: { gaming: string; productivity: string; upgrade: string };
  pros: string[];
  cons: string[];
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

// ─── ประวัติการจัดสเปค (เก็บใน localStorage) ──────────────────────────────────
export interface SpecHistory {
  id: string;
  uid: string;        // user id จาก localStorage ของ LT PC BUILD
  username: string;   // ชื่อ user
  type: 'ai' | 'manual';
  mode: 'recommend' | 'compare' | 'compat';
  title: string;      // สรุปชื่อสั้นๆ
  createdAt: string;  // ISO string
  // payload แยกตาม mode
  recommendData?: RecommendResult;
  compareData?: CompareResult;
  compatData?: CompatResult;
  // input ที่กรอก
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
  resultType: 'recommend' | 'compare' | 'compat' | 'error' | null = null;
  recommendData: RecommendResult | null = null;
  compareData:   CompareResult   | null = null;
  compatData:    CompatResult    | null = null;
  visibleCards:  boolean[] = [];

  // ─── ประวัติ ──────────────────────────────────────────────────────────────────
  myHistory:    SpecHistory[] = [];
  allHistory:   SpecHistory[] = [];   // admin เท่านั้น
  historyFilter: 'all' | 'ai' | 'manual' = 'all';
  adminSearch   = '';
  viewingDetail: SpecHistory | null = null;

  // ─── Data constants ──────────────────────────────────────────────────────────
  useCases = [
    { id: 'gaming',  icon: '🎮', label: 'เล่นเกม',      desc: 'AAA / Esports / Streaming' },
    { id: 'work',    icon: '💼', label: 'ทำงานออฟฟิศ',   desc: 'Excel / Zoom / เอกสาร' },
    { id: 'video',   icon: '🎬', label: 'ตัดต่อวิดีโอ',  desc: 'Premiere / DaVinci / After Effects' },
    { id: '3d',      icon: '🧊', label: '3D / Render',   desc: 'Blender / Maya / Cinema4D' },
    { id: 'ai',      icon: '🤖', label: 'AI / ML',        desc: 'Training / Stable Diffusion' },
    { id: 'general', icon: '🖥️', label: 'ใช้งานทั่วไป',  desc: 'ท่องเน็ต / ดูหนัง / เรียน' },
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
    { label: 'Advice',    getUrl: (q: string) => `https://www.advice.co.th/search?keyword=${encodeURIComponent(q)}` },
    { label: 'JIB',       getUrl: (q: string) => `https://www.jib.co.th/web/product/product_search/0?q=${encodeURIComponent(q)}` },
    { label: 'iHaveCPU',  getUrl: (q: string) => `https://www.google.com/search?q=site:ihavecpu.com+${encodeURIComponent(q)}` },
    { label: 'Banana IT', getUrl: (q: string) => `https://www.google.com/search?q=site:bnn.in.th+${encodeURIComponent(q)}` },
  ];

  loadingSteps = [
    '🔍 วิเคราะห์ความต้องการ...',
    '🧠 เลือก CPU ที่เหมาะสม...',
    '⚡ จับคู่ GPU และ RAM...',
    '💾 เลือก Storage ที่คุ้มค่า...',
    '💰 คำนวณงบประมาณรวม...',
    '📊 ตรวจสอบความเข้ากัน...',
    '✅ สรุปสเปคให้คุณ...',
  ];

  private loadingInterval: any;

  constructor(private cdr: ChangeDetectorRef, private http: HttpClient) {}

  // ─── Lifecycle ────────────────────────────────────────────────────────────────
  ngOnInit() {
    this.loadCurrentUser();
    this.loadHistory();
  }

  ngOnDestroy() {
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
      }
    } catch { /* ใช้ default */ }
  }

  // ─── History ──────────────────────────────────────────────────────────────────
  private loadHistory() {
    // 🌟 ดึงข้อมูลจากฐานข้อมูล MySQL ผ่าน API
    const url = `http://localhost/pc_part/api/get_history.php?uid=${this.currentUser.uid}&role=${this.currentUser.role}`;
    this.http.get<any>(url).subscribe({
      next: (res) => {
        if (res.status === 'success') {
          const all: SpecHistory[] = res.data;
          this.myHistory = all.filter(h => h.uid === this.currentUser.uid);
          this.allHistory = all;
          this.cdr.detectChanges(); // สั่งให้ Angular อัปเดตหน้าจอ
        }
      },
      error: (err) => console.error('Load history error:', err)
    });
  }

  private saveHistory(entry: Omit<SpecHistory, 'id' | 'uid' | 'username' | 'createdAt'>) {
    // 🌟 เลือกว่าจะบันทึก Data ก้อนไหนลงฐานข้อมูล
    let resultData = null;
    if (entry.mode === 'recommend') resultData = entry.recommendData;
    else if (entry.mode === 'compare') resultData = entry.compareData;
    else if (entry.mode === 'compat') resultData = entry.compatData;

    const payload = {
      uid: this.currentUser.uid,
      username: this.currentUser.username,
      type: entry.type,
      mode: entry.mode,
      title: entry.title,
      inputSummary: entry.inputSummary,
      result_data: resultData
    };

    // 🌟 ส่งข้อมูลไปบันทึกลง MySQL
    this.http.post<any>('http://localhost/pc_part/api/save_history.php', payload).subscribe({
      next: (res) => {
        if (res.status === 'success') {
          this.loadHistory(); // บันทึกเสร็จให้โหลดประวัติใหม่ทันที
        } else {
          console.error('Save history error:', res.message);
        }
      },
      error: (err) => console.error('Save history HTTP error:', err)
    });
  }

  deleteHistory(id: string) {
    if (!confirm('⚠️ ยืนยันการลบประวัตินี้?')) return;
    
    // 🌟 ส่งคำสั่งลบไปยัง MySQL
    this.http.post<any>('http://localhost/pc_part/api/delete_history.php', { id: id }).subscribe({
      next: (res) => {
        if (res.status === 'success') {
          if (this.viewingDetail?.id === id) this.viewingDetail = null;
          this.loadHistory(); // ลบเสร็จให้โหลดประวัติใหม่ทันที
        } else {
          alert('❌ ไม่สามารถลบประวัติได้: ' + res.message);
        }
      },
      error: (err) => console.error('Delete history HTTP error:', err)
    });
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
      recommend: '🤖 แนะนำสเปค',
      compare:   '⚖️ เปรียบเทียบ',
      compat:    '🔗 เช็คความเข้ากัน',
    };
    return map[mode] || mode;
  }

  // ─── Navigation ───────────────────────────────────────────────────────────────
  setMode(m: 'recommend' | 'compare' | 'compat') {
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
    this.visibleCards  = [];
    this.viewingDetail = null;
    this.cdr.detectChanges();
  }

  // ─── Loading Animation ────────────────────────────────────────────────────────
  private startLoadingAnimation() {
    let i = 0;
    this.loadingInterval = setInterval(() => {
      this.loadingText = this.loadingSteps[i % this.loadingSteps.length];
      this.cdr.detectChanges();
      i++;
    }, 900);
  }

  private stopLoadingAnimation() {
    if (this.loadingInterval) clearInterval(this.loadingInterval);
  }

  // ─── Gemini API ผ่าน PHP Proxy (ปลอดภัย 100%) ─────────────────────────────────
  private async callGemini(prompt: string, retries = 3): Promise<string> {
    const proxyUrl = 'http://localhost/pc_part/api/ai_proxy.php';

    for (let attempt = 1; attempt <= retries; attempt++) {
      try {
        const res = await fetch(proxyUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: prompt }),
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json();

        // จัดการกรณี Rate Limit (429) ที่ถูกส่งมาจาก PHP
        if (data.status === 'rate_limit') {
          if (attempt < retries) {
            const wait = 6000 * attempt;
            this.loadingText = `⏳ คนใช้งานเยอะ รอ ${wait / 1000} วิ... (พยายาม ${attempt + 1}/${retries})`;
            this.cdr.detectChanges();
            await new Promise(r => setTimeout(r, wait));
            continue;
          }
          throw new Error('Rate limit exceeded');
        }

        if (data.status === 'error') {
          throw new Error(data.message || 'API Error');
        }

        // คืนค่า Data ที่ PHP สกัดมาให้แล้ว
        return data.data || '';

      } catch (err) {
        if (attempt === retries) throw err;
        await new Promise(r => setTimeout(r, 2000));
      }
    }
    return '';
  }

  // ─── JSON Parser (robust) ─────────────────────────────────────────────────────
  private parseJson(raw: string): any {
    try {
      const start = raw.indexOf('{');
      const end   = raw.lastIndexOf('}');
      if (start !== -1 && end !== -1) {
        return JSON.parse(raw.substring(start, end + 1));
      }
      return JSON.parse(raw.replace(/```json|```/g, '').trim());
    } catch (e) {
      console.error('JSON Parse Error. Raw:', raw);
      throw e;
    }
  }

  // ─── Handlers ─────────────────────────────────────────────────────────────────

  async handleRecommend() {
    if (!this.selectedUseCase || !this.selectedBudget) return;
    this.step = 2;
    this.startLoadingAnimation();

    const budgetMap: Record<string, string> = {
      '10k': 'ต่ำกว่า 10,000 บาท',   '15k': '10,000–15,000 บาท',
      '20k': '15,000–20,000 บาท',     '30k': '20,000–30,000 บาท',
      '50k': '30,000–50,000 บาท',     '100k': '50,000 บาทขึ้นไป',
    };
    const useCaseMap: Record<string, string> = {
      gaming:  'เล่นเกม PC (AAA / Esports)',
      work:    'ทำงานออฟฟิศ (Office / Video Call)',
      video:   'ตัดต่อวิดีโอ (Premiere Pro / DaVinci Resolve)',
      '3d':    'งาน 3D Rendering / Animation (Blender / Maya)',
      ai:      'งาน AI / Machine Learning / Stable Diffusion',
      general: 'ใช้งานทั่วไป (ท่องเน็ต / ดูหนัง / เรียน)',
    };

    const budgetLabel  = budgetMap[this.selectedBudget];
    const useCaseLabel = useCaseMap[this.selectedUseCase];
    const today        = new Date().toLocaleDateString('th-TH', { year: 'numeric', month: 'long', day: 'numeric' });

    // ─── Prompt ที่ปรับปรุงแล้ว ─────────────────────────────────────────────────
    const prompt = `
วันนี้คือ ${today}

คุณคือผู้เชี่ยวชาญคอมพิวเตอร์และที่ปรึกษาด้านฮาร์ดแวร์ในประเทศไทย
มีความรู้เรื่อง CPU, GPU, RAM, Storage, Mainboard, PSU, Case, Cooler ทุกรุ่นที่วางจำหน่ายในปัจจุบัน
รู้ราคาจริงในตลาดไทยล่าสุด (JIB, Advice, iHaveCPU, Banana IT)

== ความต้องการของลูกค้า ==
การใช้งานหลัก: ${useCaseLabel}
งบประมาณ: ${budgetLabel}
ความต้องการเพิ่มเติม: ${this.extraDetail || 'ไม่มี'}

== กฎในการแนะนำ ==
1. เลือกชิ้นส่วนที่คุ้มค่าที่สุดในงบตั้งแต่ปี 2023 - ปัจจุบัน
2. ต้อง "เข้ากันได้" ทุกชิ้น: Socket CPU ↔ Mainboard, DDR gen, PCIe gen, TDP ↔ Cooler, วัตต์ ↔ PSU
3. ราคาแต่ละชิ้นรวมกันต้องไม่เกินงบที่ระบุ (เผื่อ 5–20% ได้)
4. หาก ${this.selectedUseCase} === 'gaming' ให้ prioritize GPU มากกว่า CPU
5. หาก ${this.selectedUseCase} === 'video' หรือ '3d' ให้ prioritize CPU core/thread และ RAM
6. ระบุชื่อรุ่นสินค้าจริงและครบ เช่น "AMD Ryzen 5 7600" ไม่ใช่แค่ "Ryzen 5"
7. ราคาเป็นบาทไทย ประมาณการจากตลาดไทย ณ ปัจจุบัน

== รูปแบบตอบกลับ ==
ตอบเป็น JSON เท่านั้น ห้ามมี text นอก JSON ห้ามมี markdown:
{
  "summary": "สรุปสเปคโดยรวมใน 2 ประโยค บอกจุดเด่นและเหมาะกับอะไร",
  "totalBudget": "ราคารวมโดยประมาณ เช่น 27,500 ฿",
  "tier": "ระดับสเปค เช่น Entry-level / Mid-range / High-end / Enthusiast",
  "parts": [
    {"type":"CPU","name":"ชื่อรุ่นเต็ม","price":"ราคา ฿","reason":"เหตุผลที่เลือกรุ่นนี้ เปรียบเทียบกับรุ่นอื่นในงบ"},
    {"type":"Mainboard","name":"ชื่อรุ่นเต็ม","price":"ราคา ฿","reason":"เหตุผล: socket, chipset, feature"},
    {"type":"RAM","name":"ชื่อรุ่น ขนาด ความเร็ว","price":"ราคา ฿","reason":"เหตุผล: ขนาดเพียงพอกับการใช้งาน"},
    {"type":"GPU","name":"ชื่อรุ่นเต็ม","price":"ราคา ฿","reason":"เหตุผล: ประสิทธิภาพที่ได้"},
    {"type":"Storage",":"ราคา ฿"name":"ชื่อรุ่น ขนาด interface","price","reason":"เหตุผล"},
    {"type":"PSU","name":"ชื่อรุ่น วัตต์ 80+grade","price":"ราคา ฿","reason":"เหตุผล: วัตต์เพียงพอกับ GPU+CPU"},
    {"type":"Case","name":"ชื่อรุ่น","price":"ราคา ฿","reason":"เหตุผล: ขนาด airflow"},
    {"type":"Cooler","name":"ชื่อรุ่น","price":"ราคา ฿","reason":"เหตุผล: TDP รองรับ CPU นี้ได้"}
  ],
  "performance": {
    "gaming":       "ประสิทธิภาพเกมในรายละเอียด เช่น 1080p/1440p High–Ultra กี่ fps เกมอะไร",
    "productivity": "ประสิทธิภาพงานที่ระบุ เช่น render เวลา export",
    "upgrade":      "แนะนำ upgrade อะไรได้อีกในอนาคต"
  },
  "pros": ["ข้อดี 1","ข้อดี 2","ข้อดี 3"],
  "cons": ["ข้อเสีย/ข้อควรระวัง 1","ข้อเสีย 2"]
}
`;

    try {
      const raw = await this.callGemini(prompt);
      this.recommendData = this.parseJson(raw);
      this.resultType    = 'recommend';
      this.stopLoadingAnimation();
      this.step = 3;

      const count = this.recommendData!.parts.length;
      this.visibleCards = Array(count).fill(false);
      this.cdr.detectChanges();
      this.animateCards(count);

      // บันทึก history
      this.saveHistory({
        type:          'ai',
        mode:          'recommend',
        title:         `${useCaseLabel} | ${budgetLabel}`,
        inputSummary:  `${useCaseLabel}, ${budgetLabel}${this.extraDetail ? ', ' + this.extraDetail : ''}`,
        recommendData: this.recommendData!,
      });

    } catch (e) {
      console.error(e);
      this.stopLoadingAnimation();
      this.resultType = 'error';
      this.step = 3;
      this.cdr.detectChanges();
    }
  }

  async handleCompare() {
    if (!this.spec1 || !this.spec2) return;
    this.step = 2;
    this.startLoadingAnimation();

    const today = new Date().toLocaleDateString('th-TH', { year: 'numeric', month: 'long', day: 'numeric' });

    const prompt = `
วันนี้คือ ${today}

คุณคือผู้เชี่ยวชาญคอมพิวเตอร์ในประเทศไทย เปรียบเทียบสเปค 2 ชุดนี้อย่างละเอียดและตรงไปตรงมา:

ชุดที่ 1: ${this.spec1}
ชุดที่ 2: ${this.spec2}

== กฎการเปรียบเทียบ ==
1. อ้างอิง benchmark จริง เช่น FPS, Cinebench R23, Blender time, DaVinci render time
2. คำนึงถึงราคาตลาดไทยปัจจุบัน (ปี 2025) ด้วย
3. บอกชัดเจนว่าในแต่ละ category อันไหนชนะและทำไม

ตอบเป็น JSON เท่านั้น ห้ามมี text นอก JSON:
{
  "spec1Name": "ชื่อสรุปสเปค 1 สั้นๆ",
  "spec2Name": "ชื่อสรุปสเปค 2 สั้นๆ",
  "winner": "1 หรือ 2 หรือ tie",
  "verdict": "สรุปว่าอันไหนดีกว่าโดยรวมและทำไม 2–3 ประโยค",
  "categories": [
    {"name":"Gaming (1080p)","spec1":"FPS/คะแนน","spec2":"FPS/คะแนน","winner":"1หรือ2หรือtie"},
    {"name":"Gaming (1440p)","spec1":"...","spec2":"...","winner":"..."},
    {"name":"Video Editing","spec1":"...","spec2":"...","winner":"..."},
    {"name":"Multi-core (Cinebench)","spec1":"...","spec2":"...","winner":"..."},
    {"name":"ราคา/ความคุ้มค่า","spec1":"...","spec2":"...","winner":"..."},
    {"name":"การอัปเกรดในอนาคต","spec1":"...","spec2":"...","winner":"..."},
    {"name":"ความร้อน/เสียง/ไฟ","spec1":"...","spec2":"...","winner":"..."}
  ],
  "spec1Pros": ["ข้อดี1","ข้อดี2","ข้อดี3"],
  "spec2Pros": ["ข้อดี1","ข้อดี2","ข้อดี3"],
  "recommendation": "แนะนำชุดไหนสำหรับใคร บอกกรณีที่ควรเลือกแต่ละชุด"
}
`;

    try {
      const raw = await this.callGemini(prompt);
      this.compareData = this.parseJson(raw);
      this.resultType  = 'compare';
      this.stopLoadingAnimation();
      this.step = 3;
      this.cdr.detectChanges();

      this.saveHistory({
        type:         'ai',
        mode:         'compare',
        title:        `${this.compareData!.spec1Name} vs ${this.compareData!.spec2Name}`,
        inputSummary: `${this.spec1} | ${this.spec2}`,
        compareData:  this.compareData!,
      });

    } catch (e) {
      console.error(e);
      this.stopLoadingAnimation();
      this.resultType = 'error';
      this.step = 3;
      this.cdr.detectChanges();
    }
  }

  async handleCompat() {
    if (!this.compatText.trim()) return;
    this.step = 2;
    this.loadingText = '🔍 ตรวจสอบความเข้ากันได้...';
    this.startLoadingAnimation();

    const today = new Date().toLocaleDateString('th-TH', { year: 'numeric', month: 'long', day: 'numeric' });

    const prompt = `
วันนี้คือ ${today}

คุณคือผู้เชี่ยวชาญด้านฮาร์ดแวร์คอมพิวเตอร์ในไทย ตรวจสอบความเข้ากันได้อย่างละเอียด:

${this.compatText}

== สิ่งที่ต้องตรวจสอบ ==
1. CPU Socket ↔ Mainboard Socket (ต้องตรงกัน)
2. RAM Type/Gen ↔ Mainboard รองรับ (DDR4/DDR5)
3. PSU วัตต์ ≥ TDP รวม CPU+GPU + 20% headroom
4. GPU Length ↔ Case clearance (ถ้าทราบ)
5. CPU TDP ↔ Cooler TDP Rating
6. Storage Interface (NVMe M.2 / SATA) ↔ Mainboard slot
7. ATX Form Factor ↔ Case รองรับ (ถ้าทราบ)

ตอบเป็น JSON เท่านั้น ห้ามมี text นอก JSON:
{
  "overall": "ok หรือ warning หรือ error",
  "summary": "สรุปผลการตรวจสอบโดยรวม 1–2 ประโยค",
  "checks": [
    {"item":"CPU ↔ Mainboard Socket","ok":true,"detail":"อธิบายว่า socket ตรงกันไหม"},
    {"item":"RAM Compatibility","ok":true,"detail":"DDR gen และความเร็วรองรับไหม"},
    {"item":"PSU Wattage","ok":true,"detail":"วัตต์รวมประมาณเท่าไร PSU เพียงพอไหม"},
    {"item":"GPU Clearance","ok":true,"detail":"GPU ยาวเท่าไร case รองรับไหม"},
    {"item":"CPU Cooler TDP","ok":true,"detail":"Cooler รองรับ TDP ของ CPU ไหม"},
    {"item":"Storage Interface","ok":true,"detail":"ช่อง M.2 หรือ SATA มีไหม"},
    {"item":"Motherboard Form Factor","ok":true,"detail":"ATX/mATX/ITX ตรงกับ case ไหม"}
  ],
  "warnings": ["คำเตือนสำคัญ ถ้ามี"],
  "suggestions": ["คำแนะนำเพื่อปรับปรุง เช่น upgrade PSU หรือเปลี่ยน cooler"]
}
`;

    try {
      const raw = await this.callGemini(prompt);
      this.compatData = this.parseJson(raw);
      this.resultType  = 'compat';
      this.stopLoadingAnimation();
      this.step = 3;
      this.cdr.detectChanges();

      this.saveHistory({
        type:         'ai',
        mode:         'compat',
        title:        `ตรวจสอบชิ้นส่วน ${this.compatData!.overall === 'ok' ? '✅' : '⚠️'}`,
        inputSummary: this.compatText.substring(0, 100),
        compatData:   this.compatData!,
      });

    } catch (e) {
      console.error(e);
      this.stopLoadingAnimation();
      this.resultType = 'error';
      this.step = 3;
      this.cdr.detectChanges();
    }
  }

  // ─── Card Animation ───────────────────────────────────────────────────────────
  private animateCards(count: number) {
    for (let i = 0; i < count; i++) {
      setTimeout(() => {
        this.visibleCards[i] = true;
        this.cdr.detectChanges();
      }, i * 150);
    }
  }
}