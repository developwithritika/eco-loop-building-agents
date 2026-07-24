"""
llm.py
------
The LLM-powered decision agent. Given the current building state, the
agent asks a language model to choose a single energy-management action,
optimising for occupant comfort, minimum electricity cost, renewable
energy usage, and battery health.

The agent is defensive by design: if the LLM call fails, times out, or
returns malformed JSON, control falls back to a deterministic rule-based
engine so the building is never left without a decision.
"""

import json
import re

from openai import OpenAI, OpenAIError

from config import settings
from models import BuildingState, LLMDecision

# Valid action vocabulary understood by BuildingSimulator.apply_action().
# Constraining the LLM's output to this set keeps the system predictable.
VALID_ACTIONS = [
    "Increase Cooling",
    "Increase Heating",
    "Reduce HVAC",
    "Turn Off HVAC",
    "Turn Off Lights",
    "Turn On Lights",
    "Use Solar",
    "Use Battery",
    "Charge Battery",
    "Eco Mode",
    "No Action",
]

SYSTEM_PROMPT = f"""You are an expert building energy manager AI.

Your job is to look at the current state of a smart building and choose
exactly ONE action from this list:
{", ".join(VALID_ACTIONS)}

Optimise for, in order of importance:
1. Occupant comfort (indoor temperature roughly between 20C and 26C when occupancy > 0)
2. Minimum electricity cost (prefer solar and battery over grid power)
3. Renewable energy usage (use solar generation whenever it is available)
4. Battery optimisation (charge when level is low, discharge when level is high)

Reasoning guidelines:
- If temperature > 28C and occupancy is high, choose "Increase Cooling".
- If temperature < 18C and occupancy is high, choose "Increase Heating".
- If occupancy == 0, choose "Turn Off Lights" (unless a more urgent HVAC issue exists).
- If solar_generation is high relative to grid usage, choose "Use Solar".
- If battery_level > 70, choose "Use Battery" to offset grid draw.
- If battery_level < 20, choose "Charge Battery".
- If the outside temperature is pleasant (18-24C), choose "Reduce HVAC".
- If none of the above clearly apply, choose "No Action".

You MUST respond with ONLY a single valid JSON object, with no markdown
formatting, no code fences, and no additional commentary. The JSON must
have exactly this shape:
{{"action": "<one of the allowed actions>", "reason": "<short explanation>"}}
"""


class LLMAgent:
    """
    Wraps an OpenAI-compatible chat completion model to produce building
    control decisions from a BuildingState.
    """

    def __init__(self) -> None:
        """Initialise the underlying LLM client using configured settings."""
        self._client: OpenAI | None = None
        if settings.openai_api_key:
            self._client = OpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_model

    def _build_user_prompt(self, state: BuildingState) -> str:
        """
        Serialise the building state into a compact prompt for the LLM.

        Args:
            state: The current BuildingState to reason about.

        Returns:
            A prompt string describing the building state.
        """
        return (
            "Current building state:\n"
            f"- temperature: {state.temperature} C\n"
            f"- outside_temperature: {state.outside_temperature} C\n"
            f"- occupancy: {state.occupancy}\n"
            f"- solar_generation: {state.solar_generation} kW\n"
            f"- battery_level: {state.battery_level} %\n"
            f"- grid_energy_usage: {state.grid_energy_usage} kW\n"
            f"- lighting_level: {state.lighting_level} %\n"
            f"- hvac_mode: {state.hvac_mode}\n\n"
            "Choose the single best action and respond with JSON only."
        )

    def _extract_json(self, raw_text: str) -> dict:
        """
        Extract a JSON object from a raw LLM response, tolerating stray
        markdown code fences or leading/trailing commentary.

        Args:
            raw_text: The raw text returned by the LLM.

        Returns:
            A parsed dictionary.

        Raises:
            ValueError: If no valid JSON object could be extracted.
        """
        # Strip common markdown code fences (```json ... ``` or ``` ... ```).
        cleaned = re.sub(r"```(?:json)?", "", raw_text).strip()

        # Extract the first {...} block in case of surrounding commentary.
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise ValueError("No JSON object found in LLM response.")

        return json.loads(match.group(0))

    def _fallback_decision(self, state: BuildingState) -> LLMDecision:
        """
        Deterministic rule-based decision engine used when the LLM is
        unavailable or returns an unparsable response. Mirrors the
        reasoning guidelines given to the LLM so behaviour stays
        consistent regardless of which path is taken.

        Args:
            state: The current BuildingState to reason about.

        Returns:
            A valid LLMDecision.
        """
        if state.temperature > 28.0 and state.occupancy > 0:
            return LLMDecision(
                action="Increase Cooling",
                reason="Indoor temperature exceeds comfort threshold with occupants present.",
            )
        if state.temperature < 18.0 and state.occupancy > 0:
            return LLMDecision(
                action="Increase Heating",
                reason="Indoor temperature is below comfort threshold with occupants present.",
            )
        if state.occupancy == 0 and state.lighting_level > 0:
            return LLMDecision(
                action="Turn Off Lights",
                reason="Building is unoccupied; lighting is unnecessary.",
            )
        if state.solar_generation > 3.0 and state.grid_energy_usage > 0.5:
            return LLMDecision(
                action="Use Solar",
                reason="Ample solar generation available to offset grid usage.",
            )
        if state.battery_level > 70.0:
            return LLMDecision(
                action="Use Battery",
                reason="Battery charge is high; discharging reduces grid draw.",
            )
        if state.battery_level < 20.0:
            return LLMDecision(
                action="Charge Battery",
                reason="Battery charge is low and should be replenished.",
            )
        if settings.comfort_temp_min <= state.outside_temperature <= settings.comfort_temp_max:
            return LLMDecision(
                action="Reduce HVAC",
                reason="Outside temperature is pleasant; HVAC load can be reduced.",
            )
        return LLMDecision(
            action="No Action",
            reason="Building state is within acceptable operating parameters.",
        )

    def decide(self, state: BuildingState) -> LLMDecision:
        """
        Produce a control decision for the given building state, using
        the LLM when available and falling back to rule-based logic on
        any failure.

        Args:
            state: The current BuildingState to reason about.

        Returns:
            A validated LLMDecision with an action drawn from VALID_ACTIONS.
        """
        if self._client is None:
            return self._fallback_decision(state)

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": self._build_user_prompt(state)},
                ],
                temperature=0.2,
                max_tokens=200,
            )
            raw_text = response.choices[0].message.content or ""
            parsed = self._extract_json(raw_text)
            decision = LLMDecision(**parsed)

            if decision.action not in VALID_ACTIONS:
                # LLM invented an action outside the allowed vocabulary;
                # fall back to safe deterministic logic instead.
                return self._fallback_decision(state)

            return decision

        except (OpenAIError, ValueError, json.JSONDecodeError, TypeError, KeyError):
            # Any failure in the LLM round trip or parsing falls back to
            # the deterministic engine so the control loop never stalls.
            return self._fallback_decision(state)
