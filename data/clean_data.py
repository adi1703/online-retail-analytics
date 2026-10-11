"""
Cleaning pipeline for the REAL UCI Online Retail II dataset.

Reads the raw two-sheet .xlsx produced by fetch_data.py, applies a documented,
auditable cleaning sequence, and writes:

    data/online_retail_clean.csv   -- valid SALES lines (the analysis grain)
    data/online_retail_returns.csv -- cancellation / return lines (analysed separately)
    data/online_retail.db          -- SQLite DB (schema.sql), git-ignored

The whole point of this project is REAL, messy, publicly-verifiable data, so the
cleaning is explicit and every step prints a before -> after row count by reason.

Cleaning decisions (see README for the business rationale):
  1. Drop exact duplicate rows.
  2. Split off cancellations: Invoice starts with 'C' (these carry negative Qty) ->
     treated as RETURNS, written separately, excluded from the sales grain.
  3. Drop non-product "service" StockCodes (POST, DOT, M, C2, D, S, BANK CHARGES,
     ADJUST, ADJUST2, AMAZONFEE, CRUK, B, TEST*, PADS, GIFT*/GIFT_0001_*, etc.).
  4. Drop rows with Quantity <= 0 in the SALES grain (returns already removed).
  5. Drop rows with Price <= 0 (free/adjustment lines, not genuine sales).
  6. Trim whitespace; standardise types; add revenue = Quantity * Price.
  7. Customer ID is NULL on ~22-23% of rows. We KEEP these in the sales CSV
     (they are real revenue) but FLAG them; customer-level analyses (RFM, cohort)
     filter to rows where customer_id IS NOT NULL. The dropped count is reported.
"""

import os
import sqlite3
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
XLSX_PATH = os.path.join(HERE, "online_retail_II.xlsx")
CLEAN_CSV = os.path.join(HERE, "online_retail_clean.csv")
RETURNS_CSV = os.path.join(HERE, "online_retail_returns.csv")
DB_PATH = os.path.join(HERE, "online_retail.db")
SCHEMA_SQL = os.path.join(HERE, "schema.sql")

# Non-product "service" codes (upper-cased, exact match or GIFT prefix).
SERVICE_CODES = {
    "POST", "DOT", "M", "C2", "C3", "D", "S", "BANK CHARGES",
    "ADJUST", "ADJUST2", "AMAZONFEE", "CRUK", "B", "PADS",
}
SERVICE_PREFIXES = ("TEST", "GIFT")  # TEST001/2, GIFT, GIFT_0001_*

# Tidy snake_case names that flow through SQL + Tableau.
RENAME = {
    "Invoice": "invoice",
    "StockCode": "stock_code",
    "Description": "description",
    "Quantity": "quantity",
    "InvoiceDate": "invoice_date",
    "Price": "price",
    "Customer ID": "customer_id",
    "Country": "country",
}


def _is_service(code: str) -> bool:
    c = str(code).strip().upper()
    return c in SERVICE_CODES or c.startswith(SERVICE_PREFIXES)


