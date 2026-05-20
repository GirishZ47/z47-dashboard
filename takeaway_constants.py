"""
Z47'47 hardcoded reference takeaways and index fundamentals fallback.

These are the gold-standard content for the two most visible takeaway slots.
Update manually each Monday when the 30-day rolling window advances.
"""

# ── Z47'47 Monthly Takeaway ───────────────────────────────────────────────────
HARDCODED_INDEX_TAKEAWAY = {
    "header":  "Z47 47 MONTHLY TAKEAWAY · 19 APR TO 19 MAY 2026",
    "icon":    "✨",
    "window":  "19 Apr to 19 May 2026",
    "updated": "19 May 2026",
    "text": (
        "Z47 47 outperformed the Nifty 50 over the trailing 30 days, and the relative win "
        "is meaningful — even if part of it is mechanical. The Nifty is down ~2.2% "
        "(down ~9.7% YTD), dragged by goods-export exposure to the April 9 reciprocal tariff "
        "regime; Z47 47’s fintech and consumer-tech cohorts are domestic-revenue businesses, "
        "which insulated them from the worst of the tariff drawdown and is exactly the kind of "
        "structural composition advantage the index was built to capture. The premium is doing "
        "real work: the fintech sub-cohort is anchored on UPI volumes compounding +25% YoY, "
        "NBFC credit growth at 14.2% YoY, and an India fintech market on a 16.3% CAGR to "
        "$109bn by 2031 — these are domestic compounders insulated from global cyclicality in "
        "a way large-cap India simply isn’t. The watch-item is supply, not fundamentals: "
        "24 DRHPs are filed with SEBI and Flipkart, Zepto, and Zetwerk alone are targeting "
        "₹47,000+ cr, which will test where listed multiples clear once fresh paper hits. "
        "Net read: the relative outperformance is earned in part and inherited in part; the "
        "variable to watch is the spread between primary and secondary market multiples as "
        "the IPO pipeline lands."
    ),
}

# ── Z47'47 Valuation Perspective ─────────────────────────────────────────────
HARDCODED_VALUATION_TAKEAWAY = {
    "header":  "Z47 47 VALUATION PERSPECTIVE · 19 APR TO 19 MAY 2026",
    "icon":    "\U0001f4ca",
    "window":  "19 Apr to 19 May 2026",
    "updated": "19 May 2026",
    "text": (
        "The Nifty 50 trades at ~20.5x trailing P/E and 3.24x P/B — both modestly "
        "below 5-year averages, which means the benchmark itself has de-rated ~50 bps over "
        "the last month as earnings revisions turned negative again. Whatever premium Z47 47 "
        "carries has mechanically widened, not because the cohort re-rated up but because the "
        "floor moved down. The premium itself is defensible on first principles: Nifty earnings "
        "growth is 12% for FY26 and 15.7% for FY27, while the Z47 47 cohort sits on top of "
        "TAMs compounding several multiples faster — UPI volumes +25% YoY, India’s "
        "fintech market on a 16.3% CAGR to $109 bn by 2031, formal credit penetration still "
        "in early innings. You are paying a premium for duration of growth, not just rate of "
        "growth, and that’s the right reason to pay it. The harder question is where inside "
        "the index the premium is earned versus rented: the fintech/NBFC sub-cohort trades rich "
        "but on real book value, real NIMs, real credit growth running at 14.2% YoY — "
        "that’s a premium against cash flows. The consumer-tech sub-cohort trades rich on a "
        "different basis, where high multiples are funding contribution-margin trajectories that "
        "haven’t fully landed and where the IPO pipeline (Flipkart, Zepto, Zetwerk — "
        "₹47,000+ cr) will force a comparable check. Net read: the headline premium is "
        "intact and structurally justified, but it’s being held up by the "
        "financial-services half of the cohort doing real work while the consumer-tech half is "
        "increasingly relying on TAM narrative to defend its marks — that’s the spread "
        "to watch, not the aggregate."
    ),
}

