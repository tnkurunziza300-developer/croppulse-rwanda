import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { api, type FarmField, type SoilNutrientUnit, type SoilObservation, type SoilObservationInput, type SoilOrganicMatterUnit, type SoilTestRecord, type SoilTestRecordInput } from './api';

type FormKind = 'observation' | 'test';
type Notice = { type: 'error' | 'success'; text: string } | null;
type ObservationDraft = Omit<SoilObservationInput, 'field_id' | 'soil_description' | 'drainage_observation' | 'erosion_observation' | 'management_practices' | 'notes'> & {
  field_id: string; soil_description: string; drainage_observation: string; erosion_observation: string;
  management_practices: string; notes: string;
};
type SoilTestDraft = Omit<SoilTestRecordInput,
  'field_id' | 'ph_value' | 'nitrogen_value' | 'phosphorus_value' | 'potassium_value' | 'organic_matter_value'
  | 'nitrogen_unit' | 'phosphorus_unit' | 'potassium_unit' | 'organic_matter_unit'
  | 'laboratory_name' | 'report_reference' | 'source_details' | 'notes'> & {
  field_id: string; ph_value: string; nitrogen_value: string; phosphorus_value: string; potassium_value: string;
  organic_matter_value: string; nitrogen_unit: SoilNutrientUnit | ''; phosphorus_unit: SoilNutrientUnit | '';
  potassium_unit: SoilNutrientUnit | ''; organic_matter_unit: SoilOrganicMatterUnit | '';
  laboratory_name: string; report_reference: string; source_details: string; notes: string;
};

const today = () => new Date().toISOString().slice(0, 10);
const blankObservation = (): ObservationDraft => ({ field_id: '', observation_date: today(), soil_description: '', drainage_observation: '', erosion_observation: '', management_practices: '', notes: '' });
const blankTest = (): SoilTestDraft => ({
  field_id: '', test_date: today(), ph_value: '', nitrogen_value: '', nitrogen_unit: '',
  phosphorus_value: '', phosphorus_unit: '', potassium_value: '', potassium_unit: '',
  organic_matter_value: '', organic_matter_unit: '', laboratory_name: '', report_reference: '', source_details: '', notes: '',
});
const textOrNull = (value: string) => value.trim() || null;
const numberOrNull = (value: string) => value === '' ? null : Number(value);
const shown = (value: string | number | null | undefined) => value == null || value === '' ? 'Not recorded' : String(value);
const nutrientUnits: SoilNutrientUnit[] = ['mg/kg', 'g/kg', 'cmol/kg', '%'];

function SoilError({ text, retry }: { text: string; retry: () => void }) {
  return <div className="notice notice-error" role="alert"><span>{text}</span><button type="button" className="text-button" onClick={retry}>Try again</button></div>;
}

