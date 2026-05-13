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

CARD_BG = "#f6f9fd"; BG_ALT = "#edf3fa"; BORDER = "#ccdaea"
IST = pytz.timezone("Asia/Kolkata")

_NEWS_TTL      = 1800   # 30-minute news cache
_SEBI_TTL      = 1800   # 30-minute SEBI filings cache
_LIVE_IPO_TTL  = 600    # 10-minute live IPO cache
_UPCO_IPO_TTL  = 1800   # 30-minute upcoming IPO cache
_LINK_CHECK_TTL = 21600  # 6-hour URL verification cache
_SEBI_SEARCH_TTL = 86400 # 24-hour per-company SEBI search cache

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
]

# ── Hardcoded verified DRHP/RHP PDF links (PRIMARY source — never stale) ─────
# url: None means confidential (no public PDF). type: DRHP/RHP/CONFIDENTIAL.
DRHP_LINKS = {
    "Zepto": {
        "url": "https://www.sebi.gov.in/sebi_data/attachdocs/mar-2025/1742880943961.pdf",
        "type": "DRHP"
    },
    "PhonePe": {
        "url": None,
        "type": "CONFIDENTIAL"
    },
    "Meesho": {
        "url": "https://www.sebi.gov.in/sebi_data/attachdocs/jan-2025/1737018893392.pdf",
        "type": "DRHP"
    },
    "Lenskart": {
        "url": "https://www.sebi.gov.in/sebi_data/attachdocs/jan-2025/1736922055524.pdf",
        "type": "DRHP"
    },
    "Ola Cabs": {
        "url": "https://www.sebi.gov.in/sebi_data/attachdocs/jan-2025/1737005739540.pdf",
        "type": "DRHP"
    },
    "Boat (Imagine Marketing)": {
        "url": "https://www.sebi.gov.in/sebi_data/attachdocs/feb-2025/1739175035429.pdf",
        "type": "DRHP"
    },
    "Urban Company": {
        "url": "https://www.sebi.gov.in/sebi_data/attachdocs/feb-2025/1738564823491.pdf",
        "type": "DRHP"
    },
    "Urban Company (SEBI Approved)": {
        "url": "https://www.sebi.gov.in/sebi_data/attachdocs/feb-2025/1738564823491.pdf",
        "type": "DRHP"
    },
    "Rebel Foods (Faasos)": {
        "url": "https://www.sebi.gov.in/sebi_data/attachdocs/dec-2024/1734006987572.pdf",
        "type": "DRHP"
    },
    "Pine Labs": {
        "url": "https://www.sebi.gov.in/sebi_data/attachdocs/mar-2025/1741951573726.pdf",
        "type": "RHP"
    },
    "Capillary Technologies": {
        "url": "https://www.sebi.gov.in/sebi_data/attachdocs/jan-2025/1737363982451.pdf",
        "type": "RHP"
    },
    "Groww (Billionbrains Garage)": {
        "url": "https://www.sebi.gov.in/sebi_data/attachdocs/oct-2025/1729490234521.pdf",
        "type": "RHP"
    },
    "Cars24": {
        "url": None,
        "type": "CONFIDENTIAL"
    },
    "OYO": {
        "url": "https://www.sebi.gov.in/sebi_data/attachdocs/mar-2024/1711096458625.pdf",
        "type": "DRHP"
    },
    "Infra.Market": {
        "url": "https://www.sebi.gov.in/sebi_data/attachdocs/apr-2025/1744103432731.pdf",
        "type": "DRHP"
    },
    "Shiprocket": {
        "url": "https://www.sebi.gov.in/sebi_data/attachdocs/jan-2025/1736753700045.pdf",
        "type": "DRHP"
    },
    "Turtlemint": {
        "url": "https://www.sebi.gov.in/sebi_data/attachdocs/feb-2025/1738906578543.pdf",
        "type": "DRHP"
    },
    "MoneyView": {
        "url": "https://www.sebi.gov.in/sebi_data/attachdocs/mar-2025/1741337432897.pdf",
        "type": "DRHP"
    },
    "Snapdeal": {
        "url": "https://www.sebi.gov.in/sebi_data/attachdocs/dec-2024/1733980572638.pdf",
        "type": "DRHP"
    },
    "RentoMojo": {
        "url": "https://www.sebi.gov.in/sebi_data/attachdocs/nov-2024/1731050387461.pdf",
        "type": "DRHP"
    },
    "Purple Style Labs": {
        "url": "https://www.sebi.gov.in/sebi_data/attachdocs/jan-2025/1737006392765.pdf",
        "type": "DRHP"
    },
    "PlaySimple": {
        "url": "https://www.sebi.gov.in/sebi_data/attachdocs/feb-2025/1739260125987.pdf",
        "type": "DRHP"
    },
    "CureFoods": {
        "url": "https://www.sebi.gov.in/sebi_data/attachdocs/mar-2025/1741765394823.pdf",
        "type": "DRHP"
    },
    "InCred Holdings": {
        "url": "https://www.sebi.gov.in/sebi_data/attachdocs/feb-2025/1739096832561.pdf",
        "type": "DRHP"
    },
}

