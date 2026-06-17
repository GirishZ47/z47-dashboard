"""
Z47'47 hardcoded reference takeaways and index fundamentals fallback.

These are the gold-standard content for the two most visible takeaway slots.
Update manually each Monday when the 30-day rolling window advances.
"""

# ── Z47'47 Monthly Takeaway ───────────────────────────────────────────────────
# "sections" field: new structured format for Z47fortyseven tab renderer.
# "text" field: flat bullet fallback for Z47'47 tab backward compat.
# Both fields must be kept in sync when content is updated.
HARDCODED_INDEX_TAKEAWAY = {
    "header":           "Z47 47 MONTHLY TAKEAWAY · 4 MAY –3 JUN 2026",
    "icon":             "✨",
    "window":           "4 May –3 Jun 2026",
    "date_range_label": "4 MAY – 3 JUN 2026",
    "section_label":    "MONTHLY TAKEAWAY",
    "updated":          "3 Jun 2026",
    # ── Flat bullet text (Z47’ tab backward compat) ───────────────────────
    "text": (
        "• Index performance ; Z47^<em style='font-style:italic;text-transform:none'>fortyseven</em> held while benchmarks slid. "
        "Z47^<em style='font-style:italic;text-transform:none'>fortyseven</em> traded broadly flat; Nifty fell ~2.6%, Sensex ~3.5% on FII outflows "
        "and post-RBI growth-cut pressure. The cohort’s underweight to oil, metals, and "
        "goods-export sectors is structural.\n"
        "• Market context ; the cohort proved it can absorb large institutional exits without dislocation. "
        "The supply rotation from foreign VC exits to domestic MF demand is the structural story consensus is underweighting. "
        "Q4 FY26 prints split the cohort; profitable names traded up, loss-makers de-rated regardless of revenue ; "
        "profitability is now being rewarded over scale.\n"
        "• Macro ; global pressures stack but the hits are asymmetric and partially offset. "
        "Rising oil prices hit the cohort on both demand and cost sides. "
        "The structural offset is real and cohort-wide; India’s digital adoption compounds faster than nominal GDP.\n"
        "• Top gainers ; E2E Networks (+25.7%) on domestic AI infrastructure conviction. "
        "RateGain (+28.1%) on travel-tech SaaS resilience repriced as global travel volumes hold.\n"
        "• Top laggards ; Pine Labs (–27.0%) on permanent take-rate reset pricing. "
        "Urban Company (–20.8%) on contribution-margin thesis under test from delivery-cost inflation.\n"
        "• Net Read ; the index is structurally absorbing supply; the test ahead is earnings. "
        "Q1 FY27 results, starting in July, will be the key catalyst."
    ),
    # ── Structured sections (Z47fortyseven tab new renderer) ──────────────────
    "sections": [
        {
            "type": "main_bullet",
            "header": "Index performance ; Z47^<em style=’font-style:italic;text-transform:none’>fortyseven</em> held while benchmarks slid.",
            "sub_bullets": [
                "Z47^<em style=’font-style:italic;text-transform:none’>fortyseven</em> traded broadly flat; Nifty fell ~2.6%, Sensex ∼3.5% on FII outflows and post-RBI growth-cut pressure.",
                "The cohort’s underweight to oil, metals, and goods-export sectors is structural; Z47^<em style=’font-style:italic;text-transform:none’>fortyseven</em> is built around domestic compounders that hold up precisely when global cyclical sectors don’t.",
            ],
        },
        {
            "type": "main_bullet",
            "header": "Market context ; the cohort proved it can absorb large institutional exits without dislocation.",
            "sub_bullets": [
                "Large share-block sales across multiple cohort names cleared without price disruption in a tight window",
                "The supply rotation from foreign VC exits to domestic MF demand is the structural story consensus is underweighting.",
                "The price action through these prints tells you institutional demand for new-age India is no longer flow-driven; it’s becoming structural ownership.",
                "Q4 FY26 prints split the cohort; profitable names traded up, loss-makers de-rated regardless of revenue ; profitability is now being rewarded over scale.",
            ],
        },
        {
            "type": "main_bullet",
            "header": "Macro ; global pressures stack but the hits are asymmetric and partially offset.",
            "sub_bullets": [
                "Rising oil prices hit the cohort on both demand and cost sides; discretionary spend compresses and margins get squeezed.",
                "Cost pressure stacks from two sides; rupee weakening inflates dollar-linked input costs, while expected rate cuts off the table remove the funding-cost tailwind.",
                "Sub-normal monsoon and El Niño risk threaten rural consumption growth ; the under-discussed downside variable the market isn’t yet pricing.",
                "The structural offset is real and cohort-wide; India’s digital adoption compounds faster than nominal GDP and tailwinds every sub-cohort regardless of cyclical macro.",
                "The proof points are visible across UPI volumes, e-commerce penetration, digital transacting consumers, and credit penetration ; each compounding well above headline growth.",
            ],
        },
        {
            "type": "main_bullet",
            "header": "Top gainers",
            "sub_bullets": [
                "**E2E Networks (+25.7%)** ; increasing investor conviction around domestic AI infrastructure spending, as enterprises and model builders accelerate investments in compute capacity.",
                "**RateGain (+28.1%)** ; recurring-revenue resilience in travel-tech SaaS being repriced as global travel volumes hold despite macro slowdown, with the market underweighting the cohort’s revenue durability.",
            ],
        },
        {
            "type": "main_bullet",
            "header": "Top laggards",
            "sub_bullets": [
                "**Pine Labs (–27.0%)** ; the market is pricing in a permanent take-rate reset, whereas the current pressure appears driven by near-term merchant churn; stabilisation in merchant additions could drive a sharp re-rating.",
                "**Urban Company (–20.8%)** ; the contribution-margin thesis is facing a real test as delivery-cost inflation pressures unit economics; further downside is likely if upcoming results fail to demonstrate margin resilience.",
            ],
        },
        {
            "type": "section_title",
            "header": "Net Read",
            "sub_bullets": [
                "The index is structurally absorbing supply; the test ahead is earnings.",
                "Q1 FY27 results, starting in July, will be the key catalyst; the divergence between fundamentally-driven names and narrative-led names is likely to widen.",
            ],
        },
    ],
}

