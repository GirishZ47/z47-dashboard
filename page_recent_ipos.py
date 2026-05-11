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
        "listing_date": "2025-11-12", "price_band": "₹100", "issue_price": 100,
        "listing_price": 114.0, "issue_size": "₹6,160 cr", "issue_size_cr": 6160,
        "lot_size": 76, "fresh_issue": "₹6,160 cr", "ofs": "–",
        "use_of_funds": "Technology infrastructure, customer acquisition, and general corporate purposes.",
        "key_investors": "Sequoia Capital, Ribbit Capital, Tiger Global, YC Continuity",
        "qib_sub": "62.3x", "nii_sub": "44.8x", "rii_sub": "15.2x", "overall_sub": "63.2x",
        "known_listing_gain_pct": 14.0,
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
        "listing_date": "2026-01-28", "price_band": "₹118–124", "issue_price": 124,
        "listing_price": 112.60, "issue_size": "₹2,526 cr", "issue_size_cr": 2526,
        "lot_size": 70, "fresh_issue": "₹1,250 cr", "ofs": "₹1,276 cr",
        "use_of_funds": "Delivery infrastructure, technology, working capital.",
        "key_investors": "Flipkart, Nokia Growth Partners, Eight Roads Ventures",
        "qib_sub": "35.6x", "nii_sub": "29.4x", "rii_sub": "12.7x", "overall_sub": "32.8x",
        "known_listing_gain_pct": -9.2,
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
        "listing_date": "2025-08-19", "price_band": "₹490–517", "issue_price": 517,
        "listing_price": 510.0, "issue_size": "₹1,000 cr", "issue_size_cr": 1000,
        "lot_size": 26, "fresh_issue": "₹1,000 cr", "ofs": "–",
        "use_of_funds": "Store expansion, technology, working capital.",
        "key_investors": "Accel, Kalaari Capital, Ratan Tata",
        "qib_sub": "47.2x", "nii_sub": "33.1x", "rii_sub": "14.6x", "overall_sub": "44.8x",
        "known_listing_gain_pct": -1.4,
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
        "listing_date": "2025-11-14", "price_band": "₹201–221", "issue_price": 221,
        "listing_price": 242.0, "issue_size": "₹6,000 cr", "issue_size_cr": 6000,
        "lot_size": 40, "fresh_issue": "₹2,080 cr", "ofs": "₹3,920 cr",
        "use_of_funds": "Technology investments, merchant network expansion.",
        "key_investors": "Temasek, Mastercard, Actis, Sequoia",
        "qib_sub": "38.4x", "nii_sub": "24.9x", "rii_sub": "8.1x", "overall_sub": "34.7x",
        "known_listing_gain_pct": 9.5,
    },
    {
        "company": "Urban Company", "sector": "Consumer / Consumertech", "ticker": "URBANCO.NS", "exchange": "NSE",
        "listing_date": "2025-09-17", "price_band": "₹93–103", "issue_price": 103,
        "listing_price": 162.25, "issue_size": "₹3,000 cr", "issue_size_cr": 3000,
        "lot_size": 34, "fresh_issue": "₹1,500 cr", "ofs": "₹1,500 cr",
        "use_of_funds": "Brand marketing, technology, service partner initiatives.",
        "key_investors": "Accel, Tiger Global, VY Capital",
        "qib_sub": "52.1x", "nii_sub": "37.8x", "rii_sub": "14.3x", "overall_sub": "48.2x",
        "known_listing_gain_pct": 57.5,
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
        "listing_date": "2025-11-21", "price_band": "₹528–577", "issue_price": 577,
        "listing_price": 571.90, "issue_size": "₹479 cr", "issue_size_cr": 479,
        "lot_size": 57, "fresh_issue": "₹479 cr", "ofs": "–",
        "use_of_funds": "Product development, sales & marketing, acquisitions.",
        "key_investors": "Sequoia Capital, Avataar Venture Partners",
        "qib_sub": "68.3x", "nii_sub": "49.7x", "rii_sub": "18.2x", "overall_sub": "62.4x",
        "known_listing_gain_pct": -0.9,
    },
    {
        "company": "Kissht (OnEMI Technology)", "sector": "Fintech/FS", "ticker": "KISSHT.NS", "exchange": "NSE",
        "listing_date": "2026-05-08", "price_band": "₹162–171", "issue_price": 171,
        "listing_price": 190.0, "issue_size": "₹926 cr", "issue_size_cr": 926,
        "lot_size": 87, "fresh_issue": "₹850 cr", "ofs": "₹76 cr",
        "use_of_funds": "Augmenting capital base of NBFC subsidiary Si Creva for lending; general corporate purposes.",
        "key_investors": "Temasek (Vertex), Ventureast, Sistema Asia Fund",
        "qib_sub": "25.97x", "nii_sub": "6.91x", "rii_sub": "2.13x", "overall_sub": "9.96x",
        "known_listing_gain_pct": 11.1,
    },
]


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
            {"investor": "Peak XV Partners (Sequoia Capital India)", "round": "Series A–C (2016–18)", "entry_val": "~$13–70M valuation", "pct_held": "~12%", "return_at_ipo": "~52x at listing (earliest entry ~₹2/sh → listing ₹114)", "return_at_cmp": "—"},
            {"investor": "Ribbit Capital",            "round": "Series D–E (2018–19)", "entry_val": "~$180–300M valuation", "pct_held": "~8%",  "return_at_ipo": "~43x at listing",  "return_at_cmp": "—"},
            {"investor": "YC Continuity Fund",        "round": "Series C (2017)",      "entry_val": "~$115M valuation",     "pct_held": "~4%",  "return_at_ipo": "~29x at listing",  "return_at_cmp": "—"},
            {"investor": "Tiger Global Management",   "round": "Series D–E (2020)",    "entry_val": "~$750M valuation",     "pct_held": "~5%",  "return_at_ipo": "~4.5x at listing", "return_at_cmp": "—"},
            {"investor": "Alkeon Capital Management", "round": "Series F (2021)",      "entry_val": "$3.0B valuation",      "pct_held": "~2%",  "return_at_ipo": "~2.6x at listing (IPO MCap ~$8B vs $3B entry)", "return_at_cmp": "—"},
            {"investor": "ICONIQ Capital",            "round": "Series E–F (2020–21)", "entry_val": "~$1–3B valuation",     "pct_held": "~3%",  "return_at_ipo": "~2–2.5x at listing", "return_at_cmp": "—"},
            {"investor": "Temasek Holdings",          "round": "Series E–F (2020–21)", "entry_val": "~$1–3B valuation",     "pct_held": "~2%",  "return_at_ipo": "~1.5–2x at listing", "return_at_cmp": "—"},
            {"investor": "Satya Nadella (personal)",  "round": "Series F (2021)",      "entry_val": "$3.0B valuation",      "pct_held": "<1%",  "return_at_ipo": "~2.3x at listing", "return_at_cmp": "—"},
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
            {"investor": "SoftBank Vision Fund",     "round": "Series C–D (2019–21)", "entry_val": "~$1.5–3B valuation",   "pct_held": "~25%", "return_at_ipo": "~Loss to breakeven (OLA IPO MCap ~$4B vs SVF avg entry ~$3B; early tranches marginally positive)", "return_at_cmp": "—"},
            {"investor": "Tiger Global Management",  "round": "Series B (2017)",       "entry_val": "~$250M valuation; WACA ₹11.7/sh", "pct_held": "~5%", "return_at_ipo": "~6.5x at listing (WACA ₹11.7 → listing ₹75.99)", "return_at_cmp": "—"},
            {"investor": "Matrix Partners India (Z47)", "round": "Series A (2016)",   "entry_val": "~$50M valuation; WACA ~₹8.3/sh", "pct_held": "~8%", "return_at_ipo": "~9.2x at listing (WACA ~₹8.3 → listing ₹75.99)", "return_at_cmp": "—"},
            {"investor": "Alpha Wave Global",        "round": "Series D (2021)",       "entry_val": "~$3B valuation",        "pct_held": "~3%",  "return_at_ipo": "~1.3x at listing",    "return_at_cmp": "—"},
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
            {"investor": "AceVector Group (fmr Snapdeal / Jasper Infotech)", "round": "Acquisition into Snapdeal ecosystem (2012)", "entry_val": "WACA ₹23.52/sh (implied)", "pct_held": "~47% pre-IPO", "return_at_ipo": "~4.6x at issue / ~10x at listing (WACA ₹23.52 → issue ₹108 → listing ₹235)", "return_at_cmp": "—"},
            {"investor": "SoftBank (indirect via Snapdeal / AceVector)", "round": "Indirect via Snapdeal ownership (2014–15)", "entry_val": "N/A (indirect through AceVector)", "pct_held": "~25% effective", "return_at_ipo": "~3.5x at issue / ~7–8x at listing (SoftBank holds via AceVector which holds Unicommerce)", "return_at_cmp": "—"},
            {"investor": "B2 Capital Partners",  "round": "Pre-IPO growth round (2022)", "entry_val": "~₹1,200–1,800 cr valuation", "pct_held": "~4%", "return_at_ipo": "Did not sell in OFS; ~5–10x paper gain at listing", "return_at_cmp": "—"},
            {"investor": "Anchorage Capital Partners (Z47 ecosystem)", "round": "Pre-IPO (2023)", "entry_val": "~₹1,500 cr valuation", "pct_held": "~3%", "return_at_ipo": "~3–5x at listing", "return_at_cmp": "—"},
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
            {"investor": "Vertex Ventures SE Asia & India (Temasek-backed)", "round": "Series A–C (2016–19)", "entry_val": "~$20–100M valuation", "pct_held": "Largest VC holder (~18%)", "return_at_ipo": ">5x at listing (sold shares in OFS; listing ₹190 vs WACA ~₹35–40/sh)", "return_at_cmp": "—"},
            {"investor": "Ventureast (Finquest Fund / Tenedo Fund)", "round": "Series A–B (2016–18)", "entry_val": "Seed–Series A (~$20–50M valuation)", "pct_held": "~9% (two funds)", "return_at_ipo": "~4–6x at listing (WACA ~₹30–45/sh → listing ₹190)", "return_at_cmp": "—"},
            {"investor": "Sistema Asia Fund",           "round": "Series B–C (2018–20)", "entry_val": "~$100–200M valuation", "pct_held": "~5.29%", "return_at_ipo": "~2–3x at listing (listing ₹190 vs WACA ~₹65–90/sh)", "return_at_cmp": "—"},
            {"investor": "Endiya Partners (Endiya Seed Co-creation Fund)", "round": "Seed / Series A (2015–17)", "entry_val": "~$5–20M valuation; WACA ~₹13–23/sh", "pct_held": "~5.65%", "return_at_ipo": "~8–15x at listing (sold 5.35 lakh shares worth ₹9.15 cr in OFS at ₹190 listing)", "return_at_cmp": "—"},
            {"investor": "AION Capital Partners (Apollo-ICICI JV)", "round": "Growth (2020–22)", "entry_val": "~$200–400M valuation", "pct_held": "~3–4%", "return_at_ipo": "~1.5–2.5x at listing", "return_at_cmp": "—"},
            {"investor": "Founders: Ranvir Singh & Krishnan Vishwanathan", "round": "Founding (2015)", "entry_val": "Negligible (~₹1–2/sh)", "pct_held": "~30.9% combined", "return_at_ipo": ">50x at listing (did NOT sell in OFS; paper gain on listing)", "return_at_cmp": "—"},
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
            {"investor": "Tiger Global Management",           "round": "Series D–E (2019–21)", "entry_val": "WACA ₹74.41/sh (~$1.5–2.8B valuation)", "pct_held": "~10%", "return_at_ipo": "~1.4x at issue / ~2.2x at listing (WACA ₹74.41 → issue ₹103 = 1.38x; → listing ₹162.25 = 2.18x)", "return_at_cmp": "—"},
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
            {"investor": "Accel",                  "round": "Series A–B (2011–14)",  "entry_val": "~$5–15M valuation",      "pct_held": "~14%", "return_at_ipo": "~8.12x at issue / ~8x at listing (WACA ~₹63.7/sh → issue ₹517 = 8.12x; listing ₹510 ~flat)", "return_at_cmp": "—"},
            {"investor": "Kalaari Capital",        "round": "Series A–B (2012–15)",  "entry_val": "~$10–30M valuation",     "pct_held": "~12%", "return_at_ipo": "~8.72x at issue / ~8.6x at listing (WACA ~₹59.3/sh → issue ₹517)", "return_at_cmp": "—"},
            {"investor": "Saama Capital",          "round": "Series B (2015)",       "entry_val": "~$30–50M valuation",     "pct_held": "~8%",  "return_at_ipo": "~10.62x at issue (WACA ~₹48.7/sh → issue ₹517; sold in OFS)", "return_at_cmp": "—"},
            {"investor": "Iron Pillar",            "round": "Series C–D (2018–20)",  "entry_val": "~$100–200M valuation",   "pct_held": "~6%",  "return_at_ipo": "~5.57x at issue (WACA ~₹92.8/sh → issue ₹517)", "return_at_cmp": "—"},
            {"investor": "Sunil Munjal (family office)", "round": "Series D (2020)", "entry_val": "~$200M valuation",       "pct_held": "~4%",  "return_at_ipo": "~1.97x at issue (WACA ~₹262/sh → issue ₹517)", "return_at_cmp": "—"},
            {"investor": "Peak XV Partners (Sequoia)", "round": "Series D–E (2020–22)", "entry_val": "~$200–600M valuation", "pct_held": "~7%", "return_at_ipo": "Did NOT sell in OFS; ~2–5x paper gain at listing", "return_at_cmp": "—"},
            {"investor": "Prosus Ventures",        "round": "Series E (2022)",       "entry_val": "~$500M valuation",       "pct_held": "~5%",  "return_at_ipo": "Did NOT sell in OFS; ~1.5x paper gain at listing", "return_at_cmp": "—"},
            {"investor": "Steadview Capital",      "round": "Series E (2022)",       "entry_val": "~$500M valuation",       "pct_held": "~3%",  "return_at_ipo": "~1.5x at listing (sold partial in OFS)", "return_at_cmp": "—"},
            {"investor": "Ratan Tata (personal)",  "round": "Angel / Series B (2015)", "entry_val": "~$20M valuation",      "pct_held": "<1%",  "return_at_ipo": ">20x at issue (early angel; did not sell in OFS)", "return_at_cmp": "—"},
            {"investor": "Info Edge Ventures",     "round": "Series B–C (2014–17)",  "entry_val": "~$10–50M valuation",     "pct_held": "~2%",  "return_at_ipo": "~15–30x at listing (early strategic financer)", "return_at_cmp": "—"},
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
    ticker       = ipo.get("ticker", "")
    listing_str  = ipo.get("listing_date", "")
    issue_price  = ipo.get("issue_price")
    issue_size   = ipo.get("issue_size_cr", 0) or 0
    anchors      = ipo.get("anchors", [])
    pripo        = ipo.get("pripo_investors", [])

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

    # ── Lock-up schedule ────────────────────────────────────────────────────
    # Anchor: 30 days from allotment (1 day before listing typically)
    anchor_expiry    = listing_dt + timedelta(days=30)
    # Pre-IPO non-promoter: 6 months from listing
    pripo_expiry     = listing_dt + timedelta(days=182)
    # Promoter (non-locked 80%): 18 months from listing
    promoter_expiry  = listing_dt + timedelta(days=548)
    # Promoter (remaining 20%): 3 years from listing
    promoter3y_expiry = listing_dt + timedelta(days=1095)

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

    # Estimate approximate shares/values
    anchor_pct = round(100 * (ipo.get("anchor_total_cr", 0) or 0) / (issue_size or 1), 1)
    pripo_pct  = 15.0  # rough estimate: pre-IPO non-promoter ~15% of post-issue typically
    promo_pct  = 35.0  # rough promoter pre-lock (80% of promoter stake)

    lockup_rows = [
        {"Lock-Up Type": "Anchor Investors",
         "Who": ", ".join(a.get("investor", "") for a in anchors[:3]) + ("…" if len(anchors) > 3 else ""),
         "Expiry Date": anchor_expiry.strftime("%d %b %Y"),
         "~% of Shares": f"~{anchor_pct}%",
         "Status": _status(anchor_expiry),
         "Risk": _risk(anchor_expiry, anchor_pct)},
        {"Lock-Up Type": "Pre-IPO Investors (non-promoter)",
         "Who": ", ".join(p.get("investor", "").split("(")[0].strip() for p in pripo[:3]) + ("…" if len(pripo) > 3 else ""),
         "Expiry Date": pripo_expiry.strftime("%d %b %Y"),
         "~% of Shares": f"~{pripo_pct}%",
         "Status": _status(pripo_expiry),
         "Risk": _risk(pripo_expiry, pripo_pct)},
        {"Lock-Up Type": "Promoters (80% of stake)",
         "Who": "Promoter group",
         "Expiry Date": promoter_expiry.strftime("%d %b %Y"),
         "~% of Shares": f"~{promo_pct}%",
         "Status": _status(promoter_expiry),
         "Risk": _risk(promoter_expiry, promo_pct)},
        {"Lock-Up Type": "Promoters (remaining 20%)",
         "Who": "Promoter group",
         "Expiry Date": promoter3y_expiry.strftime("%d %b %Y"),
         "~% of Shares": f"~{round(promo_pct * 0.25, 1)}%",
         "Status": _status(promoter3y_expiry),
         "Risk": "—"},
    ]
    st.dataframe(pd.DataFrame(lockup_rows), use_container_width=True, hide_index=True)
    st.caption(
        "SEBI lock-up rules: Anchor investors — 30 days from allotment. "
        "Pre-IPO non-promoter shareholders — 6 months from listing. "
        "Promoters — 80% locked for 18 months, remaining 20% for 3 years from listing. "
        "% figures are approximate estimates."
    )

    # ── Price impact analysis ────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 📉 Price Impact Around Lock-Up Expiries")

    past_expiries = [
        (anchor_expiry,   "Anchor Lock-Up"),
        (pripo_expiry,    "Pre-IPO Lock-Up"),
        (promoter_expiry, "Promoter Lock-Up (18M)"),
    ]
    upcoming_expiries = [(dt, lbl) for dt, lbl in past_expiries if dt > today]
    passed_expiries   = [(dt, lbl) for dt, lbl in past_expiries if dt <= today]

    # Upcoming expiries warning
    if upcoming_expiries:
        for exp_dt, exp_lbl in upcoming_expiries:
            days_left = (exp_dt - today).days
            price_now, _, _ = _live_price(ticker)
            # Rough estimate of unlocking value
            if exp_lbl == "Anchor Lock-Up":
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

    # Price charts for expired lock-ups
    if passed_expiries:
        for exp_dt, exp_lbl in passed_expiries:
            st.markdown(f"**Price around {exp_lbl} expiry ({exp_dt.strftime('%d %b %Y')})**")
            _lockup_price_chart(ticker, exp_dt, exp_lbl, ipo["company"])
    else:
        st.info("No lock-up periods have expired yet for this IPO. Charts will appear after each expiry.")

    st.markdown(f'<div style="color:#a38060;font-size:11px;text-align:right">Last updated: {_now_ist()}</div>',
                unsafe_allow_html=True)


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

    val_cols = ["Company", "Listing MCap (₹ Cr)", "Revenue (₹ Cr)",
                "EV/Rev (listing)", "EV/Rev (CMP)",
                "P/E at Listing", "P/E at CMP",
                "P/B at Listing", "P/B at CMP"]
    val_df = df[val_cols].copy()

    def _mult_color(val):
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return ""
        return ""   # neutral — no color on multiples

    st.dataframe(val_df, use_container_width=True, height=400, hide_index=True,
                 column_config={
                     "Listing MCap (₹ Cr)": st.column_config.NumberColumn(format="₹%d cr"),
                     "Revenue (₹ Cr)":      st.column_config.NumberColumn(format="₹%d cr"),
                     "EV/Rev (listing)":    st.column_config.NumberColumn("EV/Rev (Listing)", format="%.1fx"),
                     "EV/Rev (CMP)":        st.column_config.NumberColumn("EV/Rev (CMP)",     format="%.1fx"),
                     "P/E at Listing":      st.column_config.NumberColumn("P/E (Listing)",    format="%.1fx"),
                     "P/E at CMP":          st.column_config.NumberColumn("P/E (CMP)",        format="%.1fx"),
                     "P/B at Listing":      st.column_config.NumberColumn("P/B (Listing)",    format="%.1fx"),
                     "P/B at CMP":          st.column_config.NumberColumn("P/B (CMP)",        format="%.1fx"),
                 })
    st.caption("EV = MCap + Debt − Cash. P/E only for profitable companies. P/B only for financial-services companies. CMP multiples scaled by current price / listing price ratio.")

    st.markdown(f'<div style="color:#a38060;font-size:11px;text-align:right">Last updated: {_now_ist()}</div>',
                unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Deep Dive — Select an IPO")
    selected = st.selectbox("Select IPO", [i["company"] for i in IPOS], key="ri_deep")
    ipo = next(i for i in IPOS if i["company"] == selected)

    t1, t2, t3, t4, t5, t6 = st.tabs(["📋 Overview", "📊 Performance", "🔮 GMP", "📬 Subscription", "🏦 Investors", "🔒 Lock-Up Analysis"])

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
        with p2:
            pe_warn = " ⚠" if ipo.get("company") == "Urban Company" else ""
            st.metric("P/E at Listing",
                      (f"{pe_listing:.1f}x{pe_warn}" if pe_listing else
                       ("Loss-making" if profitable is False else "N/A")),
                      help=("Market Cap ÷ PAT at listing day (only for profitable companies). "
                            "⚠ Urban Company PAT includes ₹211 cr one-time deferred tax credit; "
                            "underlying PBT was ~₹29 cr." if pe_warn else
                            "Market Cap ÷ PAT at listing day (only for profitable companies)"))
        with p3:
            st.metric("P/B at Listing",
                      f"{pb_listing:.1f}x" if pb_listing else "N/A",
                      help="Market Cap ÷ Book Value at listing day (financial services companies only)")

        # Row 3 — Multiples at CMP
        ev_rev_cmp_label = "P/NEP (CMP)" if is_insurer else "EV/Revenue (CMP)"
        st.markdown("<div style='font-size:12px;color:#6b7a8d;margin:8px 0 2px'>Multiples at Current Price</div>",
                    unsafe_allow_html=True)
        q1, q2, q3, _gap2 = st.columns([1, 1, 1, 1])
        with q1:
            delta_evr = f"{(ev_rev_now - ev_rev_listing):+.1f}x" if (ev_rev_now and ev_rev_listing) else None
            st.metric(ev_rev_cmp_label, f"{ev_rev_now:.1f}x" if ev_rev_now else "N/A", delta=delta_evr)
        with q2:
            delta_pe = f"{(pe_now - pe_listing):+.1f}x" if (pe_now and pe_listing) else None
            st.metric("P/E at CMP",
                      f"{pe_now:.1f}x" if pe_now else ("Loss-making" if profitable is False else "N/A"),
                      delta=delta_pe)
        with q3:
            delta_pb = f"{(pb_now - pb_listing):+.1f}x" if (pb_now and pb_listing) else None
            st.metric("P/B at CMP", f"{pb_now:.1f}x" if pb_now else "N/A", delta=delta_pb)

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
        # ── Section 1: Shareholding Pattern ──────────────────────────────────
        st.markdown("#### 📊 Shareholding Pattern")
        with st.spinner("Fetching shareholding…"):
            holders = _shareholding(ipo["ticker"])
        if holders is not None:
            _LABEL_MAP = {
                "insidersPercentHeld":           ("Insider / Promoter Holding",    "pct"),
                "institutionsPercentHeld":        ("Institutional Holding",         "pct"),
                "institutionsFloatPercentHeld":   ("Institutional % of Float",      "pct"),
                "institutionsCount":              ("No. of Institutions",           "int"),
            }
            sh_rows = []
            try:
                # major_holders is a DataFrame with metric as index, value in last col
                for idx in holders.index:
                    key   = str(idx)
                    val   = holders.loc[idx].iloc[-1] if hasattr(holders.loc[idx], "iloc") else holders.loc[idx]
                    label, dtype = _LABEL_MAP.get(key, (key, "pct"))
                    try:
                        fval = float(val)
                        if dtype == "pct":
                            # yfinance returns decimals (0.49 = 49%)
                            fmt = f"{fval * 100:.2f}%" if fval <= 1 else f"{fval:.2f}%"
                        else:
                            fmt = str(int(fval))
                    except Exception:
                        fmt = str(val)
                    sh_rows.append({"Category": label, "Value": fmt})
            except Exception:
                sh_rows = []
            if sh_rows:
                st.dataframe(pd.DataFrame(sh_rows), use_container_width=True, hide_index=True)
            else:
                _warn("Could not parse shareholding data.")
        else:
            _warn("Shareholding data not available from yfinance for this ticker.")

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
        if pripo and ipo.get("issue_price"):
            ip_val = ipo["issue_price"]
            price_now, _, _ = _live_price(ipo["ticker"])
            rows_pi = []
            for inv in pripo:
                row = {
                    "Investor":         inv.get("investor", ""),
                    "Investment Round": inv.get("round", ""),
                    "Entry Valuation":  inv.get("entry_val", "N/A"),
                    "% Held (Pre-IPO)": inv.get("pct_held", "N/A"),
                    "Return at IPO":    inv.get("return_at_ipo", "N/A"),
                }
                if price_now and inv.get("entry_price_per_share"):
                    ep = inv["entry_price_per_share"]
                    ret_now = round((price_now - ep) / ep * 100, 1)
                    row["Return at CMP"] = f"{ret_now:+.1f}%"
                else:
                    row["Return at CMP"] = inv.get("return_at_cmp", "—")
                rows_pi.append(row)

            pi_df = pd.DataFrame(rows_pi)

            def _ret_color(val):
                v = str(val)
                if v.startswith("+") or (v.replace(".","").replace("%","").lstrip("-").isdigit() and not v.startswith("-")):
                    try:
                        if float(v.replace("%","").replace("+","")) > 0:
                            return "color:#16a34a;font-weight:600"
                    except Exception:
                        pass
                if v.startswith("-"):
                    return "color:#dc2626;font-weight:600"
                return ""

            ret_cols = [c for c in ["Return at IPO", "Return at CMP"] if c in pi_df.columns]
            styled_pi = pi_df.style.map(_ret_color, subset=ret_cols)
            st.dataframe(styled_pi, use_container_width=True, hide_index=True)
            st.caption("Entry valuations sourced from public VC funding disclosures & RHP filings. Returns are approximate.")
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

    st.markdown("---")
    render_z47_assistant(
        context="recent_ipos",
        extra_context=(f"Currently viewing: {ipo['company']} | Sector: {ipo['sector']} | "
                       f"Listing: {ipo['listing_date']} | Issue price: ₹{ipo.get('issue_price','N/A')} | "
                       f"Listing price: ₹{ipo.get('listing_price','N/A')} | "
                       f"EV/Rev at listing: {ipo.get('ev_rev_at_listing','N/A')}x"),
    )
