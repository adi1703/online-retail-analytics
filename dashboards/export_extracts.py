"""Export tidy, single-table CSVs to dashboards/extracts/ so the Tableau
dashboard can be assembled in minutes. The sql/*.sql files contain several
statements each (the (a)/(b)/(c) blocks), so this script builds one clean
extract per visual from the SQLite DB rather than dumping raw query output.

Run after data/clean_data.py:
    python dashboards/export_extracts.py
"""

import os
import sqlite3

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "..", "data", "online_retail.db")
OUT = os.path.join(HERE, "extracts")
os.makedirs(OUT, exist_ok=True)

con = sqlite3.connect(DB)


def q(sql: str) -> pd.DataFrame:
    return pd.read_sql_query(sql, con)


def write(df: pd.DataFrame, name: str) -> None:
    df.to_csv(os.path.join(OUT, name), index=False)
    print(f"{name}: {len(df)} rows")


# 1 · monthly revenue (with MoM growth)
write(q("""
    WITH m AS (
        SELECT substr(invoice_date,1,7) AS month,
               SUM(revenue) AS revenue, COUNT(DISTINCT invoice) AS invoices
        FROM sales GROUP BY 1)
    SELECT month, ROUND(revenue,2) AS revenue_gbp, invoices,
           ROUND(100.0*(revenue-LAG(revenue) OVER (ORDER BY month))
                 /LAG(revenue) OVER (ORDER BY month),1) AS mom_growth_pct
    FROM m ORDER BY month
"""), "01_revenue_by_month.csv")

# 2 · revenue by country (with share)
write(q("""
    WITH c AS (SELECT country, SUM(revenue) AS revenue FROM sales GROUP BY 1)
    SELECT country, ROUND(revenue,2) AS revenue_gbp,
           ROUND(100.0*revenue/SUM(revenue) OVER (),2) AS pct_of_total
    FROM c ORDER BY revenue DESC
"""), "02_revenue_by_country.csv")

# 3 · top 20 products
write(q("""
    SELECT stock_code, MAX(description) AS description,
           SUM(quantity) AS units_sold, ROUND(SUM(revenue),2) AS revenue_gbp
    FROM sales GROUP BY stock_code ORDER BY revenue_gbp DESC LIMIT 20
"""), "03_top_products.csv")

# 4 · monthly return rate (sales vs returns)
write(q("""
    WITH s AS (SELECT substr(invoice_date,1,7) AS month, SUM(revenue) AS sales_rev
               FROM sales GROUP BY 1),
         r AS (SELECT substr(invoice_date,1,7) AS month, SUM(revenue) AS ret_rev
               FROM returns GROUP BY 1)
    SELECT s.month, ROUND(s.sales_rev,2) AS sales_gbp,
           ROUND(-COALESCE(r.ret_rev,0),2) AS returns_gbp,
           ROUND(100.0*(-COALESCE(r.ret_rev,0))/s.sales_rev,2) AS return_rate_pct
    FROM s LEFT JOIN r ON s.month=r.month ORDER BY s.month
"""), "04_returns_by_month.csv")

# 5 · RFM segment summary (the table 03_rfm_segmentation.sql produces)
write(q("""
    WITH base AS (
        SELECT customer_id, MAX(invoice_date) AS last_order,
               COUNT(DISTINCT invoice) AS frequency, SUM(revenue) AS monetary
        FROM sales WHERE customer_id IS NOT NULL GROUP BY customer_id),
    snap AS (SELECT date(MAX(invoice_date),'+1 day') AS snapshot FROM sales),
    rec AS (
        SELECT b.customer_id,
               CAST(julianday(s.snapshot)-julianday(b.last_order) AS INTEGER) AS recency_days,
               b.frequency, b.monetary
        FROM base b CROSS JOIN snap s),
    scored AS (
        SELECT customer_id, recency_days, frequency, monetary,
               6-NTILE(5) OVER (ORDER BY recency_days) AS r,
               NTILE(5) OVER (ORDER BY frequency, customer_id) AS f
        FROM rec),
    seg AS (
        SELECT *, CASE
            WHEN r>=4 AND f>=4 THEN 'Champions'
            WHEN r>=3 AND f>=3 THEN 'Loyal Customers'
            WHEN r>=4 AND f<=2 THEN 'New / Potential Loyalists'
            WHEN r>=3 AND f<=2 THEN 'Promising'
            WHEN r<=2 AND f>=3 THEN 'At Risk'
            WHEN r<=2 AND f>=2 THEN 'Hibernating'
            ELSE 'Lost' END AS segment FROM scored)
    SELECT segment, COUNT(*) AS customers,
           ROUND(100.0*COUNT(*)/SUM(COUNT(*)) OVER (),1) AS pct_customers,
           ROUND(SUM(monetary),2) AS revenue_gbp,
           ROUND(100.0*SUM(monetary)/SUM(SUM(monetary)) OVER (),1) AS pct_revenue
    FROM seg GROUP BY segment ORDER BY revenue_gbp DESC
"""), "05_rfm_segments.csv")

# 6 · cohort retention in LONG form (no Tableau pivot needed)
write(q("""
    WITH orders AS (
        SELECT customer_id, substr(invoice_date,1,7) AS order_month
        FROM sales WHERE customer_id IS NOT NULL
        GROUP BY customer_id, substr(invoice_date,1,7)),
    cohort AS (SELECT customer_id, MIN(order_month) AS cohort_month FROM orders GROUP BY customer_id),
    joined AS (
        SELECT c.cohort_month, o.customer_id,
               (CAST(substr(o.order_month,1,4) AS INT)*12+CAST(substr(o.order_month,6,2) AS INT))
              -(CAST(substr(c.cohort_month,1,4) AS INT)*12+CAST(substr(c.cohort_month,6,2) AS INT)) AS period_index
        FROM orders o JOIN cohort c ON o.customer_id=c.customer_id),
    cells AS (SELECT cohort_month, period_index, COUNT(DISTINCT customer_id) AS active FROM joined GROUP BY 1,2),
    sizes AS (SELECT cohort_month, active AS cohort_size FROM cells WHERE period_index=0)
    SELECT c.cohort_month, s.cohort_size, c.period_index, c.active AS active_customers,
           ROUND(100.0*c.active/s.cohort_size,1) AS retention_pct
    FROM cells c JOIN sizes s ON c.cohort_month=s.cohort_month
    WHERE c.period_index <= 12
    ORDER BY c.cohort_month, c.period_index
"""), "06_cohort_retention_long.csv")

# 7 · customer Pareto curve (ranked, running %)
write(q("""
    WITH cust AS (SELECT customer_id, SUM(revenue) AS revenue
                  FROM sales WHERE customer_id IS NOT NULL GROUP BY customer_id),
    ranked AS (
        SELECT customer_id, revenue,
               ROW_NUMBER() OVER (ORDER BY revenue DESC) AS rev_rank,
               SUM(revenue) OVER (ORDER BY revenue DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running,
               SUM(revenue) OVER () AS total FROM cust)
    SELECT rev_rank, ROUND(revenue,2) AS revenue_gbp,
           ROUND(100.0*rev_rank/(SELECT COUNT(*) FROM cust),2) AS customer_pct,
           ROUND(100.0*running/total,2) AS cumulative_revenue_pct
    FROM ranked ORDER BY rev_rank
"""), "07_customer_pareto.csv")

con.close()
print("\nExtracts written to dashboards/extracts/")
