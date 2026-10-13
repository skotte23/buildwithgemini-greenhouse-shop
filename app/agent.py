# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors.agent_engine_sandbox_code_executor import AgentEngineSandboxCodeExecutor
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.adk.tools.tool_context import ToolContext
from google.cloud import firestore, storage
from google.genai import Client as GenAIClient
from google.genai import types

# Hardcoded GCP project ID and Cloud Storage bucket as strings
PROJECT_ID = "qwiklabs-gcp-03-d7db40a06675"
GCS_BUCKET_NAME = "greenhouse-shop-qwiklabs-gcp-03-d7db40a06675"
AGENT_ENGINE_ID = "projects/876298957881/locations/us-east1/reasoningEngines/1791919179763286016"
MEMORY_BANK_ID = "1791919179763286016"
SANDBOX_RESOURCE_NAME = "projects/876298957881/locations/us-east1/reasoningEngines/1791919179763286016/sandboxEnvironments/4954707258014433280"
MODEL = "gemini-3.8-flash"
IMAGE_MODEL = "gemini-3.1-flash-lite-image"


# WRITE: after each turn, send the session to Memory Bank for extraction.
async def generate_memories_callback(callback_context: CallbackContext):
    await callback_context.add_session_to_memory()
    return None

# Lazy-initialized Firestore client
_db: Optional[firestore.Client] = None


def get_firestore_client() -> firestore.Client:
    global _db
    if _db is None:
        _db = firestore.Client(project=PROJECT_ID)
    return _db


