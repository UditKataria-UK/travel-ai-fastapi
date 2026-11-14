
from typing import TypedDict, Any


class TripState(TypedDict):

    # ======================================
    # USER INPUT
    # ======================================

    destination: str
    days: int
    budget: float
    travelers: int

    # ======================================
    # PLANNING REQUIREMENTS
    # ======================================

    trip_requirements: str

    # ======================================
    # EXTERNAL DATA
    # ======================================

    weather: dict[str, Any]
    places: list[dict[str, Any]]
    hotels: list[dict[str, Any]]

    # ======================================
    # ITINERARY
    # ======================================

    itinerary: str

    # ======================================
    # BUDGET MANAGEMENT
    # ======================================

    estimated_cost: float
    budget_status: str

    # ======================================
    # FINAL OUTPUT
    # ======================================

    final_plan: str

    # ======================================
    # REVISION CONTROL
    # ======================================

    revision_count: int
