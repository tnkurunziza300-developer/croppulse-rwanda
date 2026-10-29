import { useCallback, useEffect, useRef, useState } from 'react';
import { api, type CropPlan, type FarmField, type FarmHarvest, type FarmTimelineEntry, type IrrigationRecord, type SavedWeatherForecast, type SoilObservation, type SoilTestRecord } from './api';

type SummaryData = {
  plans: CropPlan[]; irrigation: IrrigationRecord[]; observations: SoilObservation[];
  soilTests: SoilTestRecord[]; harvests: FarmHarvest[]; timeline: FarmTimelineEntry[];
  timelineHasMore: boolean; forecasts: SavedWeatherForecast[];
};
type SummaryKey = keyof SummaryData;
type SummaryRequestKey = Exclude<SummaryKey, 'timelineHasMore'>;
const emptyData = (): SummaryData => ({ plans: [], irrigation: [], observations: [], soilTests: [], harvests: [], timeline: [], timelineHasMore: false, forecasts: [] });
const endpoints: Record<SummaryRequestKey, (farmId: string) => string> = {
  plans: (id) => `/v1/farms/${encodeURIComponent(id)}/plans`,
  irrigation: (id) => `/v1/farms/${encodeURIComponent(id)}/irrigation-records`,
  observations: (id) => `/v1/farms/${encodeURIComponent(id)}/soil-observations`,
  soilTests: (id) => `/v1/farms/${encodeURIComponent(id)}/soil-tests`,
  harvests: (id) => `/v1/farms/${encodeURIComponent(id)}/harvests`,
  timeline: (id) => `/v1/farms/${encodeURIComponent(id)}/timeline`,
  forecasts: () => '/v1/weather/forecasts',
};
const titles: Record<SummaryRequestKey, string> = {
  plans: 'Crop plans', irrigation: 'Water records', observations: 'Soil observations',
  soilTests: 'Soil-test records', harvests: 'Harvests', timeline: 'Recent activities', forecasts: 'Saved weather forecast',
};

