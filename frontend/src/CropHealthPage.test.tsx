import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { CropHealthPage } from './CropHealthPage';
import { CropHealthReviewPage } from './CropHealthReviewPage';

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

const farm = { id: 'farm-1', owner_id: 'farmer-1', name: 'Home farm', district: 'Huye', area_ha: 1 };
const cropCase = {
  id: 'case-1', farm_id: farm.id, farm_name: farm.name, district: farm.district,
  field_id: null, field_name: null, crop_plan_id: null, crop_plan_status: null,
  farmer_id: 'farmer-1', farmer_name: 'Test Farmer', crop: 'Maize',
  symptoms: 'Yellow marks on leaves', observed_date: null, status: 'submitted', diagnosis_status: 'unresolved',
  plant_parts_affected: null, spreading: null,
  photo_url: '/v1/crop-health/cases/case-1/photo', photo_size_bytes: 600, photo_width: 80,
  photo_height: 60, created_at: '2026-10-21T08:00:00Z', updated_at: '2026-10-21T08:00:00Z', updates: [],
  ai_screening: { status: 'candidate_screening', model_name: 'Experimental model', model_version: 'abc', generated_at: '2026-10-21T08:00:00Z', score_description: 'Uncalibrated model score; not a probability or confirmed diagnosis.', message: 'Experimental screening only. Not a diagnosis.', candidates: [{ class_name: 'Corn_(maize)___healthy', label: 'healthy', model_score: 0.81 }], guidance: { version: 'test', title: 'Safe next steps', steps: ['A healthy-looking model candidate does not rule out a problem.'], treatment_notice: 'CropPulse does not recommend a pesticide, medicine, active ingredient, dose, or spray schedule from this image.', candidates: [{ name: 'Healthy (model candidate only)', organism: null, code: null, url: null }], sources: [{ name: 'FAO IPM', url: 'https://www.fao.org/', scope: 'General principles.' }] } },
};

