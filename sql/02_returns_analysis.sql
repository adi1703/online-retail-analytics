-- 02 · Returns analysis — return rate by value and by volume
-- ------------------------------------------------------------------
-- Business question: how much revenue leaks back out as cancellations,
-- and which products / months drive it? Returns erode net revenue and
-- flag quality, sizing, or expectation problems.
--
-- Business rules:
--   * Returns = lines on invoices starting 'C' (negative quantity),
--     held in the `returns` table; their revenue is negative.
--   * Return VALUE rate  = |returns revenue| / sales revenue.
--   * Return VOLUME rate = |returns units|  / sales units.
--   * Same non-product service codes already removed from both tables.
-- ------------------------------------------------------------------

-- (a) Headline return rates (value and volume)
WITH s AS (
    SELECT SUM(revenue) AS sales_rev, SUM(quantity) AS sales_units
    FROM sales
),
r AS (
    SELECT SUM(revenue) AS ret_rev, SUM(quantity) AS ret_units
    FROM returns
)
SELECT
    ROUND(s.sales_rev, 2)                                  AS sales_revenue_gbp,
    ROUND(-r.ret_rev, 2)                                   AS returns_value_gbp,
    ROUND(100.0 * (-r.ret_rev) / s.sales_rev, 2)           AS return_rate_value_pct,
    s.sales_units                                          AS units_sold,
    -r.ret_units                                           AS units_returned,
    ROUND(100.0 * (-r.ret_units) / s.sales_units, 2)       AS return_rate_volume_pct
FROM s, r;

-- (b) Monthly return value vs sales value (window-free trend)
WITH sales_m AS (
    SELECT substr(invoice_date, 1, 7) AS month, SUM(revenue) AS sales_rev
    FROM sales GROUP BY 1
),
ret_m AS (
    SELECT substr(invoice_date, 1, 7) AS month, SUM(revenue) AS ret_rev
    FROM returns GROUP BY 1
)
SELECT
    sales_m.month,
    ROUND(sales_m.sales_rev, 2)                              AS sales_gbp,
    ROUND(-COALESCE(ret_m.ret_rev, 0), 2)                    AS returns_gbp,
    ROUND(100.0 * (-COALESCE(ret_m.ret_rev, 0))
          / sales_m.sales_rev, 2)                            AS return_rate_pct
FROM sales_m
LEFT JOIN ret_m ON sales_m.month = ret_m.month
ORDER BY sales_m.month;

-- (c) Top 15 most-returned products by returned value
SELECT
    stock_code,
    MAX(description)                AS description,
    -SUM(quantity)                  AS units_returned,
    ROUND(-SUM(revenue), 2)         AS returned_value_gbp,
    COUNT(DISTINCT invoice)         AS return_invoices
FROM returns
GROUP BY stock_code
ORDER BY returned_value_gbp DESC
LIMIT 15;
