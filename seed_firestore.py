# Copyright 2026 Google LLC
"""Seed script for greenhouse-shop Firestore collection."""

from google.cloud import firestore

# Hardcoded GCP project ID as a string to avoid project number issues on Agent Platform
PROJECT_ID = "qwiklabs-gcp-03-d7db40a06675"

SAMPLE_PLANTS = [
    {
        "id": "monstera-deliciosa",
        "name": "Monstera Deliciosa",
        "category": "indoor",
        "price": 38.00,
        "care_level": "moderate",
        "light": "bright-indirect",
        "watering": "weekly",
        "pet_friendly": False,
        "description": "Iconic Swiss cheese plant with large, glossy, fenestrated leaves.",
        "stock": 15,
    },
    {
        "id": "snake-plant",
        "name": "Snake Plant (Sansevieria)",
        "category": "indoor",
        "price": 24.50,
        "care_level": "easy",
        "light": "low-to-bright",
        "watering": "bi-weekly",
        "pet_friendly": False,
        "description": "Extremely hardy air-purifying plant that thrives on neglect.",
        "stock": 25,
    },
    {
        "id": "fiddle-leaf-fig",
        "name": "Fiddle Leaf Fig",
        "category": "indoor",
        "price": 55.00,
        "care_level": "difficult",
        "light": "bright-indirect",
        "watering": "weekly",
        "pet_friendly": False,
        "description": "Dramatic statement tree with broad, violin-shaped foliage.",
        "stock": 8,
    },
    {
        "id": "spider-plant",
        "name": "Spider Plant",
        "category": "indoor",
        "price": 18.00,
        "care_level": "easy",
        "light": "medium-indirect",
        "watering": "weekly",
        "pet_friendly": True,
        "description": "Resilient, pet-safe plant with cascading variegated leaves.",
        "stock": 30,
    },
    {
        "id": "boston-fern",
        "name": "Boston Fern",
        "category": "indoor",
        "price": 22.00,
        "care_level": "moderate",
        "light": "filtered-light",
        "watering": "keep-moist",
        "pet_friendly": True,
        "description": "Lush, feathery green fronds perfect for hanging planters.",
        "stock": 12,
    },
    {
        "id": "lavender",
        "name": "English Lavender",
        "category": "outdoor",
        "price": 14.00,
        "care_level": "easy",
        "light": "full-sun",
        "watering": "low",
        "pet_friendly": False,
        "description": "Fragrant purple blooms attracting pollinators and providing relaxing aromas.",
        "stock": 20,
    },
]


def seed_plants():
    db = firestore.Client(project=PROJECT_ID)
    plants_ref = db.collection("plants")
    print(f"Seeding Firestore collection 'plants' in project {PROJECT_ID}...")

    for plant in SAMPLE_PLANTS:
        plant_id = plant["id"]
        plants_ref.document(plant_id).set(plant)
        print(f"  ✓ Seeded: {plant['name']} ({plant_id})")

    print("\n✅ Successfully seeded Firestore 'plants' collection!")


if __name__ == "__main__":
    seed_plants()
