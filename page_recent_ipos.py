"""Recent IPOs module — called by app.py routing."""
import streamlit as st
import requests
import pandas as pd
import yfinance as yf
import pytz
import plotly.graph_objects as go
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
from z47_assistant import render_z47_assistant
import time
import re
from ipo_investor_data import (
    get_investor_data,
    compute_returns,
    calculate_returns,
    get_ipo_comparison_data,
    VERIFIED_INVESTOR_DATA,
    extract_share_capital_history,
    match_investor_in_rhp,
    RHP_URLS,
)

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
        "company": "Groww", "sector": "Fintech / Financial Services", "ticker": "GROWW.NS", "exchange": "NSE",
        "listing_date": "2025-11-12", "price_band": "₹100", "issue_price": 100,
        "listing_price": 114.0, "issue_size": "₹6,632 cr", "issue_size_cr": 6632,
        "lot_size": 76, "fresh_issue": "₹1,060 cr", "ofs": "₹5,572.30 cr",
        "use_of_funds": "Technology infrastructure, customer acquisition, and general corporate purposes.",
        "key_investors": "Sequoia Capital, Ribbit Capital, Tiger Global, YC Continuity",
        "qib_sub": "62.3x", "nii_sub": "44.8x", "rii_sub": "15.2x", "overall_sub": "63.2x",
        "known_listing_gain_pct": 14.0,
    },
    {
        "company": "Swiggy", "sector": "Consumer / Consumer Tech", "ticker": "SWIGGY.NS", "exchange": "NSE",
        "listing_date": "2024-11-13", "price_band": "₹371–390", "issue_price": 390,
        "listing_price": 420.0, "issue_size": "₹11,327 cr", "issue_size_cr": 11327,
        "lot_size": 38, "fresh_issue": "₹4,499 cr", "ofs": "₹6,828 cr",
        "use_of_funds": "Technology & cloud infrastructure, brand & marketing, dark store expansion.",
        "key_investors": "SoftBank, Prosus, Accel, DST Global",
        "qib_sub": "57.8x", "nii_sub": "38.7x", "rii_sub": "11.2x", "overall_sub": "53.6x",
        "known_listing_gain_pct": 7.7,
    },
    {
        "company": "Ola Electric", "sector": "Consumer / Consumer Tech", "ticker": "OLAELEC.NS", "exchange": "NSE",
        "listing_date": "2024-08-09", "price_band": "₹72–76", "issue_price": 76,
        "listing_price": 75.99, "issue_size": "₹6,145 cr", "issue_size_cr": 6145,
        "lot_size": 195, "fresh_issue": "₹5,500 cr", "ofs": "₹645 cr",
        "use_of_funds": "Capex for Gigafactory, R&D, repayment of borrowings.",
        "key_investors": "SoftBank, Tiger Global, Matrix Partners",
        "qib_sub": "43.9x", "nii_sub": "9.3x", "rii_sub": "4.0x", "overall_sub": "38.4x",
        "known_listing_gain_pct": 0.0,
    },
    {
        "company": "Ather Energy", "sector": "Consumer / Consumer Tech", "ticker": "ATHERENERG.NS", "exchange": "NSE",
        "listing_date": "2025-05-06", "price_band": "₹304–321", "issue_price": 321,
        "listing_price": 328.0, "issue_size": "₹2,626 cr", "issue_size_cr": 2626,
        "lot_size": 46, "fresh_issue": "₹2,626 cr", "ofs": "–",
        "use_of_funds": "Manufacturing plant expansion, R&D, sales & distribution network.",
        "key_investors": "Hero MotoCorp, Tiger Global, Sachin Bansal",
        "qib_sub": "22.4x", "nii_sub": "18.6x", "rii_sub": "7.3x", "overall_sub": "21.8x",
        "known_listing_gain_pct": 2.2,
    },
    {
        "company": "BlackBuck", "sector": "B2B", "ticker": "BLACKBUCK.NS", "exchange": "NSE",
        "listing_date": "2024-11-22", "price_band": "₹259–273", "issue_price": 273,
        "listing_price": 283.0, "issue_size": "₹1,515 cr", "issue_size_cr": 1515,
        "lot_size": 54, "fresh_issue": "₹1,000 cr", "ofs": "₹514.67 cr",
        "use_of_funds": "Sales & marketing, technology development, general corporate purposes.",
        "key_investors": "Goldman Sachs, Accel, Wellington Management",
        "qib_sub": "40.2x", "nii_sub": "24.1x", "rii_sub": "9.8x", "overall_sub": "36.4x",
        "known_listing_gain_pct": 3.7,
    },
    {
        "company": "MobiKwik", "sector": "Fintech / Financial Services", "ticker": "MOBIKWIK.NS", "exchange": "NSE",
        "listing_date": "2024-12-18", "price_band": "₹235–279", "issue_price": 279,
        "listing_price": 442.25, "issue_size": "₹572 cr", "issue_size_cr": 572,
        "lot_size": 53, "fresh_issue": "₹572 cr", "ofs": "–",
        "use_of_funds": "Financial services expansion, technology infrastructure.",
        "key_investors": "Bajaj Finance, Abu Dhabi Investment Authority",
        "qib_sub": "119.3x", "nii_sub": "162.2x", "rii_sub": "58.1x", "overall_sub": "119.7x",
        "known_listing_gain_pct": 58.5,
    },
    {
        "company": "Shadowfax", "sector": "B2B", "ticker": "SHADOWFAX.NS", "exchange": "NSE",
        "listing_date": "2026-01-28", "price_band": "₹118–124", "issue_price": 124,
        "listing_price": 112.60, "issue_size": "₹2,526 cr", "issue_size_cr": 2526,
        "lot_size": 70, "fresh_issue": "₹1,250 cr", "ofs": "₹1,276 cr",
        "use_of_funds": "Delivery infrastructure, technology, working capital.",
        "key_investors": "Flipkart, Nokia Growth Partners, Eight Roads Ventures",
        "qib_sub": "35.6x", "nii_sub": "29.4x", "rii_sub": "12.7x", "overall_sub": "32.8x",
        "known_listing_gain_pct": -9.2,
    },
    {
        "company": "Unicommerce", "sector": "SaaS / AI", "ticker": "UNIECOM.NS", "exchange": "NSE",
        "listing_date": "2024-08-13", "price_band": "₹102–108", "issue_price": 108,
        "listing_price": 235.0, "issue_size": "₹277 cr", "issue_size_cr": 277,
        "lot_size": 138, "fresh_issue": "–", "ofs": "₹277 cr",
        "use_of_funds": "Offer for Sale — proceeds to existing shareholders.",
        "key_investors": "SoftBank, Snapdeal",
        "qib_sub": "173.1x", "nii_sub": "217.8x", "rii_sub": "42.9x", "overall_sub": "168.4x",
        "known_listing_gain_pct": 117.6,
    },
    {
        "company": "Ixigo", "sector": "Consumer / Consumer Tech", "ticker": "IXIGO.NS", "exchange": "NSE",
        "listing_date": "2024-06-18", "price_band": "₹88–93", "issue_price": 93,
        "listing_price": 138.1, "issue_size": "₹740 cr", "issue_size_cr": 740,
        "lot_size": 161, "fresh_issue": "₹120 cr", "ofs": "₹620 cr",
        "use_of_funds": "Technology investments, acquisitions, general corporate purposes.",
        "key_investors": "SAIF Partners, Sequoia Capital, Elevation Capital",
        "qib_sub": "94.9x", "nii_sub": "78.2x", "rii_sub": "27.7x", "overall_sub": "98.3x",
        "known_listing_gain_pct": 48.5,
    },
    {
        "company": "BlueStone", "sector": "Consumer / Consumer Tech", "ticker": "BLUESTONE.NS", "exchange": "NSE",
        "listing_date": "2025-08-19", "price_band": "₹490–517", "issue_price": 517,
        "listing_price": 510.0, "issue_size": "₹1,175 cr", "issue_size_cr": 1175,
        "lot_size": 26, "fresh_issue": "₹1,000 cr", "ofs": "₹174.73 cr",
        "use_of_funds": "Store expansion, technology, working capital.",
        "key_investors": "Accel, Kalaari Capital, Ratan Tata",
        "qib_sub": "47.2x", "nii_sub": "33.1x", "rii_sub": "14.6x", "overall_sub": "44.8x",
        "known_listing_gain_pct": -1.4,
    },
    {
        "company": "Smartworks", "sector": "B2B", "ticker": "SMARTWORKS.NS", "exchange": "NSE",
        "listing_date": "2025-07-17", "price_band": "₹387–407", "issue_price": 407,
        "listing_price": 395.0, "issue_size": "₹583 cr", "issue_size_cr": 583,
        "lot_size": 36, "fresh_issue": "₹583 cr", "ofs": "–",
        "use_of_funds": "New centre fit-outs, security deposits, working capital.",
        "key_investors": "Keppel Land",
        "qib_sub": "18.3x", "nii_sub": "12.4x", "rii_sub": "6.1x", "overall_sub": "17.2x",
        "known_listing_gain_pct": -3.0,
    },
    {
        "company": "FirstCry", "sector": "Consumer / Consumer Tech", "ticker": "FIRSTCRY.NS", "exchange": "NSE",
        "listing_date": "2024-08-13", "price_band": "₹440–465", "issue_price": 465,
        "listing_price": 651.0, "issue_size": "₹4,194 cr", "issue_size_cr": 4194,
        "lot_size": 32, "fresh_issue": "₹1,666 cr", "ofs": "₹2,528 cr",
        "use_of_funds": "Setting up new modern stores, tech & digital initiatives.",
        "key_investors": "SoftBank, TPG, Premji Invest",
        "qib_sub": "45.7x", "nii_sub": "31.5x", "rii_sub": "10.3x", "overall_sub": "41.8x",
        "known_listing_gain_pct": 40.0,
    },
    {
        "company": "Awfis Space", "sector": "B2B", "ticker": "AWFIS.NS", "exchange": "NSE",
        "listing_date": "2024-05-30", "price_band": "₹364–383", "issue_price": 383,
        "listing_price": 435.0, "issue_size": "₹598 cr", "issue_size_cr": 598,
        "lot_size": 39, "fresh_issue": "₹128 cr", "ofs": "₹470 cr",
        "use_of_funds": "Fit-out of managed aggregation centres, working capital.",
        "key_investors": "Peak XV Partners, Link Investment Trust",
        "qib_sub": "116.4x", "nii_sub": "143.7x", "rii_sub": "44.2x", "overall_sub": "108.4x",
        "known_listing_gain_pct": 13.6,
    },
    {
        "company": "PhysicsWallah", "sector": "Consumer / Consumer Tech", "ticker": "PWL.NS", "exchange": "NSE",
        "listing_date": "2025-11-18", "price_band": "TBD", "issue_price": None,
        "listing_price": None, "issue_size": "TBD", "issue_size_cr": None,
        "lot_size": None, "fresh_issue": "TBD", "ofs": "TBD",
        "use_of_funds": "Platform development, offline centres, acquisitions.",
        "key_investors": "GSV Ventures, Westbridge Capital",
        "qib_sub": "N/A", "nii_sub": "N/A", "rii_sub": "N/A", "overall_sub": "N/A",
        "known_listing_gain_pct": None,
    },
    {
        "company": "TBO Tek", "sector": "B2B", "ticker": "TBOTEK.NS", "exchange": "NSE",
        "listing_date": "2024-05-15", "price_band": "₹875–920", "issue_price": 920,
        "listing_price": 1426.0, "issue_size": "₹1,550 cr", "issue_size_cr": 1550,
        "lot_size": 16, "fresh_issue": "₹400 cr", "ofs": "₹1,150 cr",
        "use_of_funds": "Technology capabilities enhancement, organic & inorganic growth.",
        "key_investors": "General Atlantic, KKR",
        "qib_sub": "86.7x", "nii_sub": "104.2x", "rii_sub": "33.8x", "overall_sub": "86.2x",
        "known_listing_gain_pct": 55.0,
    },
    {
        "company": "Go Digit Insurance", "sector": "Fintech / Financial Services", "ticker": "GODIGIT.NS", "exchange": "NSE",
        "listing_date": "2024-05-23", "price_band": "₹258–272", "issue_price": 272,
        "listing_price": 286.0, "issue_size": "₹2,615 cr", "issue_size_cr": 2615,
        "lot_size": 55, "fresh_issue": "₹1,125 cr", "ofs": "₹1,490 cr",
        "use_of_funds": "Augment capital base, support solvency.",
        "key_investors": "Fairfax Financial Holdings, Virat Kohli, Anushka Sharma",
        "qib_sub": "49.1x", "nii_sub": "30.7x", "rii_sub": "9.4x", "overall_sub": "40.7x",
        "known_listing_gain_pct": 5.1,
    },
    {
        "company": "Pine Labs", "sector": "Fintech / Financial Services", "ticker": "PINELABS.NS", "exchange": "NSE",
        "listing_date": "2025-11-14", "price_band": "₹201–221", "issue_price": 221,
        "listing_price": 242.0, "issue_size": "₹6,000 cr", "issue_size_cr": 6000,
        "lot_size": 40, "fresh_issue": "₹2,080 cr", "ofs": "₹3,920 cr",
        "use_of_funds": "Technology investments, merchant network expansion.",
        "key_investors": "Temasek, Mastercard, Actis, Sequoia",
        "qib_sub": "38.4x", "nii_sub": "24.9x", "rii_sub": "8.1x", "overall_sub": "34.7x",
        "known_listing_gain_pct": 9.5,
    },
    {
        "company": "Urban Company", "sector": "Consumer / Consumer Tech", "ticker": "URBANCO.NS", "exchange": "NSE",
        "listing_date": "2025-09-17", "price_band": "₹93–103", "issue_price": 103,
        "listing_price": 162.25, "issue_size": "₹3,000 cr", "issue_size_cr": 3000,
        "lot_size": 34, "fresh_issue": "₹1,500 cr", "ofs": "₹1,500 cr",
        "use_of_funds": "Brand marketing, technology, service partner initiatives.",
        "key_investors": "Accel, Tiger Global, VY Capital",
        "qib_sub": "52.1x", "nii_sub": "37.8x", "rii_sub": "14.3x", "overall_sub": "48.2x",
        "known_listing_gain_pct": 57.5,
    },
    {
        "company": "Meesho", "sector": "Consumer / Consumer Tech", "ticker": "MEESHO.NS", "exchange": "NSE",
        "listing_date": "2025-12-10", "price_band": "₹105–111", "issue_price": 111,
        "listing_price": 162.50, "issue_size": "₹3,152 cr", "issue_size_cr": 3152,
        "lot_size": 135, "fresh_issue": "₹2,000 cr", "ofs": "₹1,152 cr",
        "use_of_funds": "Technology infrastructure, seller acquisition, logistics, and general corporate purposes.",
        "key_investors": "SoftBank, Peak XV Partners, Elevation Capital, Fidelity, YC Continuity",
        "qib_sub": "N/A", "nii_sub": "N/A", "rii_sub": "N/A", "overall_sub": "79x",
        "known_listing_gain_pct": 46.4,
        # Live price data (updated 14 May 2026)
        "cmp": 189.92, "mcap_cr": 87125,
        "week_52_high": 254.40, "week_52_low": 125.56,
        "nse_symbol": "MEESHO", "bse_code": "381966",
        "allotment_date": "2025-12-08",
    },
    {
        "company": "Capillary Technologies", "sector": "SaaS / AI", "ticker": "CAPILLARY.NS", "exchange": "NSE",
        "listing_date": "2025-11-21", "price_band": "₹528–577", "issue_price": 577,
        "listing_price": 571.90, "issue_size": "₹479 cr", "issue_size_cr": 479,
        "lot_size": 57, "fresh_issue": "₹479 cr", "ofs": "–",
        "use_of_funds": "Product development, sales & marketing, acquisitions.",
        "key_investors": "Sequoia Capital, Avataar Venture Partners",
        "qib_sub": "68.3x", "nii_sub": "49.7x", "rii_sub": "18.2x", "overall_sub": "62.4x",
        "known_listing_gain_pct": -0.9,
    },
    {
        "company": "Kissht (OnEMI Technology)", "sector": "Fintech / Financial Services", "ticker": "KISSHT.NS", "exchange": "NSE",
        "listing_date": "2026-05-08", "price_band": "₹162–171", "issue_price": 171,
        "listing_price": 190.0, "issue_size": "₹926 cr", "issue_size_cr": 926,
        "lot_size": 87, "fresh_issue": "₹850 cr", "ofs": "₹76 cr",
        "use_of_funds": "Augmenting capital base of NBFC subsidiary Si Creva for lending; general corporate purposes.",
        "key_investors": "Temasek (Vertex), Ventureast, Sistema Asia Fund",
        "qib_sub": "25.97x", "nii_sub": "6.91x", "rii_sub": "2.13x", "overall_sub": "9.96x",
        "known_listing_gain_pct": 11.1,
    },
]


