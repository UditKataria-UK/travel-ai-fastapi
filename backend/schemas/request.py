
from pydantic import BaseModel, Field, ConfigDict, field_validator


class TripRequest(BaseModel):

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid"
    )

    # ======================================
    # DESTINATION
    # ======================================

    destination: str = Field(
        min_length=2,
        max_length=100,
        description="Travel destination, e.g. Manali"
    )

    # ======================================
    # TRIP DETAILS
    # ======================================

    days: int = Field(
        ge=1,
        le=30,
        description="Trip duration in days"
    )

    budget: float = Field(
        gt=0,
        le=10_000_000,
        description="Total trip budget in INR"
    )

    travelers: int = Field(
        ge=1,
        le=20,
        description="Number of travelers"
    )

    # ======================================
    # DESTINATION VALIDATION
    # ======================================

    @field_validator("destination")
    @classmethod
    def validate_destination(cls, value: str) -> str:

        if not value:
            raise ValueError("Destination cannot be empty")

        return value
