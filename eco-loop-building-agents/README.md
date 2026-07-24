# Eco-Loop Building Agents

AI-powered autonomous building energy management system built using Python, FastAPI, and an LLM-based decision engine.

---

## Project Overview

Eco-Loop Building Agents is a proof-of-concept smart building controller that demonstrates how Artificial Intelligence can continuously monitor building conditions and automatically recommend energy-efficient control actions.

The project follows a closed-loop architecture:

1. Collect building state
2. Analyse the state using an LLM
3. Generate an optimal control decision
4. Apply the control action
5. Repeat continuously

The objective is to reduce unnecessary energy consumption while maintaining occupant comfort.

---

## Features

- AI-powered decision making
- Closed-loop control architecture
- Building environment simulator
- FastAPI REST API
- HVAC control
- Smart lighting control
- Battery monitoring
- Solar generation monitoring
- Modular Python architecture
- Easily extendable for real-world building integrations

---

## Architecture

```
                    +----------------------+
                    |  Building Simulator  |
                    +----------------------+
                               |
                               v
                    +----------------------+
                    |  FastAPI REST API    |
                    +----------------------+
                               |
                               v
                    +----------------------+
                    |    LLM Decision      |
                    |      Engine          |
                    +----------------------+
                               |
                               v
                    +----------------------+
                    |   Controller Agent   |
                    +----------------------+
                               |
                               v
                    +----------------------+
                    | Updated Building     |
                    | State                |
                    +----------------------+
```

---

## Project Structure

```
eco-loop-building-agents/

├── controller.py      # Main AI control loop
├── server.py          # FastAPI REST server
├── simulator.py       # Building simulator
├── llm.py             # LLM interaction
├── models.py          # Data models
├── config.py          # Configuration
├── requirements.txt   # Python dependencies
├── architecture.md    # System architecture
├── README.md
└── .env.example
```

---

## Technologies Used

- Python 3.12
- FastAPI
- OpenAI API
- Pydantic
- Uvicorn
- Requests
- Python Dotenv

---

## Installation

Clone the repository

```bash
git clone https://github.com/developwithritika/eco-loop-building-agents.git
```

Move into the project

```bash
cd eco-loop-building-agents
```

Create virtual environment

```bash
python -m venv .venv
```

Activate it

Windows

```bash
.venv\Scripts\activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

---

## Running the API

```bash
uvicorn server:app --reload
```

Server starts at

```
http://127.0.0.1:8000
```

Swagger Documentation

```
http://127.0.0.1:8000/docs
```

---

## Running the Controller

```bash
python controller.py
```

The controller continuously:

- Reads the current building state
- Sends the state to the LLM
- Receives an intelligent decision
- Updates the simulator
- Repeats the process

---

## API Endpoints

### GET /state

Returns the current building status.

Example response

```json
{
  "temperature": 21.5,
  "outside_temperature": 18.3,
  "occupancy": 2,
  "solar_generation": 0,
  "battery_level": 58.5,
  "grid_energy_usage": 0,
  "lighting_level": 7,
  "hvac_mode": "off"
}
```

---

### POST /action

Applies an AI-generated control action.

---

### GET /health

Returns API health status.

---

## Example Controller Output

```
Current State

Temperature : 21.5°C

Occupancy : 0

Lighting : 22%

LLM Decision

Turn Off Lights

Reason

Building is unoccupied.

Updated State

Lighting : 0%
```

---

## Current Workflow

1. Simulator generates building state

2. Controller collects data

3. State is sent to the LLM

4. LLM recommends an action

5. Controller updates simulator

6. Process repeats

---

## Future Improvements

This proof-of-concept has been intentionally designed with a modular architecture.

Future enhancements include:

- EnergyPlus integration
- Importing .idf building models
- Open-source LLM deployment (Llama/Mistral/Qwen)
- MCP server integration
- Live IoT sensor support
- Energy consumption dashboard
- Historical analytics
- Carbon footprint reporting

---

## Limitations

The current implementation uses a lightweight Python-based building simulator instead of a live EnergyPlus simulation engine.

The simulator has been designed as a modular component and can be replaced by an EnergyPlus API wrapper in future versions without modifying the AI controller logic.

---

## Author

**Ritika Roy**

GitHub

https://github.com/developwithritika

---

## License

This project has been created for educational and hackathon purposes.