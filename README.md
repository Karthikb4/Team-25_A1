# BiteStream — Food Delivery & Real-Time Logistics

Team 25 · Roll numbers:
2026201056 — Mihir Bachhab
2026202009 — Hammad Faizvi
2026204020 — Mohit Tripathi
2026201037 — Bankapalli Karthik

Project 1 of 5 (assigned via `team_no % 5 + 1`)

A production-style persistence layer split across PostgreSQL (transactional
data: users, wallets, orders) and MongoDB (flexible/high-volume data: menus,
reviews, driver geolocation pings).

---

## Setup Steps

> ⚠️ Fill in as each part is actually run and confirmed working. Do not mark
> a step done until someone has run it themselves.

### PostgreSQL

Target version: **PostgreSQL 18**. Note that starting in version 18,
`REFRESH MATERIALIZED VIEW` requires the `MAINTAIN` privilege on the view
rather than mere ownership (the behavior on versions 14-17). See the note
in `sql/05_materialized_views.sql` if a refresh fails with a permissions
error.

1. Create a database (e.g. `bitestream`) on PostgreSQL 18.
2. Run schema and logic scripts **in order**:
   ```bash
   psql -d bitestream -f sql/01_schema_ddl.sql
   psql -d bitestream -f sql/02_indexes.sql
   psql -d bitestream -f sql/03_triggers_and_audit.sql
   psql -d bitestream -f sql/04_stored_procedures.sql
   psql -d bitestream -f sql/05_materialized_views.sql
   psql -d bitestream -f sql/06_window_analytics.sql
   ```
3. Seed data:
   ```bash
   cd data_generation
   pip install -r requirements.txt
   python generate_reference_data.py   # writes seed_reference.json
   DATABASE_URL=postgresql://<user>:<pass>@localhost:5432/bitestream \
     python postgres_seeder.py
   ```

### MongoDB

1. Start a local MongoDB instance (`mongod`) or point at a hosted cluster.
2. Run collection/index setup and workflow scripts:
   ```bash
   mongosh <connection_string> mongo/01_collections_and_indexes.js
   ```
3. Seed data (uses the same `seed_reference.json` as the Postgres seeder,
   so restaurant/user/driver IDs line up across both databases):
   ```bash
   cd data_generation
   MONGO_URI=mongodb://localhost:27017 MONGO_DATABASE=bitestream \
     python mongo_seeder.py
   ```

### Order of operations (both databases)

`generate_reference_data.py` → `postgres_seeder.py` and `mongo_seeder.py`
(these two can run independently of each other, but both depend on
`seed_reference.json` existing first).

---

## Assumptions

> List every place the team made a judgment call the spec left open.
> Add to this list as you go — don't leave it until the end.

- **Primary keys**: all entity IDs are UUIDs (not INT/SERIAL), generated via
  `pgcrypto`'s `gen_random_uuid()` on the Postgres side, and pre-generated in
  `seed_reference.json` so the same user/restaurant/driver IDs are shared
  across both PostgreSQL and MongoDB.
- **`status` / `action_type` columns**: implemented as `VARCHAR` with a
  `CHECK` constraint rather than native Postgres `ENUM` types, so new values
  can be added later via a constraint change instead of `ALTER TYPE`.
- **Audit trigger design**: the assignment describes the trigger as firing
  `AFTER UPDATE OF wallet_balance ON users` (i.e. logging *any* wallet
  change). This implementation instead fires `AFTER INSERT ON orders` and
  logs a `DEBIT` equal to the order total. This satisfies the checkout flow
  (Workflow 1) correctly, but means:
  - Wallet changes that don't happen through an order insert (e.g. a direct
    `UPDATE`, a refund, a manual top-up) are **not** captured.
  - `CREDIT` audit rows are never produced by the current schema — no code
    path credits a wallet.
  - ⚠️ **Known conflict, unresolved as of this writing**: `postgres_seeder.py`
    performs 100,000 raw `UPDATE users SET wallet_balance = ...` statements
    directly, bypassing `sp_execute_checkout` and the `orders` table
    entirely. Under the current trigger design, **none of those updates
    will generate `wallet_audit_logs` rows.** This needs a team decision —
    see Open Items below.
