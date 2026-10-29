import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from 'react';
import { Activity, ArrowDownToLine, Check, ChevronRight, CircleAlert, Clock3, Leaf, LoaderCircle, LocateFixed, RefreshCw, ShieldCheck, Users, Sprout } from 'lucide-react';
import { api, createStreamlitHandoff, requestEmailChange } from './api';
import { downloadSavedCropPlanBrief } from './cropPlanBrief';
import { FarmProfileForm } from './FarmProfileForm';
import { SoilRecords } from './SoilRecords';
import { FarmTimeline } from './FarmTimeline';
import { FieldDecisionSummary } from './FieldDecisionSummary';
import type { Activity as FarmActivity, AdminFarmer, AgronomyReviewAuthorizationEvent, CropPlan, CropPlanCreate, CropPlanStatus, CropPlanStatusUpdate, CropRecommendation, CropRecommendationRequest, CropRecommendationResponse, Farm, FarmField, FarmHarvest, FarmHarvestInput, HarvestObservation, HarvestObservationInput, HarvestObservationUnit, IrrigationRecord, IrrigationRecordInput, IrrigationMethod, WaterSource, ReviewItem } from './api';
import { useAuth } from './auth';

const DISTRICTS = ['Bugesera', 'Gatsibo', 'Kayonza', 'Kirehe', 'Ngoma', 'Nyagatare', 'Rwamagana', 'Gisagara', 'Huye', 'Kamonyi', 'Muhanga', 'Nyamagabe', 'Nyanza', 'Nyaruguru', 'Ruhango', 'Karongi', 'Ngororero', 'Nyabihu', 'Nyamasheke', 'Rubavu', 'Rusizi', 'Rutsiro', 'Burera', 'Gakenke', 'Gicumbi', 'Musanze', 'Rulindo', 'Gasabo', 'Kicukiro', 'Nyarugenge'];
const SUPPORTED_CROPS = ['Maize', 'Beans', 'Irish potato', 'Cassava', 'Sorghum', 'Rice', 'Sweet potato', 'Soybean', 'Wheat', 'Banana', 'Coffee', 'Tea'];
const NEXT_PLAN_STATUSES: Partial<Record<CropPlanStatus, CropPlanStatus[]>> = {
  draft: ['cancelled'], planned: ['planted', 'cancelled'], planted: ['monitoring'],
  monitoring: ['harvesting'], harvesting: ['completed'],
};
const DistrictChart = lazy(() => import('./DashboardCharts').then((module) => ({ default: module.DistrictChart })));
const CropChart = lazy(() => import('./DashboardCharts').then((module) => ({ default: module.CropChart })));
type Notice = { type: 'error' | 'success'; text: string } | null;

export function PageHeader({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: ReactNode }) {
  return <div className="page-heading"><div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></div>{action && <div className="heading-action">{action}</div>}</div>;
}
export function LoadingState({ label = 'Loading records…' }: { label?: string }) { return <div className="inline-state" role="status" aria-live="polite"><LoaderCircle className="spin" size={18} aria-hidden="true" />{label}</div>; }
export function ErrorState({ text, retry }: { text: string; retry?: () => void }) { return <div className="notice notice-error" role="alert"><CircleAlert size={17} /><span>{text}</span>{retry && <button className="text-button" onClick={retry}>Try again</button>}</div>; }
function EmptyState({ title, description, icon = <Leaf size={20} /> }: { title: string; description: string; icon?: ReactNode }) { return <div className="empty-state"><div className="empty-icon">{icon}</div><strong>{title}</strong><p>{description}</p></div>; }
function Metric({ label, value, detail, icon }: { label: string; value: string | number; detail: string; icon: ReactNode }) { return <article className="metric-card"><div className="metric-top"><span>{label}</span><span className="metric-icon">{icon}</span></div><strong className="metric-value">{value}</strong><small>{detail}</small></article>; }
function StatusPill({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'green' | 'amber' | 'red' | 'blue' }) { return <span className={`status-pill status-${tone}`}><i />{children}</span>; }
function Alert({ notice }: { notice: Notice }) { return notice ? <div className={`notice notice-${notice.type}`} role={notice.type === 'error' ? 'alert' : 'status'}>{notice.type === 'success' ? <Check size={16} /> : <CircleAlert size={16} />}{notice.text}</div> : null; }
function ConfirmDialog({ title, description, reason, setReason, onCancel, onConfirm, busy, confirmLabel = 'Confirm action' }: { title: string; description: string; reason: string; setReason: (v: string) => void; onCancel: () => void; onConfirm: () => void; busy: boolean; confirmLabel?: string }) {
  return <div className="dialog-backdrop"><section className="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="confirm-title"><span className="dialog-icon"><ShieldCheck size={19} /></span><h2 id="confirm-title">{title}</h2><p>{description}</p><label>Reason for this action<textarea value={reason} onChange={(e) => setReason(e.target.value)} minLength={5} maxLength={1000} rows={3} required /></label><div className="dialog-actions"><button className="button button-secondary" onClick={onCancel}>Cancel</button><button className="button button-primary" disabled={busy || reason.trim().length < 5} onClick={onConfirm}>{busy ? 'Saving…' : confirmLabel}</button></div></section></div>;
}

interface AdminOverview {
  accounts: { total: number; active: number; suspended: number };
  farms: number;
  farmer_reported_activities: number;
  awaiting_review: number;
  farms_by_district: { district: string; farms: number }[];
  reported_activities_by_crop: { crop: string; activities: number }[];
  health: { api: string; database: string };
  definitions: Record<string, string>;
}

export function OverviewPage() {
  const { user } = useAuth();
  const [data, setData] = useState<AdminOverview | null>(null);
  const [farms, setFarms] = useState<Farm[] | null>(null);
  const [farmerPlans, setFarmerPlans] = useState<{ farm: Farm; plan: CropPlan }[] | null>(null);
  const [review, setReview] = useState<ReviewItem[] | null>(null);
  const [error, setError] = useState('');
  const [workspaceError, setWorkspaceError] = useState('');
  const [openingWorkspace, setOpeningWorkspace] = useState(false);
  const openPlanningWorkspace = async () => {
    setWorkspaceError('');
    setOpeningWorkspace(true);
    try {
      const handoff = await createStreamlitHandoff();
      window.location.assign(handoff.redirect_url);
    } catch (e) {
      setWorkspaceError(e instanceof Error ? e.message : 'The CropPulse planning workspace could not be opened.');
      setOpeningWorkspace(false);
    }
  };
  const load = useCallback(async () => {
    try {
      if (user?.role === 'admin') { const value = await api<AdminOverview>('/v1/admin/overview'); setData(value); }
      else if (user?.role === 'reviewer') { const value = await api<ReviewItem[]>('/v1/reviewer/activities?limit=100'); setReview(value); }
      else {
        const value = await api<Farm[]>('/v1/farms');
        const plansByFarm = await Promise.all(value.map(async (farm) => ({
          farm,
          plans: await api<CropPlan[]>(`/v1/farms/${encodeURIComponent(farm.id)}/plans`),
        })));
        setFarmerPlans(plansByFarm.flatMap(({ farm, plans }) => plans.map((plan) => ({ farm, plan }))));
        setFarms(value);
      }
      setError('');
    } catch (e) { setError(e instanceof Error ? e.message : 'Overview is unavailable.'); }
  }, [user]);
  useEffect(() => { void load(); }, [load]);
  return <>
    <PageHeader eyebrow="CROP PULSE / WORKSPACE" title={user?.role === 'admin' ? 'Executive overview' : user?.role === 'reviewer' ? 'Review overview' : 'Your farm workspace'} description={user?.role === 'admin' ? 'A current view of registered accounts, farmer reports, and service connectivity.' : user?.role === 'reviewer' ? 'Your assigned review queue and records requiring a decision.' : 'Your persistent farm records in one place.'} action={<button className="button button-secondary" onClick={() => { setError(''); void load(); }}><RefreshCw size={15} /> Refresh</button>} />
    {error && <ErrorState text={error} retry={() => void load()} />}
    {user?.role === 'admin' && !data && !error && <LoadingState />}
    {user?.role === 'admin' && data && <>
      <div className="metrics-grid">
        <Metric label="Registered accounts" value={data.accounts.total} detail={`${data.accounts.active} active · ${data.accounts.suspended} suspended`} icon={<Users size={18} />} />
        <Metric label="Registered farms" value={data.farms} detail="Current saved farm profiles" icon={<Leaf size={18} />} />
        <Metric label="Reported activities" value={data.farmer_reported_activities} detail="Farmer reported · not verified" icon={<Activity size={18} />} />
        <Metric label="Awaiting review" value={data.awaiting_review} detail="No decision or correction requested" icon={<Clock3 size={18} />} />
      </div>
      <div className="overview-grid">
        <section className="panel chart-panel"><div className="panel-heading"><div><h2>Farms by district</h2><p>Current farm profiles; no historical comparison.</p></div><span className="panel-badge">LIVE COUNTS</span></div>
          {data.farms_by_district.length ? <Suspense fallback={<LoadingState label="Loading chart…" />}><DistrictChart data={data.farms_by_district} /></Suspense> : <EmptyState title="No farm profiles yet" description="District comparisons appear as farmers register farms." />}
        </section>
        <section className="panel chart-panel"><div className="panel-heading"><div><h2>Reported activity by crop</h2><p>Submitted records, not a production estimate.</p></div><span className="panel-badge">FARMER REPORTED</span></div>
          {data.reported_activities_by_crop.length ? <Suspense fallback={<LoadingState label="Loading chart…" />}><CropChart data={data.reported_activities_by_crop} /></Suspense> : <EmptyState title="No activities submitted" description="Crop counts appear when farmers report activities." />}
        </section>
      </div>
      <div className="notice notice-info"><ShieldCheck size={17} /><span>Counts use current persisted records. No trends or percentages are shown because historical account snapshots are not available.</span></div>
    </>}
    {user?.role === 'reviewer' && !review && !error && <LoadingState />}
    {user?.role === 'reviewer' && review && <div className="metrics-grid compact-metrics"><Metric label="In your assigned scope" value={review.length} detail="Persisted activity submissions" icon={<ClipboardCheckIcon />} /><Metric label="Awaiting decision" value={review.filter((row) => row.review_status === 'pending' || row.review_status === 'correction_requested').length} detail="Includes correction requests" icon={<Clock3 size={18} />} /><Metric label="Approved as reviewed" value={review.filter((row) => row.review_status === 'approved_as_reviewed').length} detail="Reviewed status does not mean independently verified" icon={<ShieldCheck size={18} />} /></div>}
    {user?.role === 'farmer' && (!farms || !farmerPlans) && !error && <LoadingState label="Loading your growing seasons…" />}
    {user?.role === 'farmer' && farms && farmerPlans && <>
      <div className="metrics-grid compact-metrics">
        <Metric label="Your farms" value={farms.length} detail="Private to this account" icon={<Leaf size={18} />} />
        <Metric label="Saved crop plans" value={farmerPlans.length} detail="Plans saved through CropPulse" icon={<Sprout size={18} />} />
        <Metric label="In progress" value={farmerPlans.filter(({ plan }) => !['completed', 'cancelled'].includes(plan.status)).length} detail="Based on each plan’s saved status" icon={<Clock3 size={18} />} />
      </div>
      <section className="panel records-panel" aria-labelledby="season-workflow-title">
        <div className="panel-heading"><div><span className="eyebrow">YOUR FARM WORKFLOW</span><h2 id="season-workflow-title">Growing seasons</h2><p>Follow saved crop plans and continue the next available step. Dates and progress are based on your records.</p></div><a href="/farms" className="button button-secondary">Open my farms <ChevronRight size={15} /></a></div>
        {farms.length === 0 ? <div className="quick-link-card"><strong>Start with a farm profile</strong><p>Add your farm and district before creating a crop plan.</p><a href="/farms" className="text-link">Add your first farm <ChevronRight size={15} /></a></div>
          : farmerPlans.length === 0 ? <div className="quick-link-card"><strong>Your next step: create a crop plan</strong><p>Choose a saved farm, crop, season, intended planting date, and planned area.</p><a href="/farms" className="text-link">Create a crop plan <ChevronRight size={15} /></a></div>
            : <div className="review-list">{farmerPlans.map(({ farm, plan }) => {
              const nextStep = plan.status === 'planned' || plan.status === 'draft'
                ? 'When planting happens, record the actual planting date on My farms.'
                : plan.status === 'planted'
                  ? 'Update the plan to monitoring when you begin checking crop progress.'
                  : plan.status === 'monitoring'
                    ? 'Record farm work as it happens. Crop stage observations are not available yet.'
                    : plan.status === 'harvesting'
                      ? 'Record harvest events as farm activities, then complete the plan when the season ends.'
                      : plan.status === 'completed'
                        ? 'This plan is marked complete. Structured yield and cost review is not available yet.'
                        : 'This plan is cancelled.';
              return <article className="review-card" key={plan.id}>
                <div className="review-card-head"><div><div className="review-title-row"><h3>{plan.crop} · Season {plan.season}</h3><StatusPill tone={plan.status === 'completed' ? 'green' : plan.status === 'cancelled' ? 'red' : 'amber'}>{plan.status}</StatusPill></div><p>{farm.name} · {farm.district} · {plan.area_ha} ha</p></div></div>
                <dl className="report-facts"><div><dt>Intended planting</dt><dd>{plan.planting_date}</dd></div><div><dt>Actual planting</dt><dd>{plan.actual_planting_date ?? 'Not recorded'}</dd></div><div className="fact-notes"><dt>Next step</dt><dd>{nextStep}</dd></div></dl>
              </article>;
            })}</div>}
      </section>
      <section className="panel records-panel" aria-labelledby="weather-quick-link-title">
        <div className="panel-heading"><div><span className="eyebrow">FARM WEATHER</span><h2 id="weather-quick-link-title">Check a local point forecast</h2><p>Use saved field coordinates or enter coordinates to view a seven-day model forecast. It is not used in crop recommendations.</p></div><a className="button button-secondary" href="/weather">Open Weather & climate <ChevronRight size={15} /></a></div>
      </section>
      <section className="panel records-panel" aria-labelledby="planning-workspace-title">
        <div className="panel-heading"><div><span className="eyebrow">CROP PULSE PLANNING</span><h2 id="planning-workspace-title">Continue to the full planning workspace</h2><p>Open the existing CropPulse planning and analytics tools. Your CropPulse account is carried over securely, so you do not need to sign in again.</p></div><button className="button button-primary" type="button" onClick={() => void openPlanningWorkspace()} disabled={openingWorkspace}>{openingWorkspace ? <LoaderCircle className="spin" size={15} /> : null}{openingWorkspace ? 'Opening workspace…' : 'Open CropPulse workspace'} <ChevronRight size={15} /></button></div>
        {workspaceError && <ErrorState text={workspaceError} retry={() => void openPlanningWorkspace()} />}
        <p className="muted">This opens the current Streamlit part of CropPulse. Planning and analytics are moving into React gradually; both interfaces use the CropPulse account service.</p>
      </section>
    </>}
  </>;
}
function ClipboardCheckIcon() { return <ShieldCheck size={18} />; }

