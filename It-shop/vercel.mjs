const configuredApiUrl = process.env.RAILWAY_API_URL;
if (!configuredApiUrl) {
  throw new Error('Set RAILWAY_API_URL to the public Railway backend URL in Vercel.');
}

const backend = new URL(configuredApiUrl);
if (backend.protocol !== 'https:') {
  throw new Error('RAILWAY_API_URL must be an HTTPS URL.');
}

export const config = {
  framework: 'angular',
  buildCommand: 'npm run build',
  outputDirectory: 'dist/lt-shop/browser',
  rewrites: [
    { source: '/api/:path*', destination: `${backend.origin}/api/:path*` },
    { source: '/uploads/:path*', destination: `${backend.origin}/uploads/:path*` },
    { source: '/(.*)', destination: '/index.html' },
  ],
};
