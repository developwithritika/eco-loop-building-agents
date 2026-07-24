"""
config.py
---------
Centralised application configuration for Eco-Loop Building Agents.

All secrets and tunable parameters are loaded from environment variables
via python-dotenv. Nothing sensitive is hardcoded in source code.
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Load variables from a local .env file, if present, into the process
# environment. In production, environment variables should instead be
# injected by the deployment platform (Docker, systemd, CI/CD, etc.).
load_dotenv()


def _get_float(env_name: str, default: float) -> float:
    """
    Safely parse a float environment variable, falling back to a default
    value if the variable is missing or cannot be parsed.

    Args:
        env_name: Name of the environment variable to read.
        default: Value to use if parsing fails or the variable is unset.

    Returns:
        The parsed float value.
    """
    raw_value = os.getenv(env_name)
    if raw_value is None:
        return default
    try:
        return float(raw_value)
    except ValueError:
        return default


def _get_int(env_name: str, default: int) -> int:
    """
    Safely parse an integer environment variable, falling back to a
    default value if the variable is missing or cannot be parsed.

    Args:
        env_name: Name of the environment variable to read.
        default: Value to use if parsing fails or the variable is unset.

    Returns:
        The parsed integer value.
    """
    raw_value = os.getenv(env_name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    """
    Immutable container for application-wide settings.

    Using a frozen dataclass prevents accidental mutation of configuration
    values at runtime, which helps avoid subtle bugs in a long-running
    simulation/control loop.
    """

    # --- LLM provider settings -------------------------------------------------
    openai_api_key: str
    openai_model: str

    # --- Server settings ---------------------------------------------------
    server_host: str
    server_port: int

    # --- Controller loop settings -------------------------------------------------
    controller_interval_seconds: int

    # --- Comfort thresholds (used by the rule-based fallback engine) -------
    comfort_temp_min: float
    comfort_temp_max: float


def load_settings() -> Settings:
    """
    Build a Settings instance from the current environment.

    Returns:
        A populated, immutable Settings object.
    """
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        server_host=os.getenv("SERVER_HOST", "0.0.0.0"),
        server_port=_get_int("SERVER_PORT", 8000),
        controller_interval_seconds=_get_int("CONTROLLER_INTERVAL_SECONDS", 5),
        comfort_temp_min=_get_float("COMFORT_TEMP_MIN", 20.0),
        comfort_temp_max=_get_float("COMFORT_TEMP_MAX", 26.0),
    )


# A single, shared settings instance used throughout the application.
settings = load_settings()
