"""DRHP Filings module — called by app.py routing."""
import streamlit as st
import requests
import pandas as pd
import pytz
import time
import json
import os
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
from bs4 import BeautifulSoup
from z47_assistant import render_z47_assistant

# ── Feature 6: Hardcoded IPO Takeaways ───────────────────────────────────────
# Single source of truth lives in takeaway_constants.HARDCODED_IPO_TAKEAWAYS.
# Imported here so both the DRHP tab and Z47fortyseven tab pull from one place.
try:
    from takeaway_constants import HARDCODED_IPO_TAKEAWAYS
except Exception as _tk_imp_err:
    import traceback as _tb_drhp
    print(f"[WARN page_drhp] takeaway_constants import failed: {_tk_imp_err}")
    _tb_drhp.print_exc()
    HARDCODED_IPO_TAKEAWAYS = {}


def _get_ipo_takeaway_by_company(company_name: str) -> dict | None:
    """Look up a structured IPO takeaway dict by company name (exact or partial match)."""
    if not company_name:
        return None
    # 1. Exact match on company_key
    for _v in HARDCODED_IPO_TAKEAWAYS.values():
        if isinstance(_v, dict) and _v.get("company_key", "") == company_name:
            return _v
    # 2. Partial match (first word of company_name ⊂ company_key, case-insensitive)
    _slug = company_name.split("(")[0].strip().lower()
    for _v in HARDCODED_IPO_TAKEAWAYS.values():
        if isinstance(_v, dict) and _slug in _v.get("company_key", "").lower():
            return _v
    return None


import re as _re_drhp

def _pb_drhp(text: str) -> str:
    """Convert **text** bold markers to <strong> HTML."""
    return _re_drhp.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)


def render_ipo_takeaway_structured(tk_data: dict) -> None:
    """Render a structured IPO takeaway dict in purple-gradient IPOs-tab style."""
    sections   = tk_data.get("sections", [])
    sec_label  = tk_data.get("section_label", "Z47 IPO Takeaway")
    date_label = tk_data.get("date_range_label", "")
    full_title = f"{sec_label} · {date_label}" if date_label else sec_label

    body_html = ""
    for sec in sections:
        stype   = sec.get("type", "main_bullet")
        header  = sec.get("header", "")
        sub_bul = sec.get("sub_bullets", [])

        if stype == "section_title":
            body_html += (
                "<div style='margin-top:16px;padding-top:12px;"
                "border-top:1px solid #c4b5fd'>"
                "<p style='margin:0 0 8px;font-size:11px;font-weight:700;"
                "letter-spacing:0.08em;text-transform:uppercase;color:#6d28d9'>"
                f"{_pb_drhp(header)}</p>"
            )
            for sb in sub_bul:
                body_html += (
                    "<p style='margin:0 0 6px;font-size:13.5px;line-height:1.65;"
                    f"font-weight:500;color:#3b1f7a'>{_pb_drhp(sb)}</p>"
                )
            body_html += "</div>"
        else:
            if " ; " in header:
                lbl_part, verd_part = header.split(" ; ", 1)
                hdr_html = (
                    f"<span style='font-weight:700'>{_pb_drhp(lbl_part)}</span>"
                    f"<span style='color:#8b5cf6'> ; </span>"
                    f"<span style='font-weight:500'>{_pb_drhp(verd_part)}</span>"
                )
            else:
                hdr_html = f"<span style='font-weight:700'>{_pb_drhp(header)}</span>"
            body_html += (
                "<div style='margin-top:14px'>"
                "<p style='margin:0 0 6px;font-size:14px;line-height:1.5;color:#3b1f7a'>"
                "<span style='color:#7c3aed;font-weight:800;margin-right:6px'>•</span>"
                f"{hdr_html}</p>"
            )
            for sb in sub_bul:
                body_html += (
                    "<p style='margin:0 0 4px 20px;font-size:13.5px;"
                    f"line-height:1.65;color:#4c1d95'>{_pb_drhp(sb)}</p>"
                )
            body_html += "</div>"

    st.markdown(
        f"<div style='background:linear-gradient(135deg,#f3f0ff,#ede9fe);"
        f"border:1px solid #c4b5fd;border-radius:12px;padding:20px 24px;"
        f"margin:12px 0;box-shadow:0 1px 6px rgba(124,58,237,.10)'>"
        f"<div style='font-size:12px;font-weight:700;color:#6d28d9;letter-spacing:.06em;"
        f"text-transform:uppercase;margin-bottom:12px'>💡 {full_title}</div>"
        f"{body_html}"
        f"</div>",
        unsafe_allow_html=True,
    )


def _render_ipo_takeaway_box(text: str, title: str = "Z47 Takeaway", icon: str = "💡"):
    """Render a flat-string IPO takeaway in purple-gradient style (legacy fallback)."""
    st.markdown(
        f"""<div style='background:linear-gradient(135deg,#f3f0ff,#ede9fe);
        border:1px solid #c4b5fd;border-radius:12px;padding:18px 22px;
        margin:12px 0;box-shadow:0 1px 6px rgba(124,58,237,.10)'>
        <div style='font-size:12px;font-weight:700;color:#6d28d9;letter-spacing:.06em;
        text-transform:uppercase;margin-bottom:8px'>{icon} {title}</div>
        <div style='color:#3b1f7a;font-size:14px;line-height:1.65'>{text}</div>
        </div>""",
        unsafe_allow_html=True,
    )

CARD_BG = "#f6f9fd"; BG_ALT = "#edf3fa"; BORDER = "#ccdaea"
IST = pytz.timezone("Asia/Kolkata")

_NEWS_TTL      = 1800   # 30-minute news cache
_SEBI_TTL      = 1800   # 30-minute SEBI filings cache
_LIVE_IPO_TTL  = 600    # 10-minute live IPO cache
_UPCO_IPO_TTL  = 1800   # 30-minute upcoming IPO cache
_LINK_CHECK_TTL = 21600  # 6-hour URL verification cache
_SEBI_SEARCH_TTL = 86400 # 24-hour per-company SEBI search cache

# ── Companies explicitly blocked from the live auto-detected filings table ────
# Add names here (lowercase) to suppress false-positive SEBI/BSE auto-detections.
# Exact match OR substring match via _fuzzy_known will both suppress.
_LIVE_BLOCKLIST: set[str] = {
    "online instruments (india) limited",
    "sadbhav futuretech limited",
    "polite powertech limited",
}

_SCRAPE_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/120.0.0.0 Safari/537.36"),
    "Accept-Language": "en-US,en;q=0.9",
}
_IPO_KEYWORDS = [
    "ipo", "drhp", "rhp", "sebi approval", "listing", "public offering",
    "pre-ipo", "anchor investor", "grey market", "gmp", "book build",
    "zepto", "phonePe", "flipkart", "boat ipo", "oyo ipo", "fintech ipo",
    "startup ipo", "new age", "ather", "meesho", "groww", "swiggy ipo",
    "paytm ipo", "nykaa ipo", "open offer", "rights issue", "fpo",
]
_TECH_KEYWORDS = [
    "tech", "fintech", "digital", "payments", "lending", "insurance",
    "ecommerce", "software", "saas", "internet", "platform", "app",
    "online", "mobile", "data", "ai", "cloud", "b2b", "marketplace",
    "startup", "unicorn", "ventures", "food", "logistics", "health",
    "edtech", "gaming", "media", "travel", "wealthtech",
]

# ── Expanded keyword filter for auto-monitoring ──────────────────────────────
RELEVANT_KEYWORDS = [
    "tech", "technology", "digital", "internet", "online",
    "platform", "app", "mobile", "software", "saas", "cloud",
    "ai", "artificial intelligence", "data", "fintech",
    "payments", "lending", "insurance", "insurtech", "wealthtech",
    "ecommerce", "marketplace", "logistics", "delivery",
    "edtech", "healthtech", "agritech", "deeptech",
    "financial services", "nbfc", "microfinance",
    "consumer", "retail tech", "proptech", "hrtech",
    "gaming", "media tech", "foodtech", "traveltech",
    "infra", "b2b", "enterprise", "supply chain", "procurement",
]

# ── Watchlist — companies to watch for new filings ───────────────────────────
WATCHLIST = [
    "Reliance Jio", "Jio Platforms", "PhonePe", "Flipkart",
    "Swiggy", "CRED", "Dreamplug Technologies", "BharatPe",
    "Razorpay", "Slice", "Jupiter", "Groww", "Navi Technologies",
    "Byju's", "Unacademy", "ShareChat", "Dunzo", "Udaan",
    "Moglix", "OfBusiness", "Licious", "Country Delight",
    "Ola Electric", "Ather Energy", "Wakefit", "Virgio", "Fashinza",
    "Dealshare", "GlobalBees", "Honasa", "IndiaMart", "Shadowfax",
    "Porter", "Loadshare", "BlackBuck", "Rapido", "Yulu",
    "Infra.Market", "Inframarket", "Shiprocket", "Turtlemint",
    "MoneyView", "Snapdeal", "RentoMojo", "Cars24",
    "Purple Style Labs", "Pernia's", "PlaySimple", "CureFoods",
    "InCred", "OYO", "Meesho", "Lenskart", "Zepto",
    "Rebel Foods", "Faasos", "Ola Cabs", "Boat", "Imagine Marketing",
    "Pine Labs", "Capillary", "Urban Company",
    "Kissht", "Aye Finance",
    "BlueStone", "PhysicsWallah", "Smartworks",
]

# ── Hardcoded verified DRHP/RHP PDF links (PRIMARY source — never stale) ─────
# All URLs verified live May 2026. Sources: NSE Archives, BSE, SEBI commondocs.
# url: None = confidential / no public PDF.
# type: DRHP | UDRHP | RHP | CONFIDENTIAL | FILING_PAGE
# FILING_PAGE = url is an HTML filing page (not direct PDF); opens in browser.
# ── HOW TO UPDATE: find the real URL on sebi.gov.in/filings/ or nsearchives.nseindia.com
#    Verify it returns HTTP 200 before adding here. NEVER fabricate URLs.
DRHP_LINKS = {
    # ── CONFIDENTIAL / NO PUBLIC DRHP ─────────────────────────────────────────
    "Zepto": {
        "url": None,
        "type": "CONFIDENTIAL",
        "note": "SEBI approved confidential DRHP May 8 2026; public UDRHP not yet filed.",
    },
    "PhonePe": {
        "url": None,
        "type": "CONFIDENTIAL",
        "note": "Confidential DRHP filed with SEBI. Document not publicly available.",
    },
    "Ola Cabs": {
        "url": None,
        "type": "CONFIDENTIAL",
        "note": "No public DRHP found on SEBI or BSE. May be in pre-filing stage.",
    },
    "Rebel Foods (Faasos)": {
        "url": None,
        "type": "CONFIDENTIAL",
        "note": "No public DRHP found on SEBI or BSE.",
    },
    "Cars24": {
        "url": None,
        "type": "CONFIDENTIAL",
        "note": "Confidential filing. No public DRHP.",
    },
    "OYO": {
        "url": None,
        "type": "CONFIDENTIAL",
        "note": "Original 2021 DRHP lapsed. No new public filing found as of May 2026.",
    },
    "Infra.Market": {
        "url": None,
        "type": "CONFIDENTIAL",
        "note": "Filed confidentially with SEBI. No public DRHP available yet.",
    },

    # ── VERIFIED WORKING PDF LINKS (checked May 2026) ──────────────────────────
    "Meesho": {
        "url": "https://www.bseindia.com/corporates/download/381966/IPO%20Prior/MeeshoLimited_UDRHP1_20251018222146.pdf",
        "type": "UDRHP",
        "source": "BSE · SEBI filing Oct 2025",
    },
    "Lenskart": {
        "url": "https://nsearchives.nseindia.com/corporate/Registration_29072025101510_DRHP.pdf",
        "type": "DRHP",
        "source": "NSE Archives · SEBI filing Aug 2025",
    },
    "Boat (Imagine Marketing)": {
        "url": "https://nsearchives.nseindia.com/corporate/Imagine_UDRHP_1.pdf",
        "type": "UDRHP",
        "source": "NSE Archives · SEBI filing Oct 2025",
    },
    "Urban Company": {
        "url": "https://nsearchives.nseindia.com/corporate/Registration_28042025190408_UrbanCompanyDRHP.pdf",
        "type": "DRHP",
        "source": "NSE Archives · SEBI filing Apr 2025",
    },
    "Urban Company (SEBI Approved)": {
        "url": "https://nsearchives.nseindia.com/corporate/Registration_28042025190408_UrbanCompanyDRHP.pdf",
        "type": "DRHP",
        "source": "NSE Archives · SEBI filing Apr 2025",
    },
    "Pine Labs": {
        "url": "https://nsearchives.nseindia.com/corporate/Registration_26062025131338_PineLabsLimitedDRHP__.pdf",
        "type": "DRHP",
        "source": "NSE Archives · SEBI filing Jun 2025",
    },
    "Capillary Technologies": {
        "url": "https://investmentbank.kotak.com/downloads/capillary-technologies-india-limited-DRHP.pdf",
        "type": "DRHP",
        "source": "Kotak Investment Banking · SEBI filing Jun 2025",
    },
    "Groww (Billionbrains Garage)": {
        "url": "https://resources.groww.in/web-assets/media-library/2025/9/UDRHP%20-%201.pdf",
        "type": "UDRHP",
        "source": "Groww Investor Relations · SEBI filing Sep 2025",
    },
    "Shiprocket": {
        "url": "https://nsearchives.nseindia.com/corporate/Shiprocket_Limited_UDRHP_1.pdf",
        "type": "UDRHP",
        "source": "NSE Archives · SEBI filing Dec 2025",
    },
    "Turtlemint": {
        "url": "https://nsearchives.nseindia.com/corporate/Turtlemint_UDRHP_I.pdf",
        "type": "UDRHP",
        "source": "NSE Archives · SEBI filing Feb 2026",
    },
    "MoneyView": {
        "url": "https://nsearchives.nseindia.com/corporate/Registration_03032026232951_DRHP.pdf",
        "type": "DRHP",
        "source": "NSE Archives · SEBI filing Mar 2026",
    },
    "Snapdeal": {
        "url": "https://nsearchives.nseindia.com/corporate/AceVector_Limited_UDRHP_1.pdf",
        "type": "UDRHP",
        "source": "NSE Archives · AceVector Ltd · SEBI filing Dec 2025",
    },
    "RentoMojo": {
        "url": "https://www.sebi.gov.in/sebi_data/commondocs/apr-2026/Rentomojo%20Limited-Draft%20Abridged%20Prospectus_p.pdf",
        "type": "DRHP",
        "source": "SEBI · Apr 2026",
    },
    "Purple Style Labs": {
        "url": "https://nsearchives.nseindia.com/corporate/Registration_22092025202833_PurpleStyleLabsLimitedDRHP.pdf",
        "type": "DRHP",
        "source": "NSE Archives · SEBI filing Sep 2025",
    },
    "PlaySimple": {
        "url": "https://www.sebi.gov.in/sebi_data/commondocs/may-2026/Playsimple%20Games%20Limited_p.pdf",
        "type": "DRHP",
        "source": "SEBI · Apr 2026",
    },
    "InCred Holdings": {
        "url": "https://www.incredequities.com/wp-content/uploads/2026/05/InCred-Holdings-Limited-UDRHP-I.pdf",
        "type": "UDRHP",
        "source": "InCred Investor Relations · SEBI filing May 2026",
    },

    # ── FILING PAGE (HTML — no direct PDF; opens SEBI filing detail page) ───────
    "CureFoods": {
        "url": "https://www.sebi.gov.in/filings/public-issues/jul-2025/curefoods-india-limited_95013.html",
        "type": "FILING_PAGE",
        "source": "SEBI filing page · Jun 2025",
        "note": "Opens SEBI filing detail page; click the document link there.",
    },

    # ── LISTED — RHP available on SEBI/NSE/BSE ───────────────────────────────
    "Kissht": {
        "url": None,
        "type": "RHP",
        "note": "Listed 8 May 2026 (NSE: KISSHT / BSE). RHP filed with SEBI; check NSE Archives or SEBI for prospectus.",
    },
    "Aye Finance": {
        "url": None,
        "type": "RHP",
        "note": "Listed 16 Feb 2026 (NSE: AYEFIN / BSE). RHP filed with SEBI; check NSE Archives or SEBI for prospectus.",
    },

    # ── New listings added May 2026 ───────────────────────────────────────────
    "Ather Energy": {
        "url": None, "type": "RHP",
        "note": "Listed 6 May 2025. NSE: ATHERENERG.",
    },
    "BlueStone": {
        "url": None, "type": "RHP",
        "note": "Listed 19 Aug 2025. NSE: BLUESTONE.",
    },
    "Smartworks": {
        "url": None, "type": "RHP",
        "note": "Listed Oct 2025. NSE: SMARTWORKS.",
    },
    "PhysicsWallah": {
        "url": None, "type": "RHP",
        "note": "Listed 18 Nov 2025. NSE: PWL.",
    },
    "Shadowfax": {
        "url": None, "type": "RHP",
        "note": "Listed 28 Jan 2026. NSE: SHADOWFAX.",
    },
    "Kissht (OnEMI Technology Solutions)": {
        "url": None, "type": "RHP",
        "note": "Listed 8 May 2026. NSE: KISSHT.",
    },
}