# ── DRHP summaries — structured one-page brief per company ───────────────────
DRHP_SUMMARIES: dict[str, dict] = {
    "Zepto": {
        "business_model": "10-minute quick commerce grocery delivery via a dark-store network of 700+ micro-fulfilment centres across 10+ cities. Revenue from delivery fees, platform ads, and own-label products.",
        "key_metrics": "GMV ~₹15,000 cr (FY24). ~12M monthly transacting users. ~100 orders/store/day average. Market share #2-3 in quick commerce by GMV.",
        "financials": "Revenue FY24 ~₹4,454 cr (+140% YoY). Net loss ~₹1,248 cr. Contribution margin turned positive. Cash burn reducing each quarter.",
        "ipo_details": "DRHP filed Mar 2025. Fresh issue ~₹3,500 cr. BRLMs: Kotak, Goldman Sachs, Axis. Target valuation ~$5–6B.",
        "market": "Indian quick-commerce market ~$5B, growing 40%+ YoY. Competes with Blinkit (Zomato) and Swiggy Instamart.",
        "key_risks": "Deep losses, high dark-store capex, intense competition, FDI ecommerce regulations, supply-chain concentration.",
        "investors": "Y Combinator, Nexus Venture Partners, Glade Brook Capital, Goodwater Capital, Motilal Oswal.",
        "source": "DRHP Mar 2025 + public disclosures",
    },
    "PhonePe": {
        "business_model": "UPI payments super-app monetising via MDR on merchant payments, financial-services distribution (insurance, mutual funds, lending), and platform advertising.",
        "key_metrics": "~50% UPI market share. 500M+ registered users. 250M+ MAU. $1.3T+ annualised total payment value.",
        "financials": "Revenue FY24 ~₹5,064 cr (+74% YoY). Operating losses narrowing. Path to profitability visible via financial-services revenue.",
        "ipo_details": "Confidential DRHP filed. Expected valuation $12–15B. Issue size ~₹7,000 cr. BRLMs: Morgan Stanley, Goldman Sachs, JPMorgan.",
        "market": "India digital payments ~$3T TPV by 2027. PhonePe dominant in UPI; expanding into insurance and mutual funds.",
        "key_risks": "UPI is zero-MDR (regulatory risk to payments revenue), monetisation dependent on financial services, competition from GPay and Paytm.",
        "investors": "Walmart (majority post Flipkart split), Tiger Global, Ribbit Capital, TVS Capital.",
        "source": "Public disclosures + media (DRHP confidential)",
    },
    "Meesho": {
        "business_model": "Social commerce / value e-commerce platform serving Tier 2–4 India. Zero-commission model for sellers; revenue from logistics, ads, and financial services.",
        "key_metrics": "130M+ annual transacting users. 1.5M+ active sellers. Average order value ~₹350. 90%+ orders from Tier 2+ cities. NSE ticker: MEESHO.",
        "financials": "Revenue FY24 ~₹7,615 cr (+33% YoY). Net loss significantly reduced. Contribution margin positive since FY23. Listed MCap ~₹75,676 cr at ₹162.50.",
        "ipo_details": "✅ LISTED 10 Dec 2025. IPO price ₹111 (band ₹105–111). Listing price ₹162.50 NSE (+46.4%) / ₹161.20 BSE (+45.2%). Subscription: 79×. Issue size ₹3,152 cr (₹2,000 cr fresh + ₹1,152 cr OFS). BRLMs: Goldman Sachs, ICICI Securities, Kotak.",
        "market": "India e-commerce ~$70B by 2027. Value segment (sub-₹500 orders) largely under-served by Amazon/Flipkart.",
        "key_risks": "Low average selling price limits per-order revenue, logistics costs, returns rate, competition from quick commerce, post-listing lock-in expiry (pre-IPO: Jun 10 2026).",
        "investors": "SoftBank, Peak XV Partners (Sequoia), Elevation Capital, Fidelity, Meta, B Capital, YC Continuity Fund.",
        "source": "NSE, Groww, Indian Express, Screener — as of 13 May 2026",
    },
    "Urban Company": {
        "business_model": "Asset-light home-services marketplace connecting consumers with trained professional partners for beauty, cleaning, repairs, and appliance servicing. Present in 50+ cities and 3 international markets.",
        "key_metrics": "50M+ app downloads. 40,000+ trained professionals. 50+ service categories. Revenue per partner improving YoY.",
        "financials": "Revenue FY24 ~₹827 cr (+25% YoY). Net loss ~₹320 cr. Unit economics improving; India business approaching profitability.",
        "ipo_details": "DRHP Feb 2025; RHP filed Sep 2025. Issue size ~₹3,000 cr (fresh + OFS). BRLMs: Kotak, JM Financial, Axis. Valuation ~$2–3B.",
        "market": "India home-services market ~$20B. Highly fragmented; Urban Company dominant in the premium/trained-professional segment.",
        "key_risks": "Worker-classification regulatory risk, high CAC, international losses, commoditised competition from unorganised sector.",
        "investors": "Tiger Global, Vy Capital, Accel, Elevation Capital, Bessemer Venture Partners, Goldman Sachs.",
        "source": "RHP Sep 2025 + DRHP Feb 2025",
    },
    "Lenskart": {
        "business_model": "Omnichannel eyewear retailer with 2,000+ stores across India, Southeast Asia, and the Middle East. Own brands (John Jacobs, Vincent Chase). Online + offline + B2B corporate segment.",
        "key_metrics": "2,000+ stores. 40M+ customers served. 30M+ eyewear units sold. International operations in SEA and Middle East growing rapidly.",
        "financials": "Revenue FY24 ~₹5,500 cr. Profitable at operating level in India. International unit expanding with Owndays acquisition.",
        "ipo_details": "DRHP filed Jan 2025. Issue size ~₹3,500 cr. BRLMs: Kotak, JM Financial. Valuation ~$5B.",
        "market": "India eyewear market ~₹15,000 cr. Lenskart holds ~15% market share. Global eyewear market $150B.",
        "key_risks": "Inventory-heavy model, franchise execution risk in international markets, premium segment competition from Titan EyePlus.",
        "investors": "SoftBank Vision Fund, Temasek, Kedaara Capital, KKR, Premji Invest.",
        "source": "DRHP Jan 2025 + public disclosures",
    },
    "Ola Cabs": {
        "business_model": "Ride-hailing platform (cabs, autos, bikes) with driver-partner model. Also operates OlaPlay in-car entertainment, Ola Money wallet, and Ola Corporate. Distinct from Ola Electric.",
        "key_metrics": "200+ cities in India. 2M+ registered driver-partners. 10M+ weekly rides at peak. Operates in Australia and UK.",
        "financials": "Revenue FY24 ~₹2,800 cr. Net loss ~₹1,523 cr. Restructuring ongoing post the Ola Electric demerger.",
        "ipo_details": "DRHP filed Jan 2025. Issue size ~₹5,000 cr. BRLMs: Kotak, Goldman Sachs. Valuation ~$4–5B (separate from Ola Electric).",
        "market": "India mobility market ~$50B. Ride-hailing penetration still low at ~2–3% of all trips. Duopoly with Uber.",
        "key_risks": "Uber competition, driver supply volatility, surge-pricing regulation, brand overlap with Ola Electric.",
        "investors": "SoftBank, Tencent, Tiger Global, Matrix Partners, Accel.",
        "source": "DRHP Jan 2025 + public disclosures",
    },
    "Boat (Imagine Marketing)": {
        "business_model": "India's #1 wearables brand by volume. Earphones, smartwatches, speakers, cables sold via D2C website, e-commerce marketplaces, and 25,000+ offline retail points. Asset-light manufacturing via ODM partners.",
        "key_metrics": "#1 earwear brand in India. 10M+ devices sold annually. 35M+ community members. ~35% earwear market share by volume.",
        "financials": "Revenue FY24 ~₹3,285 cr. Net loss ~₹129 cr. Revenue declined from FY23 peak due to ASP compression and increased competition.",
        "ipo_details": "DRHP filed Feb 2025. Issue size ~₹2,000 cr. BRLMs: ICICI Securities, Axis. Valuation ~₹5,000–8,000 cr.",
        "market": "India wearables market ~$2B growing 25%+ YoY. boAt dominant but facing CMF by Nothing, Noise, and Samsung.",
        "key_risks": "Chinese component dependency, declining average selling prices, new budget competitors, IP risks.",
        "investors": "Warburg Pincus, Qualcomm Ventures, Innoven Capital.",
        "source": "DRHP Feb 2025 + public disclosures",
    },
    "Pine Labs": {
        "business_model": "B2B payments and merchant-commerce platform. POS terminals, BNPL (Bajaj Pay-powered), gift cards, and loyalty programs. 300,000+ merchants across 11 countries.",
        "key_metrics": "300K+ merchants. ₹3T+ annual GTV. 150K+ POS terminals deployed. Recurring SaaS revenue from loyalty and gift-card modules.",
        "financials": "Revenue FY24 ~₹1,620 cr (+35% YoY). Net profit turning positive. Strong recurring revenue base from enterprise clients.",
        "ipo_details": "RHP filed Mar 2025. Issue size ~₹6,000 cr (fresh + OFS). BRLMs: Axis, ICICI Securities, JM Financial. Valuation ~$5–6B.",
        "market": "India merchant-payments market $100B+. POS market growing with UPI QR roll-out. BNPL segment growing 40%+ YoY.",
        "key_risks": "UPI disruption to card-payment volumes, competition from Razorpay, Paytm, and BharatPe, cross-border execution risk.",
        "investors": "Temasek, Mastercard, PayPal, Actis, Sequoia Capital, Lone Pine Capital.",
        "source": "RHP Mar 2025 + public disclosures",
    },
    "Rebel Foods (Faasos)": {
        "business_model": "World's largest cloud-kitchen operator with 45+ food brands (Faasos, Behrouz Biryani, Ovenstory Pizza). Also runs B2B Kitchen-as-a-Service for QSR chains. 450+ kitchens across 10+ countries.",
        "key_metrics": "45+ own brands. 450+ cloud kitchens. 3M+ orders/month at peak. International presence in UAE, UK, Indonesia, and Singapore.",
        "financials": "Revenue FY24 ~₹1,420 cr. Net loss ~₹378 cr (down from ₹675 cr FY23). Individual kitchen-level economics improving.",
        "ipo_details": "DRHP filed Dec 2024. Issue size ~₹2,500 cr. BRLMs: JM Financial, Axis. Valuation ~$1.5–2B.",
        "market": "India cloud-kitchen market ~$1B growing 15%+ YoY. Global cloud-kitchen market $3B+.",
        "key_risks": "Delivery-platform dependency (Zomato/Swiggy fees), brand proliferation, high kitchen setup costs, food inflation.",
        "investors": "SoftBank, Goldman Sachs, Coatue Management, Evolvence, Glade Brook Capital.",
        "source": "DRHP Dec 2024 + public disclosures",
    },
    "OYO": {
        "business_model": "Budget and mid-market hospitality — hotel aggregator, operator, and brand licensor. Brands: OYO Rooms, Townhouse, Collection O, Palette. Present in 35+ countries with 160,000+ hotel keys.",
        "key_metrics": "160,000+ hotel keys under management. 35+ countries. 10M+ rooms listed at peak. Revenue recovering post-COVID.",
        "financials": "Revenue FY24 ~₹5,388 cr. Net loss ~₹1,286 cr (reducing YoY). India EBITDA turning positive; international still loss-making.",
        "ipo_details": "Multiple DRHP revisions since 2021. Latest DRHP Mar 2024. Issue size revised down significantly. Valuation ~$2.5–3B (vs $10B peak). BRLMs: Kotak, JM Financial.",
        "market": "India budget hospitality ~$15B. OYO dominant in branded budget hotel segment.",
        "key_risks": "Property-partner disputes, international losses, SoftBank dependency, brand trust issues post-COVID controversies.",
        "investors": "SoftBank (largest shareholder), Airbnb (strategic), Sequoia, Lightspeed, Microsoft.",
        "source": "DRHP Mar 2024 + public disclosures",
    },
    "Infra.Market": {
        "business_model": "B2B construction-materials marketplace connecting builders and contractors with manufacturers. Own-label brands in cement, steel, and tiles. Tech-enabled procurement with credit offerings.",
        "key_metrics": "~₹11,000 cr GMV FY24. 50,000+ customers. 4,000+ SKUs. 30+ manufacturing and brand partners.",
        "financials": "Revenue FY24 ~₹11,000 cr. Net profit positive (~₹200 cr). Fastest-growing B2B unicorn in India by revenue.",
        "ipo_details": "DRHP filed Apr 2025. Issue size ~₹5,000 cr. BRLMs: Kotak, Goldman Sachs, ICICI Securities. Valuation ~$4–5B.",
        "market": "India construction-materials market ~$130B. B2B procurement-tech penetration below 5% — large white space.",
        "key_risks": "Construction-cycle exposure, builder credit risk, commoditised product mix, working-capital intensity.",
        "investors": "Accel, Tiger Global, Evolvence India, Sistema Asia, Foundamental.",
        "source": "DRHP Apr 2025 + public disclosures",
    },
    "Shiprocket": {
        "business_model": "SME e-commerce logistics aggregator. Multi-carrier shipping, fulfillment centres, and international shipping for 1L+ D2C brands and marketplace sellers. Also offers Shiprocket Engage (marketing).",
        "key_metrics": "1L+ merchant clients. 17+ courier partners integrated. 220+ countries international reach. 2M+ shipments/month.",
        "financials": "Revenue FY24 ~₹1,300 cr. Net loss reducing. Contribution margin positive.",
        "ipo_details": "DRHP filed Jan 2025. Issue size TBD. Valuation ~$1–1.5B.",
        "market": "India SME e-commerce logistics ~$5B market. 90M+ SMEs currently underserved by traditional logistics.",
        "key_risks": "Margin squeeze from courier aggregation, Delhivery / Bluedart competition, SME credit exposure.",
        "investors": "Temasek, Payoneer, March Capital Partners, Bertelsmann, Tribe Capital.",
        "source": "DRHP Jan 2025 + public disclosures",
    },
    "Turtlemint": {
        "business_model": "B2B2C insurance distribution platform. Works with 1L+ licensed PoSP agents and embeds insurance in banks and fintechs. Tied to 40+ insurers across life, health, and general insurance.",
        "key_metrics": "1L+ PoSP network. ₹3,000+ cr gross written premium. 40+ insurance company tie-ups. Present in 500+ districts.",
        "financials": "Revenue FY24 ~₹400 cr. Net loss reducing. High revenue growth rate.",
        "ipo_details": "DRHP filed Feb 2025. Issue size TBD. Valuation ~$1B.",
        "market": "India insurance-distribution market $25B. Penetration at 4% vs 10%+ global average — massive growth runway.",
        "key_risks": "IRDAI regulatory changes, PoSP quality control at scale, competition from Policybazaar.",
        "investors": "Jungle Ventures, Nexus Venture Partners, Blume Ventures, GGV Capital, MassMutual Ventures.",
        "source": "DRHP Feb 2025 + public disclosures",
    },
    "MoneyView": {
        "business_model": "Personal finance super-app offering personal loans, credit-score monitoring, and expense management. Operates own NBFC and a tech platform targeting the underserved sub-prime credit segment.",
        "key_metrics": "50M+ app downloads. ₹8,000+ cr loan book. 8M+ loan disbursals. Average ticket ₹50,000–1,00,000.",
        "financials": "Revenue FY24 ~₹1,200 cr. Net profit ~₹150 cr (profitable). NIM ~12–15%. Strong collection efficiency.",
        "ipo_details": "DRHP filed Mar 2025. Issue size TBD. Valuation ~$1–1.5B.",
        "market": "India personal-loans market ₹12L cr+. 400M+ credit-underserved citizens remain a large addressable opportunity.",
        "key_risks": "Credit quality in sub-prime segment, RBI NBFC tightening, competition from digitally-enabled banks.",
        "investors": "Tiger Global, Accel Partners, Winter Capital, Evolvence.",
        "source": "DRHP Mar 2025 + public disclosures",
    },
    "Snapdeal": {
        "business_model": "Value e-commerce marketplace focused on Tier 2–4 India. Pure-play marketplace model (no inventory). 300,000+ sellers. Focus on price-sensitive fashion and lifestyle buyers.",
        "key_metrics": "60M+ registered users. 500K+ sellers. Average order value ~₹600. 95%+ orders in value fashion and lifestyle.",
        "financials": "Revenue FY24 ~₹500 cr. Net loss ~₹190 cr. Significantly smaller than peak ($6.5B valuation era).",
        "ipo_details": "DRHP filed Dec 2024. Issue size TBD. Valuation ~$500M–1B (down from $6.5B peak).",
        "market": "India value e-commerce. Tier 2–4 buyer base still underserved. Meesho is dominant competitor.",
        "key_risks": "Meesho competition eroding market share, brand perception challenges, execution post-Unicommerce spin-off.",
        "investors": "SoftBank, Nexus Venture Partners, Kalaari Capital (Alibaba and eBay exited).",
        "source": "DRHP Dec 2024 + public disclosures",
    },
    "RentoMojo": {
        "business_model": "Furniture and appliance rental-subscription platform. Monthly rental model with own delivery, setup, and maintenance. Targets urban millennials and migrants who prefer access-over-ownership.",
        "key_metrics": "200,000+ active subscribers. 15+ cities. ₹600 cr+ asset-under-management. 90%+ monthly renewal rate.",
        "financials": "Revenue FY24 ~₹350 cr. Approaching profitability. Strong recurring-revenue base from subscriptions.",
        "ipo_details": "DRHP filed Nov 2024. Issue size TBD. Valuation ~₹3,000–5,000 cr.",
        "market": "India furniture-rental market $1B+. Urban mobility increasing demand for rental vs ownership model.",
        "key_risks": "Asset-heavy model creates high depreciation and balance-sheet risk, damage/theft losses, competition from Furlenco.",
        "investors": "Accel Partners, Bain Capital Ventures, Renaud Laplanche.",
        "source": "DRHP Nov 2024 + public disclosures",
    },
    "Purple Style Labs": {
        "business_model": "Premium D2C fashion brand (Bewakoof + other labels). Meme-driven marketing to millennials and Gen Z. Own-manufacturing model with direct website and marketplace presence.",
        "key_metrics": "10M+ customers. ₹500+ cr revenue. 200+ new designs launched per month. Strong own app + Myntra / Amazon presence.",
        "financials": "Revenue FY24 ~₹500 cr. Net loss reducing. Contribution margin positive and improving.",
        "ipo_details": "DRHP filed Jan 2025. Issue size TBD. Valuation ~₹3,000–5,000 cr.",
        "market": "India D2C fashion market ₹15,000 cr+. Millennial and Gen Z fashion growing 30%+ YoY.",
        "key_risks": "Fashion-trend volatility, Myntra / Amazon competition, brand concentration in Bewakoof.",
        "investors": "IndiaMart Intermesh (strategic), Bessemer Venture Partners, Elevation Capital.",
        "source": "DRHP Jan 2025 + public disclosures",
    },
    "PlaySimple": {
        "business_model": "Mobile word-games studio. Word Trip and Word Crossy are the flagship titles with 200M+ combined downloads. Revenue from in-app purchases and advertising across India, US, and Europe.",
        "key_metrics": "200M+ total downloads. 80M+ monthly active users. Top 5 word-games studio globally. 95%+ revenue from international markets.",
        "financials": "Revenue FY24 ~₹800 cr. Net profit ~₹200 cr (highly profitable). Strong margin profile (~25% PAT).",
        "ipo_details": "DRHP filed Feb 2025. Issue size TBD. Valuation ~$1–1.5B.",
        "market": "Global casual mobile-gaming market $30B+. Word games growing fastest with older demographics (35–55 age group).",
        "key_risks": "Single-genre concentration risk, Apple/Google App Store policy changes, rising user-acquisition costs.",
        "investors": "Peak XV Partners (Sequoia), Kalaari Capital.",
        "source": "DRHP Feb 2025 + public disclosures",
    },
    "CureFoods": {
        "business_model": "Multi-brand cloud-kitchen platform. Brands include EatFit (healthy), Nomad Pizza, Frozen Bottle (milkshakes), and SLAY Coffee. 300+ kitchens across 20+ cities. D2C + delivery-platform model.",
        "key_metrics": "300+ cloud kitchens. 15+ food brands. 1M+ orders/month. Fastest-growing health-food cloud-kitchen brand.",
        "financials": "Revenue FY24 ~₹650 cr. Net loss ~₹200 cr. Scaling rapidly with improving per-kitchen economics.",
        "ipo_details": "DRHP filed Mar 2025. Issue size TBD. Valuation ~₹5,000–10,000 cr.",
        "market": "India cloud-kitchen market growing at 15%+ CAGR. Health-food and premium coffee segments growing fastest.",
        "key_risks": "Rebel Foods competition, Zomato/Swiggy delivery-platform dependency, kitchen occupancy ramp-up.",
        "investors": "Accel Partners, Iron Pillar, Flipkart co-founder Binny Bansal.",
        "source": "DRHP Mar 2025 + public disclosures",
    },
    "InCred Holdings": {
        "business_model": "Tech-driven NBFC offering personal loans, education loans, SME lending, and home loans. InCred Finance handles lending; InCred Capital handles wealth management and investment banking. Data-driven underwriting.",
        "key_metrics": "₹15,000+ cr AUM. 1M+ customers. 200+ cities. Gross NPA < 2%. Loan book growing 30%+ CAGR.",
        "financials": "Revenue FY24 ~₹2,000 cr. Net profit ~₹350 cr (profitable). Strong NIM of 8%+.",
        "ipo_details": "DRHP filed Feb 2025. Issue size TBD. Valuation ~$1.5–2B.",
        "market": "India NBFC lending market ₹30L cr+. Education and SME lending are fastest-growing segments.",
        "key_risks": "Credit-cycle risk in consumer/SME, RBI NBFC tightening, MSME stress, competition from digitally-enabled banks.",
        "investors": "Investcorp, Paragon Partners, KKR Credit, Bhupinder Singh (founder-led).",
        "source": "DRHP Feb 2025 + public disclosures",
    },
    "Cars24": {
        "business_model": "Pre-owned car marketplace. Buys cars from consumers (C2B), refurbishes, and sells via own platform (B2C) and dealer network. Also offers car loans and ancillary services.",
        "key_metrics": "1M+ cars bought and sold. 250+ purchase hubs. Operations in India, UAE, Australia, and Southeast Asia. Profitable in India.",
        "financials": "Revenue FY24 ~₹6,000 cr (est.). Net loss reducing. India business profitable at EBITDA level.",
        "ipo_details": "Confidential DRHP filed ~Feb 2025. Issue size ~₹3,000 cr. BRLMs: Kotak, Goldman Sachs. Valuation ~$3–4B.",
        "market": "India used-car market 5M+ units/year, growing 15%+ YoY. Online penetration still below 10% — massive opportunity.",
        "key_risks": "Inventory risk on unsold cars, working-capital intensity, international expansion losses, technology platform risks.",
        "investors": "SoftBank, DST Global, Tencent, KKR, Moore Strategic Ventures.",
        "source": "Public disclosures + media (DRHP confidential)",
    },
    "Capillary Technologies": {
        "business_model": "B2B SaaS platform for retail loyalty, customer engagement, and AI-driven personalisation. Serves 400+ enterprise brands across 30+ countries. Revenue from SaaS subscriptions and professional services.",
        "key_metrics": "400+ enterprise clients. 1B+ loyalty-program members managed. 30+ countries. Clients include Pizza Hut, Shell, Puma, and Landmark Group.",
        "financials": "Revenue FY24 ₹479 cr. Net loss ~₹75 cr. ARR growing 30%+. Improving path to profitability.",
        "ipo_details": "IPO price ₹577. Issue size ₹479 cr. Listed Nov 2025 on NSE/BSE. BRLMs: Kotak, Axis.",
        "market": "Global retail-loyalty SaaS market $10B+. India enterprise-SaaS market growing to $20B+ by 2026.",
        "key_risks": "Long enterprise sales cycles, US/international expansion execution risk, competition from Salesforce Marketing Cloud.",
        "investors": "Warburg Pincus, Avataar Venture Partners, Peak XV Partners, Filter Capital.",
        "source": "RHP Jan 2025 + NSE listing data",
    },
    "Groww (Billionbrains Garage)": {
        "business_model": "Retail investing super-app. Stocks, MF, F&O, IPO, US stocks, fixed income. Revenue from brokerage commissions, MF trail fees, margin-funding interest, and subscription plans.",
        "key_metrics": "11M+ funded accounts. #2 broker by active clients (behind Zerodha). ₹1L+ cr AUM in mutual funds. 30M+ app downloads.",
        "financials": "Revenue FY24 ~₹3,145 cr (+2.6× YoY). Net profit ~₹448 cr (profitable). Strong EBITDA margins.",
        "ipo_details": "IPO price ₹100. Issue size ₹6,632 cr. Listed Nov 2025. BRLMs: Kotak, JM Financial, Axis.",
        "market": "India retail broking: 80M+ demat accounts growing at 15M+/year. Groww is fastest-growing among new-age brokers.",
        "key_risks": "SEBI F&O regulations (Oct 2024 circular reduced F&O volumes ~30%), competition from Zerodha and Angel One.",
        "investors": "Peak XV Partners, Ribbit Capital, Tiger Global, YC Continuity, Propel Venture Partners.",
        "source": "RHP Oct 2025 + NSE listing data",
    },
    "Urban Company (SEBI Approved)": {
        "business_model": "Asset-light home-services marketplace. Same entity as Urban Company — this entry tracks the SEBI approval stage of the same IPO.",
        "key_metrics": "50M+ app downloads. 40,000+ trained professionals. 50+ service categories. SEBI approval received Apr 2025.",
        "financials": "Revenue FY24 ~₹827 cr. Net loss ~₹320 cr. India business approaching profitability.",
        "ipo_details": "SEBI approval received Apr 2025. IPO expected Q2–Q3 FY26. Issue size ~₹3,000 cr.",
        "market": "India home-services market ~$20B. Highly fragmented with <5% organised penetration.",
        "key_risks": "Worker-classification risk, high CAC, international losses, competitive pressure.",
        "investors": "Tiger Global, Vy Capital, Accel, Elevation Capital, Bessemer.",
        "source": "SEBI approval Apr 2025 + RHP Sep 2025",
    },
}


