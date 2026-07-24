"""
controller.py
--------------
The orchestration layer that closes the feedback loop:

    Building Simulation -> LLM Agent -> Decision Engine -> Update State -> Repeat

Run standalone with:
    python controller.py
"""

import time
from datetime import datetime

from config import settings
from llm import LLMAgent
from models import BuildingState, LLMDecision
from simulator import BuildingSimulator


class BuildingController:
    """
    Coordinates the simulator and the LLM agent, running a continuous
    control loop that observes state, decides on an action, applies it,
    and logs the full cycle.
    """

    def __init__(self, interval_seconds: int | None = None) -> None:
        """
        Initialise the controller with its own simulator and LLM agent.

        Args:
            interval_seconds: Seconds to wait between control cycles.
                Defaults to the configured CONTROLLER_INTERVAL_SECONDS.
        """
        self.simulator = BuildingSimulator()
        self.agent = LLMAgent()
        self.interval_seconds = interval_seconds or settings.controller_interval_seconds
        self._cycle_count = 0

    @staticmethod
    def _format_state(state: BuildingState) -> str:
        """
        Render a BuildingState as a compact, human-readable log line.

        Args:
            state: The BuildingState to format.

        Returns:
            A formatted multi-line string.
        """
        return (
            f"    temperature........ {state.temperature:.2f} C\n"
            f"    outside_temp....... {state.outside_temperature:.2f} C\n"
            f"    occupancy.......... {state.occupancy}\n"
            f"    solar_generation... {state.solar_generation:.2f} kW\n"
            f"    battery_level...... {state.battery_level:.2f} %\n"
            f"    grid_energy_usage.. {state.grid_energy_usage:.2f} kW\n"
            f"    lighting_level..... {state.lighting_level:.2f} %\n"
            f"    hvac_mode.......... {state.hvac_mode}"
        )

    def run_single_cycle(self) -> None:
        """
        Execute exactly one iteration of the control loop:
        generate state, get a decision, apply it, and log everything.
        """
        self._cycle_count += 1
        cycle_start = datetime.utcnow().strftime("%H:%M:%S")

        print(f"\n{'=' * 60}")
        print(f"CYCLE {self._cycle_count}  [{cycle_start} UTC]")
        print(f"{'=' * 60}")

        current_state = self.simulator.generate_state()
        print("Current State:")
        print(self._format_state(current_state))

        decision: LLMDecision = self.agent.decide(current_state)
        print("\nLLM Decision:")
        print(f"    action: {decision.action}")
        print(f"    reason: {decision.reason}")

        updated_state = self.simulator.apply_action(decision.action)
        print("\nUpdated State:")
        print(self._format_state(updated_state))

    def run_forever(self) -> None:
        """
        Run the control loop indefinitely, sleeping for
        `interval_seconds` between cycles. Interruptible with Ctrl+C.
        """
        print("Starting Eco-Loop Building Agents controller...")
        print(f"Cycle interval: {self.interval_seconds} seconds")
        print("Press Ctrl+C to stop.\n")

        try:
            while True:
                self.run_single_cycle()
                time.sleep(self.interval_seconds)
        except KeyboardInterrupt:
            print("\nController stopped by user. Shutting down cleanly.")


def main() -> None:
    """Entry point for running the controller as a standalone script."""
    controller = BuildingController()
    controller.run_forever()


if __name__ == "__main__":
    main()
