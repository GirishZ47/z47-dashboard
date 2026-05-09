"""Z47 Index — Live Dashboard"""

import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import yfinance as yf
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import anthropic

from companies import COMPANIES, SECTOR_COLORS, yf_ticker

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
#MainMenu, footer, header {{ visibility: hidden; }}
</style>
""", unsafe_allow_html=True)


# ── Data helpers ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_history() -> pd.DataFrame:
    csv_path = os.path.join(os.path.dirname(__file__), "z47_history.csv")
    df = pd.read_csv(csv_path, parse_dates=["date"])
    return df.sort_values("date").reset_index(drop=True)


@st.cache_data(ttl=300)
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


@st.cache_data(ttl=3600)
def get_usdinr() -> float:
    try:
        return round(float(yf.Ticker("USDINR=X").fast_info.last_price), 2)
    except Exception:
        return 85.0


@st.cache_data(ttl=300)
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


@st.cache_data(ttl=300)
def fetch_nasdaq_price(symbol: str) -> dict:
    try:
        fi = yf.Ticker(symbol).fast_info
        price = float(fi.last_price)
        prev  = float(fi.previous_close) if hasattr(fi, "previous_close") else None
        pct   = round((price / prev - 1) * 100, 2) if prev and prev != 0 else None
        return {"price": price, "pct_change": pct, "prev_close": prev}
    except Exception:
        return {}


@st.cache_data(ttl=3600)
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


@st.cache_data(ttl=3600)
def fetch_1m_returns() -> dict[str, float]:
    """Batch download ~35 days of prices for 1-month return calculation."""
    tickers = [yf_ticker(c) for c in COMPANIES]
    end   = pd.Timestamp.today()
    start = end - timedelta(days=37)
    try:
        raw    = yf.download(tickers, start=start.strftime("%Y-%m-%d"),
                             end=end.strftime("%Y-%m-%d"), progress=False, auto_adjust=True)
        closes = raw["Close"]
    except Exception:
        return {}

    result = {}
    for c in COMPANIES:
        tk = yf_ticker(c)
        try:
            s = closes[tk].dropna()
            if len(s) >= 2:
                result[c["ticker"]] = round(float((s.iloc[-1] / s.iloc[0] - 1) * 100), 2)
        except Exception:
            pass
    return result


@st.cache_data(ttl=86400)   # refresh once per day — historical data is stable
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
    color = SECTOR_COLORS.get(sector, "#8b6d4a")
    return (f'<span style="background:{color}18;color:{color};padding:2px 8px;'
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


def stream_ai_response(user_question, data_context):
    api_key = st.secrets.get("ANTHROPIC_API_KEY", os.environ.get("ANTHROPIC_API_KEY", ""))
    if not api_key or api_key.startswith("sk-ant-..."):
        yield "⚠️ No Anthropic API key configured. Add your key to `.streamlit/secrets.toml` under `ANTHROPIC_API_KEY`."
        return

    client = anthropic.Anthropic(api_key=api_key)
    system_prompt = (
        "You are an expert financial analyst for Z47, a venture capital firm that tracks an index "
        "of 47 Indian internet and new-age tech companies. You have access to live index data "
        "provided below. Answer questions clearly and concisely. When quoting numbers, be precise. "
        "If the answer isn't in the data provided, say so and offer what context you can.\n\n"
        + data_context
    )

    try:
        with client.messages.stream(
            model="claude-haiku-4-5",
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_question}],
        ) as stream:
            for text in stream.text_stream:
                yield text
    except anthropic.AuthenticationError:
        yield "⚠️ Invalid API key. Please update `ANTHROPIC_API_KEY` in `.streamlit/secrets.toml` with a valid key from console.anthropic.com."
    except anthropic.RateLimitError:
        yield "⚠️ Rate limit hit. Please wait a moment and try again."
    except Exception as e:
        yield f"⚠️ Error contacting AI: {e}"


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
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
        returns_1m   = fetch_1m_returns()
        long_hist    = fetch_long_history()
        live_mktcaps = fetch_market_caps()

    name_map = {c["ticker"]: c["name"] for c in COMPANIES}

    # ── AI Chatbox ──────────────────────────────────────────────────────────
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
        with st.chat_message("assistant"):
            response_text = st.write_stream(stream_ai_response(prompt, data_ctx))
        st.session_state.chat_messages.append({"role": "assistant", "content": response_text})

    st.markdown("<br>", unsafe_allow_html=True)

    # ── KPI cards ───────────────────────────────────────────────────────────
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

    # ── Performance chart ────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Performance (rebased to 100)</div>', unsafe_allow_html=True)
    period = st.radio("Period", ["1M", "3M", "6M", "1Y", "YTD", "All"],
                      index=5, horizontal=True, label_visibility="collapsed")
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

    # ── Sector breakdown ─────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Sector Composition</div>', unsafe_allow_html=True)

    sector_counts = {}
    for c in COMPANIES:
        sector_counts[c["sector"]] = sector_counts.get(c["sector"], 0) + 1

    s_df = pd.DataFrame([
        {"Sector": k, "Count": v, "Color": SECTOR_COLORS.get(k, "#8b6d4a")}
        for k, v in sorted(sector_counts.items(), key=lambda x: -x[1])
    ])

    col_pie, col_bar2 = st.columns([1, 2])
    with col_pie:
        fig_pie = go.Figure(go.Pie(
            labels=s_df["Sector"], values=s_df["Count"], hole=0.5,
            marker_colors=s_df["Color"].tolist(),
            textinfo="label+percent", textfont=dict(size=11, color="#4a3520"),
            hovertemplate="%{label}: %{value} cos<extra></extra>",
        ))
        fig_pie.update_layout(paper_bgcolor=CARD_BG, showlegend=False,
                              margin=dict(l=0, r=0, t=0, b=0), height=300)
        st.plotly_chart(fig_pie, use_container_width=True)

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


if __name__ == "__main__":
    main()
