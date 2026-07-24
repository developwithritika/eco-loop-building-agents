"""
models.py
---------
Pydantic data models shared across the simulator, LLM agent, controller,
and FastAPI server. Keeping these in a single module guarantees a single
source of truth for the shape of building state and API payloads.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class HVACMode(str, Enum):
    """Possible operating modes for the building's HVAC system."""

    OFF = "off"
    HEATING = "heating"
    COOLING = "cooling"
    ECO = "eco"


class BuildingState(BaseModel):
    """
    Represents the full observable state of the simulated building at a
    single point in time. This is the payload that flows from the
    simulator to the LLM agent and back out through the API.
    """

    temperature: float = Field(
        ..., description="Current indoor temperature in Celsius."
    )
    outside_temperature: float = Field(
        ..., description="Current outdoor temperature in Celsius."
    )
    occupancy: int = Field(
        ..., ge=0, description="Number of occupants currently in the building."
    )
    solar_generation: float = Field(
        ..., ge=0.0, description="Current solar power generation in kW."
    )
    battery_level: float = Field(
        ..., ge=0.0, le=100.0, description="Battery charge level as a percentage."
    )
    grid_energy_usage: float = Field(
        ..., ge=0.0, description="Current power drawn from the grid in kW."
    )
    lighting_level: float = Field(
        ..., ge=0.0, le=100.0, description="Lighting intensity as a percentage."
    )
    hvac_mode: HVACMode = Field(
        default=HVACMode.OFF, description="Current HVAC operating mode."
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp of when this state was generated.",
    )

    class Config:
        use_enum_values = True


class ActionRequest(BaseModel):
    """
    Payload accepted by the POST /action endpoint. Represents a single
    control action to be applied to the building simulation.
    """

    action: str = Field(
        ..., min_length=1, description="Name of the action to apply, e.g. 'Increase Cooling'."
    )
    reason: str | None = Field(
        default=None, description="Optional human-readable justification for the action."
    )


class ActionResponse(BaseModel):
    """
    Payload returned by the POST /action endpoint. Confirms which action
    was applied and includes the resulting building state.
    """

    applied_action: str = Field(..., description="The action that was applied.")
    reason: str | None = Field(
        default=None, description="Justification for the applied action, if any."
    )
    updated_state: BuildingState = Field(
        ..., description="Building state after the action was applied."
    )


class LLMDecision(BaseModel):
    """
    Structured representation of a decision returned by the LLM agent.
    This is the strict schema the agent's raw JSON output is parsed into.
    """

    action: str = Field(..., description="The chosen control action.")
    reason: str = Field(..., description="Explanation for why this action was chosen.")
