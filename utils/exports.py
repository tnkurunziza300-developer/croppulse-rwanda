from datetime import date
import pandas as pd


def to_csv_bytes(df: pd.DataFrame, origin=None) -> bytes:
    if origin and "data_origin" not in df.columns:
        df = df.assign(data_origin=origin)  # persistent disclosure travels with every export
    return df.to_csv(index=False).encode("utf-8")


def build_brief(title, geography, crop, period, findings, data_source, limitations) -> str:
    lines = [f"# {title}", f"*Generated {date.today().isoformat()} from a deterministic template (no AI model).*", "",
             f"**Geography:** {geography}  \n**Crop:** {crop}  \n**Analysis period:** {period}", "", "## Key findings"]
    lines += [f"- {f}" for f in findings] or ["- No findings selected."]
    lines += ["", "## Method", "Area-weighted yield (production ÷ area); rule-based priority categories (see Methodology page).",
              "", f"## Data source\n{data_source}", "", "## Limitations"] + [f"- {l}" for l in limitations]
    lines += ["", "## Suggested follow-up", "- Verify with additional agricultural records.", "- Consult district agricultural officers.",
              "- Examine rainfall/climate records if available.", "",
              "> This brief supports decisions but does not replace expert judgment. Associations are not causes."]
    return "\n".join(lines)


def build_decision_brief(out, district, season, inputs, status) -> str:
    L = [f"# Crop decision brief: {district}, Season {season}", f"*Generated {date.today().isoformat()} (deterministic template; not an official or government document).*", "",
         f"**Data status:** {status.get('message', '')}", f"**Growing conditions provided:** {inputs}", "", "## Ranked crops"]
    for r in [x for x in out["results"] if x["rank"]]:
        L += [f"### {r['rank']}. {r['crop']}: {r['status']}", f"- Evidence basis: {r['evidence_basis']}", f"- Planting: {r['window']}", f"- Source of planting guidance: {r['source']}"]
        L += [f"- Why: {x}" for x in r["reasons"]] + [f"- Risk/unknown: {x}" for x in r["risks"]] + [f"- Evidence: {x}" for x in r["evidence"]]
        L += ([f"- {r['weak']}"] if r["weak"] else []) + ["- Next steps: " + " ".join(r["next_steps"]), ""]
    ex = [x for x in out["results"] if not x["rank"]]
    if ex:
        L += ["## Excluded by current provisional rules"] + [f"- {x['crop']}: {' '.join(x['violations'])}" for x in ex] + [""]
    L += ["## Not assessed"] + [f"- {x}" for x in out["cannot_assess"]]
    L += ["", "## Method", "Provisional CropPulse guide category for the district's broad grouping, then crop name. NISR historical observations are descriptive context only and never affect suitability or rank. "
          "This ordering is not a probability of success. Synthetic demonstration data is never used in ranking.", "",
          "> This brief supports decisions but does not replace expert judgment. Associations are not causes."]
    return "\n".join(L)