# ── DRHP summaries — comprehensive 8-section brief per company ───────────────
# Sections: overview | business_model | financials | ipo_details | key_metrics
#           market_opportunity | competitive_position | investors_funding | key_risks
DRHP_SUMMARIES: dict[str, dict] = {
    "Zepto": {
        "overview": "Zepto (Kiranakart Technologies) is India's fastest-growing quick-commerce platform, delivering groceries and essentials in 10 minutes via a dense network of dark stores. Founded 2021 by Stanford dropouts Aadit Palicha (CEO) and Kaivalya Vohra (CTO). Became a unicorn in under 18 months. SEBI approved confidential DRHP May 2026.",
        "business_model": "Dark-store model: 700+ micro-fulfilment centres across 10+ cities. 10-minute delivery on 10,000+ SKUs. Revenue streams: delivery fees, platform fee, in-app advertising, Zepto Cafe (hot food), private-label products, Zepto Pass subscription, and B2B arm (Zepto for Business).",
        "financials": "Revenue FY24: ₹4,454 cr (+140% YoY from ₹1,856 cr FY23). Net loss FY24: ₹1,248 cr (down from ₹1,272 cr FY23). Contribution margin positive since Q3 FY24. GMV FY24: ~₹14,000–15,000 cr. Average order value ~₹580. Cash burn reducing each quarter.",
        "ipo_details": "DRHP filed Mar 2025 (confidential route). SEBI approval received May 8 2026; public UDRHP not yet filed. Fresh issue ~₹3,500 cr. BRLMs: Kotak, Goldman Sachs, Axis Capital. Expected valuation ~$5–6B. Use of funds: dark-store expansion, technology, working capital.",
        "key_metrics": "700+ dark stores. 10+ cities (Mumbai, Delhi, Bengaluru, Hyderabad, Chennai, Pune, Kolkata). ~12M monthly transacting users. ~100+ orders/store/day (mature stores). 10,000+ SKUs per store. Average delivery time: 8–10 minutes.",
        "market_opportunity": "Indian quick-commerce market ~$5B (2024), expected $40B+ by 2030. Total addressable market: India grocery $700B+. Quick-commerce penetration <2% of total grocery. Growth rate 40%+ YoY. Key tailwinds: urbanisation, nuclear families, smartphone adoption.",
        "competitive_position": "#2–3 player by GMV. Blinkit (Zomato) ~45% share, Swiggy Instamart ~25%, Zepto ~20%+. Differentiated on delivery speed (10-min promise) and dark-store density. Own-brand private labels and Zepto Cafe provide margin upside. Fastest growth rate among the three.",
        "investors_funding": "Total raised: ~$1.4B+. Investors: Y Combinator, Nexus Venture Partners, Glade Brook Capital, Goodwater Capital, Motilal Oswal, DST Global, Avenir Growth. Last round: Series G at $5B valuation (2024). Founders retain significant equity.",
        "key_risks": "Deep operating losses with unclear path to profitability. Intense competition from Blinkit (Zomato-backed) and Swiggy Instamart. High dark-store capex and lease obligations. Regulatory risk: FDI norms in multi-brand retail/e-commerce. Rising customer acquisition costs as market matures.",
        "source": "SEBI confidential DRHP approval May 2026 + public disclosures",
    },
    "PhonePe": {
        "overview": "PhonePe is India's largest digital payments platform with ~50% UPI market share. Spun out of Flipkart in 2022, redomiciled to India. Operates across UPI, mobile wallets, insurance distribution, mutual funds, and stockbroking. Majority-owned by Walmart post the Flipkart acquisition.",
        "business_model": "UPI payments super-app monetising via MDR on merchant payments, financial-services distribution (insurance, mutual funds, lending), platform advertising, and PhonePe Switch (mini-app store). SmartSpeaker and POS devices for merchant acquisition. Pincode app for hyperlocal discovery.",
        "financials": "Revenue FY24: ~₹5,064 cr (+74% YoY). Operating losses narrowing steadily. Path to profitability visible via financial-services revenue growth (insurance + MF now 20%+ of revenue). Gross margin level profitable.",
        "ipo_details": "Confidential DRHP filed with SEBI. Expected valuation $12–15B. Issue size ~₹7,000 cr. BRLMs: Morgan Stanley, Goldman Sachs, JPMorgan. Walmart expected to participate in OFS. Timeline: 2025–26.",
        "key_metrics": "~50% UPI market share by volume. 500M+ registered users. 250M+ MAU. $1.3T+ annualised total payment value. 37M+ merchant payment points. 140M+ insurance policies distributed. 60M+ MF investors on platform.",
        "market_opportunity": "India digital payments: ~$3T TPV by 2027. UPI volume growing 50%+ YoY. Insurance penetration <4% of GDP vs 11% globally — huge financial-services runway. Mutual fund AUM growing 20%+ YoY. Super-app TAM: entire India financial services market.",
        "competitive_position": "Dominant UPI platform: ~50% share (vs GPay ~35%, Paytm ~10%). 500M users and 37M+ merchants create high switching costs. Financial-services distribution leverages existing user trust. Strong moat in Tier 2/3 India where Google and Paytm are weaker.",
        "investors_funding": "Total raised: ~$800M+ post Flipkart split. Walmart (majority shareholder). Investors: Tiger Global, Ribbit Capital, TVS Capital. Raised $1B at $12B valuation (2023). Redomiciled to India from Singapore in 2022 for IPO eligibility.",
        "key_risks": "UPI is zero-MDR (regulatory risk to core payments revenue). Monetisation dependent on financial-services cross-sell success. Google Pay and Paytm competition. SEBI/IRDAI/RBI multi-regulator oversight. Reliance Jio Payments Bank emerging threat.",
        "source": "Public disclosures + media (confidential DRHP)",
    },
    "Meesho": {
        "overview": "Meesho is India's largest value e-commerce platform serving Tier 2–4 cities. Founded 2015 by Vidit Aatrey and Sanjeev Barnwal (IIT Delhi). Listed on NSE/BSE on 10 Dec 2025 at ₹162.50 (+46.4% vs IPO price ₹111). CMP ₹189.92 as of 14 May 2026. NSE: MEESHO | BSE: 381966.",
        "business_model": "Zero-commission marketplace for sellers (vs Amazon/Flipkart charging 5–30%). Revenue from logistics (Meesho Logistics), platform advertising, and financial services. Social commerce origin: resellers earn commissions sharing products on WhatsApp/social media. 90%+ orders from Tier 2+ cities. Average order value ~₹350.",
        "financials": "Revenue FY24: ₹7,615 cr (+33% YoY). Net loss significantly reduced YoY. Contribution margin positive since FY23. CMP ₹189.92, MCap ₹87,125 cr (14 May 2026). 52W range: ₹125.56–₹254.40. MCap at IPO listing: ₹75,676 cr.",
        "ipo_details": "✅ Listed 10 Dec 2025 @ ₹162.50 NSE (+46.4%) / ₹161.20 BSE (+45.2%). IPO price ₹111 (band ₹105–111). CMP ₹189.92 (+71.1% vs IPO price). Subscription 79×. Issue ₹3,152 cr (₹2,000 cr fresh + ₹1,152 cr OFS). BRLMs: Goldman Sachs, ICICI Securities, Kotak. Allotment: 8 Dec 2025. Pre-IPO lock-in expires: 10 Jun 2026.",
        "key_metrics": "130M+ annual transacting users. 1.5M+ active sellers. Average order value ~₹350. 90%+ orders from Tier 2+ cities. NSE: MEESHO, BSE: 381966. CMP ₹189.92, MCap ₹87,125 cr. Pre-IPO lock-in expiry: 10 Jun 2026 (large block unlock risk).",
        "market_opportunity": "India e-commerce ~$70B by 2027. Value segment (sub-₹500 orders) largely under-served by Amazon/Flipkart who focus on metro Tier 1 customers. 800M+ internet users in Tier 2–4 cities represent the next growth wave.",
        "competitive_position": "Dominant in value e-commerce for Tier 2–4 India. Zero-commission model creates strong seller loyalty vs Amazon/Flipkart. Direct competition from Flipkart (Shopsy) and Amazon India. No competitor at comparable scale for Tier 2+ value segment. Quick commerce (Blinkit, Zepto) targeting adjacent categories.",
        "investors_funding": "Key IPO-era investors: SoftBank, Peak XV Partners (Sequoia), Elevation Capital, Fidelity, Meta, B Capital, YC Continuity Fund, Prosus. OFS sellers at IPO: Elevation Capital, Peak XV, Vidit Aatrey, Sanjeev Barnwal, Venture Highway, Golden Summit, YC Continuity, Man Hay Tam, Sarin Family, Gemini Investments.",
        "key_risks": "Low average selling price limits per-order revenue and margin expansion. High logistics costs for Tier 2/3 delivery. High returns rate (~30%+). Quick-commerce competition in fast-moving categories. Pre-IPO lock-in expiry 10 Jun 2026 — large share unlock (~68%). Fashion-heavy category mix subject to seasonality.",
        "source": "NSE, yfinance — CMP ₹189.92 verified 14 May 2026",
    },
    "Urban Company": {
        "overview": "Urban Company (formerly UrbanClap) is India's largest home-services marketplace, connecting consumers with 40,000+ trained professionals for beauty, cleaning, repairs, and appliance servicing. Founded 2014 by Abhiraj Bhal, Varun Khaitan, and Raghav Chandra. Present in 50+ Indian cities and 3 international markets. SEBI approval received Apr 2025; RHP filed Sep 2025.",
        "business_model": "Asset-light marketplace model — professionals are independent partners, not employees. Services: beauty at home, cleaning, appliance repair, painting, plumbing, carpentry, pest control. Revenue: commission on each booking (15–25%) + product sales via kits. UC Pro: subscription model for professionals (tools, training, insurance, leads). International: UAE, Saudi Arabia, Singapore.",
        "financials": "Revenue FY24: ₹827 cr (+25% YoY from ₹661 cr FY23). Net loss FY24: ₹320 cr (reduced from ₹523 cr FY23). Gross margin ~70%+ (high-margin marketplace). India business EBITDA positive in key metros. International: still loss-making but improving. FY22 revenue: ₹453 cr.",
        "ipo_details": "✅ Listed 17 Sep 2025 @ ₹162.25 NSE (+57.5% vs IPO ₹103). Subscription 103.6×. Issue ₹1,900 cr. NSE: URBANCO. DRHP filed Feb 2025. RHP filed Sep 2025. SEBI approval received Apr 2025. BRLMs: Kotak Mahindra Capital, JM Financial, Axis Capital. OFS sellers: Tiger Global, VY Capital, Accel, Bessemer, Elevation Capital.",
        "key_metrics": "50M+ app downloads. 40,000+ trained professionals. 50+ service categories. 50+ Indian cities. 4 international markets (UAE, KSA, Singapore, Australia). ~10M services delivered annually. Customer rating: 4.7/5 average.",
        "market_opportunity": "India home-services market ~$20B, highly fragmented. Organised sector penetration <5%. Key growth drivers: working women, nuclear families, premium housing. International markets — UAE and Singapore: organised home services penetration growing. Global market $1T+.",
        "competitive_position": "Dominant player in premium organised home services in India with no direct national-scale competitor. Competition from local service providers (90%+ of market), Just Dial listings, Housejoy (much smaller). Network effects: more professionals → better service → more customers. UC Pro training programme creates service quality differentiation.",
        "investors_funding": "Total raised: ~$450M+. Investors: Tiger Global, VY Capital, Accel India, Elevation Capital (SAIF), Bessemer Venture Partners, Goldman Sachs, Steadview Capital. Last private valuation ~$2.8B (2021 Series F). Founders: Abhiraj Bhal (CEO), Varun Khaitan, Raghav Chandra (Chandra exited company after restructuring).",
        "key_risks": "Worker classification risk (professionals as contractors vs employees — regulatory risk). High customer acquisition cost. International business still loss-making. Service quality consistency across 40K+ partners. Commoditisation of home services in mid-market segment. Premium positioning vulnerable to economic slowdown.",
        "source": "RHP Sep 2025 + DRHP Feb 2025",
    },
    "Lenskart": {
        "overview": "Lenskart is India's largest omnichannel eyewear retailer with 2,000+ stores across India, Southeast Asia, and the Middle East. Founded 2010 by Peyush Bansal, Amit Chaudhary, and Sumeet Kapila. Acquired Japan's Owndays in 2022 for ~$400M, making it one of the largest global eyewear chains. Backed by SoftBank and KKR.",
        "business_model": "Omnichannel: online (lenskart.com) + offline stores + B2B corporate eyewear. Own brands: John Jacobs, Vincent Chase, Lenskart Blu. Home eye-check service. International via Owndays (Japan, Singapore, Philippines, Indonesia, UAE). Own lens manufacturing facilities. Revenue: product sales (80%+), eye testing fees, and B2B.",
        "financials": "Revenue FY24: ~₹5,500 cr, growing ~40% YoY. Profitable at operating level in India. International unit expanding with Owndays integration. Net profit positive in India; consolidated near breakeven due to international investment. Strong gross margins ~50%+ on own-brand eyewear.",
        "ipo_details": "DRHP filed Jan 2025. Issue size ~₹3,500 cr (fresh + OFS). BRLMs: Kotak, JM Financial. Expected valuation ~$5B. Use of funds: store expansion in India and SE Asia, technology, working capital. OFS: SoftBank, Kedaara Capital partial exit.",
        "key_metrics": "2,000+ stores globally. 40M+ customers served. 30M+ eyewear units sold. 40+ countries presence. 8,000+ employees. Average selling price ₹1,500–3,000 for prescription glasses. Owndays adds 400+ stores in Japan/SE Asia.",
        "market_opportunity": "India eyewear market ~₹15,000 cr growing 15%+ YoY. Lenskart holds ~15% market share. Global eyewear market $150B — opportunity via Owndays in Japan ($30B). Low penetration: only 40% of Indians who need glasses own them. Online eyewear: fastest growing, <5% of India market currently.",
        "competitive_position": "Dominant in India prescription eyewear online and fastest-growing offline. Competition: Titan EyePlus (Tata), Specsmakers, Vision Express, local opticians (90% of market). In international: Owndays competes with Luxottica and Safilo. Lenskart's price advantage (₹1,500 vs ₹5,000+ branded) is a strong moat. Online fitting tech (3D trial) is differentiating.",
        "investors_funding": "Total raised: ~$1.5B+. Investors: SoftBank Vision Fund (led 2022 round at $4.5B valuation), Temasek, KKR, Kedaara Capital, Premji Invest, Bay Capital. SoftBank owns ~15%. Founders hold significant equity. Peyush Bansal is also known as a Shark Tank India investor.",
        "key_risks": "Inventory-heavy model creates high working-capital needs. Franchise execution risk in international markets. Integration risk with Owndays (different culture, Japan market). Titan EyePlus (Tata backing) expanding aggressively. FX risk on USD-denominated Owndays revenues.",
        "source": "DRHP Jan 2025 + public disclosures",
    },
    "Ola Cabs": {
        "overview": "Ola (ANI Technologies) is India's second-largest ride-hailing platform, operating cabs, autos, bikes, and intercity services across 200+ cities. Distinct from Ola Electric (separately listed). Founded 2011 by Bhavish Aggarwal and Ankit Bhati. Backed by SoftBank (~20% stake).",
        "business_model": "Driver-partner marketplace: cabs, autos, e-bikes, intercity. Commission model (~20–25% per ride). Ola Money wallet, Ola Corporate (B2B enterprise), OlaPlay (in-car entertainment). International: UK and Australia. Subscription plans for drivers. EV transition: incentivising driver-partners to switch to EVs.",
        "financials": "Revenue FY24: ~₹2,800 cr. Net loss: ~₹1,523 cr. Restructuring ongoing post Ola Electric demerger. Revenue improving as ride volumes recover post-pandemic. EBITDA improving but still negative on standalone basis.",
        "ipo_details": "DRHP filed Jan 2025. Issue size ~₹5,000 cr. BRLMs: Kotak, Goldman Sachs. Expected valuation ~$4–5B (separate from Ola Electric at ~$4B). Use of funds: technology, driver incentives, EV transition support, international expansion.",
        "key_metrics": "200+ Indian cities. 2M+ registered driver-partners. 10M+ weekly rides at peak. UK and Australia operations. Auto segment #1 in many Indian cities. Corporate accounts: 5,000+ companies using Ola Corporate.",
        "market_opportunity": "India mobility market ~$50B. Ride-hailing penetration ~2–3% of all trips — massive runway. Urban mobility shifting from ownership to shared. EV transition in cabs creates synergy opportunity with Ola Electric. Tier 2/3 city mobility is largely untapped.",
        "competitive_position": "Duopoly with Uber in Indian ride-hailing. Ola ~50–55% rides, Uber ~45%. Ola stronger in Tier 2 cities and auto segment. Rapido (bikes, autos) emerging as a fast-growing competitor in commuter segment. Namma Yatri (ONDC-based) challenging the platform model in Bengaluru.",
        "investors_funding": "Total raised: ~$4B+. Investors: SoftBank Vision Fund (largest, ~18–20%), Tencent, Tiger Global, Matrix Partners India, Accel India. Bhavish Aggarwal owns ~8–10%. Multiple bridge rounds taken as IPO was delayed repeatedly since 2021.",
        "key_risks": "Uber competition (deep-pocketed global player). Driver supply volatility and incentive wars. Surge-pricing regulation. Brand overlap with Ola Electric (different company, same brand — customer confusion). UK and Australia operations burning cash. Rapido and ONDC disrupting the platform-fee model.",
        "source": "DRHP Jan 2025 + public disclosures",
    },
    "Boat (Imagine Marketing)": {
        "overview": "boAt (Imagine Marketing) is India's #1 wearables and audio brand by volume, selling earphones, smartwatches, speakers, and cables. Founded 2016 by Aman Gupta (CMO, known from Shark Tank India) and Sameer Mehta (CEO). Achieved ₹3,285 cr revenue in FY24. Backed by Warburg Pincus.",
        "business_model": "Asset-light manufacturing via ODM partners in China (transitioning some to India via PLI). D2C website + Amazon/Flipkart + 25,000+ offline retail points. Revenue: product sales (80%+), extended warranty, accessories. boAt Nirvana flagship premium line. Recent entry into truly wireless premium segment.",
        "financials": "Revenue FY24: ~₹3,285 cr (slightly down from FY23 ₹3,376 cr peak due to ASP compression). Net loss: ~₹129 cr. Revenue declined as Chinese competition compressed prices. Gross margin holding at ~35%+ despite competition.",
        "ipo_details": "DRHP filed Feb 2025. Issue size ~₹2,000 cr. BRLMs: ICICI Securities, Axis Capital. Expected valuation ~₹5,000–8,000 cr. Use of funds: R&D, India manufacturing capability, brand marketing. OFS: Warburg Pincus partial exit expected.",
        "key_metrics": "#1 earwear brand by volume in India (~35% share). 10M+ devices sold annually. 35M+ community members. 5,000+ PIN codes serviced. 2,500+ product SKUs. Average selling price declining from ₹2,000 (FY22) to ₹1,400 (FY24) due to market competition.",
        "market_opportunity": "India wearables market: ~$2B growing 25%+ YoY. Audio devices alone: ~$1B. Smartwatches: fastest growing sub-segment. Government PLI scheme for electronics manufacturing — tailwind for India production. Global D2C audio brands market: $50B+.",
        "competitive_position": "#1 in earwear by volume, #2–3 by value. CMF by Nothing (premium disruption at ₹1,999), Noise (close volume competitor), Samsung, Apple (premium) are key competitors. boAt squeezed: CMF attacks from above with better specs, no-name Chinese brands from below. Market leadership stable but margin under pressure.",
        "investors_funding": "Total raised: ~₹500 cr+. Key investor: Warburg Pincus (acquired stake 2021 at ~$300M valuation). Qualcomm Ventures (strategic). Innoven Capital (venture debt). Founders: Aman Gupta (CMO, Shark Tank India celebrity) and Sameer Mehta (CEO) hold majority. Aman Gupta's personal brand is a key marketing asset.",
        "key_risks": "Chinese component dependency (tariff risk). Declining average selling price (ASP compression). CMF by Nothing disrupting the ₹1,500–3,000 segment. IP risks (design patent disputes). India PLI manufacturing transition costs. Over-reliance on Aman Gupta's celebrity status.",
        "source": "DRHP Feb 2025 + public disclosures",
    },
    "Pine Labs": {
        "overview": "Pine Labs is a leading B2B merchant-commerce platform providing POS terminals, payment processing, BNPL, gift cards, and loyalty solutions. Founded 1998 in Singapore; India HQ in Noida. Processes ₹3T+ in annual GTV across 300,000+ merchants in 11 countries. Backed by Temasek, Mastercard, and PayPal.",
        "business_model": "B2B payments and merchant SaaS. POS terminal hardware + software (Plutus). BNPL: Bajaj Finserv Pay integration at POS. Gift card and prepaid card issuance (Qwikcilver acquisition — #1 gift card platform in India). Loyalty programs for retailers. Revenue: transactions + SaaS subscriptions + gift card float.",
        "financials": "Revenue FY24: ~₹1,620 cr (+35% YoY). Net profit turning positive. Strong recurring SaaS revenue base from gift cards and loyalty. GTV ₹3T+. India revenue ~70%, international ~30% (SE Asia and ME growing).",
        "ipo_details": "RHP filed Mar 2025. Issue size ~₹6,000 cr (fresh + OFS). BRLMs: Axis Capital, ICICI Securities, JM Financial. Expected valuation ~$5–6B. Use of funds: R&D, geographic expansion, working capital. OFS: Temasek, PayPal, Sequoia partial exit.",
        "key_metrics": "300K+ merchant touch points. 150K+ POS terminals deployed. ₹3T+ annual GTV. 11 countries (India, UAE, Malaysia, Singapore, etc.). Qwikcilver: 200+ brand clients (Myntra, Flipkart). 5M+ loyalty program members managed.",
        "market_opportunity": "India merchant payments: $100B+ market. POS market growing with UPI QR roll-out and card adoption. BNPL at POS: $50B+ TAM. Gift card market India: ₹10,000 cr growing 30% YoY. SE Asia and ME merchant payments expanding rapidly.",
        "competitive_position": "Largest merchant-payments platform in India by GTV. Key differentiator: only player combining POS + BNPL + gift card + loyalty in one platform. Competition: Razorpay (online-first, growing offline), Paytm, BharatPe (offline), Ingenico/Verifone (POS hardware-only). Strong enterprise client base: Big Bazaar, Shoppers Stop, Samsung, and 300K+ others.",
        "investors_funding": "Total raised: ~$800M+. Investors: Temasek (largest), Mastercard, PayPal, Actis, Lone Pine Capital, Sequoia Capital India, Sofina. Strategic investors (Mastercard, PayPal) invested for distribution partnership benefits. CEO: B. Amrish Rau (joined 2019; original founder Lokvir Kapoor departed).",
        "key_risks": "UPI disruption to card-payment volumes at POS. Razorpay and BharatPe expanding offline. Bajaj Finance dependency for BNPL volumes. Cross-border execution risk (11 countries). Hardware commoditisation as UPI QR reduces need for POS terminals.",
        "source": "RHP Mar 2025 + public disclosures",
    },
    "Rebel Foods (Faasos)": {
        "overview": "Rebel Foods is the world's largest cloud-kitchen operator, running 45+ food brands including Faasos, Behrouz Biryani, Ovenstory Pizza, and Mandarin Oak. Founded 2011 by Jaydeep Barman and Kallol Banerjee. 450+ kitchens across 10+ countries. Backed by SoftBank Vision Fund. No physical dining — 100% delivery-first.",
        "business_model": "Multi-brand cloud-kitchen operator. No physical dining. Each brand targets a different cuisine and occasion, sharing kitchen infrastructure. Kitchen-as-a-Service (KaaS): external QSR chains use Rebel kitchens. Revenue from orders via Zomato/Swiggy/own EatSure app. International: UAE, UK, Indonesia, Singapore.",
        "financials": "Revenue FY24: ~₹1,420 cr (down from ₹1,500 cr FY23 due to brand rationalisation). Net loss: ~₹378 cr (down from ₹675 cr FY23). Per-kitchen economics improving. Gross margins ~65%+. Cash burn reducing quarter on quarter.",
        "ipo_details": "DRHP filed Dec 2024. Issue size ~₹2,500 cr. BRLMs: JM Financial, Axis Capital. Expected valuation ~$1.5–2B (down from $5B 2021 peak). Use of funds: kitchen expansion, international, technology. OFS: SoftBank partial exit expected.",
        "key_metrics": "45+ own food brands. 450+ cloud kitchens. 3M+ orders/month at peak. International: UAE 100+ kitchens, UK, Indonesia, Singapore. EatSure app for direct delivery. KaaS: 50+ external restaurant clients.",
        "market_opportunity": "India cloud-kitchen market: ~$1B growing at 15%+ CAGR to $3B by 2027. Food delivery TAM India: ₹80,000 cr. Health food, biryani, and pizza categories growing fastest. Global cloud-kitchen market: $3B+ growing to $10B by 2027.",
        "competitive_position": "World's largest cloud-kitchen operator by brand count and kitchen count. India competition: CureFoods, Wow! Momo, individual QSR chains. Key differentiator: multi-brand platform maximises kitchen utilisation (5+ brands per kitchen). Delivery-platform dependency (Zomato/Swiggy) is both risk and moat — Rebel is a major supply-side partner.",
        "investors_funding": "Total raised: ~$750M+. Investors: SoftBank Vision Fund (led $175M round at $5B valuation 2021), Goldman Sachs, Coatue Management, Evolvence, Glade Brook Capital, Sequoia Capital India. Founders: Jaydeep Barman (CEO) and Kallol Banerjee. Valuation has significantly reset from 2021 peak.",
        "key_risks": "Heavy delivery-platform dependency (Zomato/Swiggy commission ~25%). Brand proliferation risk (quality inconsistency across 45+ brands). High kitchen setup capex and lease obligations. Food inflation impacting margins. Valuation reset from $5B peak to ~$1.5B IPO expectation is a narrative challenge.",
        "source": "DRHP Dec 2024 + public disclosures",
    },
    "OYO": {
        "overview": "OYO (Oravel Stays) is India's largest branded budget-hotel chain and global hospitality tech platform. Founded 2013 by Ritesh Agarwal (at age 19). Operations in 35+ countries with 160,000+ hotel keys. Multiple DRHP revisions since 2021 reflect an evolving strategy and valuation re-rating from $10B peak.",
        "business_model": "Hotel aggregator, operator, and brand licensor. Brands: OYO Rooms (budget), Townhouse (mid-market), Collection O (premium economy), Palette (luxury). Revenue: platform fee from property partners + corporate direct bookings. Technology: OYO OS (property management system licenced to hotels). International: UK (Innventiv acquisition), US, Europe.",
        "financials": "Revenue FY24: ~₹5,388 cr (recovery from COVID lows). Net loss: ~₹1,286 cr (reducing YoY from ₹2,800 cr FY22). India EBITDA turning positive. International restructuring completed in Europe — still loss-making in UK and US.",
        "ipo_details": "Multiple DRHP revisions since 2021. Latest DRHP Mar 2024. Issue size revised down from original ₹8,430 cr. Expected valuation ~$2.5–3B (down from $10B 2021 peak). BRLMs: Kotak, JM Financial, Citigroup. SEBI observations pending as of May 2026.",
        "key_metrics": "160,000+ hotel keys under management. 35+ countries. 12,000+ hotels in India. 4M+ customers/month at peak. OYO OS: 100K+ properties globally on platform. Corporate accounts: 5,000+ companies. Average daily rate: ₹900–1,500.",
        "market_opportunity": "India budget hospitality: ~$15B growing 10%+ YoY. Online hotel booking penetration still <30%. Bharat travel (Tier 2/3 city tourism) growing fastest post-COVID. Business travel recovery creating corporate demand. International budget travel market: $200B+.",
        "competitive_position": "Dominant in branded budget hotel segment in India — no competitor at national scale. Competition: MakeMyTrip/GoIbibo (online aggregators), Fab Hotels, Treebo (both much smaller). OYO's brand recognition in Tier 2/3 India is a strong moat. International: competes with Airbnb (leisure) and local budget chains. OYO OS is a SaaS moat vs unbranded hotel operators.",
        "investors_funding": "Total raised: ~$5B+. Investors: SoftBank Vision Fund (largest at ~45%), Airbnb (strategic ~3%), Sequoia Capital India, Lightspeed Venture Partners, Microsoft. Ritesh Agarwal bought back $2B of shares from early investors in 2019 at $10B valuation — significant dilution/leverage. Multiple valuation markdowns since.",
        "key_risks": "Property-partner disputes and contractual losses (past controversies). International losses in UK and US. SoftBank dependency and pressure for IPO exit. Brand trust issues from post-COVID controversies. Multiple DRHP revisions signal persistent business model and regulatory challenges. Airbnb disrupting leisure hospitality.",
        "source": "DRHP Mar 2024 + public disclosures",
    },
    "Infra.Market": {
        "overview": "Infra.Market is India's largest B2B construction-materials marketplace, connecting contractors and builders with manufacturers for cement, steel, tiles, paints, and 4,000+ SKUs. Founded 2016 by Souvik Sengupta and Aaditya Sharda (both IIT). India's fastest-growing B2B unicorn by revenue. Backed by Accel and Tiger Global.",
        "business_model": "B2B marketplace + own-brand manufacturing. Own labels: Shalimar Paints (acquired), Cimento (cement), AET tiles. Tech-enabled procurement: digital RFQ, bulk price discovery, credit offering (Infra.Market Credit). Working-capital financing to contractors. Revenue mix: marketplace (60%) + own-brand direct sales (40%).",
        "financials": "Revenue FY24: ~₹11,000 cr. Net profit: ~₹200 cr (profitable — rare among unicorn IPO aspirants). Gross margin ~15–20% (lower due to commodity product nature). EBITDA margin ~2–3%. Strong cash flow generation at scale.",
        "ipo_details": "DRHP filed Apr 2025. Issue size ~₹5,000 cr. BRLMs: Kotak, Goldman Sachs, ICICI Securities. Expected valuation ~$4–5B. Use of funds: own-brand manufacturing expansion, technology, working capital. OFS: Accel, Tiger Global partial exit.",
        "key_metrics": "~₹11,000 cr GMV FY24. 50,000+ customers. 4,000+ SKUs. 30+ manufacturing and brand partners. Shalimar Paints: established brand with 100+ years history. Pan-India presence: 20+ state offices. International expansion to UAE and SE Asia underway.",
        "market_opportunity": "India construction materials: ~$130B market. B2B procurement-tech penetration <5% — massive white space. India infrastructure spend: ₹11L cr+ annually under NIP (National Infrastructure Pipeline). Affordable housing (PM Awas Yojana) driving structural demand. Real estate upcycle creating near-term opportunity.",
        "competitive_position": "Largest B2B construction materials platform in India — no comparable national-scale competitor. Competition: traditional building material dealers (fragmented), Moglix (B2B industrial marketplace — adjacent segment). Shalimar Paints acquisition gives brand credibility against Asian Paints and Berger at the value end. Network effects from 50,000+ contractor relationships create high switching costs.",
        "investors_funding": "Total raised: ~$500M+. Investors: Accel India, Tiger Global, Evolvence India, Sistema Asia, Foundamental. Founders: Souvik Sengupta (CEO, IIT Bombay) and Aaditya Sharda (COO, IIT Delhi). Profitability reduces dilution pressure and validates the business model ahead of IPO.",
        "key_risks": "Construction-cycle exposure (real estate/infra slowdown). Builder credit risk (payment delays from contractors). Commoditised product mix limits pricing power. Working-capital intensity (₹1,500+ cr needed at current scale). Integration of Shalimar Paints acquisition across distribution network.",
        "source": "DRHP Apr 2025 + public disclosures",
    },
    "Shiprocket": {
        "overview": "Shiprocket is India's largest SME and D2C e-commerce logistics aggregator, enabling 1L+ merchants to ship via 17+ courier partners across 29,000+ PIN codes. Founded 2017 by Saahil Goel, Vishesh Khurana, Gautam Kapoor, and Akshay Ghulati. Backed by Temasek and Bertelsmann.",
        "business_model": "Multi-courier aggregation platform: discounted rates via bulk contracts with BlueDart, Delhivery, DTDC, FedEx, etc. Revenue: logistics margin on each shipment + fulfilment-centre fees + Shiprocket Engage (marketing automation) + Shiprocket Capital (merchant credit). International shipping to 220+ countries via partnerships.",
        "financials": "Revenue FY24: ~₹1,300 cr. Net loss reducing significantly. Contribution margin positive. Platform transactions growing 30%+ YoY. Average revenue per shipment: ₹60–80. Operating leverage improving with scale.",
        "ipo_details": "DRHP filed Jan 2025. Issue size ~₹2,000 cr. BRLMs: JM Financial, Axis Capital. Expected valuation ~$1–1.5B. Use of funds: technology, fulfilment infrastructure, international expansion, working capital.",
        "key_metrics": "1L+ merchant clients. 17+ courier partners integrated. 2M+ shipments/month. 29,000+ serviceable PIN codes. 220+ countries international reach. 10+ fulfilment centres. NPS among highest in logistics-tech category.",
        "market_opportunity": "India SME e-commerce logistics: ~$5B market. 90M+ SMEs currently underserved by traditional logistics. D2C brand count growing 30%+ YoY — Shiprocket's core market. India e-commerce logistics expected to reach $20B by 2027. Quick-commerce returns logistics: emerging opportunity.",
        "competitive_position": "Largest SME/D2C logistics aggregator in India. Competition: Nimbus, iThink Logistics, Eshipz (smaller aggregators). Also competes with direct courier sales from Delhivery, BlueDart. Key moat: deep technology integrations (Shopify, WooCommerce, Amazon, Flipkart plugins), discounted rates, and 1L+ merchant lock-in through the platform.",
        "investors_funding": "Total raised: ~$300M+. Investors: Temasek, Payoneer (strategic), March Capital Partners, Bertelsmann India, Tribe Capital. Founders: Saahil Goel (CEO), Vishesh Khurana, Gautam Kapoor, Akshay Ghulati. Strong operating leverage as shipment volumes scale past 2M/month.",
        "key_risks": "Margin squeeze: couriers negotiate harder as Shiprocket's volumes grow and they sell direct. Delhivery and BlueDart direct SME sales, bypassing aggregators. SME credit exposure (Shiprocket Capital default risk). High technology investment needed to stay competitive. International logistics execution complexity.",
        "source": "DRHP Jan 2025 + public disclosures",
    },
    "Turtlemint": {
        "overview": "Turtlemint is India's leading B2B2C insurance distribution platform, working with 1L+ licensed PoSP (Point of Sales Person) agents and embedding insurance APIs in banks and fintechs. Founded 2015 by Dhirendra Mahyavanshi and Anand Prabhudesai. Backed by Jungle Ventures and Nexus Venture Partners.",
        "business_model": "B2B2C model: (1) PoSP network — agents earn commissions distributing 40+ insurers' products via Turtlemint app; (2) Mint Pro API — embedded insurance for banks, NBFCs, and fintechs; (3) Direct consumer via Turtlemint.com. Revenue: trail commissions from insurers + tech platform fee. Products: life, health, motor, and property insurance.",
        "financials": "Revenue FY24: ~₹400 cr. Net loss reducing significantly. Revenue growing 40%+ YoY. Gross written premium: ₹3,000+ cr. Revenue share ~10–15% of GWP. Path to profitability via high-margin embedded API business.",
        "ipo_details": "DRHP filed Feb 2025. Issue size ~₹1,500 cr. BRLMs: Axis Capital, ICICI Securities. Expected valuation ~$1B. Use of funds: technology, agent network expansion, regulatory capital, marketing.",
        "key_metrics": "1L+ PoSP agent network across 500+ districts. ₹3,000+ cr gross written premium. 40+ insurance company tie-ups (HDFC Life, ICICI Prudential, Star Health, etc.). 4M+ customers insured. Present in 700+ cities.",
        "market_opportunity": "India insurance distribution: $25B market. Insurance penetration: 4% of GDP vs 10%+ global average. 500M+ underinsured Indians. IRDAI 'Insurance for All by 2047' policy — massive structural tailwind. Motor insurance (mandatory) growing with vehicle sales. Health insurance: fastest-growing post-COVID.",
        "competitive_position": "Largest tech-enabled PoSP network in India. Competition: Policybazaar (direct-to-consumer, listed), RenewBuy, InsuranceDekho (PoSP-focused). Mint Pro API differentiator — no competitor at scale in embedded insurance. Policybazaar owns the consumer channel; Turtlemint owns the agent distribution channel — complementary rather than directly competitive.",
        "investors_funding": "Total raised: ~$200M+. Investors: Jungle Ventures, Nexus Venture Partners, Blume Ventures, GGV Capital, MassMutual Ventures, American Family Ventures. Founders: Dhirendra Mahyavanshi (CEO) and Anand Prabhudesai (CTO). High-margin embedded API business provides a clear path to profitability.",
        "key_risks": "IRDAI regulatory changes (PoSP licensing rules, commission structure caps). PoSP quality control at scale (fraud, mis-selling risk, compliance). Competition from Policybazaar and InsuranceDekho for agent mindshare. Digital distribution channels bypassing agents in Tier 1 cities. Technology upgrade costs to remain competitive.",
        "source": "DRHP Feb 2025 + public disclosures",
    },
    "MoneyView": {
        "overview": "MoneyView (Whizdm Innovations) is India's leading personal-finance super-app offering personal loans, credit-score monitoring, expense tracking, and savings products. Founded 2014 by Sanjay Aggarwal and Puneet Agarwal. Operates own NBFC (MoneyView Financial Services). Profitable and backed by Tiger Global.",
        "business_model": "Personal finance app + NBFC lender. Revenue: (1) NII from own loan book; (2) Lead generation to partner lenders; (3) Insurance and MF distribution commissions; (4) Credit monitoring subscription. Targets sub-prime credit segment (CIBIL 650–750) ignored by traditional banks. Uses 200+ alternative data variables for credit decisions.",
        "financials": "Revenue FY24: ~₹1,200 cr. Net profit: ~₹150 cr (profitable — rare in consumer fintech). NIM ~12–15%. Gross NPA <3%. Collection efficiency 97%+. Loan book: ₹8,000+ cr growing 40%+ YoY.",
        "ipo_details": "DRHP filed Mar 2025. Issue size ~₹2,000 cr. BRLMs: Axis Capital, BofA Securities India, IIFL Capital Services, Kotak Mahindra Capital. Registrar: MUFG Intime India (formerly Link Intime). Expected valuation ~$1–1.5B. Use of funds: NBFC capital infusion, technology, marketing. OFS: Tiger Global partial exit expected.",
        "key_metrics": "50M+ app downloads. ₹8,000+ cr loan book. 8M+ loan disbursals since inception. Average ticket: ₹50,000–1,00,000. Loan tenure: 6–60 months. Interest rate: 16–36% p.a. Target: salaried Tier 2/3 India professionals.",
        "market_opportunity": "India personal loans market: ₹12L cr+. 400M+ credit-underserved citizens (sub-prime/thin-file borrowers). Consumer credit CAGR 20%+ through 2027. GST data, telecom data enabling better underwriting for sub-prime segment. Digital personal loan disbursals tripled post-COVID.",
        "competitive_position": "Leading tech-first NBFC in personal loans for sub-prime segment. Competition: KreditBee, Navi Finserv, EarlySalary, PaySense, Cashe. Key differentiator: own NBFC (lower cost of funds than P2P or marketplace lenders) + 50M+ app base for cross-sell. Profitable vs loss-making peers — unique positioning.",
        "investors_funding": "Total raised: ~$250M+. Investors: Tiger Global, Accel Partners, Winter Capital, Evolvence, Apis Growth Fund. Founders: Sanjay Aggarwal (CEO, IIMB) and Puneet Agarwal (CTO, IIMB). Profitability significantly reduces IPO valuation uncertainty vs loss-making fintech peers.",
        "key_risks": "Credit quality in sub-prime segment (economic downturn causes rapid NPA spike). RBI NBFC tightening (digital lending circular Nov 2022). Competition from digitally-enabled banks (IDFC First, AU SFB) entering personal loans online. Rising cost of borrowing impacting NIMs. Concentration in salaried Tier 2/3 segment.",
        "source": "DRHP Mar 2025 + public disclosures",
    },
    "Snapdeal": {
        "overview": "Snapdeal (AceVector) is India's value-focused e-commerce marketplace targeting Tier 2–4 India. Founded 2010 by Kunal Bahl and Rohit Bansal. Once valued at $6.5B, now repositioned as a pure value-commerce play after the failed Flipkart merger in 2017. Unicommerce (SaaS unit) was spun off and separately listed (2024).",
        "business_model": "Pure-play marketplace (no inventory). 500K+ sellers. Focus: sub-₹600 average order value, fashion, accessories, home decor. Revenue: seller commissions (5–15%), logistics via Vulcan Express (own logistics arm), and advertising. Post-Unicommerce spin-off, core business is leaner.",
        "financials": "Revenue FY24: ~₹500 cr. Net loss: ~₹190 cr. Revenue significantly smaller than peak ($6.5B era). Improving profitability metrics post-Unicommerce spin-off. Focus shifted to profitable growth vs scale at any cost.",
        "ipo_details": "DRHP filed Dec 2024. Issue size ~₹1,250 cr. BRLMs: JM Financial, Axis Capital, IIFL. Expected valuation ~$500M–1B (vs $6.5B peak). Use of funds: technology, seller ecosystem, marketing. OFS: SoftBank, Nexus, Kalaari exiting.",
        "key_metrics": "60M+ registered users. 500K+ sellers. Average order value ~₹600. 95%+ orders in value fashion and lifestyle. Vulcan Express: 29,000+ serviceable PIN codes. Present in 3,000+ cities.",
        "market_opportunity": "India value e-commerce: Tier 2–4 India has 400M+ internet users growing 20% YoY. Value fashion (sub-₹1,000) is the largest and fastest-growing e-commerce category. 500M+ mobile internet users expected, mostly value-oriented. Adjacent to Meesho's market.",
        "competitive_position": "Niche value-commerce player in Tier 2/3 India. Intense competition from Meesho (dominant, zero-commission model), Flipkart (Shopsy), Amazon (Bazaar). Snapdeal's brand recognition persists in value segment despite challenges. Much smaller scale than Meesho — strategic acquirer or niche IPO candidate.",
        "investors_funding": "Total raised: ~$1.7B+. Investors: SoftBank (largest), Nexus Venture Partners, Kalaari Capital, eBay (exited), Alibaba (exited), Foxconn. Founders: Kunal Bahl (CEO) and Rohit Bansal (COO). Most marquee investors seeking exit at IPO via OFS. Unicommerce spin-off (separately listed 2024) provided partial value realisation.",
        "key_risks": "Meesho competition rapidly eroding market share (Meesho's zero-commission model is structurally superior). Brand perception challenges post the 2017 Flipkart merger failure narrative. Execution post-Unicommerce spin-off. Valuation reset from $6.5B to sub-$1B. OFS-heavy structure means proceeds go to exiting investors, not the company.",
        "source": "DRHP Dec 2024 + public disclosures",
    },
    "RentoMojo": {
        "overview": "RentoMojo is India's leading furniture and appliance rental-subscription platform, offering monthly rental plans for beds, sofas, washing machines, TVs, and ACs. Founded 2014 by Geetansh Bamania and Ajay Nain. Targets urban migrants and millennials preferring access over ownership. Backed by Accel and Bain Capital.",
        "business_model": "Subscription rental model: customers pay monthly rent. Own delivery, setup, and maintenance teams. Revenue: monthly rentals + pickup/delivery fees + damage protection plans. Asset on balance sheet creates depreciation but also residual value via resale of used furniture. No minimum contract period for most products.",
        "financials": "Revenue FY24: ~₹350 cr. Approaching profitability. Strong recurring-revenue base (90%+ monthly renewal rate). Net Revenue Retention >100% (customers add items over time). AUM (Assets Under Rental Management): ₹600 cr+.",
        "ipo_details": "DRHP filed Nov 2024. Issue size ~₹800 cr. BRLMs: IIFL Securities, Axis Capital. Expected valuation ~₹3,000–5,000 cr. Use of funds: fleet expansion (more furniture procurement), new city entry, technology platform.",
        "key_metrics": "200,000+ active subscribers. 15+ cities (Mumbai, Bengaluru, Delhi, Hyderabad, Pune, Chennai, Noida). 90%+ monthly renewal rate. ₹600 cr+ assets under management. Average monthly rental: ₹1,500–4,000 per subscriber. NPS 70+ (high loyalty).",
        "market_opportunity": "India furniture rental: $1B+ estimated. 100M+ urban migrants who relocate frequently are the primary market. Work-from-home trend increased home furnishing demand. Rental penetration in furniture/appliances <1% — massive headroom. Aspirational urban consumers upgrading frequently without buying.",
        "competitive_position": "Market leader in organised furniture rental in India. Competition: Furlenco (pivoted to subscription-purchase), GrabOnRent, local unorganised vendors. RentoMojo's multi-city presence and end-to-end service model (delivery + setup + maintenance) creates a clear moat. No national-scale competitor at the same quality level.",
        "investors_funding": "Total raised: ~$80M+. Investors: Accel India, Bain Capital Ventures, Renaud Laplanche (founder of LendingClub, US — strategic), IDG Ventures. Founders: Geetansh Bamania (CEO, IIT Guwahati) and Ajay Nain. Asset-heavy model requires ongoing capital, making IPO necessary for fleet expansion.",
        "key_risks": "Asset-heavy model: high depreciation and balance-sheet risk. Damage/theft losses from customers. Reverse logistics costs for pickup after cancellation. EMI-based purchase competition (Bajaj Finance makes buying as cheap as renting). Geographic concentration in top 5 cities. Furniture fashion cycles affecting resale value.",
        "source": "DRHP Nov 2024 + public disclosures",
    },
    "Purple Style Labs": {
        "overview": "Purple Style Labs is the parent of Bewakoof, India's leading meme-culture D2C fashion brand targeting millennials and Gen Z. Founded 2012 by Prabhkiran Singh and Siddharth Munot (both IIT Bombay). Known for quirky, culturally-relevant prints and value pricing (₹299–999 tees). Backed by IndiaMart Intermesh and Bessemer.",
        "business_model": "D2C brand (Bewakoof): own website + app, Myntra, Amazon, and offline stores. Own-manufacturing model for core products. 200+ new designs/month driven by trend analytics and social media listening. Revenue: product sales (85%), private label for corporates (10%), licensing (5%). Expanding into ethnic wear and accessories.",
        "financials": "Revenue FY24: ~₹500 cr. Net loss reducing significantly. Contribution margin positive and improving YoY. D2C channel (own website + app) growing faster than marketplace. EBITDA positive in peak quarters. Improving unit economics as brand scales.",
        "ipo_details": "DRHP filed Jan 2025. Issue size ~₹1,000 cr. BRLMs: JM Financial, Axis Capital. Expected valuation ~₹3,000–5,000 cr. Use of funds: brand building, manufacturing capacity, offline retail expansion. OFS: Bessemer, Elevation Capital partial exit.",
        "key_metrics": "10M+ customers. ₹500+ cr revenue. 200+ new designs/month. 5M+ app downloads. 90%+ products: own Bewakoof brand. Price range: ₹299–1,499 for most items. Instagram: 5M+ followers. Myntra: top-10 brand in casualwear category.",
        "market_opportunity": "India D2C fashion market: ₹15,000 cr growing 30%+ YoY. Millennial and Gen Z fashion growing fastest. India has 250M+ Gen Z consumers — core Bewakoof target demographic. Pop-culture themed fashion (IPL, Bollywood, memes) is an under-served global niche being pioneered by Indian brands.",
        "competitive_position": "Dominant in meme/pop-culture D2C fashion segment. Competitors: The Souled Store, The Tee Merchants, Redwolf (pop culture), Myntra private labels (Roadster, HRX) at similar price points. Bewakoof's scale (10M+ customers) and design velocity (200+ monthly) create differentiation. IndiaMart as shareholder provides strategic distribution synergies.",
        "investors_funding": "Total raised: ~₹250 cr+. Investors: IndiaMart Intermesh (strategic shareholder ~26%), Bessemer Venture Partners, Elevation Capital (SAIF Partners). Founders: Prabhkiran Singh (CEO) and Siddharth Munot (CTO) — both IIT Bombay. IndiaMart's marketplace network creates unique B2B wholesale distribution opportunity.",
        "key_risks": "Fashion-trend volatility (pop-culture references age quickly). Myntra and Amazon private labels competing at same price points. Brand concentration in Bewakoof (single-brand risk). Cotton price inflation. Offline retail execution costs in a digital-first brand. Gen Z loyalty is notoriously fickle.",
        "source": "DRHP Jan 2025 + public disclosures",
    },
    "PlaySimple": {
        "overview": "PlaySimple Games (filed as 'Playsimple Games Limited') is India's leading casual mobile word-games studio, famous for Word Trip and Word Crossy with 200M+ combined downloads. Founded 2016 in Bengaluru by Siddhanth Krishnamurthy. Revenue 95%+ international (US, UK, Europe, Australia). Backed by Peak XV Partners (Sequoia) and Kalaari Capital.",
        "business_model": "Mobile game studio: develop, publish, and operate casual word games. Revenue: (1) In-app purchases (IAP) — hints, power-ups, no-ads subscriptions; (2) In-app advertising (rewarded video, banners) — ~60% of revenue. Top games: Word Trip, Word Crossy, Word Search, Word Story. Word Trip alone: 100M+ downloads.",
        "financials": "Revenue FY24: ~₹800 cr. Net profit: ~₹200 cr (~25% PAT margin — highly profitable). Revenue nearly 100% USD (currency tailwind for Indian-cost-base company). No significant marketing spend needed for existing titles. Dividend-paying company pre-IPO.",
        "ipo_details": "DRHP filed Feb 2025 (as 'Playsimple Games Limited'). Issue size ~₹2,000 cr (largely OFS — Peak XV, Kalaari, and founder selling). BRLMs: Goldman Sachs, JM Financial. Expected valuation ~$1–1.5B. Use of fresh issue: new game development, user acquisition for new titles.",
        "key_metrics": "200M+ total downloads (Word Trip 100M+, Word Crossy 60M+). 80M+ monthly active users globally. Top 5 word-games studio by revenue globally. 95%+ revenue from US, UK, Europe, Australia. Zero debt. ~25 core full-time game developers — highly capital-efficient.",
        "market_opportunity": "Global casual mobile gaming: $30B+. Word games segment: $2–3B, growing fastest with 35–65 age demographic. India game studio export market growing 40%+ YoY. Ad revenue recovery in US and Europe post-2022 correction. Gaming subscriptions (Apple Arcade, Google Play Pass) growing 30%+ YoY — new monetisation channel.",
        "competitive_position": "Top 5 globally in word games by MAU and revenue. Direct competitors: Zynga/NY Times (Wordle), Scopely, Jam City (US studios). PlaySimple's ARPU is among the highest in casual games due to loyal older demographics (35–65). India cost base (Bengaluru developers at 1/10th US cost) = structural margin advantage vs US competitors.",
        "investors_funding": "Total raised: ~$30M (lean capital structure — profitable from early). Investors: Peak XV Partners (Sequoia India), Kalaari Capital. Founder: Siddhanth Krishnamurthy (CEO). Profitable and cash-generative — IPO is primarily an investor exit vehicle. Employee stock option pool created for 200+ team members.",
        "key_risks": "Single-genre concentration risk (word games). Apple/Google App Store policy changes (30% commission, search algorithm changes). Rising user-acquisition costs for new title launches. One or two hit game dependency. Competition from AI-powered game studios (OpenAI Games). Currency risk: USD revenue vs INR costs (currently beneficial).",
        "source": "DRHP Feb 2025 (Playsimple Games Limited) + SEBI commondocs May 2026",
    },
    "CureFoods": {
        "overview": "CureFoods is India's fastest-growing multi-brand cloud-kitchen platform, operating EatFit (healthy food), Nomad Pizza, Frozen Bottle (milkshakes), and SLAY Coffee. Founded 2020 by Ankit Nagori (former Flipkart CPO and CureFit co-founder). 300+ kitchens across 20+ cities. Backed by Accel and Binny Bansal (Flipkart co-founder).",
        "business_model": "Multi-brand cloud-kitchen: each brand targets a distinct category (health food, pizza, milkshakes, coffee), sharing central kitchen infrastructure. Revenue via Zomato/Swiggy/own app delivery. Franchise model for SLAY Coffee expanding faster than company-owned. B2B: EatFit Work for corporate catering. Recent acquisitions of smaller cloud-kitchen brands.",
        "financials": "Revenue FY24: ~₹650 cr. Net loss: ~₹200 cr. Scaling rapidly with improving per-kitchen economics. Contribution margin positive in mature markets. EatFit healthy food segment commands 20% premium over competition.",
        "ipo_details": "DRHP filed Mar 2025. Issue size ~₹1,200 cr. BRLMs: Axis Capital, ICICI Securities. Expected valuation ~₹5,000–10,000 cr (wide range due to early stage). Use of funds: kitchen expansion, new city entry, technology, marketing.",
        "key_metrics": "300+ cloud kitchens. 15+ food brands under management. 1M+ orders/month. 20+ cities. SLAY Coffee: 100+ franchise locations. EatFit: top-ranked healthy food brand on Zomato/Swiggy in multiple cities. Frozen Bottle: #1 milkshake brand by orders online.",
        "market_opportunity": "India cloud-kitchen market: ₹4,000 cr growing to ₹15,000 cr by 2028. Health-food delivery fastest-growing segment (30%+ YoY). Coffee delivery market: ₹5,000 cr. Corporate catering: ₹10,000 cr market. India food delivery TAM: ₹1.4L cr.",
        "competitive_position": "Fastest-growing multi-brand cloud-kitchen in India. Competes with Rebel Foods (Faasos/Behrouz — dominant incumbent, 450+ kitchens), Wow! Momo (QSR chain), Swiggy Stores. EatFit is differentiated in health-food: no competitor at scale. SLAY Coffee competes with Blue Tokai and local cafe delivery. Ankit Nagori's reputation as CureFit co-founder accelerates B2B (corporate wellness) deals.",
        "investors_funding": "Total raised: ~$100M+. Investors: Accel India (led Series A and B), Binny Bansal (Flipkart co-founder — angel + strategic board member), Iron Pillar, Unilever Ventures. Founder: Ankit Nagori (CEO, ex-Flipkart CPO, ex-CureFit co-founder). Strong founder credibility accelerated early fundraising.",
        "key_risks": "Rebel Foods competition (bigger and better-funded). Zomato/Swiggy delivery-platform dependency and commission pressure. Kitchen occupancy ramp-up in new cities (fixed costs before volume). Brand proliferation quality control across 15+ brands. Health-food trend cyclicality. CureFit ecosystem brand separation confusion (different company, similar positioning).",
        "source": "SEBI filing page Jun 2025 + public disclosures",
    },
    "InCred Holdings": {
        "overview": "InCred Holdings is a tech-driven NBFC conglomerate offering personal loans, education loans, SME lending, and home loans via InCred Finance; and wealth management and investment banking via InCred Capital. Founded 2016 by Bhupinder Singh (ex-Deutsche Bank India CEO). One of India's few profitable new-age NBFCs. Backed by KKR Credit and Investcorp.",
        "business_model": "Two businesses: (1) InCred Finance — data-driven NBFC for personal, education, and SME loans using alternative data for underwriting; (2) InCred Capital — SEBI-registered investment bank and wealth manager. Revenue: NII from loan book (~80%) + investment banking fees + wealth management trail commissions (~20%). Uses psychometric and academic data for education loan underwriting.",
        "financials": "Revenue FY24: ~₹2,000 cr. Net profit: ~₹350 cr (profitable — NIM ~8%+). Loan book: ₹15,000+ cr. Gross NPA <2%. Capital adequacy ratio >20% (well-capitalised). Lending ~80% of revenue; IB ~20%.",
        "ipo_details": "DRHP filed Feb 2025. Issue size ~₹2,500 cr. BRLMs: JM Financial, Kotak Mahindra Capital. Expected valuation ~$1.5–2B. Use of funds: NBFC Tier 1 capital infusion, technology, branch expansion. OFS: Investcorp, Paragon partial exit.",
        "key_metrics": "₹15,000+ cr AUM. 1M+ customers. 200+ cities. Gross NPA <2%. Education loans: #2 private education lender in India. InCred Capital: top-10 investment bank in India by deal count. 3,000+ employees across finance + IB.",
        "market_opportunity": "India NBFC lending: ₹30L cr+. Education lending: ₹1L cr growing 25%+ YoY (80M+ students in higher education). SME lending: ₹20L cr, 70%+ underserved. Investment banking growing with IPO boom. India wealth management AUM projected to triple by 2027.",
        "competitive_position": "Leading private education lender and SME NBFC with combined lending + IB model — uniquely differentiated. Education competition: Avanse, Auxilo, HDFC Credila, government banks. SME: Aye Finance, Ugro Capital. InCred Capital's IB business competes with Kotak, JM Financial, Axis Capital. Combined one-stop financial-services offering is rare.",
        "investors_funding": "Total raised: ~$400M+. Investors: Investcorp, Paragon Partners, KKR Credit, Novo Holdings, Moore Capital, Alpha Capital. Founder: Bhupinder Singh (CEO, ~25% equity) — Deutsche Bank India CEO background gave early institutional investor credibility. Founder-led with meaningful skin in the game.",
        "key_risks": "Credit-cycle risk in consumer/SME (economic downturn causes NPA spikes). RBI NBFC tightening (higher capital requirements). MSME stress contagion. Competition from SFBs (AU SFB, IDFC First) entering personal loans online. Investment banking revenue cyclicality (IPO market volatility). Geographic concentration.",
        "source": "DRHP Feb 2025 + public disclosures",
    },
    "Cars24": {
        "overview": "Cars24 (CARS24 Services) is India's largest tech-enabled pre-owned car marketplace, buying cars from consumers (C2B) at fixed prices, refurbishing them, and selling via own platform (B2C) and dealer networks. Founded 2015 by Vikram Chopra, Mehul Agrawal, Ruchit Agarwal, and Gajendra Jangid. Operations in India, UAE, Australia, and SE Asia. Backed by SoftBank and DST Global. Confidential DRHP filed.",
        "business_model": "C2B2C marketplace: instant car purchase from consumers at fixed no-negotiation prices, refurbishment in own workshops, resale via CARS24.com and dealer auction. Revenue: spread between purchase and resale price (~15–20% margin). Also: CARS24 Financial Services (own NBFC for car loans), extended warranty, and insurance. C24 sub-brand for budget used cars under ₹3L.",
        "financials": "Revenue FY24: ~₹6,000 cr (estimated). Net loss reducing. India business profitable at EBITDA level. Working capital intensive (~₹2,000+ cr tied up in inventory). International operations (UAE, Australia) still loss-making but improving. Refurbishment margin ~15–20% on car value.",
        "ipo_details": "Confidential DRHP filed ~Feb 2025. Issue size ~₹3,000 cr. BRLMs: Kotak, Goldman Sachs. Expected valuation ~$3–4B. Use of funds: working capital, international expansion, technology. OFS: SoftBank, DST Global partial exit.",
        "key_metrics": "1M+ cars bought and sold since inception. 250+ purchase and inspection hubs. 2,000+ refurbishment technicians. CARS24.com: 3M+ monthly unique visitors. Operations in India, UAE, Australia, Thailand. C24 brand: entry-level used cars under ₹3L.",
        "market_opportunity": "India used-car market: 5M+ units/year, growing 15%+ YoY. Online penetration still <10% — massive headroom. Used-car to new-car ratio improving (currently 1.3× vs 2× in mature markets). UAE used-car market: $5B+. SE Asia fastest-growing used-car markets.",
        "competitive_position": "Largest tech-enabled used-car buyer in India by volume. Competition: Spinny (direct competitor, Indian unicorn), OLX Autos, CarDekho, traditional dealers. CARS24's fixed-price instant-purchase model differentiates from OLX (C2C classifieds). Spinny is the closest direct competitor — both in C2B2C segment. Strong NBFC arm creates one-stop used-car + financing solution.",
        "investors_funding": "Total raised: ~$900M+. Investors: SoftBank Vision Fund, DST Global, Tencent, KKR, Moore Strategic Ventures, Exor Seeds. Founders: Vikram Chopra (CEO), Mehul Agrawal, Ruchit Agarwal, Gajendra Jangid. Series G at $3.3B valuation (2021). SoftBank is largest shareholder.",
        "key_risks": "Inventory risk (unsold cars depreciate). Working-capital intensity (~₹2,000+ cr needed at current scale). International expansion losses (UAE, Australia). Technology R&D costs for pricing algorithms. Used-car price volatility impacts margin. Spinny competition for deal sourcing in metro cities.",
        "source": "Public disclosures + media (confidential DRHP)",
    },
    "Capillary Technologies": {
        "overview": "Capillary Technologies is a global B2B SaaS platform for retail loyalty, customer engagement, and AI-driven personalisation. Founded 2008 by Aneesh Reddy and Kumar Vembu (IIT Kharagpur). Listed on NSE/BSE in November 2025. Serves 400+ enterprise brands across 30+ countries. Backed by Warburg Pincus.",
        "business_model": "SaaS platform: Loyalty+ (point-based loyalty programs), Engage+ (omnichannel marketing automation), Insights+ (customer analytics), Merch+ (merchandise planning). Revenue: annual SaaS subscriptions + professional services + transaction fees. Clients: Pizza Hut, Shell, Puma, H&M, Sephora, Landmark Group.",
        "financials": "Revenue FY24: ₹479 cr. Net loss: ~₹75 cr. ARR growing 30%+. Gross margin: ~70%+ (SaaS characteristic). International revenue: ~60% of total. Path to profitability clear as scale improves unit economics. MCap at listing ~₹5,000 cr.",
        "ipo_details": "IPO price: ₹577. Issue size: ₹479 cr. Listed November 2025 on NSE/BSE. BRLMs: Kotak, Axis Capital. Valuation at listing ~₹5,000 cr. OFS: Warburg Pincus partial exit. Post-listing: CMP and performance available on NSE (symbol: CAPILLARY).",
        "key_metrics": "400+ enterprise clients. 1B+ loyalty program members managed on platform. 30+ countries. 2,000+ employees. 90%+ annual client retention rate. ARR growing 20%+ YoY. Net Revenue Retention >110% (existing customers expand usage).",
        "market_opportunity": "Global retail loyalty SaaS market: $10B+. India enterprise SaaS: growing to $20B+ by 2026. Loyalty program market growing 20%+ YoY as brands shift from discounts to engagement. AI-driven personalisation reducing customer acquisition costs for global retailers.",
        "competitive_position": "Leading loyalty SaaS platform in Asia and Middle East. Global competition: Salesforce Marketing Cloud (Loyalty Management), Braze, Emarsys (SAP), Antavo. Capillary is price-competitive vs Salesforce (5–10× cheaper) for mid-market retailers. Strong in emerging markets (India, SE Asia, ME) where Salesforce is weak and over-priced.",
        "investors_funding": "Total raised: ~$170M+. Investors: Warburg Pincus (led 2021 round), Avataar Venture Partners, Peak XV Partners (Sequoia India), Filter Capital. Founders: Aneesh Reddy (CEO) and Kumar Vembu (co-founder, now at Zoho as a strategic advisor). Listed company — public information available on NSE.",
        "key_risks": "Long enterprise SaaS sales cycles (6–12 months). US/Europe expansion execution risk. Salesforce competition (unlimited budget for enterprise sales). Customer concentration (top 10 clients ~40% of revenue). Forex risk: 60% international revenue, INR-denominated costs.",
        "source": "RHP Jan 2025 + NSE listing data Nov 2025",
    },
    "Groww (Billionbrains Garage)": {
        "overview": "Groww (Billionbrains Garage) is India's largest new-age retail investing platform by active users, offering stocks, mutual funds, F&O, IPOs, US stocks, and fixed deposits. Founded 2016 by Lalit Keshre, Harsh Jain, Neeraj Singh, and Ishan Bansal (all ex-Flipkart product managers). Listed on NSE/BSE in November 2025. Backed by Peak XV Partners and Tiger Global.",
        "business_model": "Discount brokerage + MF distribution platform. Revenue: (1) Brokerage on equity/F&O trades (₹20 flat fee); (2) MF trail commissions (0.5–1% of AUM); (3) Margin funding interest income; (4) Groww Plus subscription. Additional: gold buying, US stocks via international partnerships, IPO application via ASBA.",
        "financials": "Revenue FY24: ~₹3,145 cr (+2.6× YoY from ₹1,294 cr FY23). Net profit FY24: ~₹448 cr (profitable). EBITDA margin ~20%. Note: SEBI F&O regulations (Oct 2024) reduced F&O volumes ~30% — FY25 revenue headwind expected. MF trail income growing steadily as a countercyclical hedge.",
        "ipo_details": "IPO price: ₹100. Issue size: ₹6,632 cr. Listed November 2025 on NSE/BSE. BRLMs: Kotak, JM Financial, Axis Capital. Valuation at listing ~₹70,000 cr. OFS: Peak XV, Tiger Global, Ribbit Capital, founders partial exit. Post-listing: CMP available on NSE (symbol: GROWW).",
        "key_metrics": "11M+ funded accounts (active traders/investors). #2 broker by active clients (behind Zerodha). ₹1L+ cr AUM in mutual funds. 30M+ app downloads. F&O daily turnover: top 3 in India. MF distributor commission ARR: ₹400+ cr and growing.",
        "market_opportunity": "India retail broking: 80M+ demat accounts, growing 15M+/year. MF AUM expected to double to ₹100L cr by 2027. India financial savings shifting from physical (gold, real estate) to financial assets (equity, MF). First-time investor wave from Tier 2/3 India — Groww's core market vs Zerodha's metro-trader focus.",
        "competitive_position": "#2 broker by active clients. Zerodha #1 (~6M active), Groww #2 (~5M active), Angel One, Upstox following. Key differentiator: superior UX and education-first approach for first-time investors. Zerodha is trader-focused; Groww is first-time-investor-focused — complementary markets. Paytm Money and INDmoney are emerging competitors in the MF segment.",
        "investors_funding": "Total raised: ~$900M+. Investors: Peak XV Partners (Sequoia India), Tiger Global, Ribbit Capital, YC Continuity Fund, Propel Venture Partners. Founders: Lalit Keshre (CEO), Harsh Jain, Neeraj Singh, Ishan Bansal — all ex-Flipkart, all IIT/IIM. Listed company — public information available on NSE.",
        "key_risks": "SEBI F&O regulations (Oct 2024 circular significantly reduced F&O volumes — revenue headwind in FY25). Zerodha competition (profitable, founder-funded, loyal trader base). Angel One and Upstox gaining market share. Regulatory risk: SEBI continues tightening F&O rules. Market downturn reduces trading volumes and broking income.",
        "source": "RHP Oct 2025 + NSE listing data Nov 2025",
    },
    "Kissht (OnEMI Technology Solutions)": {
        "overview": "Kissht (OnEMI Technology Solutions Ltd) is a digital consumer-lending platform offering instant EMI-based loans for consumer durables, mobile phones, and personal needs at point-of-sale and online. Founded 2015 by Krishnan Vishwanathan (CEO) and Ranvir Singh. Listed on NSE/BSE on 8 May 2026. Backed by Fosun International, Sistema Asia Capital, and Vertex Ventures SE Asia.",
        "business_model": "Buy-now-pay-later (BNPL) and instant personal-loans platform. Integrates with offline/online retailers (electronics, appliances, furniture) to offer 0% or low-cost EMIs at checkout. Revenue: interest income on loan book, processing fees, and insurance cross-sell. Distribution via app, NBFC partners, and 10,000+ merchant touchpoints.",
        "financials": "Revenue FY24: ~₹1,450 cr (interest income basis). Net profit: positive. AUM growing ~40%+ YoY. Gross NPA manageable at mid-single-digit levels. Strong unit economics on consumer-durable segment (lower ticket, secured by product). FY25 revenue guidance meaningfully higher vs FY24.",
        "ipo_details": "✅ Listed 8 May 2026 on NSE (symbol: KISSHT) and BSE. Issue size ~₹2,250 cr. BRLMs: Axis Capital, ICICI Securities, Nuvama. IPO comprised fresh issue + OFS by early investors. Use of funds: augment Tier-1 capital base for loan book expansion.",
        "key_metrics": "10M+ registered users. 5M+ loans disbursed. 10,000+ merchant integrations. Average loan ticket: ₹20,000–50,000. 30+ product categories financed. NBFC licence (RBI regulated). Listed NSE: KISSHT.",
        "market_opportunity": "India consumer durable financing market: ~₹1.5L cr. BNPL market growing 30%+ YoY driven by smartphone penetration and aspirational spending in Tier 2/3 cities. Total addressable credit market for sub-prime/near-prime consumers: $100B+. Penetration of formal EMI financing in semi-urban India remains <10%.",
        "competitive_position": "Leading BNPL / consumer-durables lending platform. Competes with Bajaj Finance (dominant in consumer durables), ZestMoney (shut down), Capital Float, and bank EMI schemes. Kissht differentiates with wider geographic reach in Tier 2/3 cities and tech-first underwriting (alternative data, mobile behaviour).",
        "investors_funding": "Total raised: ~$200M+. Key investors: Fosun International (Hong Kong), Sistema Asia Capital (Russia/India), Vertex Ventures SE Asia, Brunei Investment Agency, Endeavour Investments. Listed company post-IPO. Pre-IPO: valued at ~$500M in last private round.",
        "key_risks": "Consumer credit quality risk in economic downturns. RBI NBFC regulations (tightening risk weights on consumer credit since 2023). Competition from Bajaj Finance with deeper merchant relationships and lower cost of funds. Collection risk in semi-urban geographies. Post-IPO: OFS by early investors may create selling pressure.",
        "source": "SEBI DRHP + public disclosures + NSE listing data May 2026",
    },
    "Aye Finance": {
        "overview": "Aye Finance is a technology-driven MSME lending NBFC focused on micro and small enterprises in manufacturing, trading, and services sectors — particularly in Tier 3/4 cities and semi-urban India. Founded 2014 by Sanjay Sharma (CEO) and Vikram Jetley. Listed on NSE/BSE on 16 February 2026. Backed by CapitalG (Google), A91 Partners, LGT Lightrock, and Falcon Edge Capital.",
        "business_model": "Cluster-based lending model: identifies high-density micro-enterprise clusters (e.g., leather goods in Agra, steel fabrication in Ludhiana) and develops deep underwriting expertise for that cluster. Loan products: business loans ₹1–10 lakh, secured and unsecured. Distribution: 600+ branches across 22+ states. Revenue: interest income (~30–35% yield on AUM).",
        "financials": "Revenue FY24: ~₹1,250 cr (interest and fee income). Net profit: ~₹300 cr, consistently profitable since FY23. AUM FY24: ~₹4,500 cr growing ~40%+ YoY. Gross NPA ~2–3% (strong for micro-lending segment). RoE ~18–20%. Cost-to-income ratio improving as AUM scales.",
        "ipo_details": "✅ Listed 16 Feb 2026 on NSE (symbol: AYEFIN) and BSE. Issue size ~₹1,450 cr. BRLMs: Axis Capital, Kotak Mahindra Capital, IIFL Securities. IPO: fresh issue + partial OFS by CapitalG and LGT Lightrock. Use of funds: augment Tier-1 capital for loan book growth.",
        "key_metrics": "600,000+ active loan accounts. ₹4,500 cr+ AUM. 600+ branches across 22+ states. Average loan size: ~₹1.5 lakh. 200+ enterprise clusters covered. Gross NPA ~2–3%. RoE ~18–20%. Listed NSE: AYEFIN.",
        "market_opportunity": "India MSME credit gap: $530B (IFC estimate). Formal credit penetration for micro enterprises <15%. 63M+ MSMEs in India with only 10–12M having any formal credit access. Cluster-based model allows high-quality underwriting where generic scorecards fail — large blue ocean in Tier 3/4 India.",
        "competitive_position": "Leading MSME micro-lender with proprietary cluster-underwriting moat. Competes with MFIs (Bandhan, CreditAccess Grameen), NBFCs (Ugro Capital, Vivriti Capital), and PSU bank MSME schemes. Aye's cluster model gives lower NPA vs peers at similar ticket sizes. CapitalG relationship brings data/technology advisory advantage.",
        "investors_funding": "Total raised: ~$250M+. Key investors: CapitalG (Google's independent growth fund, early backer), A91 Partners, LGT Lightrock (impact investing), Falcon Edge Capital, ABC Impact, Deutsche Investitions-und Entwicklungsgesellschaft (DEG). Sanjay Sharma (founder-CEO) retains significant stake. Listed post-IPO.",
        "key_risks": "MSME credit quality highly sensitive to economic cycles and GST/regulatory changes affecting small traders. Geographic concentration in North India. Operational risk: 600+ branch network execution. Competition from PSU banks under govt MSME schemes (CGTMSE-backed loans at subsidised rates). RBI regulations on NBFC Tier-1 capital adequacy.",
        "source": "SEBI DRHP + public disclosures + NSE listing data Feb 2026",
    },
    "Ather Energy": {
        "overview": "Ather Energy is India's leading premium electric two-wheeler OEM, designing and manufacturing e-scooters (Ather 450 series, Rizta) with proprietary battery packs, motors, and software. Founded 2013 by Tarun Mehta and Swapnil Jain (IIT Madras). Listed on NSE/BSE on 6 May 2025. Backed by Hero MotoCorp (~37%) and Flipkart (~13%).",
        "business_model": "Design, manufacture, and sell premium e-scooters under own brand. Revenue: vehicle sales (85%), Ather One subscription (service + software updates, 12%), accessories/spare parts (3%). Own fast-charging network: Ather Grid (1,500+ points). D2C experience centres (Ather Space) in 100+ cities.",
        "financials": "Revenue FY24: ~₹1,753 cr (+33% YoY). Net loss FY24: ~₹1,059 cr (declining as scale improves). Gross margin improving post PLI benefits. FY25 guidance: margins significantly better as volumes cross 3L units/year. MCap at listing: ~₹12,000 cr.",
        "ipo_details": "✅ Listed 6 May 2025 @ ₹326.05 NSE (+1.6% vs IPO ₹321). Issue size ₹2,981 cr (₹2,626 cr fresh + ₹355 cr OFS). BRLMs: Axis Capital, Goldman Sachs, IIFL Securities. NSE: ATHERENERG. Use of funds: manufacturing capacity expansion at Hosur plant, R&D, working capital.",
        "key_metrics": "3L+ e-scooters sold cumulatively. 150+ cities. 1,500+ Ather Grid charging points. 100+ experience centres. 2 manufacturing plants (Hosur, Tamil Nadu). Market share in premium e-scooter segment (>₹1.2L ASP): ~25–30%.",
        "market_opportunity": "India electric two-wheeler market: 5M+ units/year by FY27 (up from 1M in FY23). Premium e-scooter segment (₹1L+) is fastest-growing. Government FAME II and PLI subsidies accelerating adoption. Petrol two-wheeler replacement: 20M+ units/year total addressable base.",
        "competitive_position": "Leader in premium e-scooter segment. Competition: Ola Electric (volume leader overall), TVS iQube (strong mid-market), Bajaj Chetak, Honda Activa EV. Ather differentiates on software maturity, Ather Grid network, and brand loyalty among tech-savvy buyers. Hero MotoCorp's distribution network provides reach advantage.",
        "investors_funding": "Total raised: ~$450M+. Key investors: Hero MotoCorp (~37% stake), Flipkart/Walmart (via GFC, ~13%), Tiger Global, Caladium Investment, National Investment and Infrastructure Fund (NIIF). Founders: Tarun Mehta (CEO) and Swapnil Jain (CTO). Listed company post-IPO.",
        "key_risks": "EV subsidy policy risk (FAME II reduction). Battery raw material cost volatility (lithium, cobalt). Ola Electric competing aggressively on price. Charging infrastructure density still insufficient for mass adoption. Production ramp-up execution. Competition from legacy OEMs (Bajaj, TVS, Honda) entering EV segment.",
        "source": "RHP Apr 2025 + NSE listing data May 2025",
    },
    "BlueStone": {
        "overview": "BlueStone is India's leading online-first jewellery brand, offering certified diamond and gold jewellery via its website, app, and 250+ experience stores. Founded 2011 by Gaurav Singh Kushwaha (IIT Bombay). Listed on BSE/NSE on 19 Aug 2025. Backed by Accel, Kalaari Capital, and Ratan Tata (personal investment).",
        "business_model": "Omnichannel jewellery retail: own e-commerce (bluestone.com/app) + experience stores. Revenue: jewellery product sales (gold, diamond, platinum, silver). 30-day returns policy and lifetime exchange policy build customer trust. Custom jewellery design as a differentiator.",
        "financials": "Revenue FY24: ~₹1,265 cr (+53% YoY). Net loss FY24: ~₹158 cr (reducing). Gross margin ~25–28% (jewellery retail typical). EBITDA level profitable in peak quarters. Gold price tailwind drove FY24 revenue growth significantly.",
        "ipo_details": "✅ Listed 19 Aug 2025 @ ₹508.80 BSE (-1.6% vs IPO ₹517). Issue size ₹1,000 cr (fresh issue only). BRLMs: Axis Capital, Kotak Mahindra Capital. NSE: BLUESTONE. Use of funds: store expansion (target 400+ stores), technology, and working capital.",
        "key_metrics": "250+ experience stores. 10M+ app downloads. 1M+ customers. 6,000+ unique jewellery designs. 100% BIS hallmarked and IGI/GIA certified. 30-day return policy. 30+ cities with experience stores.",
        "market_opportunity": "India jewellery market: ₹6L cr+, growing 10%+ YoY. Online jewellery penetration <5% — massive headroom. Diamond jewellery fastest-growing segment as younger consumers shift from gold to diamond. Branded and certified jewellery gaining share from unorganised local jewellers.",
        "competitive_position": "Leading online-first jewellery brand. Competition: Tanishq (Tata — dominant), Kalyan Jewellers (strong retail), CaratLane (Tanishq subsidiary, online), Melorra (online). BlueStone differentiates on return policy (30-day), design variety (6,000+ SKUs), and price transparency vs traditional jewellers.",
        "investors_funding": "Total raised: ~$120M+. Investors: Accel India, Kalaari Capital, Ratan Tata (personal), Steadview Capital, IIFL Asset Management. Founder: Gaurav Singh Kushwaha (CEO, IIT Bombay). Listed company post-IPO.",
        "key_risks": "Gold price volatility impacting inventory value and revenue. Tanishq (Tata — unlimited capital) expanding online aggressively. High inventory carrying cost for jewellery. Returns rate risk (30-day policy). Lab-grown diamond disruption in diamond segment.",
        "source": "RHP Jul 2025 + BSE listing data Aug 2025",
    },
    "Smartworks": {
        "overview": "Smartworks Coworking Spaces is India's second-largest managed office / co-working operator, providing enterprise-grade flexible workspaces to corporates, MNCs, and startups. Founded 2016 by Neetish Sarda and Harsh Binani. Listed on NSE/BSE in Oct 2025. Backed by Keppel Land (Singapore) and Plutus Capital.",
        "business_model": "Managed workspace operator: long-term lease of commercial real estate, fit-out to enterprise grade, then sublease to corporates on flexible terms (3 months to 3 years). Revenue: monthly seat rentals (₹8,000–25,000/seat/month). Enterprise clients: TCS, IBM, Amazon, Wipro, MNCs. Add-on: meeting rooms, event spaces, food and beverage, IT infrastructure.",
        "financials": "Revenue FY24: ~₹1,100 cr (+40% YoY). EBITDA positive and growing. Net loss: ~₹130 cr (reducing rapidly as occupancy scales). Seat occupancy: 85%+ in mature locations. Pipeline: 100,000+ seats under development.",
        "ipo_details": "✅ Listed Oct 2025 @ ₹435 NSE (+7.1% vs IPO ₹407). Issue size ₹550 cr. BRLMs: JM Financial, Axis Capital. NSE: SMARTWORKS. Subscription: 13.45×. Use of funds: new centre fit-out, working capital, and general corporate purposes.",
        "key_metrics": "70,000+ operational seats. 40+ centres across 12 cities. 85%+ occupancy in mature centres. 200+ enterprise clients. 10M+ sq ft under management. Keppel Land (Singapore sovereign-linked) as anchor investor.",
        "market_opportunity": "India flexible workspace market: 60M sq ft by FY27 (up from 35M sq ft FY24). Enterprise flex demand growing 30%+ YoY. MNCs expanding India GCCs prefer managed offices over traditional leases. Post-COVID hybrid work is structural, not cyclical.",
        "competitive_position": "#2 managed workspace operator in India by seats. Competition: WeWork India (Brookfield-owned, largest), Table Space (#3), Awfis (listed). Smartworks differentiates on pure enterprise focus, enterprise-grade IT and security, and Keppel Land's real-estate relationships for prime locations.",
        "investors_funding": "Total raised: ~$100M+. Key investors: Keppel Land (Singapore; strategic shareholder ~35%), Plutus Capital, Investors' Trust. Founders: Neetish Sarda (CEO) and Harsh Binani (COO). Keppel Land's backing provides access to premium commercial real estate and institutional credibility with enterprise clients.",
        "key_risks": "Real-estate cycle risk (if commercial rents spike, margins compress). Enterprise client concentration. WeWork India (Brookfield) competing on price. Economic slowdown causes enterprises to reduce flex headcount. Long-term lease liabilities if occupancy drops.",
        "source": "RHP Sep 2025 + NSE listing data Oct 2025",
    },
    "PhysicsWallah": {
        "overview": "PhysicsWallah (PW) is India's leading affordable EdTech platform offering JEE, NEET, UPSC, and K-12 coaching via online and offline channels. Founded 2020 by Alakh Pandey (the 'Teacher of India') and Prateek Maheshwari. Listed on NSE/BSE on 18 Nov 2025. Backed by WestBridge Capital and GSV Ventures.",
        "business_model": "Hybrid EdTech: (1) PW App — subscription-based online courses (₹1,000–5,000/year); (2) Vidyapeeth offline centres (400+ centres in Tier 2/3 India); (3) PW Skills — upskilling for working professionals. Revenue: subscriptions, offline fee, and test series. Alakh Pandey's YouTube channel (20M+ subscribers) = massive organic acquisition flywheel.",
        "financials": "Revenue FY24: ~₹1,940 cr (+2.6× YoY from ₹744 cr FY23). Net profit: ~₹98 cr (turned profitable FY24). Offline Vidyapeeth: EBITDA positive. Online: high-margin subscription model. Raised at $2.8B valuation in Series B 2022.",
        "ipo_details": "✅ Listed 18 Nov 2025 @ ₹143.10 BSE (+31.4% vs IPO ₹109). Issue size ₹3,480 cr (₹3,100 cr fresh + ₹380 cr OFS). BRLMs: Goldman Sachs, Kotak, JM Financial. NSE: PWL. Subscription: 1.8×. Use of funds: offline centre expansion, technology platform, and marketing.",
        "key_metrics": "5M+ paid subscribers. 20M+ YouTube subscribers (Alakh Pandey channel). 400+ Vidyapeeth offline centres. 200+ cities. 5,000+ educators. JEE/NEET selections from PW students: 50,000+ annually. App: 4.8 rating, 50M+ downloads.",
        "market_opportunity": "India K-12 + test prep market: ₹5.6L cr. JEE/NEET aspirants: 3M+/year growing 10%. Affordable digital education: 600M+ students below ₹3L family income who cannot afford Byju's/Allen. UPSC and state PSC exam prep: ₹20,000 cr market.",
        "competitive_position": "Dominant in affordable JEE/NEET online prep. Competition: Allen Career Institute (offline incumbent), Unacademy (struggling), Vedantu, BYJU'S (distressed). PW's ₹1,000/year vs ₹50,000+/year for Allen = structural price disruption. Alakh Pandey's personal brand makes switching near-impossible for loyal students.",
        "investors_funding": "Total raised: ~$210M+. Investors: WestBridge Capital (led Series B at $2.8B valuation, 2022), GSV Ventures, Lightspeed India. Founders: Alakh Pandey (CEO — educator-celebrity) and Prateek Maheshwari (COO). Bootstrapped profitably until 2020; raised only one institutional round. Listed company post-IPO.",
        "key_risks": "Single-founder brand risk — Alakh Pandey's personal brand is the product. Offline centre expansion capex. Regulatory risk: UGC/AICTE oversight of EdTech certificates. Competition from Allen's aggressive online expansion. Government regulation on coaching fees (potential fee caps for JEE/NEET prep).",
        "source": "RHP Oct 2025 + NSE/BSE listing data Nov 2025",
    },
    "Shadowfax": {
        "overview": "Shadowfax is India's largest last-mile and hyperlocal delivery platform, serving e-commerce, quick-commerce, and D2C brands. Founded 2015 by Abhishek Bansal and Vaibhav Khandelwal (IIT Delhi). Listed on NSE/BSE on 28 Jan 2026. Backed by Flipkart, Mirae Asset, and Eight Roads Ventures.",
        "business_model": "Asset-light last-mile delivery: proprietary rider network (gig workers) + tech platform. Services: e-commerce last-mile, quick-commerce fulfilment (5–30 min), reverse logistics, and B2B cargo. Revenue: per-shipment fee (₹35–80). Key clients: Meesho, Flipkart, Amazon, Blinkit, Swiggy Instamart.",
        "financials": "Revenue FY24: ~₹1,850 cr (+35% YoY). Net loss: ~₹120 cr (improving rapidly). Contribution margin positive. 100M+ shipments delivered in FY24. Operating leverage: cost-per-delivery declining as volume scales past 30M shipments/month.",
        "ipo_details": "✅ Listed 28 Jan 2026 @ ₹124 NSE (flat vs IPO ₹124). Issue size ₹1,907 cr (₹1,000 cr fresh + ₹907 cr OFS). BRLMs: Axis Capital, Kotak, JM Financial. NSE: SHADOWFAX. Subscription: 2.72×. Use of funds: technology, fleet expansion, working capital.",
        "key_metrics": "30M+ shipments/month. 2,000+ cities serviced. 200,000+ delivery partners. 2,500+ delivery hubs. 95%+ on-time delivery rate. Reverse logistics: 15M+ returns processed/month. Quick-commerce fulfilment in 50+ cities.",
        "market_opportunity": "India e-commerce logistics: ₹30,000 cr growing to ₹80,000 cr by FY27. Quick-commerce last-mile: ₹5,000 cr growing 50%+ YoY. D2C brand count growing 30%+ YoY. Reverse logistics: ₹8,000 cr market growing as returns become standard.",
        "competitive_position": "Largest independent last-mile delivery platform in India. Competition: Delhivery (listed, larger), Xpressbees, Ecom Express (distressed), Bluedart (premium). Key differentiator: hyperlocal (30-min) capability for quick-commerce in addition to standard e-commerce. Flipkart as both investor and client creates strategic alignment.",
        "investors_funding": "Total raised: ~$300M+. Key investors: Flipkart (strategic ~15%), Mirae Asset Venture Investment, Eight Roads Ventures (Fidelity's venture arm), IFC, Nandan Nilekani (personal investment). Founders: Abhishek Bansal (CEO) and Vaibhav Khandelwal (CTO). Listed company post-IPO.",
        "key_risks": "Delhivery competition (larger scale, lower cost). Gig-worker classification regulatory risk. Client concentration (Meesho + Flipkart = large share of volume). Quick-commerce players building captive fleets (Blinkit, Zepto). Fuel cost and inflation impacting per-delivery economics.",
        "source": "RHP Dec 2025 + NSE listing data Jan 2026",
    },
    "Urban Company (SEBI Approved)": {
        "overview": "This entry tracks the SEBI-approval milestone for Urban Company's IPO. SEBI approval received April 2025. RHP filed September 2025. Same company as 'Urban Company' — see that entry for full analysis. IPO expected Q3 FY26.",
        "business_model": "Asset-light home-services marketplace connecting 40,000+ trained professionals with consumers across beauty, cleaning, repairs, and appliance servicing. See 'Urban Company' for full business model details.",
        "financials": "Revenue FY24: ~₹827 cr. Net loss: ~₹320 cr. India EBITDA positive. See 'Urban Company' for complete financials.",
        "ipo_details": "SEBI approval received: Apr 2025. RHP filed: Sep 2025 (WACA certified by J.C. Bhalla & Co., Sep 2 2025). IPO expected: Q3 FY26. Issue size: ~₹3,000 cr. BRLMs: Kotak, JM Financial, Axis Capital. Valuation ~$2–3B.",
        "key_metrics": "50M+ app downloads. 40,000+ trained professionals. 50+ service categories. 50+ Indian cities. 4 international markets. SEBI approval received Apr 2025.",
        "market_opportunity": "India home services: ~$20B, <5% organised penetration. See 'Urban Company' for full market analysis.",
        "competitive_position": "Dominant in premium organised home services in India. No national-scale direct competitor. See 'Urban Company' for full competitive analysis.",
        "investors_funding": "Tiger Global, VY Capital, Accel India, Elevation Capital, Bessemer Venture Partners, Goldman Sachs, Steadview Capital. Last private valuation ~$2.8B (2021). See 'Urban Company' for full investor details.",
        "key_risks": "Worker classification risk. High CAC. International losses. See 'Urban Company' for full risk analysis.",
        "source": "SEBI approval Apr 2025 + RHP Sep 2025",
    },
}


