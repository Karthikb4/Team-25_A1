# BiteStream - Database Engine & Advanced Analytics System

BiteStream is a hybrid database architecture combining **PostgreSQL** (relational OLTP, transactional consistency, audit compliance) and **MongoDB** (dynamic document catalogs, real-time driver telemetry, multi-faceted analytics).

---

## 1. Architecture Overview

BiteStream/
├── data_generation/
│   ├── create_reference_data.py       # Bridges PostgreSQL UUIDs/coordinates to Mongo
│   ├── seed_reference.json            # Reference payload for cross-database integrity
│   └── mongo_seeder.py                # High-throughput batch streaming seeder
├── mongo/
│   ├── 01_collections_and_indexes.js  # Schema validators ($jsonSchema) and specialized indexes
│   ├── 02_workflow3_geonear.js        # Workflow 3: Nearest active driver dispatch
│   └── 03_workflow4_facet.js          # Workflow 4: Review multi-faceted analytics
├── docs/
│   └── mongo_schema_map.json          # Document structure & JSON validation schema models
└── performance/
    └── mongo_execution_stats.json     # EXPLAIN execution plans proving index utilization









--------------------------------------------------------

## 2. MongoDB Setup & Execution Guide

### Prerequisites
- MongoDB Server running on localhost:27017
- Python 3.10+ with pymongo
- MongoDB Shell (mongosh)

### Step-by-Step Instructions

1. Activate Python Virtual Environment:
   source venv/bin/activate

2. Generate Reference Data:
   Produces relational mapping keys and driver telemetry base coordinates:
   python3 data_generation/create_reference_data.py

3. Seed MongoDB Collections:
   Executes memory-safe batched ingestion (5,000 documents/batch) streaming into MongoDB:
   python3 data_generation/mongo_seeder.py

4. Register Schemas, Constraints, and Indexes:
   Applies $jsonSchema document validators, TTL eviction, and 2dsphere indexing:
   mongosh bitestream mongo/01_collections_and_indexes.js

5. Execute Workflow Queries:
   - Workflow 3 (Geospatial Driver Dispatch):
     mongosh bitestream --quiet mongo/02_workflow3_geonear.js
   - Workflow 4 (Multi-Faceted Sentiment Analytics):
     mongosh bitestream --quiet mongo/03_workflow4_facet.js

6. Generate Query Performance Metrics:
   Exports comprehensive query plan telemetry:
   mkdir -p performance
   mongosh bitestream --quiet --eval '
   const samplePing = db.DriverPings.findOne({ active: true });
   const coords = (samplePing && samplePing.location) ? samplePing.location.coordinates : [80.2450, 13.0400];
   const sampleReview = db.reviews.findOne();
   const targetId = sampleReview ? sampleReview.restaurantId : "";

   const wf3Stats = db.DriverPings.explain("executionStats").aggregate([
     {
       $geoNear: {
         near: { type: "Point", coordinates: coords },
         distanceField: "distanceMeters",
         maxDistance: 5000,
         query: { active: true },
         spherical: true
       }
     },
     { $limit: 1 }
   ]);

   const wf4Stats = db.reviews.explain("executionStats").aggregate([
     { $match: { restaurantId: targetId } },
     {
       $facet: {
         "rating_distribution": [{ $group: { _id: "$rating", count: { $sum: 1 } } }],
         "overall_summary": [{ $group: { _id: null, total: { $sum: 1 }, avg: { $avg: "$rating" } } }]
       }
     }
   ]);

   print(JSON.stringify({
     workflow_3_geonear_execution_stats: wf3Stats,
     workflow_4_facet_execution_stats: wf4Stats
   }, null, 2));
   ' > performance/mongo_execution_stats.json

---

## 3. MongoDB Collections & Validation Design

All collections adhere to structural specifications documented in docs/mongo_schema_map.json:

* menus: Contains hierarchical restaurant menus, including category partitions, item availability flags, base pricing, and nested customization addons.
  - Constraints: Enforced via idx_menus_restaurant_unique compound index, restricting each restaurant to a single canonical catalog document.
* reviews: High-volume customer feedback records with integer-validated scores (1 to 5) and rating-correlated sentiment tags.
  - Validation: Schema-level constraints requiring restaurantId, orderId, rating, and UTC createdAt timestamps.
* DriverPings: Real-time driver telemetry coordinates formatted in GeoJSON (Point).
  - Validation: Enforces strict two-element float arrays [longitude, latitude], driver identity references, and status flags.

---

## 4. Indexing & Query Optimization Strategy

* 2dsphere Geospatial Index (idx_driverpings_location_2dsphere):
  - Key: { location: "2dsphere" }
  - Enables spherical distance calculations directly inside the storage engine for high-frequency driver dispatch algorithms.
* Time-To-Live (TTL) Eviction Index (idx_driver_ping_ttl_2h):
  - Key: { createdAt: 1 }, expireAfterSeconds: 7200
  - Automated database-level memory reclamation. Documents older than 2 hours are purged by background maintenance threads without requiring external cron schedulers.
* Compound Index (idx_reviews_restaurant_rating):
  - Key: { restaurantId: 1, rating: 1 }
  - Optimizes restaurant-specific aggregations by isolating relevant partitions prior to pipeline fan-out.

---

## 5. Stress Testing & Query Execution Proof

### Dataset Scale
The database was populated with large datasets exceeding the project stress requirements:
- menus: 100 complete restaurant menu catalogs.
- reviews: 100,000 customer reviews with realistic sentiment distributions.
- DriverPings: 500,000 location records maintained within active operational TTL bounds.

### Execution Plan Telemetry (from performance/mongo_execution_stats.json)

#### Workflow 3: Nearest Driver Dispatch ($geoNear)
- Query Type: Geospatial proximity aggregation using spherical calculations.
- Stage Traversal: GEO_NEAR_2DSPHERE -> FETCH.
- Targeting Performance: Zero collection scan (COLLSCAN) fallback. Out of 500,000 available records, the query isolates candidates examining only 170 documents (totalDocsExamined: 170).
- Execution Time: Under 15 ms.

#### Workflow 4: Review Multi-Faceted Analytics ($facet)
- Query Type: Single-stage multi-branch aggregation evaluating rating histograms, sentiment tag frequencies, and cumulative averages concurrently.
- Stage Traversal: Direct index seek via IXSCAN on idx_reviews_restaurant_rating.
- Execution Performance: Rapidly isolates target restaurant reviews, running three distinct pipeline branches in memory without repeated table scans across the 100,000 reviews.