function HarvestObservations({ farmId, harvest }: { farmId: string; harvest: FarmHarvest }) {
  const [items, setItems] = useState<HarvestObservation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState<Notice>(null);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [editingId, setEditingId] = useState('');
  const [draft, setDraft] = useState({ observed_date: new Date().toISOString().slice(0, 10), storage_method: '', storage_location: '', stored_quantity: '', stored_unit: 'kg' as HarvestObservationUnit, lost_quantity: '', lost_unit: 'kg' as HarvestObservationUnit, condition: '', notes: '', follow_up: '' });
  const endpoint = `/v1/farms/${encodeURIComponent(farmId)}/harvests/${encodeURIComponent(harvest.id)}/observations`;
  const load = useCallback(async () => {
    setLoading(true); setError('');
    try { setItems(await api<HarvestObservation[]>(endpoint)); }
    catch (e) { setError(e instanceof Error ? e.message : 'Post-harvest observations could not be loaded.'); }
    finally { setLoading(false); }
  }, [endpoint]);
  useEffect(() => { void load(); }, [load]);

  function edit(item: HarvestObservation) {
    setEditingId(item.id);
    setDraft({ observed_date: item.observed_date, storage_method: item.storage_method ?? '', storage_location: item.storage_location ?? '', stored_quantity: item.stored_quantity == null ? '' : String(item.stored_quantity), stored_unit: item.stored_unit ?? 'kg', lost_quantity: item.lost_quantity == null ? '' : String(item.lost_quantity), lost_unit: item.lost_unit ?? 'kg', condition: item.condition ?? '', notes: item.notes ?? '', follow_up: item.follow_up ?? '' });
    setOpen(true); setNotice(null);
  }

  async function save(event: FormEvent) {
    event.preventDefault(); if (busy) return;
    const payload: HarvestObservationInput = {
      observed_date: draft.observed_date,
      storage_method: draft.storage_method.trim() || null,
      storage_location: draft.storage_location.trim() || null,
      stored_quantity: draft.stored_quantity === '' ? null : Number(draft.stored_quantity),
      stored_unit: draft.stored_quantity === '' ? null : draft.stored_unit,
      lost_quantity: draft.lost_quantity === '' ? null : Number(draft.lost_quantity),
      lost_unit: draft.lost_quantity === '' ? null : draft.lost_unit,
      condition: draft.condition.trim() || null,
      notes: draft.notes.trim() || null,
      follow_up: draft.follow_up.trim() || null,
    };
    setBusy(true); setNotice(null);
    try {
      await api<HarvestObservation>(`${endpoint}${editingId ? `/${encodeURIComponent(editingId)}` : ''}`, { method: editingId ? 'PUT' : 'POST', body: JSON.stringify(payload) });
      setNotice({ type: 'success', text: editingId ? 'Observation updated as farmer reported.' : 'Observation saved as farmer reported.' });
      setOpen(false); setEditingId('');
      setDraft({ observed_date: new Date().toISOString().slice(0, 10), storage_method: '', storage_location: '', stored_quantity: '', stored_unit: 'kg', lost_quantity: '', lost_unit: 'kg', condition: '', notes: '', follow_up: '' });
      await load();
    } catch (e) { setNotice({ type: 'error', text: e instanceof Error ? e.message : 'Post-harvest observation could not be saved.' }); }
    finally { setBusy(false); }
  }

  return <div className="fact-notes harvest-observation-panel">
    <div className="panel-heading"><div><strong>Post-harvest observations</strong><small>Farmer-reported log. This record does not change harvest totals or crop-plan status and is not technical storage guidance.</small></div><button type="button" className="text-button" onClick={() => { setOpen((value) => !value); setEditingId(''); setNotice(null); }}>Add observation</button></div>
    {notice && <Alert notice={notice} />}
    {error && <ErrorState text={error} retry={() => void load()} />}
    {loading ? <LoadingState label="Loading observations…" /> : !error && items.length === 0 ? <p>No post-harvest observations recorded.</p> : !loading && items.length > 0 && <ul className="observation-list">{items.map((item) => <li key={item.id}>
      <div><strong>{item.observed_date}</strong><span className="verification-label">Farmer reported</span></div>
      {item.storage_method && <p>Handling / storage method: {item.storage_method}</p>}
      {item.storage_location && <p>Location: {item.storage_location}</p>}
      {item.stored_quantity != null && <p>Quantity stored: {item.stored_quantity} {item.stored_unit}</p>}
      {item.lost_quantity != null && <p>Quantity lost/damaged: {item.lost_quantity} {item.lost_unit}</p>}
      {item.condition && <p>Observed condition: {item.condition}</p>}
      {item.notes && <p>Notes: {item.notes}</p>}
      {item.follow_up && <p>Follow-up: {item.follow_up}</p>}
      <button type="button" className="text-button" onClick={() => edit(item)}>Correct entry</button>
    </li>)}</ul>}
    {open && <form className="activity-form" onSubmit={(event) => void save(event)}>
      <strong className="wide-field">{editingId ? 'Correct post-harvest observation' : 'Record post-harvest observation'}</strong>
      <label>Observation date<input type="date" max={new Date().toISOString().slice(0, 10)} required value={draft.observed_date} onChange={(event) => setDraft({ ...draft, observed_date: event.target.value })} /></label>
      <label>Handling / storage method (optional)<input maxLength={160} value={draft.storage_method} onChange={(event) => setDraft({ ...draft, storage_method: event.target.value })} /></label>
      <label>Storage location description (optional)<input maxLength={240} value={draft.storage_location} onChange={(event) => setDraft({ ...draft, storage_location: event.target.value })} /></label>
      <label>Quantity stored (optional)<input type="number" min="0" step="any" value={draft.stored_quantity} onChange={(event) => setDraft({ ...draft, stored_quantity: event.target.value })} /></label>
      <label>Stored quantity unit<select disabled={!draft.stored_quantity} value={draft.stored_unit} onChange={(event) => setDraft({ ...draft, stored_unit: event.target.value as HarvestObservationUnit })}><option value="kg">Kilograms (kg)</option><option value="g">Grams (g)</option><option value="t">Tonnes (t)</option><option value="lb">Pounds (lb)</option></select></label>
      <label>Quantity lost or damaged (optional)<input type="number" min="0" step="any" value={draft.lost_quantity} onChange={(event) => setDraft({ ...draft, lost_quantity: event.target.value })} /></label>
      <label>Lost quantity unit<select disabled={!draft.lost_quantity} value={draft.lost_unit} onChange={(event) => setDraft({ ...draft, lost_unit: event.target.value as HarvestObservationUnit })}><option value="kg">Kilograms (kg)</option><option value="g">Grams (g)</option><option value="t">Tonnes (t)</option><option value="lb">Pounds (lb)</option></select></label>
      <small className="wide-field">Losses are compared with stored quantity only when both are provided in the same unit. Different units are kept as recorded.</small>
      <label className="wide-field">Observed condition (optional)<textarea maxLength={1000} rows={2} value={draft.condition} onChange={(event) => setDraft({ ...draft, condition: event.target.value })} /></label>
      <label className="wide-field">Notes (optional)<textarea maxLength={2000} rows={2} value={draft.notes} onChange={(event) => setDraft({ ...draft, notes: event.target.value })} /></label>
      <label className="wide-field">Follow-up action (optional)<textarea maxLength={2000} rows={2} value={draft.follow_up} onChange={(event) => setDraft({ ...draft, follow_up: event.target.value })} /></label>
      <div className="form-end"><button type="button" className="button button-secondary" onClick={() => { setOpen(false); setEditingId(''); }}>Cancel</button><button className="button button-primary" disabled={busy}>{busy ? 'Saving…' : editingId ? 'Save correction' : 'Save observation'}</button></div>
    </form>}
  </div>;
}

type IrrigationDraft = {
  event_date: string; field_id: string; crop_plan_id: string; water_source: WaterSource;
  water_source_other: string; irrigation_method: IrrigationMethod; irrigation_method_other: string;
  water_quantity: string; water_quantity_unit: 'L' | 'm3'; duration_value: string;
  duration_unit: 'minutes' | 'hours'; purpose: string; notes: string;
};
const blankIrrigationDraft = (): IrrigationDraft => ({
  event_date: new Date().toISOString().slice(0, 10), field_id: '', crop_plan_id: '',
  water_source: 'unknown', water_source_other: '', irrigation_method: 'unknown',
  irrigation_method_other: '', water_quantity: '', water_quantity_unit: 'L',
  duration_value: '', duration_unit: 'minutes', purpose: '', notes: '',
});