export function FieldDecisionSummary({ farmId, fields, fieldsLoading = false }: { farmId: string; fields: FarmField[]; fieldsLoading?: boolean }) {
  const [fieldId, setFieldId] = useState('');
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<SummaryData>(emptyData);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Partial<Record<SummaryKey, string>>>({});
  const requestId = useRef(0);
  const load = useCallback(async () => {
    const request = ++requestId.current;
    if (!farmId) { setData(emptyData()); setErrors({}); return; }
    setLoading(true); setData(emptyData()); setErrors({});
    const results = await Promise.allSettled([
      api<CropPlan[]>(endpoints.plans(farmId)),
      api<IrrigationRecord[]>(endpoints.irrigation(farmId)),
      api<SoilObservation[]>(endpoints.observations(farmId)),
      api<SoilTestRecord[]>(endpoints.soilTests(farmId)),
      api<FarmHarvest[]>(endpoints.harvests(farmId)),
      api<{ entries: FarmTimelineEntry[]; has_more: boolean }>(endpoints.timeline(farmId)),
      api<{ items: SavedWeatherForecast[]; total: number }>(endpoints.forecasts(farmId)),
    ]);
    if (request !== requestId.current) return;
    const next = emptyData();
    const nextErrors: Partial<Record<SummaryKey, string>> = {};
    const keys: SummaryRequestKey[] = ['plans', 'irrigation', 'observations', 'soilTests', 'harvests', 'timeline', 'forecasts'];
    results.forEach((result, index) => {
      const key = keys[index];
      if (result.status === 'rejected') nextErrors[key] = result.reason instanceof Error ? result.reason.message : `${titles[key]} could not be loaded.`;
      else if (key === 'timeline') {
        const timelineResult = result.value as { entries: FarmTimelineEntry[]; has_more: boolean };
        next.timeline = timelineResult.entries; next.timelineHasMore = timelineResult.has_more;
      }
      else if (key === 'forecasts') next.forecasts = (result.value as { items: SavedWeatherForecast[] }).items;
      else (next[key] as unknown[]) = result.value as unknown[];
    });
    setData(next); setErrors(nextErrors); setLoading(false);
  }, [farmId]);
  useEffect(() => { setFieldId(''); }, [farmId]);
  useEffect(() => {
    if (!open) return;
    void load();
    return () => { requestId.current += 1; };
  }, [load, open]);
  useEffect(() => { if (fieldId && !fields.some((field) => field.id === fieldId)) setFieldId(''); }, [fieldId, fields]);

  const scoped = <T extends { field_id: string | null }>(rows: T[]) => fieldId ? rows.filter((row) => row.field_id === fieldId) : rows;
  const plans = scoped(data.plans);
  const irrigation = scoped(data.irrigation);
  const observations = scoped(data.observations);
  const soilTests = scoped(data.soilTests);
  const harvests = scoped(data.harvests);
  const timeline = data.timeline.filter((entry) => !fieldId || entry.field_id === fieldId);
  const recentActivities = timeline.filter((entry) => ['activity', 'post_harvest_observation', 'crop_plan_created', 'planting_recorded'].includes(entry.event_type));
  const forecasts = data.forecasts.filter((entry) => entry.location_context?.field_id && (!fieldId || entry.location_context.field_id === fieldId)
    && fields.some((field) => field.id === entry.location_context?.field_id));
  const activeField = fields.find((field) => field.id === fieldId);
  const empty = !plans.length && !irrigation.length && !observations.length && !soilTests.length && !harvests.length && !timeline.length && !forecasts.length;
  const totalErrors = Object.keys(errors).length;

  return <section className="panel records-panel field-decision-summary" aria-labelledby="field-decision-summary-title">
    <div className="panel-heading"><div><span className="eyebrow">RECORDS AND EVIDENCE</span><h2 id="field-decision-summary-title">Field decision-support summary</h2><p>A view of available records and gaps. It does not assess crop suitability or provide fertilizer, irrigation, disease, or yield advice.</p></div>
      <button type="button" className="button button-secondary" aria-expanded={open} aria-controls="field-decision-summary-content" onClick={() => setOpen((value) => !value)}>{open ? 'Close summary' : 'Open summary'}</button>
    </div>
    {open && <div id="field-decision-summary-content">
      <label className="summary-field-select">Farm or field<select aria-label="Summary farm or field" value={fieldId} onChange={(event) => setFieldId(event.target.value)} disabled={fieldsLoading}><option value="">Whole farm</option>{fields.map((field) => <option key={field.id} value={field.id}>{field.name}</option>)}</select></label>
    {loading && <p role="status" aria-live="polite">Loading farm records and evidence…</p>}
    {!loading && totalErrors > 0 && <div className="notice notice-error summary-partial-error" role="alert"><div><strong>Some summary data could not be loaded.</strong><ul>{(Object.keys(errors) as SummaryRequestKey[]).map((key) => <li key={key}>{titles[key]}: {errors[key]}</li>)}</ul></div><button type="button" className="text-button" onClick={() => void load()}>Try again</button></div>}
    {!loading && <>
      {empty && totalErrors === 0 && <p className="summary-empty">No records are currently available for {activeField ? activeField.name : 'this farm'}. This does not mean activities did not occur. <a href="#activity-history-title">Record an activity</a>.</p>}
      {empty && totalErrors > 0 && <p className="summary-empty">No successfully loaded records are available to summarize yet.</p>}
      {!empty && <div className="summary-sections">
        <article className="summary-card"><h3>Crop and season</h3>{plans.length ? plans.map((plan) => <div className="summary-item" key={plan.id}><strong>{plan.crop} · Season {plan.season}</strong><span>Plan status recorded: {plan.status.replaceAll('_', ' ')}</span><span>Recorded actual planting: {plan.actual_planting_date ?? 'Not recorded'} · Proposed date: {plan.planting_date}</span><small>Crop plan is provisional; proposed planting date is not an observed event.</small></div>) : <p>No field-linked crop plan is recorded here. <a href="#crop-plans-title">Review crop plans</a>.</p>}</article>
        <article className="summary-card"><h3>Water and weather</h3>{irrigation.length ? irrigation.slice(0, 4).map((row) => <div className="summary-item" key={row.id}><strong>{row.event_date} · {row.irrigation_method.replaceAll('_', ' ')}</strong><span>Farmer reported · Source: {row.water_source.replaceAll('_', ' ')}</span><span>{row.water_quantity == null ? 'Quantity not recorded' : `${row.water_quantity} ${row.water_quantity_unit}`} · {row.duration_value == null ? 'Duration not recorded' : `${row.duration_value} ${row.duration_unit}`}</span></div>) : <p>No field-linked water event is recorded. Missing entries do not show whether water was available or used. <a href="#irrigation-log-title">View water log</a>.</p>}
          {forecasts.length ? forecasts.slice(0, 2).map((item) => <div className="summary-item" key={item.id}><strong>{item.status === 'stale' ? 'Saved forecast marked stale' : 'Saved point forecast'}</strong><span>{item.forecast.source ?? 'Weather source not available'} · Retrieved {new Date(item.retrieved_at).toLocaleString()}</span><span>{item.forecast.forecast_type ?? 'Forecast'}; coordinates are farmer-supplied and not independently verified.</span><a href="/weather">Open weather details</a></div>) : <p>No matching field forecast appears in the latest saved forecast list. This does not rule out older forecasts or establish conditions at this field. <a href="/weather">Check Weather & climate</a>.</p>}
          <small>Saved forecasts are a bounded recent list from the weather service, not a complete history or field observation.</small>
        </article>
        <article className="summary-card"><h3>Soil evidence</h3>{observations.length || soilTests.length ? <>
          {observations.slice(0, 3).map((row) => <div className="summary-item" key={row.id}><strong>Farmer observation · {row.observation_date}</strong><span>Soil description: {row.soil_description || 'Not recorded'} · Drainage: {row.drainage_observation || 'Not recorded'} · Visible erosion: {row.erosion_observation || 'Not recorded'}</span>{row.management_practices && <span>Reported practices: {row.management_practices}</span>}<small>Visible farmer-reported observations are not measured soil-test results.</small></div>)}
          {soilTests.slice(0, 3).map((row) => <div className="summary-item" key={row.id}><strong>Soil-test transcription · {row.test_date}</strong><span>pH: {row.ph_value == null ? 'Not recorded' : row.ph_value}; N: {row.nitrogen_value == null ? 'Not recorded' : `${row.nitrogen_value} ${row.nitrogen_unit}`}; P: {row.phosphorus_value == null ? 'Not recorded' : `${row.phosphorus_value} ${row.phosphorus_unit}`}; K: {row.potassium_value == null ? 'Not recorded' : `${row.potassium_value} ${row.potassium_unit}`}; organic matter: {row.organic_matter_value == null ? 'Not recorded' : `${row.organic_matter_value} ${row.organic_matter_unit}`}</span><small>Farmer-entered transcription; {row.laboratory_name ? `provider named “${row.laboratory_name}” but not independently verified` : 'laboratory/provider not recorded'}{row.report_reference ? ` · Report reference: ${row.report_reference}` : ''}{row.source_details ? ` · Source details: ${row.source_details}` : ''}.</small></div>)}
        </> : <p>No soil observations or test records are available here. Values not recorded are unknown, not zero or normal. <a href="#soil-records-title">Review soil records</a>.</p>}</article>
        <article className="summary-card"><h3>Recent activities and harvest</h3>{harvests.length ? harvests.slice(0, 3).map((row) => <div className="summary-item" key={row.id}><strong>{row.harvest_date} · {row.crop}, Season {row.season}</strong><span>Farmer reported: {row.quantity} {row.quantity_unit} from {row.harvested_area} {row.area_unit}</span><a href="#harvest-records-title">View harvest record</a></div>) : <p>No harvest record is available here. This does not establish that harvest did not occur. <a href="#harvest-records-title">View harvest records</a>.</p>}
          {recentActivities.slice(0, 4).map((entry) => <div className="summary-item" key={entry.id}><strong>{entry.event_date ?? 'Date not recorded'} · {entry.event_type.replaceAll('_', ' ')}</strong><span>{entry.description}</span><small>{entry.source_label}</small><a href={entry.href}>View original records</a></div>)}
          {data.timelineHasMore && <small>Only the latest entries from the existing timeline response are available here; older records are not shown.</small>}
        </article>
      </div>}
      {!empty && <div className="summary-gaps"><h3>Evidence gaps and next steps</h3><ul>
        {!plans.length && <li>No crop plan is linked to {activeField ? 'this field' : 'this farm'} in the records loaded. Record one if useful; a plan is not a validated recommendation.</li>}
        {!soilTests.length && <li>No soil-test transcription is available here. If a report exists, record its measured values, units, date, and source details.</li>}
        {!forecasts.length && <li>No saved point forecast is linked to a recorded field here. Coordinates and forecasts do not verify field boundaries or observed conditions.</li>}
        {totalErrors > 0 && <li>Some records could not be loaded; retry before treating this as a complete summary.</li>}
        <li>For interpretation or decisions requiring local agronomic evidence, contact a qualified local agricultural extension professional. CropPulse currently provides no validated field-specific recommendations.</li>
      </ul></div>}
      <p className="summary-provenance">Stored crop plans are provisional. Irrigation, soil observations, soil-test transcriptions, harvests, and activities are farmer reported unless an original record explicitly says otherwise. A missing value remains unknown.</p>
    </>}
    </div>}
  </section>;
}