def load_raw() -> pd.DataFrame:
    if not os.path.exists(XLSX_PATH):
        raise SystemExit(
            f"raw data not found at {XLSX_PATH}\n"
            f"run  python data/fetch_data.py  first."
        )
    print(f"reading {XLSX_PATH} (two sheets)...")
    xls = pd.ExcelFile(XLSX_PATH)
    frames = []
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        df["source_sheet"] = sheet
        frames.append(df)
        print(f"  '{sheet}': {len(df):,} rows")
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    raw = load_raw()
    n_in = len(raw)
    log = []  # (step, rows_removed, rows_remaining)

    def step(name: str, before: int, after: int) -> None:
        log.append((name, before - after, after))

    # ---- normalise dtypes / whitespace up front (no row drops) ----
    raw = raw.rename(columns=RENAME)
    raw["invoice"] = raw["invoice"].astype(str).str.strip()
    raw["stock_code"] = raw["stock_code"].astype(str).str.strip()
    raw["description"] = raw["description"].astype(str).str.strip()
    raw["country"] = raw["country"].astype(str).str.strip()
    raw["invoice_date"] = pd.to_datetime(raw["invoice_date"])
    raw["revenue"] = (raw["quantity"] * raw["price"]).round(2)

    # ---- 1. exact duplicate rows ----
    before = len(raw)
    raw = raw.drop_duplicates(
        subset=["invoice", "stock_code", "description", "quantity",
                "invoice_date", "price", "customer_id", "country"]
    ).reset_index(drop=True)
    step("1. drop exact duplicate rows", before, len(raw))

    # ---- 2. split cancellations / returns (Invoice starts with 'C') ----
    is_cancel = raw["invoice"].str.upper().str.startswith("C")
    returns = raw[is_cancel].copy()
    before = len(raw)
    raw = raw[~is_cancel].reset_index(drop=True)
    step("2. move cancellations -> returns file", before, len(raw))

    # ---- 3. drop non-product service codes (from BOTH sales & returns) ----
    before = len(raw)
    raw = raw[~raw["stock_code"].map(_is_service)].reset_index(drop=True)
    step("3. drop non-product service StockCodes", before, len(raw))
    returns = returns[~returns["stock_code"].map(_is_service)].reset_index(drop=True)

    # ---- 4. drop non-positive quantity in the SALES grain ----
    before = len(raw)
    raw = raw[raw["quantity"] > 0].reset_index(drop=True)
    step("4. drop quantity <= 0 (sales grain)", before, len(raw))

    # ---- 5. drop non-positive price ----
    before = len(raw)
    raw = raw[raw["price"] > 0].reset_index(drop=True)
    step("5. drop price <= 0", before, len(raw))

    # ---- 6. finalise sales frame ----
    raw["revenue"] = (raw["quantity"] * raw["price"]).round(2)
    raw["customer_id"] = raw["customer_id"].astype("Int64")  # nullable int
    raw["has_customer_id"] = raw["customer_id"].notna()

    # Returns frame: clean up types + signed revenue for return analysis.
    returns["revenue"] = (returns["quantity"] * returns["price"]).round(2)
    returns["customer_id"] = returns["customer_id"].astype("Int64")
    returns = returns[returns["price"] > 0].reset_index(drop=True)

    cols = ["invoice", "stock_code", "description", "quantity", "invoice_date",
            "price", "revenue", "customer_id", "has_customer_id", "country",
            "source_sheet"]
    sales = raw[cols].copy()
    ret_cols = ["invoice", "stock_code", "description", "quantity",
                "invoice_date", "price", "revenue", "customer_id", "country",
                "source_sheet"]
    returns = returns[ret_cols].copy()

    sales.to_csv(CLEAN_CSV, index=False)
    returns.to_csv(RETURNS_CSV, index=False)

    # ---- 7. load SQLite ----
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(open(SCHEMA_SQL).read())
    # write into the schema-defined tables
    sales_db = sales.copy()
    sales_db["invoice_date"] = sales_db["invoice_date"].astype(str)
    sales_db["has_customer_id"] = sales_db["has_customer_id"].astype(int)
    sales_db.to_sql("sales", conn, if_exists="append", index=False)
    ret_db = returns.copy()
    ret_db["invoice_date"] = ret_db["invoice_date"].astype(str)
    ret_db.to_sql("returns", conn, if_exists="append", index=False)
    conn.commit()

    # ---- cleaning report ----
    print("\n" + "=" * 64)
    print("CLEANING SUMMARY  (real UCI Online Retail II)")
    print("=" * 64)
    print(f"{'rows in (both sheets, raw)':<42}{n_in:>14,}")
    print("-" * 56)
    for name, removed, remaining in log:
        print(f"{name:<42}{-removed:>+10,}  ->{remaining:>11,}")
    print("-" * 56)
    print(f"{'CLEAN SALES rows out':<42}{len(sales):>14,}")
    print(f"{'RETURNS rows (separate file)':<42}{len(returns):>14,}")

    n_missing = int((~sales["has_customer_id"]).sum())
    print("\nwithin clean sales:")
    print(f"  rows with NULL customer_id (flagged, kept) : "
          f"{n_missing:,}  ({n_missing / len(sales) * 100:.1f}%)")
    print(f"  rows usable for customer-level analysis    : "
          f"{len(sales) - n_missing:,}")

    # headline cross-checks
    rev = sales["revenue"].sum()
    print("\nheadline (sales grain, GBP):")
    print(f"  total revenue        : £{rev:,.2f}")
    print(f"  unique invoices      : {sales['invoice'].nunique():,}")
    print(f"  unique customers     : {sales['customer_id'].dropna().nunique():,}")
    print(f"  unique products      : {sales['stock_code'].nunique():,}")
    print(f"  countries            : {sales['country'].nunique():,}")
    print(f"  date range           : {sales['invoice_date'].min().date()} "
          f"-> {sales['invoice_date'].max().date()}")
    ret_rev = returns["revenue"].sum()  # signed (negative)
    print(f"  returns gross value  : £{ret_rev:,.2f}  "
          f"(return rate {abs(ret_rev) / rev * 100:.1f}% of sales £)")

    conn.close()
    print(f"\nOK -> {os.path.basename(CLEAN_CSV)}, "
          f"{os.path.basename(RETURNS_CSV)}, {os.path.basename(DB_PATH)}")


if __name__ == "__main__":
    sys.exit(main())
