# %% [markdown]
# # E-Commerce Customer & Revenue Analytics
#
# **Real, public dataset.** This analysis runs on the **UCI Online Retail II**
# dataset — ~1.07M actual transactions from a UK-based online gift retailer,
# Dec 2009 – Dec 2011. Unlike a simulated dataset, every figure below is
# verifiable against the published source:
# *Chen, D. (2019). Online Retail II. UCI Machine Learning Repository.
# https://doi.org/10.24432/C5CG6D*
#
# **Business question:** where does revenue concentrate (months, countries,
# products, customers), how much leaks back out as returns, and which customer
# segments should marketing protect vs. win back?
#
# Data: regenerate with `python ../data/fetch_data.py && python ../data/clean_data.py`.
# Every headline number below is cross-checked against the SQL in `../sql/`.

# %%
import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, PercentFormatter
from matplotlib.colors import LinearSegmentedColormap

D = os.path.join(os.path.dirname(__file__), "..", "data")
OUT = os.path.join(os.path.dirname(__file__), "figures")
os.makedirs(OUT, exist_ok=True)

INK, MUTED, PRIMARY = "#1a1a2e", "#6b7280", "#0f766e"  # teal accent
ACCENTS = ["#0f766e", "#0ea5e9", "#f59e0b", "#ef4444", "#6366f1", "#10b981", "#64748b"]
plt.rcParams.update({
    "figure.dpi": 150, "font.size": 11, "axes.edgecolor": "#e5e7eb",
    "axes.grid": True, "grid.color": "#eef0f3", "axes.spines.top": False,
    "axes.spines.right": False, "axes.titlesize": 13, "axes.titleweight": "bold",
    "axes.titlecolor": INK, "text.color": INK, "axes.labelcolor": MUTED,
    "xtick.color": MUTED, "ytick.color": MUTED,
})


def gbp(x, _=None):
    """Compact GBP axis formatter (£1.2M / £340K / £12)."""
    a = abs(x)
    if a >= 1e6:
        return f"£{x / 1e6:.1f}M"
    if a >= 1e3:
        return f"£{x / 1e3:.0f}K"
    return f"£{x:.0f}"


# Cleaned sales grain + returns (produced by ../data/clean_data.py)
sales = pd.read_csv(f"{D}/online_retail_clean.csv", parse_dates=["invoice_date"])
returns = pd.read_csv(f"{D}/online_retail_returns.csv", parse_dates=["invoice_date"])

total_rev = sales["revenue"].sum()
print(f"{len(sales):,} sales lines | {sales['invoice'].nunique():,} invoices | "
      f"{sales['customer_id'].dropna().nunique():,} customers | "
      f"{sales['country'].nunique()} countries | £{total_rev:,.0f} revenue")
print(f"date range: {sales['invoice_date'].min().date()} -> {sales['invoice_date'].max().date()}")

# %% [markdown]
# ## 0 · The cleaning story (real data is messy)
#
# The raw file is two Excel sheets totalling **1,067,371 rows**. Getting to a
# trustworthy sales grain means removing duplicates, splitting out cancellations,
# dropping non-product "service" codes (POST, DOT, BANK CHARGES, AMAZONFEE,
# gift-card codes…), and discarding non-positive price/quantity. The waterfall
# below is the same one `clean_data.py` prints — reproduced here for the writeup.

# %%
# Re-derive the cleaning waterfall from the raw workbook (for the chart only).
raw = pd.concat(
    [pd.read_excel(f"{D}/online_retail_II.xlsx", sheet_name=s)
     for s in ["Year 2009-2010", "Year 2010-2011"]],
    ignore_index=True,
)
SERVICE = {"POST", "DOT", "M", "C2", "C3", "D", "S", "BANK CHARGES", "ADJUST",
           "ADJUST2", "AMAZONFEE", "CRUK", "B", "PADS"}


def is_service(code):
    c = str(code).strip().upper()
    return c in SERVICE or c.startswith(("TEST", "GIFT"))