# ── Hardcoded Sector Takeaways ────────────────────────────────────────────────
# Render instantly on first load — no API call at render time.
# Update manually each Monday alongside the index takeaways.
HARDCODED_SECTOR_TAKEAWAYS = {
    "Consumer / Consumer Tech": {
        "header": "CONSUMER / CONSUMER TECH — MONTHLY TAKEAWAY · 19 APR TO 19 MAY 2026",
        "icon": "\U0001f4ca",
        "window": "19 Apr to 19 May 2026",
        "updated": "19 May 2026",
        "text": (
            "The sector’s -3.0% average masks a significant bifurcation: Meesho, the period’s standout at +18.5%, "
            "is demonstrating that the value-commerce model is the real structural winner in Indian e-commerce — "
            "Q4 FY26 revenue up 47% YoY to ₹3,531 Cr, GMV up 38% YoY to ₹18,941 Cr, loss narrowed 88% YoY to "
            "₹166 Cr, with 264 million annual transacting users confirming that Tier 2/3 demand is not a cycle, "
            "it is a compounding base. The consensus assumption that quick-commerce is the dominant consumer-tech "
            "value driver needs inverting: Eternal (Zomato) pulled the plug on Zomato Quick citing unit-economics, "
            "while Blinkit’s ~44-46% market share leadership is an earned structural position — but the real alpha "
            "in this cohort came from low-AOV, high-frequency social commerce, not dark stores. Ather Energy "
            "(+103% YoY to 27,024 units in April 2026) is the clearest read on India’s EV transition being a "
            "consumer-tech story as much as an auto story, while Ola Electric’s April volume of 12,166 units — "
            "down ~39% from 19,824 units in April 2025 — signals that brand trust and service infrastructure "
            "matter more than first-mover advantage in EV two-wheelers. Nykaa and Honasa both guided late-20% "
            "revenue growth for Q4, confirming that India’s branded beauty segment is a domestic secular rather "
            "than a discretionary trade, though the upcoming DPDP consent-manager obligations create a non-trivial "
            "compliance cost for every data-intensive D2C and social-commerce platform in the cohort. Net read: "
            "the sector’s composition advantage is intact — domestic revenue, domestic demand drivers — but the "
            "watch-item is whether Meesho can sustain take-rate expansion as its seller base scales, and whether "
            "the Blinkit/Instamart dark-store count race tips into a margin war that pressures Eternal’s "
            "consolidated EBITDA trajectory into FY27."
        ),
    },
    "Fintech / Financial Services": {
        "header": "FINTECH / FINANCIAL SERVICES — MONTHLY TAKEAWAY · 19 APR TO 19 MAY 2026",
        "icon": "\U0001f4ca",
        "window": "19 Apr to 19 May 2026",
        "updated": "19 May 2026",
        "text": (
            "Paytm’s FY26 full-year PAT of ₹552 Cr — a ₹1,215 Cr swing from a ₹663 Cr loss in FY25 — is the "
            "signal that separates this cohort from every prior vintage of Indian fintech: the largest, most "
            "capital-intensive name in the sector is now a profitable compounder, with Q4 FY26 consumer UPI GTV "
            "growing at 2.2x industry rate and financial services revenue up 52% YoY to ₹2,593 Cr for the full year. "
            "The common assumption is that Alibaba’s ₹573 Cr block exit on May 7 is a negative read on Paytm — "
            "the inversion is that it is the last overhang clearing: with Antfin’s partial stake sold at ₹842.50/share "
            "against a backdrop of Paytm posting its fourth consecutive quarterly profit, the supply is exiting into "
            "improving fundamentals, not deteriorating ones, and SBI MF’s absorption of 3.4M shares at the same "
            "price signals domestic institutional conviction at that clearing level. Kissht’s IPO — the first BFSI "
            "listing of FY27 — closed at 9.5x overall subscription with QIBs at 24.87x, listed at ~17.8% premium "
            "to its ₹171 issue price, and is doing real re-rating work for the digital-NBFC pipeline: the market "
            "priced an unsecured-lending book at a premium rather than a discount, which is a structural shift in "
            "how institutions view digital-credit quality. Groww’s ₹5,326 Cr lock-in expiry block on May 12 — "
            "Peak XV, Ribbit, and YC Holdings selling at 29x–52x returns — pressed the stock 5.4% on the day, "
            "but the read-through is not fundamental deterioration: Groww holds 27% demat market share as of "
            "December 2025 and the sellers are VC funds completing a lifecycle, not a strategic reassessment. "
            "Net read: the fintech cohort is transitioning from a ‘promise’ to ‘delivery’ phase; the variable to "
            "track is whether Paytm’s payment-processing margin expansion above 4 bps sustains into FY27 as UPI "
            "monetisation policy evolves, and whether Groww’s revenue-per-active-user improves as SEBI’s F&O "
            "framework normalises."
        ),
    },
    "SaaS / AI": {
        "header": "SAAS / AI — MONTHLY TAKEAWAY · 19 APR TO 19 MAY 2026",
        "icon": "\U0001f4ca",
        "window": "19 Apr to 19 May 2026",
        "updated": "19 May 2026",
        "text": (
            "The SaaS/AI cohort is splitting into two distinct businesses hiding inside one sector label: "
            "Freshworks is a USD-revenue, Nasdaq-listed compounder posting Q1 2026 revenue of $228.6M (+16% YoY, "
            "beat consensus by $5.3M), with EX-ARR at $540M (+27% YoY) and its first $1M+ ARR deal — a genuine "
            "enterprise re-rating — while E2E Networks is a pure India-infrastructure play with Q4 FY26 revenue "
            "up 186% YoY to ₹956M on 80% GPU utilisation, but FY26 PAT negative at -₹156M as the company deploys "
            "₹1,185 Cr across ~5,050 GPUs. The variant perception on Freshworks is that indirect tariff headwinds "
            "— a potential US GDP slowdown compressing discretionary IT budgets — are not priced into the stock, "
            "yet NDR at 106% and enterprise traction in its EX suite suggest Freshworks is shifting from SMB "
            "dependence toward a more defensive mid-market base. MapmyIndia’s ₹110 Cr IOCL contract and Survey "
            "of India’s national geo-spatial platform mandate are not one-off deals — they are evidence of a "
            "government procurement cycle compounding on top of automotive OEM revenue, making MapmyIndia’s "
            "moat more structural than the market credits. RateGain’s Q4 FY26 earnings call will be the cohort’s "
            "defining data point: with the Sojern acquisition closed in November 2025, the combined entity’s "
            "55–60% guided revenue growth includes inorganic contribution, and the quality-of-earnings question "
            "is whether organic ARR growth at 6–8% is being obscured by the acquisition headline. Net read: "
            "E2E Networks’ B200 cluster deployment timeline and capacity utilisation through mid-FY27 is the "
            "single most important watch-item for the cohort — if GPU utilisation holds above 80%, the "
            "depreciation drag reverses into operating leverage; if it slips, the gap between headline revenue "
            "growth and cash conversion widens further."
        ),
    },
    "B2B": {
        "header": "B2B — MONTHLY TAKEAWAY · 19 APR TO 19 MAY 2026",
        "icon": "\U0001f4ca",
        "window": "19 Apr to 19 May 2026",
        "updated": "19 May 2026",
        "text": (
            "Delhivery’s FY26 crossing the ₹10,000 Cr revenue milestone — Q4 revenue ₹2,848 Cr (+30% YoY), "
            "full-year EBITDA ₹764 Cr (2x FY25’s ₹376 Cr), express parcel volumes at 1.054 billion shipments "
            "(+40% YoY) — confirms that the logistics infrastructure buildout thesis is delivering operating "
            "leverage, but Q4 PAT of ₹73.4 Cr is flat sequentially, flagging that the topline-to-bottom-line "
            "conversion is not yet clean. The consensus view that Shadowfax is a second-tier logistics name "
            "deserves challenge: FY26 revenue of ₹4,202 Cr (+69% YoY), Q4 profit of ₹56 Cr (vs. ₹-9.9 Cr in "
            "Q4 FY25), and a Q4 revenue run-rate of ₹1,237 Cr at 74% YoY growth means Shadowfax is growing "
            "faster than Delhivery in absolute percentage terms, powered by the quick-commerce last-mile wave "
            "that Delhivery’s B2B-heavy mix underweights. BlackBuck’s SaaS-on-logistics model — FY26 revenue "
            "₹652 Cr (+53% YoY), FY26 profit ₹160 Cr — is structurally differentiated from pure throughput "
            "logistics: trucking-platform take-rates are more recurring and defensible than shipment-per-unit "
            "economics, which is the quality-of-earnings distinction the market has not fully priced. TBO Tek "
            "remains the cohort’s cleanest compounder on gross-profit-per-transaction terms, with the Hotels+ "
            "segment driving mix shift toward higher-margin inventory; the read-through is that B2B travel-tech "
            "monetisation is accruing to platform intermediaries, not airlines or OTAs. Net read: the watch-item "
            "for Delhivery is whether revenue-per-shipment stabilises as volume scales — if realisations compress "
            "while volumes grow, the EBITDA re-rating stalls; for Shadowfax, the question is whether Q-commerce "
            "dependency is a concentration risk or a defensible moat as Blinkit and Instamart consolidate."
        ),
    },
}

