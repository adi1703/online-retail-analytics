-- 04 · Monthly cohort retention (repeat-purchase by first-order month)
-- ------------------------------------------------------------------
-- Business question: once a customer makes a first purchase, do they come
-- back? Grouping customers by the MONTH of their first order and tracking
-- how many transact again N months later exposes retention decay and how
-- "sticky" each acquisition cohort is.
--
-- Business rules:
--   * Identified customers only (customer_id NOT NULL).
--   * Cohort = month of a customer's FIRST order ('YYYY-MM').
--   * period_index = whole months between order month and cohort month.
--   * Cell value = distinct customers from that cohort active in that
--     period; retention % = cell / cohort size (period 0).
-- ------------------------------------------------------------------

WITH orders AS (
    SELECT
        customer_id,
        substr(invoice_date, 1, 7) AS order_month
    FROM sales
    WHERE customer_id IS NOT NULL
    GROUP BY customer_id, substr(invoice_date, 1, 7)
),
cohort AS (
    SELECT customer_id, MIN(order_month) AS cohort_month
    FROM orders
    GROUP BY customer_id
),
joined AS (
    SELECT
        c.cohort_month,
        o.order_month,
        o.customer_id,
        -- whole-month offset between cohort month and activity month
        (CAST(substr(o.order_month, 1, 4) AS INTEGER) * 12
            + CAST(substr(o.order_month, 6, 2) AS INTEGER))
        - (CAST(substr(c.cohort_month, 1, 4) AS INTEGER) * 12
            + CAST(substr(c.cohort_month, 6, 2) AS INTEGER)) AS period_index
    FROM orders o
    JOIN cohort c ON o.customer_id = c.customer_id
),
cells AS (
    SELECT
        cohort_month,
        period_index,
        COUNT(DISTINCT customer_id) AS active_customers
    FROM joined
    GROUP BY cohort_month, period_index
),
sizes AS (
    SELECT cohort_month, active_customers AS cohort_size
    FROM cells
    WHERE period_index = 0
)
SELECT
    c.cohort_month,
    s.cohort_size,
    c.period_index,
    c.active_customers,
    ROUND(100.0 * c.active_customers / s.cohort_size, 1) AS retention_pct
FROM cells c
JOIN sizes s ON c.cohort_month = s.cohort_month
ORDER BY c.cohort_month, c.period_index;
