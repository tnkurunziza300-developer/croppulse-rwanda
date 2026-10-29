import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { FieldDecisionSummary } from './FieldDecisionSummary';

const field = { id: 'field-a', farm_id: 'farm-a', name: 'North plot', area_ha: 1, latitude: -2, longitude: 30, archived_at: null, created_at: '2026-01-01', updated_at: '2026-01-01' };
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
const emptyTimeline = { entries: [], has_more: false };

function installFetch(overrides: Record<string, unknown> = {}) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    void init;
    const path = new URL(String(input), 'http://localhost').pathname;
    const response = (value: unknown) => value instanceof Response ? value : json(value);
    if (path.endsWith('/plans')) return response(overrides.plans ?? []);
    if (path.endsWith('/irrigation-records')) return response(overrides.irrigation ?? []);
    if (path.endsWith('/soil-observations')) return response(overrides.observations ?? []);
    if (path.endsWith('/soil-tests')) return response(overrides.soilTests ?? []);
    if (path.endsWith('/harvests')) return response(overrides.harvests ?? []);
    if (path.endsWith('/timeline')) return response(overrides.timeline ?? emptyTimeline);
    if (path.endsWith('/weather/forecasts')) return response(overrides.forecasts ?? { items: [], total: 0 });
    return json({ detail: 'not found' }, 404);
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

