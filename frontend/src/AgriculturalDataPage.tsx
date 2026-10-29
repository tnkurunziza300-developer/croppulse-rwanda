import { useCallback, useEffect, useMemo, useState } from 'react';
import { ExternalLink, RefreshCw } from 'lucide-react';
import { getNisrStatistics } from './api';
import type { NisrStatistics } from './api';
import { ErrorState, LoadingState, PageHeader } from './pages';

const PAGE_SIZE = 50;

function sourceLabel(url: string) {
  if (url.includes('season-b-2026')) return '2026 Season B tables';
  if (url.includes('season-2026')) return '2026 Season A tables';
  if (url.includes('seasonal-agricultural-survey-2025')) return '2025 annual tables';
  if (url.includes('seasonal-agricultural-survey-2024')) return '2024 annual tables';
  if (url.includes('seasonal-agricultural-survey-2023')) return '2023 annual tables';
  return 'NISR publication';
}

export function AgriculturalDataPage() {
  const [data, setData] = useState<NisrStatistics | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [year, setYear] = useState('all');
  const [season, setSeason] = useState('all');
  const [district, setDistrict] = useState('all');
  const [crop, setCrop] = useState('all');
  const [page, setPage] = useState(0);

  const load = useCallback(async () => {
    setLoading(true);
    try { setData(await getNisrStatistics()); setError(''); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'NISR statistics could not be loaded.'); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void load(); }, [load]);

  const filtered = useMemo(() => (data?.records ?? []).filter((row) =>
    (year === 'all' || row.year === Number(year)) && (season === 'all' || row.season === season)
    && (district === 'all' || row.district === district) && (crop === 'all' || row.crop === crop)),
  [data, year, season, district, crop]);
  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const visible = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const area = filtered.reduce((sum, row) => sum + row.area_ha, 0);
  const production = filtered.reduce((sum, row) => sum + row.production_t, 0);
  const weightedYield = area > 0 ? production / area : null;
  const updateFilter = (setter: (value: string) => void) => (event: React.ChangeEvent<HTMLSelectElement>) => {
    setter(event.target.value); setPage(0);
  };

  return <>
    <PageHeader eyebrow="NATIONAL AGRICULTURAL DATA" title="NISR crop statistics" description="Explore Rwanda Seasonal Agricultural Survey area and production figures by district, crop, year, and season." action={<button className="button button-secondary" onClick={() => void load()} disabled={loading}><RefreshCw size={15} /> Refresh</button>} />
    {loading && !data && <LoadingState label="Loading NISR statistics…" />}
    {error && <ErrorState text={error} retry={() => void load()} />}
    {data && <>
      <section className="panel nisr-source-panel" aria-label="Dataset provenance">
        <div><span className="eyebrow">SOURCE</span><h2>{data.publisher}</h2><p>{data.title}</p></div>
        <div className="nisr-source-links"><strong>Official publications</strong>{[...new Set(data.source_url.split(' | '))].map((url) => <a key={url} href={url} target="_blank" rel="noreferrer">{sourceLabel(url)} <ExternalLink size={12} /></a>)}</div>
        <div className="nisr-source-facts"><span><strong>Coverage</strong>{data.coverage.coverage_label}</span><span><strong>Periods</strong>{data.reference_period}</span><span><strong>Retrieved</strong>{new Date(data.retrieved_at).toLocaleDateString()}</span><span><strong>Units</strong>{data.units}</span></div>
      </section>
      <div className="notice notice-info"><span>{data.limitations} CropPulse checks the imported file, manifest, units, geography, and record structure; NISR remains the source authority for survey estimates.</span></div>
      <div className="form-grid nisr-filters" aria-label="Filter statistics">
        <label>Year<select value={year} onChange={updateFilter(setYear)}><option value="all">All years</option>{data.available_years.map((value) => <option key={value}>{value}</option>)}</select></label>
        <label>Season<select value={season} onChange={updateFilter(setSeason)}><option value="all">All seasons</option>{data.available_seasons.map((value) => <option key={value}>{value}</option>)}</select></label>
        <label>District<select value={district} onChange={updateFilter(setDistrict)}><option value="all">All districts</option>{data.available_districts.map((value) => <option key={value}>{value}</option>)}</select></label>
        <label>Crop<select value={crop} onChange={updateFilter(setCrop)}><option value="all">All crops</option>{data.available_crops.map((value) => <option key={value}>{value}</option>)}</select></label>
      </div>
      <div className="metrics-grid compact-metrics">
        <article className="metric-card"><div className="metric-top"><span>Selected records</span></div><strong className="metric-value">{filtered.length.toLocaleString()}</strong><small>District · crop · season rows</small></article>
        <article className="metric-card"><div className="metric-top"><span>Area in selected records</span></div><strong className="metric-value">{area.toLocaleString(undefined, { maximumFractionDigits: 1 })} ha</strong><small>Sum of the filtered crop records</small></article>
        <article className="metric-card"><div className="metric-top"><span>Production in selected records</span></div><strong className="metric-value">{production.toLocaleString(undefined, { maximumFractionDigits: 1 })} t</strong><small>Survey-reported aggregate production</small></article>
        <article className="metric-card"><div className="metric-top"><span>Weighted yield</span></div><strong className="metric-value">{weightedYield === null ? '—' : `${weightedYield.toLocaleString(undefined, { maximumFractionDigits: 2 })} t/ha`}</strong><small>Selected-record production ÷ area</small></article>
      </div>
      <section className="panel records-panel">
        <div className="panel-heading"><div><h2>District observations</h2><p>Missing source cells are not shown as zero. Yield is calculated from reported production and area.</p></div><span className="panel-badge">NISR SAS</span></div>
        {filtered.length === 0 ? <div className="empty-state"><strong>No records for these filters</strong><p>Choose a different year, season, district, or crop.</p></div> : <>
          <div className="table-scroll"><table><thead><tr><th>Year</th><th>Season</th><th>District</th><th>Crop</th><th>Area (ha)</th><th>Production (t)</th><th>Yield (t/ha)</th></tr></thead><tbody>{visible.map((row, index) => <tr key={`${row.year}-${row.season}-${row.district}-${row.crop}-${index}`}><td>{row.year}</td><td>{row.season}</td><td>{row.district}</td><td>{row.crop}</td><td>{row.area_ha.toLocaleString(undefined, { maximumFractionDigits: 2 })}</td><td>{row.production_t.toLocaleString(undefined, { maximumFractionDigits: 2 })}</td><td>{row.yield_t_ha === null ? '—' : row.yield_t_ha.toLocaleString(undefined, { maximumFractionDigits: 2 })}</td></tr>)}</tbody></table></div>
          <div className="settings-row"><span>Showing {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, filtered.length)} of {filtered.length.toLocaleString()}</span><div className="row-actions"><button className="button button-secondary" disabled={page === 0} onClick={() => setPage((current) => current - 1)}>Previous</button><button className="button button-secondary" disabled={page + 1 >= pageCount} onClick={() => setPage((current) => current + 1)}>Next</button></div></div>
        </>}
      </section>
      <p className="muted nisr-disclaimer">These are district-level agricultural survey statistics. They are not a disease diagnosis, farmer-specific forecast, or standalone crop-treatment recommendation.</p>
    </>}
  </>;
}