# ── Monthly Takeaway generation constants ────────────────────────────────────
# Used by _gen_monthly_takeaway() in page_z47fortyseven.py.
# Add a ticker key for every company that could appear in sections 2/3/4;
# missing tickers fall back to "[Update why for {name}]" at generation time.
MONTHLY_TAKEAWAY_WHY = {
    "ETERNAL":    "quick-commerce leadership and continued investment.",
    "GROWW":      "broking market-share gains and margin-funding growth.",
    "LENSKART":   "store densification and margin expansion.",
    "CARTRADE":   "auto-marketplace dominance and a cash-rich balance sheet.",
    "OLAELEC":    "Gen-3 platform rollout and in-house cell manufacturing progress.",
    "WAKEFIT":    "input-cost trends and post-lock-in share supply.",
    "MAPMYINDIA": "muted revenue growth and slower government project execution.",
    "RATEGAIN":   "Sojern integration and margin recovery.",
    "MEESHO":     "post-lock-in share supply and underlying profitability trajectory.",
    "ANGELONE":   "digital broking scale and client-acquisition momentum.",
    "AFFLE":      "mobile adtech scale and acquisition-led expansion.",
    "AMAGI":      "cloud broadcast platform and global media wins.",
    "FRACTAL":    "enterprise AI demand and large-client expansion.",
}

# Section 5 — Key themes; verbatim bullets (update each monthly refresh)
MONTHLY_TAKEAWAY_THEMES = [
    ("In Q4FY26, Z47^<em style='font-style:italic;text-transform:none'>fortyseven</em>'s cohort "
     "grew top line ~39% YoY, more than 3x the broad market's ~12% growth."),
    ("Operating leverage lifted net margins by around 5 percentage points into positive territory, "
     "even as broad-market net margins remained roughly flat."),
    ("With 40 of 47 companies now profitable, the cohort reflects a broader shift toward "
     "profitable growth over growth at any cost."),
    ("AI adoption runs deeper across this cohort than in the broader market, with companies "
     "using it to drive growth and reshape demand, not just improve efficiency."),
    ("Cash generation is increasingly defining the winners, enabling market leaders to fund "
     "acquisitions and expansion from their own balance sheets."),
]

# Section 6 — hardcoded macro bullets (bullets 1-2); bullets 3-4 are auto-placeholders
MONTHLY_TAKEAWAY_MACRO = [
    ("The cohort saw several large block deals this month, including sizeable "
     "stake sales in Lenskart and PB Fintech. Ownership continues "
     "to shift from foreign investors to domestic institutions, creating a more "
     "durable shareholder base."),
    ("Global headwinds (oil, a softer rupee, rate-cut delay, monsoon risk) persist, but "
     "continued digital penetration across India remains a meaningful offset for much of the "
     "cohort."),
]

# Net Read — 2 hardcoded bullets (update each monthly refresh)
MONTHLY_TAKEAWAY_NET_READ = [
    ("Fundamentals continued to strengthen across the cohort, with growth, margins, and cash "
     "generation improving in tandem."),
    ("Performance dispersion widened, with profitability and earnings quality increasingly "
     "distinguishing the strongest performers from the rest."),
]

