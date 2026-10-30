import { describe, expect, it } from 'vitest';
import { assertNoSensitiveClientEnvironment, assertSafeFrontendEnvironment } from '../vite.config';

describe('production frontend environment guard', () => {
  it('rejects sensitive VITE variables without echoing their values', () => {
    const buildGuard = () => assertNoSensitiveClientEnvironment('production', {
      VITE_DEMO_ACCOUNT_PASSWORD: 'synthetic-secret-sentinel',
    });
    expect(buildGuard).toThrow(/VITE_DEMO_ACCOUNT_PASSWORD/);
    try {
      buildGuard();
    } catch (error) {
      expect(String(error)).not.toContain('synthetic-secret-sentinel');
    }
    expect(() => assertNoSensitiveClientEnvironment('production', {
      VITE_DEMO_ACCOUNT_EMAIL: 'synthetic-demo@example.invalid',
    })).toThrow(/VITE_DEMO_ACCOUNT_EMAIL/);
  });

  it('allows the public API origin and does not block development mode', () => {
    expect(() => assertNoSensitiveClientEnvironment('production', {
      VITE_API_BASE_URL: 'https://api.example.invalid',
    })).not.toThrow();
    expect(() => assertNoSensitiveClientEnvironment('development', {
      VITE_DEMO_ACCOUNT_PASSWORD: 'synthetic-secret-sentinel',
    })).not.toThrow();
  });

  it('accepts an ordinary farmer build with demo mode disabled', () => {
    expect(() => assertSafeFrontendEnvironment('production', {
      VITE_API_BASE_URL: 'https://farm-api.example.invalid',
    })).not.toThrow();
    expect(() => assertSafeFrontendEnvironment('production', {
      VITE_API_BASE_URL: 'https://farm-api.example.invalid',
      VITE_DEMO_MODE: 'false',
    })).not.toThrow();
    expect(() => assertSafeFrontendEnvironment('production', {
      VITE_API_BASE_URL: 'https://farm-api.example.invalid',
      VITE_DEMO_API_BASE_URL: 'https://demo-api.example.invalid',
    })).toThrow(/cannot be set unless VITE_DEMO_MODE=true/);
  });

  it('accepts the explicit same-origin proxy sentinel without a public backend URL', () => {
    expect(() => assertSafeFrontendEnvironment('production', {
      VITE_API_BASE_URL: 'same-origin',
      VITE_DEMO_MODE: 'false',
    })).not.toThrow();
  });

  it('enables demo builds only with a distinct explicit demo API origin', () => {
    expect(() => assertSafeFrontendEnvironment('production', {
      VITE_API_BASE_URL: 'https://farm-api.example.invalid',
      VITE_DEMO_MODE: 'true',
      VITE_DEMO_API_BASE_URL: 'https://demo-api.example.invalid',
    })).not.toThrow();
    expect(() => assertSafeFrontendEnvironment('production', {
      VITE_API_BASE_URL: 'https://farm-api.example.invalid',
      VITE_DEMO_MODE: 'true',
    })).toThrow(/no farmer API fallback/);
    expect(() => assertSafeFrontendEnvironment('production', {
      VITE_API_BASE_URL: 'https://farm-api.example.invalid',
      VITE_DEMO_MODE: 'true',
      VITE_DEMO_API_BASE_URL: 'https://farm-api.example.invalid',
    })).toThrow(/distinct/);
  });
});
