-- 01 · Revenue trends — by month, by country, top products
-- ------------------------------------------------------------------
-- Business question: where and when does revenue come from? A monthly
-- trend (with MoM growth), the country mix, and the top products give
-- the demand baseline every other analysis is measured against.
--
-- Business rules:
--   * Grain = cleaned SALES lines only (quantity > 0, price > 0, real
--     product codes). Cancellations live in `returns` and are excluded.
--   * Revenue = quantity * price, in GBP.
--   * Month bucket = first 7 chars of invoice_date ('YYYY-MM').
-- ------------------------------------------------------------------

-- (a) Monthly revenue with month-over-month growth (window LAG)
WITH monthly AS (
    SELECT
        substr(invoice_date, 1, 7) AS month,
        SUM(revenue)               AS revenue,
        COUNT(DISTINCT invoice)    AS invoices
    FROM sales
    GROUP BY substr(invoice_date, 1, 7)
)
SELECT
    month,
    ROUND(revenue, 2)                                          AS revenue_gbp,
    invoices,
    ROUND(revenue - LAG(revenue) OVER (ORDER BY month), 2)     AS mom_delta_gbp,
    ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY month))
          / LAG(revenue) OVER (ORDER BY month), 1)             AS mom_growth_pct
FROM monthly
ORDER BY month;

-- (b) Revenue by country with share of total (window SUM)
WITH by_country AS (
    SELECT country, SUM(revenue) AS revenue
    FROM sales
    GROUP BY country
)
SELECT
    country,
    ROUND(revenue, 2)                                          AS revenue_gbp,
    ROUND(100.0 * revenue / SUM(revenue) OVER (), 2)           AS pct_of_total,
    RANK() OVER (ORDER BY revenue DESC)                        AS revenue_rank
FROM by_country
ORDER BY revenue DESC
LIMIT 15;

-- (c) Top 15 products by revenue
SELECT
    stock_code,
    MAX(description)             AS description,
    SUM(quantity)               AS units_sold,
    ROUND(SUM(revenue), 2)      AS revenue_gbp,
    COUNT(DISTINCT invoice)     AS invoices
FROM sales
GROUP BY stock_code
ORDER BY revenue_gbp DESC
LIMIT 15;
