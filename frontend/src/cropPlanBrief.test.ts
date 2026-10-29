import { afterEach, describe, expect, it, vi } from 'vitest';
import type { CropPlan, Farm, FarmField } from './api';
import { buildSavedCropPlanBrief, downloadSavedCropPlanBrief } from './cropPlanBrief';

const farm: Farm = { id: 'farm-1', owner_id: 'farmer-1', name: 'North Farm', district: 'Huye', sector: 'Ngoma', area_ha: 1.5 };
const field: FarmField = { id: 'field-1', farm_id: farm.id, name: 'Upper field', area_ha: 0.75, latitude: -2.5, longitude: 29.7, archived_at: null, created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' };
const plan: CropPlan = {
  id: 'plan-1', farm_id: farm.id, field_id: field.id, district: 'Huye', crop: 'Beans', season: 'B',
  planting_date: '2026-10-20', area_ha: 0.5, plan: { farmer_notes: 'Farmer observation', recommendation_snapshot: {
    crop: 'Beans', status: 'Provisional guide fit: possible', evidence_basis: 'provisional CropPulse guide; not a prediction of success',
    planting_window: 'Provisional calendar (unverified)', guidance_source: 'CropPulse guide (unverified)',
    generated_at: '2026-10-01T10:00:00Z', snapshot_status: 'not independently verified', ranking_method: 'provisional category then crop name',
    reasons: ['Broad guide category'], risks: ['Soil is unknown'], evidence: ['No approved rule applies'],
    history: { years: [2023, 2024], yields: [1.1, 1.3] },
    conditions: { district: 'Huye', season: 'B', elevation_m: null, irrigation: 'Unknown', water_availability: 'Unknown', statistics_status: 'validated', statistics_note: 'Historical statistics only', statistics_provenance: [{ publisher: 'NISR', reference_period: '2023–2024', source_url: 'https://example.test/source' }] },
  } }, verification: 'provisional', status: 'planned', actual_planting_date: null, evidence: [],
};

afterEach(() => { vi.restoreAllMocks(); });

describe('saved crop plan brief', () => {
  it('summarizes the saved plan and labels recommendation and historical context correctly', () => {
    const brief = buildSavedCropPlanBrief(plan, farm, field, '2026-10-28T12:00:00Z');
    expect(brief).toContain('North Farm');
    expect(brief).toContain('Upper field');
    expect(brief).toContain('District: Huye');
    expect(brief).toContain('Farmer notes (not verified): Farmer observation');
    expect(brief).toContain('Provisional guide fit: possible');
    expect(brief).toContain('2023: 1.1 t/ha (historical district statistic)');
    expect(brief).toContain('not a farm-specific estimate, forecast, suitability guarantee, or ranking input');
    expect(brief).not.toContain('-2.5');
    expect(brief).not.toContain('29.7');
  });

  it('retains evidence provenance and clearly says when no evidence is attached', () => {
    const withEvidence = { ...plan, evidence: [{ id: 'e1', claim: 'Scoped claim', crop: 'Beans', geographic_applicability: 'Huye', source_name: 'Source title', source_organization: 'RAB', source_url: 'https://example.test/source', source_identifier: null, publication_date: '2025-01-01', retrieval_date: '2026-01-01', evidence_period: '2024–2025', units: 't/ha', confidence: null, limitations: 'Limited scope', dataset_version: null, recommender_version: null, generated_at: '2026-10-01T00:00:00Z', verification_status: 'reviewed' }] };
    const brief = buildSavedCropPlanBrief(withEvidence, farm, field, '2026-10-28T12:00:00Z');
    expect(brief).toContain('Status recorded with plan: reviewed');
    expect(brief).toContain('Source: Source title — RAB');
    expect(brief).toContain('https://example.test/source');
    expect(brief).toContain('Limitations: Limited scope');
    expect(buildSavedCropPlanBrief(plan, farm, field)).toContain('No independently verified evidence records are attached');
  });

  it('does not include historical values unless the saved statistics state is validated', () => {
    const unvalidated = { ...plan, plan: { recommendation_snapshot: {
      ...plan.plan.recommendation_snapshot as object,
      conditions: { statistics_status: 'warning' },
    } } };
    const brief = buildSavedCropPlanBrief(unvalidated, farm, field);
    expect(brief).not.toContain('1.1 t/ha');
    expect(brief).toContain('No validated historical statistic is included');
  });

  it('escapes farmer-controlled markdown and handles absent saved fields', () => {
    const unsafeFarm = { ...farm, name: '# Heading\n<script>alert(1)</script>' };
    const sparsePlan = { ...plan, field_id: null, plan: {} };
    const brief = buildSavedCropPlanBrief(sparsePlan, unsafeFarm, undefined, '2026-10-28T12:00:00Z');
    expect(brief).toContain('\\# Heading &lt;script&gt;alert\\(1\\)&lt;/script&gt;');
    expect(brief).not.toContain('&lt;script\\&gt;');
    expect(brief).toContain('Field: Farm-level plan');
    expect(brief).toContain('Actual planting date: Not recorded');
    expect(brief).toContain('No independently verified evidence records are attached');
  });

  it('downloads a markdown Blob with a safe filename and no false success state', async () => {
    const create = vi.fn(() => 'blob:synthetic');
    const revoke = vi.fn();
    const createDescriptor = Object.getOwnPropertyDescriptor(URL, 'createObjectURL');
    const revokeDescriptor = Object.getOwnPropertyDescriptor(URL, 'revokeObjectURL');
    Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: create });
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: revoke });
    let filename = '';
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) { filename = this.download; });

    downloadSavedCropPlanBrief(plan, farm, field);

    expect(create).toHaveBeenCalledOnce();
    const blob = create.mock.calls[0] && (create.mock as unknown as { calls: [[Blob]] }).calls[0][0];
    expect(blob).toBeInstanceOf(Blob);
    expect(blob.type).toBe('text/markdown;charset=utf-8');
    expect(await blob.text()).toContain('Saved crop plan: Beans');
    expect(filename).toBe('north-farm-beans-season-b.md');
    expect(click).toHaveBeenCalledOnce();

    if (createDescriptor) Object.defineProperty(URL, 'createObjectURL', createDescriptor); else Reflect.deleteProperty(URL, 'createObjectURL');
    if (revokeDescriptor) Object.defineProperty(URL, 'revokeObjectURL', revokeDescriptor); else Reflect.deleteProperty(URL, 'revokeObjectURL');
  });
});
