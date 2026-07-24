# Eco-Loop Building Agents

An AI-powered building energy management system. A simulated smart
building continuously reports its environmental and energy state to an
LLM agent, which chooses actions that reduce energy consumption while
keeping occupants comfortable. The loop repeats indefinitely, closing
the feedback cycle between sensing, reasoning, and control.

## Project Overview

Eco-Loop Building Agents demonstrates a full, working agentic control
system built from four cooperating layers:

1. **Simulation Layer** (`simulator.py`) — generates realistic building
   telemetry (temperature, occupancy, solar generation, battery level,
   grid usage, lighting) and applies control actions to that state.
2. **API Layer** (`server.py`) — a FastAPI service exposing the building
   state and accepting control actions over HTTP, so the building can be
   observed or driven by any external client.
3. **LLM Layer** (`llm.py`) — an agent that prompts an LLM with the
   current building state and receives a single JSON-encoded decision,
   with a deterministic rule-based fallback if the LLM is unavailable.
4. **Decision / Feedback Loop** (`controller.py`) — orchestrates the
   other three layers in a continuous cycle: observe, decide, act, log,
   repeat.

## Architecture

```
Building Simulation
        |
FastAPI / MCP Server
        |
LLM Agent
        |
Decision Engine
        |
Update Building State
        |
     (repeat)
```

See [architecture.md](architecture.md) for a detailed breakdown of each
layer's responsibilities and how they interact.

## Folder Structure

```
eco-loop-building-agents/
|-- simulator.py       Building simulation engine (BuildingSimulator)
|-- llm.py              LLM decision agent (LLMAgent) with rule-based fallback
|-- server.py           FastAPI HTTP server exposing /state and /action
|-- controller.py       Standalone control loop tying everything together
|-- models.py           Pydantic models shared across all layers
|-- config.py           Environment-based configuration (dotenv)
|-- requirements.txt    Python dependencies
|-- .env.example        Template for required environment variables
|-- README.md           This file
|-- architecture.md     Detailed architecture documentation
```

## Installation

### Prerequisites

- Python 3.11 or newer
- An OpenAI-compatible API key (optional — the system runs on a
  rule-based fallback engine if no key is provided)

### Steps

```bash
# 1. Clone or copy the project, then move into it
cd eco-loop-building-agents

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

## Setup: Environment Variables

Copy the example environment file and fill in your own values:

```bash
cp .env.example .env
```

| Variable                       | Description                                             | Default       |
|---------------------------------|-----------------------------------------------------------|---------------|
| `OPENAI_API_KEY`                | API key for the LLM provider (OpenAI-compatible)          | *(required for LLM mode)* |
| `OPENAI_MODEL`                  | Chat completion model used by the agent                   | `gpt-4o-mini` |
| `SERVER_HOST`                   | Host the FastAPI server binds to                           | `0.0.0.0`     |
| `SERVER_PORT`                   | Port the FastAPI server binds to                            | `8000`        |
| `CONTROLLER_INTERVAL_SECONDS`   | Seconds between controller decision cycles                  | `5`           |
| `COMFORT_TEMP_MIN`              | Lower bound of the comfort temperature band (Celsius)        | `20.0`        |
| `COMFORT_TEMP_MAX`              | Upper bound of the comfort temperature band (Celsius)        | `26.0`        |

If `OPENAI_API_KEY` is left empty, `LLMAgent` automatically uses its
built-in deterministic rule-based decision engine, so the whole system
remains fully runnable without any external API access.

## Running the Simulator Standalone

You can exercise the simulator directly in a Python shell to see raw
state transitions without the API or LLM involved:

```bash
python3 -c "
from simulator import BuildingSimulator
sim = BuildingSimulator()
for _ in range(3):
    print(sim.generate_state())
"
```

## Running the API Server

```bash
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

Once running, interactive API docs are available at
`http://localhost:8000/docs`.

### Endpoints

| Method | Path      | Description                                    |
|--------|-----------|-------------------------------------------------|
| GET    | `/state`  | Returns the current building state               |
| POST   | `/action` | Applies a control action, returns updated state  |
| GET    | `/health` | Liveness check                                    |

Example request:

```bash
curl -X POST http://localhost:8000/action \
  -H "Content-Type: application/json" \
  -d '{"action": "Increase Cooling", "reason": "Manual override"}'
```

## Running the Controller (Full Feedback Loop)

The controller runs the simulation, LLM agent, and decision engine
together in a continuous loop, printing each cycle to the console:

```bash
python3 controller.py
```

Press `Ctrl+C` to stop the loop cleanly.

## Sample Output

```
============================================================
CYCLE 1  [14:32:07 UTC]
============================================================
Current State:
    temperature........ 27.40 C
    outside_temp....... 29.10 C
    occupancy.......... 18
    solar_generation... 6.20 kW
    battery_level...... 64.30 %
    grid_energy_usage.. 4.80 kW
    lighting_level..... 55.00 %
    hvac_mode.......... off

LLM Decision:
    action: Increase Cooling
    reason: Indoor temperature exceeds comfort threshold with occupants present.

Updated State:
    temperature........ 27.40 C
    outside_temp....... 29.10 C
    occupancy.......... 18
    solar_generation... 6.20 kW
    battery_level...... 64.30 %
    grid_energy_usage.. 4.80 kW
    lighting_level..... 55.00 %
    hvac_mode.......... cooling
```

## Future Improvements

- Persist building state and decision history to a database for
  long-term analytics and dashboards.
- Add a WebSocket endpoint for live-streaming state updates to a
  front-end dashboard.
- Support multiple simultaneous buildings, each with its own simulator
  and agent instance, coordinated by a shared scheduler.
- Introduce a proper MCP (Model Context Protocol) server wrapper around
  the API so any MCP-compatible agent framework can drive the building.
- Add historical trend analysis so the LLM agent can reason about
  patterns over time, not just the current instantaneous state.
- Add automated tests (pytest) covering simulator physics, action
  handlers, and JSON-parsing edge cases in the LLM agent.
- Support multi-zone buildings with independent HVAC and lighting per
  floor or room.