# ── Hardcoded Top-3 Deal Takeaways ────────────────────────────────────────────
# Key format: "SYMBOL|YYYY-MM-DD"
# Render instantly on block deals page — no API call at render time.
# Update manually when new top-3 deals enter the trailing 30-day window.
HARDCODED_DEAL_TAKEAWAYS = {
    "POLICYBZR|2026-04-30": {
        "header": "Z47’s TAKEAWAY — PB FINTECH (POLICYBAZAAR) BLOCK · 30 APR 2026",
        "icon": "\U0001f4a1",
        "text": (
            "Tiger Global sold 4.1M shares of PB Fintech on April 30, 2026, at ₹1,642/share for ₹673.2 Cr — "
            "a systematic portfolio harvest that brings Tiger’s cumulative India exit tally well past $2 billion "
            "across 18 months of structured secondary disposals, closing out what was a 5x return position "
            "entered at sub-₹400 levels. The quality-of-deal signal is in who bought: Quant MF absorbed 2.05M "
            "shares (₹336.6 Cr) at the same price — domestic institutional demand clearing VC supply at market "
            "price with no visible discount is the structural positive, not the headline exit. The common read "
            "is that Tiger’s departure pressures the stock; the inversion is that each Tiger tranche clearing "
            "at progressively higher prices validates the PB Fintech re-rating as structural rather than "
            "speculative, and removes an overhang that has capped institutional positioning for two years. "
            "The read-across for other VC-backed Z47 names with Tiger exposure is that Tiger’s India exit "
            "cadence is disciplined and price-sensitive, not distressed, which reduces the risk of a disorderly "
            "supply event across the index. Net read: the variable to track is Tiger’s residual India "
            "public-market position; if April 30 was a near-complete exit, PB Fintech’s free-float quality "
            "improves materially as domestic institutions replace a liquidating global fund."
        ),
        "value_cr": 673.2,
        "updated": "19 May 2026",
    },
    "PAYTM|2026-05-07": {
        "header": "Z47’s TAKEAWAY — PAYTM (ONE97 COMMUNICATIONS) BLOCK · 7 MAY 2026",
        "icon": "\U0001f4a1",
        "text": (
            "Alibaba affiliate Antfin sold 6.8M shares of One97 Communications on May 7, 2026, at ₹842.50/share "
            "for ₹572.9 Cr — an exit that arrived on the same day Paytm’s stock was absorbing the news of its "
            "fourth consecutive quarterly profit and FY26 PAT of ₹552 Cr, making this a disposal into improving "
            "fundamentals rather than a flight from deterioration. The structural read on Alibaba’s exit "
            "trajectory is that ₹842.50 represents a partial recovery from the regulatory trough of 2024 but "
            "remains a discount to pre-RBI-action highs — Antfin is completing a China-portfolio India "
            "rationalisation that began with earlier tranches in 2025, and the May 7 sale is the continued "
            "execution of that programme, not a new negative signal. SBI MF’s absorption of 3.4M shares — "
            "exactly 50% of the block at the same ₹842.50 price — is the most important data point: a domestic "
            "public-sector institution buying at the clearing price signals price support and replaces a "
            "constrained foreign holder with an unconstrained domestic one. The read-across to other "
            "Chinese-backed Z47 names is directionally cautious: where Chinese strategic investors hold "
            "meaningful stakes acquired at pre-IPO prices, the exit clock is running, and the market should "
            "expect further structured disposals as lock-in and diplomatic considerations resolve. Net read: "
            "Paytm’s overhang narrative is becoming a clean-up story — the watch-item is the pace of Antfin’s "
            "remaining position, and whether Paytm’s financial services revenue trajectory (up 52% YoY in "
            "FY26) is sufficient to re-anchor valuation conversations away from the payments-margin debate."
        ),
        "value_cr": 572.9,
        "updated": "19 May 2026",
    },
    "NAZARA|2026-05-15": {
        "header": "Z47’s TAKEAWAY — NAZARA TECHNOLOGIES BLOCK · 15 MAY 2026",
        "icon": "\U0001f4a1",
        "text": (
            "Mitter Infotech LLP — the vehicle of Nazara founder-CEO Nitish Mittersain — sold 18.26M shares at "
            "₹266/share for ₹485.7 Cr on May 15, reducing the promoter’s direct stake from 6.09% to 0.90%, "
            "in a transaction structurally different from every other Z47 block this period: the seller named "
            "the buyers before the market opened, and those buyers — Zerodha Broking (linked to Nikhil Kamath) "
            "and Axana Estates LLP acquiring 9.13M shares each — are India-anchored, gaming-conviction investors "
            "adding to existing positions, not momentum traders. The common assumption is that a promoter selling "
            "5.2% of the company is a red flag; the inversion is that routing a disposal directly to named "
            "institutional anchors — rather than via a blind book-build — is an act of shareholder stewardship, "
            "not opportunistic liquidation, and the fact that Nazara stock rallied ~18% on the day confirms that "
            "the market read the buyer quality, not just the seller headline. Nikhil Kamath’s Zerodha buying "
            "into Nazara — FY26 revenue ₹1,829 Cr (+13% YoY), EBITDA ₹255 Cr (+66% YoY) — is a meaningful "
            "signal for the India gaming thesis: a domestic operator with deep retail-investor reach is making "
            "a concentrated public-market gaming bet, which compresses the risk-premium the sector has carried "
            "since the GST-on-gaming shock of FY24. Net read: the deal’s quality lies in the buyer roster, "
            "not the headline disposal size — watch whether Nikhil Kamath’s associated entities continue "
            "accumulating through open-market purchases, which would signal conviction beyond a single "
            "negotiated block."
        ),
        "value_cr": 485.7,
        "updated": "19 May 2026",
    },
}

