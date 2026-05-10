import streamlit as st
st.set_page_config(page_title="Block & Bulk Deals | Z47", page_icon="💼", layout="wide")

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from companies import COMPANIES
from sidebar_nav import render_sidebar

import requests
import pandas as pd
import pytz
import time
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

# ── Theme ──────────────────────────────────────────────────────────────────────
BG = "#fdf6ec"; CARD_BG = "#f6f9fd"; BG_ALT = "#edf3fa"; BORDER = "#ccdaea"
IST = pytz.timezone("Asia/Kolkata")

def now_ist():
    return datetime.now(IST).strftime("%d-%m-%Y %H:%M:%S IST")

def warn_banner(msg):
    st.markdown(
        f"""<div style='background:#fef3cd;border:1px solid #ffc107;border-radius:8px;
        padding:10px 16px;color:#856404;font-size:13px;margin-bottom:12px'>⚠️ {msg}</div>""",
        unsafe_allow_html=True,
    )

st.markdown(
    f"""<style>
    .stApp {{ background-color: {BG}; }}
    [data-testid="stHeader"] {{ display: none !important; }}
    .block-container {{ padding-top: 1.5rem; }}
    div[data-testid="metric-container"] {{ background:{CARD_BG};border:1px solid {BORDER};border-radius:10px;padding:12px }}
    </style>""",
    unsafe_allow_html=True,
)
render_sidebar()

# ── Z47 company maps ──────────────────────────────────────────────────────────
Z47_SYMBOLS = {c["ticker"] for c in COMPANIES if c["exchange"] == "NSE"}
Z47_NAME_MAP = {c["ticker"]: c["name"] for c in COMPANIES}
NSE_TICKERS = {c["name"]: c["ticker"] for c in COMPANIES if c["exchange"] == "NSE"}

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
    "X-Requested-With": "XMLHttpRequest",
}

# ── Market hours ───────────────────────────────────────────────────────────────
def is_market_open():
    now = datetime.now(IST)
    if now.weekday() >= 5:
        return False
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return market_open <= now <= market_close


def filter_z47(deals, symbol_col="symbol"):
    z47_filtered = []
    for d in deals:
        sym = str(d.get(symbol_col, "")).upper().strip()
        # Remove .NS suffix if present
        sym = sym.replace(".NS", "")
        if sym in Z47_SYMBOLS:
            d = dict(d)
            d["z47_name"] = Z47_NAME_MAP.get(sym, sym)
            z47_filtered.append(d)
    return z47_filtered


# ── Auto-refresh only during market hours ─────────────────────────────────────
if is_market_open():
    st_autorefresh(interval=300_000, key="block_bulk_refresh")

