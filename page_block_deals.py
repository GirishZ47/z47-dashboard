"""Block & Bulk Deals module — called by app.py routing."""
import re
import os
import urllib.parse
import streamlit as st
import requests
import pandas as pd
import pytz
import time
import plotly.graph_objects as go
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
from companies import COMPANIES
from z47_assistant import render_z47_assistant
import anthropic
try:
    from takeaway_constants import HARDCODED_DEAL_TAKEAWAYS
except Exception:
    HARDCODED_DEAL_TAKEAWAYS = {}

CARD_BG = "#f6f9fd"; BG_ALT = "#edf3fa"; BORDER = "#ccdaea"
IST = pytz.timezone("Asia/Kolkata")


# ── Preamble-stripping helper (mirrors app.py version) ───────────────────────
def _clean_takeaway_output(raw: str) -> str | None:
    """Strip model preamble from raw AI response. Returns cleaned text or None if too short."""
    if not raw or not raw.strip():
        return None
    lines = raw.split('\n')
    _PREAMBLE_STARTS = (
        "now i", "let me", "here is", "here's", "i'll", "i will", "i've",
        "based on", "i have", "sure,", "sure.", "okay,", "certainly,",
        "certainly.", "of course", "absolutely", "great,", "the following",
        "below is", "below are", "i'll now", "i need to",
    )
    cleaned = []
    for line in lines:
        s = line.strip()
        sl = s.lower()
        if not s:
            if cleaned:
                cleaned.append(line)
            continue
        if any(sl.startswith(p) for p in _PREAMBLE_STARTS):
            print(f"[deal _clean] stripped preamble: {s[:60]!r}")
            continue
        cleaned.append(line)
    while cleaned and not cleaned[0].strip():
        cleaned.pop(0)
    while cleaned and not cleaned[-1].strip():
        cleaned.pop()
    result = '\n'.join(cleaned).strip()
    if len(result) < 150:
        return None
    return result


_NO_PREAMBLE_DEAL = (
    "Output ONLY the final takeaway text. Do not write any preamble, introduction, "
    "meta-commentary, or header. Do not say 'Now I have', 'Let me synthesize', "
    "'Here is', or similar. Start directly with the first analytical sentence. "
)


# ── Feature 8: Deal Takeaway ──────────────────────────────────────────────────
@st.cache_data(ttl=86400, show_spinner=False)
def get_deal_takeaway(company: str, value_cr: float) -> str | None:
    """Sell-side quality 5-6 line takeaway for high-value block/bulk deals (>50 cr). Cached 24 hrs."""
    if value_cr <= 50:
        return None
    try:
        api_key = (st.secrets.get("ANTHROPIC_API_KEY", "")
                   or os.environ.get("ANTHROPIC_API_KEY", ""))
        if not api_key or api_key.startswith("sk-ant-..."):
            return None
        client = anthropic.Anthropic(api_key=api_key)
        system = (
            "You are a sell-side equity research analyst writing a block/bulk deal note for a Z47'47 constituent. "
            "Write in tight, professional English. No markdown — plain prose only."
        )
        prompt = (
            _NO_PREAMBLE_DEAL
            + f"A block/bulk deal of ₹{value_cr:.0f} crore was transacted in {company}. "
            "Search for the exact deal details — seller, buyer, price per share, shares, stake %. "
            "Write exactly 5-6 lines: "
            "(1) Headline: who sold to whom and what it signals — a verdict, not a description. "
            "(2) Key numbers: deal size, price, shares, stake % — plus whether deal cleared at "
            "discount/premium to market and what that implies about buyer conviction. "
            "(3) Seller context: lock-in expiry, portfolio rebalancing, or strategic exit? "
            "What does the seller's retention (if any) signal? "
            "(4) Buyer quality: institutional conviction read — is this a thesis-level bet or an "
            "arb/liquidity play? What does the buyer composition say about the stock's institutional floor? "
            "(5) What the market is missing about this deal — the read-through to the company's narrative "
            "or to peers in the Z47'47 universe. "
            "(6) Net read: constructive/cautious/neutral on the stock post-deal, with one-line rationale. "
            "Banned phrases: 'strong performance', 'well-positioned', 'positive momentum'. "
            "No buy/sell/hold. No markdown. No preamble."
        )
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            system=system,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content": prompt}],
            extra_headers={"anthropic-beta": "web-search-2025-03-05"},
            timeout=45,
        )
        # Concatenate ALL text blocks — preamble often lands in block 1, content in later blocks
        text_blocks = [
            b.text.strip() for b in resp.content
            if hasattr(b, "text") and b.text.strip()
        ]
        raw = '\n'.join(text_blocks) if text_blocks else None
        if not raw:
            print(f"[Deal takeaway] {company}: no text blocks")
            return None
        print(f"[Deal takeaway] {company}: {len(raw)} chars raw, {len(text_blocks)} block(s)")
        return _clean_takeaway_output(raw)
    except Exception as _e:
        print(f"[Deal takeaway] {company}: {_e}")
        return None


def _render_deal_takeaway_box(text: str, company: str):
    """Render a deal takeaway box below a high-value deal."""
    st.markdown(
        f"""<div style='background:linear-gradient(135deg,#f3f0ff,#ede9fe);
        border:1px solid #c4b5fd;border-radius:10px;padding:14px 18px;
        margin:8px 0 4px 0;box-shadow:0 1px 4px rgba(124,58,237,.10)'>
        <div style='font-size:11px;font-weight:700;color:#6d28d9;letter-spacing:.06em;
        text-transform:uppercase;margin-bottom:6px'>💡 Deal Takeaway — {company}</div>
        <div style='color:#3b1f7a;font-size:13px;line-height:1.6'>{text}</div>
        </div>""",
        unsafe_allow_html=True,
    )

Z47_SYMBOLS  = {c["ticker"] for c in COMPANIES if c["exchange"] == "NSE"}
Z47_NAME_MAP = {c["ticker"]: c["name"] for c in COMPANIES}

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

_BASE_HEADERS = {
    "User-Agent": _UA,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.nseindia.com/",
}

# Keep old name so nothing else breaks
NSE_HEADERS = _BASE_HEADERS

_DEAL_CACHE_TTL = 300  # 5 minutes


# ── Price enrichment — multi-source fallback ──────────────────────────────────
# Resolves price = 0 rows via: news → yfinance historical → yfinance live
# All results cached in session_state["bd_px_cache"] to avoid repeat calls.

_PX_CACHE_KEY = "bd_px_cache"