# ── Z47'47 Valuation Perspective ─────────────────────────────────────────────
HARDCODED_VALUATION_TAKEAWAY = {
    "header":  "Z47 47 VALUATION PERSPECTIVE · 4 MAY TO 3 JUN 2026",
    "icon":    "\U0001f4ca",
    "window":  "4 May to 3 Jun 2026",
    "updated": "3 Jun 2026",
    "text": (
        "• Z47'47's ~36.8x trailing P/E vs the Nifty's ~20.5x looks stretched on the surface; "
        "the premium has mechanically widened this month not because Z47'47 re-rated up, "
        "but because the Nifty de-rated as earnings revisions turned negative.\n"
        "• The case for the premium is half-real: Z47'47's revenue growth runs at 24% YoY vs the Nifty's 12%, "
        "and the fintech sub-cohort earns its marks against actual cash flows — Paytm profitable, "
        "NBFC credit at 14.2% YoY, UPI volumes +25% YoY. That's a real premium, not a TAM premium.\n"
        "• The case against is concentrated in consumer tech: Swiggy and MobiKwik carry meaningful EBITDA losses "
        "that make the index-level 36.8x P/E an average obscuring a wide distribution — the profitable half subsidises the multiple for the still-unprofitable half.\n"
        "• The non-obvious line: fintech/NBFC is becoming a cash-flow story while consumer tech is still a TAM story. "
        "The index headline P/E conceals a 2x multiple dispersion between these two internal sub-cohorts.\n"
        "• IPO pipeline creates a comparable-check risk: Flipkart and Zepto at ₹47,000+ Cr will force the market to price "
        "similar assets at primary clearing levels, potentially compressing secondary multiples on listed comparables.\n"
        "• What to watch: Swiggy and Instamart contribution margin in Q1 FY27 — if quick-commerce burn persists, "
        "consumer-tech multiples face incremental pressure while the fintech sub-cohort stays anchored on earnings."
    ),
}

# ── Hardcoded Sector Takeaways ────────────────────────────────────────────────
# Render instantly on first load — no API call at render time.
# Update manually each Monday alongside the index takeaways.
HARDCODED_SECTOR_TAKEAWAYS = {
    "Consumer / Consumer Tech": {
        "header": "CONSUMER / CONSUMER TECH — MONTHLY TAKEAWAY · 4 MAY TO 3 JUN 2026",
        "icon": "\U0001f4ca",
        "window": "4 May to 3 Jun 2026",
        "updated": "3 Jun 2026",
        "text": (
            "• Consumer/Consumer Tech's ~3% average decline masks the real story — Meesho +18.5% and Swiggy among the laggards "
            "confirms the cohort is fragmenting on unit economics, not softening on demand.\n"
            "• Meesho's Q4 FY26 — revenue +47% YoY to ₹3,531 Cr, GMV +38% to ₹18,941 Cr, losses narrowed 88% to ₹166 Cr, "
            "264M annual transacting users — confirms value-commerce at Tier 2/3 is a structural compounder, not a cycle story.\n"
            "• Swiggy's drag isn't food delivery, which posted its strongest adj. EBITDA margin in 15 quarters. "
            "The problem is Instamart: sequential GOV declined for the first time on record while Blinkit added 216 dark stores in the same window.\n"
            "• Eternal killed Zomato Quick on unit-economics grounds and rebranded — the multi-vertical pivot (food, grocery, going-out) "
            "is a deliberate platform repositioning. Blinkit's ~44-46% quick-commerce market share is structural.\n"
            "• Ather at 27,024 units (+103% YoY in April 2026) vs Ola at 12,166 units (−39% YoY) settles the EV two-wheeler debate: "
            "brand trust and service infrastructure beat first-mover advantage, and Ather is demonstrating both.\n"
            "• What to watch: Instamart contribution margin in Q1 FY27 — sequential improvement without volume recovery "
            "would force the market to recut its entire quick-commerce valuation framework."
        ),
    },
    "Fintech / Financial Services": {
        "header": "FINTECH / FINANCIAL SERVICES — MONTHLY TAKEAWAY · 4 MAY TO 3 JUN 2026",
        "icon": "\U0001f4ca",
        "window": "4 May to 3 Jun 2026",
        "updated": "3 Jun 2026",
        "text": (
            "• Fintech is crossing from 'promise' to 'delivery' — Paytm's FY26 PAT of ₹552 Cr and Kissht's IPO at 24.87x QIB "
            "subscription confirm the market now prices digital finance on real earnings, not narrative.\n"
            "• Paytm's consumer UPI GTV grew at 2.2x the industry rate; financial services revenue +52% YoY in FY26. "
            "GMV remains below pre-RBI-action levels — the profitability is real, the volume rebuild is incomplete.\n"
            "• Antfin's ₹572.9 Cr Paytm disposal into its fourth consecutive profit quarter is supply-into-strength: "
            "SBI MF absorbed 3.4M shares at the ₹842.50 clearing price, replacing a constrained foreign holder with an unconstrained domestic institution.\n"
            "• Kissht's listing at ~17.8% premium to its ₹171 issue price with QIBs at 24.87x repriced digital-NBFC as a category: "
            "the market valued an unsecured-lending book at a premium — a structural shift in how institutions read digital-credit quality.\n"
            "• Groww's May 12 lock-in block — Peak XV, Ribbit, YC Holdings at 29x–52x returns — was a VC lifecycle completion. "
            "Groww's 27% demat market share and #1 active-user count on NSE are unchanged; the supply cleared mechanically.\n"
            "• What to watch: Paytm's payment-processing margin vs the 4 bps threshold as UPI monetisation policy evolves — "
            "and whether Groww's non-broking revenue crosses 20% of total, which would change the quality-of-earnings story."
        ),
    },
    "SaaS / AI": {
        "header": "SAAS / AI — MONTHLY TAKEAWAY · 4 MAY TO 3 JUN 2026",
        "icon": "\U0001f4ca",
        "window": "4 May to 3 Jun 2026",
        "updated": "3 Jun 2026",
        "text": (
            "• SaaS/AI is two businesses inside one sector label: Freshworks compounds USD enterprise revenue "
            "while E2E Networks burns GPU capex that will either deliver operating leverage or widen the gap between revenue and cash conversion.\n"
            "• Freshworks' Q1 2026 — revenue $228.6M (+16% YoY, $5.3M ahead of consensus), EX-ARR $540M (+27% YoY), "
            "first $1M+ ARR deal — signals an enterprise re-rating; NDR at 106% with growing mid-market traction shifts the mix away from SMB dependence.\n"
            "• E2E Networks' 186% YoY revenue growth to ₹956M in Q4 FY26 on 80% GPU utilisation is the headline; "
            "FY26 PAT of -₹156M as it deploys ₹1,185 Cr across ~5,050 GPUs is the question — utilisation holding above 80% is the thesis test.\n"
            "• MapMyIndia's ₹110 Cr IOCL contract and Survey of India national geo-spatial mandate aren't one-offs — "
            "they mark a government procurement cycle compounding onto OEM revenue, making the mapping moat structural rather than platform-contingent.\n"
            "• RateGain's Sojern acquisition (closed Nov 2025) targets 55-60% guided revenue growth, "
            "but organic ARR at 6-8% growth is the quality-of-earnings tell — the inorganic headline is obscuring whether the native business is actually accelerating.\n"
            "• What to watch: E2E Networks' GPU utilisation through mid-FY27 — above 80% and depreciation drag flips to operating leverage; "
            "below 75% and the revenue-to-cash gap widens into a valuation problem."
        ),
    },
    "B2B": {
        "header": "B2B — MONTHLY TAKEAWAY · 4 MAY TO 3 JUN 2026",
        "icon": "\U0001f4ca",
        "window": "4 May to 3 Jun 2026",
        "updated": "3 Jun 2026",
        "text": (
            "• B2B is delivering on the infrastructure-compounding thesis but top-line-to-bottom-line conversion is lagging: "
            "Delhivery crossed ₹10,000 Cr in FY26 revenue and doubled EBITDA to ₹764 Cr, yet Q4 PAT of ₹73.4 Cr was flat sequentially.\n"
            "• Shadowfax is the cohort's hidden story: FY26 revenue ₹4,202 Cr (+69% YoY), Q4 profit ₹56 Cr vs -₹9.9 Cr a year ago — "
            "growing faster than Delhivery in percentage terms by riding the quick-commerce last-mile wave that Delhivery's B2B-heavy mix underweights.\n"
            "• BlackBuck's SaaS-on-logistics model — FY26 revenue ₹652 Cr (+53% YoY), profit ₹160 Cr — is the earnings-quality outlier: "
            "trucking-platform take-rates are more recurring than shipment-per-unit economics, a distinction the index P/E hasn't yet priced.\n"
            "• TBO Tek's Hotels+ mix shift toward higher-margin inventory is accruing to platform economics: "
            "gross-profit-per-transaction is improving as the segment grows — B2B travel-tech monetisation flows to intermediaries, not airlines or OTAs.\n"
            "• Shadowfax's quick-commerce dependency is simultaneously its growth driver and its concentration risk — "
            "if Blinkit and Instamart consolidate dark-store footprints, last-mile volume narrows around two dominant counterparties.\n"
            "• What to watch: Delhivery's revenue-per-shipment trajectory as volumes scale — stabilisation signals operating leverage "
            "into FY27 PAT; further compression stalls the EBITDA re-rating."
        ),
    },
}

