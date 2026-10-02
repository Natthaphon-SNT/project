import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';

import { ProfileComponent } from './profile';

describe('Profile', () => {
  let component: ProfileComponent;
  let fixture: ComponentFixture<ProfileComponent>;
  let http: HttpTestingController;

  beforeEach(async () => {
    localStorage.setItem('lt_user', JSON.stringify({ uid: 'test-user', role: 'customer' }));
    const payload = btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 }));
    localStorage.setItem('lt_token', `header.${payload}.signature`);
    await TestBed.configureTestingModule({
      imports: [ProfileComponent],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ProfileComponent);
    component = fixture.componentInstance;
    http = TestBed.inject(HttpTestingController);
    await fixture.whenStable();
    http.expectOne(request => request.url.endsWith('/api/profile')).flush({
      status: 'success', data: { uid: 'test-user', u_name: 'Test', u_role: 'customer' }
    });
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  function selectImage(size: number): HTMLInputElement {
    const input = document.createElement('input');
    input.type = 'file';
    const file = new File([new Uint8Array(size)], 'profile.png', { type: 'image/png' });
    Object.defineProperty(input, 'files', { value: [file] });
    component.onImageUpload({ target: input } as unknown as Event);
    return input;
  }

  it('rejects images larger than 4 MB before any upload request', () => {
    const input = selectImage(4 * 1024 * 1024 + 1);
    http.expectNone(request => request.url.endsWith('/api/profile/upload-image'));
    expect(component.uploadingImage).toBe(false);
    expect(component.message).toBe('ไฟล์ใหญ่เกินไป กรุณาเลือกรูปไม่เกิน 4 MB');
    expect(component.messageType).toBe('error');
    expect(input.value).toBe('');
  });

  it('accepts the 4 MB boundary and preserves the file and authorization', () => {
    selectImage(4 * 1024 * 1024);
    const request = http.expectOne(request => request.url.endsWith('/api/profile/upload-image'));
    expect(request.request.method).toBe('POST');
    expect(request.request.headers.get('Authorization')).toBe(`Bearer ${localStorage.getItem('lt_token')}`);
    expect((request.request.body as FormData).get('file')).toBeInstanceOf(File);
    expect(((request.request.body as FormData).get('file') as File).size).toBe(4 * 1024 * 1024);
    request.flush({ status: 'success', image_url: 'uploads/profile/test.png' });
    expect(component.profileData.u_image).toBe('uploads/profile/test.png');
    expect(component.uploadingImage).toBe(false);
  });

  it('shows a Thai size error for platform 413 responses before the function runs', () => {
    selectImage(100);
    const request = http.expectOne(request => request.url.endsWith('/api/profile/upload-image'));
    request.flush('<html>FUNCTION_PAYLOAD_TOO_LARGE</html>', { status: 413, statusText: 'Payload Too Large' });
    expect(component.message).toBe('ไฟล์ใหญ่เกินไป กรุณาเลือกรูปไม่เกิน 4 MB');
    expect(component.messageType).toBe('error');
    expect(component.uploadingImage).toBe(false);
    expect(component.profileData.u_image).toBeUndefined();
  });

  afterEach(() => {
    http.verify();
    localStorage.removeItem('lt_user');
    localStorage.removeItem('lt_token');
  });
});
