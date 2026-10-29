import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { WeatherPage } from './WeatherPage';

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

describe('WeatherPage device location', () => {
  afterEach(() => { vi.unstubAllGlobals(); });

  it('requires explicit consent and saves the forecast with the account after requesting it', async () => {
    let success: PositionCallback | undefined;
    const getCurrentPosition = vi.fn((onSuccess: PositionCallback) => { success = onSuccess; });
    Object.defineProperty(navigator, 'geolocation', { configurable: true, value: { getCurrentPosition } });
    const calls: { url: string; init?: RequestInit }[] = [];
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); calls.push({ url, init });
      if (url.endsWith('/v1/farms')) return jsonResponse([{ id: 'farm-1', owner_id: 'farmer-1', name: 'Home farm', district: 'Huye' }]);
      if (url.endsWith('/v1/farms/farm-1/fields')) return jsonResponse([]);
      if (url.endsWith('/v1/weather/forecasts')) return jsonResponse({ items: [], total: 0 });
      if (url.endsWith('/v1/weather/alert-preferences')) return jsonResponse({ items: [], active_rules: [], notice: 'No rules.' });
      if (url.endsWith('/v1/weather/alerts')) return jsonResponse({ items: [], total: 0 });
      if (url.includes('/v1/weather/climate-data')) return jsonResponse({ items: [], total: 0, filters: {}, notice: '' });
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'test-csrf-token' });
      if (url.endsWith('/v1/weather/forecast')) return jsonResponse({ status: 'available', stored: true, record_id: 'forecast-1', retrieved_at: '2026-10-22T08:00:00+00:00', message: 'Forecast', daily_forecast: [] });
      return jsonResponse({ detail: 'not found' }, 404);
    }));

    render(<WeatherPage />);
    fireEvent.click(await screen.findByRole('button', { name: /Use my current location/ }));
    expect(getCurrentPosition).toHaveBeenCalledWith(expect.any(Function), expect.any(Function), expect.objectContaining({ enableHighAccuracy: true }));
    success?.({ coords: { latitude: -2.5, longitude: 29.9, accuracy: 18 } } as GeolocationPosition);
    expect(await screen.findByText(/Location source: device GPS \(browser-reported accuracy about 18 m\)/)).toBeInTheDocument();
    expect(screen.getByLabelText('Latitude')).toHaveValue(-2.5);
    expect(screen.getByLabelText('Longitude')).toHaveValue(29.9);
    expect(screen.getByText(/You have no saved forecasts yet/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Get 7-day forecast' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Confirm that you want this forecast and its coordinates saved');
    fireEvent.click(screen.getByLabelText(/Save this forecast and its coordinates to my CropPulse account/));
    expect(screen.getByLabelText(/Save this forecast and its coordinates to my CropPulse account/)).toBeChecked();
    fireEvent.click(screen.getByRole('button', { name: 'Get 7-day forecast' }));
    await screen.findByText(/Model forecast available\. This is not a current observation\./);
    expect(await screen.findByRole('button', { name: 'View saved forecast' })).toBeInTheDocument();
    const forecast = calls.find((call) => call.url.endsWith('/v1/weather/forecast'));
    expect(JSON.parse(String(forecast?.init?.body))).toEqual({ latitude: -2.5, longitude: 29.9, save_to_account: true, location_source: 'device' });
    expect(calls.some((call) => call.init?.method === 'POST' && call.url.includes('/fields'))).toBe(false);
  });

  it('shows a useful message when the user denies location permission', async () => {
    Object.defineProperty(navigator, 'geolocation', { configurable: true, value: {
      getCurrentPosition: (_success: PositionCallback, error: PositionErrorCallback) => error({
        code: 1, message: 'denied', PERMISSION_DENIED: 1, POSITION_UNAVAILABLE: 2, TIMEOUT: 3,
      } as GeolocationPositionError),
    } });
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => String(input).endsWith('/v1/farms')
      ? jsonResponse([]) : String(input).endsWith('/v1/weather/alert-preferences')
        ? jsonResponse({ items: [], active_rules: [], notice: 'No rules.' }) : String(input).endsWith('/v1/weather/alerts')
          ? jsonResponse({ items: [], total: 0 }) : String(input).includes('/v1/weather/climate-data')
        ? jsonResponse({ items: [], total: 0, filters: {}, notice: '' }) : jsonResponse({ detail: 'not found' }, 404)));
    render(<WeatherPage />);
    fireEvent.click(await screen.findByRole('button', { name: /Use my current location/ }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Location access was denied');
  });

  it('binds only selected saved-field coordinates and explains geographic verification limits', async () => {
    const calls: { url: string; init?: RequestInit }[] = [];
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); calls.push({ url, init });
      if (url.endsWith('/v1/farms')) return jsonResponse([{ id: 'farm-1', owner_id: 'farmer-1', name: 'Home farm', district: 'Huye' }]);
      if (url.endsWith('/v1/farms/farm-1/fields')) return jsonResponse([
        { id: 'field-1', farm_id: 'farm-1', name: 'Upper field', latitude: -2.5, longitude: 29.9, archived_at: null },
      ]);
      if (url.endsWith('/v1/weather/forecasts')) return jsonResponse({ items: [], total: 0 });
      if (url.endsWith('/v1/weather/alert-preferences')) return jsonResponse({ items: [], active_rules: [], notice: 'No rules.' });
      if (url.endsWith('/v1/weather/alerts')) return jsonResponse({ items: [], total: 0 });
      if (url.includes('/v1/weather/climate-data')) return jsonResponse({ items: [], total: 0, filters: {}, notice: '' });
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'csrf' });
      if (url.endsWith('/v1/weather/forecast')) return jsonResponse({ status: 'available', stored: true,
        record_id: 'linked-forecast', retrieved_at: '2026-10-22T08:00:00+00:00', message: 'Forecast', daily_forecast: [],
        location_context: { association: 'owned_field_record', location_source: 'saved_field', field_id: 'field-1',
          farm_name: 'Home farm', field_name: 'Upper field', geographic_verification: 'not_independently_verified',
          message: 'Coordinates match saved field.' } });
      return jsonResponse({ detail: 'not found' }, 404);
    }));
    render(<WeatherPage />);
    await screen.findByRole('option', { name: /Upper field/ });
    fireEvent.change(screen.getByLabelText('Saved field coordinates'), { target: { value: 'field-1' } });
    expect(screen.getByText(/does not independently verify the point/)).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText(/Save this forecast and its coordinates to my CropPulse account/));
    fireEvent.click(screen.getByRole('button', { name: 'Get 7-day forecast' }));
    const forecast = calls.find((call) => call.url.endsWith('/v1/weather/forecast'));
    expect(JSON.parse(String(forecast?.init?.body))).toEqual({ latitude: -2.5, longitude: 29.9,
      save_to_account: true, location_source: 'saved_field', field_id: 'field-1' });
  });

  it('lets farmers opt into an eligible field preference while clearly showing that no rules are active', async () => {
    const calls: { url: string; init?: RequestInit }[] = [];
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); calls.push({ url, init });
      if (url.endsWith('/v1/farms')) return jsonResponse([]);
      if (url.endsWith('/v1/weather/forecasts')) return jsonResponse({ items: [], total: 0 });
      if (url.endsWith('/v1/weather/alert-preferences')) return jsonResponse({ items: [{ field_id: 'field-1', farm_id: 'farm-1',
        farm_name: 'Home farm', field_name: 'Upper field', has_coordinates: true, within_supported_extent: true, enabled: false }], active_rules: [], notice: 'No rules.' });
      if (url.endsWith('/v1/weather/alerts')) return jsonResponse({ items: [], total: 0 });
      if (url.includes('/v1/weather/climate-data')) return jsonResponse({ items: [], total: 0, filters: {}, notice: '' });
      if (url.endsWith('/v1/weather/alert-preferences/field-1')) return jsonResponse({ field_id: 'field-1', farm_id: 'farm-1', enabled: true, active_rules: [], notice: 'No rules.' });
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'csrf' });
      return jsonResponse({ detail: 'not found' }, 404);
    }));
    render(<WeatherPage />);
    const optIn = await screen.findByRole('checkbox', { name: /Enable future in-app weather alerts for this field/ });
    fireEvent.click(optIn);
    expect(await screen.findByText(/no alerts are currently generated/i)).toBeInTheDocument();
    const update = calls.find((call) => call.url.endsWith('/v1/weather/alert-preferences/field-1'));
    expect(update?.init?.method).toBe('PUT');
    expect(JSON.parse(String(update?.init?.body))).toEqual({ enabled: true });
    expect(calls.some((call) => call.url.includes('/schedule') || call.url.includes('/generate'))).toBe(false);
  });

  it('shows source-linked national outlook ranges and applies the filters', async () => {
    const requests: string[] = [];
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      requests.push(url);
      if (url.endsWith('/v1/farms')) return jsonResponse([]);
      if (url.endsWith('/v1/weather/forecasts')) return jsonResponse({ items: [], total: 0 });
      if (url.endsWith('/v1/weather/alert-preferences')) return jsonResponse({ items: [], active_rules: [], notice: 'No rules.' });
      if (url.endsWith('/v1/weather/alerts')) return jsonResponse({ items: [], total: 0 });
      if (url.endsWith('/v1/weather/bulletins')) return jsonResponse({ items: [], total: 0 });
      if (url.includes('/v1/weather/climate-data')) return jsonResponse({
        items: [{ id: 'rain-1', record_type: 'monthly_outlook', variable: 'rainfall_total',
          geography_type: 'national', geography_label: 'Rwanda (national range)',
          period_label: 'October 2026', valid_from: '2026-10-01', valid_to: '2026-10-31',
          period_status: 'current', value_min: 90, value_max: 300, unit: 'mm per month',
          normal_min: null, normal_max: null, anomaly_label: null,
          source_text: 'Transcription note, not a quotation: national rainfall outlook range 90–300 mm for October 2026; see PDF page 1.',
          source_page: 1, transcription_status: 'numeric-range-transcribed',
          bulletin: { id: 'bulletin-1', title: 'September 2026 monthly bulletin', issued_at: '2026-09-01',
            source_url: 'https://example.test/source.pdf', document_url: '/v1/weather/bulletins/bulletin-1/document',
            sha256: 'a'.repeat(64), provenance_status: 'publisher-indicated' } }],
        total: 1, filters: {}, notice: 'Source-linked only',
      });
      return jsonResponse({ detail: 'not found' }, 404);
    }));
    render(<WeatherPage />);
    expect((await screen.findAllByText('October 2026')).length).toBeGreaterThan(0);
    expect(screen.getByText('90–300 mm per month')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /September 2026 monthly bulletin, p\. 1/ })).toHaveAttribute('href', expect.stringContaining('bulletin-1'));
    fireEvent.change(screen.getByLabelText('Valid year'), { target: { value: '2026' } });
    expect((await screen.findAllByText('October 2026')).length).toBeGreaterThan(0);
    expect(requests.some((url) => url.includes('year=2026'))).toBe(true);
  });

  it('shows forecast-triggered rain, dry-spell, and temperature prompts with their limits', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/v1/farms')) return jsonResponse([]);
      if (url.endsWith('/v1/weather/forecasts')) return jsonResponse({ items: [], total: 0 });
      if (url.endsWith('/v1/weather/alert-preferences')) return jsonResponse({ items: [], active_rules: [], notice: 'No rules.' });
      if (url.endsWith('/v1/weather/alerts')) return jsonResponse({ items: [], total: 0 });
      if (url.endsWith('/v1/weather/bulletins')) return jsonResponse({ items: [], total: 0 });
      if (url.includes('/v1/weather/climate-data')) return jsonResponse({ items: [], total: 0, filters: {}, notice: '' });
      if (url.endsWith('/v1/browser-auth/csrf')) return jsonResponse({ csrf_token: 'test-csrf-token' });
      if (url.endsWith('/v1/weather/forecast')) return jsonResponse({
        status: 'available', stored: true, record_id: 'forecast-1', retrieved_at: '2026-10-27T08:00:00Z',
        message: 'Forecast', daily_forecast: [
          { date: '2026-10-27', temperature_max_c: 31, temperature_min_c: 14, precipitation_sum_mm: 8 },
          { date: '2026-10-28', temperature_max_c: 28, temperature_min_c: 13, precipitation_sum_mm: 0.5 },
          { date: '2026-10-29', temperature_max_c: 29, temperature_min_c: 12, precipitation_sum_mm: 0.2 },
          { date: '2026-10-30', temperature_max_c: 27, temperature_min_c: 10, precipitation_sum_mm: 0 },
        ],
      });
      return jsonResponse({ detail: 'not found' }, 404);
    }));

    render(<WeatherPage />);
    fireEvent.change(await screen.findByLabelText('Latitude'), { target: { value: '-2.5' } });
    fireEvent.change(screen.getByLabelText('Longitude'), { target: { value: '29.9' } });
    fireEvent.click(screen.getByLabelText(/Save this forecast and its coordinates to my CropPulse account/));
    fireEvent.click(screen.getByRole('button', { name: 'Get 7-day forecast' }));

    expect(await screen.findByRole('heading', { name: 'Forecast-based prompts' })).toBeInTheDocument();
    expect(screen.getByText('Rain signal')).toBeInTheDocument();
    expect(screen.getByText(/precipitation estimates of 5 mm or more appear on 2026-10-27/)).toBeInTheDocument();
    expect(screen.getByText('Dry-spell signal')).toBeInTheDocument();
    expect(screen.getByText(/three consecutive days have precipitation estimates of 1 mm or less/)).toBeInTheDocument();
    expect(screen.getByText('Temperature signal')).toBeInTheDocument();
    expect(screen.getByText(/forecast high of 30 °C or more, or low of 10 °C or less/)).toBeInTheDocument();
    expect(screen.getByText(/Automated · not RAB-verified/)).toBeInTheDocument();
    expect(screen.getByText(/These screen thresholds are simple indicators, not crop-specific limits or official warnings/)).toBeInTheDocument();
    expect(screen.getByText(/do not measure your soil moisture, confirm rainfall at your plot/)).toBeInTheDocument();
  });
});
