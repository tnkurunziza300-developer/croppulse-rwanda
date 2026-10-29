import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import { AlertCircle, ArrowLeft, Camera, Check, Clock3, ImagePlus, Leaf, LoaderCircle, RefreshCw, ShieldCheck, Upload, X } from 'lucide-react';
import { api, createCropHealthCase, fetchCropHealthPhoto, listCropHealthCases, listCropHealthCrops, replyToCropHealthCase } from './api';
import type { CropHealthCase, CropHealthUpdate, Farm, FarmField, CropPlan } from './api';
import { PageHeader, LoadingState } from './pages';
import './crop-health.css';
import { CropHealthAIScreening } from './CropHealthAIScreening';

const MAX_PHOTO_BYTES = 5 * 1024 * 1024;

function dateLabel(value: string | null) {
  if (!value) return 'Not provided';
  return new Date(`${value.slice(0, 10)}T12:00:00`).toLocaleDateString();
}

function statusLabel(status: CropHealthCase['status']) {
  return ({ submitted: 'Submitted', under_review: 'Under review', awaiting_farmer: 'Needs your reply', resolved: 'Closed' })[status];
}

function PrivatePhoto({ photoUrl, alt }: { photoUrl: string; alt: string }) {
  const [source, setSource] = useState('');
  const [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    let localUrl = '';
    setSource(''); setError('');
    void fetchCropHealthPhoto(photoUrl, controller.signal).then((blob) => {
      localUrl = URL.createObjectURL(blob);
      setSource(localUrl);
    }).catch((cause: unknown) => {
      if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Photo could not be loaded.');
    });
    return () => { controller.abort(); if (localUrl) URL.revokeObjectURL(localUrl); };
  }, [photoUrl]);
  if (error) return <div className="crop-photo-error" role="status">{error}</div>;
  if (!source) return <div className="crop-photo-loading" role="status"><LoaderCircle className="spin" size={17} /> Loading private photo…</div>;
  return <img className="crop-health-photo" src={source} alt={alt} />;
}

function UpdateList({ updates }: { updates: CropHealthUpdate[] }) {
  if (!updates.length) return <p className="crop-health-muted">No reviewer updates yet.</p>;
  return <ol className="crop-health-timeline">{updates.map((update) => <li key={update.id}>
    <div className="crop-health-update-head"><strong>{update.author_name}</strong><span>{new Date(update.created_at).toLocaleString()}</span></div>
    <small>{update.author_role === 'reviewer' ? 'CropPulse reviewer' : update.author_role === 'farmer' ? 'You' : 'Account unavailable'} · {update.update_type.replaceAll('_', ' ')}</small>
    {update.assessment === 'provisional_observation' && <span className="crop-assessment-tag">Provisional observation</span>}
    <p>{update.message}</p>
  </li>)}</ol>;
}