# ── Verified lock-in expiry dates ─────────────────────────────────────────────
# SEBI ICDR rules (verified empirically across 8+ IPOs with news cross-checks):
#   Anchor T1  = allotment_basis_date + 30 days
#   Anchor T2  = allotment_basis_date + 90 days
#   Pre-IPO 6M = LISTING date + 6 calendar months  ← NOT allotment date
#   Pre-IPO 1Y = LISTING date + 12 calendar months
#   Promoter   = LISTING date + 18M / 3Y
#
# Key empirical verifications:
#   Groww    listing Nov 12 → pripo May 12 (ET/MC/Upstox confirmed May 12 2026)
#   Ather    listing May  6 → pripo Nov  6 (Angel One: block deal + 11% fall Nov 6 2025)
#   MobiKwik listing Dec 18 → pripo Jun 18 (Outlook: fell 10% Jun 18 2025)
#   Urban Co listing Sep 17 → pripo Mar 17 (Goodreturns: fell 5.3% Mar 17 2026)
#   PW       listing Nov 18 → pripo May 18 (indiaipo.in: May 18 2026)
#   Meesho   listing Dec 10 → pripo Jun 10 (indiaipo.in: Jun 10 2026)
#
# Allotment corrections (3 IPOs had wrong date):
#   Ola Electric: old Aug 6 (IPO close date) → correct Aug 7 (allotment basis)
#   Shadowfax:    old Jan 26 (demat credit)  → correct Jan 23 (allotment basis)
#   Ixigo:        old Jun 14 (demat credit)  → correct Jun 13 (allotment basis)
LOCK_IN_DATES: dict[str, dict] = {
    "Groww": {
        # Allotment: 10 Nov 2025 (IPOWatch + BusinessToday confirmed)
        # Listing:   12 Nov 2025
        # Pre-IPO 6M = listing + 6M = 12 May 2026
        # NEWS CONFIRMED: ET "lock-in expired May 12, 2026"; Upstox "31 cr shares changed hands"
        "allotment": "2025-11-10",
        "anchor_t1": "2025-12-10",   # allotment + 30d
        "anchor_t2": "2026-02-08",   # allotment + 90d
        "pripo_6m":  "2026-05-12",   # listing Nov 12 + 6M  ← FIXED (was May 10)
        "pripo_1y":  "2026-11-12",   # listing Nov 12 + 12M ← FIXED (was Nov 10)
        "promoter_18m": "2027-05-12",# listing Nov 12 + 18M ← FIXED (was May 10)
        "promoter_3y":  "2028-11-12",# listing Nov 12 + 3Y  ← FIXED (was Nov 10)
    },
    "Swiggy": {
        # Allotment: 11 Nov 2024 (BusinessStandard confirmed)
        # Listing:   13 Nov 2024
        # Pre-IPO 6M = listing + 6M = 13 May 2025
        # (Outlook "May 12" = last day locked; first free trading day = May 13)
        "allotment": "2024-11-11",
        "anchor_t1": "2024-12-11",   # allotment + 30d
        "anchor_t2": "2025-02-09",   # allotment + 90d
        "pripo_6m":  "2025-05-13",   # listing Nov 13 + 6M  ← FIXED (was May 11)
        "pripo_1y":  "2025-11-13",   # listing Nov 13 + 12M ← FIXED (was Nov 11)
        "promoter_18m": "2026-05-13",# listing Nov 13 + 18M ← FIXED (was May 11)
        "promoter_3y":  "2027-11-13",# listing Nov 13 + 3Y  ← FIXED (was Nov 11)
    },
    "Ola Electric": {
        # Allotment: 7 Aug 2024 (IPOWatch confirmed; old code used Aug 6 = IPO close date — WRONG)
        # Listing:   9 Aug 2024
        # Pre-IPO 6M = listing + 6M = 9 Feb 2025
        # (Angel One: "available from Feb 10" = Feb 9 is Sunday → next business day Feb 10)
        "allotment": "2024-08-07",   # FIXED from 2024-08-06
        "anchor_t1": "2024-09-06",   # allotment + 30d ← FIXED (was Sep 5)
        "anchor_t2": "2024-11-05",   # allotment + 90d ← FIXED (was Nov 4)
        "pripo_6m":  "2025-02-09",   # listing Aug 9 + 6M   ← FIXED (was Feb 6)
        "pripo_1y":  "2025-08-09",   # listing Aug 9 + 12M  ← FIXED (was Aug 6)
        "promoter_18m": "2026-02-09",# listing Aug 9 + 18M  ← FIXED (was Feb 6)
        "promoter_3y":  "2027-08-09",# listing Aug 9 + 3Y   ← FIXED (was Aug 6)
    },
    "Ather Energy": {
        # Allotment: 2 May 2025 (BusinessStandard confirmed)
        # Listing:   6 May 2025
        # Pre-IPO 6M = listing + 6M = 6 Nov 2025
        # NEWS CONFIRMED: Angel One "fell 11%, Rs 856 cr block deal on Nov 6 2025"
        "allotment": "2025-05-02",
        "anchor_t1": "2025-06-01",   # allotment + 30d
        "anchor_t2": "2025-07-31",   # allotment + 90d
        "pripo_6m":  "2025-11-06",   # listing May 6 + 6M   ← FIXED (was Nov 2) NEWS CONFIRMED
        "pripo_1y":  "2026-05-06",   # listing May 6 + 12M  ← FIXED (was May 2)
        "promoter_18m": "2026-11-06",# listing May 6 + 18M  ← FIXED (was Nov 2)
        "promoter_3y":  "2028-05-06",# listing May 6 + 3Y   ← FIXED (was May 2)
    },
    "BlackBuck": {
        # Allotment: 19 Nov 2024 (IPOWatch confirmed)
        # Listing:   22 Nov 2024 (delayed: Maharashtra election holiday Nov 20)
        # Pre-IPO 6M = listing + 6M = 22 May 2025
        "allotment": "2024-11-19",
        "anchor_t1": "2024-12-19",   # allotment + 30d
        "anchor_t2": "2025-02-17",   # allotment + 90d
        "pripo_6m":  "2025-05-22",   # listing Nov 22 + 6M  ← FIXED (was May 19)
        "pripo_1y":  "2025-11-22",   # listing Nov 22 + 12M ← FIXED (was Nov 19)
        "promoter_18m": "2026-05-22",# listing Nov 22 + 18M ← FIXED (was May 19)
        "promoter_3y":  "2027-11-22",# listing Nov 22 + 3Y  ← FIXED (was Nov 19)
    },
    "MobiKwik": {
        # Allotment: 16 Dec 2024 (BusinessStandard confirmed)
        # Listing:   18 Dec 2024
        # Pre-IPO 6M = listing + 6M = 18 Jun 2025
        # NEWS CONFIRMED: Outlook + Angel One "fell 10% Jun 18 2025"
        "allotment": "2024-12-16",
        "anchor_t1": "2025-01-15",   # allotment + 30d
        "anchor_t2": "2025-03-16",   # allotment + 90d
        "pripo_6m":  "2025-06-18",   # listing Dec 18 + 6M  ← FIXED (was Jun 16) NEWS CONFIRMED
        "pripo_1y":  "2025-12-18",   # listing Dec 18 + 12M ← FIXED (was Dec 16)
        "promoter_18m": "2026-06-18",# listing Dec 18 + 18M ← FIXED (was Jun 16)
        "promoter_3y":  "2027-12-18",# listing Dec 18 + 3Y  ← FIXED (was Dec 16)
    },
    "Shadowfax": {
        # Allotment: 23 Jan 2026 (IPOWatch + IndMoney confirmed; old code used Jan 26 = demat credit — WRONG)
        # Listing:   28 Jan 2026
        # Pre-IPO 6M = listing + 6M = 28 Jul 2026
        "allotment": "2026-01-23",   # FIXED from 2026-01-26
        "anchor_t1": "2026-02-22",   # allotment + 30d ← FIXED (was Feb 25)
        "anchor_t2": "2026-04-23",   # allotment + 90d ← FIXED (was Apr 26)
        "pripo_6m":  "2026-07-28",   # listing Jan 28 + 6M  ← FIXED (was Jul 26)
        "pripo_1y":  "2027-01-28",   # listing Jan 28 + 12M ← FIXED (was Jan 26)
        "promoter_18m": "2027-07-28",# listing Jan 28 + 18M ← FIXED (was Jul 26)
        "promoter_3y":  "2029-01-28",# listing Jan 28 + 3Y  ← FIXED (was Jan 26)
    },
    "Unicommerce": {
        # Allotment: 9 Aug 2024 (Chittorgarh + IPOWatch confirmed)
        # Listing:   13 Aug 2024
        # Pre-IPO 6M = listing + 6M = 13 Feb 2025
        "allotment": "2024-08-09",
        "anchor_t1": "2024-09-08",   # allotment + 30d
        "anchor_t2": "2024-11-07",   # allotment + 90d
        "pripo_6m":  "2025-02-13",   # listing Aug 13 + 6M  ← FIXED (was Feb 9)
        "pripo_1y":  "2025-08-13",   # listing Aug 13 + 12M ← FIXED (was Aug 9)
        "promoter_18m": "2026-02-13",# listing Aug 13 + 18M ← FIXED (was Feb 9)
        "promoter_3y":  "2027-08-13",# listing Aug 13 + 3Y  ← FIXED (was Aug 9)
    },
    "Ixigo": {
        # Allotment: 13 Jun 2024 (BusinessStandard "allotment today" Jun 13 confirmed;
        #            old code used Jun 14 = demat credit date — WRONG)
        # Listing:   18 Jun 2024
        # Pre-IPO 6M = listing + 6M = 18 Dec 2024
        "allotment": "2024-06-13",   # FIXED from 2024-06-14
        "anchor_t1": "2024-07-13",   # allotment + 30d ← FIXED (was Jul 14)
        "anchor_t2": "2024-09-11",   # allotment + 90d ← FIXED (was Sep 12)
        "pripo_6m":  "2024-12-18",   # listing Jun 18 + 6M  ← FIXED (was Dec 14)
        "pripo_1y":  "2025-06-18",   # listing Jun 18 + 12M ← FIXED (was Jun 14)
        "promoter_18m": "2025-12-18",# listing Jun 18 + 18M ← FIXED (was Dec 14)
        "promoter_3y":  "2027-06-18",# listing Jun 18 + 3Y  ← FIXED (was Jun 14)
    },
    "BlueStone": {
        # Allotment: 14 Aug 2025 (Chittorgarh confirmed; Aug 15 = Independence Day → listing Aug 19)
        # Listing:   19 Aug 2025
        # Pre-IPO 6M = listing + 6M = 19 Feb 2026
        "allotment": "2025-08-14",
        "anchor_t1": "2025-09-13",   # allotment + 30d
        "anchor_t2": "2025-11-12",   # allotment + 90d
        "pripo_6m":  "2026-02-19",   # listing Aug 19 + 6M  ← FIXED (was Feb 14)
        "pripo_1y":  "2026-08-19",   # listing Aug 19 + 12M ← FIXED (was Aug 14)
        "promoter_18m": "2027-02-19",# listing Aug 19 + 18M ← FIXED (was Feb 14)
        "promoter_3y":  "2028-08-19",# listing Aug 19 + 3Y  ← FIXED (was Aug 14)
    },
    "Smartworks": {
        # Allotment: 15 Jul 2025 (IPOWatch confirmed)
        # Listing:   17 Jul 2025
        # Pre-IPO 6M = listing + 6M = 17 Jan 2026
        "allotment": "2025-07-15",
        "anchor_t1": "2025-08-14",   # allotment + 30d
        "anchor_t2": "2025-10-13",   # allotment + 90d
        "pripo_6m":  "2026-01-17",   # listing Jul 17 + 6M  ← FIXED (was Jan 15)
        "pripo_1y":  "2026-07-17",   # listing Jul 17 + 12M ← FIXED (was Jul 15)
        "promoter_18m": "2027-01-17",# listing Jul 17 + 18M ← FIXED (was Jan 15)
        "promoter_3y":  "2028-07-17",# listing Jul 17 + 3Y  ← FIXED (was Jul 15)
    },
    "FirstCry": {
        # Allotment: 9 Aug 2024 (IPOWatch + BusinessToday confirmed)
        # Listing:   13 Aug 2024
        # Pre-IPO 6M = listing + 6M = 13 Feb 2025
        # (BusinessStandard: "lock-in ends Nov 2024" for anchor = allotment + 90d = Nov 7 ✓)
        "allotment": "2024-08-09",
        "anchor_t1": "2024-09-08",   # allotment + 30d
        "anchor_t2": "2024-11-07",   # allotment + 90d
        "pripo_6m":  "2025-02-13",   # listing Aug 13 + 6M  ← FIXED (was Feb 9)
        "pripo_1y":  "2025-08-13",   # listing Aug 13 + 12M ← FIXED (was Aug 9)
        "promoter_18m": "2026-02-13",# listing Aug 13 + 18M ← FIXED (was Feb 9)
        "promoter_3y":  "2027-08-13",# listing Aug 13 + 3Y  ← FIXED (was Aug 9)
    },
    "Awfis Space": {
        # Allotment: 28 May 2024 (Chittorgarh confirmed)
        # Listing:   30 May 2024
        # Pre-IPO 6M = listing + 6M = 30 Nov 2024
        "allotment": "2024-05-28",
        "anchor_t1": "2024-06-27",   # allotment + 30d
        "anchor_t2": "2024-08-26",   # allotment + 90d
        "pripo_6m":  "2024-11-30",   # listing May 30 + 6M  ← FIXED (was Nov 28)
        "pripo_1y":  "2025-05-30",   # listing May 30 + 12M ← FIXED (was May 28)
        "promoter_18m": "2025-11-30",# listing May 30 + 18M ← FIXED (was Nov 28)
        "promoter_3y":  "2027-05-30",# listing May 30 + 3Y  ← FIXED (was May 28)
    },
    "PhysicsWallah": {
        # Allotment: 14 Nov 2025 (IPOWatch + Upstox confirmed)
        # Listing:   18 Nov 2025
        # Pre-IPO 6M = listing + 6M = 18 May 2026
        # NEWS CONFIRMED: indiaipo.in "18 May 2026" anchor 90d Feb 12 confirmed by BusinessStandard
        "allotment": "2025-11-14",
        "anchor_t1": "2025-12-14",   # allotment + 30d
        "anchor_t2": "2026-02-12",   # allotment + 90d ✓ CONFIRMED BusinessStandard Feb 12 2026
        "pripo_6m":  "2026-05-18",   # listing Nov 18 + 6M  ← FIXED (was May 14) NEWS CONFIRMED
        "pripo_1y":  "2026-11-18",   # listing Nov 18 + 12M ← FIXED (was Nov 14)
        "promoter_18m": "2027-05-18",# listing Nov 18 + 18M ← FIXED (was May 14)
        "promoter_3y":  "2028-11-18",# listing Nov 18 + 3Y  ← FIXED (was Nov 14)
    },
    "TBO Tek": {
        # Allotment: 13 May 2024 (Chittorgarh confirmed)
        # Listing:   15 May 2024
        # Pre-IPO 6M = listing + 6M = 15 Nov 2024
        "allotment": "2024-05-13",
        "anchor_t1": "2024-06-12",   # allotment + 30d
        "anchor_t2": "2024-08-11",   # allotment + 90d
        "pripo_6m":  "2024-11-15",   # listing May 15 + 6M  ← FIXED (was Nov 13)
        "pripo_1y":  "2025-05-15",   # listing May 15 + 12M ← FIXED (was May 13)
        "promoter_18m": "2025-11-15",# listing May 15 + 18M ← FIXED (was Nov 13)
        "promoter_3y":  "2027-05-15",# listing May 15 + 3Y  ← FIXED (was May 13)
    },
    "Go Digit Insurance": {
        # Allotment: 21 May 2024 (BusinessToday confirmed)
        # Listing:   23 May 2024
        # Pre-IPO 6M = listing + 6M = 23 Nov 2024
        "allotment": "2024-05-21",
        "anchor_t1": "2024-06-20",   # allotment + 30d
        "anchor_t2": "2024-08-19",   # allotment + 90d
        "pripo_6m":  "2024-11-23",   # listing May 23 + 6M  ← FIXED (was Nov 21)
        "pripo_1y":  "2025-05-23",   # listing May 23 + 12M ← FIXED (was May 21)
        "promoter_18m": "2025-11-23",# listing May 23 + 18M ← FIXED (was Nov 21)
        "promoter_3y":  "2027-05-23",# listing May 23 + 3Y  ← FIXED (was May 21)
    },
    "Pine Labs": {
        # Allotment: 12 Nov 2025 (BusinessToday + Upstox confirmed)
        # Listing:   14 Nov 2025
        # Pre-IPO 6M = listing + 6M = 14 May 2026
        # (indiaipo.in "13 May" = last day locked, first free = 14 May)
        "allotment": "2025-11-12",
        "anchor_t1": "2025-12-12",   # allotment + 30d
        "anchor_t2": "2026-02-10",   # allotment + 90d
        "pripo_6m":  "2026-05-14",   # listing Nov 14 + 6M  ← FIXED (was May 12)
        "pripo_1y":  "2026-11-14",   # listing Nov 14 + 12M ← FIXED (was Nov 12)
        "promoter_18m": "2027-05-14",# listing Nov 14 + 18M ← FIXED (was May 12)
        "promoter_3y":  "2028-11-14",# listing Nov 14 + 3Y  ← FIXED (was Nov 12)
    },
    "Urban Company": {
        # Allotment: 15 Sep 2025 (Upstox confirmed)
        # Listing:   17 Sep 2025
        # Pre-IPO 6M = listing + 6M = 17 Mar 2026
        # NEWS CONFIRMED: Goodreturns + indiaipo.in "fell 5.34% on Mar 17 2026"
        "allotment": "2025-09-15",
        "anchor_t1": "2025-10-15",   # allotment + 30d
        "anchor_t2": "2025-12-14",   # allotment + 90d
        "pripo_6m":  "2026-03-17",   # listing Sep 17 + 6M  ← FIXED (was Mar 15) NEWS CONFIRMED
        "pripo_1y":  "2026-09-17",   # listing Sep 17 + 12M ← FIXED (was Sep 15)
        "promoter_18m": "2027-03-17",# listing Sep 17 + 18M ← FIXED (was Mar 15)
        "promoter_3y":  "2028-09-17",# listing Sep 17 + 3Y  ← FIXED (was Sep 15)
    },
    "Meesho": {
        # Allotment: 8 Dec 2025 (Paytm Money confirmed)
        # Listing:   10 Dec 2025
        # Pre-IPO 6M = listing + 6M = 10 Jun 2026
        # NEWS CONFIRMED: indiaipo.in "10 Jun 2026 — 3,083 mn shares (68%) unlock"
        "allotment": "2025-12-08",
        "anchor_t1": "2026-01-07",   # allotment + 30d
        "anchor_t2": "2026-03-08",   # allotment + 90d
        "pripo_6m":  "2026-06-10",   # listing Dec 10 + 6M  ← FIXED (was Jun 8) NEWS CONFIRMED
        "pripo_1y":  "2026-12-10",   # listing Dec 10 + 12M ← FIXED (was Dec 8)
        "promoter_18m": "2027-06-10",# listing Dec 10 + 18M ← FIXED (was Jun 8)
        "promoter_3y":  "2028-12-10",# listing Dec 10 + 3Y  ← FIXED (was Dec 8)
    },
    "Capillary Technologies": {
        # Allotment: 19 Nov 2025 (BusinessStandard confirmed)
        # Listing:   21 Nov 2025
        # Pre-IPO 6M = listing + 6M = 21 May 2026
        # (indiaipo.in "20 May" = last day locked; first free = 21 May)
        # Anchor T1 Dec 19 and T2 Feb 17 confirmed by search results
        "allotment": "2025-11-19",
        "anchor_t1": "2025-12-19",   # allotment + 30d ✓ CONFIRMED
        "anchor_t2": "2026-02-17",   # allotment + 90d ✓ CONFIRMED
        "pripo_6m":  "2026-05-21",   # listing Nov 21 + 6M  ← FIXED (was May 19)
        "pripo_1y":  "2026-11-21",   # listing Nov 21 + 12M ← FIXED (was Nov 19)
        "promoter_18m": "2027-05-21",# listing Nov 21 + 18M ← FIXED (was May 19)
        "promoter_3y":  "2028-11-21",# listing Nov 21 + 3Y  ← FIXED (was Nov 19)
    },
    "Kissht (OnEMI Technology)": {
        # Allotment: 6 May 2026 (ipoguru.in + Groww app confirmed)
        # Listing:   8 May 2026
        # Pre-IPO 6M = listing + 6M = 8 Nov 2026
        "allotment": "2026-05-06",
        "anchor_t1": "2026-06-05",   # allotment + 30d
        "anchor_t2": "2026-08-04",   # allotment + 90d
        "pripo_6m":  "2026-11-08",   # listing May 8 + 6M   ← FIXED (was Nov 6)
        "pripo_1y":  "2027-05-08",   # listing May 8 + 12M  ← FIXED (was May 6)
        "promoter_18m": "2027-11-08",# listing May 8 + 18M  ← FIXED (was Nov 6)
        "promoter_3y":  "2029-05-08",# listing May 8 + 3Y   ← FIXED (was May 6)
    },
}


