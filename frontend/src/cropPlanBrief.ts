import type { CropPlan, Farm, FarmField } from './api';

type JsonObject = Record<string, unknown>;

function objectValue(value: unknown): JsonObject | null {
  return value !== null && typeof value === 'object' && !Array.isArray(value) ? value as JsonObject : null;
}

function safeText(value: unknown, fallback = 'Not recorded'): string {
  if (typeof value !== 'string' && typeof value !== 'number' && typeof value !== 'boolean') return fallback;
  const text = [...String(value)].map((character) => {
    const codePoint = character.codePointAt(0) ?? 0;
    return codePoint <= 0x1f || codePoint === 0x7f ? ' ' : character;
  }).join('').trim();
  return text || fallback;
}

function md(value: unknown, fallback?: string): string {
  const text = safeText(value, fallback).replace(/</g, '&lt;').replace(/>/g, '&gt;');
  // Values are placed after fixed labels/headings and newlines are removed, so
  // list/ordered-list markers are not at line start. Keep dates and URLs legible.
  const markdownPunctuation = new Set(['\\', '`', '*', '_', '{', '}', '[', ']', '(', ')', '#', '+', '!', '|']);
  return [...text].map((character) => markdownPunctuation.has(character) ? `\\${character}` : character).join('');
}

function list(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function linesFor(label: string, value: unknown): string[] {
  return list(value).filter((item) => typeof item === 'string' && item.trim())
    .map((item) => `- **${label}:** ${md(item)}`);
}

export function buildSavedCropPlanBrief(
  plan: CropPlan,
  farm: Farm,
  field?: FarmField,
  generatedAt = new Date().toISOString(),
): string {
  const saved = objectValue(plan.plan) ?? {};
  const snapshot = objectValue(saved.recommendation_snapshot);
  const conditions = objectValue(snapshot?.conditions);
  const history = objectValue(snapshot?.history);
  const evidence = Array.isArray(plan.evidence) ? plan.evidence : [];
  const notes = typeof saved.farmer_notes === 'string' ? saved.farmer_notes.trim() : '';

  const lines = [
    `# Saved crop plan: ${md(plan.crop)} — Season ${md(plan.season)}`,
    `Generated ${md(generatedAt)}. This is a copy of the saved plan, not an official document or new agronomic assessment.`,
    '',
    '## Farm and location',
    `- Farm: ${md(farm.name)}`,
    `- District: ${md(plan.district || farm.district)}`,
    `- Sector: ${md(farm.sector, 'Not recorded')}`,
    `- Field: ${md(field?.name, plan.field_id ? 'Saved field name unavailable' : 'Farm-level plan')}`,
    `- Farm area: ${farm.area_ha == null ? 'Not recorded' : `${md(farm.area_ha)} ha (farmer recorded)`}`,
    `- Planned crop area: ${plan.area_ha == null ? 'Not recorded' : `${md(plan.area_ha)} ha (farmer planned)`}`,
    '',
    '## Saved plan details',
    `- Crop: ${md(plan.crop)}`,
    `- Season: ${md(plan.season)}`,
    `- Plan status: ${md(plan.status)}`,
    `- Verification status: ${md(plan.verification)}`,
    `- Intended planting date: ${md(plan.planting_date)}`,
    `- Actual planting date: ${md(plan.actual_planting_date, 'Not recorded')}`,
    `- Farmer notes (not verified): ${md(notes, 'None')}`,
    '',
    '## Evidence attached to this saved plan',
  ];

  if (evidence.length) {
    for (const item of evidence) {
      lines.push(`### ${md(item.claim)}`,
        `- Status recorded with plan: ${md(item.verification_status)}`,
        `- Source: ${md(item.source_name)}${item.source_organization ? ` — ${md(item.source_organization)}` : ''}`,
        `- Source reference: ${md(item.source_url ?? item.source_identifier ?? item.source_name)}`,
        `- Publication / retrieval date: ${md(item.publication_date)} / ${md(item.retrieval_date)}`,
        `- Evidence period / units: ${md(item.evidence_period)} / ${md(item.units)}`,
        `- Limitations: ${md(item.limitations)}`);
    }
    lines.push('', 'Evidence status and source details are copied from the saved record; this download does not independently revalidate them.');
  } else {
    lines.push('No independently verified evidence records are attached to this plan. Recommendation context, if present, is provisional and is listed separately.');
  }

  if (snapshot) {
    lines.push('', '## Saved recommendation context (if available)',
      `- Saved status: ${md(snapshot.status)}`,
      `- Evidence basis: ${md(snapshot.evidence_basis)}`,
      `- Provisional planting window: ${md(snapshot.planting_window)}`,
      `- Guidance source note: ${md(snapshot.guidance_source)}`,
      `- Context generated: ${md(snapshot.generated_at)}`,
      `- Snapshot note: ${md(snapshot.snapshot_status)}`,
      `- Ranking method: ${md(snapshot.ranking_method ?? conditions?.ranking_method)}`,
      ...linesFor('Reason', snapshot.reasons),
      ...linesFor('Risk / unknown', snapshot.risks),
      ...linesFor('Evidence note', snapshot.evidence));

    if (conditions) {
      lines.push('', '### Conditions saved with the comparison',
        `- District / season: ${md(conditions.district)} / ${md(conditions.season)}`,
        `- Elevation: ${md(conditions.elevation_m, 'Unknown')} m`,
        `- Irrigation: ${md(conditions.irrigation)}`,
        `- Water availability: ${md(conditions.water_availability)}`,
        `- NISR statistics state: ${md(conditions.statistics_status)}`,
        `- Statistics note: ${md(conditions.statistics_note)}`);
    }

    const years = list(history?.years);
    const yields = list(history?.yields);
    if (conditions?.statistics_status === 'validated' && years.length && years.length === yields.length) {
      lines.push('', '### Historical district yield context',
        'These historical district-level area/production calculations are context only. They are not a farm-specific estimate, forecast, suitability guarantee, or ranking input.');
      years.forEach((year, index) => {
        const value = yields[index];
        if (typeof year === 'number' && typeof value === 'number' && Number.isFinite(value)) {
          lines.push(`- ${md(year)}: ${md(value)} t/ha (historical district statistic)`);
        }
      });
      const sources = list(conditions.statistics_provenance).map(objectValue).filter((item): item is JsonObject => item !== null);
      for (const source of sources) {
        lines.push(`- Source: ${md(source.publisher ?? source.title)}; period: ${md(source.reference_period)}; reference: ${md(source.source_url)}`);
      }
    } else if (history) {
      lines.push('', 'No validated historical statistic is included in this brief. Any unavailable or unvalidated context remains unknown.');
    }
  }

  lines.push('', '## Limitations',
    '- CropPulse recommendations and planting windows are provisional unless a saved evidence record states a narrower reviewed scope.',
    '- Historical NISR statistics, when present, describe past district observations; they do not establish crop suitability or predict an individual farm yield.',
    '- Farm, field, area, dates, and notes are farmer-recorded unless an attached evidence record states otherwise.',
    '- Coordinates are omitted from this downloadable brief.',
    '',
    '> Use this brief to review the saved record with a qualified local adviser. It is not a diagnosis, guarantee, or official agricultural recommendation.');

  return lines.join('\n');
}

export function downloadSavedCropPlanBrief(plan: CropPlan, farm: Farm, field?: FarmField): void {
  const content = buildSavedCropPlanBrief(plan, farm, field);
  const slug = `${farm.name}-${plan.crop}-season-${plan.season}`
    .normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
    .replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 80) || 'crop-plan';
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `${slug}.md`;
  anchor.hidden = true;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}
