
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

from backend.config import (
    OMNIROUTE_API_KEY,
    OMNIROUTE_BASE_URL,
    MODEL_NAME,
)

from backend.agents.state import TripState

from backend.services.weather import get_weather
from backend.services.places import get_places
from backend.services.hotels import get_hotels

from backend.utils.exceptions import AgentExecutionError


# ==========================================
# LLM CONFIGURATION - OMNIROUTE
# ==========================================

llm = ChatOpenAI(
    model=MODEL_NAME,
    base_url=OMNIROUTE_BASE_URL,
    api_key=OMNIROUTE_API_KEY,
    temperature=0,
    max_tokens=8192,
    timeout=120,
    max_retries=2,
)


# ==========================================
# STRUCTURED BUDGET MODEL
# ==========================================

class TripCostEstimate(BaseModel):

    accommodation: float = Field(ge=0)
    food: float = Field(ge=0)
    transportation: float = Field(ge=0)
    activities: float = Field(ge=0)
    miscellaneous: float = Field(ge=0)


# ==========================================
# RESPONSE HELPER
# ==========================================

def extract_text(response) -> str:

    content = response.content

    if isinstance(content, str):
        result = content.strip()

    elif isinstance(content, list):

        parts = []

        for item in content:

            if isinstance(item, str):
                parts.append(item)

            elif isinstance(item, dict):
                if item.get("type") == "text":
                    parts.append(item.get("text", ""))

        result = "\n".join(parts).strip()

    else:
        result = ""

    if not result:
        raise AgentExecutionError(
            "LLM returned an empty response."
        )

    return result


# ==========================================
# PLANNER NODE
# ==========================================

def planner_node(state: TripState):

    prompt = f"""
You are an expert AI travel planning assistant.

Create trip planning requirements using:

Destination: {state["destination"]}
Days: {state["days"]}
Budget: ₹{state["budget"]}
Travelers: {state["travelers"]}

Determine:

1. Type of trip
2. Activities to prioritize
3. Budget distribution
4. Suitable itinerary style

Do not generate the final itinerary.

Return concise planning requirements.
"""

    response = llm.invoke(prompt)

    return {
        "trip_requirements": extract_text(response)
    }


# ==========================================
# WEATHER NODE
# ==========================================

def weather_node(state: TripState):

    weather = get_weather(
        state["destination"]
    )

    return {
        "weather": weather
    }


# ==========================================
# PLACES NODE
# ==========================================

def places_node(state: TripState):

    places = get_places(
        state["destination"]
    )

    return {
        "places": places
    }


# ==========================================
# HOTELS NODE
# ==========================================

def hotels_node(state: TripState):

    hotels = get_hotels(
        state["destination"]
    )

    return {
        "hotels": hotels
    }


# ==========================================
# ITINERARY NODE
# ==========================================

def itinerary_node(state: TripState):

    prompt = f"""
You are an expert travel itinerary planner.

Create a realistic {state["days"]}-day itinerary.

TRIP DETAILS:

Destination: {state["destination"]}
Travelers: {state["travelers"]}
Budget: ₹{state["budget"]}

PLANNING REQUIREMENTS:
{state["trip_requirements"]}

WEATHER:
{state["weather"]}

AVAILABLE PLACES:
{state["places"]}

AVAILABLE HOTELS:
{state["hotels"]}

INSTRUCTIONS:

For each day include:

- Morning
- Afternoon
- Evening

Consider:

1. Weather conditions
2. Travel time
3. Nearby attractions
4. Number of travelers
5. Budget constraints

Use only supplied places and hotels for
specific recommendations.

Do not create an unrealistically packed itinerary.

Do not invent hotel prices or attraction ratings.

Keep the response concise and practical.
Return the complete day-wise itinerary.
"""

    response = llm.invoke(prompt)

    itinerary = extract_text(response)

    return {
        "itinerary": itinerary
    }


# ==========================================
# BUDGET CHECKER NODE
# ==========================================