export function IrrigationLog({ farmId, fields, plans }: { farmId: string; fields: FarmField[]; plans: CropPlan[] }) {
  const [items, setItems] = useState<IrrigationRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState<Notice>(null);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [editingId, setEditingId] = useState('');
  const [draft, setDraft] = useState<IrrigationDraft>(blankIrrigationDraft);
  const endpoint = `/v1/farms/${encodeURIComponent(farmId)}/irrigation-records`;
  const load = useCallback(async () => {
    setLoading(true); setError('');
    try { setItems(await api<IrrigationRecord[]>(endpoint)); }
    catch (e) { setError(e instanceof Error ? e.message : 'Irrigation records could not be loaded.'); }
    finally { setLoading(false); }
  }, [endpoint]);
  useEffect(() => { void load(); }, [load]);

  function edit(item: IrrigationRecord) {
    setEditingId(item.id);
    setDraft({
      event_date: item.event_date, field_id: item.field_id ?? '', crop_plan_id: item.crop_plan_id ?? '',
      water_source: item.water_source, water_source_other: item.water_source_other ?? '',
      irrigation_method: item.irrigation_method, irrigation_method_other: item.irrigation_method_other ?? '',
      water_quantity: item.water_quantity == null ? '' : String(item.water_quantity),
      water_quantity_unit: item.water_quantity_unit ?? 'L',
      duration_value: item.duration_value == null ? '' : String(item.duration_value),
      duration_unit: item.duration_unit ?? 'minutes', purpose: item.purpose ?? '', notes: item.notes ?? '',
    });
    setOpen(true); setNotice(null);
  }

  async function save(event: FormEvent) {
    event.preventDefault(); if (busy) return;
    const payload: IrrigationRecordInput = {
      event_date: draft.event_date,
      field_id: draft.field_id || null,
      crop_plan_id: draft.crop_plan_id || null,
      water_source: draft.water_source,
      water_source_other: draft.water_source === 'other' ? draft.water_source_other.trim() : null,
      irrigation_method: draft.irrigation_method,
      irrigation_method_other: draft.irrigation_method === 'other' ? draft.irrigation_method_other.trim() : null,
      water_quantity: draft.water_quantity === '' ? null : Number(draft.water_quantity),
      water_quantity_unit: draft.water_quantity === '' ? null : draft.water_quantity_unit,
      duration_value: draft.duration_value === '' ? null : Number(draft.duration_value),
      duration_unit: draft.duration_value === '' ? null : draft.duration_unit,
      purpose: draft.purpose.trim() || null,
      notes: draft.notes.trim() || null,
    };
    setBusy(true); setNotice(null);
    try {
      await api<IrrigationRecord>(`${endpoint}${editingId ? `/${encodeURIComponent(editingId)}` : ''}`, {
        method: editingId ? 'PUT' : 'POST', body: JSON.stringify(payload),
      });
      setNotice({ type: 'success', text: editingId ? 'Irrigation entry corrected as farmer reported.' : 'Irrigation entry saved as farmer reported.' });
      setOpen(false); setEditingId(''); setDraft(blankIrrigationDraft());
      await load();
    } catch (e) {
      setNotice({ type: 'error', text: e instanceof Error ? e.message : 'Irrigation entry could not be saved.' });
    } finally { setBusy(false); }
  }

  return <section className="panel records-panel irrigation-panel" aria-labelledby="irrigation-log-title">
    <div className="panel-heading"><div><span className="eyebrow">FARMER-REPORTED</span><h2 id="irrigation-log-title">Irrigation and water-management log</h2><p>Record a water-related event if useful. These entries are not verified measurements, advice, or an assessment of water adequacy.</p></div><button type="button" className="button button-secondary" onClick={() => { setEditingId(''); setDraft(blankIrrigationDraft()); setNotice(null); setOpen((value) => !value); }}>Record water event</button></div>
    {notice && <Alert notice={notice} />}
    {error && <ErrorState text={error} retry={() => void load()} />}
    {loading ? <LoadingState label="Loading irrigation records…" /> : !error && items.length === 0 ? <EmptyState title="No water events recorded" description="You can save a basic record without entering a quantity or duration." /> : !loading && items.length > 0 && <ul className="observation-list">{items.map((item) => <li key={item.id}>
      <div><strong>{item.event_date}</strong><span className="verification-label">Farmer reported</span></div>
      <p>Water source: {item.water_source === 'other' ? `Other — ${item.water_source_other}` : item.water_source.replaceAll('_', ' ')}</p>
      <p>Method: {item.irrigation_method === 'other' ? `Other — ${item.irrigation_method_other}` : item.irrigation_method.replaceAll('_', ' ')}</p>
      {item.field_id && <p>Field: {fields.find((field) => field.id === item.field_id)?.name ?? 'Previously linked field'}</p>}
      {item.crop_plan_id && <p>Crop plan: {plans.find((plan) => plan.id === item.crop_plan_id)?.crop ?? 'Linked crop plan'}</p>}
      {item.water_quantity != null && <p>Recorded quantity: {item.water_quantity} {item.water_quantity_unit}</p>}
      {item.duration_value != null && <p>Recorded duration: {item.duration_value} {item.duration_unit}</p>}
      {item.purpose && <p>Purpose or observation: {item.purpose}</p>}{item.notes && <p>Notes: {item.notes}</p>}
      <button type="button" className="text-button" onClick={() => edit(item)}>Correct entry</button>
    </li>)}</ul>}
    {open && <form className="activity-form" onSubmit={(event) => void save(event)}>
      <strong className="wide-field">{editingId ? 'Correct water event' : 'Record water event'}</strong>
      <label>Event date<input type="date" max={new Date().toISOString().slice(0, 10)} required value={draft.event_date} onChange={(event) => setDraft({ ...draft, event_date: event.target.value })} /></label>
      <label>Water source<select required value={draft.water_source} onChange={(event) => setDraft({ ...draft, water_source: event.target.value as WaterSource, water_source_other: '' })}><option value="unknown">Unknown</option><option value="rainwater">Rainwater</option><option value="river">River</option><option value="lake">Lake</option><option value="pond_reservoir">Pond or reservoir</option><option value="well_borehole">Well or borehole</option><option value="piped_supply">Piped supply</option><option value="irrigation_scheme">Irrigation scheme</option><option value="other">Other</option></select></label>
      {draft.water_source === 'other' && <label>Other water source<input required maxLength={160} value={draft.water_source_other} onChange={(event) => setDraft({ ...draft, water_source_other: event.target.value })} /> </label>}
      <label>Irrigation method<select required value={draft.irrigation_method} onChange={(event) => setDraft({ ...draft, irrigation_method: event.target.value as IrrigationMethod, irrigation_method_other: '' })}><option value="unknown">Unknown</option><option value="manual">Manual watering</option><option value="watering_can">Watering can</option><option value="hose">Hose</option><option value="sprinkler">Sprinkler</option><option value="drip">Drip</option><option value="furrow">Furrow</option><option value="basin">Basin</option><option value="other">Other</option></select></label>
      {draft.irrigation_method === 'other' && <label>Other method<input required maxLength={160} value={draft.irrigation_method_other} onChange={(event) => setDraft({ ...draft, irrigation_method_other: event.target.value })} /></label>}
      <label>Farm field (optional)<select value={draft.field_id} onChange={(event) => setDraft({ ...draft, field_id: event.target.value })}><option value="">Farm-level event</option>{fields.map((field) => <option key={field.id} value={field.id}>{field.name}</option>)}</select></label>
      <label>Crop plan (optional)<select value={draft.crop_plan_id} onChange={(event) => { const plan = plans.find((item) => item.id === event.target.value); setDraft((current) => ({ ...current, crop_plan_id: event.target.value, ...(plan?.field_id ? { field_id: plan.field_id } : {}) })); }}><option value="">Not linked to a crop plan</option>{plans.map((plan) => <option key={plan.id} value={plan.id}>{plan.crop} · Season {plan.season} · {plan.status}</option>)}</select><small>Linking an entry does not change crop-plan status.</small></label>
      <label>Water quantity (optional)<input type="number" min="0" max="1000000000" step="any" value={draft.water_quantity} onChange={(event) => setDraft({ ...draft, water_quantity: event.target.value })} /></label>
      <label>Quantity unit<select value={draft.water_quantity_unit} onChange={(event) => setDraft({ ...draft, water_quantity_unit: event.target.value as 'L' | 'm3' })}><option value="L">Litres (L)</option><option value="m3">Cubic metres (m³)</option></select></label>
      <label>Duration (optional)<input type="number" min="0" max="100000" step="any" value={draft.duration_value} onChange={(event) => setDraft({ ...draft, duration_value: event.target.value })} /></label>
      <label>Duration unit<select value={draft.duration_unit} onChange={(event) => setDraft({ ...draft, duration_unit: event.target.value as 'minutes' | 'hours' })}><option value="minutes">Minutes</option><option value="hours">Hours</option></select></label>
      <small className="wide-field">Enter measured quantities only if you know them. Amount and unit are saved together; missing values remain unrecorded.</small>
      <label className="wide-field">Purpose or farmer observation (optional)<input maxLength={240} value={draft.purpose} onChange={(event) => setDraft({ ...draft, purpose: event.target.value })} /></label>
      <label className="wide-field">Notes (optional)<textarea maxLength={2000} rows={2} value={draft.notes} onChange={(event) => setDraft({ ...draft, notes: event.target.value })} /></label>
      <div className="form-end"><button type="button" className="button button-secondary" onClick={() => { setOpen(false); setEditingId(''); }}>Cancel</button><button className="button button-primary" disabled={busy}>{busy ? 'Saving…' : editingId ? 'Save correction' : 'Save event'}</button></div>
    </form>}
  </section>;
}

