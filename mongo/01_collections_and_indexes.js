// Select database
use("bitestream");

// ==========================================
// DriverPings: Geospatial Index
// ==========================================

db.DriverPings.createIndex(
    { location: "2dsphere" },
    { name: "idx_driverpings_location_2dsphere" }
);

// ==========================================
// DriverPings: TTL Index
// ==========================================

db.DriverPings.createIndex(
    { createdAt: 1 },
    {
        name: "idx_driverpings_createdAt_ttl",
        expireAfterSeconds: 7200
    }
);