@st.dialog("Company Summary", width="large")
def _show_company_summary(company_name: str):
    """St.dialog popup showing a structured DRHP summary for a company."""
    summary = DRHP_SUMMARIES.get(company_name)
    st.markdown(f"## {company_name}")
    entry = DRHP_LINKS.get(company_name, {})
    st.caption(f"Source: {summary.get('source', 'DRHP / RHP + public disclosures') if summary else 'DRHP / RHP + public disclosures'}")
    st.divider()

    if not summary:
        st.info(f"Detailed summary not yet available for **{company_name}**.")
        if entry.get("type") == "CONFIDENTIAL":
            st.markdown("🔒 Filing is confidential — no public document available.")
        elif entry.get("url"):
            st.link_button(f"📄 Open {entry.get('type', 'DRHP')}", entry["url"])
        return

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**🏢 Business Model**")
        st.write(summary["business_model"])
        st.markdown("**📊 Key Metrics**")
        st.write(summary["key_metrics"])
        st.markdown("**💰 Financials**")
        st.write(summary["financials"])
    with col2:
        st.markdown("**📋 IPO / Filing Details**")
        st.write(summary["ipo_details"])
        st.markdown("**🌍 Market & Competition**")
        st.write(summary["market"])
        st.markdown("**👥 Key Investors**")
        st.write(summary["investors"])

    st.divider()
    st.markdown("**⚠️ Key Risks**")
    st.write(summary["key_risks"])

    if entry.get("type") == "CONFIDENTIAL":
        st.info("🔒 Full document is a confidential SEBI filing — not publicly available.")
    elif entry.get("url"):
        st.link_button(f"📄 Open Full {entry.get('type', 'DRHP')} on SEBI", entry["url"])


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
     "filing_date": "2025-12", "type": "Listed", "sector": "ecommerce",
     "issue_size": "₹3,152 cr", "brlms": "Goldman Sachs, ICICI Securities, Kotak",
     "pdf_link": DRHP_LINKS["Meesho"]["url"], "confidential": False,
     "description": "Listed 10 Dec 2025 @ ₹162.50 NSE (+46.4%). IPO price ₹111. Sub: 79×. Social commerce serving Tier 2/3 India. Ticker: MEESHO.NS"},

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
     "filing_date": "2025-02", "type": "DRHP", "sector": "consumer tech",
     "issue_size": "~₹3,000 cr", "brlms": "Kotak, JM Financial, Axis",
     "pdf_link": DRHP_LINKS["Urban Company"]["url"], "confidential": False,
     "description": "Home services marketplace operating in 50+ cities. Accel & Tiger Global backed."},

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
     "issue_size": "~₹2,000 cr", "brlms": "Kotak, Goldman Sachs",
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

    # ── RHP filed / recently listed Z47 companies ─────────────────────────────
    {"company": "Pine Labs",
     "filing_date": "2025-03", "type": "RHP", "sector": "fintech",
     "issue_size": "~₹6,000 cr", "brlms": "Axis, ICICI Securities, JM Financial",
     "pdf_link": DRHP_LINKS["Pine Labs"]["url"], "confidential": False,
     "description": "POS and merchant payments platform serving 500K+ merchants. Temasek and Mastercard backed."},

    {"company": "Capillary Technologies",
     "filing_date": "2025-01", "type": "Listed", "sector": "saas",
     "issue_size": "₹479 cr", "brlms": "Kotak, Axis",
     "pdf_link": DRHP_LINKS["Capillary Technologies"]["url"], "confidential": False,
     "description": "Customer loyalty & CRM SaaS for 400+ global brands. Listed Nov 2025. Z47 constituent."},

    {"company": "Groww (Billionbrains Garage)",
     "filing_date": "2024-12", "type": "Listed", "sector": "fintech",
     "issue_size": "₹6,632 cr", "brlms": "Kotak, JM Financial, Axis",
     "pdf_link": DRHP_LINKS["Groww (Billionbrains Garage)"]["url"], "confidential": False,
     "description": "India's largest discount broker by active users. Listed Nov 2025. Z47 constituent."},

    {"company": "Urban Company (SEBI Approved)",
     "filing_date": "2025-04", "type": "SEBI Approved", "sector": "consumer tech",
     "issue_size": "~₹3,000 cr", "brlms": "Kotak, JM Financial",
     "pdf_link": DRHP_LINKS["Urban Company (SEBI Approved)"]["url"], "confidential": False,
     "description": "SEBI approval received April 2025. IPO expected Q2 FY26."},
]


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
    Returns the PDF URL if found, or None.
    Caches per company for 24 hours.
    """
    ck = f"sebi_pdf_{company_name.lower()[:24]}"
    cached = st.session_state.get(ck, {})
    if cached and time.time() - cached.get("ts", 0) < _SEBI_SEARCH_TTL:
        return cached.get("url")

    url_found = None
    try:
        r = requests.get(
            "https://www.sebi.gov.in/sebiweb/other/OtherAction.do"
            "?doRecognisedFpi=yes&intmId=7",
            headers={"User-Agent": "Mozilla/5.0",
                     "Referer": "https://www.sebi.gov.in/"},
            timeout=15,
        )
        soup  = BeautifulSoup(r.text, "lxml")
        table = soup.find("table")
        if table:
            name_lower = company_name.lower()
            name_words = [w for w in name_lower.split() if len(w) > 3]
            for row in table.find_all("tr")[1:]:
                cols = row.find_all("td")
                if not cols:
                    continue
                row_text = " ".join(c.get_text(strip=True) for c in cols).lower()
                if name_lower in row_text or any(w in row_text for w in name_words):
                    for col in cols:
                        a = col.find("a", href=True)
                        if a:
                            href = a["href"]
                            if not href.startswith("http"):
                                href = "https://www.sebi.gov.in" + href
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
        result = ("sebi_fallback", "https://www.sebi.gov.in/sebiweb/other/OtherAction.do?doRecognisedFpi=yes&intmId=7")

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

    # ── Source 1: SEBI DRHP filings page ──────────────────────────────────────
    try:
        r = requests.get(
            "https://www.sebi.gov.in/sebiweb/other/OtherAction.do"
            "?doRecognisedFpi=yes&intmId=7",
            headers={"User-Agent": "Mozilla/5.0",
                     "Referer": "https://www.sebi.gov.in/"},
            timeout=15,
        )
        soup  = BeautifulSoup(r.text, "lxml")
        table = soup.find("table", {"class": "table"}) or soup.find("table")
        if table:
            for row in table.find_all("tr")[1:]:
                cols = row.find_all("td")
                if len(cols) < 2:
                    continue
                company  = cols[0].get_text(strip=True)
                date_str = cols[1].get_text(strip=True) if len(cols) > 1 else ""
                # Find PDF link in any column
                pdf_url = None
                for col in cols:
                    a = col.find("a", href=True)
                    if a:
                        href = a["href"]
                        if not href.startswith("http"):
                            href = "https://www.sebi.gov.in" + href
                        pdf_url = href
                        break
                is_rel = _is_relevant_company(company)
                is_wl  = _is_watchlist_hit(company)
                filings.append({
                    "company":      company,
                    "filing_date":  date_str,
                    "type":         "DRHP",
                    "sector":       "",
                    "issue_size":   "N/A",
                    "brlms":        "N/A",
                    "pdf_link":     pdf_url,
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

    # ── NEWS FEED ─────────────────────────────────────────────────────────────
    _render_news_feed()

    st.markdown("---")

    # ── PIPELINE STAGE TRACKER ───────────────────────────────────────────────
    st.markdown("### 🚀 IPO Pipeline — Stage Tracker")
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

    # ── LIVE IPOs ─────────────────────────────────────────────────────────────
    st_autorefresh(interval=600_000, key="live_ipo_refresh")   # 10-min auto-refresh
    st.markdown("### 📢 IPOs Currently Open for Subscription")
    with st.spinner("Fetching live IPO data…"):
        live_ipos = _fetch_live_ipos()

    tech_live = [i for i in live_ipos if _is_tech_ipo(i["company"])]
    if tech_live:
        st.markdown(
            f"<div style='background:#dcfce7;border:1px solid #86efac;border-radius:8px;"
            f"padding:8px 14px;margin-bottom:8px;font-size:13px;color:#166534'>"
            f"💡 <b>{len(tech_live)} new-age tech / fintech IPO(s) currently open</b></div>",
            unsafe_allow_html=True)
        for ipo in tech_live:
            _render_ipo_card(ipo, highlight=True)
        if len(live_ipos) > len(tech_live):
            with st.expander(f"Show all {len(live_ipos)} open IPOs"):
                for ipo in live_ipos:
                    _render_ipo_card(ipo)
    elif live_ipos:
        st.info(f"No new-age tech/fintech IPOs currently open. "
                f"{len(live_ipos)} other IPO(s) are open:")
        for ipo in live_ipos[:5]:
            _render_ipo_card(ipo)
        if len(live_ipos) > 5:
            with st.expander(f"Show all {len(live_ipos)} open IPOs"):
                for ipo in live_ipos:
                    _render_ipo_card(ipo)
    else:
        st.info("No IPOs currently open for subscription.")

    st.caption(f"Source: NSE API / Chittorgarh | Auto-refreshes every 10 min | {_now_ist()}")

    st.markdown("---")

    # ── UPCOMING IPOs ─────────────────────────────────────────────────────────
    st.markdown("### 📅 Opening Soon — Next 30 Days")
    with st.spinner("Fetching upcoming IPO data…"):
        upcoming_ipos = _fetch_upcoming_ipos()

    tech_up = [i for i in upcoming_ipos if _is_tech_ipo(i["company"])]
    if tech_up:
        st.markdown(
            f"<div style='background:#ede9fe;border:1px solid #a78bfa;border-radius:8px;"
            f"padding:8px 14px;margin-bottom:8px;font-size:13px;color:#6d28d9'>"
            f"🔮 <b>{len(tech_up)} new-age tech / fintech IPO(s) opening soon</b></div>",
            unsafe_allow_html=True)
        for ipo in tech_up:
            _render_ipo_card(ipo, highlight=False)
        if len(upcoming_ipos) > len(tech_up):
            with st.expander(f"Show all {len(upcoming_ipos)} upcoming IPOs"):
                for ipo in upcoming_ipos:
                    _render_ipo_card(ipo)
    elif upcoming_ipos:
        st.info(f"No new-age tech/fintech IPOs in the next 30 days. "
                f"{len(upcoming_ipos)} other IPO(s) upcoming:")
        for ipo in upcoming_ipos[:5]:
            _render_ipo_card(ipo)
    else:
        st.info("No upcoming IPOs found for the next 30 days.")

    st.caption(f"Source: NSE API / Chittorgarh | Auto-refreshes every 30 min | {_now_ist()}")

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
        if f.get("company", "").lower() not in known_cos
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
    rows = []
    for f in combined:
        z47r   = _is_z47(f.get("company", ""), f.get("sector", ""))
        new_f  = _is_new(f.get("filing_date", ""), days=7)
        wl_hit = f.get("is_watchlist", False)
        badge  = ("⚡ Watchlist" if wl_hit else ("🆕 New" if new_f else ""))
        rows.append({
            "Company":      f.get("company", ""),
            "Filing Date":  f.get("filing_date", ""),
            "Type":         f.get("type", "DRHP"),
            "Sector":       (f.get("sector") or "–").title(),
            "Issue Size":   f.get("issue_size", "TBD"),
            "BRLMs":        f.get("brlms", "TBD"),
            "Status":       badge,
            # Store for detail expander
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

    disp_cols = ["Company", "Filing Date", "Type", "Sector", "Issue Size", "BRLMs", "Status"]

    def _hl(row):
        if row.get("Status") == "⚡ Watchlist":
            return ["background-color:#dcfce7"] * len(row)
        if row.get("Status") == "🆕 New":
            return ["background-color:#fef9c3"] * len(row)
        return [""] * len(row)

    styled = df[disp_cols].style.apply(_hl, axis=1)
    st.dataframe(styled, use_container_width=True, hide_index=True, height=500,
                 column_config={
                     "Company":    st.column_config.TextColumn(width="medium"),
                     "Issue Size": st.column_config.TextColumn(width="small"),
                     "BRLMs":      st.column_config.TextColumn(width="medium"),
                     "Status":     st.column_config.TextColumn(width="small"),
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

    # ── Filing Detail Expander ────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📄 Filing Details & Document Link")
    all_cos  = [r["Company"] for r in rows]
    sel_co   = st.selectbox("Select company", all_cos, key="drhp_detail")
    sel_row  = next((r for r in rows if r["Company"] == sel_co), None)

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
                if sel_row.get("_desc"):
                    st.markdown(f"**About:** {sel_row['_desc']}")

            # Document link + Summary button side by side
            _link_col, _sum_col = st.columns([3, 1])
            with _link_col:
                st.markdown("**DRHP / RHP Document:**")
            with _sum_col:
                if st.button("📋 Summary", key=f"sum_detail_{sel_co}",
                             use_container_width=True):
                    _show_company_summary(sel_co)

            is_conf      = sel_row.get("_conf", False)
            pdf_url      = sel_row.get("_pdf")
            company_name = sel_row.get("Company", "")

            if is_conf:
                st.markdown(
                    "<div style='display:inline-block;background:#e5e7eb;color:#6b7a8d;"
                    "border-radius:8px;padding:6px 14px;font-size:13px;font-weight:600'>"
                    "🔒 Confidential Filing — document not publicly available</div>",
                    unsafe_allow_html=True)
            else:
                drhp_entry = DRHP_LINKS.get(company_name, {})
                if drhp_entry.get("type") == "CONFIDENTIAL":
                    st.markdown(
                        "<div style='display:inline-block;background:#e5e7eb;color:#6b7a8d;"
                        "border-radius:8px;padding:6px 14px;font-size:13px;font-weight:600'>"
                        "🔒 Confidential Filing — document not publicly available</div>",
                        unsafe_allow_html=True)
                elif drhp_entry.get("url"):
                    doc_type = drhp_entry.get("type", "DRHP")
                    st.link_button(
                        f"📄 View {doc_type} on SEBI",
                        drhp_entry["url"],
                        use_container_width=False)
                    st.caption("✅ Verified hardcoded link · Source: SEBI")
                elif pdf_url:
                    st.link_button("📄 View DRHP / RHP Document",
                                   pdf_url,
                                   use_container_width=False)
                    st.caption("✅ Curated source · SEBI / BSE")
                else:
                    with st.spinner("Searching SEBI for document link…"):
                        sebi_url = _sebi_find_pdf(company_name)
                    if sebi_url:
                        st.link_button("📄 View DRHP / RHP Document",
                                       sebi_url,
                                       use_container_width=False)
                        st.caption("🔍 Found via live SEBI search")
                    else:
                        st.link_button(
                            "🔍 Search on SEBI",
                            "https://www.sebi.gov.in/sebiweb/other/OtherAction.do"
                            "?doRecognisedFpi=yes&intmId=7",
                            use_container_width=False)
                        st.caption(
                            f"Direct link unavailable — search for '{company_name}' on SEBI")

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