export function FarmsPage() {
  const [farms, setFarms] = useState<Farm[]>([]);
  const [selected, setSelected] = useState('');
  const [activities, setActivities] = useState<FarmActivity[]>([]);
  const [activitiesLoading, setActivitiesLoading] = useState(false);
  const [activitiesError, setActivitiesError] = useState('');
  const [harvests, setHarvests] = useState<FarmHarvest[]>([]);
  const [harvestsLoading, setHarvestsLoading] = useState(false);
  const [harvestsError, setHarvestsError] = useState('');
  const [harvestFormOpen, setHarvestFormOpen] = useState(false);
  const [harvestBusy, setHarvestBusy] = useState(false);
  const [editingHarvestId, setEditingHarvestId] = useState('');
  const [harvestDraft, setHarvestDraft] = useState({
    field_id: '', crop_plan_id: '', crop: SUPPORTED_CROPS[0], season: 'A' as 'A' | 'B' | 'C',
    harvest_date: new Date().toISOString().slice(0, 10), harvested_area: '', area_unit: 'ha' as FarmHarvestInput['area_unit'],
    quantity: '', quantity_unit: 'kg' as FarmHarvestInput['quantity_unit'], loss_quantity: '',
    post_harvest_observations: '', notes: '',
  });
  const [fields, setFields] = useState<FarmField[]>([]);
  const [fieldError, setFieldError] = useState('');
  const [fieldsLoading, setFieldsLoading] = useState(false);
  const [fieldOpen, setFieldOpen] = useState(false);
  const [fieldDraft, setFieldDraft] = useState({ name: '', area_ha: '', latitude: '', longitude: '' });
  const [fieldBusy, setFieldBusy] = useState(false);
  const [fieldLocating, setFieldLocating] = useState(false);
  const [fieldLocationMessage, setFieldLocationMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState<Notice>(null);
  const [farmName, setFarmName] = useState('');
  const [district, setDistrict] = useState('Huye');
  const [area, setArea] = useState('');
  const [formOpen, setFormOpen] = useState(false);
  const [activityOpen, setActivityOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [activity, setActivity] = useState({ crop: 'Maize', season: 'A', activity_type: 'Planting', event_date: new Date().toISOString().slice(0, 10), quantity: '', unit: 'kg', notes: '' });
  const [plans, setPlans] = useState<CropPlan[]>([]);
  const [plansFarmId, setPlansFarmId] = useState('');
  const [plansLoading, setPlansLoading] = useState(false);
  const [plansError, setPlansError] = useState('');
  const [planFormOpen, setPlanFormOpen] = useState(false);
  const [planBusy, setPlanBusy] = useState(false);
  const [editingPlanId, setEditingPlanId] = useState('');
  const [busyPlanId, setBusyPlanId] = useState('');
  const [planNotice, setPlanNotice] = useState<Notice>(null);
  const [recommendation, setRecommendation] = useState<CropRecommendationResponse | null>(null);
  const [recommendationBusy, setRecommendationBusy] = useState(false);
  const [recommendationError, setRecommendationError] = useState('');
  const [selectedRecommendation, setSelectedRecommendation] = useState<CropRecommendation | null>(null);
  const [compareCrops, setCompareCrops] = useState<string[]>([]);
  const [planConditions, setPlanConditions] = useState({ elevation_m: '', irrigation: 'Unknown' as CropRecommendationRequest['irrigation'], water_availability: 'Unknown' as CropRecommendationRequest['water_availability'] });
  const [actualDates, setActualDates] = useState<Record<string, string>>({});
  const [planDraft, setPlanDraft] = useState({ crop: SUPPORTED_CROPS[0], season: 'A' as 'A' | 'B' | 'C', planting_date: new Date().toISOString().slice(0, 10), area_ha: '', field_id: '', notes: '' });
  const planRequestId = useRef(0);
  const activityRequestId = useRef(0);
  const harvestRequestId = useRef(0);
  const fieldRequestId = useRef(0);
  const selectedFarmId = useRef(selected);
  const loadFarms = useCallback(async () => {
    try { const rows = await api<Farm[]>('/v1/farms'); setError(''); setFarms(rows); setSelected((current) => rows.some((f) => f.id === current) ? current : rows[0]?.id ?? ''); }
    catch (e) { setError(e instanceof Error ? e.message : 'Farm records could not be loaded.'); }
    finally { setLoading(false); }
  }, []);
  const loadActivities = useCallback(async (farmId: string) => {
    const requestId = ++activityRequestId.current;
    if (!farmId) { setActivities([]); setActivitiesError(''); setActivitiesLoading(false); return; }
    setActivities([]); setActivitiesError(''); setActivitiesLoading(true);
    try {
      const rows = await api<FarmActivity[]>(`/v1/farms/${encodeURIComponent(farmId)}/activities`);
      if (requestId === activityRequestId.current && selectedFarmId.current === farmId) setActivities(rows);
    } catch (e) {
      if (requestId === activityRequestId.current && selectedFarmId.current === farmId) {
        setActivitiesError(e instanceof Error ? e.message : 'Farm activities could not be loaded.');
      }
    } finally {
      if (requestId === activityRequestId.current && selectedFarmId.current === farmId) setActivitiesLoading(false);
    }
  }, []);
  const loadHarvests = useCallback(async (farmId: string) => {
    const requestId = ++harvestRequestId.current;
    if (!farmId) { setHarvests([]); setHarvestsError(''); setHarvestsLoading(false); return; }
    setHarvests([]); setHarvestsError(''); setHarvestsLoading(true);
    try {
      const rows = await api<FarmHarvest[]>(`/v1/farms/${encodeURIComponent(farmId)}/harvests`);
      if (requestId === harvestRequestId.current && selectedFarmId.current === farmId) setHarvests(rows);
    } catch (e) {
      if (requestId === harvestRequestId.current && selectedFarmId.current === farmId) {
        setHarvestsError(e instanceof Error ? e.message : 'Harvest records could not be loaded.');
      }
    } finally {
      if (requestId === harvestRequestId.current && selectedFarmId.current === farmId) setHarvestsLoading(false);
    }
  }, []);
  const loadFields = useCallback(async (farmId: string) => {
    const requestId = ++fieldRequestId.current;
    if (!farmId) { setFields([]); setFieldError(''); setFieldsLoading(false); return; }
    setFields([]); setFieldError(''); setFieldsLoading(true);
    try {
      const rows = await api<FarmField[]>(`/v1/farms/${encodeURIComponent(farmId)}/fields`);
      if (requestId === fieldRequestId.current && selectedFarmId.current === farmId) setFields(rows);
    } catch (e) {
      if (requestId === fieldRequestId.current && selectedFarmId.current === farmId) {
        setFields([]); setFieldError(e instanceof Error ? e.message : 'Fields could not be loaded.');
      }
    } finally {
      if (requestId === fieldRequestId.current && selectedFarmId.current === farmId) setFieldsLoading(false);
    }
  }, []);
  selectedFarmId.current = selected;
  const loadPlans = useCallback(async (farmId: string) => {
    const requestId = ++planRequestId.current;
    if (!farmId) { setPlans([]); setPlansFarmId(''); setPlansLoading(false); setPlansError(''); return; }
    setPlans([]); setPlansFarmId(''); setPlansLoading(true); setPlansError('');
    try {
      const rows = await api<CropPlan[]>(`/v1/farms/${encodeURIComponent(farmId)}/plans`);
      if (requestId === planRequestId.current && selectedFarmId.current === farmId) { setPlans(rows); setPlansFarmId(farmId); }
    } catch (e) {
      if (requestId === planRequestId.current && selectedFarmId.current === farmId) setPlansError(e instanceof Error ? e.message : 'Crop plans could not be loaded.');
    } finally {
      if (requestId === planRequestId.current && selectedFarmId.current === farmId) setPlansLoading(false);
    }
  }, []);
  useEffect(() => { void loadFarms(); }, [loadFarms]);
  useEffect(() => { void loadActivities(selected); }, [loadActivities, selected]);
  useEffect(() => { void loadHarvests(selected); return () => { harvestRequestId.current += 1; }; }, [loadHarvests, selected]);
  useEffect(() => { void loadFields(selected); }, [loadFields, selected]);
  useEffect(() => { void loadPlans(selected); return () => { planRequestId.current += 1; }; }, [loadPlans, selected]);
  useEffect(() => { setRecommendation(null); setSelectedRecommendation(null); setCompareCrops([]); setRecommendationError(''); }, [selected]);
  async function createFarm(event: FormEvent) {
    event.preventDefault(); setBusy(true); setNotice(null);
    try { await api<Farm>('/v1/farms', { method: 'POST', body: JSON.stringify({ name: farmName, district, area_ha: area ? Number(area) : null }) }); setFarmName(''); setArea(''); setFormOpen(false); setNotice({ type: 'success', text: 'Farm profile saved.' }); setLoading(true); await loadFarms(); }
    catch (e) { setNotice({ type: 'error', text: e instanceof Error ? e.message : 'Farm could not be saved.' }); }
    finally { setBusy(false); }
  }
  async function saveHarvest(event: FormEvent) {
    event.preventDefault();
    const farmId = selected;
    if (!farmId || harvestBusy) return;
    const payload: FarmHarvestInput = {
      field_id: harvestDraft.field_id || null,
      crop_plan_id: harvestDraft.crop_plan_id || null,
      crop: harvestDraft.crop,
      season: harvestDraft.season,
      harvest_date: harvestDraft.harvest_date,
      harvested_area: Number(harvestDraft.harvested_area),
      area_unit: harvestDraft.area_unit,
      quantity: Number(harvestDraft.quantity),
      quantity_unit: harvestDraft.quantity_unit,
      loss_quantity: harvestDraft.loss_quantity === '' ? null : Number(harvestDraft.loss_quantity),
      post_harvest_observations: harvestDraft.post_harvest_observations.trim() || null,
      notes: harvestDraft.notes.trim() || null,
    };
    setHarvestBusy(true); setNotice(null);
    try {
      await api<FarmHarvest>(`/v1/farms/${encodeURIComponent(farmId)}/harvests${editingHarvestId ? `/${encodeURIComponent(editingHarvestId)}` : ''}`, {
        method: editingHarvestId ? 'PUT' : 'POST',
        body: JSON.stringify(payload),
      });
      if (selectedFarmId.current === farmId) {
        setNotice({ type: 'success', text: editingHarvestId ? 'Harvest record updated.' : 'Harvest record saved as farmer reported.' });
        setHarvestFormOpen(false); setEditingHarvestId('');
        setHarvestDraft({
          field_id: '', crop_plan_id: '', crop: SUPPORTED_CROPS[0], season: 'A',
          harvest_date: new Date().toISOString().slice(0, 10), harvested_area: '', area_unit: 'ha',
          quantity: '', quantity_unit: 'kg', loss_quantity: '', post_harvest_observations: '', notes: '',
        });
        await loadHarvests(farmId);
      }
    } catch (e) {
      setNotice({ type: 'error', text: e instanceof Error ? e.message : 'Harvest record could not be saved.' });
    } finally { setHarvestBusy(false); }
  }
  function editHarvest(row: FarmHarvest) {
    setEditingHarvestId(row.id);
    setHarvestDraft({
      field_id: row.field_id ?? '', crop_plan_id: row.crop_plan_id ?? '', crop: row.crop, season: row.season,
      harvest_date: row.harvest_date, harvested_area: String(row.harvested_area), area_unit: row.area_unit,
      quantity: String(row.quantity), quantity_unit: row.quantity_unit,
      loss_quantity: row.loss_quantity == null ? '' : String(row.loss_quantity),
      post_harvest_observations: row.post_harvest_observations ?? '', notes: row.notes ?? '',
    });
    setHarvestFormOpen(true);
    setNotice(null);
  }
  async function createActivity(event: FormEvent) {
    event.preventDefault(); if (!selected) return; setBusy(true); setNotice(null);
    const selectedFarm = farms.find((farm) => farm.id === selected);
    try { await api(`/v1/farms/${encodeURIComponent(selected)}/activities`, { method: 'POST', body: JSON.stringify({ ...activity, district: selectedFarm?.district, quantity: activity.quantity ? Number(activity.quantity) : null, unit: activity.quantity ? activity.unit : null }) }); setNotice({ type: 'success', text: 'Activity saved as farmer reported.' }); setActivityOpen(false); await loadActivities(selected); }
    catch (e) { setNotice({ type: 'error', text: e instanceof Error ? e.message : 'Activity could not be saved.' }); }
    finally { setBusy(false); }
  }
  async function findCropRecommendations(event: FormEvent) {
    event.preventDefault();
    const farm = farms.find((item) => item.id === selected);
    if (!farm) return;
    setRecommendationBusy(true); setRecommendationError(''); setRecommendation(null); setSelectedRecommendation(null); setCompareCrops([]);
    const request: CropRecommendationRequest = {
      district: farm.district, season: planDraft.season,
      elevation_m: planConditions.elevation_m ? Number(planConditions.elevation_m) : null,
      irrigation: planConditions.irrigation, water_availability: planConditions.water_availability,
    };
    try { setRecommendation(await api<CropRecommendationResponse>('/v1/crop-planning/recommendations', { method: 'POST', body: JSON.stringify(request) })); }
    catch (e) { setRecommendationError(e instanceof Error ? e.message : 'Crop recommendations could not be generated. Your saved plans were not changed.'); }
    finally { setRecommendationBusy(false); }
  }
  async function createField(event: FormEvent) {
    event.preventDefault(); if (!selected) return;
    setFieldBusy(true); setNotice(null);
    try {
      await api<FarmField>(`/v1/farms/${encodeURIComponent(selected)}/fields`, { method: 'POST', body: JSON.stringify({
        name: fieldDraft.name, area_ha: fieldDraft.area_ha ? Number(fieldDraft.area_ha) : null,
        latitude: fieldDraft.latitude ? Number(fieldDraft.latitude) : null,
        longitude: fieldDraft.longitude ? Number(fieldDraft.longitude) : null,
      }) });
      setFieldDraft({ name: '', area_ha: '', latitude: '', longitude: '' }); setFieldOpen(false);
      setNotice({ type: 'success', text: 'Field saved. Coordinates are farmer supplied; district boundaries are not verified.' });
      await loadFields(selected);
    } catch (e) { setNotice({ type: 'error', text: e instanceof Error ? e.message : 'Field could not be saved.' }); }
    finally { setFieldBusy(false); }
  }
  function useCurrentFieldLocation() {
    if (!navigator.geolocation) {
      setFieldLocationMessage('This browser does not support location detection. Enter coordinates manually.');
      return;
    }
    setFieldLocating(true); setFieldLocationMessage('');
    navigator.geolocation.getCurrentPosition((position) => {
      setFieldDraft((current) => ({
        ...current,
        latitude: position.coords.latitude.toFixed(6),
        longitude: position.coords.longitude.toFixed(6),
      }));
      setFieldLocationMessage(`Location detected (browser-reported accuracy about ${Math.round(position.coords.accuracy)} m). Check it before saving; this does not verify the farm or district boundary.`);
      setFieldLocating(false);
    }, (error) => {
      const message = error.code === error.PERMISSION_DENIED
        ? 'Location permission was denied. You can enter coordinates manually.'
        : error.code === error.TIMEOUT
          ? 'Location detection took too long. Try again or enter coordinates manually.'
          : 'The device location is unavailable. Check location settings or enter coordinates manually.';
      setFieldLocationMessage(message); setFieldLocating(false);
    }, { enableHighAccuracy: true, timeout: 15000, maximumAge: 30000 });
  }
  async function archiveField(field: FarmField) {
    if (!selected) return;
    if (!window.confirm(`Archive ${field.name}? It will no longer be available for new plans, but existing crop plans will keep their history.`)) return;
    try {
      await api<FarmField>(`/v1/farms/${encodeURIComponent(selected)}/fields/${encodeURIComponent(field.id)}/archive`, { method: 'POST' });
      setNotice({ type: 'success', text: `${field.name} archived. Existing crop plans remain linked for history.` });
      await loadFields(selected);
    } catch (e) { setNotice({ type: 'error', text: e instanceof Error ? e.message : 'Field could not be archived.' }); }
  }
  async function savePlan(event: FormEvent) {
    event.preventDefault(); if (!selected) return;
    const farmId = selected; const selectedFarm = farms.find((farm) => farm.id === farmId);
    if (!selectedFarm) return;
    setPlanBusy(true); setPlanNotice(null);
    const payload: CropPlanCreate = {
      district: selectedFarm.district, crop: planDraft.crop, season: planDraft.season,
      planting_date: planDraft.planting_date, area_ha: Number(planDraft.area_ha),
      field_id: planDraft.field_id || null,
      plan: {
        farmer_notes: planDraft.notes.trim(),
        ...(selectedRecommendation && recommendation ? { recommendation_snapshot: {
          crop: selectedRecommendation.crop, status: selectedRecommendation.status,
          reasons: selectedRecommendation.reasons, risks: selectedRecommendation.risks,
          evidence: selectedRecommendation.evidence, evidence_basis: selectedRecommendation.evidence_basis,
          guidance_source: selectedRecommendation.source, planting_window: selectedRecommendation.window,
          history: selectedRecommendation.history, generated_at: recommendation.context.generated_at,
          conditions: recommendation.context, ranking_method: recommendation.context.ranking_method,
          snapshot_status: 'Farmer plan context; not an independently verified evidence record.',
        } } : editingPlanId ? (() => {
          const previous = plans.find((plan) => plan.id === editingPlanId);
          const snapshot = previous?.plan.recommendation_snapshot;
          return previous?.crop === planDraft.crop && previous.season === planDraft.season && snapshot && typeof snapshot === 'object'
            ? { recommendation_snapshot: snapshot } : {};
        })() : {}),
      },
    };
    try {
      const editing = editingPlanId;
      await api<CropPlan>(`/v1/farms/${encodeURIComponent(farmId)}/plans${editing ? `/${encodeURIComponent(editing)}` : ''}`, { method: editing ? 'PUT' : 'POST', body: JSON.stringify(payload) });
      if (selectedFarmId.current === farmId) {
        setPlanNotice({ type: 'success', text: editing ? 'Crop plan changes saved.' : 'Crop plan saved. Its guidance remains provisional.' });
        setPlanFormOpen(false); setEditingPlanId(''); setPlanDraft((current) => ({ ...current, notes: '' })); setSelectedRecommendation(null);
        await loadPlans(farmId);
      }
    } catch (e) { setPlanNotice({ type: 'error', text: e instanceof Error ? e.message : 'Crop plan could not be saved.' }); }
    finally { setPlanBusy(false); }
  }
  function editPlan(plan: CropPlan) {
    if (plan.status !== 'draft' && plan.status !== 'planned') return;
    setEditingPlanId(plan.id);
    setPlanDraft({ crop: plan.crop, season: plan.season, planting_date: plan.planting_date,
      area_ha: String(plan.area_ha), field_id: plan.field_id ?? '',
      notes: typeof plan.plan.farmer_notes === 'string' ? plan.plan.farmer_notes : '' });
    setSelectedRecommendation(null);
    setPlanNotice(null);
    setPlanFormOpen(true);
  }
  function downloadPlanBrief(plan: CropPlan) {
    const farm = farms.find((item) => item.id === selected);
    if (!farm || plan.farm_id !== farm.id) {
      setPlanNotice({ type: 'error', text: 'This saved plan is not available for the selected farm.' });
      return;
    }
    try {
      const field = plan.field_id ? fields.find((item) => item.id === plan.field_id && item.farm_id === farm.id) : undefined;
      downloadSavedCropPlanBrief(plan, farm, field);
      setPlanNotice(null);
    } catch {
      setPlanNotice({ type: 'error', text: 'The crop plan brief could not be prepared for download. Try again.' });
    }
  }
  async function changePlanStatus(plan: CropPlan, status: CropPlanStatus) {
    const farmId = selected; if (!farmId || busyPlanId) return;
    if (status === 'cancelled' && !window.confirm(`Cancel this ${plan.status} plan for ${plan.crop}, season ${plan.season}? Cancelled plans cannot be reopened.`)) return;
    const body: CropPlanStatusUpdate = { status: status as CropPlanStatusUpdate['status'] };
    if (status === 'planted') {
      const actualDate = actualDates[plan.id] ?? '';
      if (!actualDate) { setPlanNotice({ type: 'error', text: 'Enter the actual planting date before marking this plan planted.' }); return; }
      if (actualDate > new Date().toISOString().slice(0, 10)) { setPlanNotice({ type: 'error', text: 'Actual planting date cannot be in the future.' }); return; }
      body.actual_planting_date = actualDate;
    }
    setBusyPlanId(plan.id); setPlanNotice(null);
    try {
      await api<CropPlan>(`/v1/farms/${encodeURIComponent(farmId)}/plans/${encodeURIComponent(plan.id)}/status`, { method: 'PATCH', body: JSON.stringify(body) });
      setPlanNotice({ type: 'success', text: `Crop plan updated to ${status}.` });
      if (selectedFarmId.current === farmId) {
        if (status === 'planted') await loadActivities(farmId);
        await loadPlans(farmId);
      }
    } catch (e) { setPlanNotice({ type: 'error', text: e instanceof Error ? e.message : 'Crop plan status could not be updated.' }); }
    finally { setBusyPlanId(''); }
  }
  const linkedHarvestPlan = plans.find((plan) => plan.id === harvestDraft.crop_plan_id);
  return <>
    <PageHeader eyebrow="FARMER WORKSPACE" title="Farm records" description="Manage your farm profiles and durable activity history. Submitted facts remain farmer reported until a review decision is recorded." action={<button className="button button-primary" onClick={() => setFormOpen((open) => !open)}><Leaf size={16} /> Add a farm</button>} />
    <Alert notice={notice} />{error && <ErrorState text={error} retry={() => void loadFarms()} />}
    {formOpen && <FarmProfileForm
      name={farmName}
      district={district}
      area={area}
      districts={DISTRICTS}
      busy={busy}
      onNameChange={setFarmName}
      onDistrictChange={setDistrict}
      onAreaChange={setArea}
      onSubmit={(event) => void createFarm(event)}
      onClose={() => setFormOpen(false)}
    />}
    {loading ? <LoadingState /> : farms.length === 0 ? <div className="panel"><EmptyState title="No farms saved yet" description="Create a farm profile to start keeping persistent records." /></div> : <>
       <div className="farm-switcher"><label htmlFor="farm-select">Active farm</label><select id="farm-select" value={selected} onChange={(e) => { setSelected(e.target.value); setFields([]); setActivities([]); }}>{farms.map((farm) => <option value={farm.id} key={farm.id}>{farm.name} · {farm.district}</option>)}</select><span>{farms.find((farm) => farm.id === selected)?.area_ha ? `${farms.find((farm) => farm.id === selected)?.area_ha} ha` : 'Area not recorded'}</span></div>
      {selected && <FieldDecisionSummary key={`summary-${selected}`} farmId={selected} fields={fields} fieldsLoading={fieldsLoading} />}
      {selected && <FarmTimeline key={selected} farmId={selected} />}
      <section className="panel records-panel"><div className="panel-heading"><div><h2>Fields</h2><p>Optional fields under this farm. Area uses hectares. Coordinates are farmer supplied; the Rwanda bounding extent is only a coarse check, not district-boundary validation.</p></div><button className="button button-secondary" onClick={() => setFieldOpen((open) => !open)}>Add a field</button></div>
         {fieldError && <ErrorState text={`Field service unavailable: ${fieldError}`} retry={() => void loadFields(selected)} />}
        {fieldOpen && <form className="activity-form" onSubmit={(e) => void createField(e)}><label>Field name<input value={fieldDraft.name} onChange={(e) => setFieldDraft({ ...fieldDraft, name: e.target.value })} required maxLength={120} /></label><label>Area (hectares, optional)<input type="number" min="0.01" step="0.01" value={fieldDraft.area_ha} onChange={(e) => setFieldDraft({ ...fieldDraft, area_ha: e.target.value })} /></label><div className="field-location-tools"><button className="button button-secondary" type="button" onClick={useCurrentFieldLocation} disabled={fieldLocating}><LocateFixed size={15} />{fieldLocating ? 'Detecting location…' : 'Use my current location'}</button><small>Requires location permission and usually HTTPS or localhost. Coordinates are saved only when you select Save field; browser location may be approximate.</small>{fieldLocationMessage && <small role="status">{fieldLocationMessage}</small>}</div><label>Latitude (optional)<input type="number" min="-90" max="90" step="any" value={fieldDraft.latitude} onChange={(e) => { setFieldDraft({ ...fieldDraft, latitude: e.target.value }); setFieldLocationMessage(''); }} /></label><label>Longitude (optional)<input type="number" min="-180" max="180" step="any" value={fieldDraft.longitude} onChange={(e) => { setFieldDraft({ ...fieldDraft, longitude: e.target.value }); setFieldLocationMessage(''); }} /></label><div className="form-end"><button className="button button-primary" disabled={fieldBusy}>{fieldBusy ? 'Saving…' : 'Save field'}</button></div></form>}
         {fieldsLoading ? <LoadingState label="Loading fields…" /> : !fieldError && fields.length === 0 ? <EmptyState title="No fields recorded" description="Create a field or continue using farm-level crop plans." /> : !fieldsLoading && fields.length > 0 && <div className="review-list">{fields.map((field) => <article className="review-card" key={field.id}><div className="review-card-head"><div><h3>{field.name}</h3><p>{field.area_ha == null ? 'Area not recorded' : `${field.area_ha} ha`} · {field.latitude == null ? 'Coordinates unavailable' : `Farmer supplied: ${field.latitude.toFixed(5)}, ${field.longitude?.toFixed(5)}`}</p></div><button className="button button-secondary" onClick={() => void archiveField(field)}>Archive</button></div></article>)}</div>}
      </section>
      <section className="panel records-panel" aria-labelledby="activity-history-title"><div className="panel-heading"><div><h2 id="activity-history-title">Activity history</h2><p>Records saved to your account, newest event first.</p></div><button className="button button-secondary" onClick={() => setActivityOpen((open) => !open)}><Activity size={15} /> Record activity</button></div>
        {activityOpen && <form className="activity-form" onSubmit={(e) => void createActivity(e)}><label>Crop<input value={activity.crop} onChange={(e) => setActivity({ ...activity, crop: e.target.value })} required maxLength={80} /></label><label>Season<select value={activity.season} onChange={(e) => setActivity({ ...activity, season: e.target.value })}><option>A</option><option>B</option><option>C</option></select></label><label>Activity<input value={activity.activity_type} onChange={(e) => setActivity({ ...activity, activity_type: e.target.value })} required maxLength={60} /></label><label>Event date<input type="date" value={activity.event_date} onChange={(e) => setActivity({ ...activity, event_date: e.target.value })} required /></label><label>Quantity (optional)<input type="number" min="0" step="any" value={activity.quantity} onChange={(e) => setActivity({ ...activity, quantity: e.target.value })} /></label><label>Unit<input value={activity.unit} onChange={(e) => setActivity({ ...activity, unit: e.target.value })} maxLength={30} /></label><label className="wide-field">Notes<textarea value={activity.notes} onChange={(e) => setActivity({ ...activity, notes: e.target.value })} maxLength={2000} rows={2} /></label><div className="form-end"><button className="button button-primary" disabled={busy}>{busy ? 'Saving…' : 'Save report'}</button></div></form>}
         {activitiesError && <ErrorState text={activitiesError} retry={() => void loadActivities(selected)} />}
         {activitiesLoading ? <LoadingState label="Loading activity history…" /> : !activitiesError && activities.length === 0 ? <EmptyState title="No activities for this farm" description="Record planting, harvest, or another farm activity." /> : !activitiesLoading && activities.length > 0 && <div className="table-scroll"><table><thead><tr><th>Activity</th><th>Crop & season</th><th>Event date</th><th>Quantity</th><th>Review status</th><th>Data source</th></tr></thead><tbody>{activities.map((row) => <tr key={row.id}><td><strong>{row.activity_type}</strong><small>{row.notes || '—'}</small></td><td>{row.crop}<small>Season {row.season}</small></td><td>{row.event_date}</td><td>{row.quantity ?? '—'} {row.unit ?? ''}</td><td><StatusPill tone={row.review_status === 'approved_as_reviewed' ? 'green' : row.review_status === 'rejected' ? 'red' : 'amber'}>{row.review_status.replaceAll('_', ' ')}</StatusPill></td><td><span className="verification-label">{row.verification.replaceAll('_', ' ')}</span></td></tr>)}</tbody></table></div>}
      </section>
      {selected && <IrrigationLog key={selected} farmId={selected} fields={fields} plans={plans} />}
      <section className="panel records-panel" aria-labelledby="harvest-records-title">
        <div className="panel-heading"><div><h2 id="harvest-records-title">Harvest records</h2><p>Record observed harvest outcomes. These farmer-reported values are separate from official statistics and do not establish that a crop plan caused the result.</p></div><button className="button button-secondary" onClick={() => { setEditingHarvestId(''); setHarvestFormOpen((open) => !open); setNotice(null); }}><Leaf size={15} /> Record harvest</button></div>
        {harvestFormOpen && <form className="activity-form" onSubmit={(event) => void saveHarvest(event)}>
          <label>Crop plan (optional)<select value={harvestDraft.crop_plan_id} onChange={(event) => {
            const plan = plans.find((item) => item.id === event.target.value);
            setHarvestDraft((current) => ({ ...current, crop_plan_id: event.target.value, ...(plan ? { crop: plan.crop, season: plan.season, field_id: plan.field_id ?? '' } : { field_id: '' }) }));
          }}><option value="">Not linked to a crop plan</option>{plans.map((plan) => <option key={plan.id} value={plan.id}>{plan.crop} · Season {plan.season} · {plan.status}</option>)}</select><small>Linking a plan does not change its status.</small></label>
          <label>Crop<select value={harvestDraft.crop} disabled={Boolean(linkedHarvestPlan)} onChange={(event) => setHarvestDraft({ ...harvestDraft, crop: event.target.value })}>{SUPPORTED_CROPS.map((crop) => <option key={crop}>{crop}</option>)}</select></label>
          <label>Season<select value={harvestDraft.season} disabled={Boolean(linkedHarvestPlan)} onChange={(event) => setHarvestDraft({ ...harvestDraft, season: event.target.value as 'A' | 'B' | 'C' })}><option>A</option><option>B</option><option>C</option></select></label>
          <label>Field (optional)<select value={harvestDraft.field_id} disabled={Boolean(linkedHarvestPlan?.field_id)} onChange={(event) => setHarvestDraft({ ...harvestDraft, field_id: event.target.value })}><option value="">Farm-level harvest</option>{harvestDraft.field_id && !fields.some((field) => field.id === harvestDraft.field_id) && <option value={harvestDraft.field_id}>Previously linked field</option>}{fields.map((field) => <option key={field.id} value={field.id}>{field.name}</option>)}</select></label>
          <label>Harvest date<input type="date" value={harvestDraft.harvest_date} max={new Date().toISOString().slice(0, 10)} onChange={(event) => setHarvestDraft({ ...harvestDraft, harvest_date: event.target.value })} required /></label>
          <label>Harvested area<input type="number" min="0.000001" step="any" value={harvestDraft.harvested_area} onChange={(event) => setHarvestDraft({ ...harvestDraft, harvested_area: event.target.value })} required /></label>
          <label>Area unit<select value={harvestDraft.area_unit} onChange={(event) => setHarvestDraft({ ...harvestDraft, area_unit: event.target.value as FarmHarvestInput['area_unit'] })}><option value="ha">Hectares (ha)</option><option value="m2">Square metres (m²)</option><option value="acre">Acres</option></select></label>
          <label>Harvest quantity<input type="number" min="0.000001" step="any" value={harvestDraft.quantity} onChange={(event) => setHarvestDraft({ ...harvestDraft, quantity: event.target.value })} required /></label>
          <label>Quantity unit<select value={harvestDraft.quantity_unit} onChange={(event) => setHarvestDraft({ ...harvestDraft, quantity_unit: event.target.value as FarmHarvestInput['quantity_unit'] })}><option value="kg">Kilograms (kg)</option><option value="g">Grams (g)</option><option value="t">Tonnes (t)</option><option value="lb">Pounds (lb)</option></select></label>
          <label>Losses (optional, same unit)<input type="number" min="0" step="any" value={harvestDraft.loss_quantity} onChange={(event) => setHarvestDraft({ ...harvestDraft, loss_quantity: event.target.value })} /></label>
          <label className="wide-field">Post-harvest observations (optional)<textarea value={harvestDraft.post_harvest_observations} onChange={(event) => setHarvestDraft({ ...harvestDraft, post_harvest_observations: event.target.value })} maxLength={2000} rows={2} /></label>
          <label className="wide-field">Notes (optional)<textarea value={harvestDraft.notes} onChange={(event) => setHarvestDraft({ ...harvestDraft, notes: event.target.value })} maxLength={2000} rows={2} /></label>
          <div className="form-end"><button className="button button-secondary" type="button" onClick={() => { setHarvestFormOpen(false); setEditingHarvestId(''); }}>Cancel</button><button className="button button-primary" disabled={harvestBusy}>{harvestBusy ? 'Saving…' : editingHarvestId ? 'Update harvest' : 'Save harvest'}</button></div>
        </form>}
        {harvestsError && <ErrorState text={harvestsError} retry={() => void loadHarvests(selected)} />}
        {harvestsLoading ? <LoadingState label="Loading harvest records…" /> : !harvestsError && harvests.length === 0 ? <EmptyState title="No harvest records yet" description="When you have an observed harvest, record its date, area, quantity and units here." /> : !harvestsLoading && harvests.length > 0 && <><div className="table-scroll"><table><thead><tr><th>Harvest date</th><th>Crop & season</th><th>Area</th><th>Quantity / losses</th><th>Calculated outcome</th><th>Plan</th><th>Record</th></tr></thead><tbody>{harvests.map((row) => <tr key={row.id}><td>{row.harvest_date}</td><td>{row.crop}<small>Season {row.season}</small></td><td>{row.harvested_area} {row.area_unit}</td><td>{row.quantity} {row.quantity_unit}{row.loss_quantity == null ? '' : ` · losses ${row.loss_quantity} ${row.quantity_unit}`}</td><td>{row.yield_kg_ha == null ? 'Not calculated' : <><strong>{row.yield_kg_ha.toLocaleString()} kg/ha</strong><small>{row.yield_calculation}</small></>}<small>Farmer reported; not an official statistic or yield forecast.</small></td><td>{row.crop_plan_id ? plans.find((plan) => plan.id === row.crop_plan_id)?.status ?? 'Linked plan' : 'Not linked'}</td><td><button className="text-button" onClick={() => editHarvest(row)}>Edit</button><small>Updated {new Date(row.updated_at).toLocaleDateString()}</small></td></tr>)}</tbody></table></div>{harvests.map((row) => <HarvestObservations key={row.id} farmId={selected} harvest={row} />)}</>}
      </section>
      <SoilRecords farmId={selected} fields={fields} />
      <section className="panel records-panel" aria-labelledby="crop-plans-title">
        <div className="panel-heading"><div><h2 id="crop-plans-title">Crop plans</h2><p>Saved records for {farms.find((farm) => farm.id === selected)?.name}. Guidance is provisional and farmer-entered notes are not verified.</p></div><button className="button button-secondary" onClick={() => { setPlanNotice(null); setPlanFormOpen((open) => !open); }}><Sprout size={15} /> Create crop plan</button></div>
        <div className="recommendation-workflow">
          <h3>Explore crops for this farm</h3>
          <p>Recommendations reuse CropPulse's existing rule-based engine. District statistics describe past observations; they do not prove farm suitability or predict your harvest.</p>
          {!selected && <EmptyState title="Select a farm first" description="The farm district is used as the planning location." />}
          {selected && <form className="activity-form" onSubmit={(event) => void findCropRecommendations(event)}>
            <label>Season<select value={planDraft.season} onChange={(e) => setPlanDraft({ ...planDraft, season: e.target.value as 'A' | 'B' | 'C' })}><option>A</option><option>B</option><option>C</option></select></label>
            <label>Elevation in metres (optional)<input type="number" min="800" max="4600" step="1" value={planConditions.elevation_m} onChange={(e) => setPlanConditions({ ...planConditions, elevation_m: e.target.value })} placeholder="Unknown" /><small>Enter only if you have a reasonable estimate.</small></label>
            <label>Irrigation access<select value={planConditions.irrigation} onChange={(e) => setPlanConditions({ ...planConditions, irrigation: e.target.value as CropRecommendationRequest['irrigation'] })}><option>Unknown</option><option>Yes</option><option>No</option></select></label>
            <label>Water availability<select value={planConditions.water_availability} onChange={(e) => setPlanConditions({ ...planConditions, water_availability: e.target.value as CropRecommendationRequest['water_availability'] })}><option>Unknown</option><option>Low</option><option>Medium</option><option>High</option></select></label>
            <div className="form-end"><button className="button button-primary" disabled={recommendationBusy}>{recommendationBusy ? 'Checking available evidence…' : 'Compare crop options'}</button></div>
          </form>}
          {recommendationError && <ErrorState text={recommendationError} />}
          {recommendation && <>
            <div className="notice notice-info" role="status"><span><strong>CropPulse data checks: {recommendation.context.statistics_status}</strong> · {recommendation.context.statistics_note}<br />Generated {new Date(recommendation.context.generated_at).toLocaleString()}. {recommendation.context.ranking_method}</span></div>
            {recommendation.context.statistics_provenance.map((source, index) => <div key={`${source.sha256 ?? source.title ?? 'source'}-${index}`} className="source-line">
              <p><strong>{source.title ?? 'Dataset source'}</strong> · {source.publisher ?? 'Publisher unavailable'}{source.reference_period ? ` · Reference period: ${source.reference_period}` : ''}{source.retrieved_at ? ` · Retrieved: ${source.retrieved_at}` : ''}{source.units ? ` · Units: ${source.units}` : ''}{source.source_url ? <> · <a href={source.source_url} target="_blank" rel="noreferrer">Source details</a></> : null}</p>
              {source.limitations && <details><summary>Dataset scope and limitations</summary><p>{source.limitations}</p></details>}
            </div>)}
            <p className="evidence-boundary-note">CropPulse’s checksum and structural checks assess file integrity and format. They do not independently verify NISR survey estimates, establish farm-level suitability, or predict a future harvest.</p>
            {recommendation.errors.length > 0 && <ErrorState text={recommendation.errors.join(' ')} />}
            {recommendation.results.filter((item) => item.rank).length === 0 && <EmptyState title="No crops remain in the current guide checks" description={recommendation.no_window.length ? `The provisional guide has no month entry for these crops in Season ${planDraft.season}: ${recommendation.no_window.join(', ')}. No entry does not establish that a crop cannot be grown locally.` : 'The provisional CropPulse rules have no candidates for these inputs. Confirm locally; this is not proof that other crops are unsuitable.'} />}
            <div className="review-list">{recommendation.results.filter((item) => item.rank).map((item) => <article className="review-card recommendation-card" key={item.crop}>
              <div className="review-card-head"><div><div className="review-title-row"><h4>#{item.rank} {item.crop} · {item.rw}</h4><StatusPill tone="amber">{item.status}</StatusPill></div><p>{item.evidence_basis}</p><label className="compare-option"><input type="checkbox" checked={compareCrops.includes(item.crop)} disabled={!compareCrops.includes(item.crop) && compareCrops.length >= 3} onChange={(event) => setCompareCrops((current) => event.target.checked ? [...current, item.crop] : current.filter((crop) => crop !== item.crop))} /> Compare this crop</label></div><button type="button" className="button button-secondary" onClick={() => { setSelectedRecommendation(item); setPlanDraft((draft) => ({ ...draft, crop: item.crop, season: recommendation.context.season })); setPlanFormOpen(true); }}>Review for my plan</button></div>
              <p><strong>Indicative planting window:</strong> {item.window}</p>
              <div className="recommendation-details"><div><strong>Why it appears</strong><ul>{item.reasons.map((reason, index) => <li key={index}>{reason}</li>)}</ul></div><div><strong>Risks and unknowns</strong>{item.risks.length ? <ul>{item.risks.map((risk, index) => <li key={index}>{risk}</li>)}</ul> : <p>None identified by the current rules; this does not establish farm suitability.</p>}</div></div>
              {recommendation.context.statistics_status === 'validated' && item.history.n_periods > 0 && <p>Historical district data: {item.history.n_periods} period(s), {item.history.years[0]}–{item.history.years[item.history.years.length - 1]}; latest calculated yield {item.history.yields[item.history.yields.length - 1]?.toFixed(2)} tonnes per hectare. These are historical area/production calculations, not forecasts.</p>}
              <details><summary>Practical next checks</summary><ul>{item.next_steps.map((step, index) => <li key={index}>{step}</li>)}</ul></details>
              <details><summary>Evidence and limitations</summary><ul>{item.evidence.map((claim, index) => <li key={index}>{claim}</li>)}</ul><p>{item.source}</p>{item.evidence_record?.approved_guidance.length ? item.evidence_record.approved_guidance.map((rule) => <section key={`${rule.rule_id}-${rule.version}`}><strong>Approved for its defined scope: {rule.category.replaceAll('_', ' ')}</strong><p>{rule.recommendation}</p><small>Applies to {rule.geography.type}: {rule.geography.scope.join(', ') || 'Rwanda-wide'} · Season(s) {rule.season_scope.join(', ')} · review by {rule.revalidate_by}</small>{rule.source_references.map((ref, index) => <p key={`${ref.title}-${index}`} className="source-line">{ref.organization}: {ref.title} · {ref.locator} · {ref.paraphrase} {ref.url && <a href={ref.url} target="_blank" rel="noreferrer">Open source</a>}</p>)}{rule.limitations.map((limitation) => <small key={limitation}>{limitation}</small>)}</section>) : <p>No approved, source-backed agronomic rule is currently loaded for this crop, district, and season. The comparison is based on provisional CropPulse rules; it is not a verified suitability recommendation. NISR statistics provide historical context only and do not validate these rules.</p>}<p>Listed zone fit, months, altitude, and water categories are provisional. No soil analysis, plot-level weather rule, market or profitability assessment is included.</p></details>
            </article>)}</div>
            {compareCrops.length > 0 && <section className="crop-compare" aria-label="Crop option comparison"><h4>Compare options ({compareCrops.length}/3)</h4><p>Crop fit comes from the provisional CropPulse guide; NISR observations are displayed as historical context and do not affect rank or suitability.</p><div className="crop-compare-grid">{recommendation.results.filter((item) => compareCrops.includes(item.crop)).map((item) => <article key={item.crop}><h5>{item.crop}</h5><dl><div><dt>Provisional guide category</dt><dd>{item.status}</dd></div><div><dt>Indicative season window (unverified)</dt><dd>{item.window}</dd></div><div><dt>Relative water category (unverified)</dt><dd>{item.water_need} (CropPulse guide)</dd></div><div><dt>Indicative altitude range (unverified)</dt><dd>{item.altitude_m_range[0]}–{item.altitude_m_range[1]} m</dd></div><div><dt>Historical data (context only)</dt><dd>{recommendation.context.statistics_status === 'validated' ? `${item.history.n_periods} period(s)${item.history.n_periods ? ` · latest ${item.history.yields[item.history.yields.length - 1]?.toFixed(2)} t/ha` : ''}` : 'Not displayed as validated historical context'}</dd></div><div><dt>Main risks and unknowns</dt><dd>{item.risks.length ? item.risks.join(' ') : 'No additional risk identified by the provisional rules.'}</dd></div></dl></article>)}</div></section>}
            {recommendation.no_window.length > 0 && <details><summary>Crops with no month entry in the provisional guide</summary><p>{recommendation.no_window.join(', ')}</p><small>No entry does not establish that a crop is unsuitable locally. The listed months elsewhere come from the unverified CropPulse guidance pack.</small></details>}
            <details><summary>What this comparison cannot assess</summary><ul>{recommendation.cannot_assess.map((item) => <li key={item}>{item}</li>)}</ul></details>
          </>}
        </div>
        <Alert notice={planNotice} />
        {planFormOpen && <form className="activity-form" onSubmit={(e) => void savePlan(e)}>
          <h3 className="wide-field">{editingPlanId ? 'Edit saved crop plan' : 'Review crop plan'}</h3>
          <label>District<select value={farms.find((farm) => farm.id === selected)?.district ?? ''} disabled aria-label="Farm district">{DISTRICTS.map((item) => <option key={item}>{item}</option>)}</select><small>From this farm profile</small></label>
          <label>Crop<select value={planDraft.crop} onChange={(e) => { const crop = e.target.value; setPlanDraft({ ...planDraft, crop }); if (selectedRecommendation?.crop !== crop) setSelectedRecommendation(null); }}>{SUPPORTED_CROPS.map((crop) => <option key={crop}>{crop}</option>)}</select></label>
          <label>Season<select value={planDraft.season} onChange={(e) => { const season = e.target.value as 'A' | 'B' | 'C'; setPlanDraft({ ...planDraft, season }); if (recommendation?.context.season !== season) setSelectedRecommendation(null); }}><option>A</option><option>B</option><option>C</option></select></label>
          <label>Proposed planting date<input type="date" value={planDraft.planting_date} onChange={(e) => setPlanDraft({ ...planDraft, planting_date: e.target.value })} required /><small>A date you propose; not a scientifically verified planting date.</small></label>
          <label>Planned area (hectares)<input type="number" min="0.01" max="100000" step="0.01" value={planDraft.area_ha} onChange={(e) => setPlanDraft({ ...planDraft, area_ha: e.target.value })} required /></label>
          <label>Field (optional)<select value={planDraft.field_id} onChange={(e) => setPlanDraft({ ...planDraft, field_id: e.target.value })}><option value="">Farm-level plan</option>{fields.map((field) => <option key={field.id} value={field.id}>{field.name}{field.area_ha == null ? '' : ` · ${field.area_ha} ha`}</option>)}</select><small>Only active fields in this farm are available.</small></label>
          <label className="wide-field">Planning notes (not verified)<textarea value={planDraft.notes} onChange={(e) => setPlanDraft({ ...planDraft, notes: e.target.value })} maxLength={2000} rows={2} placeholder="Optional notes you want to keep with this plan" /></label>
          {selectedRecommendation && <div className="wide-field notice notice-info" role="status">Selected {selectedRecommendation.crop}. Its provisional reasons, risks, source note, and generation context will be stored with this plan for later review.</div>}
          <div className="form-end"><button type="button" className="button button-secondary" onClick={() => { setPlanFormOpen(false); setEditingPlanId(''); }}>{'Cancel'}</button><button className="button button-primary" disabled={planBusy || !selected}>{planBusy ? 'Saving…' : editingPlanId ? 'Save changes' : 'Save crop plan'}</button></div>
        </form>}
        {!selected && <EmptyState title="Select a farm first" description="Crop plans are stored under a specific farm." />}
        {selected && plansLoading && <LoadingState label="Loading crop plans…" />}
        {selected && plansError && <ErrorState text={plansError} retry={() => void loadPlans(selected)} />}
        {selected && !plansLoading && !plansError && plansFarmId === selected && plans.length === 0 && <EmptyState title="No crop plans for this farm" description="Create a crop plan to keep its intended dates and progress together." />}
        {selected && !plansLoading && !plansError && plansFarmId === selected && plans.length > 0 && <div className="review-list">{plans.map((plan) => <article className="review-card" key={plan.id}>
          <div className="review-card-head"><div><div className="review-title-row"><h3>{plan.crop} · Season {plan.season}</h3><StatusPill tone={plan.status === 'completed' ? 'green' : plan.status === 'cancelled' ? 'red' : 'amber'}>{plan.status}</StatusPill></div><p>{plan.district} · {plan.area_ha} ha · Verification: {plan.verification.replaceAll('_', ' ')}</p></div><div className="decision-buttons"><button type="button" className="button button-secondary" onClick={() => downloadPlanBrief(plan)}>Download plan brief</button>{(plan.status === 'draft' || plan.status === 'planned') && <button className="button button-secondary" onClick={() => editPlan(plan)}>Edit plan</button>}</div></div>
          <dl className="report-facts"><div><dt>Intended planting date</dt><dd>{plan.planting_date}</dd></div><div><dt>Actual planting date</dt><dd>{plan.actual_planting_date ?? 'Not recorded'}</dd></div><div className="fact-notes"><dt>Farmer planning notes · not verified</dt><dd>{typeof plan.plan.farmer_notes === 'string' && plan.plan.farmer_notes ? plan.plan.farmer_notes : 'No notes provided'}</dd></div></dl>
          <div className="fact-notes"><strong>Plan progress timeline</strong><ol><li>Proposed planting target: {plan.planting_date}</li><li>Actual planting: {plan.actual_planting_date ?? 'Not recorded'}</li><li>Recorded stage: {plan.status.replaceAll('_', ' ')}</li></ol><small>Dates and progress reflect your saved plan and reports. CropPulse does not calculate crop-stage dates from these records.</small></div>
          {typeof plan.plan.recommendation_snapshot === 'object' && plan.plan.recommendation_snapshot !== null && <details className="saved-recommendation"><summary>Saved recommendation context</summary><pre>{JSON.stringify(plan.plan.recommendation_snapshot, null, 2)}</pre></details>}
          <div className="fact-notes"><strong>Evidence and provenance</strong>{plan.evidence?.length ? plan.evidence.map((item) => <p key={item.id}>{item.claim} <span className="verification-label">Source: {item.source_name}{item.source_organization ? ` · ${item.source_organization}` : ''} · {item.verification_status.replaceAll('_', ' ')}</span>{item.confidence && <small>Confidence: {item.confidence}. </small>}{item.limitations && <small>Limitations: {item.limitations}</small>}</p>) : <p>No independently verified evidence records are attached. Any recommendation context is provisional and shown separately below.</p>}</div>
          {(NEXT_PLAN_STATUSES[plan.status]?.length ?? 0) > 0 && <div className="decision-buttons" aria-label={`Actions for ${plan.crop} season ${plan.season}`}>
            {plan.status === 'planned' && <label>Actual planting date<input aria-label={`Actual planting date for ${plan.crop}`} type="date" max={new Date().toISOString().slice(0, 10)} value={actualDates[plan.id] ?? ''} onChange={(e) => setActualDates({ ...actualDates, [plan.id]: e.target.value })} /></label>}
            {NEXT_PLAN_STATUSES[plan.status]?.map((next) => <button key={next} className={`button ${next === 'cancelled' ? 'button-danger' : 'button-secondary'}`} disabled={busyPlanId === plan.id || Boolean(busyPlanId)} onClick={() => void changePlanStatus(plan, next)}>{busyPlanId === plan.id ? 'Saving…' : `Mark ${next}`}</button>)}
          </div>}
        </article>)}</div>}
      </section>
    </>}
  </>;
}

export function ReviewPage() {
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('pending');
  const [districtFilter, setDistrictFilter] = useState('');
  const [cropFilter, setCropFilter] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [confirm, setConfirm] = useState<{ item: ReviewItem; decision: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);
  const load = useCallback(async () => { try { const rows = await api<ReviewItem[]>(`/v1/reviewer/activities?limit=100&offset=${page * 100}`); setItems(rows); setError(''); } catch (e) { setError(e instanceof Error ? e.message : 'Review records are unavailable.'); } finally { setLoading(false); } }, [page]);
  useEffect(() => { void load(); }, [load]);
  const filtered = useMemo(() => items.filter((item) =>
    (filter === 'all' || item.review_status === 'pending' || item.review_status === 'correction_requested')
    && (!districtFilter || item.district === districtFilter)
    && (!cropFilter || item.crop === cropFilter)
    && (!dateFrom || item.event_date >= dateFrom)
    && (!dateTo || item.event_date <= dateTo)), [items, filter, districtFilter, cropFilter, dateFrom, dateTo]);
  async function decide() {
    if (!confirm) return; setBusy(true); setNotice(null);
    try { await api(`/v1/reviewer/activities/${encodeURIComponent(confirm.item.id)}/decisions`, { method: 'POST', body: JSON.stringify({ decision: confirm.decision, reason: reasons[confirm.item.id] ?? '' }) }); setNotice({ type: 'success', text: 'Review decision recorded. The submitted facts were preserved.' }); setConfirm(null); await load(); }
    catch (e) { setNotice({ type: 'error', text: e instanceof Error ? e.message : 'Decision could not be saved.' }); }
    finally { setBusy(false); }
  }
  const decisionLabel: Record<string, string> = { approved_as_reviewed: 'Mark reviewed', rejected: 'Reject report', correction_requested: 'Request correction' };
  return <>
    <PageHeader eyebrow="AGRICULTURAL DATA" title="Review queue" description="Inspect farmer-reported activity submissions within your assigned district scope. Decisions are retained separately from original reports." action={<button className="button button-secondary" onClick={() => void load()}><RefreshCw size={15} /> Refresh</button>} />
    <Alert notice={notice} />{error && <ErrorState text={error} retry={() => void load()} />}
    <section className="panel"><div className="panel-heading"><div><h2>Submitted farm activities</h2><p>“Mark reviewed” records a reviewer decision; it does not mean independently verified.</p></div></div><div className="review-filters"><label>Review status<select value={filter} onChange={(e) => setFilter(e.target.value)}><option value="pending">Needs review</option><option value="all">All submissions</option></select></label><label>District<select value={districtFilter} onChange={(e) => setDistrictFilter(e.target.value)}><option value="">Assigned districts</option>{DISTRICTS.map((district) => <option key={district}>{district}</option>)}</select></label><label>Crop<select value={cropFilter} onChange={(e) => setCropFilter(e.target.value)}><option value="">All crops</option>{[...new Set(items.map((item) => item.crop))].sort().map((crop) => <option key={crop}>{crop}</option>)}</select></label><label>From<input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} /></label><label>To<input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} /></label></div>
      {loading ? <LoadingState /> : filtered.length === 0 ? <EmptyState title="Queue is clear" description="There are no matching submissions in your assigned scope." icon={<Check size={20} />} /> : <div className="review-list">{filtered.map((item) => <article className="review-card" key={item.id}><div className="review-card-head"><div><div className="review-title-row"><h3>{item.activity_type} · {item.crop}</h3><StatusPill tone={item.review_status === 'pending' || item.review_status === 'correction_requested' ? 'amber' : item.review_status === 'approved_as_reviewed' ? 'green' : 'red'}>{item.review_status.replaceAll('_', ' ')}</StatusPill></div><p>{item.farm_name} · {item.district} · Season {item.season} · {item.event_date}</p></div><span className="verification-label">{item.verification.replaceAll('_', ' ')}</span></div>
          <dl className="report-facts"><div><dt>Reported quantity</dt><dd>{item.quantity ?? 'Not provided'} {item.quantity !== null && item.quantity !== undefined ? item.unit ?? '' : ''}</dd></div><div><dt>Area</dt><dd>{item.area_ha ?? 'Not provided'}{item.area_ha ? ' ha' : ''}</dd></div><div><dt>Amount</dt><dd>{item.amount_rwf ?? 'Not provided'}{item.amount_rwf ? ' RWF' : ''}</dd></div><div className="fact-notes"><dt>Farmer notes</dt><dd>{item.notes || 'No notes provided'}</dd></div></dl>
          {item.review_history.length > 0 && <details className="history-details"><summary>Previous decisions ({item.review_history.length})</summary>{item.review_history.map((decision, index) => <p key={`${decision.created_at}-${index}`}><strong>{decision.decision.replaceAll('_', ' ')}</strong> · {decision.reason} <small>{new Date(decision.created_at).toLocaleString()}</small></p>)}</details>}
          {(item.review_status === 'pending' || item.review_status === 'correction_requested') && <div className="review-actions"><label className="review-reason">Decision reason<textarea value={reasons[item.id] ?? ''} onChange={(e) => setReasons({ ...reasons, [item.id]: e.target.value })} rows={2} maxLength={2000} placeholder="Explain your decision for the record" /></label><div className="decision-buttons"><button className="button button-secondary" onClick={() => setConfirm({ item, decision: 'correction_requested' })}>Request correction</button><button className="button button-danger" onClick={() => setConfirm({ item, decision: 'rejected' })}>Reject</button><button className="button button-primary" onClick={() => setConfirm({ item, decision: 'approved_as_reviewed' })}>Mark reviewed</button></div></div>}
        </article>)}</div>}
      {!loading && items.length > 0 && <div className="pagination"><span>Page {page + 1} · {items.length} submissions loaded before filters</span><div><button className="button button-secondary" onClick={() => { setLoading(true); setPage((p) => Math.max(0, p - 1)); }} disabled={page === 0}>Previous</button><button className="button button-secondary" onClick={() => { setLoading(true); setPage((p) => p + 1); }} disabled={items.length < 100}>Next</button></div></div>}
    </section>
    {confirm && <ConfirmDialog title={decisionLabel[confirm.decision]} description={`This decision will be added to the permanent review history for ${confirm.item.activity_type.toLowerCase()} · ${confirm.item.crop}. The original farmer report will remain unchanged.`} reason={reasons[confirm.item.id] ?? ''} setReason={(v) => setReasons({ ...reasons, [confirm.item.id]: v })} onCancel={() => setConfirm(null)} onConfirm={() => void decide()} busy={busy} confirmLabel={decisionLabel[confirm.decision]} />}
  </>;
}

