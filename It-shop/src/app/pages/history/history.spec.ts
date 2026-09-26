import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { HistoryComponent } from './history';
import { vi } from 'vitest';
import { API_BASE_URL } from '../../services/api-base-url';

describe('HistoryComponent', () => {
  let component: HistoryComponent;
  let fixture: ComponentFixture<HistoryComponent>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HistoryComponent],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()]
    })
    .compileComponents();

    fixture = TestBed.createComponent(HistoryComponent);
    component = fixture.componentInstance;
    httpMock = TestBed.inject(HttpTestingController);
    await fixture.whenStable();
    // ngOnInit fires a GET; drain it so delete assertions are unambiguous.
    httpMock.match(`${API_BASE_URL}/api/spec-history`).forEach(r => r.flush({ status: 'success', data: [] }));
  });

  afterEach(() => httpMock.verify());

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('deleteItem double-click guard', () => {
    const ID = 36;
    const url = `${API_BASE_URL}/api/spec-history/${ID}`;

    it('sends only one DELETE when deleteItem is called repeatedly', () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true);
      component.historyList = [{ id: ID } as any];

      // Simulates the user hammering the same button, as in the Railway log.
      component.deleteItem(ID);
      component.deleteItem(ID);
      component.deleteItem(ID);

      const deletes = httpMock.match(req => req.method === 'DELETE' && req.url === url);
      expect(deletes.length).toBe(1);

      deletes[0].flush({ status: 'success' });
    });

    it('marks the row as deleting immediately and clears it afterwards', () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true);
      component.historyList = [{ id: ID } as any];

      component.deleteItem(ID);
      expect(component.isDeleting(ID)).toBe(true);

      httpMock.expectOne(url).flush({ status: 'success' });
      expect(component.isDeleting(ID)).toBe(false);
      expect(component.historyList.length).toBe(0);
    });

    it('releases the guard when the request fails', () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true);
      component.historyList = [{ id: ID } as any];

      component.deleteItem(ID);
      expect(component.isDeleting(ID)).toBe(true);

      httpMock.expectOne(url).flush('boom', { status: 500, statusText: 'Server Error' });
      expect(component.isDeleting(ID)).toBe(false);
    });

    it('does not send a request when the confirm dialog is cancelled', () => {
      vi.spyOn(window, 'confirm').mockReturnValue(false);
      component.deleteItem(ID);

      httpMock.expectNone(req => req.method === 'DELETE');
      expect(component.isDeleting(ID)).toBe(false);
    });

    it('allows a different id to be deleted while one is in flight', () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true);
      const other = 37;
      component.historyList = [{ id: ID }, { id: other }] as any;

      component.deleteItem(ID);
      component.deleteItem(other);

      expect(component.isDeleting(ID)).toBe(true);
      expect(component.isDeleting(other)).toBe(true);

      httpMock.expectOne(url).flush({ status: 'success' });
      httpMock.expectOne(`${API_BASE_URL}/api/spec-history/${other}`).flush({ status: 'success' });
    });
  });
});
