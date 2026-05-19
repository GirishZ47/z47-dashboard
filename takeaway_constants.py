"""
Z47'47 hardcoded reference takeaways and index fundamentals fallback.

These are the gold-standard content for the two most visible takeaway slots.
Update manually each Monday when the 30-day rolling window advances.
"""

# ── Z47'47 Monthly Takeaway ───────────────────────────────────────────────────
HARDCODED_INDEX_TAKEAWAY = {
    "header":  "Z47‧47 MONTHLY TAKEAWAY · 19 APR TO 19 MAY 2026",
    "icon":    "✨",
    "window":  "19 Apr to 19 May 2026",
    "updated": "19 May 2026",
    "text": (
        "Z47‧47 outperformed the Nifty 50 over the trailing 30 days, but the win is "
        "mechanical, not earned. The Nifty is down ~2.2% (down ~9.7% YTD), dragged by "
        "goods-export exposure to the April 9 reciprocal tariff regime; Z47‧47’s "
        "fintech and consumer-tech cohorts are domestic-revenue businesses and simply didn’t "
        "share the pain. Consensus is misreading this as resilience — it’s insulation. "
        "The more important point the price action is hiding: most 2026 new-age listings have "
        "debuted flat or at a discount, signalling that public markets have already shifted from "
        "growth narratives to demanding cash-flow visibility and unit economics. The pipeline "
        "behind that shift is enormous — 24 DRHPs filed with SEBI; Flipkart, Zepto, and "
        "Zetwerk alone targeting ₹47,000+ cr. That supply lands into a macro that has "
        "hardened: RBI on hold at 5.25%, FY27 GDP cut to 6.9%, inflation revised up — "
        "long-duration new-age multiples face both a higher discount rate and forced absorption "
        "of fresh paper. Net read: the index is being valued on flow dynamics while the category "
        "is being repriced in real time in the primary market. Either listed multiples derate to "
        "meet incoming IPO clearing levels, or IPO pricing firms up to defend secondary marks "
        "— the spread between primary and secondary is the variable that matters, not the "
        "index level itself."
    ),
}

# ── Z47'47 Valuation Perspective ─────────────────────────────────────────────
HARDCODED_VALUATION_TAKEAWAY = {
    "header":  "Z47‧47 VALUATION PERSPECTIVE · 19 APR TO 19 MAY 2026",
    "icon":    "\U0001f4ca",
    "window":  "19 Apr to 19 May 2026",
    "updated": "19 May 2026",
    "text": (
        "The Nifty 50 trades at ~20.5x trailing P/E and 3.24x P/B — both modestly "
        "below 5-year averages, which means the benchmark itself has de-rated ~50 bps over "
        "the last month as earnings revisions turned negative again. Whatever premium Z47‧47 "
        "carries has mechanically widened, not because the cohort re-rated up but because the "
        "floor moved down. The premium itself is defensible on first principles: Nifty earnings "
        "growth is 12% for FY26 and 15.7% for FY27, while the Z47‧47 cohort sits on top of "
        "TAMs compounding several multiples faster — UPI volumes +25% YoY, India’s "
        "fintech market on a 16.3% CAGR to $109 bn by 2031, formal credit penetration still "
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

EXAMPLE 1 — Z47'47 Monthly Takeaway:
"Z47'47 outperformed the Nifty 50 over the trailing 30 days, but the win is mechanical, not earned. The Nifty is down ~2.2% (down ~9.7% YTD), dragged by goods-export exposure to the April 9 reciprocal tariff regime; Z47'47's fintech and consumer-tech cohorts are domestic-revenue businesses and simply didn't share the pain. Consensus is misreading this as resilience — it's insulation. The more important point the price action is hiding: most 2026 new-age listings have debuted flat or at a discount, signalling that public markets have already shifted from growth narratives to demanding cash-flow visibility and unit economics. The pipeline behind that shift is enormous — 24 DRHPs filed with SEBI; Flipkart, Zepto, and Zetwerk alone targeting ₹47,000+ cr. That supply lands into a macro that has hardened: RBI on hold at 5.25%, FY27 GDP cut to 6.9%, inflation revised up — long-duration new-age multiples face both a higher discount rate and forced absorption of fresh paper. Net read: the index is being valued on flow dynamics while the category is being repriced in real time in the primary market. Either listed multiples derate to meet incoming IPO clearing levels, or IPO pricing firms up to defend secondary marks — the spread between primary and secondary is the variable that matters, not the index level itself."

EXAMPLE 2 — Z47'47 Valuation Perspective:
"The Nifty 50 trades at ~20.5x trailing P/E and 3.24x P/B — both modestly below 5-year averages, which means the benchmark itself has de-rated 50 bps over the last month as earnings revisions turned negative again. Whatever premium Z47'47 carries has mechanically widened, not because the cohort re-rated up but because the floor moved down. The premium itself is defensible on first principles: Nifty earnings growth is 12% for FY26 and 15.7% for FY27, while the Z47'47 cohort sits on top of TAMs compounding several multiples faster — UPI volumes +25% YoY, India's fintech market on a 16.3% CAGR to $109bn by 2031, formal credit penetration still in early innings. You are paying a premium for duration of growth, not just rate of growth, and that's the right reason to pay it. The harder question is where inside the index the premium is earned versus rented: the fintech/NBFC sub-cohort trades rich but on real book value, real NIMs, real credit growth running at 14.2% YoY — that's a premium against cash flows. Net read: the headline premium is intact and structurally justified, but it's being held up by the financial-services half of the cohort doing real work while the consumer-tech half is increasingly relying on TAM narrative to defend its marks — that's the spread to watch, not the aggregate."

RULES derived from these examples:
1. Open with a verdict. First sentence = analyst's call, not a recap.
2. Every claim must be tied to a specific number, date, or named entity.
3. At least 2 insights: variant perception ("consensus is misreading X as Y"), quality-of-earnings, structural vs cyclical, read-through to peers, what the market is missing, earned vs rented premium.
4. End with a Net Read that names a specific spread or variable to watch — not a portfolio action.
5. No third-party quotes ("ICICIdirect notes...", "JM Financial says...").
6. No hallucinated data. If you cannot verify a number, omit it entirely.
7. No recommendation language: buy, sell, hold, trim, accumulate, avoid, overweight, underweight, target price.
8. Banned phrases: 'strong performance', 'healthy growth', 'robust quarter', 'positive momentum', 'in line with expectations', 'broadly stable', 'well-positioned', 'execution remains key'."""
