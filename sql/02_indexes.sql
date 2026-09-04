CREATE UNIQUE INDEX idx_active_user_order
    ON orders (user_id)
 WHERE status IN ('PREPARING', 'DELIVERING');
-- check indexes
SELECT indexname, indexdef
  FROM pg_indexes
 WHERE tablename = 'orders';

-- important for refresh function
CREATE UNIQUE INDEX idx_mv_restaurant_perf_id
    ON mv_restaurant_performance (restaurant_id);

CREATE INDEX idx_mv_restaurant_perf_revenue
    ON mv_restaurant_performance (total_revenue DESC);
