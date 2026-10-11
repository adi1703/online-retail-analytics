# Insight memo, E-Commerce Customer & Revenue Analytics

**To:** Commercial / Growth · **From:** Data Analyst · **Re:** Where revenue concentrates, how much leaks to returns, and which customers to protect
*(REAL public data, UCI Online Retail II (Chen, 2019): ~1.07M raw transactions from a UK-based online gift retailer, Dec 2009 – Dec 2011. After cleaning: **1,003,340 sales lines, 39,516 invoices, 5,852 identified customers, 43 countries, £19.64M revenue (GBP)**. Fully reproducible from the published source.)*

## TL;DR
Revenue is **steeply concentrated**, by geography, by product, and above all by customer, and it is **strongly seasonal**, peaking every November ahead of Christmas. The highest-leverage moves are not chasing new markets but **protecting and growing the small core of customers that already drives most revenue**, capturing the seasonal peak, and trimming a modest but fixable return leak. Most customers never come back after their first month, so first-purchase follow-up is the retention battleground.

## What we found
1. **Revenue is concentrated in one market.** The **UK is 85.5% of revenue (£16.8M)**; the next-largest markets, EIRE (3.2%), Netherlands (2.8%), Germany (2.0%), France (1.6%), are rounding error by comparison. International is an upside option, not the base business.
2. **A small core of customers carries the business.** **RFM "Champions" are 25.2% of identified customers but 69.2% of revenue**; add **Loyal Customers (20.6% / 14.2%)** and two segments hold ~83% of revenue. The Pareto curve is just as stark: the **top 10 customers are 16.1%** of identified-customer revenue, the **top 100 are 37.6%**, and **~23% of customers generate 80% of revenue**. "At Risk" customers, 14.1% of customers but **9.3% of revenue**, are a high-value win-back target slipping away.
3. **Retention is a first-month problem.** Grouping customers by first-purchase month, the **average month-1 repeat-purchase rate is ~21%**, most buyers don't return the next month. But a loyal core persists: the Dec-2009 cohort still shows **~38% active 12 months later**, and overall **72% of identified customers place 2+ orders** over their lifetime. The gap between the 21% one-month figure and the 72% lifetime figure says re-engagement, not one-shot acquisition, is where retention is won.
4. **Returns are a modest, fixable leak.** Cancellations run **3.65% of revenue (£716K)** and **4.18% of units**, healthy overall, but concentrated in a handful of high-value SKUs and large mis-orders worth auditing.
5. **Demand is sharply seasonal.** Monthly revenue **peaks every November** (£1.43M in Nov 2010, £1.45M in Nov 2011) on the pre-Christmas run-up, roughly double a quiet spring month. Inventory, staffing, and marketing spend should be planned around that curve.

## Recommendations (ranked)
1. **Build a retention programme around Champions and Loyal Customers first.** They are ~46% of customers but ~83% of revenue; a loyalty/VIP track, early access, and replenishment nudges defend the revenue base far more cheaply than acquiring its equivalent in new buyers.
2. **Launch a structured win-back for "At Risk" customers.** 9.3% of revenue sits in customers who bought often but haven't recently, a targeted reactivation campaign (they have proven value) has the best ROI of any single lever here.
3. **Fix the first-month retention drop.** With month-1 repeat at ~21% but lifetime repeat at ~72%, invest in onboarding/second-purchase triggers (post-purchase email, first-reorder incentive) to convert one-time buyers into the repeat core.
4. **Plan the business around the November peak and audit return-heavy SKUs.** Pull inventory and demand-gen spend forward into Sept–Nov, and review the top returned products for sizing, description, or quality issues to recover part of the £716K leak.

## Caveat
Real, public dataset, magnitudes are genuine, but this is a single UK gift retailer over two years, so patterns are specific to that business and period. ~22.6% of sales rows have no customer ID (guest/unidentified); those are kept in revenue totals but excluded from all customer-level analysis (RFM, cohort, Pareto), so customer-share figures are of *identified-customer* revenue. The cleaning, SQL, and methodology are production-faithful and fully reproducible from `fetch_data.py → clean_data.py → notebook/analysis.py`.
