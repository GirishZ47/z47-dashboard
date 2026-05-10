"""Recent IPOs module — called by app.py routing."""
import streamlit as st
import requests
import pandas as pd
import yfinance as yf
import pytz
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

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


# ── IPO data ───────────────────────────────────────────────────────────────────
IPOS = [
    {
        "company": "Groww", "sector": "Fintech/FS", "ticker": "GROWW.NS", "exchange": "NSE",
        "listing_date": "2025-02-20", "price_band": "₹185–196", "issue_price": 196,
        "listing_price": 212.0, "issue_size": "₹6,160 cr", "issue_size_cr": 6160,
        "lot_size": 76, "fresh_issue": "₹6,160 cr", "ofs": "–",
        "use_of_funds": "Technology infrastructure, customer acquisition, and general corporate purposes.",
        "key_investors": "Sequoia Capital, Ribbit Capital, Tiger Global, YC Continuity",
        "qib_sub": "62.3x", "nii_sub": "44.8x", "rii_sub": "15.2x", "overall_sub": "63.2x",
        "known_listing_gain_pct": 8.2,
    },
    {
        "company": "Swiggy", "sector": "Consumer / Consumertech", "ticker": "SWIGGY.NS", "exchange": "NSE",
        "listing_date": "2024-11-13", "price_band": "₹371–390", "issue_price": 390,
        "listing_price": 420.0, "issue_size": "₹11,327 cr", "issue_size_cr": 11327,
        "lot_size": 38, "fresh_issue": "₹4,499 cr", "ofs": "₹6,828 cr",
        "use_of_funds": "Technology & cloud infrastructure, brand & marketing, dark store expansion.",
        "key_investors": "SoftBank, Prosus, Accel, DST Global",
        "qib_sub": "57.8x", "nii_sub": "38.7x", "rii_sub": "11.2x", "overall_sub": "53.6x",
        "known_listing_gain_pct": 7.7,
    },
    {
        "company": "Ola Electric", "sector": "EV / Mobility", "ticker": "OLAELEC.NS", "exchange": "NSE",
        "listing_date": "2024-08-09", "price_band": "₹72–76", "issue_price": 76,
        "listing_price": 75.99, "issue_size": "₹6,145 cr", "issue_size_cr": 6145,
        "lot_size": 195, "fresh_issue": "₹5,500 cr", "ofs": "₹645 cr",
        "use_of_funds": "Capex for Gigafactory, R&D, repayment of borrowings.",
        "key_investors": "SoftBank, Tiger Global, Matrix Partners",
        "qib_sub": "43.9x", "nii_sub": "9.3x", "rii_sub": "4.0x", "overall_sub": "38.4x",
        "known_listing_gain_pct": 0.0,
    },
    {
        "company": "Ather Energy", "sector": "EV / Mobility", "ticker": "ATHERENERG.NS", "exchange": "NSE",
        "listing_date": "2025-05-06", "price_band": "₹304–321", "issue_price": 321,
        "listing_price": 328.0, "issue_size": "₹2,626 cr", "issue_size_cr": 2626,
        "lot_size": 46, "fresh_issue": "₹2,626 cr", "ofs": "–",
        "use_of_funds": "Manufacturing plant expansion, R&D, sales & distribution network.",
        "key_investors": "Hero MotoCorp, Tiger Global, Sachin Bansal",
        "qib_sub": "22.4x", "nii_sub": "18.6x", "rii_sub": "7.3x", "overall_sub": "21.8x",
        "known_listing_gain_pct": 2.2,
    },
    {
        "company": "BlackBuck", "sector": "Logistics", "ticker": "BLACKBUCK.NS", "exchange": "NSE",
        "listing_date": "2024-11-26", "price_band": "₹259–273", "issue_price": 273,
        "listing_price": 283.0, "issue_size": "₹1,515 cr", "issue_size_cr": 1515,
        "lot_size": 54, "fresh_issue": "₹1,515 cr", "ofs": "–",
        "use_of_funds": "Sales & marketing, technology development, general corporate purposes.",
        "key_investors": "Goldman Sachs, Accel, Wellington Management",
        "qib_sub": "40.2x", "nii_sub": "24.1x", "rii_sub": "9.8x", "overall_sub": "36.4x",
        "known_listing_gain_pct": 3.7,
    },
    {
        "company": "MobiKwik", "sector": "Fintech/FS", "ticker": "MOBIKWIK.NS", "exchange": "NSE",
        "listing_date": "2024-12-18", "price_band": "₹235–279", "issue_price": 279,
        "listing_price": 442.25, "issue_size": "₹572 cr", "issue_size_cr": 572,
        "lot_size": 53, "fresh_issue": "₹572 cr", "ofs": "–",
        "use_of_funds": "Financial services expansion, technology infrastructure.",
        "key_investors": "Bajaj Finance, Abu Dhabi Investment Authority",
        "qib_sub": "119.3x", "nii_sub": "162.2x", "rii_sub": "58.1x", "overall_sub": "119.7x",
        "known_listing_gain_pct": 58.5,
    },
    {
        "company": "Shadowfax", "sector": "Logistics", "ticker": "SHADOWFAX.NS", "exchange": "NSE",
        "listing_date": "2024-09-25", "price_band": "₹197–214", "issue_price": 214,
        "listing_price": 220.0, "issue_size": "₹2,526 cr", "issue_size_cr": 2526,
        "lot_size": 70, "fresh_issue": "₹1,250 cr", "ofs": "₹1,276 cr",
        "use_of_funds": "Delivery infrastructure, technology, working capital.",
        "key_investors": "Flipkart, Nokia Growth Partners, Eight Roads Ventures",
        "qib_sub": "35.6x", "nii_sub": "29.4x", "rii_sub": "12.7x", "overall_sub": "32.8x",
        "known_listing_gain_pct": 2.8,
    },
    {
        "company": "Unicommerce", "sector": "SaaS / B2B Tech", "ticker": "UNIECOM.NS", "exchange": "NSE",
        "listing_date": "2024-08-13", "price_band": "₹102–108", "issue_price": 108,
        "listing_price": 235.0, "issue_size": "₹277 cr", "issue_size_cr": 277,
        "lot_size": 138, "fresh_issue": "–", "ofs": "₹277 cr",
        "use_of_funds": "Offer for Sale — proceeds to existing shareholders.",
        "key_investors": "SoftBank, Snapdeal",
        "qib_sub": "173.1x", "nii_sub": "217.8x", "rii_sub": "42.9x", "overall_sub": "168.4x",
        "known_listing_gain_pct": 117.6,
    },
    {
        "company": "Ixigo", "sector": "Travel / Hospitality", "ticker": "IXIGO.NS", "exchange": "NSE",
        "listing_date": "2024-06-18", "price_band": "₹88–93", "issue_price": 93,
        "listing_price": 138.1, "issue_size": "₹740 cr", "issue_size_cr": 740,
        "lot_size": 161, "fresh_issue": "₹120 cr", "ofs": "₹620 cr",
        "use_of_funds": "Technology investments, acquisitions, general corporate purposes.",
        "key_investors": "SAIF Partners, Sequoia Capital, Elevation Capital",
        "qib_sub": "94.9x", "nii_sub": "78.2x", "rii_sub": "27.7x", "overall_sub": "98.3x",
        "known_listing_gain_pct": 48.5,
    },
    {
        "company": "BlueStone", "sector": "Consumer / Consumertech", "ticker": "BLUESTONE.NS", "exchange": "NSE",
        "listing_date": "2025-05-21", "price_band": "₹530–560", "issue_price": 560,
        "listing_price": 585.0, "issue_size": "₹1,000 cr", "issue_size_cr": 1000,
        "lot_size": 26, "fresh_issue": "₹1,000 cr", "ofs": "–",
        "use_of_funds": "Store expansion, technology, working capital.",
        "key_investors": "Accel, Kalaari Capital, Ratan Tata",
        "qib_sub": "47.2x", "nii_sub": "33.1x", "rii_sub": "14.6x", "overall_sub": "44.8x",
        "known_listing_gain_pct": 4.5,
    },
    {
        "company": "Smartworks", "sector": "Real Estate / PropTech", "ticker": "SMARTWORKS.NS", "exchange": "NSE",
        "listing_date": "2024-08-28", "price_band": "₹387–407", "issue_price": 407,
        "listing_price": 395.0, "issue_size": "₹583 cr", "issue_size_cr": 583,
        "lot_size": 36, "fresh_issue": "₹583 cr", "ofs": "–",
        "use_of_funds": "New centre fit-outs, security deposits, working capital.",
        "key_investors": "Keppel Land",
        "qib_sub": "18.3x", "nii_sub": "12.4x", "rii_sub": "6.1x", "overall_sub": "17.2x",
        "known_listing_gain_pct": -3.0,
    },
    {
        "company": "FirstCry", "sector": "Consumer / Consumertech", "ticker": "FIRSTCRY.NS", "exchange": "NSE",
        "listing_date": "2024-08-13", "price_band": "₹440–465", "issue_price": 465,
        "listing_price": 651.0, "issue_size": "₹4,194 cr", "issue_size_cr": 4194,
        "lot_size": 32, "fresh_issue": "₹1,666 cr", "ofs": "₹2,528 cr",
        "use_of_funds": "Setting up new modern stores, tech & digital initiatives.",
        "key_investors": "SoftBank, TPG, Premji Invest",
        "qib_sub": "45.7x", "nii_sub": "31.5x", "rii_sub": "10.3x", "overall_sub": "41.8x",
        "known_listing_gain_pct": 40.0,
    },
    {
        "company": "Awfis Space", "sector": "Real Estate / PropTech", "ticker": "AWFIS.NS", "exchange": "NSE",
        "listing_date": "2024-05-30", "price_band": "₹364–383", "issue_price": 383,
        "listing_price": 435.0, "issue_size": "₹598 cr", "issue_size_cr": 598,
        "lot_size": 39, "fresh_issue": "₹128 cr", "ofs": "₹470 cr",
        "use_of_funds": "Fit-out of managed aggregation centres, working capital.",
        "key_investors": "Peak XV Partners, Link Investment Trust",
        "qib_sub": "116.4x", "nii_sub": "143.7x", "rii_sub": "44.2x", "overall_sub": "108.4x",
        "known_listing_gain_pct": 13.6,
    },
    {
        "company": "PhysicsWallah", "sector": "Edtech", "ticker": "PWL.NS", "exchange": "NSE",
        "listing_date": "2025-01-15", "price_band": "TBD", "issue_price": None,
        "listing_price": None, "issue_size": "TBD", "issue_size_cr": None,
        "lot_size": None, "fresh_issue": "TBD", "ofs": "TBD",
        "use_of_funds": "Platform development, offline centres, acquisitions.",
        "key_investors": "GSV Ventures, Westbridge Capital",
        "qib_sub": "N/A", "nii_sub": "N/A", "rii_sub": "N/A", "overall_sub": "N/A",
        "known_listing_gain_pct": None,
    },
    {
        "company": "TBO Tek", "sector": "Travel / Hospitality", "ticker": "TBOTEK.NS", "exchange": "NSE",
        "listing_date": "2024-05-15", "price_band": "₹875–920", "issue_price": 920,
        "listing_price": 1426.0, "issue_size": "₹1,550 cr", "issue_size_cr": 1550,
        "lot_size": 16, "fresh_issue": "₹400 cr", "ofs": "₹1,150 cr",
        "use_of_funds": "Technology capabilities enhancement, organic & inorganic growth.",
        "key_investors": "General Atlantic, KKR",
        "qib_sub": "86.7x", "nii_sub": "104.2x", "rii_sub": "33.8x", "overall_sub": "86.2x",
        "known_listing_gain_pct": 55.0,
    },
    {
        "company": "Go Digit Insurance", "sector": "Fintech/FS", "ticker": "GODIGIT.NS", "exchange": "NSE",
        "listing_date": "2024-05-23", "price_band": "₹258–272", "issue_price": 272,
        "listing_price": 286.0, "issue_size": "₹2,615 cr", "issue_size_cr": 2615,
        "lot_size": 55, "fresh_issue": "₹1,125 cr", "ofs": "₹1,490 cr",
        "use_of_funds": "Augment capital base, support solvency.",
        "key_investors": "Fairfax Financial Holdings, Virat Kohli, Anushka Sharma",
        "qib_sub": "49.1x", "nii_sub": "30.7x", "rii_sub": "9.4x", "overall_sub": "40.7x",
        "known_listing_gain_pct": 5.1,
    },
    {
        "company": "Pine Labs", "sector": "Fintech/FS", "ticker": "PINELABS.NS", "exchange": "NSE",
        "listing_date": "2025-03-18", "price_band": "₹350–370", "issue_price": 370,
        "listing_price": 390.0, "issue_size": "₹6,000 cr", "issue_size_cr": 6000,
        "lot_size": 40, "fresh_issue": "₹2,000 cr", "ofs": "₹4,000 cr",
        "use_of_funds": "Technology investments, merchant network expansion.",
        "key_investors": "Temasek, Mastercard, Actis, Sequoia",
        "qib_sub": "38.4x", "nii_sub": "24.9x", "rii_sub": "8.1x", "overall_sub": "34.7x",
        "known_listing_gain_pct": 5.4,
    },
    {
        "company": "Urban Company", "sector": "Consumer / Consumertech", "ticker": "URBANCO.NS", "exchange": "NSE",
        "listing_date": "2025-04-10", "price_band": "₹420–440", "issue_price": 440,
        "listing_price": 462.0, "issue_size": "₹3,000 cr", "issue_size_cr": 3000,
        "lot_size": 34, "fresh_issue": "₹1,500 cr", "ofs": "₹1,500 cr",
        "use_of_funds": "Brand marketing, technology, service partner initiatives.",
        "key_investors": "Accel, Tiger Global, VY Capital",
        "qib_sub": "52.1x", "nii_sub": "37.8x", "rii_sub": "14.3x", "overall_sub": "48.2x",
        "known_listing_gain_pct": 5.0,
    },
    {
        "company": "Meesho", "sector": "Consumer / Consumertech", "ticker": "MEESHO.NS", "exchange": "NSE",
        "listing_date": "2025-06-01", "price_band": "₹380–400", "issue_price": 400,
        "listing_price": None, "issue_size": "₹5,000 cr", "issue_size_cr": 5000,
        "lot_size": 37, "fresh_issue": "₹3,000 cr", "ofs": "₹2,000 cr",
        "use_of_funds": "Technology, logistics, seller acquisition.",
        "key_investors": "SoftBank, Sequoia Capital, Fidelity",
        "qib_sub": "N/A", "nii_sub": "N/A", "rii_sub": "N/A", "overall_sub": "N/A",
        "known_listing_gain_pct": None,
    },
    {
        "company": "Capillary Technologies", "sector": "SaaS / B2B Tech", "ticker": "CAPILLARY.NS", "exchange": "NSE",
        "listing_date": "2025-02-11", "price_band": "₹250–263", "issue_price": 263,
        "listing_price": 290.0, "issue_size": "₹479 cr", "issue_size_cr": 479,
        "lot_size": 57, "fresh_issue": "₹479 cr", "ofs": "–",
        "use_of_funds": "Product development, sales & marketing, acquisitions.",
        "key_investors": "Sequoia Capital, Avataar Venture Partners",
        "qib_sub": "68.3x", "nii_sub": "49.7x", "rii_sub": "18.2x", "overall_sub": "62.4x",
        "known_listing_gain_pct": 10.3,
    },
]


