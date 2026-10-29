# Crop disease AI readiness

## Current state

CropPulse stores private farmer reports and provides a district-scoped reviewer workflow. The `CropPulseAI` PlantVillage dataset and MobileNetV2 model are now called for maize reports only. The API stores model-ranked candidates separately from farmer observations and reviewer decisions. Raw scores are uncalibrated; outputs are not diagnoses, and no Rwanda-approved treatment catalogue is connected. Reviewers may record a provisional observation and private response. Their credentials are not verified by CropPulse. See [integration details and limits](crop-disease-model.md).

## Future model integration contract

Model inference runs behind a backend-only provider interface; farmer images are not sent to a third-party inference service. Extension to additional crops must:

- Accept only an authenticated, authorized report image and its selected crop.
- Declare its model identifier, immutable version, supported crops, and supported condition classes.
- Return zero or more candidates only for supported classes, clearly document raw score semantics, and return an explicit unavailable/unsupported result when it cannot screen.
- Store model output separately from farmer observations and human review, including model/version and inference time. A prediction must never set a confirmed diagnosis or bypass reviewer follow-up.
- Be possible to disable without affecting report submission, private images, or reviewer case history.
- Record errors without logging images, credentials, raw personal data, or prediction content unnecessarily.

The current API exposes an `ai_screening` field. Do not surface uncalibrated scores as confidence or labels as diagnoses.

## Rwanda-relevant dataset plan

Before training or adapting a model, establish a governed collection with:

- The supported crop species and explicit healthy, confirmed-condition, uncertain, lookalike, pest-damage, nutrient-stress, weather-damage, and non-crop examples.
- Original image, capture date, consent record, source, crop/variety where known, growth stage, and optional district/field context only when consented and access-controlled.
- Labels reviewed by qualified agricultural specialists, label provenance, disagreement handling, and an `uncertain` option. Keep reviewer identity and qualifications in controlled audit records, not public outputs.
- Photo-quality checks, duplicate and near-duplicate detection, privacy review, EXIF/location stripping for display, and a documented retention/deletion policy.
- Class balance reporting and separation by farm/photographer and time/season so related images cannot leak between training, validation, and test sets.
- Field representation across Rwanda districts, seasons, varieties, devices, lighting, backgrounds, symptom severity, and mixed/early-stage conditions. A convenient public dataset is not a substitute for consented Rwanda field evaluation.

Do not train on farmer-submitted CropPulse images unless there is explicit, documented permission for that use, a defined retention policy, and suitable governance. Production reports must remain separate from model-training data by default.

## Evaluation and release gate

Evaluation must use a locked, independently labeled Rwandan field test set separated by farm and collection period. Report per-class precision and recall, confusion between similar conditions, false-positive and false-negative review, performance by crop and field conditions, sensitivity to poor/blurred/occluded photos, unsupported crop behavior, and uncertainty/abstention rates. Show sample counts and confidence intervals with each metric. Do not set targets after viewing the test set or claim accuracy based only on laboratory-style public images.

Require qualified local review of error cases and a controlled pilot with a human escalation path. The model must abstain when the crop, photo quality, or class is unsupported or uncertain. A model release does not make the output a confirmed diagnosis.

## Agricultural guidance and advice

Keep treatment advice independent from raw model inference. Any future guidance entry must have an identified source organization/reference and version/date, supported crop and condition, geographic applicability, reviewer/approver, safe preventive or nonchemical measures where supported, restrictions, and conditions requiring expert follow-up. Do not recommend a pesticide product, dose, schedule, or pre-harvest interval from a photo classifier alone. If no approved local guidance exists, tell the farmer that a reviewer must follow up.

Use integrated pest-management principles and applicable Rwanda guidance. Have the responsible agricultural authority or qualified local specialists approve advice before it is shown as CropPulse guidance.

## Current farmer and reviewer workflow

The farmer selects an owned farm and crop, provides symptoms and optional context, and submits a photo. CropPulse stores a private case and returns a report reference. Maize photos also receive experimental model-ranked candidates; unsupported crops and model failures still proceed to the reviewer workflow without screening. Authorized reviewers can inspect the case, request information, append a response, and close the workflow. Image authorization is checked server-side on every request. No chemical-treatment recommendation is produced.
