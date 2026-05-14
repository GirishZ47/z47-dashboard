"""
IPO Lock-In Dates for Indian Tech/Unicorn IPOs
===============================================
Generated: 2026-05-12
Sources: BSE/NSE basis-of-allotment notices, Chittorgarh.com, Business Standard,
         MarketScreener, IPOWatch, BusinessToday, Upstox news, Goodreturns.

SEBI Lock-in Rules Applied:
  - Anchor T1: allotment + 30 calendar days (50% of anchor shares unlock)
  - Anchor T2: allotment + 90 calendar days (remaining 50% of anchor shares)
  - Pre-IPO 6m: allotment + 180 calendar days (VC/PE with >1yr pre-IPO holding)
  - Pre-IPO 1y: allotment + 365 calendar days (shares allocated <1yr before IPO)
  - Promoter 18m: allotment + 18 calendar months (promoter shares above min 20%)
  - Promoter 3y: allotment + 3 calendar years (promoter min 20% post-issue)

NOTE on allotment dates:
  - "Basis of allotment finalization" (registrar) is typically T+2 before listing.
  - Anchor investor allotment occurs the day before the IPO subscription opens.
  - SEBI lock-in is calculated from the DATE OF ALLOTMENT per the prospectus/RHP.
  - For anchor investors specifically, the lock-in runs from the anchor allotment
    date (which may differ from the public offer allotment date by 1-2 days).
  - Where user has confirmed anchor T1 dates, allotment date is back-calculated.

CRITICAL DISCREPANCY NOTE — GROWW:
  The user stated "anchor T1 = May 12, 2025 → allotment = April 12, 2025."
  Research definitively shows Groww (Billionbrains Garage Ventures) IPO:
    - Subscription: Nov 4–7, 2025
    - Allotment finalized: Nov 10, 2025
    - Listing: Nov 12, 2025
    - Anchor T1 (30d): Dec 10, 2025  (confirmed by Business Standard/PL Capital)
    - Anchor T2 (90d): Feb 8, 2026
    - 6-month pre-IPO investor unlock: ~May 9–12, 2026
      (The May 12, 2026 event — 7% stock drop + Rs 5,637 cr block deal —
       was the PRE-IPO investor 6-month lock-in expiry, NOT anchor T1.)
  The user's "May 12, 2025" is most likely a typo for "May 12, 2026"
  and "April 12, 2025" for "November 10, 2025." The dict below uses verified dates.
  Please confirm and update if a different Groww entity/IPO is intended.
"""

from datetime import date

