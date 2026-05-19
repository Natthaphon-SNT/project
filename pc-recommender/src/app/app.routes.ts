import { Routes } from '@angular/router';
import { HomeComponent } from './home/home';     
import { HistoryComponent } from './history/history'; 

export const routes: Routes = [
  { path: '', component: HomeComponent },      
  { path: 'history', component: HistoryComponent }, 
  { path: '**', redirectTo: '' }       
];