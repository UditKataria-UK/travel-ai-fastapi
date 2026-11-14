
from langgraph.graph import StateGraph, START, END

from backend.agents.state import TripState

from backend.agents.nodes import (
    planner_node,
    weather_node,
    places_node,
    hotels_node,
    itinerary_node,
    budget_checker_node,
    revise_plan_node,
    critic_node,
    budget_router
)


def build_graph():

    builder = StateGraph(TripState)

    # Register nodes

    builder.add_node("planner", planner_node)
    builder.add_node("weather", weather_node)
    builder.add_node("places", places_node)
    builder.add_node("hotels", hotels_node)
    builder.add_node("itinerary", itinerary_node)
    builder.add_node("budget_checker", budget_checker_node)
    builder.add_node("revise_plan", revise_plan_node)
    builder.add_node("critic", critic_node)

    # Starting point

    builder.add_edge(
        START,
        "planner"
    )

    # Parallel execution

    builder.add_edge("planner", "weather")
    builder.add_edge("planner", "places")
    builder.add_edge("planner", "hotels")

    # Wait for all three nodes

    builder.add_edge(
        ["weather", "places", "hotels"],
        "itinerary"
    )

    # Budget workflow

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

    # Recheck budget after revision

    builder.add_edge(
        "revise_plan",
        "budget_checker"
    )

    builder.add_edge(
        "critic",
        END
    )

    return builder.compile()


graph = build_graph()
