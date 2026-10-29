"""Import curated rainfall outlooks after the source PDF bulletin archive."""
from backend.db import get_session_factory
from utils.weather_bulletin_data import import_records


def main():
    with get_session_factory()() as db:
        count = import_records(db)
    print(f"Imported or refreshed {count} source-linked weather outlook records.")


if __name__ == "__main__":
    main()
