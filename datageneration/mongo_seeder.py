import os
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pymongo import MongoClient


MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://localhost:27017"
)

DATABASE_NAME = os.getenv(
    "MONGO_DATABASE",
    "bitestream"
)

REFERENCE_FILE = (
    Path(__file__).parent / "seed_reference.json"
)

NUM_REVIEWS = 100_000
NUM_DRIVER_PINGS = 500_000
BATCH_SIZE = 5_000


def load_reference_data():

    import json

    with open(
        REFERENCE_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)


def generate_menus(restaurants):

    menus = []

    for restaurant in restaurants:

        categories = []

        for category_number in range(3):

            items = []

            for item_number in range(8):

                addons = [
                    {
                        "addonId": "ADD001",
                        "name": "Extra Cheese",
                        "price": 40.00
                    },
                    {
                        "addonId": "ADD002",
                        "name": "Extra Sauce",
                        "price": 20.00
                    }
                ]

                items.append({
                    "itemId": (
                        f"ITEM-{category_number + 1}-"
                        f"{item_number + 1}"
                    ),
                    "name": (
                        f"Item {category_number + 1}-"
                        f"{item_number + 1}"
                    ),
                    "description": (
                        "Freshly prepared food item"
                    ),
                    "price": round(
                        random.uniform(100, 600),
                        2
                    ),
                    "available": (
                        random.random() < 0.9
                    ),
                    "customizationAddons": addons
                })

            categories.append({
                "categoryId": f"CAT{category_number + 1:03d}",
                "name": f"Category {category_number + 1}",
                "items": items
            })

        menus.append({
            "restaurantId": restaurant["id"],
            "restaurantName": restaurant["name"],
            "categories": categories,
            "updatedAt": datetime.now(timezone.utc)
        })

    return menus


def generate_reviews(reference_data):

    restaurants = reference_data["restaurants"]
    users = reference_data["users"]

    tags = [
        "positive",
        "negative",
        "food-quality",
        "delivery",
        "service",
        "price",
        "taste"
    ]

    reviews = []

    now = datetime.now(timezone.utc)

    for _ in range(NUM_REVIEWS):

        restaurant = random.choice(restaurants)
        user = random.choice(users)

        rating = random.randint(1, 5)

        reviews.append({
            "restaurantId": restaurant["id"],
            "userId": user["id"],
            "rating": rating,
            "reviewText": (
                f"Sample review with rating {rating}"
            ),
            "sentimentTags": random.sample(
                tags,
                random.randint(1, 3)
            ),
            "createdAt": (
                now
                - timedelta(
                    days=random.randint(0, 30)
                )
            )
        })

    return reviews


def generate_driver_pings(reference_data):

    drivers = reference_data["drivers"]
    restaurants = reference_data["restaurants"]

    now = datetime.now(timezone.utc)

    for _ in range(NUM_DRIVER_PINGS):

        driver = random.choice(drivers)
        restaurant = random.choice(restaurants)

        latitude = (
            restaurant["latitude"]
            + random.uniform(-0.03, 0.03)
        )

        longitude = (
            restaurant["longitude"]
            + random.uniform(-0.03, 0.03)
        )

        yield {
            "driverId": driver["id"],

            "location": {
                "type": "Point",
                "coordinates": [
                    longitude,
                    latitude
                ]
            },

            "active": (
                random.random() < 0.7
            ),

            # Keep pings inside the TTL window.
            "createdAt": (
                now
                - timedelta(
                    minutes=random.randint(0, 110)
                )
            )
        }


def insert_in_batches(collection, documents):

    batch = []
    total = 0

    for document in documents:

        batch.append(document)

        if len(batch) >= BATCH_SIZE:

            collection.insert_many(
                batch,
                ordered=False
            )

            total += len(batch)

            print(
                f"{collection.name}: "
                f"{total:,} inserted"
            )

            batch.clear()

    if batch:

        collection.insert_many(
            batch,
            ordered=False
        )

        total += len(batch)

    return total


def main():

    random.seed(42)

    reference_data = load_reference_data()

    client = MongoClient(MONGO_URI)

    db = client[DATABASE_NAME]

    menus_collection = db["menus"]
    reviews_collection = db["reviews"]
    driver_collection = db["DriverPings"]

    print("Starting MongoDB seeding...")

    # -------------------------
    # Menus
    # -------------------------

    menus = generate_menus(
        reference_data["restaurants"]
    )

    if menus:
        menus_collection.insert_many(
            menus,
            ordered=False
        )

    print(
        f"Menus inserted: {len(menus):,}"
    )

    # -------------------------
    # Reviews
    # -------------------------

    reviews = generate_reviews(
        reference_data
    )

    if reviews:
        reviews_collection.insert_many(
            reviews,
            ordered=False
        )

    print(
        f"Reviews inserted: {len(reviews):,}"
    )

    # -------------------------
    # DriverPings
    # -------------------------

    total_pings = insert_in_batches(
        driver_collection,
        generate_driver_pings(
            reference_data
        )
    )

    print(
        f"DriverPings inserted: "
        f"{total_pings:,}"
    )

    client.close()

    print("\nMongoDB seeding completed.")


if __name__ == "__main__":
    main()