import { useCallback, useEffect, useState } from 'react';
import { AlertCircle, Check, Clock3, LoaderCircle, RefreshCw, ShieldCheck } from 'lucide-react';
import { fetchCropHealthPhoto, listReviewerCropHealthCases, updateReviewerCropHealthCase, getReviewerCropHealthCase } from './api';
import type { CropHealthAssessment, CropHealthCase, CropHealthUpdate } from './api';
import { ErrorState, LoadingState, PageHeader } from './pages';
import './crop-health.css';
import { CropHealthAIScreening } from './CropHealthAIScreening';

function PrivatePhoto({ photoUrl, alt }: { photoUrl: string; alt: string }) {
  const [source, setSource] = useState('');
  const [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    let localUrl = '';
    setSource(''); setError('');
    void fetchCropHealthPhoto(photoUrl, controller.signal).then((blob) => {
      localUrl = URL.createObjectURL(blob); setSource(localUrl);
    }).catch((cause: unknown) => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Photo could not be loaded.'); });
    return () => { controller.abort(); if (localUrl) URL.revokeObjectURL(localUrl); };
  }, [photoUrl]);
  if (error) return <div className="crop-photo-error" role="status">{error}</div>;
  if (!source) return <div className="crop-photo-loading" role="status"><LoaderCircle className="spin" size={17} /> Loading private photo…</div>;
  return <img className="crop-health-photo" src={source} alt={alt} />;
}

function statusLabel(status: CropHealthCase['status']) {
  return ({ submitted: 'Submitted', under_review: 'Under review', awaiting_farmer: 'Awaiting farmer', resolved: 'Closed' })[status];
}

function UpdateList({ updates }: { updates: CropHealthUpdate[] }) {
  if (!updates.length) return <p className="crop-health-muted">No private case updates yet.</p>;
  return <ol className="crop-health-timeline">{updates.map((update) => <li key={update.id}>
    <div className="crop-health-update-head"><strong>{update.author_name}</strong><span>{new Date(update.created_at).toLocaleString()}</span></div>
    <small>{update.author_role === 'reviewer' ? 'CropPulse reviewer' : 'Farmer'} · {update.update_type.replaceAll('_', ' ')}</small>
    {update.assessment === 'provisional_observation' && <span className="crop-assessment-tag">Provisional observation</span>}
    <p>{update.message}</p>
  </li>)}</ol>;
}