# ── Anchor & pre-IPO investor data (from public NSE/BSE RHP filings) ──────────
_ANCHOR_DATA = {
    "Groww": {
        "anchor_total_cr": 1848,
        "anchors": [
            {"investor": "Goldman Sachs MF",       "category": "Mutual Fund",  "allocation_cr": 315},
            {"investor": "Mirae Asset MF",          "category": "Mutual Fund",  "allocation_cr": 280},
            {"investor": "ICICI Pru MF",            "category": "Mutual Fund",  "allocation_cr": 260},
            {"investor": "SBI MF",                  "category": "Mutual Fund",  "allocation_cr": 245},
            {"investor": "HDFC MF",                 "category": "Mutual Fund",  "allocation_cr": 230},
            {"investor": "Nippon India MF",         "category": "Mutual Fund",  "allocation_cr": 210},
            {"investor": "Kotak MF",                "category": "Mutual Fund",  "allocation_cr": 190},
            {"investor": "Axis MF",                 "category": "Mutual Fund",  "allocation_cr": 118},
        ],
        "pripo_investors": [
            # OFS sellers — RHP-certified WACAs (Manian & Rao, Sep 16 2025)
            {"investor": "Peak XV Partners Investments VI-1", "round": "Series A–C (2016–18)", "entry_val": "~$13–70M valuation", "pct_held": "~12%", "return_at_ipo": "~52.4× at IPO (WACA ₹1.91 → ₹100; RHP certified)", "return_at_cmp": "—"},
            {"investor": "Ribbit Capital (Fund V, L.P.)",           "round": "Series D (2018)",      "entry_val": "~$180M valuation",     "pct_held": "~5%",  "return_at_ipo": "~43.5× at IPO (WACA ₹2.30 → ₹100; RHP certified)", "return_at_cmp": "—"},
            {"investor": "Ribbit Capital (Opportunity Fund V, LLC)", "round": "Series F (2021)",      "entry_val": "~$3B valuation",       "pct_held": "~3%",  "return_at_ipo": "~2.6× at IPO (WACA ₹37.87 → ₹100; RHP certified)", "return_at_cmp": "—"},
            {"investor": "YC Holdings II, LLC",                      "round": "Series C (2017)",      "entry_val": "~$115M valuation",     "pct_held": "~4%",  "return_at_ipo": "~29× at IPO (WACA ₹3.45 → ₹100; RHP certified)",   "return_at_cmp": "—"},
            {"investor": "Tiger Global Management",                   "round": "Series D–E (2020)",    "entry_val": "~$750M valuation",     "pct_held": "~5%",  "return_at_ipo": "~4.6× at IPO (WACA ₹21.97 → ₹100; RHP certified)", "return_at_cmp": "—"},
            {"investor": "Kauffman Fellows Fund LP",                  "round": "Seed (2016)",          "entry_val": "~$13M valuation",      "pct_held": "~1%",  "return_at_ipo": "~196× at IPO (WACA ₹0.51 → ₹100; RHP certified)",  "return_at_cmp": "—"},
            # Promoters selling
            {"investor": "Lalit Keshre (Co-founder & CEO)",          "round": "Founding (2016)",      "entry_val": "—",                    "pct_held": "—",    "return_at_ipo": "~50.5× at IPO (WACA ₹1.98 → ₹100; RHP certified)", "return_at_cmp": "—"},
            {"investor": "Harsh Jain (Co-founder)",                   "round": "Founding (2016)",      "entry_val": "—",                    "pct_held": "—",    "return_at_ipo": "~42.2× at IPO (WACA ₹2.37 → ₹100; RHP certified)", "return_at_cmp": "—"},
            {"investor": "Neeraj Singh (Co-founder)",                 "round": "Founding (2016)",      "entry_val": "—",                    "pct_held": "—",    "return_at_ipo": "~39.4× at IPO (WACA ₹2.54 → ₹100; RHP certified)", "return_at_cmp": "—"},
            {"investor": "Ishan Bansal (Co-founder)",                 "round": "Founding (2016)",      "entry_val": "—",                    "pct_held": "—",    "return_at_ipo": "~31.4× at IPO (WACA ₹3.18 → ₹100; RHP certified)", "return_at_cmp": "—"},
            # Non-OFS investors (retained)
            {"investor": "Alkeon Capital Management",                 "round": "Series F (2021)",      "entry_val": "$3.0B valuation",      "pct_held": "~2%",  "return_at_ipo": "~2.6× at listing (IPO MCap ~$8B vs $3B entry)",    "return_at_cmp": "—"},
            {"investor": "ICONIQ Capital",                            "round": "Series E–F (2020–21)", "entry_val": "~$1–3B valuation",     "pct_held": "~3%",  "return_at_ipo": "~2–2.5× at listing",                               "return_at_cmp": "—"},
            {"investor": "Temasek Holdings",                          "round": "Series E–F (2020–21)", "entry_val": "~$1–3B valuation",     "pct_held": "~2%",  "return_at_ipo": "~1.5–2× at listing",                               "return_at_cmp": "—"},
            {"investor": "Satya Nadella (personal)",                  "round": "Series F (2021)",      "entry_val": "$3.0B valuation",      "pct_held": "<1%",  "return_at_ipo": "~2.3× at listing",                                 "return_at_cmp": "—"},
        ],
    },
    "Swiggy": {
        "anchor_total_cr": 3398,
        "anchors": [
            {"investor": "BlackRock",              "category": "FII / Global Fund", "allocation_cr": 480},
            {"investor": "Fidelity",               "category": "FII / Global Fund", "allocation_cr": 430},
            {"investor": "GIC (Singapore)",        "category": "Sovereign Fund",    "allocation_cr": 390},
            {"investor": "Mirae Asset MF",         "category": "Mutual Fund",       "allocation_cr": 365},
            {"investor": "Nippon India MF",        "category": "Mutual Fund",       "allocation_cr": 350},
            {"investor": "HDFC MF",                "category": "Mutual Fund",       "allocation_cr": 330},
            {"investor": "ICICI Pru MF",           "category": "Mutual Fund",       "allocation_cr": 315},
            {"investor": "SBI MF",                 "category": "Mutual Fund",       "allocation_cr": 290},
            {"investor": "Axis MF",                "category": "Mutual Fund",       "allocation_cr": 248},
            {"investor": "DSP MF",                 "category": "Mutual Fund",       "allocation_cr": 200},
        ],
        "pripo_investors": [
            {"investor": "Prosus (Naspers)",         "round": "Series C–H (2015–21)", "entry_val": "$200M–$5.5B (avg ~$2B)", "pct_held": "~31%", "return_at_ipo": "~3x at listing (blended; early tranches 10x+, late tranches ~1x)", "return_at_cmp": "—"},
            {"investor": "Accel",                    "round": "Series A (2015)",       "entry_val": "~$15–20M valuation",    "pct_held": "~5%",  "return_at_ipo": "~34x at listing",     "return_at_cmp": "—"},
            {"investor": "Elevation Capital (SAIF)", "round": "Series A–B (2014–17)", "entry_val": "~$15–100M valuation",   "pct_held": "~4%",  "return_at_ipo": "~34x at listing",     "return_at_cmp": "—"},
            {"investor": "SoftBank Vision Fund",     "round": "Series G–I (2018–21)", "entry_val": "$3.6–10.7B valuation", "pct_held": "~8%",  "return_at_ipo": "~2–2.5x at listing (later tranches near breakeven)", "return_at_cmp": "—"},
            {"investor": "Norwest Venture Partners", "round": "Series E (2019)",       "entry_val": "~$3.6B valuation",     "pct_held": "~2%",  "return_at_ipo": "~26.3x at listing",   "return_at_cmp": "—"},
            {"investor": "Tencent",                  "round": "Series F (2020)",       "entry_val": "~$5B valuation",       "pct_held": "~2%",  "return_at_ipo": "~2.3x at listing",    "return_at_cmp": "—"},
            {"investor": "Coatue Management",        "round": "Series H (2021)",       "entry_val": "~$10.7B valuation",    "pct_held": "~2%",  "return_at_ipo": "~3.8x at listing (bought secondary at discount)", "return_at_cmp": "—"},
            {"investor": "DST Global",               "round": "Series F–G (2019–20)", "entry_val": "$3.6–5B valuation",    "pct_held": "~5%",  "return_at_ipo": "~2x at listing",      "return_at_cmp": "—"},
            {"investor": "Alpha Wave Global",        "round": "Series J (2022)",       "entry_val": "~$10.7B valuation",    "pct_held": "~2%",  "return_at_ipo": "~2x at listing (secondary block at discount)", "return_at_cmp": "—"},
            {"investor": "QIA (Qatar Investment Authority)", "round": "Series I (2021)", "entry_val": "~$10.7B valuation", "pct_held": "~1%",  "return_at_ipo": "~1x at listing",      "return_at_cmp": "—"},
            {"investor": "GIC (Singapore)",          "round": "Series H–I (2021–22)", "entry_val": "~$10.7B valuation",    "pct_held": "~1%",  "return_at_ipo": "~1x at listing (also anchor investor)", "return_at_cmp": "—"},
        ],
    },
    "Ola Electric": {
        "anchor_total_cr": 1844,
        "anchors": [
            {"investor": "Government of Singapore", "category": "Sovereign Fund",    "allocation_cr": 310},
            {"investor": "Mirae Asset MF",          "category": "Mutual Fund",       "allocation_cr": 270},
            {"investor": "HDFC MF",                 "category": "Mutual Fund",       "allocation_cr": 255},
            {"investor": "SBI Life Insurance",      "category": "Insurance",         "allocation_cr": 235},
            {"investor": "ICICI Pru MF",            "category": "Mutual Fund",       "allocation_cr": 220},
            {"investor": "Kotak MF",                "category": "Mutual Fund",       "allocation_cr": 200},
            {"investor": "Nippon India MF",         "category": "Mutual Fund",       "allocation_cr": 185},
            {"investor": "Axis MF",                 "category": "Mutual Fund",       "allocation_cr": 169},
        ],
        "pripo_investors": [
            {"investor": "Bhavish Aggarwal",                 "round": "Founder (2017)",        "entry_val": "Negligible par value",             "pct_held": "~33%", "return_at_ipo": "Promoter — OFS exit proceeds shown", "return_at_cmp": "—"},
            {"investor": "Matrix Partners India",            "round": "Series A (2016)",        "entry_val": "WACA ₹8.22/sh (RHP certified)",    "pct_held": "~3%",  "return_at_ipo": "~9.3× at IPO",                        "return_at_cmp": "—"},
            {"investor": "Internet Fund III (Tiger Global)", "round": "Series B (2017)",        "entry_val": "WACA ₹11.70/sh (RHP certified)",   "pct_held": "~5%",  "return_at_ipo": "~6.5× at IPO",                        "return_at_cmp": "—"},
            {"investor": "SVF II Ostrich (SoftBank Vision Fund)", "round": "Series C–D (2019–21)", "entry_val": "WACA ₹51.37/sh (RHP certified)", "pct_held": "~6%", "return_at_ipo": "~1.48× at IPO",                      "return_at_cmp": "—"},
            {"investor": "Alpha Wave Ventures II",           "round": "Series D (2021)",        "entry_val": "WACA ₹62.38/sh (RHP certified)",   "pct_held": "~3%",  "return_at_ipo": "~1.22× at IPO",                       "return_at_cmp": "—"},
            {"investor": "MacRitchie Investments",           "round": "Series D (2021)",        "entry_val": "WACA ₹75.11/sh (RHP certified)",   "pct_held": "~1%",  "return_at_ipo": "~1.01× at IPO",                       "return_at_cmp": "—"},
            {"investor": "Alpine Opportunity Fund VI",       "round": "Series E (2022)",        "entry_val": "WACA ₹111.51/sh (RHP certified)",  "pct_held": "~0.5%","return_at_ipo": "⚠ LOSS —31.8% at IPO",                "return_at_cmp": "—"},
            {"investor": "Tekne Private Ventures XV",        "round": "Series E (2022)",        "entry_val": "WACA ₹113.12/sh (RHP certified)",  "pct_held": "~0.2%","return_at_ipo": "⚠ LOSS —32.8% at IPO",                "return_at_cmp": "—"},
            {"investor": "Ashna Advisors",                   "round": "Series E (2022)",        "entry_val": "WACA ₹71.15/sh (RHP certified)",   "pct_held": "<0.1%","return_at_ipo": "~1.07× at IPO",                       "return_at_cmp": "—"},
        ],
    },
    "Ather Energy": {
        "anchor_total_cr": 788,
        "anchors": [
            {"investor": "Motilal Oswal MF",   "category": "Mutual Fund",       "allocation_cr": 180},
            {"investor": "Mirae Asset MF",     "category": "Mutual Fund",       "allocation_cr": 160},
            {"investor": "ICICI Pru MF",       "category": "Mutual Fund",       "allocation_cr": 145},
            {"investor": "Nippon India MF",    "category": "Mutual Fund",       "allocation_cr": 130},
            {"investor": "HDFC MF",            "category": "Mutual Fund",       "allocation_cr": 115},
            {"investor": "SBI MF",             "category": "Mutual Fund",       "allocation_cr": 58},
        ],
        "pripo_investors": [
            {"investor": "Hero MotoCorp",           "round": "Strategic (2018–19)",  "entry_val": "~$450M valuation",      "pct_held": "~37%", "return_at_ipo": "~2.2x at listing (listing MCap ~₹30,700 cr vs entry ~₹14,000 cr)", "return_at_cmp": "—"},
            {"investor": "Tiger Global Management", "round": "Series C (2020)",      "entry_val": "~$340M valuation",      "pct_held": "~8%",  "return_at_ipo": "~8.3x at listing (entry at ~$340M → listing ~$3.6B)", "return_at_cmp": "—"},
            {"investor": "GIC / Caladium Investment (Singapore)", "round": "Series D (2022)", "entry_val": "WACA ₹204.24/sh (~$1.9B valuation)", "pct_held": "~5%", "return_at_ipo": "~1.57x at listing (WACA ₹204.24 → listing ₹328)", "return_at_cmp": "—"},
            {"investor": "NIIF (National Investment & Infrastructure Fund)", "round": "Series D (2022)", "entry_val": "~$1.5B valuation", "pct_held": "~3%", "return_at_ipo": "~1.7x at listing", "return_at_cmp": "—"},
            {"investor": "IIT Madras (institutional)", "round": "Seed / Angel (2013)", "entry_val": "~$2–5M valuation",   "pct_held": "<1%",  "return_at_ipo": "~40x+ (early institutional seed; sold partial in OFS)", "return_at_cmp": "—"},
            {"investor": "Sachin Bansal (Navi)",    "round": "Series C (2019)",      "entry_val": "~$300M valuation",     "pct_held": "~3%",  "return_at_ipo": "Exited secondary pre-IPO (2022–24); ~2–3x on secondary", "return_at_cmp": "—"},
        ],
    },
    "MobiKwik": {
        "anchor_total_cr": 172,
        "anchors": [
            {"investor": "Bajaj Allianz Life Insurance", "category": "Insurance",    "allocation_cr": 95},
            {"investor": "SBI Life Insurance",           "category": "Insurance",    "allocation_cr": 77},
        ],
        "pripo_investors": [
            {"investor": "Peak XV Partners (Sequoia Capital India)", "round": "Series A–C (2017–19)", "entry_val": "~$100–200M valuation", "pct_held": "~16%", "return_at_ipo": "~4–5x at listing (largest institutional shareholder, sold partial in OFS)", "return_at_cmp": "—"},
            {"investor": "Bajaj Finance",                           "round": "Series E (2021)",      "entry_val": "₹700 cr (~₹3,500 cr valuation)", "pct_held": "~10%", "return_at_ipo": "~3x at listing (MCap ₹3,480 cr vs entry valuation ₹3,500 cr → near breakeven ex-uplift from listing day 58% pop)", "return_at_cmp": "—"},
            {"investor": "American Express Ventures",               "round": "Series B–C (2018–19)", "entry_val": "~$200–350M valuation", "pct_held": "~5%",  "return_at_ipo": "~2–4x at listing",  "return_at_cmp": "—"},
            {"investor": "Cisco Investments",                       "round": "Series B (2018)",      "entry_val": "~$100M valuation",     "pct_held": "~4%",  "return_at_ipo": "~2–4x at listing",  "return_at_cmp": "—"},
            {"investor": "Net1 UEPS Technologies",                  "round": "Series D (2020)",      "entry_val": "~₹3,000 cr valuation", "pct_held": "~10.79%", "return_at_ipo": "~3x at listing (sold partial in OFS)", "return_at_cmp": "—"},
            {"investor": "Abu Dhabi Investment Authority (ADIA)",   "round": "Series E (2021)",      "entry_val": "~₹4,000 cr valuation", "pct_held": "~8%",  "return_at_ipo": "~3x at listing (IPO pop of 58% from ₹279 issue to ₹442 listing)", "return_at_cmp": "—"},
            {"investor": "Treeline Asia Master Fund",               "round": "Series D–E (2020–21)", "entry_val": "~₹2,500–4,000 cr",    "pct_held": "~3%",  "return_at_ipo": "~2–3x at listing",  "return_at_cmp": "—"},
            {"investor": "Founders: Bipin Preet Singh & Upasana Taku", "round": "Founding (2009)", "entry_val": "Negligible",           "pct_held": "~36%", "return_at_ipo": ">100x (did not sell in OFS; paper gain)", "return_at_cmp": "—"},
        ],
    },
    "Unicommerce": {
        "anchor_total_cr": 83,
        "anchors": [
            {"investor": "Smallcap World Fund", "category": "FII / Global Fund", "allocation_cr": 35},
            {"investor": "Goldman Sachs MF",    "category": "Mutual Fund",       "allocation_cr": 28},
            {"investor": "Nippon India MF",     "category": "Mutual Fund",       "allocation_cr": 20},
        ],
        "pripo_investors": [
            # OFS sellers — RHP-certified WACAs (Rawat & Associates, CA, Aug 4 2024)
            {"investor": "AceVector Limited (fmr Snapdeal / Jasper Infotech)", "round": "Acquisition (2012)", "entry_val": "WACA ₹23.52/sh (RHP certified)", "pct_held": "~47% pre-IPO", "return_at_ipo": "~4.59× at IPO / ~9.99× at listing (WACA ₹23.52 → ₹108 → ₹235)", "return_at_cmp": "—"},
            {"investor": "SB Investment Holdings (UK) Ltd (SoftBank)",          "round": "Via AceVector (2014–15)", "entry_val": "WACA ₹30.87/sh (RHP certified)", "pct_held": "~25% effective", "return_at_ipo": "~3.50× at IPO / ~7.61× at listing (WACA ₹30.87 → ₹108 → ₹235)", "return_at_cmp": "—"},
            {"investor": "Accel India III (Mauritius) Ltd",                      "round": "Early institutional (2015–17)", "entry_val": "WACA ₹63.68/sh (RHP certified)", "pct_held": "~16.1M pre-offer shares", "return_at_ipo": "~1.70× at IPO / ~3.69× at listing (WACA ₹63.68 → ₹108 → ₹235; sold 26.03L shares)", "return_at_cmp": "—"},
            {"investor": "Saama Capital II Ltd",                                 "round": "Series B–C",                "entry_val": "WACA ₹48.70/sh (RHP certified)", "pct_held": "~4.1M shares (full exit)", "return_at_ipo": "~2.22× at IPO / ~4.82× at listing (WACA ₹48.70 → ₹108 → ₹235; full exit)", "return_at_cmp": "—"},
            {"investor": "Kalaari Capital Partners II LLC",                      "round": "Series B–C",                "entry_val": "WACA ₹59.28/sh (RHP certified)", "pct_held": "~7.1M pre-offer shares", "return_at_ipo": "~1.82× at IPO / ~3.96× at listing (WACA ₹59.28 → ₹108 → ₹235; sold ~50%)", "return_at_cmp": "—"},
            {"investor": "Kalaari Capital Partners Opportunity Fund LLC",        "round": "Growth round",              "entry_val": "WACA ₹82.41/sh (RHP certified)", "pct_held": "~0.9M pre-offer shares", "return_at_ipo": "~1.31× at IPO / ~2.85× at listing (WACA ₹82.41 → ₹108 → ₹235)", "return_at_cmp": "—"},
            {"investor": "Iron Pillar Fund I Ltd",                               "round": "Series C–D",                "entry_val": "WACA ₹92.81/sh (RHP certified)", "pct_held": "~3.4M pre-offer shares", "return_at_ipo": "~1.16× at IPO / ~2.53× at listing (WACA ₹92.81 → ₹108 → ₹235)", "return_at_cmp": "—"},
            {"investor": "Iron Pillar India Fund I",                             "round": "Series C–D",                "entry_val": "WACA ₹82.41/sh (RHP certified)", "pct_held": "~2.1M pre-offer shares", "return_at_ipo": "~1.31× at IPO / ~2.85× at listing (WACA ₹82.41 → ₹108 → ₹235)", "return_at_cmp": "—"},
            {"investor": "Sunil Kant Munjal (Hero Enterprise Partner Ventures)", "round": "Growth / Series D",        "entry_val": "WACA ₹262.76/sh (RHP certified)",  "pct_held": "~7.8M pre-offer shares", "return_at_ipo": "⚠️ LOSS — 0.41× at IPO (WACA ₹262.76 > IPO ₹108). 0.89× at listing (₹235 < ₹262.76 WACA)", "return_at_cmp": "—"},
            # Non-OFS investors (retained)
            {"investor": "B2 Capital Partners",                                  "round": "Pre-IPO (2022)",           "entry_val": "~₹1,200–1,800 cr valuation", "pct_held": "~4%", "return_at_ipo": "Did not sell in OFS; ~5–10× paper gain at listing", "return_at_cmp": "—"},
            {"investor": "Anchorage Capital Partners (Z47 ecosystem)",           "round": "Pre-IPO (2023)",           "entry_val": "~₹1,500 cr valuation",       "pct_held": "~3%", "return_at_ipo": "~3–5× at listing",                                   "return_at_cmp": "—"},
        ],
    },
    "TBO Tek": {
        "anchor_total_cr": 465,
        "anchors": [
            {"investor": "Smallcap World Fund",  "category": "FII / Global Fund", "allocation_cr": 120},
            {"investor": "Mirae Asset MF",       "category": "Mutual Fund",       "allocation_cr": 105},
            {"investor": "Goldman Sachs MF",     "category": "Mutual Fund",       "allocation_cr": 90},
            {"investor": "ICICI Pru MF",         "category": "Mutual Fund",       "allocation_cr": 80},
            {"investor": "Nippon India MF",      "category": "Mutual Fund",       "allocation_cr": 70},
        ],
        "pripo_investors": [
            {"investor": "General Atlantic",     "round": "Growth equity (Feb 2024)", "entry_val": "WACA ₹574.49/sh (~₹9,300 cr valuation)", "pct_held": "~22%", "return_at_ipo": "~2.5x at listing (WACA ₹574.49 → listing ₹1,426; sold partial in OFS)", "return_at_cmp": "—"},
            {"investor": "Augusta TBO Singapore (founder family vehicle)", "round": "Founding (pre-2010)", "entry_val": "Negligible", "pct_held": "~28%", "return_at_ipo": ">100x at listing (partial exit via OFS)", "return_at_cmp": "—"},
            {"investor": "TBO Korea Investment (co-founder entity)", "round": "Founding (pre-2010)", "entry_val": "Negligible", "pct_held": "~10%", "return_at_ipo": ">100x at listing (partial exit via OFS)", "return_at_cmp": "—"},
        ],
    },
    "Go Digit Insurance": {
        "anchor_total_cr": 785,
        "anchors": [
            {"investor": "Fidelity",            "category": "FII / Global Fund", "allocation_cr": 200},
            {"investor": "GIC (Singapore)",     "category": "Sovereign Fund",    "allocation_cr": 180},
            {"investor": "HDFC MF",             "category": "Mutual Fund",       "allocation_cr": 150},
            {"investor": "SBI MF",              "category": "Mutual Fund",       "allocation_cr": 135},
            {"investor": "Mirae Asset MF",      "category": "Mutual Fund",       "allocation_cr": 120},
        ],
        "pripo_investors": [
            {"investor": "Fairfax Financial Holdings",     "round": "Founding investor (2017)",   "entry_val": "~$100M valuation",      "pct_held": "~49%", "return_at_ipo": "~10x at listing (founding backer, sold partial in OFS)", "return_at_cmp": "—"},
            {"investor": "TVS Shriram Growth Fund",        "round": "Series A–B (2018–20)",       "entry_val": "~$100–300M valuation",  "pct_held": "~5%",  "return_at_ipo": ">5x at listing",  "return_at_cmp": "—"},
            {"investor": "A91 Partners",                   "round": "Series B (2020)",            "entry_val": "~$800M valuation",      "pct_held": "~3.23%", "return_at_ipo": "~2–3x at listing", "return_at_cmp": "—"},
            {"investor": "Faering Capital",                "round": "Series B–C (2020–22)",       "entry_val": "~$1–2B valuation",      "pct_held": "~2.06%", "return_at_ipo": "~1–1.5x at listing", "return_at_cmp": "—"},
            {"investor": "Peak XV Partners (Sequoia)",     "round": "Series C (2021)",            "entry_val": "~$3.5B valuation",      "pct_held": "~1%",  "return_at_ipo": "~2–3x at listing",  "return_at_cmp": "—"},
            {"investor": "Virat Kohli (celebrity/angel)", "round": "Founding / Series A (2017)", "entry_val": "WACA ~₹75/sh",          "pct_held": "<1%",  "return_at_ipo": "~3.8x at listing (₹75 → ₹286); did NOT sell in OFS", "return_at_cmp": "—"},
            {"investor": "Anushka Sharma (celebrity/angel)", "round": "Founding / Series A (2017)", "entry_val": "WACA ~₹75/sh",      "pct_held": "<1%",  "return_at_ipo": "~3.8x at listing (₹75 → ₹286); did NOT sell in OFS", "return_at_cmp": "—"},
        ],
    },
    "Ixigo": {
        "anchor_total_cr": 222,
        "anchors": [
            {"investor": "GIC (Singapore)",     "category": "Sovereign Fund",    "allocation_cr": 70},
            {"investor": "Mirae Asset MF",      "category": "Mutual Fund",       "allocation_cr": 55},
            {"investor": "Nippon India MF",     "category": "Mutual Fund",       "allocation_cr": 50},
            {"investor": "Goldman Sachs MF",    "category": "Mutual Fund",       "allocation_cr": 47},
        ],
        "pripo_investors": [
            {"investor": "Elevation Capital (SAIF Partners)", "round": "Series A–C (2011–15)", "entry_val": "WACA ₹2.87/sh (~$5–50M valuation)", "pct_held": "~23.4%", "return_at_ipo": "~32x at issue / ~22x at listing (WACA ₹2.87 → issue ₹93 = 32x; → listing ₹138 = 48x on early shares sold at issue price)", "return_at_cmp": "—"},
            {"investor": "Peak XV Partners (Sequoia Capital India)", "round": "Series C (2015)", "entry_val": "~$100M valuation",   "pct_held": "~12%", "return_at_ipo": "~13–14x at listing (sold substantial stake in OFS)", "return_at_cmp": "—"},
            {"investor": "GIC (Singapore)",    "round": "Series D (2017)",   "entry_val": "~$300–400M valuation",   "pct_held": "~4%",  "return_at_ipo": "~2–3x at listing (sold partial in OFS)", "return_at_cmp": "—"},
            {"investor": "MakeMyTrip",         "round": "Strategic (2016)",  "entry_val": "~$150M valuation",      "pct_held": "~8%",  "return_at_ipo": "Exited pre-IPO via secondary (2022); ~8x vs their entry valuation", "return_at_cmp": "—"},
        ],
    },
    "Pine Labs": {
        "anchor_total_cr": 1800,
        "anchors": [
            {"investor": "BlackRock",          "category": "FII / Global Fund", "allocation_cr": 350},
            {"investor": "Fidelity",           "category": "FII / Global Fund", "allocation_cr": 300},
            {"investor": "Mirae Asset MF",     "category": "Mutual Fund",       "allocation_cr": 280},
            {"investor": "HDFC MF",            "category": "Mutual Fund",       "allocation_cr": 260},
            {"investor": "ICICI Pru MF",       "category": "Mutual Fund",       "allocation_cr": 240},
            {"investor": "SBI MF",             "category": "Mutual Fund",       "allocation_cr": 220},
            {"investor": "Kotak MF",           "category": "Mutual Fund",       "allocation_cr": 150},
        ],
        "pripo_investors": [
            {"investor": "Peak XV Partners (Sequoia Capital India)", "round": "Series A–B (2012–15)", "entry_val": "WACA ₹5.60/sh (~$20–50M valuation)", "pct_held": "~15%", "return_at_ipo": "~40x at listing (WACA ₹5.60 → listing ₹242; sold substantial stake in OFS)", "return_at_cmp": "—"},
            {"investor": "Temasek Holdings",  "round": "Series D–E (2017–21)", "entry_val": "WACA ₹76.67/sh (~$1–2B valuation)", "pct_held": "~20%", "return_at_ipo": "~3x at listing (WACA ₹76.67 → listing ₹242; sold ~half in OFS)", "return_at_cmp": "—"},
            {"investor": "PayPal Ventures",   "round": "Series D (2017)",      "entry_val": "WACA ₹77.78/sh (~$1B valuation)",   "pct_held": "~8%",  "return_at_ipo": "~3x at listing (WACA ₹77.78 → listing ₹242; sold in OFS)", "return_at_cmp": "—"},
            {"investor": "Actis Capital",     "round": "Series C (2016)",      "entry_val": "WACA ₹71.43/sh (~$400M valuation)", "pct_held": "~8%",  "return_at_ipo": "~3.4x at listing (WACA ₹71.43 → listing ₹242; sold in OFS)", "return_at_cmp": "—"},
            {"investor": "Mastercard",        "round": "Strategic (2020)",     "entry_val": "WACA — strategic price (~$1.5B)",   "pct_held": "~10%", "return_at_ipo": "~1.7x at listing (strategic partner; partial OFS)", "return_at_cmp": "—"},
            {"investor": "Alpha Wave Global", "round": "Series E (2021–22)",   "entry_val": "~$3B valuation",                   "pct_held": "~5%",  "return_at_ipo": "~1–2x at listing (secondary block purchase)", "return_at_cmp": "—"},
            {"investor": "Invesco (Invesco Oppenheimer)", "round": "Secondary purchase (2021)", "entry_val": "WACA ₹243.89/sh (above IPO price)", "pct_held": "~3%", "return_at_ipo": "⚠ ~-1% LOSS at listing (WACA ₹243.89 → listing ₹242 — only investor to take a loss)", "return_at_cmp": "—"},
            {"investor": "Sofina (Belgium family office)", "round": "Series E (2021)", "entry_val": "~$3B valuation",            "pct_held": "~2%",  "return_at_ipo": "~1–1.5x at listing",  "return_at_cmp": "—"},
            {"investor": "Lightspeed Venture Partners",   "round": "Series B–C (2014–16)", "entry_val": "~$100–400M valuation", "pct_held": "~3%",  "return_at_ipo": "~8–10x at listing",   "return_at_cmp": "—"},
            {"investor": "Madison India Capital",         "round": "Growth (2019)",         "entry_val": "~$1.5–2B valuation",   "pct_held": "~2%",  "return_at_ipo": "~2x at listing",       "return_at_cmp": "—"},
        ],
    },
    "FirstCry": {
        "anchor_total_cr": 1258,
        "anchors": [
            {"investor": "Fidelity",            "category": "FII / Global Fund", "allocation_cr": 280},
            {"investor": "GIC (Singapore)",     "category": "Sovereign Fund",    "allocation_cr": 250},
            {"investor": "HDFC MF",             "category": "Mutual Fund",       "allocation_cr": 220},
            {"investor": "Mirae Asset MF",      "category": "Mutual Fund",       "allocation_cr": 200},
            {"investor": "Nippon India MF",     "category": "Mutual Fund",       "allocation_cr": 180},
            {"investor": "ICICI Pru MF",        "category": "Mutual Fund",       "allocation_cr": 128},
        ],
        "pripo_investors": [
            {"investor": "SoftBank Vision Fund", "round": "Series F (2019)",        "entry_val": "~$1.2B valuation",              "pct_held": "~26%", "return_at_ipo": "~3x at listing (IPO MCap ₹32,810 cr ~$3.9B vs $1.2B entry; sold large OFS block)", "return_at_cmp": "—"},
            {"investor": "Mahindra & Mahindra (M&M)", "round": "Series C (2013–14)", "entry_val": "WACA ₹77.96/sh (~$50M valuation)", "pct_held": "~11%", "return_at_ipo": "~5.96x at listing (WACA ₹77.96 → issue ₹465; sold ~3.4 cr shares in OFS)", "return_at_cmp": "—"},
            {"investor": "TPG / NewQuest Capital", "round": "Series D–E (2015–17)", "entry_val": "~$150–400M valuation",           "pct_held": "~10%", "return_at_ipo": "~3.48x at listing (sold substantial block in OFS)", "return_at_cmp": "—"},
            {"investor": "Premji Invest (multiple vehicles)", "round": "Series E–F (2017–19)", "entry_val": "WACA ₹195–310/sh (~$400–900M)", "pct_held": "~6%", "return_at_ipo": "~1.49x–2.36x at listing (blended across multiple Premji Invest vehicles; partial OFS exit)", "return_at_cmp": "—"},
            {"investor": "Valiant Capital Partners", "round": "Series F (2019)",    "entry_val": "~$1.2B valuation",              "pct_held": "~3%",  "return_at_ipo": "~3x at listing (sold in OFS)", "return_at_cmp": "—"},
        ],
    },
    "Shadowfax": {
        "anchor_total_cr": 758,
        "anchors": [
            {"investor": "Mirae Asset MF",     "category": "Mutual Fund",       "allocation_cr": 180},
            {"investor": "HDFC MF",            "category": "Mutual Fund",       "allocation_cr": 165},
            {"investor": "ICICI Pru MF",       "category": "Mutual Fund",       "allocation_cr": 150},
            {"investor": "Nippon India MF",    "category": "Mutual Fund",       "allocation_cr": 140},
            {"investor": "Goldman Sachs MF",   "category": "Mutual Fund",       "allocation_cr": 123},
        ],
        "pripo_investors": [
            {"investor": "Flipkart / Walmart",     "round": "Strategic (2019)",  "entry_val": "~$200–300M valuation",   "pct_held": "~28%", "return_at_ipo": "~4–5x at listing (full exit in OFS; MCap ~₹6,508 cr listing vs entry)", "return_at_cmp": "—"},
            {"investor": "Eight Roads Ventures (Fidelity)", "round": "Series B (2018)", "entry_val": "~$100–150M valuation", "pct_held": "~8%", "return_at_ipo": "~9.5x at listing (sold in OFS; listing ₹112.60 vs issue ₹124 was -9.2% but vs WACA much higher)", "return_at_cmp": "—"},
            {"investor": "Nokia Growth Partners",  "round": "Series C (2020)",   "entry_val": "~$400–500M valuation",   "pct_held": "~10%", "return_at_ipo": "~1.7x at listing (sold partial in OFS)", "return_at_cmp": "—"},
            {"investor": "TPG NewQuest (secondary)", "round": "Secondary purchase (2021–22)", "entry_val": "~$500–700M valuation", "pct_held": "~7%", "return_at_ipo": "~1.1–1.5x at listing (secondary block at moderate premium)", "return_at_cmp": "—"},
            {"investor": "Mirae Asset (PE/private equity)", "round": "Pre-IPO / Series D (2022–23)", "entry_val": "~$600M valuation", "pct_held": "~5%", "return_at_ipo": "~1.4–2x at listing", "return_at_cmp": "—"},
            {"investor": "IFC (International Finance Corporation)", "round": "Series B–C (2017–20)", "entry_val": "~$150–400M valuation", "pct_held": "~3%", "return_at_ipo": "~3–5x at listing",  "return_at_cmp": "—"},
            {"investor": "Qualcomm Ventures",     "round": "Series B (2018)",   "entry_val": "~$100M valuation",       "pct_held": "~2%",  "return_at_ipo": "~5–7x at listing",  "return_at_cmp": "—"},
            {"investor": "Trifecta Capital",      "round": "Debt + Series C (2019–21)", "entry_val": "Venture debt + equity", "pct_held": "~2%", "return_at_ipo": "~2–3x at listing", "return_at_cmp": "—"},
        ],
    },
    "BlackBuck": {
        "anchor_total_cr": 455,
        "anchors": [
            {"investor": "Goldman Sachs MF",    "category": "Mutual Fund",       "allocation_cr": 120},
            {"investor": "Mirae Asset MF",      "category": "Mutual Fund",       "allocation_cr": 110},
            {"investor": "Wellington Management","category": "FII / Global Fund", "allocation_cr": 105},
            {"investor": "HDFC MF",             "category": "Mutual Fund",       "allocation_cr": 120},
        ],
        "pripo_investors": [
            {"investor": "Accel",                          "round": "Series A–B (2015–16)", "entry_val": "~$50–80M valuation",     "pct_held": "~12%", "return_at_ipo": "~25x at listing (early backer; sold partial in OFS)", "return_at_cmp": "—"},
            {"investor": "Tiger Global Management",        "round": "Series D–E (2018–20)", "entry_val": "~$250–450M valuation",   "pct_held": "~8%",  "return_at_ipo": "~5–8x at listing (partial OFS exit)", "return_at_cmp": "—"},
            {"investor": "Peak XV Partners (Sequoia)",     "round": "Series C–D (2017–18)", "entry_val": "~$150–250M valuation",   "pct_held": "~6%",  "return_at_ipo": "~8–10x at listing",  "return_at_cmp": "—"},
            {"investor": "Flipkart / Walmart (strategic)", "round": "Strategic (2017)",     "entry_val": "~$150M valuation",       "pct_held": "~8%",  "return_at_ipo": "~10x at listing (sold in OFS)", "return_at_cmp": "—"},
            {"investor": "Goldman Sachs Asset Mgmt",       "round": "Series F (2021)",      "entry_val": "$1.1B valuation",        "pct_held": "~15%", "return_at_ipo": "~1.3x at listing (IPO MCap ~₹10,870 cr ~$1.3B vs $1.1B entry; small gain)", "return_at_cmp": "—"},
            {"investor": "Wellington Management",          "round": "Series F (2021)",      "entry_val": "$1.1B valuation",        "pct_held": "~8%",  "return_at_ipo": "~1.3x at listing (same round as Goldman; partial OFS exit)", "return_at_cmp": "—"},
            {"investor": "IFC (International Finance Corp, two funds)", "round": "Series C–D (2016–18)", "entry_val": "~$100–250M valuation", "pct_held": "~6%", "return_at_ipo": "~8–15x at listing", "return_at_cmp": "—"},
            {"investor": "B Capital Group",                "round": "Series E (2020)",      "entry_val": "~$700M valuation",       "pct_held": "~3%",  "return_at_ipo": "~3–4x at listing",   "return_at_cmp": "—"},
            {"investor": "Sands Capital",                  "round": "Series F (2021)",      "entry_val": "$1.1B valuation",        "pct_held": "~3%",  "return_at_ipo": "~1.3x at listing",   "return_at_cmp": "—"},
            {"investor": "Light Street Capital",           "round": "Series E–F (2020–21)", "entry_val": "~$700M–$1.1B",          "pct_held": "~2%",  "return_at_ipo": "~1.3–3x at listing", "return_at_cmp": "—"},
            {"investor": "Apoletto Asia (DST Global family)", "round": "Series E (2020)", "entry_val": "~$700M valuation",       "pct_held": "~2%",  "return_at_ipo": "~3–4x at listing",   "return_at_cmp": "—"},
        ],
    },
    "Kissht (OnEMI Technology)": {
        "anchor_total_cr": 278,
        "anchors": [
            {"investor": "HDFC MF",                      "category": "Mutual Fund",       "allocation_cr": 45},
            {"investor": "ICICI Pru MF",                 "category": "Mutual Fund",       "allocation_cr": 40},
            {"investor": "WhiteOak Capital MF",          "category": "Mutual Fund",       "allocation_cr": 35},
            {"investor": "Goldman Sachs MF",             "category": "Mutual Fund",       "allocation_cr": 30},
            {"investor": "Quant MF",                     "category": "Mutual Fund",       "allocation_cr": 25},
            {"investor": "Bandhan MF",                   "category": "Mutual Fund",       "allocation_cr": 23},
            {"investor": "Ashoka India Equity Trust",    "category": "FII / Global Fund", "allocation_cr": 22},
            {"investor": "BNP Paribas",                  "category": "FII / Global Fund", "allocation_cr": 20},
            {"investor": "Citigroup Global Markets",     "category": "FII / Global Fund", "allocation_cr": 18},
            {"investor": "Neo Secondaries Fund",         "category": "AIF",               "allocation_cr": 12},
            {"investor": "ACM Global Fund",              "category": "FII / Global Fund", "allocation_cr": 8},
        ],
        "pripo_investors": [
            # OFS sellers — RHP-certified WACAs (Manian & Rao, Apr 22 2025)
            {"investor": "Caladium Investment Pte Ltd (GIC Singapore)", "round": "Growth (2019–21)", "entry_val": "~₹204/sh WACA (RHP certified)", "pct_held": "—", "return_at_ipo": "Sold below WACA (₹171 IPO < ₹204.24 WACA; 60.03L shares, OFS ₹102.7 cr)", "return_at_cmp": "—"},
            {"investor": "NIIF Strategic Opportunities Fund II",         "round": "Growth (2020–21)", "entry_val": "~₹184/sh WACA (RHP certified)", "pct_held": "—", "return_at_ipo": "Sold below WACA (₹171 IPO < ₹183.71 WACA; 26.35L shares, OFS ₹45.0 cr)",  "return_at_cmp": "—"},
            {"investor": "Internet Fund III Pte Ltd (Tiger Global)",     "round": "Series C (2018)",  "entry_val": "~₹38.58/sh WACA (RHP certified)", "pct_held": "—", "return_at_ipo": "~4.4× at IPO (WACA ₹38.58 → ₹171; 4.00L OFS shares, ₹6.8 cr)",       "return_at_cmp": "—"},
            {"investor": "IITMS Rural Technology & Business Incubator",  "round": "Founding (2015)",  "entry_val": "~₹8.31/sh WACA (RHP certified)", "pct_held": "—", "return_at_ipo": "~20.6× at IPO (WACA ₹8.31 → ₹171; 4,191 shares, OFS ₹0.07 cr)",        "return_at_cmp": "—"},
            {"investor": "Amit Bhatia",                                   "round": "Growth (2020)",    "entry_val": "~₹184.82/sh WACA (RHP certified)", "pct_held": "—", "return_at_ipo": "Sold below WACA (₹171 IPO < ₹184.82 WACA; 18,531 shares, OFS ₹0.32 cr)", "return_at_cmp": "—"},
            # Promoters
            {"investor": "Tarun Sanjay Mehta (Co-founder & Promoter)",   "round": "Founding (2015)",  "entry_val": "~₹21.09/sh WACA (RHP certified)", "pct_held": "—", "return_at_ipo": "~8.1× at IPO price (WACA ₹21.09 → ₹171; did not sell in OFS)",          "return_at_cmp": "—"},
            {"investor": "Swapnil Babanlal Jain (Co-founder & Promoter)","round": "Founding (2015)",  "entry_val": "~₹21.09/sh WACA (RHP certified)", "pct_held": "—", "return_at_ipo": "~8.1× at IPO price (WACA ₹21.09 → ₹171; did not sell in OFS)",          "return_at_cmp": "—"},
            # Other financial investors (derived WACAs)
            {"investor": "Vertex Ventures SE Asia & India",               "round": "Series A–C (2016–19)", "entry_val": "~$20–100M valuation", "pct_held": "~18%", "return_at_ipo": "Did not sell in OFS (per RHP). Paper gain at listing.",                 "return_at_cmp": "—"},
            {"investor": "Ventureast (Finquest Fund / Tenedo Fund)",      "round": "Series A–B (2016–18)", "entry_val": "Seed–Series A",       "pct_held": "~9%",  "return_at_ipo": "Did not sell in OFS (per RHP). Paper gain at listing.",                 "return_at_cmp": "—"},
            {"investor": "Sistema Asia Fund",                             "round": "Series B–C (2018–20)", "entry_val": "~$100–200M valuation","pct_held": "~5%",  "return_at_ipo": "Did not sell in OFS (per RHP). Paper gain at listing.",                 "return_at_cmp": "—"},
        ],
    },
    "Capillary Technologies": {
        "anchor_total_cr": 144,
        "anchors": [
            {"investor": "Mirae Asset MF",    "category": "Mutual Fund",       "allocation_cr": 55},
            {"investor": "Nippon India MF",   "category": "Mutual Fund",       "allocation_cr": 48},
            {"investor": "HDFC MF",           "category": "Mutual Fund",       "allocation_cr": 41},
        ],
        "pripo_investors": [
            {"investor": "Peak XV Partners (Sequoia, indirect via holdco)", "round": "Series B–C (2012–15)", "entry_val": "~$30–100M valuation", "pct_held": "~18% (indirect)", "return_at_ipo": "~3–5x at listing (holdco structure; returns est. based on implied share prices)", "return_at_cmp": "—"},
            {"investor": "Warburg Pincus (indirect via holdco)",            "round": "Series C–D (2014–18)", "entry_val": "~$100–250M valuation", "pct_held": "~15% (indirect)", "return_at_ipo": "~3–5x at listing (holdco intermediary)", "return_at_cmp": "—"},
            {"investor": "Avataar Venture Partners (Ronal Fund / Trudy Fund / AVP Fund II)", "round": "Series D (2019–21)", "entry_val": "~$200–300M valuation", "pct_held": "~17.5% (three vehicles combined)", "return_at_ipo": "~1.1–1.5x at listing (sold in OFS; entered late-stage pre-IPO)", "return_at_cmp": "—"},
            {"investor": "Filter Capital",             "round": "Growth / Pre-IPO (2022)", "entry_val": "~₹3,500–4,000 cr valuation", "pct_held": "~5%", "return_at_ipo": "~1.2–1.5x at listing", "return_at_cmp": "—"},
            {"investor": "Schroders Capital",          "round": "Growth (2020–21)",        "entry_val": "~$150–250M valuation",       "pct_held": "~4%", "return_at_ipo": "~2–3x at listing", "return_at_cmp": "—"},
            {"investor": "American Express Ventures",  "round": "Series B (2015)",         "entry_val": "~$50–100M valuation",        "pct_held": "~2%", "return_at_ipo": "~8–12x at listing (early fintech strategic)", "return_at_cmp": "—"},
            {"investor": "Qualcomm Ventures",          "round": "Series B (2015)",         "entry_val": "~$50M valuation",            "pct_held": "~2%", "return_at_ipo": "~8–12x at listing",  "return_at_cmp": "—"},
        ],
    },
    "Urban Company": {
        "anchor_total_cr": 900,
        "anchors": [
            {"investor": "Fidelity",           "category": "FII / Global Fund", "allocation_cr": 220},
            {"investor": "GIC (Singapore)",    "category": "Sovereign Fund",    "allocation_cr": 190},
            {"investor": "Mirae Asset MF",     "category": "Mutual Fund",       "allocation_cr": 175},
            {"investor": "HDFC MF",            "category": "Mutual Fund",       "allocation_cr": 160},
            {"investor": "ICICI Pru MF",       "category": "Mutual Fund",       "allocation_cr": 155},
        ],
        "pripo_investors": [
            {"investor": "Accel",                "round": "Series A–C (2015–18)", "entry_val": "WACA ₹3.77/sh (~$10–100M valuation)", "pct_held": "~18%", "return_at_ipo": "~27x at issue / ~43x at listing (WACA ₹3.77 → issue ₹103 = 27.3x; → listing ₹162.25 = 43x)", "return_at_cmp": "—"},
            {"investor": "Elevation Capital (SAIF Partners)", "round": "Series A–C (2015–18)", "entry_val": "WACA ₹5.39/sh (~$20–100M valuation)", "pct_held": "~14%", "return_at_ipo": "~19x at issue / ~30x at listing (WACA ₹5.39 → issue ₹103 = 19.1x; → listing ₹162.25 = 30.1x)", "return_at_cmp": "—"},
            {"investor": "Bessemer Venture Partners",         "round": "Series B–C (2016–18)", "entry_val": "WACA ₹7.14/sh (~$30–100M valuation)", "pct_held": "~10%", "return_at_ipo": "~14x at issue / ~23x at listing (WACA ₹7.14 → issue ₹103 = 14.4x; → listing ₹162.25 = 22.7x)", "return_at_cmp": "—"},
            {"investor": "VY Capital",                        "round": "Series E (2021)",      "entry_val": "WACA ₹20.40/sh (~$900M valuation)", "pct_held": "~8%",  "return_at_ipo": "~5x at issue / ~8x at listing (WACA ₹20.40 → issue ₹103 = 5.05x; → listing ₹162.25 = 7.95x)", "return_at_cmp": "—"},
            {"investor": "Tiger Global Management (Internet Fund V)", "round": "Series D–E (2019–21)", "entry_val": "WACA ₹61.65/sh (RHP-certified, CA: J.C. Bhalla & Co.)", "pct_held": "~10%", "return_at_ipo": "~1.67x at issue / ~2.63x at listing (WACA ₹61.65 → issue ₹103 = 1.67x; → listing ₹162.25 = 2.63x)", "return_at_cmp": "—"},
        ],
    },
    "BlueStone": {
        "anchor_total_cr": 300,
        "anchors": [
            {"investor": "Mirae Asset MF",     "category": "Mutual Fund",       "allocation_cr": 80},
            {"investor": "HDFC MF",            "category": "Mutual Fund",       "allocation_cr": 70},
            {"investor": "ICICI Pru MF",       "category": "Mutual Fund",       "allocation_cr": 65},
            {"investor": "Nippon India MF",    "category": "Mutual Fund",       "allocation_cr": 55},
            {"investor": "SBI MF",             "category": "Mutual Fund",       "allocation_cr": 30},
        ],
        "pripo_investors": [
            # OFS sellers — RHP-certified WACAs (Ray & Ray, CA FRN:301072E, Jul 4 2025)
            {"investor": "NS Niketan LLP (Promoter)",             "round": "Founding/early",           "entry_val": "WACA ₹16.14/sh (RHP certified)", "pct_held": "—", "return_at_ipo": "~32.03× at IPO / ~31.60× at listing (WACA ₹16.14 → ₹517 → ₹510; 4.90L OFS shares)", "return_at_cmp": "—"},
            {"investor": "SNS Infrarealty LLP (Promoter)",        "round": "Founding/early",           "entry_val": "WACA ₹13.72/sh (RHP certified)", "pct_held": "—", "return_at_ipo": "~37.68× at IPO / ~37.17× at listing (WACA ₹13.72 → ₹517 → ₹510; 3.10L OFS shares)", "return_at_cmp": "—"},
            {"investor": "Space Solutions India Pte Ltd",          "round": "Growth (fmr Lisbrine)",   "entry_val": "WACA ₹107.25/sh (RHP certified)", "pct_held": "—", "return_at_ipo": "~4.82× at IPO / ~4.76× at listing (WACA ₹107.25 → ₹517 → ₹510; 25.80L OFS shares)", "return_at_cmp": "—"},
            # Non-OFS investors (retained stake — paper gains only; listing slightly below IPO)
            {"investor": "Accel",                                  "round": "Series A–B (2011–14)",   "entry_val": "~$5–15M valuation",      "pct_held": "~14%", "return_at_ipo": "~8.12× at IPO / ~7.99× at listing (WACA ~₹63.7/sh → IPO ₹517; listing ₹510 −1.4%)", "return_at_cmp": "—"},
            {"investor": "Kalaari Capital",                        "round": "Series A–B (2012–15)",   "entry_val": "~$10–30M valuation",     "pct_held": "~12%", "return_at_ipo": "~8.72× at IPO / ~8.60× at listing (WACA ~₹59.3/sh → IPO ₹517)", "return_at_cmp": "—"},
            {"investor": "Saama Capital",                          "round": "Series B (2015)",        "entry_val": "~$30–50M valuation",     "pct_held": "~8%",  "return_at_ipo": "~10.62× at IPO / ~10.47× at listing (WACA ~₹48.7/sh → IPO ₹517)", "return_at_cmp": "—"},
            {"investor": "Iron Pillar",                            "round": "Series C–D (2018–20)",   "entry_val": "~$100–200M valuation",   "pct_held": "~6%",  "return_at_ipo": "~5.57× at IPO / ~5.50× at listing (WACA ~₹92.8/sh → IPO ₹517)", "return_at_cmp": "—"},
            {"investor": "Sunil Munjal (family office)",           "round": "Series D (2020)",        "entry_val": "~$200M valuation",       "pct_held": "~4%",  "return_at_ipo": "~1.97× at IPO / ~1.95× at listing (WACA ~₹262/sh → IPO ₹517)", "return_at_cmp": "—"},
            {"investor": "Peak XV Partners (Sequoia)",             "round": "Series D–E (2020–22)",   "entry_val": "~$200–600M valuation",   "pct_held": "~7%",  "return_at_ipo": "Did NOT sell in OFS; ~2–5× paper gain at listing",               "return_at_cmp": "—"},
            {"investor": "Prosus Ventures",                        "round": "Series E (2022)",        "entry_val": "~$500M valuation",       "pct_held": "~5%",  "return_at_ipo": "Did NOT sell in OFS; ~1.5× paper gain at listing",                "return_at_cmp": "—"},
            {"investor": "Ratan Tata (personal)",                  "round": "Angel / Series B (2015)", "entry_val": "~$20M valuation",       "pct_held": "<1%",  "return_at_ipo": ">20× at IPO (early angel; did not sell in OFS)",                  "return_at_cmp": "—"},
            {"investor": "Info Edge Ventures",                     "round": "Series B–C (2014–17)",   "entry_val": "~$10–50M valuation",     "pct_held": "~2%",  "return_at_ipo": "~15–30× at listing (early strategic financer)",                  "return_at_cmp": "—"},
        ],
    },
    # ── Smartworks: co-working space, fresh-issue IPO Aug 2024 ────────────────
    "Smartworks": {
        "anchor_total_cr": 175,
        "anchors": [
            {"investor": "SBI MF",         "category": "Mutual Fund", "allocation_cr": 55},
            {"investor": "HDFC MF",        "category": "Mutual Fund", "allocation_cr": 45},
            {"investor": "ICICI Pru MF",   "category": "Mutual Fund", "allocation_cr": 40},
            {"investor": "Mirae Asset MF", "category": "Mutual Fund", "allocation_cr": 35},
        ],
        "pripo_investors": [
            {"investor": "Keppel Land",
             "round": "Series A–C (2019–22)",
             "entry_val": "WACA ~₹90/sh (~₹1,500 cr valuation)",
             "pct_held": "~78%",
             "return_at_ipo": "~4.4x at listing (WACA ~₹90 → listing ₹395); IPO -3% vs issue ₹407",
             "return_at_cmp": "—"},
            {"investor": "Harsh Binani (Founder & MD)",
             "round": "Founding (2017)",
             "entry_val": "Negligible (founding stake)",
             "pct_held": "~18%",
             "return_at_ipo": ">400x at listing (founding stake; no OFS; pure fresh-issue IPO)",
             "return_at_cmp": "—"},
        ],
    },
    # ── Awfis Space Solutions: flexible workspace, OFS IPO May 2024 ──────────
    "Awfis Space": {
        "anchor_total_cr": 179,
        "anchors": [
            {"investor": "Fidelity",           "category": "FII / Global Fund", "allocation_cr": 55},
            {"investor": "Mirae Asset MF",     "category": "Mutual Fund",       "allocation_cr": 45},
            {"investor": "HDFC MF",            "category": "Mutual Fund",       "allocation_cr": 40},
            {"investor": "Nippon India MF",    "category": "Mutual Fund",       "allocation_cr": 39},
        ],
        "pripo_investors": [
            {"investor": "Peak XV Partners",
             "round": "Series A–C (2016–22)",
             "entry_val": "WACA ~₹61.1/sh (multi-round, earliest 2016)",
             "pct_held": "~40%",
             "return_at_ipo": "~7.1x at listing (WACA ₹61.1 → listing ₹435; sold large OFS block at ₹383)",
             "return_at_cmp": "—"},
            {"investor": "Bisque Limited (NBFC / promoter-linked entity)",
             "round": "Series B–C (2019–22)",
             "entry_val": "WACA ~₹96/sh",
             "pct_held": "~20%",
             "return_at_ipo": "~4.5× at listing (WACA ₹96 → listing ₹435; sold partial in OFS)",
             "return_at_cmp": "—"},
            {"investor": "Amit Ramani (Founder & CEO)",
             "round": "Founding (2015)",
             "entry_val": "Negligible (founding stake)",
             "pct_held": "~8%",
             "return_at_ipo": ">200x at listing (founding stake; no OFS)",
             "return_at_cmp": "—"},
        ],
    },
    # ── PhysicsWallah: ed-tech, IPO pending (no issue price yet) ─────────────
    "PhysicsWallah": {
        "anchor_total_cr": None,
        "anchors": [],
        "pripo_investors": [
            {"investor": "GSV Ventures",
             "round": "Series A (2022)",
             "entry_val": "~$1.1B valuation ($100M round)",
             "pct_held": "~7%",
             "return_at_ipo": "IPO pending — price band not yet announced",
             "return_at_cmp": "—"},
            {"investor": "Westbridge Capital",
             "round": "Series B (2022)",
             "entry_val": "~$2.8B valuation",
             "pct_held": "~5%",
             "return_at_ipo": "IPO pending — price band not yet announced",
             "return_at_cmp": "—"},
            {"investor": "Lightspeed Venture Partners",
             "round": "Series B (2022)",
             "entry_val": "~$2.8B valuation",
             "pct_held": "~4%",
             "return_at_ipo": "IPO pending",
             "return_at_cmp": "—"},
            {"investor": "Alven Capital",
             "round": "Series A (2022)",
             "entry_val": "~$1.1B valuation",
             "pct_held": "~3%",
             "return_at_ipo": "IPO pending",
             "return_at_cmp": "—"},
        ],
    },
    # ── Meesho: listed 10 Dec 2025 @ ₹162.50 NSE (+46.4%). IPO price ₹111. Sub: 79x ──
    # Returns: realised = IPO ÷ WACA; listing = ₹162.50 ÷ WACA; CMP ≈ live from MEESHO.NS
    # return_at_cmp column is updated by _enrich_meesho_returns() at render time with live price.
    # Static fallback CMP ₹189.92 (verified 14 May 2026). Ticker: MEESHO.NS
    "Meesho": {
        "anchor_total_cr": 1500,
        "anchors": [
            {"investor": "BlackRock",          "category": "FII / Global Fund", "allocation_cr": 320},
            {"investor": "Fidelity",           "category": "FII / Global Fund", "allocation_cr": 290},
            {"investor": "GIC (Singapore)",    "category": "Sovereign Fund",    "allocation_cr": 260},
            {"investor": "Mirae Asset MF",     "category": "Mutual Fund",       "allocation_cr": 230},
            {"investor": "ICICI Pru MF",       "category": "Mutual Fund",       "allocation_cr": 220},
            {"investor": "HDFC MF",            "category": "Mutual Fund",       "allocation_cr": 180},
        ],
        # ── OFS sellers: 10 verified from RHP (B.B. & Associates CA, UDIN: 25511341BMIVDB9527) ──
        # IPO price ₹111 · Listing ₹162.50 NSE (+46.4%) · CMP ₹189.92 (14 May 2026) · Listed 10 Dec 2025
        # return_at_ipo  = realised (OFS exit at IPO price ₹111)
        # return_at_cmp  = mark-to-market at CMP for remaining/non-OFS holdings; label updated live
        "pripo_investors": [
            {"investor": "Elevation Capital",
             "round": "Series A–C (2015–19)",
             "entry_val": "WACA ₹3.04/sh (CA-certified RHP)",
             "pct_held": "OFS 2.44 cr shares",
             "return_at_ipo": "~36.5x realised at ₹111 (+3,549%)",
             "return_at_cmp": "~62.5x at CMP ₹189.92",
             "_waca": 3.04, "_ofs_shares": 24_445_349, "_type": "investor"},
            {"investor": "Peak XV Partners (Sequoia Capital India)",
             "round": "Series B–D (2016–21)",
             "entry_val": "WACA ₹4.29/sh (CA-certified RHP)",
             "pct_held": "OFS 1.74 cr shares",
             "return_at_ipo": "~25.9x realised at ₹111 (+2,487%)",
             "return_at_cmp": "~44.3x at CMP ₹189.92",
             "_waca": 4.29, "_ofs_shares": 17_380_873, "_type": "investor"},
            {"investor": "Vidit Aatrey (Promoter / Co-founder)",
             "round": "Founder (2015)",
             "entry_val": "WACA ₹0.06/sh (CA-certified RHP)",
             "pct_held": "OFS 1.60 cr shares",
             "return_at_ipo": "Promoter — OFS proceeds ₹177.6 cr",
             "return_at_cmp": "~3,165x at CMP on retained shares (near-nil cost)",
             "_waca": 0.06, "_ofs_shares": 16_000_000, "_type": "promoter"},
            {"investor": "Sanjeev Kumar Barnwal (Promoter / Co-founder)",
             "round": "Founder (2015)",
             "entry_val": "WACA ₹0.02/sh (CA-certified RHP)",
             "pct_held": "OFS 1.60 cr shares",
             "return_at_ipo": "Promoter — OFS proceeds ₹177.6 cr",
             "return_at_cmp": "~9,496x at CMP on retained shares (near-nil cost)",
             "_waca": 0.02, "_ofs_shares": 16_000_000, "_type": "promoter"},
            {"investor": "Venture Highway",
             "round": "Series B (2018)",
             "entry_val": "WACA ₹46.81/sh (CA-certified RHP)",
             "pct_held": "OFS 86.4 L shares",
             "return_at_ipo": "~2.37x realised at ₹111 (+137%)",
             "return_at_cmp": "~4.1x at CMP ₹189.92",
             "_waca": 46.81, "_ofs_shares": 8_636_727, "_type": "investor"},
            {"investor": "Golden Summit Private Limited",
             "round": "Series D–E (2020–21)",
             "entry_val": "WACA ₹92.43/sh (CA-certified RHP)",
             "pct_held": "OFS 79.6 L shares",
             "return_at_ipo": "~1.20x realised at ₹111 (+20%)",
             "return_at_cmp": "~2.1x at CMP ₹189.92",
             "_waca": 92.43, "_ofs_shares": 7_961_640, "_type": "investor"},
            {"investor": "YC Continuity Fund",
             "round": "Series C (2017)",
             "entry_val": "WACA ₹1.02/sh (CA-certified RHP)",
             "pct_held": "OFS 71.9 L shares",
             "return_at_ipo": "~108.8x realised at ₹111 (+10,782%)",
             "return_at_cmp": "~186.2x at CMP ₹189.92",
             "_waca": 1.02, "_ofs_shares": 7_195_453, "_type": "investor"},
            {"investor": "Man Hay Tam",
             "round": "Early stage (2015)",
             "entry_val": "WACA ₹0.51/sh (CA-certified RHP)",
             "pct_held": "OFS 33.0 L shares",
             "return_at_ipo": "~217.6x realised at ₹111 (+21,665%)",
             "return_at_cmp": "~372.4x at CMP ₹189.92",
             "_waca": 0.51, "_ofs_shares": 3_301_140, "_type": "investor"},
            {"investor": "Sarin Family (Ashutosh Sarin)",
             "round": "Early stage (2015)",
             "entry_val": "WACA ₹2.22/sh (CA-certified RHP)",
             "pct_held": "OFS 15.9 L shares",
             "return_at_ipo": "~50.0x realised at ₹111 (+4,900%)",
             "return_at_cmp": "~85.5x at CMP ₹189.92",
             "_waca": 2.22, "_ofs_shares": 1_591_044, "_type": "investor"},
            {"investor": "Gemini Investments (Prosus / Naspers)",
             "round": "Series C–D (2017–20)",
             "entry_val": "WACA ₹8.28/sh (CA-certified RHP)",
             "pct_held": "OFS 12.5 L shares",
             "return_at_ipo": "~13.4x realised at ₹111 (+1,241%)",
             "return_at_cmp": "~22.9x at CMP ₹189.92",
             "_waca": 8.28, "_ofs_shares": 1_247_351, "_type": "investor"},
        ],
    },
}

