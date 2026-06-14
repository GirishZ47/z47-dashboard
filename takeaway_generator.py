"""
Standalone monthly takeaway generator.
Run: python takeaway_generator.py
Writes auto_monthly_takeaway.json to the repo root.

NUMBER CONSISTENCY GUARANTEE:
- returns_1m is computed by _fetch_returns_1m(), which is a byte-for-byte
  replica of _fetch_1m_returns() in page_z47fortyseven.py (same period="50d",
  same base_i selection, same round-to-2dp).
- Sections 2, 3, 4 read exclusively from this dict.
- _check_consistency() asserts all named percentages match before writing.
"""
from __future__ import annotations

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import pandas as pd
import yfinance as yf

try:
    from companies import COMPANIES, yf_ticker
except ImportError:
    raise SystemExit("companies.py not found — run from repo root")

try:
    from takeaway_constants import (
        MONTHLY_TAKEAWAY_WHY,
        MONTHLY_TAKEAWAY_THEMES,
        MONTHLY_TAKEAWAY_MACRO,
        MONTHLY_TAKEAWAY_NET_READ,
    )
except ImportError:
    MONTHLY_TAKEAWAY_WHY = {}
    MONTHLY_TAKEAWAY_THEMES = []
    MONTHLY_TAKEAWAY_MACRO = []
    MONTHLY_TAKEAWAY_NET_READ = []

_NEUTRAL_WHY = "moved with the broader cohort this month."
_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auto_monthly_takeaway.json")

_SECTOR_MAP = {
    "Consumer / Consumer Tech": "Consumer Tech",
    "Fintech / Financial Services": "Fintech",
    "B2B": "B2B",
    "SaaS / AI": "SaaS/AI",
}
_DESCRIPTOR = {
    "Consumer Tech": "consumer-facing businesses",
    "Fintech": "financial-services names",
    "B2B": "B2B and enterprise names",
    "SaaS/AI": "AI-linked businesses",
}


# ---------------------------------------------------------------------------
# Canonical return computation — MUST match _fetch_1m_returns() in
# page_z47fortyseven.py exactly (same logic, same rounding, same period).
# ---------------------------------------------------------------------------

def _fetch_returns_1m() -> dict:
    """
    1-calendar-month returns for all 47 companies, NaN-safe.
    Exact replica of _fetch_1m_returns() from page_z47fortyseven.py:
      - period="50d"
      - base = first row in the shared date index with date >= today-30d
      - return = round((end / base - 1) * 100, 2)
    """
    tickers = [yf_ticker(c) for c in COMPANIES]
    tk_map  = {yf_ticker(c): c["ticker"] for c in COMPANIES}
    raw     = yf.download(tickers, period="50d", progress=False, auto_adjust=True)
    closes  = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
    if closes.empty:
        return {}
    target  = date.today() - timedelta(days=30)
    valid_i = [i for i, d in enumerate(closes.index) if d.date() >= target]
    if not valid_i:
        return {}
    base_i = valid_i[0]
    result: dict = {}
    for yftk in closes.columns:
        z47tk = tk_map.get(yftk)
        if not z47tk:
            continue
        s = closes[yftk].dropna()
        if len(s) < base_i + 1:
            continue
        b = float(s.iloc[base_i])
        e = float(s.iloc[-1])
        if b and b > 0 and not pd.isna(b) and not pd.isna(e):
            result[z47tk] = round((e / b - 1) * 100, 2)
    return result


# ---------------------------------------------------------------------------
# Volume + market context (separate fetch; not shown on any app tab).
# ---------------------------------------------------------------------------