# ── Hardcoded Recent Results (instant render, no API dependency) ──────────────
# Key = company ticker (matches COMPANIES ticker field).
# Update each quarter after results season. Checked BEFORE any API call.
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
QUALITY_BAR_FEW_SHOT = """\

REFERENCE QUALITY BAR — these two takeaways are the gold standard. Match their analytical depth, structure, and voice exactly.

EXAMPLE 1 — Z47’s Monthly Takeaway:
"Z47 47 outperformed the Nifty 50 over the trailing 30 days, and the relative win is meaningful — even if part of it is mechanical. The Nifty is down ~2.2% (down ~9.7% YTD), dragged by goods-export exposure to the April 9 reciprocal tariff regime; Z47 47’s fintech and consumer-tech cohorts are domestic-revenue businesses, which insulated them from the worst of the tariff drawdown and is exactly the kind of structural composition advantage the index was built to capture. The premium is doing real work: the fintech sub-cohort is anchored on UPI volumes compounding +25% YoY, NBFC credit growth at 14.2% YoY, and an India fintech market on a 16.3% CAGR to $109bn by 2031 — these are domestic compounders insulated from global cyclicality in a way large-cap India simply isn’t. The watch-item is supply, not fundamentals: 24 DRHPs are filed with SEBI and Flipkart, Zepto, and Zetwerk alone are targeting ₹47,000+ cr, which will test where listed multiples clear once fresh paper hits. Net read: the relative outperformance is earned in part and inherited in part; the variable to watch is the spread between primary and secondary market multiples as the IPO pipeline lands."

EXAMPLE 2 — Z47’s Valuation Perspective:
"The Nifty 50 trades at ~20.5x trailing P/E and 3.24x P/B — both modestly below 5-year averages, which means the benchmark itself has de-rated 50 bps over the last month as earnings revisions turned negative again. Whatever premium Z47 47 carries has mechanically widened, not because the cohort re-rated up but because the floor moved down. The premium itself is defensible on first principles: Nifty earnings growth is 12% for FY26 and 15.7% for FY27, while the Z47 47 cohort sits on top of TAMs compounding several multiples faster — UPI volumes +25% YoY, India’s fintech market on a 16.3% CAGR to $109bn by 2031, formal credit penetration still in early innings. You are paying a premium for duration of growth, not just rate of growth, and that’s the right reason to pay it. The harder question is where inside the index the premium is earned versus rented: the fintech/NBFC sub-cohort trades rich but on real book value, real NIMs, real credit growth running at 14.2% YoY — that’s a premium against cash flows. Net read: the headline premium is intact and structurally justified, but it’s being held up by the financial-services half of the cohort doing real work while the consumer-tech half is increasingly relying on TAM narrative to defend its marks — that’s the spread to watch, not the aggregate."

RULES derived from these examples:
1. Open with a verdict. First sentence = analyst’s call, not a recap.
2. Every claim must be tied to a specific number, date, or named entity.
3. At least 2 insights: variant perception (“consensus is misreading X as Y”), quality-of-earnings, structural vs cyclical, read-through to peers, what the market is missing, earned vs rented premium.
4. End with a Net Read that names a specific spread or variable to watch — not a portfolio action.
5. No third-party quotes (“ICICIdirect notes...”, “JM Financial says...”).
6. No hallucinated data. If you cannot verify a number, omit it entirely.
7. No recommendation language: buy, sell, hold, trim, accumulate, avoid, overweight, underweight, target price.
8. Banned phrases: ‘strong performance’, ‘healthy growth’, ‘robust quarter’, ‘positive momentum’, ‘in line with expectations’, ‘broadly stable’, ‘well-positioned’, ‘execution remains key’."""