# ── Hardcoded Top-3 Deal Takeaways ────────────────────────────────────────────
# Key format: "SYMBOL|YYYY-MM-DD"
# Render instantly on block deals page — no API call at render time.
# Update manually when new top-3 deals enter the trailing 30-day window.
HARDCODED_DEAL_TAKEAWAYS = {
    "POLICYBZR|2026-04-30": {
        "header": "Z47's TAKEAWAY — PB FINTECH (POLICYBAZAAR) BLOCK · 30 APR 2026",
        "icon": "\U0001f4a1",
        "text": (
            "• Tiger Global's PB Fintech disposal signals disciplined portfolio harvest, not distress: "
            "each Tiger tranche has cleared at progressively higher prices, validating the re-rating as structural rather than speculative.\n"
            "• Tiger sold 4.1M shares at ₹1,642/share for ₹673.2 Cr on April 30 — part of a systematic India exit programme "
            "exceeding $2 billion over 18 months from a position entered below ₹400. The exit is at a return that justifies the cadence.\n"
            "• Quant MF absorbed 2.05M shares (₹336.6 Cr) at the same ₹1,642 clearing price — "
            "domestic institutional demand absorbing VC supply at market price without a discount is the structural signal, not the headline exit.\n"
            "• The overhang that capped PB Fintech's institutional positioning for two years is clearing: "
            "as Tiger's residual position shrinks, free-float quality improves as liquidating foreign capital is replaced by domestic conviction.\n"
            "• Read-across to other Z47 names with Tiger exposure: Tiger's India cadence is price-sensitive and structured, not distressed — "
            "it reduces the tail risk of a disorderly supply event across the index.\n"
            "• What to watch: Tiger's remaining India public-market position — if April 30 was a near-complete PB Fintech exit, "
            "the institutional ownership profile re-rates upward as the overhang narrative fades."
        ),
        "value_cr": 673.2,
        "updated": "3 Jun 2026",
    },
    "PAYTM|2026-05-07": {
        "header": "Z47's TAKEAWAY — PAYTM (ONE97 COMMUNICATIONS) BLOCK · 7 MAY 2026",
        "icon": "\U0001f4a1",
        "text": (
            "• Antfin's ₹572.9 Cr Paytm disposal into the company's fourth consecutive profitable quarter is supply-into-strength — "
            "the exit arrived the same day FY26 PAT of ₹552 Cr confirmed Paytm's turn from a loss-era name to a profitable compounder.\n"
            "• Alibaba affiliate Antfin sold 6.8M shares at ₹842.50/share on May 7 — a continued China-portfolio rationalisation "
            "that began in 2025. The price reflects a partial recovery from the 2024 regulatory trough, not a distressed sale.\n"
            "• SBI MF absorbed exactly 50% of the block (3.4M shares at ₹842.50) — a public-sector domestic institution at the clearing price "
            "signals price support and replaces a constrained foreign holder with an unconstrained one.\n"
            "• Paytm's financial services revenue grew 52% YoY in FY26 and consumer UPI GTV ran at 2.2x the industry rate — "
            "yet GMV remains below pre-RBI-action levels, meaning the profitability recovery is cost-led, not yet volume-led.\n"
            "• The Alibaba unwind crosses a symbolic threshold: Chinese strategic capital is now functionally absent from "
            "the listed Indian fintech cap table, which re-rates regulatory risk profiles downward for the cohort.\n"
            "• What to watch: Antfin's remaining Paytm stake — if May 7 was a near-full exit, the overhang narrative collapses; "
            "if a meaningful stake remains, the supply clock runs through FY27."
        ),
        "value_cr": 572.9,
        "updated": "3 Jun 2026",
    },
    "NAZARA|2026-05-15": {
        "header": "Z47's TAKEAWAY — NAZARA TECHNOLOGIES BLOCK · 15 MAY 2026",
        "icon": "\U0001f4a1",
        "text": (
            "• Mitter Infotech's disposal was designed to be read by the buyer list, not the seller size — "
            "routing 9.13M shares each to Zerodha (Nikhil Kamath) and Axana Estates before market open is shareholder stewardship, not opportunistic liquidation.\n"
            "• Founder-CEO Nitish Mittersain reduced his direct stake from 6.09% to 0.90% via 18.26M shares at ₹266/share for ₹485.7 Cr. "
            "Nazara rallied ~18% on the day — the market read the buyer quality, not just the exit size.\n"
            "• Nikhil Kamath's Zerodha accumulating into Nazara — FY26 revenue ₹1,829 Cr (+13% YoY), EBITDA ₹255 Cr (+66% YoY) — "
            "compresses the gaming sector's risk premium: a domestic operator with deep retail reach making a concentrated public-market gaming bet.\n"
            "• The deal reframes Nazara's ownership narrative: from a founder-heavy, gaming-optionality play to one with Kamath as an institutional anchor — "
            "a distinction that changes how retail allocators frame the stock into FY27.\n"
            "• Read-across to the gaming cohort: domestic retail-facing operators accumulating listed gaming exposure signals the TAM discount "
            "applied post-FY24 GST shock is coming off — a cohort re-rating, not just a Nazara-specific event.\n"
            "• What to watch: whether Kamath-linked entities accumulate through open-market purchases post-block — "
            "buying at above-block prices in the secondary market would signal conviction beyond a single negotiated transaction."
        ),
        "value_cr": 485.7,
        "updated": "3 Jun 2026",
    },
}

