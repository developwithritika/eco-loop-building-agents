# Eco-Loop Building Agents – System Architecture

## 1. Overview

Eco-Loop Building Agents is an AI-powered proof-of-concept that demonstrates autonomous energy management for a smart building using a closed-loop control architecture.

The system continuously monitors simulated building conditions, evaluates them using a Large Language Model (LLM), recommends optimal control actions, and applies those actions back to the building state.

The objective is to improve operational efficiency while maintaining occupant comfort.

---

# 2. Problem Statement

Commercial buildings consume a significant amount of energy due to inefficient operation of lighting, HVAC systems, and other electrical loads.

Traditional building automation systems rely on predefined rules that cannot adapt well to changing environmental conditions.

This project demonstrates how an AI agent can continuously analyse building conditions and make intelligent control decisions in real time.

---

# 3. System Components

The application consists of six primary modules.

## 3.1 Building Simulator

**File**

```
simulator.py
```

Responsibilities

- Simulates building conditions
- Generates environmental data
- Maintains current building state
- Updates values after control actions

Example parameters include:

- Indoor temperature
- Outside temperature
- Occupancy
- Solar generation
- Battery level
- Grid energy usage
- Lighting level
- HVAC mode

---

## 3.2 FastAPI Server

**File**

```
server.py
```

Responsibilities

- Provides REST API endpoints
- Exposes current building state
- Receives AI control actions
- Allows external applications to interact with the simulation

Endpoints

GET /state

Returns current building information.

POST /action

Applies AI-generated actions.

GET /health

Returns server health status.

---

## 3.3 LLM Decision Engine

**File**

```
llm.py
```

Responsibilities

- Converts building state into a structured prompt
- Sends prompt to the language model
- Receives reasoning
- Produces recommended control actions

Typical decisions include

- Turn lights on
- Turn lights off
- Increase HVAC
- Reduce HVAC
- Maintain current state

---

## 3.4 Controller

**File**

```
controller.py
```

Responsibilities

- Reads current building state
- Invokes the LLM
- Applies returned action
- Updates simulator
- Repeats continuously

The controller forms the core autonomous feedback loop.

---

## 3.5 Configuration

**File**

```
config.py
```

Stores application configuration such as

- API keys
- Simulation parameters
- Default settings

---

## 3.6 Data Models

**File**

```
models.py
```

Defines the request and response models used by the FastAPI application.

This ensures consistent communication between different components.

---

# 4. Closed-Loop Workflow

The complete execution pipeline is shown below.

```
Building Simulator
        │
        ▼
Generate Building State
        │
        ▼
FastAPI Server
        │
        ▼
LLM Decision Engine
        │
        ▼
Recommended Action
        │
        ▼
Controller
        │
        ▼
Updated Building State
        │
        ▼
Repeat
```

The cycle executes continuously throughout the simulation.

---

# 5. AI Decision Process

The LLM analyses several building parameters before selecting an action.

These include:

- Indoor temperature
- Outdoor temperature
- Occupancy
- Lighting level
- Solar generation
- Battery level
- Grid energy consumption
- HVAC mode

The language model evaluates these values and returns both:

- Recommended action
- Explanation for the decision

Example

Current State

Occupancy = 0

Lighting = 25%

Decision

Turn Off Lights

Reason

The building is currently unoccupied, therefore lighting is unnecessary.

---

# 6. Prompt Engineering Strategy

The language model receives a structured prompt containing:

- Current building metrics
- Operating constraints
- Available control actions

The prompt instructs the model to:

1. Analyse the building state.
2. Recommend one control action.
3. Explain the reasoning.
4. Avoid unnecessary actions.

This structured format improves response consistency and simplifies parsing.

---

# 7. API Design

The REST API enables communication between external applications and the simulator.

Current endpoints

| Endpoint | Method | Purpose |
|----------|---------|----------|
| /state | GET | Returns current building state |
| /action | POST | Applies AI action |
| /health | GET | Returns service status |

The API is implemented using FastAPI.

---

# 8. Prompt Latency Management

The system minimises unnecessary LLM requests by:

- Processing one simulation cycle at a time
- Using compact prompts
- Returning structured responses
- Avoiding repeated requests for unchanged states

This keeps inference latency low while maintaining responsiveness.

---

# 9. Error Handling

The application includes basic safeguards for:

- Invalid API requests
- Missing configuration
- Invalid actions
- Unexpected LLM responses

FastAPI validation prevents malformed requests from reaching the controller.

---

# 10. Scalability

The modular architecture allows individual components to be replaced independently.

Possible future extensions include:

- Multiple buildings
- IoT sensor integration
- Database storage
- Real-time dashboards
- Cloud deployment
- Multi-agent coordination

---

# 11. Future EnergyPlus Integration

The current implementation uses a lightweight Python simulator to demonstrate the autonomous control pipeline.

The simulator is intentionally isolated behind a modular interface.

In future versions, the simulator can be replaced by an EnergyPlus API wrapper that:

- Loads .idf building models
- Streams simulation metrics
- Accepts AI-generated control actions
- Executes real EnergyPlus simulations
- Measures actual energy savings

This preserves the existing controller and LLM logic while upgrading the simulation engine.

---

# 12. Current Limitations

Current implementation limitations include:

- Python-based simulator instead of EnergyPlus
- No live IoT devices
- No historical database
- No graphical dashboard
- Single-building simulation
- Cloud deployment not included

These limitations were intentionally accepted to rapidly demonstrate the autonomous AI control architecture.

---

# 13. Conclusion

Eco-Loop Building Agents demonstrates a complete closed-loop AI control pipeline for intelligent building energy management.

The project integrates:

- Building simulation
- REST APIs
- Large Language Models
- Autonomous control
- Continuous feedback

The modular architecture allows future integration with EnergyPlus, open-source LLMs, dashboards, and real-world building management systems with minimal architectural changes.