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
      - base = first row in closes on or after (last_close_date - 1 calendar month)
      - return = round((end / base - 1) * 100, 2)
    Uses same-calendar-date convention (Google Finance style).
    """
    tickers = [yf_ticker(c) for c in COMPANIES]
    tk_map  = {yf_ticker(c): c["ticker"] for c in COMPANIES}
    raw     = yf.download(tickers, period="50d", progress=False, auto_adjust=True)
    closes  = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
    if closes.empty:
        return {}
    target  = (closes.index[-1] - pd.DateOffset(months=1)).date()
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

    usdinr = 85.0
    if "USDINR=X" in closes.columns:
        fx = closes["USDINR=X"].dropna()
        if not fx.empty:
            usdinr = float(fx.iloc[-1])

    n500_ret = 0.0
    if "^CRSLDX" in closes.columns:
        n_s    = closes["^CRSLDX"].dropna()
        anchor = pd.Timestamp(n_s.index[-1]) - pd.DateOffset(months=1)
        n_1m   = n_s[n_s.index >= anchor]
        if len(n_1m) >= 2:
            n500_ret = round((float(n_1m.iloc[-1]) / float(n_1m.iloc[0]) - 1) * 100, 2)

    return usdinr, n500_ret


_Z47_EXIT_BEFORE: dict = {}  # AWFIS (slot 34) remains active; see companies.py line 9


def _apply_iterative_cap(ff_mcap_dict: dict, cap: float = 0.10) -> dict:
    """Iteratively redistribute weight from names above cap to uncapped names."""
    weights = {k: float(v) for k, v in ff_mcap_dict.items()}
    total = sum(weights.values())
    if total <= 0:
        return weights
    for k in weights:
        weights[k] /= total
    for _ in range(100):
        over = {k: v for k, v in weights.items() if v > cap}
        if not over:
            break
        excess = sum(v - cap for v in over.values())
        under = {k: v for k, v in weights.items() if v <= cap}
        u_total = sum(under.values())
        for k in over:
            weights[k] = cap
        if u_total > 0:
            for k in under:
                weights[k] += excess * (weights[k] / u_total)
    return weights


def _build_live_extended_df() -> pd.DataFrame:
    """Load z47_history.csv and append today's live row from fast_info.

    Mirrors _fetch_live_extension in page_z47fortyseven.py so the takeaway
    generator's window end equals the chart's window end exactly."""
    _csv = os.path.join(os.path.dirname(os.path.abspath(__file__)), "z47_history.csv")
    df = pd.read_csv(_csv, parse_dates=["date"])
    df = df.sort_values("date").dropna(subset=["z47_float", "n500_indexed"]).reset_index(drop=True)

    today = pd.Timestamp.today().normalize()
    last = df.iloc[-1]
    last_date = pd.Timestamp(last["date"]).normalize()
    last_z47 = float(last["z47_float"])
    last_n5i = float(last["n500_indexed"])
    last_n5a = float(last.get("n500_abs") or 0)

    # Active constituents: exclude post-exit names
    active = [c for c in COMPANIES
              if _Z47_EXIT_BEFORE.get(c["ticker"], pd.Timestamp("2099-12-31")) >= today]
    ff_map = {c["ticker"]: c["mkt_cap_mn"] * c["float_pct"] / 100.0 for c in active}
    weights = _apply_iterative_cap(ff_map)

    # Fetch daily closes from last_date-7d to today+1 (covers gap days + base prices)
    dl_start = (last_date - pd.Timedelta(days=7)).strftime("%Y-%m-%d")
    dl_end = (today + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    yf_tks = [yf_ticker(c) for c in active] + ["^CRSLDX"]
    try:
        raw = yf.download(yf_tks, start=dl_start, end=dl_end,
                          auto_adjust=True, progress=False, threads=True)
        closes = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
        closes.index = pd.DatetimeIndex(closes.index).normalize()
    except Exception:
        closes = pd.DataFrame()

    # Base prices on last_date for each constituent
    base_px: dict = {}
    if not closes.empty:
        for c in active:
            col = yf_ticker(c)
            if col in closes.columns:
                avail = closes[col].loc[closes.index <= last_date].dropna()
                if not avail.empty:
                    base_px[c["ticker"]] = float(avail.iloc[-1])

    new_rows: list[dict] = []

    # Historical gap rows: last_date < day < today
    if not closes.empty:
        gap_days = closes.index[(closes.index > last_date) & (closes.index < today)]
        for dt in sorted(gap_days):
            n5_px = None
            if "^CRSLDX" in closes.columns:
                v = closes["^CRSLDX"].get(dt)
                if v is not None and not pd.isna(v):
                    n5_px = float(v)
            if n5_px is None or last_n5a <= 0:
                continue
            num = denom = 0.0
            for c in active:
                w = weights.get(c["ticker"], 0.0)
                p_b = base_px.get(c["ticker"])
                col = yf_ticker(c)
                p_n = None
                if col in closes.columns:
                    v = closes[col].get(dt)
                    if v is not None and not pd.isna(v):
                        p_n = float(v)
                if w == 0 or not p_b or p_b <= 0 or not p_n or p_n <= 0:
                    continue
                num += w * p_n / p_b
                denom += w
            if denom < 0.5:
                continue
            new_rows.append({
                "date": dt,
                "z47_float": round(last_z47 * num / denom, 6),
                "z47_mcap": round(last_z47 * num / denom, 6),
                "n500_indexed": round(last_n5i * n5_px / last_n5a, 4),
                "n500_abs": round(n5_px, 2),
            })

    # Today's intraday row via fast_info
    def _get_px(c):
        try:
            px = float(yf.Ticker(yf_ticker(c)).fast_info.last_price)
            return c["ticker"], px if px > 0.1 else None
        except Exception:
            return c["ticker"], None

    with ThreadPoolExecutor(max_workers=12) as ex:
        today_px = dict(ex.map(_get_px, active))

    n500_live = None
    try:
        n500_live = float(yf.Ticker("^CRSLDX").fast_info.last_price)
    except Exception:
        pass

    if n500_live and last_n5a > 0:
        num = denom = 0.0
        for c in active:
            w = weights.get(c["ticker"], 0.0)
            p_b = base_px.get(c["ticker"])
            p_n = today_px.get(c["ticker"])
            if w == 0 or not p_b or p_b <= 0 or not p_n or p_n <= 0:
                continue
            num += w * p_n / p_b
            denom += w
        if denom >= 0.5 and num > 0:
            new_rows.append({
                "date": today,
                "z47_float": round(last_z47 * num / denom, 6),
                "z47_mcap": round(last_z47 * num / denom, 6),
                "n500_indexed": round(last_n5i * n500_live / last_n5a, 4),
                "n500_abs": round(n500_live, 2),
            })

    if not new_rows:
        return df

    new_df = pd.DataFrame(new_rows).sort_values("date")
    result = pd.concat([df, new_df], ignore_index=True)
    result = result.drop_duplicates(subset=["date"], keep="last")
    return result.sort_values("date").reset_index(drop=True)


def _fetch_since_base() -> tuple:
    """Return (z47_since_pct, n500_since_pct) using the live-extended series."""
    try:
        df = _build_live_extended_df()
        last = df.iloc[-1]
        z_since = round(float(last["z47_float"]) - 100.0, 1)
        n_since = round(float(last["n500_indexed"]) - 100.0, 1)
        return z_since, n_since
    except Exception as _e:
        print(f"[gen] _fetch_since_base failed: {_e}")
        return None, None


def _fetch_1m_from_history() -> tuple:
    """Return (z47_1m_pct, n500_1m_pct) from the live-extended series.

    Uses today's intraday prices so the window end matches the app chart exactly."""
    try:
        df = _build_live_extended_df()
        last_date = df["date"].iloc[-1]
        cutoff = last_date - pd.DateOffset(months=1)
        sub = df[df["date"] >= cutoff]
        if sub.empty:
            return None, None
        z_base = float(sub["z47_float"].iloc[0])
        n_base = float(sub["n500_indexed"].iloc[0])
        z_last = float(df["z47_float"].iloc[-1])
        n_last = float(df["n500_indexed"].iloc[-1])
        z_1m = round((z_last / z_base - 1) * 100, 1) if z_base else None
        n_1m = round((n_last / n_base - 1) * 100, 1) if n_base else None
        return z_1m, n_1m
    except Exception as _e:
        print(f"[gen] _fetch_1m_from_history failed: {_e}")
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
    start_dt = (pd.Timestamp(today) - pd.DateOffset(months=1)).date()
    window   = f"{start_dt.day} {start_dt.strftime('%b')} – {today.day} {today.strftime('%b %Y')}"

    print("[gen] fetching 1M returns (canonical — matches _fetch_1m_returns)...")
    returns_1m = _fetch_returns_1m()

    print("[gen] fetching market context...")
    usdinr, _n500_ret_unused = _fetch_volume_and_context()

    print("[gen] fetching market caps...")
    mcaps = _fetch_mcaps()

    print("[gen] fetching since-base performance...")
    z_since, n_since = _fetch_since_base()

    print("[gen] fetching 1M z47/n500 from history CSV (same series as chart)...")
    _z_1m_csv, _n_1m_csv = _fetch_1m_from_history()

    name_map = {c["ticker"]: c["name"] for c in COMPANIES}

    def _wt(c):
        mc = mcaps.get(c["ticker"])
        if mc:
            v = mc.get("mc", 0)
            if mc.get("currency", "INR") != "INR":
                v *= usdinr
            return v
        return c.get("mkt_cap_mn", 0)

    # 1M returns for the bullet: from z47_history.csv (same source as chart header).
    # Fallback to float-weighted constituent average only if CSV read fails.
    if _z_1m_csv is not None and _n_1m_csv is not None:
        z_ret = _z_1m_csv
        n_ret = _n_1m_csv
    else:
        total_w = sum(_wt(c) for c in COMPANIES)
        _z_wt = 0.0
        if total_w > 0:
            for c in COMPANIES:
                r = returns_1m.get(c["ticker"])
                if r is not None:
                    _z_wt += r * _wt(c) / total_w
        z_ret = round(_z_wt, 1)
        n_ret = round(_n500_ret_unused, 1)
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
            f"{_bs_sign}, reflecting growing investor interest in AI-linked businesses."
        )

    _reason_bullet = ("Anchored in domestic demand and rising digital adoption, "
                      "the cohort remained resilient amid global headwinds.")

    _em  = '<em style="font-style:italic;text-transform:none">fortyseven</em>'
    if abs(spread) < 1.0:
        _monthly_tail = "broadly in line."
    elif spread > 0:
        _monthly_tail = f"leading by {round(abs(spread) * 100):.0f} bps."
    else:
        _monthly_tail = f"trailing by {round(abs(spread) * 100):.0f} bps."
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
            f"versus Nifty 500's {_n_sign}%, {_since_ahd} by {round(abs(_since_spread) * 100):.0f} bps."
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
         "header": "Index performance",
         "sub_bullets": s1},
        {"type": "main_bullet",
         "header": "Largest constituents ; the names that anchor the index - key drivers",
         "sub_bullets": s2},
        {"type": "main_bullet", "header": "Top gainers - key drivers",  "sub_bullets": s3},
        {"type": "main_bullet", "header": "Top laggards - key drivers", "sub_bullets": s4},
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