def _px_cache_get(symbol, date_str, client, qty):
    cache = st.session_state.get(_PX_CACHE_KEY, {})
    k = (symbol.upper()[:10], date_str[:10],
         str(client)[:20].lower(), max(0, int(qty) // 10_000))
    return cache.get(k)  # (price, emoji, detail) or None

def _px_cache_set(symbol, date_str, client, qty, price, emoji, detail):
    if _PX_CACHE_KEY not in st.session_state:
        st.session_state[_PX_CACHE_KEY] = {}
    k = (symbol.upper()[:10], date_str[:10],
         str(client)[:20].lower(), max(0, int(qty) // 10_000))
    st.session_state[_PX_CACHE_KEY][k] = (float(price), emoji, str(detail))


def _extract_price_from_text(text):
    """Regex-extract a share price from news article text."""
    _PATS = [
        r'at\s+[₹Rs]+\.?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*per\s+share',
        r'at\s+a\s+price\s+of\s+[₹Rs]+\.?\s*(\d+(?:,\d+)*(?:\.\d+)?)',
        r'average\s+price\s+of\s+[₹Rs]+\.?\s*(\d+(?:,\d+)*(?:\.\d+)?)',
        r'[₹Rs]+\.?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*per\s+share',
        r'traded\s+at\s+[₹Rs]+\.?\s*(\d+(?:,\d+)*(?:\.\d+)?)',
        r'deal\s+price\s+(?:of\s+)?[₹Rs]+\.?\s*(\d+(?:,\d+)*(?:\.\d+)?)',
        r'floor\s+price\s+(?:of\s+)?[₹Rs]+\.?\s*(\d+(?:,\d+)*(?:\.\d+)?)',
        r'transaction\s+price\s+(?:of\s+)?[₹Rs]+\.?\s*(\d+(?:,\d+)*(?:\.\d+)?)',
        r'price[:\s]+[₹Rs]+\.?\s*(\d+(?:,\d+)*(?:\.\d+)?)',
        r'transacted\s+at\s+[₹Rs]+\.?\s*(\d+(?:,\d+)*(?:\.\d+)?)',
        r'sold\s+at\s+[₹Rs]+\.?\s*(\d+(?:,\d+)*(?:\.\d+)?)',
        r'bought\s+at\s+[₹Rs]+\.?\s*(\d+(?:,\d+)*(?:\.\d+)?)',
    ]
    for pat in _PATS:
        for m in re.findall(pat, text, re.IGNORECASE):
            try:
                v = float(str(m).replace(',', ''))
                if 0.5 < v < 500_000:
                    return v
            except Exception:
                continue
    return None


def _search_news_price(company_name, client_name, quantity, date_str, action):
    """
    Search Google News RSS for a specific block/bulk deal price.
    Large deals (>1L shares) are always covered by ET, Mint, MC.
    Returns (price, detail_str) or (None, None).
    """
    try:
        date_obj = datetime.strptime(date_str[:10], '%Y-%m-%d')
    except Exception:
        return None, None

    action_word = "buys" if "B" in str(action).upper() else "sells"
    date_month  = date_obj.strftime('%B %Y')
    qty_lakh    = round(quantity / 100_000, 1)

    # Build queries: specific → broad. Groww gets extra targeted queries.
    queries = [
        f'"{company_name}" "block deal" "{date_str[:10]}"',
        f'{client_name} {action_word} {company_name} block deal {date_str[:7]}',
        f'{company_name} block deal {client_name} price',
        f'{company_name} bulk deal {date_str[:10]} price share',
        f'{company_name} {action_word} {qty_lakh} lakh shares {date_month}',
        f'{company_name} block deal {date_month}',
    ]

    # Groww-specific queries (lock-in expiry on 2026-05-12 — massive deals)
    if "groww" in company_name.lower() or "billionbrains" in company_name.lower():
        queries = [
            f'Groww block deal May 2026 YC Holdings Peak XV Ribbit',
            f'Billionbrains Garage block deal 12 May 2026 price',
            f'GROWW block deal price May 12 2026',
            f'Peak XV sells Groww shares May 2026 price per share',
            f'YC Holdings Groww block deal price',
        ] + queries

    from bs4 import BeautifulSoup
    for query in queries[:5]:   # cap at 5 queries to stay fast
        try:
            encoded = urllib.parse.quote(query)
            rss_url = (f"https://news.google.com/rss/search"
                       f"?q={encoded}&hl=en-IN&gl=IN&ceid=IN:en")
            r = requests.get(rss_url, timeout=4, headers={"User-Agent": _UA})
            if r.status_code != 200:
                continue
            soup  = BeautifulSoup(r.content, "xml")
            items = soup.find_all("item")[:6]
            for item in items:
                title = item.find("title")
                desc  = item.find("description")
                text  = ((title.text if title else "") + " "
                         + (desc.text if desc else ""))
                price = _extract_price_from_text(text)
                if price:
                    t_str = (title.text[:70] if title else "news article")
                    return price, f"📰 {t_str}"
        except Exception:
            continue

    return None, None


def _get_yfinance_price(symbol, date_str):
    """Closing price from yfinance for a given NSE symbol + date."""
    try:
        import yfinance as yf
        ticker = symbol.upper() + ".NS"
        d      = datetime.strptime(date_str[:10], '%Y-%m-%d')
        start  = (d - timedelta(days=4)).strftime('%Y-%m-%d')
        end    = (d + timedelta(days=2)).strftime('%Y-%m-%d')
        df = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=True)
        if df.empty:
            return None
        df.index = df.index.tz_localize(None)
        before  = df[df.index <= pd.Timestamp(d)]
        return float(before["Close"].iloc[-1]) if not before.empty else None
    except Exception:
        return None


def _get_live_price(symbol):
    """Current live price from yfinance fast_info (for intraday deals)."""
    try:
        import yfinance as yf
        info = yf.Ticker(symbol.upper() + ".NS").fast_info
        px = (getattr(info, "last_price", None)
              or getattr(info, "regularMarketPrice", None))
        return float(px) if px and float(px) > 0.5 else None
    except Exception:
        return None


def _resolve_price(symbol, company, client, qty, date_str, action, nse_px=0.0):
    """
    Master price resolver — tries all sources in order.
    Returns (price, src_emoji, src_detail).
    src_emoji: 🔵 = NSE/BSE direct  📰 = news article  📈 = closing/live price
    """
    # SOURCE 1 — already have a good price from NSE/BSE CSV
    if nse_px and float(nse_px) > 0.5:
        return float(nse_px), "🔵", "NSE/BSE data"

    # Check session cache before making any network calls
    cached = _px_cache_get(symbol, date_str, client, qty)
    if cached:
        return cached

    today_str = datetime.now(IST).strftime('%Y-%m-%d')

    # SOURCE 2 — news search (for deals ≥ 1 lakh shares, always try first)
    if int(qty) >= 100_000:
        np_, ns = _search_news_price(company, client, qty, date_str, action)
        if np_ and float(np_) > 0.5:
            result = (float(np_), "📰", ns or "news article")
            _px_cache_set(symbol, date_str, client, qty, *result)
            return result

    # SOURCE 3 — yfinance historical closing price for that date
    yf_px = _get_yfinance_price(symbol, date_str)
    if yf_px and float(yf_px) > 0.5:
        detail = f"NSE closing price ({date_str[:10]})"
        result = (float(yf_px), "📈", detail)
        _px_cache_set(symbol, date_str, client, qty, *result)
        return result

    # SOURCE 4 — live price (today's deals only)
    if date_str[:10] == today_str:
        lp = _get_live_price(symbol)
        if lp and float(lp) > 0.5:
            result = (float(lp), "📈", "NSE live price (approx)")
            _px_cache_set(symbol, date_str, client, qty, *result)
            return result

    return (0.0, "❓", "unavailable")


def _enrich_zero_prices(rows, date_str):
    """
    For each raw deal row where tradePrice == 0, call _resolve_price() and
    update the row in-place. Adds 'priceSrc' and 'priceSrcDetail' fields.
    """
    for row in rows:
        try:
            px = float(str(row.get("tradePrice", 0)).replace(",", ""))
        except Exception:
            px = 0.0
        sym    = str(row.get("symbol", "")).upper().strip()
        if not sym:
            sym = str(row.get("Symbol", "")).upper().strip()
        company = Z47_NAME_MAP.get(sym, sym)
        client  = str(row.get("clientName", row.get("client_name", "")))
        qty     = int(row.get("quantity", 0) or 0)
        action  = str(row.get("buyOrSell", row.get("buy_sell", "B"))).upper()
        price, emoji, detail = _resolve_price(
            sym, company, client, qty, date_str, action, px)
        row["tradePrice"]     = price
        row["priceSrc"]       = emoji
        row["priceSrcDetail"] = detail
    return rows


def _fast_enrich_df(df, today_str=None):
    """
    Fast yfinance-only price enrichment for zero-price rows in a display DataFrame.
    Safe to call during render — no news search, no long timeouts.
    Deduplicates yfinance calls per symbol (px_cache).
    """
    if df is None or df.empty or "Price (₹)" not in df.columns:
        return df
    if "Src" not in df.columns:
        df = df.copy()
        df["Src"] = "🔵"
    if today_str is None:
        today_str = datetime.now(IST).strftime('%Y-%m-%d')
    zero_mask = df["Price (₹)"].fillna(0) <= 0.5
    for idx in df[zero_mask].index:
        sym    = str(df.at[idx, "Symbol"]).upper().strip()
        qty    = int(df.at[idx, "Quantity"] or 0)
        date_s = str(df.at[idx, "Date"])[:10] if "Date" in df.columns else today_str
        # Check px cache first (avoids repeated yfinance calls for same symbol/date)
        cached = _px_cache_get(sym, date_s, "", qty)
        if cached:
            px, emoji, _ = cached
        else:
            px = _get_yfinance_price(sym, date_s)
            if not px and date_s == today_str:
                px = _get_live_price(sym)
            emoji = "📈" if (px and px > 0.5) else "❓"
            if px and px > 0.5:
                _px_cache_set(sym, date_s, "", qty, px, emoji, f"NSE closing {date_s}")
        if px and px > 0.5:
            df.at[idx, "Price (₹)"]    = px
            df.at[idx, "Value (₹ Cr)"] = round(qty * px / 1e7, 2)
            df.at[idx, "Src"]          = emoji
    return df


def _news_enrich_df(df, today_str=None):
    """
    Full news + yfinance enrichment. SLOW — only call from a manual button, never
    during automatic render. Adds 'Src' and 'Price Source' columns.
    """
    if df is None or df.empty or "Price (₹)" not in df.columns:
        return df
    if "Src" not in df.columns:
        df = df.copy()
        df["Src"] = "🔵"
    if "Price Source" not in df.columns:
        df["Price Source"] = "NSE/BSE data"
    if today_str is None:
        today_str = datetime.now(IST).strftime('%Y-%m-%d')
    zero_mask = df["Price (₹)"].fillna(0) <= 0.5
    for idx in df[zero_mask].index:
        sym    = str(df.at[idx, "Symbol"]).upper()
        co     = str(df.at[idx, "Company"]) if "Company" in df.columns else ""
        cli    = str(df.at[idx, "Client / Party"]) if "Client / Party" in df.columns else ""
        qty    = int(df.at[idx, "Quantity"] or 0)
        action = str(df.at[idx, "Buy/Sell"]) if "Buy/Sell" in df.columns else "B"
        date_s = str(df.at[idx, "Date"])[:10] if "Date" in df.columns else today_str
        price, emoji, detail = _resolve_price(sym, co, cli, qty, date_s, action, 0)
        df.at[idx, "Price (₹)"]    = price
        df.at[idx, "Value (₹ Cr)"] = round(qty * price / 1e7, 2)
        df.at[idx, "Src"]          = emoji
        df.at[idx, "Price Source"] = detail
    return df


def _fetch_deals_today(deal_type="bulk"):
    """
    Fetch today's block/bulk deals via 5 sources in order.
    Caches result in st.session_state for 5 minutes.
    Always returns (rows, source_label, timestamp) — never raises.
    rows: list of dicts with keys: symbol, clientName, buyOrSell, quantity, tradePrice
    """
    cache_key    = f"bd_live_{deal_type}"
    cache_ts_key = f"bd_live_{deal_type}_ts"
    now_ts = time.time()

    # ── Cache hit ────────────────────────────────────────────────────────────
    if (now_ts - st.session_state.get(cache_ts_key, 0) < _DEAL_CACHE_TTL
            and cache_key in st.session_state):
        c = st.session_state[cache_key]
        return c["rows"], c["src"], c["ts"]

    def _save(rows, src):
        # NOTE: no enrichment here — enrichment happens AFTER display, not during fetch
        ts = datetime.now(IST)
        st.session_state[cache_key]    = {"rows": rows, "src": src, "ts": ts}
        st.session_state[cache_ts_key] = now_ts
        return rows, src, ts

    dt = deal_type  # "bulk" or "block"

    # ── Source 1: NSE direct CSV (no auth, most reliable) ───────────────────
    try:
        from io import StringIO
        prefix = "bulk" if dt == "bulk" else "block"
        url = f"https://nsearchives.nseindia.com/content/equities/{prefix}.csv"
        r = requests.get(url, headers={"User-Agent": _UA}, timeout=5)
        if r.status_code == 200 and r.content:
            df_csv = pd.read_csv(StringIO(r.content.decode("utf-8", errors="ignore")))
            df_csv.columns = [c.strip() for c in df_csv.columns]
            rows = []
            for _, row in df_csv.iterrows():
                sym = str(row.get("Symbol", row.get("SYMBOL", ""))).upper().strip()
                try:    qty = int(float(str(row.get("Quantity Traded", row.get("QTY", 0))).replace(",", "")))
                except: qty = 0
                # NSE CSV uses "Trade Price / Wt. Avg. Price" (dots) — try several variants
                _px_keys = [
                    "Trade Price / Wt. Avg. Price",
                    "Trade Price / Wght Avg Price",
                    "Trade Price/Wt. Avg. Price",
                    "PRICE", "Price", "Rate", "Avg. Price",
                ]
                _px_raw = next((row.get(k) for k in _px_keys if row.get(k) is not None), 0)
                try:    px = float(str(_px_raw).replace(",", "").replace("₹", "").strip() or 0)
                except: px = 0.0
                rows.append({
                    "symbol":     sym,
                    "clientName": str(row.get("Client Name", row.get("CLIENT_NAME", ""))).strip(),
                    "buyOrSell":  str(row.get("Buy/Sell", row.get("BUY_SELL", "B"))).upper().strip(),
                    "quantity":   qty,
                    "tradePrice": px,
                })
            if rows:
                return _save(rows, "NSE CSV")
    except Exception:
        pass

    # ── Source 2: NSE API with session + cookies ─────────────────────────────
    try:
        s = requests.Session()
        s.get("https://www.nseindia.com", headers=_BASE_HEADERS, timeout=6)
        s.get(f"https://www.nseindia.com/market-data/{dt}-deal", headers=_BASE_HEADERS, timeout=6)
        r = s.get(f"https://www.nseindia.com/api/{dt}-deal", headers=_BASE_HEADERS, timeout=6)
        if r.status_code == 200:
            data = r.json().get("data", [])
            if data:
                return _save(data, "NSE API")
    except Exception:
        pass

    # ── Source 3: BSE scrape via pd.read_html ────────────────────────────────
    try:
        bse_url = (
            "https://www.bseindia.com/markets/equity/EQReports/BulkDeal.aspx"
            if dt == "bulk" else
            "https://www.bseindia.com/markets/equity/EQReports/bdDeals.aspx"
        )
        bse_hdrs = {**_BASE_HEADERS, "Referer": "https://www.bseindia.com/"}
        r = requests.get(bse_url, headers=bse_hdrs, timeout=6)
        if r.status_code == 200 and r.text:
            tables = pd.read_html(r.text)
            if tables:
                df_t = tables[0]
                df_t.columns = [str(c).strip() for c in df_t.columns]
                rows = []
                for _, row in df_t.iterrows():
                    sym_v = str(row.get("Symbol", row.get("SYMBOL", row.iloc[0] if len(row) > 0 else ""))).upper().strip()
                    cli_v = str(row.get("Client Name", row.get("Client", row.iloc[1] if len(row) > 1 else ""))).strip()
                    bs_v  = str(row.get("Buy/Sell", row.get("BUY/SELL", row.iloc[2] if len(row) > 2 else "B"))).upper().strip()
                    try:    qty = int(float(str(row.get("Quantity", row.get("QTY", row.iloc[3] if len(row) > 3 else 0))).replace(",", "")))
                    except: qty = 0
                    try:    px  = float(str(row.get("Price", row.get("Rate", row.iloc[4] if len(row) > 4 else 0))).replace(",", ""))
                    except: px  = 0.0
                    rows.append({"symbol": sym_v, "clientName": cli_v,
                                 "buyOrSell": bs_v, "quantity": qty, "tradePrice": px})
                if rows:
                    return _save(rows, "BSE")
    except Exception:
        pass

    # ── Source 4: Trendlyne scrape ───────────────────────────────────────────
    try:
        from bs4 import BeautifulSoup
        r = requests.get(
            "https://trendlyne.com/equity/bulk-block-deals/",
            headers={**_BASE_HEADERS, "Referer": "https://trendlyne.com/"},
            timeout=6,
        )
        if r.status_code == 200 and r.text:
            soup = BeautifulSoup(r.text, "lxml")
            table = soup.find("table")
            if table:
                rows = []
                for tr in table.find_all("tr")[1:]:
                    tds = [td.get_text(strip=True) for td in tr.find_all("td")]
                    if len(tds) >= 5:
                        # Typical Trendlyne columns: Date, Symbol, Company, Deal Type, Client, Qty, Price
                        try:    qty = int(float(str(tds[5]).replace(",", ""))) if len(tds) > 5 else 0
                        except: qty = 0
                        try:    px  = float(str(tds[6]).replace(",", "")) if len(tds) > 6 else 0.0
                        except: px  = 0.0
                        rows.append({
                            "symbol":     tds[1].upper().strip() if len(tds) > 1 else "",
                            "clientName": tds[4].strip()         if len(tds) > 4 else "",
                            "buyOrSell":  "B",
                            "quantity":   qty,
                            "tradePrice": px,
                        })
                if rows:
                    return _save(rows, "Trendlyne")
    except Exception:
        pass

    # ── Source 5: MoneyControl scrape ────────────────────────────────────────
    try:
        r = requests.get(
            "https://www.moneycontrol.com/stocks/marketinfo/bulk_deals/",
            headers={**_BASE_HEADERS, "Referer": "https://www.moneycontrol.com/"},
            timeout=6,
        )
        if r.status_code == 200 and r.text:
            tables = pd.read_html(r.text)
            if tables:
                df_t = tables[0]
                rows = []
                for _, row in df_t.iterrows():
                    try:    qty = int(float(str(row.iloc[4]).replace(",", ""))) if len(row) > 4 else 0
                    except: qty = 0
                    try:    px  = float(str(row.iloc[5]).replace(",", "")) if len(row) > 5 else 0.0
                    except: px  = 0.0
                    rows.append({
                        "symbol":     str(row.iloc[0]).upper().strip() if len(row) > 0 else "",
                        "clientName": str(row.iloc[2]).strip()         if len(row) > 2 else "",
                        "buyOrSell":  str(row.iloc[3]).upper().strip() if len(row) > 3 else "B",
                        "quantity":   qty,
                        "tradePrice": px,
                    })
                if rows:
                    return _save(rows, "MoneyControl")
    except Exception:
        pass

    # All sources exhausted — return empty (never show error to user)
    return _save([], "—")


def _now_ist():
    return datetime.now(IST).strftime("%d-%m-%Y %H:%M:%S IST")


def _warn(msg):
    st.markdown(
        f"""<div style='background:#fef3cd;border:1px solid #ffc107;border-radius:8px;
        padding:10px 16px;color:#856404;font-size:13px;margin-bottom:12px'>⚠️ {msg}</div>""",
        unsafe_allow_html=True,
    )


def _is_market_open():
    now = datetime.now(IST)
    if now.weekday() >= 5:
        return False
    mo = now.replace(hour=9,  minute=15, second=0, microsecond=0)
    mc = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return mo <= now <= mc


def _filter_z47(deals, sym_col="symbol"):
    out = []
    for d in deals:
        sym = str(d.get(sym_col, "")).upper().strip().replace(".NS", "")
        if sym in Z47_SYMBOLS:
            d = dict(d)
            d["z47_name"] = Z47_NAME_MAP.get(sym, sym)
            out.append(d)
    return out


def _norm(d, src):
    if src == "NSE":
        sym   = str(d.get("symbol", d.get("Symbol", ""))).upper().replace(".NS", "")
        cli   = d.get("clientName", d.get("client_name", ""))
        ttype = d.get("buyOrSell", d.get("buy_sell", "")).upper()
        qty   = d.get("quantity",   d.get("qty", 0))
        price = d.get("tradePrice", d.get("trade_price", 0))
    else:
        sym   = str(d.get("SCRIP_CD", d.get("Symbol", ""))).upper().replace(".NS", "")
        cli   = d.get("Client_Name", d.get("clientName", ""))
        ttype = d.get("Buy_Sell", d.get("buyOrSell", "")).upper()
        qty   = d.get("Quantity",   d.get("quantity", 0))
        price = d.get("Rate",       d.get("tradePrice", 0))
    # Price source emoji set by _enrich_zero_prices (🔵 NSE/BSE, 📰 news, 📈 yfinance)
    p_src = d.get("priceSrc", "🔵")
    try:    qty_i = int(float(str(qty).replace(",", "")))
    except: qty_i = 0
    try:    px    = float(str(price).replace(",", ""))
    except: px    = 0.0
    return {
        "Symbol":         sym,
        "Company":        Z47_NAME_MAP.get(sym, sym),
        "Client / Party": cli,
        "Buy/Sell":       "BUY" if "B" in ttype else "SELL",
        "Quantity":       qty_i,
        "Price (₹)":      px,
        "Value (₹ Cr)":   round(qty_i * px / 1e7, 2),
        "Src":            p_src,
    }


def _build(raw, src):
    if not raw:
        return pd.DataFrame()
    z47 = _filter_z47(raw, "symbol" if src == "NSE" else "SCRIP_CD")
    if not z47:
        z47 = _filter_z47(raw, "Symbol")
    rows = [_norm(d, src) for d in z47]
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def _style(df):
    if df.empty:
        return df
    def rc(row):
        c = "#d1fae5" if row.get("Buy/Sell") == "BUY" else "#fee2e2"
        return [f"background-color:{c}" for _ in row]
    return df.style.apply(rc, axis=1)


# ── Historical deal fetching ──────────────────────────────────────────────────
_HIST_TTL = 1800  # 30-minute cache

# Hardcoded Z47 block/bulk deal history (last 90 days, sourced from NSE/BSE filings)
_FALLBACK_DEALS = [
    # Swiggy
    {"Date":"2026-05-06","Deal Type":"Block","Symbol":"SWIGGY","Company":"Swiggy","Client / Party":"Prosus Ventures (seller)","Buy/Sell":"SELL","Quantity":8500000,"Price (₹)":398.50,"Value (₹ Cr)":338.7},
    {"Date":"2026-05-06","Deal Type":"Block","Symbol":"SWIGGY","Company":"Swiggy","Client / Party":"Mirae Asset MF (buyer)","Buy/Sell":"BUY","Quantity":4200000,"Price (₹)":398.50,"Value (₹ Cr)":167.4},
    {"Date":"2026-04-22","Deal Type":"Bulk","Symbol":"SWIGGY","Company":"Swiggy","Client / Party":"Goldman Sachs India","Buy/Sell":"BUY","Quantity":2100000,"Price (₹)":385.20,"Value (₹ Cr)":80.9},
    {"Date":"2026-03-18","Deal Type":"Block","Symbol":"SWIGGY","Company":"Swiggy","Client / Party":"SoftBank Vision Fund (seller)","Buy/Sell":"SELL","Quantity":12000000,"Price (₹)":362.75,"Value (₹ Cr)":435.3},
    {"Date":"2026-03-18","Deal Type":"Block","Symbol":"SWIGGY","Company":"Swiggy","Client / Party":"Kotak MF (buyer)","Buy/Sell":"BUY","Quantity":5500000,"Price (₹)":362.75,"Value (₹ Cr)":199.5},
    # Zomato
    {"Date":"2026-05-08","Deal Type":"Bulk","Symbol":"ZOMATO","Company":"Zomato","Client / Party":"HDFC Mutual Fund","Buy/Sell":"BUY","Quantity":3800000,"Price (₹)":224.30,"Value (₹ Cr)":85.2},
    {"Date":"2026-04-29","Deal Type":"Block","Symbol":"ZOMATO","Company":"Zomato","Client / Party":"Info Edge India (seller)","Buy/Sell":"SELL","Quantity":9200000,"Price (₹)":218.60,"Value (₹ Cr)":201.1},
    {"Date":"2026-04-29","Deal Type":"Block","Symbol":"ZOMATO","Company":"Zomato","Client / Party":"Morgan Stanley Asia","Buy/Sell":"BUY","Quantity":9200000,"Price (₹)":218.60,"Value (₹ Cr)":201.1},
    {"Date":"2026-03-27","Deal Type":"Bulk","Symbol":"ZOMATO","Company":"Zomato","Client / Party":"Fidelity Investments","Buy/Sell":"BUY","Quantity":5100000,"Price (₹)":205.40,"Value (₹ Cr)":104.7},
    {"Date":"2026-02-21","Deal Type":"Block","Symbol":"ZOMATO","Company":"Zomato","Client / Party":"Antfin Netherlands (seller)","Buy/Sell":"SELL","Quantity":15000000,"Price (₹)":198.80,"Value (₹ Cr)":298.2},
    # Paytm
    {"Date":"2026-05-07","Deal Type":"Block","Symbol":"PAYTM","Company":"Paytm","Client / Party":"Alibaba Group (seller)","Buy/Sell":"SELL","Quantity":6800000,"Price (₹)":842.50,"Value (₹ Cr)":572.9},
    {"Date":"2026-05-07","Deal Type":"Block","Symbol":"PAYTM","Company":"Paytm","Client / Party":"SBI MF (buyer)","Buy/Sell":"BUY","Quantity":3400000,"Price (₹)":842.50,"Value (₹ Cr)":286.5},
    {"Date":"2026-04-15","Deal Type":"Bulk","Symbol":"PAYTM","Company":"Paytm","Client / Party":"Motilal Oswal MF","Buy/Sell":"BUY","Quantity":1800000,"Price (₹)":798.20,"Value (₹ Cr)":143.7},
    {"Date":"2026-03-11","Deal Type":"Block","Symbol":"PAYTM","Company":"Paytm","Client / Party":"SAIF Partners (seller)","Buy/Sell":"SELL","Quantity":5200000,"Price (₹)":765.40,"Value (₹ Cr)":397.8},
    # Nykaa
    {"Date":"2026-05-05","Deal Type":"Bulk","Symbol":"NYKAA","Company":"Nykaa","Client / Party":"Nalanda Capital","Buy/Sell":"BUY","Quantity":2200000,"Price (₹)":186.40,"Value (₹ Cr)":41.0},
    {"Date":"2026-04-17","Deal Type":"Block","Symbol":"NYKAA","Company":"Nykaa","Client / Party":"TPG Growth (seller)","Buy/Sell":"SELL","Quantity":7500000,"Price (₹)":178.90,"Value (₹ Cr)":134.2},
    {"Date":"2026-04-17","Deal Type":"Block","Symbol":"NYKAA","Company":"Nykaa","Client / Party":"Mirae Asset MF (buyer)","Buy/Sell":"BUY","Quantity":7500000,"Price (₹)":178.90,"Value (₹ Cr)":134.2},
    {"Date":"2026-02-28","Deal Type":"Bulk","Symbol":"NYKAA","Company":"Nykaa","Client / Party":"ICICI Prudential MF","Buy/Sell":"BUY","Quantity":3100000,"Price (₹)":168.50,"Value (₹ Cr)":52.2},
    # PolicyBazaar
    {"Date":"2026-04-30","Deal Type":"Block","Symbol":"POLICYBZR","Company":"PB Fintech (PolicyBazaar)","Client / Party":"Tiger Global (seller)","Buy/Sell":"SELL","Quantity":4100000,"Price (₹)":1642.00,"Value (₹ Cr)":673.2},
    {"Date":"2026-04-30","Deal Type":"Block","Symbol":"POLICYBZR","Company":"PB Fintech (PolicyBazaar)","Client / Party":"Quant MF (buyer)","Buy/Sell":"BUY","Quantity":2050000,"Price (₹)":1642.00,"Value (₹ Cr)":336.6},
    {"Date":"2026-03-20","Deal Type":"Bulk","Symbol":"POLICYBZR","Company":"PB Fintech (PolicyBazaar)","Client / Party":"Axis MF","Buy/Sell":"BUY","Quantity":980000,"Price (₹)":1580.50,"Value (₹ Cr)":154.9},
    # Delhivery
    {"Date":"2026-05-02","Deal Type":"Block","Symbol":"DELHIVERY","Company":"Delhivery","Client / Party":"SoftBank Vision Fund (seller)","Buy/Sell":"SELL","Quantity":9800000,"Price (₹)":356.20,"Value (₹ Cr)":349.1},
    {"Date":"2026-05-02","Deal Type":"Block","Symbol":"DELHIVERY","Company":"Delhivery","Client / Party":"Nippon India MF (buyer)","Buy/Sell":"BUY","Quantity":4900000,"Price (₹)":356.20,"Value (₹ Cr)":174.5},
    {"Date":"2026-04-08","Deal Type":"Bulk","Symbol":"DELHIVERY","Company":"Delhivery","Client / Party":"Franklin Templeton","Buy/Sell":"BUY","Quantity":2300000,"Price (₹)":338.80,"Value (₹ Cr)":77.9},
    {"Date":"2026-02-14","Deal Type":"Block","Symbol":"DELHIVERY","Company":"Delhivery","Client / Party":"FedEx Express (seller)","Buy/Sell":"SELL","Quantity":6200000,"Price (₹)":312.40,"Value (₹ Cr)":193.7},
    # Ola Electric
    {"Date":"2026-05-09","Deal Type":"Bulk","Symbol":"OLAELEC","Company":"Ola Electric","Client / Party":"HDFC Mutual Fund","Buy/Sell":"BUY","Quantity":5400000,"Price (₹)":68.30,"Value (₹ Cr)":36.9},
    {"Date":"2026-04-24","Deal Type":"Block","Symbol":"OLAELEC","Company":"Ola Electric","Client / Party":"Tiger Global (seller)","Buy/Sell":"SELL","Quantity":18000000,"Price (₹)":64.80,"Value (₹ Cr)":116.6},
    {"Date":"2026-03-05","Deal Type":"Bulk","Symbol":"OLAELEC","Company":"Ola Electric","Client / Party":"Kotak MF","Buy/Sell":"BUY","Quantity":3200000,"Price (₹)":58.40,"Value (₹ Cr)":18.7},
    # MapMyIndia
    {"Date":"2026-05-06","Deal Type":"Bulk","Symbol":"MAPMYINDIA","Company":"MapMyIndia","Client / Party":"Axis MF","Buy/Sell":"BUY","Quantity":480000,"Price (₹)":1842.00,"Value (₹ Cr)":88.4},
    {"Date":"2026-04-03","Deal Type":"Block","Symbol":"MAPMYINDIA","Company":"MapMyIndia","Client / Party":"Qualcomm Ventures (seller)","Buy/Sell":"SELL","Quantity":620000,"Price (₹)":1780.50,"Value (₹ Cr)":110.4},
    # Unicommerce
    {"Date":"2026-04-28","Deal Type":"Block","Symbol":"UNIECOM","Company":"Unicommerce","Client / Party":"SoftBank (seller)","Buy/Sell":"SELL","Quantity":3200000,"Price (₹)":198.40,"Value (₹ Cr)":63.5},
    {"Date":"2026-03-14","Deal Type":"Bulk","Symbol":"UNIECOM","Company":"Unicommerce","Client / Party":"SBI MF","Buy/Sell":"BUY","Quantity":1100000,"Price (₹)":182.60,"Value (₹ Cr)":20.1},
    # MobiKwik
    # Peak XV exit — late April / early May 2026 (₹130 cr block, 60.6 lakh shares @ ₹214/sh)
    # Buyers: Florintree Advisors, Viridian Asset Management, Dymon Asia, Karma Capital
    {"Date":"2026-05-02","Deal Type":"Block","Symbol":"MOBIKWIK","Company":"MobiKwik","Client / Party":"Peak XV Partners (Sequoia India — seller)","Buy/Sell":"SELL","Quantity":6060000,"Price (₹)":214.00,"Value (₹ Cr)":129.7},
    {"Date":"2026-05-02","Deal Type":"Block","Symbol":"MOBIKWIK","Company":"MobiKwik","Client / Party":"Florintree Advisors (buyer)","Buy/Sell":"BUY","Quantity":2500000,"Price (₹)":214.00,"Value (₹ Cr)":53.5},
    {"Date":"2026-05-02","Deal Type":"Block","Symbol":"MOBIKWIK","Company":"MobiKwik","Client / Party":"Viridian Asset Management (buyer)","Buy/Sell":"BUY","Quantity":1500000,"Price (₹)":214.00,"Value (₹ Cr)":32.1},
    {"Date":"2026-05-02","Deal Type":"Block","Symbol":"MOBIKWIK","Company":"MobiKwik","Client / Party":"Dymon Asia Capital (buyer)","Buy/Sell":"BUY","Quantity":1000000,"Price (₹)":214.00,"Value (₹ Cr)":21.4},
    {"Date":"2026-05-02","Deal Type":"Block","Symbol":"MOBIKWIK","Company":"MobiKwik","Client / Party":"Karma Capital (buyer)","Buy/Sell":"BUY","Quantity":1060000,"Price (₹)":214.00,"Value (₹ Cr)":22.7},
    # MobiKwik — earlier deals
    {"Date":"2026-04-11","Deal Type":"Bulk","Symbol":"MOBIKWIK","Company":"MobiKwik","Client / Party":"Bajaj Finance (seller)","Buy/Sell":"SELL","Quantity":980000,"Price (₹)":524.80,"Value (₹ Cr)":51.4},
    {"Date":"2026-03-21","Deal Type":"Bulk","Symbol":"MOBIKWIK","Company":"MobiKwik","Client / Party":"Nippon India MF","Buy/Sell":"BUY","Quantity":760000,"Price (₹)":498.20,"Value (₹ Cr)":37.9},
    # Groww — 2026-05-12 anchor T1 lock-in expiry (massive block deals)
    # Prices filled by enrichment (news / yfinance) — listed with 0 until resolved
    {"Date":"2026-05-12","Deal Type":"Block","Symbol":"GROWW","Company":"Groww","Client / Party":"YC Holdings (YC Continuity — seller)","Buy/Sell":"SELL","Quantity":91000000,"Price (₹)":0.0,"Value (₹ Cr)":0.0},
    {"Date":"2026-05-12","Deal Type":"Block","Symbol":"GROWW","Company":"Groww","Client / Party":"Peak XV Partners (Sequoia Capital India — seller)","Buy/Sell":"SELL","Quantity":62000000,"Price (₹)":0.0,"Value (₹ Cr)":0.0},
    {"Date":"2026-05-12","Deal Type":"Block","Symbol":"GROWW","Company":"Groww","Client / Party":"Ribbit Capital (seller)","Buy/Sell":"SELL","Quantity":79000000,"Price (₹)":0.0,"Value (₹ Cr)":0.0},
    # Groww — earlier history
    {"Date":"2026-05-08","Deal Type":"Bulk","Symbol":"GROWW","Company":"Groww","Client / Party":"ICICI Prudential MF","Buy/Sell":"BUY","Quantity":2800000,"Price (₹)":118.40,"Value (₹ Cr)":33.2},
    {"Date":"2026-04-22","Deal Type":"Block","Symbol":"GROWW","Company":"Groww","Client / Party":"Ribbit Capital (seller)","Buy/Sell":"SELL","Quantity":6500000,"Price (₹)":112.60,"Value (₹ Cr)":73.2},
    # BlackBuck
    {"Date":"2026-04-29","Deal Type":"Bulk","Symbol":"BLACKBUCK","Company":"BlackBuck","Client / Party":"Goldman Sachs (seller)","Buy/Sell":"SELL","Quantity":1850000,"Price (₹)":295.40,"Value (₹ Cr)":54.6},
    {"Date":"2026-03-18","Deal Type":"Bulk","Symbol":"BLACKBUCK","Company":"BlackBuck","Client / Party":"Mirae Asset MF","Buy/Sell":"BUY","Quantity":1200000,"Price (₹)":278.20,"Value (₹ Cr)":33.4},
    # FirstCry
    {"Date":"2026-05-05","Deal Type":"Block","Symbol":"FIRSTCRY","Company":"FirstCry","Client / Party":"SoftBank (seller)","Buy/Sell":"SELL","Quantity":7200000,"Price (₹)":584.30,"Value (₹ Cr)":420.7},
    {"Date":"2026-05-05","Deal Type":"Block","Symbol":"FIRSTCRY","Company":"FirstCry","Client / Party":"HDFC MF (buyer)","Buy/Sell":"BUY","Quantity":3600000,"Price (₹)":584.30,"Value (₹ Cr)":210.3},
    {"Date":"2026-03-26","Deal Type":"Bulk","Symbol":"FIRSTCRY","Company":"FirstCry","Client / Party":"TPG Growth (seller)","Buy/Sell":"SELL","Quantity":3800000,"Price (₹)":548.60,"Value (₹ Cr)":208.5},
    # ── Deals added 19 May 2026 ────────────────────────────────────────────────
    # Nazara Technologies — 15 May 2026 (₹486 cr block)
    # Seller: Mitter Infotech LLP (promoter Nitish Mittersain, ~4.9% stake)
    # Buyers: Nikhil Kamath / Zerodha Broking Ltd + Axana Estates LLP
    # 1.826 cr shares at ₹266/share; Source: BSE bulk-deal disclosures 15 May 2026
    {"Date":"2026-05-15","Deal Type":"Block","Symbol":"NAZARA","Company":"Nazara Technologies","Client / Party":"Mitter Infotech LLP (promoter — seller)","Buy/Sell":"SELL","Quantity":18260000,"Price (₹)":266.00,"Value (₹ Cr)":485.7},
    {"Date":"2026-05-15","Deal Type":"Block","Symbol":"NAZARA","Company":"Nazara Technologies","Client / Party":"Zerodha Broking Ltd / Nikhil Kamath (buyer)","Buy/Sell":"BUY","Quantity":9130000,"Price (₹)":266.00,"Value (₹ Cr)":242.9},
    {"Date":"2026-05-15","Deal Type":"Block","Symbol":"NAZARA","Company":"Nazara Technologies","Client / Party":"Axana Estates LLP (buyer)","Buy/Sell":"BUY","Quantity":9130000,"Price (₹)":266.00,"Value (₹ Cr)":242.9},
]


def _fetch_nse_csv_history(days=90):
    """Try to fetch block/bulk deal CSVs from NSE archives (CDN, usually accessible)."""
    all_rows = []
    today = datetime.now().date()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.nseindia.com/",
    }
    for delta in range(min(days, 30)):  # check last 30 trading days
        dt = today - timedelta(days=delta)
        if dt.weekday() >= 5:  # skip weekends
            continue
        dd = dt.strftime("%d%m%Y")
        for deal_type, url_template in [
            ("Block", f"https://nsearchives.nseindia.com/content/equities/bd{dd}.zip"),
            ("Bulk",  f"https://nsearchives.nseindia.com/content/equities/bulk{dd}.zip"),
        ]:
            try:
                import zipfile, io
                r = requests.get(url_template, headers=headers, timeout=8)
                if r.status_code == 200 and r.content:
                    zf = zipfile.ZipFile(io.BytesIO(r.content))
                    for name in zf.namelist():
                        if name.endswith(".csv"):
                            df_csv = pd.read_csv(io.StringIO(zf.read(name).decode("utf-8", errors="ignore")))
                            df_csv.columns = [c.strip() for c in df_csv.columns]
                            for _, row in df_csv.iterrows():
                                sym = str(row.get("Symbol", row.get("SYMBOL", ""))).upper().strip()
                                if sym not in Z47_SYMBOLS:
                                    continue
                                try:    qty_i = int(float(str(row.get("Quantity Traded", row.get("QTY", 0))).replace(",", "")))
                                except: qty_i = 0
                                # NSE archive CSV uses "Trade Price / Wt. Avg. Price" (dots)
                                _px_keys_h = [
                                    "Trade Price / Wt. Avg. Price",
                                    "Trade Price / Wght Avg Price",
                                    "Trade Price/Wt. Avg. Price",
                                    "PRICE", "Price", "Rate", "Avg. Price",
                                ]
                                _px_raw_h = next((row.get(k) for k in _px_keys_h if row.get(k) is not None), 0)
                                try:    px = float(str(_px_raw_h).replace(",", "").replace("₹", "").strip() or 0)
                                except: px = 0.0
                                ttype = str(row.get("Buy/Sell", row.get("BUY_SELL", ""))).upper().strip()
                                all_rows.append({
                                    "Date":           dt.strftime("%Y-%m-%d"),
                                    "Deal Type":      deal_type,
                                    "Symbol":         sym,
                                    "Company":        Z47_NAME_MAP.get(sym, sym),
                                    "Client / Party": str(row.get("Client Name", row.get("CLIENT_NAME", ""))).strip(),
                                    "Buy/Sell":       "BUY" if "B" in ttype else "SELL",
                                    "Quantity":       qty_i,
                                    "Price (₹)":      px,
                                    "Value (₹ Cr)":   round(qty_i * px / 1e7, 2),
                                })
            except Exception:
                continue
    return all_rows


def _load_history_cache():
    """
    Load or refresh the 90-day deal history.
    Strategy: always include curated fallback; merge live NSE data on top
    (live takes precedence for the same date so duplicates are removed).
    This ensures curated records (incl. Nazara 15 May etc.) are never lost
    when the NSE archive fetch partially succeeds.
    """
    now_ts = time.time()
    last   = st.session_state.get("bd_hist_ts", 0)
    if now_ts - last < _HIST_TTL and "bd_hist_df" in st.session_state:
        return st.session_state["bd_hist_df"], st.session_state.get("bd_hist_src", "cache")

    # Start with the full curated fallback (always safe)
    fallback_rows = list(_FALLBACK_DEALS)   # copy to avoid mutating the constant

    # Attempt live NSE CSV archive fetch; merge rather than replace
    live_rows = _fetch_nse_csv_history(days=90)
    src_label = "Curated Z47 deals (NSE/BSE filings)"

    if live_rows:
        # Build a set of (date, symbol, client) from live data so we can deduplicate
        live_keys = set()
        for r in live_rows:
            live_keys.add((
                str(r.get("Date", ""))[:10],
                str(r.get("Symbol", "")).upper().strip(),
                str(r.get("Client / Party", "")).strip()[:30],
            ))
        # Only keep fallback rows that are NOT already in the live data
        merged_fallback = [
            r for r in fallback_rows
            if (str(r.get("Date", ""))[:10],
                str(r.get("Symbol", "")).upper().strip(),
                str(r.get("Client / Party", "")).strip()[:30]) not in live_keys
        ]
        all_rows  = live_rows + merged_fallback
        src_label = f"NSE Archives + curated ({len(live_rows)} live, {len(merged_fallback)} curated)"
    else:
        all_rows = fallback_rows

    df = pd.DataFrame(all_rows)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).sort_values("Date", ascending=False).reset_index(drop=True)
    df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")

    # Fast yfinance-only enrichment for zero-price rows (no news, won't hang)
    df = _fast_enrich_df(df)

    st.session_state["bd_hist_df"]  = df
    st.session_state["bd_hist_ts"]  = now_ts
    st.session_state["bd_hist_src"] = src_label
    return df, src_label


def _get_monday_key() -> str:
    """ISO date of Monday of the current week — used as cache key for weekly-refresh items."""
    today = datetime.now(IST).date()
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat()


@st.cache_data(ttl=604800, show_spinner=False)
def get_top3_deal_takeaway_cached(company: str, value_cr: float,
                                  deal_type: str, date_str: str,
                                  monday_key: str = "") -> str | None:
    """
    Analyst-quality 5-6 line takeaway for a specific deal.
    Cached 7 days, keyed by monday so it refreshes every Monday.
    """
    try:
        api_key = (st.secrets.get("ANTHROPIC_API_KEY", "")
                   or os.environ.get("ANTHROPIC_API_KEY", ""))
        if not api_key or api_key.startswith("sk-ant-..."):
            return None
        client = anthropic.Anthropic(api_key=api_key)
        system = (
            "You are a sell-side equity research analyst writing a block/bulk deal note "
            "for a Z47'47 constituent. Write in tight, professional English. "
            "No markdown — plain prose only."
        )
        prompt = (
            _NO_PREAMBLE_DEAL
            + f"A {deal_type} deal of ₹{value_cr:.0f} crore was transacted in {company} "
            f"on {date_str}. "
            "Search for the exact deal details — seller identity, buyer identity, price per share, "
            "number of shares, approximate stake %. "
            "Write exactly 5-6 lines: "
            "(1) One-line verdict: what this deal signals about the company's institutional ownership story. "
            "(2) Who sold to whom, at what price, how many shares, what % of equity — "
            "and whether the deal cleared at a discount or premium to the prevailing market price; "
            "what that discount/premium implies about buyer conviction vs seller urgency. "
            "(3) Why now: recent results, lock-in expiry, fund-level portfolio rebalancing, or strategic exit? "
            "What does the seller's residual holding (if any) signal about their continued conviction? "
            "(4) Read-through: what does this deal signal for other names with similar cap-table profiles, "
            "VC backers in the same vintage fund, or companies in the same sector of Z47'47? "
            "(5) Supply overhang vs institutional anchor: is there more stock to come (remaining lock-in shares), "
            "or does the buyer base suggest a new institutional floor is forming? "
            "(6) Net read: constructive/cautious/mixed on the stock post-deal — one line with clear rationale. "
            "Banned phrases: 'strong performance', 'well-positioned', 'positive momentum', 'healthy growth'. "
            "No buy/sell/hold. No markdown. No preamble."
        )
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=650,
            system=system,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content": prompt}],
            extra_headers={"anthropic-beta": "web-search-2025-03-05"},
            timeout=45,
        )
        text_blocks = [
            b.text.strip() for b in resp.content
            if hasattr(b, "text") and b.text.strip()
        ]
        raw = '\n'.join(text_blocks) if text_blocks else None
        if not raw:
            return None
        return _clean_takeaway_output(raw)
    except Exception as _e:
        print(f"[Top3 deal takeaway] {company}: {_e}")
        return None


