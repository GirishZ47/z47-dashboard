"""DRHP Filings module — called by app.py routing."""
import streamlit as st
import requests
import pandas as pd
import pytz
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
from bs4 import BeautifulSoup

CARD_BG = "#f6f9fd"; BG_ALT = "#edf3fa"; BORDER = "#ccdaea"
IST = pytz.timezone("Asia/Kolkata")


def _now_ist():
    return datetime.now(IST).strftime("%d-%m-%Y %H:%M:%S IST")


def _warn(msg):
    st.markdown(
        f"""<div style='background:#fef3cd;border:1px solid #ffc107;border-radius:8px;
        padding:10px 16px;color:#856404;font-size:13px;margin-bottom:12px'>⚠️ {msg}</div>""",
        unsafe_allow_html=True,
    )


KNOWN_FILINGS = [
    {"company": "Zepto",                "filing_date": "2025-01", "type": "DRHP", "sector": "ecommerce",
     "issue_size": "~₹3,500 cr", "brlms": "Kotak, Goldman Sachs", "pdf_link": None,
     "description": "10-minute grocery delivery; Series G unicorn. India's fastest growing quick commerce."},
    {"company": "PhonePe",             "filing_date": "2025-02", "type": "DRHP", "sector": "fintech",
     "issue_size": "TBD",         "brlms": "TBD", "pdf_link": None,
     "description": "India's largest UPI payments platform. Backed by Walmart."},
    {"company": "Lenskart",            "filing_date": "2025-01", "type": "DRHP", "sector": "consumer tech",
     "issue_size": "~₹3,500 cr", "brlms": "TBD", "pdf_link": None,
     "description": "Omnichannel eyewear retailer backed by SoftBank and KKR."},
    {"company": "Meesho",              "filing_date": "2025-03", "type": "DRHP", "sector": "ecommerce",
     "issue_size": "TBD",         "brlms": "TBD", "pdf_link": None,
     "description": "Social commerce platform serving Tier 2/3 India. SoftBank-backed."},
    {"company": "Urban Company",       "filing_date": "2025-02", "type": "DRHP", "sector": "consumer tech",
     "issue_size": "~₹3,000 cr", "brlms": "TBD", "pdf_link": None,
     "description": "Home services marketplace. Accel & Tiger Global backed."},
    {"company": "Rebel Foods (Faasos)","filing_date": "2024-12", "type": "DRHP", "sector": "foodtech",
     "issue_size": "~₹2,500 cr", "brlms": "TBD", "pdf_link": None,
     "description": "Cloud kitchen network running Faasos, Behrouz Biryani, Oven Story."},
    {"company": "Ola Cabs",            "filing_date": "2025-01", "type": "DRHP", "sector": "consumer tech",
     "issue_size": "~₹5,000 cr", "brlms": "TBD", "pdf_link": None,
     "description": "Ride-hailing platform. SoftBank-backed. India's second-largest cab aggregator."},
    {"company": "Pine Labs",           "filing_date": "2025-01", "type": "RHP",  "sector": "fintech",
     "issue_size": "~₹6,000 cr", "brlms": "Axis, ICICI", "pdf_link": None,
     "description": "POS and merchant payments platform. Temasek and Mastercard backed."},
    {"company": "Boat (Imagine Marketing)", "filing_date": "2025-02", "type": "DRHP", "sector": "consumer tech",
     "issue_size": "~₹2,000 cr", "brlms": "TBD", "pdf_link": None,
     "description": "India's No.1 wearable brand. Warburg Pincus invested."},
    {"company": "Capillary Technologies","filing_date": "2025-01", "type": "RHP", "sector": "saas",
     "issue_size": "₹479 cr",   "brlms": "Kotak, Axis", "pdf_link": None,
     "description": "Customer loyalty & CRM SaaS. Listed Feb 2025."},
    {"company": "Groww",               "filing_date": "2024-12", "type": "RHP",  "sector": "fintech",
     "issue_size": "₹6,160 cr", "brlms": "Kotak, JM Financial", "pdf_link": None,
     "description": "Discount broker and fintech platform. Listed Feb 2025."},
]


def _is_z47(name, sector=""):
    kws = ["tech", "fintech", "saas", "payments", "lending", "insurance",
           "wealthtech", "neobank", "edtech", "healthtech", "logistics",
           "ecommerce", "food", "travel", "prop", "ev", "gaming", "media", "b2b", "platform"]
    return any(k in (name + " " + sector).lower() for k in kws)


