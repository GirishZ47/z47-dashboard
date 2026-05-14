"""
S&P Capital IQ hardcoded valuation data for 20 recent Indian IPOs.
All figures in ₹ Millions (mn) as per CIQ export.
Display values: divide by 10 to get ₹ Crores (cr).

Keys must match exactly the "company" field in IPOS list in page_recent_ipos.py.
"""


# ── TEV / multiple helpers ─────────────────────────────────────────────────────

def calc_tev_at_price(price: float, ciq: dict) -> tuple[float, float]:
    """
    Return (mcap_mn, tev_mn) at the given share price.
    Only MCap changes — balance sheet (cash, debt, minority, pref) stays fixed.
    TEV = MCap − Cash + Debt + Minority Interest + Preferred Equity
    """
    mcap_mn = price * ciq["shares_mn"]
    tev_mn = (
        mcap_mn
        - ciq["cash_mn"]
        + ciq["debt_mn"]
        + ciq.get("minority_mn", 0)
        + ciq.get("pref_equity_mn", 0)
    )
    return mcap_mn, tev_mn


def calc_multiples(price: float, ciq: dict, fy_data: dict) -> dict:
    """
    Calculate valuation multiples at a given price for one fiscal year.
    Returns dict with keys: mcap_cr, tev_cr, ev_rev, ev_ebitda, pe, mcap_mn, tev_mn
    """
    if not price or price <= 0:
        return {}

    mcap_mn, tev_mn = calc_tev_at_price(price, ciq)
    rev_mn = fy_data.get("revenue_mn") or 0
    ebitda_mn = fy_data.get("ebitda_mn")
    eps = fy_data.get("eps_diluted")
    metric_type = ciq.get("metric_type", "ev_ebitda")

    # EV/Revenue (Group 1 companies)
    ev_rev = round(tev_mn / rev_mn, 1) if rev_mn > 0 else None

    # EV/EBITDA
    if metric_type == "insurance":
        ev_ebitda = "insurance_na"
    elif ebitda_mn is not None and ebitda_mn > 0:
        ev_ebitda = round(tev_mn / ebitda_mn, 1)
    else:
        ev_ebitda = None   # negative or zero EBITDA → N/M

    # P/E (based on EPS, not MCap/PAT — more accurate)
    pe = round(price / eps, 1) if (eps and eps > 0) else None

    return {
        "mcap_mn":  mcap_mn,
        "tev_mn":   tev_mn,
        "mcap_cr":  mcap_mn / 10,
        "tev_cr":   tev_mn / 10,
        "ev_rev":   ev_rev,
        "ev_ebitda": ev_ebitda,
        "pe":       pe,
    }


# ── CIQ dataset ───────────────────────────────────────────────────────────────
# metric_type: "ev_rev" = EV/Revenue (Group 1 — platform/marketplace)
#              "ev_ebitda" = EV/EBITDA (Groups 2 & 3)
#              "insurance" = P/E only (Go Digit)

