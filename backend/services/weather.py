
import logging
import requests

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from backend.config import WEATHER_API_URL
from backend.utils.exceptions import ExternalServiceError


logger = logging.getLogger(__name__)

GEOCODING_URL = (
    "https://geocoding-api.open-meteo.com/v1/search"
)


# ==========================================
# LOCATION PREFERENCES
# ==========================================

LOCATION_PREFERENCES = {
    "manali": {
        "country_code": "IN",
        "admin1": "Himachal Pradesh"
    }
}


# ==========================================
# HTTP SESSION WITH RETRIES
# ==========================================

def create_session():

    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        respect_retry_after_header=True
    )

    adapter = HTTPAdapter(
        max_retries=retry_strategy
    )

    session = requests.Session()

    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


session = create_session()


# ==========================================
# LOCATION RESOLUTION
# ==========================================

def resolve_location(destination: str) -> dict:

    destination = destination.strip()

    if not destination:
        raise ValueError("Destination cannot be empty.")

    try:

        response = session.get(
            GEOCODING_URL,
            params={
                "name": destination,
                "count": 10,
                "language": "en",
                "format": "json"
            },
            timeout=(5, 15)
        )

        response.raise_for_status()

        data = response.json()

        locations = data.get("results", [])

        if not isinstance(locations, list) or not locations:
            raise ValueError(
                f"Location not found: {destination}"
            )

        exact_matches = [
            location
            for location in locations
            if location.get("name", "").casefold()
            == destination.casefold()
        ]

        candidates = exact_matches or locations

        preference = LOCATION_PREFERENCES.get(
            destination.casefold()
        )

        if preference:

            candidates = [
                location
                for location in candidates
                if (
                    location.get("country_code", "").upper()
                    == preference["country_code"]
                    and location.get("admin1", "").casefold()
                    == preference["admin1"].casefold()
                )
            ]

            if not candidates:
                raise ValueError(
                    f"Could not resolve {destination} "
                    "to the expected region."
                )

        elif len(candidates) > 1:

            raise ValueError(
                f"Multiple locations found for {destination}. "
                "Please include state or country."
            )

        selected = candidates[0]

        if not isinstance(selected, dict):
            raise ExternalServiceError(
                "Invalid geocoding result."
            )

        latitude = selected.get("latitude")
        longitude = selected.get("longitude")

        if latitude is None or longitude is None:
            raise ExternalServiceError(
                "Geocoding response is missing coordinates."
            )

        logger.info(
            "Resolved %s to %s, %s",
            destination,
            selected.get("name"),
            selected.get("admin1")
        )

        return selected

    except ValueError:
        raise

    except requests.RequestException as exc:

        logger.exception("Geocoding API request failed")

        raise ExternalServiceError(
            "Geocoding service is temporarily unavailable."
        ) from exc

    except (KeyError, TypeError) as exc:

        raise ExternalServiceError(
            "Invalid geocoding API response."
        ) from exc


# ==========================================
# WEATHER FETCHING
# ==========================================

def get_weather(destination: str) -> dict:

    try:

        # Resolve destination

        location = resolve_location(destination)

        latitude = location["latitude"]
        longitude = location["longitude"]

        # Fetch weather

        response = session.get(
            WEATHER_API_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": (
                    "temperature_2m,"
                    "relative_humidity_2m,"
                    "wind_speed_10m,"
                    "weather_code"
                ),
                "daily": (
                    "temperature_2m_max,"
                    "temperature_2m_min,"
                    "weather_code"
                ),
                "forecast_days": 7,
                "timezone": "auto"
            },
            timeout=(5, 20)
        )

        response.raise_for_status()

        weather_data = response.json()

        current = weather_data.get("current")
        daily = weather_data.get("daily")

        if not isinstance(current, dict):
            raise ExternalServiceError(
                "Current weather data is missing."
            )

        if not isinstance(daily, dict):
            raise ExternalServiceError(
                "Weather forecast data is missing."
            )

        required_current_fields = [
            "temperature_2m",
            "relative_humidity_2m",
            "wind_speed_10m",
            "weather_code"
        ]

        missing_fields = [
            field
            for field in required_current_fields
            if field not in current
        ]

        if missing_fields:
            raise ExternalServiceError(
                f"Missing current weather fields: {missing_fields}"
            )

        required_daily_fields = [
            "time",
            "temperature_2m_max",
            "temperature_2m_min",
            "weather_code"
        ]

        missing_daily_fields = [
            field
            for field in required_daily_fields
            if field not in daily
        ]

        if missing_daily_fields:
            raise ExternalServiceError(
                f"Missing forecast fields: {missing_daily_fields}"
            )

        logger.info(
            "Weather fetched successfully for %s",
            location.get("name")
        )

        return {
            "city": location["name"],
            "region": location.get("admin1"),
            "country": location.get("country"),
            "country_code": location.get("country_code"),

            "latitude": latitude,
            "longitude": longitude,

            "temperature": current["temperature_2m"],
            "humidity": current["relative_humidity_2m"],
            "wind_speed": current["wind_speed_10m"],
            "weather_code": current["weather_code"],

            "forecast": daily
        }

    except ValueError:
        raise

    except ExternalServiceError:
        raise

    except requests.RequestException as exc:

        logger.exception("Weather API request failed")

        raise ExternalServiceError(
            "Weather service is temporarily unavailable."
        ) from exc

    except (KeyError, TypeError) as exc:

        logger.exception("Invalid weather API response")

        raise ExternalServiceError(
            "Invalid weather API response."
        ) from exc
