
import json
import numpy as np
import pandas as pd
import tensorflow as tf
from pathlib import Path

from sklearn.metrics import classification_report, accuracy_score
from sklearn.metrics import confusion_matrix

# Project files
ROOT = Path(__file__).resolve().parent
TEST_CSV = ROOT / "data/test.csv"
MODEL_PATH = ROOT / "models/best_model.keras"
CLASS_NAMES_PATH = ROOT / "models/class_names.json"

IMAGE_SIZE = (160, 160)
BATCH_SIZE = 16

print("Loading trained model...")
model = tf.keras.models.load_model(MODEL_PATH)

with open(CLASS_NAMES_PATH, "r", encoding="utf-8") as f:
    class_names = json.load(f)

df = pd.read_csv(TEST_CSV)
def portable_image_path(value):
    path = Path(str(value))
    if path.is_absolute() and path.is_file():
        return str(path)
    if not path.is_absolute() and (ROOT / path).is_file():
        return str((ROOT / path).resolve())
    parts = path.parts
    if "PlantVillage_Images" in parts:
        candidate = ROOT / Path(*parts[parts.index("PlantVillage_Images"):])
        if candidate.is_file():
            return str(candidate.resolve())
    return str(path)

df["filepath"] = df["filepath"].map(portable_image_path)
print(f"Test images: {len(df)}")
print(f"Classes: {len(class_names)}")


def load_image(path, label):
    image = tf.io.read_file(path)
    image = tf.io.decode_image(
        image, channels=3, expand_animations=False
    )
    image.set_shape([None, None, 3])
    image = tf.image.resize(image, IMAGE_SIZE)
    image = tf.keras.applications.mobilenet_v2.preprocess_input(
        image
    )
    return image, label


label_to_index = {
    name: index for index, name in enumerate(class_names)
}

paths = df["filepath"].astype(str).to_numpy()
labels = df["label"].map(label_to_index)

if labels.isna().any():
    raise ValueError("Some test labels do not match class_names.json")

labels = labels.to_numpy(dtype=np.int32)

dataset = tf.data.Dataset.from_tensor_slices((paths, labels))
dataset = dataset.map(
    load_image, num_parallel_calls=tf.data.AUTOTUNE
)
dataset = dataset.batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)

print("\nEvaluating on unseen test images...")
results = model.evaluate(dataset, verbose=1, return_dict=True)

print("\nTest results:")
for metric, value in results.items():
    print(f"{metric}: {value:.4f}")

print("\nGenerating predictions...")
probabilities = model.predict(dataset, verbose=1)
predictions = np.argmax(probabilities, axis=1)

print(f"\nTest accuracy: {accuracy_score(labels, predictions):.4%}")
print("\nClassification report:")
print(
    classification_report(
        labels,
        predictions,
        labels=list(range(len(class_names))),
        target_names=class_names,
        zero_division=0,
    )
)

cm = confusion_matrix(
    labels, predictions, labels=list(range(len(class_names)))
)
np.savetxt(ROOT / "models" / "confusion_matrix.csv", cm, delimiter=",", fmt="%d")
print("\nConfusion matrix saved to models/confusion_matrix.csv")
