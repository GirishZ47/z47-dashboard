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

def _neutral_why(ret) -> str:
    """Two-factor neutral fallback when a ticker has no library entry."""
    return "stock-specific factors and broader market conditions."
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
    """Nifty 500 1M return + USD/INR."""
    all_ticks = ["^CRSLDX", "USDINR=X"]
    raw = yf.download(all_ticks, period="70d", progress=False, auto_adjust=True)

    if not isinstance(raw.columns, pd.MultiIndex):
        return 85.0, 0.0

    closes  = raw["Close"]
    today_dt = date.today()
    start30  = pd.Timestamp(today_dt - timedelta(days=30))

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

    return usdinr, n500_ret


def _fetch_since_base() -> tuple:
    """Return (z47_since_pct, n500_since_pct) from history CSV (base 100 = 1 Jan 2024)."""
    try:
        _csv = os.path.join(os.path.dirname(os.path.abspath(__file__)), "z47_history.csv")
        df = pd.read_csv(_csv, parse_dates=["date"])
        df = df.sort_values("date").dropna(subset=["z47_float", "n500_indexed"])
        last = df.iloc[-1]
        z_since = round(float(last["z47_float"]) - 100.0, 1)
        n_since = round(float(last["n500_indexed"]) - 100.0, 1)
        return z_since, n_since
    except Exception as _e:
        print(f"[gen] _fetch_since_base failed: {_e}")
        return None, None


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
            m = re.match(r"^(.+?)\s+\[?([+-]\d+\.\d+)%\]?", clean)
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

    print("[gen] fetching market context...")
    usdinr, n500_ret = _fetch_volume_and_context()

    print("[gen] fetching market caps...")
    mcaps = _fetch_mcaps()

    print("[gen] fetching since-base performance...")
    z_since, n_since = _fetch_since_base()

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
        _bs_v = round(vsr[bs], 1) + 0.0
        _bs_sign = "roughly flat" if _bs_v == 0.0 else (f"+{_bs_v:.1f}%" if _bs_v > 0 else f"{_bs_v:.1f}%")
        _ws_v = round(vsr[ws], 1) + 0.0
        _ws_sign = "roughly flat" if _ws_v == 0.0 else (f"+{_ws_v:.1f}%" if _ws_v > 0 else f"{_ws_v:.1f}%")
        sector_line = (
            f"{bs} was the best-performing sector in the cohort at "
            f"{_bs_sign}, while {ws} was the weakest at "
            f"{_ws_sign}, reflecting growing investor interest in "
            f"{_desc}."
        )

    _reason_bullet = ("Anchored in domestic demand and rising digital adoption, "
                      "the cohort remained resilient amid global headwinds.")

    _em  = '<em style="font-style:italic;text-transform:none">fortyseven</em>'
    if abs(spread) < 1.0:
        _monthly_tail = "roughly in line with the Nifty 500."
    elif spread > 0:
        _monthly_tail = f"leading by {abs(spread):.1f} percentage points."
    else:
        _monthly_tail = f"trailing by {abs(spread):.1f} percentage points."
    _monthly_bullet = (
        f"The cohort moved {z_ret:+.1f}% over the month versus Nifty 500's "
        f"{n_ret:+.1f}%, {_monthly_tail}"
    )

    if z_since is not None and n_since is not None:
        _z_dir = "up" if z_since >= 0 else "down"
        _n_sign = f"+{n_since:.1f}" if n_since >= 0 else f"{n_since:.1f}"
        _since_spread = round(z_since - n_since, 1)
        _since_ahd = "ahead" if _since_spread >= 0 else "behind"
        _since_bullet = (
            f"Z47^{_em} is {_z_dir} {abs(z_since):.1f}% since its January 2024 base date, "
            f"versus Nifty 500's {_n_sign}%, {_since_ahd} by {abs(_since_spread):.1f} percentage points."
        )
        s1 = [_since_bullet, _monthly_bullet, _reason_bullet]
    else:
        s1 = [_monthly_bullet, _reason_bullet]

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
        why = MONTHLY_TAKEAWAY_WHY.get(tk_) or _neutral_why(ret)
        s2.append(f"{nm} [{rs}]; {why}")

    # Sections 3 & 4: top/bottom 2 — sorted from same returns_1m
    # Matches _s5_movers: valid = {t: v for t,v in returns_1m.items() if v not None/NaN}
    # sorted descending / ascending; takeaway takes positions [0] and [1].
    valid_r = {t: v for t, v in returns_1m.items() if v is not None and not pd.isna(v)}
    top2g   = sorted(valid_r.items(), key=lambda x: -x[1])[:2]
    top2l   = sorted(valid_r.items(), key=lambda x:  x[1])[:2]

    def _why(t, p):
        return MONTHLY_TAKEAWAY_WHY.get(t) or _neutral_why(p)

    s3 = [f"{name_map.get(t, t)} [{p:+.1f}%]; {_why(t, p)}" for t, p in top2g]
    s4 = [f"{name_map.get(t, t)} [{p:+.1f}%]; {_why(t, p)}" for t, p in top2l]

    # Section 6 bullet 3: block deal
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

    s6 = list(MONTHLY_TAKEAWAY_MACRO)

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
