"""Import the reviewed source PDFs into the configured CropPulse database.

Run after applying migrations, from the project root:
  python -m utils.import_weather_bulletins
"""
from pathlib import Path

from backend.db import get_session_factory
from utils.weather_bulletins import import_bulletins


def main() -> None:
    source = Path(__file__).resolve().parents[1] / "data" / "raw" / "weather_climate"
    with get_session_factory()() as db:
        count = import_bulletins(db, source)
    print(f"Imported {count} source weather bulletins into the configured CropPulse database.")


if __name__ == "__main__":
    main()
