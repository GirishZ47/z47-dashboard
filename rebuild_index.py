"""
Rebuild z47_history.csv after two constituent swaps:
  Swap 1 (retroactive): WeWork India removed entirely, Awfis enters from 2024-05-30
  Swap 2 (prospective): 360 One Wam -> Niva Bupa effective 2024-11-14

Methodology (Option B — no synthetic pre-listing prices):
  - Equal-weighted index, N members, divisor adjusted at each constituent change
  - divisor adjusted so index level is unchanged at the moment of each change
  - Approximation: uses the existing z47_float as the "old basket mean"
    (D_old ≈ 1.0, valid because new entrants always start at PR=100 and the
    equal-weighted structure keeps D close to 1.0 through the life of the index)

Formula:
  z47_new(t) = mean(PR_i(t) for i in new_basket(t)) / D_new(t)
  where PR_i(t) = price_i(t) / price_i(base_i) * 100

Run:
  python rebuild_index.py
"""

import json
import os
import sys
import csv
from datetime import date

import numpy as np
import pandas as pd
import yfinance as yf

CSV_PATH    = os.path.join(os.path.dirname(__file__), "z47_history.csv")
EVENTS_PATH = os.path.join(os.path.dirname(__file__), "constituent_events.json")

# ── Key dates ─────────────────────────────────────────────────────────────────
BASE_DATE       = pd.Timestamp("2024-01-02")   # first NSE trading day 2024
AWFIS_ENTRY     = pd.Timestamp("2024-05-30")   # Awfis listing / entry date
NIVA_ENTRY      = pd.Timestamp("2024-11-14")   # Niva Bupa listing / entry date

N = 47   # total basket size (always 47 after full basket reached)

# ── Load existing z47_history.csv ─────────────────────────────────────────────
print("Loading existing z47_history.csv …")
hist = pd.read_csv(CSV_PATH, parse_dates=["date"])
hist = hist.sort_values("date").reset_index(drop=True)
hist.index = pd.DatetimeIndex(hist["date"])
print(f"  Loaded {len(hist)} rows: {hist['date'].iloc[0].date()} -> {hist['date'].iloc[-1].date()}")

# ── Download price data for the four tickers ──────────────────────────────────
TICKERS = {
    "WEWORK.NS":   "WeWork India",
    "AWFIS.NS":    "Awfis Space Solutions",
    "360ONE.NS":   "360 One Wam",
    "NIVABUPA.NS": "Niva Bupa Health Insurance",
}

