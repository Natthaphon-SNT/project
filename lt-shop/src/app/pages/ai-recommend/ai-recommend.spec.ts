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

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});