@st.dialog("Company Deep Dive", width="large")
def _show_company_summary(company_name: str):
    """8-section comprehensive DRHP summary popup."""
    s     = DRHP_SUMMARIES.get(company_name)
    entry = DRHP_LINKS.get(company_name, {})
    doc_type   = entry.get("type", "DRHP")
    doc_url    = entry.get("url")
    doc_source = entry.get("source", "")
    doc_note   = entry.get("note", "")

    # ── Header ───────────────────────────────────────────────────────────────
    st.markdown(f"## {company_name}")
    src_label = s.get("source", "DRHP / RHP + public disclosures") if s else "DRHP / RHP + public disclosures"
    st.caption(f"Source: {src_label}")

    # ── Feature 6: IPO Takeaway (hardcoded, shown before divider) ────────────
    _ipo_tk = _get_ipo_takeaway_by_company(company_name)
    if _ipo_tk:
        render_ipo_takeaway_structured(_ipo_tk)

    # Document link at the very top for quick access
    if doc_type == "CONFIDENTIAL":
        st.info(f"🔒 **Confidential Filing** — {doc_note or 'Document not publicly available.'}")
    elif doc_type == "FILING_PAGE" and doc_url:
        st.link_button("📋 View Filing on SEBI →", doc_url)
        if doc_note:
            st.caption(doc_note)
    elif doc_url:
        st.link_button(f"📄 Open Full {doc_type} →", doc_url)
        if doc_source:
            st.caption(f"Source: {doc_source}")

    st.divider()

    # ── No summary yet ────────────────────────────────────────────────────────
    if not s:
        st.info(f"Detailed summary not yet available for **{company_name}**.")
        return

    # ── Section 1: Overview — full width ──────────────────────────────────────
    if s.get("overview"):
        st.markdown("### 🏢 Overview")
        st.write(s["overview"])
        st.divider()

    # ── Sections 2–3: Business Model | IPO Details ───────────────────────────
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 💼 Business Model")
        st.write(s.get("business_model", ""))
    with c2:
        st.markdown("### 📋 IPO / Filing Details")
        st.write(s.get("ipo_details", ""))

    st.divider()

    # ── Sections 4–5: Financials | Key Metrics ───────────────────────────────
    c3, c4 = st.columns(2)
    with c3:
        st.markdown("### 💰 Key Financials")
        st.write(s.get("financials", ""))
    with c4:
        st.markdown("### 📊 Key Metrics")
        st.write(s.get("key_metrics", ""))

    st.divider()

    # ── Sections 6–7: Market Opportunity | Competitive Position ──────────────
    c5, c6 = st.columns(2)
    with c5:
        st.markdown("### 🌍 Market Opportunity")
        # Support both new key (market_opportunity) and old key (market)
        st.write(s.get("market_opportunity") or s.get("market", ""))
    with c6:
        st.markdown("### 🏆 Competitive Position")
        st.write(s.get("competitive_position", ""))

    st.divider()

    # ── Section 8: Investors & Funding — full width ──────────────────────────
    st.markdown("### 👥 Investors & Funding")
    # Support both new key (investors_funding) and old key (investors)
    st.write(s.get("investors_funding") or s.get("investors", ""))

    st.divider()

    # ── Section 9: Key Risks — full width, highlighted ───────────────────────
    st.markdown("### ⚠️ Key Risks")
    st.warning(s.get("key_risks", ""))


