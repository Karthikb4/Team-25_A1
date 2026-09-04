// BiteStream - Collections, Validators, and Indexes Setup

// 1. Menus
db.runCommand({
  collMod: "menus",
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["restaurantId", "categories", "updatedAt"],
      properties: {
        restaurantId: { bsonType: "string" },
        restaurantName: { bsonType: "string" },
        categories: { bsonType: "array" },
        updatedAt: { bsonType: "date" }
      }
    }
  },
  validationLevel: "moderate"
});
db.menus.createIndex({ restaurantId: 1 }, { unique: true, name: "idx_menus_restaurant_unique" });

// 2. Reviews
db.runCommand({
  collMod: "reviews",
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["restaurantId", "orderId", "rating", "createdAt"],
      properties: {
        restaurantId: { bsonType: "string" },
        orderId: { bsonType: "string" },
        rating: { bsonType: "int", minimum: 1, maximum: 5 },
        sentimentTags: { bsonType: "array" },
        createdAt: { bsonType: "date" }
      }
    }
  },
  validationLevel: "moderate"
});
db.reviews.createIndex({ restaurantId: 1, rating: 1 }, { name: "idx_reviews_restaurant_rating" });
db.reviews.createIndex({ sentimentTags: 1 }, { name: "idx_reviews_tags" });

// 3. DriverPings
db.runCommand({
  collMod: "DriverPings",
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["driverId", "location", "active", "createdAt"],
      properties: {
        driverId: { bsonType: "string" },
        location: {
          bsonType: "object",
          required: ["type", "coordinates"],
          properties: {
            type: { enum: ["Point"] },
            coordinates: { bsonType: "array", minItems: 2, maxItems: 2 }
          }
        },
        active: { bsonType: "bool" },
        createdAt: { bsonType: "date" }
      }
    }
  },
  validationLevel: "moderate"
});

// Match the exact existing keys and names on DriverPings
db.DriverPings.createIndex({ location: "2dsphere" }, { name: "idx_driverpings_location_2dsphere" });
db.DriverPings.createIndex({ createdAt: 1 }, { expireAfterSeconds: 7200, name: "idx_driver_ping_ttl_2h" });
db.DriverPings.createIndex({ active: 1, createdAt: -1 }, { name: "idx_driver_active_created" });

print("Indexes and validation schemas registered successfully.");