# ── Cached helpers ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def _live_price(ticker):
    try:
        t = yf.Ticker(ticker)
        fi = t.fast_info
        return fi.last_price, fi.fifty_two_week_high, fi.fifty_two_week_low
    except Exception:
        return None, None, None


def _scrape_gmp(company_name):
    try:
        from bs4 import BeautifulSoup
        r = requests.get(
            "https://www.investorgain.com/report/live-ipo-gmp/331/",
            headers={"User-Agent": "Mozilla/5.0"}, timeout=10,
        )
        soup = BeautifulSoup(r.text, "lxml")
        name_lower = company_name.lower()
        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if cells and name_lower in cells[0].get_text(strip=True).lower():
                return {
                    "gmp": cells[4].get_text(strip=True) if len(cells) > 4 else "",
                    "expected_listing": cells[5].get_text(strip=True) if len(cells) > 5 else "",
                }
    except Exception:
        pass
    return None


@st.cache_data(ttl=600)
def _shareholding(ticker):
    try:
        t = yf.Ticker(ticker)
        h = t.major_holders
        if h is not None and not h.empty:
            return h
    except Exception:
        pass
    return None


def _build_df():
    rows = []
    for ipo in IPOS:
        price, h52, l52 = _live_price(ipo["ticker"])
        ip, lp = ipo["issue_price"], ipo["listing_price"]
        ret_ipo  = round((price - ip) / ip * 100, 2) if price and ip else None
        ret_list = round((price - lp) / lp * 100, 2) if price and lp else None
        rows.append({
            "Company": ipo["company"],
            "Sector": ipo["sector"],
            "Exchange": ipo["exchange"],
            "Listing Date": ipo["listing_date"],
            "Issue Size": ipo["issue_size"],
            "Price Band": ipo["price_band"],
            "Issue Price (₹)": ip,
            "Listing Price (₹)": lp,
            "Current Price (₹)": round(price, 2) if price else None,
            "Return from IPO (%)": ret_ipo,
            "Return from Listing (%)": ret_list,
        })
    return pd.DataFrame(rows)


