import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

const sensitivePublicName = /(?:PASSWORD|SECRET|TOKEN|PRIVATE|CREDENTIAL|API_KEY)/i;

export function assertNoSensitiveClientEnvironment(mode: string, values: Record<string, string>) {
  if (mode !== 'production') return;
  const unsafeNames = Object.keys(values).filter((name) => name.startsWith('VITE_') && sensitivePublicName.test(name));
  if (unsafeNames.length) {
    throw new Error(`Refusing a production frontend build with sensitive VITE_ variables: ${unsafeNames.join(', ')}. Values are omitted.`);
  }
}

export default defineConfig(({ mode }) => {
  const runtimeEnvironment = (globalThis as typeof globalThis & {
    process?: { env?: Record<string, string | undefined> };
  }).process?.env ?? {};
  const envDir = runtimeEnvironment.CROP_PULSE_FRONTEND_ENV_DIR || '.';
  assertNoSensitiveClientEnvironment(mode, loadEnv(mode, envDir, ''));
  return {
    envDir,
    plugins: [react()],
    test: { environment: 'jsdom', setupFiles: './src/test-setup.ts' },
  };
});
