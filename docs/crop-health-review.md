# Crop health reports and reviewer follow-up

The React farmer workspace includes private crop-health case reporting. It records a farmer's selected farm, optional active field and crop plan, supported crop, symptom description, optional first-noticed date, optional affected plant parts and whether the issue appears to be spreading, and one photo. Submission shows upload progress, a clear failure message when it cannot be saved, and a short report reference after the API confirms persistence. Cases are stored in the CropPulse database. Maize photos receive experimental model-ranked candidate labels; these are not diagnoses or treatment recommendations. See [crop-disease model setup and limitations](crop-disease-model.md).

## Case lifecycle

`submitted -> under_review -> awaiting_farmer -> under_review -> resolved` (shown to farmers as **Closed**)

- A farmer may submit a reply only while the case is `awaiting_farmer`; the reply returns it to `under_review`.
- A reviewer may start a submitted case, send a private update, request more information, or resolve a case under review.
- Resolved cases cannot be reopened in this phase. A resolved case is a workflow state and does not indicate a confirmed disease diagnosis.
- Review updates include the reviewer identity when available and a server timestamp. A reviewer may mark an update as a **provisional observation**. Confirmed diagnoses are not supported because reviewer qualifications are not verified by this application.

The farmer sees reports only for farms they own. Active reviewers see cases only in districts currently assigned to their reviewer account. The district assignment and account status are checked on each list, detail, update, and photo request. Existing administrators can access the reviewer endpoints according to the current `require_reviewer` policy, matching existing activity review access; no new role or permissions were introduced.

## Photo privacy and validation

- Accepted formats: JPEG, PNG, and WebP. The backend decodes and verifies image contents; file names and claimed MIME types alone are not trusted.
- The incoming file limit is 5 MiB; dimensions are limited to 4096 by 4096 pixels and 12 million total pixels.
- Images are orientation-corrected, converted to JPEG, and re-encoded without preserving EXIF metadata. User filenames are not stored.
- Normalized image bytes and metadata are stored in the relational database, not in a public static directory. Photo endpoints return private, non-cacheable responses and require an authorized farmer or reviewer session.
- This database-BLOB storage is suitable only for the current small local/pilot scope. Production scale needs a private object store, retention/deletion policy, backup capacity, encryption-at-rest review, upload throttling, and malware/security operations.

## API

- `GET /v1/crop-health/crops` returns the supported crop names for an authenticated farmer.
- `POST /v1/crop-health/cases` accepts multipart form data and a verified image upload.
- `GET /v1/crop-health/cases` and `GET /v1/crop-health/cases/{id}` return the farmer's own reports and updates.
- `GET /v1/crop-health/cases/{id}/photo` streams the photo only after owner or district-scope authorization.
- `POST /v1/crop-health/cases/{id}/reply` lets the owner answer a reviewer information request.
- `GET /v1/reviewer/crop-health/cases` and `GET /v1/reviewer/crop-health/cases/{id}` return cases within reviewer authorization.
- `POST /v1/reviewer/crop-health/cases/{id}/updates` starts review, requests information, sends a private update, or resolves a case.

The additive Alembic migration `0009_crop_health_cases` adds case and update tables. Apply it to a development database only after backup with `python -m alembic upgrade head`. Production migration and deployment require a separately reviewed release procedure.

Migration `0010_crop_health_context` adds nullable `plant_parts_affected` and `spreading` fields. Existing reports remain valid and display these values as not provided.

## Limitations

Reports are farmer observations. CropPulse does not identify plant diseases from images, confirm diagnoses, send notifications, or provide treatment/pesticide prescriptions. Reviewers are identified as CropPulse reviewers; their professional credentials are not verified. Follow-up is visible in the React case history only. The previous Streamlit pest report remains a separate session-only feature and is not migrated or connected to these persistent cases.

See [crop-disease AI readiness](crop-disease-ai-readiness.md) for the future model, dataset, evaluation, and reviewed-guidance requirements. AI status is currently unavailable; reports remain usable without a model.
