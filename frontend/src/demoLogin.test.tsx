import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

const demoFarmer = { id: 'synthetic-farmer', email: 'synthetic@example.test', display_name: 'Synthetic Farmer', role: 'farmer', status: 'active' };

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
  vi.resetModules();
});

describe('demo login entry', () => {
  it('shows verified demo credentials and uses the normal sign-in flow', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://farmer-api.example.test');
    vi.stubEnv('VITE_DEMO_API_BASE_URL', 'https://demo-api.example.test');
    vi.stubEnv('VITE_DEMO_MODE', 'true');
    vi.stubEnv('PROD', false);
    vi.resetModules();

    const [{ AuthProvider }, { LoginPage }] = await Promise.all([
      import('./auth'),
      import('./LoginPage'),
    ]);
    const calls: { url: string; init?: RequestInit }[] = [];
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); calls.push({ url, init });
      if (url.endsWith('/v1/browser-auth/csrf')) return new Response(JSON.stringify({ csrf_token: 'synthetic-csrf' }), { status: 200 });
      if (url.endsWith('/v1/me')) return new Response(JSON.stringify({ detail: 'Sign in required' }), { status: 401 });
      if (url.endsWith('/v1/demo/public-config')) return new Response(JSON.stringify({ environment: 'demo', demo_enabled: true, isolation_verified: true, synthetic_data_only: true, login_identifier: demoFarmer.email, password: 'synthetic-demo-password' }), { status: 200 });
      if (url.endsWith('/v1/browser-auth/login')) return new Response(JSON.stringify(demoFarmer), { status: 200 });
      return new Response(JSON.stringify({ detail: 'Not Found' }), { status: 404 });
    }));

    render(<MemoryRouter><AuthProvider><LoginPage serviceError="" /></AuthProvider></MemoryRouter>);
    expect(await screen.findByRole('heading', { name: 'Demo Account' })).toBeInTheDocument();
    expect(screen.getByText(demoFarmer.email)).toBeInTheDocument();
    expect(screen.getByText('synthetic-demo-password')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Use Demo Account' }));
    expect(screen.getByLabelText('Email address')).toHaveValue(demoFarmer.email);
    expect(screen.getByLabelText('Password')).toHaveValue('synthetic-demo-password');
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));

    await waitFor(() => expect(calls.some((call) => call.url.endsWith('/v1/browser-auth/login'))).toBe(true));
    const loginCall = calls.find((call) => call.url.endsWith('/v1/browser-auth/login'));
    expect(loginCall?.init?.method).toBe('POST');
    expect(loginCall?.init?.credentials).toBe('include');
    expect(new Headers(loginCall?.init?.headers).get('X-CSRF-Token')).toBe('synthetic-csrf');
    expect(JSON.parse(String(loginCall?.init?.body))).toEqual({ email: demoFarmer.email, password: 'synthetic-demo-password' });
    expect(calls.every((call) => call.url.startsWith('https://demo-api.example.test/'))).toBe(true);
    expect(calls.some((call) => call.url.startsWith('https://farmer-api.example.test/'))).toBe(false);
  });

  it('hides credentials and disables sign-in when isolation verification is absent', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://farmer-api.example.test');
    vi.stubEnv('VITE_DEMO_API_BASE_URL', 'https://demo-api.example.test');
    vi.stubEnv('VITE_DEMO_MODE', 'true');
    vi.stubEnv('PROD', false);
    vi.resetModules();

    const [{ AuthProvider }, { LoginPage }] = await Promise.all([
      import('./auth'),
      import('./LoginPage'),
    ]);
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/v1/browser-auth/csrf')) return new Response(JSON.stringify({ csrf_token: 'synthetic-csrf' }), { status: 200 });
      if (url.endsWith('/v1/me')) return new Response(JSON.stringify({ detail: 'Sign in required' }), { status: 401 });
      if (url.endsWith('/v1/demo/public-config')) return new Response(JSON.stringify({ environment: 'demo', demo_enabled: true, isolation_verified: false, synthetic_data_only: false, login_identifier: demoFarmer.email, password: 'synthetic-demo-password' }), { status: 200 });
      return new Response(JSON.stringify({ detail: 'Not Found' }), { status: 404 });
    }));

    render(<MemoryRouter><AuthProvider><LoginPage serviceError="" /></AuthProvider></MemoryRouter>);
    expect(await screen.findByRole('alert')).toHaveTextContent(/has not verified its synthetic-only data isolation/);
    expect(screen.getByRole('heading', { name: 'Demo Account' })).toBeInTheDocument();
    expect(screen.queryByText('synthetic-demo-password')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeDisabled();
  });
});
