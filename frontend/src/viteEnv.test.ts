import { describe, expect, it } from 'vitest';
import { assertNoSensitiveClientEnvironment } from '../vite.config';

describe('production frontend environment guard', () => {
  it('rejects sensitive VITE variables without echoing their values', () => {
    expect(() => assertNoSensitiveClientEnvironment('production', {
      VITE_DEMO_ACCOUNT_PASSWORD: 'synthetic-secret-sentinel',
    })).toThrow(/VITE_DEMO_ACCOUNT_PASSWORD/);
    expect(() => assertNoSensitiveClientEnvironment('production', {
      VITE_DEMO_ACCOUNT_PASSWORD: 'synthetic-secret-sentinel',
    })).not.toThrowError(/synthetic-secret-sentinel/);
  });

  it('allows the public API origin and does not block development mode', () => {
    expect(() => assertNoSensitiveClientEnvironment('production', {
      VITE_API_BASE_URL: 'https://api.example.invalid',
    })).not.toThrow();
    expect(() => assertNoSensitiveClientEnvironment('development', {
      VITE_DEMO_ACCOUNT_PASSWORD: 'synthetic-secret-sentinel',
    })).not.toThrow();
  });
});
