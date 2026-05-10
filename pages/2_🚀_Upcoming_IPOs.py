import streamlit as st
st.set_page_config(page_title="Upcoming IPOs | Z47", page_icon="🚀", layout="wide")

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sidebar_nav import render_sidebar

import requests
import pandas as pd
import pytz
from datetime import datetime, date, timedelta
from streamlit_autorefresh import st_autorefresh
from bs4 import BeautifulSoup

# ── Theme ──────────────────────────────────────────────────────────────────────
BG = "#fdf6ec"; CARD_BG = "#f6f9fd"; BG_ALT = "#edf3fa"; BORDER = "#ccdaea"
IST = pytz.timezone("Asia/Kolkata")

def now_ist():
    return datetime.now(IST).strftime("%d-%m-%Y %H:%M:%S IST")

def today_ist():
    return datetime.now(IST).date()

def warn_banner(msg):
    st.markdown(
        f"""<div style='background:#fef3cd;border:1px solid #ffc107;border-radius:8px;
        padding:10px 16px;color:#856404;font-size:13px;margin-bottom:12px'>⚠️ {msg}</div>""",
        unsafe_allow_html=True,
    )

def success_banner(msg):
    st.markdown(
        f"""<div style='background:#d1fae5;border:1px solid #34d399;border-radius:8px;
        padding:10px 16px;color:#065f46;font-size:13px;margin-bottom:12px'>✅ {msg}</div>""",
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

st_autorefresh(interval=900_000, key="upcoming_ipo_refresh")
render_sidebar()

# ── NSE headers ───────────────────────────────────────────────────────────────
NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
    "X-Requested-With": "XMLHttpRequest",
}

# ── Hardcoded fallback pipeline ────────────────────────────────────────────────
UPCOMING_FALLBACK = [
    {
        "company": "Ola Cabs", "sector": "Consumer / Consumertech",
        "status": "DRHP Filed", "open_date": None, "close_date": None,
        "expected_listing": "2025-Q3", "price_band": "TBD", "issue_size": "~₹5,000 cr",
        "gmp": "N/A", "gmp_pct": None,
        "description": "Ride-hailing platform DRHP filed with SEBI in early 2025.",
    },
    {
        "company": "Meesho", "sector": "Consumer / Consumertech",
        "status": "DRHP Filed", "open_date": None, "close_date": None,
        "expected_listing": "2025-Q3", "price_band": "₹380–400", "issue_size": "~₹5,000 cr",
        "gmp": "N/A", "gmp_pct": None,
        "description": "Social commerce platform, one of India's largest e-commerce players.",
    },
    {
        "company": "PhonePe", "sector": "Fintech/FS",
        "status": "Expected 2025", "open_date": None, "close_date": None,
        "expected_listing": "2025-Q4", "price_band": "TBD", "issue_size": "TBD",
        "gmp": "N/A", "gmp_pct": None,
        "description": "UPI-based payments giant, Walmart-backed. India's largest digital payments app.",
    },
    {
        "company": "Zepto", "sector": "Consumer / Consumertech",
        "status": "DRHP Filed", "open_date": None, "close_date": None,
        "expected_listing": "2025-Q3", "price_band": "TBD", "issue_size": "~₹3,500 cr",
        "gmp": "N/A", "gmp_pct": None,
        "description": "10-minute grocery delivery startup. DRHP filed with SEBI in 2025.",
    },
    {
        "company": "Boat (Imagine Marketing)", "sector": "Consumer / Consumertech",
        "status": "DRHP Filed", "open_date": None, "close_date": None,
        "expected_listing": "2025-Q3", "price_band": "TBD", "issue_size": "~₹2,000 cr",
        "gmp": "N/A", "gmp_pct": None,
        "description": "Consumer electronics and wearables brand. India's No.1 wearable brand.",
    },
    {
        "company": "Lenskart", "sector": "Consumer / Consumertech",
        "status": "Expected", "open_date": None, "close_date": None,
        "expected_listing": "2025-Q4", "price_band": "TBD", "issue_size": "~₹3,500 cr",
        "gmp": "N/A", "gmp_pct": None,
        "description": "Omnichannel eyewear retailer. Backed by SoftBank and KKR.",
    },
    {
        "company": "Rebel Foods (Faasos)", "sector": "Consumer / Consumertech",
        "status": "Expected", "open_date": None, "close_date": None,
        "expected_listing": "2025-Q4", "price_band": "TBD", "issue_size": "~₹2,500 cr",
        "gmp": "N/A", "gmp_pct": None,
        "description": "Cloud kitchen platform (Faasos, Behrouz, Oven Story). Backed by Coatue.",
    },
    {
        "company": "Urban Company", "sector": "Consumer / Consumertech",
        "status": "Expected", "open_date": None, "close_date": None,
        "expected_listing": "2025-Q3", "price_band": "₹420–440", "issue_size": "~₹3,000 cr",
        "gmp": "N/A", "gmp_pct": None,
        "description": "Home services platform. Backed by Accel, Tiger Global.",
    },
]

