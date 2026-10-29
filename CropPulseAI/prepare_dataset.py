
from pathlib import Path
import pandas as pd
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parent
DATASET_DIR = ROOT / "PlantVillage_Images" / "raw" / "color"
OUTPUT_DIR = ROOT / "data"
SEED = 42

# Supported image formats
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}

def main():
    if not DATASET_DIR.is_dir():
        raise FileNotFoundError(
            f"Dataset folder not found: {DATASET_DIR.resolve()}"
        )

    records = []

    for class_dir in sorted(DATASET_DIR.iterdir()):
        if not class_dir.is_dir():
            continue

        for image_path in sorted(class_dir.iterdir()):
            if image_path.is_file() and image_path.suffix.lower() in IMAGE_EXTENSIONS:
                records.append({
                    # Keep manifests portable when the project folder moves.
                    "filepath": image_path.relative_to(ROOT).as_posix(),
                    "label": class_dir.name,
                })

    df = pd.DataFrame(records)

    if df.empty:
        raise ValueError("No supported image files were found.")

    if df["label"].nunique() != 38:
        raise ValueError(
            f"Expected 38 classes, found {df['label'].nunique()}."
        )

    # First reserve 15% for testing.
    train_val, test = train_test_split(
        df,
        test_size=0.15,
        random_state=SEED,
        stratify=df["label"],
    )

    # Reserve 15% of the total dataset for validation.
    train, validation = train_test_split(
        train_val,
        test_size=0.15 / 0.85,
        random_state=SEED,
        stratify=train_val["label"],
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    train.to_csv(OUTPUT_DIR / "train.csv", index=False)
    validation.to_csv(OUTPUT_DIR / "validation.csv", index=False)
    test.to_csv(OUTPUT_DIR / "test.csv", index=False)

    print("Dataset preparation complete!")
    print(f"Classes: {df['label'].nunique()}")
    print(f"Total images: {len(df):,}")
    print(f"Training images: {len(train):,}")
    print(f"Validation images: {len(validation):,}")
    print(f"Test images: {len(test):,}")
    print(f"CSV manifests saved in: {OUTPUT_DIR.resolve()}")

    print("\nClass counts:")
    print(pd.crosstab(
        df["label"],
        df["label"].map(
            lambda label: (
                "train" if label in set(train["label"])
                else "other"
            )
        )
    ).head())

if __name__ == "__main__":
    main()