- **MongoDB embedding vs. referencing**: `menus` embeds categories → items →
  customizationAddons as nested arrays within a single document per
  restaurant (read as a whole per restaurant, not queried at the item
  level). `reviews` and `DriverPings` are flat, unembedded collections due
  to high write volume (100k+ and 500k+ documents respectively) and the
  need to query/aggregate them independently.
- **Cross-database references are application-level, not enforced**:
  `restaurantId`, `userId`, and `driverId` fields in MongoDB documents match
  UUIDs from PostgreSQL's `restaurants`/`users` tables and
  `seed_reference.json`'s `drivers` array. There is no foreign-key
  constraint across the two engines — consistency depends on both seeders
  reading from the same `seed_reference.json`.
- **`EXPLAIN ANALYZE` cannot wrap `REFRESH MATERIALIZED VIEW` or `CALL`
  (stored procedures)**: this is a documented PostgreSQL limitation, not a
  gap in our testing — `EXPLAIN` only works on statements that produce a
  query plan (`SELECT`/`INSERT`/`UPDATE`/`DELETE`), and both `REFRESH
  MATERIALIZED VIEW` and `CALL` are execution wrappers around other
  statements rather than single plannable queries themselves. (A proposal
  to add `EXPLAIN ANALYZE REFRESH MATERIALIZED VIEW` support was submitted
  to PostgreSQL upstream and rejected by a core developer for this reason.)
  Where this affects our proof:
  - **`restaurant_order_summary`**: instead of explaining the `REFRESH`
    statement, we `EXPLAIN (ANALYZE, BUFFERS)` the view's underlying
    `SELECT` directly (the same query used in its `CREATE MATERIALIZED
    VIEW ... AS SELECT ...` definition), which is what actually determines
    index usage.
  - **`sp_execute_checkout`**: instead of explaining the `CALL`, we
    `EXPLAIN (ANALYZE, BUFFERS)` its two underlying DML statements
    individually — the wallet-balance `UPDATE` and the `orders` `INSERT` —
    which is exactly what the procedure executes internally.
  - **Triggers**: this doesn't apply the same way — Postgres reports
    trigger execution time as a line item inside the `EXPLAIN ANALYZE`
    output of whichever DML statement fired it (see the wallet-audit
    trigger evidence under Workflow 2 above), so no workaround was needed
    there.
- **PostgreSQL version**: developed and tested against PostgreSQL 18.
  `sql/05_materialized_views.sql`'s refresh function relies on
  `REFRESH MATERIALIZED VIEW CONCURRENTLY`, which requires the `MAINTAIN`
  privilege on Postgres 18 (a change from ownership-based access on
  versions 14-17) — see that file for the relevant `GRANT` statement.
- **No PostgreSQL `drivers` table exists**: `seed_reference.json` and
  `DriverPings.driverId` reference 1,000 drivers, but no relational
  `drivers` table is defined anywhere in `01_schema_ddl.sql`. MongoDB is
  currently the sole source of truth for driver identity. Confirm with team
  whether this is intentional or a gap.
