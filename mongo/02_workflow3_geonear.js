// Workflow 3: Nearest Active Driver ($geoNear)

var coords = null;

if (typeof targetCoords !== 'undefined' && Array.isArray(targetCoords)) {
  coords = targetCoords;
} else {
  // Sample an active driver location with a realistic offset
  const sample = db.DriverPings.aggregate([
    { $match: { active: true } },
    { $sample: { size: 1 } }
  ]).toArray();

  if (sample.length > 0) {
    const rawLon = sample[0].location.coordinates[0];
    const rawLat = sample[0].location.coordinates[1];
    coords = [rawLon + (Math.random() - 0.5) * 0.01, rawLat + (Math.random() - 0.5) * 0.01];
  } else {
    coords = [80.2450, 13.0400];
  }
}

const pipeline = [
  {
    $geoNear: {
      near: {
        type: "Point",
        coordinates: coords
      },
      distanceField: "distanceMeters",
      maxDistance: 5000,
      query: { active: true },
      spherical: true
    }
  },
  { $limit: 1 },
  {
    $project: {
      _id: 0,
      driverId: 1,
      active: 1,
      distanceMeters: { $round: ["$distanceMeters", 2] },
      coordinates: "$location.coordinates",
      createdAt: 1
    }
  }
];

const results = db.DriverPings.aggregate(pipeline).toArray();

// Output strictly formatted JSON for evaluation scripts
print(JSON.stringify(results, null, 2));

