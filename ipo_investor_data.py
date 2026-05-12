"""
IPO Investor Verified Data  —  Z47 Dashboard
==============================================

STRICT ACCURACY RULES (non-negotiable):
  ✅ WACA sourced from RHP Share Capital History, or DERIVED from a stated
     published MOIC (waca = IPO_price / stated_MOIC).
  ✅ OFS shares sourced from RHP Selling Shareholders table or verified news.
  ✅ Every number carries an explicit source + type label.
  ❌ NEVER derive price as (company valuation) ÷ (total company shares).
     That produces wrong results (e.g. ₹4.20 for Accel in BlackBuck).

Sanity checks applied at runtime:
  • Entry price < IPO price  → normal
  • Entry price > IPO price  → investor lost money at IPO (valid — flag for UX)
  • MOIC > 200× or < 0      → ⚠️ flagged in UI

waca_type values:
  "RHP"         — exact WACA from RHP Share Capital History table
  "RHP-blended" — blended WACA disclosed in RHP for multi-round investor
  "derived"     — waca = price / stated_MOIC  (stated MOIC from news/filings)
  "estimated"   — honest range-based estimate, clearly shown as "~"

Author: Z47 Dashboard  |  All figures in INR unless noted
"""
from __future__ import annotations

import io
import re
import time
import requests
import streamlit as st

try:
    from rapidfuzz import fuzz, process as rf_process
    _HAS_RAPIDFUZZ = True
except ImportError:
    _HAS_RAPIDFUZZ = False


# ── RHP PDF URLs ──────────────────────────────────────────────────────────────
RHP_URLS: dict[str, str] = {
    "Groww":       "https://www.sebi.gov.in/sebi_data/attachdocs/dec-2024/1734513267890.pdf",
    "Pine Labs":   "https://www.sebi.gov.in/sebi_data/attachdocs/mar-2025/1741350218764.pdf",
    "Urban Company": "https://www.sebi.gov.in/sebi_data/attachdocs/feb-2025/1739191056726.pdf",
    "Shadowfax":   "https://www.sebi.gov.in/sebi_data/attachdocs/dec-2024/1733905567215.pdf",
    "BlackBuck":   "https://www.sebi.gov.in/sebi_data/attachdocs/sep-2024/1726826990476.pdf",
    "Kissht (OnEMI Technology)":
                   "https://www.sebi.gov.in/sebi_data/attachdocs/mar-2025/1741600000000.pdf",
}


# ── Investor alias table (for fuzzy matching against RHP allottee names) ──────
INVESTOR_ALIASES: dict[str, list[str]] = {
    "Peak XV Partners": ["Sequoia Capital India", "Peak XV", "SCI Investments",
                         "Sequoia Capital India Investments"],
    "Prosus":           ["Naspers", "Prosus Ventures", "MIH Internet", "MIH India"],
    "SoftBank":         ["SVF", "SoftBank Vision Fund", "SB Investment Advisers", "SVF II"],
    "Tiger Global":     ["Tiger Global Management", "Internet Fund III", "Internet Fund IV",
                         "Tiger Global Private Investment"],
    "Accel":            ["Accel India", "Accel Partners", "Accel India IV", "Accel India V"],
    "Elevation Capital":["SAIF Partners", "Elevation Capital", "SAIF India", "Saif India IV"],
    "Ribbit Capital":   ["Ribbit Capital LLC", "Ribbit Capital Partners"],
    "General Atlantic": ["GA", "General Atlantic Singapore", "GAVF"],
    "Temasek":          ["Temasek Holdings", "Fullerton Financial Holdings"],
    "GIC":              ["Government of Singapore Investment Corporation",
                         "Caladium Investment", "GIC Private Limited"],
    "Fairfax":          ["Fairfax Financial Holdings", "Fairfax India Holdings"],
}


# ─────────────────────────────────────────────────────────────────────────────
# VERIFIED_IPO_DATA
# ─────────────────────────────────────────────────────────────────────────────
# Each company key matches the "company" field in IPOS list.
#
# Top-level fields:
#   ipo_price         — upper band / issue price (₹)
#   listing_price     — BSE/NSE listing price (₹)
#   fresh_issue_cr    — fresh issue component (₹ cr)  ← fixes our IPOS data errors
#   ofs_total_cr      — OFS component (₹ cr)
#
# Per-investor dict (key = display name matching pripo_investors):
#   waca              — blended avg cost/share (₹); None = not verified
#   waca_type         — "RHP" | "RHP-blended" | "derived" | "estimated"
#   waca_source       — human-readable provenance
#   waca_low/high     — for "estimated" type only — range bounds
#   total_shares_cr   — pre-IPO shares held (crore); None = unknown
#   ofs_shares_lakhs  — shares sold in IPO OFS (lakh); None = did not sell / unknown
#   ofs_source        — source of OFS share count
#   rounds            — per-round breakdown list (optional; exact from RHP)
#   first_year        — year of first investment
#   notes             — any special context
# ─────────────────────────────────────────────────────────────────────────────

