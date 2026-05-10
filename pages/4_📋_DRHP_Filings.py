import streamlit as st
st.set_page_config(page_title="DRHP Filings | Z47", page_icon="📋", layout="wide")

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sidebar_nav import render_sidebar

import requests
import pandas as pd
import pytz
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
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

st_autorefresh(interval=1_800_000, key="drhp_refresh")
render_sidebar()

# ── Sector tags ────────────────────────────────────────────────────────────────
Z47_SECTORS = [
    "fintech", "payments", "insurtech", "lending", "wealthtech", "neobank",
    "new-age tech", "saas", "consumer tech", "edtech", "healthtech",
    "logistics", "ecommerce", "foodtech", "traveltech", "proptech",
    "ev", "gaming", "media", "b2b tech",
]

# ── Hardcoded known filings ────────────────────────────────────────────────────
KNOWN_FILINGS = [
    {
        "company": "Zepto",
        "filing_date": "2025-01",
        "type": "DRHP",
        "sector": "ecommerce",
        "issue_size": "~₹3,500 cr",
        "brlms": "Kotak, Goldman Sachs",
        "pdf_link": None,
        "description": "10-minute grocery delivery; Series G unicorn. India's fastest growing quick commerce.",
    },
    {
        "company": "PhonePe",
        "filing_date": "2025-02",
        "type": "DRHP",
        "sector": "fintech",
        "issue_size": "TBD",
        "brlms": "TBD",
        "pdf_link": None,
        "description": "India's largest UPI payments platform. Backed by Walmart.",
    },
    {
        "company": "Lenskart",
        "filing_date": "2025-01",
        "type": "DRHP",
        "sector": "consumer tech",
        "issue_size": "~₹3,500 cr",
        "brlms": "TBD",
        "pdf_link": None,
        "description": "Omnichannel eyewear retailer backed by SoftBank and KKR.",
    },
    {
        "company": "Meesho",
        "filing_date": "2025-03",
        "type": "DRHP",
        "sector": "ecommerce",
        "issue_size": "TBD",
        "brlms": "TBD",
        "pdf_link": None,
        "description": "Social commerce platform serving Tier 2/3 India. SoftBank-backed.",
    },
    {
        "company": "Urban Company",
        "filing_date": "2025-02",
        "type": "DRHP",
        "sector": "consumer tech",
        "issue_size": "~₹3,000 cr",
        "brlms": "TBD",
        "pdf_link": None,
        "description": "Home services marketplace. Accel & Tiger Global backed.",
    },
    {
        "company": "Rebel Foods (Faasos)",
        "filing_date": "2024-12",
        "type": "DRHP",
        "sector": "foodtech",
        "issue_size": "~₹2,500 cr",
        "brlms": "TBD",
        "pdf_link": None,
        "description": "Cloud kitchen network running Faasos, Behrouz Biryani, Oven Story.",
    },
    {
        "company": "Ola Cabs",
        "filing_date": "2025-01",
        "type": "DRHP",
        "sector": "consumer tech",
        "issue_size": "~₹5,000 cr",
        "brlms": "TBD",
        "pdf_link": None,
        "description": "Ride-hailing platform. SoftBank-backed. India's second-largest cab aggregator.",
    },
    {
        "company": "Pine Labs",
        "filing_date": "2025-01",
        "type": "RHP",
        "sector": "fintech",
        "issue_size": "~₹6,000 cr",
        "brlms": "Axis, ICICI",
        "pdf_link": None,
        "description": "POS and merchant payments platform. Temasek and Mastercard backed.",
    },
    {
        "company": "Boat (Imagine Marketing)",
        "filing_date": "2025-02",
        "type": "DRHP",
        "sector": "consumer tech",
        "issue_size": "~₹2,000 cr",
        "brlms": "TBD",
        "pdf_link": None,
        "description": "India's No.1 wearable brand. Warburg Pincus invested.",
    },
    {
        "company": "Capillary Technologies",
        "filing_date": "2025-01",
        "type": "RHP",
        "sector": "saas",
        "issue_size": "₹479 cr",
        "brlms": "Kotak, Axis",
        "pdf_link": None,
        "description": "Customer loyalty & CRM SaaS. Listed Feb 2025.",
    },
    {
        "company": "Groww",
        "filing_date": "2024-12",
        "type": "RHP",
        "sector": "fintech",
        "issue_size": "₹6,160 cr",
        "brlms": "Kotak, JM Financial",
        "pdf_link": None,
        "description": "Discount broker and fintech platform. Listed Feb 2025.",
    },
]


