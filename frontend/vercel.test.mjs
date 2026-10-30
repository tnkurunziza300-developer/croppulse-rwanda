import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

beforeEach(() => {
  vi.stubEnv('CROP_PULSE_API_ORIGIN', 'https://config.example.invalid');
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

describe('Vercel same-origin API proxy configuration', () => {
  it('rewrites only /v1 paths to the configured HTTPS origin before the SPA fallback', async () => {
    const { createVercelConfig } = await import('./vercel.mjs');
    const config = createVercelConfig('https://api.example.invalid');

    expect(config.rewrites).toEqual([
      { source: '/v1/:path*', destination: 'https://api.example.invalid/v1/:path*' },
      { source: '/(.*)', destination: '/index.html' },
    ]);
    expect(config.headers).toEqual([{
      source: '/v1/:path*',
      headers: [{ key: 'x-vercel-enable-rewrite-caching', value: '0' }],
    }]);
    expect(config.framework).toBe('vite');
    expect(config.outputDirectory).toBe('dist');
  });

  it.each([
    undefined,
    '',
    'http://api.example.invalid',
    'https://user:password@api.example.invalid',
    'https://api.example.invalid/v1',
    'https://localhost',
  ])('rejects missing or unsafe proxy origins without echoing the value', async (origin) => {
    const { createVercelConfig } = await import('./vercel.mjs');
    let error;
    try {
      createVercelConfig(origin);
    } catch (caught) {
      error = caught;
    }
    expect(error).toBeInstanceOf(Error);
    expect(String(error)).not.toContain('password');
    expect(String(error)).not.toContain('api.example.invalid');
  });

  it('requires the server-side environment variable when Vercel loads the config', async () => {
    vi.stubEnv('CROP_PULSE_API_ORIGIN', '');
    await expect(import('./vercel.mjs?missing-origin')).rejects.toThrow(/CROP_PULSE_API_ORIGIN/);
  });
});