export function AccountsPage() {
  const [accounts, setAccounts] = useState<AdminFarmer[]>([]);
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState<Notice>(null);
  const [pending, setPending] = useState<{ account: AdminFarmer; kind: 'suspend' | 'activate' | 'revoke' } | null>(null);
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [permissionsFor, setPermissionsFor] = useState('');
  const [roleDraft, setRoleDraft] = useState('farmer');
  const [districtDraft, setDistrictDraft] = useState<string[]>([]);
  const [permissionReason, setPermissionReason] = useState('');
  const load = useCallback(async () => { const params = new URLSearchParams({ limit: '100', offset: String(page * 100) }); if (search.trim()) params.set('q', search.trim()); if (status) params.set('status', status); try { const rows = await api<AdminFarmer[]>(`/v1/admin/farmers?${params}`); setAccounts(rows); setError(''); } catch (e) { setError(e instanceof Error ? e.message : 'Accounts are unavailable.'); } finally { setLoading(false); } }, [page, search, status]);
  useEffect(() => { void load(); }, [load]);
  async function accountAction() {
    if (!pending) return; setBusy(true); setNotice(null);
    try {
      if (pending.kind === 'revoke') await api(`/v1/admin/farmers/${pending.account.id}/revoke-sessions`, { method: 'POST', body: JSON.stringify({ reason }) });
      else await api(`/v1/admin/farmers/${pending.account.id}/status`, { method: 'PATCH', body: JSON.stringify({ status: pending.kind === 'suspend' ? 'suspended' : 'active', reason }) });
      setNotice({ type: 'success', text: pending.kind === 'revoke' ? 'Active account sessions revoked.' : `Account ${pending.kind === 'suspend' ? 'suspended' : 'reactivated'}.` }); setPending(null); setReason(''); await load();
    } catch (e) { setNotice({ type: 'error', text: e instanceof Error ? e.message : 'Account change failed.' }); }
    finally { setBusy(false); }
  }
  async function savePermissions(account: AdminFarmer) {
    setBusy(true); setNotice(null);
    try {
      await api(`/v1/admin/farmers/${account.id}/permissions`, { method: 'PATCH', body: JSON.stringify({ role: roleDraft, districts: roleDraft === 'reviewer' ? districtDraft : [], reason: permissionReason }) });
      setNotice({ type: 'success', text: 'Account permissions updated and recorded in the audit history.' }); setPermissionsFor(''); setPermissionReason(''); await load();
    } catch (e) { setNotice({ type: 'error', text: e instanceof Error ? e.message : 'Permission change failed.' }); }
    finally { setBusy(false); }
  }
  const actionLabel = pending?.kind === 'suspend' ? 'Suspend account' : pending?.kind === 'activate' ? 'Reactivate account' : 'Revoke active sessions';
  return <>
    <PageHeader eyebrow="PLATFORM ADMINISTRATION" title="Farmer accounts" description="Search accounts and apply audited access controls. Personal details are shown only to platform administrators." />
    <Alert notice={notice} />{error && <ErrorState text={error} retry={() => { setLoading(true); void load(); }} />}
    <section className="panel"><div className="panel-heading"><div><h2>Registered accounts</h2><p>Page size is limited to 100 accounts per query.</p></div><div className="table-filters"><label className="sr-only" htmlFor="account-search">Search name or email</label><input id="account-search" placeholder="Search name or email" value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') { setLoading(true); setPage(0); setSearch(query); } }} /><button className="button button-secondary" onClick={() => { setLoading(true); setPage(0); setSearch(query); }}>Search</button><label className="sr-only" htmlFor="status-filter">Filter by status</label><select id="status-filter" value={status} onChange={(e) => { setLoading(true); setPage(0); setStatus(e.target.value); }}><option value="">All statuses</option><option value="active">Active</option><option value="suspended">Suspended</option></select></div></div>
      {loading ? <LoadingState /> : accounts.length === 0 ? <EmptyState title="No matching accounts" description="Try changing the search or status filter." icon={<Users size={20} />} /> : <><div className="table-scroll"><table><thead><tr><th>Account</th><th>Role</th><th>District scope</th><th>Status</th><th>Farms</th><th>Created</th><th>Actions</th></tr></thead><tbody>{accounts.map((account) => <tr key={account.id}><td><strong>{account.display_name}</strong><small>{account.email}</small></td><td><StatusPill tone={account.role === 'admin' ? 'blue' : account.role === 'reviewer' ? 'green' : 'neutral'}>{account.role}</StatusPill></td><td>{account.role === 'reviewer' ? account.reviewer_districts.join(', ') || 'No districts assigned' : '—'}</td><td><StatusPill tone={account.status === 'active' ? 'green' : 'red'}>{account.status}</StatusPill></td><td>{account.farm_count}</td><td>{new Date(account.created_at).toLocaleDateString()}</td><td><div className="row-actions"><button className="table-action" onClick={() => { setPending({ account, kind: account.status === 'active' ? 'suspend' : 'activate' }); setReason(''); }}>{account.status === 'active' ? 'Suspend' : 'Reactivate'}</button><button className="table-action" onClick={() => { setPending({ account, kind: 'revoke' }); setReason(''); }}>Revoke sessions</button><button className="table-action" onClick={() => { setPermissionsFor(permissionsFor === account.id ? '' : account.id); setRoleDraft(account.role); setDistrictDraft(account.reviewer_districts ?? []); setPermissionReason(''); }}>Permissions</button></div>
          {permissionsFor === account.id && <div className="permission-panel"><label>Role<select value={roleDraft} onChange={(e) => setRoleDraft(e.target.value)}><option value="farmer">Farmer</option><option value="reviewer">Agricultural reviewer</option><option value="admin">Platform administrator</option></select></label>{roleDraft === 'reviewer' && <fieldset><legend>Assigned districts</legend><div className="district-checks">{DISTRICTS.map((district) => <label key={district}><input type="checkbox" checked={districtDraft.includes(district)} onChange={(e) => setDistrictDraft(e.target.checked ? [...districtDraft, district] : districtDraft.filter((item) => item !== district))} />{district}</label>)}</div></fieldset>}<label>Reason<textarea rows={2} value={permissionReason} onChange={(e) => setPermissionReason(e.target.value)} minLength={5} /></label><button className="button button-primary" disabled={busy || permissionReason.trim().length < 5 || (roleDraft === 'reviewer' && districtDraft.length === 0)} onClick={() => void savePermissions(account)}>Save permissions</button></div>}
        </td></tr>)}</tbody></table></div><div className="pagination"><span>Page {page + 1} · {accounts.length} accounts shown</span><div><button className="button button-secondary" onClick={() => setPage((p) => Math.max(0, p - 1))} disabled={page === 0 || loading}>Previous</button><button className="button button-secondary" onClick={() => setPage((p) => p + 1)} disabled={accounts.length < 100 || loading}>Next</button></div></div></>}
    </section>
    {pending && <ConfirmDialog title={actionLabel} description={`${pending.account.display_name} (${pending.account.email}). ${pending.kind === 'suspend' ? 'This revokes active sessions and blocks future sign-ins.' : pending.kind === 'activate' ? 'The farmer can sign in again after this change.' : 'This signs out all devices currently using the account.'}`} reason={reason} setReason={setReason} onCancel={() => setPending(null)} onConfirm={() => void accountAction()} busy={busy} confirmLabel={actionLabel} />}
  </>;
}

