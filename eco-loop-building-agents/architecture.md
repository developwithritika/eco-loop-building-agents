# Architecture: Eco-Loop Building Agents

This document describes the internal architecture of the Eco-Loop
Building Agents system: how each layer is structured, what it owns, and
how data flows through the full feedback loop.

## High-Level Flow

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

The system is a closed control loop. At every cycle:

1. The simulation advances, producing a new `BuildingState`.
2. That state is handed to the LLM agent.
3. The agent returns a single decision (an action plus a reason).
4. The decision engine validates the action and applies it back onto
   the simulation, mutating the building's state.
5. The loop repeats, so the building's trajectory is shaped by the
   cumulative effect of every past decision.

## Simulation Layer (`simulator.py`)

**Responsibility:** own the ground-truth physical and energy state of
the building, and know how to advance it realistically over time.

- `BuildingSimulator` holds a single `BuildingState` instance.
- `generate_state()` advances the simulation by one cycle. Each
  variable (indoor temperature, outdoor temperature, occupancy, solar
  generation, battery level, lighting, grid usage) is updated using a
  bounded random walk, with some variables also depending on
  time-of-day (solar generation, occupancy) and on other variables in
  the same cycle (indoor temperature depends on outdoor temperature and
  current HVAC mode; grid usage depends on HVAC, lighting, and
  occupancy).
- `apply_action(action)` maps a named action (e.g. `"Increase
  Cooling"`) onto concrete state mutations, such as switching
  `hvac_mode` or discharging the battery. Unknown actions are treated
  as no-ops rather than errors, so a single bad decision from the LLM
  layer cannot crash the simulation.
- `reset()` returns the simulator to a fresh, plausible initial state.
- All values are clamped to physically realistic ranges (e.g.
  temperature between 10C and 40C, battery between 0% and 100%) so the
  simulation never drifts into nonsensical territory.

This layer has no dependency on FastAPI or the LLM SDK — it is pure
Python and fully unit-testable in isolation.

## API Layer (`server.py`)

**Responsibility:** expose the simulation over HTTP so it can be
observed or controlled by any client — the bundled controller, a
dashboard, or an external MCP-compatible agent.

- Built with FastAPI, using the shared Pydantic models from
  `models.py` for request and response validation.
- `GET /state` returns the current `BuildingState` without mutating it.
- `POST /action` accepts an `ActionRequest`, applies it via
  `BuildingSimulator.apply_action()`, and returns an `ActionResponse`
  containing both the applied action and the resulting state.
- `GET /health` provides a minimal liveness endpoint suitable for
  container orchestration or uptime monitoring.
- A single process-wide `BuildingSimulator` instance backs the API.
  This keeps the example simple; a production system would instead key
  simulator instances by building ID in a registry or database.

This layer is intentionally thin: it performs no decision-making of its
own and delegates all physical logic to the simulation layer.

## LLM Layer (`llm.py`)

**Responsibility:** turn a `BuildingState` into a single, well-formed
control decision, using a language model as the reasoning engine.

- `LLMAgent` wraps an OpenAI-compatible chat completion client.
- The system prompt fixes the agent's optimisation priorities, in
  order: occupant comfort, minimum electricity cost, renewable energy
  usage, and battery optimisation. It also enumerates the closed set of
  valid actions and the reasoning heuristics the agent should apply
  (e.g. cool when hot and occupied, turn off lights when empty, prefer
  solar when abundant).
- The agent is instructed to respond with **only** a JSON object of the
  shape `{"action": "...", "reason": "..."}` — no markdown, no
  commentary — which keeps downstream parsing simple and reliable.
- `_extract_json()` defensively strips stray code fences and pulls out
  the first `{...}` block before parsing, tolerating minor formatting
  slips from the model.
- If the API call fails, times out, returns malformed JSON, or invents
  an action outside the allowed vocabulary, `decide()` transparently
  falls back to `_fallback_decision()` — a deterministic, rule-based
  implementation of the same heuristics given to the LLM. This
  guarantees the control loop always receives a valid decision, with or
  without a working LLM connection.

## Decision Layer (`controller.py` + `simulator.py.apply_action`)

**Responsibility:** connect the LLM's chosen action back to a concrete
state mutation, and orchestrate the end-to-end loop.

- `BuildingController` owns its own `BuildingSimulator` and
  `LLMAgent` instances (independent from the ones used by the API
  server, since the controller is designed to also run standalone).
- `run_single_cycle()` performs one full iteration: generate state,
  request a decision, apply the decision, and print a clearly formatted
  log of the current state, the decision and its reason, and the
  resulting updated state.
- `run_forever()` repeats `run_single_cycle()` on a fixed interval
  (`CONTROLLER_INTERVAL_SECONDS`, default 5 seconds), and can be
  stopped cleanly with `Ctrl+C`.
- Validation of the action against the allowed vocabulary happens
  inside `LLMAgent.decide()`, before the decision ever reaches the
  simulator — the decision layer is therefore split across the LLM
  layer (validation) and the simulation layer (physical effect), with
  the controller purely orchestrating the sequence.

## Feedback Loop

The defining property of this architecture is that it is a **closed
loop**, not a single request/response cycle:

```
state_t -> LLM decision -> action applied -> state_(t+1) -> LLM decision -> ...
```

Each decision changes the building's `hvac_mode`, `lighting_level`,
`battery_level`, or `grid_energy_usage`, and those changes feed directly
into how the simulation evolves on the next cycle (for example, cooling
mode actively lowers indoor temperature in the next
`generate_state()` call). This means the LLM agent's decisions have
lasting, compounding effects on the building — much like a real
building management system — rather than being evaluated against a
static, unchanging environment.

## Configuration (`config.py`)

All tunable values and secrets are loaded from environment variables via
`python-dotenv`, exposed through a single immutable `Settings`
dataclass (`settings`). No API keys or environment-specific values are
hardcoded anywhere in the codebase; `.env.example` documents every
supported variable.

## Data Contracts (`models.py`)

All cross-layer data exchange uses Pydantic models defined once and
shared everywhere:

- `BuildingState` — the full observable state of the building.
- `ActionRequest` / `ActionResponse` — the API's action contract.
- `LLMDecision` — the strict schema the LLM agent's JSON output is
  parsed into, and the same schema used by the rule-based fallback.

Centralising these models in one module guarantees that the simulator,
the LLM agent, the API layer, and the controller all agree on exactly
the same shape of data, eliminating an entire class of integration bugs.