def _fetch_volume_and_context():
    """OHLCV for volume MoM + Nifty 500 1M return + USD/INR."""
    tickers_yf = [yf_ticker(c) for c in COMPANIES]
    tk_map     = {yf_ticker(c): c["ticker"] for c in COMPANIES}
    all_ticks  = tickers_yf + ["^CRSLDX", "USDINR=X"]
    raw = yf.download(all_ticks, period="70d", progress=False, auto_adjust=True)

    if not isinstance(raw.columns, pd.MultiIndex):
        return 0.0, 0.0, 85.0, 0.0

    closes  = raw["Close"]
    volumes = raw["Volume"]
    today_dt = date.today()
    start30  = pd.Timestamp(today_dt - timedelta(days=30))
    start60  = pd.Timestamp(today_dt - timedelta(days=60))
    idx = pd.to_datetime(closes.index).tz_localize(None)
    mask30 = idx >= start30
    mask60 = (idx >= start60) & (idx < start30)

    usdinr = 85.0
    if "USDINR=X" in closes.columns:
        fx = closes["USDINR=X"].dropna()
        if not fx.empty:
            usdinr = float(fx.iloc[-1])

    n500_ret = 0.0
    if "^CRSLDX" in closes.columns:
        n_s  = closes["^CRSLDX"].dropna()
        n_30 = n_s[n_s.index >= start30]
        if len(n_30) >= 2:
            n500_ret = round((float(n_30.iloc[-1]) / float(n_30.iloc[0]) - 1) * 100, 2)

    # Volume: only stocks with data in BOTH windows (avoids pre-listing distortion)
    const_cols  = [t for t in tickers_yf if t in closes.columns and t in volumes.columns]
    daily_val   = closes[const_cols] * volumes[const_cols]
    stocks_both = [col for col in daily_val.columns
                   if daily_val[col][mask30].notna().any()
                   and daily_val[col][mask60].notna().any()]
    if stocks_both:
        vol_30d = float(daily_val[stocks_both][mask30].sum().sum())
        vol_60d = float(daily_val[stocks_both][mask60].sum().sum())
    else:
        vol_30d = float(daily_val[const_cols][mask30].sum().sum())
        vol_60d = 0.0

    return vol_30d, vol_60d, usdinr, n500_ret


def _fetch_mcaps():
    def _get(c):
        try:
            fi = yf.Ticker(yf_ticker(c)).fast_info
            mc = getattr(fi, "market_cap", None)
            if mc and mc > 0:
                cur = "INR" if c["exchange"] == "NSE" else "USD"
                return c["ticker"], {"mc": mc / 1e6, "currency": cur}
        except Exception:
            pass
        return c["ticker"], None
    out = {}
    with ThreadPoolExecutor(max_workers=12) as ex:
        for tk, mc in ex.map(_get, COMPANIES):
            if mc:
                out[tk] = mc
    return out


# ---------------------------------------------------------------------------
# Build-step consistency check
# ---------------------------------------------------------------------------