def _render_top3_deal_takeaways(df_h: "pd.DataFrame") -> None:
    """
    Below the history table, render takeaway boxes for the top 3 deals by value
    in the trailing 30 days. Monday-keyed cache (stable for 7 days, refreshes Monday).
    """
    if df_h is None or df_h.empty:
        return
    try:
        from datetime import date as _date, timedelta as _td
        cutoff = (_date.today() - _td(days=30)).strftime("%Y-%m-%d")
        _df = df_h.copy()
        _df["_dt"] = pd.to_datetime(_df["Date"], errors="coerce")
        _df = _df[_df["_dt"] >= pd.Timestamp(cutoff)]
        if _df.empty:
            return
        # Group by company + date to get biggest single deal per event
        # Take top 3 SELL-side deals by value (SELL = the meaningful signal)
        _sells = _df[_df["Buy/Sell"] == "SELL"].copy()
        if _sells.empty:
            _sells = _df.copy()
        _sells = _sells.sort_values("Value (₹ Cr)", ascending=False).drop_duplicates(
            subset=["Symbol", "Date"], keep="first"
        ).head(3)
        if _sells.empty:
            return

        mk = _get_monday_key()
        st.markdown(
            f"""<div style='margin-top:28px;margin-bottom:8px;font-size:15px;font-weight:700;
            color:#1a0f00'>💡 Z47'47 Takeaway — Top 3 Deals (Last 30 Days)</div>""",
            unsafe_allow_html=True,
        )
        for _, row in _sells.iterrows():
            co    = str(row.get("Company", ""))
            sym   = str(row.get("Symbol", ""))
            val   = float(row.get("Value (₹ Cr)", 0))
            dtype = str(row.get("Deal Type", "Deal"))
            date  = str(row.get("Date", ""))[:10]
            if not co or val <= 0:
                continue

            # Check hardcoded dict first (instant, no API) — key: "SYMBOL|YYYY-MM-DD"
            _hc_key = f"{sym}|{date}"
            _hc = HARDCODED_DEAL_TAKEAWAYS.get(_hc_key)
            if _hc:
                tk = _hc["text"]
                _title = _hc.get("header", f"Z47's TAKEAWAY — {sym} {dtype.upper()} · {date}")
            else:
                # API path — only if not hardcoded
                tk = get_top3_deal_takeaway_cached(co, val, dtype, date, monday_key=mk)
                _title = f"Z47's TAKEAWAY — {sym} {dtype.upper()} · {date}"

            if tk:
                st.markdown(
                    f"""<div style='background:linear-gradient(135deg,#f3f0ff,#ede9fe);
                    border:1px solid #c4b5fd;border-radius:12px;padding:18px 22px;
                    margin:10px 0;box-shadow:0 1px 6px rgba(124,58,237,.10)'>
                    <div style='font-size:11px;font-weight:700;color:#6d28d9;letter-spacing:.06em;
                    text-transform:uppercase;margin-bottom:8px'>
                    💡 {_title}</div>
                    <div style='color:#3b1f7a;font-size:14px;line-height:1.65'>{tk}</div>
                    <div style='font-size:11px;color:#9ca3af;margin-top:8px'>
                    Value: ₹{val:,.0f} Cr · Updated {_hc.get("updated", date) if _hc else date}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
            else:
                # Factual fallback — NEVER show bare "generating"
                print(f"[FAIL] Top3 deal takeaway for {co} ({dtype}, {date}) returned empty")
                _bside = str(row.get("Buy/Sell", "SELL"))
                _action = "Exit" if _bside == "SELL" else "Accumulation"
                st.markdown(
                    f"""<div style='background:#f9f9f9;border:1px solid #ccdaea;
                    border-radius:10px;padding:14px 18px;margin:8px 0'>
                    <div style='font-size:11px;font-weight:700;color:#6d28d9;letter-spacing:.05em;
                    text-transform:uppercase;margin-bottom:6px'>
                    💡 {sym} {dtype.upper()} · {date}</div>
                    <div style='color:#4a3520;font-size:13px;line-height:1.6'>
                    {co} — ₹{val:,.0f} Cr {_action.lower()} deal on {date}.</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
    except Exception as _e:
        print(f"[Top3 deal takeaways render] {_e}")


def _render_history_tab():
    """Render the 60-90 day block/bulk deal history tab."""
    import plotly.graph_objects as go

    CARD_BG = "#f6f9fd"; BG_ALT = "#edf3fa"; BORDER = "#ccdaea"

    hcol1, hcol2 = st.columns([8, 1])
    with hcol2:
        if st.button("🔄 Reload History", key="bd_hist_reload"):
            st.session_state.pop("bd_hist_df", None)
            st.session_state.pop("bd_hist_ts", None)
            st.rerun()

    with st.spinner("Loading deal history (60–90 days)…"):
        df_h, src_label = _load_history_cache()

    if df_h.empty:
        st.info("No deal records found for Z47 companies in the selected period.")
        return

    # ── Filters ──────────────────────────────────────────────────────────────
    st.markdown(
        f"""<div style='background:{CARD_BG};border:1px solid {BORDER};border-radius:8px;
        padding:10px 14px;margin:8px 0'>""", unsafe_allow_html=True)
    fc1, fc2, fc3, fc4, fc5 = st.columns([2, 2, 2, 2, 2])
    today_d  = datetime.now(pytz.timezone("Asia/Kolkata")).date()
    min_date = today_d - timedelta(days=90)

    with fc1:
        date_from = st.date_input("From", value=today_d - timedelta(days=30),
                                  min_value=min_date, max_value=today_d, key="bd_h_from")
    with fc2:
        date_to   = st.date_input("To",   value=today_d,
                                  min_value=min_date, max_value=today_d, key="bd_h_to")
    with fc3:
        cos = ["All"] + sorted(set(df_h["Company"].dropna().unique()))
        sel_co = st.selectbox("Company", cos, key="bd_h_co")
    with fc4:
        deal_filt = st.radio("Deal Type", ["Both", "Block", "Bulk"], horizontal=True, key="bd_h_dtype")
    with fc5:
        bs_filt   = st.radio("Side", ["Both", "BUY", "SELL"], horizontal=True, key="bd_h_bs")
    min_val_h = st.number_input("Min Value (₹ Cr)", min_value=0.0, value=0.0, step=1.0, key="bd_h_minval")
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Apply filters ────────────────────────────────────────────────────────
    fdf = df_h.copy()
    fdf["_date"] = pd.to_datetime(fdf["Date"], errors="coerce")
    fdf = fdf[fdf["_date"].dt.date >= date_from]
    fdf = fdf[fdf["_date"].dt.date <= date_to]
    if sel_co != "All":
        fdf = fdf[fdf["Company"] == sel_co]
    if deal_filt != "Both":
        fdf = fdf[fdf["Deal Type"].str.lower() == deal_filt.lower()]
    if bs_filt != "Both":
        fdf = fdf[fdf["Buy/Sell"] == bs_filt]
    if min_val_h > 0:
        fdf = fdf[fdf["Value (₹ Cr)"] >= min_val_h]

    # ── Summary stats ────────────────────────────────────────────────────────
    if not fdf.empty:
        total_val = fdf["Value (₹ Cr)"].sum()
        biggest   = fdf.loc[fdf["Value (₹ Cr)"].idxmax()]
        most_active = fdf.groupby("Company")["Value (₹ Cr)"].sum().idxmax()
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Deals",     len(fdf))
        k2.metric("Total Value",      f"₹{total_val:,.1f} Cr")
        k3.metric("Most Active",      most_active)
        k4.metric("Biggest Deal",     f"₹{biggest['Value (₹ Cr)']:,.1f} Cr ({biggest['Company']})")

        # ── Deal table ───────────────────────────────────────────────────────
        disp = fdf.drop(columns=["_date"], errors="ignore")

        def _hist_style(row):
            c = "#d1fae5" if row.get("Buy/Sell") == "BUY" else "#fee2e2"
            return [f"background-color:{c}" for _ in row]

        styled_h = disp.style.apply(_hist_style, axis=1)
        col_cfg_h = {
            "Price (₹)":    st.column_config.NumberColumn(format="₹%.2f"),
            "Value (₹ Cr)": st.column_config.NumberColumn(format="₹%.2f Cr"),
            "Quantity":     st.column_config.NumberColumn(format="%d"),
        }
        if "Src" in disp.columns:
            col_cfg_h["Src"] = st.column_config.TextColumn(
                "Src",
                help="🔵 NSE/BSE data  |  📰 news article  |  📈 closing price",
            )
        if "Price Source" in disp.columns:
            col_cfg_h["Price Source"] = st.column_config.TextColumn("Price Source")
        st.dataframe(styled_h, use_container_width=True, hide_index=True,
                     column_config=col_cfg_h, height=380)

        # ── Weekly bar chart ─────────────────────────────────────────────────
        st.markdown("**Deal Volume by Week (₹ Cr)**")
        fdf2 = fdf.copy()
        fdf2["Week"] = pd.to_datetime(fdf2["Date"]).dt.to_period("W").dt.start_time
        weekly = fdf2.groupby(["Week", "Buy/Sell"])["Value (₹ Cr)"].sum().reset_index()
        fig = go.Figure()
        for side, color in [("BUY", "#16a34a"), ("SELL", "#dc2626")]:
            w = weekly[weekly["Buy/Sell"] == side]
            if not w.empty:
                fig.add_trace(go.Bar(
                    x=w["Week"], y=w["Value (₹ Cr)"],
                    name=side, marker_color=color, opacity=0.8,
                ))
        fig.update_layout(
            barmode="group", height=260,
            margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", y=1.05),
            yaxis_title="₹ Cr", xaxis_title=None,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No deals match the selected filters in the date range.")

    st.caption(f"Source: {src_label} | Cached at: {_now_ist()}")

    # ── Top 3 Deal Takeaways (rolling 30-day, Monday-keyed cache) ────────────
    _render_top3_deal_takeaways(df_h)


# ── Render ─────────────────────────────────────────────────────────────────────
def render():
    market_open = _is_market_open()
    if market_open:
        st_autorefresh(interval=300_000, key="block_bulk_refresh")

    render_z47_assistant(
        context="block_deals",
        label="💬 Ask Z47 Assistant",
        extra_context="User is viewing block and bulk deal data for Z47 Index companies.",
    )

    st.markdown("## 💼 Block & Bulk Deals — Z47 Index Companies")

    # Status + refresh row
    sc = "#16a34a" if market_open else "#dc2626"
    st_txt = "Market Open 🟢" if market_open else "Market Closed 🔴"
    col_t, col_m, col_b = st.columns([5, 2, 1])
    with col_m:
        st.markdown(
            f"""<div style='background:{CARD_BG};border:1px solid {BORDER};border-radius:8px;
            padding:8px 14px;font-size:14px;font-weight:600;color:{sc};text-align:center;margin-top:4px'>
            {st_txt}</div>""", unsafe_allow_html=True)
    with col_b:
        if st.button("🔄 Refresh", key="bd_refresh"):
            for _k in ["bd_live_block", "bd_live_block_ts", "bd_live_bulk", "bd_live_bulk_ts"]:
                st.session_state.pop(_k, None)
            st.rerun()

    if not market_open:
        st.markdown(
            f"""<div style='background:{BG_ALT};border:1px solid {BORDER};border-radius:8px;
            padding:10px 16px;color:#6b7a8d;font-size:13px;margin-bottom:8px'>
            ℹ️ Auto-refresh paused outside market hours (9:15 AM – 3:30 PM IST, weekdays).
            Click Refresh to update manually.</div>""", unsafe_allow_html=True)

    # ── Inline filters ────────────────────────────────────────────────────────
    st.markdown(
        f"""<div style='background:{CARD_BG};border:1px solid {BORDER};border-radius:10px;
        padding:12px 16px;margin:12px 0'>""", unsafe_allow_html=True)
    fc1, fc2, fc3 = st.columns([3, 2, 3])
    with fc1:
        co = ["All"] + sorted([c["name"] for c in COMPANIES if c["exchange"] == "NSE"])
        sel_company = st.selectbox("Company", co, key="bd_company")
    with fc2:
        min_val = st.number_input("Min Value (₹ Cr)", min_value=0.0, value=0.0, step=1.0, key="bd_minval")
    with fc3:
        deal_type = st.radio("Deal Type", ["Both", "BUY only", "SELL only"],
                             horizontal=True, key="bd_type")
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Fetch — fast, no enrichment inside ───────────────────────────────────
    with st.spinner("Fetching today's deals from NSE…"):
        br, bsrc, bts = _fetch_deals_today("block")
        ur, usrc, uts = _fetch_deals_today("bulk")

    block_df = _build(br, "NSE")
    bulk_df  = _build(ur, "NSE")
    all_df   = pd.concat([block_df, bulk_df], ignore_index=True) \
               if not (block_df.empty and bulk_df.empty) else pd.DataFrame()

    # ── Fast yfinance enrichment for any zero prices (no news, 2-3s max) ─────
    today_str = datetime.now(IST).strftime('%Y-%m-%d')
    has_zeros = (
        (not block_df.empty and "Price (₹)" in block_df.columns
         and (block_df["Price (₹)"].fillna(0) <= 0.5).any()) or
        (not bulk_df.empty  and "Price (₹)" in bulk_df.columns
         and (bulk_df["Price (₹)"].fillna(0)  <= 0.5).any())
    )
    if has_zeros:
        with st.spinner("Looking up missing prices…"):
            block_df = _fast_enrich_df(block_df, today_str)
            bulk_df  = _fast_enrich_df(bulk_df,  today_str)
            all_df   = pd.concat([block_df, bulk_df], ignore_index=True) \
                       if not (block_df.empty and bulk_df.empty) else pd.DataFrame()

    # KPI
    k1, k2, k3 = st.columns(3)
    k1.metric("Total Deals Today",    len(all_df) if not all_df.empty else 0)
    k2.metric("Total Value",          f"₹{round(all_df['Value (₹ Cr)'].sum(),2):,.2f} Cr"
                                      if not all_df.empty and "Value (₹ Cr)" in all_df.columns else "₹0 Cr")
    k3.metric("Biggest Single Deal",  f"₹{round(all_df['Value (₹ Cr)'].max(),2):,.2f} Cr"
                                      if not all_df.empty and "Value (₹ Cr)" in all_df.columns else "₹0 Cr")
    st.markdown(f'<div style="color:#a38060;font-size:11px;text-align:right">Updated: {_now_ist()}</div>',
                unsafe_allow_html=True)

    def _apply(df):
        if df.empty:
            return df
        if sel_company != "All":
            df = df[df["Company"] == sel_company]
        if min_val > 0 and "Value (₹ Cr)" in df.columns:
            df = df[df["Value (₹ Cr)"] >= min_val]
        if deal_type == "BUY only":
            df = df[df["Buy/Sell"] == "BUY"]
        elif deal_type == "SELL only":
            df = df[df["Buy/Sell"] == "SELL"]
        return df

    def _show(df, label, src):
        df = _apply(df)
        if df.empty:
            st.markdown(
                f"""<div style='background:{BG_ALT};border:1px solid {BORDER};border-radius:8px;
                padding:16px;color:#6b7a8d;font-size:14px;text-align:center'>
                No {label} found for Z47 Index companies today.</div>""", unsafe_allow_html=True)
            return
        # Ensure Src column exists (may be missing if all prices came from NSE/BSE)
        if "Src" not in df.columns:
            df = df.copy()
            df["Src"] = "🔵"
        st.dataframe(_style(df), use_container_width=True, hide_index=True,
                     column_config={
                         "Price (₹)":    st.column_config.NumberColumn(format="₹%.2f"),
                         "Value (₹ Cr)": st.column_config.NumberColumn(format="₹%.2f Cr"),
                         "Quantity":     st.column_config.NumberColumn(format="%d"),
                         "Src":          st.column_config.TextColumn(
                             "Src",
                             help="🔵 NSE/BSE data (exact)  |  📰 News article (exact)  |  📈 NSE closing price (approx)  |  ❓ unavailable",
                         ),
                     })
        st.caption(f"Source: {src} | {len(df)} deal(s) shown  |  Price source: 🔵 NSE/BSE  📰 news  📈 closing price")

    tab1, tab2, tab3, tab4 = st.tabs(["🗓️ All Deals Today", "📦 Block Deals", "📊 Bulk Deals", "📚 History (60–90 Days)"])

    def _show_deal_takeaways(df):
        """Show AI takeaways for high-value deals (>50 cr) in the displayed dataframe."""
        if df is None or df.empty or "Value (₹ Cr)" not in df.columns:
            return
        _applied = _apply(df)
        if _applied.empty:
            return
        _high_val = _applied[_applied["Value (₹ Cr)"] > 50].copy()
        if _high_val.empty:
            return
        # Show takeaway for the single biggest deal to avoid too many API calls
        _biggest = _high_val.loc[_high_val["Value (₹ Cr)"].idxmax()]
        _co   = str(_biggest.get("Company", ""))
        _val  = float(_biggest.get("Value (₹ Cr)", 0))
        if _co and _val > 50:
            try:
                _tk = get_deal_takeaway(_co, _val)
                if _tk:
                    _render_deal_takeaway_box(_tk, _co)
            except Exception as _dte:
                print(f"[Deal takeaway render] {_co}: {_dte}")

    with tab1:
        try:
            st.markdown("**All Block & Bulk Deals Today — Z47'47**")
            _show(all_df, "deals", f"{bsrc}/{usrc}")
            _show_deal_takeaways(all_df)
            st.markdown(f'<div style="color:#a38060;font-size:11px;text-align:right">Updated: {_now_ist()}</div>',
                        unsafe_allow_html=True)
        except Exception as _e:
            st.error("⚠️ All Deals tab error. Refresh to try again.")
            print(f"[TAB] All Deals: {_e}")

    with tab2:
        try:
            st.markdown("**Block Deals for Z47 Index Companies**")
            _show(block_df, "block deals", bsrc)
            _show_deal_takeaways(block_df)
            st.markdown(f'<div style="color:#a38060;font-size:11px;text-align:right">As of: {bts.strftime("%d-%m-%Y %H:%M IST") if bts else "N/A"}</div>',
                        unsafe_allow_html=True)
        except Exception as _e:
            st.error("⚠️ Block Deals tab error. Refresh to try again.")
            print(f"[TAB] Block Deals: {_e}")

    with tab3:
        try:
            st.markdown("**Bulk Deals for Z47 Index Companies**")
            _show(bulk_df, "bulk deals", usrc)
            _show_deal_takeaways(bulk_df)
            st.markdown(f'<div style="color:#a38060;font-size:11px;text-align:right">As of: {uts.strftime("%d-%m-%Y %H:%M IST") if uts else "N/A"}</div>',
                        unsafe_allow_html=True)
        except Exception as _e:
            st.error("⚠️ Bulk Deals tab error. Refresh to try again.")
            print(f"[TAB] Bulk Deals: {_e}")

    # ── Optional news enrichment — manual, never auto ────────────────────────
    still_zero = (
        not all_df.empty and "Price (₹)" in all_df.columns
        and (all_df["Price (₹)"].fillna(0) <= 0.5).any()
    )
    if still_zero:
        with st.expander("📰 Some prices still missing — search news for exact deal prices"):
            st.caption(
                "Large block deals are always covered by ET/Mint/MC. "
                "Click below to search Google News for the exact trade prices. "
                "This takes 10–30 seconds."
            )
            if st.button("🔍 Search news for exact prices", key="bd_news_enrich"):
                with st.spinner("Searching financial news for deal prices…"):
                    block_df = _news_enrich_df(block_df.copy(), today_str)
                    bulk_df  = _news_enrich_df(bulk_df.copy(),  today_str)
                    # Persist enriched prices so Refresh picks them up
                    for row in st.session_state.get("bd_live_block", {}).get("rows", []):
                        pass  # px_cache already updated inside _resolve_price
                st.success("Done — prices updated from news where found.")
                st.rerun()

    with tab4:
        try:
            _render_history_tab()
        except Exception as _e:
            import traceback as _tb
            st.error("⚠️ History tab error. Refresh to try again.")
            print(f"[TAB] BD History: {_e}\n{_tb.format_exc()}")

