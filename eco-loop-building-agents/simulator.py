"""
simulator.py
------------
A realistic, self-contained simulation of a smart building's environmental
and energy state. The BuildingSimulator generates plausible state
transitions on every cycle and knows how to apply high-level control
actions (as chosen by the LLM agent) to that state.
"""

import random
from datetime import datetime, timedelta

from models import BuildingState, HVACMode


class BuildingSimulator:
    """
    Simulates a single building's environmental and energy conditions
    over time.

    The simulator owns a single BuildingState instance and mutates it
    on each call to generate_state(). Randomness is bounded so that
    values stay within physically plausible ranges.
    """

    # Physical bounds used to clamp all generated/updated values.
    MIN_TEMPERATURE = 10.0
    MAX_TEMPERATURE = 40.0
    MIN_OUTSIDE_TEMPERATURE = -5.0
    MAX_OUTSIDE_TEMPERATURE = 45.0
    MAX_OCCUPANCY = 50
    MAX_SOLAR_GENERATION_KW = 10.0
    MAX_GRID_USAGE_KW = 15.0

    def __init__(self, seed: int | None = None) -> None:
        """
        Initialise the simulator with a fresh, randomised building state.

        Args:
            seed: Optional random seed for reproducible simulations
                (useful for testing and demos).
        """
        if seed is not None:
            random.seed(seed)
        self._simulated_time = datetime.utcnow()
        self.state: BuildingState = self._initial_state()

    def _initial_state(self) -> BuildingState:
        """
        Build a plausible starting state for the building, roughly
        representing a mild morning with the building unoccupied.

        Returns:
            A freshly constructed BuildingState.
        """
        return BuildingState(
            temperature=22.0,
            outside_temperature=18.0,
            occupancy=0,
            solar_generation=0.5,
            battery_level=60.0,
            grid_energy_usage=1.0,
            lighting_level=10.0,
            hvac_mode=HVACMode.OFF,
            timestamp=self._simulated_time,
        )

    @staticmethod
    def _clamp(value: float, minimum: float, maximum: float) -> float:
        """
        Restrict a numeric value to the inclusive range [minimum, maximum].

        Args:
            value: The value to clamp.
            minimum: Lower bound.
            maximum: Upper bound.

        Returns:
            The clamped value.
        """
        return max(minimum, min(maximum, value))

    def _advance_time(self) -> None:
        """Advance the simulator's internal clock by one simulated cycle."""
        self._simulated_time += timedelta(minutes=5)

    def _simulate_outside_temperature(self) -> float:
        """
        Generate a new outside temperature using a smooth random walk
        combined with a coarse day/night sinusoidal influence.

        Returns:
            The updated outside temperature in Celsius.
        """
        hour = self._simulated_time.hour
        # Simple day/night curve: warmest around 2 PM, coolest around 4 AM.
        day_night_bias = 5.0 * (1.0 - abs(hour - 14) / 12.0)
        drift = random.uniform(-1.0, 1.0)
        new_temp = self.state.outside_temperature + drift * 0.3 + day_night_bias * 0.05
        return self._clamp(
            new_temp, self.MIN_OUTSIDE_TEMPERATURE, self.MAX_OUTSIDE_TEMPERATURE
        )

    def _simulate_indoor_temperature(self, outside_temperature: float) -> float:
        """
        Generate a new indoor temperature influenced by the outside
        temperature, current HVAC mode, and small random fluctuation.

        Args:
            outside_temperature: The newly simulated outside temperature.

        Returns:
            The updated indoor temperature in Celsius.
        """
        # Indoor temperature drifts slightly toward outside temperature
        # (heat exchange through walls/windows) unless HVAC counteracts it.
        drift_towards_outside = (outside_temperature - self.state.temperature) * 0.05

        hvac_effect = 0.0
        if self.state.hvac_mode == HVACMode.COOLING:
            hvac_effect = -0.8
        elif self.state.hvac_mode == HVACMode.HEATING:
            hvac_effect = 0.8
        elif self.state.hvac_mode == HVACMode.ECO:
            hvac_effect = -0.2 if self.state.temperature > 24.0 else 0.2

        noise = random.uniform(-0.3, 0.3)
        new_temp = self.state.temperature + drift_towards_outside + hvac_effect + noise
        return self._clamp(new_temp, self.MIN_TEMPERATURE, self.MAX_TEMPERATURE)

    def _simulate_occupancy(self) -> int:
        """
        Generate a new occupancy count using a bounded random walk that
        loosely follows a working-hours pattern.

        Returns:
            The updated occupancy count.
        """
        hour = self._simulated_time.hour
        working_hours = 8 <= hour <= 19
        max_expected = self.MAX_OCCUPANCY if working_hours else 5

        step = random.randint(-3, 3)
        new_occupancy = self.state.occupancy + step
        return int(self._clamp(new_occupancy, 0, max_expected))

    def _simulate_solar_generation(self) -> float:
        """
        Generate new solar power generation, peaking around midday and
        producing near-zero output at night.

        Returns:
            The updated solar generation in kW.
        """
        hour = self._simulated_time.hour
        if hour < 6 or hour > 19:
            base_output = 0.0
        else:
            # Bell-shaped curve peaking at noon.
            base_output = self.MAX_SOLAR_GENERATION_KW * max(
                0.0, 1.0 - abs(hour - 12) / 7.0
            )
        noise = random.uniform(-0.5, 0.5)
        new_solar = base_output + noise
        return self._clamp(new_solar, 0.0, self.MAX_SOLAR_GENERATION_KW)

    def _simulate_battery_level(self, solar_generation: float) -> float:
        """
        Update the battery charge level based on solar surplus and
        approximate building load.

        Args:
            solar_generation: The newly simulated solar generation in kW.

        Returns:
            The updated battery level as a percentage.
        """
        approximate_load_kw = 1.0 + (self.state.occupancy * 0.05)
        net_power = solar_generation - approximate_load_kw

        # Convert net power surplus/deficit into an approximate charge
        # delta for this simulation cycle.
        charge_delta = net_power * 1.5
        new_level = self.state.battery_level + charge_delta
        return self._clamp(new_level, 0.0, 100.0)

    def _simulate_lighting_level(self) -> float:
        """
        Generate a new lighting level, correlated with occupancy: an
        empty building trends toward lights-off over time.

        Returns:
            The updated lighting level as a percentage.
        """
        if self.state.occupancy == 0:
            target = 0.0
        else:
            target = min(100.0, 30.0 + self.state.occupancy * 2.0)

        # Move gradually toward the target rather than jumping instantly.
        new_level = self.state.lighting_level + (target - self.state.lighting_level) * 0.3
        return self._clamp(new_level, 0.0, 100.0)

    def _simulate_grid_energy_usage(
        self, solar_generation: float, battery_level: float
    ) -> float:
        """
        Estimate grid energy draw based on total building load offset by
        solar generation and available battery power.

        Args:
            solar_generation: The newly simulated solar generation in kW.
            battery_level: The newly simulated battery level percentage.

        Returns:
            The updated grid energy usage in kW.
        """
        hvac_load = {
            HVACMode.OFF: 0.2,
            HVACMode.ECO: 0.8,
            HVACMode.HEATING: 2.5,
            HVACMode.COOLING: 2.5,
        }[self.state.hvac_mode]

        lighting_load = (self.state.lighting_level / 100.0) * 1.5
        occupancy_load = self.state.occupancy * 0.03
        total_load = hvac_load + lighting_load + occupancy_load

        # Battery can offset load only if it holds a meaningful charge.
        battery_offset = 1.0 if battery_level > 20.0 else 0.0

        remaining_load = total_load - solar_generation - battery_offset
        return self._clamp(remaining_load, 0.0, self.MAX_GRID_USAGE_KW)

    def generate_state(self) -> BuildingState:
        """
        Advance the simulation by one cycle, generating a new, internally
        consistent BuildingState.

        Returns:
            The newly generated BuildingState (also stored on self.state).
        """
        self._advance_time()

        outside_temperature = self._simulate_outside_temperature()
        temperature = self._simulate_indoor_temperature(outside_temperature)
        occupancy = self._simulate_occupancy()
        solar_generation = self._simulate_solar_generation()
        battery_level = self._simulate_battery_level(solar_generation)
        lighting_level = self._simulate_lighting_level()
        grid_energy_usage = self._simulate_grid_energy_usage(
            solar_generation, battery_level
        )

        self.state = BuildingState(
            temperature=round(temperature, 2),
            outside_temperature=round(outside_temperature, 2),
            occupancy=occupancy,
            solar_generation=round(solar_generation, 2),
            battery_level=round(battery_level, 2),
            grid_energy_usage=round(grid_energy_usage, 2),
            lighting_level=round(lighting_level, 2),
            hvac_mode=self.state.hvac_mode,
            timestamp=self._simulated_time,
        )
        return self.state

    def apply_action(self, action: str) -> BuildingState:
        """
        Apply a high-level control action to the current building state.
        Unrecognised actions are ignored (state is returned unchanged)
        rather than raising, so a single bad LLM response cannot crash
        the control loop.

        Args:
            action: The name of the action to apply, e.g. "Increase Cooling".

        Returns:
            The updated BuildingState after applying the action.
        """
        normalized_action = action.strip().lower()

        action_handlers = {
            "increase cooling": self._action_increase_cooling,
            "increase heating": self._action_increase_heating,
            "reduce hvac": self._action_reduce_hvac,
            "turn off hvac": self._action_turn_off_hvac,
            "turn off lights": self._action_turn_off_lights,
            "turn on lights": self._action_turn_on_lights,
            "use solar": self._action_use_solar,
            "use battery": self._action_use_battery,
            "charge battery": self._action_charge_battery,
            "eco mode": self._action_eco_mode,
            "no action": lambda: None,
        }

        handler = action_handlers.get(normalized_action)
        if handler is not None:
            handler()
        # Unknown actions are intentionally no-ops; the caller can decide
        # how to log/report them.

        return self.state

    def _action_increase_cooling(self) -> None:
        """Set HVAC to cooling mode to bring temperature down."""
        self.state.hvac_mode = HVACMode.COOLING

    def _action_increase_heating(self) -> None:
        """Set HVAC to heating mode to bring temperature up."""
        self.state.hvac_mode = HVACMode.HEATING

    def _action_reduce_hvac(self) -> None:
        """Switch HVAC to a low-energy eco mode."""
        self.state.hvac_mode = HVACMode.ECO

    def _action_turn_off_hvac(self) -> None:
        """Turn HVAC off entirely."""
        self.state.hvac_mode = HVACMode.OFF

    def _action_turn_off_lights(self) -> None:
        """Turn building lighting off."""
        self.state.lighting_level = 0.0

    def _action_turn_on_lights(self) -> None:
        """Turn building lighting on to a comfortable level."""
        self.state.lighting_level = 70.0

    def _action_use_solar(self) -> None:
        """
        Prioritise solar power: reduces effective grid draw to reflect
        routing available solar generation directly to building load.
        """
        offset = min(self.state.grid_energy_usage, self.state.solar_generation)
        self.state.grid_energy_usage = self._clamp(
            self.state.grid_energy_usage - offset, 0.0, self.MAX_GRID_USAGE_KW
        )

    def _action_use_battery(self) -> None:
        """Draw from the battery to offset grid usage, if charge allows."""
        if self.state.battery_level > 20.0:
            offset = min(self.state.grid_energy_usage, 1.5)
            self.state.grid_energy_usage = self._clamp(
                self.state.grid_energy_usage - offset, 0.0, self.MAX_GRID_USAGE_KW
            )
            self.state.battery_level = self._clamp(
                self.state.battery_level - 2.0, 0.0, 100.0
            )

    def _action_charge_battery(self) -> None:
        """Route additional power toward charging the battery."""
        self.state.battery_level = self._clamp(
            self.state.battery_level + 3.0, 0.0, 100.0
        )

    def _action_eco_mode(self) -> None:
        """Apply a broad energy-saving posture across HVAC and lighting."""
        self.state.hvac_mode = HVACMode.ECO
        self.state.lighting_level = self._clamp(
            self.state.lighting_level * 0.7, 0.0, 100.0
        )

    def reset(self) -> BuildingState:
        """
        Reset the simulator back to its initial state.

        Returns:
            The freshly reset BuildingState.
        """
        self._simulated_time = datetime.utcnow()
        self.state = self._initial_state()
        return self.state
