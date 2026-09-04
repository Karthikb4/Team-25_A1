use("bitestream");

const restaurantId = "6ba0b353-f07c-486b-8c5d-72a49605cb11";

const result = db.reviews
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

printjson(result);