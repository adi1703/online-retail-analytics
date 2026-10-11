-- 05 · Revenue concentration / Pareto (top customers & products)
-- ------------------------------------------------------------------
-- Business question: how concentrated is revenue? If a small slice of
-- customers or SKUs carries most of the money, account management and
-- inventory should be ranked by value, not by count — and the long tail
-- becomes a candidate for rationalisation.
--
-- Business rules:
--   * Customer Pareto uses identified customers only (customer_id NOT NULL),
--     so shares are of identified-customer revenue.
--   * Product Pareto uses all cleaned sales.
--   * Running total + running % computed with SUM() OVER an ordered window.
-- ------------------------------------------------------------------

-- (a) Customer Pareto: each customer's running share of revenue
WITH cust AS (
    SELECT customer_id, SUM(revenue) AS revenue
    FROM sales
    WHERE customer_id IS NOT NULL
    GROUP BY customer_id
),
ranked AS (
    SELECT
        customer_id,
        revenue,
        ROW_NUMBER() OVER (ORDER BY revenue DESC)                 AS rev_rank,
        SUM(revenue) OVER (ORDER BY revenue DESC
                           ROWS BETWEEN UNBOUNDED PRECEDING
                           AND CURRENT ROW)                        AS running_revenue,
        SUM(revenue) OVER ()                                       AS total_revenue
    FROM cust
)
SELECT
    rev_rank,
    customer_id,
    ROUND(revenue, 2)                                             AS revenue_gbp,
    ROUND(100.0 * revenue / total_revenue, 2)                    AS pct_of_total,
    ROUND(100.0 * running_revenue / total_revenue, 2)            AS cumulative_pct
FROM ranked
WHERE rev_rank <= 20
ORDER BY rev_rank;

-- (b) Concentration summary: share held by the top-N customers
WITH cust AS (
    SELECT customer_id, SUM(revenue) AS revenue
    FROM sales
    WHERE customer_id IS NOT NULL
    GROUP BY customer_id
),
ranked AS (
    SELECT
        revenue,
        ROW_NUMBER() OVER (ORDER BY revenue DESC) AS rev_rank,
        SUM(revenue) OVER ()                      AS total_revenue
    FROM cust
)
SELECT
    'top 10'  AS bucket,
    ROUND(100.0 * SUM(CASE WHEN rev_rank <= 10  THEN revenue END) / MAX(total_revenue), 1) AS pct_of_revenue
FROM ranked
UNION ALL
SELECT 'top 50',
    ROUND(100.0 * SUM(CASE WHEN rev_rank <= 50  THEN revenue END) / MAX(total_revenue), 1) FROM ranked
UNION ALL
SELECT 'top 100',
    ROUND(100.0 * SUM(CASE WHEN rev_rank <= 100 THEN revenue END) / MAX(total_revenue), 1) FROM ranked;

-- (c) Product Pareto summary: share held by the top-N products
WITH prod AS (
    SELECT stock_code, SUM(revenue) AS revenue
    FROM sales
    GROUP BY stock_code
),
ranked AS (
    SELECT
        revenue,
        ROW_NUMBER() OVER (ORDER BY revenue DESC) AS rev_rank,
        SUM(revenue) OVER ()                      AS total_revenue
    FROM prod
)
SELECT
    'top 10'  AS bucket,
    ROUND(100.0 * SUM(CASE WHEN rev_rank <= 10  THEN revenue END) / MAX(total_revenue), 1) AS pct_of_revenue
FROM ranked
UNION ALL
SELECT 'top 50',
    ROUND(100.0 * SUM(CASE WHEN rev_rank <= 50  THEN revenue END) / MAX(total_revenue), 1) FROM ranked
UNION ALL
SELECT 'top 100',
    ROUND(100.0 * SUM(CASE WHEN rev_rank <= 100 THEN revenue END) / MAX(total_revenue), 1) FROM ranked;