export function CropHealthReviewPage() {
  const [cases, setCases] = useState<CropHealthCase[]>([]);
  const [selected, setSelected] = useState<CropHealthCase | null>(null);
  const [message, setMessage] = useState('');
  const [assessment, setAssessment] = useState<CropHealthAssessment>('unresolved');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const load = useCallback(async () => {
    setLoading(true); setError('');
    try { setCases(await listReviewerCropHealthCases()); }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'The crop-health review queue could not be loaded.'); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void load(); }, [load]);

  async function openCase(caseId: string) {
    setError(''); setNotice(''); setMessage(''); setAssessment('unresolved');
    try { setSelected(await getReviewerCropHealthCase(caseId)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'The report could not be opened.'); }
  }

  async function reviewAction(action: 'start_review' | 'request_information' | 'provide_update' | 'resolve') {
    if (!selected) return;
    setBusy(true); setError(''); setNotice('');
    try {
      const updated = await updateReviewerCropHealthCase(selected.id, {
        action, message: message.trim(), assessment: assessment,
      });
      setSelected(updated); setCases((current) => current.map((item) => item.id === updated.id ? updated : item));
      setMessage('');
      setNotice(action === 'request_information' ? 'Your request was sent privately to the farmer.' : action === 'resolve' ? 'The case is marked resolved.' : 'Your private case update was saved.');
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'The review update could not be saved.'); }
    finally { setBusy(false); }
  }

  return <>
    <PageHeader eyebrow="REVIEW WORKSPACE" title="Crop health review" description="Review farmer-submitted reports in your authorized district scope and follow up privately." action={<button className="button button-secondary" onClick={() => void load()}><RefreshCw size={15} /> Refresh</button>} />
    <div className="notice notice-info crop-health-notice"><ShieldCheck size={17} /><span>Photos are farmer-submitted evidence, not an automatic diagnosis. CropPulse reviewer qualifications are not verified here. Mark observations as provisional; do not prescribe pesticide products, rates, or withdrawal periods from this screen.</span></div>
    {error && <ErrorState text={error} />}
    {notice && <div className="notice notice-success" role="status"><Check size={17} />{notice}</div>}
    <div className="crop-health-review-layout">
      <section className="panel crop-health-review-queue">
        <div className="panel-heading"><div><span className="eyebrow">DISTRICT-SCOPED CASES</span><h2>Reports</h2><p>Access is checked against your active reviewer assignment each time.</p></div><Clock3 size={19} /></div>
        {loading && !cases.length ? <LoadingState label="Loading review queue…" /> : cases.length === 0 ? <div className="crop-health-empty"><div><Clock3 size={21} /></div><strong>No reports in your scope</strong><p>Reports appear here when a farmer submits one from a district assigned to your reviewer account.</p></div> : <div className="crop-health-case-list" aria-label="Crop-health review cases">{cases.map((item) => <button className={`crop-health-case-choice${selected?.id === item.id ? ' selected' : ''}`} key={item.id} onClick={() => void openCase(item.id)}><span><strong>{item.crop} · {item.farm_name}</strong><small>{item.farmer_name} · {item.district}</small></span><span className={`crop-case-status status-${item.status}`}>{statusLabel(item.status)}</span></button>)}</div>}
      </section>
      <section className="panel crop-health-review-detail">
        {!selected ? <div className="crop-health-empty"><div><ShieldCheck size={21} /></div><strong>Select a report</strong><p>Farmer details, photo and private follow-up will appear here.</p></div> : <>
          <div className="crop-health-detail-heading"><div><span className={`crop-case-status status-${selected.status}`}>{statusLabel(selected.status)}</span><h2>{selected.crop} · {selected.farm_name}</h2><p>{selected.farmer_name} · {selected.field_name ? `${selected.field_name} · ` : ''}{selected.district} · First noticed {selected.observed_date ?? 'not provided'}</p></div><span className="crop-health-case-date">Submitted {new Date(selected.created_at).toLocaleString()}</span></div>
          <dl className="crop-health-review-facts"><div><dt>Symptoms described by farmer</dt><dd>{selected.symptoms}</dd></div><div><dt>Plant parts affected</dt><dd>{selected.plant_parts_affected || 'Not provided'}</dd></div><div><dt>Reported as spreading</dt><dd>{selected.spreading === null ? 'Not provided' : selected.spreading ? 'Yes' : 'No'}</dd></div><div><dt>Linked crop plan</dt><dd>{selected.crop_plan_status ?? 'No plan linked'}</dd></div><div><dt>Assessment state</dt><dd>{selected.diagnosis_status === 'provisional_observation' ? 'Provisional observation only' : 'Unresolved; no diagnosis recorded'}</dd></div></dl>
          <PrivatePhoto photoUrl={selected.photo_url} alt={`Private farmer-submitted photo of ${selected.crop}`} />
          <CropHealthAIScreening screening={selected.ai_screening} />
          <h3>Private case history</h3><UpdateList updates={selected.updates ?? []} />
          {selected.status === 'submitted' && <form className="crop-health-review-form" onSubmit={(event) => event.preventDefault()}><label htmlFor="review-message">Start review note</label><textarea id="review-message" value={message} onChange={(event) => setMessage(event.target.value)} minLength={1} maxLength={4000} rows={3} required placeholder="Write a short private update for the farmer." /><button type="button" className="button button-primary" disabled={busy || !message.trim()} onClick={() => void reviewAction('start_review')}>{busy ? 'Saving…' : 'Start review'}</button></form>}
          {selected.status === 'under_review' && <form className="crop-health-review-form" onSubmit={(event) => event.preventDefault()}>
            <label htmlFor="review-message">Private update or question</label><textarea id="review-message" value={message} onChange={(event) => setMessage(event.target.value)} minLength={1} maxLength={4000} rows={3} required placeholder="Ask for more detail, or share a cautious observation. Notes are visible to the farmer." />
            <label htmlFor="review-assessment">Observation status</label><select id="review-assessment" value={assessment} onChange={(event) => setAssessment(event.target.value as CropHealthAssessment)}><option value="unresolved">No assessment / unresolved</option><option value="provisional_observation">Provisional observation</option></select>
            <div className="crop-health-form-actions"><button type="button" className="button button-secondary" disabled={busy || !message.trim()} onClick={() => void reviewAction('request_information')}>Request more information</button><button type="button" className="button button-secondary" disabled={busy || !message.trim()} onClick={() => void reviewAction('provide_update')}>Send update</button><button type="button" className="button button-primary" disabled={busy || !message.trim()} onClick={() => void reviewAction('resolve')}>Resolve case</button></div>
          </form>}
          {selected.status === 'awaiting_farmer' && <p className="crop-health-muted">Waiting for the farmer to reply. The case returns to your queue when they respond.</p>}
          {selected.status === 'resolved' && <p className="crop-health-muted">This case is closed. Reopening is not available in this phase.</p>}
          {selected.status === 'resolved' && selected.diagnosis_status === 'unresolved' && <div className="notice notice-info"><AlertCircle size={16} />This case is operationally closed; it does not mean a disease was diagnosed.</div>}
        </>}
      </section>
    </div>
  </>;
}
