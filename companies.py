# Z47 Index constituents — updated June 2026
# mkt_cap_mn = INR Mn; pre-2024 entrants at Jan 2 2024 price; post-2024 at listing-day price; others at March 2026
# Sectors: exactly 4 — Fintech / Financial Services | Consumer / Consumer Tech | B2B | SaaS / AI
# Sector counts: Consumer Tech 19 | Fintech 13 | B2B 6 | SaaS/AI 9 | Total 47
# Constituent changes (full event log with divisors in constituent_events.json):
#   30 May 2024: Awfis (AWFIS)         IN  [slot 34] — WeWork India (WEWORK)   OUT (retroactive erasure)
#   14 Nov 2024: 360 One Wam (360ONE)  OUT; no direct replacement in revised constituent set
#   16 Feb 2026: Aye Finance (AYE)     IN  [slot 40] — Smartworks (SMARTWORKS) OUT
#    8 May 2026: Kissht (KISSHT)       IN  [slot 44] — Awfis prev@44 (AWFIS)  OUT (Awfis stays at slot 34)
#   16 Jun 2026: Angel One (ANGELONE) / Affle (AFFLE) IN from 1 Jan 2024 (listed pre-base)
#                Amagi (AMAGI) IN from 21 Jan 2026 / Fractal (FRACTAL) IN from 16 Feb 2026
#                OUT: Niva Bupa (NIVABUPA) / Home First (HOMEFIRST) / India Shelter (INDIASHLTR) / Yatra (YATRA)
COMPANIES = [
    {"num":  1, "name": "Eternal (Zomato)",           "ticker": "ETERNAL",    "exchange": "NSE",    "sector": "Consumer / Consumer Tech",       "float_pct": 74.43, "mkt_cap_mn": 2365689.80},
    {"num":  2, "name": "Groww",                       "ticker": "GROWW",      "exchange": "NSE",    "sector": "Fintech / Financial Services",    "float_pct":  9.71, "mkt_cap_mn": 1305096.31},
    {"num":  3, "name": "Swiggy",                      "ticker": "SWIGGY",     "exchange": "NSE",    "sector": "Consumer / Consumer Tech",        "float_pct": 49.57, "mkt_cap_mn":  724990.31},
    {"num":  4, "name": "Info Edge (Naukri)",           "ticker": "NAUKRI",     "exchange": "NSE",    "sector": "Consumer / Consumer Tech",        "float_pct": 58.77, "mkt_cap_mn":  635916.08},
    {"num":  5, "name": "Lenskart",                    "ticker": "LENSKART",   "exchange": "NSE",    "sector": "Consumer / Consumer Tech",        "float_pct": 16.81, "mkt_cap_mn":  891605.00},
    {"num":  6, "name": "Paytm",                       "ticker": "PAYTM",      "exchange": "NSE",    "sector": "Fintech / Financial Services",    "float_pct": 65.52, "mkt_cap_mn":  766390.70},
    {"num":  7, "name": "SBI Cards",                   "ticker": "SBICARD",    "exchange": "NSE",    "sector": "Fintech / Financial Services",    "float_pct": 31.42, "mkt_cap_mn":  616783.03},
    {"num":  8, "name": "Nykaa",                       "ticker": "NYKAA",      "exchange": "NSE",    "sector": "Consumer / Consumer Tech",        "float_pct": 47.63, "mkt_cap_mn":  772427.24},
    {"num":  9, "name": "PolicyBazaar",                "ticker": "POLICYBZR",  "exchange": "NSE",    "sector": "Fintech / Financial Services",    "float_pct": 73.43, "mkt_cap_mn":  779221.40},
    {"num": 10, "name": "Meesho",                      "ticker": "MEESHO",     "exchange": "NSE",    "sector": "Consumer / Consumer Tech",        "float_pct":  6.22, "mkt_cap_mn":  886706.00},
    {"num": 11, "name": "MakeMyTrip",                  "ticker": "MMYT",       "exchange": "NASDAQ", "sector": "Consumer / Consumer Tech",        "float_pct": 25.74, "mkt_cap_mn":  451627.42},
    {"num": 12, "name": "Angel One",                    "ticker": "ANGELONE",  "exchange": "NSE",    "sector": "Fintech / Financial Services",    "float_pct": 53.55, "mkt_cap_mn":  310982.12},  # in from 1 Jan 2024 (listed Oct 2020)
    {"num": 13, "name": "PhysicsWallah",               "ticker": "PWL",        "exchange": "NSE",    "sector": "Consumer / Consumer Tech",        "float_pct": 16.12, "mkt_cap_mn":  314394.59},
    {"num": 14, "name": "Delhivery",                   "ticker": "DELHIVERY",  "exchange": "NSE",    "sector": "B2B",                             "float_pct": 74.39, "mkt_cap_mn":  360683.49},
    {"num": 15, "name": "Go Digit Insurance",          "ticker": "GODIGIT",    "exchange": "NSE",    "sector": "Fintech / Financial Services",    "float_pct": 25.96, "mkt_cap_mn":  291291.42},
    {"num": 16, "name": "Ather Energy",                "ticker": "ATHERENERG", "exchange": "NSE",    "sector": "Consumer / Consumer Tech",        "float_pct": 49.83, "mkt_cap_mn":  347161.09},
    {"num": 17, "name": "Pine Labs",                   "ticker": "PINELABS",   "exchange": "NSE",    "sector": "Fintech / Financial Services",    "float_pct": 15.37, "mkt_cap_mn":  231515.48},
    {"num": 18, "name": "Freshworks",                  "ticker": "FRSH",       "exchange": "NASDAQ", "sector": "SaaS / AI",                       "float_pct": 79.18, "mkt_cap_mn":  235269.90},
    {"num": 19, "name": "Urban Company",               "ticker": "URBANCO",    "exchange": "NSE",    "sector": "Consumer / Consumer Tech",        "float_pct": 21.81, "mkt_cap_mn":  226114.52},
    {"num": 20, "name": "TBO Tek",                     "ticker": "TBOTEK",     "exchange": "NSE",    "sector": "B2B",                             "float_pct": 31.36, "mkt_cap_mn":  134492.65},
    {"num": 21, "name": "FirstCry",                    "ticker": "FIRSTCRY",   "exchange": "NSE",    "sector": "Consumer / Consumer Tech",        "float_pct": 42.29, "mkt_cap_mn":  124618.59},
    {"num": 22, "name": "Aptus Value Housing",         "ticker": "APTUS",      "exchange": "NSE",    "sector": "Fintech / Financial Services",    "float_pct": 70.54, "mkt_cap_mn":  137729.29},
    {"num": 23, "name": "Ola Electric",                "ticker": "OLAELEC",    "exchange": "NSE",    "sector": "Consumer / Consumer Tech",        "float_pct": 45.42, "mkt_cap_mn":  154776.02},
    {"num": 24, "name": "IndiaMart",                   "ticker": "INDIAMART",  "exchange": "NSE",    "sector": "B2B",                             "float_pct": 50.77, "mkt_cap_mn":  125632.83},
    {"num": 25, "name": "Five-Star Business Finance",  "ticker": "FIVESTAR",   "exchange": "NSE",    "sector": "Fintech / Financial Services",    "float_pct": 65.56, "mkt_cap_mn":  139691.70},
    {"num": 26, "name": "CarTrade",                    "ticker": "CARTRADE",   "exchange": "NSE",    "sector": "Consumer / Consumer Tech",        "float_pct": 87.96, "mkt_cap_mn":   92108.10},
    {"num": 27, "name": "Affle (Affle 3i)",             "ticker": "AFFLE",      "exchange": "NSE",    "sector": "SaaS / AI",                       "float_pct": 43.69, "mkt_cap_mn":  184182.96},  # in from 1 Jan 2024 (listed Aug 2019)
    {"num": 28, "name": "BlackBuck",                   "ticker": "BLACKBUCK",  "exchange": "NSE",    "sector": "B2B",                             "float_pct": 57.32, "mkt_cap_mn":  101952.93},
    {"num": 29, "name": "Nazara Technologies",         "ticker": "NAZARA",     "exchange": "NSE",    "sector": "Consumer / Consumer Tech",        "float_pct": 61.16, "mkt_cap_mn":  101637.08},
    {"num": 30, "name": "MedPlus Health",              "ticker": "MEDPLUS",    "exchange": "NSE",    "sector": "Consumer / Consumer Tech",        "float_pct": 59.66, "mkt_cap_mn":  105828.17},
    {"num": 31, "name": "Ixigo",                       "ticker": "IXIGO",      "exchange": "NSE",    "sector": "Consumer / Consumer Tech",        "float_pct": 48.82, "mkt_cap_mn":   73933.22},
    {"num": 32, "name": "Honasa (Mamaearth)",          "ticker": "HONASA",     "exchange": "NSE",    "sector": "Consumer / Consumer Tech",        "float_pct": 41.66, "mkt_cap_mn":  115376.13},
    {"num": 33, "name": "Amagi Media Labs",             "ticker": "AMAGI",      "exchange": "NSE",    "sector": "SaaS / AI",                       "float_pct": 20.99, "mkt_cap_mn":   75340.04},  # in from 21 Jan 2026 (listing date)
    {"num": 34, "name": "Awfis Space Solutions",        "ticker": "AWFIS",     "exchange": "NSE",    "sector": "B2B",                             "float_pct": 41.80, "mkt_cap_mn":   22216.79},  # in from 30 May 2024 (listing date), replaces WeWork India retroactively
    {"num": 35, "name": "RateGain",                    "ticker": "RATEGAIN",   "exchange": "NSE",    "sector": "SaaS / AI",                       "float_pct": 51.41, "mkt_cap_mn":   74897.62},
    {"num": 36, "name": "MapmyIndia",                  "ticker": "MAPMYINDIA", "exchange": "NSE",    "sector": "SaaS / AI",                       "float_pct": 31.56, "mkt_cap_mn":   52976.04},
    {"num": 37, "name": "BlueStone",                   "ticker": "BLUESTONE",  "exchange": "NSE",    "sector": "Consumer / Consumer Tech",        "float_pct": 36.14, "mkt_cap_mn":   76599.46},
    {"num": 38, "name": "Shadowfax",                   "ticker": "SHADOWFAX",  "exchange": "NSE",    "sector": "B2B",                             "float_pct": 20.86, "mkt_cap_mn":   99121.48},
    {"num": 39, "name": "Wakefit",                     "ticker": "WAKEFIT",    "exchange": "NSE",    "sector": "Consumer / Consumer Tech",        "float_pct": 20.01, "mkt_cap_mn":   43677.70},
    {"num": 40, "name": "Aye Finance",                  "ticker": "AYE",        "exchange": "NSE",    "sector": "Fintech / Financial Services",    "float_pct": 30.02, "mkt_cap_mn":   30628.37},  # joined 16 Feb 2026
    {"num": 41, "name": "E2E Networks",                "ticker": "E2E",        "exchange": "NSE",    "sector": "SaaS / AI",                       "float_pct": 41.93, "mkt_cap_mn":   65932.11},
    {"num": 42, "name": "Capillary Technologies",      "ticker": "CAPILLARY",  "exchange": "NSE",    "sector": "SaaS / AI",                       "float_pct": 18.77, "mkt_cap_mn":   43991.72},
    {"num": 43, "name": "Medi Assist",                 "ticker": "MEDIASSIST", "exchange": "NSE",    "sector": "Fintech / Financial Services",    "float_pct": 86.70, "mkt_cap_mn":   28211.15},
    {"num": 44, "name": "Kissht (OnEMI Technology)",    "ticker": "KISSHT",     "exchange": "NSE",    "sector": "Fintech / Financial Services",    "float_pct": 28.31, "mkt_cap_mn":   33034.47},  # joined 8 May 2026
    {"num": 45, "name": "Fractal Analytics",            "ticker": "FRACTAL",    "exchange": "NSE",    "sector": "SaaS / AI",                       "float_pct": 20.25, "mkt_cap_mn":  145680.25},  # in from 16 Feb 2026 (listing date)
    {"num": 46, "name": "MobiKwik",                    "ticker": "MOBIKWIK",   "exchange": "NSE",    "sector": "Fintech / Financial Services",    "float_pct": 52.90, "mkt_cap_mn":   16906.54},
    {"num": 47, "name": "Unicommerce",                 "ticker": "UNIECOM",    "exchange": "NSE",    "sector": "SaaS / AI",                       "float_pct": 40.00, "mkt_cap_mn":   10231.95},
]

# yfinance ticker (NSE gets ".NS" suffix, NASDAQ stays as-is)
def yf_ticker(c: dict) -> str:
    return c["ticker"] + ".NS" if c["exchange"] == "NSE" else c["ticker"]

SECTOR_COLORS = {
    "Fintech / Financial Services": "#D6E4FF",   # pastel blue
    "Consumer / Consumer Tech":     "#D4EDDA",   # pastel green
    "B2B":                          "#E8D5F5",   # pastel purple
    "SaaS / AI":                    "#D1ECF1",   # pastel teal
}

# Dark text/badge colors that pair with the pastel backgrounds above
SECTOR_BADGE_COLORS = {
    "Fintech / Financial Services": "#1d4ed8",   # deep blue
    "Consumer / Consumer Tech":     "#166534",   # deep green
    "B2B":                          "#6d28d9",   # deep purple
    "SaaS / AI":                    "#0e7490",   # deep teal
}

MKT_CAP_DATE = "March 2026"  # date of Excel data used for base market cap