LOCK_IN_DATES = {

    "Groww": {
        # Billionbrains Garage Ventures Ltd
        # IPO: Nov 4-7 2025 | Allotment: Nov 10 | Listing: Nov 12 2025
        # CAUTION: User stated allotment=Apr 12 2025 / anchor T1=May 12 2025.
        # Research shows these dates are INCORRECT. See module docstring above.
        # May 12 2026 was the 6-month PRE-IPO investor unlock (with 7% stock drop).
        "allotment_date": "2025-11-10",
        "listing_date": "2025-11-12",
        "anchor_t1": "2025-12-10",   # +30d; confirmed by Business Standard 2025-12-10
        "anchor_t2": "2026-02-08",   # +90d
        "pripo_6m":  "2026-05-09",   # +180d; ~May 12 2026 per news (6m unlock event)
        "pripo_1y":  "2026-11-10",   # +365d (for pre-IPO shares held <1yr before IPO)
        "promoter_18m": "2027-05-10",
        "promoter_3y":  "2028-11-10",
        "source": "Chittorgarh / Business Standard / Outlook Business / PL Capital",
        "notes": (
            "User-stated dates (allotment Apr 12 2025, T1 May 12 2025) appear INCORRECT. "
            "Verified listing Nov 12 2025. The May 12 2026 event reported in news was the "
            "6-month pre-IPO investor (Peak XV, Ribbit, YC) unlock — ~180d from Nov 10 2025. "
            "Please verify against BSE allotment notice before use."
        ),
    },

    "Swiggy": {
        # Allotment: Nov 11 2024 | Listing: Nov 13 2024
        "allotment_date": "2024-11-11",
        "listing_date":   "2024-11-13",
        "anchor_t1": "2024-12-11",   # +30d; confirmed by Business Standard (stock -4%)
        "anchor_t2": "2025-02-09",   # +90d
        "pripo_6m":  "2025-05-10",   # +180d
        "pripo_1y":  "2025-11-11",   # +365d
        "promoter_18m": "2026-05-11",
        "promoter_3y":  "2027-11-11",
        "source": "BusinessToday / Chittorgarh / Business Standard",
        "notes": "Allotment date confirmed by multiple sources as Nov 11 2024.",
    },

    "Ola Electric": {
        # Ola Electric Mobility Ltd
        # Anchor allotment: Aug 1 2024 | Public allotment finalization: Aug 7 2024
        # Listing: Aug 9 2024
        # USER CONFIRMED: allotment Aug 6, anchor T1 Sep 5 2024
        # MarketScreener confirms 181.7M shares locked until Sep 5 2024.
        # This implies SEBI used Aug 6 (IPO close date) as the lock-in start date.
        # Note: Registrar finalized basis of allotment on Aug 7, but anchor/SEBI
        # date for lock-in computation appears to be Aug 6.
        "allotment_date": "2024-08-06",   # user-confirmed; IPO close date used for lock-in
        "listing_date":   "2024-08-09",
        "anchor_t1": "2024-09-05",   # +30d; user confirmed; MarketScreener confirms
        "anchor_t2": "2024-11-04",   # +90d
        "pripo_6m":  "2025-02-02",   # +180d
        "pripo_1y":  "2025-08-06",   # +365d
        "promoter_18m": "2026-02-06",
        "promoter_3y":  "2027-08-06",
        "source": "User confirmed + MarketScreener lock-up notice + Business Standard",
        "notes": (
            "Registrar finalized basis of allotment Aug 7; but SEBI lock-in runs from "
            "Aug 6 (confirmed by MarketScreener: 181.7M shares locked to Sep 5 2024). "
            "Business Standard reported anchor T2 as Nov 5 2024 (=Aug 7+90d), suggesting "
            "some discrepancy; user-confirmed Aug 6 / Sep 5 used here."
        ),
    },

    "Ather Energy": {
        # Allotment: May 2 2025 | Listing: May 6 2025
        "allotment_date": "2025-05-02",
        "listing_date":   "2025-05-06",
        "anchor_t1": "2025-06-01",   # +30d
        "anchor_t2": "2025-07-31",   # +90d
        "pripo_6m":  "2025-10-29",   # +180d
        "pripo_1y":  "2026-05-02",   # +365d
        "promoter_18m": "2026-11-02",
        "promoter_3y":  "2028-05-02",
        "source": "Business Standard / Chittorgarh / AngelOne",
        "notes": "Allotment date confirmed as May 2 2025 by Business Standard.",
    },

    "BlackBuck": {
        # Zinka Logistics Solutions Ltd
        # Allotment: Nov 19 2024 | Listing: Nov 22 2024
        # (originally scheduled Nov 21; deferred to Nov 22 due to Maharashtra election holiday)
        "allotment_date": "2024-11-19",
        "listing_date":   "2024-11-22",
        "anchor_t1": "2024-12-19",   # +30d
        "anchor_t2": "2025-02-17",   # +90d
        "pripo_6m":  "2025-05-18",   # +180d
        "pripo_1y":  "2025-11-19",   # +365d
        "promoter_18m": "2026-05-19",
        "promoter_3y":  "2027-11-19",
        "source": "Business Standard / Upstox / Chittorgarh",
        "notes": (
            "Listing rescheduled from Nov 21 to Nov 22 due to Maharashtra election. "
            "User listed date as Nov 26 — actual listing was Nov 22."
        ),
    },

    "MobiKwik": {
        # One MobiKwik Systems Ltd
        # Allotment: Dec 16 2024 | Listing: Dec 18 2024
        "allotment_date": "2024-12-16",
        "listing_date":   "2024-12-18",
        "anchor_t1": "2025-01-15",   # +30d
        "anchor_t2": "2025-03-16",   # +90d
        "pripo_6m":  "2025-06-14",   # +180d
        "pripo_1y":  "2025-12-16",   # +365d
        "promoter_18m": "2026-06-16",
        "promoter_3y":  "2027-12-16",
        "source": "BusinessToday / Chittorgarh / IPOJi",
        "notes": "Allotment date confirmed as Dec 16 2024; listing Dec 18 2024.",
    },

    "Shadowfax": {
        # Shadowfax Technologies Ltd
        # Allotment: Jan 23 2026 | Listing: Jan 28 2026
        "allotment_date": "2026-01-23",
        "listing_date":   "2026-01-28",
        "anchor_t1": "2026-02-22",   # +30d
        "anchor_t2": "2026-04-23",   # +90d
        "pripo_6m":  "2026-07-22",   # +180d
        "pripo_1y":  "2027-01-23",   # +365d
        "promoter_18m": "2027-07-23",
        "promoter_3y":  "2029-01-23",
        "source": "Sahi.com / IPOJi / Chittorgarh / Groww",
        "notes": "Allotment Jan 23 2026, listing Jan 28 2026 confirmed by multiple sources.",
    },

    "Unicommerce": {
        # Unicommerce eSolutions Ltd (formerly Unirec Technologies)
        # Allotment: Aug 9 2024 | Listing: Aug 13 2024
        "allotment_date": "2024-08-09",
        "listing_date":   "2024-08-13",
        "anchor_t1": "2024-09-08",   # +30d
        "anchor_t2": "2024-11-07",   # +90d
        "pripo_6m":  "2025-02-05",   # +180d
        "pripo_1y":  "2025-08-09",   # +365d
        "promoter_18m": "2026-02-09",
        "promoter_3y":  "2027-08-09",
        "source": "Business Standard / Chittorgarh",
        "notes": "Allotment finalized Aug 9 2024; listing Aug 13 2024.",
    },

    "Ixigo": {
        # Le Travenues Technology Ltd
        # Allotment: Jun 13 2024 | Listing: Jun 18 2024
        "allotment_date": "2024-06-13",
        "listing_date":   "2024-06-18",
        "anchor_t1": "2024-07-13",   # +30d
        "anchor_t2": "2024-09-11",   # +90d
        "pripo_6m":  "2024-12-10",   # +180d
        "pripo_1y":  "2025-06-13",   # +365d
        "promoter_18m": "2025-12-13",
        "promoter_3y":  "2027-06-13",
        "source": "BusinessToday / Business Standard / Chittorgarh",
        "notes": "Allotment finalized Jun 13 2024; listing Jun 18 2024.",
    },

    "BlueStone": {
        # Bluestone Jewellery and Lifestyle Ltd
        # Allotment: Aug 14 2025 | Listing: Aug 19 2025
        "allotment_date": "2025-08-14",
        "listing_date":   "2025-08-19",
        "anchor_t1": "2025-09-13",   # +30d
        "anchor_t2": "2025-11-12",   # +90d
        "pripo_6m":  "2026-02-10",   # +180d
        "pripo_1y":  "2026-08-14",   # +365d
        "promoter_18m": "2027-02-14",
        "promoter_3y":  "2028-08-14",
        "source": "Business Standard / BusinessToday / IPOWatch",
        "notes": "Allotment Aug 14 2025; listing Aug 19 2025 confirmed.",
    },

    "Smartworks": {
        # Smartworks Coworking Spaces Ltd
        # Allotment: Jul 15 2025 | Listing: Jul 17 2025
        # (User noted 'Aug 28 2024' listing — INCORRECT; actual listing Jul 17 2025)
        "allotment_date": "2025-07-15",
        "listing_date":   "2025-07-17",
        "anchor_t1": "2025-08-14",   # +30d
        "anchor_t2": "2025-10-13",   # +90d
        "pripo_6m":  "2026-01-11",   # +180d
        "pripo_1y":  "2026-07-15",   # +365d
        "promoter_18m": "2027-01-15",
        "promoter_3y":  "2028-07-15",
        "source": "Business Standard / IPOWatch / BusinessToday",
        "notes": (
            "User noted Aug 28 2024 as listing date — INCORRECT. "
            "Smartworks Coworking IPO actually listed Jul 17 2025 (allotment Jul 15 2025). "
            "The company had filed DRHP earlier but the actual IPO was in July 2025."
        ),
    },

    "FirstCry": {
        # Brainbees Solutions Ltd (FirstCry)
        # Allotment: Aug 9 2024 | Listing: Aug 13 2024
        "allotment_date": "2024-08-09",
        "listing_date":   "2024-08-13",
        "anchor_t1": "2024-09-08",   # +30d
        "anchor_t2": "2024-11-07",   # +90d
        "pripo_6m":  "2025-02-05",   # +180d
        "pripo_1y":  "2025-08-09",   # +365d
        "promoter_18m": "2026-02-09",
        "promoter_3y":  "2027-08-09",
        "source": "Business Standard / BusinessToday / IPOWatch",
        "notes": (
            "Allotment Aug 9 2024; listing Aug 13 2024. "
            "Same allotment date as Unicommerce (coincidence — different company)."
        ),
    },

    "Awfis": {
        # Awfis Space Solutions Ltd
        # Allotment: May 28 2024 | Listing: May 30 2024
        "allotment_date": "2024-05-28",
        "listing_date":   "2024-05-30",
        "anchor_t1": "2024-06-27",   # +30d
        "anchor_t2": "2024-08-26",   # +90d
        "pripo_6m":  "2024-11-24",   # +180d
        "pripo_1y":  "2025-05-28",   # +365d
        "promoter_18m": "2025-11-28",
        "promoter_3y":  "2027-05-28",
        "source": "Chittorgarh / ICICI Direct / IPOWatch",
        "notes": "Allotment May 28 2024; listing May 30 2024 confirmed.",
    },

    "PhysicsWallah": {
        # Physicswallah Ltd
        # Allotment: Nov 14 2025 | Listing: Nov 18 2025
        # (User noted this as 'pending/upcoming as of May 2026' — INCORRECT;
        #  PW actually listed Nov 18 2025)
        "allotment_date": "2025-11-14",
        "listing_date":   "2025-11-18",
        "anchor_t1": "2025-12-14",   # +30d
        "anchor_t2": "2026-02-12",   # +90d
        "pripo_6m":  "2026-05-13",   # +180d
        "pripo_1y":  "2026-11-14",   # +365d
        "promoter_18m": "2027-05-14",
        "promoter_3y":  "2028-11-14",
        "source": "Business Standard / Upstox / Chittorgarh",
        "notes": (
            "User listed as 'pending/upcoming as of May 2026' — INCORRECT. "
            "PhysicsWallah IPO (₹3,480 cr) listed Nov 18 2025; allotment Nov 14 2025. "
            "Price band ₹109/share. SEBI approval received Jul 2025."
        ),
    },

    "TBO Tek": {
        # TBO Tek Ltd
        # Allotment: May 13 2024 | Listing: May 15 2024
        "allotment_date": "2024-05-13",
        "listing_date":   "2024-05-15",
        "anchor_t1": "2024-06-12",   # +30d
        "anchor_t2": "2024-08-11",   # +90d
        "pripo_6m":  "2024-11-09",   # +180d
        "pripo_1y":  "2025-05-13",   # +365d
        "promoter_18m": "2025-11-13",
        "promoter_3y":  "2027-05-13",
        "source": "Chittorgarh / Upstox / IPOWatch",
        "notes": "Allotment May 13 2024; listing May 15 2024 confirmed.",
    },

    "Go Digit": {
        # Go Digit General Insurance Ltd
        # Allotment: May 21 2024 | Listing: May 23 2024
        "allotment_date": "2024-05-21",
        "listing_date":   "2024-05-23",
        "anchor_t1": "2024-06-20",   # +30d
        "anchor_t2": "2024-08-19",   # +90d
        "pripo_6m":  "2024-11-17",   # +180d
        "pripo_1y":  "2025-05-21",   # +365d
        "promoter_18m": "2025-11-21",
        "promoter_3y":  "2027-05-21",
        "source": "BusinessToday / Business Standard / Chittorgarh",
        "notes": "Allotment May 21 2024; listing May 23 2024 confirmed.",
    },

    "Pine Labs": {
        # Pine Labs Ltd
        # Allotment: Nov 12 2025 | Listing: Nov 14 2025
        "allotment_date": "2025-11-12",
        "listing_date":   "2025-11-14",
        "anchor_t1": "2025-12-12",   # +30d
        "anchor_t2": "2026-02-10",   # +90d
        "pripo_6m":  "2026-05-11",   # +180d
        "pripo_1y":  "2026-11-12",   # +365d
        "promoter_18m": "2027-05-12",
        "promoter_3y":  "2028-11-12",
        "source": "Upstox / BusinessToday / Chittorgarh / Groww",
        "notes": "Allotment Nov 12 2025; listing Nov 14 2025 confirmed.",
    },

    "Urban Company": {
        # Urban Company Ltd
        # Allotment: Sep 15 2025 | Listing: Sep 17 2025
        # (One source states Sep 16; Sep 15 is T+2 from listing and matches
        #  The Hans India 'Sept 15, 2025' guide)
        "allotment_date": "2025-09-15",
        "listing_date":   "2025-09-17",
        "anchor_t1": "2025-10-15",   # +30d
        "anchor_t2": "2025-12-14",   # +90d
        "pripo_6m":  "2026-03-14",   # +180d
        "pripo_1y":  "2026-09-15",   # +365d
        "promoter_18m": "2027-03-15",
        "promoter_3y":  "2028-09-15",
        "source": "Upstox / The Hans India / Chittorgarh",
        "notes": (
            "One source states allotment Sep 16; another Sep 15. "
            "Sep 15 (Monday) used as T+2 before listing (Sep 17, Wednesday). "
            "Verify against BSE basis-of-allotment notice."
        ),
    },

    "Meesho": {
        # Meesho Ltd (Fashnear Technologies Pvt Ltd)
        # Allotment: Dec 8 2025 | Listing: Dec 10 2025
        # IPO price ₹111 (band ₹105–111). Sub: 79x. Issue: ₹3,152 cr.
        # Listing price: ₹162.50 NSE (+46.4%) / ₹161.20 BSE (+45.2%).
        # CMP: ₹189.92 (14 May 2026). MCap: ₹87,125 cr. 52W: ₹125.56–₹254.40.
        # Pre-IPO 6M: listing + 6M = Jun 10 2026 (SEBI ICDR rule; confirmed indiaipo.in)
        # "3,083 mn shares (~68%) unlock Jun 10 2026" — indiaipo.in
        "allotment_date": "2025-12-08",
        "listing_date":   "2025-12-10",
        "anchor_t1": "2026-01-07",   # allotment + 30d
        "anchor_t2": "2026-03-08",   # allotment + 90d
        "pripo_6m":  "2026-06-10",   # listing Dec 10 + 6M ← SEBI rule; NEWS CONFIRMED indiaipo.in
        "pripo_1y":  "2026-12-10",   # listing Dec 10 + 12M
        "promoter_18m": "2027-06-10",# listing Dec 10 + 18M
        "promoter_3y":  "2028-12-10",# listing Dec 10 + 3Y
        "source": "NSE / BSE / indiaipo.in / Groww / PaytmMoney",
        "notes": (
            "Listed Dec 10 2025. Allotment Dec 8 2025. IPO price ₹111. "
            "Pre-IPO lock-in Jun 10 2026 (listing + 6M per SEBI ICDR; confirmed indiaipo.in: "
            "'3,083 mn shares ~68% unlock Jun 10 2026'). "
            "CMP ₹189.92 (+71.1% vs IPO). MCap ₹87,125 cr as of 14 May 2026."
        ),
    },

    "Capillary Technologies": {
        # Capillary Technologies India Ltd
        # Allotment: Nov 19 2025 | Listing: Nov 21 2025
        "allotment_date": "2025-11-19",
        "listing_date":   "2025-11-21",
        "anchor_t1": "2025-12-19",   # +30d
        "anchor_t2": "2026-02-17",   # +90d
        "pripo_6m":  "2026-05-18",   # +180d
        "pripo_1y":  "2026-11-19",   # +365d
        "promoter_18m": "2027-05-19",
        "promoter_3y":  "2028-11-19",
        "source": "Upstox / Groww / Chittorgarh / Business Standard",
        "notes": "Allotment Nov 19 2025; listing Nov 21 2025 confirmed.",
    },

    "Kissht": {
        # OnEMI Technology Solutions Ltd (brand: Kissht + Ring)
        # Allotment: May 6 2026 | Listing: May 8 2026
        "allotment_date": "2026-05-06",
        "listing_date":   "2026-05-08",
        "anchor_t1": "2026-06-05",   # +30d
        "anchor_t2": "2026-08-04",   # +90d
        "pripo_6m":  "2026-11-02",   # +180d
        "pripo_1y":  "2027-05-06",   # +365d
        "promoter_18m": "2027-11-06",
        "promoter_3y":  "2029-05-06",
        "source": "Chittorgarh / Groww / Business Standard / IPOGuru",
        "notes": (
            "Allotment May 6 2026; listing May 8 2026. "
            "IPO open Apr 30–May 5 2026; price ₹171/share. "
            "Lock-in dates are forward-looking from today (May 12 2026)."
        ),
    },

}


