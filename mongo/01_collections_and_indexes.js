const db = db.getSiblingDB("bitestream");

// 1. Drop existing non-_id indexes to prevent naming conflicts
try {
  db.DriverPings.dropIndexes();
  db.reviews.dropIndexes();
  print(">>> Cleared older indexes successfully.");
} catch (e) {
  print(">>> Index drop notice: " + e.message);
}

// 2. DriverPings: 2dsphere index on location
db.DriverPings.createIndex(
  { location: "2dsphere" },
  { name: "idx_driver_location_2dsphere" }
);

// 3. DriverPings: TTL index on createdAt (2 hours / 7200s)
db.DriverPings.createIndex(
  { createdAt: 1 },
  { expireAfterSeconds: 7200, name: "idx_driver_ping_ttl_2h" }
);

// 4. DriverPings: Compound index for active driver queries
db.DriverPings.createIndex(
  { active: 1, createdAt: -1 },
  { name: "idx_driver_active_created" }
);

// 5. reviews: Compound index on restaurantId and rating
db.reviews.createIndex(
  { restaurantId: 1, rating: 1 },
  { name: "idx_reviews_restaurant_rating" }
);

print(">>> Indexes created successfully on database 'bitestream'!");