export function SoilRecords({ farmId, fields }: { farmId: string; fields: FarmField[] }) {
  const [observations, setObservations] = useState<SoilObservation[]>([]);
  const [tests, setTests] = useState<SoilTestRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState<Notice>(null);
  const [formKind, setFormKind] = useState<FormKind | null>(null);
  const [editingId, setEditingId] = useState('');
  const [busy, setBusy] = useState(false);
  const [observationDraft, setObservationDraft] = useState<ObservationDraft>(blankObservation);
  const [testDraft, setTestDraft] = useState<SoilTestDraft>(blankTest);
  const requestId = useRef(0);

  const load = useCallback(async () => {
    const request = ++requestId.current;
    if (!farmId) { setObservations([]); setTests([]); setError(''); return; }
    setLoading(true); setError('');
    try {
      const [observationRows, testRows] = await Promise.all([
        api<SoilObservation[]>(`/v1/farms/${encodeURIComponent(farmId)}/soil-observations`),
        api<SoilTestRecord[]>(`/v1/farms/${encodeURIComponent(farmId)}/soil-tests`),
      ]);
      if (request === requestId.current) { setObservations(observationRows); setTests(testRows); }
    } catch (cause) {
      if (request === requestId.current) setError(cause instanceof Error ? cause.message : 'Soil records could not be loaded.');
    } finally {
      if (request === requestId.current) setLoading(false);
    }
  }, [farmId]);

  useEffect(() => {
    setObservations([]); setTests([]);
    void load();
    return () => { requestId.current += 1; };
  }, [load]);

  function startObservationEdit(row: SoilObservation) {
    setFormKind('observation'); setEditingId(row.id); setNotice(null);
    setObservationDraft({ field_id: row.field_id ?? '', observation_date: row.observation_date,
      soil_description: row.soil_description ?? '', drainage_observation: row.drainage_observation ?? '',
      erosion_observation: row.erosion_observation ?? '', management_practices: row.management_practices ?? '', notes: row.notes ?? '' });
  }

  function startTestEdit(row: SoilTestRecord) {
    setFormKind('test'); setEditingId(row.id); setNotice(null);
    setTestDraft({ field_id: row.field_id ?? '', test_date: row.test_date, ph_value: row.ph_value == null ? '' : String(row.ph_value),
      nitrogen_value: row.nitrogen_value == null ? '' : String(row.nitrogen_value), nitrogen_unit: row.nitrogen_unit ?? '',
      phosphorus_value: row.phosphorus_value == null ? '' : String(row.phosphorus_value), phosphorus_unit: row.phosphorus_unit ?? '',
      potassium_value: row.potassium_value == null ? '' : String(row.potassium_value), potassium_unit: row.potassium_unit ?? '',
      organic_matter_value: row.organic_matter_value == null ? '' : String(row.organic_matter_value), organic_matter_unit: row.organic_matter_unit ?? '',
      laboratory_name: row.laboratory_name ?? '', report_reference: row.report_reference ?? '', source_details: row.source_details ?? '', notes: row.notes ?? '' });
  }

  function closeForm() { setFormKind(null); setEditingId(''); }

  async function saveObservation(event: FormEvent) {
    event.preventDefault(); if (busy) return;
    const payload: SoilObservationInput = { ...observationDraft, field_id: observationDraft.field_id || null,
      soil_description: textOrNull(observationDraft.soil_description), drainage_observation: textOrNull(observationDraft.drainage_observation),
      erosion_observation: textOrNull(observationDraft.erosion_observation), management_practices: textOrNull(observationDraft.management_practices), notes: textOrNull(observationDraft.notes) };
    await submit('observation', payload);
  }

  async function saveTest(event: FormEvent) {
    event.preventDefault(); if (busy) return;
    const measures: [string, string, string][] = [
      ['Nitrogen', testDraft.nitrogen_value, testDraft.nitrogen_unit], ['Phosphorus', testDraft.phosphorus_value, testDraft.phosphorus_unit],
      ['Potassium', testDraft.potassium_value, testDraft.potassium_unit], ['Organic matter', testDraft.organic_matter_value, testDraft.organic_matter_unit],
    ];
    const incomplete = measures.find(([, value, unit]) => (value === '') !== (unit === ''));
    if (incomplete) { setNotice({ type: 'error', text: `${incomplete[0]} measurement needs both a value and a unit, or both left blank.` }); return; }
    const payload: SoilTestRecordInput = {
      field_id: testDraft.field_id || null, test_date: testDraft.test_date, ph_value: numberOrNull(testDraft.ph_value),
      nitrogen_value: numberOrNull(testDraft.nitrogen_value), nitrogen_unit: testDraft.nitrogen_unit || null,
      phosphorus_value: numberOrNull(testDraft.phosphorus_value), phosphorus_unit: testDraft.phosphorus_unit || null,
      potassium_value: numberOrNull(testDraft.potassium_value), potassium_unit: testDraft.potassium_unit || null,
      organic_matter_value: numberOrNull(testDraft.organic_matter_value), organic_matter_unit: testDraft.organic_matter_unit || null,
      laboratory_name: textOrNull(testDraft.laboratory_name), report_reference: textOrNull(testDraft.report_reference),
      source_details: textOrNull(testDraft.source_details), notes: textOrNull(testDraft.notes),
    };
    await submit('test', payload);
  }

  async function submit(kind: FormKind, payload: SoilObservationInput | SoilTestRecordInput) {
    setBusy(true); setNotice(null);
    const collection = kind === 'observation' ? 'soil-observations' : 'soil-tests';
    try {
      await api(`/v1/farms/${encodeURIComponent(farmId)}/${collection}${editingId ? `/${encodeURIComponent(editingId)}` : ''}`, {
        method: editingId ? 'PUT' : 'POST', body: JSON.stringify(payload),
      });
      setNotice({ type: 'success', text: `${kind === 'observation' ? 'Soil observation' : 'Soil-test record'} saved as farmer-reported information.` });
      closeForm();
      await load();
    } catch (cause) {
      setNotice({ type: 'error', text: cause instanceof Error ? cause.message : 'Soil record could not be saved.' });
    } finally { setBusy(false); }
  }

  const fieldName = (fieldId: string | null) => fieldId ? fields.find((field) => field.id === fieldId)?.name ?? 'Previously linked field' : 'Farm-level record';
  const fieldSelect = (id: string, value: string, change: (value: string) => void) => <label htmlFor={id}>Field (optional)<select id={id} value={value} onChange={(event) => change(event.target.value)}><option value="">Farm-level record</option>{value && !fields.some((field) => field.id === value) && <option value={value}>Previously linked field</option>}{fields.map((field) => <option key={field.id} value={field.id}>{field.name}</option>)}</select></label>;

  return <section className="panel records-panel soil-records" aria-labelledby="soil-records-title">
    <div className="panel-heading"><div><span className="eyebrow">FARMER-REPORTED</span><h2 id="soil-records-title">Soil observations and test records</h2><p>Record visible observations separately from soil-test measurements. CropPulse does not interpret these values or provide fertilizer advice.</p></div><div className="soil-actions"><button type="button" className="button button-secondary" onClick={() => { setFormKind('observation'); setEditingId(''); setObservationDraft(blankObservation()); setNotice(null); }}>Record observation</button><button type="button" className="button button-secondary" onClick={() => { setFormKind('test'); setEditingId(''); setTestDraft(blankTest()); setNotice(null); }}>Record soil test</button></div></div>
    <div className="notice notice-info soil-boundary" role="note">All records are entered by you. A laboratory or provider name and report reference are not independently verified. Blank values mean unmeasured or not recorded, not zero, normal, or safe.</div>
    {notice && <div className={`notice notice-${notice.type}`} role={notice.type === 'error' ? 'alert' : 'status'}>{notice.text}</div>}
    {error && <SoilError text={error} retry={() => void load()} />}
    {loading && <div className="inline-state" role="status" aria-live="polite">Loading soil records…</div>}
    {!loading && !error && observations.length === 0 && tests.length === 0 && <div className="empty-state"><strong>No soil records yet</strong><p>Optionally add farmer-entered observations or measurements from a soil-test report. These do not generate recommendations.</p></div>}
    {formKind === 'observation' && <form className="activity-form soil-form" onSubmit={(event) => void saveObservation(event)}>
      <h3 className="wide-field">{editingId ? 'Correct soil observation' : 'New soil observation'}</h3>
      {fieldSelect('soil-observation-field', observationDraft.field_id, (field_id) => setObservationDraft({ ...observationDraft, field_id }))}
      <label htmlFor="soil-observation-date">Observation date<input id="soil-observation-date" type="date" max={today()} required value={observationDraft.observation_date} onChange={(event) => setObservationDraft({ ...observationDraft, observation_date: event.target.value })} /></label>
      <label htmlFor="soil-description">Soil type or description (optional)<input id="soil-description" maxLength={500} value={observationDraft.soil_description} onChange={(event) => setObservationDraft({ ...observationDraft, soil_description: event.target.value })} /></label>
      <label htmlFor="soil-drainage">Drainage observation (optional)<input id="soil-drainage" maxLength={500} value={observationDraft.drainage_observation} onChange={(event) => setObservationDraft({ ...observationDraft, drainage_observation: event.target.value })} /></label>
      <label htmlFor="soil-erosion">Visible erosion observation (optional)<input id="soil-erosion" maxLength={500} value={observationDraft.erosion_observation} onChange={(event) => setObservationDraft({ ...observationDraft, erosion_observation: event.target.value })} /></label>
      <label className="wide-field" htmlFor="soil-management">Soil-management or conservation practices (optional)<textarea id="soil-management" maxLength={2000} rows={2} value={observationDraft.management_practices} onChange={(event) => setObservationDraft({ ...observationDraft, management_practices: event.target.value })} /></label>
      <label className="wide-field" htmlFor="soil-observation-notes">Notes (optional)<textarea id="soil-observation-notes" maxLength={2000} rows={2} value={observationDraft.notes} onChange={(event) => setObservationDraft({ ...observationDraft, notes: event.target.value })} /></label>
      <div className="form-end"><button type="button" className="button button-secondary" onClick={closeForm}>Cancel</button><button className="button button-primary" disabled={busy}>{busy ? 'Saving…' : editingId ? 'Save correction' : 'Save observation'}</button></div>
    </form>}
    {formKind === 'test' && <form className="activity-form soil-form" onSubmit={(event) => void saveTest(event)}>
      <h3 className="wide-field">{editingId ? 'Correct soil-test record' : 'New soil-test record'}</h3>
      {fieldSelect('soil-test-field', testDraft.field_id, (field_id) => setTestDraft({ ...testDraft, field_id }))}
      <label htmlFor="soil-test-date">Test date<input id="soil-test-date" type="date" max={today()} required value={testDraft.test_date} onChange={(event) => setTestDraft({ ...testDraft, test_date: event.target.value })} /></label>
      <p className="wide-field soil-scale-note">Optional pH uses the conventional unitless 0–14 scale. Nutrient and organic-matter measurements require the unit shown on your report; values are stored as entered and are not compared or interpreted.</p>
      <label htmlFor="soil-ph">pH (unitless, 0–14; optional)<input id="soil-ph" type="number" min="0" max="14" step="any" value={testDraft.ph_value} onChange={(event) => setTestDraft({ ...testDraft, ph_value: event.target.value })} /></label>
      {([['nitrogen', 'Nitrogen'], ['phosphorus', 'Phosphorus'], ['potassium', 'Potassium']] as const).map(([key, label]) => <div className="soil-measure" key={key}>
        <label htmlFor={`soil-${key}`}>{label} value (optional)<input id={`soil-${key}`} type="number" min="0" max="1000000000" step="any" value={testDraft[`${key}_value`]} onChange={(event) => setTestDraft({ ...testDraft, [`${key}_value`]: event.target.value })} /></label>
        <label htmlFor={`soil-${key}-unit`}>{label} unit<select id={`soil-${key}-unit`} value={testDraft[`${key}_unit`]} onChange={(event) => setTestDraft({ ...testDraft, [`${key}_unit`]: event.target.value as SoilNutrientUnit | '' })}><option value="">Not recorded</option>{nutrientUnits.map((unit) => <option key={unit} value={unit}>{unit}</option>)}</select></label>
      </div>)}
      <div className="soil-measure"><label htmlFor="soil-organic-matter">Organic matter value (optional)<input id="soil-organic-matter" type="number" min="0" max="1000000000" step="any" value={testDraft.organic_matter_value} onChange={(event) => setTestDraft({ ...testDraft, organic_matter_value: event.target.value })} /></label>
        <label htmlFor="soil-organic-matter-unit">Organic matter unit<select id="soil-organic-matter-unit" value={testDraft.organic_matter_unit} onChange={(event) => setTestDraft({ ...testDraft, organic_matter_unit: event.target.value as SoilOrganicMatterUnit | '' })}><option value="">Not recorded</option><option value="g/kg">g/kg</option><option value="%">%</option></select></label></div>
      <label htmlFor="soil-lab">Laboratory or provider name (optional)<input id="soil-lab" maxLength={240} value={testDraft.laboratory_name} onChange={(event) => setTestDraft({ ...testDraft, laboratory_name: event.target.value })} /></label>
      <label htmlFor="soil-report-ref">Report reference (optional)<input id="soil-report-ref" maxLength={240} value={testDraft.report_reference} onChange={(event) => setTestDraft({ ...testDraft, report_reference: event.target.value })} /></label>
      <label className="wide-field" htmlFor="soil-source-details">Source or transcription details (optional)<textarea id="soil-source-details" maxLength={2000} rows={2} value={testDraft.source_details} onChange={(event) => setTestDraft({ ...testDraft, source_details: event.target.value })} /></label>
      <label className="wide-field" htmlFor="soil-test-notes">Notes (optional)<textarea id="soil-test-notes" maxLength={2000} rows={2} value={testDraft.notes} onChange={(event) => setTestDraft({ ...testDraft, notes: event.target.value })} /></label>
      <div className="form-end"><button type="button" className="button button-secondary" onClick={closeForm}>Cancel</button><button className="button button-primary" disabled={busy}>{busy ? 'Saving…' : editingId ? 'Save correction' : 'Save test record'}</button></div>
    </form>}
    {!loading && <div className="soil-record-grid">
      <section aria-labelledby="soil-observations-title"><h3 id="soil-observations-title">Farmer soil observations</h3>{observations.length === 0 ? <p className="soil-empty">No observations recorded.</p> : observations.map((row) => <article className="review-card soil-record-card" key={row.id}><div className="review-card-head"><div><strong>{row.observation_date}</strong><small>{fieldName(row.field_id)} · Farmer reported</small></div><button type="button" className="text-button" onClick={() => startObservationEdit(row)}>Correct</button></div><dl>
        <div><dt>Soil description</dt><dd>{shown(row.soil_description)}</dd></div><div><dt>Drainage</dt><dd>{shown(row.drainage_observation)}</dd></div><div><dt>Visible erosion</dt><dd>{shown(row.erosion_observation)}</dd></div><div><dt>Practices</dt><dd>{shown(row.management_practices)}</dd></div><div><dt>Notes</dt><dd>{shown(row.notes)}</dd></div>
      </dl></article>)}</section>
      <section aria-labelledby="soil-tests-title"><h3 id="soil-tests-title">Soil-test measurements entered by farmer</h3>{tests.length === 0 ? <p className="soil-empty">No soil-test records recorded.</p> : tests.map((row) => <article className="review-card soil-record-card" key={row.id}><div className="review-card-head"><div><strong>{row.test_date}</strong><small>{fieldName(row.field_id)} · Farmer entered; not independently verified</small></div><button type="button" className="text-button" onClick={() => startTestEdit(row)}>Correct</button></div><dl>
        <div><dt>pH (unitless, 0–14 scale)</dt><dd>{shown(row.ph_value)}</dd></div><div><dt>Nitrogen</dt><dd>{row.nitrogen_value == null ? 'Not recorded' : `${row.nitrogen_value} ${row.nitrogen_unit}`}</dd></div><div><dt>Phosphorus</dt><dd>{row.phosphorus_value == null ? 'Not recorded' : `${row.phosphorus_value} ${row.phosphorus_unit}`}</dd></div><div><dt>Potassium</dt><dd>{row.potassium_value == null ? 'Not recorded' : `${row.potassium_value} ${row.potassium_unit}`}</dd></div><div><dt>Organic matter</dt><dd>{row.organic_matter_value == null ? 'Not recorded' : `${row.organic_matter_value} ${row.organic_matter_unit}`}</dd></div><div><dt>Laboratory or provider</dt><dd>{shown(row.laboratory_name)}</dd></div><div><dt>Report reference</dt><dd>{shown(row.report_reference)}</dd></div><div><dt>Source details</dt><dd>{shown(row.source_details)}</dd></div><div><dt>Notes</dt><dd>{shown(row.notes)}</dd></div>
      </dl></article>)}</section>
    </div>}
  </section>;
}