# ── JSON cache file for persisting auto-discovered filings ───────────────────
_CACHE_FILE = "drhp_cache.json"
_AUTO_MONITOR_TTL = 21600   # 6 hours between background scrapes


def _load_cache() -> dict:
    """Load persisted auto-discovered filings from JSON."""
    try:
        if os.path.exists(_CACHE_FILE):
            with open(_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_cache(data: dict):
    """Persist auto-discovered filings to JSON."""
    try:
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
_TAG_MAP = {
    "DRHP Filed":    ["drhp", "draft red herring"],
    "SEBI Approval": ["sebi approv", "sebi nod", "sebi green"],
    "Upcoming IPO":  ["upcoming ipo", "plans ipo", "planning ipo", "to list", "eye ipo",
                      "set to ipo", "files for ipo", "prepares ipo"],
    "Anchor":        ["anchor investor", "anchor allot"],
    "GMP":           ["gmp", "grey market premium", "gray market"],
    "Listing":       ["lists at", "listing price", "listing gain", "listed on", "debut"],
}

RSS_FEEDS = [
    ("Google News — IPO DRHP",
     "https://news.google.com/rss/search?q=IPO+DRHP+India+SEBI&hl=en-IN&gl=IN&ceid=IN:en"),
    ("Google News — Upcoming IPO",
     "https://news.google.com/rss/search?q=upcoming+IPO+India+2025+2026&hl=en-IN&gl=IN&ceid=IN:en"),
    ("Google News — Startups",
     "https://news.google.com/rss/search?q=NSE+IPO+Zepto+PhonePe+Flipkart+SEBI+filing&hl=en-IN&gl=IN&ceid=IN:en"),
    ("Google News — Fintech",
     "https://news.google.com/rss/search?q=India+fintech+startup+IPO+DRHP&hl=en-IN&gl=IN&ceid=IN:en"),
    ("Economic Times",
     "https://economictimes.indiatimes.com/markets/ipos/rssfeeds/1715249553.cms"),
    ("Business Standard",
     "https://www.business-standard.com/rss/markets/ipo-fpo-rights-12.rss"),
    ("Mint",
     "https://www.livemint.com/rss/markets"),
]

SCRAPE_SOURCES = [
    ("MoneyControl", "https://www.moneycontrol.com/news/tags/ipo.html",
     "li.clearfix a", "span.ago", None),
    ("Inc42",        "https://inc42.com/buzz/?s=IPO",
     "h2.entry-title a", "time.entry-date", None),
    ("Entrackr",     "https://entrackr.com/?s=IPO",
     "h2.entry-title a", "time", None),
]


def _now_ist():
    return datetime.now(IST).strftime("%d-%m-%Y %H:%M:%S IST")


# ── Curated DRHP / RHP filings — PDF links sourced from DRHP_LINKS ───────────
# pdf_link: always taken from DRHP_LINKS dict above.
# confidential: True if filing is under confidential-filing route (no public PDF)
KNOWN_FILINGS = [
    # ── Pipeline: DRHP filed, not yet listed ──────────────────────────────────
    {"company": "Zepto",
     "filing_date": "2025-03", "type": "DRHP", "sector": "ecommerce",
     "issue_size": "~₹3,500 cr", "brlms": "Kotak, Goldman Sachs, Axis",
     "pdf_link": DRHP_LINKS["Zepto"]["url"], "confidential": False,
     "description": "10-minute grocery delivery; Series G unicorn. India's fastest-growing quick commerce."},

    {"company": "PhonePe",
     "filing_date": "2025-04", "type": "DRHP", "sector": "fintech",
     "issue_size": "~₹7,000 cr", "brlms": "Morgan Stanley, Goldman Sachs, JPMorgan",
     "pdf_link": None, "confidential": True,
     "description": "India's largest UPI payments platform with 550M+ registered users. Backed by Walmart. Confidential DRHP filing."},

    {"company": "Meesho",
     "filing_date": "2025-12", "type": "Listed ✅", "sector": "ecommerce",
     "issue_size": "₹3,152 cr", "brlms": "Goldman Sachs, ICICI Securities, Kotak",
     "pdf_link": DRHP_LINKS["Meesho"]["url"], "confidential": False,
     "description": (
         "✅ Listed 10 Dec 2025 @ ₹162.50 NSE (+46.4%) / ₹161.20 BSE (+45.2%). "
         "IPO price ₹111 (band ₹105–111). Subscription: 79×. "
         "CMP ₹189.92 (+71.1% vs IPO). MCap ₹87,125 cr. "
         "52W: ₹125.56–₹254.40. Allotment 8 Dec 2025. "
         "Pre-IPO lock-in: 10 Jun 2026. "
         "Social commerce platform serving Tier 2/3 India. NSE: MEESHO."
     )},

    {"company": "Lenskart",
     "filing_date": "2025-01", "type": "DRHP", "sector": "consumer tech",
     "issue_size": "~₹3,500 cr", "brlms": "Kotak, JM Financial",
     "pdf_link": DRHP_LINKS["Lenskart"]["url"], "confidential": False,
     "description": "Omnichannel eyewear retailer backed by SoftBank and KKR. 2,000+ stores across 40+ countries."},

    {"company": "Ola Cabs",
     "filing_date": "2025-01", "type": "DRHP", "sector": "consumer tech",
     "issue_size": "~₹5,000 cr", "brlms": "Kotak, Goldman Sachs",
     "pdf_link": DRHP_LINKS["Ola Cabs"]["url"], "confidential": False,
     "description": "Ride-hailing platform with 500M+ trips. SoftBank-backed. India's second-largest cab aggregator."},

    {"company": "Boat (Imagine Marketing)",
     "filing_date": "2025-02", "type": "DRHP", "sector": "consumer tech",
     "issue_size": "~₹2,000 cr", "brlms": "ICICI Securities, Axis",
     "pdf_link": DRHP_LINKS["Boat (Imagine Marketing)"]["url"], "confidential": False,
     "description": "India's No.1 wearable brand with 28% market share. Warburg Pincus invested."},

    {"company": "Urban Company",
     "filing_date": "2025-09", "type": "Listed ✅", "sector": "consumer tech",
     "issue_size": "₹1,900 cr", "brlms": "Kotak, JM Financial, Axis",
     "pdf_link": DRHP_LINKS["Urban Company"]["url"], "confidential": False,
     "description": "✅ Listed 17 Sep 2025 @ ₹162.25 NSE (+57.5% vs IPO ₹103). Subscription 103.6×. Issue ₹1,900 cr. NSE: URBANCO."},

    {"company": "Rebel Foods (Faasos)",
     "filing_date": "2024-12", "type": "DRHP", "sector": "foodtech",
     "issue_size": "~₹2,500 cr", "brlms": "JM Financial, Axis",
     "pdf_link": DRHP_LINKS["Rebel Foods (Faasos)"]["url"], "confidential": False,
     "description": "World's largest internet restaurant company — Faasos, Behrouz Biryani, Oven Story."},

    {"company": "OYO",
     "filing_date": "2024-03", "type": "DRHP", "sector": "traveltech",
     "issue_size": "~₹8,430 cr", "brlms": "Kotak, JM Financial, Citigroup",
     "pdf_link": DRHP_LINKS["OYO"]["url"], "confidential": False,
     "description": "Hotel aggregator & hospitality tech platform. SoftBank-backed. 175,000+ hotels across 35 countries."},

    {"company": "Infra.Market",
     "filing_date": "2025-04", "type": "DRHP", "sector": "b2b",
     "issue_size": "~₹5,000 cr", "brlms": "Kotak, Goldman Sachs, ICICI Securities",
     "pdf_link": DRHP_LINKS["Infra.Market"]["url"], "confidential": False,
     "description": "B2B construction materials marketplace. Accel & Evolvence-backed. India's largest B2B building materials platform."},

    {"company": "Shiprocket",
     "filing_date": "2025-01", "type": "DRHP", "sector": "logistics",
     "issue_size": "~₹2,000 cr", "brlms": "JM Financial, Axis",
     "pdf_link": DRHP_LINKS["Shiprocket"]["url"], "confidential": False,
     "description": "E-commerce logistics platform powering 1L+ D2C sellers. Temasek & Bertelsmann backed."},

    {"company": "Turtlemint",
     "filing_date": "2025-02", "type": "DRHP", "sector": "insurtech",
     "issue_size": "~₹1,500 cr", "brlms": "Axis, ICICI Securities",
     "pdf_link": DRHP_LINKS["Turtlemint"]["url"], "confidential": False,
     "description": "Insurance distribution platform. Jungle Ventures & Nexus-backed. 3L+ insurance agents on platform."},

    {"company": "MoneyView",
     "filing_date": "2025-03", "type": "DRHP", "sector": "fintech",
     "issue_size": "~₹2,000 cr", "brlms": "Axis Capital, BofA Securities, IIFL Capital, Kotak",
     "pdf_link": DRHP_LINKS["MoneyView"]["url"], "confidential": False,
     "description": "Digital lending platform. Tiger Global & Storm Ventures-backed. 5M+ loan customers."},

    {"company": "Snapdeal",
     "filing_date": "2024-12", "type": "DRHP", "sector": "ecommerce",
     "issue_size": "~₹1,250 cr", "brlms": "JM Financial, Axis, IIFL",
     "pdf_link": DRHP_LINKS["Snapdeal"]["url"], "confidential": False,
     "description": "Value e-commerce marketplace focused on Tier 2/3 India. Kalaari & Sequoia-backed."},

    {"company": "RentoMojo",
     "filing_date": "2024-11", "type": "DRHP", "sector": "consumer tech",
     "issue_size": "~₹800 cr", "brlms": "IIFL, Axis",
     "pdf_link": DRHP_LINKS["RentoMojo"]["url"], "confidential": False,
     "description": "Furniture and appliance rental platform. Accel & Bain Capital-backed."},

    {"company": "Purple Style Labs",
     "filing_date": "2025-01", "type": "DRHP", "sector": "consumer tech",
     "issue_size": "~₹1,000 cr", "brlms": "JM Financial, Axis",
     "pdf_link": DRHP_LINKS["Purple Style Labs"]["url"], "confidential": False,
     "description": "Luxury fashion marketplace — Pernia's Pop-Up Shop. Elevation Capital-backed."},

    {"company": "PlaySimple",
     "filing_date": "2025-02", "type": "DRHP", "sector": "gaming",
     "issue_size": "~₹2,000 cr", "brlms": "Goldman Sachs, JM Financial",
     "pdf_link": DRHP_LINKS["PlaySimple"]["url"], "confidential": False,
     "description": "Mobile word game publisher — Wordful, Daily Word Search. 80M+ MAU globally."},

    {"company": "CureFoods",
     "filing_date": "2025-03", "type": "DRHP", "sector": "foodtech",
     "issue_size": "~₹1,200 cr", "brlms": "Axis, ICICI Securities",
     "pdf_link": DRHP_LINKS["CureFoods"]["url"], "confidential": False,
     "description": "Cloud kitchen platform — EatFit, Nomad Pizza, SLAY Coffee. Accel & Iron Pillar-backed."},

    {"company": "InCred Holdings",
     "filing_date": "2025-02", "type": "DRHP", "sector": "fintech",
     "issue_size": "~₹2,500 cr", "brlms": "JM Financial, Kotak",
     "pdf_link": DRHP_LINKS["InCred Holdings"]["url"], "confidential": False,
     "description": "Digital lending NBFC. Bhupinder Singh-led. Education, home, business loans."},

    {"company": "Cars24",
     "filing_date": "2025-02", "type": "DRHP", "sector": "consumer tech",
     "issue_size": "~₹3,000 cr", "brlms": "Kotak, Goldman Sachs",
     "pdf_link": None, "confidential": True,
     "description": "Pre-owned car marketplace. SoftBank, DST Global, Tencent-backed. Confidential DRHP filing."},

    # ── Listed companies ──────────────────────────────────────────────────────
    {"company": "Ather Energy",
     "filing_date": "2025-05", "type": "Listed ✅", "sector": "consumer tech",
     "issue_size": "₹2,981 cr", "brlms": "Axis Capital, Goldman Sachs, IIFL",
     "pdf_link": None, "confidential": False,
     "description": "✅ Listed 6 May 2025 @ ₹326.05 NSE (+1.6% vs IPO ₹321). Electric two-wheeler OEM. Backed by Hero MotoCorp & Flipkart. NSE: ATHERENERG."},

    {"company": "BlueStone",
     "filing_date": "2025-08", "type": "Listed ✅", "sector": "consumer tech",
     "issue_size": "₹1,000 cr", "brlms": "Axis Capital, Kotak",
     "pdf_link": None, "confidential": False,
     "description": "✅ Listed 19 Aug 2025 @ ₹508.80 BSE (-1.6% vs IPO ₹517). Online-first jewellery brand. Backed by Accel & Kalaari. NSE: BLUESTONE."},

    {"company": "Smartworks",
     "filing_date": "2025-10", "type": "Listed ✅", "sector": "consumer tech",
     "issue_size": "₹550 cr", "brlms": "JM Financial, Axis",
     "pdf_link": None, "confidential": False,
     "description": "✅ Listed Oct 2025 @ ₹435 NSE (+7.1% vs IPO ₹407). Managed co-working space operator. Subscription 13.45×. NSE: SMARTWORKS."},

    {"company": "PhysicsWallah",
     "filing_date": "2025-11", "type": "Listed ✅", "sector": "edtech",
     "issue_size": "₹3,480 cr", "brlms": "Goldman Sachs, Kotak, JM Financial",
     "pdf_link": None, "confidential": False,
     "description": "✅ Listed 18 Nov 2025 @ ₹143.10 BSE (+31.4% vs IPO ₹109). EdTech unicorn — Alakh Pandey founder. Issue ₹3,480 cr (₹3,100 cr fresh + ₹380 cr OFS). Subscription 1.8×. NSE: PWL."},

    {"company": "Shadowfax",
     "filing_date": "2026-01", "type": "Listed ✅", "sector": "logistics",
     "issue_size": "₹1,907 cr", "brlms": "Axis Capital, Kotak, JM Financial",
     "pdf_link": None, "confidential": False,
     "description": "✅ Listed 28 Jan 2026 @ ₹124 NSE (flat vs IPO ₹124). Last-mile logistics platform. Issue ₹1,907 cr (₹1,000 cr fresh + ₹907 cr OFS). Subscription 2.72×. NSE: SHADOWFAX."},

    # ── RHP filed / recently listed Z47 companies ─────────────────────────────
    {"company": "Pine Labs",
     "filing_date": "2025-11", "type": "Listed ✅", "sector": "fintech",
     "issue_size": "₹3,900 cr", "brlms": "Axis, ICICI Securities, JM Financial",
     "pdf_link": DRHP_LINKS["Pine Labs"]["url"], "confidential": False,
     "description": "✅ Listed 14 Nov 2025 @ ₹242 NSE (+9.5% vs IPO ₹221). Issue ₹3,900 cr. NSE: PINELABS."},

    {"company": "Capillary Technologies",
     "filing_date": "2025-02", "type": "Listed ✅", "sector": "saas",
     "issue_size": "₹479 cr", "brlms": "Kotak, Axis",
     "pdf_link": DRHP_LINKS["Capillary Technologies"]["url"], "confidential": False,
     "description": "✅ Listed Feb 2025. Z47 constituent. NSE: CAPILLARY."},

    {"company": "Groww (Billionbrains Garage)",
     "filing_date": "2024-12", "type": "Listed ✅", "sector": "fintech",
     "issue_size": "₹6,632 cr", "brlms": "Kotak, JM Financial, Axis",
     "pdf_link": DRHP_LINKS["Groww (Billionbrains Garage)"]["url"], "confidential": False,
     "description": "✅ Listed 14 Nov 2025 @ ₹114 NSE (+50% vs IPO ₹76). Issue ₹6,632 cr. NSE: GROWW."},

    {"company": "Aye Finance",
     "filing_date": "2026-02", "type": "Listed ✅", "sector": "fintech",
     "issue_size": "₹1,010 cr", "brlms": "Axis Capital, Kotak, IIFL",
     "pdf_link": DRHP_LINKS["Aye Finance"]["url"], "confidential": False,
     "description": "✅ Listed 16 Feb 2026 @ ₹131 NSE (+1.6% vs IPO ₹129). Issue ₹1,010 cr. NSE: AYE. Subscription 1.04×."},

    {"company": "Kissht (OnEMI Technology Solutions)",
     "filing_date": "2026-05", "type": "Listed ✅", "sector": "fintech",
     "issue_size": "₹926 cr", "brlms": "Axis Capital, ICICI Securities, Nuvama",
     "pdf_link": DRHP_LINKS["Kissht (OnEMI Technology Solutions)"]["url"], "confidential": False,
     "description": "✅ Listed 8 May 2026 @ ₹190 NSE (+11.1% vs IPO ₹171). Issue ₹926 cr. NSE: KISSHT."},

]


def _validate_pipeline_stages():
    """
    Cross-check pipeline data against yfinance on startup.
    Logs a warning if a company shows as DRHP/RHP/SEBI Approved
    but is actually trading on NSE.
    """
    import yfinance as yf
    # Map company name → NSE symbol for non-listed pipeline entries
    _SYM_MAP = {
        "Zepto":                    "ZEPTO",
        "PhonePe":                  "PHONPE",
        "Lenskart":                 "LENSKART",
        "Ola Cabs":                 "OLACABS",
        "Boat (Imagine Marketing)": "IMAGINE",
        "Shiprocket":               "SHIPROCKET",
        "MoneyView":                "MONEYVIEW",
    }
    warnings = []
    for f in KNOWN_FILINGS:
        stage = f.get("type", "")
        if stage.startswith("Lis"):
            continue  # already listed — skip
        company = f["company"]
        sym = _SYM_MAP.get(company)
        if not sym:
            continue
        try:
            hist = yf.Ticker(f"{sym}.NS").history(period="5d")
            if not hist.empty:
                warnings.append(
                    f"⚠️ {company} shows as '{stage}' but is TRADING on NSE ({sym}) — should be 'Listed ✅'"
                )
        except Exception:
            pass
    for w in warnings:
        print(w)
    return warnings

# Run on startup
_validate_pipeline_stages()


# ── URL verification helpers ───────────────────────────────────────────────────

def _verify_url(url):
    """
    Check whether a URL returns a usable PDF/document.
    Caches result per URL for 6 hours in session_state.
    Returns True / False.
    """
    if not url:
        return False
    ck = f"url_ok_{abs(hash(url))}"
    cached = st.session_state.get(ck, {})
    if cached and time.time() - cached.get("ts", 0) < _LINK_CHECK_TTL:
        return cached["ok"]
    ok = False
    try:
        r = requests.head(url,
                          headers={"User-Agent": "Mozilla/5.0"},
                          timeout=8, allow_redirects=True)
        ok = r.status_code in (200, 206, 301, 302)
    except Exception:
        pass
    st.session_state[ck] = {"ok": ok, "ts": time.time()}
    return ok


def _sebi_find_pdf(company_name):
    """
    Search the live SEBI DRHP filings page for a company name.
    Returns the PDF URL (or filing page URL) if found, or None.
    Uses the real SEBI listing page (verified May 2026).
    Caches per company for 24 hours.
    """
    ck = f"sebi_pdf_{company_name.lower()[:24]}"
    cached = st.session_state.get(ck, {})
    if cached and time.time() - cached.get("ts", 0) < _SEBI_SEARCH_TTL:
        return cached.get("url")

    url_found = None
    try:
        # Real SEBI DRHP listing page (not the old broken intmId=7 URL)
        r = requests.get(
            "https://www.sebi.gov.in/sebiweb/home/HomeAction.do"
            "?doListing=yes&sid=3&ssid=15&smid=10",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                   "AppleWebKit/537.36",
                     "Referer": "https://www.sebi.gov.in/"},
            timeout=15,
        )
        soup  = BeautifulSoup(r.text, "lxml")
        table = soup.find("table")
        if table:
            name_lower = company_name.lower()
            name_words = [w for w in name_lower.split() if len(w) > 3]
            for row in table.find_all("tr")[1:]:
                row_text = row.get_text(strip=True).lower()
                if name_lower in row_text or any(w in row_text for w in name_words):
                    # Prefer PDF link; fall back to filing detail page
                    for a in row.find_all("a", href=True):
                        href = a["href"]
                        if not href.startswith("http"):
                            href = "https://www.sebi.gov.in" + href
                        if ".pdf" in href.lower() or ".zip" in href.lower():
                            url_found = href
                            break
                    if not url_found:
                        for a in row.find_all("a", href=True):
                            href = a["href"]
                            if not href.startswith("http"):
                                href = "https://www.sebi.gov.in" + href
                            if "/filings/" in href:
                                url_found = href
                                break
                    if url_found:
                        break
    except Exception:
        pass

    st.session_state[ck] = {"url": url_found, "ts": time.time()}
    return url_found


