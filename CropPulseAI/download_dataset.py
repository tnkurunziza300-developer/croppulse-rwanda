
from datasets import load_dataset

print("Downloading PlantVillage dataset...")

dataset = load_dataset(
    "mohanty/PlantVillage",
    revision="refs/convert/parquet"
)

print("\nDataset downloaded successfully!")
print(dataset)

for split_name, split_data in dataset.items():
    print(f"\nSplit: {split_name}")
    print("Columns:", split_data.column_names)
    print("Number of records:", len(split_data))

dataset.save_to_disk("PlantVillage")

print("\nDataset saved in the PlantVillage folder!")