export function ReportsPage() {
  const [data, setData] = useState<AdminOverview | null>(null);
  const [error, setError] = useState('');
  useEffect(() => { void api<AdminOverview>('/v1/admin/overview').then(setData).catch((e: Error) => setError(e.message)); }, []);
  function exportCsv() {
    if (!data) return;
    const rows = [['Metric', 'Value', 'Definition'], ['Registered accounts', data.accounts.total, 'Current accounts'], ['Active accounts', data.accounts.active, 'Current account status'], ['Suspended accounts', data.accounts.suspended, 'Current account status'], ['Registered farms', data.farms, 'Current saved farm profiles'], ['Farmer reported activities', data.farmer_reported_activities, data.definitions.farmer_reported_activities], ['Awaiting review', data.awaiting_review, data.definitions.awaiting_review]];
    const csv = rows.map((row) => row.map((field) => `"${String(field).replaceAll('"', '""')}"`).join(',')).join('\r\n');
    const blob = new Blob([`Generated at,${new Date().toISOString()}\r\n${csv}`], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = `croppulse-aggregate-report-${new Date().toISOString().slice(0, 10)}.csv`; a.click(); URL.revokeObjectURL(url);
  }
  return <><PageHeader eyebrow="PLATFORM ADMINISTRATION" title="Reports & exports" description="Download current aggregated platform counts with their definitions and generation time." action={<button className="button button-primary" onClick={exportCsv} disabled={!data}><ArrowDownToLine size={16} /> Export aggregate CSV</button>} />{error && <ErrorState text={error} />}{data && <><div className="notice notice-info"><ShieldCheck size={17} /><span>This export contains counts only. There are no historical snapshots for trend reporting, and no farmer email addresses are included.</span></div><section className="panel"><div className="panel-heading"><div><h2>Report contents</h2><p>Current values queried from persistent records.</p></div><span className="panel-badge">{new Date().toLocaleString()}</span></div><div className="report-metric-list">{[['Registered accounts', data.accounts.total], ['Active accounts', data.accounts.active], ['Suspended accounts', data.accounts.suspended], ['Registered farms', data.farms], ['Farmer reported activities', data.farmer_reported_activities], ['Awaiting review', data.awaiting_review]].map(([label, value]) => <div key={String(label)}><span>{label}</span><strong>{value}</strong></div>)}</div></section></>}</>;
}

export function SystemPage() {
  const [data, setData] = useState<AdminOverview | null>(null);
  const [events, setEvents] = useState<{ id: string; actor_id: string | null; target_farmer_id: string | null; action: string; target_type: string; target_id: string; reason: string; result: string; created_at: string }[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    void Promise.all([api<AdminOverview>('/v1/admin/overview'), api<typeof events>('/v1/admin/audit-events?limit=50')])
      .then(([overview, audit]) => { setData(overview); setEvents(audit); })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);
  return <><PageHeader eyebrow="PLATFORM ADMINISTRATION" title="System health" description="Live connectivity checks and recent privileged actions currently available from this API." />{error && <ErrorState text={error} />}{loading && <LoadingState />}{data && <><div className="health-grid"><div className="health-card"><span>API request</span><StatusPill tone="green">{data.health.api}</StatusPill><small>Current request returned successfully.</small></div><div className="health-card"><span>Database</span><StatusPill tone="green">{data.health.database}</StatusPill><small>The API executed database reads for this response.</small></div><div className="health-card"><span>Backup status</span><StatusPill>Not monitored</StatusPill><small>No backup monitoring integration is configured.</small></div><div className="health-card"><span>Recent error counts</span><StatusPill>Not available</StatusPill><small>Error history is not persisted by this application.</small></div></div><MessagingAdminSetting /><AgronomyReviewAuthorizationAdmin /><div className="notice notice-info"><ShieldCheck size={17} /><span>These are current request checks, not service uptime or backup guarantees. No secrets, server traces, or credentials are exposed.</span></div><section className="panel"><div className="panel-heading"><div><h2>Administrative activity</h2><p>Recent privileged actions with recorded actor, target, reason, and result.</p></div><span className="panel-badge">LATEST {events.length}</span></div>{events.length === 0 ? <EmptyState title="No administrative actions recorded" description="Role, account status, session, and review decisions will appear here when performed." icon={<ShieldCheck size={20} />} /> : <div className="table-scroll"><table><thead><tr><th>Time</th><th>Action</th><th>Actor</th><th>Target</th><th>Reason</th><th>Result</th></tr></thead><tbody>{events.map((event) => <tr key={event.id}><td>{new Date(event.created_at).toLocaleString()}</td><td><strong>{event.action.replaceAll('_', ' ')}</strong></td><td><small>{event.actor_id ? event.actor_id.slice(0, 8) : 'Operator bootstrap'}</small></td><td>{event.target_type} · {event.target_id.slice(0, 8)}</td><td>{event.reason || '—'}</td><td><StatusPill tone={event.result === 'success' ? 'green' : 'red'}>{event.result}</StatusPill></td></tr>)}</tbody></table></div>}</section></>}</>;
}

function AgronomyReviewAuthorizationAdmin() {
  const [accounts, setAccounts] = useState<AdminFarmer[]>([]);
  const [events, setEvents] = useState<AgronomyReviewAuthorizationEvent[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [people, history] = await Promise.all([
        api<AdminFarmer[]>('/v1/admin/farmers?status=active&limit=100'),
        api<AgronomyReviewAuthorizationEvent[]>('/v1/admin/agronomy-review-authorizations'),
      ]);
      setAccounts(people.filter((person) => person.role === 'reviewer' || person.role === 'admin'));
      setEvents(history);
      setError('');
    } catch (e) { setError(e instanceof Error ? e.message : 'Agronomy review permissions could not be loaded.'); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void load(); }, [load]);
  const latestAction = new Map<string, 'grant' | 'revoke'>();
  events.forEach((event) => { if (!latestAction.has(event.reviewer_id)) latestAction.set(event.reviewer_id, event.action); });
  async function update(action: 'grant' | 'revoke') {
    if (!selectedId || reason.trim().length < 8) return;
    setBusy(true);
    try {
      await api(`/v1/admin/farmers/${selectedId}/agronomy-review-authorization`, { method: 'POST', body: JSON.stringify({ action, reason }) });
      setReason(''); setError(''); await load();
    } catch (e) { setError(e instanceof Error ? e.message : 'The authorization change could not be saved.'); }
    finally { setBusy(false); }
  }
  return <section className="panel agronomy-review-admin" aria-labelledby="agronomy-review-admin-title">
    <div className="panel-heading"><div><h2 id="agronomy-review-admin-title">Agronomic rule-review access</h2><p>Explicitly grant this additional permission to an active reviewer or administrator. No account receives it by default.</p></div><ShieldCheck size={19} /></div>
    {error && <ErrorState text={error} />}{loading ? <LoadingState label="Loading review permissions…" /> : <>
      <label>Reviewer account<select value={selectedId} onChange={(event) => setSelectedId(event.target.value)}><option value="">Choose an active reviewer or administrator</option>{accounts.map((person) => <option key={person.id} value={person.id}>{person.display_name} · {person.role} · {person.email}</option>)}</select></label>
      {selectedId && <p>{latestAction.get(selectedId) === 'grant' ? 'Currently explicitly authorized.' : 'No active agronomy review authorization recorded.'}</p>}
      <label htmlFor="agronomy-review-authorization-reason">Audit reason</label><input id="agronomy-review-authorization-reason" value={reason} onChange={(event) => setReason(event.target.value)} minLength={8} maxLength={1000} />
      <div className="dialog-actions"><button className="button button-primary" disabled={busy || !selectedId || reason.trim().length < 8} onClick={() => void update('grant')}>Grant review access</button><button className="button button-secondary" disabled={busy || !selectedId || reason.trim().length < 8 || latestAction.get(selectedId) !== 'grant'} onClick={() => void update('revoke')}>Revoke review access</button></div>
      {events.length > 0 && <div className="table-scroll"><table><thead><tr><th>When</th><th>Reviewer</th><th>Action</th><th>Authorized by</th><th>Reason</th></tr></thead><tbody>{events.map((event) => <tr key={event.id}><td>{new Date(event.created_at).toLocaleString()}</td><td>{event.reviewer_name} · {event.reviewer_role}</td><td>{event.action}</td><td>{event.actor_id?.slice(0, 8) ?? 'Removed account'}</td><td>{event.reason}</td></tr>)}</tbody></table></div>}
      <p className="summary-provenance">This permission does not verify professional qualifications. Rule-review decisions are auditable but do not activate farmer guidance; the agronomic evidence trust anchor is still disabled.</p>
    </>}
  </section>;
}