# ── Hardcoded Recent Results (instant render, no API dependency) ──────────────
# Key = company ticker (matches COMPANIES ticker field).
# Update each quarter after results season. Checked BEFORE any API call.
# NOTE: Recent Results stay in prose format — they are company-specific quarterly
# recaps and benefit from narrative. Do NOT convert to bullets.
HARDCODED_RECENT_RESULTS = {
    "SWIGGY": {
        "header_quarter": "Q4 FY26",
        "updated": "20 May 2026",
        "body": (
            "Swiggy's Q4 FY26 print was a revenue-growth story with a profitability gap still "
            "to close: revenue of ₹61.5B (+54% YoY) confirmed the top-line trajectory, but EBITDA "
            "loss of -₹7.0B and net loss of -₹10.7B show that Instamart dark-store expansion and "
            "the build-out of Snacc are absorbing the contribution-margin gains Swiggy has highlighted "
            "at the segment level. The 54% YoY revenue acceleration outpaces Blinkit's growth in the "
            "same quarter, suggesting market-share recovery in urban core, but at an 11.4% EBITDA loss "
            "margin, Swiggy is burning faster than its IPO-era projections implied. The non-obvious "
            "issue is assortment depth: Swiggy's capital-light dark-store model controls capex but "
            "constrains SKU coverage relative to Blinkit's inventory-dense stores, which limits AOV "
            "expansion and makes the contribution-margin story harder to close quickly. The structural "
            "positive is scale — at ₹61.5B quarterly revenue, incremental margin conversion becomes "
            "the central investment thesis; the only debate is speed. Watch-item: Q1 FY27 EBITDA — "
            "if the loss narrows sequentially despite the seasonally weaker summer quarter, the "
            "profitability inflection narrative gains real traction. Net read: cautious on near-term "
            "FCF, constructive on the revenue trajectory; re-rating requires a credible and sequential "
            "EBITDA direction shift, which Q1 FY27 will either confirm or defer."
        ),
    },
    "ETERNAL": {
        "header_quarter": "Q4 FY26",
        "updated": "20 May 2026",
        "body": (
            "Eternal (formerly Zomato) delivered Q4 FY26 as a continued proof of the India "
            "quick-commerce thesis: Blinkit crossed 1,000 dark stores during the quarter and is "
            "on track for EBITDA breakeven at the segment level by H1 FY27, while Zomato's food "
            "delivery business sustained adjusted EBITDA margins in the mid-single digits. The "
            "rebrand to Eternal is not cosmetic — it signals the board's intent to position the "
            "company as a multi-vertical platform (food, grocery, dining, going-out) rather than "
            "a food-delivery app with a quick-commerce adjacency. The quality-of-earnings story is "
            "improving: GOV growth in food delivery is being driven by higher AOV (premiumisation) "
            "rather than pure order-volume growth, which is a better indicator of structural "
            "demand than discounting-led volume. The risk to re-rating is concentration: Blinkit's "
            "capex programme requires consistent execution across 1,000+ locations, and any "
            "supply-chain or regulatory disruption in the hyperlocal delivery network creates "
            "operational drag at scale. Watch-item: Blinkit EBITDA breakeven timing — a Q1 or "
            "Q2 FY27 breakeven would be a meaningful positive surprise. Net read: constructive "
            "on the multi-vertical platform thesis; the market is appropriately pricing growth "
            "but may be underweighting the operating leverage kicker from Blinkit's scale."
        ),
    },
    "GROWW": {
        "header_quarter": "Q4 FY26",
        "updated": "20 May 2026",
        "body": (
            "Groww (Billionbrains Garage Ventures) reported its first full year as a listed entity "
            "with Q4 FY26 reflecting both the strength of India's retail investor boom and the "
            "structural shift in revenue mix: F&O continues to drive the majority of broking revenue, "
            "but SEBI's circular restricting weekly options expiries (effective Nov 2024) compressed "
            "F&O turnover across discount brokers in Q4. The critical number is active client growth "
            "— Groww crossed 12M+ funded accounts and maintained the #1 position by active user "
            "count on NSE, which is the moat metric the market pays for. The non-obvious risk is "
            "the blended yield per client: as the F&O regulatory headwind persists, revenue per "
            "active client is compressing even as client count grows, creating a scenario where "
            "top-line growth masks yield dilution. The structural positive is AMC: Groww's mutual "
            "fund distribution business is scaling and provides a recurring-fee complement to "
            "transaction-driven broking revenue. Watch-item: the pace of non-broking revenue "
            "(AMC, insurance, lending) as a percentage of total revenue — a meaningful shift above "
            "20% would change the quality-of-earnings narrative. Net read: constructive on the "
            "client franchise, cautious on near-term yield compression from the F&O regulatory "
            "reset; the re-rating catalyst is product-mix diversification."
        ),
    },
    "PAYTM": {
        "header_quarter": "Q4 FY26",
        "updated": "20 May 2026",
        "body": (
            "Paytm's Q4 FY26 was its fourth consecutive profitable quarter — FY26 PAT of ₹552 Cr "
            "marked a definitive exit from the loss era triggered by the RBI action on Paytm "
            "Payments Bank in early 2024. The profitability is real but the composition matters: "
            "the recovery has been driven primarily by a cost rationalisation (headcount down ~30% "
            "since FY24 peak) and a pivot to high-margin financial services (loan distribution, "
            "insurance, devices) rather than a GMV-led top-line re-acceleration. Financial services "
            "revenue grew 52% YoY in FY26, which is the structural tailwind — but the GMV "
            "run-rate remains below pre-RBI-action levels as the merchant base rebuild takes time. "
            "Antfin's continued disposal (most recently ₹572.9 Cr at ₹842.50/share on May 7) is "
            "creating an overhang that will persist until the Chinese investor's position is "
            "substantially reduced or fully exited. Watch-item: GMV trajectory and merchant "
            "re-activation rate — if GMV returns to pre-action levels by Q2 FY27, the financial "
            "services attach rate re-accelerates on a larger base. Net read: cautious-to-neutral; "
            "the profitability milestone is investable, the Antfin overhang is not resolved, and "
            "the market needs GMV confirmation before re-rating to pre-crisis multiples."
        ),
    },
    "POLICYBZR": {
        "header_quarter": "Q4 FY26",
        "updated": "20 May 2026",
        "body": (
            "PB Fintech (PolicyBazaar/PaisaBazaar) sustained its insurance aggregation leadership "
            "in Q4 FY26, with new business margin on the proprietary insurance products (Posp and "
            "PB Partners) continuing to expand as the company shifts from pure comparison to "
            "product manufacturing. The critical shift to track is the PB Plus and term-life own "
            "products — these carry materially higher margins than the aggregation business and "
            "represent the long-term margin re-rating story. The revenue quality is improving: "
            "renewal premiums as a share of total collected premiums is growing, which reduces "
            "the CAC-intensity of revenue and improves LTV/CAC. The risk is regulatory: insurance "
            "distribution norms, digital KYC requirements, and direct-channel competition from "
            "insurers remain overhangs that can compress take-rate without warning. Watch-item: "
            "own-product (PB Plus, term-life) premium as a percentage of total premium — crossing "
            "20% would be a meaningful structural milestone. Net read: constructive on the "
            "product-manufacturing transition thesis; current valuation prices in aggregation "
            "but may not fully reflect the margin uplift from own products at scale."
        ),
    },
}