def _get_best_link(filing):
    """
    Return (status, url) for a filing dict.
    status ∈ {'verified', 'confidential', 'sebi_fallback', 'not_found'}

    Priority:
    1. DRHP_LINKS[company] — hardcoded, trusted, no HEAD-check needed
    2. filing["pdf_link"]  — hardcoded in KNOWN_FILINGS
    3. SEBI dynamic search — fallback when neither above is available
    Never returns 'not_found' without offering SEBI search as last resort.
    """
    company = filing.get("company", "")
    if filing.get("confidential"):
        return "confidential", None

    # 1. Check DRHP_LINKS by exact company name (primary trusted source)
    drhp_entry = DRHP_LINKS.get(company, {})
    if drhp_entry.get("type") == "CONFIDENTIAL":
        return "confidential", None
    if drhp_entry.get("url"):
        return "verified", drhp_entry["url"]

    # 2. Check session cache
    ck = f"best_link_{company[:24]}"
    cached = st.session_state.get(ck, {})
    if cached and time.time() - cached.get("ts", 0) < _LINK_CHECK_TTL:
        return cached["status"], cached.get("url")

    # 3. Try hardcoded URL from filing dict (already from DRHP_LINKS via KNOWN_FILINGS)
    hardcoded = filing.get("pdf_link") or filing.get("_pdf")
    if hardcoded:
        # Trust SEBI/BSE hardcoded URLs — they came from DRHP_LINKS, which is verified
        result = ("verified", hardcoded)
        st.session_state[ck] = {"status": result[0], "url": result[1], "ts": time.time()}
        return result

    # 4. Dynamic SEBI search as fallback
    sebi_url = _sebi_find_pdf(company)
    if sebi_url:
        result = ("verified", sebi_url)
    else:
        # Always fall back to SEBI search page — never 'not_found'
        # Real SEBI DRHP listing page (intmId=7 is the old broken URL)
        result = ("sebi_fallback", "https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=3&ssid=15&smid=10")

    st.session_state[ck] = {"status": result[0], "url": result[1], "ts": time.time()}
    return result


