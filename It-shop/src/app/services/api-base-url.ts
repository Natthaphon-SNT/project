// Resolves the FastAPI backend URL from the Angular environment.
// - Development build:  environment.ts   → 'http://localhost:3000'
// - Production build:   environment.prod.ts → '' (same-origin Vercel proxy)
//
// The Angular CLI swaps the file automatically via `fileReplacements` in
// angular.json, so no runtime branching on `window.location` is needed.
import { environment } from '../../environments/environment';

export const API_BASE_URL: string = environment.apiUrl;
