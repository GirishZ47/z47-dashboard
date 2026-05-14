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
from z47_assistant import render_z47_assistant, ask_z47_with_search, SYSTEM_PROMPTS, _SEARCH_GUIDANCE

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
    page_title="Z47 Index",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Colour palette ────────────────────────────────────────────────────────────
BG      = "#fdf6ec"   # page background — warm cream
CARD_BG = "#f6f9fd"   # cards / charts — barely-there blue tint
BG_ALT  = "#edf3fa"   # table header rows / alternating rows
BORDER  = "#ccdaea"   # soft blue-grey border

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
    """Income statement, balance sheet, cash flow — slow-changing data."""
    try:
        t = yf.Ticker(yf_tk)
        result = {}
        for key, attr in [
            ("income_annual",      "financials"),
            ("income_quarterly",   "quarterly_financials"),
            ("balance_annual",     "balance_sheet"),
            ("balance_quarterly",  "quarterly_balance_sheet"),
            ("cashflow_annual",    "cashflow"),
            ("cashflow_quarterly", "quarterly_cashflow"),
        ]:
            try:    result[key] = getattr(t, attr)
            except: result[key] = pd.DataFrame()
        return result
    except Exception:
        return {}


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
                xaxis=dict(showgrid=False, color="#a38060", tickprefix=sym),
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
    tab_is, tab_bs, tab_cf, tab_earn, tab_analyst, tab_news = st.tabs([
        "📊 Income Statement",
        "🏦 Balance Sheet",
        "💸 Cash Flow",
        "📈 Earnings Trends",
        "🎯 Analyst Insights",
        "📰 Recent News",
    ])

    tk = c["ticker"]
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
        ("z47_float",      "Z47's 47", "#c2410c", 2.5),   # warm orange for Z47
        ("nifty_indexed",  "Nifty 50", "#1d4ed8", 2.0),
        ("sensex_indexed", "Sensex",   "#15803d", 2.0),
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
        f"Z47's 47 Index: {z47_now:.1f} (rebased to 100 on 1 Jan 2024)",
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
        f'<div style="color:#1a0f00;font-size:24px;font-weight:800;margin-bottom:2px">Z47 Index</div>'
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
            f'<div class="mobile-kpi"><div class="mobile-kpi-label">Z47\'s 47</div>'
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
            f'<div class="{oc}" style="margin-top:4px">{oa} {abs(outperf):.1f} pp</div></div>',
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
        for c in COMPANIES:
            if c["exchange"] == "NSE":
                price_cache[c["ticker"]] = fetch_nse_price(c["ticker"])
            else:
                price_cache[c["ticker"]] = fetch_nasdaq_price(c["ticker"])

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
    with c1: _nav_btn("📊 Z47 Index",       "nav_z47",   "z47")
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


def main():
    # Session state defaults
    if "nav_page" not in st.session_state:
        st.session_state.nav_page = "z47"
    if "ipo_tab" not in st.session_state:
        st.session_state.ipo_tab = "recent"

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
        main_mobile()
        return

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
            f'<div style="color:#1a0f00;font-size:34px;font-weight:800;margin-bottom:4px">Z47 Index</div>'
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
        (c1, "Z47's 47 Index",  f"{last['z47_float']:.1f}", z47_ret),
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
            f'<div class="{oc}" style="margin-top:4px">{oa} {abs(outperf):.1f} pp vs Nifty</div>'
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
        st.markdown(_rebase_card("Z47's 47 Index", "z47_float",      "#c2410c"), unsafe_allow_html=True)
    with rb2:
        st.markdown(_rebase_card("Nifty 50",       "nifty_indexed",  "#1d4ed8"), unsafe_allow_html=True)
    with rb3:
        st.markdown(_rebase_card("Sensex",         "sensex_indexed", "#15803d"), unsafe_allow_html=True)
    st.markdown("<div style='margin-bottom:12px'></div>", unsafe_allow_html=True)

    # Chart uses the same period already selected above
    st.markdown('<div class="card-wrap" style="padding:16px">', unsafe_allow_html=True)
    st.plotly_chart(make_perf_chart(df, period), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Returns table ────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Returns Summary</div>', unsafe_allow_html=True)

    ret_periods = [("1M", 30), ("3M", 90), ("6M", 180), ("1Y", 365)]
    idx_cols    = [("Z47's 47", "z47_float"),
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
        for c in COMPANIES:
            if c["exchange"] == "NSE":
                price_cache[c["ticker"]] = fetch_nse_price(c["ticker"])
            else:
                price_cache[c["ticker"]] = fetch_nasdaq_price(c["ticker"])

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
        with st.spinner(f"Loading {chosen['name']} details…"):
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
        <b style='color:#1a0f00'>Base Date</b> — 1 January 2024 = 100 for Z47's 47, Nifty 50, and Sensex.
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
