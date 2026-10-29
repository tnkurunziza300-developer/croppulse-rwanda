
import sys
import json
import numpy as np
import tensorflow as tf
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "models" / "best_model.keras"
CLASS_NAMES_PATH = ROOT / "models" / "class_names.json"
IMAGE_SIZE = (160, 160)

if len(sys.argv) < 2:
    print('Usage: python predict_image.py "path_to_image.jpg"')
    sys.exit(1)

image_path = Path(sys.argv[1]).expanduser()

print("Loading model...")
model = tf.keras.models.load_model(MODEL_PATH)

with open(CLASS_NAMES_PATH, "r", encoding="utf-8") as f:
    class_names = json.load(f)

try:
    image_bytes = tf.io.read_file(str(image_path))
    image_array = tf.io.decode_image(image_bytes, channels=3, expand_animations=False)
    image_array.set_shape([None, None, 3])
    image_array = tf.image.resize(image_array, IMAGE_SIZE)
    image_array = tf.keras.applications.mobilenet_v2.preprocess_input(
        image_array
    )
    image_array = np.expand_dims(image_array, axis=0)

    probabilities = model.predict(image_array, verbose=0)[0]
    top_indices = np.argsort(probabilities)[::-1][:3]

    print("\nTop predictions:")
    for rank, index in enumerate(top_indices, start=1):
        print(
            f"{rank}. {class_names[index]} "
            f"- {probabilities[index] * 100:.2f}%"
        )

except (OSError, ValueError) as error:
    print(f"Could not process image: {error}")
    sys.exit(1)
