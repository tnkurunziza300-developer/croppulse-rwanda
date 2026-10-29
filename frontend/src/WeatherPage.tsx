import { useEffect, useState, type FormEvent } from 'react';
import { CloudRain, ExternalLink, FileText, LocateFixed, MapPin, RefreshCw, ShieldCheck } from 'lucide-react';
import { api, listSavedWeatherForecasts, listWeatherAlerts, listWeatherAlertPreferences, listWeatherBulletins, listWeatherClimateData, requestWeatherForecast, updateWeatherAlertPreference, updateWeatherAlertStatus, weatherBulletinDocumentUrl } from './api';
import type { Farm, FarmField, SavedWeatherForecast, WeatherAlert, WeatherAlertPreference, WeatherBulletin, WeatherClimateRecord, WeatherForecast } from './api';
import { ErrorState, LoadingState, PageHeader } from './pages';
import './weather-alerts.css';

function formatRetrievedAt(value?: string) {
  if (!value) return 'Unknown';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Unknown' : `${date.toLocaleString(undefined, { timeZone: 'UTC' })} (UTC)`;
}

function formatCacheAge(seconds?: number) {
  if (typeof seconds !== 'number' || !Number.isFinite(seconds) || seconds < 0) return 'Age unavailable';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${hours} h ${minutes} min old`;
}

function formatBulletinDate(value: string) {
  const date = new Date(`${value}T00:00:00Z`);
  return Number.isNaN(date.getTime()) ? 'Unknown' : date.toLocaleDateString(undefined, { timeZone: 'UTC', year: 'numeric', month: 'short', day: 'numeric' });
}

type ForecastPrompt = { title: string; signal: string; suggestion: string };

function buildForecastPrompts(days: WeatherForecast['daily_forecast'] = []): ForecastPrompt[] {
  const prompts: ForecastPrompt[] = [];
  const dateLabels = (matchingDays: typeof days) => matchingDays.slice(0, 3).map((day) => day.date).join(', ');
  const rainDays = days.filter((day) => typeof day.precipitation_sum_mm === 'number'
    && Number.isFinite(day.precipitation_sum_mm) && day.precipitation_sum_mm >= 5);
  if (rainDays.length) {
    prompts.push({
      title: 'Rain signal',
      signal: `Daily precipitation estimates of 5 mm or more appear on ${dateLabels(rainDays)}${rainDays.length > 3 ? ` and ${rainDays.length - 3} more day(s)` : ''}.`,
      suggestion: 'Consider checking local field drainage and soil conditions before planned field work.',
    });
  }

  let drySpell: typeof days = [];
  let currentDrySpell: typeof days = [];
  for (const day of days) {
    const isDryEstimate = typeof day.precipitation_sum_mm === 'number'
      && Number.isFinite(day.precipitation_sum_mm) && day.precipitation_sum_mm <= 1;
    if (!isDryEstimate) {
      if (currentDrySpell.length > drySpell.length) drySpell = currentDrySpell;
      currentDrySpell = [];
      continue;
    }
    if (currentDrySpell.length && (Date.parse(`${day.date}T00:00:00Z`) - Date.parse(`${currentDrySpell.at(-1)?.date}T00:00:00Z`)) !== 86400000) {
      if (currentDrySpell.length > drySpell.length) drySpell = currentDrySpell;
      currentDrySpell = [];
    }
    currentDrySpell.push(day);
  }
  if (currentDrySpell.length > drySpell.length) drySpell = currentDrySpell;
  if (drySpell.length >= 3) {
    prompts.push({
      title: 'Dry-spell signal',
      signal: `At least three consecutive days have precipitation estimates of 1 mm or less per day (${dateLabels(drySpell)}${drySpell.length > 3 ? ` and ${drySpell.length - 3} more day(s)` : ''}).`,
      suggestion: 'Check soil moisture locally before deciding whether irrigation is needed.',
    });
  }

  const temperatureDays = days.filter((day) => (typeof day.temperature_max_c === 'number' && Number.isFinite(day.temperature_max_c) && day.temperature_max_c >= 30)
    || (typeof day.temperature_min_c === 'number' && Number.isFinite(day.temperature_min_c) && day.temperature_min_c <= 10));
  if (temperatureDays.length) {
    prompts.push({
      title: 'Temperature signal',
      signal: `A forecast high of 30 °C or more, or low of 10 °C or less, appears on ${dateLabels(temperatureDays)}${temperatureDays.length > 3 ? ` and ${temperatureDays.length - 3} more day(s)` : ''}.`,
      suggestion: 'Check local crop conditions; do not change field practices based on this estimate alone.',
    });
  }
  return prompts;
}

export function WeatherPage() {
  const [farms, setFarms] = useState<Farm[]>([]);
  const [fields, setFields] = useState<FarmField[]>([]);
  const [farmId, setFarmId] = useState('');
  const [fieldId, setFieldId] = useState('');
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [loadingFarms, setLoadingFarms] = useState(true);
  const [loadingFields, setLoadingFields] = useState(false);
  const [loadingForecast, setLoadingForecast] = useState(false);
  const [locating, setLocating] = useState(false);
  const [locationAccuracy, setLocationAccuracy] = useState<number | null>(null);
  const [locationSource, setLocationSource] = useState<'manual' | 'saved-field' | 'device'>('manual');
  const [pageError, setPageError] = useState('');
  const [formError, setFormError] = useState('');
  const [forecast, setForecast] = useState<WeatherForecast | null>(null);
  const [storageNotice, setStorageNotice] = useState('');
  const [saveForecastConsent, setSaveForecastConsent] = useState(false);
  const [savedForecasts, setSavedForecasts] = useState<SavedWeatherForecast[]>([]);
  const [loadingSavedForecasts, setLoadingSavedForecasts] = useState(true);
  const [savedForecastError, setSavedForecastError] = useState('');
  const [bulletins, setBulletins] = useState<WeatherBulletin[]>([]);
  const [loadingBulletins, setLoadingBulletins] = useState(true);
  const [bulletinError, setBulletinError] = useState('');
  const [climateRecords, setClimateRecords] = useState<WeatherClimateRecord[]>([]);
  const [loadingClimate, setLoadingClimate] = useState(true);
  const [climateError, setClimateError] = useState('');
  const [climateYear, setClimateYear] = useState('');
  const [climateType, setClimateType] = useState('');
  const [climateSearch, setClimateSearch] = useState('');
  const [alertPreferences, setAlertPreferences] = useState<WeatherAlertPreference[]>([]);
  const [weatherAlerts, setWeatherAlerts] = useState<WeatherAlert[]>([]);
  const [alertRulesCount, setAlertRulesCount] = useState(0);
  const [alertLoading, setAlertLoading] = useState(true);
  const [alertError, setAlertError] = useState('');
  const [alertUpdating, setAlertUpdating] = useState('');

  useEffect(() => {
    let cancelled = false;
    void api<Farm[]>('/v1/farms').then((rows) => {
      if (!cancelled) {
        setFarms(rows);
        setFarmId(rows[0]?.id ?? '');
        setPageError('');
      }
    }).catch((error: Error) => { if (!cancelled) setPageError(error.message); })
      .finally(() => { if (!cancelled) setLoadingFarms(false); });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    let cancelled = false;
    void Promise.all([listWeatherAlertPreferences(), listWeatherAlerts()]).then(([preferences, alerts]) => {
      if (!cancelled) {
        setAlertPreferences(preferences.items);
        setAlertRulesCount(preferences.active_rules.length);
        setWeatherAlerts(alerts.items);
        setAlertError('');
      }
    }).catch((error: Error) => { if (!cancelled) setAlertError(error.message); })
      .finally(() => { if (!cancelled) setAlertLoading(false); });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setLoadingClimate(true);
    void listWeatherClimateData({
      year: climateYear ? Number(climateYear) : undefined,
      recordType: climateType || undefined,
      search: climateSearch,
    }, controller.signal).then((result) => {
      setClimateRecords(result.items);
      setClimateError('');
    }).catch((error: Error) => {
      if (!controller.signal.aborted) setClimateError(error.message);
    }).finally(() => { if (!controller.signal.aborted) setLoadingClimate(false); });
    return () => controller.abort();
  }, [climateYear, climateType, climateSearch]);

  useEffect(() => {
    let cancelled = false;
    void listSavedWeatherForecasts().then((result) => {
      if (!cancelled) { setSavedForecasts(result.items); setSavedForecastError(''); }
    }).catch((error: Error) => {
      if (!cancelled) setSavedForecastError(error.message);
    }).finally(() => { if (!cancelled) setLoadingSavedForecasts(false); });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    let cancelled = false;
    void listWeatherBulletins().then((result) => {
      if (!cancelled) { setBulletins(result.items); setBulletinError(''); }
    }).catch((error: Error) => {
      if (!cancelled) setBulletinError(error.message);
    }).finally(() => { if (!cancelled) setLoadingBulletins(false); });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!farmId) { setFields([]); setFieldId(''); return; }
    let cancelled = false;
    setLoadingFields(true);
    void api<FarmField[]>(`/v1/farms/${encodeURIComponent(farmId)}/fields`).then((rows) => {
      if (!cancelled) { setFields(rows.filter((field) => !field.archived_at)); setFieldId(''); }
    }).catch((error: Error) => { if (!cancelled) setPageError(error.message); })
      .finally(() => { if (!cancelled) setLoadingFields(false); });
    return () => { cancelled = true; };
  }, [farmId]);

  function updateLocation(latitudeValue: string, longitudeValue: string) {
    setLatitude(latitudeValue);
    setLongitude(longitudeValue);
    setLocationSource('manual');
    setFieldId('');
    setLocationAccuracy(null);
    setForecast(null);
    setStorageNotice('');
    setSaveForecastConsent(false);
    setFormError('');
  }

  function selectField(value: string) {
    setFieldId(value);
    const field = fields.find((item) => item.id === value);
    if (field?.latitude != null && field.longitude != null) {
      updateLocation(String(field.latitude), String(field.longitude));
      setLocationSource('saved-field');
      setFieldId(value);
    } else if (!value) {
      updateLocation('', '');
    }
  }

  function useCurrentLocation() {
    setFormError('');
    if (!navigator.geolocation) {
      setFormError('This browser does not provide location detection. Enter coordinates manually or choose a saved field.');
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition((position) => {
      setLatitude(position.coords.latitude.toFixed(5));
      setLongitude(position.coords.longitude.toFixed(5));
      setLocationAccuracy(Number.isFinite(position.coords.accuracy) ? position.coords.accuracy : null);
      setLocationSource('device');
      setFieldId('');
      setForecast(null);
      setStorageNotice('');
      setSaveForecastConsent(false);
      setFormError('');
      setLocating(false);
    }, (error) => {
      const message = error.code === error.PERMISSION_DENIED
        ? 'Location access was denied. Allow location access in your browser or enter coordinates manually.'
        : error.code === error.TIMEOUT
          ? 'Your device location took too long to respond. Try again or enter coordinates manually.'
          : 'Your current location could not be determined. Check device location settings or enter coordinates manually.';
      setFormError(message);
      setLocating(false);
    }, { enableHighAccuracy: true, timeout: 12000, maximumAge: 60000 });
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setForecast(null);
    setStorageNotice('');
    setFormError('');
    const latitudeNumber = Number(latitude);
    const longitudeNumber = Number(longitude);
    if (!latitude.trim() || !longitude.trim() || !Number.isFinite(latitudeNumber) || !Number.isFinite(longitudeNumber)) {
      setFormError('Enter both farm coordinates as decimal numbers.');
      return;
    }
    if (!saveForecastConsent) {
      setFormError('Confirm that you want this forecast and its coordinates saved to your CropPulse account.');
      return;
    }
    setLoadingForecast(true);
    try {
      const result = await requestWeatherForecast(latitudeNumber, longitudeNumber, true, {
        location_source: locationSource === 'saved-field' && fieldId ? 'saved_field' : locationSource === 'device' ? 'device' : 'manual',
        ...(locationSource === 'saved-field' && fieldId ? { field_id: fieldId } : {}),
      });
      setForecast(result);
      if ((result.status === 'available' || result.status === 'stale') && !result.stored) {
        setStorageNotice('A newer forecast for this location is already saved in your account. This older response was shown but did not replace it.');
      }
      if (result.stored && result.record_id && result.retrieved_at && (result.status === 'available' || result.status === 'stale')) {
        const record: SavedWeatherForecast = {
          id: result.record_id,
          requested_coordinates: { latitude: Number(latitudeNumber.toFixed(4)), longitude: Number(longitudeNumber.toFixed(4)) },
          status: result.status,
          retrieved_at: result.retrieved_at,
          updated_at: new Date().toISOString(),
          location_context: result.location_context,
          forecast: result,
        };
        setSavedForecasts((current) => [record, ...current.filter((item) => item.id !== record.id)]);
      }
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'Forecast could not be requested.');
    } finally {
      setLoadingForecast(false);
    }
  }

  async function changeAlertPreference(preference: WeatherAlertPreference) {
    setAlertUpdating(preference.field_id);
    setAlertError('');
    try {
      const result = await updateWeatherAlertPreference(preference.field_id, !preference.enabled);
      setAlertPreferences((items) => items.map((item) => item.field_id === preference.field_id
        ? { ...item, enabled: result.enabled } : item));
    } catch (error) {
      setAlertError(error instanceof Error ? error.message : 'Alert preference could not be saved.');
    } finally { setAlertUpdating(''); }
  }

  async function changeAlertStatus(alert: WeatherAlert, status: 'acknowledged' | 'dismissed') {
    setAlertUpdating(alert.id);
    setAlertError('');
    try {
      const updated = await updateWeatherAlertStatus(alert.id, status);
      setWeatherAlerts((items) => items.map((item) => item.id === alert.id ? updated : item));
    } catch (error) {
      setAlertError(error instanceof Error ? error.message : 'Alert status could not be updated.');
    } finally { setAlertUpdating(''); }
  }

  const locationFarm = farms.find((farm) => farm.id === farmId);
  const rows = forecast?.daily_forecast ?? [];
  const forecastPrompts = buildForecastPrompts(rows);
  const monthlyOutlooks = climateRecords.filter((record) => record.record_type === 'monthly_outlook' && record.geography_type === 'national');
  const seasonalOutlooks = climateRecords.filter((record) => record.record_type === 'seasonal_outlook' && record.geography_type === 'national');

  function renderRainfallRangeChart(records: WeatherClimateRecord[], title: string) {
    if (!records.length) return null;
    const maximum = Math.max(...records.map((record) => record.value_max));
    const scaleMaximum = Math.ceil(maximum / 50) * 50 || 50;
    return <div className="weather-climate-chart" role="img" aria-label={`${title}, rainfall range in millimetres per period`}>
      <h3>{title}</h3>
      <div className="weather-climate-axis"><span>0 mm</span><span>{scaleMaximum} mm</span></div>
      {records.map((record) => {
        const left = (record.value_min / scaleMaximum) * 100;
        const width = Math.max(1, ((record.value_max - record.value_min) / scaleMaximum) * 100);
        return <div className="weather-climate-range-row" key={record.id}>
          <span className="weather-climate-period">{record.period_label}</span>
          <div className="weather-climate-track"><span style={{ left: `${left}%`, width: `${width}%` }} /></div>
          <strong>{record.value_min}–{record.value_max} mm</strong>
        </div>;
      })}
    </div>;
  }

  function openSavedForecast(record: SavedWeatherForecast) {
    const retrievedMillis = new Date(record.retrieved_at).getTime();
    const age = Number.isFinite(retrievedMillis) ? Math.max(0, Math.floor((Date.now() - retrievedMillis) / 1000)) : undefined;
    setForecast({ ...record.forecast, status: 'saved', cache_age_seconds: age,
      message: 'This saved forecast may no longer describe current conditions. Check its retrieval time and forecast dates.' });
    setStorageNotice('');
    setFormError('');
  }

  return <>
    <PageHeader eyebrow="FARM WEATHER" title="Weather & climate" description="View a seven-day model forecast, saved climate outlooks, and your weather alert preferences." />
    {pageError && <ErrorState text={pageError} retry={() => window.location.reload()} />}
    {loadingFarms ? <LoadingState label="Loading your farm locations…" /> : <>
      <section className="panel weather-location-panel">
        <div className="panel-heading"><div><h2>Choose a forecast location</h2><p>Use coordinates saved on a field or enter the farm coordinates yourself.</p></div><MapPin size={19} /></div>
        {farms.length > 0 && <div className="form-grid weather-form-grid">
          <label>Farm<select value={farmId} onChange={(event) => { setFarmId(event.target.value); setFieldId(''); setLatitude(''); setLongitude(''); setLocationSource('manual'); setForecast(null); setStorageNotice(''); }}>
            {farms.map((farm) => <option value={farm.id} key={farm.id}>{farm.name} · {farm.district}</option>)}
          </select></label>
          <label>Saved field coordinates{loadingFields ? <small>Loading fields…</small> : <select value={fieldId} onChange={(event) => selectField(event.target.value)}>
            <option value="">Enter coordinates manually</option>
            {fields.map((field) => <option key={field.id} value={field.id} disabled={field.latitude == null || field.longitude == null}>{field.name}{field.latitude == null ? ' · coordinates not saved' : ` · ${field.latitude}, ${field.longitude}`}</option>)}
          </select>}</label>
        </div>}
        {farms.length === 0 && <p className="weather-location-help">No saved farm is available on this account. You can still enter a location within Rwanda below.</p>}
        <div className="weather-location-actions"><button className="button button-secondary" type="button" onClick={useCurrentLocation} disabled={locating}><LocateFixed size={15} />{locating ? 'Detecting location…' : 'Use my current location'}</button><span>Requires browser location permission and usually HTTPS (or localhost). Detection alone does not save your location; requesting a forecast stores its coordinates with your account.</span></div>
        <form className="form-grid weather-form-grid" onSubmit={(event) => void submit(event)}>
          <label>Latitude<input type="number" inputMode="decimal" min="-90" max="90" step="any" value={latitude} onChange={(event) => updateLocation(event.target.value, longitude)} required placeholder="For example: -2.50" /></label>
          <label>Longitude<input type="number" inputMode="decimal" min="-180" max="180" step="any" value={longitude} onChange={(event) => updateLocation(latitude, event.target.value)} required placeholder="For example: 29.90" /></label>
          <div className="weather-form-submit"><button className="button button-primary" disabled={loadingForecast || !latitude || !longitude}>{loadingForecast ? <><RefreshCw size={15} className="weather-spinning" /> Loading forecast…</> : 'Get 7-day forecast'}</button></div>
          <label className="weather-save-consent"><input type="checkbox" checked={saveForecastConsent} onChange={(event) => setSaveForecastConsent(event.target.checked)} /><span>Save this forecast and its coordinates to my CropPulse account so I can view it later. It is visible through my account and removed if my account is deleted.</span></label>
          {formError && <p className="error-inline weather-form-error" role="alert">{formError}</p>}
        </form>
        <div className="notice notice-info weather-coordinate-note"><ShieldCheck size={16} /><span>{locationSource === 'device' ? <>Location source: device GPS{locationAccuracy != null ? ` (browser-reported accuracy about ${Math.round(locationAccuracy)} m)` : ''}. Forecast coordinates are sent to Open-Meteo and saved with your consent; they are not added to a farm record. Browser location can be approximate. CropPulse checks only a rectangular Rwanda extent, not the exact national boundary or farm boundary.</> : locationSource === 'saved-field' && fieldId ? <>Location source: saved coordinates from your selected field. The field belongs to this account and the forecast will be linked to that field if the coordinates still match when saved. CropPulse does not independently verify the point against Rwanda, district, or farm boundaries.</> : <>Location source: manually entered coordinates. They are not verified as a farm location. Forecast coordinates are sent to Open-Meteo and saved with your consent. CropPulse checks only a rectangular Rwanda extent, not the exact national or farm boundary.</>}</span></div>
        {locationFarm && locationSource !== 'device' && <p className="weather-farm-context">Selected farm context: <strong>{locationFarm.name}, {locationFarm.district}</strong>{locationSource === 'saved-field' ? '. The saved field record provides the location association; its geographic accuracy is not independently verified.' : '. Manually entered coordinates are not linked to this farm.'}</p>}
      </section>

      {forecast && forecast.status === 'unavailable' && <div className="notice notice-error" role="alert">{forecast.message}</div>}
      {storageNotice && <div className="notice notice-warning" role="status">{storageNotice}</div>}
      {forecast && forecast.status === 'stale' && <div className="notice notice-warning weather-stale" role="alert"><strong>STALE FORECAST</strong><span>{forecast.message} Cached forecast age: {formatCacheAge(forecast.cache_age_seconds)}.</span></div>}
      {forecast && forecast.status === 'saved' && <div className="notice notice-warning weather-stale" role="status"><strong>SAVED FORECAST</strong><span>{forecast.message} Original retrieval age: {formatCacheAge(forecast.cache_age_seconds)}.</span></div>}
      {forecast && (forecast.status === 'available' || forecast.status === 'stale' || forecast.status === 'saved') && <>
        {forecast.status === 'available' && <div className="notice notice-success"><CloudRain size={16} /><span>Model forecast available. This is not a current observation.</span></div>}
        <section className="panel weather-results">
          <div className="weather-context-pills"><span>Forecast period: {rows[0]?.date ?? 'not available'} to {rows.at(-1)?.date ?? 'not available'}</span><span>{forecast.status === 'available' ? 'Fresh response' : forecast.status === 'stale' ? `Stale · ${formatCacheAge(forecast.cache_age_seconds)}` : 'Saved forecast · check retrieval time'}</span></div>
          {forecast.location_context && <p className="weather-farm-context"><strong>{forecast.location_context.association === 'owned_field_record' ? `${forecast.location_context.farm_name} · ${forecast.location_context.field_name}` : forecast.location_context.location_source === 'device' ? 'Device location' : 'Coordinate-only location'}.</strong> {forecast.location_context.message}</p>}
          <div className="panel-heading"><div><h2>Seven-day forecast</h2><p>{forecast.message}</p></div><span className="panel-badge">{forecast.forecast_type ?? 'Model forecast'}</span></div>
          <p className="weather-provenance">Retrieved: {formatRetrievedAt(forecast.retrieved_at)} · Provider grid point: {forecast.coordinates?.latitude ?? 'unknown'}, {forecast.coordinates?.longitude ?? 'unknown'}</p>
          {rows.length ? <div className="table-scroll"><table><caption>Daily model forecast · precipitation is the estimated total for each day</caption><thead><tr><th>Date</th><th>Maximum temperature</th><th>Minimum temperature</th><th>Precipitation total</th></tr></thead><tbody>{rows.map((day) => <tr key={day.date}><td><strong>{new Date(`${day.date}T12:00:00`).toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short' })}</strong><small>{day.date}</small></td><td>{day.temperature_max_c == null ? 'Unavailable' : `${day.temperature_max_c} °C`}</td><td>{day.temperature_min_c == null ? 'Unavailable' : `${day.temperature_min_c} °C`}</td><td>{day.precipitation_sum_mm == null ? 'Unavailable' : `${day.precipitation_sum_mm} mm`}</td></tr>)}</tbody></table></div> : <div className="notice notice-warning">The provider returned no daily forecast rows.</div>}
          {rows.length > 0 && <section className="weather-guidance" aria-labelledby="weather-guidance-title">
            <div className="weather-guidance-heading"><div><h3 id="weather-guidance-title">Forecast-based prompts</h3><p>Simple signals from this forecast to help you decide what to check locally.</p></div><span>Automated · not RAB-verified</span></div>
            {forecastPrompts.length ? <div className="weather-guidance-grid">{forecastPrompts.map((prompt) => <article className="weather-guidance-card" key={prompt.title}>
              <h4>{prompt.title}</h4><p><strong>Forecast signal:</strong> {prompt.signal}</p><p><strong>Consider:</strong> {prompt.suggestion}</p>
            </article>)}</div> : <p className="weather-guidance-empty">No rain, dry-spell, or temperature prompt crossed the simple display thresholds for this forecast period. This does not mean conditions are risk-free.</p>}
            <p className="weather-guidance-caveat">These screen thresholds are simple indicators, not crop-specific limits or official warnings. Daily precipitation and temperature are model estimates; they do not measure soil moisture or confirm rainfall at your plot. Check local conditions before acting. These prompts do not diagnose disease or recommend pesticides. For farm-specific guidance, contact a local agricultural extension officer.</p>
          </section>}
          <div className="notice notice-info weather-coordinate-note"><CloudRain size={16} /><span>Daily precipitation and temperature are model estimates. They do not measure your soil moisture, confirm rainfall at your plot, or by themselves determine planting, irrigation, pesticide, or disease actions. For farm-specific advice, contact a local agricultural extension officer.</span></div>
          <p className="weather-attribution">{forecast.attribution ?? 'Weather forecast data by Open-Meteo.com (CC BY 4.0)'}</p>
        </section>
      </>}
    </>}
    <section className="panel weather-results">
      <div className="panel-heading"><div><h2>Your saved forecasts</h2><p>The latest saved forecast for each requested location, up to 50 locations.</p></div><CloudRain size={19} /></div>
      {savedForecastError && <div className="notice notice-warning" role="status">Saved forecast list is unavailable: {savedForecastError}</div>}
      {loadingSavedForecasts && <LoadingState label="Loading your saved forecasts…" />}
      {!loadingSavedForecasts && !savedForecastError && savedForecasts.length === 0 && <p className="weather-location-help">You have no saved forecasts yet.</p>}
      {!loadingSavedForecasts && savedForecasts.length > 0 && <div className="weather-bulletin-list">{savedForecasts.map((record) => <article className="weather-bulletin" key={record.id}>
        <div className="weather-bulletin-copy"><h3>Location {record.requested_coordinates.latitude}, {record.requested_coordinates.longitude}</h3><p>Retrieved {formatRetrievedAt(record.retrieved_at)} · {record.status === 'stale' ? 'Provider cache was stale when saved' : 'Open-Meteo forecast'}</p></div>
        <button className="button button-secondary" type="button" onClick={() => openSavedForecast(record)}>View saved forecast</button>
      </article>)}</div>}
    </section>
    <section className="panel weather-alert-section" aria-labelledby="weather-alert-heading">
      <div className="panel-heading"><div><h2 id="weather-alert-heading">Weather alerts</h2><p>Manage future in-app alert preferences and review alert history.</p></div><ShieldCheck size={19} /></div>
      <div className="notice notice-info weather-bulletin-notice"><ShieldCheck size={16} /><span>No agricultural weather rules have been approved for automatic alerts. Saving a preference does not start forecast monitoring, and CropPulse currently generates no farming warnings from weather values.</span></div>
      {alertError && <div className="notice notice-error" role="alert">{alertError}</div>}
      {alertLoading ? <LoadingState label="Loading weather alert settings…" /> : <>
        {alertPreferences.length === 0 ? <p className="weather-location-help">Add a farm field with coordinates to choose a location for a future alert preference. Saved points are not independently checked against the exact Rwanda boundary.</p> : <div className="weather-bulletin-list">{alertPreferences.map((preference) => <article className="weather-alert-preference" key={preference.field_id}>
          <div><h3>{preference.farm_name} · {preference.field_name}</h3><p>{preference.has_coordinates ? (preference.within_supported_extent ? 'Coordinates are within the forecast service extent; exact Rwanda and farm boundaries are not verified.' : 'Coordinates are outside the supported forecast extent.') : 'No coordinates are saved for this field.'}</p><small>{preference.enabled ? 'Preference enabled for future reviewed rules; no alerts are currently generated.' : 'Preference off.'}</small></div>
          <label className="weather-alert-toggle"><input type="checkbox" checked={preference.enabled} disabled={alertUpdating === preference.field_id || (!preference.enabled && (!preference.has_coordinates || !preference.within_supported_extent))} onChange={() => void changeAlertPreference(preference)} />Enable future in-app weather alerts for this field</label>
        </article>)}</div>}
        <h3 className="weather-alert-history-title">Alert history</h3>
        {weatherAlerts.length === 0 ? <p className="weather-location-help">No weather alerts have been generated. Alert generation remains inactive until a locally reviewed, source-documented rule is approved.</p> : <div className="weather-bulletin-list">{weatherAlerts.map((alert) => <article className="weather-alert-preference" key={alert.id}>
          <div><strong>{alert.alert_type.replaceAll('_', ' ')}</strong><p>{alert.farm_name && alert.field_name ? `${alert.farm_name} · ${alert.field_name} · ` : ''}{alert.valid_from} to {alert.valid_to} · {alert.reason}</p><small>{alert.status} · {alert.approval_status} rule · Forecast retrieved {formatRetrievedAt(alert.forecast_retrieved_at)} · Expires {formatRetrievedAt(alert.expires_at)}</small></div>
          {alert.status === 'active' && <div className="weather-alert-actions"><button className="button button-secondary" disabled={alertUpdating === alert.id} onClick={() => void changeAlertStatus(alert, 'acknowledged')}>Acknowledge</button><button className="button button-secondary" disabled={alertUpdating === alert.id} onClick={() => void changeAlertStatus(alert, 'dismissed')}>Dismiss</button></div>}
        </article>)}</div>}
        <p className="weather-attribution">Active approved rules available: {alertRulesCount}. No text/SMS or email alerts are sent.</p>
      </>}
    </section>
    <section className="panel weather-climate-section">
      <div className="panel-heading"><div><h2>METEO RWANDA outlook data</h2><p>Rainfall ranges transcribed from selected monthly and seasonal bulletin text. The charts show published outlook ranges, not measured farm weather.</p></div><CloudRain size={19} /></div>
      <div className="weather-climate-filters">
        <label>Valid year<select value={climateYear} onChange={(event) => setClimateYear(event.target.value)}><option value="">All available years</option><option value="2025">2025</option><option value="2026">2026</option></select></label>
        <label>Bulletin period<select value={climateType} onChange={(event) => setClimateType(event.target.value)}><option value="">Monthly and seasonal</option><option value="monthly_outlook">Monthly outlook</option><option value="seasonal_outlook">Seasonal outlook</option></select></label>
        <label>Search period or source note<input value={climateSearch} onChange={(event) => setClimateSearch(event.target.value)} placeholder="For example: October or Rwanda" /></label>
      </div>
      <div className="notice notice-info weather-bulletin-notice"><ShieldCheck size={16} /><span>Only numeric rainfall ranges explicitly transcribed from PDF text appear here. Source notes are summaries, not quotations. District map shading, missing values, and bulletins without a checked numeric range are not converted into data.</span></div>
      {climateError && <div className="notice notice-warning" role="status">Structured outlook data could not be loaded: {climateError}</div>}
      {loadingClimate && <LoadingState label="Loading bulletin data…" />}
      {!loadingClimate && !climateError && climateRecords.length === 0 && <p className="weather-location-help">No checked outlook ranges match these filters.</p>}
      {!loadingClimate && !climateError && climateRecords.length > 0 && <>
        {renderRainfallRangeChart(monthlyOutlooks, 'Monthly national rainfall outlook ranges')}
        {renderRainfallRangeChart(seasonalOutlooks, 'Seasonal national rainfall outlook ranges')}
        <div className="table-scroll weather-climate-table"><table><thead><tr><th>Valid period</th><th>Scope</th><th>Published rainfall range</th><th>Long-term mean</th><th>Outlook</th><th>Source</th></tr></thead><tbody>
          {climateRecords.map((record) => <tr key={record.id}>
            <td><strong>{record.period_label}</strong><small>{record.record_type === 'monthly_outlook' ? 'Monthly outlook' : 'Seasonal outlook'} · {record.period_status}</small></td>
            <td>{record.geography_label}</td>
            <td>{record.value_min}–{record.value_max} {record.unit}</td>
            <td>{record.normal_min == null || record.normal_max == null ? 'Not stated in this record' : `${record.normal_min}–${record.normal_max} mm`}</td>
            <td>{record.anomaly_label ?? 'See source bulletin'}</td>
            <td><a href={weatherBulletinDocumentUrl(record.bulletin.id)} target="_blank" rel="noreferrer">{record.bulletin.title}, p. {record.source_page}</a><small>Issued {formatBulletinDate(record.bulletin.issued_at)} · {record.transcription_status.replaceAll('-', ' ')}</small></td>
          </tr>)}
        </tbody></table></div>
      </>}
      <p className="weather-attribution">Values are linked to the original METEO RWANDA bulletin and page. The listed periods are incomplete and should not be interpreted as a continuous historical series.</p>
    </section>
    <section className="panel weather-bulletin-section">
      <div className="panel-heading"><div><h2>METEO RWANDA forecast bulletins</h2><p>Publisher documents supplied to CropPulse, stored in the database in their original PDF form.</p></div><FileText size={20} /></div>
      <div className="notice notice-info weather-bulletin-notice"><ShieldCheck size={16} /><span>These are monthly or seasonal forecasts, not measured weather observations or farm-coordinate forecasts. Always check the issue and valid dates. Older bulletins are marked as past.</span></div>
      {bulletinError && <div className="notice notice-warning" role="status">The bulletin library is unavailable: {bulletinError}</div>}
      {loadingBulletins && <LoadingState label="Loading weather bulletins…" />}
      {!loadingBulletins && !bulletinError && bulletins.length === 0 && <p className="weather-location-help">No source bulletins have been imported into this database yet.</p>}
      {!loadingBulletins && bulletins.length > 0 && <div className="weather-bulletin-list">{bulletins.map((bulletin) => <article className="weather-bulletin" key={bulletin.id}>
        <div className="weather-bulletin-copy"><span className={`weather-bulletin-status weather-bulletin-${bulletin.status}`}>{bulletin.status === 'past' ? 'Past bulletin' : bulletin.status === 'upcoming' ? 'Upcoming' : 'Current period'}</span><h3>{bulletin.title}</h3><p>{bulletin.publisher} · PDF date {formatBulletinDate(bulletin.issued_at)} · Valid {formatBulletinDate(bulletin.valid_from)} to {formatBulletinDate(bulletin.valid_to)}</p><small>Source review: {bulletin.provenance_status.replaceAll('-', ' ')}</small></div>
        <div className="weather-bulletin-links"><a className="button button-secondary" href={weatherBulletinDocumentUrl(bulletin.id)} target="_blank" rel="noreferrer"><FileText size={15} /> View source PDF</a><a href={bulletin.source_url} target="_blank" rel="noreferrer">METEO RWANDA source page <ExternalLink size={13} /></a></div>
      </article>)}</div>}
      <p className="weather-attribution">Source: METEO RWANDA. PDFs are preserved unchanged; the structured ranges above are a separate, limited transcription of explicitly stated national values. Permission terms for external republication have not been confirmed.</p>
    </section>
  </>;
}
