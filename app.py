"""Z47 Index — Live Dashboard  v2.1"""

import os
import time
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import yfinance as yf
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import anthropic
from streamlit_js_eval import streamlit_js_eval
from streamlit_autorefresh import st_autorefresh

from companies import COMPANIES, SECTOR_COLORS, SECTOR_BADGE_COLORS, yf_ticker
import page_recent_ipos
import page_upcoming_ipos
import page_block_deals
import page_drhp
from z47_assistant import render_z47_assistant, ask_z47_with_search, SYSTEM_PROMPTS
try:
    from takeaway_constants import (
        HARDCODED_INDEX_TAKEAWAY,
        HARDCODED_VALUATION_TAKEAWAY,
        HARDCODED_FUNDAMENTALS,
        HARDCODED_SECTOR_TAKEAWAYS,
        QUALITY_BAR_FEW_SHOT,
    )
except Exception as _tc_err:
    import traceback as _tb
    print(f"[WARN] takeaway_constants failed to import: {_tc_err}")
    _tb.print_exc()
    HARDCODED_INDEX_TAKEAWAY    = {"text": "", "window": "", "icon": "✨", "header": "", "updated": ""}
    HARDCODED_VALUATION_TAKEAWAY = {"text": "", "window": "", "icon": "📊", "header": "", "updated": ""}
    HARDCODED_FUNDAMENTALS      = {}
    HARDCODED_SECTOR_TAKEAWAYS  = {}
    QUALITY_BAR_FEW_SHOT        = ""

# ── Persistent disk cache (survives container restarts) ───────────────────────
# Falls back gracefully if /tmp is read-only or pickle fails — no crash.
import pickle as _pickle

_DISK_CACHE_DIR = "/tmp/z47_cache"

def _dcache_get(key: str, ttl_secs: int):
    """Return cached value if present and not expired, else None."""
    try:
        _path = f"{_DISK_CACHE_DIR}/{key}.pkl"
        if os.path.exists(_path):
            if time.time() - os.path.getmtime(_path) < ttl_secs:
                with open(_path, "rb") as _f:
                    return _pickle.load(_f)
    except Exception as _dce:
        print(f"[DiskCache] read error {key}: {_dce}")
    return None

def _dcache_set(key: str, value) -> None:
    """Write value to disk cache."""
    try:
        os.makedirs(_DISK_CACHE_DIR, exist_ok=True)
        with open(f"{_DISK_CACHE_DIR}/{key}.pkl", "wb") as _f:
            _pickle.dump(value, _f, protocol=4)
    except Exception as _dce:
        print(f"[DiskCache] write error {key}: {_dce}")

# ── Startup health check ──────────────────────────────────────────────────────
def _run_startup_health_check() -> None:
    """
    Validate critical data at import time and print warnings to console.
    Never raises — problems are logged, not surfaced to users.
    """
    try:
        from ipo_investor_data import VERIFIED_INVESTOR_DATA
        _issues = []
        for _company, _investors in VERIFIED_INVESTOR_DATA.items():
            for _name, _data in _investors.items():
                _waca = _data.get("waca")
                if _waca is not None:
                    try:
                        float(_waca)
                    except (TypeError, ValueError):
                        _issues.append(
                            f"  BAD WACA: {_company} / {_name} → {_waca!r}"
                        )
                _ofs = _data.get("ofs_shares")
                if _ofs is not None:
                    try:
                        int(_ofs)
                    except (TypeError, ValueError):
                        _issues.append(
                            f"  BAD OFS: {_company} / {_name} → {_ofs!r}"
                        )
        if _issues:
            print("[HEALTH CHECK] ⚠️  Data issues found:")
            for _i in _issues:
                print(_i)
        else:
            print(f"[HEALTH CHECK] ✅  All VERIFIED_INVESTOR_DATA entries validated "
                  f"({sum(len(v) for v in VERIFIED_INVESTOR_DATA.values())} investors).")
    except Exception as _hc_err:
        print(f"[HEALTH CHECK] Could not run: {_hc_err}")

_run_startup_health_check()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Z47'47",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Colour palette ────────────────────────────────────────────────────────────
BG      = "#fdf6ec"   # page background — warm cream
CARD_BG = "#f6f9fd"   # cards / charts — barely-there blue tint
BG_ALT  = "#edf3fa"   # table header rows / alternating rows
BORDER  = "#ccdaea"   # soft blue-grey border

# ── Canonical chart line colors — use EVERYWHERE for consistency ──────────────
# Sampled from the Z47'47 overview chart (make_perf_chart) which is the reference
C_Z47     = "#c2410c"   # Z47'47  — darker red-orange, solid
C_NIFTY   = "#1d4ed8"   # Nifty 50 — blue, solid
C_SENSEX  = "#15803d"   # Sensex   — green, solid
C_COMPANY = "#ff7f0e"   # Individual company — bright orange, dashed

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
.stApp {{ background-color: {BG}; }}

section[data-testid="stSidebar"] {{ background: {BG_ALT}; }}

.metric-card {{
    background: {CARD_BG};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 20px 24px;
    text-align: center;
    box-shadow: 0 1px 4px rgba(180,120,60,.08);
}}
.metric-label {{ color: #8b6d4a; font-size: 11px; font-weight: 600;
    letter-spacing: .06em; text-transform: uppercase; margin-bottom: 6px; }}