def is_z47_relevant(company_name, sector=""):
    keywords = [
        "tech", "fintech", "saas", "payments", "lending", "insurance",
        "wealthtech", "neobank", "edtech", "healthtech", "logistics",
        "ecommerce", "food", "travel", "prop", "ev", "gaming", "media",
        "b2b", "platform",
    ]
    text = (company_name + " " + sector).lower()
    return any(kw in text for kw in keywords)


def sector_badge(sector):
    sector_colors = {
        "fintech": "#16a34a", "payments": "#16a34a", "insurtech": "#16a34a",
        "lending": "#0891b2", "wealthtech": "#0891b2", "neobank": "#0891b2",
        "saas": "#7c3aed", "b2b tech": "#7c3aed",
        "ecommerce": "#ea580c", "consumer tech": "#ea580c", "foodtech": "#ea580c",
        "edtech": "#d97706", "healthtech": "#db2777",
        "logistics": "#475569", "traveltech": "#2563eb",
        "ev": "#dc2626", "gaming": "#92400e", "media": "#92400e",
        "proptech": "#6b7280",
    }
    color = sector_colors.get(sector.lower(), "#6b7280")
    return f'<span style="background:{color};color:white;border-radius:5px;padding:2px 7px;font-size:11px;font-weight:600">{sector.upper()}</span>'


