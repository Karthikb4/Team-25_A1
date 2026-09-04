import json
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

# Collection names matching database definitions
MENUS_COLLECTION = "menus"
REVIEWS_COLLECTION = "reviews"
PINGS_COLLECTION = "DriverPings"

# The TTL index field matching $jsonSchema and 01_collections_and_indexes.js
PING_TIME_FIELD = "createdAt"

NUM_REVIEWS = 100_000
NUM_DRIVER_PINGS = 500_000
BATCH_SIZE = 5_000

PING_AGE_MINUTES = 20
PING_JITTER_DEG = 0.01

SEED = 42
rng = random.Random(SEED)

POSITIVE_TAGS = [
    "positive",
    "food-quality",
    "taste",
    "fast-delivery",
    "well-packaged",
    "value-for-money"
]

NEGATIVE_TAGS = [
    "negative",
    "late-delivery",
    "cold-food",
    "overpriced",
    "rude-service",
    "wrong-order"
]

NEUTRAL_TAGS = [
    "portion-size",
    "packaging",
    "service"
]


def load_reference_data():
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
                    "description": "Freshly prepared food item",
                    "price": round(rng.uniform(100, 600), 2),
                    "available": rng.random() < 0.9,
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


def tags_for_rating(rating):
    if rating >= 4:
        pool = POSITIVE_TAGS + NEUTRAL_TAGS
    elif rating <= 2:
        pool = NEGATIVE_TAGS + NEUTRAL_TAGS
    else:
        pool = NEUTRAL_TAGS + rng.sample(POSITIVE_TAGS, 2) + rng.sample(NEGATIVE_TAGS, 2)

    return rng.sample(pool, rng.randint(1, 3))


def generate_reviews(reference_data):
    restaurants = reference_data["restaurants"]
    users = reference_data["users"]
    now = datetime.now(timezone.utc)

    for _ in range(NUM_REVIEWS):
        restaurant = rng.choice(restaurants)
        user = rng.choice(users)

        rating = rng.choices(
            [1, 2, 3, 4, 5],
            weights=[8, 10, 17, 30, 35]
        )[0]

        yield {
            "restaurantId": restaurant["id"],
            "userId": user["id"],
            "orderId": f"ORD-{rng.randint(100000, 999999)}",
            "rating": int(rating),
            "reviewText": f"Sample review with rating {rating}",
            "sentimentTags": tags_for_rating(rating),
            "createdAt": (
                now
                - timedelta(
                    days=rng.randint(0, 90),
                    minutes=rng.randint(0, 1439)
                )
            )
        }


def generate_driver_pings(reference_data):
    drivers = reference_data["drivers"]
    now = datetime.now(timezone.utc)

    for _ in range(NUM_DRIVER_PINGS):
        driver = rng.choice(drivers)

        home_lat = driver.get("home_latitude") or driver.get("latitude") or 13.0400
        home_lng = driver.get("home_longitude") or driver.get("longitude") or 80.2450
        is_active = driver.get("is_active", True) if "is_active" in driver else (rng.random() < 0.75)

        latitude = home_lat + rng.uniform(-PING_JITTER_DEG, PING_JITTER_DEG)
        longitude = home_lng + rng.uniform(-PING_JITTER_DEG, PING_JITTER_DEG)

        yield {
            "driverId": driver["id"],
            "location": {
                "type": "Point",
                "coordinates": [
                    round(longitude, 6),
                    round(latitude, 6)
                ]
            },
            "active": is_active,
            PING_TIME_FIELD: (
                now
                - timedelta(
                    seconds=rng.randint(0, PING_AGE_MINUTES * 60)
                )
            )
        }


def insert_in_batches(collection, documents, label=None):
    label = label or collection.name
    batch = []
    total = 0

    for document in documents:
        batch.append(document)
        if len(batch) >= BATCH_SIZE:
            collection.insert_many(batch, ordered=False)
            total += len(batch)
            print(f"{label}: {total:,} inserted")
            batch.clear()

    if batch:
        collection.insert_many(batch, ordered=False)
        total += len(batch)
        print(f"{label}: {total:,} inserted")

    return total


def verify_data(db):
    pings = db[PINGS_COLLECTION]

    print("\nMongoDB verification")
    print("------------------------")
    print(f"menus:       {db[MENUS_COLLECTION].count_documents({}):,}")
    print(f"reviews:     {db[REVIEWS_COLLECTION].count_documents({}):,}")
    print(f"DriverPings: {pings.count_documents({}):,}")

    active = pings.count_documents({"active": True})
    print(f"  active:    {active:,}")

    distinct_drivers = len(pings.distinct("driverId"))
    print(f"  drivers:   {distinct_drivers:,}")

    oldest = pings.find_one(sort=[(PING_TIME_FIELD, 1)])
    if oldest:
        age = datetime.now(timezone.utc) - oldest[PING_TIME_FIELD].replace(
            tzinfo=timezone.utc
        )
        remaining = 7200 - age.total_seconds()
        print(
            f"  oldest ping expires in ~{remaining / 60:.0f} min "
            f"(TTL 7200s)"
        )


def main():
    reference_data = load_reference_data()

    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]

    print("Cleaning collections before seeding...")
    db[MENUS_COLLECTION].delete_many({})
    db[REVIEWS_COLLECTION].delete_many({})
    db[PINGS_COLLECTION].delete_many({})

    print("Starting MongoDB seeding...")

    menus = generate_menus(reference_data["restaurants"])
    if menus:
        db[MENUS_COLLECTION].insert_many(menus, ordered=False)
    print(f"Menus inserted: {len(menus):,}")

    total_reviews = insert_in_batches(
        db[REVIEWS_COLLECTION],
        generate_reviews(reference_data),
        label=REVIEWS_COLLECTION
    )
    print(f"Reviews inserted: {total_reviews:,}")

    total_pings = insert_in_batches(
        db[PINGS_COLLECTION],
        generate_driver_pings(reference_data),
        label=PINGS_COLLECTION
    )
    print(f"DriverPings inserted: {total_pings:,}")

    verify_data(db)
    client.close()

    print("\nMongoDB seeding completed.")


if __name__ == "__main__":
    main()