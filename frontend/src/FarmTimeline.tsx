import { useCallback, useEffect, useRef, useState } from 'react';
import { Activity } from 'lucide-react';
import { api, type FarmTimelineEntry, type FarmTimelineEventType } from './api';

const eventLabels: Record<FarmTimelineEventType, string> = {
  crop_plan_created: 'Crop plan created', planting_recorded: 'Planting recorded', activity: 'Farm activity',
  irrigation: 'Irrigation / water event', soil_observation: 'Soil observation', soil_test: 'Soil-test record',
  harvest: 'Harvest', post_harvest_observation: 'Post-harvest observation',
};
const linkLabels: Record<FarmTimelineEventType, string> = {
  crop_plan_created: 'crop plan', planting_recorded: 'crop plan', activity: 'activity', irrigation: 'irrigation',
  soil_observation: 'soil', soil_test: 'soil', harvest: 'harvest', post_harvest_observation: 'harvest',
};

function dateLabel(value: string | null) {
  if (!value) return 'Date not recorded';
  const [year, month, day] = value.slice(0, 10).split('-').map(Number);
  if (!year || !month || !day) return 'Date not recorded';
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeZone: 'UTC' }).format(new Date(Date.UTC(year, month - 1, day)));
}

export function FarmTimeline({ farmId }: { farmId: string }) {
  const [entries, setEntries] = useState<FarmTimelineEntry[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const requestId = useRef(0);

  const load = useCallback(async () => {
    const request = ++requestId.current;
    if (!farmId) { setEntries([]); setHasMore(false); setError(''); return; }
    setLoading(true); setError('');
    try {
      const response = await api<{ entries: FarmTimelineEntry[]; has_more: boolean }>(`/v1/farms/${encodeURIComponent(farmId)}/timeline`);
      if (request === requestId.current) {
        const ordered = [...response.entries].sort((a, b) => {
          if (!a.event_date) return b.event_date ? 1 : a.id.localeCompare(b.id);
          if (!b.event_date) return -1;
          return b.event_date.localeCompare(a.event_date) || a.id.localeCompare(b.id);
        });
        setEntries(ordered); setHasMore(response.has_more);
      }
    } catch (cause) {
      if (request === requestId.current) { setEntries([]); setHasMore(false); setError(cause instanceof Error ? cause.message : 'Farm timeline could not be loaded.'); }
    } finally {
      if (request === requestId.current) setLoading(false);
    }
  }, [farmId]);

  useEffect(() => {
    setEntries([]); setHasMore(false); void load();
    return () => { requestId.current += 1; };
  }, [load]);

  return <section className="panel records-panel farm-timeline" aria-labelledby="farm-timeline-title">
    <div className="panel-heading"><div><span className="eyebrow">EXISTING FARM RECORDS</span><h2 id="farm-timeline-title">Farm activity timeline</h2><p>Read-only view of saved plans and farmer-reported records. A missing timeline entry does not mean an activity did not happen.</p></div></div>
    {error && <div className="notice notice-error" role="alert"><span>{error}</span><button type="button" className="text-button" onClick={() => void load()}>Try again</button></div>}
    {loading && <div className="timeline-loading" role="status" aria-live="polite">Loading farm timeline…</div>}
    {!loading && !error && entries.length === 0 && <div className="timeline-empty"><Activity size={18} /><p>No existing records are available for this farm timeline. This does not show whether other farm activity occurred.</p></div>}
    {!loading && !error && entries.length > 0 && <>
      <ol className="timeline-list">
        {entries.map((entry) => <li key={entry.id} className="timeline-entry">
          <div className="timeline-date">{dateLabel(entry.event_date)}</div>
          <article className="timeline-card">
            <div className="timeline-card-top"><span className="timeline-kind">{eventLabels[entry.event_type]}</span><span className="verification-label">{entry.source_label}</span></div>
            <p>{entry.description}</p>
            <div className="timeline-context">{entry.farm_name}{entry.field_name ? ` · ${entry.field_name}` : ' · Farm-level or field not recorded'}</div>
            <a className="text-button timeline-link" href={entry.href}>View {linkLabels[entry.event_type]} records</a>
          </article>
        </li>)}
      </ol>
      {hasMore && <p className="timeline-more">Showing the latest 300 matching records. Older entries are not included in this view.</p>}
      <p className="timeline-undated-note">Entries without a stored event date, if present, are shown last as “Date not recorded.” No date is inferred from another record.</p>
    </>}
  </section>;
}