.metric-value {{ color: #1a0f00; font-size: 28px; font-weight: 700; line-height: 1; }}
.delta-pos {{ color: #16a34a; font-size: 13px; font-weight: 500; margin-top: 4px; }}
.delta-neg {{ color: #dc2626; font-size: 13px; font-weight: 500; margin-top: 4px; }}
.delta-neu {{ color: #a38060; font-size: 13px; margin-top: 4px; }}

.section-header {{
    color: #1a0f00; font-size: 17px; font-weight: 700;
    margin: 36px 0 14px 0;
    padding-bottom: 8px;
    border-bottom: 2px solid {BORDER};
}}

.card-wrap {{
    background: {CARD_BG};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 20px 24px;
    box-shadow: 0 1px 4px rgba(180,120,60,.08);
}}

.last-updated {{ color: #a38060; font-size: 12px; text-align: right; }}
#MainMenu, footer, header {{ visibility: hidden; height: 0 !important; }}
[data-testid="stHeader"]    {{ display: none !important; height: 0 !important; }}
[data-testid="stToolbar"]   {{ display: none !important; height: 0 !important; }}
[data-testid="stDecoration"]{{ display: none !important; }}
[data-testid="collapsedControl"] {{ display: none !important; }}
[data-testid="stSidebar"]   {{ display: none !important; }}
.stApp > header {{ display: none !important; }}
.block-container {{ padding-top: 0.5rem !important; }}

/* ── Active nav button → orange ──────────────────────────────────── */
button[kind="primary"],
button[data-testid="baseButton-primary"] {{
    background-color: #ea580c !important;
    border-color:     #ea580c !important;
    color: white !important;
}}
button[kind="primary"]:hover,
button[data-testid="baseButton-primary"]:hover {{
    background-color: #c2410c !important;
    border-color:     #c2410c !important;
}}

/* ── Top nav ──────────────────────────────────────────────────────── */
.topnav-wrap {{
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 10px 0 6px 0;
    border-bottom: 2px solid {BORDER};
    margin-bottom: 18px;
}}
.subnav-wrap {{
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 0;
    border-bottom: 1px solid {BORDER};
    margin-bottom: 14px;
}}

/* ── Mobile card ─────────────────────────────────────────────────── */
.mobile-kpi {{
    background: {CARD_BG};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 14px 16px;
    text-align: center;
    margin-bottom: 8px;
}}
.mobile-kpi-label {{ color: #8b6d4a; font-size: 10px; font-weight: 600;
    letter-spacing: .06em; text-transform: uppercase; margin-bottom: 4px; }}
.mobile-kpi-value {{ color: #1a0f00; font-size: 22px; font-weight: 700; line-height: 1; }}
</style>
""", unsafe_allow_html=True)


# ── Data helpers ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def load_history() -> pd.DataFrame:
    csv_path = os.path.join(os.path.dirname(__file__), "z47_history.csv")
    df = pd.read_csv(csv_path, parse_dates=["date"])
    return df.sort_values("date").reset_index(drop=True)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_live_indices() -> tuple:
    nifty = sensex = None
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.nseindia.com/"}
    try:
        s = requests.Session()
        s.get("https://www.nseindia.com", headers=headers, timeout=6)
        r = s.get("https://www.nseindia.com/api/allIndices", headers=headers, timeout=8)
        if r.status_code == 200:
            for idx in r.json().get("data", []):
                if idx.get("index") == "NIFTY 50":
                    nifty = float(idx["last"])
    except Exception:
        pass
    try:
        nifty = nifty or float(yf.Ticker("^NSEI").fast_info.last_price)
    except Exception:
        pass
    try:
        sensex = float(yf.Ticker("^BSESN").fast_info.last_price)
    except Exception:
        pass
    return nifty, sensex


@st.cache_data(ttl=3600, show_spinner=False)
def get_usdinr() -> float:
    try:
        return round(float(yf.Ticker("USDINR=X").fast_info.last_price), 2)
    except Exception:
        return 85.0


@st.cache_data(ttl=300, show_spinner=False)
def fetch_nse_price(symbol: str) -> dict:
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.nseindia.com/"}
    try:
        s = requests.Session()
        s.get("https://www.nseindia.com", headers=headers, timeout=5)
        r = s.get(f"https://www.nseindia.com/api/quote-equity?symbol={symbol}",
                  headers=headers, timeout=8)
        if r.status_code == 200:
            pi = r.json().get("priceInfo", {})
            return {"price": pi.get("lastPrice"), "pct_change": pi.get("pChange"),
                    "prev_close": pi.get("previousClose")}
    except Exception:
        pass
    return {}


@st.cache_data(ttl=300, show_spinner=False)
def fetch_nasdaq_price(symbol: str) -> dict:
    try:
        fi = yf.Ticker(symbol).fast_info
        price = float(fi.last_price)
        prev  = float(fi.previous_close) if hasattr(fi, "previous_close") else None
        pct   = round((price / prev - 1) * 100, 2) if prev and prev != 0 else None
        return {"price": price, "pct_change": pct, "prev_close": prev}
    except Exception:
        return {}


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_market_caps() -> dict:
    """Live market cap for all 47 companies via parallel yfinance fast_info calls."""
    def _get(c):
        try:
            fi = yf.Ticker(yf_ticker(c)).fast_info
            mc = getattr(fi, "market_cap", None)
            if mc and mc > 0:
                currency = "INR" if c["exchange"] == "NSE" else "USD"
                return c["ticker"], {"mc": mc / 1e6, "currency": currency}
        except Exception:
            pass
        return c["ticker"], None

    results = {}
    with ThreadPoolExecutor(max_workers=12) as ex:
        futures = {ex.submit(_get, c): c for c in COMPANIES}
        for f in as_completed(futures):
            ticker, data = f.result()
            if data:
                results[ticker] = data
    return results


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_1m_returns() -> dict[str, float]:
    """
    Batch download 50 days of prices and compute exact 1-calendar-month returns.

    Methodology (matches Google Finance):
    - End price   = close of the most recent trading day available
    - Start price = close of the first trading day ON OR AFTER the date
                    that is exactly 1 calendar month ago
                    (skips forward over weekends / market holidays, as
                    Google Finance does when that date falls on a holiday)
    - Return = (end − start) / start × 100

    Fixes the previous bug where iloc[0] of a 37-day window was used as the
    start, anchoring ~37 calendar days ago instead of exactly 1 month ago.
    """
    tickers      = [yf_ticker(c) for c in COMPANIES]
    today        = pd.Timestamp(datetime.now().date())
    start_target = today - relativedelta(months=1)
    fetch_start  = (today - pd.Timedelta(days=50)).strftime("%Y-%m-%d")

    try:
        raw    = yf.download(tickers, start=fetch_start,
                             progress=False, auto_adjust=True, timeout=25)
        closes = raw["Close"]
    except Exception:
        return {}

    result = {}
    for c in COMPANIES:
        tk = yf_ticker(c)
        try:
            s = closes[tk].dropna()
            if s.empty or len(s) < 2:
                continue

            # Normalise index to tz-naive dates
            s.index = pd.to_datetime(s.index)
            if s.index.tz is not None:
                s.index = s.index.tz_localize(None)
            s = s.sort_index()

            end_price = float(s.iloc[-1])

            # First trading day on or after exactly 1M ago
            candidates = s[s.index >= start_target]
            if candidates.empty:
                start_price = float(s.iloc[0])   # fallback: oldest available
            else:
                start_price = float(candidates.iloc[0])

            if start_price <= 0 or end_price <= 0:
                continue

            result[c["ticker"]] = round(float((end_price / start_price - 1) * 100), 2)
        except Exception:
            pass
    return result


@st.cache_data(ttl=86400, show_spinner=False)   # refresh once per day — historical data is stable
def fetch_long_history() -> dict:
    """
    Compute % market-cap change since listing and since 1 Jan 2024 for all 47 stocks.

    Why not use share price directly:
      Stock splits and bonus issues divide the price but multiply shares,
      leaving market cap unchanged. Using raw price would show a false drop.

    How we fix it:
      yf.download with auto_adjust=False gives unadjusted ('raw') prices.
      We separately download the split/bonus history and build a cumulative
      split-factor series. Dividing historical raw prices by cumulative split
      factors converts them to a 'constant share-count' basis — equivalent to
      market-cap % change — without any dividend contamination.

    % change = (current_price / split_adjusted_historical_price - 1) × 100
             = (current_mkt_cap / historical_mkt_cap) - 1               ✓
    """
    tickers = [yf_ticker(c) for c in COMPANIES]
    jan2024 = pd.Timestamp("2024-01-01")

    # ── 1. Download raw (unadjusted) close prices ──────────────────────────
    try:
        raw    = yf.download(tickers, start="2019-01-01", progress=False,
                             auto_adjust=False)
        closes = raw["Close"]
    except Exception:
        return {}

    # ── 2. Per-ticker: build split-adjusted series ──────────────────────────
    results = {}
    for c in COMPANIES:
        tk = yf_ticker(c)
        try:
            series = closes[tk].dropna().copy()
            if len(series) < 5:
                continue

            # Fetch split & bonus history for this ticker
            try:
                actions = yf.Ticker(tk).splits          # pd.Series indexed by date
                if not actions.empty:
                    # Build cumulative divisor: product of all split factors on/after t
                    # i.e. historical price × divisor = 'today-share-count' price
                    divisor = pd.Series(1.0, index=series.index)
                    for split_date, factor in actions.items():
                        if factor <= 0:
                            continue
                        split_ts = pd.Timestamp(split_date).tz_localize(None) \
                                   if split_date.tzinfo else pd.Timestamp(split_date)
                        # All dates BEFORE the split get divided by the factor
                        divisor[divisor.index < split_ts] /= float(factor)
                    series = series / divisor
            except Exception:
                pass  # if actions unavailable, raw price is used as-is

            current = float(series.iloc[-1])
            first   = float(series.iloc[0])
            listing_pct = round((current / first - 1) * 100, 1)

            sub2024     = series[series.index >= jan2024]
            jan2024_pct = round((current / float(sub2024.iloc[0]) - 1) * 100, 1) \
                          if not sub2024.empty else None

            results[c["ticker"]] = {
                "since_listing_pct": listing_pct,
                "since_jan2024_pct": jan2024_pct,
                "listing_date":      pd.Timestamp(series.index[0]).strftime("%b %Y"),
            }
        except Exception:
            pass
    return results


@st.cache_data(ttl=300, show_spinner=False)   # same cadence as prices
def fetch_company_news(yf_tk: str) -> list:
    """
    Fetch and normalise news from yfinance.
    yfinance ≥0.2.50 wraps each article in a 'content' sub-dict with new
    field names. We normalise to a flat dict so the rest of the UI doesn't care.
    """
    try:
        raw = yf.Ticker(yf_tk).news or []
    except Exception:
        return []

    normalised = []
    for item in raw:
        # New format: all data is under item["content"]
        c = item.get("content", {})
        if c:
            # ISO date string → unix timestamp for backwards compat
            pub_str = c.get("pubDate") or c.get("displayTime", "")
            try:
                import datetime
                ts = int(datetime.datetime.fromisoformat(
                    pub_str.replace("Z", "+00:00")).timestamp())
            except Exception:
                ts = 0

            url = (c.get("clickThroughUrl") or c.get("canonicalUrl") or {}).get("url", "#")
            ctype = c.get("contentType", "STORY")

            normalised.append({
                "title":               c.get("title", ""),
                "link":                url,
                "publisher":           (c.get("provider") or {}).get("displayName", ""),
                "providerPublishTime": ts,
                "type":                "PRESS_RELEASE" if ctype == "PRESS_RELEASE" else "STORY",
                "summary":             c.get("summary", ""),
            })
        else:
            # Old flat format — pass through as-is
            normalised.append(item)

    return normalised


def _yf_info_with_fallback(c: dict) -> dict:
    """
    Fetch yfinance info + recommendations + earnings history for a company.

    Uses retry with exponential back-off to survive Yahoo Finance rate limits.
    All 47 NSE companies work with .NS; .BO is a belt-and-suspenders fallback.
    Also pre-fetches recommendations_summary and earnings_history here so the
    daily cached batch (fetch_all_analyst_data) is the reliable source — the
    per-company live call is only used as a supplement.
    """
    def _extract(info):
        return {
            "targetLow":          info.get("targetLowPrice"),
            "targetHigh":         info.get("targetHighPrice"),
            "targetMean":         info.get("targetMeanPrice"),
            "targetMedian":       info.get("targetMedianPrice"),
            "currentPrice":       info.get("currentPrice") or info.get("previousClose"),
            "previousClose":      info.get("previousClose"),
            "recommendationKey":  info.get("recommendationKey"),
            "numberOfAnalysts":   info.get("numberOfAnalystOpinions"),
            "trailingPE":         info.get("trailingPE"),
            "forwardPE":          info.get("forwardPE"),
            "trailingEps":        info.get("trailingEps"),
            "beta":               info.get("beta"),
            "fiftyTwoWeekLow":    info.get("fiftyTwoWeekLow"),
            "fiftyTwoWeekHigh":   info.get("fiftyTwoWeekHigh"),
            "dividendYield":      info.get("dividendYield"),
            "averageVolume":      info.get("averageVolume"),
            "volume":             info.get("volume"),
            "marketCap":          info.get("marketCap"),
        }

    def _fetch_ticker_with_retry(sym, retries=3):
        """Return a live yf.Ticker, retrying on rate-limit / empty response."""
        for attempt in range(retries):
            try:
                info = yf.Ticker(sym).info or {}
                if info.get("regularMarketPrice") or info.get("currentPrice") or info.get("previousClose"):
                    return yf.Ticker(sym)   # re-create so all attrs are fresh
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
            except Exception:
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
        return yf.Ticker(sym)   # last-ditch attempt

    def _fetch_info_with_retry(sym, retries=3):
        for attempt in range(retries):
            try:
                info = yf.Ticker(sym).info or {}
                if info.get("regularMarketPrice") or info.get("currentPrice") or info.get("previousClose"):
                    return info
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
            except Exception:
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
        try:
            return yf.Ticker(sym).info or {}
        except Exception:
            return {}

    def _fetch_recs(t):
        """Fetch recommendations_summary, fall back to recommendations."""
        try:
            rs = t.recommendations_summary
            if rs is not None and not rs.empty:
                return rs
        except Exception:
            pass
        try:
            r = t.recommendations
            if r is not None and not r.empty:
                return r
        except Exception:
            pass
        return pd.DataFrame()

    def _fetch_earnings(t):
        """Fetch earnings_history (no lxml needed — columns: epsActual, epsEstimate)."""
        try:
            eh = t.earnings_history
            if eh is not None and not eh.empty:
                return eh
        except Exception:
            pass
        return pd.DataFrame()

    # ── NASDAQ stocks ────────────────────────────────────────────────────
    if c["exchange"] != "NSE":
        sym = yf_ticker(c)
        t   = _fetch_ticker_with_retry(sym)
        return {
            **_extract(t.info or {}),
            "recommendations": _fetch_recs(t),
            "earnings_history": _fetch_earnings(t),
        }

    # ── NSE: try .NS first ───────────────────────────────────────────────
    ns_sym  = c["ticker"] + ".NS"
    ns_info = _fetch_info_with_retry(ns_sym)
    ns_data = _extract(ns_info)

    # If analyst price target still missing, try .BO
    if not ns_data.get("targetMean"):
        try:
            bo_info = _fetch_info_with_retry(c["ticker"] + ".BO")
            bo_data = _extract(bo_info)
            ns_data = {**ns_data, **{k: v for k, v in bo_data.items() if v and not ns_data.get(k)}}
        except Exception:
            pass

    # Fetch recommendations + earnings on the primary ticker
    t_ns = yf.Ticker(ns_sym)
    return {
        **ns_data,
        "recommendations":  _fetch_recs(t_ns),
        "earnings_history": _fetch_earnings(t_ns),
    }


@st.cache_data(ttl=86400, show_spinner=False)  # refresh daily — analyst data changes slowly
def fetch_all_analyst_data() -> dict:
    """Pre-fetch analyst price targets + key stats for all 47 companies.

    Uses 4 workers (not 10) so Yahoo Finance doesn't rate-limit us.
    Each worker also retries with back-off inside _yf_info_with_fallback.
    """
    results = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(_yf_info_with_fallback, c): c for c in COMPANIES}
        for f in as_completed(futures):
            c = futures[f]
            try:
                results[c["ticker"]] = f.result()
            except Exception:
                results[c["ticker"]] = {}
    return results


@st.cache_data(ttl=86400, show_spinner=False)  # financial statements are quarterly — refresh daily
def fetch_company_financials(yf_tk: str) -> dict:
    """Income statement, balance sheet, cash flow — fetched in parallel. Disk-cached 24h."""
    # ── Disk cache (survives container restarts) ──────────────────────────────
    _dc_key = f"fins_{yf_tk.replace('.', '_').replace('=', '_')}"
    _cached = _dcache_get(_dc_key, ttl_secs=86400)
    if _cached is not None:
        print(f"[PERF] fetch_company_financials({yf_tk}): disk cache hit")
        return _cached

    _t0 = time.time()
    _attrs = [
        ("income_annual",      "financials"),
        ("income_quarterly",   "quarterly_financials"),
        ("balance_annual",     "balance_sheet"),
        ("balance_quarterly",  "quarterly_balance_sheet"),
        ("cashflow_annual",    "cashflow"),
        ("cashflow_quarterly", "quarterly_cashflow"),
    ]

    def _fetch_one(item):
        _key, _attr = item
        try:    return _key, getattr(yf.Ticker(yf_tk), _attr)
        except: return _key, pd.DataFrame()

    result = {}
    try:
        with ThreadPoolExecutor(max_workers=6) as _ex:
            for _k, _df in _ex.map(_fetch_one, _attrs):
                result[_k] = _df
    except Exception:
        result = {}
    print(f"[PERF] fetch_company_financials({yf_tk}): live fetch {time.time()-_t0:.1f}s")
    _dcache_set(_dc_key, result)
    return result


# ── Index Fundamentals — constituent lists ────────────────────────────────────

NIFTY50_SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "BHARTIARTL.NS",
    "ICICIBANK.NS", "INFY.NS", "SBIN.NS", "HINDUNILVR.NS",
    "ITC.NS", "LICI.NS", "KOTAKBANK.NS", "LT.NS",
    "HCLTECH.NS", "BAJFINANCE.NS", "MARUTI.NS", "SUNPHARMA.NS",
    "ADANIENT.NS", "ONGC.NS", "NTPC.NS", "TITAN.NS",
    "ULTRACEMCO.NS", "WIPRO.NS", "AXISBANK.NS", "ASIANPAINT.NS",
    "POWERGRID.NS", "M&M.NS", "ADANIPORTS.NS", "NESTLEIND.NS",
    "TECHM.NS", "BAJAJFINSV.NS", "COALINDIA.NS", "TATASTEEL.NS",
    "JSWSTEEL.NS", "HINDALCO.NS", "DRREDDY.NS", "CIPLA.NS",
    "DIVISLAB.NS", "BRITANNIA.NS", "EICHERMOT.NS", "BPCL.NS",
    "APOLLOHOSP.NS", "TATACONSUM.NS", "HEROMOTOCO.NS",
    "SHRIRAMFIN.NS", "BAJAJ-AUTO.NS", "GRASIM.NS",
    "SBILIFE.NS", "HDFCLIFE.NS", "INDUSINDBK.NS", "BEL.NS",
]

SENSEX_SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "BHARTIARTL.NS",
    "ICICIBANK.NS", "INFY.NS", "SBIN.NS", "HINDUNILVR.NS",
    "ITC.NS", "KOTAKBANK.NS", "LT.NS", "HCLTECH.NS",
    "BAJFINANCE.NS", "MARUTI.NS", "SUNPHARMA.NS", "TITAN.NS",
    "ULTRACEMCO.NS", "WIPRO.NS", "AXISBANK.NS", "ASIANPAINT.NS",
    "POWERGRID.NS", "M&M.NS", "NESTLEIND.NS", "TECHM.NS",
    "BAJAJFINSV.NS", "TATASTEEL.NS", "JSWSTEEL.NS",
    "DRREDDY.NS", "ADANIPORTS.NS", "NTPC.NS",
]

# Module-level Z47 symbols list (derived from COMPANIES at import time)
# Used by MCap blocks and performance chart features
def _get_z47_symbols():
    return [yf_ticker(c) for c in COMPANIES]

# Eagerly evaluated at startup — used in get_total_market_caps()
Z47_SYMBOLS = _get_z47_symbols()


# ── Preamble-stripping helper ─────────────────────────────────────────────────
def _clean_takeaway_output(raw: str) -> str | None:
    """
    Strip model preamble/meta-commentary from a raw AI response.
    Returns cleaned text or None if the result is too short to be useful.
    Centralised here so every takeaway generator uses the same logic.
    """
    if not raw or not raw.strip():
        return None
    import re as _re
    lines = raw.split('\n')
    _PREAMBLE_STARTS = (
        "now i", "let me", "here is", "here's", "i'll", "i will", "i've",
        "based on", "i have", "sure,", "sure.", "okay,", "certainly,",
        "certainly.", "of course", "absolutely", "great,", "the following",
        "below is", "below are", "i'll now", "i need to", "i'll write",
        "i'll provide", "i'll analyze", "i'll search",
    )
    # Header-label lines like "Z47'47 WEEKLY TAKEAWAY — WEEK 21, 2026"
    _HEADER_PAT = _re.compile(
        r"^(z47'?47|z47)\s+(weekly|monthly|takeaway|valuation|sector|—|index)",
        _re.IGNORECASE,
    )
    cleaned = []
    for line in lines:
        s = line.strip()
        sl = s.lower()
        if not s:
            # Keep blank lines only after content has started
            if cleaned:
                cleaned.append(line)
            continue
        if any(sl.startswith(p) for p in _PREAMBLE_STARTS):
            print(f"[_clean_takeaway] stripped preamble line: {s[:60]!r}")
            continue
        if _HEADER_PAT.match(s):
            print(f"[_clean_takeaway] stripped header line: {s[:60]!r}")
            continue
        cleaned.append(line)
    # Remove leading/trailing blank lines
    while cleaned and not cleaned[0].strip():
        cleaned.pop(0)
    while cleaned and not cleaned[-1].strip():
        cleaned.pop()
    result = '\n'.join(cleaned).strip()
    if len(result) < 150:
        print(f"[_clean_takeaway] result too short ({len(result)} chars) — returning None")
        return None
    return result


# ── No-preamble instruction prefix (injected into every takeaway prompt) ─────
_NO_PREAMBLE = (
    "Output ONLY the final takeaway text. Do not write any preamble, introduction, "
    "meta-commentary, or header label. Do not say 'Now I have sufficient data', "
    "'Let me synthesize', 'Here is the takeaway', 'I'll write', 'Based on my research', "
    "or any similar lead-in. The UI renders the section header separately — "
    "do not repeat it. Start directly with the first analytical sentence of your content. "
    "CRITICAL: Output the COMPLETE takeaway. Do not abbreviate, do not cut off mid-sentence. "
    "Every sentence must be fully written and terminated with a period. "
    "The final sentence must end with a period — not mid-word or mid-clause. "
)


# ── Shared AI takeaway helper ────────────────────────────────────────────────
def _ai_takeaway(system: str, prompt: str, max_tokens: int = 1500):
    """
    Call Claude with web search and return a cleaned text takeaway, or None on failure.
    Concatenates ALL text blocks (not just first) to capture post-search content.
    Strips model preamble via _clean_takeaway_output().
    max_tokens default raised to 1500 — a 5-6 sentence analyst note needs ~700-1200 tokens.
    """
    _COMPLETE_ENDINGS = ('.', '!', '?', '"', '’', ')', '”')

    def _call_api():
        api_key = (st.secrets.get("ANTHROPIC_API_KEY", "")
                   or os.environ.get("ANTHROPIC_API_KEY", ""))
        if not api_key or api_key.startswith("sk-ant-..."):
            return None
        client = anthropic.Anthropic(api_key=api_key)
        system_with_qb = system + "\n" + QUALITY_BAR_FEW_SHOT
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=max_tokens,
            system=system_with_qb,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content": prompt}],
            extra_headers={"anthropic-beta": "web-search-2025-03-05"},
            timeout=45,
        )
        text_blocks = [
            b.text.strip() for b in resp.content
            if hasattr(b, "text") and b.text.strip()
        ]
        if not text_blocks:
            print(f"[_ai_takeaway] no text blocks (stop_reason={resp.stop_reason})")
            return None
        raw = '\n'.join(text_blocks)
        print(f"[_ai_takeaway] raw: {len(raw)} chars, {len(text_blocks)} block(s), "
              f"stop={resp.stop_reason}")
        return _clean_takeaway_output(raw)

    try:
        result = _call_api()
        if result is None:
            return None
        # Completeness check — warn if truncated, retry once
        if not result.rstrip().endswith(_COMPLETE_ENDINGS):
            print(f"[_ai_takeaway] INCOMPLETE — ends with: {result.rstrip()[-60:]!r} — retrying")
            retry = _call_api()
            if retry and retry.rstrip().endswith(_COMPLETE_ENDINGS):
                print(f"[_ai_takeaway] retry succeeded ({len(retry)} chars)")
                return retry
            # Retry also incomplete — return whichever is longer
            if retry and len(retry) > len(result):
                result = retry
            print(f"[_ai_takeaway] retry still incomplete — returning best available")
        return result
    except Exception as _e:
        print(f"[_ai_takeaway] error: {_e}")
        return None


# ── Shared takeaway box renderer ──────────────────────────────────────────────
def render_takeaway_box(text: str, title: str = "Z47 Takeaway", icon: str = "✨"):
    """Render a purple-gradient takeaway box."""
    st.markdown(
        f"""<div style='background:linear-gradient(135deg,#f3f0ff,#ede9fe);
        border:1px solid #c4b5fd;border-radius:12px;padding:18px 22px;
        margin:12px 0;box-shadow:0 1px 6px rgba(124,58,237,.10)'>
        <div style='font-size:12px;font-weight:700;color:#6d28d9;letter-spacing:.06em;
        text-transform:uppercase;margin-bottom:8px'>{icon} {title}</div>
        <div style='color:#3b1f7a;font-size:14px;line-height:1.65'>{text}</div>
        </div>""",
        unsafe_allow_html=True,
    )


# Financial companies — EV/EBITDA excluded; EV/Revenue uses P/S (MCap/Rev) proxy
# Covers Nifty50 + Sensex30 banks, NBFCs, insurance + asset management
_FINANCIAL_SYMS = {
    # Banks
    "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS",
    "AXISBANK.NS", "INDUSINDBK.NS", "BANDHANBNK.NS",
    "FEDERALBNK.NS", "IDFCFIRSTB.NS", "PNB.NS",
    "BANKBARODA.NS", "CANBK.NS", "UNIONBANK.NS",
    "AUBANK.NS", "KARURVYSYA.NS", "RBLBANK.NS",
    # NBFCs / Financial Services
    "BAJFINANCE.NS", "BAJAJFINSV.NS", "SHRIRAMFIN.NS",
    "CHOLAFIN.NS", "MUTHOOTFIN.NS", "M&MFIN.NS",
    "LTFH.NS", "PFC.NS", "RECLTD.NS", "HUDCO.NS", "IRFC.NS",
    # Insurance
    "SBILIFE.NS", "HDFCLIFE.NS", "LICI.NS",
    "ICICIGI.NS", "GICRE.NS", "NIACL.NS", "GODIGIT.NS",
    # Asset Management / Broking / Exchange
    "HDFCAMC.NS", "NAM-INDIA.NS", "UTIAMC.NS",
    "360ONE.NS", "ANGELONE.NS", "CDSL.NS", "BSE.NS",
}

# Z47 financial companies — NBFC / insurance / HFC / fintech-financial
# EV/EBITDA excluded; EV/Revenue uses P/S (MCap/Rev) proxy
_Z47_FINANCIAL_SYMS = {
    "GROWW.NS", "PAYTM.NS", "SBICARD.NS", "POLICYBZR.NS",
    "360ONE.NS", "GODIGIT.NS", "PINELABS.NS", "APTUS.NS",
    "FIVESTAR.NS", "HOMEFIRST.NS", "INDIASHLTR.NS",
    "MOBIKWIK.NS", "MEDIASSIST.NS", "AYE.NS", "KISSHT.NS",
    "MMYT",       # US-listed, no EV data anyway
}


# ── Feature 1: Total Market Cap Blocks ───────────────────────────────────────

# Build a static fallback map: yf_symbol → INR value from companies.py
# Covers unlisted companies (LENSKART, WAKEFIT) and NASDAQ-USD companies
# that need conversion. Values in INR (mkt_cap_mn * 1e6).
_Z47_STATIC_MCAP_INR: dict[str, float] = {
    yf_ticker(c): c["mkt_cap_mn"] * 1e6
    for c in COMPANIES
}
# NASDAQ companies (MMYT, FRSH) have mkt_cap_mn stored in INR Mn already,
# so no extra conversion needed for the static fallback.

# Set of NASDAQ-listed Z47 tickers (yfinance returns USD for these)
_Z47_NASDAQ_SYMS: set[str] = {
    yf_ticker(c) for c in COMPANIES if c["exchange"] == "NASDAQ"
}

@st.cache_data(ttl=300, show_spinner=False)
def get_total_market_caps() -> dict:
    """
    Robust market cap calculation for Z47, Nifty50, and Sensex.

    Key fixes vs prior version:
    - NASDAQ symbols (MMYT, FRSH): yfinance returns USD → multiply by usd_inr
    - Unlisted symbols (LENSKART, WAKEFIT): yfinance returns 0 → fall back to
      static mkt_cap_mn from companies.py (INR, March 2026 basis)
    - 4-method fetch per symbol (fast_info → info → price×shares → history×shares)

    Expected ranges (May 2026):
      Z47  (47):  ~₹15-22 lakh cr  / $175-260B
      Nifty50:    ~₹180-250 lakh cr / $2.1-3.0T
      Sensex30:   ~₹140-200 lakh cr / $1.7-2.4T
    """
    # Live USD/INR rate — fetch first so fetch_mcap can use it
    try:
        usd_inr = yf.Ticker("INR=X").fast_info.last_price
        if not usd_inr or usd_inr < 70:
            usd_inr = 84.0
    except Exception:
        usd_inr = 84.0

    def fetch_mcap_inr(sym: str) -> float:
        """Return market cap in INR. Uses 4 methods + static fallback."""
        try:
            t = yf.Ticker(sym)
            is_usd = sym in _Z47_NASDAQ_SYMS   # NASDAQ → USD

            # Method 1: fast_info (fastest)
            try:
                mc = t.fast_info.market_cap
                if mc and mc > 1e9:
                    return float(mc) * (usd_inr if is_usd else 1)
            except Exception:
                pass

            # Method 2: info dict
            try:
                info = t.info
                mc = info.get("marketCap")
                if mc and mc > 1e9:
                    return float(mc) * (usd_inr if is_usd else 1)

                # Method 3: currentPrice × shares
                price  = (info.get("currentPrice") or
                          info.get("regularMarketPrice") or 0)
                shares = info.get("sharesOutstanding") or 0
                if price > 0 and shares > 0:
                    calc = float(price * shares)
                    if calc > 1e9:
                        return calc * (usd_inr if is_usd else 1)
            except Exception:
                pass

            # Method 4: last history close × shares
            try:
                info   = t.info
                hist   = t.history(period="1d")
                shares = info.get("sharesOutstanding") or 0
                if not hist.empty and shares > 0:
                    price = float(hist["Close"].iloc[-1])
                    calc  = price * shares
                    if calc > 1e9:
                        return calc * (usd_inr if is_usd else 1)
            except Exception:
                pass

        except Exception as _e:
            print(f"[MCap] {sym}: {_e}")

        # Static fallback: mkt_cap_mn from companies.py (already INR)
        static = _Z47_STATIC_MCAP_INR.get(sym, 0)
        if static > 0:
            print(f"[MCap] {sym}: using static fallback ₹{static/1e12:.2f}L cr")
            return static
        return 0

    def fetch_mcap_nse(sym: str) -> float:
        """Fetch MCap for NSE-only (Nifty/Sensex) symbols — always INR."""
        try:
            t = yf.Ticker(sym)
            try:
                mc = t.fast_info.market_cap
                if mc and mc > 1e9:
                    return float(mc)
            except Exception:
                pass
            info = t.info
            mc   = info.get("marketCap")
            if mc and mc > 1e9:
                return float(mc)
            price  = (info.get("currentPrice") or
                      info.get("regularMarketPrice") or 0)
            shares = info.get("sharesOutstanding") or 0
            if price > 0 and shares > 0:
                return float(price * shares)
        except Exception as _e:
            print(f"[MCap] {sym}: {_e}")
        return 0

    def sum_parallel(symbols, fetch_fn, label):
        total, zero = 0, []
        with ThreadPoolExecutor(max_workers=12) as ex:
            futs = {ex.submit(fetch_fn, s): s for s in symbols}
            for f in as_completed(futs, timeout=30):
                sym = futs[f]
                try:
                    v = f.result()
                    total += v
                    if v == 0:
                        zero.append(sym)
                except Exception:
                    zero.append(sym)
        if zero:
            print(f"[MCap] {label} zeros: {zero}")
        return total

    z47_inr    = sum_parallel(Z47_SYMBOLS,     fetch_mcap_inr, "Z47")
    nifty_inr  = sum_parallel(NIFTY50_SYMBOLS, fetch_mcap_nse, "Nifty50")
    sensex_inr = sum_parallel(SENSEX_SYMBOLS,  fetch_mcap_nse, "Sensex")

    # Sanity validation
    _RANGES = {
        "Z47":    (10e12,  30e12,  "₹10-30L cr"),
        "Nifty":  (140e12, 350e12, "₹140-350L cr"),
        "Sensex": (110e12, 280e12, "₹110-280L cr"),
    }
    for label, val in [("Z47", z47_inr), ("Nifty", nifty_inr), ("Sensex", sensex_inr)]:
        lo, hi, exp = _RANGES[label]
        ok = "PASS" if lo <= val <= hi else "FAIL"
        print(f"[MCap {ok}] {label}=₹{val/1e12:.1f}L cr  expected {exp}  USD/INR={usd_inr:.1f}")

    def fmt_inr(v):
        if v <= 0:
            return "—"
        lakh_cr = v / 1e12      # 1 lakh crore = 1e12 INR
        if lakh_cr >= 100:
            return f"₹{lakh_cr:.0f}L cr"
        return f"₹{lakh_cr:.1f}L cr"

    def fmt_usd(v):
        if v <= 0:
            return "—"
        usd = v / usd_inr
        if usd >= 1e12:
            return f"${usd/1e12:.2f}T"
        if usd >= 1e11:
            return f"${usd/1e9:.0f}B"
        if usd >= 1e9:
            return f"${usd/1e9:.1f}B"
        return f"${usd/1e6:.0f}M"

    return {
        "z47_inr":          z47_inr,
        "nifty_inr":        nifty_inr,
        "sensex_inr":       sensex_inr,
        "z47_inr_fmt":      fmt_inr(z47_inr),
        "nifty_inr_fmt":    fmt_inr(nifty_inr),
        "sensex_inr_fmt":   fmt_inr(sensex_inr),
        "z47_usd_fmt":      fmt_usd(z47_inr),
        "nifty_usd_fmt":    fmt_usd(nifty_inr),
        "sensex_usd_fmt":   fmt_usd(sensex_inr),
        "z47_pct_of_nifty": (z47_inr / nifty_inr * 100 if nifty_inr > 0 else 0),
        "usd_inr_rate":     usd_inr,
    }


def render_mcap_blocks():
    """Render 4 market cap blocks: Z47, Nifty50, Sensex, Z47 as % of Nifty."""
    mc = get_total_market_caps()
    c1, c2, c3, c4 = st.columns(4)

    _bs = ("background:#f8f9fa;border-radius:12px;padding:18px 20px;"
           "text-align:center;border-top:3px solid {color}")

    def _block(col, title, inr_fmt, usd_fmt, subtitle, color):
        with col:
            st.markdown(
                f"<div style='{_bs.format(color=color)}'>"
                f"<div style='font-size:10px;color:#888;text-transform:uppercase;"
                f"letter-spacing:1px;margin-bottom:8px'>{title}</div>"
                f"<div style='font-size:22px;font-weight:700;color:#1a1a2e;"
                f"line-height:1.2'>{inr_fmt}</div>"
                f"<div style='font-size:13px;color:#666;margin-top:4px'>/ {usd_fmt}</div>"
                f"<div style='font-size:11px;color:#aaa;margin-top:6px'>{subtitle}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    _block(c1, "Z47 Total Market Cap",
           mc["z47_inr_fmt"], mc["z47_usd_fmt"],
           "47 new-age tech companies", "#ff7f0e")
    _block(c2, "Nifty 50 — Constituent MCap Sum",
           mc["nifty_inr_fmt"], mc["nifty_usd_fmt"],
           "50 cos · full MCap, not free-float", "#1f77b4")
    _block(c3, "Sensex 30 — Constituent MCap Sum",
           mc["sensex_inr_fmt"], mc["sensex_usd_fmt"],
           "30 cos · full MCap, not free-float", "#2ca02c")

    pct = mc["z47_pct_of_nifty"]
    _purple_style = _bs.format(color="#764ba2")
    with c4:
        st.markdown(
            f"<div style='{_purple_style}'>"
            f"<div style='font-size:10px;color:#888;text-transform:uppercase;"
            f"letter-spacing:1px;margin-bottom:8px'>Z47 as % of Nifty 50</div>"
            f"<div style='font-size:28px;font-weight:700;color:#1a7a4a'>"
            f"{pct:.1f}%</div>"
            f"<div style='font-size:12px;color:#666;margin-top:6px'>"
            f"of Nifty total market cap</div>"
            f"<div style='font-size:10px;color:#aaa;margin-top:4px'>"
            f"USD/INR: {mc['usd_inr_rate']:.1f}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )


# ── Monthly rolling-window helper ─────────────────────────────────────────────
def _monthly_window():
    """
    Return (monday_key, start_label, end_label, start_date_str, end_date_str) for
    monthly rolling takeaway caching.
    Cache key = ISO date of Monday of current week → refreshes every Monday.
    Window = trailing 30 days from today.
    """
    from datetime import date as _d, timedelta as _td
    today = _d.today()
    monday = today - _td(days=today.weekday())   # Monday of current week
    start  = today - _td(days=30)
    return (
        monday.isoformat(),
        f"{start.day} {start.strftime('%b')}",          # e.g. "19 Apr"
        f"{today.day} {today.strftime('%b %Y')}",        # e.g. "19 May 2026"
        start.strftime("%Y-%m-%d"),
        today.strftime("%Y-%m-%d"),
    )


# ── Feature 3 & 7: Z47'47 Monthly takeaway (v2) ──────────────────────────────
@st.cache_data(ttl=604800, show_spinner=False)
def get_z47_index_takeaway_v2(monday_key: str = "") -> str | None:
    """Analyst-quality 5-6 sentence monthly takeaway on Z47'47 index. Cached 1 week (Monday-keyed)."""
    _mk, _sl, _el, _sd, _ed = _monthly_window()
    system = (
        "You are a sell-side equity research analyst writing a monthly takeaway for Z47'47 — "
        "the Z47 index of 47 Indian new-age tech and financial services companies. "
        "Write in tight, professional English. No markdown, no bullet points — plain prose only. "
        "You cover the INDEX as a whole: sector themes, macro read-throughs, valuation observations. "
        "Do not go company-by-company. Write at the index and sector-cohort level."
    )
    prompt = (
        _NO_PREAMBLE
        + f"Analyze the rolling 30-day period from {_sd} to {_ed}. "
        "Search for Z47'47 index performance, Indian new-age tech sector news, "
        "and macro developments over this period. "
        "Write exactly 5-6 lines in this structure: "
        "(1) Headline: Z47'47's 30-day move vs Nifty 50 and what drove the relative performance "
        "at the sector-cohort level — not company-by-company. "
        "(2-4) Mix of key data points (index level, sector performance, macro event) AND at least "
        "2 analyst insights from: variant perception (what consensus has wrong about the index), "
        "structural vs cyclical distinction (permanent re-rate vs mean-reversion), "
        "quality-of-sector-earnings (real outperformance or just multiple expansion without earnings), "
        "read-through to the index from macro/policy events, "
        "what the market is missing about Z47'47's composition or risk profile, "
        "risk-reward asymmetry at current index levels. "
        "Every number must be followed by what it means — not just the number. "
        "(5) The watch-item: what single event or data release would change the index view. "
        "(6) Net read: constructive/cautious/mixed on the index with one-line rationale. "
        "Banned phrases: 'strong performance', 'healthy growth', 'robust quarter', "
        "'positive momentum', 'in line with expectations', 'broadly stable', "
        "'well-positioned', 'execution remains key'. "
        "No buy/sell/hold. No markdown. Plain prose. No preamble."
    )
    return _ai_takeaway(system, prompt, max_tokens=1500)


# ── Valuation multiples takeaway (v2) ────────────────────────────────────────
@st.cache_data(ttl=604800, show_spinner=False)
def get_valuation_multiples_takeaway(ev_revenue: float | None, ev_ebitda: float | None,
                                     pe: float | None, rev_growth: float | None,
                                     ebitda_margin: float | None,
                                     monday_key: str = "") -> str | None:
    """4-5 sentence research-quality valuation note on Z47'47 vs Nifty. Monday-keyed, cached 1 week."""
    _mk, _sl, _el, _sd, _ed = _monthly_window()
    parts = []
    if ev_revenue:    parts.append(f"Z47 EV/Revenue={ev_revenue:.1f}x")
    if ev_ebitda:     parts.append(f"Z47 EV/EBITDA={ev_ebitda:.1f}x")
    if pe:            parts.append(f"Z47 P/E={pe:.1f}x")
    if rev_growth:    parts.append(f"Z47 Rev Growth={rev_growth*100:.0f}%")
    if ebitda_margin: parts.append(f"Z47 EBITDA Margin={ebitda_margin*100:.0f}%")
    metrics_str = ", ".join(parts) if parts else "data unavailable"
    system = (
        "You are a sell-side equity research analyst writing a valuation deep-dive note for Z47'47 — "
        "the index of 47 Indian new-age tech and financial-services companies. "
        "Write in tight, professional English. Cite actual numbers. No markdown — plain prose only."
    )
    prompt = (
        _NO_PREAMBLE
        + f"Rolling 30-day window: {_sd} to {_ed}. Z47'47 current multiples: {metrics_str}. "
        "Search for the latest Nifty 50 P/E, EV/EBITDA, P/B and Sensex valuation data "
        "from screener.in, NSE, or financial news. "
        "Write exactly 4-5 lines — build the valuation case analytically, not just state conclusions: "
        "(1) Where Z47'47 trades vs Nifty 50 right now on P/E (or P/B for the NBFC cohort) and "
        "EV/EBITDA — cite the actual numbers for both indices, and state whether the premium has "
        "expanded or compressed over the rolling 30-day period. "
        "(2) The case FOR the premium: earnings growth differential between Z47'47 and Nifty, "
        "business-mix advantages (tech-forward, asset-light, high gross-margin SaaS vs old-economy "
        "Nifty), structural tailwinds (TAM expansion, formalization, digital adoption rate) — "
        "anchored to specific data points, not assertions. "
        "(3) The case AGAINST: where the multiple is stretched vs 3-year history or global comps; "
        "which sub-segments within Z47'47 (e.g., loss-making consumer tech, pre-profit NBFCs) are "
        "at peak multiples; what consensus is over-extrapolating in the growth assumption. "
        "(4) The non-obvious insight: what is underpriced or overpriced within Z47'47 that the "
        "headline index P/E conceals — e.g., cross-sector dispersion, quality differences in the "
        "earnings mix (real margin expansion vs denominator effect), or a re-rating catalyst the "
        "market hasn't priced. "
        "(5) Net read: risk-reward at current levels — constructive/cautious/mixed — with the one "
        "variable that would sharply change the premium direction. "
        "Banned phrases: 'strong performance', 'healthy growth', 'robust quarter', "
        "'well-positioned', 'execution remains key', 'positive momentum'. "
        "No buy/sell/hold. No markdown. No preamble."
    )
    return _ai_takeaway(system, prompt, max_tokens=1500)


# ── Sector takeaway v2 ────────────────────────────────────────────────────────
# Sector-specific KPI guidance injected into each sector prompt
_SECTOR_KPI_MAP = {
    "Consumer / Consumer Tech": (
        "GMV, take-rate, contribution margin, adj-EBITDA margin, monthly transacting users (MTU), "
        "AOV, dark-store or kitchen count, cohort retention, CAC payback."
    ),
    "Fintech / Financial Services": (
        "AUM/disbursement growth, NIM, GNPA/NNPA bps, credit cost, opex-to-AUM, CIR, RoA, "
        "capital adequacy, secured-vs-unsecured mix; for brokers: active clients, ADTO, "
        "F&O share, blended yield; for insurance: NBM, renewal rate."
    ),
    "SaaS / AI": (
        "ARR growth, net dollar retention (NDR), gross margin, Rule of 40 score, "
        "customer count, CAC payback period, churn."
    ),
    "EdTech": (
        "Paid user growth, ARPU, cohort economics, gross margin, operating leverage, "
        "blended subscription vs one-time revenue mix."
    ),
    "HealthTech / Diagnostics": (
        "Same-clinic/same-lab revenue growth, prescription volume, EBITDA margin, "
        "B2C vs B2B revenue split, test portfolio mix."
    ),
    "Gaming / Media": (
        "Segment revenue mix (mobile/PC/esports), organic vs inorganic growth, "
        "EBITDA margin, paying-user count, ARPU, churn."
    ),
    "Logistics / Mobility": (
        "GTV, shipment volume, revenue-per-shipment, contribution margin, "
        "unit economics, utilisation rate, B2C vs B2B mix."
    ),
}

@st.cache_data(ttl=604800, show_spinner=False)
def get_sector_takeaway_v2(sector: str, top_movers_str: str,
                            monday_key: str = "") -> str | None:
    """5-6 line analyst-quality sector note. Monday-keyed rolling-30-day window, cached 1 week."""
    _mk, _sl, _el, _sd, _ed = _monthly_window()
    kpi_hint = _SECTOR_KPI_MAP.get(sector, "Use the most relevant financial and operating KPIs for this sector.")
    system = (
        f"You are a sell-side equity research analyst writing a monthly sector note for the "
        f"'{sector}' cohort within Z47'47 — the index of 47 Indian new-age tech and financial-services companies. "
        "Write in tight, professional English. No markdown — plain prose only."
    )
    prompt = (
        _NO_PREAMBLE
        + f"Analyze the rolling 30-day period from {_sd} to {_ed}. "
        f"Z47'47 sector: {sector}. 30-day top movers: {top_movers_str}. "
        f"Key sector KPIs to reference where available: {kpi_hint} "
        "Search for the latest news, results, or regulatory developments in this sector. "
        "Write exactly 5-6 lines: "
        "(1) One-line verdict on the sector for the rolling 30-day period — what the performance actually signals, "
        "not a recap of the movers list. "
        "(2-3) What is driving the dispersion between winners and laggards — cite specific names and % moves "
        "where relevant; do not just list them, interpret WHY the top performer outperformed (quality of earnings? "
        "re-rating catalyst? regulatory tailwind?). Include at least 2 of: consensus mispricing, "
        "structural vs cyclical distinction, regulatory or macro read-through, what the market is underweighting "
        "in this sector's risk or opportunity profile. "
        "(4) Structural vs noise: is this performance a permanent re-rating or mean-reversion from an extreme? "
        "What is the earnings-quality story behind the sector's 30-day move? "
        "(5) Read-through: what does this sector's print signal for adjacent sectors, supply-chain, "
        "or the upcoming IPO pipeline in the Z47'47 universe? "
        "(6) Net read: constructive/cautious/mixed — one line with the one variable that would change the view. "
        "Banned phrases: 'strong performance', 'healthy growth', 'robust quarter', 'positive momentum', "
        "'broadly stable', 'well-positioned', 'execution remains key'. "
        "No buy/sell/hold. No markdown. No preamble."
    )
    return _ai_takeaway(system, prompt, max_tokens=1500)


# ── Recent Results — sell-side quarterly summary ──────────────────────────────
@st.cache_data(ttl=604800, show_spinner=False)
def get_recent_results(company_name: str, ticker: str, sector: str) -> str | None:
    """Sell-side quality 5-6 line quarterly results note. Cached 7 days + disk cache."""
    # ── Disk cache keyed only by ticker (7-day mtime TTL, survives restarts) ──
    _dc_key = f"rr_{ticker.replace('.', '_').replace('=', '_')}"
    _rr_cached = _dcache_get(_dc_key, ttl_secs=604800)
    if _rr_cached is not None:
        print(f"[PERF] get_recent_results({company_name}): disk cache hit")
        return _rr_cached

    # Sector-aware KPI guidance injected into the prompt
    _KPI_GUIDE = {
        "Fintech / Financial Services": (
            "For lenders/NBFCs: AUM growth, disbursement run-rate, NIM, GNPA/NNPA bps, "
            "credit cost (bps), opex-to-AUM, CIR, RoA, capital adequacy, "
            "secured-vs-unsecured mix. For brokers: active clients, ADTO, F&O share, "
            "blended yield, cost-to-income, ARPU. For insurance: premium accreted, "
            "new business margin, renewal rate, insurance EBITDA."
        ),
        "Consumer / Consumer Tech": (
            "GMV growth, take-rate, contribution margin, adj. EBITDA margin, "
            "monthly transacting users (MTU), average order value (AOV), "
            "dark store or kitchen count, cohort retention."
        ),
        "B2B": (
            "Revenue growth, order/shipment volume, capacity utilisation, "
            "service-level metrics, EBITDA margin, working capital days."
        ),
        "SaaS / AI": (
            "ARR growth, net dollar retention (NDR), gross margin, "
            "Rule of 40 score, customer count, CAC payback period."
        ),
    }
    kpi_hint = _KPI_GUIDE.get(sector, "Use the most relevant financial and operating KPIs for this company type.")

    system = (
        "You are a sell-side equity research analyst writing a quarterly results note for a Z47'47 constituent. "
        "Write in tight, professional English. Cite actual numbers, dates, and entity names. "
        "No markdown — plain prose only."
    )
    prompt = (
        _NO_PREAMBLE
        + f"Quarter: most recent for {company_name} (ticker: {ticker}, sector: {sector}). "
        f"Sector KPIs to reference: {kpi_hint} "
        "Search BSE/NSE corporate filings, investor relations page, screener.in, trendlyne.com, "
        "moneycontrol.com for the most recent quarterly results. "
        "Write exactly 5-6 lines: "
        "(1) Headline — what the quarter meant strategically, not just a revenue number. A verdict. "
        "(2-3) The 2-3 most important numbers with YoY/QoQ context PLUS what they mean analytically: "
        "is the beat/miss real or optical (denominator effect, one-off, mix shift)? "
        "What is the quality-of-earnings story the headline number doesn't show? "
        "What is the under-discussed line item or footnote that matters most? "
        "(4) Structural vs noise: what is genuinely improving in the business model vs what is one-quarter? "
        "(5) Watch-item: the specific metric or event that would change the view next quarter. "
        "(6) Net read: constructive/cautious/mixed — one sentence with clear rationale. "
        "Banned phrases: 'strong performance', 'healthy growth', 'robust quarter', 'positive momentum', "
        "'in line with expectations', 'broadly stable', 'well-positioned', 'execution remains key'. "
        "No buy/sell/hold. No markdown. No preamble."
    )
    _rr_result = _ai_takeaway(system, prompt, max_tokens=1500)
    if _rr_result:
        _dcache_set(_dc_key, _rr_result)
    return _rr_result


# ── Company takeaway v2 ────────────────────────────────────────────────────────
@st.cache_data(ttl=604800, show_spinner=False)
def get_company_takeaway_v2(company_name: str, ticker: str) -> str | None:
    """Structured 5-6 sentence analyst note for a Z47 company. Cached 1 week + disk cache."""
    from datetime import date
    week = date.today().isocalendar()[:2]

    # ── Disk cache (survives container restarts) ──────────────────────────────
    _dc_key = f"co_tk_{ticker.replace('.', '_').replace('=', '_')}_{week[0]}_{week[1]}"
    _co_cached = _dcache_get(_dc_key, ttl_secs=604800)
    if _co_cached is not None:
        print(f"[PERF] get_company_takeaway_v2({company_name}): disk cache hit")
        return _co_cached

    system = (
        "You are a sell-side equity research analyst writing a company note for a Z47'47 constituent. "
        "Write in tight, professional English. Cite actual numbers, dates, and entity names. "
        "No markdown — plain prose only."
    )
    prompt = (
        _NO_PREAMBLE
        + f"Week {week[1]}, {week[0]}. Company: {company_name} (ticker: {ticker}). "
        "Write exactly 5-6 lines: "
        "(1) Headline: the ONE thing that matters about this company's current situation — a verdict, not a recap. "
        "(2-4) Mix of data points AND at least 2 analyst insights: "
        "variant perception (what consensus has wrong), "
        "quality-of-earnings (is the recent performance real or optical — denominator effects, one-offs, mix shifts), "
        "structural vs cyclical (permanent re-rate vs mean-reversion), "
        "read-through to peers or adjacent Z47'47 names, "
        "management credibility (guidance track record, tone shift, capital allocation signal), "
        "what the market is missing (under-discussed line item, footnote that matters), "
        "risk-reward asymmetry at current price (what's priced in vs what isn't). "
        "Every number must be followed by what it means, not just stated. "
        "(5) Watch-item: the specific event or data point that would change the analytical view. "
        "(6) Net read: constructive/cautious/mixed — one sentence with clear rationale. "
        "Banned phrases: 'strong performance', 'healthy growth', 'robust quarter', 'positive momentum', "
        "'in line with expectations', 'broadly stable', 'well-positioned', 'execution remains key'. "
        "No buy/sell/hold. Use web search for latest data. No markdown. No preamble."
    )
    _co_result = _ai_takeaway(system, prompt, max_tokens=1500)
    if _co_result:
        _dcache_set(_dc_key, _co_result)
    return _co_result


# ── Valuation multiples line chart with JSON persistence ──────────────────────
import json as _json

def _get_multiples_json_path() -> str:
    """Return the JSON file path — Streamlit Cloud mount or local fallback."""
    cloud = "/mount/src/z47-dashboard/data/multiples_history.json"
    if os.path.exists("/mount/src/z47-dashboard"):
        return cloud
    return os.path.join(os.path.dirname(__file__), "data", "multiples_history.json")


def load_multiples_history() -> list:
    """Load stored daily valuation-multiples snapshots from JSON."""
    path = _get_multiples_json_path()
    try:
        if os.path.exists(path):
            with open(path, "r") as _f:
                return _json.load(_f)
    except Exception as _e:
        print(f"[Multiples history] load error: {_e}")
    return []


def save_multiples_snapshot(metrics: dict) -> None:
    """Append today's valuation snapshot to the JSON store (no-op if already saved today)."""
    from datetime import date as _date
    path = _get_multiples_json_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        history = load_multiples_history()
        today_str = _date.today().isoformat()
        if history and history[-1].get("date") == today_str:
            return   # already saved today
        z47    = metrics.get("z47",    {})
        nifty  = metrics.get("nifty",  {})
        sensex = metrics.get("sensex", {})
        snapshot = {
            "date":   today_str,
            "z47":    {"ev_revenue": z47.get("ev_revenue"),    "ev_ebitda": z47.get("ev_ebitda"),    "pe": z47.get("pe")},
            "nifty":  {"ev_revenue": nifty.get("ev_revenue"),  "ev_ebitda": nifty.get("ev_ebitda"),  "pe": nifty.get("pe")},
            "sensex": {"ev_revenue": sensex.get("ev_revenue"), "ev_ebitda": sensex.get("ev_ebitda"), "pe": sensex.get("pe")},
        }
        history.append(snapshot)
        with open(path, "w") as _f:
            _json.dump(history, _f, indent=2)
    except Exception as _e:
        print(f"[Multiples history] save error: {_e}")


def render_multiples_line_chart(metrics: dict):
    """Trend line chart of Z47/Nifty/Sensex valuation multiples over time."""
    # Persist today's snapshot
    try:
        save_multiples_snapshot(metrics)
    except Exception as _se:
        print(f"[Multiples] snapshot save: {_se}")

    history = load_multiples_history()

    if not history or len(history) < 2:
        st.info(
            "📈 Building valuation history — trend lines will appear after a few daily snapshots. "
            "Today's multiples are shown in the Index Fundamentals table above."
        )
        return

    # Build DataFrame
    rows = []
    for snap in history:
        rows.append({
            "date":          snap.get("date"),
            "z47_ev_rev":    (snap.get("z47") or {}).get("ev_revenue"),
            "z47_ev_ebitda": (snap.get("z47") or {}).get("ev_ebitda"),
            "z47_pe":        (snap.get("z47") or {}).get("pe"),
            "nifty_ev_rev":    (snap.get("nifty") or {}).get("ev_revenue"),
            "nifty_ev_ebitda": (snap.get("nifty") or {}).get("ev_ebitda"),
            "nifty_pe":        (snap.get("nifty") or {}).get("pe"),
            "sensex_ev_rev":    (snap.get("sensex") or {}).get("ev_revenue"),
            "sensex_ev_ebitda": (snap.get("sensex") or {}).get("ev_ebitda"),
            "sensex_pe":        (snap.get("sensex") or {}).get("pe"),
        })
    hdf = pd.DataFrame(rows)
    hdf["date"] = pd.to_datetime(hdf["date"])
    hdf = hdf.sort_values("date").reset_index(drop=True)

    # Period + metric selectors on the same row
    col_p, col_m, _ = st.columns([3, 3, 4])
    with col_p:
        period = st.radio(
            "Period", ["1W", "1M", "3M", "6M", "1Y", "All"],
            horizontal=True, label_visibility="collapsed", key="multiples_period"
        )
    with col_m:
        metric = st.radio(
            "Metric", ["EV/Revenue", "EV/EBITDA", "P/E"],
            horizontal=True, label_visibility="collapsed", key="multiples_metric"
        )

    # Slice to selected period
    if period != "All":
        period_days = {"1W": 7, "1M": 30, "3M": 90, "6M": 180, "1Y": 365}[period]
        cutoff = hdf["date"].iloc[-1] - pd.Timedelta(days=period_days)
        hdf = hdf[hdf["date"] >= cutoff].reset_index(drop=True)

    if hdf.empty or len(hdf) < 1:
        st.info("Not enough history for this period yet — check back soon.")
        return

    metric_col_map = {
        "EV/Revenue": ("ev_rev",    "EV / Revenue (x)"),
        "EV/EBITDA":  ("ev_ebitda", "EV / EBITDA (x)"),
        "P/E":        ("pe",        "P/E Ratio (x)"),
    }
    col_suffix, y_label = metric_col_map[metric]

    fig = go.Figure()
    for index_name, prefix, color in [
        ("Z47'47",     "z47",    C_Z47),
        ("Nifty 50",   "nifty",  C_NIFTY),
        ("BSE Sensex", "sensex", C_SENSEX),
    ]:
        col = f"{prefix}_{col_suffix}"
        series = hdf[["date", col]].dropna(subset=[col])
        if not series.empty:
            fig.add_trace(go.Scatter(
                x=series["date"], y=series[col],
                name=index_name, mode="lines+markers",
                line=dict(color=color, width=2),
                marker=dict(size=5),
                hovertemplate=f"{index_name}: %{{y:.1f}}x<extra></extra>",
            ))

    fig.update_layout(
        paper_bgcolor=CARD_BG,
        plot_bgcolor=CARD_BG,
        height=320,
        margin=dict(l=0, r=0, t=20, b=0),
        legend=dict(orientation="h", y=1.12, font=dict(size=12),
                    bgcolor="rgba(0,0,0,0)"),
        yaxis=dict(title=y_label, showgrid=True, gridcolor=BORDER,
                   zeroline=False, tickfont=dict(size=11), color="#a38060"),
        xaxis=dict(showgrid=False, tickfont=dict(size=11), color="#a38060"),
        hovermode="x unified",
        font=dict(family="Inter, sans-serif"),
    )
    st.markdown('<div class="card-wrap" style="padding:16px">', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    n_snap = len(history)
    st.caption(f"Valuation multiples refreshed daily · {n_snap} snapshot{'s' if n_snap != 1 else ''} stored")


def render_sector_breakdown_with_takeaways(returns_1m: dict) -> None:
    """Per-sector performance mini-table (top 5 by 1M return) + AI takeaway."""
    name_map = {c["ticker"]: c["name"] for c in COMPANIES}

    # Group companies by sector (preserving COMPANIES order)
    sectors: dict[str, list] = {}
    for c in COMPANIES:
        sectors.setdefault(c["sector"], []).append(c)

    for sector_name, cos in sectors.items():
        sector_returns = []
        for c in cos:
            ret = returns_1m.get(c["ticker"])
            sector_returns.append((c["ticker"], c["name"], ret))

        # Sort descending by return (None → last)
        sector_returns.sort(key=lambda x: (x[2] is None, -(x[2] or 0)))

        valid_rets = [r for _, _, r in sector_returns if r is not None]
        avg_ret = sum(valid_rets) / len(valid_rets) if valid_rets else None

        bg       = SECTOR_COLORS.get(sector_name, "#f3ede4")
        badge_c  = SECTOR_BADGE_COLORS.get(sector_name, "#5a3e28")
        avg_str  = f"{avg_ret:+.1f}%" if avg_ret is not None else "—"
        avg_color = "#16a34a" if (avg_ret or 0) >= 0 else "#dc2626"

        # Build movers string for prompt
        movers_str = ", ".join(
            f"{name} {ret:+.1f}%" for _, name, ret in sector_returns[:5] if ret is not None
        ) or "data unavailable"

        # Section header badge
        st.markdown(
            f"<div style='background:{bg};border-radius:10px;padding:10px 16px;"
            f"margin-bottom:8px;display:flex;justify-content:space-between;align-items:center'>"
            f"<span style='font-weight:700;color:{badge_c};font-size:14px'>{sector_name}</span>"
            f"<span style='font-size:12px;color:{avg_color};font-weight:600'>"
            f"Avg 1M: {avg_str} &nbsp;·&nbsp; {len(cos)} companies</span></div>",
            unsafe_allow_html=True,
        )

        # Top-5 mini-table
        rows_html = ""
        for ticker, co_name, ret in sector_returns[:5]:
            arrow = "▲" if (ret or 0) >= 0 else "▼"
            color = "#16a34a" if (ret or 0) >= 0 else "#dc2626"
            ret_str = f"{arrow} {abs(ret):.1f}%" if ret is not None else "—"
            rows_html += (
                f"<tr style='border-top:1px solid {BORDER}'>"
                f"<td style='padding:7px 12px;color:#1a0f00;font-size:12px'>{co_name}</td>"
                f"<td style='padding:7px 12px;text-align:right;color:{color};"
                f"font-weight:700;font-size:12px'>{ret_str}</td></tr>"
            )

        st.markdown(
            f"<div class='card-wrap' style='padding:0;margin-bottom:6px'>"
            f"<div style='padding:6px 12px;color:#8b6d4a;font-size:11px;font-weight:600;"
            f"border-bottom:1px solid {BORDER}'>TOP 5 BY 1M RETURN</div>"
            f"<table style='width:100%;border-collapse:collapse'>"
            f"<tbody>{rows_html}</tbody></table></div>",
            unsafe_allow_html=True,
        )

        # Sector takeaway — hardcoded dict first (instant, no API); API fallback if not found
        try:
            _mk, _sl, _el, _sd, _ed = _monthly_window()
            _hardcoded_sec = HARDCODED_SECTOR_TAKEAWAYS.get(sector_name)
            if _hardcoded_sec:
                # Instant render — no API call
                render_takeaway_box(
                    _hardcoded_sec["text"],
                    title=f"{sector_name} — Monthly Takeaway · {_hardcoded_sec['window']}",
                    icon="\U0001f4ca",
                )
            else:
                # Sector not in hardcoded dict — try API
                _sec_tk = get_sector_takeaway_v2(sector_name, movers_str, monday_key=_mk)
                if _sec_tk:
                    render_takeaway_box(
                        _sec_tk,
                        title=f"{sector_name} — Monthly Takeaway · {_sl} to {_el}",
                        icon="\U0001f4ca",
                    )
                else:
                    # Factual fallback — NEVER show bare "generating"
                    _cos_with_data = [c for c in cos if c["ticker"] in returns_1m]
                    _rets = [returns_1m[c["ticker"]] for c in _cos_with_data]
                    _avg  = round(sum(_rets) / len(_rets), 1) if _rets else None
                    _top  = sorted(_cos_with_data,
                                   key=lambda c: returns_1m.get(c["ticker"], -999),
                                   reverse=True)
                    _top_str = (
                        f"Top performer: {_top[0]['name']} "
                        f"({returns_1m[_top[0]['ticker']]:+.1f}%)"
                        if _top else ""
                    )
                    _avg_str = f"Avg 1M: {_avg:+.1f}%" if _avg is not None else ""
                    _fallback = (
                        f"{sector_name}: {_avg_str}, {len(cos)} companies. "
                        f"{_top_str}."
                    ).strip(". ")
                    render_takeaway_box(
                        _fallback,
                        title=f"{sector_name} — Sector Snapshot · {_sl} to {_el}",
                        icon="\U0001f4ca",
                    )
        except Exception as _se:
            print(f"[Sector takeaway v2] {sector_name}: {_se}")

        st.markdown("<div style='margin-bottom:24px'></div>", unsafe_allow_html=True)


def _fetch_constituent_fundamentals(symbols: list, fin_syms: set) -> list:
    """Parallel yfinance fetch for a list of symbols. Returns list of dicts."""

    def _one(sym):
        try:
            ticker_obj = yf.Ticker(sym)
            # Try .info first; if it returns a near-empty dict fall back to fast_info
            try:
                info = ticker_obj.info or {}
                if len(info) < 8:
                    print(f"[Fund fetch] {sym}: info sparse ({len(info)} keys), trying fast_info")
                    fi = ticker_obj.fast_info
                    fi_mcap = (getattr(fi, "market_cap", None)
                               or getattr(fi, "marketCap", None))
                    if fi_mcap:
                        info["marketCap"] = fi_mcap
            except Exception as _ie:
                print(f"[Fund fetch] {sym}: info() raised {type(_ie).__name__}: {_ie}")
                info = {}
                try:
                    fi = ticker_obj.fast_info
                    fi_mcap = (getattr(fi, "market_cap", None)
                               or getattr(fi, "marketCap", None))
                    if fi_mcap:
                        info["marketCap"] = fi_mcap
                except Exception:
                    pass

            is_fin = sym in fin_syms
            mcap   = info.get("marketCap")        or 0
            debt   = info.get("totalDebt")         or 0
            cash   = info.get("totalCash")         or 0
            minint = info.get("minorityInterest")   or 0
            ev     = mcap + debt - cash + minint
            ebitda = info.get("ebitda")            or 0
            rg     = info.get("revenueGrowth")
            em     = info.get("ebitdaMargins")
            pe     = info.get("trailingPE")
            pb     = info.get("priceToBook")

            # ── EV/Revenue ───────────────────────────────────────────────────
            ev_rev       = None
            ev_rev_proxy = False

            if is_fin:
                # Primary: P/S ratio from yfinance = MCap/Revenue directly
                ps = info.get("priceToSalesTrailing12Months")
                if ps and 0 < float(ps) < 150:
                    ev_rev       = float(ps)
                    ev_rev_proxy = True
                else:
                    # Fallback: derive revenue from totalRevenue or grossProfits
                    rev = (info.get("totalRevenue") or
                           info.get("grossProfits")  or
                           info.get("operatingRevenue") or 0)
                    if mcap > 0 and rev > 0:
                        ev_rev       = mcap / rev
                        ev_rev_proxy = True
            else:
                rev = info.get("totalRevenue") or 0
                if ev > 0 and rev > 0:
                    ev_rev       = ev / rev
                    ev_rev_proxy = False

            # Filter extreme values (data error guard)
            if ev_rev is not None and (ev_rev <= 0 or ev_rev > 150):
                ev_rev = None

            # ── EV/EBITDA — still exclude financials ─────────────────────────
            ev_ebit = None
            if not is_fin and ev > 0 and ebitda > 0:
                ev_ebit = ev / ebitda
                if ev_ebit <= 0 or ev_ebit > 200:
                    ev_ebit = None

            return {
                "symbol":           sym,
                "is_financial":     is_fin,
                "ev_revenue":       ev_rev,
                "ev_revenue_proxy": ev_rev_proxy,
                "ev_ebitda":        ev_ebit,
                "pe":               pe,
                "pb":               pb,
                "rev_growth":       rg * 100 if rg is not None else None,
                "ebitda_margin":    em * 100 if (not is_fin and em is not None) else None,
            }
        except Exception as _e:
            print(f"[Fund fetch] {sym}: {_e}")
            return {"symbol": sym, "is_financial": sym in fin_syms, "ev_revenue_proxy": False}

    results = []
    with ThreadPoolExecutor(max_workers=12) as _ex:
        _futs = {_ex.submit(_one, s): s for s in symbols}
        for _f in as_completed(_futs, timeout=50):
            try:
                results.append(_f.result())
            except Exception:
                pass
    return results


def _compute_index_metrics(data: list, index_name: str, n_declared: int) -> dict:
    """Aggregate constituent data into index-level metrics."""

    def _ok(v, lo, hi):
        try:
            f = float(v)
            return lo < f < hi
        except (TypeError, ValueError):
            return False

    def _vals(key, excl_fin=False, lo=None, hi=None):
        out = []
        for d in data:
            if excl_fin and d.get("is_financial"):
                continue
            v = d.get(key)
            if v is None:
                continue
            if lo is not None and not _ok(v, lo, hi):
                continue
            out.append(float(v))
        return out

    def _median(vals):
        if not vals:
            return None
        s = sorted(vals); n = len(s); mid = n // 2
        return round(s[mid] if n % 2 == 1 else (s[mid - 1] + s[mid]) / 2, 1)

    def _mean(vals):
        return round(sum(vals) / len(vals), 1) if vals else None

    n_non_fin = sum(1 for d in data if not d.get("is_financial"))

    # Debug: log symbols still missing EV/Revenue
    _missing_evr = [d["symbol"] for d in data if d.get("ev_revenue") is None]
    if _missing_evr:
        print(f"[Fund] {index_name} missing EV/Revenue: {_missing_evr}")

    # EV/Revenue: ALL companies — financials use P/S proxy (excl_fin=False)
    ev_rev_v  = _vals("ev_revenue",                    lo=0,    hi=100)
    ev_ebit_v = _vals("ev_ebitda",     excl_fin=True,  lo=0,    hi=200)
    pe_v      = _vals("pe",                            lo=0,    hi=500)
    pb_v      = _vals("pb",                            lo=0,    hi=100)
    rg_v      = _vals("rev_growth",                    lo=-50,  hi=200)
    em_v      = _vals("ebitda_margin", excl_fin=True,  lo=-100, hi=80)

    # Count proxy vs standard in EV/Revenue
    n_ev_rev_proxy = sum(
        1 for d in data
        if d.get("ev_revenue_proxy") and d.get("ev_revenue") is not None
        and 0 < d["ev_revenue"] < 100
    )
    n_ev_rev_std = sum(
        1 for d in data
        if not d.get("ev_revenue_proxy") and d.get("ev_revenue") is not None
        and 0 < d["ev_revenue"] < 100
    )

    return {
        "index_name":      index_name,
        "n_total":         n_declared,
        "n_fetched":       len(data),
        "n_non_financial": n_non_fin,
        "ev_revenue":      _median(ev_rev_v),
        "n_ev_revenue":    len(ev_rev_v),
        "n_ev_rev_proxy":  n_ev_rev_proxy,
        "n_ev_rev_std":    n_ev_rev_std,
        "ev_ebitda":       _median(ev_ebit_v),
        "n_ev_ebitda":     len(ev_ebit_v),
        "pe":              _median(pe_v),
        "n_pe":            len(pe_v),
        "pe_source":       "computed",
        "pb":              _median(pb_v),
        "n_pb":            len(pb_v),
        "rev_growth":      _mean(rg_v),
        "n_rev_growth":    len(rg_v),
        "ebitda_margin":   _mean(em_v),
        "n_ebitda_margin": len(em_v),
    }


@st.cache_data(ttl=3600, show_spinner=False)
def _get_nifty50_official_pe() -> dict:
    """Try to fetch official Nifty 50 P/E from NSE API."""
    try:
        _s = requests.Session()
        _h = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.nseindia.com/",
              "Accept": "application/json, */*"}
        _s.get("https://www.nseindia.com", headers=_h, timeout=5)
        r = _s.get(
            "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%2050",
            headers=_h, timeout=8,
        )
        if r.status_code == 200:
            meta = r.json().get("metadata", {})
            pe = meta.get("pe"); pb = meta.get("pb")
            if pe:
                return {"pe": float(pe), "pb": float(pb) if pb else None,
                        "source": "NSE official"}
    except Exception as _e:
        print(f"[NSE PE] {_e}")
    return {"pe": None, "pb": None, "source": "unavailable"}


@st.cache_data(ttl=3600, show_spinner=False)
def get_all_index_fundamentals() -> dict:
    """
    Compute fundamentals for Z47, Nifty 50, and BSE Sensex.
    Parallel yfinance fetch for all ~130 constituents; cached 1 hour.
    """
    print("[Fund] Computing index fundamentals for Z47 + Nifty50 + Sensex…")
    Z47_SYMS = [yf_ticker(c) for c in COMPANIES]

    # Parallel fetch all three constituent lists at once
    all_syms = list(dict.fromkeys(Z47_SYMS + NIFTY50_SYMBOLS + SENSEX_SYMBOLS))
    all_data = _fetch_constituent_fundamentals(all_syms, _FINANCIAL_SYMS | _Z47_FINANCIAL_SYMS)
    data_map = {d["symbol"]: d for d in all_data}

    z47_data    = [data_map[s] for s in Z47_SYMS         if s in data_map]
    nifty_data  = [data_map[s] for s in NIFTY50_SYMBOLS  if s in data_map]
    sensex_data = [data_map[s] for s in SENSEX_SYMBOLS   if s in data_map]

    # For Z47, use the Z47-specific financial exclusion set
    for d in z47_data:
        d["is_financial"] = d["symbol"] in _Z47_FINANCIAL_SYMS

    z47_m    = _compute_index_metrics(z47_data,    "Z47",       len(Z47_SYMS))
    nifty_m  = _compute_index_metrics(nifty_data,  "Nifty 50",  len(NIFTY50_SYMBOLS))
    sensex_m = _compute_index_metrics(sensex_data, "BSE Sensex", len(SENSEX_SYMBOLS))

    # Override Nifty P/E with official NSE value where available
    official = _get_nifty50_official_pe()
    if official.get("pe"):
        nifty_m["pe"]        = round(official["pe"], 1)
        nifty_m["pe_source"] = official["source"]
        if official.get("pb"):
            nifty_m["pb"] = round(official["pb"], 1)

    as_of = pd.Timestamp.now().strftime("%d %b %Y %H:%M")
    result = {
        "z47":    z47_m,
        "nifty":  nifty_m,
        "sensex": sensex_m,
        "as_of":  as_of,
    }

    # ── Hardcoded fallback when yfinance coverage is too low ─────────────────
    # Threshold: < 30% of constituents returned valid P/E → data is broken
    _MIN_COV = 0.30
    for _key, _total_field in [("z47", 47), ("nifty", 50), ("sensex", 30)]:
        _idx = result[_key]
        _n_pe = _idx.get("n_pe") or 0
        if _n_pe < int(_total_field * _MIN_COV):
            print(
                f"[Fund] {_key} coverage too low ({_n_pe}/{_total_field} P/E) — "
                f"patching with hardcoded reference values"
            )
            _fb = dict(HARDCODED_FUNDAMENTALS.get(_key, {}))
            _fb["as_of"] = as_of   # keep the live timestamp
            result[_key] = _fb

    return result


@st.cache_data(ttl=300, show_spinner=False)   # same cadence as prices
def fetch_company_live(yf_tk: str) -> dict:
    """Key stats, analyst targets, recommendations, earnings dates — refreshed with prices."""
    result = {}
    try:
        t = yf.Ticker(yf_tk)

        # ── info / analyst key stats ────────────────────────────────────
        try:
            info = t.info or {}
            # If analyst data missing and this is an NSE stock, try .BO
            if not info.get("targetMeanPrice") and yf_tk.endswith(".NS"):
                bo_tk = yf_tk.replace(".NS", ".BO")
                try:
                    bo_info = yf.Ticker(bo_tk).info or {}
                    info = {**info, **{k: v for k, v in bo_info.items() if v and not info.get(k)}}
                except Exception:
                    pass
            result["info"] = info
        except Exception:
            result["info"] = {}

        # ── Earnings history (no lxml required; has epsActual + epsEstimate) ──
        try:
            eh = t.earnings_history
            result["earnings_history"] = eh if eh is not None else pd.DataFrame()
        except Exception:
            result["earnings_history"] = pd.DataFrame()

        # ── Recommendations — summary preferred, raw as fallback ────────
        recs_loaded = False
        try:
            rs = t.recommendations_summary
            if rs is not None and not rs.empty:
                result["recommendations"] = rs
                recs_loaded = True
        except Exception:
            pass
        if not recs_loaded:
            try:
                result["recommendations"] = t.recommendations
            except Exception:
                result["recommendations"] = pd.DataFrame()

        # ── Price targets — dedicated endpoint, fallback to info ────────
        targets_loaded = False
        try:
            apt = t.analyst_price_targets
            if apt and apt.get("mean"):
                result["price_targets"] = apt
                targets_loaded = True
        except Exception:
            pass
        if not targets_loaded:
            info = result.get("info", {})
            result["price_targets"] = {
                "low":     info.get("targetLowPrice"),
                "high":    info.get("targetHighPrice"),
                "mean":    info.get("targetMeanPrice"),
                "median":  info.get("targetMedianPrice"),
                "current": info.get("currentPrice") or info.get("previousClose"),
            }
        return result
    except Exception:
        return {}


def fetch_company_details(yf_tk: str) -> dict:
    """Merge live + financial data for a company."""
    return {**fetch_company_financials(yf_tk), **fetch_company_live(yf_tk)}


# ── Company detail helpers ────────────────────────────────────────────────────

def _fmt_fin(v, sym="₹"):
    if v is None: return "—"
    try:
        v = float(v)
        if pd.isna(v): return "—"
    except Exception:
        return "—"
    neg = "-" if v < 0 else ""
    av  = abs(v)
    if av >= 1e12: return f"{neg}{sym}{av/1e12:.2f}T"
    if av >= 1e9:  return f"{neg}{sym}{av/1e9:.2f}B"
    if av >= 1e6:  return f"{neg}{sym}{av/1e6:.2f}M"
    if av >= 1e3:  return f"{neg}{sym}{av/1e3:.0f}K"
    return f"{neg}{sym}{av:.2f}"


def _fin_table_html(df, sym, row_specs):
    """Render a yfinance financials DataFrame as styled HTML.
    row_specs: [(display_name, [candidate_yf_keys]), ...]
    """
    if df is None or df.empty:
        return f"<p style='color:#a38060;padding:16px'>Data not available for this company.</p>"

    df = df.iloc[:, :4]   # max 4 periods
    col_dates = []
    for c in df.columns:
        try:    col_dates.append(pd.Timestamp(c).strftime("%b '%y"))
        except: col_dates.append(str(c))

    th  = (f"padding:9px 12px;color:#8b6d4a;font-weight:600;font-size:12px;"
           f"text-align:right;background:{BG_ALT};white-space:nowrap")
    thl = th.replace("text-align:right", "text-align:left")
    html = (f"<div style='overflow-x:auto'>"
            f"<table style='width:100%;border-collapse:collapse;font-size:12px'>"
            f"<thead><tr><th style='{thl}'>Breakdown</th>")
    for d in col_dates:
        html += f"<th style='{th}'>{d}</th>"
    html += "</tr></thead><tbody>"

    for display_name, candidates in row_specs:
        matched = None
        for cand in candidates:
            for idx in df.index:
                if cand.lower() == str(idx).lower():
                    matched = idx; break
            if matched: break

        html += f"<tr style='border-top:1px solid {BORDER}'>"
        bold = "font-weight:600" if display_name in ("Total Revenue","Gross Profit","Net Income","Operating Income") else ""
        html += (f"<td style='padding:8px 12px;color:#1a0f00;{bold}'>{display_name}</td>")
        for col in df.columns:
            if matched is not None:
                try:
                    val = float(df.loc[matched, col])
                    color = "#dc2626" if val < 0 else "#1a0f00"
                    html += f"<td style='padding:8px 12px;text-align:right;color:{color}'>{_fmt_fin(val,sym)}</td>"
                except Exception:
                    html += f"<td style='padding:8px 12px;text-align:right;color:#a38060'>—</td>"
            else:
                html += f"<td style='padding:8px 12px;text-align:right;color:#a38060'>—</td>"
        html += "</tr>"

    html += "</tbody></table></div>"
    return html


IS_ROWS = [
    ("Total Revenue",     ["Total Revenue", "Operating Revenue"]),
    ("Cost of Revenue",   ["Cost Of Revenue"]),
    ("Gross Profit",      ["Gross Profit"]),
    ("Operating Expense", ["Total Expenses", "Operating Expense"]),
    ("Operating Income",  ["EBIT", "Operating Income", "Total Operating Income As Reported"]),
    ("EBITDA",            ["EBITDA", "Normalized EBITDA"]),
    ("Pretax Income",     ["Pretax Income"]),
    ("Tax Provision",     ["Tax Provision"]),
    ("Net Income",        ["Net Income Common Stockholders", "Net Income"]),
    ("Basic EPS",         ["Basic EPS"]),
    ("Diluted EPS",       ["Diluted EPS"]),
]
BS_ROWS = [
    ("Total Assets",       ["Total Assets"]),
    ("Total Liabilities",  ["Total Liabilities Net Minority Interest", "Total Liabilities"]),
    ("Stockholders Equity",["Stockholders Equity", "Total Equity Gross Minority Interest"]),
    ("Cash & Equivalents", ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"]),
    ("Total Debt",         ["Total Debt"]),
    ("Net Debt",           ["Net Debt"]),
    ("Working Capital",    ["Working Capital"]),
]
CF_ROWS = [
    ("Operating Cash Flow",  ["Operating Cash Flow"]),
    ("Investing Cash Flow",  ["Investing Cash Flow"]),
    ("Financing Cash Flow",  ["Financing Cash Flow"]),
    ("Free Cash Flow",       ["Free Cash Flow"]),
    ("Capital Expenditure",  ["Capital Expenditure"]),
    ("Net Income",           ["Net Income From Continuing Operations", "Net Income"]),
]


def _render_news(news_list):
    from datetime import datetime, timezone
    if not news_list:
        st.markdown('<p style="color:#a38060;padding:12px">No recent news available.</p>',
                    unsafe_allow_html=True)
        return

    html = ""
    for n in news_list[:20]:
        ts = n.get("providerPublishTime", 0)
        try:
            dt = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%d %b %Y")
        except Exception:
            dt = ""
        pub   = n.get("publisher", "")
        title = n.get("title", "")
        link  = n.get("link", "#")
        html += (
            f"<div style='padding:12px 0;border-bottom:1px solid {BORDER}'>"
            f"<a href='{link}' target='_blank' style='color:#1a0f00;font-weight:600;"
            f"font-size:13px;text-decoration:none;line-height:1.4'>{title}</a>"
            f"<div style='color:#a38060;font-size:11px;margin-top:4px'>"
            f"{pub} &nbsp;·&nbsp; {dt}</div></div>"
        )

    st.markdown(f"<div class='card-wrap'>{html}</div>", unsafe_allow_html=True)


def _quarter_label(d) -> str:
    """Convert a date to e.g. 'Q1 '26' — %q not supported on Windows."""
    try:
        ts = pd.Timestamp(d)
        q  = (ts.month - 1) // 3 + 1
        return f"Q{q} '{ts.strftime('%y')}"
    except Exception:
        return str(d)[:7]


def _render_earnings_trends(details, sym):
    # earnings_history: columns epsActual, epsEstimate — no lxml required
    earn_df = details.get("earnings_history", pd.DataFrame())
    inc_q   = details.get("income_quarterly", pd.DataFrame())

    col_l, col_r = st.columns(2)

    # ── EPS: estimate vs actual ──────────────────────────────────────
    with col_l:
        st.markdown('<div style="font-weight:700;color:#1a0f00;margin-bottom:10px">Earnings Per Share</div>',
                    unsafe_allow_html=True)

        eps_plotted = False
        if earn_df is not None and not earn_df.empty:
            # earnings_history columns: epsActual, epsEstimate (index = quarter date)
            if "epsActual" in earn_df.columns:
                # Keep rows where we have at least an actual; sort chronologically
                df = earn_df.dropna(subset=["epsActual"]).copy()
                df = df.sort_index().tail(6)   # last 6 quarters max

                quarters = []
                for d in df.index:
                    quarters.append(_quarter_label(d))

                actuals   = df["epsActual"].tolist()
                estimates = df["epsEstimate"].tolist() if "epsEstimate" in df.columns else [None]*len(actuals)

                fig = go.Figure()

                # Plot estimates where available
                est_x = [q for q, e in zip(quarters, estimates) if e is not None and not pd.isna(e)]
                est_y = [e for e in estimates if e is not None and not pd.isna(e)]
                if est_x:
                    fig.add_trace(go.Scatter(
                        x=est_x, y=est_y, mode="markers",
                        marker=dict(size=14, color="white", line=dict(color="#8b6d4a", width=2)),
                        name="Estimate",
                    ))

                # Color actuals: green = beat estimate, red = missed, blue = no estimate
                colors = []
                for a, e in zip(actuals, estimates):
                    if e is None or pd.isna(e):
                        colors.append("#1d4ed8")
                    elif a >= e:
                        colors.append("#16a34a")
                    else:
                        colors.append("#dc2626")

                fig.add_trace(go.Scatter(
                    x=quarters, y=actuals, mode="markers",
                    marker=dict(size=14, color=colors),
                    name="Actual",
                ))

                # Beat/Miss annotations only where we have both
                for q, a, e in zip(quarters, actuals, estimates):
                    if e is not None and not pd.isna(e):
                        beat = a >= e
                        diff = round(a - e, 2)
                        fig.add_annotation(
                            x=q, y=a,
                            text=f"{'Beat' if beat else 'Missed'}<br>{'+' if diff>=0 else ''}{diff}",
                            showarrow=False, yshift=-28,
                            font=dict(size=10, color="#16a34a" if beat else "#dc2626"),
                        )

                fig.update_layout(
                    paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG, height=280,
                    margin=dict(l=0, r=0, t=10, b=60),
                    xaxis=dict(showgrid=False, color="#a38060"),
                    yaxis=dict(showgrid=False, color="#a38060", title="EPS"),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                                font=dict(color="#4a3520")),
                    showlegend=True,
                )
                st.markdown('<div class="card-wrap" style="padding:12px">', unsafe_allow_html=True)
                st.plotly_chart(fig, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
                eps_plotted = True

        if not eps_plotted:
            st.info("EPS data not available.")

    # ── Revenue vs Earnings (quarterly) ──────────────────────────────
    with col_r:
        st.markdown('<div style="font-weight:700;color:#1a0f00;margin-bottom:10px">Revenue vs. Earnings</div>',
                    unsafe_allow_html=True)
        if inc_q is not None and not inc_q.empty:
            df4 = inc_q.iloc[:, :4][::-1]
            rev_row = next((i for i in df4.index
                            if "total revenue" in str(i).lower() or "operating revenue" in str(i).lower()), None)
            ni_row  = next((i for i in df4.index
                            if "net income common" in str(i).lower() or "net income" == str(i).lower()), None)

            dates = [_quarter_label(c) for c in df4.columns]
            rev = [float(df4.loc[rev_row, c])/1e9 if rev_row else 0 for c in df4.columns]
            ni  = [float(df4.loc[ni_row,  c])/1e9 if ni_row  else 0 for c in df4.columns]

            fig2 = go.Figure()
            fig2.add_trace(go.Bar(x=dates, y=rev, name="Revenue",
                                  marker_color="#1d4ed8", opacity=0.85))
            fig2.add_trace(go.Bar(x=dates, y=ni,  name="Earnings",
                                  marker_color=["#f59e0b" if v < 0 else "#16a34a" for v in ni]))
            fig2.update_layout(
                paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG, height=280,
                barmode="group", margin=dict(l=0, r=0, t=10, b=40),
                xaxis=dict(showgrid=False, color="#a38060"),
                yaxis=dict(showgrid=False, color="#a38060", title=f"{sym}B"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                            font=dict(color="#4a3520")),
            )
            st.markdown('<div class="card-wrap" style="padding:12px">', unsafe_allow_html=True)
            st.plotly_chart(fig2, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("Revenue data not available.")


def _render_analyst_insights(details, info, sym):
    apt  = details.get("price_targets", {})
    recs = details.get("recommendations", pd.DataFrame())

    col_l, col_r = st.columns(2)

    # ── Price targets ─────────────────────────────────────────────────
    with col_l:
        st.markdown('<div style="font-weight:700;color:#1a0f00;margin-bottom:10px">Analyst Price Targets</div>',
                    unsafe_allow_html=True)
        low  = apt.get("low")  or info.get("targetLowPrice")
        high = apt.get("high") or info.get("targetHighPrice")
        mean = apt.get("mean") or info.get("targetMeanPrice") or info.get("targetMedianPrice")
        curr = apt.get("current") or info.get("currentPrice") or info.get("previousClose")

        if all(v for v in [low, high, mean, curr]):
            # ── x-axis range: 30% padding on each side of Low-to-High ──
            _all_vals   = [low, high, mean, curr]
            _data_min   = min(_all_vals)
            _data_max   = max(_all_vals)
            _data_range = _data_max - _data_min or _data_max * 0.1
            _pad        = _data_range * 0.30
            _ax_min     = max(0, _data_min - _pad)
            _ax_max     = _data_max + _pad
            # Round to clean numbers (nearest power-of-10 two digits below max)
            _mag        = 10 ** max(0, len(str(int(_ax_max))) - 2)
            _ax_min     = int(_ax_min / _mag) * _mag
            _ax_max     = (int(_ax_max / _mag) + 1) * _mag

            fig = go.Figure()
            # Range bar
            fig.add_trace(go.Scatter(
                x=[low, high], y=[1, 1], mode="lines",
                line=dict(color="#d1d5db", width=6), showlegend=False,
            ))
            # Mean
            fig.add_trace(go.Scatter(
                x=[mean], y=[1], mode="markers+text",
                marker=dict(size=16, color="#1d4ed8"),
                text=[f"{sym}{mean:,.0f}<br>Mean"],
                textposition="top center",
                textfont=dict(size=11, color="#1d4ed8"),
                name="Mean Target",
            ))
            # Current
            fig.add_trace(go.Scatter(
                x=[curr], y=[1], mode="markers+text",
                marker=dict(size=14, color="#c2410c", symbol="diamond"),
                text=[f"{sym}{curr:,.0f}<br>Current"],
                textposition="bottom center",
                textfont=dict(size=11, color="#c2410c"),
                name="Current Price",
            ))
            fig.update_layout(
                paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG, height=220,
                margin=dict(l=40, r=40, t=50, b=50),
                xaxis=dict(range=[_ax_min, _ax_max],
                           showgrid=False, color="#a38060", tickprefix=sym),
                yaxis=dict(visible=False),
                legend=dict(orientation="h", yanchor="bottom", y=1.0, font=dict(color="#4a3520")),
                annotations=[
                    dict(x=low,  y=0.85, text=f"{sym}{low:,.0f}<br>Low",
                         showarrow=False, font=dict(size=10, color="#a38060")),
                    dict(x=high, y=0.85, text=f"{sym}{high:,.0f}<br>High",
                         showarrow=False, font=dict(size=10, color="#a38060")),
                ],
            )
            st.markdown('<div class="card-wrap" style="padding:12px">', unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("Price target data not available.")

    # ── Analyst recommendations ───────────────────────────────────────
    with col_r:
        st.markdown('<div style="font-weight:700;color:#1a0f00;margin-bottom:10px">Analyst Recommendations</div>',
                    unsafe_allow_html=True)
        # rec_map covers both recommendations_summary and raw recommendations columns
        rec_map = [
            ("strongBuy",   "Strong Buy",   "#15803d"),
            ("buy",         "Buy",          "#4ade80"),
            ("hold",        "Hold",         "#f59e0b"),
            ("underperform","Underperform", "#f97316"),
            ("strongSell",  "Strong Sell",  "#dc2626"),
            ("sell",        "Sell",         "#b91c1c"),
        ]

        def _period_label(p):
            """Convert '0m' → 'This Month', '-1m' → 'Last Month', else pass through."""
            try:
                n = int(str(p).replace("m", ""))
                if n == 0:   return "This Month"
                if n == -1:  return "Last Month"
                if n == -2:  return "2 Months Ago"
                if n == -3:  return "3 Months Ago"
                return str(p)
            except Exception:
                return str(p)

        df_recs  = None
        periods  = []
        if recs is not None and not recs.empty:
            if "strongBuy" in recs.columns:
                # recommendations_summary format — most common
                df_recs = recs.head(4).copy()
                raw_periods = df_recs["period"].tolist() if "period" in df_recs.columns \
                              else [str(i) for i in df_recs.index]
                periods = [_period_label(p) for p in raw_periods]
            elif "To Grade" in recs.columns or "toGrade" in recs.columns:
                # Raw analyst actions — aggregate by month
                grade_col = "To Grade" if "To Grade" in recs.columns else "toGrade"
                recs.index = pd.to_datetime(recs.index, utc=True)
                recs["month"] = recs.index.to_period("M")
                month_periods = sorted(recs["month"].unique())[-4:]
                grade_map = {
                    "strong buy": "strongBuy", "buy": "buy", "hold": "hold",
                    "underperform": "underperform", "sell": "sell", "strong sell": "strongSell",
                    "neutral": "hold", "outperform": "buy", "overweight": "buy",
                    "underweight": "sell", "market perform": "hold",
                }
                rows = []
                for p in month_periods:
                    sub    = recs[recs["month"] == p]
                    counts = {"period": str(p)}
                    for k in ["strongBuy","buy","hold","underperform","strongSell","sell"]:
                        counts[k] = 0
                    for g in sub[grade_col].str.lower():
                        mapped = grade_map.get(g)
                        if mapped:
                            counts[mapped] += 1
                    rows.append(counts)
                df_recs = pd.DataFrame(rows)
                periods = [r["period"] for r in rows]

        if df_recs is not None and not df_recs.empty:
            fig = go.Figure()
            for col_key, label, color in rec_map:
                vals = df_recs[col_key].tolist() if col_key in df_recs.columns else [0]*len(periods)
                if not any(v > 0 for v in vals):
                    continue   # skip empty series to keep legend clean
                fig.add_trace(go.Bar(
                    x=periods, y=vals, name=label,
                    marker_color=color,
                    text=[v if v > 0 else "" for v in vals],
                    textposition="inside",
                    textfont=dict(color="white", size=10),
                ))
            fig.update_layout(
                paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG, height=220,
                barmode="stack",
                margin=dict(l=0, r=0, t=10, b=40),
                xaxis=dict(showgrid=False, color="#a38060"),
                yaxis=dict(showgrid=False, color="#a38060"),
                legend=dict(orientation="v", x=1.02, y=1, font=dict(color="#4a3520", size=10)),
            )
            st.markdown('<div class="card-wrap" style="padding:12px">', unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("Recommendation data not available.")


# ── Feature 2: Company Performance Chart ─────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_company_price_data(ticker_sym: str, period: str) -> pd.DataFrame:
    """Fetch historical price data for a company vs Nifty/Sensex benchmarks."""
    period_map = {"1M": 30, "3M": 90, "6M": 180, "1Y": 365, "All": 900}
    days = period_map.get(period, 900)
    start = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        df = yf.download(
            [ticker_sym, "^NSEI", "^BSESN"],
            start=start,
            auto_adjust=True,
            progress=False,
        )
        return df
    except Exception:
        return pd.DataFrame()


def render_company_performance_chart(company_name: str, ticker_sym: str):
    """Performance chart tab for company deep dive — vs Nifty 50, Sensex and Z47 Index."""
    period = st.radio(
        "Period", ["1M", "3M", "6M", "1Y", "All"],
        horizontal=True, key=f"perf_period_{ticker_sym}"
    )
    raw = _fetch_company_price_data(ticker_sym, period)
    if raw is None or raw.empty:
        st.info("Price data not available for this company.")
        return
    try:
        # Extract Close prices — yf.download returns MultiIndex cols when multiple tickers
        if isinstance(raw.columns, pd.MultiIndex):
            close = raw["Close"] if "Close" in raw.columns.get_level_values(0) else None
        else:
            close = raw[["Close"]] if "Close" in raw.columns else None

        if close is None or close.empty:
            st.info("Price data unavailable.")
            return

        # Rename columns for clarity
        col_map = {ticker_sym: company_name, "^NSEI": "Nifty 50", "^BSESN": "Sensex"}
        close = close.rename(columns=col_map)
        close = close.dropna(how="all")

        # Rebase to 100 from first valid observation
        first_valid = close.bfill().iloc[0]
        rebased = close.div(first_valid) * 100

        # Downsample to ≤500 points for faster Plotly render
        if len(rebased) > 500:
            _step = max(1, len(rebased) // 500)
            rebased = rebased.iloc[::_step]

        fig = go.Figure()
        # Company line: bright orange dashed — distinct from the darker Z47'47 solid line
        _line_styles = {
            company_name: dict(color=C_COMPANY, width=2.5, dash="dash"),
            "Nifty 50":   dict(color=C_NIFTY,   width=2),
            "Sensex":     dict(color=C_SENSEX,   width=2),
        }
        for col in rebased.columns:
            if col in rebased:
                series = rebased[col].dropna()
                if not series.empty:
                    fig.add_trace(go.Scatter(
                        x=series.index, y=series.values,
                        mode="lines", name=col,
                        line=_line_styles.get(col, dict(color="#6b7a8d", width=2)),
                        hovertemplate=f"{col}: %{{y:.1f}}<extra></extra>",
                    ))

        # ── Z47 Index as 4th dashed orange line ──────────────────────────────
        try:
            z47_hist = load_history()
            z47_hist = z47_hist.copy()
            z47_hist["date"] = pd.to_datetime(z47_hist["date"])
            # Align to same date range as the chart
            if not rebased.empty:
                start_dt = rebased.index.min()
                end_dt   = rebased.index.max()
                if hasattr(start_dt, "tz_localize"):
                    start_dt = start_dt.tz_localize(None) if start_dt.tzinfo else start_dt
                    end_dt   = end_dt.tz_localize(None) if end_dt.tzinfo else end_dt
                z47_slice = z47_hist[
                    (z47_hist["date"] >= start_dt) & (z47_hist["date"] <= end_dt)
                ]
            else:
                z47_slice = z47_hist
            if not z47_slice.empty:
                z47_base = z47_slice["z47_float"].iloc[0]
                if z47_base:
                    z47_y = (z47_slice["z47_float"] / z47_base * 100).tolist()
                    fig.add_trace(go.Scatter(
                        x=z47_slice["date"].tolist(), y=z47_y,
                        name="Z47'47", mode="lines",
                        line=dict(color=C_Z47, width=2),
                        hovertemplate="Z47'47: %{y:.1f}<extra></extra>",
                    ))
        except Exception as _z47e:
            print(f"[Performance chart Z47 line] {ticker_sym}: {_z47e}")

        fig.update_layout(
            paper_bgcolor=CARD_BG,
            plot_bgcolor=CARD_BG,
            height=340,
            margin=dict(l=0, r=0, t=20, b=0),
            legend=dict(orientation="h", y=1.10, font=dict(size=12),
                        bgcolor="rgba(0,0,0,0)"),
            yaxis=dict(title="Rebased to 100", showgrid=True,
                       gridcolor=BORDER, tickfont=dict(size=11), color="#a38060"),
            xaxis=dict(showgrid=False, tickfont=dict(size=11), color="#a38060"),
            font=dict(family="Inter, sans-serif"),
            hovermode="x unified",
            transition_duration=0,    # disable animations for instant render
        )
        st.markdown('<div class="card-wrap" style="padding:16px">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.caption(f"Performance rebased to 100 | {period} period | Source: Yahoo Finance · Z47 history CSV")
    except Exception as _pe:
        st.info("Could not render performance chart.")
        print(f"[Performance chart] {ticker_sym}: {_pe}")


def _build_rr_factual_fallback(c: dict, details: dict, qstr: str) -> str:
    """
    Build a one-paragraph factual summary from already-loaded financial data.
    Used when the Claude API call fails or times out — never shows placeholder text.
    """
    import re as _rfb_re
    sym  = "₹" if c["exchange"] == "NSE" else "$"
    info = details.get("info", {})
    iq   = details.get("income_quarterly")

    def _fmt_v(v):
        if v is None:
            return None
        try:
            v = float(v)
            if pd.isna(v):
                return None
        except Exception:
            return None
        neg = "-" if v < 0 else ""
        av  = abs(v)
        if av >= 1e12: return f"{neg}{sym}{av/1e12:.2f}T"
        if av >= 1e9:  return f"{neg}{sym}{av/1e9:.1f}B"
        if av >= 1e6:  return f"{neg}{sym}{av/1e6:.0f}M"
        return f"{neg}{sym}{av/1e3:.0f}K"

    def _get_row(df, candidates):
        for cand in candidates:
            for idx in df.index:
                if cand.lower() == str(idx).lower():
                    return df.loc[idx]
        return None

    rev_val = ni_val = ebitda_val = rev_yoy = None

    # Try quarterly income statement (most reliable source)
    if iq is not None and not iq.empty and len(iq.columns) >= 1:
        try:
            rev_row  = _get_row(iq, ["Total Revenue", "Operating Revenue"])
            ni_row   = _get_row(iq, ["Net Income Common Stockholders", "Net Income"])
            eb_row   = _get_row(iq, ["EBITDA", "Normalized EBITDA", "EBIT",
                                      "Operating Income"])
            if rev_row is not None:
                rev_val = float(rev_row.iloc[0]) if not pd.isna(rev_row.iloc[0]) else None
                if len(rev_row) >= 5:
                    rev_prev = (float(rev_row.iloc[4])
                                if not pd.isna(rev_row.iloc[4]) else None)
                    if rev_val and rev_prev and rev_prev != 0:
                        rev_yoy = round((rev_val / rev_prev - 1) * 100, 1)
            if ni_row is not None:
                ni_val = float(ni_row.iloc[0]) if not pd.isna(ni_row.iloc[0]) else None
            if eb_row is not None:
                ebitda_val = (float(eb_row.iloc[0])
                              if not pd.isna(eb_row.iloc[0]) else None)
        except Exception:
            pass

    # Fallback to TTM fields from info
    if rev_val is None:
        rev_val = info.get("totalRevenue")
    if ni_val is None:
        ni_val = info.get("netIncomeToCommon")

    parts = []
    if rev_val is not None:
        yoy_s = (f" ({'+' if rev_yoy >= 0 else ''}{rev_yoy:.1f}% YoY)"
                 if rev_yoy is not None else "")
        parts.append(f"revenue {_fmt_v(rev_val)}{yoy_s}")

    if ebitda_val is not None:
        lbl = "EBITDA loss" if ebitda_val < 0 else "EBITDA"
        parts.append(f"{lbl} {_fmt_v(ebitda_val)}")

    if ni_val is not None:
        lbl = "net loss" if ni_val < 0 else "PAT"
        parts.append(f"{lbl} {_fmt_v(ni_val)}")

    if parts:
        return f"{c['name']} reported {', '.join(parts)} in {qstr}. See Income Statement tab for full line items."
    return f"Latest reported quarter: {qstr}. See Income Statement tab for line items."


def render_company_deep_dive(c, details, usdinr, price_data=None, mc_data=None):
    info       = details.get("info", {})
    sym        = "₹" if c["exchange"] == "NSE" else "$"
    price_data = price_data or {}

    # ── helpers ──────────────────────────────────────────────────────
    def _p(key, fallback=None):
        v = info.get(key, fallback)
        return f"{sym}{v:,.2f}" if isinstance(v, (int, float)) else "—"

    def _mc_str():
        # Prefer live market cap we already have; fall back to yfinance info
        if mc_data:
            v = mc_data["mc"] * 1e6   # mc is in Mn, convert to units
            if mc_data["currency"] != "INR":
                v_inr = v * usdinr
            else:
                v_inr = v
            if v_inr >= 1e12: return f"₹{v_inr/1e12:.2f}T"
            if v_inr >= 1e9:  return f"₹{v_inr/1e9:.2f}B"
            return f"₹{v_inr/1e6:.1f}M"
        v = info.get("marketCap")
        if not isinstance(v, (int, float)): return "—"
        if v >= 1e12: return f"{sym}{v/1e12:.2f}T"
        if v >= 1e9:  return f"{sym}{v/1e9:.2f}B"
        return f"{sym}{v/1e6:.1f}M"

    def _n(key, fmt="{:,.0f}"):
        v = info.get(key)
        return fmt.format(v) if isinstance(v, (int, float)) else "—"

    # Use live NSE/NASDAQ price as fallback when yfinance info is missing
    live_price = price_data.get("price")
    live_prev  = price_data.get("prev_close")
    prev_close = info.get("previousClose") or live_prev
    curr_price = info.get("currentPrice") or info.get("regularMarketPrice") or live_price

    def _price_str(v):
        return f"{sym}{v:,.2f}" if isinstance(v, (int, float)) else "—"

    day_low  = info.get("dayLow")  or (live_price * 0.99 if live_price else None)
    day_high = info.get("dayHigh") or (live_price * 1.01 if live_price else None)

    stat_groups = [
        [
            ("Previous Close",  _price_str(prev_close)),
            ("Current Price",   _price_str(curr_price)),
            ("Day's Range",     f"{_price_str(day_low)} – {_price_str(day_high)}"),
            ("52-Week Range",   f"{_p('fiftyTwoWeekLow')} – {_p('fiftyTwoWeekHigh')}"),
            ("Sector",          c["sector"]),
        ],
        [
            ("Volume",        _n("volume") if info.get("volume") else (f"{price_data.get('volume'):,.0f}" if price_data.get("volume") else "—")),
            ("Avg. Volume",   _n("averageVolume")),
            ("Market Cap",    _mc_str()),
            ("Float %",       f"{c['float_pct']}%"),
            ("Exchange",      c["exchange"]),
        ],
        [
            ("PE Ratio (TTM)", _n("trailingPE", "{:.1f}x")),
            ("EPS (TTM)",      f"{sym}{info['trailingEps']:.2f}" if isinstance(info.get("trailingEps"), (int,float)) else "—"),
            ("Beta (5Y)",      _n("beta", "{:.2f}")),
            ("1Y Target Est",  _p("targetMeanPrice")),
            ("Div & Yield",    f"{info.get('dividendYield',0)*100:.2f}%" if info.get("dividendYield") else "—"),
        ],
    ]

    # ── Company takeaway banner (v2) ─────────────────────────────────────────
    try:
        _co_takeaway = get_company_takeaway_v2(c["name"], yf_ticker(c))
        if _co_takeaway:
            render_takeaway_box(_co_takeaway, title=f"{c['name']} — Z47 Analyst Note", icon="💡")
    except Exception as _ct_err:
        print(f"[Company takeaway v2] {c['name']}: {_ct_err}")

    cols = st.columns(3)
    for col, stats in zip(cols, stat_groups):
        with col:
            rows_html = "".join(
                f"<tr style='border-top:1px solid {BORDER}'>"
                f"<td style='padding:8px 12px;color:#8b6d4a;font-size:12px;white-space:nowrap'>{lbl}</td>"
                f"<td style='padding:8px 12px;color:#1a0f00;font-weight:500;text-align:right'>{val}</td></tr>"
                for lbl, val in stats
            )
            st.markdown(
                f"<div class='card-wrap' style='padding:0'>"
                f"<table style='width:100%;border-collapse:collapse'><tbody>{rows_html}</tbody></table></div>",
                unsafe_allow_html=True,
            )

    st.markdown("<div style='margin-top:20px'></div>", unsafe_allow_html=True)
    # ── Tabs: Performance | IS | BS | CF | Earnings | Recent Results | Analyst | News ──
    tab_perf, tab_is, tab_bs, tab_cf, tab_earn, tab_rr, tab_analyst, tab_news = st.tabs([
        "📈 Performance",
        "📊 Income Statement",
        "🏦 Balance Sheet",
        "💸 Cash Flow",
        "📈 Earnings Trends",
        "📋 Recent Results",
        "🎯 Analyst Insights",
        "📰 Recent News",
    ])

    tk = c["ticker"]
    with tab_perf:
        try:
            render_company_performance_chart(c["name"], yf_ticker(c))
        except Exception as _pf_err:
            st.info("Performance chart temporarily unavailable.")
            print(f"[Performance tab] {c['name']}: {_pf_err}")

    with tab_is:
        freq = st.radio("", ["Annual", "Quarterly"], horizontal=True, key=f"is_{tk}")
        df = details.get("income_annual" if freq=="Annual" else "income_quarterly", pd.DataFrame())
        st.markdown(f"<div class='card-wrap' style='padding:0'>{_fin_table_html(df, sym, IS_ROWS)}</div>",
                    unsafe_allow_html=True)

    with tab_bs:
        freq = st.radio("", ["Annual", "Quarterly"], horizontal=True, key=f"bs_{tk}")
        df = details.get("balance_annual" if freq=="Annual" else "balance_quarterly", pd.DataFrame())
        st.markdown(f"<div class='card-wrap' style='padding:0'>{_fin_table_html(df, sym, BS_ROWS)}</div>",
                    unsafe_allow_html=True)

    with tab_cf:
        freq = st.radio("", ["Annual", "Quarterly"], horizontal=True, key=f"cf_{tk}")
        df = details.get("cashflow_annual" if freq=="Annual" else "cashflow_quarterly", pd.DataFrame())
        st.markdown(f"<div class='card-wrap' style='padding:0'>{_fin_table_html(df, sym, CF_ROWS)}</div>",
                    unsafe_allow_html=True)

    with tab_earn:
        _render_earnings_trends(details, sym)

    with tab_rr:
        _rr_col, _rr_btn_col = st.columns([9, 1])
        with _rr_btn_col:
            if st.button("🔄 Refresh", key=f"rr_refresh_{tk}"):
                # Force-clear both the in-memory and disk caches
                get_recent_results.clear()
                _rr_dk = f"rr_{yf_ticker(c).replace('.', '_').replace('=', '_')}"
                try:
                    _rr_dpath = f"{_DISK_CACHE_DIR}/{_rr_dk}.pkl"
                    if os.path.exists(_rr_dpath):
                        os.remove(_rr_dpath)
                except Exception:
                    pass
                st.rerun()

        import re as _rr_re
        import concurrent.futures as _rr_cf
        from datetime import date as _dt

        _today = _dt.today()
        # Indian fiscal quarter: Apr-Jun = Q1, Jul-Sep = Q2, Oct-Dec = Q3, Jan-Mar = Q4
        _m   = _today.month
        _fq  = (_m - 4) // 3 + 1 if _m >= 4 else (_m + 8) // 3
        _fyr = _today.year + 1 if _m >= 4 else _today.year
        # Most recently REPORTED quarter = one quarter behind the current quarter
        # e.g. May 2026 → current FQ is Q1 FY27 → reported = Q4 FY26
        if _fq == 1:
            _rep_fq, _rep_fyr = 4, _fyr - 1
        else:
            _rep_fq, _rep_fyr = _fq - 1, _fyr
        _qstr = f"Q{_rep_fq} FY{str(_rep_fyr)[2:]}"

        _rr_text    = None
        _rr_source  = "api"   # "disk", "api", "fallback"
        _rr_updated = _today.strftime('%d %b %Y')

        try:
            # ── Fast path: disk cache (survives container restarts) ───────────
            _rr_dk  = f"rr_{yf_ticker(c).replace('.', '_').replace('=', '_')}"
            _rr_text = _dcache_get(_rr_dk, ttl_secs=604800)
            if _rr_text is not None:
                _rr_source = "disk"
                # Update display timestamp from file mtime
                try:
                    import datetime as _rr_dt
                    _mtime = os.path.getmtime(f"{_DISK_CACHE_DIR}/{_rr_dk}.pkl")
                    _rr_updated = _rr_dt.datetime.fromtimestamp(_mtime).strftime('%d %b %Y')
                except Exception:
                    pass
            else:
                # ── Slow path: call Claude with 15s timeout ───────────────────
                with _rr_cf.ThreadPoolExecutor(max_workers=1) as _rr_ex:
                    _rr_fut = _rr_ex.submit(
                        get_recent_results, c["name"], yf_ticker(c), c["sector"]
                    )
                    try:
                        _rr_text = _rr_fut.result(timeout=15)
                        _rr_source = "api"
                    except _rr_cf.TimeoutError:
                        _rr_text = None
                        print(f"[RR TIMEOUT] {c['name']} timed out after 15s — showing factual fallback")
                    except Exception as _rr_ex_err:
                        _rr_text = None
                        print(f"[RR ERR] {c['name']}: {_rr_ex_err}")

        except Exception as _rr_outer_err:
            _rr_text = None
            print(f"[RR OUTER ERR] {c['name']}: {_rr_outer_err}")

        if _rr_text:
            # ── Quarter label validation: extract quarter from body, sync header ──
            _q_match = _rr_re.search(r'Q([1-4])\s*FY(\d{2})', _rr_text)
            if _q_match:
                _body_qstr = f"Q{_q_match.group(1)} FY{_q_match.group(2)}"
                if _body_qstr != _qstr:
                    print(f"[RR QFIX] {c['name']}: header {_qstr} → body says {_body_qstr}")
                    _qstr = _body_qstr

            _src_note = ("Powered by Claude + web search"
                         if _rr_source in ("api", "disk") else "Factual summary")
            st.markdown(
                f"""<div style='background:linear-gradient(135deg,#f3f0ff,#ede9fe);
                border:1px solid #c4b5fd;border-radius:12px;padding:18px 22px;
                margin:12px 0;box-shadow:0 1px 6px rgba(124,58,237,.10)'>
                <div style='font-size:12px;font-weight:700;color:#6d28d9;letter-spacing:.06em;
                text-transform:uppercase;margin-bottom:8px'>💡 RECENT RESULTS — {_qstr}</div>
                <div style='color:#3b1f7a;font-size:14px;line-height:1.65'>{_rr_text}</div>
                <div style='font-size:11px;color:#9ca3af;margin-top:10px'>
                Last updated: {_rr_updated} &nbsp;·&nbsp; {_src_note}
                </div></div>""",
                unsafe_allow_html=True,
            )
        else:
            # ── Factual fallback from financial data — never shows placeholder ──
            print(f"[RR FALLBACK] {c['name']} — rendering factual fallback")
            _fallback_body = _build_rr_factual_fallback(c, details, _qstr)
            st.markdown(
                f"""<div style='background:#f9f9f9;border:1px solid #ccdaea;
                border-radius:10px;padding:14px 18px;margin:10px 0'>
                <div style='font-size:11px;font-weight:700;color:#6d28d9;letter-spacing:.05em;
                text-transform:uppercase;margin-bottom:6px'>📋 {c['name']} — {_qstr} Results</div>
                <div style='color:#4a3520;font-size:13px;line-height:1.6'>{_fallback_body}</div>
                <div style='font-size:11px;color:#9ca3af;margin-top:8px'>
                Source: yfinance / BSE filings &nbsp;·&nbsp; Click ↻ Refresh for AI analysis
                </div></div>""",
                unsafe_allow_html=True,
            )

    with tab_analyst:
        _render_analyst_insights(details, info, sym)

    with tab_news:
        news = fetch_company_news(yf_ticker(c))
        _render_news(news)


# ── Utility ───────────────────────────────────────────────────────────────────

def build_extended_df(hist, nifty_live, sensex_live):
    last  = hist.iloc[-1]
    today = pd.Timestamp.today().normalize()
    if pd.Timestamp(last["date"]).normalize() >= today:
        return hist
    nb, sb = last.get("nifty_abs"), last.get("sensex_abs")
    z47 = last["z47_float"] * (nifty_live / nb)  if nb and nifty_live  else last["z47_float"]
    ni  = last["nifty_indexed"]  * (nifty_live  / nb) if nb and nifty_live  else last["nifty_indexed"]
    si  = last["sensex_indexed"] * (sensex_live / sb) if sb and sensex_live else last["sensex_indexed"]
    new = pd.DataFrame([{"date": today, "z47_float": z47, "z47_mcap": last["z47_mcap"],
                          "nifty_indexed": ni, "sensex_indexed": si,
                          "nifty_abs": nifty_live or nb, "sensex_abs": sensex_live or sb}])
    return pd.concat([hist, new], ignore_index=True)


def safe_render(fn, name: str) -> None:
    """
    Wrap any page/section render call with crash protection.
    Shows a friendly error banner and logs the full traceback to console.
    """
    try:
        fn()
    except Exception as _e:
        import traceback as _tb
        st.error(f"⚠️ {name} encountered an error. Press F5 / ⌘R to refresh.")
        print(f"[CRASH] {name}: {type(_e).__name__}: {_e}\n{_tb.format_exc()}")


def pct_since(df, col, days=None, ytd=False):
    last_val = df[col].iloc[-1]
    if ytd:
        sub = df[df["date"] >= pd.Timestamp(df["date"].iloc[-1].year, 1, 1)]
    elif days:
        cutoff = df["date"].iloc[-1] - pd.Timedelta(days=days)
        sub = df[df["date"] >= cutoff]
    else:
        sub = df
    if sub.empty: return None
    base = sub[col].iloc[0]
    return round((last_val / base - 1) * 100, 2) if base else None


def delta_html(v, label="since Jan 2024"):
    if v is None: return '<div class="delta-neu">—</div>'
    cls = "delta-pos" if v > 0 else "delta-neg"
    arr = "▲" if v > 0 else "▼"
    return (f'<div class="{cls}">{arr} {abs(v):.1f}%'
            f'<span style="color:#a38060;font-size:11px;font-weight:400"> {label}</span></div>')


def fmt_ret(v):
    if v is None: return "—"
    color = "#16a34a" if v > 0 else "#dc2626" if v < 0 else "#a38060"
    arr   = "▲" if v > 0 else "▼" if v < 0 else ""
    return f'<span style="color:{color}">{arr} {abs(v):.1f}%</span>'


def _fmt_chg(v, decimals=2):
    if v is None: return '<span style="color:#a38060">—</span>'
    color = "#16a34a" if v > 0 else "#dc2626" if v < 0 else "#a38060"
    arr   = "▲" if v > 0 else "▼" if v < 0 else ""
    return f'<span style="color:{color}">{arr} {abs(v):.{decimals}f}%</span>'


def badge(sector):
    bg   = SECTOR_COLORS.get(sector, "#f3ede4")
    text = SECTOR_BADGE_COLORS.get(sector, "#5a3e28")
    return (f'<span style="background:{bg};color:{text};padding:2px 8px;'
            f'border-radius:4px;font-size:11px;font-weight:600">{sector}</span>')


def make_perf_chart(df, period):
    if period == "All":
        plot = df.copy()
    elif period == "YTD":
        plot = df[df["date"] >= pd.Timestamp(df["date"].iloc[-1].year, 1, 1)].copy()
    else:
        days = {"1M": 30, "3M": 90, "6M": 180, "1Y": 365}[period]
        cutoff = df["date"].iloc[-1] - pd.Timedelta(days=days)
        plot = df[df["date"] >= cutoff].copy()

    if not plot.empty and period != "All":
        for col in ["z47_float", "nifty_indexed", "sensex_indexed"]:
            b = plot[col].iloc[0]
            if b: plot[col] = plot[col] / b * 100

    fig = go.Figure()
    for col, name, color, width in [
        ("z47_float",      "Z47'47",  C_Z47,    2.5),
        ("nifty_indexed",  "Nifty 50", C_NIFTY, 2.0),
        ("sensex_indexed", "Sensex",   C_SENSEX, 2.0),
    ]:
        fig.add_trace(go.Scatter(
            x=plot["date"], y=plot[col], name=name,
            line=dict(color=color, width=width),
            hovertemplate=f"%{{y:.1f}}<extra>{name}</extra>",
        ))

    fig.add_hline(y=100, line_dash="dash", line_color="#c8a882", line_width=1)

    fig.update_layout(
        paper_bgcolor=CARD_BG,
        plot_bgcolor=CARD_BG,
        height=420,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    bgcolor="rgba(0,0,0,0)", font=dict(color="#4a3520")),
        xaxis=dict(showgrid=False, zeroline=False, color="#a38060",
                   tickfont=dict(size=11), linecolor=BORDER, linewidth=1),
        yaxis=dict(showgrid=False, zeroline=False, color="#a38060",
                   tickfont=dict(size=11), linecolor=BORDER, linewidth=1),
        margin=dict(l=0, r=0, t=0, b=0),
        hovermode="x unified",
        transition_duration=0,
    )
    return fig


# ── AI Chat helpers ───────────────────────────────────────────────────────────

def build_data_context(df, returns_1m, live_mktcaps, usdinr, nifty_live, sensex_live):
    last = df.iloc[-1]
    last_date = pd.Timestamp(last["date"]).strftime("%d %b %Y")

    z47_now   = round(float(last["z47_float"]), 2)
    z47_ytd   = pct_since(df, "z47_float", ytd=True)
    z47_1y    = pct_since(df, "z47_float", days=365)
    z47_all   = pct_since(df, "z47_float")
    nifty_ytd = pct_since(df, "nifty_indexed", ytd=True)
    nifty_all = pct_since(df, "nifty_indexed")

    total_mcap_inr = 0.0
    for c in COMPANIES:
        mc = live_mktcaps.get(c["ticker"])
        if mc:
            if mc["currency"] == "INR":
                total_mcap_inr += mc["mc"]
            else:
                total_mcap_inr += mc["mc"] * usdinr
        else:
            total_mcap_inr += c["mkt_cap_mn"]

    top5g = sorted(returns_1m.items(), key=lambda x: -x[1])[:5] if returns_1m else []
    top5l = sorted(returns_1m.items(), key=lambda x:  x[1])[:5] if returns_1m else []
    name_map = {c["ticker"]: c["name"] for c in COMPANIES}

    sector_counts = {}
    for c in COMPANIES:
        sector_counts[c["sector"]] = sector_counts.get(c["sector"], 0) + 1

    lines = [
        "=== Z47 INDEX — LIVE DATA SNAPSHOT ===",
        f"Date: {last_date}",
        f"1 USD = ₹{usdinr}",
        "",
        "--- INDEX LEVELS ---",
        f"Z47'47: {z47_now:.1f} (rebased to 100 on 1 Jan 2024)",
        f"Nifty 50 (live): {nifty_live:,.0f}" if nifty_live else "Nifty 50: unavailable",
        f"Sensex (live): {sensex_live:,.0f}" if sensex_live else "Sensex: unavailable",
        "",
        "--- Z47 PERFORMANCE ---",
        f"YTD: {z47_ytd:+.1f}%" if z47_ytd else "YTD: N/A",
        f"1 Year: {z47_1y:+.1f}%" if z47_1y else "1 Year: N/A",
        f"Since Jan 2024: {z47_all:+.1f}%" if z47_all else "Since Jan 2024: N/A",
        f"vs Nifty 50 (YTD): {(z47_ytd or 0) - (nifty_ytd or 0):+.1f} pp",
        f"vs Nifty 50 (Since Jan 2024): {(z47_all or 0) - (nifty_all or 0):+.1f} pp",
        "",
        "--- TOTAL MARKET CAP ---",
        f"Total constituent market cap: ₹{total_mcap_inr/1e6:.2f} Tn  (${total_mcap_inr/usdinr/1e6:.2f} Tn USD)",
        "",
        "--- TOP 5 GAINERS (1M) ---",
    ]
    for tk, pct in top5g:
        lines.append(f"  {name_map.get(tk, tk)} ({tk}): +{pct:.1f}%")

    lines += ["", "--- TOP 5 LOSERS (1M) ---"]
    for tk, pct in top5l:
        lines.append(f"  {name_map.get(tk, tk)} ({tk}): {pct:.1f}%")

    lines += ["", "--- ALL 47 CONSTITUENTS (1M RETURN) ---"]
    for c in COMPANIES:
        mc = live_mktcaps.get(c["ticker"])
        if mc:
            mc_inr = mc["mc"] if mc["currency"] == "INR" else mc["mc"] * usdinr
        else:
            mc_inr = c["mkt_cap_mn"]
        ret_str = f"{returns_1m[c['ticker']]:+.1f}%" if c["ticker"] in returns_1m else "N/A"
        lines.append(
            f"  {c['num']}. {c['name']} ({c['ticker']}, {c['exchange']}) | "
            f"Sector: {c['sector']} | Float: {c['float_pct']}% | "
            f"Mkt Cap: ₹{mc_inr:,.0f} Mn | 1M: {ret_str}"
        )

    lines += ["", "--- SECTOR BREAKDOWN ---"]
    for sector, count in sorted(sector_counts.items(), key=lambda x: -x[1]):
        lines.append(f"  {sector}: {count} companies")

    lines += [
        "",
        "--- METHODOLOGY ---",
        "Free-float market-cap weighted index (same as NSE sectoral indices).",
        "Base: 100 on 1 Jan 2024. Divisor adjusted on additions/removals.",
        "47 Indian internet & new-age tech companies (NSE + NASDAQ listed).",
    ]

    return "\n".join(lines)


def _build_z47_system_prompt(data_context: str) -> str:
    """Build the full system prompt for the Z47 Index chat with web search guidance."""
    base = SYSTEM_PROMPTS["z47_index"]
    if data_context:
        return (
            base
            + "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            + "PRE-COMPUTED LIVE DATA (use this for return / price questions)\n"
            + "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            + data_context
        )
    return base


def call_ai_response(messages: list, data_context: str) -> str:
    """
    Non-streaming AI response with web search.  Replaces stream_ai_response().
    Uses ask_z47_with_search() from z47_assistant — automatically searches
    the web for P/E ratios, quarterly results, analyst targets, and news.
    """
    system_prompt = _build_z47_system_prompt(data_context)
    return ask_z47_with_search(messages, system_prompt)


# ── Mobile layout ─────────────────────────────────────────────────────────────

def main_mobile():
    hist = load_history()
    nifty_live, sensex_live = fetch_live_indices()
    usdinr = get_usdinr()
    df = build_extended_df(hist, nifty_live, sensex_live)
    last = df.iloc[-1]
    last_date_str = pd.Timestamp(last["date"]).strftime("%d %b %Y")

    with st.spinner("Loading market data…"):
        returns_1m   = fetch_1m_returns()
        long_hist    = fetch_long_history()
        live_mktcaps = fetch_market_caps()
    name_map = {c["ticker"]: c["name"] for c in COMPANIES}

    z47_ret    = pct_since(df, "z47_float")
    nifty_ret  = pct_since(df, "nifty_indexed")
    outperf    = round(z47_ret - nifty_ret, 1) if z47_ret is not None and nifty_ret is not None else None
    z47_ytd    = pct_since(df, "z47_float", ytd=True)

    # ── Header ──────────────────────────────────────────────────────
    st.markdown(
        f'<div style="color:#1a0f00;font-size:24px;font-weight:800;margin-bottom:2px">Z47\'47</div>'
        f'<div style="color:#8b6d4a;font-size:11px;margin-bottom:4px">'
        f'Free-float market-cap weighted · 47 Indian internet &amp; tech cos</div>'
        f'<div style="color:#a38060;font-size:11px;margin-bottom:20px">'
        f'Data as of <b style="color:#4a3520">{last_date_str}</b> &nbsp;·&nbsp; 1 USD = ₹{usdinr}</div>',
        unsafe_allow_html=True,
    )

    # ── KPI cards 2×2 ───────────────────────────────────────────────
    c1, c2 = st.columns(2)
    nifty_disp  = f"{nifty_live:,.0f}"  if nifty_live  else f"{last['nifty_indexed']:.1f}"
    sensex_disp = f"{sensex_live:,.0f}" if sensex_live else f"{last['sensex_indexed']:.1f}"
    oc  = "delta-pos" if outperf and outperf > 0 else "delta-neg"
    oa  = "▲" if outperf and outperf > 0 else "▼"

    with c1:
        st.markdown(
            f'<div class="mobile-kpi"><div class="mobile-kpi-label">Z47\'47</div>'
            f'<div class="mobile-kpi-value">{last["z47_float"]:.1f}</div>'
            f'{delta_html(z47_ret)}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="mobile-kpi"><div class="mobile-kpi-label">Sensex</div>'
            f'<div class="mobile-kpi-value">{sensex_disp}</div>'
            f'{delta_html(pct_since(df, "sensex_indexed"))}</div>', unsafe_allow_html=True)
    with c2:
        st.markdown(
            f'<div class="mobile-kpi"><div class="mobile-kpi-label">Nifty 50</div>'
            f'<div class="mobile-kpi-value">{nifty_disp}</div>'
            f'{delta_html(nifty_ret)}</div>', unsafe_allow_html=True)
        ow = "outperforms" if outperf and outperf > 0 else "underperforms"
        st.markdown(
            f'<div class="mobile-kpi"><div class="mobile-kpi-label">Z47 vs Nifty</div>'
            f'<div class="mobile-kpi-value" style="font-size:15px">Z47 {ow}</div>'
            f'<div class="{oc}" style="margin-top:4px">{oa} {abs(outperf or 0):.1f} pp</div></div>',
            unsafe_allow_html=True)

    # ── Performance chart (compact) ──────────────────────────────────
    st.markdown('<div class="section-header">Performance</div>', unsafe_allow_html=True)
    period = st.radio("Period", ["1M", "3M", "6M", "1Y", "YTD", "All"],
                      index=5, horizontal=True, label_visibility="collapsed", key="mob_period")
    fig = make_perf_chart(df, period)
    fig.update_layout(height=280, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, use_container_width=True)

    # ── AI Chatbox ───────────────────────────────────────────────────
    st.markdown('<div class="section-header">Ask Z47 Assistant</div>', unsafe_allow_html=True)
    if "mob_chat" not in st.session_state:
        st.session_state.mob_chat = []
    for msg in st.session_state.mob_chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    with st.form(key="mob_chat_form", clear_on_submit=True, border=False):
        user_input = st.text_input("q", placeholder="Ask anything about Z47…",
                                   label_visibility="collapsed")
        submitted  = st.form_submit_button("Ask →", use_container_width=True)
    if submitted and user_input.strip():
        prompt = user_input.strip()
        st.session_state.mob_chat.append({"role": "user", "content": prompt})
        data_ctx = build_data_context(df, returns_1m, live_mktcaps, usdinr, nifty_live, sensex_live)
        msgs_for_api = [{"role": m["role"], "content": m["content"]}
                        for m in st.session_state.mob_chat]
        with st.chat_message("assistant"):
            with st.spinner("🔍 Searching and analyzing…"):
                response_text = call_ai_response(msgs_for_api, data_ctx)
            st.markdown(response_text)
        st.session_state.mob_chat.append({"role": "assistant", "content": response_text})

    # ── Top 5 gainers / losers (stacked) ─────────────────────────────
    st.markdown('<div class="section-header">Top Movers — Last Month</div>', unsafe_allow_html=True)
    if returns_1m:
        for title, items, color, arrow in [
            ("🏆 Top 5 Gainers", sorted(returns_1m.items(), key=lambda x: -x[1])[:5], "#16a34a", "▲"),
            ("📉 Top 5 Losers",  sorted(returns_1m.items(), key=lambda x:  x[1])[:5], "#dc2626", "▼"),
        ]:
            rows_html = "".join(
                f"<tr style='border-top:1px solid {BORDER}'>"
                f"<td style='padding:9px 12px;color:#1a0f00;font-size:13px'>{name_map.get(tk,tk)}</td>"
                f"<td style='padding:9px 12px;text-align:right;color:{color};font-weight:700'>"
                f"{arrow} {abs(pct):.1f}%</td></tr>"
                for tk, pct in items
            )
            st.markdown(
                f"<div class='card-wrap' style='padding:0;margin-bottom:12px'>"
                f"<div style='padding:12px 14px;font-weight:700;color:#1a0f00;"
                f"border-bottom:1px solid {BORDER};font-size:13px'>{title}</div>"
                f"<table style='width:100%;border-collapse:collapse'><tbody>{rows_html}</tbody></table></div>",
                unsafe_allow_html=True,
            )

    # ── Constituents (compact — key columns only) ────────────────────
    st.markdown('<div class="section-header">Constituents</div>', unsafe_allow_html=True)
    th2 = "padding:8px 10px;color:#8b6d4a;font-weight:600;font-size:11px"
    tbl = (
        f"<div class='card-wrap' style='padding:0;overflow-x:auto'>"
        f"<table style='width:100%;border-collapse:collapse;font-size:12px'>"
        f"<thead><tr style='background:{BG_ALT}'>"
        f"<th style='text-align:left;{th2}'>Company</th>"
        f"<th style='text-align:right;{th2}'>Price</th>"
        f"<th style='text-align:right;{th2}'>Day</th>"
        f"<th style='text-align:right;{th2}'>1M</th>"
        f"<th style='text-align:right;{th2}'>Mkt Cap ₹Mn</th>"
        f"</tr></thead><tbody>"
    )
    with st.spinner("Fetching prices…"):
        price_cache = {}
        def _fetch_price_one(c):
            if c["exchange"] == "NSE":
                return c["ticker"], fetch_nse_price(c["ticker"])
            else:
                return c["ticker"], fetch_nasdaq_price(c["ticker"])
        with ThreadPoolExecutor(max_workers=12) as _px:
            for _tk, _pd in _px.map(_fetch_price_one, COMPANIES):
                price_cache[_tk] = _pd

    for c in COMPANIES:
        q   = price_cache.get(c["ticker"], {})
        px  = q.get("price")
        pct = q.get("pct_change")
        m1  = returns_1m.get(c["ticker"])
        mc  = live_mktcaps.get(c["ticker"])
        mc_inr = round(mc["mc"] if mc and mc["currency"]=="INR" else (mc["mc"]*usdinr if mc else c["mkt_cap_mn"]), 0)
        px_str = (f"₹{px:,.0f}" if c["exchange"]=="NSE" else f"${px:,.1f}") if px else "—"
        tbl += (
            f"<tr style='border-top:1px solid {BORDER}'>"
            f"<td style='padding:8px 10px;color:#1a0f00;font-weight:500'>{c['name']}</td>"
            f"<td style='padding:8px 10px;text-align:right;color:#4a3520'>{px_str}</td>"
            f"<td style='padding:8px 10px;text-align:right'>{_fmt_chg(pct)}</td>"
            f"<td style='padding:8px 10px;text-align:right'>{_fmt_chg(m1)}</td>"
            f"<td style='padding:8px 10px;text-align:right;color:#4a3520'>{mc_inr:,.0f}</td>"
            f"</tr>"
        )
    tbl += "</tbody></table></div>"
    st.markdown(tbl, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)


# ── Main ──────────────────────────────────────────────────────────────────────

def _nav_btn(label, key, target_page, ipo_tab=None):
    """Render one top-nav button; returns True if active."""
    active = (
        st.session_state.get("nav_page", "z47") == target_page
        and (ipo_tab is None or st.session_state.get("ipo_tab", "recent") == ipo_tab)
    )
    if st.button(label, key=key, type="primary" if active else "secondary",
                 use_container_width=True):
        st.session_state.nav_page = target_page
        if ipo_tab is not None:
            st.session_state.ipo_tab = ipo_tab
        st.rerun()
    return active


def _render_top_nav():
    """Persistent 3-button top nav — always rendered first."""
    page = st.session_state.get("nav_page", "z47")

    # ── Level-1 nav ───────────────────────────────────────────────────────────
    c1, c2, c3, _gap = st.columns([1.6, 0.9, 2.0, 5])
    with c1: _nav_btn("📊 Z47'47",       "nav_z47",   "z47")
    with c2: _nav_btn("📈 IPOs",            "nav_ipos",  "ipos")
    with c3: _nav_btn("💼 Block & Bulk Deals","nav_block","block")

    st.markdown("<hr style='border-color:#ccdaea;margin:6px 0 0 0'>", unsafe_allow_html=True)

    # ── Level-2 IPO sub-nav (only when IPOs is active) ───────────────────────
    if page == "ipos":
        s1, s2, s3, _gap2 = st.columns([1.7, 1.9, 1.8, 4.6])
        with s1: _nav_btn("📈 Recent IPOs",   "snav_recent",   "ipos", "recent")
        with s2: _nav_btn("🚀 Upcoming IPOs", "snav_upcoming", "ipos", "upcoming")
        with s3: _nav_btn("📋 DRHP Filings",  "snav_drhp",     "ipos", "drhp")
        st.markdown("<hr style='border-color:#ccdaea;margin:6px 0 14px 0'>", unsafe_allow_html=True)


def _prewarm_recent_results_bg() -> None:
    """
    Background thread: pre-populate all company caches for the priority 20 companies.
    Warms: fetch_company_financials, get_company_takeaway_v2, get_recent_results.
    Each company's failure is isolated — one bad API call never stops the others.
    daemon=True: thread dies automatically when the main process exits.

    To trigger a full scheduled refresh (e.g. weekly Streamlit Cloud rerun):
        from app import _prewarm_recent_results_bg
        _prewarm_recent_results_bg()
    Or call refresh_all_recent_results() for a synchronous full pass.
    """
    import threading as _threading

    # Priority order specified by stakeholder — CEO-visible companies first
    _PRIORITY_TICKERS = [
        "KISSHT", "ETERNAL", "SWIGGY", "GROWW", "NAZARA",
        "PAYTM", "POLICYBZR", "MOBIKWIK", "MEESHO", "NYKAA",
        "HONASA", "MAPMYINDIA", "OLAELEC", "MEDPLUS", "PWL",
        "AYE", "MEDIASSIST", "APTUS", "CAPILLARY",
    ]
    _ticker_to_co = {c["ticker"]: c for c in COMPANIES}

    def _worker():
        _ordered = [_ticker_to_co[t] for t in _PRIORITY_TICKERS if t in _ticker_to_co]
        # Append any remaining COMPANIES not in priority list (in original order)
        _seen = {c["ticker"] for c in _ordered}
        _ordered += [c for c in COMPANIES if c["ticker"] not in _seen]
        _ordered = _ordered[:20]   # cap at 20

        print(f"[PREWARM] Starting prewarm for {len(_ordered)} companies…")
        for _c in _ordered:
            _tk = yf_ticker(_c)
            # 1. Financials (parallel yfinance — fast, disk-cached)
            try:
                fetch_company_financials(_tk)
            except Exception as _e:
                print(f"[PREWARM FINS] {_c['name']}: {_e}")
            # 2. Company analyst note (Claude API — disk-cached)
            try:
                get_company_takeaway_v2(_c["name"], _tk)
            except Exception as _e:
                print(f"[PREWARM TKWY] {_c['name']}: {_e}")
            # 3. Recent Results (Claude API — disk-cached)
            try:
                get_recent_results(_c["name"], _tk, _c["sector"])
            except Exception as _e:
                print(f"[PREWARM RR] {_c['name']}: {_e}")
        print("[PREWARM] Done.")

    _threading.Thread(target=_worker, daemon=True).start()


def refresh_all_recent_results() -> None:
    """
    Synchronous full refresh of Recent Results for all 47 companies.
    Clears disk cache first, then regenerates via Claude API.
    Use for scheduled weekly reruns or manual admin refresh.

    Wire to Streamlit Cloud scheduled rerun:
        Add a cron at https://share.streamlit.io → Settings → Scheduled reruns.
        In the rerun script, call:  from app import refresh_all_recent_results; refresh_all_recent_results()
    """
    import glob as _glob
    # Clear existing RR disk cache files
    for _f in _glob.glob(f"{_DISK_CACHE_DIR}/rr_*.pkl"):
        try:
            os.remove(_f)
        except Exception:
            pass
    get_recent_results.clear()
    # Regenerate for all 47 companies
    for _c in COMPANIES:
        try:
            get_recent_results(_c["name"], yf_ticker(_c), _c["sector"])
        except Exception as _e:
            print(f"[REFRESH RR] {_c['name']}: {_e}")
    print("[REFRESH RR] Complete.")


def main():
    # Session state defaults
    if "nav_page" not in st.session_state:
        st.session_state.nav_page = "z47"
    if "ipo_tab" not in st.session_state:
        st.session_state.ipo_tab = "recent"

    # Pre-warm Recent Results cache for top 20 companies on first load
    if "rr_prewarm_triggered" not in st.session_state:
        st.session_state.rr_prewarm_triggered = True
        _prewarm_recent_results_bg()

    _render_top_nav()

    page = st.session_state.nav_page

    # ── Route to sub-pages ────────────────────────────────────────────────────
    if page == "ipos":
        tab = st.session_state.get("ipo_tab", "recent")
        try:
            if tab == "recent":
                page_recent_ipos.render()
            elif tab == "upcoming":
                page_upcoming_ipos.render()
            else:
                page_drhp.render()
        except Exception as _page_err:
            import traceback as _tb
            st.error(
                "⚠️ This page encountered an error. Please refresh to try again.\n\n"
                f"*Details logged to console.*"
            )
            print(f"[PAGE ERROR] ipos/{tab}: {type(_page_err).__name__}: {_page_err}\n"
                  f"{_tb.format_exc()}")
        return

    if page == "block":
        try:
            page_block_deals.render()
        except Exception as _page_err:
            import traceback as _tb
            st.error("⚠️ Block Deals page encountered an error. Please refresh.")
            print(f"[PAGE ERROR] block: {type(_page_err).__name__}: {_page_err}\n"
                  f"{_tb.format_exc()}")
        return

    # ── Z47 Index (default) ───────────────────────────────────────────────────
    # Auto-refresh every 5 minutes — keeps prices, indices and live data current
    st_autorefresh(interval=300_000, key="z47_autorefresh")

    screen_width = streamlit_js_eval(js_expressions="window.innerWidth", key="screen_w")
    if screen_width is not None and screen_width < 768:
        try:
            main_mobile()
        except Exception as _mob_err:
            import traceback as _tb
            st.error("⚠️ Z47 Index encountered an error. Press F5 / ⌘R to refresh.")
            print(f"[CRASH] main_mobile: {type(_mob_err).__name__}: {_mob_err}\n{_tb.format_exc()}")
        return

    try:
        _run_z47_desktop()
    except Exception as _desk_err:
        import traceback as _tb
        st.error("⚠️ Z47 Index encountered an error. Press F5 / ⌘R to refresh.")
        print(f"[CRASH] z47_desktop: {type(_desk_err).__name__}: {_desk_err}\n{_tb.format_exc()}")


def render_index_fundamentals(metrics: dict) -> None:
    """Render the Index Fundamentals comparison table (Z47 vs Nifty50 vs Sensex)."""
    z47    = metrics.get("z47",    {})
    nifty  = metrics.get("nifty",  {})
    sensex = metrics.get("sensex", {})
    as_of  = metrics.get("as_of",  "N/A")

    def _fx(v):
        return "—" if v is None else f"{v:.1f}x"

    def _fp(v):
        if v is None: return "—"
        return f"{'+' if v > 0 else ''}{v:.1f}%"

    TH = "padding:10px 16px;color:#8b6d4a;font-size:12px;font-weight:600;white-space:nowrap"
    TD = "padding:11px 16px;vertical-align:top"

    hdr = (
        f"<tr style='background:{BG_ALT}'>"
        f"<th style='text-align:left;{TH}'>Metric</th>"
        f"<th style='text-align:right;{TH}'>Z47'47"
        f"<div style='font-weight:400;font-size:10px;color:#a38060'>median · 47 cos</div></th>"
        f"<th style='text-align:right;{TH}'>Nifty 50"
        f"<div style='font-weight:400;font-size:10px;color:#a38060'>median · 50 cos</div></th>"
        f"<th style='text-align:right;{TH}'>BSE Sensex"
        f"<div style='font-weight:400;font-size:10px;color:#a38060'>median · 30 cos</div></th>"
        f"</tr>"
    )

    def _cell(val, n, total, is_pct=False, is_z47=False, src=""):
        txt = _fp(val) if is_pct else _fx(val)
        if val is None:
            col = "#9ca3af"
        elif is_pct:
            col = "#16a34a" if val >= 0 else "#dc2626"
        else:
            col  = "#1a0f00" if is_z47 else "#4a3520"
        fw   = "700" if is_z47 else "600"
        cov  = (f"<div style='font-size:10px;color:#a38060'>{n}/{total} cos</div>"
                if n is not None else "")
        src_tag = (f"<div style='font-size:10px;color:#16a34a'>★ NSE official</div>"
                   if "NSE" in src else "")
        return (
            f"<td style='text-align:right;{TD}'>"
            f"<span style='font-size:18px;font-weight:{fw};color:{col}'>{txt}</span>"
            f"{cov}{src_tag}</td>"
        )

    def _sec(label):
        return (
            f"<tr style='background:{BG_ALT}'>"
            f"<td colspan='4' style='padding:5px 16px;color:#8b6d4a;"
            f"font-size:10px;font-weight:700;letter-spacing:.6px'>{label}</td></tr>"
        )

    def _row(label, sub, zk_v, zk_n, nk_v, nk_n, sk_v, sk_n, is_pct=False,
             nifty_src="", z_total=47, n_total=50, s_total=30):
        return (
            f"<tr style='border-top:1px solid {BORDER}'>"
            f"<td style='{TD}'><div style='font-weight:600;color:#1a0f00'>{label}</div>"
            f"<div style='font-size:11px;color:#8b6d4a'>{sub}</div></td>"
            + _cell(zk_v, zk_n, z_total, is_pct, is_z47=True)
            + _cell(nk_v, nk_n, n_total, is_pct, src=nifty_src)
            + _cell(sk_v, sk_n, s_total, is_pct)
            + "</tr>"
        )

    npe_src = nifty.get("pe_source", "computed")
    n_nf    = nifty.get("n_non_financial",  38)
    s_nf    = sensex.get("n_non_financial", 22)

    rows = (
        _sec("VALUATION MULTIPLES (TTM · MEDIAN)")
        + _row("EV / Revenue",
               "all cos; financials use MCap/Rev*",
               z47.get("ev_revenue"),    z47.get("n_ev_revenue"),
               nifty.get("ev_revenue"),  nifty.get("n_ev_revenue"),
               sensex.get("ev_revenue"), sensex.get("n_ev_revenue"))
        + _row("EV / EBITDA",
               "non-financial, EBITDA profitable only",
               z47.get("ev_ebitda"),    z47.get("n_ev_ebitda"),
               nifty.get("ev_ebitda"),  nifty.get("n_ev_ebitda"),
               sensex.get("ev_ebitda"), sensex.get("n_ev_ebitda"),
               n_total=n_nf, s_total=s_nf)
        + _row("P / E Ratio",
               "profitable cos only",
               z47.get("pe"),    z47.get("n_pe"),
               nifty.get("pe"),  nifty.get("n_pe"),
               sensex.get("pe"), sensex.get("n_pe"),
               nifty_src=npe_src)
        + _sec("OPERATING METRICS (TTM · MEAN)")
        + _row("Revenue Growth YoY",
               "mean of all constituents",
               z47.get("rev_growth"),    z47.get("n_rev_growth"),
               nifty.get("rev_growth"),  nifty.get("n_rev_growth"),
               sensex.get("rev_growth"), sensex.get("n_rev_growth"),
               is_pct=True)
        + _row("EBITDA Margin",
               "mean, non-financial cos",
               z47.get("ebitda_margin"),    z47.get("n_ebitda_margin"),
               nifty.get("ebitda_margin"),  nifty.get("n_ebitda_margin"),
               sensex.get("ebitda_margin"), sensex.get("n_ebitda_margin"),
               is_pct=True, n_total=n_nf, s_total=s_nf)
    )

    st.markdown('<div class="section-header">Index Fundamentals</div>', unsafe_allow_html=True)
    st.markdown(
        "<p style='color:#8b6d4a;font-size:12px;margin-bottom:12px'>"
        "Valuation multiples (median) and operating metrics (mean) computed from each index's "
        "constituents via yfinance. EV metrics exclude banks, NBFCs and insurance. "
        "Coverage (X/Y) = companies with valid data for that metric.</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='card-wrap' style='padding:0;overflow-x:auto'>"
        f"<table style='width:100%;border-collapse:collapse;font-size:13px'>"
        f"<thead>{hdr}</thead><tbody>{rows}</tbody></table>"
        f"<div style='padding:10px 14px;color:#a38060;font-size:11px'>"
        f"★ Nifty 50 P/E from NSE official API where available. "
        f"Data: yfinance TTM | Refreshes every hour | "
        f"Last updated: {as_of}</div></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div style='font-size:11px;color:#9ca3af;margin-top:6px;line-height:1.6'>"
        "* <b>EV/Revenue methodology:</b> Non-financial companies use standard "
        "EV/Revenue (EV = Market Cap + Debt − Cash). "
        "Financial companies (banks, NBFCs, insurance) use Market Cap ÷ Revenue as a proxy, "
        "since debt is their core business input and traditional EV overstates their enterprise value. "
        "The index-level figure is a blended median across both methodologies. "
        "EV/EBITDA continues to exclude financial companies as EBITDA is not a relevant metric for them."
        "</div>",
        unsafe_allow_html=True,
    )
    _rf1, _rf2 = st.columns([1, 10])
    with _rf1:
        if st.button("🔄 Refresh", key="refresh_fundamentals"):
            get_all_index_fundamentals.clear()
            _get_nifty50_official_pe.clear()
            st.rerun()


def _run_z47_desktop():
    """Desktop Z47 Index page — wrapped by main() for crash safety."""
    hist = load_history()
    nifty_live, sensex_live = fetch_live_indices()
    usdinr = get_usdinr()
    df = build_extended_df(hist, nifty_live, sensex_live)

    last          = df.iloc[-1]
    last_date_str = pd.Timestamp(last["date"]).strftime("%d %b %Y")

    # ── Header ──────────────────────────────────────────────────────────────
    col_h, col_u = st.columns([5, 1])
    with col_h:
        st.markdown(
            f'<div style="color:#1a0f00;font-size:34px;font-weight:800;margin-bottom:4px">Z47\'47</div>'
            f'<div style="color:#8b6d4a;font-size:13px;margin-bottom:24px">'
            "Free-float market-cap weighted index of 47 Indian internet &amp; new-age tech companies"
            " &nbsp;·&nbsp; Rebased to 100 on 1 Jan 2024"
            "</div>",
            unsafe_allow_html=True,
        )
    with col_u:
        st.markdown(
            f'<div class="last-updated" style="padding-top:28px">Data as of<br>'
            f'<b style="color:#4a3520">{last_date_str}</b><br>'
            f'<span style="font-size:11px">1 USD = ₹{usdinr}</span></div>',
            unsafe_allow_html=True,
        )

    # ── Fetch all market data early (needed by chatbox + rest of page) ─────────
    with st.spinner("Loading market data…"):
        returns_1m      = fetch_1m_returns()
        long_hist       = fetch_long_history()
        live_mktcaps    = fetch_market_caps()
        all_analyst     = fetch_all_analyst_data()    # daily pre-fetch for all 47

    name_map = {c["ticker"]: c["name"] for c in COMPANIES}

    # ── AI Chatbox (absolute top) ────────────────────────────────────────────
    st.markdown('<div class="section-header" style="margin-top:8px">Ask Z47 Assistant</div>',
                unsafe_allow_html=True)

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    # Render conversation history (grows naturally with messages)
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input bar always directly below the last message
    with st.form(key="chat_form", clear_on_submit=True, border=False):
        col_in, col_btn = st.columns([9, 1])
        with col_in:
            user_input = st.text_input(
                "question",
                placeholder="Ask anything — top movers, sector performance, Z47 vs Nifty…",
                label_visibility="collapsed",
            )
        with col_btn:
            submitted = st.form_submit_button("Ask →", use_container_width=True)

    if submitted and user_input.strip():
        prompt = user_input.strip()
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        data_ctx = build_data_context(df, returns_1m, live_mktcaps, usdinr, nifty_live, sensex_live)
        msgs_for_api = [{"role": m["role"], "content": m["content"]}
                        for m in st.session_state.chat_messages]
        with st.chat_message("assistant"):
            with st.spinner("🔍 Searching and analyzing…"):
                response_text = call_ai_response(msgs_for_api, data_ctx)
            st.markdown(response_text)
        st.session_state.chat_messages.append({"role": "assistant", "content": response_text})

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Feature 1: Market Cap Blocks ─────────────────────────────────────────
    try:
        render_mcap_blocks()
    except Exception as _mcap_err:
        print(f"[MCap blocks] error: {_mcap_err}")
    st.markdown("<br>", unsafe_allow_html=True)

    # ── KPI cards (live values) ──────────────────────────────────────────────
    z47_ret    = pct_since(df, "z47_float")
    nifty_ret  = pct_since(df, "nifty_indexed")
    sensex_ret = pct_since(df, "sensex_indexed")
    outperf    = round(z47_ret - nifty_ret, 1) \
                 if z47_ret is not None and nifty_ret is not None else None

    nifty_disp  = f"{nifty_live:,.0f}"  if nifty_live  else f"{last['nifty_indexed']:.1f}"
    sensex_disp = f"{sensex_live:,.0f}" if sensex_live else f"{last['sensex_indexed']:.1f}"

    c1, c2, c3, c4 = st.columns(4)
    for col, label, value, ret in [
        (c1, "Z47'47",  f"{last['z47_float']:.1f}", z47_ret),
        (c2, "Nifty 50 (Live)", nifty_disp,                  nifty_ret),
        (c3, "Sensex (Live)",   sensex_disp,                 sensex_ret),
    ]:
        with col:
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="metric-label">{label}</div>'
                f'<div class="metric-value">{value}</div>'
                f'{delta_html(ret)}'
                f'</div>',
                unsafe_allow_html=True,
            )

    oc = "delta-pos" if outperf and outperf > 0 else "delta-neg"
    oa = "▲" if outperf and outperf > 0 else "▼"
    ow = "outperforms" if outperf and outperf > 0 else "underperforms"
    with c4:
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-label">Z47 vs Nifty 50</div>'
            f'<div class="metric-value" style="font-size:20px">Z47 {ow}</div>'
            f'<div class="{oc}" style="margin-top:4px">{oa} {abs(outperf or 0):.1f} pp vs Nifty</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Performance chart + period selector ─────────────────────────────────
    st.markdown('<div class="section-header">Performance (rebased to 100)</div>', unsafe_allow_html=True)
    period = st.radio("Period", ["1M", "3M", "6M", "1Y", "YTD", "All"],
                      index=5, horizontal=True, label_visibility="collapsed")

    # ── Rebased blocks — read directly from the same data the chart uses ────
    # Replicate make_perf_chart's slicing + reindexing (no new logic)
    if period == "All":
        _plot = df.copy()
    elif period == "YTD":
        _plot = df[df["date"] >= pd.Timestamp(df["date"].iloc[-1].year, 1, 1)].copy()
    else:
        _days = {"1M": 30, "3M": 90, "6M": 180, "1Y": 365}[period]
        _cutoff = df["date"].iloc[-1] - pd.Timedelta(days=_days)
        _plot = df[df["date"] >= _cutoff].copy()

    if not _plot.empty and period != "All":
        for _col in ["z47_float", "nifty_indexed", "sensex_indexed"]:
            _b = _plot[_col].iloc[0]
            if _b:
                _plot[_col] = _plot[_col] / _b * 100

    # Current rebased level = last value in the (possibly reindexed) plot
    # Return for this period = last - first (first is always 100 after reindex, or raw for "All")
    def _rb_level(col):
        return float(_plot[col].iloc[-1]) if not _plot.empty else 100.0

    def _rb_ret(col):
        if _plot.empty:
            return None
        start = float(_plot[col].iloc[0])
        end   = float(_plot[col].iloc[-1])
        return round((end - start) / start * 100, 1) if start else None

    _period_label = {
        "1M": "in 1 month", "3M": "in 3 months", "6M": "in 6 months",
        "1Y": "in 1 year",  "YTD": "year-to-date", "All": "since Jan 2024",
    }[period]

    # Read the actual first data-point date straight from the chart's slice —
    # same source the chart uses, so non-trading days are handled automatically.
    _start_date_str = pd.Timestamp(_plot["date"].iloc[0]).strftime("%-d %b %Y") \
                      if not _plot.empty else "1 Jan 2024"

    def _rebase_card(label, col, accent):
        lv  = _rb_level(col)
        ret = _rb_ret(col)
        arrow     = "▲" if (ret or 0) >= 0 else "▼"
        ret_color = "#16a34a" if (ret or 0) >= 0 else "#dc2626"
        ret_str   = f"{ret:+.1f}%" if ret is not None else "N/A"
        return (
            f"<div style='background:{CARD_BG};border:1px solid {accent}40;"
            f"border-left:4px solid {accent};border-radius:10px;padding:14px 18px'>"
            f"<div style='font-size:11px;color:#8b6d4a;font-weight:600;letter-spacing:.5px;"
            f"text-transform:uppercase;margin-bottom:6px'>{label}</div>"
            f"<div style='font-size:28px;font-weight:800;color:#1a0f00;line-height:1'>"
            f"{lv:.1f}</div>"
            f"<div style='font-size:11px;color:#6b7a8d;margin-top:2px'>Rebased to 100 on {_start_date_str}</div>"
            f"<div style='display:flex;gap:16px;margin-top:8px'>"
            f"<span style='font-size:13px;font-weight:700;color:{ret_color}'>"
            f"{arrow} {ret_str} {_period_label}</span>"
            f"</div></div>"
        )

    rb1, rb2, rb3 = st.columns(3)
    with rb1:
        st.markdown(_rebase_card("Z47'47", "z47_float",      C_Z47), unsafe_allow_html=True)
    with rb2:
        st.markdown(_rebase_card("Nifty 50",       "nifty_indexed",  "#1d4ed8"), unsafe_allow_html=True)
    with rb3:
        st.markdown(_rebase_card("Sensex",         "sensex_indexed", "#15803d"), unsafe_allow_html=True)
    st.markdown("<div style='margin-bottom:12px'></div>", unsafe_allow_html=True)

    # Chart uses the same period already selected above
    st.markdown('<div class="card-wrap" style="padding:16px">', unsafe_allow_html=True)
    st.plotly_chart(make_perf_chart(df, period), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Z47'47 Monthly Takeaway (hardcoded reference content — instant render) ─
    try:
        render_takeaway_box(
            HARDCODED_INDEX_TAKEAWAY["text"],
            title=f"Z47'47 — Monthly Takeaway · {HARDCODED_INDEX_TAKEAWAY['window']}",
            icon="✨",
        )
        st.caption(
            f"Last updated: {HARDCODED_INDEX_TAKEAWAY['updated']} "
            f"· Next refresh: Monday 26 May"
        )
    except Exception as _zt_err:
        print(f"[Z47 index takeaway] render error: {_zt_err}")

    # ── Returns table ────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Returns Summary</div>', unsafe_allow_html=True)

    ret_periods = [("1M", 30), ("3M", 90), ("6M", 180), ("1Y", 365)]
    idx_cols    = [("Z47'47", "z47_float"),
                   ("Nifty 50", "nifty_indexed"),
                   ("Sensex",   "sensex_indexed")]

    th = "padding:10px 16px;color:#8b6d4a;font-size:12px;font-weight:600"
    header = (f"<tr style='background:{BG_ALT}'>"
              f"<th style='text-align:left;{th}'>Index</th>")
    for lbl, _ in ret_periods:
        header += f"<th style='text-align:right;{th}'>{lbl}</th>"
    header += (f"<th style='text-align:right;{th}'>YTD</th>"
               f"<th style='text-align:right;{th}'>Since Jan 2024</th></tr>")

    body = ""
    for name, col in idx_cols:
        body += (f"<tr style='border-top:1px solid {BORDER}'>"
                 f"<td style='padding:10px 16px;color:#1a0f00;font-weight:600'>{name}</td>")
        for _, days in ret_periods:
            body += f"<td style='padding:10px 16px;text-align:right'>{fmt_ret(pct_since(df, col, days=days))}</td>"
        body += (f"<td style='padding:10px 16px;text-align:right'>{fmt_ret(pct_since(df, col, ytd=True))}</td>"
                 f"<td style='padding:10px 16px;text-align:right'>{fmt_ret(pct_since(df, col))}</td></tr>")

    st.markdown(
        f"<div class='card-wrap' style='padding:0'>"
        f"<table style='width:100%;border-collapse:collapse'>"
        f"<thead>{header}</thead><tbody>{body}</tbody></table></div>",
        unsafe_allow_html=True,
    )

    # ── Index Fundamentals ────────────────────────────────────────────────────
    _all_fund = None
    try:
        with st.spinner("Loading index fundamentals… (first load fetches ~130 stocks, ~15–25 s)"):
            _all_fund = get_all_index_fundamentals()
        render_index_fundamentals(_all_fund)
    except Exception as _fund_err:
        st.info("📊 Index fundamentals temporarily unavailable.")
        print(f"[Fundamentals section] {type(_fund_err).__name__}: {_fund_err}")

    # ── Valuation Multiples Line Chart (Change 3) ────────────────────────────
    if _all_fund:
        try:
            st.markdown('<div class="section-header">Valuation Multiples Trend — Z47 vs Nifty vs Sensex</div>',
                        unsafe_allow_html=True)
            render_multiples_line_chart(_all_fund)
        except Exception as _mc_err:
            print(f"[Multiples line chart] error: {_mc_err}")

    # ── Valuation Perspective (hardcoded reference — always renders, no API dep) ─
    try:
        render_takeaway_box(
            HARDCODED_VALUATION_TAKEAWAY["text"],
            title=f"Z47'47 Valuation Perspective · {HARDCODED_VALUATION_TAKEAWAY['window']}",
            icon="📊",
        )
        st.caption(
            f"Last updated: {HARDCODED_VALUATION_TAKEAWAY['updated']} "
            f"· Next refresh: Monday 26 May"
        )
    except Exception as _vt_err:
        print(f"[Valuation takeaway] render error: {_vt_err}")

    # ── Top 5 gainers / losers ───────────────────────────────────────────────
    st.markdown('<div class="section-header">Top 5 Gainers &amp; Losers — Last Month</div>',
                unsafe_allow_html=True)

    if returns_1m:
        top5g = sorted(returns_1m.items(), key=lambda x: -x[1])[:5]
        top5l = sorted(returns_1m.items(), key=lambda x:  x[1])[:5]

        col_g, col_l = st.columns(2)
        for col, title, items, color, arrow in [
            (col_g, "🏆 Top 5 Gainers (1M)",  top5g, "#16a34a", "▲"),
            (col_l, "📉 Top 5 Losers (1M)",   top5l, "#dc2626", "▼"),
        ]:
            with col:
                rows_html = ""
                for ticker, pct in items:
                    rows_html += (
                        f"<tr style='border-top:1px solid {BORDER}'>"
                        f"<td style='padding:10px 14px;color:#1a0f00;font-weight:500'>{name_map.get(ticker, ticker)}</td>"
                        f"<td style='padding:10px 14px;font-family:monospace;color:#8b6d4a;font-size:12px'>{ticker}</td>"
                        f"<td style='padding:10px 14px;text-align:right;color:{color};font-weight:700'>"
                        f"{arrow} {abs(pct):.1f}%</td></tr>"
                    )
                st.markdown(
                    f"<div class='card-wrap' style='padding:0'>"
                    f"<div style='padding:14px 16px;font-weight:700;color:#1a0f00;"
                    f"border-bottom:1px solid {BORDER}'>{title}</div>"
                    f"<table style='width:100%;border-collapse:collapse'>"
                    f"<thead><tr style='background:{BG_ALT}'>"
                    f"<th style='text-align:left;padding:8px 14px;color:#8b6d4a;font-size:12px'>Company</th>"
                    f"<th style='text-align:left;padding:8px 14px;color:#8b6d4a;font-size:12px'>Ticker</th>"
                    f"<th style='text-align:right;padding:8px 14px;color:#8b6d4a;font-size:12px'>1M Return</th>"
                    f"</tr></thead><tbody>{rows_html}</tbody></table></div>",
                    unsafe_allow_html=True,
                )
    else:
        st.info("1-month data unavailable — try again shortly.")

    # ── Sector Breakdown & Takeaways (Change 5) ──────────────────────────────
    with st.expander("🏭 Sector Breakdown & Takeaways", expanded=True):
        if returns_1m:
            render_sector_breakdown_with_takeaways(returns_1m)
        else:
            st.info("Loading sector data — refresh in a moment.")

    # ── 1-Month bar chart — all constituents ─────────────────────────────────
    st.markdown('<div class="section-header">1-Month Price Movement — All Constituents</div>',
                unsafe_allow_html=True)

    if returns_1m:
        sorted_items  = sorted(returns_1m.items(), key=lambda x: x[1])
        values_sorted = [x[1] for x in sorted_items]
        names_sorted  = [name_map.get(x[0], x[0]) for x in sorted_items]
        colors        = ["#16a34a" if v >= 0 else "#dc2626" for v in values_sorted]

        fig_bar = go.Figure(go.Bar(
            x=values_sorted, y=names_sorted, orientation="h",
            marker_color=colors,
            text=[f"{'+' if v >= 0 else ''}{v:.1f}%" for v in values_sorted],
            textposition="outside",
            textfont=dict(size=10, color="#4a3520"),
            hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
        ))
        fig_bar.update_layout(
            paper_bgcolor=CARD_BG,
            plot_bgcolor=CARD_BG,
            height=max(640, len(COMPANIES) * 18),
            xaxis=dict(title="1-Month Return (%)", showgrid=False, zeroline=True,
                       zerolinecolor=BORDER, zerolinewidth=2,
                       color="#a38060", tickfont=dict(size=11)),
            yaxis=dict(showgrid=False, color="#4a3520", tickfont=dict(size=11)),
            margin=dict(l=10, r=80, t=10, b=40),
        )
        st.markdown('<div class="card-wrap" style="padding:16px">', unsafe_allow_html=True)
        st.plotly_chart(fig_bar, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Constituents table ───────────────────────────────────────────────────
    st.markdown('<div class="section-header">Constituents — Live Prices &amp; Market Cap</div>',
                unsafe_allow_html=True)

    with st.spinner("Fetching live prices…"):
        price_cache = {}
        def _fetch_price_desktop(c):
            if c["exchange"] == "NSE":
                return c["ticker"], fetch_nse_price(c["ticker"])
            else:
                return c["ticker"], fetch_nasdaq_price(c["ticker"])
        with ThreadPoolExecutor(max_workers=12) as _px2:
            for _tk2, _pd2 in _px2.map(_fetch_price_desktop, COMPANIES):
                price_cache[_tk2] = _pd2

    th2 = f"padding:10px 12px;color:#8b6d4a;font-weight:600;font-size:12px"
    tbl = (
        f"<div class='card-wrap' style='padding:0;overflow-x:auto'>"
        f"<table style='width:100%;border-collapse:collapse;font-size:13px'>"
        f"<thead><tr style='background:{BG_ALT}'>"
        f"<th style='text-align:left;{th2}'>#</th>"
        f"<th style='text-align:left;{th2}'>Company</th>"
        f"<th style='text-align:left;{th2}'>Sector</th>"
        f"<th style='text-align:left;{th2}'>Ticker</th>"
        f"<th style='text-align:right;{th2}'>Price</th>"
        f"<th style='text-align:right;{th2}'>Day Chg</th>"
        f"<th style='text-align:right;{th2}'>1M Chg</th>"
        f"<th style='text-align:right;{th2}'>Mkt Cap Chg (Since Listing)†</th>"
        f"<th style='text-align:right;{th2}'>Mkt Cap Chg (Since Jan 2024)</th>"
        f"<th style='text-align:right;{th2}'>Mkt Cap (₹ Mn)</th>"
        f"<th style='text-align:right;{th2}'>Mkt Cap ($ Mn)</th>"
        f"<th style='text-align:right;{th2}'>Float %</th>"
        f"</tr></thead><tbody>"
    )

    for c in COMPANIES:
        q    = price_cache.get(c["ticker"], {})
        px   = q.get("price")
        pct  = q.get("pct_change")
        m1   = returns_1m.get(c["ticker"])
        lh   = long_hist.get(c["ticker"], {})
        s_listing = lh.get("since_listing_pct")
        s_2024    = lh.get("since_jan2024_pct")
        list_date = lh.get("listing_date", "")

        px_str = (f"₹{px:,.2f}" if c["exchange"] == "NSE"
                  else f"${px:,.2f}") if px else "—"

        # market cap
        mc_data = live_mktcaps.get(c["ticker"])
        if mc_data:
            if mc_data["currency"] == "INR":
                mc_inr = round(mc_data["mc"], 0)
                mc_usd = round(mc_data["mc"] / usdinr, 0)
            else:
                mc_usd = round(mc_data["mc"], 0)
                mc_inr = round(mc_data["mc"] * usdinr, 0)
        else:
            mc_inr = round(c["mkt_cap_mn"], 0)
            mc_usd = round(c["mkt_cap_mn"] / usdinr, 0)

        listing_str = (f'{_fmt_chg(s_listing, 1)}'
                       f'<div style="color:#a38060;font-size:10px">from {list_date}</div>'
                       if s_listing is not None else '<span style="color:#a38060">—</span>')

        tbl += (
            f"<tr style='border-top:1px solid {BORDER}'>"
            f"<td style='padding:9px 12px;color:#a38060'>{c['num']}</td>"
            f"<td style='padding:9px 12px;color:#1a0f00;font-weight:500'>{c['name']}</td>"
            f"<td style='padding:9px 12px'>{badge(c['sector'])}</td>"
            f"<td style='padding:9px 12px;color:#c2410c;font-family:monospace;font-size:12px'>{c['ticker']}</td>"
            f"<td style='padding:9px 12px;text-align:right;color:#1a0f00;font-weight:500'>{px_str}</td>"
            f"<td style='padding:9px 12px;text-align:right'>{_fmt_chg(pct)}</td>"
            f"<td style='padding:9px 12px;text-align:right'>{_fmt_chg(m1)}</td>"
            f"<td style='padding:9px 12px;text-align:right'>{listing_str}</td>"
            f"<td style='padding:9px 12px;text-align:right'>{_fmt_chg(s_2024, 1)}</td>"
            f"<td style='padding:9px 12px;text-align:right;color:#4a3520'>{mc_inr:,.0f}</td>"
            f"<td style='padding:9px 12px;text-align:right;color:#4a3520'>{mc_usd:,.0f}</td>"
            f"<td style='padding:9px 12px;text-align:right;color:#4a3520'>{c['float_pct']:.1f}%</td>"
            f"</tr>"
        )

    tbl += (
        f"</tbody></table>"
        f"<div style='padding:10px 14px;color:#a38060;font-size:11px'>"
        f"† Market cap % change uses split-adjusted prices (adjusted for stock splits &amp; bonus issues, "
        f"NOT for dividends) — equivalent to true market-cap % change. "
        f"Data from Jan 2019 or IPO date, whichever is later. "
        f"Live market cap from NSE / NYSE (Yahoo Finance), refreshed hourly. "
        f"USD at ₹{usdinr}/$ live rate.</div></div>"
    )
    st.markdown(tbl, unsafe_allow_html=True)

    # ── Company Deep Dive ────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Company Deep Dive</div>', unsafe_allow_html=True)
    st.markdown(
        '<div style="color:#8b6d4a;font-size:12px;margin-bottom:12px">'
        'Select any company to view key stats and financial statements (refreshed hourly).'
        '</div>', unsafe_allow_html=True,
    )

    company_options = ["— Select a company —"] + [f"{c['name']}  ({c['ticker']})" for c in COMPANIES]
    selected = st.selectbox("Company", company_options, label_visibility="collapsed")

    if selected != "— Select a company —":
        idx = company_options.index(selected) - 1
        chosen = COMPANIES[idx]
        # Disk-cached + parallel fetch — no blocking spinner needed
        details = fetch_company_details(yf_ticker(chosen))
        # Enrich with pre-fetched analyst data (fills gaps — never overwrites with None)
        pre = all_analyst.get(chosen["ticker"], {})
        if pre:
            current_info = details.get("info", {})
            # Map from pre-fetched keys → yfinance info field names
            pre_to_info = {
                "targetLow":       "targetLowPrice",
                "targetHigh":      "targetHighPrice",
                "targetMean":      "targetMeanPrice",
                "targetMedian":    "targetMedianPrice",
                "currentPrice":    "currentPrice",
                "trailingPE":      "trailingPE",
                "forwardPE":       "forwardPE",
                "trailingEps":     "trailingEps",
                "beta":            "beta",
                "fiftyTwoWeekLow": "fiftyTwoWeekLow",
                "fiftyTwoWeekHigh":"fiftyTwoWeekHigh",
                "dividendYield":   "dividendYield",
                "averageVolume":   "averageVolume",
                "numberOfAnalysts":"numberOfAnalystOpinions",
                "recommendationKey":"recommendationKey",
            }
            # Only update when pre-fetched value is not None (never wipe existing data)
            for pre_key, info_key in pre_to_info.items():
                val = pre.get(pre_key)
                if val is not None:
                    current_info[info_key] = val
            details["info"] = current_info

            # Also update price_targets if we have better data
            if pre.get("targetMean"):
                details["price_targets"] = {
                    "low":     pre.get("targetLow"),
                    "high":    pre.get("targetHigh"),
                    "mean":    pre.get("targetMean"),
                    "median":  pre.get("targetMedian"),
                    "current": pre.get("currentPrice"),
                }

            # Use pre-fetched recommendations if live fetch came back empty
            pre_recs = pre.get("recommendations")
            if pre_recs is not None and not pre_recs.empty:
                live_recs = details.get("recommendations")
                if live_recs is None or (hasattr(live_recs, "empty") and live_recs.empty):
                    details["recommendations"] = pre_recs

            # Use pre-fetched earnings_history if live fetch came back empty
            pre_earn = pre.get("earnings_history")
            if pre_earn is not None and not pre_earn.empty:
                live_earn = details.get("earnings_history")
                if live_earn is None or (hasattr(live_earn, "empty") and live_earn.empty):
                    details["earnings_history"] = pre_earn
        price_data = price_cache.get(chosen["ticker"], {})
        mc_data    = live_mktcaps.get(chosen["ticker"])
        render_company_deep_dive(chosen, details, usdinr, price_data, mc_data)

    # ── Sector breakdown ─────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Sector Composition</div>', unsafe_allow_html=True)

    sector_counts = {}
    for c in COMPANIES:
        sector_counts[c["sector"]] = sector_counts.get(c["sector"], 0) + 1

    s_df = pd.DataFrame([
        {"Sector": k, "Count": v, "Color": SECTOR_COLORS.get(k, "#8b6d4a")}
        for k, v in sorted(sector_counts.items(), key=lambda x: -x[1])
    ])

    # Pastel colors + short display labels for the donut chart only
    _PIE_PASTELS = {
        "Fintech / Financial Services": "#D6E4FF",
        "Consumer / Consumer Tech":     "#D4EDDA",
        "B2B":                          "#E8D5F5",
        "SaaS / AI":                    "#D1ECF1",
    }
    _PIE_SHORT = {
        "Fintech / Financial Services": "Fintech / Fin. Services",
        "Consumer / Consumer Tech":     "Consumer Tech",
        "B2B":                          "B2B",
        "SaaS / AI":                    "SaaS / AI",
    }
    pie_colors  = [_PIE_PASTELS.get(s, "#eeeeee") for s in s_df["Sector"]]
    pie_labels  = [_PIE_SHORT.get(s, s)            for s in s_df["Sector"]]

    col_pie, col_bar2 = st.columns([1, 2])
    with col_pie:
        fig_pie = go.Figure(go.Pie(
            labels=pie_labels,
            values=s_df["Count"],
            hole=0.5,
            marker=dict(
                colors=pie_colors,
                line=dict(color="#cccccc", width=1.5),
            ),
            textinfo="label+percent",
            textposition="inside",
            insidetextorientation="horizontal",
            textfont=dict(size=11, color="#1a1a1a"),
            automargin=True,
            hovertext=s_df["Sector"],
            hovertemplate="%{hovertext}: %{value} companies (%{percent})<extra></extra>",
        ))
        fig_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            uniformtext_minsize=9,
            uniformtext_mode="hide",
            margin=dict(l=10, r=10, t=10, b=10),
            height=420,
        )
        st.plotly_chart(fig_pie, use_container_width=True)

        # Clean HTML legend with full sector names + pastel swatches
        legend_parts = []
        for s, v in zip(s_df["Sector"], s_df["Count"]):
            bg = _PIE_PASTELS.get(s, "#eeeeee")
            legend_parts.append(
                f"<span style='display:inline-flex;align-items:center;margin:3px 10px 3px 0'>"
                f"<span style='width:13px;height:13px;border-radius:3px;background:{bg};"
                f"border:1px solid #ccc;display:inline-block;margin-right:5px'></span>"
                f"<span style='font-size:11px;color:#1a1a1a'>{s} ({int(v)})</span></span>"
            )
        legend_html = "".join(legend_parts)
        st.markdown(
            f"<div style='text-align:center;margin-top:-8px;line-height:1.8'>{legend_html}</div>",
            unsafe_allow_html=True,
        )

    with col_bar2:
        fig_sb = go.Figure(go.Bar(
            x=s_df["Count"], y=s_df["Sector"], orientation="h",
            marker_color=s_df["Color"].tolist(),
            text=s_df["Count"], textposition="outside",
            textfont=dict(color="#4a3520"),
            hovertemplate="%{y}: %{x}<extra></extra>",
        ))
        fig_sb.update_layout(
            paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            yaxis=dict(showgrid=False, color="#4a3520"),
            margin=dict(l=0, r=40, t=0, b=0), height=300,
        )
        st.plotly_chart(fig_sb, use_container_width=True)

    # ── Index Changes Log ────────────────────────────────────────────────────
    _INDEX_CHANGES = [
        {"date": "16 Feb 2026", "action": "IN",  "company": "Aye Finance",
         "symbol": "AYE",       "sector": "Fintech / Financial Services",
         "replaces": "Smartworks", "reason": "New listing — MSME lending NBFC"},
        {"date": "16 Feb 2026", "action": "OUT", "company": "Smartworks",
         "symbol": "SMARTWORKS", "sector": "B2B",
         "replaces": "",        "reason": "Replaced by Aye Finance"},
        {"date": "8 May 2026",  "action": "IN",  "company": "Kissht (OnEMI Technology)",
         "symbol": "KISSHT",    "sector": "Fintech / Financial Services",
         "replaces": "Awfis", "reason": "New listing — consumer lending fintech"},
        {"date": "8 May 2026",  "action": "OUT", "company": "Awfis Space Solutions",
         "symbol": "AWFIS",     "sector": "B2B",
         "replaces": "",        "reason": "Replaced by Kissht"},
    ]
    with st.expander("Index Changes — Constituent History", expanded=False):
        th_s = "padding:8px 12px;color:#8b6d4a;font-weight:600;font-size:12px;text-align:left"
        td_s = "padding:8px 12px;font-size:13px;color:#4a3520;border-top:1px solid " + BORDER
        rows_html = ""
        for chg in _INDEX_CHANGES:
            action_color = "#16a34a" if chg["action"] == "IN" else "#dc2626"
            action_badge = (f"<span style='background:{action_color}20;color:{action_color};"
                            f"font-weight:700;padding:2px 8px;border-radius:4px;font-size:11px'>"
                            f"{chg['action']}</span>")
            rows_html += (
                f"<tr>"
                f"<td style='{td_s}'>{chg['date']}</td>"
                f"<td style='{td_s}'>{action_badge}</td>"
                f"<td style='{td_s}'><b>{chg['company']}</b></td>"
                f"<td style='{td_s};font-family:monospace'>{chg['symbol']}</td>"
                f"<td style='{td_s}'>{chg['sector']}</td>"
                f"<td style='{td_s};color:#8b6d4a'>{chg['reason']}</td>"
                f"</tr>"
            )
        st.markdown(
            f"<div style='overflow-x:auto'>"
            f"<table style='width:100%;border-collapse:collapse'>"
            f"<thead><tr style='background:{BG_ALT}'>"
            f"<th style='{th_s}'>Date</th>"
            f"<th style='{th_s}'>Action</th>"
            f"<th style='{th_s}'>Company</th>"
            f"<th style='{th_s}'>Symbol</th>"
            f"<th style='{th_s}'>Sector</th>"
            f"<th style='{th_s}'>Reason</th>"
            f"</tr></thead><tbody>{rows_html}</tbody></table></div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div style='font-size:11px;color:#8b6d4a;margin-top:8px'>"
            "Divisor smoothing applied at each change date — index value continuous across all transitions."
            "</div>",
            unsafe_allow_html=True,
        )

    # ── Methodology ──────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Methodology</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class='card-wrap' style='color:#4a3520;font-size:13px;line-height:1.8'>
        <b style='color:#1a0f00'>Index Construction</b> — Free-float market-cap weighted index using the same
        methodology as NSE sectoral indices:&nbsp;
        <code style='background:{BG};padding:2px 8px;border-radius:4px;color:#c2410c'>
            Index = Σ(Free-Float Market Cap) / Divisor
        </code><br><br>
        <b style='color:#1a0f00'>Divisor Smoothing</b> — When a company is added or removed, the divisor adjusts
        to prevent discontinuous jumps, preserving historical continuity.<br><br>
        <b style='color:#1a0f00'>Float Data</b> — Float % from BSE/NSE (Free Float Mkt Cap ÷ Full Mkt Cap),
        refreshed quarterly from SEBI filings.<br><br>
        <b style='color:#1a0f00'>Market Cap</b> — Live market cap from NSE (INR) and NYSE/NASDAQ (USD) via
        Yahoo Finance, refreshed hourly. USD converted at live USD/INR rate.<br><br>
        <b style='color:#1a0f00'>Mkt Cap % Change (Since Listing / Since Jan 2024)</b> — Uses raw prices
        adjusted only for stock splits and bonus issues (not dividends). This gives the true market-cap
        % change: a 2-for-1 split halves the price but doubles shares, so market cap is unchanged and
        our calculation reflects that correctly. Data sourced from NSE / NYSE via Yahoo Finance.<br><br>
        <b style='color:#1a0f00'>NASDAQ Stocks</b> — MakeMyTrip (MMYT) and Freshworks (FRSH) priced in USD,
        converted to INR at the live exchange rate.<br><br>
        <b style='color:#1a0f00'>Base Date</b> — 1 January 2024 = 100 for Z47'47, Nifty 50, and Sensex.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)

    # ── Z47 Assistant (bottom of index page, collapsible) ────────────────────
    st.markdown("---")
    render_z47_assistant(
        context="z47_index",
        label="💬 Ask Z47 Assistant",
        extra_context=build_data_context(df, returns_1m, live_mktcaps, usdinr, nifty_live, sensex_live),
    )


if __name__ == "__main__":
    main()
