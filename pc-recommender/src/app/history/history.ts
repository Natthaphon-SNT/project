import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { RouterModule } from '@angular/router';

interface HistoryPart {
  category: string;
  name: string;
  price: number;
}

interface HistoryItem {
  id: number;
  user_input: string;
  budget: number;
  usage_type: string;
  total_price: number;
  created_at: string;
  ai_advice: string[];
  parts: HistoryPart[];
}

@Component({
  selector: 'app-history',
  standalone: true,
  imports: [CommonModule, HttpClientModule, RouterModule], 
  templateUrl: './history.html',
  styleUrls: ['./history.scss']
})
export class HistoryComponent implements OnInit {
  historyList: HistoryItem[] = []; 
  isLoading: boolean = true;
  
  // 🌟 เพิ่ม ChangeDetectorRef เข้ามาใน Constructor
  constructor(private http: HttpClient, private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    this.fetchHistory();
  }

  fetchHistory() {
    this.isLoading = true;
    this.http.get<{status: string, data: any[]}>('http://localhost:8000/api/history')
      .subscribe({
        next: (res) => {
          console.log('✅ ข้อมูลดิบจาก Backend:', res); 
          
          if (res.status === 'success' && res.data) {
            this.historyList = res.data.map(item => {
              let parsedAdvice = [];
              let parsedParts = [];
              try {
                parsedAdvice = JSON.parse(item.ai_advice || '[]');
                parsedParts = JSON.parse(item.parts_json || '[]');
              } catch (e) {
                console.error('⚠️ แปลง JSON ไม่สำเร็จ:', e);
              }

              return {
                id: item.id,
                user_input: item.user_input,
                budget: item.budget,
                usage_type: item.usage_type,
                total_price: item.total_price,
                created_at: item.created_at,
                ai_advice: parsedAdvice,
                parts: parsedParts
              };
            });
            console.log('✅ แปลงข้อมูลพร้อมแสดงผลแล้ว:', this.historyList);
          }
          this.isLoading = false;
          
          // 🌟 บังคับ Angular ให้อัปเดตหน้าจอทันทีแบบ 100%
          this.cdr.detectChanges(); 
        },
        error: (err) => {
          console.error('❌ ดึงข้อมูลประวัติไม่ได้:', err);
          this.isLoading = false;
          this.cdr.detectChanges(); // บังคับอัปเดตแม้จะ Error จะได้ซ่อนสถานะโหลด
        }
      });
  }

  deleteItem(id: number) {
    if(!confirm('ยืนยันที่จะลบรายการนี้ใช่ไหม?')) return;

    this.http.delete(`http://localhost:8000/api/history/${id}`)
      .subscribe({
        next: () => {
          this.historyList = this.historyList.filter(item => item.id !== id);
          // 🌟 บังคับอัปเดตหน้าจอทันทีหลังกดลบ ข้อมูลจะหายวับไปเลย
          this.cdr.detectChanges(); 
        },
        error: (err) => {
          console.error('❌ ลบข้อมูลไม่ได้', err);
          alert('ไม่สามารถลบข้อมูลได้! ลองเปิด Console (F12) ดู Error');
        }
      });
  }
}