import json
import random
import uuid
from pathlib import Path

NUM_USERS = 20_000
NUM_RESTAURANTS = 100
NUM_DRIVERS = 1_000

# Chennai approximate center
CENTER_LAT = 13.0827
CENTER_LON = 80.2707

OUTPUT_FILE = Path(__file__).parent / "seed_reference.json"


def generate_uuid():
    return str(uuid.uuid4())


def main():
    random.seed(42)

    users = []
    restaurants = []
    drivers = []

    # Shared users
    for i in range(NUM_USERS):
        users.append({
            "id": generate_uuid(),
            "name": f"User {i + 1}"
        })

    # Shared restaurants
    for i in range(NUM_RESTAURANTS):
        restaurants.append({
            "id": generate_uuid(),
            "name": f"BiteStream Restaurant {i + 1}",
            "latitude": round(
                CENTER_LAT + random.uniform(-0.08, 0.08),
                6
            ),
            "longitude": round(
                CENTER_LON + random.uniform(-0.08, 0.08),
                6
            )
        })

    # Shared drivers
    for i in range(NUM_DRIVERS):
        drivers.append({
            "id": generate_uuid(),
            "name": f"Driver {i + 1}"
        })

    reference_data = {
        "users": users,
        "restaurants": restaurants,
        "drivers": drivers
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(
            reference_data,
            f,
            indent=2
        )

    print(f"Reference data written to: {OUTPUT_FILE}")
    print(f"Users: {len(users)}")
    print(f"Restaurants: {len(restaurants)}")
    print(f"Drivers: {len(drivers)}")


if __name__ == "__main__":
    main()