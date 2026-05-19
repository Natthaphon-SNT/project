import { Pipe, PipeTransform } from '@angular/core';
import { SpecHistory } from './ai-recommend';

@Pipe({ name: 'adminFilter', standalone: true })
export class AdminFilterPipe implements PipeTransform {
  transform(history: SpecHistory[], type: 'ai' | 'manual'): number {
    return history.filter(h => h.type === type).length;
  }
}