- **Workflows are called with manually-passed parameters, not through an
  API**: this assignment is database-only (per the spec: "there is no
  front end application code for this assignment"), so `sp_execute_checkout`,
  `02_workflow3_geonear.js`, and `03_workflow4_facet.js` are all invoked
  directly with hardcoded/manually-supplied parameters (a `restaurantId`,
  a set of coordinates, etc.) rather than through a REST/GraphQL API layer.
  We're assuming a real application would eventually call these same
  pipelines through an API that passes those parameters dynamically — that
  API is out of scope for this assignment and has not been built.
- **Multi-faceted review analytics (Workflow 4) is scoped per-restaurant**:
  `03_workflow4_facet.js` filters by a single `restaurantId` before running
  the `$facet` aggregation (rating distribution, tag frequency, overall
  average), rather than computing these facets globally across all
  restaurants at once. This matches the assignment's framing of the
  workflow as restaurant-level analytics and keeps the aggregation scoped
  to a single index seek on `idx_reviews_restaurant_rating` (see the
  Workflow 4 performance proof below) rather than a full-collection scan.

---

## Open Items / Known Gaps

- [ ] Reconcile `postgres_seeder.py`'s raw wallet `UPDATE` behavior with the
      order-insert-triggered audit design (see Assumptions above). Decide:
      either route seeded wallet changes through `sp_execute_checkout`, or
      extend the trigger to also cover direct `UPDATE OF wallet_balance`.
- [ ] No code path currently produces a `CREDIT` audit log row. Confirm
      whether the assignment/viva requires demonstrating this, and if so,
      add a refund/top-up path.
- [x] `docs/relational_erd.png` / `.mmd` — drafted from `01_schema_ddl.sql`.
- [x] `docs/mongo_schema_map.json` — drafted from `mongo_seeder.py` output;
      validation rules section still needs a pass against the real
      `01_collections_and_indexes.js` once confirmed final.
- [x] `sql/06_window_analytics.sql` — EXPLAIN ANALYZE captured and added to
      README (Workflow 2). No problematic sequential scans; the one `Seq
      Scan on orders` is the correct planner choice at 93% selectivity, not
      a missing index. **Note:** the captured plan references a trigger
      named `trg_users_wallet_audit`. Earlier drafts of
      `03_triggers_and_audit.sql` in this repo used the name
      `orders_wallet_audit`, fired `AFTER INSERT ON orders`. Confirm which
      name/design is actually deployed — this plan implies the trigger was
      changed to fire on `users` (matching the fix your teammate proposed
      earlier), which would be the correct outcome, but the naming should
      be made consistent across the SQL file and this README.
- [x] `sql/05_materialized_views.sql` — drafted: `restaurant_order_summary`
      materialized view + `refresh_restaurant_order_summary()` wrapper
      function, with a `UNIQUE` index enabling `REFRESH CONCURRENTLY`.
- [ ] **Still needed**: `EXPLAIN (ANALYZE, BUFFERS)` on the view's
      underlying `SELECT` (not the `REFRESH` statement — see Assumptions
      above for why), plus a real role name filled into the Postgres 18
      `MAINTAIN` grant statement, then add both to this README.
- [ ] **Still needed**: `EXPLAIN (ANALYZE, BUFFERS)` on
      `sp_execute_checkout`'s two underlying statements (the wallet
      `UPDATE` and the `orders` `INSERT`) individually — not the `CALL`
      itself, per the Assumptions note above.
- [x] `mongo/01_collections_and_indexes.js`, `02_workflow3_geonear.js`,
      `03_workflow4_facet.js` — teammate reports these exist; not yet
      reviewed directly (only described via README). **Get the actual files
      before final submission to verify against the claims below.**
- [x] `performance/mongo_execution_stats.json` — real output received (see
      EXPLAIN Plans section above), both workflows confirm index usage
      (`GEO_NEAR_2DSPHERE`, `IXSCAN`) with no collection scans.
- [ ] `performance/postgres_explain_analyzes.txt` — pending, blocked on
      `05_materialized_views.sql` / `06_window_analytics.sql`.
- [ ] **Unresolved: `reviews` `orderId` field.** An earlier teammate draft
      described `reviews` validation as requiring `orderId`, but
      `mongo_seeder.py::generate_reviews()` never generates one — only
      `restaurantId`, `userId`, `rating`, `reviewText`, `sentimentTags`,
      `createdAt`. If the real validator requires `orderId`, every seeded
      review insert should have failed — but the stress-test numbers above
      suggest inserts succeeded. **Confirm with team which is accurate** and
      correct whichever side is wrong (seeder or validator description).
- [ ] Confirm `$limit` value used in `mongo/02_workflow3_geonear.js` — see
      note under Workflow 3 performance proof above; `nReturned: 32` implies
      no `$limit: 1`, which differs from an earlier draft of that script.

---

## EXPLAIN Plans (Performance Proof)