def _parse_date(s):
    for fmt in ("%Y-%m", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%b %Y", "%B %Y"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except Exception:
            continue
    return None


def _is_new(s, days=7):
    dt = _parse_date(s)
    return dt is not None and dt >= datetime.now() - timedelta(days=days)


@st.cache_data(ttl=1800)
def _bse_filings():
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(
            "https://api.bseindia.com/BseIndiaAPI/api/IPOQList/w?flag=P&type=M",
            headers=headers, timeout=15)
        if r.status_code == 200:
            return r.json(), "BSE API", datetime.now(IST)
    except Exception:
        pass
    try:
        r = requests.get(
            "https://www.bseindia.com/markets/PublicIssues/DraftOffer.aspx",
            headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, "lxml")
        table = soup.find("table", {"id": "ContentPlaceHolder1_GridViewIPO"}) or soup.find("table")
        results = []
        if table:
            for row in table.find_all("tr")[1:]:
                cols = row.find_all("td")
                if len(cols) >= 2:
                    link_tag = cols[-1].find("a")
                    results.append({
                        "company": cols[0].get_text(strip=True),
                        "filing_date": cols[1].get_text(strip=True) if len(cols) > 1 else "",
                        "type": "DRHP", "sector": "", "issue_size": "N/A",
                        "brlms": "N/A", "pdf_link": link_tag["href"] if link_tag else None,
                        "description": "",
                    })
        if results:
            return results, "BSE Website", datetime.now(IST)
    except Exception:
        pass
    return [], "unavailable", datetime.now(IST)


@st.cache_data(ttl=1800)
def _sebi_filings():
    try:
        r = requests.get(
            "https://www.sebi.gov.in/sebiweb/other/OtherAction.do?doRecognisedFpi=yes&intmId=7",
            headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        soup = BeautifulSoup(r.text, "lxml")
        table = soup.find("table", {"class": "table"}) or soup.find("table")
        if table:
            filings = []
            for row in table.find_all("tr")[1:]:
                cols = row.find_all("td")
                if len(cols) >= 3:
                    link_tag = cols[-1].find("a")
                    filings.append({
                        "company": cols[0].get_text(strip=True),
                        "filing_date": cols[1].get_text(strip=True),
                        "type": "DRHP", "sector": "", "issue_size": "N/A",
                        "brlms": "N/A",
                        "pdf_link": link_tag["href"] if link_tag and "href" in link_tag.attrs else None,
                        "description": "",
                    })
            if filings:
                return filings, "SEBI", datetime.now(IST)
    except Exception:
        pass
    return [], "unavailable", datetime.now(IST)


# ── Render ─────────────────────────────────────────────────────────────────────
def render():
    st_autorefresh(interval=1_800_000, key="drhp_refresh")

    st.markdown("## 📋 DRHP / RHP Filings Monitor — New Age Tech & Fintech")
    st.markdown(
        "<p style='color:#6b7a8d;font-size:14px'>Tracks DRHP and RHP filings from BSE/SEBI for new-age tech and fintech companies.</p>",
        unsafe_allow_html=True,
    )

    col_h, col_b = st.columns([6, 1])
    with col_b:
        if st.button("🔄 Refresh", key="drhp_ref"):
            st.cache_data.clear()
            st.rerun()

    with st.spinner("Fetching BSE filings…"):
        bse_data, bse_src, _ = _bse_filings()
    with st.spinner("Fetching SEBI filings…"):
        sebi_data, sebi_src, _ = _sebi_filings()

    live = []
    if isinstance(bse_data, list) and bse_data:
        live.extend(bse_data)
    if isinstance(sebi_data, list) and sebi_data:
        live.extend(sebi_data)

    known_cos = {f["company"].lower() for f in KNOWN_FILINGS}
    unique_live = [f for f in live if isinstance(f, dict) and f.get("company", "").lower() not in known_cos]
    combined = unique_live + KNOWN_FILINGS or KNOWN_FILINGS

    # New filings alert
    new_filings = [f for f in combined if _is_new(f.get("filing_date", ""), days=7)]
    if new_filings:
        st.markdown(
            f"""<div style='background:#fef9c3;border:2px solid #fbbf24;border-radius:10px;
            padding:14px 18px;margin-bottom:16px'>
            <b style='color:#92400e'>🆕 {len(new_filings)} new filing(s) in the last 7 days:</b>
            &nbsp; {', '.join(f['company'] for f in new_filings)}</div>""",
            unsafe_allow_html=True,
        )

    # ── Inline filters ────────────────────────────────────────────────────────
    st.markdown(
        f"""<div style='background:{CARD_BG};border:1px solid {BORDER};border-radius:10px;
        padding:12px 16px;margin:12px 0'>""", unsafe_allow_html=True)
    fc1, fc2, fc3 = st.columns([2, 2, 2])
    with fc1:
        types = ["All"] + sorted(set(f.get("type", "DRHP") for f in combined))
        sel_type = st.selectbox("Filing Type", types, key="drhp_type")
    with fc2:
        secs = sorted(set(f.get("sector", "") for f in combined if f.get("sector")))
        sel_sec = st.selectbox("Sector", ["All"] + secs, key="drhp_sec")
    with fc3:
        z47_only = st.checkbox("Z47-relevant only", value=False, key="drhp_z47")
    st.markdown("</div>", unsafe_allow_html=True)

    # Build rows
    rows = []
    for f in combined:
        z47r = _is_z47(f.get("company", ""), f.get("sector", ""))
        new_f = _is_new(f.get("filing_date", ""), days=7)
        rows.append({
            "Company":      f.get("company", ""),
            "Filing Date":  f.get("filing_date", ""),
            "Type":         f.get("type", "DRHP"),
            "Sector":       (f.get("sector") or "–").title(),
            "Issue Size":   f.get("issue_size", "TBD"),
            "BRLMs":        f.get("brlms", "TBD"),
            "Z47 Relevant": "✅ Yes" if z47r else "–",
            "PDF":          f.get("pdf_link") or "–",
            "New (7d)":     "🆕 New" if new_f else "",
            "_z47": z47r, "_new": new_f,
            "_sec_raw": (f.get("sector") or "").lower(),
            "_type_raw": f.get("type", "DRHP"),
            "_desc": f.get("description", ""),
        })

    df = pd.DataFrame(rows)
    if sel_type != "All":
        df = df[df["_type_raw"] == sel_type]
    if sel_sec != "All":
        df = df[df["_sec_raw"] == sel_sec.lower()]
    if z47_only:
        df = df[df["_z47"]]

    disp_cols = ["Company", "Filing Date", "Type", "Sector", "Issue Size", "BRLMs", "Z47 Relevant", "PDF", "New (7d)"]

    def _hl(row):
        return (["background-color:#fef9c3"] * len(row)
                if row.get("New (7d)") == "🆕 New" else [""] * len(row))

    styled = df[disp_cols].style.apply(_hl, axis=1)
    st.dataframe(styled, use_container_width=True, hide_index=True, height=500,
                 column_config={
                     "Company":    st.column_config.TextColumn(width="medium"),
                     "Issue Size": st.column_config.TextColumn(width="small"),
                     "BRLMs":      st.column_config.TextColumn(width="medium"),
                     "PDF":        st.column_config.LinkColumn("PDF / Link", display_text="View"),
                     "New (7d)":   st.column_config.TextColumn(width="small"),
                 })
    st.markdown(f'<div style="color:#a38060;font-size:11px;text-align:right">Updated: {_now_ist()}</div>',
                unsafe_allow_html=True)

    # Detail expander
    st.markdown("---")
    st.markdown("### Filing Details")
    sel_co = st.selectbox("Select company", [r["Company"] for r in rows], key="drhp_detail")
    sel_row = next((r for r in rows if r["Company"] == sel_co), None)
    if sel_row:
        with st.expander(f"📄 {sel_row['Company']} — {sel_row['Type']}", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**Company:** {sel_row['Company']}")
                st.markdown(f"**Filing Date:** {sel_row['Filing Date']}")
                st.markdown(f"**Filing Type:** {sel_row['Type']}")
                st.markdown(f"**Sector:** {sel_row['Sector']}")
            with c2:
                st.markdown(f"**Issue Size:** {sel_row['Issue Size']}")
                st.markdown(f"**BRLMs:** {sel_row['BRLMs']}")
                st.markdown(f"**Z47 Relevant:** {sel_row['Z47 Relevant']}")
                if sel_row["PDF"] and sel_row["PDF"] != "–":
                    st.markdown(f"**PDF:** [{sel_row['PDF']}]({sel_row['PDF']})")
            if sel_row.get("_desc"):
                st.markdown(f"**About:** {sel_row['_desc']}")

    # Stats
    st.markdown("---")
    st.markdown("### Summary Statistics")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Filings", len(rows))
    m2.metric("New (7 days)",  sum(1 for r in rows if r["_new"]))
    m3.metric("Z47 Relevant",  sum(1 for r in rows if r["_z47"]))
    m4.metric("DRHP vs RHP",
              f"{sum(1 for r in rows if r['_type_raw']=='DRHP')}D "
              f"/ {sum(1 for r in rows if r['_type_raw']=='RHP')}R")
    st.markdown(
        f'<div style="color:#a38060;font-size:11px;text-align:right">'
        f'Sources: BSE ({bse_src}), SEBI ({sebi_src}), Hardcoded | Updated: {_now_ist()}</div>',
        unsafe_allow_html=True)
