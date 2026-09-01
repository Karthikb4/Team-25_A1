import json
import os
import random
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/bitestream"
)

REFERENCE_FILE = (
    Path(__file__).parent / "seed_reference.json"
)

NUM_ORDERS = 120_000
NUM_WALLET_UPDATES = 100_000


def load_reference_data():
    with open(
        REFERENCE_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)


def generate_users(reference_data):
    users = []

    for user in reference_data["users"]:
        users.append((
            user["id"],
            user["name"],
            Decimal(
                random.randint(500, 5000)
            )
        ))

    return users


def insert_users(conn, users):
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO users
                (id, name, wallet_balance)
            VALUES
                (%s, %s, %s)
            """,
            users
        )


def insert_restaurants(conn, restaurants):
    rows = [
        (
            restaurant["id"],
            restaurant["name"],
            restaurant["latitude"],
            restaurant["longitude"]
        )
        for restaurant in restaurants
    ]

    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO restaurants
                (id, name, latitude, longitude)
            VALUES
                (%s, %s, %s, %s)
            """,
            rows
        )


def generate_orders(reference_data):
    users = reference_data["users"]
    restaurants = reference_data["restaurants"]

    statuses = [
        "PREPARING",
        "DELIVERING",
        "DELIVERED"
    ]

    now = datetime.now(timezone.utc)

    orders = []

    for _ in range(NUM_ORDERS):

        user = random.choice(users)
        restaurant = random.choice(restaurants)

        amount = Decimal(
            random.randint(100, 2000)
        ).quantize(
            Decimal("0.01")
        )

        created_at = (
            now
            - timedelta(
                days=random.randint(0, 30),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
        )

        orders.append((
            str(__import__("uuid").uuid4()),
            user["id"],
            restaurant["id"],
            amount,
            random.choice(statuses),
            created_at
        ))

    return orders


def insert_orders(conn, orders):
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO orders
                (
                    id,
                    user_id,
                    restaurant_id,
                    total_amount,
                    status,
                    created_at
                )
            VALUES
                (%s, %s, %s, %s, %s, %s)
            """,
            orders
        )


def generate_wallet_updates(reference_data):
    """
    These updates cause the PostgreSQL audit trigger
    to create wallet_audit_logs automatically.
    """

    users = reference_data["users"]

    updates = []

    for _ in range(NUM_WALLET_UPDATES):

        user = random.choice(users)

        amount = Decimal(
            random.randint(10, 500)
        ).quantize(
            Decimal("0.01")
        )

        updates.append((
            amount,
            user["id"]
        ))

    return updates


def perform_wallet_updates(conn, updates):

    with conn.cursor() as cur:

        for amount, user_id in updates:

            cur.execute(
                """
                UPDATE users
                SET wallet_balance =
                    wallet_balance - %s
                WHERE id = %s
                  AND wallet_balance >= %s
                """,
                (
                    amount,
                    user_id,
                    amount
                )
            )


def verify_data(conn):

    with conn.cursor() as cur:

        cur.execute(
            "SELECT COUNT(*) FROM users"
        )
        users = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(*) FROM restaurants"
        )
        restaurants = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(*) FROM orders"
        )
        orders = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(*) FROM wallet_audit_logs"
        )
        audits = cur.fetchone()[0]

    print()
    print("PostgreSQL verification")
    print("------------------------")
    print(f"Users:            {users}")
    print(f"Restaurants:      {restaurants}")
    print(f"Orders:           {orders}")
    print(f"Audit logs:       {audits}")


def main():

    random.seed(42)

    reference_data = load_reference_data()

    print("Starting PostgreSQL seeding...")

    users = generate_users(reference_data)

    with psycopg.connect(DATABASE_URL) as conn:

        insert_users(
            conn,
            users
        )

        insert_restaurants(
            conn,
            reference_data["restaurants"]
        )

        orders = generate_orders(
            reference_data
        )

        insert_orders(
            conn,
            orders
        )

        wallet_updates = generate_wallet_updates(
            reference_data
        )

        perform_wallet_updates(
            conn,
            wallet_updates
        )

        conn.commit()

        verify_data(conn)

    print("\nPostgreSQL seeding completed.")


if __name__ == "__main__":
    main()