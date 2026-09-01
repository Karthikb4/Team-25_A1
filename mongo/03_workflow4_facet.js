// Workflow 4: Multi-Faceted Review Analytics ($facet)
const db = db.getSiblingDB("bitestream_db");

// Analyze reviews for restaurant_id: 1 (or change as needed)
const targetRestaurantId = 1;

const pipeline = [
  {
    $match: { restaurant_id: targetRestaurantId }
  },
  {
    $facet: {
      // 1. Rating Distribution (1 to 5 stars)
      rating_distribution: [
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
            stars: "$_id",
            count: 1,
            _id: 0
          }
        }
      ],

      // 2. Most frequent tag strings via $unwind
      most_frequent_tags: [
        {
          $unwind: "$sentiment_tags"
        },
        {
          $group: {
            _id: "$sentiment_tags",
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
            tag: "$_id",
            count: "$frequency",
            _id: 0
          }
        }
      ],

      // 3. Overall average rating
      overall_summary: [
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

const analyticsOutput = db.reviews.aggregate(pipeline).toArray();
print("=== Workflow 4: Multi-Faceted Review Analytics ===");
printjson(analyticsOutput);