# ── Auto-detect new DRHP filings from SEBI / BSE ─────────────────────────────

def _is_relevant_company(company_name: str) -> bool:
    """True if the company matches RELEVANT_KEYWORDS or is on WATCHLIST."""
    c_lower = company_name.lower()
    if any(kw in c_lower for kw in RELEVANT_KEYWORDS):
        return True
    for wl_name in WATCHLIST:
        if wl_name.lower() in c_lower or c_lower in wl_name.lower():
            return True
    return False


def _is_watchlist_hit(company_name: str) -> bool:
    """True if company is specifically on the watchlist."""
    c_lower = company_name.lower()
    for wl_name in WATCHLIST:
        if wl_name.lower() in c_lower or c_lower in wl_name.lower():
            return True
    return False


def _fuzzy_known(company_lower: str, known_cos: set) -> bool:
    """
    True if company_lower fuzzy-matches any curated KNOWN_FILINGS company name.
    Handles cases like 'playsimple games limited' matching 'playsimple'.
    Uses substring containment with a minimum length guard (≥6 chars) to avoid
    false positives on short words.
    """
    if company_lower in known_cos:
        return True
    for kc in known_cos:
        if len(kc) >= 6 and (kc in company_lower or company_lower in kc):
            return True
    return False


def _sebi_fetch_all():
    """
    Fetch ALL DRHP entries from SEBI + BSE filings pages; filter for tech/fintech.
    Also checks against WATCHLIST for known companies.
    Cached 30 minutes in session. Persists new discoveries to JSON.
    Returns list of filing dicts.
    """
    ck = "sebi_all_filings"
    now_ts = time.time()
    if (now_ts - st.session_state.get("sebi_all_ts", 0) < _SEBI_TTL
            and ck in st.session_state):
        return st.session_state[ck]

    filings = []

    # ── Source 1: SEBI DRHP filings page (real listing URL, verified May 2026) ──
    # URL: https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=3&ssid=15&smid=10
    # Table structure: col[0]=Date, col[1]=Title (with a[href] links in <td>)
    # PDF links use pattern: /sebi_data/commondocs/MONTH-YEAR/FILENAME.pdf
    # Filing detail pages: /filings/public-issues/MONTH-YEAR/SLUG_ID.html
    try:
        r = requests.get(
            "https://www.sebi.gov.in/sebiweb/home/HomeAction.do"
            "?doListing=yes&sid=3&ssid=15&smid=10",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                   "AppleWebKit/537.36",
                     "Referer": "https://www.sebi.gov.in/"},
            timeout=15,
        )
        soup  = BeautifulSoup(r.text, "lxml")
        table = soup.find("table")
        if table:
            for row in table.find_all("tr")[1:]:
                cols = row.find_all("td")
                if len(cols) < 2:
                    continue
                date_str = cols[0].get_text(strip=True)
                # Title is in col[1]; company name = title up to " - DRHP"
                title_text = cols[1].get_text(strip=True)
                company = title_text.split(" - DRHP")[0].split(" - RHP")[0].strip()
                if not company:
                    continue
                # Prefer PDF link (commondocs) over filing detail page
                pdf_url      = None
                filing_page  = None
                for a in row.find_all("a", href=True):
                    href = a["href"]
                    if not href.startswith("http"):
                        href = "https://www.sebi.gov.in" + href
                    if ".pdf" in href.lower() or ".zip" in href.lower():
                        pdf_url = href
                    elif "/filings/" in href:
                        filing_page = href
                # Use PDF if available, else filing page as fallback
                link = pdf_url or filing_page
                is_rel = _is_relevant_company(company)
                is_wl  = _is_watchlist_hit(company)
                filings.append({
                    "company":      company,
                    "filing_date":  date_str,
                    "type":         "DRHP",
                    "sector":       "",
                    "issue_size":   "N/A",
                    "brlms":        "N/A",
                    "pdf_link":     link,
                    "confidential": False,
                    "description":  "Auto-detected from SEBI",
                    "is_tech":      is_rel,
                    "is_watchlist": is_wl,
                    "source":       "SEBI Live",
                })
    except Exception:
        pass

    # ── Source 2: BSE DRHP listings page ──────────────────────────────────────
    try:
        r = requests.get(
            "https://www.bseindia.com/markets/PublicIssues/DraftOffer.aspx",
            headers={"User-Agent": "Mozilla/5.0"}, timeout=15,
        )
        soup  = BeautifulSoup(r.text, "lxml")
        table = (soup.find("table", {"id": "ContentPlaceHolder1_GridViewIPO"})
                 or soup.find("table"))
        if table:
            for row in table.find_all("tr")[1:]:
                cols = row.find_all("td")
                if len(cols) < 2:
                    continue
                company  = cols[0].get_text(strip=True)
                link_tag = cols[-1].find("a")
                pdf_url  = link_tag["href"] if link_tag else None
                if pdf_url and not pdf_url.startswith("http"):
                    pdf_url = "https://www.bseindia.com" + pdf_url
                is_rel = _is_relevant_company(company)
                is_wl  = _is_watchlist_hit(company)
                filings.append({
                    "company":      company,
                    "filing_date":  cols[1].get_text(strip=True) if len(cols) > 1 else "",
                    "type":         "DRHP",
                    "sector":       "",
                    "issue_size":   "N/A",
                    "brlms":        "N/A",
                    "pdf_link":     pdf_url,
                    "confidential": False,
                    "description":  "Auto-detected from BSE",
                    "is_tech":      is_rel,
                    "is_watchlist": is_wl,
                    "source":       "BSE Live",
                })
    except Exception:
        pass

    # ── Deduplicate SEBI + BSE by company name (prefer SEBI PDF) ──────────────
    seen: dict[str, dict] = {}
    for f in filings:
        key = f["company"].lower().strip()
        if key not in seen or (f.get("source") == "SEBI Live" and f.get("pdf_link")):
            seen[key] = f
    filings = list(seen.values())

    # ── Persist newly discovered relevant companies to JSON cache ──────────────
    cache = _load_cache()
    for f in filings:
        if f.get("is_tech") or f.get("is_watchlist"):
            key = f["company"].lower().strip()
            if key not in cache:
                cache[key] = {
                    "company":    f["company"],
                    "filing_date": f.get("filing_date", ""),
                    "type":       f.get("type", "DRHP"),
                    "pdf_link":   f.get("pdf_link"),
                    "source":     f.get("source", ""),
                    "discovered": datetime.now(IST).strftime("%Y-%m-%d"),
                }
    _save_cache(cache)

    # ── Inject previously cached companies not in live results ────────────────
    live_keys = {f["company"].lower().strip() for f in filings}
    for key, cached_f in cache.items():
        if key not in live_keys:
            filings.append({
                "company":      cached_f["company"],
                "filing_date":  cached_f.get("filing_date", ""),
                "type":         cached_f.get("type", "DRHP"),
                "sector":       "",
                "issue_size":   "N/A",
                "brlms":        "N/A",
                "pdf_link":     cached_f.get("pdf_link"),
                "confidential": False,
                "description":  f"Auto-detected from {cached_f.get('source', 'cache')}",
                "is_tech":      True,
                "is_watchlist": False,
                "source":       "Cache",
            })

    st.session_state[ck]            = filings
    st.session_state["sebi_all_ts"] = now_ts
    st.session_state["sebi_last_checked"] = datetime.now(IST).strftime("%d %b %Y %H:%M IST")
    return filings


