import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { FarmsPage } from './pages';

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => { resolve = done; });
  return { promise, resolve };
}

const farms = [
  { id: 'farm-a', owner_id: 'farmer-1', name: 'North farm', district: 'Huye', area_ha: 1 },
  { id: 'farm-b', owner_id: 'farmer-1', name: 'South farm', district: 'Nyanza', area_ha: 2 },
];

function activity(id: string, farmId: string, activityType: string) {
  return { id, farm_id: farmId, district: farmId === 'farm-a' ? 'Huye' : 'Nyanza', crop: 'Maize', season: 'A',
    activity_type: activityType, event_date: '2026-10-20', quantity: null, unit: null, notes: '',
    verification: 'farmer_reported', review_status: 'awaiting_review' };
}

function field(id: string, farmId: string, name: string) {
  return { id, farm_id: farmId, name, area_ha: 1, latitude: null, longitude: null,
    archived_at: null, created_at: '2026-10-20T00:00:00Z', updated_at: '2026-10-20T00:00:00Z' };
}

afterEach(() => { vi.unstubAllGlobals(); });

describe('FarmsPage', () => {
  it('keeps late responses from a previously selected farm out of the current view', async () => {
    const northActivities = deferred<Response>();
    const northFields = deferred<Response>();
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/v1/farms')) return jsonResponse(farms);
      if (url.endsWith('/v1/farms/farm-a/activities')) return northActivities.promise;
      if (url.endsWith('/v1/farms/farm-a/fields')) return northFields.promise;
      if (url.endsWith('/v1/farms/farm-b/activities')) return jsonResponse([activity('activity-b', 'farm-b', 'South farm activity')]);
      if (url.endsWith('/v1/farms/farm-b/fields')) return jsonResponse([field('field-b', 'farm-b', 'South field')]);
      if (url.endsWith('/plans')) return jsonResponse([]);
      return jsonResponse({ detail: 'not found' }, 404);
    }));

    render(<FarmsPage />);
    const farmSelector = await screen.findByLabelText('Active farm');
    expect(await screen.findByText('Loading fields…')).toBeInTheDocument();
    fireEvent.change(farmSelector, { target: { value: 'farm-b' } });

    expect(await screen.findByText('South field')).toBeInTheDocument();
    expect(await screen.findByText('South farm activity')).toBeInTheDocument();
    await act(async () => {
      northFields.resolve(jsonResponse([field('field-a', 'farm-a', 'North field')]));
      northActivities.resolve(jsonResponse([activity('activity-a', 'farm-a', 'North farm activity')]));
    });
    await waitFor(() => {
      expect(screen.queryByText('North field')).not.toBeInTheDocument();
      expect(screen.queryByText('North farm activity')).not.toBeInTheDocument();
    });
    expect(screen.getByText('South field')).toBeInTheDocument();
    expect(screen.getByText('South farm activity')).toBeInTheDocument();
  });

  it('requires confirmation before archiving a field or cancelling a crop plan', async () => {
    const archive = vi.fn();
    const cancelPlan = vi.fn();
    let plans = [{ id: 'plan-1', farm_id: 'farm-a', field_id: null, district: 'Huye', crop: 'Maize', season: 'A',
      planting_date: '2026-10-20', area_ha: 1, plan: {}, verification: 'farmer_reported', status: 'draft',
      actual_planting_date: null, evidence: [] }];
    const confirm = vi.fn(() => false);
    vi.stubGlobal('confirm', confirm);
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'test-csrf-token' });
      if (url.endsWith('/v1/farms')) return jsonResponse([farms[0]]);
      if (url.endsWith('/v1/farms/farm-a/fields')) return jsonResponse([field('field-a', 'farm-a', 'North field')]);
      if (url.endsWith('/v1/farms/farm-a/activities')) return jsonResponse([]);
      if (url.endsWith('/v1/farms/farm-a/plans')) return jsonResponse(plans);
      if (url.endsWith('/archive') && init?.method === 'POST') { archive(); return jsonResponse(field('field-a', 'farm-a', 'North field')); }
      if (url.endsWith('/plan-1/status') && init?.method === 'PATCH') { cancelPlan(); plans = [{ ...plans[0], status: 'cancelled' }]; return jsonResponse(plans[0]); }
      return jsonResponse({ detail: 'not found' }, 404);
    }));

    render(<FarmsPage />);
    fireEvent.click(await screen.findByRole('button', { name: 'Archive' }));
    expect(window.confirm).toHaveBeenCalledWith(expect.stringContaining('Archive North field?'));
    expect(archive).not.toHaveBeenCalled();

    fireEvent.click(await screen.findByRole('button', { name: 'Mark cancelled' }));
    expect(window.confirm).toHaveBeenCalledWith(expect.stringContaining('Cancelled plans cannot be reopened.'));
    expect(cancelPlan).not.toHaveBeenCalled();

    confirm.mockReturnValue(true);
    fireEvent.click(screen.getByRole('button', { name: 'Archive' }));
    await waitFor(() => expect(archive).toHaveBeenCalledOnce());
    fireEvent.click(screen.getByRole('button', { name: 'Mark cancelled' }));
    await waitFor(() => expect(cancelPlan).toHaveBeenCalledOnce());
  });
});
