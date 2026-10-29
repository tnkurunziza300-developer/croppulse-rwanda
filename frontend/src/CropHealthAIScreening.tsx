import type { CropHealthAIScreening as Screening } from './api';

const labels: Record<string, string> = {
  candidate_screening: 'Experimental candidate screening',
  unsupported_crop: 'No model coverage for this crop',
  unavailable: 'Screening unavailable',
  not_run: 'Screening not run',
};

export function CropHealthAIScreening({ screening }: { screening: Screening }) {
  return <section className="crop-ai-screening" aria-label="Experimental crop image screening">
    <span className="eyebrow">MODEL ASSISTANCE · NOT A DIAGNOSIS</span>
    <h3>{labels[screening.status] ?? 'Screening status unavailable'}</h3>
    <p>{screening.message}</p>
    {screening.candidates.length > 0 && <>
      <p><strong>Model-ranked labels for review</strong></p>
      <ol>{screening.candidates.map((candidate) => <li key={candidate.class_name}>
        <span>{candidate.label}</span><span>{(candidate.model_score * 100).toFixed(1)}% raw score</span>
      </li>)}</ol>
      <small>{screening.score_description} {screening.generated_at ? `Screened ${new Date(screening.generated_at).toLocaleString()}.` : ''}</small>
    </>}
    {screening.guidance && <div className="crop-ai-guidance">
      <h4>{screening.guidance.title}</h4>
      <ul>{screening.guidance.steps.map((step, index) => <li key={index}>{step}</li>)}</ul>
      <p className="crop-ai-treatment-notice">{screening.guidance.treatment_notice}</p>
      {screening.guidance.candidates.length > 0 && <div>
        <strong>Names for human review</strong>
        <ul>{screening.guidance.candidates.map((candidate) => <li key={candidate.name}>
          {candidate.name}{candidate.organism && <> — <i>{candidate.organism}</i>{candidate.code && ` (${candidate.code})`}</>}
          {candidate.url && <> · <a href={candidate.url} target="_blank" rel="noreferrer">EPPO reference</a></>}
        </li>)}</ul>
      </div>}
      <details><summary>Sources and limits</summary><ul>{screening.guidance.sources.map((source) => <li key={source.url}>
        <a href={source.url} target="_blank" rel="noreferrer">{source.name}</a> — {source.scope}
      </li>)}</ul><small>Guidance library version {screening.guidance.version}. Source links checked 21 October 2026.</small></details>
    </div>}
  </section>;
}
