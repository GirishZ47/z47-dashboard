"""Upcoming IPOs module — called by app.py routing."""
import streamlit as st
import requests
import pandas as pd
import pytz
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
from bs4 import BeautifulSoup
from z47_assistant import render_z47_assistant

CARD_BG = "#f6f9fd"; BG_ALT = "#edf3fa"; BORDER = "#ccdaea"
IST = pytz.timezone("Asia/Kolkata")

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
    "X-Requested-With": "XMLHttpRequest",
}


def _now_ist():
    return datetime.now(IST).strftime("%d-%m-%Y %H:%M:%S IST")


def _today_ist():
    return datetime.now(IST).date()


def _warn(msg):
    st.markdown(
        f"""<div style='background:#fef3cd;border:1px solid #ffc107;border-radius:8px;
        padding:10px 16px;color:#856404;font-size:13px;margin-bottom:12px'>⚠️ {msg}</div>""",
        unsafe_allow_html=True,
    )


UPCOMING_FALLBACK = [
    {"company": "Zepto",             "sector": "Consumer / Consumer Tech",
     "status": "DRHP Filed", "open_date": None, "close_date": None,
     "expected_listing": "2025-Q3", "price_band": "TBD", "issue_size": "~₹3,500 cr",
     "expected_mcap_cr": 50000, "expected_val_usd_b": 6.0,
     "revenue_cr": 11110, "revenue_year": "FY25", "profitable": False,
     "pat_cr": None, "book_value_cr": None,
     "expected_ev_rev": 4.5, "expected_pe": None, "expected_pb": None,
     "description": "10-minute grocery delivery startup. DRHP filed with SEBI in 2025. Valued at ~$6B in last funding round."},
    {"company": "PhonePe",           "sector": "Fintech / Financial Services",
     "status": "Expected 2025", "open_date": None, "close_date": None,
     "expected_listing": "2025-Q4", "price_band": "TBD", "issue_size": "TBD",
     "expected_mcap_cr": 83000, "expected_val_usd_b": 10.0,
     "revenue_cr": 7631, "revenue_year": "FY25", "profitable": False,
     "pat_cr": None, "book_value_cr": 8200,
     "expected_ev_rev": 10.9, "expected_pe": None, "expected_pb": 10.1,  # fintech/payments — P/B relevant; BV ~₹8,200 cr
     "description": "UPI-based payments giant, Walmart-backed. India's largest digital payments app. Last valued at ~$12B."},
    {"company": "Meesho",            "sector": "Consumer / Consumer Tech",
     "status": "DRHP Filed", "open_date": None, "close_date": None,
     "expected_listing": "2025-Q3", "price_band": "₹380–400", "issue_size": "~₹5,000 cr",
     "expected_mcap_cr": 33200, "expected_val_usd_b": 4.0,
     "revenue_cr": 7615, "revenue_year": "FY24", "profitable": False,
     "pat_cr": None, "book_value_cr": None,
     "expected_ev_rev": 4.4, "expected_pe": None, "expected_pb": None,
     "description": "Social commerce platform, one of India's largest e-commerce players. Last valued at $4.9B."},
    {"company": "Rebel Foods (Faasos)", "sector": "Consumer / Consumer Tech",
     "status": "Expected", "open_date": None, "close_date": None,
     "expected_listing": "2025-Q4", "price_band": "TBD", "issue_size": "~₹2,500 cr",
     "expected_mcap_cr": 13800, "expected_val_usd_b": 1.7,
     "revenue_cr": 1650, "revenue_year": "FY24", "profitable": False,
     "pat_cr": None, "book_value_cr": None,
     "expected_ev_rev": 8.4, "expected_pe": None, "expected_pb": None,
     "description": "Cloud kitchen platform (Faasos, Behrouz, Oven Story). Backed by Coatue. Last valued at $1.4B."},
    {"company": "Boat (Imagine Marketing)", "sector": "Consumer / Consumer Tech",
     "status": "DRHP Filed", "open_date": None, "close_date": None,
     "expected_listing": "2025-Q3", "price_band": "TBD", "issue_size": "~₹2,000 cr",
     "expected_mcap_cr": 4500, "expected_val_usd_b": 0.5,
     "revenue_cr": 3098, "revenue_year": "FY24", "profitable": True,
     "pat_cr": 82, "book_value_cr": None,
     "expected_ev_rev": 1.5, "expected_pe": 54.9, "expected_pb": None,  # PAT ~₹82 cr FY24
     "description": "Consumer electronics and wearables brand. India's No.1 wearable brand. Backed by Warburg Pincus."},
    {"company": "Lenskart",          "sector": "Consumer / Consumer Tech",
     "status": "Expected", "open_date": None, "close_date": None,
     "expected_listing": "2025-Q4", "price_band": "TBD", "issue_size": "~₹3,500 cr",
     "expected_mcap_cr": 41500, "expected_val_usd_b": 5.0,
     "revenue_cr": 5427, "revenue_year": "FY24", "profitable": False,
     "pat_cr": None, "book_value_cr": None,
     "expected_ev_rev": 7.6, "expected_pe": None, "expected_pb": None,
     "description": "Omnichannel eyewear retailer. Backed by SoftBank and KKR. Last valued at $4.5B."},
    {"company": "Ola Cabs",          "sector": "Consumer / Consumer Tech",
     "status": "DRHP Filed", "open_date": None, "close_date": None,
     "expected_listing": "2025-Q3", "price_band": "TBD", "issue_size": "~₹5,000 cr",
     "expected_mcap_cr": None, "expected_val_usd_b": None,
     "revenue_cr": 1171, "revenue_year": "FY24", "profitable": False,
     "pat_cr": None, "book_value_cr": None,
     "expected_ev_rev": None, "expected_pe": None, "expected_pb": None,
     "description": "Ride-hailing platform DRHP filed with SEBI in early 2025. Valuation uncertain."},
]