# ── Data fetchers ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_block_deals():
    try:
        s = requests.Session()
        s.get("https://www.nseindia.com", headers=NSE_HEADERS, timeout=6)
        time.sleep(1)
        r = s.get("https://www.nseindia.com/api/block-deal", headers=NSE_HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return data.get("data", []), "NSE", datetime.now(IST)
    except Exception:
        pass

    try:
        r = requests.get(
            "https://api.bseindia.com/BseIndiaAPI/api/BlockBulkDeals/w?Type=B",
            headers={"User-Agent": "Mozilla/5.0"}, timeout=10,
        )
        if r.status_code == 200:
            return r.json().get("Table", []), "BSE", datetime.now(IST)
    except Exception:
        pass

    return [], "No data", datetime.now(IST)


@st.cache_data(ttl=300)
def fetch_bulk_deals():
    try:
        s = requests.Session()
        s.get("https://www.nseindia.com", headers=NSE_HEADERS, timeout=6)
        time.sleep(1)
        r = s.get("https://www.nseindia.com/api/bulk-deal", headers=NSE_HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return data.get("data", []), "NSE", datetime.now(IST)
    except Exception:
        pass

    try:
        r = requests.get(
            "https://api.bseindia.com/BseIndiaAPI/api/BlockBulkDeals/w?Type=BU",
            headers={"User-Agent": "Mozilla/5.0"}, timeout=10,
        )
        if r.status_code == 200:
            return r.json().get("Table", []), "BSE", datetime.now(IST)
    except Exception:
        pass

    return [], "No data", datetime.now(IST)


def normalize_deal_row(d, source):
    """Normalize NSE or BSE deal row to a common schema."""
    if source == "NSE":
        symbol = str(d.get("symbol", d.get("Symbol", ""))).upper().replace(".NS", "")
        client = d.get("clientName", d.get("client_name", d.get("clientname", "")))
        trade_type = d.get("buyOrSell", d.get("buy_sell", d.get("buysell", ""))).upper()
        qty = d.get("quantity", d.get("qty", 0))
        price = d.get("tradePrice", d.get("trade_price", d.get("tradeprice", 0)))
    else:  # BSE
        symbol = str(d.get("SCRIP_CD", d.get("Symbol", ""))).upper().replace(".NS", "")
        client = d.get("Client_Name", d.get("clientName", ""))
        trade_type = d.get("Buy_Sell", d.get("buyOrSell", "")).upper()
        qty = d.get("Quantity", d.get("quantity", 0))
        price = d.get("Rate", d.get("tradePrice", 0))

    try:
        qty_int = int(float(str(qty).replace(",", "")))
    except Exception:
        qty_int = 0
    try:
        price_float = float(str(price).replace(",", ""))
    except Exception:
        price_float = 0.0

    value_cr = round(qty_int * price_float / 1e7, 2)

    return {
        "Symbol": symbol,
        "Company": Z47_NAME_MAP.get(symbol, symbol),
        "Client / Party": client,
        "Buy/Sell": "BUY" if "B" in trade_type else "SELL",
        "Quantity": qty_int,
        "Price (₹)": price_float,
        "Value (₹ Cr)": value_cr,
    }


def build_deal_df(raw_deals, source):
    if not raw_deals:
        return pd.DataFrame()
    z47 = filter_z47(raw_deals, symbol_col="symbol" if source == "NSE" else "SCRIP_CD")
    if not z47:
        z47 = filter_z47(raw_deals, symbol_col="Symbol")
    rows = [normalize_deal_row(d, source) for d in z47]
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


# ── Page ───────────────────────────────────────────────────────────────────────
st.markdown("## 💼 Block & Bulk Deals — Z47 Index Companies")

market_status = is_market_open()
status_color = "#16a34a" if market_status else "#dc2626"
status_text = "Market Open 🟢" if market_status else "Market Closed 🔴"

col_title, col_mkt, col_btn = st.columns([5, 2, 1])
with col_mkt:
    st.markdown(
        f"""<div style='background:{CARD_BG};border:1px solid {BORDER};border-radius:8px;
        padding:8px 14px;font-size:14px;font-weight:600;color:{status_color};text-align:center;margin-top:4px'>
        {status_text}</div>""",
        unsafe_allow_html=True,
    )
with col_btn:
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

if not market_status:
    st.markdown(
        f"""<div style='background:{BG_ALT};border:1px solid {BORDER};border-radius:8px;
        padding:10px 16px;color:#6b7a8d;font-size:13px;margin-bottom:8px'>
        ℹ️ Auto-refresh is paused outside market hours (9:15 AM – 3:30 PM IST, weekdays).
        Click Refresh to manually update.
        </div>""",
        unsafe_allow_html=True,
    )

# ── Sidebar filters ────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Filters")
    company_options = ["All"] + sorted([c["name"] for c in COMPANIES if c["exchange"] == "NSE"])
    sel_company = st.selectbox("Company", company_options)
    min_value = st.number_input("Min Deal Value (₹ Cr)", min_value=0.0, value=0.0, step=1.0)
    deal_type_filter = st.radio("Deal Type", ["Both", "BUY only", "SELL only"])

# ── Fetch data ─────────────────────────────────────────────────────────────────
with st.spinner("Fetching block deals from NSE…"):
    block_raw, block_src, block_ts = fetch_block_deals()

with st.spinner("Fetching bulk deals from NSE…"):
    bulk_raw, bulk_src, bulk_ts = fetch_bulk_deals()

block_df = build_deal_df(block_raw, block_src)
bulk_df = build_deal_df(bulk_raw, bulk_src)

# ── KPI cards ─────────────────────────────────────────────────────────────────
all_deals_df = pd.concat([block_df, bulk_df], ignore_index=True) if not (block_df.empty and bulk_df.empty) else pd.DataFrame()

total_deals = len(all_deals_df) if not all_deals_df.empty else 0
total_value = round(all_deals_df["Value (₹ Cr)"].sum(), 2) if not all_deals_df.empty and "Value (₹ Cr)" in all_deals_df.columns else 0
biggest_deal = round(all_deals_df["Value (₹ Cr)"].max(), 2) if not all_deals_df.empty and "Value (₹ Cr)" in all_deals_df.columns else 0

k1, k2, k3 = st.columns(3)
k1.metric("Total Deals Today", total_deals)
k2.metric("Total Value", f"₹{total_value:,.2f} Cr")
k3.metric("Biggest Single Deal", f"₹{biggest_deal:,.2f} Cr")

st.markdown(
    f'<div style="color:#a38060;font-size:11px;text-align:right">Last updated: {now_ist()}</div>',
    unsafe_allow_html=True,
)


def apply_filters(df):
    if df.empty:
        return df
    if sel_company != "All":
        df = df[df["Company"] == sel_company]
    if min_value > 0 and "Value (₹ Cr)" in df.columns:
        df = df[df["Value (₹ Cr)"] >= min_value]
    if deal_type_filter == "BUY only":
        df = df[df["Buy/Sell"] == "BUY"]
    elif deal_type_filter == "SELL only":
        df = df[df["Buy/Sell"] == "SELL"]
    return df


def style_deals(df):
    if df.empty:
        return df
    def row_color(row):
        color = "#d1fae5" if row.get("Buy/Sell") == "BUY" else "#fee2e2"
        return [f"background-color: {color}" for _ in row]
    return df.style.apply(row_color, axis=1)


def show_deal_table(df, label):
    df = apply_filters(df)
    if df.empty:
        st.markdown(
            f"""<div style='background:{BG_ALT};border:1px solid {BORDER};border-radius:8px;
            padding:16px;color:#6b7a8d;font-size:14px;text-align:center'>
            No {label} found for Z47 Index companies today.
            This is normal on low-volume days.
            </div>""",
            unsafe_allow_html=True,
        )
        return
    styled = style_deals(df)
    st.dataframe(
        styled,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Price (₹)": st.column_config.NumberColumn(format="₹%.2f"),
            "Value (₹ Cr)": st.column_config.NumberColumn(format="₹%.2f Cr"),
            "Quantity": st.column_config.NumberColumn(format="%d"),
        },
    )
    st.caption(f"Source: {block_src if 'block' in label.lower() else bulk_src} | {len(df)} deal(s) shown")


# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📦 Today's Block Deals", "📊 Today's Bulk Deals", "🗓️ Historical (7 days)"])

with tab1:
    st.markdown(f"**Block Deals for Z47 Index Companies**")
    if block_src == "No data":
        warn_banner("Could not fetch block deals from NSE or BSE. Please try again later.")
    show_deal_table(block_df, "block deals")
    st.markdown(
        f'<div style="color:#a38060;font-size:11px;text-align:right">Data as of: {block_ts.strftime("%d-%m-%Y %H:%M:%S IST") if block_ts else "N/A"}</div>',
        unsafe_allow_html=True,
    )

with tab2:
    st.markdown(f"**Bulk Deals for Z47 Index Companies**")
    if bulk_src == "No data":
        warn_banner("Could not fetch bulk deals from NSE or BSE. Please try again later.")
    show_deal_table(bulk_df, "bulk deals")
    st.markdown(
        f'<div style="color:#a38060;font-size:11px;text-align:right">Data as of: {bulk_ts.strftime("%d-%m-%Y %H:%M:%S IST") if bulk_ts else "N/A"}</div>',
        unsafe_allow_html=True,
    )

with tab3:
    st.markdown("**Historical Block & Bulk Deals (Last 7 Days) — Z47 Index**")
    warn_banner(
        "Historical multi-day deal data requires authenticated NSE API access. "
        "Showing today's data as the most recent snapshot."
    )
    if not all_deals_df.empty:
        hist_df = apply_filters(all_deals_df)
        if not hist_df.empty:
            styled_hist = style_deals(hist_df)
            st.dataframe(
                styled_hist,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Price (₹)": st.column_config.NumberColumn(format="₹%.2f"),
                    "Value (₹ Cr)": st.column_config.NumberColumn(format="₹%.2f Cr"),
                    "Quantity": st.column_config.NumberColumn(format="%d"),
                },
            )
        else:
            st.info("No deals match the current filters.")
    else:
        st.markdown(
            f"""<div style='background:{BG_ALT};border:1px solid {BORDER};border-radius:8px;
            padding:16px;color:#6b7a8d;font-size:14px;text-align:center'>
            No block/bulk deals found for Z47 Index companies today.
            This is normal on low-volume days.
            </div>""",
            unsafe_allow_html=True,
        )
    st.markdown(
        f'<div style="color:#a38060;font-size:11px;text-align:right">Last updated: {now_ist()}</div>',
        unsafe_allow_html=True,
    )