describe('field decision-support summary', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('shows stored plan, soil, irrigation, harvest and sourced forecast values with provenance', async () => {
    const fetchMock = installFetch({
      plans: [{ id: 'plan-1', field_id: 'field-a', crop: 'Maize', season: 'A', status: 'planned', planting_date: '2026-10-01', actual_planting_date: null }],
      irrigation: [{ id: 'water-1', field_id: 'field-a', event_date: '2026-09-20', irrigation_method: 'drip', water_source: 'river', water_quantity: null, water_quantity_unit: null, duration_value: 20, duration_unit: 'minutes' }],
      soilTests: [{ id: 'test-1', field_id: 'field-a', test_date: '2026-08-10', ph_value: null, nitrogen_value: 4, nitrogen_unit: 'mg/kg', phosphorus_value: null, phosphorus_unit: null, potassium_value: null, potassium_unit: null, organic_matter_value: null, organic_matter_unit: null, laboratory_name: 'Farmer named lab' }],
      harvests: [{ id: 'harvest-1', field_id: 'field-a', crop: 'Beans', season: 'B', harvest_date: '2026-07-02', quantity: 0, quantity_unit: 'kg', harvested_area: 0.5, area_unit: 'ha' }],
      timeline: { entries: [{ id: 'activity-1', field_id: 'field-a', event_date: '2026-09-10', event_type: 'activity', description: 'Farmer report: field preparation', source_label: 'Farmer reported', href: '#activity-history-title' }], has_more: false },
      forecasts: { total: 1, items: [{ id: 'forecast-1', field_id: 'field-a', status: 'stale', retrieved_at: '2026-06-01T00:00:00Z', location_context: { field_id: 'field-a' }, forecast: { status: 'stale', source: 'Open-Meteo', forecast_type: 'model forecast', message: '' } }] },
    });
    render(<FieldDecisionSummary farmId="farm-a" fields={[field]} />);
    fireEvent.click(screen.getByRole('button', { name: 'Open summary' }));
    expect(await screen.findByText(/Maize · Season A/)).toBeInTheDocument();
    expect(screen.getByText(/Quantity not recorded · 20 minutes/)).toBeInTheDocument();
    expect(screen.getByText(/pH: Not recorded; N: 4 mg\/kg/)).toBeInTheDocument();
    expect(screen.getByText(/Farmer-entered transcription/)).toBeInTheDocument();
    expect(screen.getByText(/0 kg from 0.5 ha/)).toBeInTheDocument();
    expect(screen.getByText(/Saved forecast marked stale/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'View original records' })).toHaveAttribute('href', '#activity-history-title');
    expect(fetchMock.mock.calls.every(([, init]) => !init?.method || init.method === 'GET')).toBe(true);
  });

  it('filters to the selected field and does not assign farm-level records to it', async () => {
    installFetch({
      plans: [
        { id: 'field-plan', field_id: 'field-a', crop: 'Maize', season: 'A', status: 'planned', planting_date: '2026-10-01', actual_planting_date: null },
        { id: 'farm-plan', field_id: null, crop: 'Beans', season: 'B', status: 'planned', planting_date: '2026-10-02', actual_planting_date: null },
      ],
      timeline: { entries: [{ id: 'entry-field', field_id: 'field-a', event_date: '2026-09-01', event_type: 'activity', description: 'Field activity', source_label: 'Farmer reported', href: '#activity-history-title' }, { id: 'entry-farm', field_id: null, event_date: '2026-09-02', event_type: 'activity', description: 'Farm activity', source_label: 'Farmer reported', href: '#activity-history-title' }], has_more: false },
    });
    render(<FieldDecisionSummary farmId="farm-a" fields={[field]} />);
    fireEvent.click(screen.getByRole('button', { name: 'Open summary' }));
    fireEvent.change(await screen.findByLabelText('Summary farm or field'), { target: { value: 'field-a' } });
    await waitFor(() => expect(screen.getByText('Field activity')).toBeInTheDocument());
    expect(screen.queryByText('Farm activity')).not.toBeInTheDocument();
    expect(screen.getByText(/Maize · Season A/)).toBeInTheDocument();
    expect(screen.queryByText(/Beans · Season B/)).not.toBeInTheDocument();
  });

  it('renders partial API failures and retry without hiding successfully loaded records', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = new URL(String(input), 'http://localhost').pathname;
      if (path.endsWith('/plans')) return json([{ id: 'plan-1', field_id: null, crop: 'Maize', season: 'A', status: 'planned', planting_date: '2026-10-01' }]);
      if (path.endsWith('/soil-tests')) return json({ detail: 'service unavailable' }, 503);
      if (path.endsWith('/timeline')) return json(emptyTimeline);
      if (path.endsWith('/weather/forecasts')) return json({ items: [], total: 0 });
      return json([]);
    });
    vi.stubGlobal('fetch', fetchMock);
    render(<FieldDecisionSummary farmId="farm-a" fields={[]} />);
    fireEvent.click(screen.getByRole('button', { name: 'Open summary' }));
    expect(await screen.findByText(/Some summary data could not be loaded/)).toBeInTheDocument();
    expect(screen.getByText(/Maize · Season A/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    await waitFor(() => expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(14));
  });

  it('has loading and explicit empty states', async () => {
    const resolvers: ((response: Response) => void)[] = [];
    vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>((done) => { resolvers.push(done); })));
    render(<FieldDecisionSummary farmId="farm-a" fields={[]} />);
    fireEvent.click(screen.getByRole('button', { name: 'Open summary' }));
    expect(screen.getByRole('status')).toHaveTextContent('Loading farm records and evidence');
    await waitFor(() => expect(resolvers).toHaveLength(7));
    resolvers.forEach((resolve, index) => resolve(json(index === 5 ? emptyTimeline : index === 6 ? { items: [], total: 0 } : [])));
    await waitFor(() => expect(screen.getByText(/No records are currently available/)).toBeInTheDocument());
    expect(screen.getByText(/This does not mean activities did not occur/)).toBeInTheDocument();
  });

  it('opens by keyboard and exposes a labelled farm-or-field selector', async () => {
    const user = userEvent.setup();
    installFetch();
    render(<FieldDecisionSummary farmId="farm-a" fields={[field]} />);
    await user.tab();
    expect(screen.getByRole('button', { name: 'Open summary' })).toHaveFocus();
    await user.keyboard('{Enter}');
    expect(await screen.findByLabelText('Summary farm or field')).toBeInTheDocument();
  });
});