@st.cache_data(ttl=900)
def _ig_ipos():
    results = []
    try:
        r = requests.get(
            "https://www.investorgain.com/report/live-ipo-gmp/331/",
            headers={"User-Agent": "Mozilla/5.0"}, timeout=15,
        )
        soup = BeautifulSoup(r.text, "lxml")
        table = soup.find("table", {"id": "mainTable"}) or soup.find("table")
        if not table:
            return results
        for row in table.find_all("tr")[1:]:
            cells = row.find_all("td")
            if len(cells) < 5:
                continue
            try:
                results.append({
                    "company":          cells[0].get_text(strip=True),
                    "price_band":       cells[1].get_text(strip=True) if len(cells) > 1 else "N/A",
                    "open_date":        cells[2].get_text(strip=True) if len(cells) > 2 else "N/A",
                    "close_date":       cells[3].get_text(strip=True) if len(cells) > 3 else "N/A",
                    "gmp":              cells[4].get_text(strip=True) if len(cells) > 4 else "N/A",
                    "expected_listing": cells[5].get_text(strip=True) if len(cells) > 5 else "N/A",
                    "source": "investorgain",
                })
            except Exception:
                continue
    except Exception:
        pass
    return results


@st.cache_data(ttl=900)
def _iw_ipos():
    results = []
    try:
        r = requests.get(
            "https://ipowatch.in/ipo-grey-market-premium-latest-ipo-gmp/",
            headers={"User-Agent": "Mozilla/5.0"}, timeout=15,
        )
        soup = BeautifulSoup(r.text, "lxml")
        for tbl in soup.find_all("table"):
            for row in tbl.find_all("tr")[1:]:
                cells = row.find_all("td")
                if len(cells) < 4:
                    continue
                try:
                    company = cells[0].get_text(strip=True)
                    if company and len(company) > 1:
                        results.append({
                            "company":          company,
                            "price_band":       cells[1].get_text(strip=True) if len(cells) > 1 else "N/A",
                            "gmp":              cells[2].get_text(strip=True) if len(cells) > 2 else "N/A",
                            "expected_listing": cells[3].get_text(strip=True) if len(cells) > 3 else "N/A",
                            "source": "ipowatch",
                        })
                except Exception:
                    continue
    except Exception:
        pass
    return results