w = {}
w["raw rows"] = len(raw)
d = raw.drop_duplicates()
w["after dedupe"] = len(d)
inv = d["Invoice"].astype(str).str.upper()
d2 = d[~inv.str.startswith("C")]
w["after removing\ncancellations"] = len(d2)
d3 = d2[~d2["StockCode"].map(is_service)]
w["after removing\nservice codes"] = len(d3)
d4 = d3[d3["Quantity"] > 0]
w["after Qty > 0"] = len(d4)
d5 = d4[d4["Price"] > 0]
w["after Price > 0\n(final sales)"] = len(d5)

steps = list(w.keys())
vals = list(w.values())
removed = [vals[0]] + [vals[i - 1] - vals[i] for i in range(1, len(vals))]

fig, ax = plt.subplots(figsize=(9, 4.6))
bottom = 0
ax.bar(0, vals[0], color=PRIMARY, width=0.62)
ax.text(0, vals[0] + 8000, f"{vals[0]:,}", ha="center", fontsize=9, color=INK)
for i in range(1, len(vals)):
    base = vals[i]
    drop = vals[i - 1] - vals[i]
    ax.bar(i, base, color=PRIMARY, width=0.62)
    ax.bar(i, drop, bottom=base, color="#fca5a5", width=0.62)
    ax.text(i, vals[i - 1] + 8000, f"-{drop:,}", ha="center", fontsize=8.5, color="#b91c1c")
ax.text(len(vals) - 1, vals[-1] / 2, f"{vals[-1]:,}\nkept", ha="center",
        va="center", fontsize=9, color="white", fontweight="bold")
ax.set_xticks(range(len(steps)))
ax.set_xticklabels(steps, fontsize=8.2)
ax.set_ylabel("Rows")
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v/1e6:.1f}M" if v >= 1e6 else f"{v/1e3:.0f}K"))
ax.set_title("Cleaning waterfall — 1.07M raw rows → 1.00M clean sales lines")
ax.margins(x=0.02)
fig.tight_layout()
fig.savefig(f"{OUT}/data_cleaning.png", facecolor="white")
plt.close(fig)
print(pd.Series(w))
n_missing = int(sales["customer_id"].isna().sum())
print(f"\nNULL customer_id in clean sales: {n_missing:,} ({n_missing/len(sales)*100:.1f}%) "
      f"— kept as revenue, excluded from customer-level analysis.")

# %% [markdown]
# ## 1 · Revenue trend, by country, and top products
# Revenue is strongly seasonal (autumn run-up to Christmas) and overwhelmingly
# concentrated in the home market.

# %%
sales["month"] = sales["invoice_date"].dt.to_period("M").astype(str)
monthly = sales.groupby("month")["revenue"].sum()
# drop the partial final month (Dec 2011 ends on the 9th) for a clean trend line
monthly_full = monthly.iloc[:-1]

fig, ax = plt.subplots(figsize=(9, 4.4))
ax.plot(range(len(monthly_full)), monthly_full.values, "-o", color=PRIMARY, lw=2.4, ms=6)
ax.fill_between(range(len(monthly_full)), monthly_full.values, color=PRIMARY, alpha=0.08)
ax.set_xticks(range(len(monthly_full)))
ax.set_xticklabels(monthly_full.index, rotation=55, ha="right", fontsize=8)
ax.yaxis.set_major_formatter(FuncFormatter(gbp))
ax.set_ylabel("Revenue (GBP)")
ax.set_title("Monthly revenue — seasonal peak each Nov (pre-Christmas)")
peak = monthly_full.idxmax()
pk = list(monthly_full.index).index(peak)
ax.annotate(f"peak {peak}: {gbp(monthly_full.max())}", (pk, monthly_full.max()),
            textcoords="offset points", xytext=(-12, -22), ha="right",
            fontsize=8.5, color=INK,
            arrowprops=dict(arrowstyle="->", color=MUTED, lw=0.9))
fig.tight_layout()
fig.savefig(f"{OUT}/revenue_trend.png", facecolor="white")
plt.close(fig)
print(monthly_full.round(0))

# %%
# Country mix + top products (combined reference figure)
cty = sales.groupby("country")["revenue"].sum().sort_values(ascending=False)
cty_top = cty.head(8)[::-1]
prod = (sales.groupby("stock_code")
        .agg(rev=("revenue", "sum"), desc=("description", "first"))
        .sort_values("rev", ascending=False).head(10))
