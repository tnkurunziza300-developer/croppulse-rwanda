"""Import and expose publisher-authored weather bulletin PDFs without parsing them."""
from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import WeatherBulletin

METEO = "Rwanda Meteorology Agency (METEO RWANDA)"
MONTHLY_PAGE = "https://www.meteorwanda.gov.rw/products/monthly-forecast"
SEASONAL_PAGE = "https://www.meteorwanda.gov.rw/products/seasonal-forecast"

# Curated from the source-file names and embedded PDF dates during the review.
# The source PDFs stay byte-for-byte intact; their maps/narrative are not
# converted into synthetic point observations.
BULLETINS = (
    ("April_2026_Monthly_climatology_and_rainfall_forecast_for_May_2026.pdf", "monthly", "May 2026 monthly weather forecast", "2026-05-05", "2026-05-01", "2026-05-31", MONTHLY_PAGE, "publisher-indicated; exact-original-match-pending"),
    ("August__2024_Monthly_climatology_and_rainfall_forecast_for_September_2024.pdf", "monthly", "September 2024 monthly weather forecast", "2024-09-06", "2024-09-01", "2024-09-30", MONTHLY_PAGE, "publisher-indicated; exact-original-match-pending"),
    ("December_2024_Monthly_climatology_and_rainfall_forecast_for_January_2025.pdf", "monthly", "January 2025 monthly weather forecast", "2025-01-06", "2025-01-01", "2025-01-31", MONTHLY_PAGE, "publisher-indicated; exact-original-match-pending"),
    ("February_2026_Monthly_climatology_and_rainfall_forecast_for_March_2026.pdf", "monthly", "March 2026 monthly weather forecast", "2026-03-05", "2026-03-01", "2026-03-31", MONTHLY_PAGE, "publisher-indicated; exact-original-match-pending"),
    ("January_2026_Monthly_climatology_and_rainfall_forecast_for_February_2026.pdf", "monthly", "February 2026 monthly weather forecast", "2026-02-05", "2026-02-01", "2026-02-28", MONTHLY_PAGE, "publisher-indicated; exact-original-match-pending"),
    ("July_2026_Monthly_climatology_and_rainfall_forecast_for_August_2026.pdf", "monthly", "August 2026 monthly weather forecast", "2026-08-05", "2026-08-01", "2026-08-31", MONTHLY_PAGE, "publisher-indicated; exact-original-match-pending"),
    ("June_2026_Monthly_climatology_and_rainfall_forecast_for_July_2026.pdf", "monthly", "July 2026 monthly weather forecast", "2026-07-05", "2026-07-01", "2026-07-31", MONTHLY_PAGE, "publisher-indicated; exact-original-match-pending"),
    ("March_2026_Monthly_climatology_and_rainfall_forecast_for_April_2026.__1_.pdf", "monthly", "April 2026 monthly weather forecast", "2026-04-06", "2026-04-01", "2026-04-30", "https://www.meteorwanda.gov.rw/fileadmin/user_upload/Meteorwanda/Monthly_Forecast/__2026/Weather_Forecast_for_April_2026.pdf", "publisher-indicated; official-product-pattern-cross-check"),
    # Filename says May 2025, but the PDF identifies bulletin No. 5/2026.
    ("May_2025_Monthly_climatology_and_rainfall_forecast_for_June_2026.pdf", "monthly", "June 2026 monthly weather forecast (source filename mismatch)", "2026-06-06", "2026-06-01", "2026-06-30", MONTHLY_PAGE, "publisher-indicated; filename-mismatch"),
    ("November_2024_Monthly_climatology_and_rainfall_forecast_for_December_2024.pdf", "monthly", "December 2024 monthly weather forecast", "2024-12-07", "2024-12-01", "2024-12-31", MONTHLY_PAGE, "publisher-indicated; exact-original-match-pending"),
    ("November_2025_Monthly_climatology_and_rainfall_forecast_for_December_2025.pdf", "monthly", "December 2025 monthly weather forecast", "2025-12-05", "2025-12-01", "2025-12-31", MONTHLY_PAGE, "publisher-indicated; exact-original-match-pending"),
    ("October__2024_Monthly_climatology_and_rainfall_forecast_for_November_2024.or.pdf", "monthly", "November 2024 monthly weather forecast", "2024-11-06", "2024-11-01", "2024-11-30", MONTHLY_PAGE, "publisher-indicated; exact-original-match-pending"),
    ("September_2026_Monthly_climatology_and_rainfall_forecast_for_October_2026_.pdf", "monthly", "October 2026 monthly weather forecast", "2026-10-05", "2026-10-01", "2026-10-31", MONTHLY_PAGE, "publisher-indicated; exact-original-match-pending"),
    ("SEASONAL_FORECAST_FOR_JUNE_TO_AUGUST_2025.pdf", "seasonal", "June–August 2025 seasonal forecast", "2025-06-11", "2025-06-01", "2025-08-31", "https://www.meteorwanda.gov.rw/index.php?eID=dumpFile&f=140725&t=f&token=199c0184b0b06d56fd79d1c215603c5ecf9490fa", "publisher-indicated; official-publication-cross-check"),
    ("SEASONAL_FORECAST_FOR_JUNE_TO_AUGUST_2026.pdf", "seasonal", "June–August 2026 seasonal forecast", "2026-06-09", "2026-06-01", "2026-08-31", SEASONAL_PAGE, "publisher-indicated; exact-original-match-pending"),
    ("SEASONAL_FORECAST_FOR_MARCH-MAY_2025.pdf", "seasonal", "March–May 2025 seasonal forecast", "2025-01-22", "2025-03-01", "2025-05-31", "https://www.meteorwanda.gov.rw/fileadmin/user_upload/Meteorwanda/Seasonal_Forecast/2025/MAM_2025_SEASONAL_FORECAST.pdf", "publisher-indicated; official-publication-cross-check"),
    ("SEASONAL_FORECAST_FOR_MARCH-MAY_2026.pdf", "seasonal", "March–May 2026 seasonal forecast", "2026-02-10", "2026-03-01", "2026-05-31", SEASONAL_PAGE, "publisher-indicated; exact-original-match-pending"),
    ("SEASONAL_FORECAST_FOR_SEPTEMBER-DECEMBER_2026.pdf", "seasonal", "September–December 2026 seasonal forecast", "2026-08-21", "2026-09-01", "2026-12-31", "https://www.meteorwanda.gov.rw/publications-1/news/news-detail?cHash=7e7904cef04ef17f7f4c3057981be5f9&tx_news_pi1%5Baction%5D=detail&tx_news_pi1%5Bcontroller%5D=News&tx_news_pi1%5Bnews%5D=82767", "publisher-indicated; official-announcement-cross-check"),
    ("SEASONAL_FORECAST_FOR_SEPTEMBER_TO_DECEMBER_2025.pdf", "seasonal", "September–December 2025 seasonal forecast", "2025-08-29", "2025-09-01", "2025-12-31", "https://meteorwanda.gov.rw/fileadmin/user_upload/SOND_2025_SEASONAL_FORECAST.pdf", "publisher-indicated; official-publication-cross-check"),
)