def _check_consistency(sections: list, returns_1m: dict) -> None:
    """
    Assert every named-company percentage in sections 2, 3, 4 exactly matches
    the value in returns_1m (the canonical source).  Raises AssertionError on
    any mismatch — treat this as a build failure.
    """
    name_map = {c["name"]: c["ticker"] for c in COMPANIES}

    # sections[1]=largest constituents, [2]=top gainers, [3]=top laggards
    for sec_idx in (1, 2, 3):
        if sec_idx >= len(sections):
            continue
        for bullet in sections[sec_idx].get("sub_bullets", []):
            # bullet format: "Name +X.X%; why sentence"
            # strip HTML tags for matching
            clean = re.sub(r"<[^>]+>", "", bullet)
            m = re.match(r"^(.+?)\s+([+-]\d+\.\d+)%", clean)
            if not m:
                continue
            nm, pct_str = m.group(1).strip(), m.group(2)
            pct_bullet = float(pct_str)
            tk = name_map.get(nm)
            if tk is None:
                # try reverse map via returns_1m keys
                for c in COMPANIES:
                    if c["name"] == nm:
                        tk = c["ticker"]
                        break
            if tk is None:
                print(f"  [check] WARNING: could not map name '{nm}' to ticker; skipping")
                continue
            pct_source = returns_1m.get(tk)
            if pct_source is None:
                print(f"  [check] WARNING: no returns_1m entry for {tk} ({nm}); skipping")
                continue
            # Bullets format to 1dp; compare rounded source to same precision.
            assert abs(pct_bullet - round(pct_source, 1)) < 0.005, (
                f"NUMBER MISMATCH: section[{sec_idx}] bullet '{nm}' "
                f"shows {pct_bullet:+.2f}% but returns_1m[{tk}] = {pct_source:+.2f}% "
                f"(rounds to {round(pct_source,1):+.1f}%)"
            )
    print("  [check] all named percentages verified against returns_1m")


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate() -> dict:
    """Generate and return the monthly takeaway dict (no Streamlit deps)."""
    today    = date.today()
    start_dt = today - timedelta(days=30)
    window   = f"{start_dt.day} {start_dt.strftime('%b')} – {today.day} {today.strftime('%b %Y')}"

    print("[gen] fetching 1M returns (canonical — matches _fetch_1m_returns)...")
    returns_1m = _fetch_returns_1m()

    print("[gen] fetching volume + market context...")
    vol_30d, vol_60d, usdinr, n500_ret = _fetch_volume_and_context()

    print("[gen] fetching market caps...")
    mcaps = _fetch_mcaps()

    name_map = {c["ticker"]: c["name"] for c in COMPANIES}

    def _wt(c):
        mc = mcaps.get(c["ticker"])
        if mc:
            v = mc.get("mc", 0)
            if mc.get("currency", "INR") != "INR":
                v *= usdinr
            return v
        return c.get("mkt_cap_mn", 0)

    # Float-weighted Z47 return (uses same returns_1m for internal consistency)
    total_w = sum(_wt(c) for c in COMPANIES)
    z_ret   = 0.0
    if total_w > 0:
        for c in COMPANIES:
            r = returns_1m.get(c["ticker"])
            if r is not None:
                z_ret += r * _wt(c) / total_w
    z_ret  = round(z_ret, 1)
    n_ret  = round(n500_ret, 1)
    spread = round(z_ret - n_ret, 1)

    # Sector returns
    _sr = {}
    for _full, _short in _SECTOR_MAP.items():
        _tks = [c["ticker"] for c in COMPANIES if c["sector"] == _full]
        _vs  = [returns_1m[t] for t in _tks if returns_1m.get(t) is not None]
        _sr[_short] = round(sum(_vs) / len(_vs), 1) if _vs else None
    vsr = {k: v for k, v in _sr.items() if v is not None}

    bs = ws = None
    sector_line = None
    if vsr:
        bs   = max(vsr, key=vsr.get)
        ws   = min(vsr, key=vsr.get)
        _desc    = _DESCRIPTOR.get(bs, bs.lower())
        _ws_sign = f"+{vsr[ws]:.1f}%" if vsr[ws] >= 0 else f"{vsr[ws]:.1f}%"
        sector_line = (
            f"{bs} was the best-performing sector in the cohort at "
            f"+{vsr[bs]:.1f}%, while {ws} was the weakest at "
            f"{_ws_sign}, reflecting a clear investor preference for "
            f"{_desc} this month."
        )

    if spread > 0:
        _bs_name = bs if bs else "its strongest sectors"
        cond = (f"The cohort outpaced the broad index, with strength in {_bs_name} "
                f"reinforcing the resilience of its domestic-demand and digital base.")
    elif spread < 0:
        _ws_name = ws if ws else "its weaker sectors"
        cond = (f"The cohort lagged the broad index as weakness in {_ws_name} "
                f"outweighed its broader domestic-demand resilience this month.")
    else:
        cond = ("The cohort tracked the broad index over the month, with company-specific "
                "moves offsetting across sectors.")

    _em  = '<em style="font-style:italic;text-transform:none">fortyseven</em>'
    _ahd = "ahead" if spread > 0 else "behind" if spread < 0 else "in line"
    s1 = [
        (f"Z47^{_em} moved {z_ret:+.1f}% over the month versus Nifty 500’s "
         f"{n_ret:+.1f}%, finishing {abs(spread):.1f} percentage points {_ahd}."),
        cond,
    ]
    if sector_line:
        s1.append(sector_line)

    # Section 2: top 3 by mcap — % from canonical returns_1m
    top3 = sorted(COMPANIES, key=_wt, reverse=True)[:3]
    s2 = []
    for c in top3:
        tk_ = c["ticker"]
        nm  = name_map.get(tk_, c["name"])
        ret = returns_1m.get(tk_)
        rs  = f"{ret:+.1f}%" if ret is not None else "—"
        why = MONTHLY_TAKEAWAY_WHY.get(tk_, _NEUTRAL_WHY)
        s2.append(f"{nm} {rs}; {why}")

    # Sections 3 & 4: top/bottom 2 — sorted from same returns_1m
    # Matches _s5_movers: valid = {t: v for t,v in returns_1m.items() if v not None/NaN}
    # sorted descending / ascending; takeaway takes positions [0] and [1].
    valid_r = {t: v for t, v in returns_1m.items() if v is not None and not pd.isna(v)}
    top2g   = sorted(valid_r.items(), key=lambda x: -x[1])[:2]
    top2l   = sorted(valid_r.items(), key=lambda x:  x[1])[:2]

    def _why(t):
        return MONTHLY_TAKEAWAY_WHY.get(t, _NEUTRAL_WHY)

    s3 = [f"{name_map.get(t, t)} {p:+.1f}%; {_why(t)}" for t, p in top2g]
    s4 = [f"{name_map.get(t, t)} {p:+.1f}%; {_why(t)}" for t, p in top2l]

    # Section 6 bullet 3: volume
    s6_vol = None
    if vol_30d > 0:
        bn30  = vol_30d / (usdinr * 1e9)
        if vol_60d > 0:
            mom_v = round((vol_30d - vol_60d) / vol_60d * 100, 0)
            ud_v  = "up" if mom_v >= 0 else "down"
            s6_vol = (f"{bn30:.1f} bn dollars of cohort shares traded "
                      f"over the month, {ud_v} {abs(int(mom_v))}% "
                      f"versus the prior month.")
        else:
            s6_vol = f"{bn30:.1f} bn dollars of cohort shares traded over the month."

    # Section 6 bullet 4: block deal
    s6_block = None
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from page_block_deals import _fetch_nse_csv_history, _FALLBACK_DEALS
        _live  = _fetch_nse_csv_history() or []
        _cut30 = start_dt.isoformat()
        _all_d = list(_live) + list(_FALLBACK_DEALS)
        _d30   = [d for d in _all_d if str(d.get("Date", ""))[:10] >= _cut30]
        if _d30:
            _lg  = max(_d30, key=lambda d: d.get("Value (₹ Cr)", 0) or 0)
            _co  = (_lg.get("Company") or
                    name_map.get(_lg.get("Symbol", ""), _lg.get("Symbol", "Unknown")))
            _val = _lg.get("Value (₹ Cr)", 0) or 0
            _qty = _lg.get("Quantity", 0) or 0
            _px  = _lg.get("Price (₹)", 0) or 0
            if _val > 0:
                _px_s    = f" at ₹{_px:.2f}" if _px > 0 else ""
                s6_block = (f"Largest block: {_co}, {_val:.0f} Cr across "
                            f"{_qty:,} shares{_px_s}.")
    except Exception as _be:
        print(f"[gen] block deals skipped: {_be}")

    s6 = list(MONTHLY_TAKEAWAY_MACRO) + [b for b in [s6_vol, s6_block] if b]

    sections = [
        {"type": "main_bullet",
         "header": f"Index performance ; Z47^{_em} vs Nifty 500",
         "sub_bullets": s1},
        {"type": "main_bullet",
         "header": "Largest constituents ; the names that anchor the index",
         "sub_bullets": s2},
        {"type": "main_bullet", "header": "Top gainers",  "sub_bullets": s3},
        {"type": "main_bullet", "header": "Top laggards", "sub_bullets": s4},
        {"type": "main_bullet",
         "header": "Key themes ; latest results",
         "sub_bullets": list(MONTHLY_TAKEAWAY_THEMES)},
        {"type": "main_bullet",
         "header": "Market &amp; macro context",
         "sub_bullets": s6},
        {"type": "section_title", "header": "Net Read",
         "sub_bullets": list(MONTHLY_TAKEAWAY_NET_READ)},
    ]

    return sections, returns_1m, {
        "section_label":    "MONTHLY TAKEAWAY",
        "window":           window,
        "date_range_label": window.upper(),
        "updated":          f"{today.day} {today.strftime('%b %Y')}",
        "sections":         sections,
    }


if __name__ == "__main__":
    print("[refresh_takeaway] starting...")
    try:
        sections, returns_1m, tk = generate()

        print("[check] verifying number consistency...")
        _check_consistency(sections, returns_1m)

        with open(_OUT, "w", encoding="utf-8") as f:
            json.dump(tk, f, indent=2, ensure_ascii=False)
        print(f"[refresh_takeaway] written to {_OUT}")
        print(f"  window:  {tk['window']}")
        print(f"  updated: {tk['updated']}")
        print(f"  top gainers:  {tk['sections'][2]['sub_bullets']}")
        print(f"  top laggards: {tk['sections'][3]['sub_bullets']}")
    except AssertionError as e:
        print(f"\n[refresh_takeaway] BUILD FAILED: {e}")
        raise SystemExit(1)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise SystemExit(1)
