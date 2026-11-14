
import logging

from backend.services.serpapi import serpapi_search
from backend.utils.exceptions import ExternalServiceError


logger = logging.getLogger(__name__)


# ==========================================
# HOTEL SERVICE
# ==========================================

def get_hotels(destination: str) -> list[dict]:

    if not destination or not destination.strip():
        raise ValueError("Destination cannot be empty.")

    query = f"best hotels in {destination.strip()}"

    try:

        data = serpapi_search(query)

        if not isinstance(data, dict):
            raise ExternalServiceError(
                "Invalid hotel API response."
            )

        local_results = data.get("local_results", [])

        if not isinstance(local_results, list):
            raise ExternalServiceError(
                "Invalid hotel results format."
            )

        hotels = []
        seen_hotels = set()

        for hotel in local_results:

            if not isinstance(hotel, dict):
                continue

            name = hotel.get("title")
            address = hotel.get("address")

            # Skip incomplete results

            if not name or not address:
                continue

            # Remove duplicates

            unique_key = name.strip().casefold()

            if unique_key in seen_hotels:
                continue

            seen_hotels.add(unique_key)

            # Validate rating

            rating = hotel.get("rating")

            try:
                rating = float(rating) if rating is not None else None
            except (ValueError, TypeError):
                rating = None

            if rating is not None and not 0 <= rating <= 5:
                rating = None

            # Validate review count

            reviews = hotel.get("reviews")

            try:
                reviews = int(reviews) if reviews is not None else None
            except (ValueError, TypeError):
                reviews = None

            if reviews is not None and reviews < 0:
                reviews = None

            # Preserve source price as text.
            # It is not necessarily a confirmed booking price.

            price = hotel.get("price")

            hotels.append({
                "name": name.strip(),
                "rating": rating,
                "reviews": reviews,
                "address": address.strip(),
                "price": str(price) if price is not None else None,
                "type": hotel.get("type")
            })

            if len(hotels) >= 8:
                break

        logger.info(
            "Retrieved %d hotels for %s",
            len(hotels),
            destination
        )

        return hotels

    except ExternalServiceError:
        raise

    except (TypeError, AttributeError) as exc:

        logger.exception("Hotel processing failed")

        raise ExternalServiceError(
            "Unable to process hotel API response."
        ) from exc
