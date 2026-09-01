// Workflow 3: Nearest Active Driver ($geoNear within 5km / 5000m)
const db = db.getSiblingDB("bitestream_db");

// Target coordinates (e.g. Restaurant at Longitude 78.3826, Latitude 17.4435)
const targetLongitude = 78.3826;
const targetLatitude = 17.4435;
const maxDistanceInMeters = 5000; // 5km limit

const pipeline = [
  {
    $geoNear: {
      near: {
        type: "Point",
        coordinates: [targetLongitude, targetLatitude]
      },
      distanceField: "distance_meters",
      maxDistance: maxDistanceInMeters,
      query: { status: "ACTIVE" },
      spherical: true
    }
  },
  {
    $project: {
      _id: 1,
      driver_id: 1,
      status: 1,
      distance_meters: { $round: ["$distance_meters", 2] },
      coordinates: "$location.coordinates",
      created_at: 1
    }
  },
  {
    $limit: 10
  }
];

const results = db.driver_pings.aggregate(pipeline).toArray();
print("=== Workflow 3: Closest Active Drivers within 5km ===");
printjson(results);