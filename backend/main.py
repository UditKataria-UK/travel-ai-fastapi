import os
import requests
from typing import TypedDict

from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is missing from .env")

if not SERPAPI_API_KEY:
    raise ValueError("SERPAPI_API_KEY is missing from .env")

llm = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0
)

app = FastAPI(
    title="AI Trip Planner",
    description="AI-powered trip planner using FastAPI and LangGraph",
    version="1.0.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TripRequest(BaseModel):
    destination: str
    days: int
    budget: float
    travelers: int

class TripState(TypedDict):

    destination: str
    days: int
    budget: float
    travelers: int

    trip_requirements: str

    weather: dict
    places: list
    hotels: list

    itinerary: str

    estimated_cost: float
    budget_status: str

    final_plan: str
    revision_count: int


def get_weather(destination: str):

    # --------------------------------
    # Step 1: City → Coordinates
    # --------------------------------

    geocoding_url = (
        "https://geocoding-api.open-meteo.com/v1/search"
    )

    params = {
        "name": destination,
        "count": 1,
        "language": "en",
        "format": "json"
    }

    response = requests.get(
        geocoding_url,
        params=params,
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    if "results" not in data:
        raise ValueError(
            f"Could not find location: {destination}"
        )

    location = data["results"][0]

    latitude = location["latitude"]
    longitude = location["longitude"]

    city_name = location["name"]

    # --------------------------------
    # Step 2: Coordinates → Weather
    # --------------------------------

    weather_url = "https://api.open-meteo.com/v1/forecast"

    weather_params = {
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
    }

    weather_response = requests.get(
        weather_url,
        params=weather_params,
        timeout=10
    )

    weather_response.raise_for_status()

    weather_data = weather_response.json()

    current = weather_data["current"]

    return {
        "city": city_name,
        "latitude": latitude,
        "longitude": longitude,

        "temperature": current["temperature_2m"],
        "humidity": current["relative_humidity_2m"],
        "wind_speed": current["wind_speed_10m"],
        "weather_code": current["weather_code"],

        "forecast": weather_data.get("daily", {})
    }


# ============================================================
# SERPAPI HELPER
# ============================================================

def serpapi_search(query: str):

    url = "https://serpapi.com/search.json"

    params = {
        "engine": "google_maps",
        "q": query,
        "api_key": SERPAPI_API_KEY
    }

    response = requests.get(
        url,
        params=params,
        timeout=15
    )

    response.raise_for_status()

    return response.json()


# ============================================================
# PLACES TOOL
# ============================================================

def get_places(destination: str):

    data = serpapi_search(
        f"best tourist attractions in {destination}"
    )

    places = []

    for place in data.get("local_results", [])[:8]:

        places.append({
            "name": place.get("title"),
            "rating": place.get("rating"),
            "reviews": place.get("reviews"),
            "address": place.get("address"),
            "type": place.get("type")
        })

    return places


# ============================================================
# HOTELS TOOL
# ============================================================

def get_hotels(destination: str):

    data = serpapi_search(
        f"best hotels in {destination}"
    )

    hotels = []

    for hotel in data.get("local_results", [])[:8]:

        hotels.append({
            "name": hotel.get("title"),
            "rating": hotel.get("rating"),
            "reviews": hotel.get("reviews"),
            "address": hotel.get("address"),
            "price": hotel.get("price"),
            "type": hotel.get("type")
        })

    return hotels


# ============================================================
# PLANNER NODE
# ============================================================

def planner_node(state: TripState):

    prompt = f"""
You are the planning node of an AI Trip Planner.

Create the requirements for a trip using:

Destination: {state["destination"]}
Number of days: {state["days"]}
Budget: ₹{state["budget"]}
Travelers: {state["travelers"]}

Determine:

1. What type of trip this should be
2. What activities should be prioritized
3. How the budget should roughly be distributed
4. What kind of itinerary would make sense

Do NOT create the final answer yet.

Return concise planning requirements that other nodes can use.
"""

    response = llm.invoke(prompt)

    return {
        "trip_requirements": response.content
    }


# ============================================================
# WEATHER NODE
# ============================================================

def weather_node(state: TripState):

    weather = get_weather(
        state["destination"]
    )

    return {
        "weather": weather
    }


# ============================================================
# PLACES NODE
# ============================================================

def places_node(state: TripState):

    places = get_places(
        state["destination"]
    )

    return {
        "places": places
    }


# ============================================================
# HOTELS NODE
# ============================================================

def hotels_node(state: TripState):

    hotels = get_hotels(
        state["destination"]
    )

    return {
        "hotels": hotels
    }


# ============================================================
# ITINERARY NODE
# ============================================================

def itinerary_node(state: TripState):

    prompt = f"""
You are an expert travel itinerary planner.

Create a {state["days"]}-day itinerary.

Trip information:

Destination:
{state["destination"]}

Travelers:
{state["travelers"]}

Budget:
₹{state["budget"]}

Planning requirements:
{state["trip_requirements"]}

Weather information:
{state["weather"]}

Available places:
{state["places"]}

Available hotels:
{state["hotels"]}

Create a realistic day-by-day itinerary.

For each day include:

- Morning
- Afternoon
- Evening

Consider:

- Weather
- Travel time
- Logical grouping of nearby places
- Traveler count
- Budget

Do not make the itinerary unrealistically packed.
"""

    response = llm.invoke(prompt)

    return {
        "itinerary": response.content
    }


# ============================================================
# BUDGET CHECKER NODE
# ============================================================
def budget_checker_node(state: TripState):

    prompt = f"""
Estimate the total cost of this trip.

Destination: {state["destination"]}
Days: {state["days"]}
Travelers: {state["travelers"]}
Budget: ₹{state["budget"]}

Hotels:
{state["hotels"]}

Itinerary:
{state["itinerary"]}

Estimate the total cost including:

- Accommodation
- Food
- Local transport
- Activities
- Miscellaneous expenses

Return exactly:

Estimated Cost: ₹<amount>

Status: WITHIN BUDGET

or

Status: OVER BUDGET
"""

    response = llm.invoke(prompt)

    text = response.content

    import re

    match = re.search(
        r"Estimated Cost:\s*₹?([\d,]+)",
        text
    )

    if match:
        estimated_cost = float(
            match.group(1).replace(",", "")
        )
    else:
        estimated_cost = state["budget"]

    if "OVER BUDGET" in text.upper():
        budget_status = "OVER BUDGET"
    else:
        budget_status = "WITHIN BUDGET"

    return {
        "estimated_cost": estimated_cost,
        "budget_status": budget_status
    }


def revise_plan_node(state: TripState):

    prompt = f"""
You are revising a travel itinerary because it is over budget.

Destination: {state["destination"]}
Days: {state["days"]}
Travelers: {state["travelers"]}
Available Budget: ₹{state["budget"]}

Current Itinerary:
{state["itinerary"]}

Available Hotels:
{state["hotels"]}

Current estimated cost:
₹{state["estimated_cost"]}

Create a cheaper version of the itinerary.

Reduce expensive activities, unnecessary travel,
and expensive accommodation choices.

Keep the trip enjoyable and realistic.

Return ONLY the revised itinerary.
"""

    response = llm.invoke(prompt)

    return {
        "itinerary": response.content,
        "revision_count": state["revision_count"] + 1
    }

def budget_router(state: TripState):

    if state["budget_status"] == "WITHIN BUDGET":
        return "critic"

    if state["revision_count"] >= 2:
        return "critic"

    return "revise_plan"

# ============================================================
# CRITIC NODE
# ============================================================

def critic_node(state: TripState):

    prompt = f"""
You are the final critic for an AI trip planner.

Review the proposed trip.

Destination:
{state["destination"]}

Days:
{state["days"]}

Budget:
₹{state["budget"]}

Travelers:
{state["travelers"]}

Weather:
{state["weather"]}

Places:
{state["places"]}

Hotels:
{state["hotels"]}

Itinerary:
{state["itinerary"]}

Budget status:
{state["budget_status"]}

Check:

1. Is the itinerary realistic?
2. Is it too packed?
3. Does it consider weather?
4. Does it fit the trip duration?
5. Is the hotel selection reasonable?
6. Is the budget reasonable?

Then produce the FINAL TRIP PLAN.

Format:

# Trip Summary

# Recommended Hotel

# Day 1

# Day 2

# Day 3

Continue for all days.

# Estimated Budget

# Travel Tips

Keep the answer practical and concise.
"""

    response = llm.invoke(prompt)

    return {
        "final_plan": response.content
    }


# ============================================================
# LANGGRAPH
# ============================================================

builder = StateGraph(TripState)


builder.add_node(
    "planner",
    planner_node
)

builder.add_node(
    "weather",
    weather_node
)

builder.add_node(
    "places",
    places_node
)

builder.add_node(
    "hotels",
    hotels_node
)

builder.add_node(
    "itinerary",
    itinerary_node
)

builder.add_node(
    "budget_checker",
    budget_checker_node
)

builder.add_node(
    "critic",
    critic_node
)

builder.add_node(
    "revise_plan",
    revise_plan_node
)


# ============================================================
# GRAPH FLOW
# ============================================================

builder.add_edge(
    START,
    "planner"
)

builder.add_edge(
    "planner",
    "weather"
)

builder.add_edge(
    "weather",
    "places"
)

builder.add_edge(
    "places",
    "hotels"
)

builder.add_edge(
    "hotels",
    "itinerary"
)

builder.add_edge(
    "itinerary",
    "budget_checker"
)

builder.add_conditional_edges(
    "budget_checker",
    budget_router,
    {
        "critic": "critic",
        "revise_plan": "revise_plan"
    }
)
builder.add_edge(
    "revise_plan",
    "budget_checker"
)

builder.add_edge(
    "critic",
    END
)


graph = builder.compile()


# ============================================================
# FASTAPI ROUTES
# ============================================================

@app.get("/")
def home():

    return {
        "message": "AI Trip Planner API is running"
    }


@app.post("/plan-trip")
def plan_trip(request: TripRequest):

    try:

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

            "estimated_cost": 0,
            "budget_status": "",
            "revision_count": 0,

            "final_plan": ""
        }

        result = graph.invoke(
            initial_state
        )

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

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )