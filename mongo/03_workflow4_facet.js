// Workflow 4: Multi-Faceted Review Analytics ($facet)
const db = db.getSiblingDB("bitestream");

// Target a valid restaurantId from the database
const sampleReview = db.reviews.findOne();
const targetRestaurantId = sampleReview ? sampleReview.restaurantId : null;

print(`Running Workflow 4 for restaurantId: ${targetRestaurantId}`);

const pipeline = [
  {
    $match: { restaurantId: targetRestaurantId }
  },
  {
    $facet: {
      // 1. Star Rating Distribution (1 to 5)
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

      // 2. Most Frequent Sentiment Tags
      most_frequent_tags: [
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
            tag: "$_id",
            count: "$frequency",
            _id: 0
          }
        }
      ],

      // 3. Overall Summary Metrics
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