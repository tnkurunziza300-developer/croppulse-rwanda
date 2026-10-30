import { afterEach, describe, expect, it, vi } from 'vitest';
import { api, resolveApiBaseUrl } from './api';
import { assertSafeFrontendEnvironment } from '../vite.config';

afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); vi.resetModules(); });

describe('resolveApiBaseUrl', () => {
  it('aligns a loopback API hostname with a localhost app page', () => {
    expect(resolveApiBaseUrl('http://127.0.0.1:8001', 'localhost')).toBe('http://localhost:8001');
  });

  it('aligns a loopback API hostname with a 127.0.0.1 app page', () => {
    expect(resolveApiBaseUrl('http://localhost:8001/', '127.0.0.1')).toBe('http://127.0.0.1:8001');
  });

  it('keeps a remote API origin unchanged', () => {
    expect(resolveApiBaseUrl('https://api.example.org/', 'localhost')).toBe('https://api.example.org');
  });

  it('uses the local API default when none is configured', () => {
    expect(resolveApiBaseUrl(undefined, '127.0.0.1')).toBe('http://127.0.0.1:8001');
  });

  it('requires an explicit HTTPS API origin for production builds', () => {
    expect(() => resolveApiBaseUrl(undefined, 'crop.example.org', true)).toThrow(/explicit HTTPS/);
    expect(() => resolveApiBaseUrl('http://127.0.0.1:8001', 'crop.example.org', true)).toThrow(/HTTPS origin/);
    expect(() => resolveApiBaseUrl('https://api.example.org/v1', 'crop.example.org', true)).toThrow(/without credentials or a path/);
    expect(resolveApiBaseUrl('https://api.example.org/', 'crop.example.org', true)).toBe('https://api.example.org');
  });

  it('uses relative same-origin API paths for an explicitly configured production proxy', () => {
    expect(resolveApiBaseUrl('same-origin', 'crop.example.org', true)).toBe('');
  });

  it('keeps API requests same-origin, credentialed, and path/query intact in proxy mode', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'same-origin');
    vi.stubEnv('PROD', true);
    const calls: { url: string; init?: RequestInit }[] = [];
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      calls.push({ url, init });
      if (url === '/v1/browser-auth/csrf') {
        return new Response(JSON.stringify({ csrf_token: 'csrf-test-token' }), { status: 200 });
      }
      return new Response(JSON.stringify({ ok: true }), { status: 200 });
    }));

    const { api: isolatedApi } = await import('./api');
    await expect(isolatedApi('/v1/farms?offset=20&limit=10', {
      method: 'POST', body: JSON.stringify({ name: 'synthetic farm' }),
    })).resolves.toEqual({ ok: true });

    expect(calls.map(({ url }) => url)).toEqual([
      '/v1/browser-auth/csrf',
      '/v1/farms?offset=20&limit=10',
    ]);
    expect(calls.every(({ init }) => init?.credentials === 'include')).toBe(true);
    expect(calls[1].init?.method).toBe('POST');
    expect(calls[1].init?.body).toBe(JSON.stringify({ name: 'synthetic farm' }));
  });

  it('uses only the explicit demo API when demo mode is enabled', () => {
    expect(resolveApiBaseUrl(
      'https://farm-api.example.org', 'crop.example.org', true, true, 'https://demo-api.example.org',
    )).toBe('https://demo-api.example.org');
  });

  it('fails closed in demo mode when the isolated API is missing or aliases the farmer API', () => {
    expect(() => resolveApiBaseUrl('https://farm-api.example.org', 'crop.example.org', true, true)).toThrow(/no farmer API fallback/);
    expect(() => resolveApiBaseUrl(
      'https://farm-api.example.org', 'crop.example.org', true, true, 'https://farm-api.example.org/',
    )).toThrow(/distinct origin/);
  });

  it('requires HTTPS for remote demo services outside local development', () => {
    expect(() => resolveApiBaseUrl(
      'https://farm-api.example.org', 'crop.example.org', false, true, 'http://demo-api.example.org',
    )).toThrow(/must use HTTPS/);
    expect(resolveApiBaseUrl(
      'http://127.0.0.1:8001', 'localhost', false, true, 'http://127.0.0.1:8002',
    )).toBe('http://127.0.0.1:8002');
  });

  it('keeps demo routing disabled by default', () => {
    expect(resolveApiBaseUrl('https://farm-api.example.org', 'crop.example.org')).toBe('https://farm-api.example.org');
  });

  it('loads public demo credentials only from the explicitly configured demo API', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://farm-api.example.org');
    vi.stubEnv('VITE_DEMO_MODE', 'true');
    vi.stubEnv('VITE_DEMO_API_BASE_URL', 'https://demo-api.example.org');
    vi.stubEnv('PROD', true);
    const calls: { url: string; init?: RequestInit }[] = [];
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); calls.push({ url, init });
      return new Response(JSON.stringify({
        environment: 'demo', demo_enabled: true, isolation_verified: true, synthetic_data_only: true,
        login_identifier: 'synthetic@example.test', password: 'synthetic-demo-password',
      }), { status: 200 });
    }));

    const { getDemoAccountCredentials } = await import('./api');
    await expect(getDemoAccountCredentials()).resolves.toEqual({
      loginIdentifier: 'synthetic@example.test', password: 'synthetic-demo-password',
    });

    expect(calls).toHaveLength(1);
    expect(calls.every((call) => call.url.startsWith('https://demo-api.example.org/'))).toBe(true);
    expect(calls.some((call) => call.url.startsWith('https://farm-api.example.org/'))).toBe(false);
    expect(calls[0].url).toBe('https://demo-api.example.org/v1/demo/public-config');
    expect(calls[0].init?.method).toBe('GET');
    expect(calls[0].init?.credentials).toBe('include');
  });

  it('rejects demo credentials unless the service confirms verified synthetic-only isolation', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://farm-api.example.org');
    vi.stubEnv('VITE_DEMO_MODE', 'true');
    vi.stubEnv('VITE_DEMO_API_BASE_URL', 'https://demo-api.example.org');
    vi.stubEnv('PROD', true);
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
      environment: 'demo', demo_enabled: true, isolation_verified: false, synthetic_data_only: false,
      login_identifier: 'synthetic@example.test', password: 'synthetic-demo-password',
    }), { status: 200 })));

    const { getDemoAccountCredentials } = await import('./api');
    await expect(getDemoAccountCredentials()).rejects.toThrow(/has not confirmed its synthetic-only isolation/);
  });

  it('rejects credential variables from a demo frontend build', () => {
    expect(() => assertSafeFrontendEnvironment('production', {
      VITE_API_BASE_URL: 'https://farm-api.example.invalid',
      VITE_DEMO_MODE: 'true',
      VITE_DEMO_API_BASE_URL: 'https://demo-api.example.invalid',
      VITE_DEMO_ACCOUNT_PASSWORD: 'synthetic-build-secret',
    })).toThrow(/VITE_DEMO_ACCOUNT_PASSWORD/);
  });

  it.each([
    ['/v1/farms/farm-1/harvests', 'The API at this address does not provide harvest records.'],
    ['/v1/farms/farm-1/irrigation-records', 'The API at this address does not provide irrigation records.'],
  ])('explains when a running API does not register the %s endpoint', async (path, expected) => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ detail: 'Not Found' }), {
      status: 404, headers: { 'Content-Type': 'application/json' },
    })));
    await expect(api(path)).rejects.toThrow(expected);
  });

  it('keeps genuine missing-farm 404s generic to avoid exposing ownership details', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ detail: 'Farm was not found.' }), {
      status: 404, headers: { 'Content-Type': 'application/json' },
    })));
    await expect(api('/v1/farms/farm-1/harvests')).rejects.toThrow('That record could not be found.');
  });

  it.each([
    ['/v1/farms/farm-1/harvests', 'migrations 0016–0018'],
    ['/v1/farms/farm-1/irrigation-records', 'migration 0018'],
  ])('makes %s server errors actionable without exposing server details', async (path, expected) => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ detail: 'Internal Server Error' }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    })));
    await expect(api(path)).rejects.toThrow(expected);
  });
});