describe('React crop-health reporting and review', () => {
  afterEach(() => vi.unstubAllGlobals());
  it('submits a private photo report and clearly says it was not diagnosed', async () => {
    const calls: { url: string; init?: RequestInit }[] = [];
    class MockUploadRequest {
      static instance: MockUploadRequest | null = null;
      upload = { addEventListener: (_type: string, handler: (event: ProgressEvent) => void) => { this.progress = handler; } };
      progress: ((event: ProgressEvent) => void) | null = null;
      handlers: Record<string, (event: ProgressEvent) => void> = {};
      headers = new Headers(); method = ''; url = ''; status = 201; responseText = JSON.stringify(cropCase);
      withCredentials = false; timeout = 0;
      constructor() { MockUploadRequest.instance = this; }
      open(method: string, url: string) { this.method = method; this.url = url; }
      setRequestHeader(name: string, value: string) { this.headers.set(name, value); }
      addEventListener(type: string, handler: (event: ProgressEvent) => void) { this.handlers[type] = handler; }
      send(body: FormData) {
        calls.push({ url: this.url, init: { method: this.method, body, headers: this.headers } });
        this.progress?.({ lengthComputable: true, loaded: 50, total: 100 } as ProgressEvent);
      }
    }
    vi.stubGlobal('URL', { ...URL, createObjectURL: vi.fn(() => 'blob:crop-photo'), revokeObjectURL: vi.fn() });
    vi.stubGlobal('XMLHttpRequest', MockUploadRequest as unknown as typeof XMLHttpRequest);
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); calls.push({ url, init });
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'csrf' });
      if (url.endsWith('/v1/farms') && !url.includes('/fields')) return jsonResponse([farm]);
      if (url.endsWith('/v1/crop-health/crops')) return jsonResponse(['Maize', 'Beans']);
      if (url.endsWith('/v1/crop-health/cases') && init?.method === 'POST') return jsonResponse(cropCase, 201);
      if (url.endsWith('/v1/crop-health/cases')) return jsonResponse([]);
      if (url.endsWith(`/v1/farms/${farm.id}/fields`)) return jsonResponse([]);
      if (url.endsWith(`/v1/farms/${farm.id}/plans`)) return jsonResponse([]);
      if (url.endsWith('/photo')) return new Response(new Blob(['photo'], { type: 'image/jpeg' }), { status: 200, headers: { 'Content-Type': 'image/jpeg' } });
      return jsonResponse({ detail: 'not found' }, 404);
    }));

    const { container } = render(<CropHealthPage />);
    await screen.findByRole('option', { name: /Home farm/ });
    fireEvent.change(screen.getByLabelText('What symptoms can you see?'), { target: { value: 'Yellow marks on leaves' } });
    fireEvent.change(screen.getByLabelText(/Which parts of the plant are affected/), { target: { value: 'Lower leaves' } });
    fireEvent.change(screen.getByLabelText(/Is the problem spreading/), { target: { value: 'false' } });
    const file = new File(['valid image mock'], 'crop.png', { type: 'image/png' });
    fireEvent.change(container.querySelector('input[type="file"]')!, { target: { files: [file] } });
    fireEvent.click(screen.getByRole('button', { name: /Review report/ }));
    expect(await screen.findByRole('heading', { name: 'Review before submitting' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Submit privately/ }));
    expect(await screen.findByText(/Uploading your report · 50%/)).toBeInTheDocument();
    act(() => MockUploadRequest.instance?.handlers.load?.(new ProgressEvent('load')));
    expect(await screen.findByText('Report case-1 was submitted for review. No automatic diagnosis was made.')).toBeInTheDocument();
    expect(await screen.findByText('Experimental candidate screening')).toBeInTheDocument();
    expect(screen.getByText('81.0% raw score')).toBeInTheDocument();
    expect(screen.getByText(/does not rule out a problem/)).toBeInTheDocument();
    expect(screen.getByText(/does not recommend a pesticide/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'FAO IPM' })).toHaveAttribute('target', '_blank');
    expect(screen.queryByRole('progressbar', { name: 'Crop report upload progress' })).not.toBeInTheDocument();
    const upload = calls.find((call) => call.url.endsWith('/v1/crop-health/cases') && call.init?.method === 'POST');
    expect(upload?.init?.body).toBeInstanceOf(FormData);
    expect((upload?.init?.body as FormData).get('farm_id')).toBe(farm.id);
    expect((upload?.init?.body as FormData).get('plant_parts_affected')).toBe('Lower leaves');
    expect((upload?.init?.body as FormData).get('spreading')).toBe('false');
    const uploadedPhoto = (upload?.init?.body as FormData).get('photo');
    expect(uploadedPhoto).toBeInstanceOf(File);
    expect((uploadedPhoto as File).name).toBe(file.name);
    expect(new Headers(upload?.init?.headers).has('Content-Type')).toBe(false);
  });

  it('shows an error when the crop report service is unavailable', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).endsWith('/v1/farms')) return jsonResponse({ detail: 'Database unavailable.' }, 503);
      return jsonResponse({ detail: 'not found' }, 404);
    }));
    render(<CropHealthPage />);
    expect(await screen.findByRole('alert')).toHaveTextContent('CropPulse is temporarily unavailable');
  });

  it('lets an authorized reviewer start a case with a private update', async () => {
    const calls: { url: string; init?: RequestInit }[] = [];
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); calls.push({ url, init });
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'csrf' });
      if (url.endsWith('/v1/reviewer/crop-health/cases')) return jsonResponse([{ ...cropCase, farmer_name: 'Test Farmer' }]);
      if (url.endsWith('/v1/reviewer/crop-health/cases/case-1')) return jsonResponse({ ...cropCase, farmer_name: 'Test Farmer' });
      if (url.endsWith('/updates') && init?.method === 'POST') return jsonResponse({
        ...cropCase, status: 'under_review', updates: [{ id: 'update-1', author_id: 'reviewer-1', author_name: 'Reviewer', author_role: 'reviewer', update_type: 'start_review', assessment: null, message: 'I am reviewing this report.', created_at: '2026-10-21T08:01:00Z' }],
      }, 201);
      if (url.endsWith('/photo')) return new Response(new Blob(['photo'], { type: 'image/jpeg' }), { status: 200, headers: { 'Content-Type': 'image/jpeg' } });
      return jsonResponse({ detail: 'not found' }, 404);
    }));
    render(<CropHealthReviewPage />);
    fireEvent.click(await screen.findByRole('button', { name: /Maize · Home farm/ }));
    await screen.findByText('Yellow marks on leaves');
    expect(await screen.findByText('Experimental candidate screening')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Start review note'), { target: { value: 'I am reviewing this report.' } });
    fireEvent.click(screen.getByRole('button', { name: 'Start review' }));
    expect(await screen.findByText('Your private case update was saved.')).toBeInTheDocument();
    const update = calls.find((call) => call.url.endsWith('/updates'));
    expect(JSON.parse(String(update?.init?.body))).toMatchObject({ action: 'start_review', message: 'I am reviewing this report.' });
    expect(screen.getByText('Unresolved; no diagnosis recorded')).toBeInTheDocument();
  });
});