def budget_checker_node(state: TripState):

    budget_llm = llm.with_structured_output(
        TripCostEstimate
    )

    prompt = f"""
You are a professional travel expense estimator.

Estimate the complete trip expenses in Indian Rupees.

TRIP DETAILS:

Destination: {state["destination"]}
Days: {state["days"]}
Travelers: {state["travelers"]}
Available Budget: ₹{state["budget"]}

HOTELS:
{state["hotels"]}

ITINERARY:
{state["itinerary"]}

Estimate expenses for the ENTIRE group and
the ENTIRE trip, not per person.

Return these five expense categories:

1. Accommodation: Total accommodation cost.
2. Food: Total food cost.
3. Transportation: Total local transportation cost.
4. Activities: Total activities and entry fees.
5. Miscellaneous: Other reasonable expenses.

IMPORTANT:

- All amounts must be in INR.
- Estimate expenses realistically.
- Consider all travelers.
- Accommodation must cover the complete stay.
- Do not return a grand total.
- Return only the structured expense breakdown.
"""

    try:

        estimate = budget_llm.invoke(prompt)

        estimated_cost = round(
            estimate.accommodation
            + estimate.food
            + estimate.transportation
            + estimate.activities
            + estimate.miscellaneous,
            2
        )

        if estimated_cost <= 0:
            raise ValueError(
                "Estimated trip cost must be positive."
            )

        budget_status = (
            "WITHIN BUDGET"
            if estimated_cost <= state["budget"]
            else "OVER BUDGET"
        )

        return {
            "estimated_cost": estimated_cost,
            "budget_status": budget_status
        }

    except Exception as exc:

        raise AgentExecutionError(
            f"Budget estimation failed: {exc}"
        ) from exc


# ==========================================
# REVISION NODE
# ==========================================

def revise_plan_node(state: TripState):

    prompt = f"""
You are optimizing a travel itinerary.

Destination: {state["destination"]}
Days: {state["days"]}
Travelers: {state["travelers"]}

Available Budget: ₹{state["budget"]}

Current Estimated Cost:
₹{state["estimated_cost"]}

Current Itinerary:
{state["itinerary"]}

Hotels:
{state["hotels"]}

Create a more affordable itinerary.

Focus on:

1. Affordable accommodation
2. Less expensive activities
3. Reduced unnecessary travel
4. Budget-friendly food options

Maintain trip quality and practicality.

Do not invent hotel prices or availability.

Return ONLY the revised itinerary.
"""

    response = llm.invoke(prompt)

    revised_itinerary = extract_text(response)

    return {
        "itinerary": revised_itinerary,
        "revision_count": state["revision_count"] + 1
    }


# ==========================================
# BUDGET ROUTER
# ==========================================

def budget_router(state: TripState):

    if state["budget_status"] == "WITHIN BUDGET":
        return "critic"

    if state["revision_count"] >= 2:
        return "critic"

    return "revise_plan"


# ==========================================
# CRITIC NODE
# ==========================================

def critic_node(state: TripState):

    prompt = f"""
You are the final quality reviewer for an AI trip planner.

Review and improve the supplied itinerary.

DESTINATION:
{state["destination"]}

DURATION:
{state["days"]} days

TRAVELERS:
{state["travelers"]}

AVAILABLE BUDGET:
₹{state["budget"]}

WEATHER:
{state["weather"]}

PLACES:
{state["places"]}

HOTELS:
{state["hotels"]}

APPROVED ITINERARY:
{state["itinerary"]}

AUTHORITATIVE ESTIMATED COST:
₹{state["estimated_cost"]}

AUTHORITATIVE BUDGET STATUS:
{state["budget_status"]}

Review:

1. Is the itinerary realistic?
2. Is it too packed?
3. Does it consider weather?
4. Does it fit the trip duration?
5. Are hotel recommendations reasonable?
6. Does it respect the budget?

Prepare the final trip plan.

FORMAT:

# Trip Summary

# Recommended Hotels

# Day-wise Itinerary

# Travel Tips

IMPORTANT:

- Preserve the supplied itinerary's activities.
- Generate all requested days.
- Do not invent hotel prices or bookings.
- Do not generate an estimated budget section.
- Do not generate a budget status section.
- Do not calculate or change any expense amounts.
- Do not contradict the supplied weather information.

Return a practical and concise final plan.
"""

    response = llm.invoke(prompt)

    final_content = extract_text(response)

    budget_section = f"""

---

# Estimated Budget

**Total Estimated Cost: ₹{state["estimated_cost"]:,.2f}**

**Available Budget: ₹{state["budget"]:,.2f}**

**Budget Status: {state["budget_status"]}**
"""

    final_plan = final_content + budget_section

    return {
        "final_plan": final_plan
    }
