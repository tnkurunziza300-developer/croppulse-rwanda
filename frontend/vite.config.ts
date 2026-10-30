import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

const sensitivePublicName = /(?:PASSWORD|SECRET|TOKEN|PRIVATE|CREDENTIAL|API_KEY|DEMO_ACCOUNT_EMAIL)/i;

export function assertNoSensitiveClientEnvironment(mode: string, values: Record<string, string | undefined>) {
  if (mode !== 'production') return;
  const unsafeNames = Object.keys(values).filter((name) => name.startsWith('VITE_') && sensitivePublicName.test(name));
  if (unsafeNames.length) {
    throw new Error(`Refusing a production frontend build with sensitive VITE_ variables: ${unsafeNames.join(', ')}. Values are omitted.`);
  }
}

export function assertSafeFrontendEnvironment(mode: string, values: Record<string, string | undefined>) {
  assertNoSensitiveClientEnvironment(mode, values);
  const demoMode = values.VITE_DEMO_MODE;
  if (demoMode !== undefined && demoMode !== '' && demoMode !== 'true' && demoMode !== 'false') {
    throw new Error('VITE_DEMO_MODE must be either true or false.');
  }
  if (demoMode !== 'true') {
    if (values.VITE_DEMO_API_BASE_URL?.trim()) {
      throw new Error('VITE_DEMO_API_BASE_URL cannot be set unless VITE_DEMO_MODE=true.');
    }
  } else {
    const farmerValue = values.VITE_API_BASE_URL?.trim() ?? '';
    const demoValue = values.VITE_DEMO_API_BASE_URL?.trim() ?? '';
    const parseOrigin = (value: string, name: string): URL => {
      let url: URL;
      try { url = new URL(value); } catch { throw new Error(`${name} must be an explicit API origin.`); }
      if (!url.hostname || url.username || url.password || !['', '/'].includes(url.pathname) || url.search || url.hash) {
        throw new Error(`${name} must be an API origin without credentials or a path.`);
      }
      const loopback = ['localhost', '127.0.0.1'].includes(url.hostname);
      if (url.protocol !== 'https:' && !(url.protocol === 'http:' && loopback && mode !== 'production')) {
        throw new Error(`${name} must use HTTPS (HTTP is allowed only for local development).`);
      }
      if (mode === 'production' && (url.protocol !== 'https:' || ['localhost', '127.0.0.1'].includes(url.hostname))) {
        throw new Error(`${name} must be a public HTTPS origin in production.`);
      }
      return url;
    };
    if (!farmerValue) throw new Error('Demo builds require an explicit VITE_API_BASE_URL to verify isolation.');
    if (!demoValue) throw new Error('Demo builds require an explicit VITE_DEMO_API_BASE_URL; no farmer API fallback is allowed.');
    if (parseOrigin(farmerValue, 'VITE_API_BASE_URL').origin === parseOrigin(demoValue, 'VITE_DEMO_API_BASE_URL').origin) {
      throw new Error('Demo builds require a VITE_DEMO_API_BASE_URL distinct from the farmer API origin.');
    }
  }
  if (mode === 'production') {
    const apiBaseUrl = values.VITE_API_BASE_URL?.trim() ?? '';
    // Vercel routes /v1/* to the API service on the same origin. This explicit
    // sentinel is build-time configuration; service bindings are runtime-only.
    if (apiBaseUrl === 'same-origin') return;
    let parsedApiBase: URL | undefined;
    try { parsedApiBase = new URL(apiBaseUrl); } catch { /* produce a safe configuration error below */ }
    if (!parsedApiBase || parsedApiBase.protocol !== 'https:' || !parsedApiBase.hostname
        || ['localhost', '127.0.0.1'].includes(parsedApiBase.hostname)
        || parsedApiBase.username || parsedApiBase.password
        || !['', '/'].includes(parsedApiBase.pathname) || parsedApiBase.search || parsedApiBase.hash) {
      throw new Error('Production builds require VITE_API_BASE_URL to be an explicit HTTPS origin without credentials or a path.');
    }
  }
}

export default defineConfig(({ mode }) => {
  const runtimeEnvironment = (globalThis as typeof globalThis & {
    process?: { env?: Record<string, string | undefined> };
  }).process?.env ?? {};
  const envDir = runtimeEnvironment.CROP_PULSE_FRONTEND_ENV_DIR || '.';
  const clientEnvironment = { ...loadEnv(mode, envDir, ''), ...runtimeEnvironment };
  assertSafeFrontendEnvironment(mode, clientEnvironment);
  return {
    envDir,
    plugins: [react()],
    test: { environment: 'jsdom', setupFiles: './src/test-setup.ts' },
  };
});
