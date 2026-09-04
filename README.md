# BiteStream — Food Delivery & Real-Time Logistics

Team 25 
Project 1 of 5 (assigned via `team_no % 5 + 1`)

A production-style persistence layer split across PostgreSQL (transactional
data: users, wallets, orders) and MongoDB (flexible/high-volume data: menus,
reviews, driver geolocation pings).

---

## Setup Steps

> ⚠️ Fill in as each part is actually run and confirmed working. Do not mark
> a step done until someone has run it themselves.

### PostgreSQL

1. Create a database (e.g. `bitestream`) on PostgreSQL [version].
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
- **[Add MongoDB schema assumptions here once `01_collections_and_indexes.js`
  and `mongo_schema_map.json` are written — e.g. embedding vs. referencing
  choices in `menus`, validation strictness, TTL window rationale.]**

---

## Open Items / Known Gaps

- [ ] Reconcile `postgres_seeder.py`'s raw wallet `UPDATE` behavior with the
      order-insert-triggered audit design (see Assumptions above). Decide:
      either route seeded wallet changes through `sp_execute_checkout`, or
      extend the trigger to also cover direct `UPDATE OF wallet_balance`.
- [ ] No code path currently produces a `CREDIT` audit log row. Confirm
      whether the assignment/viva requires demonstrating this, and if so,
      add a refund/top-up path.
- [ ] `docs/relational_erd.png` — pending.
- [ ] `docs/mongo_schema_map.json` — pending.
- [ ] `sql/05_materialized_views.sql`, `sql/06_window_analytics.sql` — pending.
- [ ] `mongo/01_collections_and_indexes.js`, `02_workflow3_geonear.js`,
      `03_workflow4_facet.js` — pending.
- [ ] `performance/postgres_explain_analyzes.txt`,
      `performance/mongo_execution_stats.json` — pending; requires all of the
      above to exist and run against seeded data first.

---

## EXPLAIN Plans (Performance Proof)

> Paste raw `EXPLAIN ANALYZE` (Postgres) and `explain('executionStats')`
> (Mongo) output here for Workflows 2, 3, and 4 once available. Confirm each
> plan shows an **Index Scan / Bitmap Index Scan** (not `Seq Scan`) or
> **IXSCAN** (not `COLLSCAN`) before pasting — a scan that isn't hitting an
> index isn't proof of anything and should be fixed first.

### Workflow 2 — SQL Window Analytics (7-day moving average, DENSE_RANK)

```
[paste EXPLAIN ANALYZE output here]
```

### Workflow 3 — Nearest Active Driver ($geoNear)

```
[paste explain("executionStats") output here]
```

### Workflow 4 — Multi-Faceted Review Analytics ($facet)

```
[paste explain("executionStats") output here]
```

---

## Repository

- GitHub URL: [fill in]
- Final commit hash: [fill in at submission time]
