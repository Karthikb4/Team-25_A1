const db = db.getSiblingDB("bitestream_db");

// 1. Initialize Collections explicitly
db.createCollection("menus");
db.createCollection("reviews");
db.createCollection("driver_pings");

// 2. Geospatial 2dsphere index on location (Mandated by Project 1 spec)
db.driver_pings.createIndex(
  { location: "2dsphere" },
  { name: "idx_driver_location_2dsphere" }
);

// 3. TTL Index on created_at: expireAfterSeconds: 7200 (2 hours) (Mandated by Project 1 spec)
db.driver_pings.createIndex(
  { created_at: 1 },
  { expireAfterSeconds: 7200, name: "idx_driver_ping_ttl_2h" }
);

// 4. Secondary compound index for active driver queries
db.driver_pings.createIndex(
  { status: 1, created_at: -1 },
  { name: "idx_driver_status_created" }
);

// 5. Index for Workflow 4 ($facet review analytics)
db.reviews.createIndex(
  { restaurant_id: 1, rating: 1 },
  { name: "idx_reviews_restaurant_rating" }
);

print(">>> MongoDB collections and all required indexes created successfully.");