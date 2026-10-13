# Greenhouse Shop 🌿

A botanical concierge AI agent built with Google Agent Development Kit (ADK) and Gemini, providing plant care recommendations, inventory management, soil calculations, local weather insights, nursery discovery, and photorealistic plant previews.

---

## Capabilities & Integrations

The agent integrates the following Google Cloud and external services:

### 1. Vertex AI Memory Bank (Long-Term Memory)
- **Service:** Vertex AI Memory Bank (`VertexAiMemoryBankService`)
- **Capabilities:**
  - Employs `PreloadMemoryTool` to load past user context at session start.
  - Automatically captures and writes user facts, preferences (gardening experience, home light conditions, pet ownership) into Memory Bank across turns via `after_agent_callback`.

### 2. Google Cloud Firestore (Live Inventory Management)
- **Service:** Cloud Firestore
- **Functions:**
  - `list_plants`: Queries plant inventory, optionally filtered by category (`indoor` / `outdoor`).
  - `get_plant_details`: Fetches full botanical details, light needs, watering schedule, and pricing.
  - `search_plants_by_care`: Filters plants by care difficulty (`easy`, `moderate`, `difficult`) and pet safety (`pet_friendly`).
  - `add_or_update_plant`: Adds or modifies plant records in the Firestore catalog.
  - `update_plant_stock`: Manages stock counts after purchases or restocks.

### 3. Google Cloud Storage & Gemini Image Generation
- **Models & Services:** `gemini-3.1-flash-lite-image` on Vertex AI + Google Cloud Storage
- **Functions:**
  - `generate_plant_image`: Generates photorealistic plant previews in home settings.
  - Saves generated images as ADK session artifacts via `ToolContext`.
  - Automatically uploads image bytes to a public Cloud Storage bucket and returns public URLs embedded directly in markdown.

### 4. Agent Engine Python Code Execution Sandbox
- **Service:** `AgentEngineSandboxCodeExecutor`
- **Capabilities:**
  - Runs Python in a secure, isolated sandbox for calculating complex soil volumes, fertilizer dilutions, and custom potting mix formulations.

### 5. Google Maps Geocoding & Places (New) APIs
- **Functions:**
  - `geocode_address`: Converts physical addresses or landmarks into latitude/longitude coordinates via Google Maps Geocoding REST API.
  - `find_nearby_places`: Searches for nearby local florists, nurseries, and garden centers using the Places API (New) with circle location restrictions.

### 6. Environmental & Growing Conditions (Open-Meteo API)
- **Functions:**
  - `get_local_plant_growing_conditions`: Geocodes city names and fetches live humidity, temperature, and UV index to provide real-time plant watering and care advice.

### 7. Custom Web Frontend & A2A Proxy
- **Stack:** FastAPI proxy + HTML5/CSS/JS frontend located in `frontend/`
- **Protocol:** Communicates with the deployed Agent Engine runtime using the Agent2Agent (A2A) protocol.
- **UI Support:** Features built-in rendering for chat messages, markdown images, and A2UI card payloads.

---

## Status of Planned Features

- **Vertex AI Memory Bank:** Implemented
- **Firestore Inventory:** Implemented
- **Cloud Storage Image Storage:** Implemented
- **Gemini Image Generation:** Implemented
- **Agent Sandbox Code Execution:** Implemented
- **Google Maps Geocoding & Places (New):** Implemented
- **FastAPI Chat Frontend (A2A):** Implemented
- **Agent-side A2UI Card Synthesis (`enable-a2ui`):** *Planned, not yet implemented* (The agent currently formats responses in rich Markdown; frontend A2UI card renderer is ready for agent-emitted A2UI events).

---

## Local Setup & Run

### Prerequisites
- Python 3.11+
- Google Cloud CLI (`gcloud`) authenticated with Application Default Credentials:
  ```bash
  gcloud auth application-default login
  ```
- Google Maps API key (set in `.env` as `GOOGLE_MAPS_API_KEY`)

### 1. Running the Agent Backend (ADK Playground)
From the project root:
```bash
uv run adk web . --port 8080 --reload_agents
```

### 2. Running the Frontend Proxy & Chat UI
From the `frontend/` directory:
```bash
cd frontend
pip install -r requirements.txt
export AGENT_ENGINE_RESOURCE_NAME="projects/<PROJECT_ID>/locations/<REGION>/reasoningEngines/<ENGINE_ID>"
export AGENT_DIRECTORY="app"
python main.py
```