# ── Hardcoded Index Fundamentals fallback ─────────────────────────────────────
# Used when yfinance returns < 30% coverage on any metric.
# Values as of approximately 19 May 2026 from published market data.
# Update manually alongside the monthly takeaways.
HARDCODED_FUNDAMENTALS = {
    "z47": {
        "index_name": "Z47",
        "n_total": 47, "n_fetched": 47, "n_non_financial": 28,
        "ev_revenue":      8.4,  "n_ev_revenue":      47,
        "ev_rev_proxy":    0,    "n_ev_rev_proxy":     20, "n_ev_rev_std": 27,
        "ev_ebitda":      34.2,  "n_ev_ebitda":        19,
        "pe":             36.8,  "n_pe":               31,
        "pe_source":      "reference (19 May 2026)",
        "pb":              6.2,  "n_pb":               40,
        "rev_growth":     24.1,  "n_rev_growth":       44,
        "ebitda_margin":  11.8,  "n_ebitda_margin":    19,
    },
    "nifty": {
        "index_name": "Nifty 50",
        "n_total": 50, "n_fetched": 50, "n_non_financial": 38,
        "ev_revenue":      4.1,  "n_ev_revenue":      50,
        "ev_rev_proxy":    0,    "n_ev_rev_proxy":      8, "n_ev_rev_std": 42,
        "ev_ebitda":      22.8,  "n_ev_ebitda":        36,
        "pe":             20.5,  "n_pe":               48,
        "pe_source":      "NSE official / reference (19 May 2026)",
        "pb":              3.24, "n_pb":               48,
        "rev_growth":     12.0,  "n_rev_growth":       50,
        "ebitda_margin":  18.4,  "n_ebitda_margin":    36,
    },
    "sensex": {
        "index_name": "BSE Sensex",
        "n_total": 30, "n_fetched": 30, "n_non_financial": 22,
        "ev_revenue":      4.5,  "n_ev_revenue":      30,
        "ev_rev_proxy":    0,    "n_ev_rev_proxy":      5, "n_ev_rev_std": 25,
        "ev_ebitda":      23.5,  "n_ev_ebitda":        22,
        "pe":             21.2,  "n_pe":               28,
        "pe_source":      "reference (19 May 2026)",
        "pb":              3.4,  "n_pb":               28,
        "rev_growth":     11.5,  "n_rev_growth":       30,
        "ebitda_margin":  19.2,  "n_ebitda_margin":    22,
    },
}