def import_bulletins(db: Session, source_dir: Path) -> int:
    """Idempotently store original PDFs and reviewed source metadata in the DB."""
    source_dir = Path(source_dir)
    prepared = []
    for (filename, category, title, issue, valid_from, valid_to,
         source_url, provenance) in BULLETINS:
        path = source_dir / filename
        if not path.is_file():
            raise FileNotFoundError(f"Weather bulletin source file is missing: {filename}")
        content = path.read_bytes()
        if not content.startswith(b"%PDF-"):
            raise ValueError(f"Weather bulletin is not a PDF: {filename}")
        prepared.append((filename, category, title, date.fromisoformat(issue),
                         date.fromisoformat(valid_from), date.fromisoformat(valid_to),
                         source_url, provenance, content, hashlib.sha256(content).hexdigest()))

    for (filename, category, title, issue, valid_from, valid_to,
         source_url, provenance, content, digest) in prepared:
        row = db.scalar(select(WeatherBulletin).where(WeatherBulletin.document_key == filename))
        if row is None:
            row = WeatherBulletin(document_key=filename)
            db.add(row)
        row.title = title
        row.category = category
        row.publisher = METEO
        row.issued_at = issue
        row.valid_from = valid_from
        row.valid_to = valid_to
        row.source_url = source_url
        row.provenance_status = provenance
        row.sha256 = digest
        row.content_type = "application/pdf"
        row.document_bytes = content
    db.commit()
    return len(prepared)


def bulletin_metadata(row: WeatherBulletin, today: date | None = None) -> dict:
    today = today or date.today()
    status = "upcoming" if row.valid_from > today else "in_season" if row.valid_to >= today else "past"
    return {
        "id": row.id, "title": row.title, "category": row.category,
        "publisher": row.publisher, "issued_at": row.issued_at.isoformat(),
        "valid_from": row.valid_from.isoformat(), "valid_to": row.valid_to.isoformat(),
        "status": status, "source_url": row.source_url,
        "provenance_status": row.provenance_status, "sha256": row.sha256,
        "document_url": f"/v1/weather/bulletins/{row.id}/document",
    }
