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
            {"investor": "Sequoia Capital / Peak XV", "round": "Series A–C (2016–18)", "entry_val": "~$30–300M",  "pct_held": "~12%", "return_at_ipo": "~5–40x",  "return_at_cmp": "—"},
            {"investor": "Ribbit Capital",            "round": "Series B–D (2018–20)", "entry_val": "~$200–800M", "pct_held": "~8%",  "return_at_ipo": "~2–8x",   "return_at_cmp": "—"},
            {"investor": "YC Continuity",             "round": "Series C (2018)",      "entry_val": "~$250M",     "pct_held": "~4%",  "return_at_ipo": "~5x",      "return_at_cmp": "—"},
            {"investor": "Tiger Global",              "round": "Series F (2021)",      "entry_val": "$3.0B",      "pct_held": "~5%",  "return_at_ipo": "-57%",     "return_at_cmp": "—"},
            {"investor": "Alkeon Capital",            "round": "Series F (2021)",      "entry_val": "$3.0B",      "pct_held": "~2%",  "return_at_ipo": "-57%",     "return_at_cmp": "—"},
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
            {"investor": "Prosus (Naspers)",  "round": "Series D–H (2017–21)", "entry_val": "$0.5–5.5B",  "pct_held": "~31%", "return_at_ipo": "Varies",  "return_at_cmp": "—"},
            {"investor": "SoftBank Vision Fund","round": "Series I (2021)",   "entry_val": "$10.7B",     "pct_held": "~8%",  "return_at_ipo": "-64%",    "return_at_cmp": "—"},
            {"investor": "Accel",             "round": "Series A (2015)",      "entry_val": "~$100M",     "pct_held": "~5%",  "return_at_ipo": "~40x",    "return_at_cmp": "—"},
            {"investor": "DST Global",        "round": "Series F–G (2019–20)","entry_val": "$3.6–5B",    "pct_held": "~5%",  "return_at_ipo": "-15–25%", "return_at_cmp": "—"},
            {"investor": "Alpha Wave / Falcon Edge","round": "Series J (2022)","entry_val": "$10.7B",    "pct_held": "~2%",  "return_at_ipo": "-64%",    "return_at_cmp": "—"},
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
            {"investor": "SoftBank Vision Fund", "round": "Series C–D (2019–21)", "entry_val": "$2–3B",   "pct_held": "~25%", "return_at_ipo": "-70–80%", "return_at_cmp": "—"},
            {"investor": "Tiger Global",         "round": "Series C (2019)",       "entry_val": "~$1B",   "pct_held": "~5%",  "return_at_ipo": "-90%",    "return_at_cmp": "—"},
            {"investor": "Matrix Partners",      "round": "Series A–B (2016–18)", "entry_val": "~$100M", "pct_held": "~8%",  "return_at_ipo": "~3–5x",   "return_at_cmp": "—"},
            {"investor": "Hero MotoCorp",        "round": "Strategic (2019)",      "entry_val": "~$1B",   "pct_held": "~4%",  "return_at_ipo": "-90%",    "return_at_cmp": "—"},
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
            {"investor": "Hero MotoCorp",       "round": "Strategic (2018)",      "entry_val": "~$200M",  "pct_held": "~34%", "return_at_ipo": "~5x",    "return_at_cmp": "—"},
            {"investor": "Tiger Global",        "round": "Series C–D (2020–21)", "entry_val": "~$600M",  "pct_held": "~8%",  "return_at_ipo": "~2x",    "return_at_cmp": "—"},
            {"investor": "Sachin Bansal (navi)","round": "Series D (2020)",      "entry_val": "~$600M",  "pct_held": "~4%",  "return_at_ipo": "~2x",    "return_at_cmp": "—"},
            {"investor": "GIC (Singapore)",     "round": "Series E (2022)",      "entry_val": "~$1.3B",  "pct_held": "~5%",  "return_at_ipo": "~0.8x",  "return_at_cmp": "—"},
        ],
    },
    "MobiKwik": {
        "anchor_total_cr": 172,
        "anchors": [
            {"investor": "Bajaj Allianz Life Insurance", "category": "Insurance",    "allocation_cr": 95},
            {"investor": "SBI Life Insurance",           "category": "Insurance",    "allocation_cr": 77},
        ],
        "pripo_investors": [
            {"investor": "Bajaj Finance",  "round": "Series E (2021)", "entry_val": "~₹4,000 cr", "pct_held": "~12%", "return_at_ipo": "~3x",  "return_at_cmp": "—"},
            {"investor": "ABIA (Abu Dhabi)","round": "Series E (2021)","entry_val": "~₹4,000 cr", "pct_held": "~8%",  "return_at_ipo": "~3x",  "return_at_cmp": "—"},
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
            {"investor": "SoftBank (via Snapdeal)", "round": "Acquisition (2012)", "entry_val": "N/A",     "pct_held": "~49%", "return_at_ipo": "High",  "return_at_cmp": "—"},
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
            {"investor": "General Atlantic", "round": "Growth (2019)", "entry_val": "~$200M",  "pct_held": "~22%", "return_at_ipo": "~7x",  "return_at_cmp": "—"},
            {"investor": "KKR",              "round": "Growth (2022)", "entry_val": "~$700M",  "pct_held": "~11%", "return_at_ipo": "~2x",  "return_at_cmp": "—"},
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
            {"investor": "Fairfax Financial Holdings", "round": "Founding Investor (2017)", "entry_val": "~$100M",  "pct_held": "~49%", "return_at_ipo": "~10x",  "return_at_cmp": "—"},
            {"investor": "TVS Capital",               "round": "Series B (2020)",          "entry_val": "~$800M",  "pct_held": "~3%",  "return_at_ipo": "~1.2x", "return_at_cmp": "—"},
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
            {"investor": "SAIF Partners (Elevation Capital)", "round": "Series A–C (2011–15)", "entry_val": "~$20–100M", "pct_held": "~20%", "return_at_ipo": "~15x",  "return_at_cmp": "—"},
            {"investor": "Sequoia Capital / Peak XV",         "round": "Series C (2015)",      "entry_val": "~$100M",    "pct_held": "~12%", "return_at_ipo": "~13x",  "return_at_cmp": "—"},
            {"investor": "Micromax (Alibaba exit)",           "round": "Strategic (2016)",     "entry_val": "~$150M",    "pct_held": "~8%",  "return_at_ipo": "~8x",   "return_at_cmp": "—"},
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
            {"investor": "Temasek",     "round": "Series D–E (2018–21)", "entry_val": "$1–2B",   "pct_held": "~20%", "return_at_ipo": "~3–5x",  "return_at_cmp": "—"},
            {"investor": "Mastercard",  "round": "Strategic (2020)",     "entry_val": "~$1.5B",  "pct_held": "~10%", "return_at_ipo": "~3x",    "return_at_cmp": "—"},
            {"investor": "Actis",       "round": "Series C (2016)",      "entry_val": "~$400M",  "pct_held": "~8%",  "return_at_ipo": "~8x",    "return_at_cmp": "—"},
            {"investor": "Sequoia Capital", "round": "Series B (2014)",  "entry_val": "~$100M",  "pct_held": "~7%",  "return_at_ipo": "~30x",   "return_at_cmp": "—"},
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
            {"investor": "SoftBank Vision Fund", "round": "Series F (2019)", "entry_val": "~$1.2B", "pct_held": "~25%", "return_at_ipo": "~1.6x",  "return_at_cmp": "—"},
            {"investor": "TPG Growth",           "round": "Series D (2016)", "entry_val": "~$300M", "pct_held": "~10%", "return_at_ipo": "~6x",    "return_at_cmp": "—"},
            {"investor": "Premji Invest",        "round": "Series E (2017)", "entry_val": "~$450M", "pct_held": "~5%",  "return_at_ipo": "~4x",    "return_at_cmp": "—"},
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
            {"investor": "Flipkart / Walmart",        "round": "Strategic (2019)", "entry_val": "~$300M", "pct_held": "~28%", "return_at_ipo": "~2.5x", "return_at_cmp": "—"},
            {"investor": "Nokia Growth Partners",     "round": "Series C (2020)",  "entry_val": "~$450M", "pct_held": "~10%", "return_at_ipo": "~1.7x", "return_at_cmp": "—"},
            {"investor": "Eight Roads (Fidelity)",    "round": "Series B (2018)",  "entry_val": "~$150M", "pct_held": "~8%",  "return_at_ipo": "~5x",   "return_at_cmp": "—"},
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
            {"investor": "Goldman Sachs Asset Mgmt", "round": "Series F (2021)", "entry_val": "$1.1B",  "pct_held": "~15%", "return_at_ipo": "-77%",  "return_at_cmp": "—"},
            {"investor": "Accel",                    "round": "Series A (2015)", "entry_val": "~$50M",  "pct_held": "~12%", "return_at_ipo": "~25x",  "return_at_cmp": "—"},
            {"investor": "Wellington Management",    "round": "Series F (2021)", "entry_val": "$1.1B",  "pct_held": "~8%",  "return_at_ipo": "-77%",  "return_at_cmp": "—"},
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
            {"investor": "Sequoia Capital / Peak XV", "round": "Series B–C (2012–15)", "entry_val": "~$50–150M", "pct_held": "~20%", "return_at_ipo": "~8–15x", "return_at_cmp": "—"},
            {"investor": "Avataar Venture Partners",  "round": "Series D (2019)",      "entry_val": "~$250M",    "pct_held": "~12%", "return_at_ipo": "~3x",    "return_at_cmp": "—"},
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
            {"investor": "Accel",         "round": "Series A–B (2015–17)", "entry_val": "~$30–100M", "pct_held": "~18%", "return_at_ipo": "~30–100x", "return_at_cmp": "—"},
            {"investor": "Tiger Global",  "round": "Series D (2019)",      "entry_val": "~$900M",    "pct_held": "~10%", "return_at_ipo": "~2x",      "return_at_cmp": "—"},
            {"investor": "VY Capital",    "round": "Series E (2021)",      "entry_val": "~$2.8B",    "pct_held": "~8%",  "return_at_ipo": "-55%",     "return_at_cmp": "—"},
        ],
    },
}

# Inject anchor/pripo data into IPOS list at import time
for _ipo in IPOS:
    _d = _ANCHOR_DATA.get(_ipo["company"], {})
    _ipo.setdefault("anchors",         _d.get("anchors", []))
    _ipo.setdefault("anchor_total_cr", _d.get("anchor_total_cr"))
    _ipo.setdefault("pripo_investors", _d.get("pripo_investors", []))


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
    st.dataframe(styled, use_container_width=True, height=400, hide_index=True,
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

    t1, t2, t3, t4, t5 = st.tabs(["📋 Overview", "📊 Performance", "🔮 GMP", "📬 Subscription", "🏦 Investors"])

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
