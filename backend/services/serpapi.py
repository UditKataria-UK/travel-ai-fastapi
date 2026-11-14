
import logging
import requests

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from backend.config import SERPAPI_API_KEY
from backend.utils.exceptions import ExternalServiceError


logger = logging.getLogger(__name__)

SERPAPI_URL = "https://serpapi.com/search.json"


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

    return session


session = create_session()


# ==========================================
# SERPAPI SEARCH
# ==========================================

def serpapi_search(query: str) -> dict:

    if not SERPAPI_API_KEY:
        raise ExternalServiceError(
            "SerpAPI API key is not configured."
        )

    if not query or not query.strip():
        raise ValueError("Search query cannot be empty.")

    try:

        response = session.get(
            SERPAPI_URL,
            params={
                "engine": "google_maps",
                "q": query.strip(),
                "api_key": SERPAPI_API_KEY
            },
            timeout=(5, 20)
        )

        response.raise_for_status()

        data = response.json()

        if not isinstance(data, dict):
            raise ExternalServiceError(
                "Invalid SerpAPI response format."
            )

        if "error" in data:
            logger.error(
                "SerpAPI returned an error: %s",
                data["error"]
            )

            raise ExternalServiceError(
                "SerpAPI search failed."
            )

        logger.info(
            "SerpAPI search completed successfully: %s",
            query
        )

        return data

    except ExternalServiceError:
        raise

    except requests.RequestException as exc:

        logger.exception("SerpAPI request failed")

        raise ExternalServiceError(
            "SerpAPI service is temporarily unavailable."
        ) from exc

    except ValueError as exc:

        logger.exception("Invalid SerpAPI JSON response")

        raise ExternalServiceError(
            "SerpAPI returned an invalid JSON response."
        ) from exc
