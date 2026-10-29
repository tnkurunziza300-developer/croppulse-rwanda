
from pathlib import Path
import json
import pandas as pd
import tensorflow as tf

from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input

# -----------------------------
# 1. Configuration
# -----------------------------
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "models"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

IMAGE_SIZE = (160, 160)
BATCH_SIZE = 16
EPOCHS = 5
SEED = 42

tf.keras.utils.set_random_seed(SEED)

# -----------------------------
# 2. Load CSV manifests
# -----------------------------
train_df = pd.read_csv(DATA_DIR / "train.csv")
val_df = pd.read_csv(DATA_DIR / "validation.csv")

def portable_image_path(value):
    path = Path(str(value))
    if path.is_absolute() and path.is_file():
        return str(path)
    if not path.is_absolute() and (ROOT / path).is_file():
        return str((ROOT / path).resolve())
    # Resolve manifests created on the original workstation by their known
    # dataset-relative suffix without changing the saved training split.
    parts = path.parts
    if "PlantVillage_Images" in parts:
        relative = Path(*parts[parts.index("PlantVillage_Images"):])
        candidate = ROOT / relative
        if candidate.is_file():
            return str(candidate.resolve())
    return str(path)

train_df["filepath"] = train_df["filepath"].map(portable_image_path)
val_df["filepath"] = val_df["filepath"].map(portable_image_path)

class_names = sorted(train_df["label"].unique())
num_classes = len(class_names)
class_to_index = {name: i for i, name in enumerate(class_names)}

if num_classes != 38:
    raise ValueError(f"Expected 38 classes, found {num_classes}")

if set(val_df["label"].unique()) != set(class_names):
    raise ValueError("Training and validation classes do not match.")

# Save class names for future predictions.
with open(OUTPUT_DIR / "class_names.json", "w", encoding="utf-8") as f:
    json.dump(class_names, f, indent=2)

print("Classes:", num_classes)
print("Training images:", len(train_df))
print("Validation images:", len(val_df))

# -----------------------------
# 3. Build image pipelines
# -----------------------------
def load_image(path, label):
    image_bytes = tf.io.read_file(path)
    image = tf.io.decode_image(
        image_bytes,
        channels=3,
        expand_animations=False,
    )
    image.set_shape([None, None, 3])
    image = tf.image.resize(image, IMAGE_SIZE)
    image = preprocess_input(image)
    return image, label

def make_dataset(df, training=False):
    labels = df["label"].map(class_to_index).to_numpy()

    ds = tf.data.Dataset.from_tensor_slices(
        (df["filepath"].to_numpy(), labels)
    )

    if training:
        ds = ds.shuffle(
            buffer_size=min(len(df), 5000),
            seed=SEED,
            reshuffle_each_iteration=True,
        )

    ds = ds.map(
        load_image,
        num_parallel_calls=tf.data.AUTOTUNE,
    )

    ds = ds.batch(BATCH_SIZE)
    ds = ds.prefetch(tf.data.AUTOTUNE)
    return ds

train_ds = make_dataset(train_df, training=True)
val_ds = make_dataset(val_df)

# -----------------------------
# 4. Load pretrained backbone
# -----------------------------
base_model = MobileNetV2(
    input_shape=(*IMAGE_SIZE, 3),
    include_top=False,
    weights="imagenet",
)

base_model.trainable = False

# -----------------------------
# 5. Build classifier
# -----------------------------
inputs = keras.Input(shape=(*IMAGE_SIZE, 3))

x = base_model(inputs, training=False)
x = layers.GlobalAveragePooling2D()(x)
x = layers.Dropout(0.25)(x)

outputs = layers.Dense(
    num_classes,
    activation="softmax",
)(x)

model = keras.Model(inputs, outputs)

model.compile(
    optimizer=keras.optimizers.Adam(learning_rate=0.001),
    loss="sparse_categorical_crossentropy",
    metrics=["accuracy"],
)

model.summary()

# -----------------------------
# 6. Train and save best model
# -----------------------------
callbacks = [
    keras.callbacks.ModelCheckpoint(
        filepath=str(OUTPUT_DIR / "best_model.keras"),
        monitor="val_accuracy",
        save_best_only=True,
        mode="max",
        verbose=1,
    ),
    keras.callbacks.EarlyStopping(
        monitor="val_loss",
        patience=2,
        restore_best_weights=True,
        verbose=1,
    ),
]

history = model.fit(
    train_ds,
    validation_data=val_ds,
    epochs=EPOCHS,
    callbacks=callbacks,
)

# Save the final model as well.
model.save(OUTPUT_DIR / "final_model.keras")

print("\nTraining finished.")
print("Best model:", OUTPUT_DIR / "best_model.keras")
print("Final model:", OUTPUT_DIR / "final_model.keras")
print("Class labels:", OUTPUT_DIR / "class_names.json")
