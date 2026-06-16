"""
rebuild_index.py - Z47fortyseven Index v2
Methodology: free-float market-cap weighted, 10% iterative per-name cap
Rebalance: quarterly (first trading day of Jan/Apr/Jul/Oct) + each constituent event
Benchmark: Nifty 500 (^CRSLDX) rebased to 100 on 2024-01-02
Output: z47_history.csv
  columns: date, z47_float, z47_mcap, n500_indexed, n500_abs

Run:
  python rebuild_index.py
"""

import io
import json
import os
import sys
import csv
from concurrent.futures import ThreadPoolExecutor

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import numpy as np
import pandas as pd
import yfinance as yf

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CSV_PATH    = os.path.join(BASE_DIR, "z47_history.csv")
EVENTS_PATH = os.path.join(BASE_DIR, "constituent_events.json")
EXCEL_PATH  = (
    r"C:\Users\Girish Shenoy\Z47\The Vault - Documents\Corp Dev"
    r"\8. Public market projects and research\IPO CoE\Z47 Index.xlsx"
)

BASE_DATE   = pd.Timestamp("2024-01-02")
EXCEL_END   = pd.Timestamp("2026-05-07")
N500_TICKER = "^CRSLDX"
CAP         = 0.10      # 10% per-name cap (iterative)
WEWORK_TICKERS = {"WEWORK", "WEWORK.NS"}  # Option B: excluded entirely

# ── Import COMPANIES from companies.py ────────────────────────────────────────
sys.path.insert(0, BASE_DIR)
from companies import COMPANIES

Z47_BY_TICKER = {c["ticker"]: c for c in COMPANIES}


def yf_sym(ticker: str, exchange: str) -> str:
    return ticker + ".NS" if exchange == "NSE" else ticker


# ── Proxy companies (NOT in Excel) ────────────────────────────────────────────
# ff_mcap at entry = mkt_cap_mn × float_pct / 100  (INR Mn)
# After entry: ff_mcap(t) = ff_mcap_entry × price(t) / price(entry_date)
PROXY_CONSTS = {}
for _tk in ("AYE", "KISSHT", "ANGELONE", "AFFLE", "AMAGI", "FRACTAL"):
    _c = Z47_BY_TICKER[_tk]
    PROXY_CONSTS[_tk] = {
        "yf_sym":       yf_sym(_c["ticker"], _c["exchange"]),
        "ff_mcap_entry": _c["mkt_cap_mn"] * _c["float_pct"] / 100.0,
    }

# Entry dates for proxy and event-driven constituents (from constituent_events.json)
ENTRY_DATE = {
    "AWFIS":    pd.Timestamp("2024-05-30"),
    "AYE":      pd.Timestamp("2026-02-16"),
    "KISSHT":   pd.Timestamp("2026-05-08"),
    "ANGELONE": pd.Timestamp("2024-01-02"),   # BASE_DATE, listed Oct 2020
    "AFFLE":    pd.Timestamp("2024-01-02"),   # BASE_DATE, listed Aug 2019
    "AMAGI":    pd.Timestamp("2026-01-21"),   # listing date
    "FRACTAL":  pd.Timestamp("2026-02-16"),   # listing date
}
EXIT_DATE = {
    "AWFIS":      pd.Timestamp("2026-05-07"),   # trust constituent_events.json
    "360ONE":     pd.Timestamp("2024-11-13"),
    "SMARTWORKS": pd.Timestamp("2026-02-15"),
}

