"""Country centroid loading helpers."""
import csv
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent / "country-coord.csv"


def load_country_coordinates():
    country_coordinates = {}
    if not DATA_FILE.exists():
        return country_coordinates
    with DATA_FILE.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            code = (row.get("Alpha-2 code") or "").strip().upper()
            try:
                latitude = float(row["Latitude (average)"])
                longitude = float(row["Longitude (average)"])
            except (KeyError, TypeError, ValueError):
                continue
            if code:
                country_coordinates[code] = {
                    "country_name": row.get("Country", code),
                    "latitude": latitude,
                    "longitude": longitude,
                }
    return country_coordinates


def get_attack_coordinates(source_country, target_country):
    coordinates = load_country_coordinates()
    source = coordinates.get(source_country)
    target = coordinates.get(target_country)
    if source is None or target is None:
        return None
    return {"source": source, "target": target}
