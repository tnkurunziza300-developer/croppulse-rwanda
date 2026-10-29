import { afterEach, describe, expect, it, vi } from 'vitest';
import { api, resolveApiBaseUrl } from './api';

afterEach(() => vi.unstubAllGlobals());

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