CIQ_DATA: dict = {

    # ── GROUP 1 — EV/Revenue + P/E ─────────────────────────────────────────

    "Groww": {
        "metric_type": "ev_rev",
        "shares_mn":   6_273.60,
        "cash_mn":     16_000,       # ~₹1,600 cr (asset-light broker, large client funds pool)
        "debt_mn":     2_000,        # ~₹200 cr
        "minority_mn": 0,
        "pref_equity_mn": 0,
        "fiscal_years": ["FY25A", "FY26A", "FY27E"],
        "financials": {
            "FY25A": {
                "revenue_mn":    40_179.48,
                "ebitda_mn":     None,          # not available in CIQ file
                "net_income_mn": 18_243.73,
                "eps_diluted":   3.19,
            },
            "FY26A": {
                "revenue_mn":    47_699.33,
                "ebitda_mn":     None,
                "net_income_mn": 20_830,
                "eps_diluted":   3.40,
            },
            "FY27E": {
                "revenue_mn":    63_579.51,
                "ebitda_mn":     None,
                "net_income_mn": 30_202.68,
                "eps_diluted":   4.91,
                "is_estimate":   True,
            },
        },
        "company_note": "✅ Profitable — FY25 PAT ₹1,824 cr, FY26 PAT ₹2,083 cr. EPS growing steadily. Asset-light brokerage model with large client fund float.",
    },

    "Ather Energy": {
        "metric_type": "ev_rev",
        "shares_mn":   382.67,
        "cash_mn":     13_751.6,
        "debt_mn":     6_642.2,
        "minority_mn": 0,
        "pref_equity_mn": 0,
        "fiscal_years": ["FY25A", "FY26A"],
        "financials": {
            "FY25A": {
                "revenue_mn":    22_550,
                "ebitda_mn":     -7_038,
                "net_income_mn": -8_123,
                "eps_diluted":   -32.24,
                "gross_margin_pct": 16.8,
            },
            "FY26A": {
                "revenue_mn":    36_717.6,
                "ebitda_mn":     -4_083.6,
                "net_income_mn": -5_171.7,
                "eps_diluted":   -13.99,
                "gross_margin_pct": 21.1,
            },
        },
        "company_note": "📉 Loss-making across all years. Gross margin improving: 16.8% (FY25) → 21.1% (FY26). Path to profitability: FY27–28E per analysts.",
    },

    "BlackBuck": {
        "metric_type": "ev_rev",
        "shares_mn":   181.90,
        "cash_mn":     7_657.21,
        "debt_mn":     477.3,
        "minority_mn": 0,
        "pref_equity_mn": 0,
        "fiscal_years": ["FY24A", "FY25A", "FY26E"],
        "financials": {
            "FY24A": {
                "revenue_mn":    2_969.22,
                "ebitda_mn":     -1_595.1,
                "net_income_mn": -1_939.5,
                "eps_diluted":   -9.06,
                "gross_margin_pct": 3.4,
            },
            "FY25A": {
                "revenue_mn":    4_267.28,
                "ebitda_mn":     -3_002.1,
                "net_income_mn": -86.6,
                "eps_diluted":   -2.19,
                "gross_margin_pct": 65.5,
            },
            "FY26E": {
                "revenue_mn":    6_253.02,
                "ebitda_mn":     1_684.41,
                "net_income_mn": 1_434.93,
                "eps_diluted":   7.76,
                "gross_margin_pct": 82.0,
                "is_estimate":   True,
            },
        },
        "company_note": "📈 Turning profitable in FY26E — first EBITDA-positive year. Net income FY25 near breakeven (loss ₹9 cr). Gross margin surge: 3.4% (FY24) → 65.5% (FY25) → 82.0% (FY26E est).",
    },

    "Ola Electric": {
        "metric_type": "ev_rev",
        "shares_mn":   4_410.83,
        "cash_mn":     29_260,
        "debt_mn":     31_210,
        "minority_mn": 0,
        "pref_equity_mn": 0,
        "fiscal_years": ["FY24A", "FY25A", "FY26E"],
        "financials": {
            "FY24A": {
                "revenue_mn":    50_100,
                "ebitda_mn":     -14_250,
                "net_income_mn": -15_840,
                "eps_diluted":   -4.35,
                "gross_margin_pct": 11.6,
            },
            "FY25A": {
                "revenue_mn":    45_140,
                "ebitda_mn":     -20_040,
                "net_income_mn": -22_760,
                "eps_diluted":   -5.48,
                "gross_margin_pct": 16.5,
            },
            "FY26E": {
                "revenue_mn":    23_042.46,
                "ebitda_mn":     -9_160.91,
                "net_income_mn": -17_480.52,
                "eps_diluted":   -3.96,
                "gross_margin_pct": 30.7,
                "is_estimate":   True,
            },
        },
        "company_note": "📉 Revenue declining: ₹5,010 cr (FY24) → ₹4,514 cr (FY25) → ₹2,304 cr (FY26E est). All years loss-making. Gross margin improving despite revenue decline.",
    },

    "Swiggy": {
        "metric_type": "ev_rev",
        "shares_mn":   2_593.88,
        "cash_mn":     73_120,
        "debt_mn":     25_510,
        "minority_mn": 0,
        "pref_equity_mn": 0,
        "fiscal_years": ["FY24A", "FY25A", "FY26A"],
        "financials": {
            "FY24A": {
                "revenue_mn":    112_473.9,
                "ebitda_mn":     -23_873.5,
                "net_income_mn": -23_502.4,
                "eps_diluted":   -10.70,
                "gross_margin_pct": 40.6,
            },
            "FY25A": {
                "revenue_mn":    152_267.55,
                "ebitda_mn":     -30_626.1,
                "net_income_mn": -31_168,
                "eps_diluted":   -13.72,
                "gross_margin_pct": 43.1,
            },
            "FY26A": {
                "revenue_mn":    230_530,
                "ebitda_mn":     -32_310,
                "net_income_mn": -41_540,
                "eps_diluted":   -16.87,
                "gross_margin_pct": 44.5,
            },
        },
        "company_note": "📉 Loss-making. Revenue growing strongly: +35% FY25, +51% FY26. Losses widening despite improving gross margin (40% → 44.5%). EBITDA breakeven expected FY28E per analysts.",
    },

    # ── GROUP 2 — EV/EBITDA + P/E ──────────────────────────────────────────

    "BlueStone": {
        "metric_type": "ev_ebitda",
        "shares_mn":   152.361,
        "cash_mn":     8_568.28,
        "debt_mn":     19_838.95,
        "minority_mn": 23.08,
        "pref_equity_mn": 0,
        "fiscal_years": ["FY25A", "FY26A", "FY27E"],
        "financials": {
            "FY25A": {
                "revenue_mn":    17_700.02,
                "ebitda_mn":     -259.10,
                "net_income_mn": -2_216.70,
                "eps_diluted":   -79.74,
            },
            "FY26A": {
                "revenue_mn":    24_364.24,
                "ebitda_mn":     3_894.93,
                "net_income_mn": 148.37,
                "eps_diluted":   1.05,
            },
            "FY27E": {
                "revenue_mn":    31_682.21,
                "ebitda_mn":     4_136.07,
                "net_income_mn": 48.25,
                "eps_diluted":   0.35,
                "is_estimate":   True,
            },
        },
        "company_note": "✅ FY26: First profitable year (PAT ₹15 cr, EPS ₹1.05). EBITDA turned positive FY26 after FY25 losses. Net debt ₹1,129 cr (debt > cash).",
    },

    "Smartworks": {
        "metric_type": "ev_ebitda",
        "shares_mn":   114.262,
        "cash_mn":     2_355.61,
        "debt_mn":     47_783.50,   # lease obligations (Ind AS 116)
        "minority_mn": 0,
        "pref_equity_mn": 0,
        "fiscal_years": ["FY25A", "FY26A", "FY27E"],
        "financials": {
            "FY25A": {
                "revenue_mn":    13_398.72,
                "ebitda_mn":     3_991.42,   # elevated — Ind AS 116
                "net_income_mn": -617.40,
                "eps_diluted":   -6.04,
                "ind_as_116":    True,
            },
            "FY26A": {
                "revenue_mn":    17_958.05,
                "ebitda_mn":     11_551.21,  # elevated — Ind AS 116
                "net_income_mn": 105.28,
                "eps_diluted":   0.95,
                "ind_as_116":    True,
            },
            "FY27E": {
                "revenue_mn":    23_562.74,
                "ebitda_mn":     15_337.37,  # elevated — Ind AS 116
                "net_income_mn": 923.80,
                "eps_diluted":   8.37,
                "ind_as_116":    True,
                "is_estimate":   True,
            },
        },
        "company_note": "FY26: First profitable year at PAT level (₹11 cr). Co-working space operator with 55 centres.",
        "ind_as_116_warning": "⚠️ EBITDA is significantly elevated by Ind AS 116 lease accounting. Gross lease obligations ~₹47,784 mn sit on balance sheet as debt. Pre-Ind AS 116 EBITDA would be materially lower. The high debt figure represents lease obligations, not financial debt.",
    },

    "MobiKwik": {
        "metric_type": "ev_ebitda",
        "shares_mn":   78.730,
        "cash_mn":     8_931.35,
        "debt_mn":     2_759.55,
        "minority_mn": 0,
        "pref_equity_mn": 0,
        "fiscal_years": ["FY24A", "FY25A", "FY26A"],
        "financials": {
            "FY24A": {
                "revenue_mn":    8_750.03,
                "ebitda_mn":     3_223.76,
                "net_income_mn": 140.79,
                "eps_diluted":   2.38,
            },
            "FY25A": {
                "revenue_mn":    11_701.74,
                "ebitda_mn":     1_089.49,
                "net_income_mn": -1_215.30,
                "eps_diluted":   -19.27,
            },
            "FY26A": {
                "revenue_mn":    11_541.95,
                "ebitda_mn":     1_340.37,
                "net_income_mn": -621.00,
                "eps_diluted":   -7.93,
            },
        },
        "company_note": "⚠️ Only profitable in FY24. Returned to loss FY25–26. Net cash positive ₹617 cr — cushions losses. EBITDA positive across years but PAT remains negative.",
    },

    "Unicommerce": {
        "metric_type": "ev_ebitda",
        "shares_mn":   111.362,
        "cash_mn":     577.89,
        "debt_mn":     94.69,
        "minority_mn": 0,
        "pref_equity_mn": 0,
        "fiscal_years": ["FY24A", "FY25A", "FY26A"],
        "financials": {
            "FY24A": {
                "revenue_mn":    1_035.81,
                "ebitda_mn":     126.11,
                "net_income_mn": 131.17,
                "eps_diluted":   1.17,
            },
            "FY25A": {
                "revenue_mn":    1_347.90,
                "ebitda_mn":     236.60,
                "net_income_mn": 176.81,
                "eps_diluted":   1.58,
            },
            "FY26A": {
                "revenue_mn":    2_043.38,
                "ebitda_mn":     332.58,
                "net_income_mn": 204.58,
                "eps_diluted":   1.78,
            },
        },
        "company_note": "✅ Consistently profitable B2B SaaS since FY22. Asset-light model. Net cash ₹48 cr. Revenue accelerated +51.6% in FY26.",
    },

    "Ixigo": {
        "metric_type": "ev_ebitda",
        "shares_mn":   436.674,
        "cash_mn":     3_566.29,
        "debt_mn":     249.15,
        "minority_mn": 16.22,
        "pref_equity_mn": 0,
        "fiscal_years": ["FY24A", "FY25A", "FY26E"],
        "financials": {
            "FY24A": {
                "revenue_mn":    6_558.73,
                "ebitda_mn":     363.99,
                "net_income_mn": 757.97,
                "eps_diluted":   1.98,
            },
            "FY25A": {
                "revenue_mn":    9_142.46,
                "ebitda_mn":     731.27,
                "net_income_mn": 601.82,
                "eps_diluted":   1.55,
            },
            "FY26E": {
                "revenue_mn":    12_426,
                "ebitda_mn":     775,
                "net_income_mn": 748.75,
                "eps_diluted":   1.80,
                "is_estimate":   True,
            },
        },
        "company_note": "✅ Profitable since FY23. Net cash ₹332 cr. EBITDA margin improving: 5.5% (FY24) → 8.0% (FY25). High multiples reflect travel-tech growth premium.",
    },

    "FirstCry": {
        "metric_type": "ev_ebitda",
        "shares_mn":   522.050,
        "cash_mn":     10_441.92,
        "debt_mn":     16_612.28,
        "minority_mn": 5_096.28,
        "pref_equity_mn": 0,
        "fiscal_years": ["FY24A", "FY25A", "FY26E"],
        "financials": {
            "FY24A": {
                "revenue_mn":    64_808.56,
                "ebitda_mn":     -666.40,
                "net_income_mn": -2_742.80,
                "eps_diluted":   -6.20,
            },
            "FY25A": {
                "revenue_mn":    76_596.14,
                "ebitda_mn":     501.81,
                "net_income_mn": -1_914.70,
                "eps_diluted":   -4.11,
            },
            "FY26E": {
                "revenue_mn":    85_410.56,
                "ebitda_mn":     2_547.12,
                "net_income_mn": -1_257.93,
                "eps_diluted":   -2.84,
                "is_estimate":   True,
            },
        },
        "company_note": "📉 Loss-making. EBITDA turned positive FY25 for the first time. Net debt ₹617 cr. Minority interest ₹510 cr included in TEV. Path to PAT profitability: FY27–28E.",
    },

    "Shadowfax": {
        "metric_type": "ev_ebitda",
        "shares_mn":   583.622,
        "cash_mn":     5_582.51,
        "debt_mn":     1_474.39,
        "minority_mn": 0,
        "pref_equity_mn": 2_604.83,   # preferred equity included in TEV
        "fiscal_years": ["FY25A", "FY26E", "FY27E"],
        "financials": {
            "FY25A": {
                "revenue_mn":    24_851.31,
                "ebitda_mn":     130.65,
                "net_income_mn": 64.26,
                "eps_diluted":   0.13,
                "show_as_context": True,   # barely profitable — show as reference
            },
            "FY26E": {
                "revenue_mn":    40_015.93,
                "ebitda_mn":     1_626.96,
                "net_income_mn": 795.24,
                "eps_diluted":   1.34,
                "is_estimate":   True,
            },
            "FY27E": {
                "revenue_mn":    51_763.67,
                "ebitda_mn":     2_674.47,
                "net_income_mn": 1_902.49,
                "eps_diluted":   3.18,
                "is_estimate":   True,
            },
        },
        "company_note": "✅ Turned profitable FY25 (PAT ₹6 cr, barely). Preferred equity ₹260 cr included in TEV. Revenue growing ~61% FY25→26E. Significant profit ramp in FY26E.",
    },

    # ── GROUP 3 — EV/EBITDA + P/E (special handling) ───────────────────────

    "PhysicsWallah": {
        "metric_type": "ev_ebitda",
        "shares_mn":   2_859.6925,
        "cash_mn":     21_895.54,
        "debt_mn":     9_702.44,
        "minority_mn": 495.48,
        "pref_equity_mn": 8_344.48,   # include pref equity in TEV
        "fiscal_years": ["FY25A", "FY26E", "FY27E"],
        "financials": {
            "FY25A": {
                "revenue_mn":    28_920.36,
                "ebitda_mn":     372.44,
                "net_income_mn": -2_159.00,
                "eps_diluted":   -0.86,
            },
            "FY26E": {
                "revenue_mn":    38_504.43,
                "ebitda_mn":     3_983.83,
                "net_income_mn": 625.42,
                "eps_diluted":   0.1475,
                "is_estimate":   True,
            },
            "FY27E": {
                "revenue_mn":    49_483.20,
                "ebitda_mn":     8_111.98,
                "net_income_mn": 3_558.61,
                "eps_diluted":   1.2207,
                "is_estimate":   True,
            },
        },
        "company_note": "📉 FY25 loss-making. EBITDA barely positive. Turning profitable FY26E. EdTech scale-up phase. TEV includes ₹835 cr preferred equity + ₹50 cr minority interest.",
    },

    "TBO Tek": {
        "metric_type": "ev_ebitda",
        "shares_mn":   106.301,
        "cash_mn":     19_326.58,
        "debt_mn":     7_187.06,
        "minority_mn": 0,
        "pref_equity_mn": 0,
        "fiscal_years": ["FY25A", "FY26E", "FY27E"],
        "financials": {
            "FY25A": {
                "revenue_mn":    17_374.73,
                "ebitda_mn":     3_075.39,
                "net_income_mn": 2_298.91,
                "eps_diluted":   21.48,
            },
            "FY26E": {
                "revenue_mn":    26_565.87,
                "ebitda_mn":     3_856.78,
                "net_income_mn": 2_571.27,
                "eps_diluted":   23.11,
                "is_estimate":   True,
            },
            "FY27E": {
                "revenue_mn":    35_746.04,
                "ebitda_mn":     5_555.21,
                "net_income_mn": 3_784.36,
                "eps_diluted":   33.68,
                "is_estimate":   True,
            },
        },
        "company_note": "✅ Consistently profitable B2B travel-tech platform. Large net cash position ₹1,214 cr (cash > debt). Growing revenue and margin trajectory.",
    },

    "Pine Labs": {
        "metric_type": "ev_ebitda",
        "shares_mn":   1_148.276,
        "cash_mn":     60_637.30,   # large cash from IPO fresh issue
        "debt_mn":     8_582.10,
        "minority_mn": 0,
        "pref_equity_mn": 0,
        "fiscal_years": ["FY25A", "FY26E", "FY27E"],
        "financials": {
            "FY25A": {
                "revenue_mn":    22_742.74,
                "ebitda_mn":     1_976.42,
                "net_income_mn": -1_454.90,
                "eps_diluted":   -1.45,
            },
            "FY26E": {
                "revenue_mn":    27_421.05,
                "ebitda_mn":     4_910.13,
                "net_income_mn": 1_242.24,
                "eps_diluted":   1.08,
                "is_estimate":   True,
            },
            "FY27E": {
                "revenue_mn":    32_641.77,
                "ebitda_mn":     7_633.36,
                "net_income_mn": 3_737.00,
                "eps_diluted":   3.20,
                "is_estimate":   True,
            },
        },
        "company_note": "📉 FY25 loss-making despite positive EBITDA (D&A exceeds EBITDA margin). Large net cash ₹5,206 cr from IPO. Turning profitable FY26E. Payments infrastructure at scale.",
    },

    "Urban Company": {
        "metric_type": "ev_ebitda",
        "shares_mn":   1_542.181,
        "cash_mn":     14_405.30,
        "debt_mn":     1_357.90,
        "minority_mn": 0,
        "pref_equity_mn": 0,
        "fiscal_years": ["FY25A", "FY26A", "FY27E"],
        "financials": {
            "FY25A": {
                "revenue_mn":    11_449.48,
                "ebitda_mn":     -553.00,
                "net_income_mn": 2_397.65,    # positive — exceptional items
                "eps_diluted":   1.65,
                "exceptional_note": "PAT positive due to exceptional items (deferred tax credit). Core EBITDA negative.",
            },
            "FY26A": {
                "revenue_mn":    16_922.30,
                "ebitda_mn":     -771.10,
                "net_income_mn": -2_348.10,
                "eps_diluted":   -1.57,
            },
            "FY27E": {
                "revenue_mn":    20_632.25,
                "ebitda_mn":     -3_346.55,
                "net_income_mn": -2_755.23,
                "eps_diluted":   -1.71,
                "is_estimate":   True,
            },
        },
        "company_note": "📉 EBITDA negative across all years shown. FY25 PAT positive due to exceptional items only (not core operations). Home-services marketplace in growth phase.",
    },

    "Meesho": {
        "metric_type": "ev_ebitda",
        "shares_mn":   4_587.448,
        "cash_mn":     28_449.12,
        "debt_mn":     626.29,
        "minority_mn": 0,
        "pref_equity_mn": 0,
        "fiscal_years": ["FY25A", "FY26A", "FY27E"],
        "financials": {
            "FY25A": {
                "revenue_mn":    93_899.03,
                "ebitda_mn":     -5_941.00,
                "net_income_mn": -39_417.10,   # includes strategic investment write-downs
                "eps_diluted":   -9.98,
                "exceptional_note": "Large net loss includes strategic investment write-downs.",
            },
            "FY26A": {
                "revenue_mn":    126_263.48,
                "ebitda_mn":     -14_851.10,
                "net_income_mn": -13_577.40,
                "eps_diluted":   -3.11,
            },
            "FY27E": {
                "revenue_mn":    171_598.58,
                "ebitda_mn":     -5_356.29,
                "net_income_mn": -3_585.77,
                "eps_diluted":   -0.78,
                "is_estimate":   True,
            },
        },
        "company_note": "📉 Loss-making across all years. Revenue growing strongly: +34% FY26, +36% FY27E. EBITDA losses reducing. Path to profitability FY28E per analysts.",
    },

    "Capillary Technologies": {
        "metric_type": "ev_ebitda",
        "shares_mn":   79.472,
        "cash_mn":     1_604.34,
        "debt_mn":     536.07,
        "minority_mn": 0,
        "pref_equity_mn": 0,
        "fiscal_years": ["FY25A", "FY26A", "FY27E"],
        "financials": {
            "FY25A": {
                "revenue_mn":    6_006.32,
                "ebitda_mn":     660.41,
                "net_income_mn": 132.80,
                "eps_diluted":   1.91,
            },
            "FY26A": {
                "revenue_mn":    7_483.33,
                "ebitda_mn":     1_065.85,
                "net_income_mn": 523.88,
                "eps_diluted":   6.87,
            },
            "FY27E": {
                "revenue_mn":    10_500,
                "ebitda_mn":     1_617,
                "net_income_mn": 926,
                "eps_diluted":   11.50,
                "is_estimate":   True,
            },
        },
        "company_note": "✅ FY25 first profitable year. B2B loyalty SaaS. Revenue grew +24.6% in FY26. Improving profitability trajectory with EBITDA expanding.",
    },

    "Awfis Space": {
        "metric_type": "ev_ebitda",
        "shares_mn":   71.540,
        "cash_mn":     759.07,
        "debt_mn":     14_509.70,   # lease obligations (Ind AS 116)
        "minority_mn": 0,
        "pref_equity_mn": 0,
        "fiscal_years": ["FY24A", "FY25A"],
        "financials": {
            "FY24A": {
                "revenue_mn":    8_488.19,
                "ebitda_mn":     1_046.74,   # elevated — Ind AS 116
                "net_income_mn": -175.70,
                "eps_diluted":   -2.79,
                "ind_as_116":    True,
            },
            "FY25A": {
                "revenue_mn":    12_075.35,
                "ebitda_mn":     2_091.97,   # elevated — Ind AS 116
                "net_income_mn": 678.70,
                "eps_diluted":   9.67,
                "ind_as_116":    True,
            },
        },
        "company_note": "✅ FY25: First profitable year at PAT level. Flexible workspace operator. EBITDA inflated by Ind AS 116.",
        "ind_as_116_warning": "⚠️ EBITDA is materially elevated due to Ind AS 116 lease accounting. Debt of ₹1,451 cr represents lease obligations, not financial debt. Pre-Ind AS 116, EBITDA would be significantly lower.",
    },

    "Go Digit Insurance": {
        "metric_type": "insurance",   # P/E only — EV/EBITDA not standard for insurers
        "shares_mn":   923.562,
        "cash_mn":     2_191.50,
        "debt_mn":     3_500.00,
        "minority_mn": 0,
        "pref_equity_mn": 0,
        "fiscal_years": ["FY24A", "FY25A"],
        "financials": {
            "FY24A": {
                "revenue_mn":    81_473.50,    # GWP + investment income
                "ebitda_mn":     2_382.40,     # not meaningful for insurance
                "net_income_mn": 1_816.80,
                "eps_diluted":   2.05,
            },
            "FY25A": {
                "revenue_mn":    93_709.40,
                "ebitda_mn":     5_143.70,
                "net_income_mn": 4_249.40,
                "eps_diluted":   4.62,
            },
        },
        "company_note": "✅ Insurance company. Growing profitably — net profit 2.3x YoY FY24→25. EPS from ₹2.05 to ₹4.62. Revenue includes gross written premiums and investment income.",
        "insurance_note": "⚠️ EV/EBITDA is not a standard valuation metric for insurance companies. P/E (Price/Earnings) is the primary multiple for insurers. Shown here for reference only.",
    },
}
