"""Normalize Cloudflare Radar's aggregated country-to-country ranking data."""
from country_coordinates import load_country_coordinates

COUNTRY_COORDINATES = load_country_coordinates()


def _extract_records(data):
    result = data.get("result") or {}
    # Cloudflare's top-attacks response uses top_0 for the ranked list.
    # Iterate the entire returned list; never truncate to an arbitrary top five.
    records = result.get("top_0")
    if isinstance(records, list):
        return records
    # Be tolerant of API response variants where result itself is a list.
    if isinstance(result, list):
        return result
    return []


def process_attack_data(data):
    """Return every valid ranked record, enriched with country centroids."""
    processed = []
    for index, attack in enumerate(_extract_records(data), start=1):
        if not isinstance(attack, dict):
            continue
        source_code = str(attack.get("originCountryAlpha2") or "").upper()
        target_code = str(attack.get("targetCountryAlpha2") or "").upper()
        source_info = COUNTRY_COORDINATES.get(source_code, {})
        target_info = COUNTRY_COORDINATES.get(target_code, {})
        try:
            percentage = float(attack.get("value", 0))
        except (TypeError, ValueError):
            continue
        processed.append({
            "source": source_code,
            "source_country": attack.get("originCountryName") or source_info.get("country_name") or source_code or "Unknown",
            "source_latitude": source_info.get("latitude"),
            "source_longitude": source_info.get("longitude"),
            "target": target_code,
            "target_country": attack.get("targetCountryName") or target_info.get("country_name") or target_code or "Unknown",
            "target_latitude": target_info.get("latitude"),
            "target_longitude": target_info.get("longitude"),
            "percentage": percentage,
            "rank": attack.get("rank", index),
        })
    return processed