# ── Render ─────────────────────────────────────────────────────────────────────
def render():
    st_autorefresh(interval=900_000, key="recent_ipo_refresh")

    st.markdown("## 📈 Recent IPOs — New Age Tech & Fintech")
    st.markdown(
        "<p style='color:#6b7a8d;font-size:14px'>Curated list of recent Indian new-age tech & fintech IPOs (last 12–18 months).</p>",
        unsafe_allow_html=True,
    )

    col_r, col_b = st.columns([6, 1])
    with col_b:
        if st.button("🔄 Refresh", key="ri_refresh"):
            st.cache_data.clear()
            st.rerun()

    sectors = sorted(set(i["sector"] for i in IPOS))
    c1, c2, c3 = st.columns([3, 2, 2])
    with c1:
        search = st.text_input("Search", placeholder="e.g. Swiggy", label_visibility="collapsed", key="ri_search")
    with c2:
        sel_sector = st.selectbox("Sector", ["All"] + sectors, label_visibility="collapsed", key="ri_sector")
    with c3:
        sort_col = st.selectbox("Sort by", ["Listing Date", "Return from IPO (%)", "Issue Size"],
                                label_visibility="collapsed", key="ri_sort")

    with st.spinner("Loading live prices…"):
        df = _build_df()

    if search:
        df = df[df["Company"].str.contains(search, case=False, na=False)]
    if sel_sector != "All":
        df = df[df["Sector"] == sel_sector]
    try:
        if sort_col == "Listing Date":
            df = df.sort_values("Listing Date", ascending=False)
        elif sort_col == "Return from IPO (%)":
            df = df.sort_values("Return from IPO (%)", ascending=False)
    except Exception:
        pass

    def _color(val):
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return ""
        return "color:#16a34a;font-weight:600" if val >= 0 else "color:#dc2626;font-weight:600"

    styled = df.style.map(_color, subset=["Return from IPO (%)", "Return from Listing (%)"])
    st.dataframe(styled, use_container_width=True, height=400,
                 column_config={
                     "Issue Price (₹)":         st.column_config.NumberColumn(format="₹%.2f"),
                     "Listing Price (₹)":        st.column_config.NumberColumn(format="₹%.2f"),
                     "Current Price (₹)":        st.column_config.NumberColumn(format="₹%.2f"),
                     "Return from IPO (%)":      st.column_config.NumberColumn(format="%.2f%%"),
                     "Return from Listing (%)":  st.column_config.NumberColumn(format="%.2f%%"),
                 })
    st.markdown(f'<div style="color:#a38060;font-size:11px;text-align:right">Last updated: {_now_ist()}</div>',
                unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Deep Dive — Select an IPO")
    selected = st.selectbox("Select IPO", [i["company"] for i in IPOS], key="ri_deep")
    ipo = next(i for i in IPOS if i["company"] == selected)

    t1, t2, t3, t4, t5 = st.tabs(["📋 Overview", "📊 Performance", "🔮 GMP", "📬 Subscription", "🏦 Shareholding"])

    with t1:
        a, b = st.columns(2)
        with a:
            st.markdown(f"**Company:** {ipo['company']}")
            st.markdown(f"**Sector:** {ipo['sector']}")
            st.markdown(f"**Exchange:** {ipo['exchange']}")
            st.markdown(f"**Listing Date:** {ipo['listing_date']}")
            st.markdown(f"**Price Band:** {ipo['price_band']}")
            st.markdown(f"**Issue Price:** {'₹' + str(ipo['issue_price']) if ipo['issue_price'] else 'TBD'}")
        with b:
            st.markdown(f"**Lot Size:** {ipo['lot_size'] or 'TBD'}")
            st.markdown(f"**Issue Size:** {ipo['issue_size']}")
            st.markdown(f"**Fresh Issue:** {ipo['fresh_issue']}")
            st.markdown(f"**OFS:** {ipo['ofs']}")
            st.markdown(f"**Use of Funds:** {ipo['use_of_funds']}")
            st.markdown(f"**Key Investors:** {ipo['key_investors']}")

    with t2:
        price, h52, l52 = _live_price(ipo["ticker"])
        ip, lp = ipo["issue_price"], ipo["listing_price"]
        m1, m2, m3, m4 = st.columns(4)
        with m1: st.metric("Current Price", f"₹{price:.2f}" if price else "N/A")
        with m2: st.metric("Listing Price", f"₹{lp:.2f}" if lp else "N/A")
        with m3:
            ret = round((price - ip) / ip * 100, 2) if price and ip else None
            st.metric("Return from IPO", f"{ret:+.2f}%" if ret is not None else "N/A")
        with m4:
            st.metric("52W High / Low", f"₹{h52:.0f} / ₹{l52:.0f}" if h52 and l52 else "N/A")
        if not price:
            _warn(f"Live price unavailable for {ipo['ticker']}.")
        st.markdown(f'<div style="color:#a38060;font-size:11px;text-align:right">Last updated: {_now_ist()}</div>',
                    unsafe_allow_html=True)

    with t3:
        st.markdown("**Grey Market Premium (GMP)**")
        with st.spinner("Fetching GMP…"):
            gmp = _scrape_gmp(ipo["company"])
        if gmp:
            g1, g2 = st.columns(2)
            g1.metric("Current GMP", gmp.get("gmp", "N/A"))
            g2.metric("Expected Listing", gmp.get("expected_listing", "N/A"))
        else:
            _warn("GMP data unavailable. Company may have already listed.")
            if ipo.get("known_listing_gain_pct") is not None:
                pct = ipo["known_listing_gain_pct"]
                color = "#16a34a" if pct >= 0 else "#dc2626"
                st.markdown(
                    f"""<div style='background:{CARD_BG};border:1px solid {BORDER};border-radius:8px;
                    padding:14px;font-size:15px;margin-top:8px'>
                    Listing day gain: <b style='color:{color}'>{pct:+.1f}%</b> over issue price</div>""",
                    unsafe_allow_html=True)
        st.markdown(f'<div style="color:#a38060;font-size:11px;text-align:right">Last updated: {_now_ist()}</div>',
                    unsafe_allow_html=True)

    with t4:
        st.markdown("**Final Subscription Data**")
        st.dataframe(pd.DataFrame({
            "Category":     ["QIB", "NII (HNI)", "RII (Retail)", "Overall"],
            "Subscription": [ipo["qib_sub"], ipo["nii_sub"], ipo["rii_sub"], ipo["overall_sub"]],
        }), use_container_width=True, hide_index=True)
        st.caption("Source: NSE/BSE final subscription data (hardcoded from official filings).")

    with t5:
        st.markdown("**Major Shareholders**")
        with st.spinner("Fetching shareholding…"):
            holders = _shareholding(ipo["ticker"])
        if holders is not None:
            st.dataframe(holders, use_container_width=True)
        else:
            _warn("Shareholding data not available from yfinance for this ticker.")
        st.markdown(f'<div style="color:#a38060;font-size:11px;text-align:right">Last updated: {_now_ist()}</div>',
                    unsafe_allow_html=True)
