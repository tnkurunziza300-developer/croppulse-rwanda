const apiPath = '/v1/:path*';

export function createVercelConfig(configuredApiOrigin) {
  const value = configuredApiOrigin?.trim();
  if (!value) {
    throw new Error('CROP_PULSE_API_ORIGIN must be configured as an HTTPS origin.');
  }

  let apiOrigin;
  try {
    apiOrigin = new globalThis.URL(value);
  } catch {
    throw new Error('CROP_PULSE_API_ORIGIN must be configured as an HTTPS origin.');
  }

  if (apiOrigin.protocol !== 'https:' || !apiOrigin.hostname
      || ['localhost', '127.0.0.1', '[::1]'].includes(apiOrigin.hostname)
      || apiOrigin.username || apiOrigin.password
      || !['', '/'].includes(apiOrigin.pathname) || apiOrigin.search || apiOrigin.hash) {
    throw new Error('CROP_PULSE_API_ORIGIN must be a public HTTPS origin without credentials or a path.');
  }

  return {
    framework: 'vite',
    buildCommand: 'npm run build',
    outputDirectory: 'dist',
    rewrites: [
      {
        source: apiPath,
        destination: `${apiOrigin.origin}${apiPath}`,
      },
      {
        source: '/(.*)',
        destination: '/index.html',
      },
    ],
    headers: [
      {
        source: apiPath,
        headers: [{ key: 'x-vercel-enable-rewrite-caching', value: '0' }],
      },
    ],
  };
}

// This file runs as Vercel project configuration. CROP_PULSE_API_ORIGIN is
// build-time server configuration and is never exposed through Vite's VITE_ prefix.
export const config = createVercelConfig(globalThis.process?.env?.CROP_PULSE_API_ORIGIN);