# ── Historical exited companies (may or may not be in Excel) ─────────────────
# Used as proxy fallback if not found in Excel
HISTORICAL_FALLBACK = {
    "360ONE": {
        "yf_sym": "360ONE.NS",
        "float_pct": 65.0,
        "mkt_cap_mn": 400000.0,     # ~₹40,000 Cr estimate at Jan 2024
        "entry": pd.Timestamp("2024-01-02"),
    },
    "SMARTWORKS": {
        "yf_sym": "SMARTWORKS.NS",
        "float_pct": 35.0,
        "mkt_cap_mn": 16000.0,      # ~₹1,600 Cr estimate
        "entry": pd.Timestamp("2024-01-02"),
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# 1. LOAD EXCEL ff_mcap DATA
# ─────────────────────────────────────────────────────────────────────────────

def load_excel_ff_mcap() -> dict[str, pd.Series]:
    """
    Returns {z47_ticker: pd.Series(ff_mcap_INR_Mn, DatetimeIndex)}
    for all companies found in the Excel.
    Float % sheet: CapIQ_Float (fallback: Free Float Index Calculation)
    MCap sheet:    CapIQ_MCap  (fallback: MCap)
    Structure: row 1 (0-idx) = dates, rows 2-48 (0-idx) = companies
               col 0 = company name, col 1 = CapIQ ticker (e.g. NSEI:ETERNAL)
               cols 2+ = daily values
    """
    print("\n── Loading Excel ff_mcap ─────────────────────────────────────────")

    float_df = mcap_df = None
    for sname in ["CapIQ_Float", "Free Float Index Calculation", "Float"]:
        try:
            float_df = pd.read_excel(EXCEL_PATH, sheet_name=sname, header=None)
            print(f"  Float sheet '{sname}': {float_df.shape}")
            break
        except Exception:
            pass
    for sname in ["CapIQ_MCap", "MCap", "Market Cap"]:
        try:
            mcap_df = pd.read_excel(EXCEL_PATH, sheet_name=sname, header=None)
            print(f"  MCap sheet  '{sname}': {mcap_df.shape}")
            break
        except Exception:
            pass

    if float_df is None or mcap_df is None:
        raise RuntimeError("Could not open Excel sheets. Check EXCEL_PATH.")

    # Structure (verified from debug):
    #   Row 0-1: all NaN
    #   Row 2: col 0-1=NaN, col 2='INR Mn', col 3+ = dates
    #   Rows 3-49: col 0=NaN, col 1=company name, col 2=CapIQ ticker, col 3+=values
    dates_raw = float_df.iloc[2, 3:]
    dates = pd.to_datetime(dates_raw, errors="coerce")
    valid = dates.notna().values
    dates = dates[valid]
    print(f"  Date range: {dates.iloc[0].date()} → {dates.iloc[-1].date()}  ({len(dates)} cols)")

    # Build z47 ticker lookup: CapIQ ticker string (uppercase) → z47_ticker
    # Handles "NSEI:ETERNAL", "NasdaqGS:MMYT", etc.
    ticker_lookup: dict[str, str] = {}
    all_z47 = set(Z47_BY_TICKER.keys()) | set(HISTORICAL_FALLBACK.keys())
    for z47t in all_z47:
        ticker_lookup[z47t.upper()] = z47t
        for prefix in ("NSEI:", "NSE:", "BSE:", "NASDAQGS:", "NASDAQNM:", "NYSE:",
                       "NASDAQGS:", "NASDAQ:"):
            ticker_lookup[(prefix + z47t).upper()] = z47t

    result: dict[str, pd.Series] = {}

    # Company data in rows 3-49 (0-indexed), same for both sheets
    for row_idx in range(3, 50):
        raw_ticker = str(float_df.iloc[row_idx, 2]).strip()  # col 2 = CapIQ ticker
        if not raw_ticker or raw_ticker.lower() in ("nan", "none", ""):
            continue

        # Skip WeWork early (Option B)
        if "WEWORK" in raw_ticker.upper():
            print(f"  Skipping WeWork (Option B): '{raw_ticker}'")
            continue

        # Resolve to z47 ticker
        z47t = ticker_lookup.get(raw_ticker.upper())
        if z47t is None:
            # Try matching the suffix after ":"
            if ":" in raw_ticker:
                suffix = raw_ticker.split(":", 1)[1].upper()
                z47t = ticker_lookup.get(suffix)
        if z47t is None:
            print(f"  WARN unmapped Excel ticker: '{raw_ticker}'")
            continue

        fvals = pd.to_numeric(float_df.iloc[row_idx, 3:].values[valid], errors="coerce")
        mvals = pd.to_numeric(mcap_df.iloc[row_idx, 3:].values[valid],  errors="coerce")

        ff = mvals * fvals / 100.0   # INR Mn

        series = pd.Series(ff, index=dates.values, name=z47t)
        series = series[~series.index.duplicated(keep="first")].sort_index()
        result[z47t] = series

    print(f"  Loaded {len(result)} tickers from Excel.")
    if "360ONE" in result:
        print("  360ONE found in Excel ✓")
    else:
        print("  360ONE NOT in Excel → will use proxy")
    if "SMARTWORKS" in result:
        print("  SMARTWORKS found in Excel ✓")
    else:
        print("  SMARTWORKS NOT in Excel → will use proxy")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 2. DOWNLOAD PRICES
# ─────────────────────────────────────────────────────────────────────────────

def download_prices(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    """
    Download adjusted close prices for a list of yfinance tickers.
    Returns DataFrame with ticker columns. Missing data forward-filled.
    Handles MultiIndex columns from yfinance.
    """
    if not tickers:
        return pd.DataFrame()
    raw = yf.download(tickers, start=start, end=end,
                      auto_adjust=True, progress=False, threads=True)
    if isinstance(raw.columns, pd.MultiIndex):
        closes = raw["Close"]
    else:
        closes = raw[["Close"]].rename(columns={"Close": tickers[0]}) if len(tickers) == 1 else raw
    closes.index = pd.DatetimeIndex(closes.index).normalize()
    if isinstance(closes, pd.Series):
        closes = closes.to_frame(name=tickers[0])
    return closes


# ─────────────────────────────────────────────────────────────────────────────
# 3. ITERATIVE 10% CAP
# ─────────────────────────────────────────────────────────────────────────────

def apply_iterative_cap(ff_mcap_dict: dict[str, float], cap: float = CAP) -> dict[str, float]:
    """
    Input:  {ticker: ff_mcap}   (zero/negative values excluded)
    Output: {ticker: weight}    (sum = 1, max = cap)
    Uses iterative redistribution.
    """
    active = {k: v for k, v in ff_mcap_dict.items() if v > 0}
    if not active:
        return {}
    total = sum(active.values())
    w = {k: v / total for k, v in active.items()}
    for _ in range(100):
        over   = {k: wt for k, wt in w.items() if wt > cap + 1e-9}
        if not over:
            break
        excess = sum(wt - cap for wt in over.values())
        for k in over:
            w[k] = cap
        under  = {k: wt for k, wt in w.items() if k not in over}
        ut     = sum(under.values())
        if ut <= 0:
            break
        for k in under:
            w[k] += excess * under[k] / ut
    s = sum(w.values())
    return {k: v / s for k, v in w.items()}


# ─────────────────────────────────────────────────────────────────────────────
# 4. REBALANCE DATE SCHEDULE
# ─────────────────────────────────────────────────────────────────────────────

def get_rebalance_dates(trading_days: pd.DatetimeIndex,
                        event_dates: list,
                        start: pd.Timestamp,
                        end: pd.Timestamp) -> list[pd.Timestamp]:
    """
    Returns sorted list of rebalance dates:
    - BASE_DATE
    - First trading day of each quarter (Jan, Apr, Jul, Oct)
    - First trading day on/after each constituent event date
    """
    dates = {BASE_DATE}

    # Quarterly
    for yr in range(start.year, end.year + 1):
        for mo in [1, 4, 7, 10]:
            q = pd.Timestamp(year=yr, month=mo, day=1)
            avail = trading_days[trading_days >= q]
            if not avail.empty and start <= avail[0] <= end:
                dates.add(avail[0])

    # Event-driven
    for ev in event_dates:
        ev_ts = pd.Timestamp(ev)
        avail = trading_days[trading_days >= ev_ts]
        if not avail.empty and start <= avail[0] <= end:
            dates.add(avail[0])

    return sorted(dates)


# ─────────────────────────────────────────────────────────────────────────────
# 5. CONSTITUENT ACTIVE SET
# ─────────────────────────────────────────────────────────────────────────────

def build_active_set(dt: pd.Timestamp,
                     effective_entry: dict[str, pd.Timestamp],
                     effective_exit:  dict[str, pd.Timestamp]) -> set[str]:
    """
    Returns set of z47 tickers active on date dt.
    effective_entry and effective_exit are computed in main() from Excel data + events.
    """
    active = set()
    all_tickers = set(Z47_BY_TICKER.keys()) | set(HISTORICAL_FALLBACK.keys())
    all_tickers.discard("WEWORK")

    for tk in all_tickers:
        entry = effective_entry.get(tk, BASE_DATE)
        exit_ = effective_exit.get(tk, None)
        if entry <= dt and (exit_ is None or dt <= exit_):
            active.add(tk)

    return active


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    # ── Step 1: Load Excel ff_mcap ────────────────────────────────────────────
    excel_ff = load_excel_ff_mcap()

    # ── Auto-detect entry dates from Excel (first date MCap > 0) ─────────────
    # This correctly handles companies listed after Jan 2, 2024 (SWIGGY, OLA, etc.)
    print("\n── Auto-detecting entry dates from Excel ─────────────────────────────")
    effective_entry: dict[str, pd.Timestamp] = {}
    for tk, series in excel_ff.items():
        positive = series[series > 0]
        if not positive.empty:
            first_pos = positive.index[0]
            # Entry into the INDEX is max(first price date, BASE_DATE)
            # For companies listed before base, entry = BASE_DATE
            effective_entry[tk] = max(first_pos, BASE_DATE)
        else:
            effective_entry[tk] = BASE_DATE   # no price data → won't contribute weight

    # Proxy companies: explicit entry from ENTRY_DATE
    for tk, dt in ENTRY_DATE.items():
        effective_entry[tk] = dt

    # Historical companies not in Excel
    for tk, info in HISTORICAL_FALLBACK.items():
        if tk not in effective_entry:
            effective_entry[tk] = info["entry"]

    # Log entries after BASE_DATE
    late_entries = {tk: dt for tk, dt in effective_entry.items() if dt > BASE_DATE}
    for tk, dt in sorted(late_entries.items(), key=lambda x: x[1]):
        print(f"  {tk}: enters index {dt.date()}")

    # ── Exit dates (from constituent_events.json + known exits) ──────────────
    effective_exit: dict[str, pd.Timestamp] = dict(EXIT_DATE)   # copy

    # ── Step 2: Determine all tickers to download ─────────────────────────────
    print("\n── Determining tickers to download ──────────────────────────────────")

    # All tickers ever active
    all_active_tickers: set[str] = set()
    for c in COMPANIES:
        all_active_tickers.add(c["ticker"])
    for tk in HISTORICAL_FALLBACK:
        all_active_tickers.add(tk)
    all_active_tickers.discard("WEWORK")

    # Map to yfinance symbols
    yf_sym_map: dict[str, str] = {}
    for tk in all_active_tickers:
        if tk in Z47_BY_TICKER:
            c = Z47_BY_TICKER[tk]
            yf_sym_map[tk] = yf_sym(c["ticker"], c["exchange"])
        elif tk in HISTORICAL_FALLBACK:
            yf_sym_map[tk] = HISTORICAL_FALLBACK[tk]["yf_sym"]

    # Add Nifty 500
    all_yf = sorted(set(yf_sym_map.values())) + [N500_TICKER]

    dl_start = "2023-12-29"   # slightly before base to get Jan 2 prices
    dl_end   = (pd.Timestamp.today() + pd.Timedelta(days=2)).strftime("%Y-%m-%d")

    print(f"  Downloading {len(all_yf)} tickers from {dl_start} to {dl_end}…")
    prices_all = download_prices(all_yf, dl_start, dl_end)
    print(f"  Got {len(prices_all)} trading days.")

    # Build reverse map: yf_sym -> z47_ticker
    yf_to_z47 = {v: k for k, v in yf_sym_map.items()}

    # Extract prices per z47 ticker
    prices: dict[str, pd.Series] = {}
    for tk, yfk in yf_sym_map.items():
        if yfk in prices_all.columns:
            s = prices_all[yfk].dropna()
            if not s.empty:
                prices[tk] = s
            else:
                print(f"  WARN: no price data for {tk} ({yfk}) — will retry")
        else:
            print(f"  WARN: {yfk} not in download result — will retry")

    # ── Retry failed tickers individually with their entry date ──────────────
    # Bulk download fails for recently-listed tickers (yfinance "no data for startDate").
    # Re-fetch each missing ticker from its effective entry date - 7 days.
    missing = [tk for tk in yf_sym_map if tk not in prices]
    if missing:
        print(f"\n  Retrying {len(missing)} missing tickers individually…")
        for tk in missing:
            yfk = yf_sym_map[tk]
            entry_dt = effective_entry.get(tk, BASE_DATE)
            retry_start = (entry_dt - pd.Timedelta(days=10)).strftime("%Y-%m-%d")
            try:
                retry_data = yf.download(yfk, start=retry_start, end=dl_end,
                                         auto_adjust=True, progress=False)
                if isinstance(retry_data.columns, pd.MultiIndex):
                    retry_data = retry_data["Close"]
                    if isinstance(retry_data, pd.DataFrame):
                        retry_data = retry_data[yfk] if yfk in retry_data.columns else retry_data.iloc[:, 0]
                elif "Close" in retry_data.columns:
                    retry_data = retry_data["Close"]
                retry_data.index = pd.DatetimeIndex(retry_data.index).normalize()
                s = retry_data.dropna()
                if not s.empty:
                    prices[tk] = s
                    print(f"    {tk} ({yfk}): {len(s)} rows from {s.index[0].date()} ✓")
                else:
                    print(f"    {tk} ({yfk}): still no data")
            except Exception as e:
                print(f"    {tk} ({yfk}): retry error: {e}")

    n500_prices = prices_all[N500_TICKER].dropna() if N500_TICKER in prices_all.columns else pd.Series(dtype=float)
    print(f"  Nifty 500 (^CRSLDX): {len(n500_prices)} rows  "
          f"{n500_prices.index[0].date()} → {n500_prices.index[-1].date()}")

    # ── Step 3: Build ff_mcap series for every ticker ─────────────────────────
    print("\n── Building daily ff_mcap series ────────────────────────────────────")

    # All trading days from BASE_DATE to last price date
    all_trading_days = pd.DatetimeIndex(sorted(prices_all.index[prices_all.index >= BASE_DATE]))
    end_date = all_trading_days[-1]
    print(f"  Trading days: {BASE_DATE.date()} → {end_date.date()}  ({len(all_trading_days)} days)")

    # Build ff_mcap for each ticker on each trading day
    ff_mcap_daily: dict[str, pd.Series] = {}

    for tk in all_active_tickers:
        # ── Excel source ──
        if tk in excel_ff:
            raw_series = excel_ff[tk]
            # Forward-fill within Excel range; zero before listing (MCap=0 handled naturally)
            raw = raw_series.reindex(all_trading_days, method="ffill")
            # Extend beyond Excel end via price-scaling
            excel_last = raw.loc[:EXCEL_END].dropna()
            if not excel_last.empty:
                last_ff   = excel_last.iloc[-1]
                last_date = excel_last.index[-1]
                p_series  = prices.get(tk)
                if p_series is not None and last_date in p_series.index:
                    p_base = p_series.loc[last_date]
                    for d in all_trading_days[all_trading_days > EXCEL_END]:
                        if d in p_series.index and p_base > 0:
                            raw.loc[d] = last_ff * p_series.loc[d] / p_base
            # Clip negative values to 0
            raw = raw.clip(lower=0)
            ff_mcap_daily[tk] = raw

        # ── Proxy source (AYE, KISSHT, ANGELONE, AFFLE, AMAGI, FRACTAL) ──
        elif tk in PROXY_CONSTS:
            info    = PROXY_CONSTS[tk]
            entry   = ENTRY_DATE[tk]
            ff_ent  = info["ff_mcap_entry"]
            p_series = prices.get(tk)
            vals = pd.Series(0.0, index=all_trading_days, name=tk)
            if p_series is not None:
                p_entry_avail = p_series[p_series.index >= entry]
                if not p_entry_avail.empty:
                    p_entry = p_entry_avail.iloc[0]
                    for d in all_trading_days[all_trading_days >= entry]:
                        if d in p_series.index and p_entry > 0:
                            vals.loc[d] = ff_ent * p_series.loc[d] / p_entry
                        elif d in vals.index:
                            # forward-fill last known
                            prev = vals.loc[:d].replace(0, np.nan).dropna()
                            if not prev.empty:
                                vals.loc[d] = prev.iloc[-1]
            ff_mcap_daily[tk] = vals

        # ── Historical fallback (360ONE, SMARTWORKS if not in Excel) ──
        elif tk in HISTORICAL_FALLBACK:
            info     = HISTORICAL_FALLBACK[tk]
            entry    = info["entry"]
            exit_    = EXIT_DATE.get(tk)
            ff_entry = info["mkt_cap_mn"] * info["float_pct"] / 100.0
            p_series = prices.get(tk)
            vals = pd.Series(0.0, index=all_trading_days, name=tk)
            if p_series is not None:
                p_avail = p_series[p_series.index >= entry]
                if not p_avail.empty:
                    p0 = p_avail.iloc[0]
                    for d in all_trading_days[all_trading_days >= entry]:
                        if exit_ is not None and d > exit_:
                            break
                        if d in p_series.index and p0 > 0:
                            vals.loc[d] = ff_entry * p_series.loc[d] / p0
            ff_mcap_daily[tk] = vals

        else:
            print(f"  WARN: no ff_mcap source for {tk}, treating as 0")
            ff_mcap_daily[tk] = pd.Series(0.0, index=all_trading_days, name=tk)

    # ── Synthetic price fallback for tickers still missing from prices ────────
    # Use ff_mcap as a price proxy (normalized to 100 at first positive date).
    # Mathematically valid: between rebalances, contribution ∝ ff_mcap change.
    still_missing = [tk for tk in all_active_tickers if tk not in prices]
    if still_missing:
        print(f"\n  Building synthetic price proxies for {len(still_missing)} tickers…")
        for tk in still_missing:
            s = ff_mcap_daily.get(tk)
            if s is not None:
                pos = s[s > 0]
                if not pos.empty:
                    base_ff = float(pos.iloc[0])
                    if base_ff > 0:
                        synth = (s / base_ff * 100.0).where(s > 0).ffill()
                        synth = synth.dropna()
                        if not synth.empty:
                            prices[tk] = synth
                            print(f"    {tk}: synthetic proxy from ff_mcap ({len(synth)} rows)")

    # ── Validate: fail loudly if any CURRENTLY-ACTIVE constituent has no data ──
    current_active = {
        tk for tk in all_active_tickers
        if effective_entry.get(tk, BASE_DATE) <= end_date
        and effective_exit.get(tk) is None
    }
    missing_now = [
        tk for tk in current_active
        if prices.get(tk) is None or prices[tk].empty
    ]
    if missing_now:
        raise RuntimeError(
            f"FATAL: no price data for currently-active constituent(s): "
            f"{missing_now}. Cannot build a valid index. "
            f"Resolve the data gap before re-running."
        )

    # ── Step 4: Collect all entry dates as rebalance triggers ────────────────
    print("\n── Entry event rebalance triggers ───────────────────────────────────")
    implicit_events: list[pd.Timestamp] = []
    for tk, entry_dt in effective_entry.items():
        if entry_dt > BASE_DATE:
            implicit_events.append(entry_dt)
            print(f"  {tk}: entry rebalance trigger {entry_dt.date()}")

    # ── Step 5: Determine rebalance schedule ─────────────────────────────────
    with open(EVENTS_PATH) as f:
        events_json = json.load(f)
    explicit_event_dates = [e["effective_date"] for e in events_json]
    all_event_dates = explicit_event_dates + [d.strftime("%Y-%m-%d") for d in implicit_events]

    rebalance_dates = get_rebalance_dates(
        all_trading_days, all_event_dates, BASE_DATE, end_date
    )
    print(f"\n── Rebalance schedule: {len(rebalance_dates)} dates ─────────────────")
    for rd in rebalance_dates:
        print(f"  {rd.date()}")

    # ── Step 6: Compute index day by day ─────────────────────────────────────
    print("\n── Computing index ──────────────────────────────────────────────────")

    index_vals: dict[pd.Timestamp, float] = {}
    units: dict[str, float] = {}   # z47_ticker -> portfolio units
    prev_active: set[str] = set()

    rebalance_set = set(rebalance_dates)

    for dt in all_trading_days:

        is_rebalance = (dt in rebalance_set)

        # Get active constituents today
        active = build_active_set(dt, effective_entry, effective_exit)

        if is_rebalance or dt == BASE_DATE:
            # ── Pre-rebalance index value ──
            if dt == BASE_DATE:
                i_prev = 100.0   # index starts at 100
            else:
                # Compute from current units + last-available prices.
                # Use last available price (not exact-date check) so that
                # tickers with missing data on this date (recently listed,
                # or weekend data gaps) don't silently drop out of i_prev.
                i_prev = 0.0
                for tk, u in units.items():
                    p_series = prices.get(tk)
                    if p_series is not None:
                        avail_p = p_series.loc[:dt].dropna()
                        if not avail_p.empty:
                            i_prev += u * float(avail_p.iloc[-1])
                if i_prev <= 0:
                    i_prev = list(index_vals.values())[-1] if index_vals else 100.0

            # ── Build ff_mcap snapshot for active constituents ──
            ff_snap: dict[str, float] = {}
            for tk in active:
                s = ff_mcap_daily.get(tk)
                v = 0.0
                if s is not None:
                    avail = s.loc[:dt].dropna()
                    if not avail.empty:
                        v = float(avail.iloc[-1])
                ff_snap[tk] = max(v, 0.0)

            # ── Apply 10% cap → weights ──
            weights = apply_iterative_cap(ff_snap)

            if not weights:
                # Fallback: equal-weight active set
                weights = {tk: 1.0 / len(active) for tk in active}

            # ── Set new units for continuous index ──
            new_units: dict[str, float] = {}
            for tk, w in weights.items():
                p_series = prices.get(tk)
                if p_series is None:
                    continue
                avail_p = p_series.loc[:dt].dropna()
                if avail_p.empty:
                    continue
                p_now = float(avail_p.iloc[-1])
                if p_now > 0:
                    new_units[tk] = w * i_prev / p_now

            units = new_units

            if dt == BASE_DATE:
                index_vals[dt] = 100.0
            else:
                # Continuity verification using last-available price (not exact-date)
                # This matches how i_prev was computed, ensuring index_vals[dt] = i_prev
                iv = 0.0
                for _tk, _u in units.items():
                    _ps = prices.get(_tk)
                    if _ps is not None:
                        _ap = _ps.loc[:dt].dropna()
                        if not _ap.empty:
                            iv += _u * float(_ap.iloc[-1])
                index_vals[dt] = iv if iv > 0 else i_prev

            # Print rebalance summary
            top3 = sorted(weights.items(), key=lambda x: -x[1])[:3]
            print(f"  Rebalance {dt.date()}  I={index_vals[dt]:.2f}"
                  f"  N={len(weights)}  top3={[(t, round(w*100,1)) for t,w in top3]}")

        else:
            # ── Normal day: compute from units ──
            iv = 0.0
            for tk, u in units.items():
                p_series = prices.get(tk)
                if p_series is None:
                    continue
                # Use last available price on or before dt
                avail_p = p_series.loc[:dt].dropna()
                if avail_p.empty:
                    continue
                iv += u * float(avail_p.iloc[-1])

            if iv <= 0:
                # Forward-fill from previous day
                iv = list(index_vals.values())[-1] if index_vals else 100.0
            index_vals[dt] = iv

        prev_active = active

    # ── Step 7: Build Nifty 500 series ───────────────────────────────────────
    print("\n── Building Nifty 500 series ─────────────────────────────────────────")
    n500_abs_series: dict[pd.Timestamp, float] = {}
    n500_idx_series: dict[pd.Timestamp, float] = {}

    if not n500_prices.empty:
        # Base value: first available on or after BASE_DATE
        n500_base_avail = n500_prices[n500_prices.index >= BASE_DATE]
        if n500_base_avail.empty:
            print("  WARN: Nifty 500 has no data at base date")
        else:
            n500_base_val = float(n500_base_avail.iloc[0])
            print(f"  N500 base value at {n500_base_avail.index[0].date()}: {n500_base_val:.2f}")
            for dt in all_trading_days:
                avail = n500_prices.loc[:dt].dropna()
                if not avail.empty:
                    v = float(avail.iloc[-1])
                    n500_abs_series[dt] = round(v, 2)
                    n500_idx_series[dt] = round(v / n500_base_val * 100.0, 4)
    else:
        print("  ERROR: No Nifty 500 data")

    # ── Step 8: Write CSV ─────────────────────────────────────────────────────
    print(f"\n── Writing {CSV_PATH} ───────────────────────────────────────────────")

    rows = []
    for dt in all_trading_days:
        if dt not in index_vals:
            continue
        iv = round(index_vals[dt], 6)
        rows.append({
            "date":         dt.strftime("%Y-%m-%d"),
            "z47_float":    iv,
            "z47_mcap":     iv,       # kept equal for backward compat
            "n500_indexed": n500_idx_series.get(dt, ""),
            "n500_abs":     n500_abs_series.get(dt, ""),
        })

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date","z47_float","z47_mcap","n500_indexed","n500_abs"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"  Wrote {len(rows)} rows.")

    # ── Step 9: Verification ─────────────────────────────────────────────────
    print("\n── Verification ─────────────────────────────────────────────────────")
    print(f"  First row:  {rows[0]}")
    print(f"  Last  row:  {rows[-1]}")

    z47_vals = [r["z47_float"] for r in rows]
    n500_vals = [r["n500_indexed"] for r in rows if r["n500_indexed"] != ""]
    print(f"  z47  range: {min(z47_vals):.2f} – {max(z47_vals):.2f}")
    print(f"  N500 range: {min(n500_vals):.2f} – {max(n500_vals):.2f}")

    # Check continuity around key events
    def check_continuity(label, date_before, date_on):
        idx_before = {r["date"]: r["z47_float"] for r in rows}
        v_before = idx_before.get(date_before)
        v_on     = idx_before.get(date_on)
        if v_before and v_on:
            pct = (v_on - v_before) / v_before * 100
            print(f"  Continuity {label}: {date_before}={v_before:.4f}  {date_on}={v_on:.4f}  Δ={pct:+.2f}%")
        else:
            print(f"  Continuity {label}: data not available ({date_before}={v_before}, {date_on}={v_on})")

    check_continuity("Awfis entry",   "2024-05-29", "2024-05-30")
    check_continuity("360One exit",   "2024-11-13", "2024-11-14")
    check_continuity("Amagi entry",   "2026-01-20", "2026-01-21")
    check_continuity("Fractal entry", "2026-02-13", "2026-02-16")
    check_continuity("Aye entry",     "2026-02-13", "2026-02-16")
    check_continuity("Kissht entry",  "2026-05-07", "2026-05-08")

    print("\nDone.")


if __name__ == "__main__":
    main()
