"""Cloudflare Radar API client with timeouts and clear configuration errors."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://api.cloudflare.com/client/v4/radar/attacks/layer7/top/attacks"
API_TIMEOUT_SECONDS = float(os.getenv("CLOUDFLARE_TIMEOUT_SECONDS", "20"))


def get_attack_data():
    """Fetch the latest aggregated Layer 7 attack ranking from Cloudflare Radar."""
    api_token = os.getenv("API_TOKEN")
    if not api_token:
        raise RuntimeError("API_TOKEN is not configured. Add it to your .env file.")

    params = {
        "dateRange": os.getenv("CLOUDFLARE_DATE_RANGE", "1h"),
        "normalization": os.getenv("CLOUDFLARE_NORMALIZATION", "PERCENTAGE"),
        "limit": 200,
    }
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Accept": "application/json",
    }
    response = requests.get(
        API_URL, headers=headers, params=params, timeout=API_TIMEOUT_SECONDS
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("success", False):
        errors = payload.get("errors") or [{"message": "Unknown Cloudflare API error"}]
        raise RuntimeError(f"Cloudflare Radar API returned an error: {errors}")
    return payload