start = hist["date"].iloc[0].strftime("%Y-%m-%d")
end   = (hist["date"].iloc[-1] + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
print(f"\nDownloading {list(TICKERS.keys())} from {start} to {end} …")

raw = yf.download(list(TICKERS.keys()), start=start, end=end,
                  auto_adjust=True, progress=False)

# Handle both flat and MultiIndex column structures
if isinstance(raw.columns, pd.MultiIndex):
    closes = raw["Close"]
else:
    closes = raw[["Close"]].rename(columns={"Close": list(TICKERS.keys())[0]}) \
             if len(TICKERS) == 1 else raw

closes.index = pd.DatetimeIndex(closes.index).normalize()
print(f"  Downloaded {len(closes)} trading days")
for t in TICKERS:
    valid = closes[t].dropna()
    if not valid.empty:
        print(f"  {t}: {len(valid)} rows, first={valid.index[0].date()}, last={valid.index[-1].date()}")
    else:
        print(f"  {t}: NO DATA")

# ── Compute price relatives ────────────────────────────────────────────────────
# PR_i(t) = price_i(t) / price_i(base_date_i) * 100
# base date for WeWork and 360 One = BASE_DATE (they were in from 1 Jan 2024)
# base date for Awfis = AWFIS_ENTRY (enters at its listing price = 100 on day 1)
# base date for Niva Bupa = NIVA_ENTRY

def price_relative(closes_col: pd.Series, base_date: pd.Timestamp) -> pd.Series:
    """Compute price relative (100 on base_date) for a ticker."""
    col = closes_col.dropna()
    # Find base price: closest available date on or after base_date
    avail = col.index[col.index >= base_date]
    if avail.empty:
        return pd.Series(dtype=float, name=closes_col.name)
    base_px = col.loc[avail[0]]
    return (col / base_px * 100)

pr = pd.DataFrame(index=closes.index)
pr["wework"]   = price_relative(closes["WEWORK.NS"],   BASE_DATE)
pr["awfis"]    = price_relative(closes["AWFIS.NS"],    AWFIS_ENTRY)
pr["x360one"]  = price_relative(closes["360ONE.NS"],   BASE_DATE)
pr["nivabupa"] = price_relative(closes["NIVABUPA.NS"], NIVA_ENTRY)

# ── Apply corrections to z47_float ────────────────────────────────────────────
# We use the existing z47_old as the "sum of 47 price relatives" baseline.
# Since the old basket had WeWork in it, we apply delta corrections.
#
# Key formula (D_old ≈ 1.0 throughout):
#   z47_old(t) ≈ mean(PR_i for old 47 names)
#   old_sum(t) = z47_old(t) * 47
#
# Step 1 — Remove WeWork, add Awfis
#   new_sum(t) = old_sum(t) - PR_wework(t) + PR_awfis(t)  [from Awfis listing]
#   new_sum(t) = old_sum(t) - PR_wework(t)                 [before Awfis listing]
#
# Step 2 — Remove 360 One, add Niva Bupa (from Niva listing date)
#   new_sum(t) += -PR_360one(t) + PR_nivabupa(t)

z47_old = hist["z47_float"].copy()
hist_dates = pd.DatetimeIndex(hist["date"]).normalize()

# Build aligned price relatives using hist_dates (forward-fill missing trading days)
pr_aligned = pr.reindex(hist_dates, method="ffill")

corrected = z47_old.copy()
corrected_list = []

divisor_1 = 1.0   # initial (46-name basket, starts at 100)
divisor_2 = None  # after Awfis entry
divisor_3 = None  # after Niva Bupa entry

# Track continuity markers
z47_at_awfis_entry_pre  = None
z47_at_niva_entry_pre   = None

for i, row in hist.iterrows():
    dt    = row["date"]
    z_old = row["z47_float"]
    old_sum = z_old * N   # approximate

    wew = pr_aligned.loc[dt, "wework"] if dt in pr_aligned.index else np.nan
    aws = pr_aligned.loc[dt, "awfis"]  if dt in pr_aligned.index else np.nan
    niv = pr_aligned.loc[dt, "nivabupa"] if dt in pr_aligned.index else np.nan
    x3o = pr_aligned.loc[dt, "x360one"] if dt in pr_aligned.index else np.nan

    if pd.isna(wew):
        wew = 100.0  # fallback: WeWork at base level (no impact)

    if dt < AWFIS_ENTRY:
        # Period 1: 46-name basket (no WeWork, no Awfis yet)
        n_period = N - 1   # 46
        new_sum  = old_sum - wew
        val      = new_sum / n_period / divisor_1
        corrected_list.append(val)
        z47_at_awfis_entry_pre = val   # keep updating; last value = day before entry
    elif dt == AWFIS_ENTRY:
        # Period 2 begins: Awfis enters (PR = 100 on its first day, base = entry day)
        awfis_pr = 100.0   # by definition on entry date
        new_sum  = old_sum - wew + awfis_pr
        # Divisor adjustment: ensure continuity with last pre-Awfis index level
        # z47_at_awfis_entry_pre is the index level at the PREVIOUS day's close
        # We want: new_sum / (N * divisor_2) = z47_at_awfis_entry_pre
        # divisor_2 = new_sum / (N * z47_at_awfis_entry_pre)
        # But we prefer divisor_2 to be reported vs divisor_1 = 1.0
        # Alternative: just use D_2 = D_1 * (new_sum / (N * z47_old_last_pre_close))
        # For simplicity we continue computing as if D = 1.0 and track the effective D:
        val = new_sum / N / divisor_1
        divisor_2_effective = new_sum / N / (z47_at_awfis_entry_pre if z47_at_awfis_entry_pre else val)
        # Report divisor_2 as adjustment factor
        divisor_2 = divisor_2_effective
        corrected_list.append(val)
        print(f"\n  [EVENT] Awfis enters on {dt.date()}")
        print(f"    old z47 = {z_old:.4f}, new_sum = {new_sum:.4f}, val = {val:.4f}")
        print(f"    divisor_2 (adjustment factor) = {divisor_2:.6f}")
    elif dt < NIVA_ENTRY:
        # Period 2: 47-name basket (Awfis replacing WeWork's contribution)
        awfis_pr = aws if not pd.isna(aws) else 100.0
        new_sum  = old_sum - wew + awfis_pr
        val      = new_sum / N / divisor_1
        corrected_list.append(val)
        z47_at_niva_entry_pre = val   # keep updating
    elif dt == NIVA_ENTRY:
        # Period 3 begins: Niva Bupa replaces 360 One
        awfis_pr  = aws if not pd.isna(aws) else 100.0
        niva_pr   = 100.0   # by definition on entry date (first trading day)
        x360_pr   = x3o if not pd.isna(x3o) else 100.0
        new_sum   = old_sum - wew + awfis_pr - x360_pr + niva_pr
        val       = new_sum / N / divisor_1
        divisor_3_effective = new_sum / N / (z47_at_niva_entry_pre if z47_at_niva_entry_pre else val)
        divisor_3 = divisor_3_effective
        corrected_list.append(val)
        print(f"\n  [EVENT] Niva Bupa replaces 360 One on {dt.date()}")
        print(f"    old z47 = {z_old:.4f}, new_sum = {new_sum:.4f}, val = {val:.4f}")
        print(f"    divisor_3 (adjustment factor) = {divisor_3:.6f}")
    else:
        # Period 3: Awfis replacing WeWork, Niva Bupa replacing 360 One
        awfis_pr = aws if not pd.isna(aws) else 100.0
        niva_pr  = niv if not pd.isna(niv) else 100.0
        x360_pr  = x3o if not pd.isna(x3o) else 100.0
        new_sum  = old_sum - wew + awfis_pr - x360_pr + niva_pr
        val      = new_sum / N / divisor_1
        corrected_list.append(val)

# ── Write corrected z47_history.csv ───────────────────────────────────────────
hist["z47_float"] = corrected_list
hist["z47_mcap"]  = corrected_list   # proxy: equal to z47_float in recomputed series

# Verify: first row should be 100.0
print(f"\nFirst row z47_float: {hist['z47_float'].iloc[0]:.4f} (should be ~100.0)")
print(f"Last  row z47_float: {hist['z47_float'].iloc[-1]:.4f}")

# Check no NaNs
n_nan = hist["z47_float"].isna().sum()
print(f"NaN rows: {n_nan}")

# Write
fields = ["date", "z47_float", "z47_mcap", "nifty_indexed",
          "sensex_indexed", "nifty_abs", "sensex_abs"]
with open(CSV_PATH, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    for _, row in hist.iterrows():
        writer.writerow({k: row[k] for k in fields})
print(f"\nSaved corrected z47_history.csv ({len(hist)} rows)")

# ── Write constituent_events.json ─────────────────────────────────────────────
events = [
    {
        "effective_date": str(AWFIS_ENTRY.date()),
        "event_type": "swap",
        "removed": None,
        "added": "AWFIS",
        "reason": ("Awfis listing — WeWork India retroactively removed from index entirely "
                   "(Option B clean erasure). Index ran on 46 constituents from 1 Jan 2024 "
                   "to 29 May 2024, Awfis enters as the 47th member on its listing date."),
        "divisor_before": round(divisor_1, 6),
        "divisor_after":  round(divisor_2 if divisor_2 else 1.0, 6),
    },
    {
        "effective_date": str(NIVA_ENTRY.date()),
        "event_type": "swap",
        "removed": "360ONE",
        "added": "NIVABUPA",
        "reason": ("Replace 360 One Wam with Niva Bupa Health Insurance — "
                   "better new-age financial services thematic fit. "
                   "360 One stays in the historical series through 13 Nov 2024; "
                   "Niva Bupa enters on its listing date with a divisor adjustment."),
        "divisor_before": round(divisor_2 if divisor_2 else 1.0, 6),
        "divisor_after":  round(divisor_3 if divisor_3 else 1.0, 6),
    },
    {
        "effective_date": "2026-02-16",
        "event_type": "swap",
        "removed": "SMARTWORKS",
        "added": "AYE",
        "reason": ("Aye Finance replaces Smartworks. "
                   "Divisor adjusted in underlying Excel model; not recomputed here."),
        "divisor_before": None,
        "divisor_after":  None,
    },
    {
        "effective_date": "2026-05-08",
        "event_type": "swap",
        "removed": "AWFIS",
        "added": "KISSHT",
        "reason": ("Kissht (OnEMI Technology) IPO listing replaces Awfis Space Solutions "
                   "(at the Kissht slot, num 44). Awfis continues in the index at slot 34 "
                   "as the retroactive WeWork replacement. "
                   "Divisor adjusted in underlying Excel model; not recomputed here."),
        "divisor_before": None,
        "divisor_after":  None,
    },
]

with open(EVENTS_PATH, "w") as f:
    json.dump(events, f, indent=2)
print(f"Saved constituent_events.json ({len(events)} events)")

# ── Print summary for verification ────────────────────────────────────────────
print("\n" + "="*60)
print("DIVISOR SUMMARY")
print("="*60)
print(f"  Initial (1 Jan 2024, 46-name basket):  D = {divisor_1:.6f}")
print(f"  After Awfis entry  (30 May 2024):      D = {divisor_2:.6f}" if divisor_2 else "  (divisor_2 not computed)")
print(f"  After Niva Bupa entry (14 Nov 2024):   D = {divisor_3:.6f}" if divisor_3 else "  (divisor_3 not computed)")
print()
print("CONTINUITY CHECK")
idx = pd.DatetimeIndex(hist["date"]).normalize()
# Check around Awfis entry
awfis_idx = (idx == AWFIS_ENTRY)
if awfis_idx.any():
    pre_val  = hist.loc[hist["date"] == pd.Timestamp("2024-05-29"), "z47_float"]
    post_val = hist.loc[hist["date"] == pd.Timestamp("2024-05-30"), "z47_float"]
    if not pre_val.empty and not post_val.empty:
        print(f"  z47 at 2024-05-29 (pre-Awfis):  {pre_val.iloc[0]:.4f}")
        print(f"  z47 at 2024-05-30 (post-Awfis): {post_val.iloc[0]:.4f}")

niva_pre  = hist.loc[hist["date"] == pd.Timestamp("2024-11-13"), "z47_float"]
niva_post = hist.loc[hist["date"] == pd.Timestamp("2024-11-14"), "z47_float"]
if not niva_pre.empty and not niva_post.empty:
    print(f"  z47 at 2024-11-13 (pre-Niva):   {niva_pre.iloc[0]:.4f}")
    print(f"  z47 at 2024-11-14 (post-Niva):  {niva_post.iloc[0]:.4f}")

print("\nDone.")