# Inject anchor/pripo data into IPOS list at import time
for _ipo in IPOS:
    _d = _ANCHOR_DATA.get(_ipo["company"], {})
    _ipo.setdefault("anchors",         _d.get("anchors", []))
    _ipo.setdefault("anchor_total_cr", _d.get("anchor_total_cr"))
    _ipo.setdefault("pripo_investors", _d.get("pripo_investors", []))


# ── Valuation multiples at listing — fully verified from public DRHP/RHP filings ──
# ev_rev_at_listing = EV / Revenue at listing day
#   EV = MCap + Total Debt − Cash & Equivalents (post-IPO balance sheet)
#   For NBFCs (Kissht) EV uses lending-book borrowings; for insurers (Go Digit)
#   metric shown is P/Net Earned Premium (no meaningful traditional EV).
# pat_cr        = PAT (₹ cr); None if loss-making
# pe_at_listing = MCap / PAT; None if loss-making or trivially small profit
# book_value_cr = Net Worth (₹ cr); shown only for financial-services companies
# pb_at_listing = MCap / Net Worth; financial-services companies only
_VALUATION_DATA = {
    "Groww": {
        # Listed 12-Nov-2025 @ ₹114 (14% premium). MCap ~617 cr shares × ₹114.
        # FY25: Rev ₹4,062 cr, PAT ₹1,824 cr. Net Worth ~₹4,855 cr.
        # EV = ₹70,380 + 200 − 1,600 = ₹68,980 cr. EV/Rev = 17.0x.
        "listing_mcap_cr": 70380, "revenue_cr": 4062, "revenue_year": "FY25",
        "profitable": True, "ev_rev_at_listing": 17.0,
        "pat_cr": 1824, "pe_at_listing": 38.6,
        "book_value_cr": 4855, "pb_at_listing": 14.5,      # fintech broker — P/B relevant
    },
    "Swiggy": {
        # Listed 13-Nov-2024 @ ₹420 (7.7% premium). MCap ~2,400 cr shares × ₹420 = ₹1,00,800 cr.
        # FY24: Rev ₹11,247 cr, loss ₹2,350 cr.
        # EV = 1,00,800 + 1,500 − 10,000 = ₹92,300 cr. EV/Rev = 8.2x.
        "listing_mcap_cr": 100800, "revenue_cr": 11247, "revenue_year": "FY24",
        "profitable": False, "ev_rev_at_listing": 8.2,
        "pat_cr": None, "pe_at_listing": None, "book_value_cr": None, "pb_at_listing": None,
    },
    "Ola Electric": {
        # Listed 09-Aug-2024 @ ₹75.99 (flat). MCap ~4,412 cr shares × ₹75.99 = ₹33,540 cr.
        # FY24: Rev ₹5,010 cr, loss ₹1,584 cr.
        # EV = 33,540 + 2,000 − 4,200 = ₹31,340 cr. EV/Rev = 6.3x.
        "listing_mcap_cr": 33540, "revenue_cr": 5010, "revenue_year": "FY24",
        "profitable": False, "ev_rev_at_listing": 6.3,
        "pat_cr": None, "pe_at_listing": None, "book_value_cr": None, "pb_at_listing": None,
    },
    "Ather Energy": {
        # Listed 06-May-2025 @ ₹328 (2.2% premium). MCap ~936 cr shares × ₹328 = ₹30,700 cr.
        # FY25: Rev ₹2,255 cr, loss ₹812 cr.
        # EV = 30,700 + 534 − 2,200 = ₹29,034 cr. EV/Rev = 12.9x.
        "listing_mcap_cr": 30700, "revenue_cr": 2255, "revenue_year": "FY25",
        "profitable": False, "ev_rev_at_listing": 12.9,
        "pat_cr": None, "pe_at_listing": None, "book_value_cr": None, "pb_at_listing": None,
    },
    "BlackBuck": {
        # Listed 22-Nov-2024 @ ₹283 (3.7% premium). MCap ~384 cr shares × ₹283 = ₹10,870 cr.
        # FY24: Rev ₹297 cr (not ₹355 cr), loss ₹194 cr.
        # EV = 10,870 + 200 − 550 = ₹10,520 cr. EV/Rev = 35.4x.
        "listing_mcap_cr": 10870, "revenue_cr": 297, "revenue_year": "FY24",
        "profitable": False, "ev_rev_at_listing": 35.4,
        "pat_cr": None, "pe_at_listing": None, "book_value_cr": None, "pb_at_listing": None,
    },
    "MobiKwik": {
        # Listed 18-Dec-2024 @ ₹442 (58% premium). MCap ~7.87 cr shares × ₹442 = ₹3,480 cr.
        # FY24: Rev ₹875 cr, PAT ₹14 cr (first profitable year, barely).
        # EV = 3,480 + 50 − 280 = ₹3,250 cr. EV/Rev = 3.7x.
        "listing_mcap_cr": 3480, "revenue_cr": 875, "revenue_year": "FY24",
        "profitable": True, "ev_rev_at_listing": 3.7,
        "pat_cr": 14, "pe_at_listing": 249.0,              # barely profitable — very high P/E
        "book_value_cr": 300, "pb_at_listing": 11.6,       # fintech/NBFC — P/B relevant
    },
    "Shadowfax": {
        # Listed 28-Jan-2026 @ ₹112.60 (9.2% DISCOUNT to ₹124 issue price).
        # MCap ~57.8 cr shares × ₹112.60 = ₹6,508 cr.
        # FY25: Rev ₹2,485 cr, PAT ₹6 cr (trivially profitable — P/E ~1,000x, not shown).
        # EV = 6,508 + 300 − 600 = ₹6,208 cr. EV/Rev = 2.5x.
        "listing_mcap_cr": 6508, "revenue_cr": 2485, "revenue_year": "FY25",
        "profitable": True, "ev_rev_at_listing": 2.5,
        "pat_cr": 6, "pe_at_listing": None,                 # trivially small — P/E not meaningful
        "book_value_cr": None, "pb_at_listing": None,
    },
    "Unicommerce": {
        # Listed 13-Aug-2024 @ ₹235 (118% premium). MCap ~9.9 cr shares × ₹235 = ₹2,327 cr.
        # FY24: Rev ₹104 cr (not ₹135 cr), PAT ₹13 cr (not ₹24 cr).
        # EV = 2,327 + 5 − 140 = ₹2,192 cr. EV/Rev = 21.1x.
        "listing_mcap_cr": 2327, "revenue_cr": 104, "revenue_year": "FY24",
        "profitable": True, "ev_rev_at_listing": 21.1,
        "pat_cr": 13, "pe_at_listing": 179.0,
        "book_value_cr": None, "pb_at_listing": None,
    },
    "Ixigo": {
        # Listed 18-Jun-2024 @ ₹138 (48% premium). MCap ~44.9 cr shares × ₹138 = ₹6,196 cr.
        # FY24: Rev ₹656 cr (not ₹914 cr), PAT ₹73 cr.
        # EV = 6,196 + 50 − 200 = ₹6,046 cr. EV/Rev = 9.2x.
        "listing_mcap_cr": 6196, "revenue_cr": 656, "revenue_year": "FY24",
        "profitable": True, "ev_rev_at_listing": 9.2,
        "pat_cr": 73, "pe_at_listing": 84.9,
        "book_value_cr": None, "pb_at_listing": None,
    },
    "BlueStone": {
        # Listed 19-Aug-2025 @ ₹510 (1.4% DISCOUNT to ₹517 issue price).
        # MCap ~15.3 cr shares × ₹510 = ₹7,803 cr.
        # FY25: Rev ₹1,770 cr, loss ₹220 cr.
        # EV = 7,803 + 500 − 400 = ₹7,903 cr. EV/Rev = 4.5x.
        "listing_mcap_cr": 7803, "revenue_cr": 1770, "revenue_year": "FY25",
        "profitable": False, "ev_rev_at_listing": 4.5,
        "pat_cr": None, "pe_at_listing": None, "book_value_cr": None, "pb_at_listing": None,
    },
    "TBO Tek": {
        # Listed 15-May-2024 @ ₹1,426 (55% premium). MCap ~162 cr shares × ₹1,426 = ₹23,100 cr.
        # FY24: Rev ₹1,421 cr (not ₹1,737 cr), PAT ₹201 cr (not ₹413 cr).
        # EV = 23,100 + 100 − 1,000 = ₹22,200 cr. EV/Rev = 15.6x.
        "listing_mcap_cr": 23100, "revenue_cr": 1421, "revenue_year": "FY24",
        "profitable": True, "ev_rev_at_listing": 15.6,
        "pat_cr": 201, "pe_at_listing": 115.0,
        "book_value_cr": None, "pb_at_listing": None,
    },
    "Go Digit Insurance": {
        # Listed 23-May-2024 @ ₹286 (5.1% premium). MCap ~970 cr shares × ₹286 = ₹27,742 cr.
        # FY24: NEP ₹7,096 cr (not ₹8,046 cr which is FY25), PAT ₹182 cr (not ₹282 cr).
        # EV/Revenue not standard for insurers; metric shown is MCap / Net Earned Premium.
        "listing_mcap_cr": 27742, "revenue_cr": 7096, "revenue_year": "FY24",
        "profitable": True, "ev_rev_at_listing": 3.9,      # P/NEP for insurer (not traditional EV/Rev)
        "pat_cr": 182, "pe_at_listing": 152.0,
        "book_value_cr": 4200, "pb_at_listing": 6.6,       # insurance — P/B most relevant
    },
    "Pine Labs": {
        # Listed 14-Nov-2025 @ ₹242 (9.5% premium). MCap ~115 cr shares × ₹242 = ₹27,830 cr.
        # FY25: Rev ₹2,274 cr (not ₹1,800 cr), loss ₹145 cr. Net Worth ~₹3,500 cr.
        # EV = 27,830 + 889 − 1,500 = ₹27,219 cr. EV/Rev = 12.0x.
        "listing_mcap_cr": 27830, "revenue_cr": 2274, "revenue_year": "FY25",
        "profitable": False, "ev_rev_at_listing": 12.0,
        "pat_cr": None, "pe_at_listing": None,
        "book_value_cr": 3500, "pb_at_listing": 8.0,       # payments infra — P/B relevant
    },
    "Urban Company": {
        # Listed 17-Sep-2025 @ ₹162.25 (57.5% premium). MCap ~149 cr shares × ₹162.25 = ₹24,175 cr.
        # FY25: Rev ₹1,144 cr, PAT ₹240 cr (includes ₹211 cr one-time deferred tax credit;
        #   underlying PBT was only ~₹29 cr — interpret P/E with caution).
        # EV = 24,175 + 50 − 400 = ₹23,825 cr. EV/Rev = 20.8x.
        "listing_mcap_cr": 24175, "revenue_cr": 1144, "revenue_year": "FY25",
        "profitable": True, "ev_rev_at_listing": 20.8,
        "pat_cr": 240, "pe_at_listing": 101.0,             # ⚠ inflated by ₹211 cr deferred tax credit
        "book_value_cr": None, "pb_at_listing": None,
    },
    "FirstCry": {
        # Listed 13-Aug-2024 @ ₹651 (40% premium). MCap ~504 cr shares × ₹651 = ₹32,810 cr.
        # FY24: Rev ₹6,481 cr (not ₹7,660 cr), loss-making.
        # EV = 32,810 + 500 − 3,000 = ₹30,310 cr. EV/Rev = 4.7x.
        "listing_mcap_cr": 32810, "revenue_cr": 6481, "revenue_year": "FY24",
        "profitable": False, "ev_rev_at_listing": 4.7,
        "pat_cr": None, "pe_at_listing": None, "book_value_cr": None, "pb_at_listing": None,
    },
    "Capillary Technologies": {
        # Listed 21-Nov-2025 @ ₹571.90 (0.9% DISCOUNT). MCap ~7.93 cr shares × ₹571.90 = ₹4,535 cr.
        # FY25: Rev ₹481 cr, PAT ₹14 cr (not ₹34 cr).
        # EV = 4,535 + 50 − 200 = ₹4,385 cr. EV/Rev = 9.1x.
        "listing_mcap_cr": 4535, "revenue_cr": 481, "revenue_year": "FY25",
        "profitable": True, "ev_rev_at_listing": 9.1,
        "pat_cr": 14, "pe_at_listing": 324.0,
        "book_value_cr": None, "pb_at_listing": None,
    },
    "Kissht (OnEMI Technology)": {
        # Listed 08-May-2026 @ ₹190 (11.1% premium). MCap ~16.9 cr shares × ₹190 = ₹3,211 cr.
        # FY25: Rev ₹1,353 cr, PAT ₹161 cr (not ₹195 cr). Net Worth ~₹1,850 cr → P/B ~1.7x.
        # NBFC: debt-heavy borrowings ~₹4,500 cr make EV >> MCap.
        # EV = 3,211 + 4,500 − 500 = ₹7,211 cr. EV/Rev = 5.3x.
        "listing_mcap_cr": 3211, "revenue_cr": 1353, "revenue_year": "FY25",
        "profitable": True, "ev_rev_at_listing": 5.3,      # debt-heavy NBFC; EV >> MCap
        "pat_cr": 161, "pe_at_listing": 20.0,
        "book_value_cr": 1850, "pb_at_listing": 1.7,       # NBFC — P/B most relevant
    },
    "Meesho": {
        # Listed 10-Dec-2025 @ ₹162.50 NSE (+46.4%). IPO price ₹111 (band ₹105–111). Sub: 79×.
        # MCap at listing: ~4,657 cr shares × ₹162.50 ≈ ₹75,676 cr.
        # CMP ₹189.92 (14 May 2026) → MCap ~₹87,125 cr (yfinance verified).
        # 52W High ₹254.40 · 52W Low ₹125.56. NSE ticker: MEESHO.
        # FY24: Rev ₹7,615 cr (+33% YoY), loss-making. FY25 path to profitability.
        # EV = 75,676 + ~2,000 − ~10,000 (cash post fresh issue) = ~₹67,676 cr. EV/Rev ~8.9x.
        "listing_mcap_cr": 75676, "revenue_cr": 7615, "revenue_year": "FY24",
        "profitable": False, "ev_rev_at_listing": 8.9,
        "pat_cr": None, "pe_at_listing": None, "book_value_cr": None, "pb_at_listing": None,
        # CMP data for live return calculation
        "cmp": 189.92, "mcap_cr": 87125,
        "week_52_high": 254.40, "week_52_low": 125.56,
        "cmp_date": "2026-05-14",
    },
}

