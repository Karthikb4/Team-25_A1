// Workflow 3: Nearest Active Driver ($geoNear within 5km)
const db = db.getSiblingDB("bitestream");

// Dynamically pick the coordinates of an active ping
const sample = db.DriverPings.findOne({ active: true });
const centerCoords = sample ? sample.location.coordinates : [80.175, 13.121];

print(`Searching 5km radius around coordinates: [${centerCoords}] for active drivers...`);

const pipeline = [
  {
    $geoNear: {
      near: {
        type: "Point",
        coordinates: centerCoords
      },
      distanceField: "distanceMeters",
      maxDistance: 5000,
      query: { active: true },
      spherical: true
    }
  },
  {
    $project: {
      _id: 1,
      driverId: 1,
      active: 1,
      distanceMeters: { $round: ["$distanceMeters", 2] },
      coordinates: "$location.coordinates",
      createdAt: 1
    }
  },
  {
    $limit: 10
  }
];

const results = db.DriverPings.aggregate(pipeline).toArray();
print("=== Workflow 3: Closest Active Drivers within 5km ===");
printjson(results);