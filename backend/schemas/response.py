
from typing import Any
from pydantic import BaseModel, Field


class TripResponse(BaseModel):

    # ======================================
    # TRIP DETAILS
    # ======================================

    destination: str
    days: int
    budget: float
    travelers: int

    # ======================================
    # EXTERNAL DATA
    # ======================================

    weather: dict[str, Any] = Field(default_factory=dict)

    places: list[dict[str, Any]] = Field(default_factory=list)

    hotels: list[dict[str, Any]] = Field(default_factory=list)

    # ======================================
    # ITINERARY
    # ======================================

    itinerary: str

    # ======================================
    # BUDGET
    # ======================================

    estimated_cost: float
    budget_status: str

    # ======================================
    # FINAL OUTPUT
    # ======================================

    final_plan: str