# ── Live / Upcoming IPO fetchers ──────────────────────────────────────────────

def _fetch_live_ipos():
    """
    Fetch IPOs currently open for subscription.
    Sources: NSE API → Chittorgarh scrape.
    Cached 10 minutes.
    """
    ck = "live_ipos"
    now_ts = time.time()
    if (now_ts - st.session_state.get("live_ipos_ts", 0) < _LIVE_IPO_TTL
            and ck in st.session_state):
        return st.session_state[ck]

    ipos = []
    _nse_h = {"User-Agent": "Mozilla/5.0", "Accept": "*/*",
               "Referer": "https://www.nseindia.com/"}

    # Source 1: NSE API
    try:
        s = requests.Session()
        s.get("https://www.nseindia.com", headers=_nse_h, timeout=12)
        time.sleep(0.5)
        r = s.get(
            "https://www.nseindia.com/api/allIpo"
            "?series[]=NB&series[]=MF&series[]=BN&series[]=NC&status=current",
            headers=_nse_h, timeout=12,
        )
        if r.status_code == 200:
            raw = r.json()
            entries = raw if isinstance(raw, list) else raw.get("data", [])
            for item in entries:
                name = str(item.get("companyName", item.get("name", ""))).strip()
                if not name:
                    continue
                ipos.append({
                    "company":    name,
                    "price_band": str(item.get("priceBand", item.get("price_band", "TBD"))),
                    "open_date":  str(item.get("openDate", "")),
                    "close_date": str(item.get("closeDate", "")),
                    "issue_size": str(item.get("issueSize", "N/A")),
                    "gmp":        "—",
                    "source":     "NSE",
                })
    except Exception:
        pass

    # Source 2: Chittorgarh scrape (if NSE returned nothing)
    if not ipos:
        try:
            r = requests.get(
                "https://www.chittorgarh.com/ipo/ipo_list.asp?a=open",
                headers={"User-Agent": "Mozilla/5.0"}, timeout=12,
            )
            soup  = BeautifulSoup(r.text, "lxml")
            table = soup.find("table")
            if table:
                for row in table.find_all("tr")[1:]:
                    cols = row.find_all("td")
                    if len(cols) < 2:
                        continue
                    name = cols[0].get_text(strip=True)
                    if not name or name.lower() == "ipo name":
                        continue
                    ipos.append({
                        "company":    name,
                        "price_band": cols[2].get_text(strip=True) if len(cols) > 2 else "TBD",
                        "open_date":  cols[1].get_text(strip=True) if len(cols) > 1 else "—",
                        "close_date": cols[3].get_text(strip=True) if len(cols) > 3 else "—",
                        "issue_size": cols[4].get_text(strip=True) if len(cols) > 4 else "N/A",
                        "gmp":        "—",
                        "source":     "Chittorgarh",
                    })
        except Exception:
            pass

    st.session_state[ck]            = ipos
    st.session_state["live_ipos_ts"] = now_ts
    return ipos


def _fetch_upcoming_ipos():
    """
    Fetch IPOs opening in the next ~30 days.
    Sources: NSE API → Chittorgarh scrape.
    Cached 30 minutes.
    """
    ck = "upcoming_ipos"
    now_ts = time.time()
    if (now_ts - st.session_state.get("upcoming_ipos_ts", 0) < _UPCO_IPO_TTL
            and ck in st.session_state):
        return st.session_state[ck]

    ipos = []
    _nse_h = {"User-Agent": "Mozilla/5.0", "Accept": "*/*",
               "Referer": "https://www.nseindia.com/"}

    # Source 1: NSE forthcoming
    try:
        s = requests.Session()
        s.get("https://www.nseindia.com", headers=_nse_h, timeout=12)
        time.sleep(0.5)
        r = s.get(
            "https://www.nseindia.com/api/allIpo?status=forthcoming",
            headers=_nse_h, timeout=12,
        )
        if r.status_code == 200:
            raw = r.json()
            entries = raw if isinstance(raw, list) else raw.get("data", [])
            for item in entries:
                name = str(item.get("companyName", item.get("name", ""))).strip()
                if not name:
                    continue
                ipos.append({
                    "company":    name,
                    "price_band": str(item.get("priceBand", "TBD")),
                    "open_date":  str(item.get("openDate", "TBD")),
                    "close_date": str(item.get("closeDate", "TBD")),
                    "issue_size": str(item.get("issueSize", "N/A")),
                    "source":     "NSE",
                })
    except Exception:
        pass

    # Source 2: Chittorgarh upcoming
    if not ipos:
        try:
            r = requests.get(
                "https://www.chittorgarh.com/ipo/ipo_list.asp?a=upcoming",
                headers={"User-Agent": "Mozilla/5.0"}, timeout=12,
            )
            soup  = BeautifulSoup(r.text, "lxml")
            table = soup.find("table")
            if table:
                for row in table.find_all("tr")[1:]:
                    cols = row.find_all("td")
                    if len(cols) < 2:
                        continue
                    name = cols[0].get_text(strip=True)
                    if not name or name.lower() == "ipo name":
                        continue
                    ipos.append({
                        "company":    name,
                        "price_band": cols[2].get_text(strip=True) if len(cols) > 2 else "TBD",
                        "open_date":  cols[1].get_text(strip=True) if len(cols) > 1 else "TBD",
                        "close_date": "",
                        "issue_size": cols[3].get_text(strip=True) if len(cols) > 3 else "N/A",
                        "source":     "Chittorgarh",
                    })
        except Exception:
            pass

    st.session_state[ck]               = ipos
    st.session_state["upcoming_ipos_ts"] = now_ts
    return ipos


# ── News helpers ───────────────────────────────────────────────────────────────

def _parse_dt(raw):
    """Parse any date string → aware IST datetime, or None."""
    if not raw:
        return None
    if isinstance(raw, datetime):
        dt = raw
    else:
        import email.utils
        for fn in [
            lambda s: datetime(*time.strptime(s, "%a, %d %b %Y %H:%M:%S %z")[:6],
                               tzinfo=pytz.UTC),
            lambda s: datetime(*email.utils.parsedate(s)[:6], tzinfo=pytz.UTC),
            lambda s: datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=pytz.UTC),
            lambda s: datetime.strptime(s[:10], "%Y-%m-%d").replace(tzinfo=pytz.UTC),
        ]:
            try:
                dt = fn(str(raw).strip())
                break
            except Exception:
                dt = None
        else:
            return None
    try:
        return dt.astimezone(IST) if dt else None
    except Exception:
        return None


def _tag_article(headline):
    hl = (headline or "").lower()
    tags = []
    for tag, kws in _TAG_MAP.items():
        if any(k in hl for k in kws):
            tags.append(tag)
    return tags or ["IPO News"]


def _relevant(headline, snippet=""):
    text = (headline + " " + snippet).lower()
    return any(k in text for k in _IPO_KEYWORDS)


def _dedupe(articles):
    seen_urls = set(); seen_heads = []; out = []
    for a in articles:
        url  = a.get("url", "")
        hl60 = (a.get("headline", "") or "")[:60].lower()
        if url and url in seen_urls:
            continue
        duplicate = any(
            len(hl60) > 10 and sum(c1 == c2 for c1, c2 in zip(hl60, h)) / max(len(hl60), 1) > 0.8
            for h in seen_heads
        )
        if duplicate:
            continue
        if url:
            seen_urls.add(url)
        seen_heads.append(hl60)
        out.append(a)
    return out


def _fetch_rss_feeds():
    try:
        import feedparser
    except ImportError:
        return []
    articles = []
    cutoff   = datetime.now(IST) - timedelta(days=180)
    for source_name, url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in (feed.entries or []):
                headline = entry.get("title", "").strip()
                link     = entry.get("link", "")
                snippet  = BeautifulSoup(
                    entry.get("summary", entry.get("description", "")), "lxml"
                ).get_text()[:300]
                pub_dt   = _parse_dt(entry.get("published", entry.get("updated", "")))
                if not headline or not _relevant(headline, snippet):
                    continue
                if pub_dt and pub_dt < cutoff:
                    continue
                articles.append({
                    "headline": headline, "url": link, "source": source_name,
                    "snippet":  snippet[:200] if snippet else "",
                    "pub_dt":   pub_dt,
                    "pub_str":  pub_dt.strftime("%d %b %Y, %I:%M %p IST") if pub_dt else "—",
                    "tags":     _tag_article(headline),
                })
        except Exception:
            continue
    return articles


