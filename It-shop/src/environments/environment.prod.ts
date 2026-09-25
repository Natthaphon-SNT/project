// Production uses Vercel's same-origin /api and /uploads rewrites.
// If you deploy without that proxy, replace '' with your backend HTTPS URL.
export const environment = {
  production: true,
  apiUrl: '',
};
