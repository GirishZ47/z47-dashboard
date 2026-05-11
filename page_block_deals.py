"""Block & Bulk Deals module — called by app.py routing."""
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

CARD_BG = "#f6f9fd"; BG_ALT = "#edf3fa"; BORDER = "#ccdaea"
IST = pytz.timezone("Asia/Kolkata")

Z47_SYMBOLS  = {c["ticker"] for c in COMPANIES if c["exchange"] == "NSE"}
Z47_NAME_MAP = {c["ticker"]: c["name"] for c in COMPANIES}

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
    "X-Requested-With": "XMLHttpRequest",
}


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


@st.cache_data(ttl=300)
def _block_deals():
    try:
        s = requests.Session()
        s.get("https://www.nseindia.com", headers=NSE_HEADERS, timeout=6)
        time.sleep(1)
        r = s.get("https://www.nseindia.com/api/block-deal", headers=NSE_HEADERS, timeout=10)
        if r.status_code == 200:
            return r.json().get("data", []), "NSE", datetime.now(IST)
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
def _bulk_deals():
    try:
        s = requests.Session()
        s.get("https://www.nseindia.com", headers=NSE_HEADERS, timeout=6)
        time.sleep(1)
        r = s.get("https://www.nseindia.com/api/bulk-deal", headers=NSE_HEADERS, timeout=10)
        if r.status_code == 200:
            return r.json().get("data", []), "NSE", datetime.now(IST)
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
    try:    qty_i = int(float(str(qty).replace(",", "")))
    except: qty_i = 0
    try:    px    = float(str(price).replace(",", ""))
    except: px    = 0.0
    return {
        "Symbol":        sym,
        "Company":       Z47_NAME_MAP.get(sym, sym),
        "Client / Party": cli,
        "Buy/Sell":      "BUY" if "B" in ttype else "SELL",
        "Quantity":      qty_i,
        "Price (₹)":     px,
        "Value (₹ Cr)":  round(qty_i * px / 1e7, 2),
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

def _fetch_nse_deal_history(deal_type="bulk", days=90):
    """Fetch block/bulk deal archives from NSE API."""
    try:
        s = requests.Session()
        s.get("https://www.nseindia.com", headers=NSE_HEADERS, timeout=8)
        time.sleep(1)
        endpoint = ("https://www.nseindia.com/api/block-deal-archives"
                    if deal_type == "block" else
                    "https://www.nseindia.com/api/bulk-deal-archives")
        r = s.get(endpoint, headers=NSE_HEADERS, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                return data, "NSE"
            if isinstance(data, dict):
                return data.get("data", []), "NSE"
    except Exception:
        pass
    return [], None


def _fetch_bse_deal_history(deal_type="bulk"):
    """Fetch block/bulk deal history from BSE API."""
    try:
        bse_type = "B" if deal_type == "block" else "BU"
        r = requests.get(
            f"https://api.bseindia.com/BseIndiaAPI/api/BlockBulkDeals/w?Type={bse_type}",
            headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
        if r.status_code == 200:
            return r.json().get("Table", []), "BSE"
    except Exception:
        pass
    return [], None


def _norm_hist(d, src, deal_type):
    """Normalise a historical deal record to a flat dict."""
    if src == "NSE":
        sym    = str(d.get("symbol", d.get("Symbol", ""))).upper().replace(".NS", "")
        cli    = d.get("clientName", d.get("client_name", d.get("Client_Name", "")))
        ttype  = d.get("buyOrSell", d.get("buy_sell", d.get("Buy_Sell", ""))).upper()
        qty    = d.get("quantity",   d.get("qty",      d.get("Quantity",  0)))
        price  = d.get("tradePrice", d.get("trade_price", d.get("Rate", 0)))
        date_s = d.get("date",       d.get("DT_DATE",   d.get("DEAL_DATE", "")))
    else:
        sym    = str(d.get("SCRIP_CD", d.get("Symbol", ""))).upper().replace(".NS", "")
        cli    = d.get("Client_Name", d.get("clientName", ""))
        ttype  = d.get("Buy_Sell",    d.get("buyOrSell", "")).upper()
        qty    = d.get("Quantity",    d.get("quantity",   0))
        price  = d.get("Rate",        d.get("tradePrice", 0))
        date_s = d.get("DT_DATE",     d.get("DEAL_DATE",  d.get("date", "")))
    try:    qty_i = int(float(str(qty).replace(",", "")))
    except: qty_i = 0
    try:    px    = float(str(price).replace(",", ""))
    except: px    = 0.0
    # Parse date
    date_parsed = None
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%d %b %Y", "%Y%m%d"):
        try:
            date_parsed = datetime.strptime(str(date_s).split("T")[0], fmt).date()
            break
        except Exception:
            continue
    if sym not in Z47_SYMBOLS:
        return None
    return {
        "Date":          str(date_parsed) if date_parsed else date_s,
        "Deal Type":     deal_type.title(),
        "Symbol":        sym,
        "Company":       Z47_NAME_MAP.get(sym, sym),
        "Client / Party": cli,
        "Buy/Sell":      "BUY" if "B" in ttype else "SELL",
        "Quantity":      qty_i,
        "Price (₹)":     px,
        "Value (₹ Cr)":  round(qty_i * px / 1e7, 2),
    }


def _load_history_cache():
    """Load or refresh the 90-day deal history from session_state cache."""
    now_ts = time.time()
    last   = st.session_state.get("bd_hist_ts", 0)
    if now_ts - last < _HIST_TTL and "bd_hist_df" in st.session_state:
        return st.session_state["bd_hist_df"], st.session_state.get("bd_hist_src", "cache")

    all_rows = []
    sources  = []
    for deal_type in ("block", "bulk"):
        raw, src = _fetch_nse_deal_history(deal_type)
        if not raw:
            raw, src = _fetch_bse_deal_history(deal_type)
        if raw and src:
            sources.append(f"{src} {deal_type}")
            for d in raw:
                norm = _norm_hist(d, src, deal_type)
                if norm:
                    all_rows.append(norm)

    if all_rows:
        df = pd.DataFrame(all_rows)
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date"]).sort_values("Date", ascending=False)
        df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
    else:
        df = pd.DataFrame()

    st.session_state["bd_hist_df"]  = df
    st.session_state["bd_hist_ts"]  = now_ts
    st.session_state["bd_hist_src"] = ", ".join(sources) if sources else "unavailable"
    return df, st.session_state["bd_hist_src"]


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
        st.warning(
            "Historical deal data could not be fetched from NSE or BSE. "
            "This is common when NSE blocks programmatic access. "
            "Try the Reload button or check back during market hours."
        )
        st.caption(f"Sources attempted: NSE archives, BSE archives | {_now_ist()}")
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
        st.dataframe(styled_h, use_container_width=True, hide_index=True,
                     column_config={
                         "Price (₹)":    st.column_config.NumberColumn(format="₹%.2f"),
                         "Value (₹ Cr)": st.column_config.NumberColumn(format="₹%.2f Cr"),
                         "Quantity":     st.column_config.NumberColumn(format="%d"),
                     }, height=380)

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


# ── Render ─────────────────────────────────────────────────────────────────────
def render():
    market_open = _is_market_open()
    if market_open:
        st_autorefresh(interval=300_000, key="block_bulk_refresh")

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
            st.cache_data.clear()
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

    # ── Fetch ────────────────────────────────────────────────────────────────
    with st.spinner("Fetching block deals…"):
        br, bsrc, bts = _block_deals()
    with st.spinner("Fetching bulk deals…"):
        ur, usrc, uts = _bulk_deals()

    block_df = _build(br, bsrc)
    bulk_df  = _build(ur, usrc)
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
        st.dataframe(_style(df), use_container_width=True, hide_index=True,
                     column_config={
                         "Price (₹)":   st.column_config.NumberColumn(format="₹%.2f"),
                         "Value (₹ Cr)":st.column_config.NumberColumn(format="₹%.2f Cr"),
                         "Quantity":     st.column_config.NumberColumn(format="%d"),
                     })
        st.caption(f"Source: {src} | {len(df)} deal(s) shown")

    tab1, tab2, tab3, tab4 = st.tabs(["📦 Block Deals", "📊 Bulk Deals", "🗓️ All Deals Today", "📚 History (60–90 Days)"])

    with tab1:
        st.markdown("**Block Deals for Z47 Index Companies**")
        if bsrc == "No data":
            _warn("Could not fetch block deals from NSE or BSE.")
        _show(block_df, "block deals", bsrc)
        st.markdown(f'<div style="color:#a38060;font-size:11px;text-align:right">As of: {bts.strftime("%d-%m-%Y %H:%M IST") if bts else "N/A"}</div>',
                    unsafe_allow_html=True)

    with tab2:
        st.markdown("**Bulk Deals for Z47 Index Companies**")
        if usrc == "No data":
            _warn("Could not fetch bulk deals from NSE or BSE.")
        _show(bulk_df, "bulk deals", usrc)
        st.markdown(f'<div style="color:#a38060;font-size:11px;text-align:right">As of: {uts.strftime("%d-%m-%Y %H:%M IST") if uts else "N/A"}</div>',
                    unsafe_allow_html=True)

    with tab3:
        st.markdown("**All Block & Bulk Deals Today — Z47 Index**")
        _show(all_df, "deals", f"{bsrc}/{usrc}")
        st.markdown(f'<div style="color:#a38060;font-size:11px;text-align:right">Updated: {_now_ist()}</div>',
                    unsafe_allow_html=True)

    with tab4:
        _render_history_tab()

    st.markdown("---")
    render_z47_assistant(context="block_deals")