function MessagingAdminSetting() {
  const [enabled, setEnabled] = useState(false);
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [loaded, setLoaded] = useState(false);
  useEffect(() => { void api<{ farmer_reviewer_enabled: boolean }>('/v1/admin/messaging-setting')
    .then((setting) => setEnabled(setting.farmer_reviewer_enabled)).catch((e: Error) => setError(e.message)).finally(() => setLoaded(true)); }, []);
  async function save() {
    if (reason.trim().length < 5) { setError('Enter a reason of at least 5 characters.'); return; }
    setBusy(true); setError('');
    try {
      const setting = await api<{ farmer_reviewer_enabled: boolean }>('/v1/admin/messaging-setting', {
        method: 'PUT', body: JSON.stringify({ farmer_reviewer_enabled: !enabled, reason: reason.trim() }),
      });
      setEnabled(setting.farmer_reviewer_enabled); setReason('');
    } catch (e) { setError(e instanceof Error ? e.message : 'Setting could not be saved.'); }
    finally { setBusy(false); }
  }
  return <section className="panel messaging-admin-setting"><div><h2>Private farmer-to-reviewer messaging</h2><p>{enabled ? 'Enabled. Eligible farmers and CropPulse reviewers can use private text conversations.' : 'Disabled. An administrator must enable messaging before users can access it.'}</p></div><label htmlFor="messaging-setting-reason">Reason for change</label><input id="messaging-setting-reason" value={reason} onChange={(event) => setReason(event.target.value)} maxLength={1000} placeholder="Required audit reason" />{error && <ErrorState text={error} />}<button className="button button-primary" disabled={!loaded || busy} onClick={() => void save()}>{busy ? 'Saving…' : enabled ? 'Disable messaging' : 'Enable messaging'}</button></section>;
}