> Paste raw `EXPLAIN ANALYZE` (Postgres) and `explain('executionStats')`
> (Mongo) output here for Workflows 2, 3, and 4. Confirm each plan shows an
> **Index Scan / Bitmap Index Scan** (not `Seq Scan`) or **IXSCAN** (not
> `COLLSCAN`) before pasting — a scan that isn't hitting an index isn't proof
> of anything and should be fixed first.

### Workflow 2 — SQL Window Analytics (7-day moving average, DENSE_RANK)

Full `EXPLAIN (ANALYZE, BUFFERS)` output for the window analytics query
(`06_window_analytics.sql`), executed against the seeded dataset
(~120,000 orders):

```
Sort  (cost=198229.96..198230.21 rows=100 width=196) (actual time=81.844..81.875 rows=920.00 loops=1)
  Sort Key: (dense_rank() OVER w1), f.order_date
  Sort Method: quicksort  Memory: 109kB
  Buffers: shared hit=1486
  CTE daily_revenue
    ->  HashAggregate  (cost=12745.60..15940.38 rows=110916 width=60) (actual time=49.004..51.357 rows=9199.00 loops=1)
          Group Key: o.restaurant_id, (o.created_at)::date
          Planned Partitions: 8  Batches: 1  Memory Usage: 4113kB
          Buffers: shared hit=1482
          ->  Seq Scan on orders o  (cost=0.00..3261.96 rows=111984 width=25) (actual time=0.014..17.845 rows=111985.00 loops=1)
                Filter: ((status)::text = 'DELIVERED'::text)
                Rows Removed by Filter: 8015
                Buffers: shared hit=1482
  CTE filled
    ->  Merge Left Join  (cost=32294.90..39811.22 rows=277290 width=60) (actual time=62.401..65.832 rows=9200.00 loops=1)
          Merge Cond: ((r_1.id = dr.restaurant_id) AND (((d.order_date)::date) = dr.order_date))
          [... full nested-loop / generate_series date-filling logic ...]
  ->  Merge Join  (cost=122370.02..142475.04 rows=100 width=196) (actual time=69.712..81.541 rows=920.00 loops=1)
        Merge Cond: (f.restaurant_id = filled.restaurant_id)
        ->  WindowAgg  (cost=40092.25..56729.65 rows=277290 width=156) (actual time=68.195..79.543 rows=8281.00 loops=1)
              Window: w2 AS (PARTITION BY f.restaurant_id ORDER BY f.order_date)
              ->  WindowAgg ... Window: w1 (running total)
                    ->  WindowAgg ... Window: w7 AS (7-day moving window: ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)
        ->  Hash Join (restaurant name lookup + DENSE_RANK top-10 by revenue)
              ->  WindowAgg  Window: w1 AS (ORDER BY sum(daily_revenue) DESC)
                    Run Condition: (dense_rank() OVER w1 <= 10)
Planning Time: 0.653 ms
Execution Time: 82.123 ms
```