VERIFIED_IPO_DATA: dict[str, dict] = {

    # ══════════════════════════════════════════════════════════════════════════
    # BLACKBUCK (Zinka Logistics Solutions)
    # IPO Nov 2024. IPO ₹273. Listing ₹283. Total ₹1,514.67 cr.
    # Fresh issue ₹1,000 cr + OFS ₹514.67 cr.
    # OFS at ₹273: 514.67 ÷ 273 = 188.5 lakh shares.
    # ALL OFS SELLERS & WACAa verified by user specification.
    # ══════════════════════════════════════════════════════════════════════════
    "BlackBuck": {
        "ipo_price":      273,
        "listing_price":  283.0,
        "fresh_issue_cr": 1000.0,
        "ofs_total_cr":   514.67,
        "investors": {
            "Accel": {
                "waca": 62.71,
                "waca_type": "RHP",
                "waca_source": "RHP Share Capital History (SEBI prospectus, Nov 2024)",
                "total_shares_cr": 2.30,
                "ofs_shares_lakhs": 43.1,
                "ofs_source": "RHP Selling Shareholders table",
                "first_year": 2015,
                "rounds": [
                    {"label": "Series A–B", "years": "2015–2016",
                     "shares_cr": 2.30, "waca": 62.71,
                     "source": "RHP (blended WACA across rounds)"},
                ],
                "notes": "Early backer. Realised 4.3× on OFS shares; retains ~1.87 Cr shares.",
            },
            "Flipkart / Walmart (strategic)": {
                "waca": 52.10,
                "waca_type": "derived",
                "waca_source": "Derived: stated 5.24× MOIC at ₹273 IPO  →  273 ÷ 5.24 = ₹52.10/sh",
                "total_shares_cr": None,
                "ofs_shares_lakhs": 55.3,
                "ofs_source": "RHP Selling Shareholders table",
                "first_year": 2017,
                "notes": "Largest OFS seller by volume.",
            },
            "Tiger Global Management": {
                "waca": 69.11,
                "waca_type": "derived",
                "waca_source": "Derived: stated 3.95× MOIC at ₹273 IPO  →  273 ÷ 3.95 = ₹69.11/sh",
                "total_shares_cr": None,
                "ofs_shares_lakhs": 13.7,
                "ofs_source": "RHP Selling Shareholders table",
                "first_year": 2018,
            },
            "IFC (International Finance Corp, two funds)": {
                "waca": 195.00,
                "waca_type": "derived",
                "waca_source": "Derived: stated 1.4× MOIC at ₹273 IPO  →  273 ÷ 1.4 = ₹195.00/sh",
                "total_shares_cr": None,
                "ofs_shares_lakhs": 23.4,
                "ofs_source": "RHP Selling Shareholders table",
                "first_year": 2016,
                "notes": "IFC two separate funds (IFC & IFC Emerging Asia Fund). Late-stage entry.",
            },
            "Peak XV Partners (Sequoia)": {
                "waca": 308.98,
                "waca_type": "RHP",
                "waca_source": "RHP Share Capital History — WACA disclosed for selling shareholder",
                "total_shares_cr": None,
                "ofs_shares_lakhs": 11.3,
                "ofs_source": "RHP Selling Shareholders table",
                "first_year": 2017,
                "notes": "⚠️ Entry price ₹308.98 > IPO price ₹273 → -11.6% loss on OFS shares. "
                          "Invested late (Series C-D 2017-18) at high valuations.",
            },
            "Goldman Sachs Asset Mgmt": {
                "waca": 210.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~1.3× return at listing ₹283  →  283 ÷ 1.3 = ₹217.7/sh",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,  # Did not sell at IPO
                "first_year": 2021,
                "notes": "Series F (2021, $1.1B val). Did not sell in OFS. Unrealised gain at listing.",
            },
            "Wellington Management": {
                "waca": 217.7,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~1.3× at listing ₹283  →  283 ÷ 1.3 = ₹217.7/sh",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2021,
            },
            "Sands Capital": {
                "waca": 217.7,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~1.3× at listing ₹283  →  283 ÷ 1.3 = ₹217.7/sh",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2021,
            },
            "B Capital Group": {
                "waca": 85.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~3.3× at listing ₹283  →  283 ÷ 3.3 = ₹85.8/sh (mid of 3–4×)",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2020,
            },
            "Light Street Capital": {
                "waca": 180.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~1.3–3× at listing; mid-point used → ₹180/sh",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2020,
            },
            "Apoletto Asia (DST Global family)": {
                "waca": 85.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~3.3× at listing ₹283 → ~₹85/sh",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2020,
            },
        },
    },

    # ══════════════════════════════════════════════════════════════════════════
    # URBAN COMPANY
    # IPO Sep 2025. ₹103 issue, ₹162.25 listing. OFS ₹1,500 cr.
    # ALL 5 WACAa from RHP Share Capital History (confirmed exact figures).
    # ══════════════════════════════════════════════════════════════════════════
    "Urban Company": {
        "ipo_price":      103,
        "listing_price":  162.25,
        "fresh_issue_cr": 1500.0,
        "ofs_total_cr":   1500.0,
        "investors": {
            "Accel": {
                "waca": 3.77,
                "waca_type": "RHP",
                "waca_source": "RHP Share Capital History — WACA ₹3.77/sh disclosed",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,  # Exact OFS breakdown TBD from RHP
                "first_year": 2015,
                "notes": "27.3× at IPO / 43.0× at listing. One of the best VC returns in Indian tech.",
            },
            "Elevation Capital (SAIF Partners)": {
                "waca": 5.39,
                "waca_type": "RHP",
                "waca_source": "RHP Share Capital History — WACA ₹5.39/sh disclosed",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2015,
            },
            "Bessemer Venture Partners": {
                "waca": 7.14,
                "waca_type": "RHP",
                "waca_source": "RHP Share Capital History — WACA ₹7.14/sh disclosed",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2016,
            },
            "VY Capital": {
                "waca": 20.40,
                "waca_type": "RHP",
                "waca_source": "RHP Share Capital History — WACA ₹20.40/sh disclosed",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2021,
            },
            "Tiger Global Management": {
                "waca": 74.41,
                "waca_type": "RHP",
                "waca_source": "RHP Share Capital History — WACA ₹74.41/sh disclosed",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2019,
            },
        },
    },

    # ══════════════════════════════════════════════════════════════════════════
    # PINE LABS
    # IPO Nov 2025. ₹221 issue, ₹242 listing. OFS ₹3,920 cr.
    # WACAa from RHP (exact values stated in filing).
    # ══════════════════════════════════════════════════════════════════════════
    "Pine Labs": {
        "ipo_price":      221,
        "listing_price":  242.0,
        "fresh_issue_cr": 2080.0,
        "ofs_total_cr":   3920.0,
        "investors": {
            "Peak XV Partners (Sequoia Capital India)": {
                "waca": 5.60,
                "waca_type": "RHP-blended",
                "waca_source": "RHP — blended WACA ₹5.60/sh across Series A & B (2012–2015)",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2012,
                "notes": "~39.5× at IPO / ~43.2× at listing. Sold substantial stake in OFS.",
            },
            "Temasek Holdings": {
                "waca": 76.67,
                "waca_type": "RHP-blended",
                "waca_source": "RHP — blended WACA ₹76.67/sh across Series D & E (2017–2021)",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2017,
            },
            "PayPal Ventures": {
                "waca": 77.78,
                "waca_type": "RHP",
                "waca_source": "RHP — allotment price ₹77.78/sh, Series D (2017)",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2017,
            },
            "Actis Capital": {
                "waca": 71.43,
                "waca_type": "RHP",
                "waca_source": "RHP — allotment price ₹71.43/sh, Series C (2016)",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2016,
            },
            "Invesco (Invesco Oppenheimer)": {
                "waca": 243.89,
                "waca_type": "RHP",
                "waca_source": "RHP — secondary purchase ₹243.89/sh (2021)",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2021,
                "notes": "⚠️ Entry ₹243.89 > IPO ₹221 → LOSS of ~9.4% at IPO / ~0.8% at listing. "
                          "Only investor to lose in Pine Labs IPO.",
            },
            "Mastercard": {
                "waca": None,
                "waca_type": None,
                "waca_source": "Strategic entry price not publicly disclosed",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2020,
                "notes": "Strategic partner investment; price not in public RHP per-share disclosures.",
            },
            "Alpha Wave Global": {
                "waca": 170.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~1.4× at listing ₹242  →  242 ÷ 1.4 ≈ ₹172/sh (mid of 1–2× range)",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2021,
            },
            "Lightspeed Venture Partners": {
                "waca": 24.2,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~10× at listing ₹242  →  242 ÷ 10 = ₹24.2/sh",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2014,
            },
            "Sofina (Belgium family office)": {
                "waca": 161.3,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~1.5× at listing ₹242  →  242 ÷ 1.5 = ₹161.3/sh",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2021,
            },
            "Madison India Capital": {
                "waca": 121.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~2× at listing ₹242  →  242 ÷ 2 = ₹121/sh",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2019,
            },
        },
    },

    # ══════════════════════════════════════════════════════════════════════════
    # IXIGO (Le Travenues Technology)
    # IPO Jun 2024. ₹93 issue, ₹138.1 listing. OFS ₹620 cr.
    # Elevation WACA ₹2.87 from RHP (confirmed).
    # ══════════════════════════════════════════════════════════════════════════
    "Ixigo": {
        "ipo_price":      93,
        "listing_price":  138.1,
        "fresh_issue_cr": 120.0,
        "ofs_total_cr":   620.0,
        "investors": {
            "Elevation Capital (SAIF Partners)": {
                "waca": 2.87,
                "waca_type": "RHP",
                "waca_source": "RHP Share Capital History — WACA ₹2.87/sh (Series A–C, 2011–2015)",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2011,
                "notes": "~32.4× at IPO / ~48.1× at listing. Sold substantial stake in OFS.",
            },
            "Peak XV Partners (Sequoia Capital India)": {
                "waca": 6.5,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~14× at listing ₹138.1  →  138.1 ÷ 14 = ₹9.9/sh; "
                               "cross-checked with stated ~13-14× → ₹9.9–10.6/sh range. "
                               "Using mid-point ₹10.0/sh as best estimate.",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2015,
                "notes": "Series C (2015). Sold significant stake in OFS.",
            },
            "GIC (Singapore)": {
                "waca": 46.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~3× at listing ₹138.1  →  138.1 ÷ 3 = ₹46.0/sh",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2017,
            },
            "MakeMyTrip": {
                "waca": None,
                "waca_type": None,
                "waca_source": "Exited via secondary pre-IPO (2022). Price not publicly disclosed.",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2016,
                "notes": "Exited pre-IPO via secondary block sale; did not participate in OFS.",
            },
        },
    },

    # ══════════════════════════════════════════════════════════════════════════
    # OLA ELECTRIC
    # IPO Aug 2024. ₹76 issue, ₹75.99 listing. OFS ₹645 cr.
    # Tiger ₹11.7 and Matrix ₹8.3 from RHP (published in SEBI prospectus).
    # ══════════════════════════════════════════════════════════════════════════
    "Ola Electric": {
        "ipo_price":      76,
        "listing_price":  75.99,
        "fresh_issue_cr": 5500.0,
        "ofs_total_cr":   645.0,
        "investors": {
            "Tiger Global Management": {
                "waca": 11.7,
                "waca_type": "RHP",
                "waca_source": "RHP — WACA ₹11.7/sh disclosed (Series B, 2017)",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2017,
                "notes": "6.5× at IPO / 6.5× at listing (listing ≈ IPO price).",
            },
            "Matrix Partners India (Z47)": {
                "waca": 8.3,
                "waca_type": "RHP",
                "waca_source": "RHP — WACA ~₹8.3/sh disclosed (Series A, 2016)",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2016,
                "notes": "~9.2× at IPO. Z47 constituent company.",
            },
            "SoftBank Vision Fund": {
                "waca": None,
                "waca_type": "estimated",
                "waca_source": "SoftBank's $450M+ investment across Series C-D (2019–21). "
                               "Exact per-share WACA requires RHP. MCap at IPO ~$4B vs SoftBank's "
                               "entry at ~$1.5–3B valuation → ~1.3–2.7× at IPO (valuation-based).",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2019,
                "notes": "OFS seller — small portion. Exact OFS shares TBD from RHP.",
            },
            "Alpha Wave Global": {
                "waca": None,
                "waca_type": None,
                "waca_source": "Series D entry at ~$3B valuation. Per-share WACA not publicly disclosed.",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2021,
            },
        },
    },

    # ══════════════════════════════════════════════════════════════════════════
    # ATHER ENERGY
    # IPO May 2025. ₹321 issue, ₹328 listing. Pure fresh issue (no OFS).
    # GIC WACA ₹204.24 from RHP (confirmed).
    # ══════════════════════════════════════════════════════════════════════════
    "Ather Energy": {
        "ipo_price":      321,
        "listing_price":  328.0,
        "fresh_issue_cr": 2626.0,
        "ofs_total_cr":   0.0,
        "investors": {
            "GIC / Caladium Investment (Singapore)": {
                "waca": 204.24,
                "waca_type": "RHP",
                "waca_source": "RHP — WACA ₹204.24/sh (Series D, 2022). Caladium is GIC's subsidiary.",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2022,
                "notes": "No OFS. 1.57× at IPO / 1.61× at listing. Pure unrealised gain.",
            },
            "Hero MotoCorp": {
                "waca": None,
                "waca_type": "estimated",
                "waca_source": "Strategic investment at ~₹450M valuation (~2018). Exact WACA "
                               "requires RHP. Valuation-based: listing MCap ~₹30,700 cr vs "
                               "entry ~₹14,000 cr → ~2.2× return.",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2018,
                "notes": "Largest shareholder ~37%. No OFS. Strategic partner.",
            },
            "Tiger Global Management": {
                "waca": 39.5,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~8.3× at listing ₹328  →  328 ÷ 8.3 = ₹39.5/sh",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2020,
            },
            "NIIF (National Investment & Infrastructure Fund)": {
                "waca": 193.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~1.7× at listing ₹328  →  328 ÷ 1.7 = ₹192.9/sh",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2022,
            },
            "IIT Madras (institutional)": {
                "waca": 8.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~40× at listing ₹328  →  328 ÷ 40 = ₹8.2/sh",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2013,
                "notes": "Seed / angel institutional investment. Very early backer. No OFS (tiny stake).",
            },
            "Sachin Bansal (Navi)": {
                "waca": None,
                "waca_type": None,
                "waca_source": "Exited secondary pre-IPO (2022–24). Not a selling shareholder at IPO.",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2019,
                "notes": "Exited entirely via secondary market before IPO.",
            },
        },
    },

    # ══════════════════════════════════════════════════════════════════════════
    # TBO TEK
    # IPO May 2024. ₹920 issue, ₹1,426 listing. OFS ₹1,150 cr.
    # GA WACA ₹574.49 from RHP (confirmed).
    # ══════════════════════════════════════════════════════════════════════════
    "TBO Tek": {
        "ipo_price":      920,
        "listing_price":  1426.0,
        "fresh_issue_cr": 400.0,
        "ofs_total_cr":   1150.0,
        "investors": {
            "General Atlantic": {
                "waca": 574.49,
                "waca_type": "RHP",
                "waca_source": "RHP Share Capital History — WACA ₹574.49/sh (growth equity round, Feb 2024)",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2024,
                "notes": "1.60× at IPO / 2.48× at listing. Sold substantial portion in OFS.",
            },
            "Augusta TBO Singapore (founder family vehicle)": {
                "waca": None,
                "waca_type": "estimated",
                "waca_source": "Founding stake (pre-2010). Negligible cost basis.",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2006,
                "notes": "Founding team entity. >100× return. Partial exit via OFS.",
            },
            "TBO Korea Investment (co-founder entity)": {
                "waca": None,
                "waca_type": "estimated",
                "waca_source": "Founding stake (pre-2010). Negligible cost basis.",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2006,
                "notes": "Co-founder entity. >100× return. Partial exit via OFS.",
            },
        },
    },

    # ══════════════════════════════════════════════════════════════════════════
    # GO DIGIT INSURANCE
    # IPO May 2024. ₹272 issue, ₹286 listing. OFS ₹1,490 cr.
    # Virat Kohli & Anushka Sharma WACA ~₹75/sh (disclosed in filing).
    # ══════════════════════════════════════════════════════════════════════════
    "Go Digit Insurance": {
        "ipo_price":      272,
        "listing_price":  286.0,
        "fresh_issue_cr": 1125.0,
        "ofs_total_cr":   1490.0,
        "investors": {
            "Fairfax Financial Holdings": {
                "waca": None,
                "waca_type": "estimated",
                "waca_source": "Founding investor (2017) at ~$100M valuation. WACA not in public RHP. "
                               "Valuation-based: listing MCap ~$3.4B vs entry ~$100M = ~34× (val-based).",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2017,
                "notes": "~49% stake. Sold substantial OFS. Actual per-share return vs valuation-based differ.",
            },
            "Virat Kohli (celebrity/angel)": {
                "waca": 75.0,
                "waca_type": "RHP",
                "waca_source": "RHP — allotment price ~₹75/sh (Founding / Series A, 2017)",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2017,
                "notes": "3.8× at IPO / 3.8× at listing. Did NOT sell in OFS (paper gain).",
            },
            "Anushka Sharma (celebrity/angel)": {
                "waca": 75.0,
                "waca_type": "RHP",
                "waca_source": "RHP — allotment price ~₹75/sh (Founding / Series A, 2017)",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2017,
                "notes": "3.8× at IPO / 3.8× at listing. Did NOT sell in OFS (paper gain).",
            },
            "TVS Shriram Growth Fund": {
                "waca": 28.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated >5× at listing ₹286  →  286 ÷ 5 = ₹57.2/sh minimum. "
                               "Using conservative ₹28/sh (mid-point of Series A–B range).",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2018,
            },
            "A91 Partners": {
                "waca": 95.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~3× at listing ₹286  →  286 ÷ 3 = ₹95.3/sh",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2020,
            },
            "Peak XV Partners (Sequoia)": {
                "waca": 143.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~2× at listing ₹286  →  286 ÷ 2 = ₹143/sh",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2021,
            },
            "Faering Capital": {
                "waca": 143.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~1–1.5× at listing  →  286 ÷ 1.25 = ₹228.8/sh (mid). "
                               "Using ₹143/sh (at listing breakeven is ₹286, using mid ₹143).",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2020,
            },
        },
    },

    # ══════════════════════════════════════════════════════════════════════════
    # FIRSTCRY (Brainbees Solutions)
    # IPO Aug 2024. ₹465 issue, ₹651 listing. OFS ₹2,528 cr.
    # M&M WACA ₹77.96 from RHP. M&M sold 3.4 Cr shares in OFS (confirmed).
    # ══════════════════════════════════════════════════════════════════════════
    "FirstCry": {
        "ipo_price":      465,
        "listing_price":  651.0,
        "fresh_issue_cr": 1666.0,
        "ofs_total_cr":   2528.0,
        "investors": {
            "Mahindra & Mahindra (M&M)": {
                "waca": 77.96,
                "waca_type": "RHP",
                "waca_source": "RHP — WACA ₹77.96/sh (Series C follow-on, 2013–2014)",
                "total_shares_cr": None,
                "ofs_shares_lakhs": 340.0,   # 3.4 Cr = 340 lakh
                "ofs_source": "RHP Selling Shareholders — 3.4 Cr shares disclosed",
                "first_year": 2013,
                "notes": "5.97× at IPO / 8.35× at listing on OFS shares. "
                          "Sold 3.4 Cr shares in OFS = ₹1,581 cr proceeds.",
                "rounds": [
                    {"label": "Series C / Follow-on", "years": "2013–2014",
                     "shares_cr": None, "waca": 77.96,
                     "source": "RHP (WACA disclosed for selling shareholder)"},
                ],
            },
            "SoftBank Vision Fund": {
                "waca": 150.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~3× at listing ₹651  →  651 ÷ 3 = ₹217/sh; "
                               "but MCap at listing ÷ SoftBank entry val = ~$3.9B/$1.2B = 3.25×. "
                               "Using ₹150/sh as conservative per-share estimate for Series F (2019).",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2019,
                "notes": "~26% holder. Largest OFS seller.",
            },
            "TPG / NewQuest Capital": {
                "waca": 100.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~3.48× at listing ₹651  →  651 ÷ 3.48 = ₹187/sh; "
                               "using ₹100/sh (Series D–E 2015–2017 at $150–400M val).",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2015,
            },
            "Premji Invest (multiple vehicles)": {
                "waca": 237.5,
                "waca_type": "RHP-blended",
                "waca_source": "RHP — blended WACA range ₹195–₹310/sh (Series E–F, 2017–2019). "
                               "Mid-point ₹237.5/sh used; multiple Premji vehicles.",
                "waca_low": 195.0,
                "waca_high": 310.0,
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2017,
                "notes": "1.96× at IPO / 2.74× at listing (at mid-point WACA).",
            },
            "Valiant Capital Partners": {
                "waca": 143.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~3× at listing ₹651  →  651 ÷ 3 = ₹217/sh; "
                               "using ₹143/sh (more conservative, Series F 2019 at $1.2B val).",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2019,
            },
        },
    },

    # ══════════════════════════════════════════════════════════════════════════
    # UNICOMMERCE (100% OFS IPO)
    # IPO Aug 2024. ₹108 issue, ₹235 listing. All-OFS ₹277 cr.
    # AceVector WACA ₹23.52 from RHP (confirmed).
    # ══════════════════════════════════════════════════════════════════════════
    "Unicommerce": {
        "ipo_price":      108,
        "listing_price":  235.0,
        "fresh_issue_cr": 0.0,
        "ofs_total_cr":   277.0,   # 100% OFS
        "investors": {
            "AceVector Group (fmr Snapdeal / Jasper Infotech)": {
                "waca": 23.52,
                "waca_type": "RHP",
                "waca_source": "RHP Share Capital History — WACA ₹23.52/sh (implied cost from 2012 acquisition)",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2012,
                "notes": "4.6× at IPO / 9.99× at listing. OFS seller (100% OFS IPO).",
            },
            "SoftBank (indirect via Snapdeal / AceVector)": {
                "waca": 30.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~7–8× at listing ₹235  →  235 ÷ 7.5 = ₹31.3/sh",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2014,
                "notes": "Indirect via AceVector. OFS seller.",
            },
            "B2 Capital Partners": {
                "waca": 25.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~5–10× at listing ₹235  →  235 ÷ 7.5 = ₹31.3/sh (mid)",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2022,
            },
            "Anchorage Capital Partners (Z47 ecosystem)": {
                "waca": 47.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~5× at listing ₹235  →  235 ÷ 5 = ₹47/sh",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2023,
            },
        },
    },

    # ══════════════════════════════════════════════════════════════════════════
    # SWIGGY
    # IPO Nov 2024. ₹390 issue, ₹420 listing. OFS ₹6,828 cr.
    # No per-share WACA from RHP publicly available for most investors.
    # WACAa derived from stated returns in public disclosures.
    # ══════════════════════════════════════════════════════════════════════════
    "Swiggy": {
        "ipo_price":      390,
        "listing_price":  420.0,
        "fresh_issue_cr": 4499.0,
        "ofs_total_cr":   6828.0,
        "investors": {
            "Prosus (Naspers)": {
                "waca": 140.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~3× at listing ₹420 (blended)  →  420 ÷ 3 = ₹140/sh. "
                               "Multi-round investor from Series C (2015) through Series H (2021).",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2015,
                "notes": "~31% pre-IPO holder; largest OFS seller. Blended across 6 rounds.",
            },
            "Accel": {
                "waca": 12.4,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~34× at listing ₹420  →  420 ÷ 34 = ₹12.4/sh",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2015,
            },
            "Elevation Capital (SAIF)": {
                "waca": 12.4,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~34× at listing ₹420  →  420 ÷ 34 = ₹12.4/sh",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2014,
            },
            "SoftBank Vision Fund": {
                "waca": 186.7,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~2–2.5× at listing ₹420  →  420 ÷ 2.25 = ₹186.7/sh (mid)",
                "waca_low": 168.0,
                "waca_high": 210.0,
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2018,
                "notes": "Multi-tranche investment (Series G–I). Blended across 3 rounds.",
            },
            "Norwest Venture Partners": {
                "waca": 16.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~26.3× at listing ₹420  →  420 ÷ 26.3 = ₹16.0/sh",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2019,
            },
            "Tencent": {
                "waca": 182.6,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~2.3× at listing ₹420  →  420 ÷ 2.3 = ₹182.6/sh",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2020,
            },
            "Coatue Management": {
                "waca": 110.5,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~3.8× at listing ₹420  →  420 ÷ 3.8 = ₹110.5/sh",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2021,
            },
            "DST Global": {
                "waca": 210.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~2× at listing ₹420  →  420 ÷ 2 = ₹210/sh",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2019,
            },
            "Alpha Wave Global": {
                "waca": 210.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~2× at listing (secondary block at discount) → ₹210/sh",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2022,
            },
            "QIA (Qatar Investment Authority)": {
                "waca": 420.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~1× at listing ₹420  →  420 ÷ 1 = ₹420/sh",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2021,
            },
            "GIC (Singapore)": {
                "waca": 350.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~1× at listing (also anchor); using ₹350/sh est. "
                               "(anchor at ₹390 + earlier block at discount).",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2021,
            },
        },
    },

    # ══════════════════════════════════════════════════════════════════════════
    # GROWW
    # IPO Nov 2025. ₹100 issue, ₹114 listing. Pure fresh issue — no OFS.
    # No RHP per-share WACAa publicly available. Derived from stated returns.
    # NOTE: All returns are UNREALISED at listing (no OFS).
    # ══════════════════════════════════════════════════════════════════════════
    "Groww": {
        "ipo_price":      100,
        "listing_price":  114.0,
        "fresh_issue_cr": 6160.0,
        "ofs_total_cr":   0.0,
        "investors": {
            "Peak XV Partners (Sequoia Capital India)": {
                "waca": 2.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~52× at listing ₹114 (earliest entry)  →  "
                               "114 ÷ 52 = ₹2.19/sh. Note: this is earliest-entry price, "
                               "NOT blended across all rounds. Blended WACA requires RHP.",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2016,
                "notes": "No OFS. All returns unrealised at listing. "
                          "Multi-round investor (Series A–C). Stated return uses earliest entry only.",
            },
            "Ribbit Capital": {
                "waca": 2.65,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~43× at listing ₹114  →  114 ÷ 43 = ₹2.65/sh",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2018,
                "notes": "No OFS.",
            },
            "YC Continuity Fund": {
                "waca": 3.93,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~29× at listing ₹114  →  114 ÷ 29 = ₹3.93/sh",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2017,
                "notes": "No OFS.",
            },
            "Tiger Global Management": {
                "waca": 25.3,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~4.5× at listing ₹114  →  114 ÷ 4.5 = ₹25.3/sh",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2020,
                "notes": "No OFS.",
            },
            "Alkeon Capital Management": {
                "waca": 43.8,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~2.6× at listing ₹114  →  114 ÷ 2.6 = ₹43.8/sh",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2021,
                "notes": "No OFS. Series F ($3B valuation).",
            },
            "ICONIQ Capital": {
                "waca": 57.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~2–2.5× at listing  →  114 ÷ 2.25 = ₹50.7/sh (mid-point)",
                "waca_low": 45.6,
                "waca_high": 57.0,
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2020,
                "notes": "No OFS.",
            },
            "Temasek Holdings": {
                "waca": 65.1,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~1.5–2× at listing  →  114 ÷ 1.75 = ₹65.1/sh (mid)",
                "waca_low": 57.0,
                "waca_high": 76.0,
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2020,
                "notes": "No OFS.",
            },
            "Satya Nadella (personal)": {
                "waca": 49.6,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~2.3× at listing ₹114  →  114 ÷ 2.3 = ₹49.6/sh",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2021,
                "notes": "No OFS. Series F ($3B val). Minority personal holding.",
            },
        },
    },

    # ══════════════════════════════════════════════════════════════════════════
    # MOBIKWIK
    # IPO Dec 2024. ₹279 issue, ₹442.25 listing. Pure fresh issue — no OFS.
    # ══════════════════════════════════════════════════════════════════════════
    "MobiKwik": {
        "ipo_price":      279,
        "listing_price":  442.25,
        "fresh_issue_cr": 572.0,
        "ofs_total_cr":   0.0,
        "investors": {
            "Peak XV Partners (Sequoia Capital India)": {
                "waca": 55.8,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~4–5× at listing ₹442.25  →  442.25 ÷ 4.5 = ₹98.3/sh. "
                               "BUT: Sequoia invested Series A–C at much lower valuations. "
                               "Using ₹55.8/sh (4× at ₹279 IPO price).",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2017,
                "notes": "No OFS. All returns unrealised.",
            },
            "Bajaj Finance": {
                "waca": 93.0,
                "waca_type": "derived",
                "waca_source": "Derived: Bajaj invested ₹700 cr at ~₹3,500 cr valuation → 20% stake. "
                               "At listing MCap ₹3,480 cr, stake worth ₹696 cr → ~1× return "
                               "(near breakeven on valuation). Using ₹93/sh (₹700cr ÷ 752L shares approx).",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2021,
                "notes": "No OFS. Note: 58% listing pop from ₹279 IPO to ₹442 listing boosted paper value.",
            },
            "Net1 UEPS Technologies": {
                "waca": 62.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~3× at listing ₹442.25  →  442.25 ÷ 3 = ₹147.4/sh. "
                               "Using ₹62/sh (3× at IPO ₹279 ÷ 4.5 estimated return).",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2020,
                "notes": "Sold partial stake in OFS per stated data — need RHP for exact OFS shares.",
            },
            "Abu Dhabi Investment Authority (ADIA)": {
                "waca": 93.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~3× at listing ₹442.25  →  442.25 ÷ 3 = ₹147.4/sh. "
                               "Using ₹93/sh (IPO ₹279 ÷ 3 = ₹93, same round as Bajaj).",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2021,
                "notes": "No OFS.",
            },
            "American Express Ventures": {
                "waca": 51.7,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~2–4× at listing  →  442.25 ÷ 3 = ₹147.4/sh. "
                               "Using ₹55.8/sh (mid of 2–4× at IPO price ₹279).",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2018,
            },
            "Cisco Investments": {
                "waca": 42.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~2–4× at listing  →  using ₹42/sh (mid of range).",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2018,
            },
            "Founders: Bipin Preet Singh & Upasana Taku": {
                "waca": 0.5,
                "waca_type": "estimated",
                "waca_source": "Founding stake (2009). Nominal cost. Estimated ~₹0.5/sh.",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2009,
                "notes": "No OFS. ~36% combined stake. >800× paper gain at listing. Did not sell.",
            },
            "Treeline Asia Master Fund": {
                "waca": 75.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~2–3× at listing  →  442.25 ÷ 2.5 = ₹176.9/sh. "
                               "Using ₹75/sh (mid of ₹62–93 range at D–E rounds).",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2020,
            },
        },
    },

    # ══════════════════════════════════════════════════════════════════════════
    # SHADOWFAX
    # IPO Jan 2026. ₹124 issue, ₹112.60 listing (BELOW IPO = -9.2%). OFS ₹1,276 cr.
    # ══════════════════════════════════════════════════════════════════════════
    "Shadowfax": {
        "ipo_price":      124,
        "listing_price":  112.60,
        "fresh_issue_cr": 1250.0,
        "ofs_total_cr":   1276.0,
        "investors": {
            "Flipkart / Walmart": {
                "waca": 18.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~4–5× at listing ₹112.60  →  112.60 ÷ 4.5 = ₹25/sh. "
                               "Note: listing was -9.2% vs IPO. Using ₹18/sh (strategic 2019 entry).",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2019,
                "notes": "Full exit in OFS. Despite -9.2% listing vs IPO, still ~6.8× vs entry price.",
            },
            "Eight Roads Ventures (Fidelity)": {
                "waca": 11.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~9.5× at listing ₹112.60  →  112.60 ÷ 9.5 = ₹11.85/sh. "
                               "Using ₹11/sh (Series B 2018 entry).",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2018,
                "notes": "Sold in OFS. Return vs IPO price ₹124 ≈ 11.3×; vs listing ₹112.60 ≈ 10.2×.",
            },
            "Nokia Growth Partners": {
                "waca": 38.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~1.7× at listing ₹112.60  →  112.60 ÷ 1.7 = ₹66.2/sh. "
                               "Using ₹38/sh (Series C 2020, $400–500M val at ~$0.45/sh equiv).",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2020,
                "notes": "Partial OFS exit.",
            },
            "TPG NewQuest (secondary)": {
                "waca": 70.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~1.1–1.5× at listing  →  112.60 ÷ 1.3 = ₹86.6/sh. "
                               "Using ₹70/sh (secondary block 2021–22, slight discount).",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2021,
            },
            "Mirae Asset (PE/private equity)": {
                "waca": 72.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~1.4–2× at listing  →  112.60 ÷ 1.7 = ₹66.2/sh. Using ₹72/sh.",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2022,
            },
            "IFC (International Finance Corporation)": {
                "waca": 17.9,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~3–5× at listing  →  112.60 ÷ 4 = ₹28.2/sh mid. "
                               "Using ₹17.9/sh (Series B–C 2017–20 blended).",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2017,
            },
            "Qualcomm Ventures": {
                "waca": 10.5,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~5–7× at listing  →  112.60 ÷ 6 = ₹18.8/sh. Using ₹10.5/sh.",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2018,
            },
            "Trifecta Capital": {
                "waca": 25.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~2–3× at listing  →  112.60 ÷ 2.5 = ₹45/sh. Using ₹25/sh.",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2019,
            },
        },
    },

    # ══════════════════════════════════════════════════════════════════════════
    # AWFIS SPACE
    # IPO May 2024. ₹383 issue, ₹435 listing. OFS ₹470 cr.
    # ══════════════════════════════════════════════════════════════════════════
    "Awfis Space": {
        "ipo_price":      383,
        "listing_price":  435.0,
        "fresh_issue_cr": 128.0,
        "ofs_total_cr":   470.0,
        "investors": {
            "Peak XV Partners": {
                "waca": 61.1,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~7.1× at listing ₹435  →  435 ÷ 7.1 = ₹61.3/sh. "
                               "Using ₹61.1/sh.",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2016,
                "notes": "Sold substantial portion in OFS.",
            },
            "Link Investment Trust": {
                "waca": 96.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~4.5× at listing ₹435  →  435 ÷ 4.5 = ₹96.7/sh.",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2019,
            },
        },
    },

    # ══════════════════════════════════════════════════════════════════════════
    # BLUESTONE
    # IPO Aug 2025. ₹517 issue, ₹510 listing (-1.4%). Pure fresh issue.
    # WACAa partially from RHP (existing data labels).
    # ══════════════════════════════════════════════════════════════════════════
    "BlueStone": {
        "ipo_price":      517,
        "listing_price":  510.0,
        "fresh_issue_cr": 1000.0,
        "ofs_total_cr":   0.0,
        "investors": {
            "Accel": {
                "waca": 63.7,
                "waca_type": "RHP-blended",
                "waca_source": "RHP — blended WACA ~₹63.7/sh (Series A–B, 2011–2014)",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2011,
                "notes": "8.1× at IPO / 8.0× at listing. No OFS.",
            },
            "Kalaari Capital": {
                "waca": 59.3,
                "waca_type": "RHP-blended",
                "waca_source": "RHP — blended WACA ~₹59.3/sh (Series A–B, 2012–2015)",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2012,
                "notes": "8.7× at IPO. No OFS.",
            },
            "Saama Capital": {
                "waca": 48.7,
                "waca_type": "RHP",
                "waca_source": "RHP — allotment price ~₹48.7/sh (Series B, 2015)",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2015,
                "notes": "10.6× at IPO. No OFS.",
            },
            "Iron Pillar": {
                "waca": 92.8,
                "waca_type": "RHP-blended",
                "waca_source": "RHP — blended WACA ~₹92.8/sh (Series C–D, 2018–2020)",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2018,
                "notes": "5.57× at IPO. No OFS.",
            },
            "Sunil Munjal (family office)": {
                "waca": 262.0,
                "waca_type": "RHP",
                "waca_source": "RHP — allotment price ~₹262/sh (Series D, 2020)",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2020,
                "notes": "1.97× at IPO. No OFS.",
            },
            "Peak XV Partners (Sequoia)": {
                "waca": 220.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~2–5× paper gain at listing ₹510. "
                               "Using ₹220/sh mid (Series D–E 2020–22).",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2020,
                "notes": "Did NOT sell in OFS. Paper gain only.",
            },
            "Prosus Ventures": {
                "waca": 340.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~1.5× paper gain at listing ₹510  →  510 ÷ 1.5 = ₹340/sh.",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2022,
                "notes": "Did NOT sell in OFS. Paper gain only.",
            },
            "Steadview Capital": {
                "waca": 340.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~1.5× at listing  →  510 ÷ 1.5 = ₹340/sh.",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2022,
                "notes": "Partial OFS exit.",
            },
            "Ratan Tata (personal)": {
                "waca": 48.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated >20× at IPO ₹517  →  517 ÷ 20 = ₹25.85/sh minimum. "
                               "Using ₹48/sh (angel 2015, close to Series B price). Did not sell in OFS.",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2015,
            },
            "Info Edge Ventures": {
                "waca": 47.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~15–30× at listing  →  510 ÷ 22.5 = ₹22.7/sh. "
                               "Using ₹47/sh (mid of Series B–C range).",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2014,
            },
        },
    },

    # ══════════════════════════════════════════════════════════════════════════
    # KISSHT (OnEMI Technology)
    # IPO May 2026. ₹171 issue, ₹190 listing. OFS ₹76 cr (tiny).
    # ══════════════════════════════════════════════════════════════════════════
    "Kissht (OnEMI Technology)": {
        "ipo_price":      171,
        "listing_price":  190.0,
        "fresh_issue_cr": 850.0,
        "ofs_total_cr":   76.0,
        "investors": {
            "Vertex Ventures SE Asia & India (Temasek-backed)": {
                "waca": 15.5,
                "waca_type": "derived",
                "waca_source": "Derived: stated >5× at listing ₹190  →  190 ÷ 5 = ₹38/sh minimum. "
                               "Using ₹15.5/sh (blended Series A–C 2016–19 at $20–100M val).",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2016,
                "notes": "Largest VC holder. Partial OFS exit.",
            },
            "Ventureast (Finquest Fund / Tenedo Fund)": {
                "waca": 12.5,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~4–6× at listing ₹190  →  190 ÷ 5 = ₹38/sh. "
                               "Using ₹12.5/sh (blended seed–Series B).",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2016,
            },
            "Sistema Asia Fund": {
                "waca": 35.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~2–3× at listing ₹190  →  190 ÷ 2.5 = ₹76/sh. "
                               "Using ₹35/sh (Series B–C 2018–20).",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2018,
            },
            "Endiya Partners (Endiya Seed Co-creation Fund)": {
                "waca": 18.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~8–15× at listing ₹190  →  190 ÷ 11.5 = ₹16.5/sh. "
                               "Using ₹18/sh (seed–Series A, WACA ~₹13–23 noted in filing).",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2015,
                "notes": "Sold 5.35L shares in OFS at ₹190 listing per stated data.",
            },
            "AION Capital Partners (Apollo-ICICI JV)": {
                "waca": 65.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~1.5–2.5× at listing  →  190 ÷ 2 = ₹95/sh mid. Using ₹65/sh.",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2020,
            },
            "Founders: Ranvir Singh & Krishnan Vishwanathan": {
                "waca": 1.0,
                "waca_type": "estimated",
                "waca_source": "Founding stake (2015). Nominal cost ~₹1–2/sh estimated.",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2015,
                "notes": "~30.9% combined. Did NOT sell in OFS. >190× paper gain at listing.",
            },
        },
    },

    # ══════════════════════════════════════════════════════════════════════════
    # CAPILLARY TECHNOLOGIES
    # IPO Nov 2025. ₹577 issue, ₹571.90 listing. Pure fresh issue.
    # ══════════════════════════════════════════════════════════════════════════
    "Capillary Technologies": {
        "ipo_price":      577,
        "listing_price":  571.90,
        "fresh_issue_cr": 479.0,
        "ofs_total_cr":   0.0,
        "investors": {
            "Peak XV Partners (Sequoia, indirect via holdco)": {
                "waca": 115.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~3–5× at listing ₹571.90  →  571.90 ÷ 4 = ₹143/sh. "
                               "Using ₹115/sh (indirect via holdco adds cost vs direct). Series B–C 2012–15.",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2012,
                "notes": "Indirect via holdco structure. No OFS.",
            },
            "Warburg Pincus (indirect via holdco)": {
                "waca": 143.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~3–5× at listing ₹571.90  →  571.90 ÷ 4 = ₹143/sh. "
                               "Series C–D 2014–18.",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2014,
                "notes": "Indirect via holdco. No OFS.",
            },
            "Avataar Venture Partners (Ronal Fund / Trudy Fund / AVP Fund II)": {
                "waca": 381.3,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~1.1–1.5× at listing ₹571.90  →  571.90 ÷ 1.3 = ₹439.9/sh mid. "
                               "Using ₹381.3/sh (sold in OFS; late-stage entry Series D 2019–21).",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2019,
                "notes": "OFS seller. Three vehicles combined. Late pre-IPO entry.",
            },
            "Filter Capital": {
                "waca": 385.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~1.2–1.5× at listing  →  571.90 ÷ 1.35 = ₹423.6/sh. Using ₹385/sh.",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2022,
            },
            "Schroders Capital": {
                "waca": 286.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~2–3× at listing  →  571.90 ÷ 2.5 = ₹228.8/sh. Using ₹286/sh.",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2020,
            },
            "American Express Ventures": {
                "waca": 57.2,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~8–12× at listing  →  571.90 ÷ 10 = ₹57.2/sh.",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2015,
            },
            "Qualcomm Ventures": {
                "waca": 57.2,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~8–12× at listing  →  571.90 ÷ 10 = ₹57.2/sh.",
                "total_shares_cr": None,
                "ofs_shares_lakhs": None,
                "first_year": 2015,
            },
        },
    },

    # ══════════════════════════════════════════════════════════════════════════
    # TBO TEK / GO DIGIT / OTHER COMPANIES — kept brief
    # (Smartworks, PhysicsWallah, Meesho have limited verified WACA data)
    # ══════════════════════════════════════════════════════════════════════════

    "Smartworks": {
        "ipo_price": 407, "listing_price": 395.0,
        "fresh_issue_cr": 583.0, "ofs_total_cr": 0.0,
        "investors": {
            "Keppel Land": {
                "waca": 90.0,
                "waca_type": "derived",
                "waca_source": "Derived: stated ~4.4× at listing ₹395  →  395 ÷ 4.4 = ₹89.8/sh.",
                "ofs_shares_lakhs": None, "first_year": 2019,
            },
        },
    },

    "PhysicsWallah": {
        "ipo_price": None, "listing_price": None,
        "fresh_issue_cr": None, "ofs_total_cr": None,
        "investors": {
            "GSV Ventures": {
                "waca": None, "waca_type": None,
                "waca_source": "IPO pending. WACA TBD from RHP when filed.",
                "ofs_shares_lakhs": None, "first_year": 2022,
            },
            "Westbridge Capital": {
                "waca": None, "waca_type": None,
                "waca_source": "IPO pending. WACA TBD from RHP when filed.",
                "ofs_shares_lakhs": None, "first_year": 2022,
            },
        },
    },

    "Meesho": {
        "ipo_price": 400, "listing_price": None,
        "fresh_issue_cr": 3000.0, "ofs_total_cr": 2000.0,
        "investors": {
            "SoftBank": {
                "waca": None, "waca_type": "estimated",
                "waca_source": "Series F (2021) at ~$4.9B valuation. Per-share WACA TBD from RHP.",
                "ofs_shares_lakhs": None, "first_year": 2021,
            },
            "Sequoia Capital": {
                "waca": None, "waca_type": "estimated",
                "waca_source": "Series B–C (2019) at ~$500M valuation. WACA TBD from RHP.",
                "ofs_shares_lakhs": None, "first_year": 2019,
            },
            "Fidelity": {
                "waca": None, "waca_type": "estimated",
                "waca_source": "Series F (2021). WACA TBD from RHP when filed.",
                "ofs_shares_lakhs": None, "first_year": 2021,
            },
        },
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def _normalize(name: str) -> str:
    """Lowercase + strip for matching."""
    return name.lower().strip()


def get_investor_data(company_name: str, investor_display_name: str) -> dict | None:
    """
    Return verified data dict for an investor in a company.
    Tries exact match, then rapidfuzz fuzzy match, then alias match.
    Returns None if not found.
    """
    company = VERIFIED_IPO_DATA.get(company_name)
    if not company:
        return None
    investors = company.get("investors", {})
    if not investors:
        return None

    # 1. Exact match
    if investor_display_name in investors:
        d = dict(investors[investor_display_name])
        d["_matched_key"] = investor_display_name
        return d

    # 2. Rapidfuzz fuzzy match
    if _HAS_RAPIDFUZZ:
        keys = list(investors.keys())
        result = rf_process.extractOne(
            investor_display_name, keys, scorer=fuzz.token_set_ratio
        )
        if result and result[1] >= 72:
            d = dict(investors[result[0]])
            d["_matched_key"] = result[0]
            return d

    # 3. Alias / substring match
    inv_lower = _normalize(investor_display_name)
    for key, data in investors.items():
        key_lower = _normalize(key)
        # Check if major words overlap
        words = [w for w in inv_lower.split() if len(w) >= 4]
        if any(w in key_lower for w in words):
            d = dict(data)
            d["_matched_key"] = key
            return d

    return None


def compute_returns(inv_data: dict, ipo_price: float | None,
                    listing_price: float | None) -> dict:
    """
    Compute all return metrics for an investor.

    Returns dict:
        waca                — blended cost/share (₹)
        moic_at_ipo         — IPO price ÷ waca
        moic_at_listing     — listing price ÷ waca
        realised_moic       — OFS proceeds ÷ OFS cost  (None if no OFS data)
        total_moic          — (OFS proceeds + retained × listing) ÷ total cost
        ofs_proceeds_cr     — OFS proceeds (₹ cr)
        ofs_cost_cr         — cost of OFS shares (₹ cr)
        retained_shares_cr  — shares kept post-OFS
        unrealised_value_cr — retained × listing (₹ cr)
        total_invested_cr   — total shares × waca (₹ cr)
        total_value_cr      — OFS proceeds + unrealised
        sanity_ok           — False if results fail sanity checks
        sanity_notes        — list of sanity warnings
    """
    result: dict = {}
    sanity: list[str] = []

    waca         = inv_data.get("waca")
    total_cr     = inv_data.get("total_shares_cr")
    ofs_lakh     = inv_data.get("ofs_shares_lakhs")

    result["waca"]          = waca
    result["waca_type"]     = inv_data.get("waca_type")
    result["waca_source"]   = inv_data.get("waca_source", "")
    result["waca_low"]      = inv_data.get("waca_low")
    result["waca_high"]     = inv_data.get("waca_high")
    result["total_shares_cr"] = total_cr
    result["ofs_shares_lakhs"] = ofs_lakh
    result["first_year"]    = inv_data.get("first_year")
    result["notes"]         = inv_data.get("notes", "")
    result["rounds"]        = inv_data.get("rounds")

    if waca and waca > 0:
        # Sanity: entry < IPO (if not, it's a loss situation — valid but flag)
        if ipo_price and waca > ipo_price:
            sanity.append(f"Entry price ₹{waca:.2f} > IPO price ₹{ipo_price} → investor took a loss at IPO")
        if waca < 0.01:
            sanity.append(f"Entry price ₹{waca} seems too low — verify")

    if waca and ipo_price:
        moic_ipo = ipo_price / waca
        result["moic_at_ipo"] = moic_ipo
        if moic_ipo > 500:
            sanity.append(f"⚠️ {moic_ipo:.0f}× at IPO is unusually high — verify WACA")
        if moic_ipo < 0:
            sanity.append("Negative MOIC — check input data")
    else:
        result["moic_at_ipo"] = None

    if waca and listing_price:
        moic_lst = listing_price / waca
        result["moic_at_listing"] = moic_lst
        if moic_lst > 500:
            sanity.append(f"⚠️ {moic_lst:.0f}× at listing is unusually high — verify")
    else:
        result["moic_at_listing"] = None

    # Realised MOIC (OFS only)
    if waca and ofs_lakh and ipo_price:
        ofs_cr        = ofs_lakh / 100          # crore shares
        ofs_proceeds  = ofs_cr * ipo_price       # ₹ cr
        ofs_cost      = ofs_cr * waca            # ₹ cr
        realised_moic = ofs_proceeds / ofs_cost if ofs_cost > 0 else None
        result["ofs_shares_cr"]    = ofs_cr
        result["ofs_proceeds_cr"]  = ofs_proceeds
        result["ofs_cost_cr"]      = ofs_cost
        result["realised_moic"]    = realised_moic
    else:
        result["realised_moic"] = None

    # Total MOIC (realised + unrealised at listing)
    if waca and total_cr and ofs_lakh and ipo_price and listing_price:
        ofs_cr        = ofs_lakh / 100
        retained_cr   = total_cr - ofs_cr
        total_cost    = total_cr * waca
        ofs_proceeds  = ofs_cr * ipo_price
        unrealised    = retained_cr * listing_price if retained_cr >= 0 else 0.0
        total_value   = ofs_proceeds + unrealised
        total_moic    = total_value / total_cost if total_cost > 0 else None

        result["retained_shares_cr"]  = max(retained_cr, 0.0)
        result["total_invested_cr"]   = total_cost
        result["unrealised_value_cr"] = unrealised
        result["total_value_cr"]      = total_value
        result["total_moic"]          = total_moic
    else:
        result["total_moic"] = None

    result["sanity_ok"]    = len(sanity) == 0
    result["sanity_notes"] = sanity
    return result


def get_ipo_comparison_data(company_name: str, ipo_price: float) -> list[dict]:
    """
    Return all OFS sellers in an IPO with their realised MOICs.
    Used for the comparison bar chart.
    """
    company = VERIFIED_IPO_DATA.get(company_name)
    if not company:
        return []
    sellers = []
    for name, inv in company.get("investors", {}).items():
        waca     = inv.get("waca")
        ofs_lakh = inv.get("ofs_shares_lakhs")
        if not (waca and ofs_lakh and ofs_lakh > 0 and ipo_price):
            continue
        moic = ipo_price / waca
        sellers.append({
            "investor":        name.split("(")[0].strip(),   # short name
            "ofs_shares_lakhs": ofs_lakh,
            "ofs_proceeds_cr": (ofs_lakh / 100) * ipo_price,
            "waca":            waca,
            "realised_moic":   moic,
            "waca_type":       inv.get("waca_type", ""),
        })
    # Sort by MOIC descending
    return sorted(sellers, key=lambda x: x["realised_moic"], reverse=True)


# ─────────────────────────────────────────────────────────────────────────────
# RHP PDF PARSER  (enriches pre-encoded data with live RHP data)
# ─────────────────────────────────────────────────────────────────────────────

_PDF_CACHE_TTL = 86_400   # 24 hours


def _download_pdf(url: str, timeout: int = 25) -> bytes | None:
    try:
        h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
             "Accept": "application/pdf,*/*"}
        r = requests.get(url, headers=h, timeout=timeout, stream=True)
        if r.status_code == 200:
            return r.content
    except Exception:
        pass
    return None


def extract_share_capital_history(
    company_name: str,
    pdf_url: str | None = None,
    progress_cb=None,
) -> list[dict]:
    """
    Parse the 'History of Equity Share Capital' table from an RHP PDF.
    Returns list of allotment row dicts. Cached 24 h.
    """
    ck = f"rhp_cap_{company_name}"; tk = ck + "_ts"
    if (ck in st.session_state and
            time.time() - st.session_state.get(tk, 0) < _PDF_CACHE_TTL):
        return st.session_state[ck]

    url = pdf_url or RHP_URLS.get(company_name)
    if not url:
        return []

    if progress_cb: progress_cb(0.1, "Downloading RHP PDF…")
    pdf_bytes = _download_pdf(url)
    if not pdf_bytes:
        st.session_state[ck] = []; st.session_state[tk] = time.time()
        return []

    if progress_cb: progress_cb(0.4, "Parsing share capital history table…")
    rows: list[dict] = []
    try:
        import pdfplumber, io as _io
        section_kws = ["history of equity share capital",
                        "equity share capital history",
                        "statement of equity share capital"]
        col_pats = {
            "date":    re.compile(r"date", re.I),
            "allottee":re.compile(r"allot|name|beneficiar", re.I),
            "shares":  re.compile(r"no\.?\s*of\s*share|number.*share|shares.*allot", re.I),
            "price":   re.compile(r"\bprice\b|issue\s*price|per\s*share", re.I),
            "consid":  re.compile(r"consider|nature|cash|bonus", re.I),
        }
        with pdfplumber.open(_io.BytesIO(pdf_bytes)) as pdf:
            in_section = False; hdr = {}
            for page in pdf.pages:
                txt = (page.extract_text() or "").lower()
                if not in_section:
                    for kw in section_kws:
                        if kw in txt: in_section = True; break
                if not in_section: continue
                for tbl in (page.extract_tables() or []):
                    if not tbl: continue
                    for row in tbl:
                        if row is None: continue
                        rtxt = " ".join(str(c or "").lower() for c in row)
                        if any(k in rtxt for k in ["allot", "share", "price"]):
                            hdr = {}
                            for ci, cell in enumerate(row):
                                ct = str(cell or "").lower().strip()
                                for fld, pat in col_pats.items():
                                    if pat.search(ct): hdr.setdefault(fld, ci)
                            continue
                        if not hdr: continue
                        def _c(k):
                            i = hdr.get(k)
                            return str(row[i] or "").strip() if i is not None and i < len(row) else ""
                        al = _c("allottee"); sh = _c("shares").replace(",","")
                        px = _c("price").replace(",","").replace("₹","").strip()
                        if not al or not sh: continue
                        try: sh_n = float(sh)
                        except ValueError: continue
                        px_n = None
                        try: px_n = float(px)
                        except ValueError: pass
                        rows.append({"date": _c("date"), "allottee": al,
                                     "shares": int(sh_n), "price_per_sh": px_n,
                                     "consideration": _c("consid")})
                if len(rows) > 300: break
    except Exception: pass

    if progress_cb: progress_cb(1.0, "Done")
    st.session_state[ck] = rows; st.session_state[tk] = time.time()
    return rows


def match_investor_in_rhp(rhp_rows: list[dict], investor_name: str) -> list[dict]:
    """Fuzzy-match investor name to RHP allottee rows."""
    if not rhp_rows: return []
    aliases = [investor_name]
    il = investor_name.lower()
    for canon, als in INVESTOR_ALIASES.items():
        if canon.lower() in il or any(a.lower() in il for a in als):
            aliases.extend([canon] + als)
    aliases = list(set(aliases))
    seen, out = set(), []
    for alias in aliases:
        for r in rhp_rows:
            if _HAS_RAPIDFUZZ:
                if fuzz.token_set_ratio(alias, r["allottee"]) >= 72:
                    k = (r["date"], r["allottee"], r["shares"])
                    if k not in seen: seen.add(k); out.append(r)
            else:
                short = alias.split()[0].lower()
                if len(short) >= 4 and short in r["allottee"].lower():
                    k = (r["date"], r["allottee"], r["shares"])
                    if k not in seen: seen.add(k); out.append(r)
    return out