# ── Quality-bar few-shot prompt injected into every takeaway generation ───────
# Anchors AI-generated takeaways to the bullet format and analytical voice.
QUALITY_BAR_FEW_SHOT = """\

REFERENCE FORMAT — write in this exact bullet structure. These two examples are the gold standard for voice, format, and analytical depth.

FORMAT RULES:
- 5-7 bullets total. Flat list — no sub-bullets, no nested structure.
- Start every bullet with • (bullet character).
- Opening verdict bullet: one sharp line stating the central call. This is the headline.
- Supporting bullets: each a self-contained insight pulling in a specific company highlight or lowlight with the WHY behind it.
- Final bullet must begin "What to watch:" and name the specific observable to track.
- Each bullet: 1-2 sentences, ~25-40 words. Lead with the conclusion, then the data.

EXAMPLE 1 — Z47'47 MONTHLY TAKEAWAY (bullet format):
• Z47'47 outperformed the Nifty 50 over the trailing 30 days, and the composition earned the insulation: the April 9 tariff drawdown hit goods-export names hard; Z47'47's domestic-revenue cohorts watched from the sideline.
• Paytm's FY26 PAT of ₹552 Cr — a ₹1,215 Cr swing from a ₹663 Cr loss in FY25 — is the cohort's signal data point: the sector's largest name is now profitable, which changes the base case for the fintech sub-cohort as a whole.
• Meesho's +18.5% was the index's single biggest contributor — Q4 FY26 revenue +47% YoY, losses narrowed 88% to ₹166 Cr, 264M annual transacting users. Value-commerce at Tier 2/3 is a compounding base, not a cyclical bounce.
• Groww's ₹5,326 Cr lock-in block on May 12 pressed the stock 5.4% intraday; Peak XV, Ribbit, YC Holdings completed a VC lifecycle exit at 29x–52x returns. Groww's 27% demat market share is unchanged — the supply was mechanical, not fundamental.
• The IPO pipeline is the real variable: 24 DRHPs filed, Flipkart, Zepto, and Zetwerk targeting ₹47,000+ Cr. Where listed multiples clear once primary supply lands is not currently priced at the index level.
• What to watch: the spread between primary IPO clearing multiples and secondary market multiples on comparable listed names — convergence in either direction is where the next index re-rating gets written.

EXAMPLE 2 — SECTOR TAKEAWAY (bullet format):
• Consumer/Consumer Tech's ~3% average decline masks the real story — Meesho +18.5% and Swiggy among the laggards confirms the cohort is fragmenting on unit economics, not softening on demand.
• Meesho's Q4 FY26 — revenue +47% YoY to ₹3,531 Cr, losses narrowed 88% to ₹166 Cr, 264M annual transacting users — confirms value-commerce at Tier 2/3 is a structural compounder, not a cycle story.
• Swiggy's drag isn't food delivery, which posted its strongest adj. EBITDA margin in 15 quarters. The problem is Instamart: sequential GOV declined for the first time on record while Blinkit added 216 dark stores in the same window.
• Ather at 27,024 units (+103% YoY in April 2026) vs Ola at 12,166 units (−39% YoY) settles the EV two-wheeler debate: brand trust and service infrastructure beat first-mover advantage.
• What to watch: Instamart contribution margin in Q1 FY27 — sequential improvement without volume recovery would force the market to recut its quick-commerce valuation framework.

RULES derived from these examples:
1. Open with the verdict. First bullet = analyst's call, not a recap.
2. Every bullet must name a specific company, number, date, or entity — no generic observations.
3. Cause-effect chains must be explicit: "the drag is X because Y" — not just "X was weak."
4. Lead with the conclusion, then the supporting data — not the other way around.
5. At least one bullet must surface the non-obvious: consensus mispricing, footnote nobody flagged, structural shift hiding inside a headline number.
6. End with "What to watch:" naming a specific observable, not a portfolio action.
7. No third-party quotes ("ICICIdirect notes...", "JM Financial says...").
8. No hallucinated data. If you cannot verify a number, omit it entirely. Better directionally right than precisely wrong.
9. No recommendation language: buy, sell, hold, trim, accumulate, avoid, overweight, underweight, target price.
10. Banned phrases: 'strong performance', 'healthy growth', 'robust quarter', 'positive momentum', 'in line with expectations', 'broadly stable', 'well-positioned', 'execution remains key', 'going forward', 'macroeconomic headwinds', 'constructive setup', 'navigating the environment'.

QUALITY SELF-CHECK before finalizing:
- Does every bullet contain a specific company, number, or named entity?
- Does at least one bullet make the reader learn something non-obvious about a specific company?
- Is every claim verifiable from real data?
- Did I hedge anywhere I shouldn't have?
- Is each bullet under 40 words?
- Did I use any banned phrase or recommendation language?
Regenerate any bullet that fails."""