prod_lbl = (prod["desc"].str.title().str.slice(0, 28))[::-1]

fig, (axc, axp) = plt.subplots(1, 2, figsize=(11, 4.6))
axc.barh(range(len(cty_top)), cty_top.values, color=PRIMARY)
axc.set_yticks(range(len(cty_top)))
axc.set_yticklabels(cty_top.index, fontsize=9)
axc.xaxis.set_major_formatter(FuncFormatter(gbp))
axc.set_title(f"Revenue by country (UK = {cty['United Kingdom']/total_rev*100:.0f}% of total)")
for i, v in enumerate(cty_top.values):
    axc.text(v, i, f"  {v/total_rev*100:.1f}%", va="center", fontsize=8, color=MUTED)

axp.barh(range(len(prod)), prod["rev"].values[::-1], color=ACCENTS[1])
axp.set_yticks(range(len(prod)))
axp.set_yticklabels(prod_lbl, fontsize=8)
axp.xaxis.set_major_formatter(FuncFormatter(gbp))
axp.set_title("Top 10 products by revenue")
fig.tight_layout()
fig.savefig(f"{OUT}/top_products_and_country.png", facecolor="white")
plt.close(fig)
print(cty.head(6).round(0))
print(prod[["desc", "rev"]].round(0).to_string())

# %% [markdown]
# ## 2 · Returns analysis
# Cancellations (invoices starting `C`) are real revenue leakage. The overall
# rate is modest but a handful of SKUs and high-value mis-orders dominate it.

# %%
ret_val = -returns["revenue"].sum()
ret_units = -returns["quantity"].sum()
rate_val = ret_val / total_rev * 100
rate_vol = ret_units / sales["quantity"].sum() * 100

returns["month"] = returns["invoice_date"].dt.to_period("M").astype(str)
ret_m = (-returns.groupby("month")["revenue"].sum())
sales_m = sales.groupby("month")["revenue"].sum()
rate_m = (ret_m / sales_m * 100).dropna().iloc[:-1]

fig, ax = plt.subplots(figsize=(9, 4.2))
ax.bar(range(len(rate_m)), rate_m.values, color=ACCENTS[3], width=0.7)
ax.axhline(rate_val, color=INK, ls="--", lw=1.2)
ax.text(len(rate_m) - 1, rate_val + 0.2, f"overall {rate_val:.1f}% by value",
        ha="right", fontsize=8.5, color=INK)
ax.set_xticks(range(len(rate_m)))
ax.set_xticklabels(rate_m.index, rotation=55, ha="right", fontsize=8)
ax.yaxis.set_major_formatter(PercentFormatter())
ax.set_ylabel("Return rate (% of monthly sales £)")
ax.set_title("Monthly return rate by value")
fig.tight_layout()
fig.savefig(f"{OUT}/returns.png", facecolor="white")
plt.close(fig)
print(f"return rate by VALUE : {rate_val:.2f}%  (£{ret_val:,.0f} of £{total_rev:,.0f})")
print(f"return rate by VOLUME: {rate_vol:.2f}%  ({ret_units:,.0f} of {sales['quantity'].sum():,.0f} units)")

# %% [markdown]
# ## 3 · RFM customer segmentation
# Score every identified customer on Recency / Frequency / Monetary (NTILE
# quintiles), then map to action segments. **Champions are a quarter of
# customers but ~69% of revenue** — the classic skew that should drive spend.

# %%
cust = sales.dropna(subset=["customer_id"]).copy()
cust["customer_id"] = cust["customer_id"].astype(int)
snapshot = cust["invoice_date"].max() + pd.Timedelta(days=1)
rfm = cust.groupby("customer_id").agg(
    recency=("invoice_date", lambda x: (snapshot - x.max()).days),
    frequency=("invoice", "nunique"),
    monetary=("revenue", "sum")).reset_index()