# ── Data fetchers ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=900)
def fetch_upcoming_ipos_investorgain():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    results = []
    try:
        r = requests.get(
            "https://www.investorgain.com/report/live-ipo-gmp/331/",
            headers=headers, timeout=15,
        )
        soup = BeautifulSoup(r.text, "lxml")
        table = soup.find("table", {"id": "mainTable"}) or soup.find("table")
        if not table:
            return results
        rows = table.find_all("tr")[1:]
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 5:
                continue
            try:
                company = cells[0].get_text(strip=True)
                price_band = cells[1].get_text(strip=True) if len(cells) > 1 else "N/A"
                gmp = cells[4].get_text(strip=True) if len(cells) > 4 else "N/A"
                exp_listing = cells[5].get_text(strip=True) if len(cells) > 5 else "N/A"
                open_date = cells[2].get_text(strip=True) if len(cells) > 2 else "N/A"
                close_date = cells[3].get_text(strip=True) if len(cells) > 3 else "N/A"
                results.append({
                    "company": company,
                    "price_band": price_band,
                    "open_date": open_date,
                    "close_date": close_date,
                    "gmp": gmp,
                    "expected_listing": exp_listing,
                    "source": "investorgain",
                })
            except Exception:
                continue
    except Exception:
        pass
    return results


@st.cache_data(ttl=900)
def fetch_upcoming_ipos_ipowatch():
    headers = {"User-Agent": "Mozilla/5.0"}
    results = []
    try:
        r = requests.get(
            "https://ipowatch.in/ipo-grey-market-premium-latest-ipo-gmp/",
            headers=headers, timeout=15,
        )
        soup = BeautifulSoup(r.text, "lxml")
        tables = soup.find_all("table")
        for tbl in tables:
            rows = tbl.find_all("tr")[1:]
            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 4:
                    continue
                try:
                    company = cells[0].get_text(strip=True)
                    price_band = cells[1].get_text(strip=True) if len(cells) > 1 else "N/A"
                    gmp = cells[2].get_text(strip=True) if len(cells) > 2 else "N/A"
                    exp_pct = cells[3].get_text(strip=True) if len(cells) > 3 else "N/A"
                    if company and len(company) > 1:
                        results.append({
                            "company": company,
                            "price_band": price_band,
                            "gmp": gmp,
                            "expected_listing": exp_pct,
                            "source": "ipowatch",
                        })
                except Exception:
                    continue
    except Exception:
        pass
    return results


@st.cache_data(ttl=300)
def fetch_ipo_subscription(symbol):
    try:
        s = requests.Session()
        s.get("https://www.nseindia.com", headers=NSE_HEADERS, timeout=6)
        r = s.get(
            f"https://www.nseindia.com/api/ipo-detail?symbol={symbol}",
            headers=NSE_HEADERS, timeout=8,
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}


@st.cache_data(ttl=300)
def fetch_live_ipos_nse():
    """Fetch currently open IPOs from NSE."""
    try:
        s = requests.Session()
        s.get("https://www.nseindia.com", headers=NSE_HEADERS, timeout=6)
        r = s.get(
            "https://www.nseindia.com/api/ipo-current-allotment",
            headers=NSE_HEADERS, timeout=10,
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}


# ── Page ───────────────────────────────────────────────────────────────────────
st.markdown("## 🚀 Upcoming IPOs — New Age Tech & Fintech")
st.markdown(
    "<p style='color:#6b7a8d;font-size:14px'>Tracks open, upcoming, and pipeline new-age tech & fintech IPOs with live GMP data.</p>",
    unsafe_allow_html=True,
)

col_h, col_b = st.columns([6, 1])
with col_b:
    if st.button("🔄 Refresh Now"):
        st.cache_data.clear()
        st.rerun()

