// Workflow 4: Multi-Faceted Review Analytics ($facet)

var targetId = null;

if (typeof targetRestaurantId !== 'undefined' && targetRestaurantId) {
  targetId = targetRestaurantId;
} else {
  const sample = db.reviews.aggregate([{ $sample: { size: 1 } }]).toArray();
  targetId = (sample.length > 0) ? sample[0].restaurantId : "1cb63086-8207-435d-ba11-b7cf514e6cd5";
}

const pipeline = [
  {
    $match: {
      restaurantId: targetId
    }
  },
  {
    $facet: {
      "rating_distribution": [
        {
          $group: {
            _id: "$rating",
            count: { $sum: 1 }
          }
        },
        {
          $sort: { _id: 1 }
        },
        {
          $project: {
            _id: 0,
            stars: "$_id",
            count: 1
          }
        }
      ],
      "most_frequent_tags": [
        {
          $unwind: "$sentimentTags"
        },
        {
          $group: {
            _id: "$sentimentTags",
            frequency: { $sum: 1 }
          }
        },
        {
          $sort: { frequency: -1 }
        },
        {
          $limit: 10
        },
        {
          $project: {
            _id: 0,
            tag: "$_id",
            count: "$frequency"
          }
        }
      ],
      "overall_summary": [
        {
          $group: {
            _id: null,
            total_reviews: { $sum: 1 },
            avg_rating: { $avg: "$rating" }
          }
        },
        {
          $project: {
            _id: 0,
            total_reviews: 1,
            average_rating: { $round: ["$avg_rating", 2] }
          }
        }
      ]
    }
  }
];

const results = db.reviews.aggregate(pipeline).toArray();

// Output strictly formatted JSON for evaluation scripts
print(JSON.stringify(results, null, 2));