**Analysis — why `Seq Scan on orders` here is correct, not a missed index:**
The `DELIVERED` filter matches ~112,000 of ~120,000 orders (93% of the
table). At that selectivity, a sequential scan genuinely costs less than
an index scan would (index traversal + per-row heap fetches for almost
every row is more expensive than reading the table straight through),
so the planner's choice is correct. The partial index
`idx_orders_delivered_restaurant_created_at` defined in `02_indexes.sql`
is intentionally still useful for other, more selective queries (e.g. a
single restaurant's recent `DELIVERED` orders) — it isn't picked up here
because this query legitimately needs most of the table.

**Cardinality estimation note:** actual row counts diverge sharply from
planner estimates in several places — most notably the final
`DENSE_RANK` / top-10 `WindowAgg` step, planned for 277,290 rows but
producing only 10 (a ~27,700x overestimate). This stems from the
`generate_series`-based date-filling CTE (`filled`), which the planner
can't estimate accurately since it doesn't know in advance how many
calendar days will actually have order data. Despite the estimation
gap, total execution time is ~82ms with no sequential-scan-driven
slowdown, and no step falls back to a scan that a targeted index would
meaningfully improve — the query performs well in practice even where
the planner's row estimates are off.

**Wallet audit trigger — supporting evidence.** A secondary
`EXPLAIN (ANALYZE)` was also captured for the trigger itself, confirming
`trg_users_wallet_audit` fires correctly on a wallet-balance update
(`Trigger trg_users_wallet_audit: time=0.125 calls=1`) and that the
actual `UPDATE` targets the row via `Index Scan using users_pkey`
(not a scan). Note the test query used `WHERE id = (SELECT id FROM users
LIMIT 1)` to pick an arbitrary user, which is why a `Seq Scan on
users users_1` appears inside `InitPlan 1` — that scan selects *which*
row to update (bounded by `LIMIT 1`, so it stops after one row and costs
almost nothing: `actual rows=1.00`), not the update itself. It's an
artifact of the test query's arbitrary-user selection, not of the
schema or trigger design.

```
Update on users  (cost=0.34..8.36 rows=0 width=0) (actual time=0.055..0.056 rows=0.00 loops=1)
  Buffers: shared hit=8
  InitPlan 1
    ->  Limit  (cost=0.00..0.05 rows=1 width=16) (actual time=0.011..0.011 rows=1.00 loops=1)
          ->  Seq Scan on users users_1  (cost=0.00..1083.00 rows=20000 width=16) (actual time=0.010..0.010 rows=1.00 loops=1)
  ->  Index Scan using users_pkey on users  (cost=0.29..8.31 rows=1 width=22) (actual time=0.026..0.027 rows=1.00 loops=1)
        Index Cond: (id = (InitPlan 1).col1)
        Index Searches: 1
Planning Time: 0.065 ms
Trigger trg_users_wallet_audit: time=0.125 calls=1
Execution Time: 0.200 ms
```

### Workflow 3 — Nearest Active Driver ($geoNear)

The nearest-driver workflow uses MongoDB's `$geoNear` operator with a
`2dsphere` index on the `location` field. The execution plan confirms
MongoDB uses the `idx_driverpings_location_2dsphere` index via the
`GEO_NEAR_2DSPHERE` stage — no collection scan.

```json
{
  "executionSuccess": true,
  "executionTimeMillis": 3,
  "totalKeysExamined": 332,
  "totalDocsExamined": 282,
  "nReturned": 32,
  "indexUsed": {
    "indexName": "idx_driverpings_location_2dsphere",
    "keyPattern": { "location": "2dsphere" }
  }
}
```

> ⚠️ Confirm with team: the setup script in this README's earlier draft
> showed `$geoNear` followed by `{ $limit: 1 }`, which would produce
> `nReturned: 1`. This run shows `nReturned: 32` — confirm whether `$limit`
> was intentionally changed to return multiple nearby drivers, and update
> `mongo/02_workflow3_geonear.js` / this note so they match.

### Workflow 4 — Multi-Faceted Review Analytics ($facet)

The review analytics workflow filters reviews by `restaurantId` before
running the `$facet` aggregation. The execution plan confirms MongoDB uses
the compound index `idx_reviews_restaurant_rating` via an `IXSCAN` — no
collection scan across the 100,000 reviews.

```json
{
  "executionSuccess": true,
  "executionTimeMillis": 8,
  "totalKeysExamined": 1028,
  "totalDocsExamined": 1028,
  "nReturned": 1028,
  "indexUsed": {
    "indexName": "idx_reviews_restaurant_rating",
    "keyPattern": { "restaurantId": 1, "rating": 1 }
  },
  "sampleRestaurantId": "346c9f49-ef62-42a6-a7d9-75d42837527d"
}
```

`totalKeysExamined == totalDocsExamined == nReturned` here, which is the
expected signature of a clean compound-index match with no post-filter
rejects — every document the index pointed to was relevant and returned.

---

## Repository

- GitHub URL: https://github.com/Karthikb4/Team-25_A1
- Final commit hash: `b42ff80e4bc823c29511d180838f33b28244d60`

  Note: this is the second-last hash, since the last hash would always be
  the README commit itself, and we can't write into the README after
  committing it :)