def _fetch_scraped_sources():
    articles = []
    cutoff   = datetime.now(IST) - timedelta(days=180)
    for source_name, url, link_sel, date_sel, _ in SCRAPE_SOURCES:
        try:
            r    = requests.get(url, headers=_SCRAPE_HEADERS, timeout=10)
            soup = BeautifulSoup(r.text, "lxml")
            links = soup.select(link_sel)
            dates = soup.select(date_sel) if date_sel else []
            for i, tag in enumerate(links[:30]):
                headline = tag.get_text(strip=True)
                href     = tag.get("href", "")
                if href and not href.startswith("http"):
                    from urllib.parse import urljoin
                    href = urljoin(url, href)
                date_raw = (dates[i].get("datetime", dates[i].get_text(strip=True))
                            if i < len(dates) else "")
                pub_dt   = _parse_dt(date_raw)
                if not headline or not _relevant(headline):
                    continue
                if pub_dt and pub_dt < cutoff:
                    continue
                articles.append({
                    "headline": headline, "url": href, "source": source_name,
                    "snippet":  "",
                    "pub_dt":   pub_dt,
                    "pub_str":  pub_dt.strftime("%d %b %Y, %I:%M %p IST") if pub_dt else "—",
                    "tags":     _tag_article(headline),
                })
        except Exception:
            continue
    return articles


def _load_news_cache(force=False):
    now_ts = time.time()
    last   = st.session_state.get("drhp_news_ts", 0)
    if not force and now_ts - last < _NEWS_TTL and "drhp_news" in st.session_state:
        return st.session_state["drhp_news"], False

    prev_urls = {a["url"] for a in st.session_state.get("drhp_news", [])}
    combined  = _fetch_rss_feeds() + _fetch_scraped_sources()
    combined.sort(key=lambda a: a["pub_dt"] or datetime(2000, 1, 1, tzinfo=IST), reverse=True)
    deduped   = _dedupe(combined)
    new_count = sum(1 for a in deduped if a["url"] not in prev_urls and a["url"])

    st.session_state["drhp_news"]     = deduped
    st.session_state["drhp_news_ts"]  = now_ts
    st.session_state["drhp_news_new"] = new_count
    return deduped, new_count > 0


_TAG_COLOURS = {
    "DRHP Filed":    ("#1e40af", "#dbeafe"),
    "SEBI Approval": ("#166534", "#dcfce7"),
    "Upcoming IPO":  ("#7c3aed", "#ede9fe"),
    "Anchor":        ("#92400e", "#fef3cd"),
    "GMP":           ("#0f766e", "#ccfbf1"),
    "Listing":       ("#be185d", "#fce7f3"),
    "IPO News":      ("#374151", "#f3f4f6"),
}


def _badge(tag):
    fg, bg = _TAG_COLOURS.get(tag, ("#374151", "#f3f4f6"))
    return (f"<span style='background:{bg};color:{fg};font-size:10px;font-weight:600;"
            f"padding:2px 7px;border-radius:10px;margin-right:4px'>{tag}</span>")


def _render_news_feed():
    with st.expander("📰 IPO & DRHP News Feed", expanded=True):
        nh1, nh2, nh3 = st.columns([5, 3, 1])
        with nh1:
            st.markdown(
                f"<span style='color:#6b7a8d;font-size:12px'>Last updated: {_now_ist()}</span>",
                unsafe_allow_html=True)
        with nh2:
            search_q = st.text_input("🔍 Filter news", placeholder="e.g. Zepto, SEBI, GMP…",
                                     label_visibility="collapsed", key="drhp_news_search")
        with nh3:
            do_refresh = st.button("🔄 Refresh", key="drhp_news_refresh")

        if do_refresh:
            st.session_state.pop("drhp_news_ts", None)

        with st.spinner("Fetching IPO news…"):
            articles, is_new = _load_news_cache(force=do_refresh)

        new_count = st.session_state.get("drhp_news_new", 0)
        if is_new and new_count > 0:
            st.markdown(
                f"<div style='background:#dcfce7;border:1px solid #86efac;border-radius:8px;"
                f"padding:6px 14px;margin-bottom:8px;font-size:13px;color:#166534'>"
                f"🟢 <b>{new_count} new article{'s' if new_count>1 else ''}</b> since last refresh</div>",
                unsafe_allow_html=True)

        all_sources = sorted(set(a["source"] for a in articles))
        if all_sources:
            with st.expander("🗂️ Filter by source", expanded=False):
                src_cols = st.columns(min(len(all_sources), 4))
                sel_sources = set()
                for i, src in enumerate(all_sources):
                    with src_cols[i % 4]:
                        if st.checkbox(src, value=True, key=f"drhp_src_{src.replace(' ','_')}"):
                            sel_sources.add(src)
        else:
            sel_sources = set(all_sources)

        filtered = [a for a in articles
                    if a["source"] in sel_sources
                    and (not search_q or search_q.lower() in (a["headline"] + a["snippet"]).lower())]

        if not filtered:
            if not articles:
                st.info("Unable to fetch news at this time. Will retry in 30 minutes.")
            else:
                st.info("No articles match the selected filters.")
            return

        page_key = "drhp_news_page"
        if page_key not in st.session_state:
            st.session_state[page_key] = 20
        if do_refresh or search_q:
            st.session_state[page_key] = 20

        page_size = st.session_state[page_key]
        shown     = filtered[:page_size]

        st.markdown(
            f"<div style='color:#6b7a8d;font-size:12px;margin-bottom:8px'>"
            f"Showing {len(shown)} of {len(filtered)} articles</div>",
            unsafe_allow_html=True)

        for art in shown:
            tags_html    = "".join(_badge(t) for t in art["tags"])
            source_html  = (f"<span style='color:#6b7a8d;font-size:11px'>"
                            f"📡 {art['source']} &nbsp;·&nbsp; 🕐 {art['pub_str']}</span>")
            snippet_html = (f"<div style='color:#4b5563;font-size:12px;margin:4px 0 2px'>"
                            f"{art['snippet']}</div>" if art.get("snippet") else "")
            url = art.get("url", "#")
            st.markdown(
                f"""<div style='background:{CARD_BG};border:1px solid {BORDER};
                border-radius:8px;padding:10px 14px;margin-bottom:8px'>
                <div style='margin-bottom:4px'>{tags_html}</div>
                <div style='font-size:14px;font-weight:600;margin-bottom:2px'>
                  <a href='{url}' target='_blank' style='color:#1e40af;text-decoration:none'>
                  {art['headline']}</a></div>
                {snippet_html}
                {source_html}
                </div>""",
                unsafe_allow_html=True)

        if len(filtered) > page_size:
            if st.button(f"Load More ({len(filtered) - page_size} remaining)",
                         key="drhp_news_more"):
                st.session_state[page_key] += 20
                st.rerun()


# ── IPO card renderer ─────────────────────────────────────────────────────────

def _is_tech_ipo(name):
    return any(kw in name.lower() for kw in _TECH_KEYWORDS)


def _render_ipo_card(ipo, highlight=False):
    bg = "#f0fdf4" if highlight else CARD_BG
    bd = "#86efac" if highlight else BORDER
    company    = ipo.get("company", "")
    price_band = ipo.get("price_band", "TBD")
    open_date  = ipo.get("open_date", "—")
    close_date = ipo.get("close_date", "—")
    issue_size = ipo.get("issue_size", "N/A")
    gmp        = ipo.get("gmp", "—")
    source     = ipo.get("source", "")
    tech_badge = (
        "<span style='background:#dbeafe;color:#1e40af;font-size:10px;font-weight:700;"
        "padding:1px 6px;border-radius:8px;margin-left:6px'>Tech/Fintech</span>"
        if _is_tech_ipo(company) else ""
    )
    st.markdown(
        f"""<div style='background:{bg};border:1px solid {bd};border-radius:8px;
        padding:10px 16px;margin-bottom:8px'>
        <div style='font-size:14px;font-weight:700;color:#1a0f00'>{company}{tech_badge}</div>
        <div style='font-size:12px;color:#6b7a8d;margin-top:4px'>
          📅 Open: <b>{open_date}</b> &nbsp;·&nbsp; Close: <b>{close_date}</b>
          &nbsp;·&nbsp; 💰 Price: <b>{price_band}</b>
          &nbsp;·&nbsp; Size: <b>{issue_size}</b>
          {"&nbsp;·&nbsp; GMP: <b>" + gmp + "</b>" if gmp != "—" else ""}
          &nbsp;·&nbsp; <span style='color:#9ca3af'>{source}</span>
        </div></div>""",
        unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_z47(name, sector=""):
    return any(k in (name + " " + sector).lower() for k in _TECH_KEYWORDS)


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


# ── Render ─────────────────────────────────────────────────────────────────────
def render():
    st_autorefresh(interval=1_800_000, key="drhp_refresh")

    render_z47_assistant(
        context="drhp",
        label="💬 Ask Z47 Assistant",
        extra_context="User is viewing DRHP and RHP filings and IPO news feed.",
    )

    st.markdown("## 📋 DRHP / RHP Filings Monitor — New Age Tech & Fintech")
    st.markdown(
        "<p style='color:#6b7a8d;font-size:14px'>Tracks DRHP and RHP filings from SEBI/BSE for "
        "new-age tech and fintech companies. Auto-refreshes every 30 minutes.</p>",
        unsafe_allow_html=True,
    )

    col_h, col_b = st.columns([6, 1])
    with col_b:
        if st.button("🔄 Refresh", key="drhp_ref"):
            for k in ["drhp_news_ts", "sebi_all_ts", "sebi_all_filings",
                      "live_ipos", "live_ipos_ts", "upcoming_ipos", "upcoming_ipos_ts"]:
                st.session_state.pop(k, None)
            st.rerun()

    # ── PIPELINE STAGE TRACKER ───────────────────────────────────────────────
    st.markdown("### 🚀 IPO Pipeline — Stage Tracker")
    _LISTING_DATES = {
        "Kissht (OnEMI Technology Solutions)": "2026-05-08",
        "Aye Finance":                          "2026-02-16",
        "Shadowfax":                            "2026-01-28",
        "Meesho":                               "2025-12-10",
        "PhysicsWallah":                        "2025-11-18",
        "Pine Labs":                            "2025-11-14",
        "Groww (Billionbrains Garage)":         "2025-11-14",
        "Smartworks":                           "2025-10-01",
        "Urban Company":                        "2025-09-17",
        "BlueStone":                            "2025-08-19",
        "Ather Energy":                         "2025-05-06",
        "Capillary Technologies":               "2025-02-18",
    }
    _STAGES = [
        ("DRHP",          "📋 DRHP Filed",      "#dbeafe", "#1e40af"),
        ("SEBI Approved", "✅ SEBI Approved",    "#dcfce7", "#166534"),
        ("RHP",           "📄 RHP Filed",        "#ede9fe", "#6d28d9"),
        ("Listed",        "🎉 Listed",           "#fce7f3", "#be185d"),
    ]
    stage_cols = st.columns(len(_STAGES))
    for (stage_key, stage_lbl, stage_bg, stage_fg), col in zip(_STAGES, stage_cols):
        if stage_key == "SEBI Approved":
            in_stage = [f["company"] for f in KNOWN_FILINGS if f.get("type") == "SEBI Approved"]
        else:
            in_stage = [f["company"] for f in KNOWN_FILINGS
                        if f.get("type", "").startswith(stage_key[:3])
                        or f.get("type") == stage_key]
        if stage_key == "Listed":
            in_stage.sort(key=lambda n: _LISTING_DATES.get(n, "2000-01-01"), reverse=True)
        names_html = "".join(
            f"<div style='font-size:12px;color:#1a0f00;padding:3px 0;"
            f"border-top:1px solid {stage_bg}'>{n}</div>"
            for n in in_stage
        ) or f"<div style='font-size:12px;color:#9ca3af'>None</div>"
        with col:
            st.markdown(
                f"<div style='background:{stage_bg};border:1px solid {stage_fg}40;"
                f"border-radius:10px;padding:12px 14px'>"
                f"<div style='font-size:11px;font-weight:700;color:{stage_fg};margin-bottom:6px'>"
                f"{stage_lbl} &nbsp;({len(in_stage)})</div>"
                f"{names_html}</div>",
                unsafe_allow_html=True,
            )
    st.markdown("<div style='margin-bottom:16px'></div>", unsafe_allow_html=True)

    st.markdown("---")

    # ── DRHP / RHP FILINGS TABLE ───────────────────────────────────────────────
    st.markdown("### 📂 DRHP / RHP Filings — New Age Tech & Fintech")

    # ── Manual refresh button + last-checked timestamp ────────────────────────
    _hdr_c1, _hdr_c2 = st.columns([5, 2])
    with _hdr_c1:
        st.markdown(
            "<p style='color:#6b7a8d;font-size:12px'>Auto-updated from SEBI and BSE every 30 minutes. "
            "Hardcoded entries supplemented with live SEBI scraping. "
            "New watchlist hits flagged automatically.</p>",
            unsafe_allow_html=True)
    with _hdr_c2:
        if st.button("🔄 Check for new filings", key="drhp_manual_refresh"):
            # Force-clear cache so next fetch is fresh
            for _ck in ["sebi_all_filings", "sebi_all_ts"]:
                st.session_state.pop(_ck, None)
            st.rerun()
        _last_chk = st.session_state.get("sebi_last_checked", "Not yet checked")
        st.caption(f"Last checked: {_last_chk}")

    # Fetch live SEBI/BSE filings to supplement KNOWN_FILINGS
    with st.spinner("Fetching SEBI / BSE filings…"):
        live_sebi = _sebi_fetch_all()

    known_cos  = {f["company"].lower() for f in KNOWN_FILINGS}
    unique_live = [
        f for f in live_sebi
        if not _fuzzy_known(f.get("company", "").lower(), known_cos)
        and f.get("company", "").lower() not in _LIVE_BLOCKLIST
        and f.get("is_tech", False)
    ]
    combined = KNOWN_FILINGS + unique_live  # known first (curated), then live auto-detected

    # New filings alert (last 7 days from live source)
    new_filings = [f for f in unique_live if _is_new(f.get("filing_date", ""), days=7)]
    watchlist_hits = [f for f in unique_live if f.get("is_watchlist")]
    if watchlist_hits:
        st.markdown(
            f"<div style='background:#dcfce7;border:2px solid #86efac;border-radius:10px;"
            f"padding:14px 18px;margin-bottom:10px'>"
            f"<b style='color:#166534'>⚡ {len(watchlist_hits)} Watchlist Hit(s): "
            f"{', '.join(f['company'] for f in watchlist_hits)}</b></div>",
            unsafe_allow_html=True)
    if new_filings:
        st.markdown(
            f"<div style='background:#fef9c3;border:2px solid #fbbf24;border-radius:10px;"
            f"padding:14px 18px;margin-bottom:16px'>"
            f"<b style='color:#92400e'>🆕 {len(new_filings)} new SEBI filing(s) in the last 7 days: "
            f"{', '.join(f['company'] for f in new_filings)}</b></div>",
            unsafe_allow_html=True)

    # ── Inline filters ────────────────────────────────────────────────────────
    st.markdown(
        f"<div style='background:{CARD_BG};border:1px solid {BORDER};"
        f"border-radius:10px;padding:12px 16px;margin:12px 0'>",
        unsafe_allow_html=True)
    fc1, fc2, fc3 = st.columns([2, 2, 2])
    with fc1:
        types   = ["All"] + sorted(set(f.get("type", "DRHP") for f in combined))
        sel_type = st.selectbox("Filing Type", types, key="drhp_type")
    with fc2:
        secs    = sorted(set(f.get("sector", "") for f in combined if f.get("sector")))
        sel_sec = st.selectbox("Sector", ["All"] + secs, key="drhp_sec")
    with fc3:
        z47_only = st.checkbox("Tech/Fintech only", value=False, key="drhp_z47")
    st.markdown("</div>", unsafe_allow_html=True)

    # Build display rows
    _SEBI_SEARCH_URL = ("https://www.sebi.gov.in/sebiweb/home/HomeAction.do"
                        "?doListing=yes&sid=3&ssid=15&smid=10")
    rows = []
    for f in combined:
        z47r   = _is_z47(f.get("company", ""), f.get("sector", ""))
        new_f  = _is_new(f.get("filing_date", ""), days=7)
        wl_hit = f.get("is_watchlist", False)

        # ── Build the DRHP link-column URL ────────────────────────────────────
        _dco   = f.get("company", "")
        _de    = DRHP_LINKS.get(_dco, {})
        _dtype = _de.get("type", "")
        if _dtype == "CONFIDENTIAL" or f.get("confidential"):
            _drhp_url = ""           # No link — confidential badge shown in detail pane
        elif _de.get("url"):
            _drhp_url = _de["url"]   # Verified hardcoded URL (PDF or filing page)
        elif f.get("pdf_link"):
            _drhp_url = f["pdf_link"]
        else:
            _drhp_url = _SEBI_SEARCH_URL  # Fallback: SEBI search page

        rows.append({
            "Company":      _dco,
            "Filing Date":  f.get("filing_date", ""),
            "Type":         f.get("type", "DRHP"),
            "Sector":       (f.get("sector") or "–").title(),
            "Issue Size":   f.get("issue_size", "TBD"),
            "BRLMs":        f.get("brlms", "TBD"),
            "DRHP":         _drhp_url,
            # Internal cols for filtering / detail pane (not shown in table)
            "_z47":         z47r, "_new": new_f, "_wl": wl_hit,
            "_sec_raw":     (f.get("sector") or "").lower(),
            "_type_raw":    f.get("type", "DRHP"),
            "_desc":        f.get("description", ""),
            "_pdf":         f.get("pdf_link"),
            "_conf":        f.get("confidential", False),
        })

    df = pd.DataFrame(rows)
    if sel_type != "All":
        df = df[df["_type_raw"] == sel_type]
    if sel_sec != "All":
        df = df[df["_sec_raw"] == sel_sec.lower()]
    if z47_only:
        df = df[df["_z47"]]

    disp_cols = ["Company", "Filing Date", "Type", "Sector", "Issue Size", "BRLMs", "DRHP"]

    def _hl(row):
        # Highlight uses internal _wl / _new columns (not shown in table)
        if row.get("_wl"):
            return ["background-color:#dcfce7"] * len(row)
        if row.get("_new"):
            return ["background-color:#fef9c3"] * len(row)
        return [""] * len(row)

    # Apply highlighting on full df (which has _wl / _new), then show only disp_cols
    styled = df.style.apply(_hl, axis=1)
    st.dataframe(styled, use_container_width=True, hide_index=True, height=500,
                 column_order=disp_cols,
                 column_config={
                     "Company":    st.column_config.TextColumn(width="medium"),
                     "Issue Size": st.column_config.TextColumn(width="small"),
                     "BRLMs":      st.column_config.TextColumn(width="medium"),
                     "DRHP":       st.column_config.LinkColumn(
                                       "DRHP", display_text="📄 View",
                                       width="small"),
                 })

    st.markdown(
        f'<div style="color:#a38060;font-size:11px;text-align:right">'
        f'Sources: SEBI Live + BSE Live + Curated | Updated: {_now_ist()}</div>',
        unsafe_allow_html=True)

    # ── Quick Summary buttons — one per filtered company ─────────────────────
    st.markdown("---")
    st.markdown("### 📋 Company Summaries")
    st.caption("Click any company to view a structured one-page brief (business model, financials, risks, investors).")
    _summary_rows = [r["Company"] for r in rows
                     if sel_type == "All" or r["_type_raw"] == sel_type]
    # Re-apply active filters
    if sel_sec != "All":
        _summary_rows = [r["Company"] for r in rows
                         if r["_sec_raw"] == sel_sec.lower()
                         and (sel_type == "All" or r["_type_raw"] == sel_type)]
    if z47_only:
        _summary_rows = [r["Company"] for r in rows
                         if r["_z47"]
                         and (sel_type == "All" or r["_type_raw"] == sel_type)
                         and (sel_sec == "All" or r["_sec_raw"] == sel_sec.lower())]
    # Deduplicate while preserving order
    _seen = set(); _deduped_rows = []
    for _c in _summary_rows:
        if _c not in _seen:
            _seen.add(_c); _deduped_rows.append(_c)

    _COLS_PER_ROW = 4
    for _chunk_start in range(0, len(_deduped_rows), _COLS_PER_ROW):
        _chunk = _deduped_rows[_chunk_start: _chunk_start + _COLS_PER_ROW]
        _btn_cols = st.columns(_COLS_PER_ROW)
        for _ci, _co in enumerate(_chunk):
            with _btn_cols[_ci]:
                if st.button(f"📋 {_co}", key=f"sum_btn_{_co}", use_container_width=True):
                    _show_company_summary(_co)

    # ── Summary Stats ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Summary Statistics")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Filings",     len(rows))
    m2.metric("New (7 days)",      sum(1 for r in rows if r["_new"]))
    m3.metric("Watchlist Hits",    sum(1 for r in rows if r.get("_wl")))
    m4.metric("Tech / Fintech",    sum(1 for r in rows if r["_z47"]))
    m5.metric("DRHP vs RHP",
              f"{sum(1 for r in rows if r['_type_raw']=='DRHP')}D "
              f"/ {sum(1 for r in rows if r['_type_raw']=='RHP')}R")
    st.markdown(
        f'<div style="color:#a38060;font-size:11px;text-align:right">'
        f'Updated: {_now_ist()}</div>',
        unsafe_allow_html=True)

    # ── NEWS FEED (moved to last) ──────────────────────────────────────────────
    st.markdown("---")
    _render_news_feed()
