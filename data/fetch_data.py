"""
Fetch the REAL, public Online Retail II dataset from the UCI ML Repository.

Source : Chen, D. (2019). Online Retail II. UCI Machine Learning Repository.
         https://doi.org/10.24432/C5CG6D
Page   : https://archive.ics.uci.edu/dataset/502/online+retail+ii
File   : a single .xlsx with TWO sheets, "Year 2009-2010" and "Year 2010-2011",
         ~1,067,371 transaction rows for a UK-based online gift retailer.

This script is the first step of a fully reproducible pipeline:

    python data/fetch_data.py     # -> data/online_retail_II.xlsx  (raw, git-ignored)
    python data/clean_data.py     # -> data/online_retail_clean.csv + data/online_retail.db
    python notebook/analysis.py   # -> notebook/figures/*.png

The raw .xlsx (~45 MB) is intentionally git-ignored; this script reproduces it
byte-for-byte from the canonical UCI URL. If UCI is unreachable, see FALLBACK_URL.
"""

import hashlib
import os
import sys
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))

# Canonical UCI archive (a ZIP wrapping the .xlsx)
UCI_ZIP_URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"
# If UCI is down, a widely-mirrored copy of the SAME file lives on the dataset's
# original Kaggle/GitHub mirrors; swap this in and re-run if needed.
FALLBACK_URL = (
    "https://github.com/npcurt/online-retail-II/raw/main/online_retail_II.zip"
)

ZIP_PATH = os.path.join(HERE, "online_retail_II.zip")
XLSX_PATH = os.path.join(HERE, "online_retail_II.xlsx")


def _download(url: str, dest: str) -> None:
    print(f"  GET {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
        f.write(r.read())
    print(f"  saved {dest}  ({os.path.getsize(dest):,} bytes)")


def main() -> None:
    print("=" * 64)
    print("Fetching UCI Online Retail II (real, public data)")
    print("=" * 64)

    if os.path.exists(XLSX_PATH):
        print(f"already present: {XLSX_PATH}  ({os.path.getsize(XLSX_PATH):,} bytes)")
        print("delete it to force a re-download.")
        return

    try:
        _download(UCI_ZIP_URL, ZIP_PATH)
    except Exception as exc:  # noqa: BLE001
        print(f"  ! UCI download failed ({exc}); trying fallback mirror...")
        _download(FALLBACK_URL, ZIP_PATH)

    print("Unzipping...")
    with zipfile.ZipFile(ZIP_PATH) as z:
        names = z.namelist()
        xlsx = next(n for n in names if n.lower().endswith(".xlsx"))
        with z.open(xlsx) as src, open(XLSX_PATH, "wb") as out:
            out.write(src.read())
    print(f"  -> {XLSX_PATH}  ({os.path.getsize(XLSX_PATH):,} bytes)")

    sha = hashlib.sha256(open(XLSX_PATH, "rb").read()).hexdigest()
    print(f"\nsha256(online_retail_II.xlsx) = {sha}")
    print("\nOK -> data/online_retail_II.xlsx   (next: python data/clean_data.py)")


if __name__ == "__main__":
    sys.exit(main())
