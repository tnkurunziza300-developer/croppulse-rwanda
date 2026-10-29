import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { IrrigationLog } from './pages';
import type { IrrigationRecord, IrrigationRecordInput } from './api';

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

const fields = [{ id: 'field-1', farm_id: 'farm-1', name: 'Upper plot', area_ha: null, latitude: null, longitude: null, archived_at: null, created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' }];
const plans = [{ id: 'plan-1', farm_id: 'farm-1', field_id: 'field-1', district: 'Huye', crop: 'Beans', season: 'B' as const, planting_date: '2026-09-01', area_ha: 1, plan: {}, verification: 'provisional', status: 'planned' as const, actual_planting_date: null, evidence: [] }];

afterEach(() => vi.unstubAllGlobals());

describe('farmer irrigation log', () => {
  it('creates, lists, and corrects records while preserving missing and zero values', async () => {
    const records: IrrigationRecord[] = [];
    const calls: { url: string; method: string; body?: IrrigationRecordInput }[] = [];
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'csrf' });
      const method = init?.method ?? 'GET';
      calls.push({ url, method, body: init?.body ? JSON.parse(String(init.body)) as IrrigationRecordInput : undefined });
      if (url.endsWith('/irrigation-records') && method === 'GET') return jsonResponse(records);
      if (url.endsWith('/irrigation-records') && method === 'POST') {
        const body = JSON.parse(String(init?.body)) as IrrigationRecordInput;
        const created: IrrigationRecord = { ...body, id: 'record-1', farm_id: 'farm-1', verification: 'farmer_reported', created_at: '2026-10-28T00:00:00Z', updated_at: '2026-10-28T00:00:00Z' };
        records.push(created);
        return jsonResponse(created, 201);
      }
      if (url.endsWith('/irrigation-records/record-1') && method === 'PUT') {
        const body = JSON.parse(String(init?.body)) as IrrigationRecordInput;
        Object.assign(records[0], body, { updated_at: '2026-10-28T00:01:00Z' });
        return jsonResponse(records[0]);
      }
      return jsonResponse({ detail: 'not found' }, 404);
    }));

    render(<IrrigationLog farmId="farm-1" fields={fields} plans={plans} />);
    expect(await screen.findByText('No water events recorded')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Record water event' }));
    fireEvent.change(screen.getByLabelText('Water quantity (optional)'), { target: { value: '0' } });
    fireEvent.change(screen.getByLabelText('Quantity unit'), { target: { value: 'm3' } });
    fireEvent.change(screen.getByLabelText('Farm field (optional)'), { target: { value: 'field-1' } });
    fireEvent.change(screen.getByLabelText(/^Crop plan \(optional\)/), { target: { value: 'plan-1' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save event' }));
    expect(await screen.findByText('Irrigation entry saved as farmer reported.')).toBeInTheDocument();
    expect(await screen.findByText('Recorded quantity: 0 m3')).toBeInTheDocument();
    expect(screen.getByText('Farmer reported')).toBeInTheDocument();
    const post = calls.find((call) => call.method === 'POST');
    expect(post?.body).toMatchObject({ water_source: 'unknown', irrigation_method: 'unknown', field_id: 'field-1', crop_plan_id: 'plan-1', water_quantity: 0, water_quantity_unit: 'm3', duration_value: null, duration_unit: null });

    fireEvent.click(screen.getByRole('button', { name: 'Correct entry' }));
    fireEvent.change(screen.getByLabelText('Notes (optional)'), { target: { value: 'Corrected farmer note' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save correction' }));
    expect(await screen.findByText('Irrigation entry corrected as farmer reported.')).toBeInTheDocument();
    expect(await screen.findByText('Notes: Corrected farmer note')).toBeInTheDocument();
    expect(calls.some((call) => call.method === 'PUT' && call.url.endsWith('/irrigation-records/record-1'))).toBe(true);
  });

  it('requires a description for Other and keeps the form open after an API failure', async () => {
    let postCount = 0;
    let failLoad = true;
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'csrf' });
      if (url.endsWith('/irrigation-records') && init?.method === 'GET' && failLoad) { failLoad = false; return jsonResponse({ detail: 'load failed' }, 503); }
      if (url.endsWith('/irrigation-records') && init?.method === 'GET') return jsonResponse([]);
      if (url.endsWith('/irrigation-records') && init?.method === 'POST') { postCount += 1; return jsonResponse({ detail: 'temporary failure' }, 503); }
      return jsonResponse({ detail: 'not found' }, 404);
    }));
    render(<IrrigationLog farmId="farm-1" fields={[]} plans={[]} />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Irrigation records could not be loaded.');
    expect(screen.getByRole('alert')).toHaveTextContent('migration 0018');
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    await screen.findByText('No water events recorded');
    fireEvent.click(screen.getByRole('button', { name: 'Record water event' }));
    fireEvent.change(screen.getByLabelText('Water source'), { target: { value: 'other' } });
    const sourceDescription = screen.getByLabelText('Other water source') as HTMLInputElement;
    expect(sourceDescription).toBeRequired();
    fireEvent.click(screen.getByRole('button', { name: 'Save event' }));
    expect(postCount).toBe(0);
    fireEvent.change(sourceDescription, { target: { value: 'Community catchment' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save event' }));
    expect(await screen.findByText('CropPulse is temporarily unavailable. Your changes may not have been saved.')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Community catchment')).toBeInTheDocument();
    expect(postCount).toBe(1);
  });
});
