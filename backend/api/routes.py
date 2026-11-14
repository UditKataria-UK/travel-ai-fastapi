
import logging

from fastapi import APIRouter, HTTPException

from backend.schemas.request import TripRequest
from backend.schemas.response import TripResponse
from backend.agents.graph import graph
from backend.utils.exceptions import ExternalServiceError, AgentExecutionError


logger = logging.getLogger(__name__)

router = APIRouter()


# ==========================================
# PLAN TRIP ENDPOINT
# ==========================================

@router.post(
    "/plan-trip",
    response_model=TripResponse
)
def plan_trip(request: TripRequest):

    # ======================================
    # INITIAL GRAPH STATE
    # ======================================

    initial_state = {

        "destination": request.destination,
        "days": request.days,
        "budget": request.budget,
        "travelers": request.travelers,

        "trip_requirements": "",

        "weather": {},
        "places": [],
        "hotels": [],

        "itinerary": "",

        "estimated_cost": 0.0,
        "budget_status": "",

        "final_plan": "",
        "revision_count": 0
    }

    try:

        # ==================================
        # EXECUTE LANGGRAPH WORKFLOW
        # ==================================

        result = graph.invoke(initial_state)

        # ==================================
        # VALIDATE FINAL GRAPH OUTPUT
        # ==================================

        required_outputs = [
            "weather",
            "places",
            "hotels",
            "itinerary",
            "estimated_cost",
            "budget_status",
            "final_plan"
        ]

        missing_outputs = [
            field
            for field in required_outputs
            if field not in result or result[field] is None
        ]

        if missing_outputs:
            raise AgentExecutionError(
                f"Graph returned incomplete output: {missing_outputs}"
            )

        # ==================================
        # API RESPONSE
        # ==================================

        return {
            "destination": result["destination"],
            "days": result["days"],
            "budget": result["budget"],
            "travelers": result["travelers"],

            "weather": result["weather"],
            "places": result["places"],
            "hotels": result["hotels"],

            "itinerary": result["itinerary"],

            "estimated_cost": result["estimated_cost"],
            "budget_status": result["budget_status"],

            "final_plan": result["final_plan"]
        }

    # ======================================
    # EXTERNAL SERVICE ERRORS
    # ======================================

    except ExternalServiceError as exc:

        logger.exception("External service failure")

        raise HTTPException(
            status_code=502,
            detail="An external travel service is temporarily unavailable."
        ) from exc

    # ======================================
    # AGENT EXECUTION ERRORS
    # ======================================

    except AgentExecutionError as exc:

        logger.exception("AI agent execution failure")

        raise HTTPException(
            status_code=502,
            detail="The AI trip planning service failed. Please try again."
        ) from exc

    # ======================================
    # VALIDATION ERRORS
    # ======================================

    except ValueError as exc:

        logger.warning(
            "Invalid trip planning input: %s",
            exc
        )

        raise HTTPException(
            status_code=422,
            detail=str(exc)
        ) from exc

    # ======================================
    # UNEXPECTED ERRORS
    # ======================================

    except Exception as exc:

        logger.exception("Trip planning failed")

        raise HTTPException(
            status_code=500,
            detail="Unable to generate trip plan. Please try again."
        ) from exc
