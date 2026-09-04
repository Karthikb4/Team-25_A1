use("bitestream");

// -------------------------------------------------------------
// 1. Workflow 3: Nearest Active Driver ($geoNear) Execution Stats
// -------------------------------------------------------------
const restaurantLatitude = 13.0827;
const restaurantLongitude = 80.2707;

const workflow3Stats = db.DriverPings
    .explain("executionStats")
    .aggregate([
        {
            $geoNear: {
                near: {
                    type: "Point",
                    coordinates: [
                        restaurantLongitude,
                        restaurantLatitude
                    ]
                },
                key: "location",
                distanceField: "distanceFromRestaurant",
                maxDistance: 5000,
                spherical: true,
                query: {
                    active: true
                }
            }
        },
        { $limit: 1 },
        {
            $project: {
                _id: 0,
                driverId: 1,
                location: 1,
                active: 1,
                distanceFromRestaurant: 1
            }
        }
    ]);

// -------------------------------------------------------------
// 2. Workflow 4: Multi-Faceted Review Analytics ($facet) Stats
// -------------------------------------------------------------
const restaurantId = "346c9f49-ef62-42a6-a7d9-75d42837527d";

const workflow4Stats = db.Reviews
    .explain("executionStats")
    .aggregate([
        {
            $match: {
                restaurantId: restaurantId
            }
        },
        {
            $facet: {
                ratingDistribution: [
                    {
                        $group: {
                            _id: "$rating",
                            count: { $sum: 1 }
                        }
                    },
                    { $sort: { _id: 1 } },
                    {
                        $project: {
                            _id: 0,
                            rating: "$_id",
                            count: 1
                        }
                    }
                ],
                frequentTags: [
                    { $unwind: "$sentimentTags" },
                    {
                        $group: {
                            _id: "$sentimentTags",
                            count: { $sum: 1 }
                        }
                    },
                    { $sort: { count: -1 } },
                    {
                        $project: {
                            _id: 0,
                            tag: "$_id",
                            count: 1
                        }
                    }
                ],
                overallAverageRating: [
                    {
                        $group: {
                            _id: null,
                            averageRating: { $avg: "$rating" },
                            reviewCount: { $sum: 1 }
                        }
                    },
                    {
                        $project: {
                            _id: 0,
                            averageRating: {
                                $round: ["$averageRating", 2]
                            },
                            reviewCount: 1
                        }
                    }
                ]
            }
        }
    ]);

// -------------------------------------------------------------
// 3. Combine into a Single JSON Object and Output
// -------------------------------------------------------------
const combinedReport = {
    generatedAt: new Date().toISOString(),
    database: "bitestream",
    workflow3_geonear_stats: workflow3Stats,
    workflow4_facet_stats: workflow4Stats
};

print(JSON.stringify(combinedReport, null, 2));