export function SettingsPage() {
  const { user, logout, deleteAccount } = useAuth();
  const [newEmail, setNewEmail] = useState('');
  const [emailPassword, setEmailPassword] = useState('');
  const [emailBusy, setEmailBusy] = useState(false);
  const [emailNotice, setEmailNotice] = useState<Notice>(null);
  const [deletePassword, setDeletePassword] = useState('');
  const [deletePhrase, setDeletePhrase] = useState('');
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [deleteError, setDeleteError] = useState('');
  async function requestChange(event: FormEvent) {
    event.preventDefault(); setEmailBusy(true); setEmailNotice(null);
    try {
      const result = await requestEmailChange(emailPassword, newEmail.trim());
      setEmailNotice({ type: 'success', text: result.message }); setEmailPassword(''); setNewEmail('');
    } catch (e) { setEmailNotice({ type: 'error', text: e instanceof Error ? e.message : 'Email change could not be requested.' }); }
    finally { setEmailBusy(false); }
  }
  async function removeAccount(event: FormEvent) {
    event.preventDefault(); if (deletePhrase !== 'DELETE') return;
    setDeleteBusy(true); setDeleteError('');
    try { await deleteAccount(deletePassword); }
    catch (e) { setDeleteError(e instanceof Error ? e.message : 'Account deletion could not be completed.'); }
    finally { setDeleteBusy(false); }
  }
  return <>
    <PageHeader eyebrow="ACCOUNT" title="Account settings" description="Identity, access scope, and session controls for this account." />
    <section className="panel settings-panel">
      <div className="settings-identity"><span className="avatar avatar-large">{user?.display_name.slice(0, 1).toUpperCase()}</span><div><h2>{user?.display_name}</h2><p>{user?.email}</p><StatusPill tone={user?.role === 'admin' ? 'blue' : 'green'}>{user?.role}</StatusPill></div></div>
      <div className="settings-row"><div><strong>Account status</strong><p>Current account access state.</p></div><StatusPill tone={user?.status === 'active' ? 'green' : 'red'}>{user?.status}</StatusPill></div>
      <div className="settings-row"><div><strong>Browser session</strong><p>HttpOnly session cookie, bounded to 30 minutes and revocable by the server.</p></div><button className="button button-secondary" onClick={() => void logout()}>Sign out</button></div>
      <form className="panel form-panel" onSubmit={(event) => void requestChange(event)}>
        <div className="panel-heading"><div><h2>Change email address</h2><p>We will send a one-time confirmation link to the new address. Your email changes only after confirmation.</p></div></div>
        <Alert notice={emailNotice} />
        <div className="form-grid"><label>New email address<input type="email" autoComplete="email" value={newEmail} onChange={(e) => setNewEmail(e.target.value)} required maxLength={254} /></label><label>Current password<input type="password" autoComplete="current-password" value={emailPassword} onChange={(e) => setEmailPassword(e.target.value)} required maxLength={128} /></label><div className="form-end"><button type="submit" className="button button-primary" disabled={emailBusy}>{emailBusy ? 'Sending…' : 'Send confirmation link'}</button></div></div>
      </form>
      <div className="panel form-panel"><div className="panel-heading"><div><h2>Password recovery</h2><p>Forgot your password? Sign out and use “Forgot password?” on the sign-in screen. A reset link will be sent to your account email.</p></div><button className="button button-secondary" type="button" onClick={() => void logout()}>Sign out to recover password</button></div></div>
      <form className="panel form-panel" onSubmit={(event) => void removeAccount(event)}>
        <div className="panel-heading"><div><h2>Delete account</h2><p>This permanently removes your account, farms, plans, activities, and active sessions. Reviewer decisions and audit records are retained with your identity removed. The last administrator cannot delete their account.</p></div></div>
        {deleteError && <ErrorState text={deleteError} />}
        <div className="form-grid"><label>Current password<input type="password" autoComplete="current-password" value={deletePassword} onChange={(e) => setDeletePassword(e.target.value)} required maxLength={128} /></label><label>Type DELETE to confirm<input value={deletePhrase} onChange={(e) => setDeletePhrase(e.target.value)} required pattern="DELETE" /></label><div className="form-end"><button className="button button-danger" disabled={deleteBusy || deletePhrase !== 'DELETE'}>{deleteBusy ? 'Deleting…' : 'Permanently delete account'}</button></div></div>
      </form>
    </section>
  </>;
}