export function CropHealthPage() {
  const [farms, setFarms] = useState<Farm[]>([]);
  const [crops, setCrops] = useState<string[]>([]);
  const [fields, setFields] = useState<FarmField[]>([]);
  const [plans, setPlans] = useState<CropPlan[]>([]);
  const [cases, setCases] = useState<CropHealthCase[]>([]);
  const [selectedCase, setSelectedCase] = useState<CropHealthCase | null>(null);
  const [farmId, setFarmId] = useState('');
  const [fieldId, setFieldId] = useState('');
  const [planId, setPlanId] = useState('');
  const [crop, setCrop] = useState('');
  const [symptoms, setSymptoms] = useState('');
  const [observedDate, setObservedDate] = useState('');
  const [plantParts, setPlantParts] = useState('');
  const [spreading, setSpreading] = useState('');
  const [photo, setPhoto] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState('');
  const [reviewing, setReviewing] = useState(false);
  const [reply, setReply] = useState('');
  const [busy, setBusy] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const load = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const [farmRows, cropRows, caseRows] = await Promise.all([
        api<Farm[]>('/v1/farms'), listCropHealthCrops(), listCropHealthCases(),
      ]);
      setFarms(farmRows); setCrops(cropRows); setCases(caseRows);
      setFarmId((previous) => farmRows.some((farm) => farm.id === previous) ? previous : farmRows[0]?.id ?? '');
      setCrop((previous) => cropRows.includes(previous) ? previous : cropRows[0] ?? '');
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Crop-health reports could not be loaded.'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    if (!farmId) { setFields([]); setPlans([]); setFieldId(''); setPlanId(''); return; }
    let active = true;
    void Promise.all([
      api<FarmField[]>(`/v1/farms/${encodeURIComponent(farmId)}/fields`),
      api<CropPlan[]>(`/v1/farms/${encodeURIComponent(farmId)}/plans`),
    ]).then(([fieldRows, planRows]) => {
      if (!active) return;
      setFields(fieldRows); setPlans(planRows);
      setFieldId((previous) => fieldRows.some((field) => field.id === previous) ? previous : '');
      setPlanId('');
    }).catch((cause: unknown) => { if (active) setError(cause instanceof Error ? cause.message : 'Farm fields and plans could not be loaded.'); });
    return () => { active = false; };
  }, [farmId]);
  useEffect(() => {
    if (!photo) { setPhotoPreview(''); return; }
    const url = URL.createObjectURL(photo); setPhotoPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [photo]);

  const selectedFarm = useMemo(() => farms.find((farm) => farm.id === farmId), [farms, farmId]);
  const eligiblePlans = useMemo(() => plans.filter((plan) => !fieldId || !plan.field_id || plan.field_id === fieldId), [plans, fieldId]);
  function updatePhoto(file: File | undefined) {
    setNotice(''); setPhoto(null);
    if (!file) return;
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) { setError('Choose a JPEG, PNG, or WebP image.'); return; }
    if (file.size > MAX_PHOTO_BYTES) { setError('Choose a photo no larger than 5 MB.'); return; }
    setError(''); setPhoto(file);
  }
  function reviewReport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError('');
    if (!selectedFarm || !photo) { setError('Choose one of your farms and attach a crop photo.'); return; }
    setReviewing(true);
  }
  async function submitReport() {
    if (!photo || !selectedFarm) return;
    setBusy(true); setUploadProgress(null); setError(''); setNotice('');
    const form = new FormData();
    form.append('farm_id', farmId); form.append('crop', crop); form.append('symptoms', symptoms.trim());
    if (fieldId) form.append('field_id', fieldId);
    if (planId) form.append('crop_plan_id', planId);
    if (observedDate) form.append('observed_date', observedDate);
    if (plantParts.trim()) form.append('plant_parts_affected', plantParts.trim());
    if (spreading) form.append('spreading', spreading);
    form.append('photo', photo, photo.name);
    try {
      const created = await createCropHealthCase(form, setUploadProgress);
      setCases((current) => [created, ...current]); setSelectedCase(created);
      setFarmId(''); setFieldId(''); setPlanId(''); setSymptoms(''); setObservedDate(''); setPlantParts(''); setSpreading(''); setPhoto(null); setReviewing(false);
      setNotice(`Report ${created.id.slice(0, 8)} was submitted for review. No automatic diagnosis was made.`);
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'The crop-health report could not be submitted.'); }
    finally { setBusy(false); setUploadProgress(null); }
  }
  async function sendReply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!selectedCase) return;
    setBusy(true); setError(''); setNotice('');
    try {
      const updated = await replyToCropHealthCase(selectedCase.id, reply);
      setSelectedCase(updated); setCases((current) => current.map((item) => item.id === updated.id ? updated : item));
      setReply(''); setNotice('Your reply was sent privately to the CropPulse reviewer.');
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Your reply could not be sent.'); }
    finally { setBusy(false); }
  }
  async function openCase(caseId: string) {
    setError(''); setNotice('');
    try { setSelectedCase(await api<CropHealthCase>(`/v1/crop-health/cases/${encodeURIComponent(caseId)}`)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'The report details could not be opened.'); }
  }

  return <>
    <PageHeader eyebrow="FARMER SUPPORT" title="Crop health reports" description="Share a photo and describe what you see. A district-assigned CropPulse reviewer can follow up on your private case." action={<button className="button button-secondary" onClick={() => void load()}><RefreshCw size={15} /> Refresh</button>} />
    <div className="notice notice-info crop-health-notice"><ShieldCheck size={17} /><span>Reports are private to your account and authorized reviewers for your farm district. Maize photos may show experimental model-ranked labels; these are not diagnoses, and other crops go to human review without model screening. CropPulse reviewers’ agricultural qualifications are not verified by this system.</span></div>
    {error && <div className="notice notice-error" role="alert"><AlertCircle size={17} />{error}</div>}
    {notice && <div className="notice notice-success" role="status"><Check size={17} />{notice}</div>}
    <div className="crop-health-layout">
      <section className="panel crop-health-form-panel">
        <div className="panel-heading"><div><span className="eyebrow">NEW REPORT</span><h2>Tell us what you see</h2><p>Farm and crop information helps route your report to the right district reviewer.</p></div><Leaf size={19} /></div>
        {!farms.length && !loading ? <div className="crop-health-no-farms"><strong>Add a farm first</strong><p>A report must be linked to one of your CropPulse farms.</p><a className="button button-secondary" href="/farms">Open My farms</a></div>
          : reviewing ? <div className="crop-health-confirm">
            <div className="crop-health-confirm-title"><h3>Review before submitting</h3><span>Private crop-health case</span></div>
            <dl><div><dt>Farm</dt><dd>{selectedFarm?.name} · {selectedFarm?.district}</dd></div><div><dt>Crop</dt><dd>{crop}</dd></div><div><dt>Field</dt><dd>{fields.find((field) => field.id === fieldId)?.name ?? 'Farm-level report'}</dd></div><div><dt>First noticed</dt><dd>{dateLabel(observedDate || null)}</dd></div><div><dt>Affected plant parts</dt><dd>{plantParts.trim() || 'Not provided'}</dd></div><div><dt>Spreading</dt><dd>{spreading === 'true' ? 'Yes' : spreading === 'false' ? 'No' : 'Not sure / not provided'}</dd></div><div><dt>Symptoms</dt><dd>{symptoms}</dd></div></dl>
            {photoPreview && <img className="crop-health-preview" src={photoPreview} alt="Preview of the selected crop" />}
            {busy && <div className="crop-health-upload-progress" role="status"><span>Uploading your report{uploadProgress === null ? '…' : ` · ${uploadProgress}%`}</span><progress max={100} value={uploadProgress ?? undefined} aria-label="Crop report upload progress" /></div>}
            <div className="crop-health-form-actions"><button className="button button-secondary" type="button" disabled={busy} onClick={() => setReviewing(false)}><ArrowLeft size={15} /> Edit report</button><button className="button button-primary" type="button" disabled={busy} onClick={() => void submitReport()}>{busy ? <LoaderCircle className="spin" size={15} /> : <Upload size={15} />}{busy ? 'Submitting…' : 'Submit privately'}</button></div>
          </div> : <form className="crop-health-form" onSubmit={reviewReport}>
            <label>Farm<select value={farmId} onChange={(event) => setFarmId(event.target.value)} required><option value="" disabled>Choose your farm</option>{farms.map((farm) => <option value={farm.id} key={farm.id}>{farm.name} · {farm.district}</option>)}</select><small>Only farms owned by your account are shown.</small></label>
            <div className="crop-health-form-row"><label>Field <span>(optional)</span><select value={fieldId} onChange={(event) => setFieldId(event.target.value)}><option value="">Farm-level report</option>{fields.map((field) => <option value={field.id} key={field.id}>{field.name}</option>)}</select></label><label>Crop plan <span>(optional)</span><select value={planId} onChange={(event) => { const value = event.target.value; setPlanId(value); const plan = plans.find((item) => item.id === value); if (plan) { setCrop(plan.crop); if (plan.field_id) setFieldId(plan.field_id); } }}><option value="">No linked plan</option>{eligiblePlans.map((plan) => <option value={plan.id} key={plan.id}>{plan.crop} · Season {plan.season}</option>)}</select></label></div>
            <label>Crop<select value={crop} onChange={(event) => setCrop(event.target.value)} required>{crops.map((item) => <option value={item} key={item}>{item}</option>)}</select></label>
            <label>What symptoms can you see?<textarea value={symptoms} onChange={(event) => setSymptoms(event.target.value)} minLength={1} maxLength={3000} rows={4} required placeholder="For example: yellow patches, wilting, spots, holes, or affected plant parts. Describe only what you observed." /></label>
            <label>When did you first notice this? <span>(optional)</span><input type="date" value={observedDate} max={new Date().toISOString().slice(0, 10)} onChange={(event) => setObservedDate(event.target.value)} /></label>
            <label>Which parts of the plant are affected? <span>(optional)</span><input value={plantParts} onChange={(event) => setPlantParts(event.target.value)} maxLength={300} placeholder="For example: lower leaves, stems, fruit, or the whole plant" /></label>
            <label>Is the problem spreading? <span>(optional)</span><select value={spreading} onChange={(event) => setSpreading(event.target.value)}><option value="">Not sure / not provided</option><option value="true">Yes</option><option value="false">No</option></select></label>
            <label className="crop-photo-picker"><span>Photo of the affected crop</span><small>JPEG, PNG, or WebP · maximum 5 MB. We remove photo metadata before storing it.</small><input type="file" accept="image/jpeg,image/png,image/webp" capture="environment" onChange={(event) => updatePhoto(event.target.files?.[0])} required={!photo} />{photoPreview ? <span className="crop-photo-choice"><img src={photoPreview} alt="Selected crop photo preview" /><span><strong>{photo?.name}</strong><small>{((photo?.size ?? 0) / 1024 / 1024).toFixed(2)} MB</small></span><button type="button" className="icon-button" aria-label="Remove selected photo" onClick={(event) => { event.preventDefault(); event.stopPropagation(); setPhoto(null); }}><X size={16} /></button></span> : <span className="crop-photo-placeholder"><Camera size={18} />Take a photo or choose an image</span>}</label>
            <div className="crop-health-form-actions"><span><ImagePlus size={15} /> Photo required</span><button className="button button-primary" disabled={busy || loading || !farms.length}>Review report <ArrowLeft className="crop-health-next-icon" size={15} /></button></div>
          </form>}
      </section>

      <section className="panel crop-health-cases-panel">
        <div className="panel-heading"><div><span className="eyebrow">YOUR REPORTS</span><h2>Case history</h2><p>Track status and reviewer follow-up.</p></div><Clock3 size={19} /></div>
        {loading && !cases.length ? <LoadingState label="Loading your reports…" /> : cases.length === 0 ? <div className="crop-health-empty"><div><Leaf size={21} /></div><strong>No reports yet</strong><p>Your submitted crop-health cases will appear here.</p></div> : <div className="crop-health-case-list" aria-label="Your crop-health reports">{cases.map((item) => <button className={`crop-health-case-choice${selectedCase?.id === item.id ? ' selected' : ''}`} key={item.id} onClick={() => void openCase(item.id)}><span><strong>{item.crop} · {item.farm_name}</strong><small>{item.district} · {new Date(item.created_at).toLocaleDateString()}</small></span><span className={`crop-case-status status-${item.status}`}>{statusLabel(item.status)}</span></button>)}</div>}
        {selectedCase && <article className="crop-health-case-detail">
          <div className="crop-health-detail-heading"><div><span className={`crop-case-status status-${selectedCase.status}`}>{statusLabel(selectedCase.status)}</span><h3>{selectedCase.crop} · {selectedCase.farm_name}</h3><p>{selectedCase.field_name ? `${selectedCase.field_name} · ` : ''}{selectedCase.district} · First noticed {dateLabel(selectedCase.observed_date)}</p></div><button className="icon-button" aria-label="Close report details" onClick={() => setSelectedCase(null)}><X size={16} /></button></div>
          <dl className="crop-health-review-facts"><div><dt>First noticed</dt><dd>{dateLabel(selectedCase.observed_date)}</dd></div><div><dt>Affected plant parts</dt><dd>{selectedCase.plant_parts_affected || 'Not provided'}</dd></div><div><dt>Is it spreading?</dt><dd>{selectedCase.spreading === null ? 'Not sure / not provided' : selectedCase.spreading ? 'Yes' : 'No'}</dd></div></dl>
          <p className="crop-health-symptoms">{selectedCase.symptoms}</p>
          <PrivatePhoto photoUrl={selectedCase.photo_url} alt={`Farmer-submitted ${selectedCase.crop} crop photo`} />
          <CropHealthAIScreening screening={selectedCase.ai_screening} />
          <h4>Private case updates</h4><UpdateList updates={selectedCase.updates ?? []} />
          {selectedCase.status === 'awaiting_farmer' && <form className="crop-health-reply" onSubmit={(event) => void sendReply(event)}><label htmlFor="crop-health-reply">Reply to the review request</label><textarea id="crop-health-reply" value={reply} onChange={(event) => setReply(event.target.value)} maxLength={4000} rows={3} required /><button className="button button-primary" disabled={busy || !reply.trim()}>{busy ? 'Sending…' : 'Send reply'}</button></form>}
          {selectedCase.status === 'resolved' && <p className="crop-health-muted">This case is closed. Reopening is not available in this phase.</p>}
        </article>}
      </section>
    </div>
  </>;
}