# ── Section 1: Live IPOs (Open Now) ───────────────────────────────────────────
st.markdown("---")
st.markdown(
    f"""<div style='background:{CARD_BG};border:1px solid {BORDER};border-radius:10px;
    padding:14px 18px;margin-bottom:12px'>
    <h3 style='margin:0;color:#1e40af'>🟢 Live IPOs (Open for Subscription)</h3>
    </div>""",
    unsafe_allow_html=True,
)

with st.spinner("Checking for live IPOs…"):
    live_nse = fetch_live_ipos_nse()
    ig_ipos = fetch_upcoming_ipos_investorgain()

live_shown = False
if ig_ipos:
    today = today_ist()
    for ipo in ig_ipos:
        try:
            od = ipo.get("open_date", "")
            cd = ipo.get("close_date", "")
            # If open date and close date bracket today, treat as live
            od_parsed = datetime.strptime(od, "%d-%m-%Y").date() if od and od != "N/A" else None
            cd_parsed = datetime.strptime(cd, "%d-%m-%Y").date() if cd and cd != "N/A" else None
            if od_parsed and cd_parsed and od_parsed <= today <= cd_parsed:
                live_shown = True
                gmp_val = ipo.get("gmp", "N/A")
                gmp_color = "#16a34a" if "+" in str(gmp_val) else ("#dc2626" if "-" in str(gmp_val) else "#6b7a8d")
                st.markdown(
                    f"""<div style='background:{BG_ALT};border:2px solid #34d399;border-radius:10px;
                    padding:14px 18px;margin-bottom:10px'>
                    <span style='background:#065f46;color:white;border-radius:5px;
                    padding:2px 8px;font-size:12px;font-weight:700'>OPEN NOW</span>
                    &nbsp;&nbsp;<b style='font-size:16px'>{ipo['company']}</b><br/>
                    <span style='color:#6b7a8d;font-size:13px'>Open: {od} &nbsp;|&nbsp; Close: {cd}
                    &nbsp;|&nbsp; Price Band: {ipo.get('price_band','N/A')}
                    &nbsp;|&nbsp; GMP: <b style='color:{gmp_color}'>{gmp_val}</b></span>
                    </div>""",
                    unsafe_allow_html=True,
                )
        except Exception:
            continue

if not live_shown:
    st.markdown(
        f"""<div style='background:{BG_ALT};border:1px solid {BORDER};border-radius:8px;
        padding:14px;color:#6b7a8d;font-size:14px'>
        No new-age tech/fintech IPOs currently open for subscription.
        Check back closer to opening dates.
        </div>""",
        unsafe_allow_html=True,
    )

st.markdown(
    f'<div style="color:#a38060;font-size:11px;text-align:right">Last updated: {now_ist()}</div>',
    unsafe_allow_html=True,
)

