import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { SoilRecords } from './SoilRecords';

afterEach(() => vi.unstubAllGlobals());

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

describe('farmer soil records', () => {
  it('creates, lists and corrects a farmer-reported soil observation', async () => {
    let observations: Record<string, unknown>[] = [];
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'soil-test-csrf' });
      if (url.endsWith('/soil-observations') && init?.method === 'POST') {
        const payload = JSON.parse(String(init.body)) as Record<string, unknown>;
        const created = { ...payload, id: 'soil-observation-1', farm_id: 'farm-1', verification: 'farmer_reported', created_at: '2026-10-28T00:00:00Z', updated_at: '2026-10-28T00:00:00Z' };
        observations = [created]; return jsonResponse(created, 201);
      }
      if (url.endsWith('/soil-observations/soil-observation-1') && init?.method === 'PUT') {
        const payload = JSON.parse(String(init.body)) as Record<string, unknown>;
        const updated = { ...observations[0], ...payload, updated_at: '2026-10-28T00:01:00Z' };
        observations = [updated]; return jsonResponse(updated);
      }
      if (url.endsWith('/soil-observations')) return jsonResponse(observations);
      if (url.endsWith('/soil-tests')) return jsonResponse([]);
      return jsonResponse({ detail: 'not found' }, 404);
    }));

    render(<SoilRecords farmId="farm-1" fields={[]} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Record observation' }));
    fireEvent.change(screen.getByLabelText('Soil type or description (optional)'), { target: { value: 'Farmer described soil' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save observation' }));
    expect(await screen.findByText('Farmer described soil')).toBeInTheDocument();
    expect(screen.getByText(/Farm-level record · Farmer reported/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Correct' }));
    fireEvent.change(screen.getByLabelText('Soil type or description (optional)'), { target: { value: 'Corrected description' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save correction' }));
    expect(await screen.findByText('Corrected description')).toBeInTheDocument();
    await waitFor(() => expect(observations[0].soil_description).toBe('Corrected description'));
  });

  it('keeps blank test measurements null and preserves explicitly entered zero with its unit', async () => {
    let tests: Record<string, unknown>[] = [];
    const calls: { url: string; method?: string; body?: Record<string, unknown> }[] = [];
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); const body = init?.body ? JSON.parse(String(init.body)) as Record<string, unknown> : undefined;
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'soil-test-csrf' });
      calls.push({ url, method: init?.method, body });
      if (url.endsWith('/soil-tests') && init?.method === 'POST') {
        const created = { ...body, id: 'soil-test-1', farm_id: 'farm-1', verification: 'farmer_reported', created_at: '2026-10-28T00:00:00Z', updated_at: '2026-10-28T00:00:00Z' };
        tests = [created]; return jsonResponse(created, 201);
      }
      if (url.endsWith('/soil-tests/soil-test-1') && init?.method === 'PUT') {
        const updated = { ...tests[0], ...body, updated_at: '2026-10-28T00:01:00Z' };
        tests = [updated]; return jsonResponse(updated);
      }
      if (url.endsWith('/soil-tests')) return jsonResponse(tests);
      if (url.endsWith('/soil-observations')) return jsonResponse([]);
      return jsonResponse({ detail: 'not found' }, 404);
    }));

    render(<SoilRecords farmId="farm-1" fields={[]} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Record soil test' }));
    fireEvent.change(screen.getByLabelText('pH (unitless, 0–14; optional)'), { target: { value: '0' } });
    fireEvent.change(screen.getByLabelText('Nitrogen value (optional)'), { target: { value: '0' } });
    fireEvent.change(screen.getByLabelText('Nitrogen unit'), { target: { value: 'mg/kg' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save test record' }));
    expect(await screen.findByText('0 mg/kg')).toBeInTheDocument();
    expect(screen.getAllByText('Not recorded').length).toBeGreaterThan(0);
    const saved = calls.find((call) => call.url.endsWith('/soil-tests') && call.method === 'POST')?.body;
    expect(saved?.ph_value).toBe(0);
    expect(saved?.nitrogen_value).toBe(0);
    expect(saved?.nitrogen_unit).toBe('mg/kg');
    expect(saved?.phosphorus_value).toBeNull();
    expect(saved?.phosphorus_unit).toBeNull();

    fireEvent.click(screen.getByRole('button', { name: 'Correct' }));
    fireEvent.change(screen.getByLabelText('pH (unitless, 0–14; optional)'), { target: { value: '6.4' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save correction' }));
    expect(await screen.findByText('6.4')).toBeInTheDocument();
    expect(calls.some((call) => call.url.endsWith('/soil-tests/soil-test-1') && call.method === 'PUT')).toBe(true);
  });

  it('shows API load and validation errors and keeps the form open after a rejected submission', async () => {
    let failLoad = true;
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'soil-test-csrf' });
      if (url.endsWith('/soil-observations') && init?.method === 'POST') return jsonResponse({ detail: 'Soil description was invalid.' }, 422);
      if (url.endsWith('/soil-observations') && failLoad) { failLoad = false; return jsonResponse({ detail: 'Temporary load failure.' }, 503); }
      if (url.endsWith('/soil-observations')) return jsonResponse([]);
      if (url.endsWith('/soil-tests')) return jsonResponse([]);
      return jsonResponse({ detail: 'not found' }, 404);
    }));

    render(<SoilRecords farmId="farm-1" fields={[]} />);
    expect(await screen.findByRole('alert')).toHaveTextContent('temporarily unavailable');
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Record observation' }));
    fireEvent.change(screen.getByLabelText('Soil type or description (optional)'), { target: { value: 'Keep this text' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save observation' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Soil description was invalid.');
    expect(screen.getByDisplayValue('Keep this text')).toBeInTheDocument();
  });
});
