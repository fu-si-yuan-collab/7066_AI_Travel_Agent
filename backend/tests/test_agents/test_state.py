"""Tests for agent state definitions."""

from app.agents.state import AgentState, TravelPlan


def test_travel_plan_defaults():
    plan = TravelPlan()
    assert plan.destination == ""
    assert plan.num_travelers == 1
    assert plan.currency == "CNY"


def test_agent_state_defaults():
    state = AgentState()
    assert state.messages == []
    assert state.current_step == "initial"
    assert state.needs_user_input is False
    assert state.flight_results == []
