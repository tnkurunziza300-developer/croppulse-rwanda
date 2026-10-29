# Crop image screening model

## What is connected

The farmer's **Crop health reports** page sends the photo through the existing private report API. The backend normalizes the image, stores the private report, then runs `CropPulseAI/models/best_model.keras` and stores the result on that same report. The farmer and district-authorized reviewer see the same screening block in the report details. Screening failure never prevents report submission.

This integration is in the persistent React/API workflow only. The legacy Streamlit pest-report form still stores temporary session observations and does not run the model; consolidating that legacy form into React is separate work.

The API currently screens **maize only**. It ranks the four maize labels bundled in `CropPulseAI/models/class_names.json`. Other crops receive an explicit unsupported status while their report proceeds normally. Potato is intentionally held back: the bundled confusion-matrix artifact has weak performance on the healthy potato class, so it is not exposed pending better evaluation. This does not mean that the model has been validated for Rwanda or for field photographs.

The displayed values are uncalibrated model scores, not probabilities. Labels are candidates for human review, not diagnoses. A source-linked deterministic guidance panel offers general follow-up steps and identity references; it does not generate disease diagnoses or prescribe medicines, pesticide rates, or other treatments. See [Crop-health guidance library](crop-health-guidance-library.md) for source scope, licensing boundaries, and limitations. A reviewer must assess the case; reviewer status does not establish professional qualifications.

## Setup

1. Keep `CropPulseAI/models/best_model.keras` and `CropPulseAI/models/class_names.json` at those project-relative paths. The trained model and labels are part of the application assets.
2. Install the backend dependencies from the project root: `python -m pip install -r requirements.txt`. The model runtime is CPU-only TensorFlow (`tensorflow-cpu`). The first screening request loads the model; CPU inference may add noticeable delay.
3. Apply the additive migration with the project's usual database migration procedure: `python -m alembic upgrade head`. Revision `0011_crop_health_ai_screening` adds five optional screening fields to existing private reports. Old reports remain `not_run`.
4. Restart FastAPI. If TensorFlow or either artifact is unavailable, screening is marked unavailable and report submission continues.

Do not delete report images, back up, or copy model artifacts into a public location. The model is loaded by the backend and no image is sent to an external inference provider.

## Data, model, and licensing provenance

The included download script fetches the `mohanty/PlantVillage` dataset from Hugging Face; the included training pipeline builds a 38-class MobileNetV2 classifier from those images. The bundled Hugging Face dataset page identifies the dataset as CC BY-SA 3.0 and cites Mohanty, Hughes, and Salathé, *Using deep learning for image-based plant disease detection* (2016). Attribution and share-alike obligations may apply to dataset adaptations and possibly this trained model; the local dataset metadata does not record a license or exact immutable source revision. Review the upstream license, derivative-model status, and intended commercial deployment with qualified counsel before distributing the model or using it in a commercial service. Keep source attribution and license notices with distributions.

Sources: [Hugging Face PlantVillage dataset card and license](https://huggingface.co/datasets/mohanty/PlantVillage), [original PlantVillage dataset repository](https://github.com/spMohanty/PlantVillage-Dataset), [research article DOI](https://doi.org/10.3389/fpls.2016.01419).

## Known limits and next work

- PlantVillage images are controlled leaf images, not verified Rwanda field photos. The model has not been locally field-tested, externally validated, calibrated, or assessed for out-of-distribution rejection.
- The saved split is an image-level random split. Related leaves/backgrounds may cross splits, so the bundled metrics cannot establish real-world accuracy. The confusion matrix is an existing artifact, not a fresh independently reproducible evaluation.
- Only maize is currently exposed. Other supported CropPulse crops need suitable class coverage and Rwanda-specific testing before screening is enabled. Potato is excluded because of weak bundled healthy-class results.
- There is no verified, Rwanda-specific disease treatment knowledge base. The general guidance panel is not a treatment knowledge base; do not infer chemical or disease-specific agronomic advice from the class label.
- Before operational use, create farmer-consented Rwanda field evaluation data, split by plant/field/site/time to prevent leakage, test unknown/healthy cases, calibrate and set abstention thresholds, obtain qualified agronomist review, and add a sourced, locally approved treatment knowledge base with safety constraints.
- The source image dataset is large. Measure packaged model/data sizes for the target deployment; the web frontend must not receive the model file.
