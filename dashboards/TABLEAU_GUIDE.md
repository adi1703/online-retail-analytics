# Tableau Public build guide, "E-Commerce Customer & Revenue Analytics"

**Goal:** one interactive Tableau Public dashboard a commercial team could steer the
business with, revenue trend, country mix, returns, RFM segments, and cohort retention.
**Time:** ~90 min. **Cost:** free. Every dataset is pre-aggregated in `dashboards/extracts/`, no pivoting needed (or connect raw `../data/online_retail_clean.csv` to show the wrangling).
**Source:** UCI Online Retail II (real UK online-retail transactions, 2009–2011).

## 0. Setup
Download **Tableau Public** (free), create an account, **Connect → Text file** for each CSV below.

## 1. Worksheets

| # | Sheet | Data source | Build |
|---|-------|-------------|-------|
| A | **Monthly revenue** (headline) | `01_revenue_by_month.csv` | Line: Columns `month` (discrete), Rows `revenue_gbp`; add `mom_growth_pct` as a label or second axis. Title: *"Revenue peaks every November (pre-Christmas)."* |
| B | **Revenue by country** | `02_revenue_by_country.csv` | Horizontal bars: Rows `country` (filter to top 8 by `revenue_gbp`), Columns `revenue_gbp`, label `pct_of_total`. Title: *"85% of revenue is the home UK market."* |
| C | **Top products** | `03_top_products.csv` | Horizontal bars: Rows `description` (sort by `revenue_gbp` desc, top 10), Columns `revenue_gbp`. |
| D | **Return rate over time** | `04_returns_by_month.csv` | Bars `return_rate_pct` by `month`, with a reference line at the overall 3.6%. Title: *"Returns run ~3–4% of revenue."* |
| E | **RFM segments** | `05_rfm_segments.csv` | Bars: Rows `segment` (sort by `revenue_gbp` desc), dual measure `pct_customers` vs `pct_revenue`. Title: *"Champions = 25% of customers, 69% of revenue."* |
| F | **Cohort retention heatmap** | `06_cohort_retention_long.csv` | Marks = Square; Columns `period_index`, Rows `cohort_month`, Color `retention_pct` (teal sequential), label values. Title: *"Repeat-purchase retention by acquisition cohort."* |
| G | **Customer Pareto** | `07_customer_pareto.csv` | Line: Columns `customer_pct`, Rows `cumulative_revenue_pct`; reference lines at 80% rev / 23% customers. Title: *"~23% of customers drive 80% of revenue."* |

**KPI tiles (optional):** `£19.6M revenue`, `5,852 customers`, `39,516 invoices`, `43 countries`,
`3.6% return rate` (type as text or build from the extracts).

## 2. Dashboard
- New Dashboard 1200×900. Title: **E-Commerce Customer & Revenue Analytics, UCI Online Retail II**.
- Top: KPI tiles. Left column: A + B + C (the revenue story). Right column: E + F + G (customers).
  Bottom strip: D (returns).
- Footer text: *"Real public data, UCI Online Retail II (Chen, 2019). Fully reproducible from fetch_data.py → clean_data.py."*
- Teal accent (#0f766e), hide gridlines, tooltips on.

## 3. Publish + wire back
1. **Server → Tableau Public → Save** → copy the URL.
2. Set `TABLEAU_URL` in the portfolio `src/app/projects/online-retail/dashboards.tsx`, and screenshot the
   dashboard to `public/images/online-retail/tableau.png` for a sharper preview.
3. Send me the URL and I'll wire it in / embed the live viz. *(TODO: dashboard not yet published.)*
