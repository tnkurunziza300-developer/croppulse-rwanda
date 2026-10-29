import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { App } from './App';
import { FarmsPage } from './pages';

const farmer = { id: 'farmer-1', email: 'synthetic@example.com', display_name: 'Synthetic Farmer', role: 'farmer', status: 'active' };
const reviewer = { id: 'reviewer-1', email: 'reviewer@example.com', display_name: 'Synthetic Reviewer', role: 'reviewer', status: 'active' };
const admin = { id: 'admin-1', email: 'admin@example.com', display_name: 'Synthetic Admin', role: 'admin', status: 'active' };
const originalGeolocation = Object.getOwnPropertyDescriptor(navigator, 'geolocation');
function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

describe('React authentication and role navigation', () => {
  afterEach(() => {
    vi.unstubAllGlobals(); vi.unstubAllEnvs(); window.history.replaceState({}, '', '/');
    if (originalGeolocation) Object.defineProperty(navigator, 'geolocation', originalGeolocation);
    else Reflect.deleteProperty(navigator, 'geolocation');
  });

  it('never renders demo credentials injected through client environment variables', async () => {
    vi.stubEnv('VITE_DEMO_ACCOUNT_EMAIL', 'private-demo@example.test');
    vi.stubEnv('VITE_DEMO_ACCOUNT_PASSWORD', 'synthetic-demo-password');
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'csrf' });
      if (url.endsWith('/v1/me')) return jsonResponse({ detail: 'Sign in required' }, 401);
      return jsonResponse({ detail: 'not found' }, 404);
    }));

    render(<MemoryRouter><App /></MemoryRouter>);
    render(<MemoryRouter><App /></MemoryRouter>);
    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeInTheDocument();
    expect(screen.queryByText('private-demo@example.test')).not.toBeInTheDocument();
    expect(screen.queryByText('synthetic-demo-password')).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Try a demo account' })).not.toBeInTheDocument();
  });

  it('shows the demo farmer normal saved-workflow overview without a separate walkthrough', async () => {
    let signedIn = false;
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'csrf' });
      if (url.endsWith('/v1/me')) return signedIn ? jsonResponse(farmer) : jsonResponse({ detail: 'Sign in required' }, 401);
      if (url.endsWith('/v1/browser-auth/login')) { signedIn = true; return jsonResponse(farmer); }
      if (url.endsWith('/v1/farms')) return jsonResponse([{ id: 'demo-farm', owner_id: farmer.id, name: 'CropPulse Supervisor Demo Farm (Synthetic)', district: 'Rwamagana', area_ha: 1 }]);
      if (url.endsWith('/v1/farms/demo-farm/plans')) return jsonResponse([{ id: 'demo-plan', crop: 'Maize', season: 'A', status: 'planned', planting_date: '2026-11-10', actual_planting_date: null, area_ha: 0.8 }]);
      return jsonResponse({ detail: 'not found' }, 404);
    }));

    render(<MemoryRouter><App /></MemoryRouter>);
    fireEvent.change(await screen.findByLabelText('Email address'), { target: { value: farmer.email } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'synthetic-password' } });
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(await screen.findByRole('heading', { name: 'Your farm workspace' })).toBeInTheDocument();
    expect(await screen.findByRole('heading', { name: 'Maize · Season A' })).toBeInTheDocument();
    expect(screen.getByText(/CropPulse Supervisor Demo Farm \(Synthetic\)/)).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Guided walkthrough' })).not.toBeInTheDocument();
  });

  it('exchanges a Streamlit return link and retains the administrator role', async () => {
    window.history.replaceState({}, '', '/overview?cp_handoff=synthetic-one-use-code');
    const calls: { url: string; init?: RequestInit }[] = [];
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); calls.push({ url, init });
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'handoff-csrf' });
      if (url.endsWith('/v1/browser-auth/react-handoff/exchange')) return jsonResponse(admin);
      return jsonResponse({ detail: 'unexpected request' }, 404);
    }));

    render(<MemoryRouter><App /></MemoryRouter>);

    expect(await screen.findByRole('link', { name: 'Farmer accounts' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'System health' })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'My farms' })).not.toBeInTheDocument();
    expect(window.location.search).not.toContain('cp_handoff');
    const exchange = calls.find((call) => call.url.endsWith('/v1/browser-auth/react-handoff/exchange'));
    expect(JSON.parse(String(exchange?.init?.body))).toEqual({ code: 'synthetic-one-use-code' });
    expect(new Headers(exchange?.init?.headers).get('X-CSRF-Token')).toBe('handoff-csrf');
    expect(calls.some((call) => call.url.endsWith('/v1/me'))).toBe(false);
  });

  it('returns to the Streamlit workspace after React sign-in when requested', async () => {
    const calls: { url: string; init?: RequestInit }[] = [];
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); calls.push({ url, init });
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'return-csrf' });
      if (url.endsWith('/v1/me')) return jsonResponse({ detail: 'Sign in required' }, 401);
      if (url.endsWith('/v1/browser-auth/login')) return jsonResponse(admin);
      if (url.endsWith('/v1/browser-auth/streamlit-handoff')) return jsonResponse({
        redirect_url: 'http://127.0.0.1:8501/?cp_handoff=synthetic-streamlit-code', expires_in_seconds: 300,
      });
      return jsonResponse({ detail: 'unexpected request' }, 404);
    }));

    render(<MemoryRouter initialEntries={['/overview?cp_return=streamlit']}><App /></MemoryRouter>);
    await screen.findByRole('heading', { name: 'Welcome back' });
    fireEvent.change(screen.getByLabelText('Email address'), { target: { value: admin.email } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'synthetic-password' } });
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));

    await waitFor(() => expect(calls.some((call) => call.url.endsWith('/v1/browser-auth/streamlit-handoff'))).toBe(true));
    const handoff = calls.find((call) => call.url.endsWith('/v1/browser-auth/streamlit-handoff'));
    expect(handoff?.init?.method).toBe('POST');
    expect(screen.getByRole('link', { name: 'Farmer accounts' })).toBeInTheDocument();
  });

  it('creates a field and offers it as an optional crop-plan location', async () => {
    const farm = { id: 'farm-1', owner_id: farmer.id, name: 'Home farm', district: 'Huye', area_ha: 1 };
    const fields: Record<string, unknown>[] = [];
    const plans: Record<string, unknown>[] = [];
    const savedPayloads: Record<string, unknown>[] = [];
    let recommendationRequest: Record<string, unknown> | null = null;
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'csrf' });
      if (url.endsWith('/v1/farms')) return jsonResponse([farm]);
      if (url.endsWith(`/v1/farms/${farm.id}/fields`) && init?.method === 'POST') {
        const body = JSON.parse(String(init.body)) as Record<string, unknown>;
        const created = { ...body, id: 'field-1', farm_id: farm.id, archived_at: null, created_at: '2026-10-20T00:00:00Z', updated_at: '2026-10-20T00:00:00Z' };
        fields.push(created); return jsonResponse(created, 201);
      }
      if (url.endsWith(`/v1/farms/${farm.id}/fields`)) return jsonResponse(fields);
      if (url.endsWith(`/v1/farms/${farm.id}/activities`)) return jsonResponse([]);
      if (url.endsWith(`/v1/farms/${farm.id}/plans`) && init?.method === 'POST') {
        const body = JSON.parse(String(init.body)) as Record<string, unknown>;
        const created = { ...body, id: 'plan-1', farm_id: farm.id, verification: 'provisional', status: 'planned', actual_planting_date: null, evidence: [] };
        plans.push(created); savedPayloads.push(body); return jsonResponse(created, 201);
      }
      if (url.endsWith('/v1/crop-planning/recommendations')) { recommendationRequest = JSON.parse(String(init?.body)); return jsonResponse({
        errors: [], no_window: [], cannot_assess: ['Soil suitability unavailable'], data_note: 'Manifest checks pending.',
        context: { district: 'Huye', season: 'A', elevation_m: null, irrigation: 'Unknown', water_availability: 'Unknown', generated_at: '2026-10-22T12:00:00Z', statistics_status: 'pending', statistics_provenance: [{ title: 'NISR SAS aggregate', publisher: 'NISR', reference_period: '2023–2026 Seasons A/B/C', retrieved_at: '2026-10-23', units: 'area ha; production tonnes', limitations: 'District aggregates only; not farm-level evidence.', source_url: 'https://example.test/nisr', sha256: 'a'.repeat(64) }], statistics_note: 'Validation pending.', ranking_method: 'Current documented rules; not a success probability.' },
        results: [
          { crop: 'Maize', rw: 'Ibigori', fit: 2, status: 'Provisional guide fit: possible', rank: 1, water_need: 'Medium', altitude_m_range: [800, 2200], reasons: ['Provisional zone guidance.'], risks: ['Soil unavailable.'], violations: [], evidence: ['No validated local yield history.'], evidence_basis: 'Provisional guidance only.', window: 'Indicative only', weak: 'Not a prediction.', source: 'CropPulse provisional guide.', next_steps: ['Confirm with local extension staff.'], history: { n_periods: 0, years: [], yields: [], change_pct: null, cv_pct: null }, used_stats: false },
          { crop: 'Beans', rw: 'Ibishyimbo', fit: 2, status: 'Provisional guide fit: possible', rank: 2, water_need: 'Low', altitude_m_range: [900, 2300], reasons: ['Provisional zone guidance.'], risks: [], violations: [], evidence: ['No validated local yield history.'], evidence_basis: 'Provisional guidance only.', window: 'Indicative only', weak: 'Not a prediction.', source: 'CropPulse provisional guide.', next_steps: ['Check local guidance.'], history: { n_periods: 0, years: [], yields: [], change_pct: null, cv_pct: null }, used_stats: false },
        ],
      }); }
      if (url.endsWith(`/v1/farms/${farm.id}/plans`)) return jsonResponse(plans);
      return jsonResponse({ detail: 'not found' }, 404);
    }));
    render(<MemoryRouter><FarmsPage /></MemoryRouter>);
    await screen.findByRole('heading', { name: 'Fields' });
    fireEvent.click(screen.getByRole('button', { name: 'Add a field' }));
    fireEvent.change(screen.getByLabelText('Field name'), { target: { value: 'North field' } });
    fireEvent.change(screen.getByLabelText('Area (hectares, optional)'), { target: { value: '0.4' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save field' }));
    expect(await screen.findByText('North field')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Compare crop options' }));
    expect(await screen.findAllByText('Provisional guidance only.')).toHaveLength(2);
    expect(screen.getAllByText('Provisional guide fit: possible')).toHaveLength(2);
    expect(screen.getByText(/Retrieved: 2026-10-23 · Units: area ha; production tonnes/)).toBeInTheDocument();
    fireEvent.click(screen.getByText('Dataset scope and limitations'));
    expect(screen.getByText('District aggregates only; not farm-level evidence.')).toBeInTheDocument();
    expect(screen.getByText(/do not independently verify NISR survey estimates/)).toBeInTheDocument();
    fireEvent.click(screen.getAllByLabelText('Compare this crop')[0]);
    fireEvent.click(screen.getAllByLabelText('Compare this crop')[1]);
    const comparison = screen.getByRole('region', { name: 'Crop option comparison' });
    expect(comparison).toHaveTextContent('Relative water category (unverified)');
    expect(within(comparison).getAllByRole('article')).toHaveLength(2);
    fireEvent.click(screen.getAllByRole('button', { name: 'Review for my plan' })[0]);
    expect(await screen.findByLabelText(/Field \(optional\)/)).toHaveTextContent('North field');
    fireEvent.change(screen.getByLabelText(/Field \(optional\)/), { target: { value: 'field-1' } });
    fireEvent.change(screen.getByLabelText('Planned area (hectares)'), { target: { value: '0.4' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save crop plan' }));
    expect(await screen.findByText(/No independently verified evidence records are attached/)).toBeInTheDocument();
    expect(plans[0]?.field_id).toBe('field-1');
    expect(savedPayloads[0]?.plan).toMatchObject({ recommendation_snapshot: { crop: 'Maize', evidence_basis: 'Provisional guidance only.' } });
    expect(recommendationRequest).toMatchObject({ district: 'Huye', season: 'A', elevation_m: null, irrigation: 'Unknown', water_availability: 'Unknown' });
  });

  it('fills field coordinates from browser location but saves only after form submission', async () => {
    const farm = { id: 'farm-location', owner_id: farmer.id, name: 'Location test farm', district: 'Huye', area_ha: 1 };
    const savedFields: Record<string, unknown>[] = [];
    const getCurrentPosition = vi.fn((success: PositionCallback) => success({
      coords: { latitude: -2.5, longitude: 29.9, accuracy: 71 } as GeolocationCoordinates,
      timestamp: Date.now(),
    } as GeolocationPosition));
    Object.defineProperty(navigator, 'geolocation', { configurable: true, value: { getCurrentPosition } });
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'csrf' });
      if (url.endsWith('/v1/farms')) return jsonResponse([farm]);
      if (url.endsWith(`/v1/farms/${farm.id}/fields`) && init?.method === 'POST') {
        const body = JSON.parse(String(init.body)) as Record<string, unknown>;
        savedFields.push(body);
        return jsonResponse({ ...body, id: 'field-location', farm_id: farm.id, archived_at: null,
          created_at: '2026-10-20T00:00:00Z', updated_at: '2026-10-20T00:00:00Z' }, 201);
      }
      if (url.endsWith(`/v1/farms/${farm.id}/fields`)) return jsonResponse(savedFields);
      if (url.endsWith(`/v1/farms/${farm.id}/activities`) || url.endsWith(`/v1/farms/${farm.id}/plans`)) return jsonResponse([]);
      return jsonResponse({ detail: 'not found' }, 404);
    }));

    render(<MemoryRouter><FarmsPage /></MemoryRouter>);
    await screen.findByRole('heading', { name: 'Fields' });
    fireEvent.click(screen.getByRole('button', { name: 'Add a field' }));
    fireEvent.click(screen.getByRole('button', { name: 'Use my current location' }));
    expect(await screen.findByText(/accuracy about 71 m/)).toBeInTheDocument();
    expect(screen.getByLabelText('Latitude (optional)')).toHaveValue(-2.5);
    expect(screen.getByLabelText('Longitude (optional)')).toHaveValue(29.9);
    expect(savedFields).toHaveLength(0);

    fireEvent.change(screen.getByLabelText('Field name'), { target: { value: 'GPS field' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save field' }));
    await waitFor(() => expect(savedFields).toHaveLength(1));
    expect(savedFields[0]).toMatchObject({ latitude: -2.5, longitude: 29.9 });
  });

  it('shows a recoverable planning error when recommendations cannot be reached', async () => {
    const farm = { id: 'farm-err', owner_id: farmer.id, name: 'Farm', district: 'Karongi', area_ha: 0.5 };
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'csrf' });
      if (url.endsWith('/v1/farms')) return jsonResponse([farm]);
      if (url.endsWith('/irrigation-records')) return jsonResponse([]);
      if (url.endsWith('/timeline')) return jsonResponse({ entries: [], has_more: false });
      if (url.endsWith(`/v1/farms/${farm.id}/fields`) || url.endsWith(`/v1/farms/${farm.id}/activities`) || url.endsWith(`/v1/farms/${farm.id}/plans`) || url.endsWith(`/v1/farms/${farm.id}/harvests`)) return jsonResponse([]);
      if (url.includes('/soil-observations') || url.includes('/soil-tests')) return jsonResponse([]);
      if (url.endsWith('/v1/crop-planning/recommendations')) return jsonResponse({ detail: 'Service unavailable' }, 503);
      return jsonResponse({ detail: 'not found' }, 404);
    }));
    render(<MemoryRouter><FarmsPage /></MemoryRouter>);
    await screen.findByRole('heading', { name: 'Farm records' });
    fireEvent.click(screen.getByRole('button', { name: 'Compare crop options' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('CropPulse is temporarily unavailable');
    expect(screen.getByLabelText(/Elevation in metres/)).toBeInTheDocument();
  });

  it('signs in with a server session and renders only farmer navigation', async () => {
    const calls: { url: string; init?: RequestInit }[] = [];
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); calls.push({ url, init: init ? { ...init, headers: new Headers(init.headers) } : undefined });
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'synthetic-csrf-signature' });
      if (url.endsWith('/v1/me')) return jsonResponse({ detail: 'Sign in required' }, 401);
      if (url.endsWith('/v1/browser-auth/login')) return jsonResponse(farmer);
      if (url.endsWith('/v1/browser-auth/logout')) return new Response(null, { status: 204 });
      if (url.endsWith('/v1/farms')) return jsonResponse([]);
      return jsonResponse({ detail: 'not found' }, 404);
    }));
    render(<MemoryRouter><App /></MemoryRouter>);
    await screen.findByRole('heading', { name: 'Welcome back' });
    fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'synthetic@example.com' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'synthetic-password' } });
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));
    await screen.findByRole('heading', { name: 'Your farm workspace' });
    expect(screen.getByRole('link', { name: /My farms/ })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /Farmer accounts/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /Data review/ })).not.toBeInTheDocument();
    const loginCall = calls.find((call) => call.url.endsWith('/v1/browser-auth/login'));
    expect(loginCall?.init?.credentials).toBe('include');
    expect(new Headers(loginCall?.init?.headers).get('X-CSRF-Token')).toBe('synthetic-csrf-signature');
    expect(new Headers(loginCall?.init?.headers).has('Authorization')).toBe(false);
    await waitFor(() => expect(calls.some((call) => call.url.endsWith('/v1/farms'))).toBe(true));
    expect(window.localStorage.length).toBe(0);
    fireEvent.click(screen.getByRole('button', { name: /Synthetic Farmer/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Sign out' }));
    await screen.findByRole('heading', { name: 'Welcome back' });
    expect(calls.some((call) => call.url.endsWith('/v1/browser-auth/logout'))).toBe(true);
  });

  it('restores the current account after a browser refresh and enforces route roles', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'csrf' });
      if (url.endsWith('/v1/me')) return jsonResponse(farmer);
      if (url.endsWith('/v1/farms')) return jsonResponse([]);
      return jsonResponse({ detail: 'Not found' }, 404);
    }));
    render(<MemoryRouter initialEntries={['/accounts']}><App /></MemoryRouter>);
    await screen.findByRole('heading', { name: 'Access restricted' });
    expect(screen.getByRole('link', { name: /My farms/ })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /Farmer accounts/ })).not.toBeInTheDocument();
  });

  it('shows saved crop-season progress and a planning workspace handoff', async () => {
    const farm = { id: 'farm-workflow', owner_id: farmer.id, name: 'Home farm', district: 'Huye', area_ha: 1 };
    const plan = { id: 'plan-workflow', farm_id: farm.id, district: farm.district, crop: 'Maize', season: 'A', planting_date: '2026-10-01', area_ha: 0.5, plan: {}, verification: 'provisional', status: 'monitoring', actual_planting_date: '2026-10-02' };
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'csrf' });
      if (url.endsWith('/v1/me')) return jsonResponse(farmer);
      if (url.endsWith('/v1/farms')) return jsonResponse([farm]);
      if (url.endsWith(`/v1/farms/${farm.id}/plans`)) return jsonResponse([plan]);
      if (url.endsWith('/v1/browser-auth/streamlit-handoff')) return jsonResponse({ detail: 'Workspace handoff is unavailable.' }, 503);
      return jsonResponse({ detail: 'not found' }, 404);
    }));
    render(<MemoryRouter initialEntries={['/overview']}><App /></MemoryRouter>);
    expect(await screen.findByRole('heading', { name: 'Growing seasons' })).toBeInTheDocument();
    expect(screen.getByText('Record farm work as it happens. Crop stage observations are not available yet.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Open CropPulse workspace' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('CropPulse is temporarily unavailable');
  });

  it('requires explicit account notice acceptance before registration', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'csrf' });
      if (url.endsWith('/v1/me')) return jsonResponse({ detail: 'Sign in required' }, 401);
      return jsonResponse({ detail: 'Unexpected request' }, 404);
    }));
    render(<MemoryRouter><App /></MemoryRouter>);
    await screen.findByRole('heading', { name: 'Welcome back' });
    fireEvent.click(screen.getAllByRole('button', { name: 'Create account' })[0]);
    fireEvent.change(screen.getByLabelText('Your name'), { target: { value: 'Synthetic Person' } });
    fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'synthetic@example.com' } });
    fireEvent.change(screen.getByLabelText(/Password/), { target: { value: 'synthetic-password-123' } });
    fireEvent.click(screen.getByRole('button', { name: 'Create account' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Please accept the account data notice');
  });

  it('lets farmers start a reviewer conversation, read explicitly, and send private text', async () => {
    const conversation = { id: 'conversation-1', other_user_id: 'reviewer-1', other_display_name: 'Synthetic Reviewer', other_role: 'CropPulse reviewer', created_at: '2026-10-20T10:00:00Z', last_message: null, last_message_at: '2026-10-20T10:00:00Z', unread_count: 0 };
    const calls: { url: string; method: string; body?: string }[] = [];
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); const method = init?.method ?? 'GET'; calls.push({ url, method, body: typeof init?.body === 'string' ? init.body : undefined });
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'csrf' });
      if (url.endsWith('/v1/me')) return jsonResponse(farmer);
      if (url.endsWith('/v1/messaging/reviewers')) return jsonResponse([{ id: reviewer.id, display_name: reviewer.display_name, role_label: 'CropPulse reviewer', eligible_districts: ['Huye'] }]);
      if (url.endsWith('/v1/messaging/conversations') && method === 'GET') return jsonResponse(calls.some((call) => call.method === 'POST' && call.url.endsWith('/v1/messaging/conversations')) ? [conversation] : []);
      if (url.endsWith('/v1/messaging/conversations') && method === 'POST') return jsonResponse(conversation);
      if (url.includes('/v1/messaging/conversations/conversation-1/messages?') && method === 'GET') return jsonResponse({ items: [], total: 0, offset: 0, limit: 50 });
      if (url.endsWith('/v1/messaging/conversations/conversation-1/read')) return jsonResponse({ marked_read: 0, read_at: '2026-10-20T10:00:00Z' });
      if (url.endsWith('/v1/messaging/conversations/conversation-1/messages') && method === 'POST') return jsonResponse({ id: 'message-1', sender_id: farmer.id, body: 'Hello reviewer', created_at: '2026-10-20T10:01:00Z', read_at: null }, 201);
      return jsonResponse({ detail: 'not found' }, 404);
    }));
    render(<MemoryRouter initialEntries={['/messages']}><App /></MemoryRouter>);
    expect(await screen.findByRole('heading', { name: 'Messages' })).toBeInTheDocument();
    expect(await screen.findByText('CropPulse reviewer')).toBeInTheDocument();
    expect(screen.getByText('Huye')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Message' }));
    expect(await screen.findByRole('heading', { name: 'Synthetic Reviewer' })).toBeInTheDocument();
    await waitFor(() => expect(calls.some((call) => call.url.endsWith('/v1/messaging/conversations/conversation-1/read'))).toBe(true));
    fireEvent.change(screen.getByLabelText('Write a message'), { target: { value: 'Hello reviewer' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send' }));
    await waitFor(() => expect(calls.some((call) => call.method === 'POST' && call.url.endsWith('/v1/messaging/conversations/conversation-1/messages'))).toBe(true));
    expect(calls.some((call) => call.body === JSON.stringify({ body: 'Hello reviewer' }))).toBe(true);
    expect(screen.getByRole('link', { name: /Private messages/ })).toBeInTheDocument();
  });

  it('shows persisted unread counts to reviewers and exposes messaging load errors', async () => {
    let markedRead = false;
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'csrf' });
      if (url.endsWith('/v1/me')) return jsonResponse(reviewer);
      if (url.endsWith('/v1/messaging/conversations')) return jsonResponse([{ id: 'conversation-unread', other_user_id: farmer.id, other_display_name: farmer.display_name, other_role: 'Farmer', created_at: '2026-10-20T10:00:00Z', last_message: 'Please contact me', last_message_at: '2026-10-20T10:00:00Z', unread_count: markedRead ? 0 : 3 }]);
      if (url.includes('/v1/messaging/conversations/conversation-unread/messages?')) return jsonResponse({ items: [], total: 0, offset: 0, limit: 50 });
      if (url.endsWith('/v1/messaging/conversations/conversation-unread/read')) { markedRead = true; return jsonResponse({ marked_read: 3, read_at: '2026-10-20T10:00:00Z' }); }
      return jsonResponse({ detail: 'not found' }, 404);
    }));
    render(<MemoryRouter initialEntries={['/messages']}><App /></MemoryRouter>);
    expect(await screen.findByRole('button', { name: /3 unread messages/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Synthetic Farmer/ }));
    expect(await screen.findByRole('heading', { name: 'Synthetic Farmer' })).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole('button', { name: /3 unread messages/ })).not.toBeInTheDocument());
  });

  it('shows API failure when reviewer discovery cannot load', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'csrf' });
      if (url.endsWith('/v1/me')) return jsonResponse(farmer);
      if (url.endsWith('/v1/messaging/reviewers')) return jsonResponse({ detail: 'Service unavailable' }, 503);
      if (url.endsWith('/v1/messaging/conversations')) return jsonResponse([]);
      return jsonResponse({ detail: 'not found' }, 404);
    }));
    render(<MemoryRouter initialEntries={['/messages']}><App /></MemoryRouter>);
    expect(await screen.findByRole('alert')).toHaveTextContent('CropPulse is temporarily unavailable');
  });

  it('explains when the configured API is an older server without messaging routes', async () => {
    const calls: { url: string; method: string }[] = [];
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); calls.push({ url, method: init?.method ?? 'GET' });
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'csrf' });
      if (url.endsWith('/v1/me')) return jsonResponse(farmer);
      if (url.endsWith('/v1/messaging/reviewers') || url.endsWith('/v1/messaging/conversations')) return jsonResponse({ detail: 'Not Found' }, 404);
      return jsonResponse({ detail: 'not found' }, 404);
    }));
    render(<MemoryRouter initialEntries={['/messages']}><App /></MemoryRouter>);
    expect(await screen.findByRole('alert')).toHaveTextContent('does not provide the messaging endpoints');
    expect(calls).toContainEqual({ url: 'http://localhost:8001/v1/messaging/reviewers', method: 'GET' });
    expect(calls).toContainEqual({ url: 'http://localhost:8001/v1/messaging/conversations', method: 'GET' });
  });

  it('registers through the cookie session flow without storing a token in browser storage', async () => {
    const calls: { url: string; init?: RequestInit }[] = [];
    let csrfCount = 0;
    let registerCount = 0;
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); calls.push({ url, init: init ? { ...init, headers: new Headers(init.headers) } : undefined });
      if (url.endsWith('/v1/browser-auth/csrf')) {
        csrfCount += 1;
        return jsonResponse({ csrf_token: csrfCount === 1 ? 'stale-registration-csrf' : 'fresh-registration-csrf' });
      }
      if (url.endsWith('/v1/me')) return jsonResponse({ detail: 'Signed out' }, 401);
      if (url.endsWith('/v1/browser-auth/register')) {
        registerCount += 1;
        if (registerCount === 1) return jsonResponse({ detail: 'Request security check failed. Refresh the page and try again.' }, 403);
        return jsonResponse(farmer, 201);
      }
      if (url.endsWith('/v1/farms')) return jsonResponse([]);
      return jsonResponse({ detail: 'Not found' }, 404);
    }));
    render(<MemoryRouter><App /></MemoryRouter>);
    await screen.findByRole('heading', { name: 'Welcome back' });
    fireEvent.click(screen.getByRole('button', { name: 'Create account' }));
    fireEvent.change(screen.getByLabelText('Your name'), { target: { value: 'Synthetic Farmer' } });
    fireEvent.change(screen.getByLabelText('Email address'), { target: { value: farmer.email } });
    fireEvent.change(screen.getByLabelText(/Password/), { target: { value: 'synthetic-password-123' } });
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: 'Create account' }));
    await screen.findByRole('heading', { name: 'Your farm workspace' });
    const call = calls.find((item) => item.url.endsWith('/v1/browser-auth/register'));
    const registrationCalls = calls.filter((item) => item.url.endsWith('/v1/browser-auth/register'));
    expect(new Headers(registrationCalls[0]?.init?.headers).get('X-CSRF-Token')).toBe('stale-registration-csrf');
    expect(new Headers(registrationCalls[1]?.init?.headers).get('X-CSRF-Token')).toBe('fresh-registration-csrf');
    expect(call).toBe(registrationCalls[0]);
    expect(call?.init?.credentials).toBe('include');
    expect(new Headers(call?.init?.headers).has('Authorization')).toBe(false);
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
  });

  it('submits a password recovery request from the sign-in screen', async () => {
    const calls: { url: string; init?: RequestInit }[] = [];
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); calls.push({ url, init });
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'csrf' });
      if (url.endsWith('/v1/me')) return jsonResponse({ detail: 'Sign in required' }, 401);
      if (url.endsWith('/v1/browser-auth/password-recovery')) return jsonResponse({ message: 'If an active account uses that email, a password reset link will arrive shortly.' }, 202);
      return jsonResponse({ detail: 'not found' }, 404);
    }));
    render(<MemoryRouter><App /></MemoryRouter>);
    await screen.findByRole('heading', { name: 'Welcome back' });
    fireEvent.click(screen.getByRole('button', { name: 'Forgot password?' }));
    fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'farmer@example.com' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send reset link' }));
    expect(await screen.findByRole('status')).toHaveTextContent('If an active account uses that email');
    const request = calls.find((call) => call.url.endsWith('/v1/browser-auth/password-recovery'));
    expect(JSON.parse(String(request?.init?.body))).toEqual({ email: 'farmer@example.com' });
  });

  it('explains when the running API is too old to accept password recovery', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'csrf' });
      if (url.endsWith('/v1/me')) return jsonResponse({ detail: 'Sign in required' }, 401);
      if (url.endsWith('/v1/browser-auth/password-recovery')) return jsonResponse({ detail: 'Not Found' }, 404);
      return jsonResponse({ detail: 'not found' }, 404);
    }));
    render(<MemoryRouter><App /></MemoryRouter>);
    await screen.findByRole('heading', { name: 'Welcome back' });
    fireEvent.click(screen.getByRole('button', { name: 'Forgot password?' }));
    fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'farmer@example.com' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send reset link' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('does not support password recovery yet');
  });

  it('completes a token-based password reset from the email link', async () => {
    const calls: { url: string; init?: RequestInit }[] = [];
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); calls.push({ url, init });
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'csrf' });
      if (url.endsWith('/v1/me')) return jsonResponse({ detail: 'Sign in required' }, 401);
      if (url.endsWith('/v1/browser-auth/password-reset/complete')) return jsonResponse({ message: 'Password reset. Sign in with your new password.' });
      return jsonResponse({ detail: 'not found' }, 404);
    }));
    render(<MemoryRouter initialEntries={['/reset-password?token=single-use-token-from-email-1234567890']}><App /></MemoryRouter>);
    await screen.findByRole('heading', { name: 'Choose a new password' });
    fireEvent.change(screen.getByLabelText(/New password/), { target: { value: 'new-long-password-123' } });
    fireEvent.change(screen.getByLabelText('Confirm new password'), { target: { value: 'new-long-password-123' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save new password' }));
    expect(await screen.findByRole('status')).toHaveTextContent('Password reset. Sign in with your new password.');
    const request = calls.find((call) => call.url.endsWith('/v1/browser-auth/password-reset/complete'));
    expect(JSON.parse(String(request?.init?.body))).toEqual({ token: 'single-use-token-from-email-1234567890', new_password: 'new-long-password-123' });
  });

  it('requests email change and requires the explicit account deletion confirmation in settings', async () => {
    const calls: { url: string; init?: RequestInit }[] = [];
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); calls.push({ url, init });
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'csrf' });
      if (url.endsWith('/v1/me')) return jsonResponse(farmer);
      if (url.endsWith('/v1/browser-auth/email-change')) return jsonResponse({ message: 'Check the new email address for a confirmation link.' }, 202);
      if (url.endsWith('/v1/browser-auth/account')) return new Response(null, { status: 204 });
      return jsonResponse({ detail: 'not found' }, 404);
    }));
    render(<MemoryRouter initialEntries={['/settings']}><App /></MemoryRouter>);
    await screen.findByRole('heading', { name: 'Account settings' });
    fireEvent.change(screen.getByLabelText('New email address'), { target: { value: 'new@example.com' } });
    const emailPassword = screen.getAllByLabelText('Current password')[0] as HTMLInputElement;
    expect(emailPassword.type).toBe('password');
    fireEvent.change(emailPassword, { target: { value: 'current-password' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send confirmation link' }));
    expect(await screen.findByText('Check the new email address for a confirmation link.')).toBeInTheDocument();
    expect(JSON.parse(String(calls.find((call) => call.url.endsWith('/email-change'))?.init?.body))).toEqual({ current_password: 'current-password', new_email: 'new@example.com' });
    fireEvent.change(screen.getAllByLabelText('Current password')[1], { target: { value: 'current-password' } });
    fireEvent.change(screen.getByLabelText('Type DELETE to confirm'), { target: { value: 'DELETE' } });
    fireEvent.click(screen.getByRole('button', { name: 'Permanently delete account' }));
    await screen.findByRole('heading', { name: 'Welcome back' });
    expect(JSON.parse(String(calls.find((call) => call.url.endsWith('/browser-auth/account'))?.init?.body))).toEqual({ current_password: 'current-password', confirmation: 'DELETE' });
  });

  it('shows an actionable email delivery error when the server has no mail configuration', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'csrf' });
      if (url.endsWith('/v1/me')) return jsonResponse(farmer);
      if (url.endsWith('/v1/browser-auth/email-change')) return jsonResponse({ detail: 'Account email delivery is not configured by the server administrator.' }, 503);
      return jsonResponse({ detail: 'not found' }, 404);
    }));
    render(<MemoryRouter initialEntries={['/settings']}><App /></MemoryRouter>);
    await screen.findByRole('heading', { name: 'Account settings' });
    fireEvent.change(screen.getByLabelText('New email address'), { target: { value: 'new@example.com' } });
    fireEvent.change(screen.getAllByLabelText('Current password')[0], { target: { value: 'current-password' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send confirmation link' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Account email delivery is not configured');
  });

  it('shows an API error instead of hiding failed farm loads', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'csrf' });
      if (url.endsWith('/v1/me')) return jsonResponse(farmer);
      if (url.endsWith('/v1/farms')) return jsonResponse({ detail: 'database unavailable' }, 503);
      return jsonResponse({ detail: 'not found' }, 404);
    }));
    render(<MemoryRouter initialEntries={['/farms']}><App /></MemoryRouter>);
    await screen.findByRole('heading', { name: 'Farm records' });
    expect(await screen.findByText('No farms saved yet')).toBeInTheDocument();
    expect(await screen.findByRole('alert')).toHaveTextContent('temporarily unavailable');
  });

  it('returns to sign-in when the server rejects an expired active session', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'csrf' });
      if (url.endsWith('/v1/me')) return jsonResponse(farmer);
      if (url.endsWith('/v1/farms')) return jsonResponse({ detail: 'Session expired or signed out.' }, 401);
      return jsonResponse({ detail: 'not found' }, 404);
    }));
    render(<MemoryRouter initialEntries={['/farms']}><App /></MemoryRouter>);
    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('Your session ended. Sign in again to continue.');
  });

  it('creates a farm through the persistent API workflow', async () => {
    let farms: { id: string; owner_id: string; name: string; district: string; area_ha: number }[] = [];
    let savedFarmPayload: { name: string; district: string; area_ha: number } | null = null;
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'csrf' });
      if (url.endsWith('/v1/me')) return jsonResponse(farmer);
      if (url.endsWith('/v1/farms') && init?.method === 'POST') {
        const body = JSON.parse(String(init.body)) as { name: string; district: string; area_ha: number };
        savedFarmPayload = body;
        const row = { id: 'farm-1', owner_id: farmer.id, name: body.name, district: body.district, area_ha: body.area_ha };
        farms = [row]; return jsonResponse(row, 201);
      }
      if (url.endsWith('/v1/farms')) return jsonResponse(farms);
      if (url.includes('/activities')) return jsonResponse([]);
      return jsonResponse({ detail: 'not found' }, 404);
    }));
    render(<MemoryRouter initialEntries={['/farms']}><App /></MemoryRouter>);
    await screen.findByRole('heading', { name: 'Farm records' });
    fireEvent.click(screen.getByRole('button', { name: /Add a farm/ }));
    fireEvent.change(screen.getByLabelText('Farm name'), { target: { value: 'Synthetic test plot' } });
    fireEvent.change(screen.getByLabelText('Area (hectares)'), { target: { value: '0.5' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save farm' }));
    expect(await screen.findByText('Farm profile saved.')).toBeInTheDocument();
    expect(await screen.findByRole('option', { name: /Synthetic test plot/ })).toBeInTheDocument();
    expect(savedFarmPayload).toEqual({ name: 'Synthetic test plot', district: 'Huye', area_ha: 0.5 });
    expect(screen.queryByLabelText('Farm name')).not.toBeInTheDocument();
  });

  it('loads and creates saved crop plans, then records a separately entered actual planting date', async () => {
    const farm = { id: 'farm-plan', owner_id: farmer.id, name: 'Synthetic plan farm', district: 'Huye', area_ha: 1.5 };
    const calls: { url: string; init?: RequestInit }[] = [];
    let plans: Record<string, unknown>[] = [];
    let activities: Record<string, unknown>[] = [];
    let rejectNextPlanting = true;
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); calls.push({ url, init });
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'csrf' });
      if (url.endsWith('/v1/me')) return jsonResponse(farmer);
      if (url.endsWith('/v1/farms')) return jsonResponse([farm]);
      if (url.includes('/fields')) return jsonResponse([]);
      if (url.includes('/activities')) return jsonResponse(activities);
      if (url.includes('/harvests')) return jsonResponse([]);
      if (url.includes('/irrigation-records')) return jsonResponse([]);
      if (url.endsWith('/timeline')) return jsonResponse({ entries: [], has_more: false });
      if (url.includes('/soil-observations') || url.includes('/soil-tests')) return jsonResponse([]);
      if (url.endsWith('/plans') && init?.method === 'POST') {
        const body = JSON.parse(String(init.body));
        const row = { ...body, id: 'plan-1', farm_id: farm.id, verification: 'provisional', status: 'planned', actual_planting_date: null };
        plans = [row]; return jsonResponse(row, 201);
      }
      if (url.includes('/plans/') && init?.method === 'PUT') {
        const body = JSON.parse(String(init.body));
        plans = [{ ...plans[0], ...body }]; return jsonResponse(plans[0]);
      }
      if (url.includes('/plans/') && url.endsWith('/status') && init?.method === 'PATCH') {
        const body = JSON.parse(String(init.body));
        if (body.status === 'planted' && rejectNextPlanting) {
          rejectNextPlanting = false;
          return jsonResponse({ detail: 'The plan transition was rejected.' }, 409);
        }
        plans = plans.map((plan) => ({ ...plan, status: body.status, actual_planting_date: body.actual_planting_date ?? null }));
        if (body.status === 'planted') activities = [{ id: 'planting-activity-1', farm_id: farm.id, district: farm.district, crop: 'Beans', season: 'B', activity_type: 'Planting', event_date: body.actual_planting_date, quantity: null, unit: null, notes: 'Farmer confirmed planting.', verification: 'user_reported', review_status: 'pending' }];
        return jsonResponse(plans[0]);
      }
      if (url.endsWith('/plans')) return jsonResponse(plans);
      return jsonResponse({ detail: 'not found' }, 404);
    }));
    render(<MemoryRouter initialEntries={['/farms']}><App /></MemoryRouter>);
    await screen.findByRole('heading', { name: 'Farm records' });
    expect(await screen.findByText('No crop plans for this farm')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Create crop plan' }));
    fireEvent.change(screen.getByLabelText('Crop'), { target: { value: 'Beans' } });
    fireEvent.change(screen.getAllByLabelText('Season')[1], { target: { value: 'B' } });
    fireEvent.change(screen.getByLabelText('Planning notes (not verified)'), { target: { value: 'Synthetic farmer note' } });
    fireEvent.change(screen.getByLabelText('Planned area (hectares)'), { target: { value: '0.75' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save crop plan' }));
    expect(await screen.findByText('Crop plan saved. Its guidance remains provisional.')).toBeInTheDocument();
    expect(await screen.findByRole('heading', { name: /Beans.*Season B/ })).toBeInTheDocument();
    expect(screen.getByText('Not recorded')).toBeInTheDocument();
    const create = calls.find((call) => call.url.endsWith('/plans') && call.init?.method === 'POST');
    expect(JSON.parse(String(create?.init?.body))).toMatchObject({ district: 'Huye', crop: 'Beans', season: 'B', area_ha: 0.75, plan: { farmer_notes: 'Synthetic farmer note' } });
    expect(screen.getByText(/Verification: provisional/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Edit plan' }));
    fireEvent.change(screen.getByLabelText('Planning notes (not verified)'), { target: { value: 'Updated farmer note' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }));
    expect(await screen.findByText('Crop plan changes saved.')).toBeInTheDocument();
    const edit = calls.find((call) => call.url.endsWith('/plans/plan-1') && call.init?.method === 'PUT');
    expect(JSON.parse(String(edit?.init?.body))).toMatchObject({ crop: 'Beans', plan: { farmer_notes: 'Updated farmer note' } });
    const actualDate = new Date().toISOString().slice(0, 10);
    fireEvent.click(screen.getByRole('button', { name: 'Mark planted' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Enter the actual planting date');
    expect(calls.some((call) => call.url.endsWith('/status'))).toBe(false);
    fireEvent.change(screen.getByLabelText('Actual planting date for Beans'), { target: { value: actualDate } });
    fireEvent.click(screen.getByRole('button', { name: 'Mark planted' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('transition was rejected');
    expect(screen.queryByText('Crop plan updated to planted.')).not.toBeInTheDocument();
    expect(screen.queryByText('Planting')).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Beans.*Season B/ }).parentElement).toHaveTextContent('planned');
    fireEvent.click(screen.getByRole('button', { name: 'Mark planted' }));
    await screen.findByText('Crop plan updated to planted.');
    expect(await screen.findByText('Planting')).toBeInTheDocument();
    expect(screen.getByText('Farmer confirmed planting.')).toBeInTheDocument();
    const update = calls.find((call) => call.url.endsWith('/plan-1/status'));
    expect(JSON.parse(String(update?.init?.body))).toEqual({ status: 'planted', actual_planting_date: actualDate });
    expect(screen.getAllByText(actualDate)).toHaveLength(3);
    expect(screen.queryByRole('button', { name: 'Mark completed' })).not.toBeInTheDocument();
  });

  it('creates and corrects a farmer-reported harvest with the calculated yield', async () => {
    const farm = { id: 'harvest-farm', owner_id: farmer.id, name: 'Synthetic harvest farm', district: 'Huye', area_ha: 1 };
    const calls: { url: string; init?: RequestInit }[] = [];
    let records: Record<string, unknown>[] = [];
    let observations: Record<string, unknown>[] = [];
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); calls.push({ url, init });
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'csrf' });
      if (url.endsWith('/v1/me')) return jsonResponse(farmer);
      if (url.endsWith('/v1/farms')) return jsonResponse([farm]);
      if (url.includes('/fields')) return jsonResponse([]);
      if (url.includes('/activities')) return jsonResponse([]);
      if (url.endsWith('/plans')) return jsonResponse([]);
      if (url.endsWith('/harvests') && init?.method === 'POST') {
        const body = JSON.parse(String(init.body));
        const row = { ...body, id: 'harvest-1', farm_id: farm.id, yield_kg_ha: 400, yield_calculation: '(200 kg x 1 kg/kg) / (0.5 ha x 1 ha/ha) = 400 kg/ha', created_at: '2026-10-28T10:00:00Z', updated_at: '2026-10-28T10:00:00Z' };
        records = [row]; return jsonResponse(row, 201);
      }
      if (url.endsWith('/harvests/harvest-1') && init?.method === 'PUT') {
        const body = JSON.parse(String(init.body));
        const row = { ...records[0], ...body, yield_kg_ha: 500, yield_calculation: '(500 kg x 1 kg/kg) / (1 ha x 1 ha/ha) = 500 kg/ha', updated_at: '2026-10-28T11:00:00Z' };
        records = [row]; return jsonResponse(row);
      }
      if (url.includes('/observations') && init?.method === 'POST') {
        const body = JSON.parse(String(init.body));
        const row = { ...body, id: 'observation-1', harvest_id: 'harvest-1', created_at: '2026-10-28T12:00:00Z', updated_at: '2026-10-28T12:00:00Z' };
        observations = [row]; return jsonResponse(row, 201);
      }
      if (url.includes('/observations/observation-1') && init?.method === 'PUT') {
        const body = JSON.parse(String(init.body));
        const row = { ...observations[0], ...body, updated_at: '2026-10-28T13:00:00Z' };
        observations = [row]; return jsonResponse(row);
      }
      if (url.includes('/observations')) return jsonResponse(observations);
      if (url.endsWith('/harvests')) return jsonResponse(records);
      return jsonResponse({ detail: 'not found' }, 404);
    }));

    render(<MemoryRouter initialEntries={['/farms']}><App /></MemoryRouter>);
    await screen.findByRole('heading', { name: 'Farm records' });
    await screen.findByLabelText('Active farm');
    fireEvent.click(screen.getByRole('button', { name: 'Record harvest' }));
    fireEvent.change(screen.getByLabelText('Harvested area'), { target: { value: '0.5' } });
    fireEvent.change(screen.getByLabelText('Harvest quantity'), { target: { value: '200' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save harvest' }));

    expect(await screen.findByText('Harvest record saved as farmer reported.')).toBeInTheDocument();
    expect(await screen.findByText('400 kg/ha')).toBeInTheDocument();
    expect(screen.getByText('(200 kg x 1 kg/kg) / (0.5 ha x 1 ha/ha) = 400 kg/ha')).toBeInTheDocument();
    const create = calls.find((call) => call.url.endsWith('/harvests') && call.init?.method === 'POST');
    expect(JSON.parse(String(create?.init?.body))).toMatchObject({
      crop: 'Maize', season: 'A', harvested_area: 0.5, area_unit: 'ha', quantity: 200, quantity_unit: 'kg',
      field_id: null, crop_plan_id: null, loss_quantity: null,
    });

    fireEvent.click(screen.getByRole('button', { name: 'Edit' }));
    fireEvent.change(screen.getByLabelText('Harvest quantity'), { target: { value: '500' } });
    fireEvent.click(screen.getByRole('button', { name: 'Update harvest' }));
    expect(await screen.findByText('Harvest record updated.')).toBeInTheDocument();
    expect(await screen.findByText('500 kg/ha')).toBeInTheDocument();
    expect(calls.some((call) => call.url.endsWith('/harvests/harvest-1') && call.init?.method === 'PUT')).toBe(true);

    fireEvent.click(screen.getByRole('button', { name: 'Add observation' }));
    fireEvent.change(screen.getByLabelText('Handling / storage method (optional)'), { target: { value: 'Synthetic storage method' } });
    fireEvent.change(screen.getByLabelText('Quantity stored (optional)'), { target: { value: '100' } });
    fireEvent.change(screen.getByLabelText('Quantity lost or damaged (optional)'), { target: { value: '2' } });
    fireEvent.change(screen.getByLabelText('Observed condition (optional)'), { target: { value: 'Synthetic observation' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save observation' }));
    expect(await screen.findByText('Observation saved as farmer reported.')).toBeInTheDocument();
    expect(await screen.findByText('Handling / storage method: Synthetic storage method')).toBeInTheDocument();
    const observationCreate = calls.find((call) => call.url.endsWith('/harvests/harvest-1/observations') && call.init?.method === 'POST');
    expect(JSON.parse(String(observationCreate?.init?.body))).toMatchObject({ stored_quantity: 100, stored_unit: 'kg', lost_quantity: 2, lost_unit: 'kg' });

    fireEvent.click(screen.getByRole('button', { name: 'Correct entry' }));
    fireEvent.change(screen.getByLabelText('Observed condition (optional)'), { target: { value: 'Corrected condition' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save correction' }));
    expect(await screen.findByText('Observation updated as farmer reported.')).toBeInTheDocument();
    expect(await screen.findByText('Observed condition: Corrected condition')).toBeInTheDocument();
    expect(calls.some((call) => call.url.endsWith('/observations/observation-1') && call.init?.method === 'PUT')).toBe(true);
    expect(records[0].quantity).toBe(500);
  });

  it('shows post-harvest observation load and save failures without false success', async () => {
    const farm = { id: 'observation-error-farm', owner_id: farmer.id, name: 'Synthetic observation farm', district: 'Huye', area_ha: 1 };
    const harvest = { id: 'harvest-error-1', farm_id: farm.id, crop: 'Beans', season: 'A', harvest_date: '2026-10-01', harvested_area: 1, area_unit: 'ha', quantity: 100, quantity_unit: 'kg', loss_quantity: null, post_harvest_observations: null, notes: null, yield_kg_ha: 100, yield_calculation: 'test only', created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:00Z' };
    let failLoad = true;
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'csrf' });
      if (url.endsWith('/v1/me')) return jsonResponse(farmer);
      if (url.endsWith('/v1/farms')) return jsonResponse([farm]);
      if (url.includes('/fields') || url.includes('/activities') || url.endsWith('/plans')) return jsonResponse([]);
      if (url.includes('/irrigation-records')) return jsonResponse([]);
      if (url.endsWith('/harvests')) return jsonResponse([harvest]);
      if (url.includes('/observations') && init?.method === 'POST') return jsonResponse({ detail: 'Observation could not be saved.' }, 422);
      if (url.includes('/observations') && failLoad) { failLoad = false; return jsonResponse({ detail: 'Observation history unavailable.' }, 503); }
      if (url.includes('/observations')) return jsonResponse([]);
      if (url.endsWith('/timeline')) return jsonResponse({ entries: [], has_more: false });
      if (url.includes('/soil-observations') || url.includes('/soil-tests')) return jsonResponse([]);
      return jsonResponse({ detail: 'not found' }, 404);
    }));
    render(<MemoryRouter initialEntries={['/farms']}><App /></MemoryRouter>);
    await screen.findByRole('heading', { name: 'Farm records' });
    expect(await screen.findByRole('alert')).toHaveTextContent('Harvest records could not be loaded.');
    expect(screen.getByRole('alert')).toHaveTextContent('migrations 0016–0018');
    fireEvent.click(screen.getByRole('button', { name: 'Add observation' }));
    fireEvent.click(screen.getByRole('button', { name: 'Save observation' }));
    expect(await screen.findByText('Observation could not be saved.')).toBeInTheDocument();
    expect(screen.queryByText('Observation saved as farmer reported.')).not.toBeInTheDocument();
  });

  it('keeps harvest form data and reports API validation errors', async () => {
    const farm = { id: 'harvest-error-farm', owner_id: farmer.id, name: 'Synthetic harvest farm', district: 'Huye', area_ha: 1 };
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'csrf' });
      if (url.endsWith('/v1/me')) return jsonResponse(farmer);
      if (url.endsWith('/v1/farms')) return jsonResponse([farm]);
      if (url.includes('/fields') || url.includes('/activities') || url.endsWith('/plans')) return jsonResponse([]);
      if (url.includes('/irrigation-records')) return jsonResponse([]);
      if (url.endsWith('/harvests') && init?.method === 'POST') return jsonResponse({ detail: 'Harvest date cannot be in the future.' }, 422);
      if (url.endsWith('/harvests')) return jsonResponse([]);
      if (url.endsWith('/timeline')) return jsonResponse({ entries: [], has_more: false });
      if (url.includes('/soil-observations') || url.includes('/soil-tests')) return jsonResponse([]);
      return jsonResponse({ detail: 'not found' }, 404);
    }));
    render(<MemoryRouter initialEntries={['/farms']}><App /></MemoryRouter>);
    await screen.findByRole('heading', { name: 'Farm records' });
    await screen.findByLabelText('Active farm');
    fireEvent.click(screen.getByRole('button', { name: 'Record harvest' }));
    fireEvent.change(screen.getByLabelText('Harvested area'), { target: { value: '0.25' } });
    fireEvent.change(screen.getByLabelText('Harvest quantity'), { target: { value: '80' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save harvest' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Harvest date cannot be in the future.');
    expect(screen.getByLabelText('Harvested area')).toHaveValue(0.25);
    expect(screen.getByLabelText('Harvest quantity')).toHaveValue(80);
  });

  it('does not show a previous farm crop plan after switching farms while its request is pending', async () => {
    const farms = [
      { id: 'farm-one', owner_id: farmer.id, name: 'First farm', district: 'Huye', area_ha: 1 },
      { id: 'farm-two', owner_id: farmer.id, name: 'Second farm', district: 'Kayonza', area_ha: 2 },
    ];
    let resolveFirst!: (response: Response) => void;
    const firstPlans = new Promise<Response>((resolve) => { resolveFirst = resolve; });
    const first = { id: 'plan-old', farm_id: 'farm-one', district: 'Huye', crop: 'Maize', season: 'A', planting_date: '2026-10-01', area_ha: 1, plan: {}, verification: 'provisional', status: 'planned', actual_planting_date: null };
    const second = { ...first, id: 'plan-new', farm_id: 'farm-two', district: 'Kayonza', crop: 'Beans', season: 'B' };
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'csrf' });
      if (url.endsWith('/v1/me')) return jsonResponse(farmer);
      if (url.endsWith('/v1/farms')) return jsonResponse(farms);
      if (url.includes('/fields')) return jsonResponse([]);
      if (url.endsWith('/farm-one/plans')) return firstPlans;
      if (url.endsWith('/farm-two/plans')) return jsonResponse([second]);
      if (url.includes('/activities')) return jsonResponse([]);
      return jsonResponse({ detail: 'not found' }, 404);
    }));
    render(<MemoryRouter initialEntries={['/farms']}><App /></MemoryRouter>);
    await screen.findByRole('heading', { name: 'Farm records' });
    fireEvent.change(await screen.findByLabelText('Active farm'), { target: { value: 'farm-two' } });
    expect(await screen.findByRole('heading', { name: /Beans.*Season B/ })).toBeInTheDocument();
    resolveFirst(jsonResponse([first]));
    await waitFor(() => expect(screen.queryByRole('heading', { name: /Maize.*Season A/ })).not.toBeInTheDocument());
    expect(screen.getByText(/Kayonza.*1 ha.*Verification: provisional/)).toBeInTheDocument();
  });

  it('shows crop-plan loading and error states and retries the selected farm request', async () => {
    const farm = { id: 'farm-retry', owner_id: farmer.id, name: 'Retry farm', district: 'Huye', area_ha: 1 };
    let resolvePlans!: (response: Response) => void;
    const firstRequest = new Promise<Response>((resolve) => { resolvePlans = resolve; });
    let requestCount = 0;
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'csrf' });
      if (url.endsWith('/v1/me')) return jsonResponse(farmer);
      if (url.endsWith('/v1/farms')) return jsonResponse([farm]);
      if (url.includes('/fields')) return jsonResponse([]);
      if (url.includes('/activities')) return jsonResponse([]);
      if (url.endsWith('/harvests')) return jsonResponse([]);
      if (url.includes('/irrigation-records')) return jsonResponse([]);
      if (url.endsWith('/timeline')) return jsonResponse({ entries: [], has_more: false });
      if (url.includes('/soil-observations') || url.includes('/soil-tests')) return jsonResponse([]);
      if (url.endsWith('/plans')) { requestCount += 1; return requestCount === 1 ? firstRequest : jsonResponse([]); }
      return jsonResponse({ detail: 'not found' }, 404);
    }));
    render(<MemoryRouter initialEntries={['/farms']}><App /></MemoryRouter>);
    await screen.findByRole('heading', { name: 'Farm records' });
    expect(await screen.findByText(/Loading crop plans/)).toBeInTheDocument();
    resolvePlans(jsonResponse({ detail: 'temporary failure' }, 503));
    expect(await screen.findByRole('alert')).toHaveTextContent('temporarily unavailable');
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByText('No crop plans for this farm')).toBeInTheDocument();
    expect(requestCount).toBe(2);
  });

  it('keeps crop-plan input on save failure and prevents duplicate submissions', async () => {
    const farm = { id: 'farm-error', owner_id: farmer.id, name: 'Synthetic farm', district: 'Huye', area_ha: 1 };
    let resolvePost!: (response: Response) => void;
    const post = new Promise<Response>((resolve) => { resolvePost = resolve; });
    let postCount = 0;
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'csrf' });
      if (url.endsWith('/v1/me')) return jsonResponse(farmer);
      if (url.endsWith('/v1/farms')) return jsonResponse([farm]);
      if (url.includes('/fields')) return jsonResponse([]);
      if (url.includes('/activities')) return jsonResponse([]);
      if (url.includes('/harvests')) return jsonResponse([]);
      if (url.includes('/irrigation-records')) return jsonResponse([]);
      if (url.endsWith('/timeline')) return jsonResponse({ entries: [], has_more: false });
      if (url.includes('/soil-observations') || url.includes('/soil-tests')) return jsonResponse([]);
      if (url.endsWith('/plans') && init?.method === 'POST') { postCount += 1; return post; }
      if (url.endsWith('/plans')) return jsonResponse([]);
      return jsonResponse({ detail: 'not found' }, 404);
    }));
    render(<MemoryRouter initialEntries={['/farms']}><App /></MemoryRouter>);
    await screen.findByRole('heading', { name: 'Farm records' });
    await screen.findByLabelText('Active farm');
    fireEvent.click(screen.getByRole('button', { name: 'Create crop plan' }));
    fireEvent.change(screen.getByLabelText('Planning notes (not verified)'), { target: { value: 'Keep this after an error' } });
    fireEvent.change(screen.getByLabelText('Planned area (hectares)'), { target: { value: '0.5' } });
    const saveButton = screen.getByRole('button', { name: 'Save crop plan' });
    fireEvent.click(saveButton);
    await waitFor(() => expect(postCount).toBe(1));
    expect(saveButton).toBeDisabled();
    fireEvent.click(saveButton);
    expect(postCount).toBe(1);
    resolvePost(jsonResponse({ detail: 'temporary failure' }, 503));
    expect(await screen.findByRole('alert')).toHaveTextContent('temporarily unavailable');
    expect(screen.getByLabelText('Planning notes (not verified)')).toHaveValue('Keep this after an error');
  });

  it('requires a reason and confirmation before recording reviewer decisions', async () => {
    const item = { id: 'activity-1', farm_id: 'farm-1', farm_name: 'Synthetic plot', district: 'Huye', crop: 'Maize', season: 'A', activity_type: 'Harvest', event_date: '2026-07-01', area_ha: 0.5, quantity: 100, unit: 'kg', amount_rwf: null, notes: 'Synthetic report', verification: 'user_reported', review_status: 'pending', review_history: [] };
    let decision = '';
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'csrf' });
      if (url.endsWith('/v1/me')) return jsonResponse(reviewer);
      if (url.includes('/v1/reviewer/activities') && init?.method === 'POST') { decision = JSON.parse(String(init.body)).decision; return jsonResponse({ decision }, 200); }
      if (url.includes('/v1/reviewer/activities')) return jsonResponse([{ ...item, review_status: decision || 'pending', review_history: decision ? [{ decision, reason: 'Synthetic review rationale', reviewer_id: reviewer.id, created_at: '2026-07-02T09:00:00Z' }] : [] }]);
      return jsonResponse({ detail: 'not found' }, 404);
    }));
    render(<MemoryRouter initialEntries={['/review']}><App /></MemoryRouter>);
    await screen.findByRole('heading', { name: 'Review queue' });
    expect(screen.getByRole('link', { name: /Data review/ })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /Farmer accounts/ })).not.toBeInTheDocument();
    expect(await screen.findByText('Synthetic report')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Decision reason'), { target: { value: 'Please confirm the recorded amount' } });
    fireEvent.click(screen.getByRole('button', { name: 'Mark reviewed' }));
    const dialog = screen.getByRole('dialog');
    expect(within(dialog).getByText(/original farmer report will remain unchanged/)).toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole('button', { name: 'Mark reviewed' }));
    await waitFor(() => expect(decision).toBe('approved_as_reviewed'));
  });

  it('confirms and audits administrator account suspension actions', async () => {
    const target = { id: 'target-1', email: 'target@example.com', display_name: 'Synthetic target', role: 'farmer', status: 'active', created_at: '2026-01-01T00:00:00Z', farm_count: 1 };
    let currentStatus = 'active';
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'csrf' });
      if (url.endsWith('/v1/me')) return jsonResponse(admin);
      if (url.includes('/v1/admin/farmers/') && url.endsWith('/status')) { currentStatus = JSON.parse(String(init?.body)).status; return jsonResponse({ id: target.id, status: currentStatus }); }
      if (url.includes('/v1/admin/farmers')) return jsonResponse([{ ...target, status: currentStatus }]);
      if (url.endsWith('/v1/admin/overview')) return jsonResponse({ accounts: { total: 2, active: 2, suspended: 0 }, farms: 1, farmer_reported_activities: 0, awaiting_review: 0, farms_by_district: [], reported_activities_by_crop: [], health: { api: 'available', database: 'available' }, definitions: {} });
      return jsonResponse({ detail: 'not found' }, 404);
    }));
    render(<MemoryRouter initialEntries={['/accounts']}><App /></MemoryRouter>);
    await screen.findByRole('heading', { name: 'Farmer accounts' });
    expect(await screen.findByText('Synthetic target')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Suspend' }));
    const dialog = screen.getByRole('dialog');
    fireEvent.change(within(dialog).getByLabelText('Reason for this action'), { target: { value: 'Synthetic policy test' } });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Suspend account' }));
    expect(await screen.findByText('Account suspended.')).toBeInTheDocument();
    await waitFor(() => expect(currentStatus).toBe('suspended'));
  });

  it('shows a loading state while waiting for farm records, then an empty state', async () => {
    let resolveFarms!: (response: Response) => void;
    const farmsRequest = new Promise<Response>((resolve) => { resolveFarms = resolve; });
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'csrf' });
      if (url.endsWith('/v1/me')) return jsonResponse(farmer);
      if (url.endsWith('/v1/farms')) return farmsRequest;
      return jsonResponse({ detail: 'not found' }, 404);
    }));
    render(<MemoryRouter initialEntries={['/farms']}><App /></MemoryRouter>);
    expect(await screen.findByRole('status')).toHaveTextContent('Loading records');
    resolveFarms(jsonResponse([]));
    expect(await screen.findByText('No farms saved yet')).toBeInTheDocument();
  });
});