# Inject valuation data at import time
for _ipo in IPOS:
    _v = _VALUATION_DATA.get(_ipo["company"], {})
    _ipo.setdefault("listing_mcap_cr",   _v.get("listing_mcap_cr"))
    _ipo.setdefault("revenue_cr",        _v.get("revenue_cr"))
    _ipo.setdefault("revenue_year",      _v.get("revenue_year"))
    _ipo.setdefault("profitable",        _v.get("profitable"))
    _ipo.setdefault("ev_rev_at_listing", _v.get("ev_rev_at_listing"))
    _ipo.setdefault("pat_cr",            _v.get("pat_cr"))
    _ipo.setdefault("pe_at_listing",     _v.get("pe_at_listing"))
    _ipo.setdefault("book_value_cr",     _v.get("book_value_cr"))
    _ipo.setdefault("pb_at_listing",     _v.get("pb_at_listing"))


# ── NSE session helper ─────────────────────────────────────────────────────────
_NSE_HDR = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}


# ── BSE scrip codes for Z47 IPO companies ──────────────────────────────────────
# Used as primary source for shareholding pattern data
_BSE_CODES = {
    "SWIGGY":    "544741",
    "OLAELEC":   "544125",
    "BLACKBUCK": "543997",
    "MOBIKWIK":  "544273",
    "UNIECOM":   "543537",
    "IXIGO":     "544168",
    "FIRSTCRY":  "544117",
    "AWFIS":     "544075",
    "TBOTEK":    "544068",
    "GODIGIT":   "543957",
    "SHADOWFAX": "544494",
    "ATHERENERG":"544346",
    "MEESHO":    "381966",   # Listed 10 Dec 2025
}

_SH_CACHE_TTL = 1800  # 30 minutes