rfm["R"] = pd.qcut(rfm["recency"], 5, labels=[5, 4, 3, 2, 1]).astype(int)
rfm["F"] = pd.qcut(rfm["frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
rfm["M"] = pd.qcut(rfm["monetary"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)


def segment(row):
    R, F = row["R"], row["F"]
    if R >= 4 and F >= 4:
        return "Champions"
    if R >= 3 and F >= 3:
        return "Loyal Customers"
    if R >= 4 and F <= 2:
        return "New / Potential Loyalists"
    if R >= 3 and F <= 2:
        return "Promising"
    if R <= 2 and F >= 3:
        return "At Risk"
    if R <= 2 and F >= 2:
        return "Hibernating"
    return "Lost"


rfm["segment"] = rfm.apply(segment, axis=1)
seg = rfm.groupby("segment").agg(
    customers=("customer_id", "count"), revenue=("monetary", "sum"))
seg["cust_pct"] = seg["customers"] / seg["customers"].sum() * 100
seg["rev_pct"] = seg["revenue"] / seg["revenue"].sum() * 100
seg = seg.sort_values("revenue", ascending=False)

order = seg.index[::-1]
fig, ax = plt.subplots(figsize=(9, 4.8))
y = np.arange(len(order))
ax.barh(y - 0.2, seg.loc[order, "cust_pct"], height=0.38, color=MUTED, label="% of customers")
ax.barh(y + 0.2, seg.loc[order, "rev_pct"], height=0.38, color=PRIMARY, label="% of revenue")
ax.set_yticks(y)
ax.set_yticklabels(order, fontsize=9)
ax.xaxis.set_major_formatter(PercentFormatter())
ax.set_title("RFM segments — share of customers vs share of revenue")
ax.legend(loc="lower right", frameon=False, fontsize=9)
for yi, s in zip(y, order):
    ax.text(seg.loc[s, "rev_pct"] + 0.6, yi + 0.2, f"{seg.loc[s,'rev_pct']:.0f}%",
            va="center", fontsize=8, color=INK)
fig.tight_layout()
fig.savefig(f"{OUT}/rfm_segments.png", facecolor="white")
plt.close(fig)
print(seg[["customers", "cust_pct", "revenue", "rev_pct"]].round(1).to_string())

# %% [markdown]
# ## 4 · Monthly cohort retention
# Group customers by their first-purchase month and track repeat purchasing.
# Retention drops sharply after month 0, but a loyal core keeps buying a year
# later — and the long-lived 2009-12 cohort even rebounds the following Christmas.

# %%
cust["order_month"] = cust["invoice_date"].dt.to_period("M")
first = cust.groupby("customer_id")["order_month"].min().rename("cohort")
cust = cust.join(first, on="customer_id")
cust["pidx"] = (cust["order_month"].astype("int64") - cust["cohort"].astype("int64")).astype(int)
piv = (cust.groupby(["cohort", "pidx"])["customer_id"].nunique().unstack("pidx"))
size = piv[0]
ret = piv.div(size, axis=0) * 100
ret = ret.iloc[:, :13]  # first 13 month-offsets
ret.index = ret.index.astype(str)

fig, ax = plt.subplots(figsize=(10, 6))
cmap = LinearSegmentedColormap.from_list("teal", ["#f8fafc", "#99f6e4", PRIMARY, "#134e4a"])
data = ret.values.astype(float)
im = ax.imshow(np.ma.masked_invalid(data), aspect="auto", cmap=cmap, vmin=0, vmax=50)
ax.set_xticks(range(ret.shape[1]))
ax.set_xticklabels(range(ret.shape[1]), fontsize=9)
ax.set_yticks(range(ret.shape[0]))
ax.set_yticklabels([f"{c}  (n={int(size.loc[pd.Period(c)])})" for c in ret.index], fontsize=8)
ax.set_xlabel("Months since first purchase")
ax.set_title("Monthly cohort retention — repeat-purchase % by acquisition cohort")
for i in range(data.shape[0]):
    for j in range(data.shape[1]):
        v = data[i, j]
        if not np.isnan(v):
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=6.5,
                    color="white" if v > 25 else INK)
cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
cb.set_label("retention %", fontsize=8)
ax.grid(False)
fig.tight_layout()
fig.savefig(f"{OUT}/cohort_retention.png", facecolor="white")
plt.close(fig)
m1 = ret[1].dropna()
print(f"avg month-1 repeat rate: {m1.mean():.1f}%")
print(f"2009-12 cohort: size={int(size.iloc[0])}, m1={ret.loc['2009-12',1]:.1f}%, m12={ret.loc['2009-12',12]:.1f}%")
print(f"overall repeat-customer rate (>=2 invoices): "
      f"{(cust.groupby('customer_id')['invoice'].nunique() >= 2).mean()*100:.1f}%")

# %% [markdown]
# ## 5 · Revenue concentration (Pareto)
# A Pareto curve confirms the skew: a small minority of customers carries the
# bulk of revenue, so account management should rank by value, not count.

# %%
cust_rev = (cust.groupby("customer_id")["revenue"].sum()
            .sort_values(ascending=False).reset_index(drop=True))
cum = cust_rev.cumsum() / cust_rev.sum() * 100
share = np.arange(1, len(cust_rev) + 1) / len(cust_rev) * 100
n80 = int((cum <= 80).sum()) + 1
pct80 = n80 / len(cust_rev) * 100
top10 = cust_rev.head(10).sum() / cust_rev.sum() * 100
top100 = cust_rev.head(100).sum() / cust_rev.sum() * 100

fig, ax = plt.subplots(figsize=(8.5, 4.6))
ax.plot(share, cum.values, color=PRIMARY, lw=2.6)
ax.fill_between(share, cum.values, color=PRIMARY, alpha=0.08)
ax.axhline(80, color=MUTED, ls="--", lw=1)
ax.axvline(pct80, color=ACCENTS[3], ls="--", lw=1)
ax.plot(pct80, 80, "o", color=ACCENTS[3], ms=8)
ax.annotate(f"{pct80:.0f}% of customers\n= 80% of revenue", (pct80, 80),
            textcoords="offset points", xytext=(16, -28), fontsize=9, color=INK,
            arrowprops=dict(arrowstyle="->", color=MUTED))
ax.set_xlabel("Customers (ranked by revenue, %)")
ax.set_ylabel("Cumulative revenue (%)")
ax.xaxis.set_major_formatter(PercentFormatter())
ax.yaxis.set_major_formatter(PercentFormatter())
ax.set_title("Customer revenue Pareto (identified customers)")
ax.set_xlim(0, 100)
ax.set_ylim(0, 101)
fig.tight_layout()
fig.savefig(f"{OUT}/pareto.png", facecolor="white")
plt.close(fig)
print(f"top 10 customers : {top10:.1f}% of identified-customer revenue")
print(f"top 100 customers: {top100:.1f}%")
print(f"{pct80:.1f}% of customers ({n80}) generate 80% of revenue")

# %% [markdown]
# ## Headline summary (cross-checks the SQL in `../sql/`)

# %%
print("=" * 60)
print("UCI ONLINE RETAIL II — headline metrics (REAL data, GBP)")
print("=" * 60)
print(f"total revenue          : £{total_rev:,.2f}")
print(f"unique invoices        : {sales['invoice'].nunique():,}")
print(f"unique customers       : {sales['customer_id'].dropna().nunique():,}")
print(f"unique products        : {sales['stock_code'].nunique():,}")
print(f"countries              : {sales['country'].nunique()}")
print(f"date range             : {sales['invoice_date'].min().date()} -> {sales['invoice_date'].max().date()}")
print(f"top country            : United Kingdom ({cty['United Kingdom']/total_rev*100:.1f}% of revenue)")
print(f"return rate (value)    : {rate_val:.2f}%")
print(f"return rate (volume)   : {rate_vol:.2f}%")
print(f"Champions segment      : {seg.loc['Champions','cust_pct']:.1f}% of customers, "
      f"{seg.loc['Champions','rev_pct']:.1f}% of revenue")
print(f"top-10-customer share  : {top10:.1f}% of identified-customer revenue")
print(f"80% revenue from        : {pct80:.1f}% of customers")
print("\nAll figures saved to notebook/figures/")