# ── Live data fetchers ─────────────────────────────────────────────────────────
@st.cache_data(ttl=1800)
def fetch_bse_drhp_filings():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        r = requests.get(
            "https://api.bseindia.com/BseIndiaAPI/api/IPOQList/w?flag=P&type=M",
            headers=headers, timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            return data, "BSE API", datetime.now(IST)
    except Exception:
        pass

    try:
        r = requests.get(
            "https://www.bseindia.com/markets/PublicIssues/DraftOffer.aspx",
            headers=headers, timeout=15,
        )
        soup = BeautifulSoup(r.text, "lxml")
        table = soup.find("table", {"id": "ContentPlaceHolder1_GridViewIPO"}) or soup.find("table")
        results = []
        if table:
            rows = table.find_all("tr")[1:]
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 2:
                    company = cols[0].get_text(strip=True)
                    date_filed = cols[1].get_text(strip=True) if len(cols) > 1 else ""
                    link_tag = cols[-1].find("a")
                    pdf_link = link_tag["href"] if link_tag and "href" in link_tag.attrs else None
                    results.append({
                        "company": company,
                        "filing_date": date_filed,
                        "type": "DRHP",
                        "sector": "",
                        "issue_size": "N/A",
                        "brlms": "N/A",
                        "pdf_link": pdf_link,
                        "description": "",
                    })
        if results:
            return results, "BSE Website", datetime.now(IST)
    except Exception:
        pass

    return [], "unavailable", datetime.now(IST)


@st.cache_data(ttl=1800)
def fetch_sebi_drhp():
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(
            "https://www.sebi.gov.in/sebiweb/other/OtherAction.do?doRecognisedFpi=yes&intmId=7",
            headers=headers, timeout=15,
        )
        soup = BeautifulSoup(r.text, "lxml")
        table = soup.find("table", {"class": "table"}) or soup.find("table")
        if table:
            rows = table.find_all("tr")[1:]
            filings = []
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 3:
                    link_tag = cols[-1].find("a")
                    filings.append({
                        "company": cols[0].get_text(strip=True),
                        "filing_date": cols[1].get_text(strip=True),
                        "type": "DRHP",
                        "sector": "",
                        "issue_size": "N/A",
                        "brlms": "N/A",
                        "pdf_link": link_tag["href"] if link_tag and "href" in link_tag.attrs else None,
                        "description": "",
                    })
            if filings:
                return filings, "SEBI", datetime.now(IST)
    except Exception:
        pass
    return [], "unavailable", datetime.now(IST)


def parse_filing_date(d_str):
    for fmt in ("%Y-%m", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%b %Y", "%B %Y"):
        try:
            return datetime.strptime(d_str.strip(), fmt)
        except Exception:
            continue
    return None


def is_new_filing(filing_date_str, days=7):
    dt = parse_filing_date(filing_date_str)
    if dt is None:
        return False
    cutoff = datetime.now() - timedelta(days=days)
    return dt >= cutoff


# ── Page ───────────────────────────────────────────────────────────────────────
st.markdown("## 📋 DRHP / RHP Filings Monitor — New Age Tech & Fintech")
st.markdown(
    "<p style='color:#6b7a8d;font-size:14px'>Tracks DRHP and RHP filings from BSE/SEBI for new-age tech and fintech companies.</p>",
    unsafe_allow_html=True,
)

col_h, col_b = st.columns([6, 1])
with col_b:
    if st.button("🔄 Refresh Now"):
        st.cache_data.clear()
        st.rerun()

# ── Fetch live data ────────────────────────────────────────────────────────────
with st.spinner("Fetching BSE filings…"):
    bse_data, bse_src, bse_ts = fetch_bse_drhp_filings()

with st.spinner("Fetching SEBI filings…"):
    sebi_data, sebi_src, sebi_ts = fetch_sebi_drhp()

# Merge live + fallback
live_filings = []
if isinstance(bse_data, list) and bse_data:
    live_filings.extend(bse_data)
if isinstance(sebi_data, list) and sebi_data:
    live_filings.extend(sebi_data)

# Merge with known filings — known filings act as supplement/fallback
all_known_companies = {f["company"].lower() for f in KNOWN_FILINGS}
unique_live = []
for f in live_filings:
    if isinstance(f, dict) and f.get("company", "").lower() not in all_known_companies:
        unique_live.append(f)

combined = unique_live + KNOWN_FILINGS

if not combined:
    warn_banner("No filings data from live sources. Showing curated hardcoded list only.")
    combined = KNOWN_FILINGS

# ── New filings alert ─────────────────────────────────────────────────────────
new_filings = [f for f in combined if is_new_filing(f.get("filing_date", ""), days=7)]
if new_filings:
    st.markdown(
        f"""<div style='background:#fef9c3;border:2px solid #fbbf24;border-radius:10px;
        padding:14px 18px;margin-bottom:16px'>
        <b style='color:#92400e'>🆕 {len(new_filings)} new filing(s) in the last 7 days:</b>
        &nbsp; {', '.join(f['company'] for f in new_filings)}
        </div>""",
        unsafe_allow_html=True,
    )

# ── Sidebar filters ────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Filters")
    filing_types = ["All"] + sorted(set(f.get("type", "DRHP") for f in combined))
    sel_type = st.selectbox("Filing Type", filing_types)
    sectors_avail = sorted(set(f.get("sector", "") for f in combined if f.get("sector")))
    sel_sector_f = st.selectbox("Sector", ["All"] + sectors_avail)
    z47_only = st.checkbox("Z47-relevant only", value=False)

# ── Build table ────────────────────────────────────────────────────────────────
rows = []
for f in combined:
    z47_rel = is_z47_relevant(f.get("company", ""), f.get("sector", ""))
    new_flag = is_new_filing(f.get("filing_date", ""), days=7)
    rows.append({
        "Company": f.get("company", ""),
        "Filing Date": f.get("filing_date", ""),
        "Type": f.get("type", "DRHP"),
        "Sector": f.get("sector", "").title() if f.get("sector") else "–",
        "Issue Size": f.get("issue_size", "TBD"),
        "BRLMs": f.get("brlms", "TBD"),
        "Z47 Relevant": "✅ Yes" if z47_rel else "–",
        "PDF": f.get("pdf_link") or "–",
        "New (7d)": "🆕 New" if new_flag else "",
        "_z47": z47_rel,
        "_new": new_flag,
        "_sector_raw": f.get("sector", "").lower(),
        "_type_raw": f.get("type", "DRHP"),
        "_desc": f.get("description", ""),
    })

df = pd.DataFrame(rows)

# Apply filters
if sel_type != "All":
    df = df[df["_type_raw"] == sel_type]
if sel_sector_f != "All":
    df = df[df["_sector_raw"] == sel_sector_f.lower()]
if z47_only:
    df = df[df["_z47"] == True]

display_cols = ["Company", "Filing Date", "Type", "Sector", "Issue Size", "BRLMs", "Z47 Relevant", "PDF", "New (7d)"]
display_df = df[display_cols].copy()

# ── Render table with highlighting ────────────────────────────────────────────
def highlight_new(row):
    if row.get("New (7d)") == "🆕 New":
        return ["background-color: #fef9c3" for _ in row]
    return ["" for _ in row]

styled_df = display_df.style.apply(highlight_new, axis=1)

st.dataframe(
    styled_df,
    use_container_width=True,
    hide_index=True,
    height=500,
    column_config={
        "Company": st.column_config.TextColumn(width="medium"),
        "Issue Size": st.column_config.TextColumn(width="small"),
        "BRLMs": st.column_config.TextColumn(width="medium"),
        "PDF": st.column_config.LinkColumn("PDF / Link", display_text="View"),
        "New (7d)": st.column_config.TextColumn(width="small"),
    },
)

st.markdown(
    f'<div style="color:#a38060;font-size:11px;text-align:right">Last updated: {now_ist()}</div>',
    unsafe_allow_html=True,
)

# ── Filing detail expanders ────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### Filing Details")

selected_company = st.selectbox("Select a company to view details", [r["Company"] for r in rows])

sel_row = next((r for r in rows if r["Company"] == selected_company), None)
if sel_row:
    with st.expander(f"📄 {sel_row['Company']} — {sel_row['Type']}", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Company:** {sel_row['Company']}")
            st.markdown(f"**Filing Date:** {sel_row['Filing Date']}")
            st.markdown(f"**Filing Type:** {sel_row['Type']}")
            st.markdown(f"**Sector:** {sel_row['Sector']}")
        with col2:
            st.markdown(f"**Issue Size:** {sel_row['Issue Size']}")
            st.markdown(f"**BRLMs:** {sel_row['BRLMs']}")
            st.markdown(f"**Z47 Relevant:** {sel_row['Z47 Relevant']}")
            if sel_row["PDF"] and sel_row["PDF"] != "–":
                st.markdown(f"**PDF:** [{sel_row['PDF']}]({sel_row['PDF']})")
        if sel_row.get("_desc"):
            st.markdown(f"**About:** {sel_row['_desc']}")

# ── Stats ──────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### Summary Statistics")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Filings Tracked", len(rows))
m2.metric("New in Last 7 Days", sum(1 for r in rows if r["_new"]))
m3.metric("Z47 Relevant", sum(1 for r in rows if r["_z47"]))
m4.metric("DRHP vs RHP", f"{sum(1 for r in rows if r['_type_raw']=='DRHP')}D / {sum(1 for r in rows if r['_type_raw']=='RHP')}R")

st.markdown(
    f'<div style="color:#a38060;font-size:11px;text-align:right">Sources: BSE ({bse_src}), SEBI ({sebi_src}), Hardcoded Known Filings | Last updated: {now_ist()}</div>',
    unsafe_allow_html=True,
)
