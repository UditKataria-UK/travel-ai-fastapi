
import logging

from backend.services.serpapi import serpapi_search
from backend.utils.exceptions import ExternalServiceError


logger = logging.getLogger(__name__)


# ==========================================
# PLACES SERVICE
# ==========================================

def get_places(destination: str) -> list[dict]:

    if not destination or not destination.strip():
        raise ValueError("Destination cannot be empty.")

    query = f"best tourist attractions in {destination.strip()}"

    try:

        data = serpapi_search(query)

        if not isinstance(data, dict):
            raise ExternalServiceError(
                "Invalid places API response."
            )

        local_results = data.get("local_results", [])

        if not isinstance(local_results, list):
            raise ExternalServiceError(
                "Invalid places results format."
            )

        places = []
        seen_places = set()

        for place in local_results:

            if not isinstance(place, dict):
                continue

            name = place.get("title")
            address = place.get("address")

            # Skip incomplete results

            if not name or not address:
                continue

            # Remove duplicate places

            unique_key = name.strip().casefold()

            if unique_key in seen_places:
                continue

            seen_places.add(unique_key)

            rating = place.get("rating")
            reviews = place.get("reviews")

            # Validate rating

            try:
                rating = float(rating) if rating is not None else None
            except (ValueError, TypeError):
                rating = None

            if rating is not None and not 0 <= rating <= 5:
                rating = None

            # Validate review count

            try:
                reviews = int(reviews) if reviews is not None else None
            except (ValueError, TypeError):
                reviews = None

            if reviews is not None and reviews < 0:
                reviews = None

            places.append({
                "name": name.strip(),
                "rating": rating,
                "reviews": reviews,
                "address": address.strip(),
                "type": place.get("type")
            })

            # Limit final results

            if len(places) >= 8:
                break

        logger.info(
            "Retrieved %d places for %s",
            len(places),
            destination
        )

        return places

    except ExternalServiceError:
        raise

    except (TypeError, AttributeError) as exc:

        logger.exception("Places processing failed")

        raise ExternalServiceError(
            "Unable to process places API response."
        ) from exc