# ── Render ─────────────────────────────────────────────────────────────────────
def render():
    st_autorefresh(interval=900_000, key="upcoming_ipo_refresh")

    st.markdown("## 🚀 Upcoming IPOs — New Age Tech & Fintech")
    st.markdown(
        "<p style='color:#6b7a8d;font-size:14px'>Tracks open, upcoming, and pipeline new-age tech & fintech IPOs with live GMP data.</p>",
        unsafe_allow_html=True,
    )

    col_h, col_b = st.columns([6, 1])
    with col_b:
        if st.button("🔄 Refresh", key="ui_refresh"):
            st.cache_data.clear()
            st.rerun()

    # ── Open Now ──────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        f"""<div style='background:{CARD_BG};border:1px solid {BORDER};border-radius:10px;
        padding:14px 18px;margin-bottom:12px'>
        <h3 style='margin:0;color:#1e40af'>🟢 Live IPOs (Open for Subscription)</h3></div>""",
        unsafe_allow_html=True,
    )

    with st.spinner("Checking live IPOs…"):
        ig = _ig_ipos()

    live_shown = False
    if ig:
        today = _today_ist()
        for ipo in ig:
            try:
                od = ipo.get("open_date", "")
                cd = ipo.get("close_date", "")
                od_p = datetime.strptime(od, "%d-%m-%Y").date() if od and od != "N/A" else None
                cd_p = datetime.strptime(cd, "%d-%m-%Y").date() if cd and cd != "N/A" else None
                if od_p and cd_p and od_p <= today <= cd_p:
                    live_shown = True
                    gv = ipo.get("gmp", "N/A")
                    gc = "#16a34a" if "+" in str(gv) else ("#dc2626" if "-" in str(gv) else "#6b7a8d")
                    st.markdown(
                        f"""<div style='background:{BG_ALT};border:2px solid #34d399;border-radius:10px;
                        padding:14px 18px;margin-bottom:10px'>
                        <span style='background:#065f46;color:white;border-radius:5px;
                        padding:2px 8px;font-size:12px;font-weight:700'>OPEN NOW</span>
                        &nbsp;&nbsp;<b style='font-size:16px'>{ipo['company']}</b><br/>
                        <span style='color:#6b7a8d;font-size:13px'>Open: {od} &nbsp;|&nbsp; Close: {cd}
                        &nbsp;|&nbsp; Band: {ipo.get('price_band','N/A')}
                        &nbsp;|&nbsp; GMP: <b style='color:{gc}'>{gv}</b></span>
                        </div>""",
                        unsafe_allow_html=True,
                    )
            except Exception:
                continue

    if not live_shown:
        st.markdown(
            f"""<div style='background:{BG_ALT};border:1px solid {BORDER};border-radius:8px;
            padding:14px;color:#6b7a8d;font-size:14px'>
            No new-age tech/fintech IPOs currently open for subscription.</div>""",
            unsafe_allow_html=True,
        )
    st.markdown(f'<div style="color:#a38060;font-size:11px;text-align:right">Updated: {_now_ist()}</div>',
                unsafe_allow_html=True)

    # ── Opening Soon ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        f"""<div style='background:{CARD_BG};border:1px solid {BORDER};border-radius:10px;
        padding:14px 18px;margin-bottom:12px'>
        <h3 style='margin:0;color:#1e40af'>📅 Opening Soon (Next 30 Days)</h3></div>""",
        unsafe_allow_html=True,
    )

    opening_soon = []
    if ig:
        cutoff = _today_ist() + timedelta(days=30)
        for ipo in ig:
            try:
                od = ipo.get("open_date", "")
                od_p = datetime.strptime(od, "%d-%m-%Y").date() if od and od != "N/A" else None
                if od_p and _today_ist() < od_p <= cutoff:
                    opening_soon.append(ipo)
            except Exception:
                continue

    if opening_soon:
        df_s = pd.DataFrame(opening_soon)[["company", "price_band", "open_date", "close_date", "gmp", "expected_listing"]]
        df_s.columns = ["Company", "Price Band", "Open Date", "Close Date", "GMP", "Exp. Listing"]
        st.dataframe(df_s, use_container_width=True, hide_index=True)
    else:
        st.markdown(
            f"""<div style='background:{BG_ALT};border:1px solid {BORDER};border-radius:8px;
            padding:14px;color:#6b7a8d;font-size:14px'>
            No opening-soon data from live source.</div>""",
            unsafe_allow_html=True,
        )

    # ── Pipeline ──────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        f"""<div style='background:{CARD_BG};border:1px solid {BORDER};border-radius:10px;
        padding:14px 18px;margin-bottom:12px'>
        <h3 style='margin:0;color:#1e40af'>📂 DRHP Filed / SEBI Pipeline</h3></div>""",
        unsafe_allow_html=True,
    )
    pl_rows = []
    for f in UPCOMING_FALLBACK:
        mcap   = f.get("expected_mcap_cr")
        usd    = f.get("expected_val_usd_b")
        rev    = f.get("revenue_cr")
        rev_yr = f.get("revenue_year", "")
        pat    = f.get("pat_cr")
        bv     = f.get("book_value_cr")
        prof   = f.get("profitable")
        pl_rows.append({
            "Company":            f["company"],
            "Sector":             f["sector"],
            "Status":             f["status"],
            "Issue Size":         f["issue_size"],
            "Expected Listing":   f["expected_listing"],
            "Exp. MCap (₹ Cr)":   mcap,
            "Exp. Val ($B)":      usd,
            f"Revenue ({rev_yr})": rev,
            "PAT (₹ Cr)":         pat,
            "Book Value (₹ Cr)":  bv,
            "Exp. EV/Rev":        f.get("expected_ev_rev"),
            "Exp. P/E":           f.get("expected_pe"),
            "Exp. P/B":           f.get("expected_pb"),
            "Profitable?":        "✅ Yes" if prof else ("❌ No" if prof is not None else "—"),
            "About":              f["description"],
        })
    pl = pd.DataFrame(pl_rows)
    st.dataframe(pl, use_container_width=True, hide_index=True,
                 column_config={
                     "Exp. MCap (₹ Cr)":   st.column_config.NumberColumn(format="₹%d cr"),
                     "Exp. Val ($B)":       st.column_config.NumberColumn(format="$%.1fB"),
                     "Revenue (FY25)":      st.column_config.NumberColumn(format="₹%d cr"),
                     "Revenue (FY24)":      st.column_config.NumberColumn(format="₹%d cr"),
                     "Revenue ()":          st.column_config.NumberColumn(format="₹%d cr"),
                     "PAT (₹ Cr)":          st.column_config.NumberColumn(format="₹%d cr"),
                     "Book Value (₹ Cr)":   st.column_config.NumberColumn(format="₹%d cr"),
                     "Exp. EV/Rev":         st.column_config.NumberColumn(format="%.1fx"),
                     "Exp. P/E":            st.column_config.NumberColumn(format="%.1fx"),
                     "Exp. P/B":            st.column_config.NumberColumn(format="%.1fx"),
                     "About":               st.column_config.TextColumn(width="large"),
                 })

    # ── GMP Tracker ───────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        f"""<div style='background:{CARD_BG};border:1px solid {BORDER};border-radius:10px;
        padding:14px 18px;margin-bottom:12px'>
        <h3 style='margin:0;color:#1e40af'>🔮 GMP Tracker (Grey Market Premium)</h3></div>""",
        unsafe_allow_html=True,
    )

    iw = _iw_ipos()
    gmp_rows = []

    source_list = ig or iw
    source_label = "investorgain.com" if ig else ("ipowatch.in" if iw else None)
    for i in source_list:
        gmp_str = str(i.get("gmp", ""))
        try:
            gmp_num = float(gmp_str.replace("₹", "").replace(",", "").replace("+", "").strip())
        except Exception:
            gmp_num = None
        gmp_rows.append({
            "Company":       i.get("company", ""),
            "Price Band":    i.get("price_band", "N/A"),
            "Open":          i.get("open_date", "N/A"),
            "Close":         i.get("close_date", "N/A"),
            "GMP (₹)":       gmp_str,
            "GMP_num":       gmp_num,
            "Exp. Listing":  i.get("expected_listing", "N/A"),
        })

    if not gmp_rows:
        _warn("Live GMP data unavailable from both investorgain.com and ipowatch.in.")
    else:
        disp_cols = ["Company", "Price Band", "Open", "Close", "GMP (₹)", "Exp. Listing"]
        gmp_df = pd.DataFrame(gmp_rows)

        def _gmp_style(row):
            n = gmp_rows[row.name].get("GMP_num", 0) if row.name < len(gmp_rows) else 0
            return [
                ("background-color:#d1fae5;font-weight:600;color:#065f46" if n and n > 0 else
                 "background-color:#fee2e2;font-weight:600;color:#7f1d1d" if n and n < 0 else "")
                if col == "GMP (₹)" else ""
                for col in disp_cols
            ]

        styled_gmp = gmp_df[disp_cols].style.apply(_gmp_style, axis=1)
        st.dataframe(styled_gmp, use_container_width=True, hide_index=True, height=400)
        if source_label:
            st.caption(f"Source: {source_label}")

    st.markdown(f'<div style="color:#a38060;font-size:11px;text-align:right">Updated: {_now_ist()}</div>',
                unsafe_allow_html=True)

    st.markdown("---")
    render_z47_assistant(context="upcoming_ipos")