# ── Section 2: Opening Soon ────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    f"""<div style='background:{CARD_BG};border:1px solid {BORDER};border-radius:10px;
    padding:14px 18px;margin-bottom:12px'>
    <h3 style='margin:0;color:#1e40af'>📅 Opening Soon (Next 30 Days)</h3>
    </div>""",
    unsafe_allow_html=True,
)

opening_soon = []
if ig_ipos:
    cutoff = today_ist() + timedelta(days=30)
    for ipo in ig_ipos:
        try:
            od = ipo.get("open_date", "")
            od_parsed = datetime.strptime(od, "%d-%m-%Y").date() if od and od != "N/A" else None
            if od_parsed and today_ist() < od_parsed <= cutoff:
                opening_soon.append(ipo)
        except Exception:
            continue

if opening_soon:
    df_soon = pd.DataFrame(opening_soon)[["company", "price_band", "open_date", "close_date", "gmp", "expected_listing"]]
    df_soon.columns = ["Company", "Price Band", "Open Date", "Close Date", "GMP", "Exp. Listing"]
    st.dataframe(df_soon, use_container_width=True, hide_index=True)
else:
    warn_banner("Could not fetch opening-soon data from live source. Showing known pipeline below.")
    fallback_df = pd.DataFrame([
        {
            "Company": f["company"],
            "Sector": f["sector"],
            "Status": f["status"],
            "Price Band": f["price_band"],
            "Issue Size": f["issue_size"],
            "Expected Listing": f["expected_listing"],
        }
        for f in UPCOMING_FALLBACK
        if f["status"] in ("DRHP Filed", "Expected 2025", "Expected")
    ])
    st.dataframe(fallback_df, use_container_width=True, hide_index=True)

# ── Section 3: DRHP Filed / SEBI Approved ─────────────────────────────────────
st.markdown("---")
st.markdown(
    f"""<div style='background:{CARD_BG};border:1px solid {BORDER};border-radius:10px;
    padding:14px 18px;margin-bottom:12px'>
    <h3 style='margin:0;color:#1e40af'>📂 DRHP Filed / SEBI Pipeline</h3>
    </div>""",
    unsafe_allow_html=True,
)

pipeline_df = pd.DataFrame([
    {
        "Company": f["company"],
        "Sector": f["sector"],
        "Status": f["status"],
        "Price Band": f["price_band"],
        "Issue Size": f["issue_size"],
        "Expected": f["expected_listing"],
        "About": f["description"],
    }
    for f in UPCOMING_FALLBACK
])

st.dataframe(
    pipeline_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "About": st.column_config.TextColumn(width="large"),
    },
)

# ── Section 4: GMP Tracker ─────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    f"""<div style='background:{CARD_BG};border:1px solid {BORDER};border-radius:10px;
    padding:14px 18px;margin-bottom:12px'>
    <h3 style='margin:0;color:#1e40af'>🔮 GMP Tracker (Grey Market Premium)</h3>
    </div>""",
    unsafe_allow_html=True,
)

iw_ipos = fetch_upcoming_ipos_ipowatch()

gmp_rows = []
sources_used = []

if ig_ipos:
    sources_used.append("investorgain.com")
    for i in ig_ipos:
        gmp_str = str(i.get("gmp", ""))
        try:
            gmp_num = float(gmp_str.replace("₹", "").replace(",", "").replace("+", "").strip())
        except Exception:
            gmp_num = None
        gmp_rows.append({
            "Company": i.get("company", ""),
            "Price Band": i.get("price_band", "N/A"),
            "Open": i.get("open_date", "N/A"),
            "Close": i.get("close_date", "N/A"),
            "GMP (₹)": gmp_str,
            "GMP_num": gmp_num,
            "Exp. Listing": i.get("expected_listing", "N/A"),
            "Source": "investorgain",
        })
elif iw_ipos:
    sources_used.append("ipowatch.in")
    for i in iw_ipos:
        gmp_str = str(i.get("gmp", ""))
        try:
            gmp_num = float(gmp_str.replace("₹", "").replace(",", "").replace("+", "").strip())
        except Exception:
            gmp_num = None
        gmp_rows.append({
            "Company": i.get("company", ""),
            "Price Band": i.get("price_band", "N/A"),
            "Open": "N/A",
            "Close": "N/A",
            "GMP (₹)": gmp_str,
            "GMP_num": gmp_num,
            "Exp. Listing": i.get("expected_listing", "N/A"),
            "Source": "ipowatch",
        })
else:
    warn_banner("Live GMP data unavailable. Both investorgain.com and ipowatch.in returned no data.")

if gmp_rows:
    gmp_df = pd.DataFrame(gmp_rows)
    display_cols = ["Company", "Price Band", "Open", "Close", "GMP (₹)", "Exp. Listing", "Source"]

    def gmp_style(row):
        num = row.get("GMP_num")
        if num is None:
            return [""] * len(row)
        color = "#d1fae5" if num > 0 else ("#fee2e2" if num < 0 else "")
        return [f"background-color: {color}" if col == "GMP (₹)" else "" for col in row.index]

    styled_gmp = gmp_df[display_cols].style.apply(
        lambda row: [
            f"background-color: #d1fae5;font-weight:600;color:#065f46" if row.name < len(gmp_rows) and gmp_rows[row.name].get("GMP_num", 0) > 0 and col == "GMP (₹)"
            else f"background-color: #fee2e2;font-weight:600;color:#7f1d1d" if row.name < len(gmp_rows) and gmp_rows[row.name].get("GMP_num", 0) < 0 and col == "GMP (₹)"
            else ""
            for col in display_cols
        ],
        axis=1,
    )
    st.dataframe(styled_gmp, use_container_width=True, hide_index=True, height=400)
    if sources_used:
        st.caption(f"Source: {', '.join(sources_used)}")

st.markdown(
    f'<div style="color:#a38060;font-size:11px;text-align:right">Last updated: {now_ist()}</div>',
    unsafe_allow_html=True,
)
