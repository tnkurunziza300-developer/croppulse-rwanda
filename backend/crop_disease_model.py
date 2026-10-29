"""Private, experimental PlantVillage image screening for crop-health reports.

This returns within-crop model-ranked candidates only. Scores are raw softmax
outputs, not calibrated probabilities, diagnoses, or treatment recommendations.
"""
from functools import lru_cache
from hashlib import sha256
from io import BytesIO
import json
import logging
from pathlib import Path
from threading import Lock


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "CropPulseAI" / "models" / "best_model.keras"
CLASS_NAMES_PATH = ROOT / "CropPulseAI" / "models" / "class_names.json"
IMAGE_SIZE = (160, 160)
MODEL_NAME = "CropPulseAI MobileNetV2 PlantVillage"
SUPPORTED_CLASS_PREFIXES = {
    "Maize": "Corn_(maize)___",
}
_prediction_lock = Lock()
_logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_model_bundle():
    import tensorflow as tf

    class_names = json.loads(CLASS_NAMES_PATH.read_text(encoding="utf-8"))
    if not isinstance(class_names, list) or len(class_names) != 38 or len(set(class_names)) != 38:
        raise ValueError("The model class-name manifest must contain 38 unique classes.")
    model = tf.keras.models.load_model(MODEL_PATH, compile=False, safe_mode=True)
    if model.input_shape[-3:] != (160, 160, 3) or model.output_shape[-1] != len(class_names):
        raise ValueError("The model input or output shape does not match its manifest.")
    digest = sha256(MODEL_PATH.read_bytes()).hexdigest()
    return tf, model, class_names, digest


def screen_crop_image(crop: str, image_bytes: bytes) -> dict:
    """Return an advisory model screen without allowing inference to block a report."""
    prefix = SUPPORTED_CLASS_PREFIXES.get(crop)
    if prefix is None:
        return {
            "status": "unsupported_crop", "model_name": MODEL_NAME,
            "model_version": None, "generated_at": None, "candidates": [],
            "message": "This model has no disease classes for the selected crop. The report remains available for reviewer follow-up.",
        }
    try:
        tf, model, class_names, model_version = _load_model_bundle()
        class_indices = [i for i, name in enumerate(class_names) if name.startswith(prefix)]
        if len(class_indices) < 2:
            raise ValueError("The selected crop lacks both healthy and condition classes.")
        image = tf.io.decode_jpeg(image_bytes, channels=3)
        image = tf.image.resize(image, IMAGE_SIZE)
        image = tf.keras.applications.mobilenet_v2.preprocess_input(image)
        with _prediction_lock:
            scores = model(tf.expand_dims(image, axis=0), training=False).numpy()[0]
        if len(scores) != len(class_names):
            raise ValueError("The model output does not match its class-name manifest.")
        ranked = sorted(class_indices, key=lambda index: float(scores[index]), reverse=True)[:3]
        candidates = [{
            "class_name": class_names[index],
            "label": class_names[index].split("___", 1)[-1].replace("_", " "),
            "model_score": round(float(scores[index]), 6),
        } for index in ranked]
        return {
            "status": "candidate_screening", "model_name": MODEL_NAME,
            "model_version": model_version, "generated_at": None,
            "score_description": "Uncalibrated model score; not a probability or confirmed diagnosis.",
            "candidates": candidates,
            "message": "Experimental PlantVillage screening only, not a confirmed diagnosis. A CropPulse reviewer must assess this report; do not use this result to choose treatment.",
        }
    except Exception as exc:  # Reports must remain usable if model inference is unavailable.
        _logger.warning("Crop-health model screening unavailable (%s).", type(exc).__name__)
        return {
            "status": "unavailable", "model_name": MODEL_NAME,
            "model_version": None, "generated_at": None, "candidates": [],
            "message": "Automated screening is unavailable. The report was still saved for reviewer follow-up.",
        }