def list_plants(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """List plants from the inventory, optionally filtered by category ('indoor' or 'outdoor').

    Args:
        category: Optional category filter ('indoor' or 'outdoor').

    Returns:
        A list of plant documents matching the query.
    """
    db = get_firestore_client()
    plants_ref = db.collection("plants")
    if category:
        query = plants_ref.where("category", "==", category.lower())
        docs = query.stream()
    else:
        docs = plants_ref.stream()

    return [doc.to_dict() for doc in docs]


def get_plant_details(plant_id: str) -> Dict[str, Any]:
    """Retrieve detailed information for a specific plant by its unique ID.

    Args:
        plant_id: Unique slug/ID of the plant (e.g. 'monstera-deliciosa', 'snake-plant').

    Returns:
        The plant document dictionary or error message if not found.
    """
    db = get_firestore_client()
    doc_ref = db.collection("plants").document(plant_id.lower().strip())
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    return {"error": f"Plant with ID '{plant_id}' was not found in the inventory."}


def search_plants_by_care(
    care_level: Optional[str] = None,
    pet_friendly: Optional[bool] = None,
) -> List[Dict[str, Any]]:
    """Find plants by care difficulty ('easy', 'moderate', 'difficult') and pet friendliness.

    Args:
        care_level: Optional care difficulty ('easy', 'moderate', 'difficult').
        pet_friendly: Optional boolean flag whether the plant is safe for pets.

    Returns:
        List of matching plant records.
    """
    db = get_firestore_client()
    plants = [doc.to_dict() for doc in db.collection("plants").stream()]

    results = []
    for plant in plants:
        if care_level and plant.get("care_level", "").lower() != care_level.lower():
            continue
        if pet_friendly is not None and plant.get("pet_friendly") != pet_friendly:
            continue
        results.append(plant)
    return results


def add_or_update_plant(
    plant_id: str,
    name: str,
    category: str,
    price: float,
    care_level: str,
    light: str,
    watering: str,
    pet_friendly: bool,
    description: str,
    stock: int,
) -> Dict[str, Any]:
    """Add a new plant or update an existing plant in the Firestore inventory.

    Args:
        plant_id: Unique identifier for the plant (e.g. 'pothos-golden').
        name: Common name of the plant.
        category: 'indoor' or 'outdoor'.
        price: Price in USD.
        care_level: 'easy', 'moderate', or 'difficult'.
        light: Sunlight requirement description.
        watering: Watering schedule/instruction.
        pet_friendly: Whether the plant is safe for dogs/cats.
        description: Botanical description and care overview.
        stock: Current available inventory quantity.

    Returns:
        A confirmation dictionary indicating success.
    """
    db = get_firestore_client()
    clean_id = plant_id.lower().strip().replace(" ", "-")
    data = {
        "id": clean_id,
        "name": name,
        "category": category.lower(),
        "price": float(price),
        "care_level": care_level.lower(),
        "light": light,
        "watering": watering,
        "pet_friendly": bool(pet_friendly),
        "description": description,
        "stock": int(stock),
    }
    db.collection("plants").document(clean_id).set(data)
    return {"status": "success", "message": f"Plant '{name}' ({clean_id}) saved to inventory.", "plant": data}


def update_plant_stock(plant_id: str, quantity_change: int) -> Dict[str, Any]:
    """Adjust the inventory stock level of a plant (e.g. after a purchase or restock).

    Args:
        plant_id: The ID of the plant.
        quantity_change: Positive integer to restock, or negative integer for purchase.

    Returns:
        Result dictionary with the updated stock count.
    """
    db = get_firestore_client()
    clean_id = plant_id.lower().strip()
    doc_ref = db.collection("plants").document(clean_id)
    doc = doc_ref.get()
    if not doc.exists:
        return {"error": f"Plant '{plant_id}' not found."}

    current_stock = doc.to_dict().get("stock", 0)
    new_stock = max(0, current_stock + quantity_change)
    doc_ref.update({"stock": new_stock})
    return {"status": "success", "plant_id": clean_id, "previous_stock": current_stock, "new_stock": new_stock}


def calculate_soil_and_potting_mix(
    pot_diameter_inches: float,
    plant_type: str = "general",
) -> Dict[str, Any]:
    """Calculate the estimated potting soil volume and recommended soil mix recipe for a pot size.

    Args:
        pot_diameter_inches: Top diameter of the pot in inches (e.g. 6, 8, 10, 12).
        plant_type: Type of plant (e.g. 'monstera', 'aroid', 'succulent', 'snake plant', 'fern', 'general').

    Returns:
        Dictionary with soil volume in quarts/liters and recommended recipe breakdown.
    """
    import math

    # Standard tapered pot height is ~ 0.9 * diameter. Volume of cylinder approximation in cubic inches:
    radius = pot_diameter_inches / 2.0
    height = pot_diameter_inches * 0.85
    cubic_inches = math.pi * (radius**2) * height
    quarts = round(cubic_inches / 57.75, 2)
    liters = round(quarts * 0.946353, 2)

    plant_key = plant_type.lower()
    if any(k in plant_key for k in ["succulent", "cactus", "snake"]):
        mix = "50% potting soil, 30% perlite or pumice, 20% coarse sand (high drainage)"
    elif any(k in plant_key for k in ["monstera", "aroid", "philodendron", "fig"]):
        mix = "40% potting soil, 30% orchid bark, 20% perlite, 10% worm castings (chunky, airy)"
    elif any(k in plant_key for k in ["fern", "calathea", "spider"]):
        mix = "60% potting soil, 20% peat moss/coco coir, 20% perlite (moisture retentive)"
    else:
        mix = "70% high-quality potting mix, 30% perlite (general all-purpose)"

    return {
        "pot_diameter_inches": pot_diameter_inches,
        "volume_quarts": quarts,
        "volume_liters": liters,
        "recommended_recipe": mix,
    }


def get_local_plant_growing_conditions(city_name: str) -> Dict[str, Any]:
    """Fetch current real-world humidity, temperature, and sunlight conditions for a city
    using the free Open-Meteo API to determine plant growing and watering suitability.

    Args:
        city_name: City name (e.g. 'Austin', 'Seattle', 'London', 'San Francisco').

    Returns:
        Dictionary containing humidity, temperature in F and C, UV index, and plant advice.
    """
    import urllib.parse
    import urllib.request
    import json

    # 1. Geocode city name to lat/long
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(city_name)}&count=1&language=en&format=json"
    req = urllib.request.Request(geo_url, headers={"User-Agent": "GreenhouseShop/1.0"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        geo_data = json.loads(resp.read().decode())

    results = geo_data.get("results")
    if not results:
        return {"error": f"Could not find geographic location for '{city_name}'."}

    loc = results[0]
    lat = loc["latitude"]
    lon = loc["longitude"]
    resolved_name = f"{loc.get('name')}, {loc.get('admin1', loc.get('country', ''))}"

    # 2. Fetch current weather and humidity
    weather_url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,relative_humidity_2m,uv_index&timezone=auto"
    )
    req_w = urllib.request.Request(weather_url, headers={"User-Agent": "GreenhouseShop/1.0"})
    with urllib.request.urlopen(req_w, timeout=5) as resp_w:
        w_data = json.loads(resp_w.read().decode())

    current = w_data.get("current", {})
    temp_c = current.get("temperature_2m")
    temp_f = round((temp_c * 9 / 5) + 32, 1) if temp_c is not None else None
    humidity = current.get("relative_humidity_2m")
    uv = current.get("uv_index")

    # Botanical humidity guidance
    if humidity is not None:
        if humidity < 40:
            humidity_rating = "Low / Dry (Aroids & ferns may need misting or pebble trays)"
        elif humidity <= 60:
            humidity_rating = "Moderate / Ideal for most common houseplants"
        else:
            humidity_rating = "High / Excellent for tropicals, monsteras, and ferns"
    else:
        humidity_rating = "Unknown"

    return {
        "city": resolved_name,
        "temperature_fahrenheit": temp_f,
        "temperature_celsius": temp_c,
        "relative_humidity_percent": humidity,
        "uv_index": uv,
        "climate_assessment": humidity_rating,
    }


def geocode_address(address: str) -> Dict[str, Any]:
    """Convert a postal address or location query into geographic coordinates (latitude, longitude)
    using the Google Maps Geocoding API.

    Args:
        address: Street address, landmark, or city (e.g. '1600 Amphitheatre Pkwy, Mountain View, CA').

    Returns:
        Dictionary containing formatted address, latitude, and longitude.
    """
    import os
    import json
    import urllib.parse
    import urllib.request

    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY environment variable is not set."}

    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={urllib.parse.quote(address)}&key={api_key}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        return {"error": f"Failed to connect to Geocoding API: {e}"}

    if data.get("status") != "OK" or not data.get("results"):
        return {"error": f"Geocoding failed with status: {data.get('status')}", "message": data.get("error_message")}

    first_result = data["results"][0]
    loc = first_result.get("geometry", {}).get("location", {})
    return {
        "formatted_address": first_result.get("formatted_address"),
        "latitude": loc.get("lat"),
        "longitude": loc.get("lng"),
    }


def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "florist",
    radius_meters: float = 3000.0,
    max_results: int = 5,
) -> List[Dict[str, Any]]:
    """Search for nearby places of a specific type around given coordinates using the Places API (New).

    Args:
        latitude: Center latitude coordinate.
        longitude: Center longitude coordinate.
        place_type: Type of place to search for (e.g. 'florist', 'park', 'cafe', 'store', 'garden_center').
        radius_meters: Search radius in meters (default 3000.0).
        max_results: Maximum number of results to return (max 20).

    Returns:
        List of nearby places with name, formatted address, and location coordinates.
    """
    import os
    import json
    import urllib.request

    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
    if not api_key:
        return [{"error": "GOOGLE_MAPS_API_KEY environment variable is not set."}]

    endpoint = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
    }
    payload = {
        "includedTypes": [place_type],
        "maxResultCount": min(max_results, 20),
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": float(latitude),
                    "longitude": float(longitude),
                },
                "radius": float(radius_meters),
            }
        },
    }

    req = urllib.request.Request(endpoint, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        return [{"error": f"Failed to call Places API: {e}"}]

    places = []
    for p in data.get("places", []):
        name = p.get("displayName", {}).get("text", "")
        address = p.get("formattedAddress", "")
        location = p.get("location", {})
        places.append({
            "name": name,
            "address": address,
            "location": location,
        })
    return places


async def generate_plant_image(
    plant_name: str,
    setting_description: str = "in a bright living room in a modern ceramic planter",
    tool_context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """Generate a photo-realistic visual preview for a plant using the gemini-3.1-flash-lite-image model.
    Saves the image as a session artifact and uploads it to the public Cloud Storage bucket.

    Args:
        plant_name: Name of the plant to generate (e.g. 'Monstera Deliciosa', 'Snake Plant', 'Boston Fern').
        setting_description: Scene or setting description (e.g. 'on a wooden plant stand by a sunny window').
        tool_context: ADK ToolContext injected automatically by the framework.

    Returns:
        Dictionary containing the public image URL, bucket details, and confirmation message.
    """
    import uuid

    clean_slug = plant_name.lower().replace(" ", "_").replace("-", "_")
    image_filename = f"{clean_slug}_{uuid.uuid4().hex[:8]}.jpg"
    full_prompt = f"Professional studio photography of a healthy, vibrant {plant_name} plant {setting_description}, natural soft daylight, botanical showcase, 4k."

    # 1. Generate image using gemini-3.1-flash-lite-image in global region
    genai_client = GenAIClient(vertexai=True, project=PROJECT_ID, location="global")
    response = genai_client.models.generate_content(
        model=IMAGE_MODEL,
        contents=full_prompt,
    )

    image_bytes = None
    mime_type = "image/jpeg"
    if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.data:
                image_bytes = part.inline_data.data
                if part.inline_data.mime_type:
                    mime_type = part.inline_data.mime_type
                break

    if not image_bytes:
        return {"error": "Failed to generate image bytes from image model."}

    # 2. Save image as an artifact in ToolContext for Playground Artifacts panel
    artifact_saved = False
    if tool_context is not None:
        try:
            artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            await tool_context.save_artifact(filename=image_filename, artifact=artifact_part)
            artifact_saved = True
        except Exception as e:
            # Continue even if runner doesn't have ArtifactService enabled
            print(f"Warning saving artifact: {e}")

    # 3. Upload same image bytes to public Cloud Storage bucket
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(f"plant_previews/{image_filename}")
    blob.upload_from_string(image_bytes, content_type=mime_type)
    public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/plant_previews/{image_filename}"

    return {
        "status": "success",
        "plant_name": plant_name,
        "filename": image_filename,
        "artifact_saved": artifact_saved,
        "image_url": public_url,
        "markdown_display": f"![{plant_name}]({public_url})",
    }


root_agent = Agent(
    name="greenhouse_shop_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=(
        "You are the expert botanical concierge for Greenhouse Shop. "
        "You help customers find houseplants suited to their lighting conditions, pet safety needs, "
        "and experience level. You have direct access to our live Firestore plant inventory to check "
        "availability, care requirements, pricing, and stock levels. You can calculate potting soil volume "
        "and recipes, query live environmental conditions for any city, find nearby plant nurseries and florists, "
        "and generate photorealistic visual previews of plants in home settings. When an image is generated, "
        "always include its public image markdown link in your response so the user can see it. "
        "You remember the customer's stated preferences, skill level, home environment details, pet ownership, and facts "
        "from previous conversations and use them to personalize your recommendations. "
        "\n\n# Code Execution:\n"
        "You have access to an isolated Agent Platform Python code execution sandbox. Whenever complex "
        "mathematical modeling, growth projections, custom soil chemistry ratios, fertilizer dilutions, or data calculations "
        "are needed or requested, write executable Python code inside a ```tool_code ... ``` or ```python ... ``` block. "
        "Always print results with print(...) so output is captured and returned. "
        "After code execution, summarize the findings clearly for the customer. "
        "Always provide welcoming and knowledgeable botanical advice."
    ),
    code_executor=AgentEngineSandboxCodeExecutor(
        sandbox_resource_name=SANDBOX_RESOURCE_NAME,
    ),
    tools=[
        PreloadMemoryTool(),
        list_plants,
        get_plant_details,
        search_plants_by_care,
        add_or_update_plant,
        update_plant_stock,
        calculate_soil_and_potting_mix,
        get_local_plant_growing_conditions,
        geocode_address,
        find_nearby_places,
        generate_plant_image,
    ],
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)

