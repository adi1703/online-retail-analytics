-- 03 · RFM customer segmentation (Recency / Frequency / Monetary)
-- ------------------------------------------------------------------
-- Business question: which customers should marketing protect, grow, or
-- win back? RFM scores every customer on how recently they bought, how
-- often, and how much, then maps the score to a named action segment.
--
-- Business rules:
--   * Only customers with a non-NULL customer_id (guest rows excluded).
--   * Snapshot date = max(invoice_date) + 1 day (so recency >= 1).
--   * Recency  = days since last order  (LOWER is better).
--   * Frequency = # distinct invoices.
--   * Monetary  = total revenue (GBP).
--   * NTILE(5) quintiles per dimension. Recency is reversed so 5 = best
--     (most recent). Segment names follow the standard RFM grid.
-- ------------------------------------------------------------------

WITH base AS (
    SELECT
        customer_id,
        MAX(invoice_date)        AS last_order,
        COUNT(DISTINCT invoice)  AS frequency,
        SUM(revenue)             AS monetary
    FROM sales
    WHERE customer_id IS NOT NULL
    GROUP BY customer_id
),
snap AS (
    SELECT date(MAX(invoice_date), '+1 day') AS snapshot FROM sales
),
recency AS (
    SELECT
        b.customer_id,
        CAST(julianday(s.snapshot) - julianday(b.last_order) AS INTEGER) AS recency_days,
        b.frequency,
        b.monetary
    FROM base b CROSS JOIN snap s
),
scored AS (
    SELECT
        customer_id,
        recency_days,
        frequency,
        ROUND(monetary, 2) AS monetary,
        -- recency: smallest days -> highest score (reverse NTILE)
        6 - NTILE(5) OVER (ORDER BY recency_days)            AS r_score,
        NTILE(5) OVER (ORDER BY frequency, customer_id)      AS f_score,
        NTILE(5) OVER (ORDER BY monetary,  customer_id)      AS m_score
    FROM recency
),
segmented AS (
    SELECT
        *,
        CASE
            WHEN r_score >= 4 AND f_score >= 4 THEN 'Champions'
            WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal Customers'
            WHEN r_score >= 4 AND f_score <= 2 THEN 'New / Potential Loyalists'
            WHEN r_score >= 3 AND f_score <= 2 THEN 'Promising'
            WHEN r_score <= 2 AND f_score >= 3 THEN 'At Risk'
            WHEN r_score <= 2 AND f_score >= 2 THEN 'Hibernating'
            ELSE 'Lost'
        END AS segment
    FROM scored
)
SELECT
    segment,
    COUNT(*)                                                   AS customers,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)         AS pct_customers,
    ROUND(SUM(monetary), 2)                                    AS revenue_gbp,
    ROUND(100.0 * SUM(monetary) / SUM(SUM(monetary)) OVER (), 1) AS pct_revenue,
    ROUND(AVG(recency_days), 0)                                AS avg_recency_days,
    ROUND(AVG(frequency), 1)                                   AS avg_frequency,
    ROUND(AVG(monetary), 0)                                    AS avg_monetary_gbp
FROM segmented
GROUP BY segment
ORDER BY revenue_gbp DESC;