# ─── SUMMARY OF DATE CORRECTIONS vs USER INPUT ──────────────────────────────
#
# IPO              | User-stated listing    | Actual listing    | Notes
# ─────────────────┼────────────────────────┼───────────────────┼────────────────
# Groww            | ~Apr 2025              | Nov 12 2025       | MAJOR MISMATCH
# BlackBuck        | Nov 26 2024            | Nov 22 2024       | minor
# Smartworks       | Aug 28 2024            | Jul 17 2025       | MAJOR MISMATCH
# PhysicsWallah    | "pending May 2026"     | Nov 18 2025       | already listed
# Meesho           | "~Jun 2025, pending?"  | Dec 10 2025       | already listed
# Ola Electric     | Aug 9 2024 (ok)        | Aug 9 2024        | allotment Aug 6 vs 7
#
# All other IPO listing dates matched user input.
#
# ─── HOW TO USE ─────────────────────────────────────────────────────────────
#
# from ipo_lock_in_dates import LOCK_IN_DATES
# from datetime import date
#
# today = date.today()
# for name, d in LOCK_IN_DATES.items():
#     if d["anchor_t1"] and date.fromisoformat(d["anchor_t1"]) >= today:
#         print(f"{name}: Anchor T1 expires {d['anchor_t1']}")