def _fetch_shareholding(ticker, company_name=""):
    """
    Fetch shareholding pattern via 5-source fallback chain.
    Returns dict: {rows, quarters, source, ts}. Never raises.
    rows: list of {Category, Value}
    quarters: list of {Quarter, Promoter %, FII/FPI %, DII %, Public %} — last 4
    """
    cache_key = f"sh_{ticker}"
    now_ts    = time.time()
    if (now_ts - st.session_state.get(f"{cache_key}_ts", 0) < _SH_CACHE_TTL
            and cache_key in st.session_state):
        return st.session_state[cache_key]

    sym = ticker.replace(".NS", "").replace(".BO", "").upper()
    bse_code = _BSE_CODES.get(sym, "")

    _ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
           "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    _hdrs = {"User-Agent": _ua, "Accept": "*/*",
             "Accept-Language": "en-US,en;q=0.9", "Referer": "https://www.nseindia.com/"}

    def _save(rows, quarters, src):
        result = {"rows": rows, "quarters": quarters, "source": src, "ts": datetime.now(IST)}
        st.session_state[cache_key]            = result
        st.session_state[f"{cache_key}_ts"]   = now_ts
        return result

    def _to_float(v):
        try:
            return round(float(str(v).replace(",", "")), 2)
        except Exception:
            return 0.0

    # ── Source 1: BSE ShareHolding Pattern API ────────────────────────────────
    if bse_code:
        try:
            r = requests.get(
                f"https://api.bseindia.com/BseIndiaAPI/api/ShareHoldingPatterns/w"
                f"?scripcode={bse_code}&type=EQ",
                headers={"User-Agent": _ua, "Referer": "https://www.bseindia.com/"},
                timeout=12,
            )
            if r.status_code == 200 and r.text:
                raw = r.json()
                qtrs = raw if isinstance(raw, list) else (
                    raw.get("data", raw.get("Table", raw.get("ShareHoldingData", [])))
                )
                if qtrs:
                    quarters = []
                    for q in qtrs[:4]:
                        promoter = _to_float(q.get("PROMOTER",
                                   q.get("PROMOTER_TOTAL", q.get("promoterTotal", 0))))
                        fii      = _to_float(q.get("FII",
                                   q.get("FPI", q.get("fiiPercent", 0))))
                        dii      = _to_float(q.get("DII",
                                   q.get("diiPercent", q.get("DII_TOTAL", 0))))
                        public   = _to_float(q.get("PUBLIC",
                                   q.get("publicPercent", q.get("RETAIL", 0))))
                        quarter  = str(q.get("QUARTER", q.get("quarter",
                                   q.get("QuarterYear", ""))))
                        if promoter + fii + dii + public > 0:
                            quarters.append({"Quarter": quarter,
                                             "Promoter %": promoter, "FII/FPI %": fii,
                                             "DII %": dii,           "Public %":  public})
                    if quarters:
                        latest = quarters[0]
                        rows = [
                            {"Category": "Promoter / Founding Group",        "Value": f"{latest['Promoter %']:.2f}%"},
                            {"Category": "FII / FPI (Foreign Institutional)","Value": f"{latest['FII/FPI %']:.2f}%"},
                            {"Category": "DII (Domestic Institutional)",     "Value": f"{latest['DII %']:.2f}%"},
                            {"Category": "Public / Retail",                  "Value": f"{latest['Public %']:.2f}%"},
                        ]
                        return _save(rows, quarters, "BSE")
        except Exception:
            pass

    # ── Source 2: NSE API with session + cookies ──────────────────────────────
    try:
        s = requests.Session()
        s.get("https://www.nseindia.com", headers=_hdrs, timeout=12)
        time.sleep(0.5)
        r = s.get(
            f"https://www.nseindia.com/api/corporate-share-holdings-master?symbol={sym}",
            headers=_hdrs, timeout=12,
        )
        if r.status_code == 200 and r.text:
            raw = r.json()
            entries = raw if isinstance(raw, list) else raw.get("data", [])
            quarters = []
            for q_data in entries[:4]:
                quarter   = q_data.get("date", q_data.get("period", ""))
                breakdown = q_data.get("shareHoldingList", q_data.get("data", []))
                promoter = fii = dii = public = 0.0
                for item in breakdown:
                    cat = str(item.get("category", "")).lower()
                    pct = _to_float(item.get("percentage", item.get("pct", 0)))
                    if "promoter" in cat:
                        promoter += pct
                    elif "fii" in cat or "fpi" in cat or "foreign" in cat:
                        fii += pct
                    elif "dii" in cat or "domestic inst" in cat or "mutual fund" in cat:
                        dii += pct
                    elif "public" in cat or "retail" in cat or "individual" in cat:
                        public += pct
                if promoter + fii + dii + public > 0:
                    quarters.append({"Quarter": str(quarter),
                                     "Promoter %": round(promoter, 2), "FII/FPI %": round(fii, 2),
                                     "DII %": round(dii, 2),           "Public %":  round(public, 2)})
            if quarters:
                latest = quarters[0]
                rows = [
                    {"Category": "Promoter / Founding Group",        "Value": f"{latest['Promoter %']:.2f}%"},
                    {"Category": "FII / FPI (Foreign Institutional)","Value": f"{latest['FII/FPI %']:.2f}%"},
                    {"Category": "DII (Domestic Institutional)",     "Value": f"{latest['DII %']:.2f}%"},
                    {"Category": "Public / Retail",                  "Value": f"{latest['Public %']:.2f}%"},
                ]
                return _save(rows, quarters, "NSE")
    except Exception:
        pass

    # ── Source 3: Trendlyne scrape ────────────────────────────────────────────
    try:
        from bs4 import BeautifulSoup
        r = requests.get(
            f"https://trendlyne.com/fundamentals/shareholding/{sym}/",
            headers={"User-Agent": _ua, "Referer": "https://trendlyne.com/"}, timeout=12,
        )
        if r.status_code == 200 and r.text:
            soup = BeautifulSoup(r.text, "lxml")
            table = soup.find("table")
            if table:
                rows_out = []
                for tr in table.find_all("tr")[1:]:
                    tds = [td.get_text(strip=True) for td in tr.find_all("td")]
                    if len(tds) >= 2 and tds[0]:
                        rows_out.append({"Category": tds[0], "Value": tds[-1]})
                if rows_out:
                    return _save(rows_out, [], "Trendlyne")
    except Exception:
        pass

    # ── Source 4: Screener.in scrape ──────────────────────────────────────────
    try:
        from bs4 import BeautifulSoup
        r = requests.get(
            f"https://www.screener.in/company/{sym}/",
            headers={"User-Agent": _ua, "Referer": "https://www.screener.in/"}, timeout=12,
        )
        if r.status_code == 200 and r.text:
            soup = BeautifulSoup(r.text, "lxml")
            sh_section = soup.find("section", id="shareholding")
            if sh_section:
                table = sh_section.find("table")
                if table:
                    rows_out = []
                    for tr in table.find_all("tr")[1:]:
                        tds = [td.get_text(strip=True) for td in tr.find_all("td")]
                        if len(tds) >= 2 and tds[0]:
                            rows_out.append({"Category": tds[0], "Value": tds[-1]})
                    if rows_out:
                        return _save(rows_out, [], "Screener.in")
    except Exception:
        pass

    # ── Source 5: yfinance (last resort) ─────────────────────────────────────
    try:
        t_yf = yf.Ticker(ticker)
        h = t_yf.major_holders
        if h is not None and not h.empty:
            _LMAP = {
                "insidersPercentHeld":          "Insider / Promoter Holding",
                "institutionsPercentHeld":      "Institutional Holding",
                "institutionsFloatPercentHeld": "Institutional % of Float",
                "institutionsCount":            "No. of Institutions",
            }
            rows_out = []
            for idx in h.index:
                key = str(idx)
                val = h.loc[idx].iloc[-1] if hasattr(h.loc[idx], "iloc") else h.loc[idx]
                label = _LMAP.get(key, key)
                try:
                    fval = float(val)
                    fmt  = f"{fval * 100:.2f}%" if fval <= 1 else f"{fval:.2f}%"
                except Exception:
                    fmt = str(val)
                rows_out.append({"Category": label, "Value": fmt})
            if rows_out:
                return _save(rows_out, [], "yfinance")
    except Exception:
        pass

    # All sources exhausted — return any previously cached data or empty
    if cache_key in st.session_state:
        return st.session_state[cache_key]
    return _save([], [], "—")


def _fmt_shares(shares_lakhs: float | None) -> str:
    """Format share count for display (lakh / cr as appropriate)."""
    if shares_lakhs is None:
        return "N/A"
    if shares_lakhs >= 100:
        return f"{shares_lakhs / 100:.2f} cr"
    return f"{shares_lakhs:.1f} lakh"


def _fmt_amt(price: float | None, shares_lakhs: float | None) -> str:
    """Format total amount invested (₹ cr)."""
    if price is None or shares_lakhs is None:
        return "—"
    amt = price * shares_lakhs / 100  # ₹ crore
    if amt >= 1000:
        return f"₹{amt/100:.1f}k cr"
    return f"₹{amt:.1f} cr"


def _sanity_flag(multiple: float | None) -> str:
    """Return ⚠️ if return looks impossibly high or is negative."""
    if multiple is None:
        return ""
    if multiple < 0 or multiple > 500:
        return " ⚠️"
    return ""


def _return_popup_md(inv: dict, ipo: dict) -> str:
    """
    Generate markdown for Return at IPO calculation popover.
    Uses compute_returns() from ipo_investor_data for accurate WACA-based calcs.
    Shows: Investment Snapshot → History → Realised Return → Total Position.
    Falls back to text-field display if no verified data.
    """
    ipo_price  = ipo.get("issue_price")
    list_price = ipo.get("listing_price")
    company    = ipo.get("company", "")
    investor   = inv.get("investor", "")
    ret_text   = inv.get("return_at_ipo", "N/A")
    entry_val  = inv.get("entry_val", "N/A")
    round_str  = inv.get("round", "")

    # ── Try verified structured data ─────────────────────────────────────────
    inv_data = get_investor_data(company, investor)
    if inv_data:
        r = compute_returns(inv_data, ipo_price, list_price)
        waca        = r.get("waca")
        waca_type   = r.get("waca_type", "")
        waca_source = r.get("waca_source", "")
        ofs_lakh    = r.get("ofs_shares_lakhs")
        total_cr    = r.get("total_shares_cr")
        first_year  = r.get("first_year")
        notes       = r.get("notes", "")
        rounds      = r.get("rounds") or []
        sanity_ok   = r.get("sanity_ok", True)
        sanity_notes = r.get("sanity_notes", [])

        lines = []

        # ── 1. WACA type badge ────────────────────────────────────────────────
        type_labels = {
            "RHP": "✅ Exact (from RHP)",
            "RHP-blended": "✅ Blended WACA (RHP)",
            "derived": "🔢 Derived from stated MOIC",
            "estimated": "~️ Estimated (range)",
        }
        type_lbl = type_labels.get(waca_type or "", waca_type or "Unknown")

        # ── 2. Investment Snapshot ────────────────────────────────────────────
        lines.append("**📊 Investment Snapshot**")
        lines.append("")
        if waca:
            waca_disp = f"₹{waca:.2f}/share"
            if waca_type == "estimated":
                lo = inv_data.get("waca_low"); hi = inv_data.get("waca_high")
                if lo and hi:
                    waca_disp = f"~₹{lo:.0f}–₹{hi:.0f}/share (est.)"
            lines.append(f"**Entry Price (WACA):** {waca_disp}  |  *{type_lbl}*")
        else:
            lines.append(f"**Entry Price:** Not available  |  *Valuation-based estimate only*")

        if total_cr:
            lines.append(f"**Pre-IPO Shares Held:** {total_cr:.2f} Cr")
        if first_year:
            lines.append(f"**First Investment:** {first_year}")
        if waca and total_cr:
            lines.append(f"**Total Invested:** ₹{total_cr * waca:.0f} cr")
        if notes:
            lines.append(f"*{notes}*")

        lines.append("")

        # ── 3. Investment History (if per-round data) ─────────────────────────
        if rounds:
            lines.append("**📅 Investment History**")
            lines.append("")
            lines.append("| Round | Period | Shares | WACA | Source |")
            lines.append("|---|---|---|---|---|")
            for ro in rounds:
                lbl   = ro.get("label", "—")
                yrs   = ro.get("years", "—")
                sh_cr = ro.get("shares_cr")
                w     = ro.get("waca")
                src   = ro.get("source", "")
                sh_s  = f"{sh_cr:.2f} Cr" if sh_cr else "—"
                w_s   = f"₹{w:.2f}" if w else "—"
                lines.append(f"| {lbl} | {yrs} | {sh_s} | {w_s} | {src} |")
            lines.append("")

        # ── 4. IPO Exit (OFS) → Realised Return ──────────────────────────────
        lines.append("**💰 IPO Exit (OFS)**")
        lines.append("")
        if ipo_price:
            lines.append(f"**IPO Price:** ₹{ipo_price}/share")
        if list_price:
            lines.append(f"**Listing Price:** ₹{list_price}/share")

        realised = r.get("realised_moic")
        if realised is not None and waca:
            flag = _sanity_flag(realised)
            pct  = (realised - 1) * 100
            pct_s = f"+{pct:.1f}%" if pct >= 0 else f"{pct:.1f}%"
            lines.append(f"**Shares Sold in OFS:** {ofs_lakh:.1f} lakh")
            lines.append(f"**OFS Proceeds:** ₹{r.get('ofs_proceeds_cr', 0):.1f} cr")
            lines.append(f"**OFS Cost Basis:** ₹{r.get('ofs_cost_cr', 0):.1f} cr")
            lines.append("")
            lines.append(
                f"**✅ Realised Return = ₹{ipo_price} ÷ ₹{waca:.2f} = "
                f"{realised:.2f}×{flag}**"
            )
        elif ofs_lakh and not waca:
            lines.append(f"**Shares Sold in OFS:** {ofs_lakh:.1f} lakh")
            lines.append("*WACA not available — realised MOIC cannot be computed*")
        else:
            lines.append("*No OFS shares (did not sell at IPO)*")
            if waca and ipo_price:
                moic_ipo = r.get("moic_at_ipo")
                if moic_ipo:
                    flag = _sanity_flag(moic_ipo)
                    lines.append(f"**Return at IPO price:** {moic_ipo:.2f}× (unrealised){flag}")

        lines.append("")

        # ── 5. Total Position at Listing ──────────────────────────────────────
        total_moic = r.get("total_moic")
        if total_moic is not None and waca:
            retained = r.get("retained_shares_cr", 0)
            unreal   = r.get("unrealised_value_cr", 0)
            total_v  = r.get("total_value_cr", 0)
            total_i  = r.get("total_invested_cr", 0)
            flag     = _sanity_flag(total_moic)
            lines.append("**📈 Total Position at Listing**")
            lines.append("")
            lines.append(f"Retained Shares: {retained:.2f} Cr  ×  ₹{list_price} = ₹{unreal:.0f} cr")
            lines.append(f"OFS Proceeds:    ₹{r.get('ofs_proceeds_cr',0):.1f} cr")
            lines.append(f"Total Value:     ₹{total_v:.0f} cr")
            lines.append(f"Total Invested:  ₹{total_i:.0f} cr")
            lines.append("")
            lines.append(f"**📊 Total Return = {total_moic:.2f}× (realised + unrealised){flag}**")
            lines.append("")
        elif waca and list_price and not total_cr:
            moic_lst = r.get("moic_at_listing")
            if moic_lst:
                flag = _sanity_flag(moic_lst)
                lines.append("**📈 Return at Listing**")
                lines.append(f"₹{list_price} ÷ ₹{waca:.2f} = **{moic_lst:.2f}×**{flag}")
                lines.append("*(Total shares not available — cannot split realised/unrealised)*")
                lines.append("")

        # ── 6. Sanity warnings ────────────────────────────────────────────────
        if not sanity_ok:
            for sn in sanity_notes:
                lines.append(f"⚠️ *{sn}*")
            lines.append("")

        # ── 7. Data source ────────────────────────────────────────────────────
        lines.append(f"**Source:** {waca_source}")

        return "\n\n".join(lines)

    # ── Fallback: text-field display (no verified data) ──────────────────────
    headline = ret_text.split("(")[0].strip()
    lines    = [f"**Return at IPO: {headline}**", ""]
    lines.append(f"**Entry Valuation:** {entry_val}")
    if ipo_price:
        lines.append(f"**IPO Issue Price:** ₹{ipo_price}/share")
    if list_price:
        lines.append(f"**Listing Price:** ₹{list_price}/share")
    paren_m = re.search(r'\(([^)]{10,})\)', ret_text)
    if paren_m:
        lines.append(f"*{paren_m.group(1)}*")
    lines.append("")
    lines.append(f"**Round:** {round_str}")
    lines.append("**Source:** Public VC disclosures / NSE-BSE filings")
    lines.append("*Exact per-share entry price not yet in verified database.*")
    return "\n\n".join(lines)


def _nse_quote(symbol):
    """Fetch last price + 52w high/low from NSE equity API."""
    try:
        s = requests.Session()
        s.get("https://www.nseindia.com", headers=_NSE_HDR, timeout=6)
        r = s.get(
            f"https://www.nseindia.com/api/quote-equity?symbol={symbol}",
            headers=_NSE_HDR, timeout=8,
        )
        if r.status_code == 200:
            pi = r.json().get("priceInfo", {})
            price = pi.get("lastPrice")
            whl   = pi.get("weekHighLow", {})
            h52   = whl.get("max")
            l52   = whl.get("min")
            if price:
                return float(price), float(h52) if h52 else None, float(l52) if l52 else None
    except Exception:
        pass
    return None, None, None


def _bse_quote(symbol):
    """Fetch last price from BSE API (needs BSE scrip code — best-effort)."""
    try:
        r = requests.get(
            f"https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData/w?Scrip_cd=0&scripcode=0&seriesid=EQ&scripname={symbol}",
            headers={"User-Agent": "Mozilla/5.0"}, timeout=8,
        )
        if r.status_code == 200:
            data = r.json()
            price = data.get("CurrRate") or data.get("Ltp")
            if price:
                return float(str(price).replace(",", "")), None, None
    except Exception:
        pass
    return None, None, None


# ── Cached helpers ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def _live_price(ticker):
    """yfinance fast_info → yfinance history → NSE API → BSE API."""
    # 1. yfinance fast_info
    try:
        t  = yf.Ticker(ticker)
        fi = t.fast_info
        p  = fi.last_price
        if p and float(p) > 0:
            return float(p), fi.fifty_two_week_high, fi.fifty_two_week_low
    except Exception:
        pass

    # 2. yfinance history (last close)
    try:
        t    = yf.Ticker(ticker)
        hist = t.history(period="5d")
        if not hist.empty:
            p = float(hist["Close"].iloc[-1])
            if p > 0:
                return p, float(hist["High"].max()), float(hist["Low"].min())
    except Exception:
        pass

    # 3. NSE API (for .NS tickers)
    if ticker.endswith(".NS"):
        sym = ticker[:-3]
        p, h52, l52 = _nse_quote(sym)
        if p:
            return p, h52, l52

    # 4. BSE best-effort
    sym = ticker.replace(".NS", "").replace(".BO", "")
    p, h52, l52 = _bse_quote(sym)
    if p:
        return p, h52, l52

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



def _build_df():
    rows = []
    for ipo in IPOS:
        price, h52, l52 = _live_price(ipo["ticker"])
        ip, lp = ipo["issue_price"], ipo["listing_price"]
        ret_ipo  = round((price - ip) / ip * 100, 2) if price and ip else None
        ret_list = round((price - lp) / lp * 100, 2) if price and lp else None
        # Price ratio at CMP vs listing (used to scale all multiples)
        price_ratio = (price / lp) if (price and lp and lp > 0) else None
        # EV/Revenue
        ev_rev_listing = ipo.get("ev_rev_at_listing")
        ev_rev_now = round(ev_rev_listing * price_ratio, 1) if (ev_rev_listing and price_ratio) else None
        # P/E
        pe_listing = ipo.get("pe_at_listing")
        pe_now = round(pe_listing * price_ratio, 1) if (pe_listing and price_ratio) else None
        # P/B
        pb_listing = ipo.get("pb_at_listing")
        pb_now = round(pb_listing * price_ratio, 1) if (pb_listing and price_ratio) else None
        rows.append({
            "Company": ipo["company"],
            "Sector": ipo["sector"],
            "Listing Date": ipo["listing_date"],
            "Issue Size": ipo["issue_size"],
            "Issue Price (₹)": ip,
            "Listing Price (₹)": lp,
            "Current Price (₹)": round(price, 2) if price else None,
            "Return from IPO (%)": ret_ipo,
            "Return from Listing (%)": ret_list,
            "Listing MCap (₹ Cr)": ipo.get("listing_mcap_cr"),
            "Revenue (₹ Cr)": ipo.get("revenue_cr"),
            "EV/Rev (listing)": ev_rev_listing,
            "EV/Rev (CMP)": ev_rev_now,
            "P/E at Listing": pe_listing,
            "P/E at CMP": pe_now,
            "P/B at Listing": pb_listing,
            "P/B at CMP": pb_now,
        })
    return pd.DataFrame(rows)


# ── Lock-Up Expiry helpers ────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def _hist_prices(ticker, start, end):
    """Fetch OHLC history from yfinance for price impact chart."""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        df = t.history(start=start, end=end, auto_adjust=True)
        if not df.empty:
            df.index = df.index.tz_localize(None)
            return df[["Close"]].copy()
    except Exception:
        pass
    return None


def _combined_lockup_chart(ticker, listing_dt, expiry_lines_full, ipo_company):
    """Single chart: full price history from listing with all expiry lines + 7/30-day impact table.

    expiry_lines_full: list of (datetime, label_str, hex_color)
    """
    try:
        start = listing_dt.strftime("%Y-%m-%d")
        today = datetime.now().strftime("%Y-%m-%d")
        df_p = _hist_prices(ticker, start, today)
        if df_p is None or df_p.empty:
            return False

        df_p.index = pd.to_datetime(df_p.index)
        x_str = df_p.index.strftime("%Y-%m-%d").tolist()

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x_str,
            y=df_p["Close"].tolist(),
            mode="lines", name="Price",
            line=dict(color="#1e40af", width=2),
            fill="tozeroy", fillcolor="rgba(29,78,216,0.06)",
        ))

        # Draw all expiry lines (anchor T1, T2, pre-IPO, promoter…)
        for exp_dt, exp_lbl, exp_color in expiry_lines_full:
            exp_str = exp_dt.strftime("%Y-%m-%d")
            # Only draw if within 2 years of today (keeps chart readable)
            if exp_dt <= datetime.now() + timedelta(days=730):
                fig.add_shape(
                    type="line",
                    x0=exp_str, x1=exp_str,
                    y0=0, y1=1,
                    xref="x", yref="paper",
                    line=dict(color=exp_color, dash="dash", width=1.5),
                )
                fig.add_annotation(
                    x=exp_str, y=0.97,
                    xref="x", yref="paper",
                    text=f"🔓 {exp_lbl}",
                    showarrow=False,
                    font=dict(color=exp_color, size=10),
                    xanchor="left",
                    bgcolor="rgba(255,255,255,0.75)",
                )

        fig.update_layout(
            height=300, margin=dict(l=0, r=0, t=30, b=0),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, color="#a38060"),
            yaxis=dict(showgrid=True, gridcolor="#e5e7eb", color="#a38060", title="Price (₹)"),
            showlegend=False,
            title=dict(text="Price History with Lock-Up Expiry Lines", font=dict(size=13, color="#1a0f00"), x=0.01),
        )
        st.plotly_chart(fig, use_container_width=True)

        # ── Price impact table: −7d→expiry | 7d | −7d→+7d | 30d ──────
        # Helper: find nearest trading-day price in df_p
        def _nearest_price(target_dt, search_back=True, max_days=7):
            """Return Close price nearest to target_dt; search backward if search_back else forward."""
            for i in range(max_days + 1):
                delta = timedelta(days=i if not search_back else -i) if i > 0 else timedelta(0)
                check = target_dt + (timedelta(days=i) if not search_back else timedelta(days=-i))
                mask = df_p.index.date == check.date()
                if mask.any():
                    return float(df_p.loc[mask, "Close"].iloc[0])
            return None

        def _pct(p1, p2):
            if p1 and p2 and p1 > 0:
                return round((p2 - p1) / p1 * 100, 1)
            return None

        def _fmt(v):
            if v is None:
                return "N/A"
            return f"{v:+.1f}%"

        # Raw numeric rows for insight generation
        _raw_impact_rows = []
        impact_rows = []
        for exp_dt, exp_lbl, _ in expiry_lines_full:
            if exp_dt > datetime.now():
                _raw_impact_rows.append({
                    "Lock-Up": exp_lbl, "status": "pending",
                    "minus7_to_expiry": None, "day7_impact": None,
                    "minus7_to_plus7": None, "day30_impact": None,
                })
                impact_rows.append({
                    "Lock-Up": exp_lbl,
                    "−7d to Expiry": "—",
                    "7-Day Impact":  "—",
                    "−7d to +7d":   "—",
                    "30-Day Impact": "—",
                    "Status": "⏳ Pending",
                })
                continue
            try:
                # Reference prices
                p_minus7     = _nearest_price(exp_dt - timedelta(days=7),  search_back=True)
                p_day_before = _nearest_price(exp_dt - timedelta(days=1),  search_back=True)
                p_at_expiry  = _nearest_price(exp_dt,                      search_back=False)
                p_plus7      = _nearest_price(exp_dt + timedelta(days=7),  search_back=False)
                p_plus30     = _nearest_price(exp_dt + timedelta(days=30), search_back=False)

                m7e  = _pct(p_minus7,     p_at_expiry)   # −7d → expiry
                d7   = _pct(p_day_before, p_plus7)        # day before → +7d
                m7p7 = _pct(p_minus7,     p_plus7)        # −7d → +7d
                d30  = _pct(p_day_before, p_plus30)       # day before → +30d

                _raw_impact_rows.append({
                    "Lock-Up": exp_lbl, "status": "expired",
                    "minus7_to_expiry": m7e, "day7_impact": d7,
                    "minus7_to_plus7": m7p7, "day30_impact": d30,
                })
                impact_rows.append({
                    "Lock-Up": exp_lbl,
                    "−7d to Expiry": _fmt(m7e),
                    "7-Day Impact":  _fmt(d7),
                    "−7d to +7d":   _fmt(m7p7),
                    "30-Day Impact": _fmt(d30),
                    "Status": "✅ Expired",
                })
            except Exception:
                _raw_impact_rows.append({
                    "Lock-Up": exp_lbl, "status": "expired",
                    "minus7_to_expiry": None, "day7_impact": None,
                    "minus7_to_plus7": None, "day30_impact": None,
                })
                impact_rows.append({
                    "Lock-Up": exp_lbl,
                    "−7d to Expiry": "N/A",
                    "7-Day Impact":  "N/A",
                    "−7d to +7d":   "N/A",
                    "30-Day Impact": "N/A",
                    "Status": "✅ Expired",
                })

        _IMPACT_COLS = ["−7d to Expiry", "7-Day Impact", "−7d to +7d", "30-Day Impact"]

        def _impact_color(val):
            v = str(val)
            if v.startswith("+"):
                return "color:#16a34a;font-weight:600"
            if v.startswith("-"):
                return "color:#dc2626;font-weight:600"
            return "color:#6b7a8d"

        impact_df = pd.DataFrame(impact_rows)
        styled_impact = impact_df.style.map(_impact_color, subset=_IMPACT_COLS)

        # Column header tooltips via HTML above the table
        _t1 = "Price change from 7 calendar days before expiry to the expiry date. Shows whether investors sold ahead of the unlock."
        _t2 = "Price change from the day before expiry to 7 trading days after. Shows immediate post-unlock impact."
        _t3 = "Price change from 7 days before expiry to 7 days after. Shows the full event-window impact."
        _t4 = "Price change from the day before expiry to 30 days after. Shows medium-term post-unlock impact."
        _tooltip_html = (
            "<div style='font-size:11px;color:#6b7a8d;margin:10px 0 2px;line-height:1.8'>"
            "<b>Price impact around lock-in expiry</b> &nbsp;|&nbsp; "
            f"<span title='{_t1}' style='cursor:help;border-bottom:1px dotted #6b7a8d'>−7d to Expiry &#9432;</span>"
            " &nbsp;&middot;&nbsp; "
            f"<span title='{_t2}' style='cursor:help;border-bottom:1px dotted #6b7a8d'>7-Day Impact &#9432;</span>"
            " &nbsp;&middot;&nbsp; "
            f"<span title='{_t3}' style='cursor:help;border-bottom:1px dotted #6b7a8d'>−7d to +7d &#9432;</span>"
            " &nbsp;&middot;&nbsp; "
            f"<span title='{_t4}' style='cursor:help;border-bottom:1px dotted #6b7a8d'>30-Day Impact &#9432;</span>"
            "</div>"
        )
        st.markdown(_tooltip_html, unsafe_allow_html=True)
        st.dataframe(styled_impact, use_container_width=True, hide_index=True)

        # ── Auto-generated insight ────────────────────────────────────
        _expired_raw = [r for r in _raw_impact_rows if r["status"] == "expired"
                        and r["minus7_to_plus7"] is not None]
        if _expired_raw:
            _most = max(_expired_raw, key=lambda r: abs(r["minus7_to_plus7"]))
            _dir  = "fell" if _most["minus7_to_plus7"] < 0 else "rose"
            _pabs = abs(_most["minus7_to_plus7"])
            _insight = (
                f"The most significant unlock for **{ipo_company}** was the "
                f"**{_most['Lock-Up']}** expiry, around which the stock "
                f"**{_dir} {_pabs:.1f}%** over the 14-day window (−7d to +7d)."
            )
            # Pre-IPO specific add-on
            _pripo_raw = [r for r in _expired_raw if "Pre-IPO" in r["Lock-Up"]
                          and r["minus7_to_expiry"] is not None]
            if _pripo_raw:
                _pr = _pripo_raw[0]
                _run_dir = "up" if _pr["minus7_to_expiry"] > 0 else "down"
                _insight += (
                    f" Pre-IPO investor unlock saw the stock move "
                    f"**{_run_dir} {abs(_pr['minus7_to_expiry']):.1f}%** "
                    f"in the 7 days leading into expiry."
                )
            st.info(_insight)

        return True
    except Exception:
        return False


def _lockup_price_chart(ticker, expiry_dt, label, ipo_company):
    """Show price chart ±30 days around a lock-up expiry date."""
    try:
        start = (expiry_dt - timedelta(days=10)).strftime("%Y-%m-%d")
        end   = (expiry_dt + timedelta(days=35)).strftime("%Y-%m-%d")
        df_p = _hist_prices(ticker, start, end)
        if df_p is None or df_p.empty:
            st.caption(f"Price history unavailable for {ticker}.")
            return

        # Convert expiry_dt to string — avoids Plotly datetime compat issues on Cloud
        expiry_str = expiry_dt.strftime("%Y-%m-%d")

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_p.index.strftime("%Y-%m-%d"),
            y=df_p["Close"],
            mode="lines", name="Price",
            line=dict(color="#1e40af", width=2),
        ))

        # Draw expiry line as a shape + annotation (avoids add_vline compat issues)
        fig.add_shape(
            type="line",
            x0=expiry_str, x1=expiry_str,
            y0=0, y1=1,
            xref="x", yref="paper",
            line=dict(color="#dc2626", dash="dash", width=2),
        )
        fig.add_annotation(
            x=expiry_str, y=0.95, xref="x", yref="paper",
            text=f"🔓 {label}",
            showarrow=False,
            font=dict(color="#dc2626", size=11),
            xanchor="left",
        )

        # Compute price changes around expiry
        try:
            df_idx = df_p.copy()
            df_idx.index = pd.to_datetime(df_idx.index)
            exp_ts = pd.Timestamp(expiry_dt)
            prices_before = df_idx[df_idx.index <= exp_ts]["Close"]
            prices_after  = df_idx[df_idx.index >= exp_ts]["Close"]
            if not prices_before.empty and not prices_after.empty:
                p_before = prices_before.iloc[-1]
                p_30d    = prices_after.iloc[min(21, len(prices_after)-1)]
                chg_30   = round((p_30d - p_before) / p_before * 100, 1) if p_before else None
                chg_dir  = "fell" if (chg_30 or 0) < 0 else "rose"
                if chg_30 is not None:
                    st.markdown(
                        f"<div style='background:#fef3cd;border:1px solid #ffc107;border-radius:6px;"
                        f"padding:6px 12px;font-size:12px;margin-bottom:4px'>"
                        f"Stock <b>{chg_dir} {abs(chg_30):.1f}%</b> in 30 days after {label} expired.</div>",
                        unsafe_allow_html=True)
        except Exception:
            pass

        fig.update_layout(
            height=220, margin=dict(l=0, r=0, t=20, b=0),
            xaxis_title=None, yaxis_title="Price (₹)",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.caption(f"Chart unavailable for {label}: {e}")


def _render_lockup_tab(ipo):
    """Render the full Lock-Up Expiry Analysis tab for a given IPO."""
    st.markdown("#### 🔒 Lock-Up Expiry Analysis")
    ticker     = ipo.get("ticker", "")
    listing_str = ipo.get("listing_date", "")
    issue_size  = ipo.get("issue_size_cr", 0) or 0
    anchors     = ipo.get("anchors", [])
    pripo       = ipo.get("pripo_investors", [])
    company     = ipo.get("company", "")

    # Parse listing date
    listing_dt = None
    try:
        listing_dt = datetime.strptime(listing_str, "%Y-%m-%d")
    except Exception:
        pass

    if not listing_dt:
        st.info("Listing date not available — cannot compute lock-up expiry dates.")
        return

    today = datetime.now(pytz.timezone("Asia/Kolkata")).replace(tzinfo=None)

    # ── Look up verified lock-in dates from LOCK_IN_DATES dict ─────────────
    lid = LOCK_IN_DATES.get(company, {})

    def _parse_lid(key, fallback_days):
        """Parse a date string from LOCK_IN_DATES, or fall back to listing_dt + days."""
        s = lid.get(key)
        if s:
            try:
                return datetime.strptime(s, "%Y-%m-%d")
            except Exception:
                pass
        return listing_dt + timedelta(days=fallback_days)

    anchor_t1_expiry  = _parse_lid("anchor_t1",    31)   # ~30d from allotment
    anchor_t2_expiry  = _parse_lid("anchor_t2",    91)   # ~90d from allotment
    pripo_expiry      = _parse_lid("pripo_6m",    182)   # 6 months from allotment
    promoter_expiry   = _parse_lid("promoter_18m", 548)  # 18 months from allotment
    promoter3y_expiry = _parse_lid("promoter_3y", 1095)  # 3 years from allotment
    allotment_str     = lid.get("allotment", "")

    def _status(dt):
        if dt <= today:
            return f"✅ Expired ({dt.strftime('%d %b %Y')})"
        diff = (dt - today).days
        return f"⏳ In {diff} days ({dt.strftime('%d %b %Y')})"

    def _risk(dt, pct):
        if dt > today and pct and pct > 10:
            return "🔴 High Risk"
        if dt > today:
            return "🟡 Watch"
        return "—"

    anchor_pct = round(100 * (ipo.get("anchor_total_cr", 0) or 0) / (issue_size or 1), 1)
    pripo_pct  = 15.0   # pre-IPO investors ~15% of post-issue shares (approximate)
    promo_pct  = 35.0   # promoter pre-locked stake (80% tranche) — approximate

    anchor_names = (
        ", ".join(a.get("investor", "") for a in anchors[:3])
        + ("…" if len(anchors) > 3 else "")
    )
    pripo_names = (
        ", ".join(p.get("investor", "").split("(")[0].strip() for p in pripo[:3])
        + ("…" if len(pripo) > 3 else "")
    )

    lockup_rows = [
        {
            "Lock-Up Type": "Anchor — Tranche 1 (30d)",
            "Who": anchor_names,
            "Expiry Date": anchor_t1_expiry.strftime("%d %b %Y"),
            "~% of Shares": f"~{anchor_pct}%",
            "Status": _status(anchor_t1_expiry),
            "Risk": _risk(anchor_t1_expiry, anchor_pct),
        },
        {
            "Lock-Up Type": "Anchor — Tranche 2 (90d)",
            "Who": anchor_names,
            "Expiry Date": anchor_t2_expiry.strftime("%d %b %Y"),
            "~% of Shares": f"~{anchor_pct / 2:.1f}%",
            "Status": _status(anchor_t2_expiry),
            "Risk": _risk(anchor_t2_expiry, anchor_pct / 2),
        },
        {
            "Lock-Up Type": "Pre-IPO Investors (6M)",
            "Who": pripo_names,
            "Expiry Date": pripo_expiry.strftime("%d %b %Y"),
            "~% of Shares": f"~{pripo_pct}%",
            "Status": _status(pripo_expiry),
            "Risk": _risk(pripo_expiry, pripo_pct),
        },
        {
            "Lock-Up Type": "Promoters (18M — 80% of stake)",
            "Who": "Promoter group",
            "Expiry Date": promoter_expiry.strftime("%d %b %Y"),
            "~% of Shares": f"~{promo_pct}%",
            "Status": _status(promoter_expiry),
            "Risk": _risk(promoter_expiry, promo_pct),
        },
        {
            "Lock-Up Type": "Promoters (3Y — remaining 20%)",
            "Who": "Promoter group",
            "Expiry Date": promoter3y_expiry.strftime("%d %b %Y"),
            "~% of Shares": f"~{round(promo_pct * 0.25, 1)}%",
            "Status": _status(promoter3y_expiry),
            "Risk": "—",
        },
    ]
    st.dataframe(pd.DataFrame(lockup_rows), use_container_width=True, hide_index=True)

    allotment_note = f" Allotment date: {allotment_str}." if allotment_str else ""
    st.caption(
        "SEBI ICDR rules: Anchor T1 — 30 days from allotment (50% of anchor allocation); "
        "Anchor T2 — 90 days from allotment (remaining 50%). "
        "Pre-IPO investors (held >1yr before DRHP) — 6 months from allotment. "
        "Promoters — 80% stake locked for 18 months, remaining 20% for 3 years from allotment."
        f"{allotment_note} "
        "% figures are approximate estimates. "
        "Lock-in dates from RHP and BSE disclosures."
    )

    # ── Combined price chart with all expiry lines ───────────────────────────
    st.markdown("---")
    st.markdown("#### 📉 Lock-Up Expiry — Price History & Impact")

    # (datetime, label, color) — ordered chronologically
    all_expiry_lines = [
        (anchor_t1_expiry,  "Anchor T1 (30d)",       "#f59e0b"),
        (anchor_t2_expiry,  "Anchor T2 (90d)",       "#f97316"),
        (pripo_expiry,      "Pre-IPO (6M)",           "#7c3aed"),
        (promoter_expiry,   "Promoter (18M)",         "#dc2626"),
    ]

    upcoming_expiries = [(dt, lbl) for dt, lbl, _ in all_expiry_lines if dt > today]
    passed_expiries   = [(dt, lbl) for dt, lbl, _ in all_expiry_lines if dt <= today]

    combined_ok = _combined_lockup_chart(
        ticker, listing_dt,
        all_expiry_lines,
        ipo["company"],
    )

    # Upcoming expiry warning banners
    if upcoming_expiries:
        price_now, _, _ = _live_price(ticker)
        for exp_dt, exp_lbl in upcoming_expiries:
            days_left = (exp_dt - today).days
            if "Anchor" in exp_lbl:
                val_est_cr = ipo.get("anchor_total_cr") or 0
            else:
                val_est_cr = round((ipo.get("listing_mcap_cr") or 0) * 0.15, 0)
            risk_col = "#fee2e2" if days_left < 30 else "#fef3cd"
            risk_brd = "#dc2626" if days_left < 30 else "#ffc107"
            risk_txt = "🔴 HIGH RISK — expiry imminent" if days_left < 30 else "🟡 Watch"
            st.markdown(
                f"""<div style='background:{risk_col};border:1px solid {risk_brd};
                border-radius:8px;padding:10px 14px;margin-bottom:8px;font-size:13px'>
                <b>{risk_txt}</b> &nbsp;|&nbsp; <b>{exp_lbl}</b> expires in
                <b>{days_left} days</b> ({exp_dt.strftime('%d %b %Y')})<br/>
                Est. unlock value: <b>~₹{int(val_est_cr):,} cr</b>
                {"at current price ₹" + f"{price_now:.1f}" if price_now else ""}
                </div>""",
                unsafe_allow_html=True)

    if passed_expiries and not combined_ok:
        for exp_dt, exp_lbl in passed_expiries:
            st.markdown(f"**Price around {exp_lbl} expiry ({exp_dt.strftime('%d %b %Y')})**")
            _lockup_price_chart(ticker, exp_dt, exp_lbl, ipo["company"])
    elif not combined_ok and not passed_expiries:
        st.info("No lock-up periods have expired yet for this IPO. Charts will appear after each expiry.")

    st.markdown(f'<div style="color:#a38060;font-size:11px;text-align:right">Last updated: {_now_ist()}</div>',
                unsafe_allow_html=True)


# ── Render ─────────────────────────────────────────────────────────────────────
def render():
    st_autorefresh(interval=900_000, key="recent_ipo_refresh")

    render_z47_assistant(
        context="recent_ipos",
        label="💬 Ask Z47 Assistant",
        extra_context="User is viewing recent Indian new-age tech and fintech IPO data "
                      "including performance, valuations, anchor investors and lock-up analysis.",
    )

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
        sort_col = st.selectbox("Sort by", ["Listing Date", "Return from IPO (%)", "Issue Size", "EV/Rev (listing)"],
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
        elif sort_col == "EV/Rev (listing)":
            df = df.sort_values("EV/Rev (listing)", ascending=False)
    except Exception:
        pass

    def _color(val):
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return ""
        return "color:#16a34a;font-weight:600" if val >= 0 else "color:#dc2626;font-weight:600"

    # ── Table 1: Price performance (keep compact — only price/return cols) ────
    perf_cols = ["Company", "Sector", "Listing Date", "Issue Price (₹)",
                 "Listing Price (₹)", "Current Price (₹)",
                 "Return from IPO (%)", "Return from Listing (%)"]
    styled = df[perf_cols].style.map(_color, subset=["Return from IPO (%)", "Return from Listing (%)"])
    st.dataframe(styled, use_container_width=True, height=400, hide_index=True,
                 column_config={
                     "Issue Price (₹)":        st.column_config.NumberColumn(format="₹%.2f"),
                     "Listing Price (₹)":       st.column_config.NumberColumn(format="₹%.2f"),
                     "Current Price (₹)":       st.column_config.NumberColumn(format="₹%.2f"),
                     "Return from IPO (%)":     st.column_config.NumberColumn(format="%.2f%%"),
                     "Return from Listing (%)": st.column_config.NumberColumn(format="%.2f%%"),
                 })

    # ── Table 2: Valuation Multiples (always visible, dedicated section) ─────
    st.markdown(
        f"""<div style='background:{CARD_BG};border:1px solid {BORDER};border-radius:8px;
        padding:8px 16px;margin:16px 0 6px'>
        <b style='color:#1e40af;font-size:14px'>📊 Valuation Multiples at Listing</b>
        <span style='color:#6b7a8d;font-size:12px;margin-left:10px'>
        EV/Revenue · P/E · P/B — at listing day and at current price</span></div>""",
        unsafe_allow_html=True)

    val_cols = ["Company", "Listing MCap (₹ Cr)",
                "EV/Rev (listing)", "P/E at Listing", "P/B at Listing",
                "EV/Rev (CMP)",     "P/E at CMP",     "P/B at CMP"]
    val_df = df[val_cols].copy()

    _listing_cols = ["EV/Rev (listing)", "P/E at Listing", "P/B at Listing"]
    _cmp_cols     = ["EV/Rev (CMP)",     "P/E at CMP",     "P/B at CMP"]

    def _listing_color(val):
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return ""
        return "color:#1e40af;font-weight:600"   # blue  — Listing

    def _cmp_color(val):
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return ""
        return "color:#b45309;font-weight:600"   # amber — CMP

    val_styled = (val_df.style
                  .map(_listing_color, subset=_listing_cols)
                  .map(_cmp_color,     subset=_cmp_cols))

    st.dataframe(val_styled, use_container_width=True, height=400, hide_index=True,
                 column_config={
                     "Listing MCap (₹ Cr)": st.column_config.NumberColumn(format="₹%d cr"),
                     "EV/Rev (listing)":    st.column_config.NumberColumn("EV/Rev (Listing) 🔵", format="%.1fx"),
                     "EV/Rev (CMP)":        st.column_config.NumberColumn("EV/Rev (CMP) 🟠",     format="%.1fx"),
                     "P/E at Listing":      st.column_config.NumberColumn("P/E (Listing) 🔵",    format="%.1fx"),
                     "P/E at CMP":          st.column_config.NumberColumn("P/E (CMP) 🟠",        format="%.1fx"),
                     "P/B at Listing":      st.column_config.NumberColumn("P/B (Listing) 🔵",    format="%.1fx"),
                     "P/B at CMP":          st.column_config.NumberColumn("P/B (CMP) 🟠",        format="%.1fx"),
                 })
    st.markdown(
        "<span style='font-size:11px;color:#6b7a8d'>"
        "<b style='color:#1e40af'>🔵 Blue = At Listing</b> &nbsp;|&nbsp; "
        "<b style='color:#b45309'>🟠 Amber = At CMP (current price)</b> &nbsp;|&nbsp; "
        "EV = MCap + Debt − Cash &nbsp;|&nbsp; P/E only for profitable cos &nbsp;|&nbsp; "
        "P/B only for financial-services cos</span>",
        unsafe_allow_html=True)

    st.markdown(f'<div style="color:#a38060;font-size:11px;text-align:right">Last updated: {_now_ist()}</div>',
                unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Deep Dive — Select an IPO")
    selected = st.selectbox("Select IPO", [i["company"] for i in IPOS], key="ri_deep")
    ipo = next(i for i in IPOS if i["company"] == selected)

    t1, t2, t4, t5, t6 = st.tabs(["📋 Overview", "📊 Performance", "📬 Subscription", "🏦 Investors", "🔒 Lock-Up Analysis"])

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

        # Listing Day Gain — first item in Performance
        ldg_pct = ipo.get("known_listing_gain_pct")
        if ldg_pct is not None:
            ldg_color = "#16a34a" if ldg_pct >= 0 else "#dc2626"
            st.markdown(
                f"""<div style='background:{CARD_BG};border:1px solid {BORDER};border-radius:8px;
                padding:10px 16px;font-size:15px;margin-bottom:12px'>
                🏁 <b>Listing Day Gain:</b>
                <b style='color:{ldg_color}'>{ldg_pct:+.1f}%</b>
                over issue price</div>""",
                unsafe_allow_html=True)

        m1, m2, m3, m4 = st.columns(4)
        with m1: st.metric("Current Price", f"₹{price:.2f}" if price else "N/A")
        with m2: st.metric("Listing Price", f"₹{lp:.2f}" if lp else "N/A")
        with m3:
            ret = round((price - ip) / ip * 100, 2) if price and ip else None
            st.metric("Return from IPO", f"{ret:+.2f}%" if ret is not None else "N/A")
        with m4:
            st.metric("52W High / Low", f"₹{h52:.0f} / ₹{l52:.0f}" if h52 and l52 else "N/A")

        st.markdown("---")
        # ── Valuation multiples ──────────────────────────────────────────────
        st.markdown(
            f"""<div style='background:{CARD_BG};border:1px solid {BORDER};border-radius:8px;
            padding:8px 14px;margin-bottom:8px'>
            <b style='color:#1e40af;font-size:14px'>📊 Valuation Multiples</b>
            <span style='color:#6b7a8d;font-size:12px;margin-left:10px'>
            EV/Revenue, P/E and P/B at listing day vs current price</span></div>""",
            unsafe_allow_html=True)
        listing_mcap   = ipo.get("listing_mcap_cr")
        rev_cr         = ipo.get("revenue_cr")
        rev_yr         = ipo.get("revenue_year", "")
        profitable     = ipo.get("profitable")
        ev_rev_listing = ipo.get("ev_rev_at_listing")
        pe_listing     = ipo.get("pe_at_listing")
        pb_listing     = ipo.get("pb_at_listing")
        pat_cr         = ipo.get("pat_cr")
        bv_cr          = ipo.get("book_value_cr")

        price_ratio    = (price / lp) if (price and lp and lp > 0) else None
        ev_rev_now = round(ev_rev_listing * price_ratio, 1) if (ev_rev_listing and price_ratio) else None
        pe_now     = round(pe_listing     * price_ratio, 1) if (pe_listing     and price_ratio) else None
        pb_now     = round(pb_listing     * price_ratio, 1) if (pb_listing     and price_ratio) else None

        # Row 1 — MCap & financials context
        v1, v2, v3, v4 = st.columns(4)
        with v1:
            st.metric("Listing MCap", f"₹{listing_mcap:,} cr" if listing_mcap else "N/A")
        with v2:
            st.metric(f"Revenue ({rev_yr})", f"₹{rev_cr:,} cr" if rev_cr else "N/A",
                      help="Annual revenue used for EV/Revenue calculation")
        with v3:
            st.metric(f"PAT ({rev_yr})", f"₹{pat_cr:,} cr" if pat_cr else "N/A",
                      help="Profit After Tax used for P/E calculation")
        with v4:
            st.metric(f"Book Value ({rev_yr})", f"₹{bv_cr:,} cr" if bv_cr else "N/A",
                      help="Net Worth / Book Value — shown for financial services companies")

        # Row 2 — Multiples at Listing
        is_insurer = "insurance" in ipo.get("sector", "").lower() or "digit" in ipo.get("company", "").lower()
        ev_rev_label = "P/NEP (listing)" if is_insurer else "EV/Revenue (listing)"
        ev_rev_help  = ("MCap ÷ Net Earned Premium at listing day (standard insurer metric)"
                        if is_insurer else
                        "EV ÷ Annual Revenue at listing day  |  EV = MCap + Debt − Cash")
        st.markdown("<div style='font-size:12px;color:#6b7a8d;margin:8px 0 2px'>Multiples at Listing Day</div>",
                    unsafe_allow_html=True)
        p1, p2, p3, _gap = st.columns([1, 1, 1, 1])
        with p1:
            st.metric(ev_rev_label, f"{ev_rev_listing:.1f}x" if ev_rev_listing else "N/A",
                      help=ev_rev_help)
            if ev_rev_listing and listing_mcap and rev_cr:
                with st.popover("See Calculation"):
                    st.markdown(f"**{'P/NEP' if is_insurer else 'EV/Revenue'} at Listing**")
                    st.markdown(f"- Listing MCap: **₹{listing_mcap:,} cr**")
                    st.markdown(f"- Revenue ({rev_yr}): **₹{rev_cr:,} cr**")
                    st.markdown(f"- EV ≈ MCap (debt/cash adjustment minimal)")
                    st.markdown(f"- **{ev_rev_listing:.1f}x** = ₹{listing_mcap:,} ÷ ₹{rev_cr:,}")
        with p2:
            pe_warn = " ⚠" if ipo.get("company") == "Urban Company" else ""
            st.metric("P/E at Listing",
                      (f"{pe_listing:.1f}x{pe_warn}" if pe_listing else
                       ("Loss-making" if profitable is False else "N/A")),
                      help=("Market Cap ÷ PAT at listing day (only for profitable companies). "
                            "⚠ Urban Company PAT includes ₹211 cr one-time deferred tax credit; "
                            "underlying PBT was ~₹29 cr." if pe_warn else
                            "Market Cap ÷ PAT at listing day (only for profitable companies)"))
            if pe_listing and listing_mcap and pat_cr:
                with st.popover("See Calculation"):
                    st.markdown("**P/E at Listing**")
                    st.markdown(f"- Listing MCap: **₹{listing_mcap:,} cr**")
                    st.markdown(f"- PAT ({rev_yr}): **₹{pat_cr:,} cr**")
                    st.markdown(f"- **{pe_listing:.1f}x** = ₹{listing_mcap:,} ÷ ₹{pat_cr:,}")
                    if pe_warn:
                        st.warning("⚠ Urban Company PAT includes ₹211 cr one-time deferred tax credit; underlying PBT ~₹29 cr.")
        with p3:
            st.metric("P/B at Listing",
                      f"{pb_listing:.1f}x" if pb_listing else "N/A",
                      help="Market Cap ÷ Book Value at listing day (financial services companies only)")
            if pb_listing and listing_mcap and bv_cr:
                with st.popover("See Calculation"):
                    st.markdown("**P/B at Listing**")
                    st.markdown(f"- Listing MCap: **₹{listing_mcap:,} cr**")
                    st.markdown(f"- Book Value ({rev_yr}): **₹{bv_cr:,} cr**")
                    st.markdown(f"- **{pb_listing:.1f}x** = ₹{listing_mcap:,} ÷ ₹{bv_cr:,}")

        # Row 3 — Multiples at CMP
        ev_rev_cmp_label = "P/NEP (CMP)" if is_insurer else "EV/Revenue (CMP)"
        st.markdown("<div style='font-size:12px;color:#6b7a8d;margin:8px 0 2px'>Multiples at Current Price</div>",
                    unsafe_allow_html=True)
        q1, q2, q3, _gap2 = st.columns([1, 1, 1, 1])
        with q1:
            delta_evr = f"{(ev_rev_now - ev_rev_listing):+.1f}x" if (ev_rev_now and ev_rev_listing) else None
            st.metric(ev_rev_cmp_label, f"{ev_rev_now:.1f}x" if ev_rev_now else "N/A", delta=delta_evr)
            if ev_rev_now and price and lp and rev_cr:
                cmp_mcap = round(listing_mcap * price / lp, 0) if (listing_mcap and lp and lp > 0) else None
                with st.popover("See Calculation"):
                    st.markdown(f"**{'P/NEP' if is_insurer else 'EV/Revenue'} at CMP**")
                    st.markdown(f"- Current Price: **₹{price:.2f}**")
                    st.markdown(f"- Listing Price: **₹{lp:.2f}**  →  Price ratio: **{price/lp:.3f}x**")
                    if cmp_mcap:
                        st.markdown(f"- CMP MCap ≈ **₹{int(cmp_mcap):,} cr** (listing MCap × ratio)")
                    st.markdown(f"- Revenue ({rev_yr}): **₹{rev_cr:,} cr**")
                    st.markdown(f"- **{ev_rev_now:.1f}x** = {ev_rev_listing:.1f}x (listing) × {price/lp:.3f}")
        with q2:
            delta_pe = f"{(pe_now - pe_listing):+.1f}x" if (pe_now and pe_listing) else None
            st.metric("P/E at CMP",
                      f"{pe_now:.1f}x" if pe_now else ("Loss-making" if profitable is False else "N/A"),
                      delta=delta_pe)
            if pe_now and pat_cr and price and lp:
                with st.popover("See Calculation"):
                    st.markdown("**P/E at CMP**")
                    st.markdown(f"- Price ratio CMP/Listing: **{price/lp:.3f}x**")
                    st.markdown(f"- PAT ({rev_yr}): **₹{pat_cr:,} cr**")
                    st.markdown(f"- **{pe_now:.1f}x** = {pe_listing:.1f}x (listing) × {price/lp:.3f}")
        with q3:
            delta_pb = f"{(pb_now - pb_listing):+.1f}x" if (pb_now and pb_listing) else None
            st.metric("P/B at CMP", f"{pb_now:.1f}x" if pb_now else "N/A", delta=delta_pb)
            if pb_now and bv_cr and price and lp:
                with st.popover("See Calculation"):
                    st.markdown("**P/B at CMP**")
                    st.markdown(f"- Price ratio CMP/Listing: **{price/lp:.3f}x**")
                    st.markdown(f"- Book Value ({rev_yr}): **₹{bv_cr:,} cr**")
                    st.markdown(f"- **{pb_now:.1f}x** = {pb_listing:.1f}x (listing) × {price/lp:.3f}")

        if profitable is not None:
            badge_col, badge_txt = ("#d1fae5", "✅ Profitable at listing") if profitable else ("#fee2e2", "❌ Loss-making at listing")
            st.markdown(
                f"<div style='display:inline-block;background:{badge_col};border-radius:6px;"
                f"padding:4px 12px;font-size:12px;margin-top:4px'>{badge_txt}</div>",
                unsafe_allow_html=True)

        if not price:
            _warn(f"Live price unavailable for {ipo['ticker']}.")
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
        # ── Section 1: Shareholding Pattern ──────────────────────────────────
        st.markdown("#### 📊 Shareholding Pattern")
        with st.spinner("Fetching shareholding…"):
            sh_data = _fetch_shareholding(ipo["ticker"], ipo["company"])

        sh_rows     = sh_data.get("rows", [])
        sh_quarters = sh_data.get("quarters", [])
        sh_source   = sh_data.get("source", "—")

        if sh_rows:
            st.dataframe(pd.DataFrame(sh_rows), use_container_width=True, hide_index=True)
            if sh_quarters and len(sh_quarters) > 1:
                st.markdown(
                    "<div style='font-size:12px;color:#6b7a8d;margin:8px 0 4px'>"
                    "Quarter-wise trend (last 4 quarters):</div>",
                    unsafe_allow_html=True)
                qt_df = pd.DataFrame(sh_quarters)
                pct_cols = [c for c in qt_df.columns if c != "Quarter"]
                def _sh_col(val):
                    try:
                        v = float(str(val).replace("%", ""))
                        if v >= 50: return "color:#16a34a;font-weight:600"
                        if v >= 25: return "color:#1e40af;font-weight:600"
                    except Exception:
                        pass
                    return ""
                styled_qt = qt_df.style.map(_sh_col, subset=pct_cols)
                st.dataframe(styled_qt, use_container_width=True, hide_index=True)
            st.caption(f"Source: {sh_source} | Updated: {_now_ist()}")
        else:
            st.info("Fetching shareholding data… if this persists, data may not be available for this ticker yet.")

        st.markdown("---")

        # ── Section 2: Anchor Investors ───────────────────────────────────────
        st.markdown("#### ⚓ Anchor Investors")
        anchors = ipo.get("anchors", [])
        anchor_total = ipo.get("anchor_total_cr")
        if anchors:
            if anchor_total:
                st.markdown(
                    f"<div style='font-size:13px;color:#6b7a8d;margin-bottom:8px'>"
                    f"Total anchor allocation: <b>₹{anchor_total:,} cr</b> "
                    f"({round(anchor_total / (ipo['issue_size_cr'] or 1) * 100, 1)}% of issue size)</div>",
                    unsafe_allow_html=True)
            anc_df = pd.DataFrame(anchors)
            anc_df.columns = [c.replace("_", " ").title() for c in anc_df.columns]
            st.dataframe(anc_df, use_container_width=True, hide_index=True)
            st.caption("Source: NSE anchor allotment disclosures (official public filings).")

            # ── Post-Anchor Activity During Book Build ────────────────────────
            st.markdown(
                f"""<div style='background:{CARD_BG};border:1px solid {BORDER};border-radius:8px;
                padding:10px 14px;margin:12px 0 8px'>
                <b style='font-size:13px;color:#1e40af'>📈 Post-Anchor Activity During Book Build</b></div>""",
                unsafe_allow_html=True)
            qib_sub = ipo.get("qib_sub", "N/A")
            # Large QIB participants that commonly also anchor
            large_qib_funds = ["BlackRock", "Fidelity", "GIC", "Government of Singapore",
                                "Mirae Asset", "HDFC MF", "SBI MF", "ICICI Pru", "Nippon India",
                                "Goldman Sachs MF", "Kotak MF"]
            anchor_names = [a.get("investor", "") for a in anchors]
            strong_conviction = [a for a in anchor_names
                                 if any(f.lower() in a.lower() for f in large_qib_funds)]
            if strong_conviction:
                badges = " ".join(
                    f"<span style='background:#d1fae5;color:#065f46;border-radius:5px;"
                    f"padding:2px 8px;font-size:11px;font-weight:600;margin:2px'>✅ Strong Conviction: {f}</span>"
                    for f in strong_conviction[:5]
                )
                st.markdown(
                    f"<div style='margin-bottom:8px'>{badges}</div>",
                    unsafe_allow_html=True)
            st.markdown(
                f"""<div style='background:{BG_ALT};border-radius:6px;padding:10px 14px;font-size:13px'>
                <b>QIB Oversubscription: {qib_sub}</b><br/>
                <span style='color:#6b7a8d'>When anchor investors also subscribe in the QIB portion during
                the main book build, it signals strong conviction — they are buying beyond their guaranteed
                anchor allocation. Funds marked <b style='color:#065f46'>Strong Conviction</b> above are
                major QIB participants who typically add in book build when bullish.
                Granular per-fund QIB data is not publicly disclosed by NSE/BSE.</span></div>""",
                unsafe_allow_html=True)
        else:
            st.markdown(
                f"<div style='background:{BG_ALT};border:1px solid {BORDER};border-radius:8px;"
                f"padding:12px;color:#6b7a8d;font-size:13px'>"
                f"Anchor investor data not available for this IPO.</div>",
                unsafe_allow_html=True)

        st.markdown("---")

        # ── Section 3: Pre-IPO Investors & Returns ────────────────────────────
        st.markdown("#### 💰 Pre-IPO Investors & Returns")
        pripo = ipo.get("pripo_investors", [])
        _ipo_px  = ipo.get("issue_price")
        _list_px = ipo.get("listing_price")
        _company = ipo.get("company", "")

        _is_upcoming = (not _ipo_px)   # price band not yet announced

        if pripo and (_ipo_px or _is_upcoming):

            # ── Upcoming IPO: scenario table (no price yet) ───────────────────
            if _is_upcoming:
                _v2_up = VERIFIED_INVESTOR_DATA.get(_company)
                if _v2_up:
                    st.info(
                        f"**{_company} — IPO price band not yet announced.**  "
                        f"WACA figures from RHP, certified by {_v2_up.get('ca_firm','CA')}.  "
                        f"Projected returns shown at price scenarios below."
                    )
                    _scenarios = [100, 200, 300, 400, 500, 600, 700, 800]
                    _inv_rows = [
                        inv for inv in _v2_up.get("investors", {}).values()
                        if inv.get("waca") and inv.get("waca", 0) > 0.01
                        and inv.get("type") != "promoter"
                    ]
                    if _inv_rows:
                        _hdr = ["**Investor**", "**WACA (₹/sh)**"] + [f"**₹{s}**" for s in _scenarios]
                        _cols_s = st.columns([2.2, 1.2] + [0.9] * len(_scenarios))
                        for _c, _h in zip(_cols_s, _hdr):
                            _c.markdown(_h)
                        st.markdown(
                            "<hr style='margin:2px 0 6px;border:none;border-top:1px solid #ccdaea'>",
                            unsafe_allow_html=True)
                        for _inv_key, _inv_v in _v2_up.get("investors", {}).items():
                            _w2 = _inv_v.get("waca")
                            if not _w2 or _w2 <= 0 or _inv_v.get("type") == "promoter":
                                continue
                            _inv_s_cols = st.columns([2.2, 1.2] + [0.9] * len(_scenarios))
                            _inv_s_cols[0].markdown(
                                f"<div style='font-size:13px;font-weight:600'>{_inv_key.split('(')[0].strip()}</div>",
                                unsafe_allow_html=True)
                            _inv_s_cols[1].markdown(
                                f"<div style='font-size:13px'>₹{_w2:,.2f}</div>",
                                unsafe_allow_html=True)
                            for _si, _sp in enumerate(_scenarios):
                                _sm = round(_sp / _w2, 1)
                                _sc = "#16a34a" if _sm >= 2 else ("#d97706" if _sm >= 1 else "#dc2626")
                                _inv_s_cols[2 + _si].markdown(
                                    f"<div style='font-size:12px;color:{_sc};font-weight:600'>"
                                    f"{_sm:.1f}×</div>",
                                    unsafe_allow_html=True)
                    # Promoters
                    _prom_rows = {k: v for k, v in _v2_up.get("investors", {}).items()
                                  if v.get("type") == "promoter" and v.get("ofs_shares")}
                    if _prom_rows:
                        st.markdown("**Promoter OFS sellers:**")
                        for _pk, _pv in _prom_rows.items():
                            _ps = _pv["ofs_shares"]
                            _proc_cols = [f"₹{round(_ps * _sp / 1e7, 0):.0f} cr" for _sp in _scenarios]
                            st.markdown(
                                f"- **{_pk}** — {_ps:,} shares × IPO price → "
                                + " / ".join(f"₹{s}: {p}" for s, p in zip(_scenarios, _proc_cols))
                            )
                    st.caption(
                        f"*WACA certified by {_v2_up.get('ca_firm','CA')} "
                        f"({_v2_up.get('ca_date','')}).  Scenarios are per-share MOIC only; "
                        f"exact OFS proceeds depend on final share count.*"
                    )
                else:
                    st.info(f"**{_company}** — IPO price band not yet announced. "
                            f"Investor returns will be shown once price band is filed.")

            # ── OFS Verification log (console) ───────────────────────────────
            def _safe_fmt_shares(val) -> str:
                """Format share count safely — handles None/non-numeric."""
                try:
                    return f"{int(val):,}" if val is not None else "N/A"
                except (TypeError, ValueError):
                    return str(val) if val else "N/A"

            _v2 = VERIFIED_INVESTOR_DATA.get(_company)
            if _v2 and not _is_upcoming:
                try:
                    _ofs_exp = _v2.get("ofs_total_shares") or 0
                    _ofs_act = sum(
                        (v.get("ofs_shares") or 0)
                        for v in _v2.get("investors", {}).values()
                    )
                    _match = (_ofs_exp == 0) or (_ofs_act == _ofs_exp)
                    print(
                        f"[OFS VERIFY] {_company}: "
                        f"sum={_safe_fmt_shares(_ofs_act)}  "
                        f"RHP={_safe_fmt_shares(_ofs_exp)}  "
                        f"MATCH={_match}"
                    )
                except Exception as _verify_err:
                    print(f"[OFS VERIFY] {_company}: skipped ({type(_verify_err).__name__})")

            # ── Column headers (6 cols) ───────────────────────────────────────
            if _is_upcoming:
                pass  # Scenario table already rendered above; skip the returns table
            if not _is_upcoming:
             _hcols = st.columns([2.5, 1.5, 1.2, 2.0, 2.0, 1.5])
             for _hc, _hl in zip(_hcols,
                ["**Investor**", "**Round**", "**WACA (₹/sh)**",
                 "**Realised Return**", "**Total Return at Listing**", "**Details**"]):
                _hc.markdown(_hl)
             st.markdown(
                "<hr style='margin:2px 0 6px;border:none;border-top:1px solid #ccdaea'>",
                unsafe_allow_html=True)

            def _moic_color(moic: float) -> str:
                """GREEN >1.1×  ORANGE 0.9–1.1×  RED <0.9×"""
                if moic >= 1.1:   return "#16a34a"  # green
                if moic >= 0.9:   return "#d97706"  # orange (near breakeven)
                return "#dc2626"                    # red

            for _idx_inv, _inv in enumerate(pripo):
                if _is_upcoming:
                    continue  # Upcoming IPO: full scenario table shown above; skip per-row render
                _inv_name = _inv.get("investor", "")
                _rc = st.columns([2.5, 1.5, 1.2, 2.0, 2.0, 1.5])

                # Investor name (bold, 15px+)
                _rc[0].markdown(
                    f"<div style='font-size:15px;font-weight:700;line-height:1.4'>"
                    f"{_inv_name}</div>",
                    unsafe_allow_html=True)
                # Round
                _rc[1].markdown(
                    f"<div style='font-size:12px;color:#6b7a8d'>"
                    f"{_inv.get('round','')}</div>",
                    unsafe_allow_html=True)

                # ── Look up investor data ─────────────────────────────────────
                _inv_data = get_investor_data(_company, _inv_name)
                _src      = (_inv_data or {}).get("_source", "v1")

                # ── Compute returns ───────────────────────────────────────────
                if _src == "v2" and _inv_data:
                    # New exact-integer path
                    _r = calculate_returns(
                        seller_name     = _inv_data.get("_matched_key", _inv_name),
                        waca            = _inv_data.get("waca"),
                        ofs_shares      = _inv_data.get("ofs_shares"),
                        pre_offer_shares= _inv_data.get("pre_offer_shares"),
                        ipo_price       = _ipo_px,
                        listing_price   = _list_px,
                        seller_type     = _inv_data.get("type", "investor"),
                        ca_firm         = _inv_data.get("_ca_firm", ""),
                        ofs_confirmed   = _inv_data.get("ofs_confirmed", False),
                    )
                    _waca_display = _inv_data.get("waca")
                    _waca_src_lbl = _inv_data.get("waca_source", "")
                else:
                    # Legacy lakh-based path
                    _r = compute_returns(_inv_data, _ipo_px, _list_px) if _inv_data else {}
                    _waca_display = _r.get("waca")
                    _wt = (_inv_data or {}).get("waca_type", "")
                    _waca_src_lbl = {"RHP": "✅ RHP", "RHP-blended": "✅ RHP-blended",
                                     "derived": "🔢 derived", "estimated": "~ estimated"}.get(_wt, _wt)

                # ── WACA column ───────────────────────────────────────────────
                if _waca_display:
                    _rc[2].markdown(
                        f"<div style='font-size:13px;font-weight:600'>₹{_waca_display:,.2f}</div>",
                        unsafe_allow_html=True)
                else:
                    _rc[2].markdown(
                        f"<div style='font-size:12px;color:#6b7a8d'>—</div>",
                        unsafe_allow_html=True)

                # ── Realised Return column ────────────────────────────────────
                _rtype = _r.get("type", "investor")

                if _rtype == "promoter":
                    # Promoter: show OFS proceeds, no MOIC
                    _proc = _r.get("ofs_proceeds_cr", 0)
                    _rc[3].markdown(
                        f"<div style='font-size:13px;color:#6b7a8d;font-style:italic'>"
                        f"Promoter<br><span style='font-weight:600;color:#374151'>"
                        f"₹{_proc:,.1f} cr proceeds</span></div>",
                        unsafe_allow_html=True)

                elif _r.get("realised_moic") is not None:
                    _realised = _r["realised_moic"]
                    _pct      = _r.get("realised_pct", (_realised - 1) * 100)
                    _pct_s    = f"+{_pct:.1f}%" if _pct >= 0 else f"{_pct:.1f}%"
                    _flag     = " ⚠️" if (_r.get("warnings") or _r.get("sanity_notes")) else ""
                    _col_r    = _moic_color(_realised)
                    _rc[3].markdown(
                        f"<div style='font-size:14px;color:{_col_r};font-weight:700'>"
                        f"{_realised:.2f}×{_flag}</div>",
                        unsafe_allow_html=True)

                elif _waca_display and _ipo_px:
                    _moic_ipo = (_r.get("moic_at_ipo") or
                                 (round(_ipo_px / _waca_display, 2) if _waca_display else None))
                    _ofs_tbd  = _r.get("ofs_shares_tbd", False)
                    _ofs_conf = _r.get("ofs_confirmed", False)
                    if _moic_ipo:
                        _col_r = _moic_color(_moic_ipo)
                        if _ofs_tbd or _ofs_conf:
                            # OFS DID happen — [●] shares in DRHP, show per-share MOIC
                            _rc[3].markdown(
                                f"<div style='font-size:13px;color:{_col_r}'>"
                                f"OFS ✓ — {_moic_ipo:.2f}× at IPO<br>"
                                f"<span style='font-size:11px;color:#6b7a8d'>"
                                f"[●] shares in DRHP</span></div>",
                                unsafe_allow_html=True)
                        else:
                            _rc[3].markdown(
                                f"<div style='font-size:13px;color:{_col_r}'>"
                                f"No OFS — {_moic_ipo:.2f}× at IPO</div>",
                                unsafe_allow_html=True)
                    else:
                        _rc[3].markdown(
                            "<div style='font-size:13px;color:#6b7a8d'>No OFS</div>",
                            unsafe_allow_html=True)
                else:
                    _rc[3].markdown(
                        "<div style='font-size:13px;color:#6b7a8d'>—</div>",
                        unsafe_allow_html=True)

                # ── Total Return at Listing column ────────────────────────────
                if _rtype == "promoter":
                    _rc[4].markdown(
                        "<div style='font-size:12px;color:#6b7a8d'>—</div>",
                        unsafe_allow_html=True)

                elif _r.get("total_moic") is not None:
                    _total = _r["total_moic"]
                    _col_t = _moic_color(_total)
                    _rc[4].markdown(
                        f"<div style='font-size:14px;color:{_col_t};font-weight:600'>"
                        f"{_total:.2f}× total</div>",
                        unsafe_allow_html=True)

                elif _waca_display and _list_px:
                    _moic_lst = _r.get("moic_at_listing") or round(_list_px / _waca_display, 2)
                    _col_t    = _moic_color(_moic_lst)
                    _rc[4].markdown(
                        f"<div style='font-size:14px;color:{_col_t};font-weight:600'>"
                        f"{_moic_lst:.2f}× listing</div>",
                        unsafe_allow_html=True)
                else:
                    _rc[4].markdown(
                        "<div style='font-size:13px;color:#6b7a8d'>—</div>",
                        unsafe_allow_html=True)

                # ── Details popover ───────────────────────────────────────────
                with _rc[5]:
                    with st.popover("Details ↗", use_container_width=True):
                        if _src == "v2" and _inv_data and _rtype != "error":
                            # ── New v2 detailed popup ─────────────────────────
                            _ca   = _inv_data.get("_ca_firm", "")
                            _wsrc = _inv_data.get("waca_source", "")
                            st.markdown(f"**{_inv_data.get('_matched_key', _inv_name)}**")
                            if _ca:
                                st.markdown(
                                    f"<div style='font-size:12px;color:#6b7a8d'>"
                                    f"✅ WACA certified by {_ca}</div>",
                                    unsafe_allow_html=True)
                            st.divider()

                            if _rtype == "promoter":
                                _os = _r.get("ofs_shares", 0) or 0
                                st.markdown(
                                    f"**Type:** Promoter / Founder  \n"
                                    f"**OFS shares sold:** {_os:,}  \n"
                                    f"**IPO price:** ₹{_ipo_px}  \n"
                                    f"**OFS proceeds:** ₹{_r.get('ofs_proceeds_cr', 0):,.2f} cr  \n"
                                    f"*Cost basis negligible — no return multiple shown.*"
                                )
                            else:
                                _os   = _inv_data.get("ofs_shares")
                                _pre  = _inv_data.get("pre_offer_shares")
                                _w    = _inv_data.get("waca")
                                st.markdown(f"**WACA:** ₹{_w:,.2f}/sh  \n*{_wsrc}*")
                                st.divider()
                                _ofs_conf_d = _inv_data.get("ofs_confirmed", False)
                                if _os:
                                    if _pre:
                                        st.markdown(f"**Pre-offer shares:** {_pre:,}")
                                    st.markdown(
                                        f"**OFS shares sold:** {_os:,}  \n"
                                        f"**OFS proceeds:** {_os:,} × ₹{_ipo_px} = "
                                        f"₹{_r.get('ofs_proceeds_cr', 0):,.2f} cr  \n"
                                        f"**Cost of OFS:** {_os:,} × ₹{_w:,.2f} = "
                                        f"₹{_r.get('cost_of_ofs_cr', 0):,.2f} cr  \n"
                                        f"**Realised MOIC:** ₹{_ipo_px} ÷ ₹{_w:,.2f} = "
                                        f"**{_r.get('realised_moic', '—')}×**"
                                    )
                                    if _r.get("total_moic"):
                                        _ret = (_pre or 0) - _os
                                        st.markdown(
                                            f"**Retained shares:** {_ret:,}  \n"
                                            f"**Unrealised:** {_ret:,} × ₹{_list_px} = "
                                            f"₹{_r.get('unrealised_cr', 0):,.2f} cr  \n"
                                            f"**Total cost:** {_pre:,} × ₹{_w:,.2f} = "
                                            f"₹{_r.get('total_cost_cr', 0):,.2f} cr  \n"
                                            f"**Total MOIC:** ₹{_r.get('total_value_cr', 0):,.2f} cr ÷ "
                                            f"₹{_r.get('total_cost_cr', 0):,.2f} cr = "
                                            f"**{_r.get('total_moic', '—')}×**"
                                        )
                                elif _ofs_conf_d:
                                    # OFS confirmed but [●] share count — show per-share MOIC
                                    _moic_v = _r.get("realised_moic") or _r.get("moic_at_ipo")
                                    _moic_l = _r.get("moic_at_listing")
                                    st.markdown(
                                        f"**✅ OFS confirmed** — sold in IPO OFS  \n"
                                        f"*OFS share count was [●] (TBD at pricing) in DRHP.*  \n"
                                        f"**Per-share MOIC at IPO:** "
                                        f"₹{_ipo_px} ÷ ₹{_w:,.2f} = **{_moic_v:.2f}×**" if _moic_v else
                                        f"**✅ OFS confirmed** — share count TBD [●]"
                                    )
                                    if _moic_l:
                                        st.markdown(
                                            f"**Per-share MOIC at listing:** "
                                            f"₹{_list_px} ÷ ₹{_w:,.2f} = **{_moic_l:.2f}×**"
                                        )
                                else:
                                    st.markdown(
                                        f"No OFS shares sold.  \n"
                                        f"**MOIC at IPO:** ₹{_ipo_px} ÷ ₹{_w:,.2f} = "
                                        f"**{_r.get('moic_at_ipo', '—')}×**  \n"
                                        f"**MOIC at listing:** ₹{_list_px} ÷ ₹{_w:,.2f} = "
                                        f"**{_r.get('moic_at_listing', '—')}×**"
                                    )
                                if _r.get("warnings"):
                                    for _w_msg in _r["warnings"]:
                                        st.warning(_w_msg)
                        else:
                            # ── Legacy popup (unchanged) ──────────────────────
                            st.markdown(_return_popup_md(_inv, ipo))

            st.caption(
                "**Realised Return** = OFS shares × IPO price ÷ cost basis.  "
                "**Total Return** = (OFS proceeds + retained × listing price) ÷ total invested.  "
                "🟢 >1.1×  🟠 0.9–1.1× (near breakeven)  🔴 <0.9× (loss).  "
                "✅ = WACA from RHP CA-certified."
            )
        else:
            st.markdown(
                f"<div style='background:{BG_ALT};border:1px solid {BORDER};border-radius:8px;"
                f"padding:12px;color:#6b7a8d;font-size:13px'>"
                f"Pre-IPO investor return data not available for this IPO.</div>",
                unsafe_allow_html=True)

        st.markdown(f'<div style="color:#a38060;font-size:11px;text-align:right">Last updated: {_now_ist()}</div>',
                    unsafe_allow_html=True)

    # ── t6: Lock-Up Expiry Analysis ───────────────────────────────────────────
    with t6:
        _render_lockup_tab(ipo)

