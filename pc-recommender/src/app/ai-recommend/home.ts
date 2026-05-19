import { ChangeDetectorRef, Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { RouterModule } from '@angular/router';

// ✅ Interface นี้ตรงกับ Python Response 100%
interface Part {
  category: string;
  name: string;
  price: number;
  shop_prices: {
    advice: number;
    jib: number;
    ihavecpu: number;
  };
}

interface AIResponseData {
  budget: number;
  usage: string;
  parts: Part[];
  total_price: number;
  advice: string | string[];
}

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule, FormsModule, HttpClientModule, RouterModule],
  templateUrl: './home.html',
  styleUrls: ['./home.scss']
})
export class HomeComponent {
  userInput: string = '';
  result: AIResponseData | null = null; // เก็บข้อมูลส่วน .data ที่นี่
  isLoading: boolean = false;

  constructor(private http: HttpClient, private cdr: ChangeDetectorRef) {}

  submitRequirement() {
    if (!this.userInput) return;

    this.isLoading = true;
    this.cdr.detectChanges(); // บังคับให้ UI อัปเดตว่ากำลัง "ประมวลผล"

    this.http.post<any>('http://localhost:8000/api/analyze-requirement', {
      user_input: this.userInput
    }).subscribe({
      next: (response) => {
        console.log('✅ Data received:', response);
        if (response.status === 'success') {
          this.result = response.data;
        }
        this.isLoading = false;
        this.cdr.detectChanges(); 
      },
      error: (err) => {
        console.error('❌ Error:', err);
        alert('เกิดข้อผิดพลาด: ' + err.message);
        this.isLoading = false;
        this.cdr.detectChanges(); 
      }
    });
  }

  // ฟังก์ชันคำนวณราคารวมของแต่ละร้าน
  calculateTotal(storeName: 'jib' | 'advice' | 'ihavecpu'): number {
    if (!this.result || !this.result.parts) return 0;
    
    return this.result.parts.reduce((acc, part) => {
      const price = part.shop_prices[storeName];
      return acc + (price > 0 ? price : 0);
    }, 0);
  }

  // เช็คว่าเป็น List หรือไม่ (สำหรับแสดงคำแนะนำ)
  isList(val: any): boolean {
    return Array.isArray(val);
  }

  // ==========================================
  // วิธีที่ 1: เปิดลิงก์ค้นหาสินค้าบนเว็บของแต่ละร้าน (อัปเดต URL ล่าสุด)
  // ==========================================
  openStoreSearch(store: 'jib' | 'advice' | 'ihavecpu', productName: string) {
    // เข้ารหัสชื่อสินค้าเพื่อให้รองรับการเว้นวรรคและอักขระพิเศษ
    const keyword = encodeURIComponent(productName);
    let url = '';

    switch(store) {
      case 'jib':
        // URL ของ JIB (อัปเดตล่าสุด)
        url = `https://www.jib.co.th/web/product/product_search/0?str_search=${keyword}`;
        break;
      case 'advice':
        // URL ของ Advice (ยังใช้แบบเดิม)
        url = `https://www.advice.co.th/search?keyword=${keyword}`;
        break;
      case 'ihavecpu':
        // URL ของ iHaveCPU (อัปเดตเป็น /product/search/ชื่อสินค้า)
        url = `https://ihavecpu.com/product/search/${keyword}`;
        break;
    }

    if (url) {
      window.open(url, '_blank'); // เปิดแท็บใหม่
    }
  }

  // ==========================================
  // วิธีที่ 2: สร้างลิงก์แชร์สเปกของเว็บเราเอง (ไม่ต้องใช้ Database)
  // ==========================================
  generateShareLink() {
    if (!this.result) return;

    // แปลงข้อมูล result เป็น JSON string
    const jsonString = JSON.stringify(this.result);
    // เข้ารหัสข้อความเป็น Base64 เพื่อให้ใส่ใน URL ได้
    const base64Data = btoa(unescape(encodeURIComponent(jsonString)));
    
    // สร้าง URL ปัจจุบันต่อด้วย parameter ?spec=
    const shareUrl = `${window.location.origin}${window.location.pathname}?spec=${base64Data}`;

    // คัดลอกลง Clipboard
    navigator.clipboard.writeText(shareUrl).then(() => {
      alert('🔗 สร้างลิงก์แชร์สำเร็จ!\nคุณสามารถนำลิงก์นี้ไปส่งให้ร้านดูสเปกได้เลย (ลิงก์ถูกคัดลอกแล้ว)');
    }).catch(err => {
      console.error('Copy failed', err);
      alert('❌ ไม่สามารถสร้างลิงก์แชร์ได้');
    });
  }

  // ฟังก์ชันช่วยสร้าง URL สำหรับแชร์
  getShareUrl(): string {
    if (!this.result) return '';
    const jsonString = JSON.stringify(this.result);
    const base64Data = btoa(unescape(encodeURIComponent(jsonString)));
    return `${window.location.origin}${window.location.pathname}?spec=${base64Data}`;
  }

  // สร้างข้อความสรุปสเปกแบบแบ่งหัวข้อสวยงาม
  generateExportText(): string {
    if (!this.result) return '';

    let text = `🖥️ สรุปสเปกคอมพิวเตอร์ (AI จัดให้) 🤖\n`;
    text += `━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n`;

    text += `🎯 ความต้องการเบื้องต้น\n`;
    text += `💰 งบประมาณ : ${this.result.budget.toLocaleString()} บาท\n`;
    text += `🎮 การใช้งาน : ${this.result.usage}\n\n`;

    text += `📦 รายการชิ้นส่วน (Hardware)\n`;
    text += `━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n`;
    this.result.parts.forEach(part => {
      text += `🔸 [${part.category}]\n    👉 ${part.name}\n`;
    });
    text += `\n`;

    text += `📊 สรุปราคาประเมินจาก 3 ร้านดัง\n`;
    text += `━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n`;
    text += `🏪 JIB       : ${this.calculateTotal('jib').toLocaleString()} บาท\n`;
    text += `🏪 Advice    : ${this.calculateTotal('advice').toLocaleString()} บาท\n`;
    text += `🏪 iHaveCPU  : ${this.calculateTotal('ihavecpu').toLocaleString()} บาท\n`;
    text += `*(หมายเหตุ: ราคาอาจมีการเปลี่ยนแปลง กรุณาเช็คหน้าเว็บอีกครั้ง)*\n\n`;

    text += `💡 คำแนะนำเพิ่มเติมจาก AI\n`;
    text += `━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n`;
    if (this.isList(this.result.advice)) {
      (this.result.advice as string[]).forEach(tip => text += `✅ ${tip}\n`);
    } else {
      text += `✅ ${this.result.advice}\n`;
    }

    text += `\n🔗 เปิดดูสเปกและเปรียบเทียบราคาบนเว็บ:\n`;
    text += `${this.getShareUrl()}\n`;

    return text;
  }

  // คัดลอกลง Clipboard (สำหรับแปะในแชท LINE / Facebook)
  copyToClipboard() {
    const text = this.generateExportText();
    if (!text) return;

    navigator.clipboard.writeText(text).then(() => {
      alert('📋 คัดลอกสเปกแบบจัดรูปแบบสวยงามเรียบร้อยแล้ว!\nสามารถนำไปแปะส่งให้ร้านดูใน LINE หรือ Facebook ได้เลยครับ');
    }).catch(err => {
      console.error('Copy failed', err);
      alert('❌ ไม่สามารถคัดลอกได้');
    });
  }

}