# ── IPO Takeaways — single source of truth for Z47fortyseven + IPOs tabs ──────
# Key: short canonical name (e.g. "KISSHT"). Each entry has:
#   company_key   — full name used in DRHP tab lookup
#   date_range_label, section_label — rendered in both locations
#   sections      — structured list consumed by both tab renderers
#
# VERBATIM CONTENT RULE: every sub-bullet is LOCKED after user sign-off.
# DO NOT rephrase, smooth, or reorder. Add new IPOs as new dict entries.
HARDCODED_IPO_TAKEAWAYS = {
    "KISSHT": {
        "date_range_label": "LISTED MAY 2026",
        "section_label":    "KISSHT IPO TAKEAWAY",
        "company_key":      "Kissht (OnEMI Technology Solutions)",
        "sections": [
            {
                "type": "main_bullet",
                "header": ("A modest listing pop followed by strong post-listing gains reinforced "
                           "the market's preference for asset quality and disciplined underwriting "
                           "over pure loan-book growth."),
                "sub_bullets": [],
            },
            {
                "type": "main_bullet",
                "header": ("The listing helped reset perceptions around unsecured lending, creating "
                           "a constructive valuation anchor for the issuers that follow."),
                "sub_bullets": [],
            },
            {
                "type": "main_bullet",
                "header": ("The buyer mix was a notable positive, with strong participation from "
                           "long-only domestic institutions supporting a more durable post-listing "
                           "ownership base."),
                "sub_bullets": [],
            },
            {
                "type": "main_bullet",
                "header": ("The IPO structure reflected improving market discipline, with "
                           "predominantly primary capital raised to fund growth rather than provide "
                           "liquidity to existing shareholders."),
                "sub_bullets": [],
            },
            {
                "type": "section_title",
                "header": "Net Read",
                "sub_bullets": [
                    ("The listing reinforced the market's growing preference for disciplined "
                     "lenders, expanding the investable universe for digital financial-services "
                     "companies."),
                ],
            },
        ],
    },
}
