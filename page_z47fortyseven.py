"""
Z47fortyseven — public-facing index page.

Architecture notes (critical for maintainers):
  - ALL visual styling uses INLINE style="..." attributes.
    Do NOT use <style> class-based injection — Streamlit Cloud's DOMPurify
    strips <style> tags but keeps their text content, causing CSS to render
    as visible body text (F1). Inline styles bypass DOMPurify entirely.
  - Background override uses st.html() (Streamlit 1.32+) or a very short
    <style> fallback — no CSS comments in that fallback.
  - No <div class="wrapper"> trick across multiple st.markdown calls —
    Streamlit closes each markdown container immediately, so the wrapper
    div never wraps anything. Styling MUST be per-element inline.
"""
from __future__ import annotations

import os
import re
import glob as _glob
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta, datetime, time as _time

import pandas as pd
import plotly.graph_objects as go
import pytz as _pytz
import streamlit as st
import yfinance as yf

# ── Timezone ──────────────────────────────────────────────────────────────────
# Streamlit Cloud runs in UTC. Always use _IST_TZ for user-facing timestamps.
_IST_TZ = _pytz.timezone("Asia/Kolkata")


def _now_ist() -> datetime:
    """Current time in IST (timezone-aware)."""
    return datetime.now(_IST_TZ)


def _now_ist_str(fmt: str = "%H:%M IST") -> str:
    return _now_ist().strftime(fmt)


def _is_market_hours() -> bool:
    """True if NSE market is currently open (Mon–Fri, 09:15–15:35 IST)."""
    now = _now_ist()
    if now.weekday() >= 5:   # Sat / Sun
        return False
    t = now.time()
    return _time(9, 15) <= t <= _time(15, 35)

from companies import COMPANIES, yf_ticker

try:
    from takeaway_constants import HARDCODED_INDEX_TAKEAWAY
except Exception:
    HARDCODED_INDEX_TAKEAWAY = {"text": "", "window": "", "updated": "", "icon": ""}

# ── Brand palette ─────────────────────────────────────────────────────────────
_OG  = "#FF6B1A"
_BLK = "#0A0A0A"
_DGR = "#4A4A4A"
_LGR = "#888888"
_BRD = "#E8E8E8"
_GRN = "#1F8A50"
_RED = "#D14343"
_WHT = "#FFFFFF"
_F   = "font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif"

# Inline style shortcuts
def _lbl(extra=""):
    """Section label style."""
    return (f"font-size:11px;font-weight:700;letter-spacing:0.09em;"
            f"text-transform:uppercase;color:{_OG};margin:0 0 6px;{_F};{extra}")

def _card_wrap(extra=""):
    return (f"background:{_WHT};border:1px solid {_BRD};border-radius:8px;"
            f"padding:20px 24px;{extra}")

# ─────────────────────────────────────────────────────────────────────────────
# Data helpers — self-contained, no app.py imports
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)   # 1-hr TTL — matches "updated hourly" claim
def _live_indices() -> tuple:
    n500 = usdinr = fx_chg = None
    try:    n500   = round(float(yf.Ticker("^CRSLDX").fast_info.last_price), 2)
    except: pass
    try:
        fxt   = yf.Ticker("USDINR=X")
        usdinr = round(float(fxt.fast_info.last_price), 2)
        fxh    = fxt.history(period="2d")
        if len(fxh) >= 2:
            prev   = float(fxh["Close"].iloc[-2])
            fx_chg = round((usdinr / prev - 1) * 100, 2) if prev else None
    except:
        usdinr = 85.0
    return n500, usdinr or 85.0, fx_chg


@st.cache_data(ttl=3600, show_spinner=False)
def _load_history() -> pd.DataFrame:
    csv = os.path.join(os.path.dirname(__file__), "z47_history.csv")
    df  = pd.read_csv(csv, parse_dates=["date"])
    return df.sort_values("date").reset_index(drop=True)


def _extend_history(hist: pd.DataFrame, n500_live) -> pd.DataFrame:
    """Fill all missing trading days via yfinance ratio-scaling."""
    last      = hist.iloc[-1]
    today     = pd.Timestamp.today().normalize()
    last_date = pd.Timestamp(last["date"]).normalize()
    if last_date >= today:
        return hist
    nb_base = float(last.get("n500_abs")  or 0)
    z47_b   = float(last["z47_float"])
    ni_b    = float(last["n500_indexed"])
    z47mc_b = float(last.get("z47_mcap") or z47_b)
    new_rows: list[dict] = []
    try:
        s  = (last_date + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        e  = (today     + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        nf = yf.download("^CRSLDX", start=s, end=e, progress=False, auto_adjust=True)
        def _cls(d):
            if d.empty: return pd.Series(dtype=float)
            if isinstance(d.columns, pd.MultiIndex): return d["Close"].squeeze()
            return d["Close"].squeeze() if "Close" in d.columns else d.iloc[:, 0]
        nfc = _cls(nf)
        for dt in nfc.index:
            dn = pd.Timestamp(dt).normalize()
            if dn <= last_date: continue
            nb_new = float(nfc.loc[dt])
            if not nb_new or not nb_base: continue
            r = nb_new / nb_base
            new_rows.append({"date": dn,
                "z47_float": round(z47_b*r,4), "z47_mcap": round(z47mc_b*r,4),
                "n500_indexed": round(ni_b*r,4),
                "n500_abs": round(nb_new,2)})
    except Exception as _e:
        print(f"[z47fs extend_history] {_e}")
    if not new_rows:
        ratio = (n500_live / nb_base) if nb_base and n500_live else 1.0
        new_rows = [{"date": today, "z47_float": round(z47_b*ratio,4),
            "z47_mcap": round(z47mc_b*ratio,4),
            "n500_indexed": round(ni_b*ratio,4),
            "n500_abs": n500_live or nb_base}]
    return pd.concat([hist, pd.DataFrame(new_rows).sort_values("date")], ignore_index=True)


@st.cache_data(ttl=3600, show_spinner=False)   # 1-hr TTL — constituent prices
def _fetch_price(symbol: str, exchange: str) -> dict:
    """Live price: fast_info → history(5d) → {}."""
    tk = symbol + ".NS" if exchange == "NSE" else symbol
    try:
        fi = yf.Ticker(tk).fast_info
        px = float(fi.last_price)
        if px and px > 0.1:
            pc  = float(getattr(fi, "previous_close", 0) or 0)
            pct = round((px / pc - 1) * 100, 2) if pc > 0 else None
            return {"price": px, "pct_change": pct}
    except Exception:
        pass
    try:
        h = yf.Ticker(tk).history(period="5d")
        if not h.empty:
            px = float(h["Close"].iloc[-1])
            pc = float(h["Close"].iloc[-2]) if len(h) >= 2 else None
            return {"price": px, "pct_change": round((px/pc-1)*100,2) if pc and pc > 0 else None}
    except Exception:
        pass
    return {}


@st.cache_data(ttl=3600, show_spinner=False)   # 1-hr TTL — 1M returns
def _fetch_1m_returns() -> dict[str, float]:
    """1-calendar-month returns for all 47 companies, NaN-safe."""
    tickers = [yf_ticker(c) for c in COMPANIES]
    tk_map  = {yf_ticker(c): c["ticker"] for c in COMPANIES}
    try:
        raw    = yf.download(tickers, period="50d", progress=False, auto_adjust=True)
        closes = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
        if closes.empty:
            return {}
        target = date.today() - timedelta(days=30)
        valid_i = [i for i, d in enumerate(closes.index) if d.date() >= target]
        if not valid_i:
            return {}
        base_i = valid_i[0]
        result: dict[str, float] = {}
        for yftk in closes.columns:
            z47tk = tk_map.get(yftk)
            if not z47tk:
                continue
            s = closes[yftk].dropna()
            if len(s) < base_i + 1:
                continue
            b = float(s.iloc[base_i])
            e_val = float(s.iloc[-1])
            if b and b > 0 and not pd.isna(b) and not pd.isna(e_val):
                result[z47tk] = round((e_val / b - 1) * 100, 2)
        return result
    except Exception as _e:
        print(f"[z47fs 1m_returns ERROR] {_e}")
        return {}


@st.cache_data(ttl=3600, show_spinner=False)   # 1-hr TTL — market caps
def _fetch_mcaps() -> dict:
    """Live market caps for all 47 companies."""
    def _get(c):
        try:
            fi = yf.Ticker(yf_ticker(c)).fast_info
            mc = getattr(fi, "market_cap", None)
            if mc and mc > 0:
                return c["ticker"], {"mc": mc/1e6, "currency": "INR" if c["exchange"]=="NSE" else "USD"}
        except Exception:
            pass
        return c["ticker"], None
    out = {}
    with ThreadPoolExecutor(max_workers=12) as ex:
        for tk, mc in ex.map(_get, COMPANIES):
            if mc: out[tk] = mc
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Utility helpers
# ─────────────────────────────────────────────────────────────────────────────

def _pct_since(df: pd.DataFrame, col: str,
               days: int | None = None, ytd: bool = False,
               all_time: bool = False) -> float | None:
    if df.empty: return None
    last = df[col].iloc[-1]
    if all_time:
        sub = df
    elif ytd:
        yr  = df["date"].iloc[-1].year
        sub = df[df["date"] >= pd.Timestamp(yr, 1, 1)]
    elif days:
        cut = df["date"].iloc[-1] - pd.Timedelta(days=days)
        sub = df[df["date"] >= cut]
    else:
        return None
    if sub.empty: return None
    base = sub[col].iloc[0]
    return round((last / base - 1) * 100, 2) if base and base != 0 else None


def _period_kw(period: str) -> dict:
    if period == "All": return {"all_time": True}
    if period == "YTD": return {"ytd": True}
    return {"days": {"1M": 30, "3M": 90, "6M": 180, "1Y": 365}[period]}


def _delta_html(v, suffix="%", size=13):
    if v is None:
        return f'<span style="color:{_LGR};font-size:{size}px">—</span>'
    c    = _GRN if v >= 0 else _RED
    sign = "+" if v > 0 else ""
    return (f'<span style="color:{c};font-size:{size}px;'
            f'font-weight:500;{_F}">{sign}{v:.1f}{suffix}</span>')


def _chg_cell(v):
    if v is None:
        return f'<span style="color:{_LGR}">—</span>'
    c    = _GRN if v >= 0 else _RED
    sign = "+" if v > 0 else ""
    return f'<span style="color:{c};font-weight:600">{sign}{v:.1f}%</span>'


def _divider():
    st.markdown(
        f'<hr style="border:none;border-top:1px solid {_BRD};margin:40px 0">',
        unsafe_allow_html=True,
    )


def _hero_band() -> None:
    """Full hero band — repeated verbatim before each of the 4 sections."""
    st.markdown(
        f'<div style="border-top:1.5px solid {_OG};border-bottom:1.5px solid {_OG};'
        f'padding:28px 0;display:flex;flex-direction:column;gap:28px">'
        f'<h1 style="margin:0;padding:0;font-size:28px;font-weight:800;'
        f'color:{_BLK};letter-spacing:-0.02em;line-height:1.1;{_F}">'
        f'Z47^<em style="font-style:italic">fortyseven</em></h1>'
        f'<p style="margin:0;padding:0;font-size:28px;font-weight:600;'
        f'color:{_OG};line-height:1.25;{_F}">'
        f"Powering India&#x2019;s journey to a developed nation by 2047"
        f'</p>'
        f'<p style="margin:0;padding:0;font-size:15px;font-weight:400;'
        f'font-style:italic;color:{_BLK};line-height:1.5;{_F}">'
        f'Tracking 47 listed Indian new-age technology, consumer and new-economy '
        f'financial-services companies'
        f'</p>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _section_label(label: str) -> None:
    """Orange small-caps section label — 24px top margin after hero band."""
    st.markdown(
        f'<p style="font-size:13px;font-weight:700;letter-spacing:0.05em;'
        f'text-transform:uppercase;color:{_OG};margin:24px 0 20px;{_F}">{label}</p>',
        unsafe_allow_html=True,
    )


def _section_spacer() -> None:
    """80px gap between sections."""
    st.markdown('<div style="height:80px"></div>', unsafe_allow_html=True)


def _s_kissht_takeaway() -> None:
    """Kissht IPO Takeaway — structured, from takeaway_constants.HARDCODED_IPO_TAKEAWAYS."""
    tk_data = None
    try:
        from takeaway_constants import HARDCODED_IPO_TAKEAWAYS as _IPO_TK
        tk_data = _IPO_TK.get("KISSHT")
    except Exception as _e:
        print(f"[z47fs kissht_takeaway] {_e}")
    if not tk_data:
        return

    sections   = tk_data.get("sections", [])
    sec_label  = tk_data.get("section_label", "KISSHT IPO TAKEAWAY")
    date_label = tk_data.get("date_range_label", "")
    full_label = f"{sec_label} · {date_label}" if date_label else sec_label

    # 24px gap between Monthly Takeaway and Kissht block
    st.markdown(
        f'<div style="height:24px"></div>'
        f'<p style="{_lbl()}">{full_label}</p>',
        unsafe_allow_html=True,
    )
    if not sections:
        return

    body_html        = ""
    is_first_section = True

    for sec in sections:
        stype   = sec.get("type", "main_bullet")
        header  = sec.get("header", "")
        sub_bul = sec.get("sub_bullets", [])

        if stype == "section_title":
            body_html += (
                f'<div style="margin-top:32px">'
                f'<p style="margin:0 0 10px;font-size:11px;font-weight:700;'
                f'letter-spacing:0.08em;text-transform:uppercase;color:{_OG};{_F}">'
                f'{_process_bold(header)}</p>'
            )
            for sb in sub_bul:
                body_html += (
                    f'<div style="position:relative;padding-left:14px;margin-bottom:7px">'
                    f'<span style="position:absolute;left:0;top:6px;color:{_BLK};'
                    f'font-size:8px;line-height:1">&#9679;</span>'
                    f'<p style="margin:0;font-size:14px;line-height:1.65;'
                    f'font-weight:500;color:{_BLK};{_F}">{_process_bold(sb)}</p>'
                    f'</div>'
                )
            body_html += '</div>'
        else:
            mt = "0" if is_first_section else "22px"
            if " ; " in header:
                lbl_part, verd_part = header.split(" ; ", 1)
                hdr_html = (
                    f'<span style="font-weight:700;color:{_BLK}">{_process_bold(lbl_part)}</span>'
                    f'<span style="color:{_LGR}"> &nbsp;·&nbsp; </span>'
                    f'<span style="font-weight:500;color:{_BLK}">{_process_bold(verd_part)}</span>'
                )
            else:
                hdr_html = (
                    f'<span style="font-weight:700;color:{_BLK}">'
                    f'{_process_bold(header)}</span>'
                )
            body_html += (
                f'<div style="margin-top:{mt}">'
                f'<p style="margin:0 0 7px;font-size:14px;line-height:1.5;{_F}">'
                f'<span style="color:{_OG};font-weight:800;font-size:16px;'
                f'margin-right:8px;line-height:1.2">•</span>'
                f'{hdr_html}</p>'
            )
            for j, sb in enumerate(sub_bul):
                mt_sb = "0" if j == 0 else "5px"
                body_html += (
                    f'<div style="position:relative;margin:{mt_sb} 0 0 24px;padding-left:14px">'
                    f'<span style="position:absolute;left:0;top:6px;color:{_BLK};'
                    f'font-size:8px;line-height:1">&#9679;</span>'
                    f'<p style="margin:0;font-size:13.5px;line-height:1.65;'
                    f'color:{_DGR};font-weight:400;{_F}">{_process_bold(sb)}</p>'
                    f'</div>'
                )
            body_html += '</div>'

        is_first_section = False

    st.markdown(
        f'<div style="border-top:2px solid {_OG};border-bottom:1px solid {_BRD};'
        f'background:{_WHT};padding:28px 32px 24px;margin:8px 0">'
        f'{body_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def _slim_footer() -> None:
    """Slim centered disclaimer footer at page bottom."""
    st.markdown(
        f'<div style="text-align:center">'
        f'<div style="border-top:1px solid {_OG};margin-bottom:32px"></div>'
        f'<p style="font-size:12px;color:{_LGR};margin:0;{_F}">'
        f'For informational purposes only. Not investment advice. &copy; 2026 Z47.'
        f'</p>'
        f'<div style="height:32px"></div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Weekly refresh check
# ─────────────────────────────────────────────────────────────────────────────

def _maybe_refresh_weekly() -> None:
    """Clear AI-content disk caches once per week (Monday-keyed). Idempotent."""
    try:
        today   = date.today()
        monday  = today - timedelta(days=today.weekday())
        flagdir = "/tmp/z47_cache"
        os.makedirs(flagdir, exist_ok=True)
        flag_path = os.path.join(flagdir, "weekly_refresh.txt")

        last_refresh = date(2000, 1, 1)
        if os.path.exists(flag_path):
            try:
                last_refresh = date.fromisoformat(open(flag_path).read().strip())
            except Exception:
                pass

        if last_refresh >= monday:
            return  # Already refreshed this week

        for pattern in ["idx_tk_*.pkl", "val_tk_*.pkl", "sec_tk_*.pkl"]:
            for fp in _glob.glob(os.path.join(flagdir, pattern)):
                try: os.remove(fp)
                except Exception: pass

        with open(flag_path, "w") as fh:
            fh.write(monday.isoformat())
        now_str = _now_ist_str("%Y-%m-%d %H:%M IST")
        print(f"[REFRESH {now_str}] Weekly AI content caches cleared — will regenerate on next view")
    except Exception as _e:
        print(f"[z47fs weekly_refresh] {_e}")


# ─────────────────────────────────────────────────────────────────────────────
# Section renderers — ALL inline styles, no CSS class dependencies
# ─────────────────────────────────────────────────────────────────────────────

def _render_header_bar(df: pd.DataFrame, usdinr: float,
                       fetch_ts: str | None = None,
                       fetch_age_s: float | None = None) -> bool:
    """
    Data-freshness strip + inline refresh button.
    Returns True if the refresh button was clicked (caller handles cache clear + rerun).
    Colors:
      green  = fresh (< 3 min)
      orange = approaching stale (3–10 min)
      red    = stale (> 10 min)
    """
    try:
        last_dt  = df["date"].max()
        age_days = (pd.Timestamp.today().normalize() - last_dt).days
        idx_col  = _GRN if age_days <= 1 else (_OG if age_days <= 3 else _RED)
        idx_lbl  = "today" if age_days <= 1 else last_dt.strftime("%d %b")
    except Exception:
        idx_col, idx_lbl = _LGR, "unknown"

    tk_updated = HARDCODED_INDEX_TAKEAWAY.get("updated", "—")

    # Price freshness color
    if fetch_age_s is None:
        price_col = _LGR
        price_lbl = fetch_ts or _now_ist_str()
    elif fetch_age_s < 180:       # < 3 min
        price_col = _GRN
        price_lbl = fetch_ts or _now_ist_str()
    elif fetch_age_s < 600:       # 3–10 min
        price_col = _OG
        age_m = int(fetch_age_s // 60)
        price_lbl = f"{fetch_ts} ({age_m}m ago)"
    else:                          # > 10 min — STALE
        price_col = _RED
        age_m = int(fetch_age_s // 60)
        price_lbl = f"STALE — {fetch_ts} ({age_m}m ago)"

    mh_dot = (f'<span style="color:{_GRN};font-size:8px">●</span>&nbsp;MARKET OPEN&nbsp;·&nbsp;'
              if _is_market_hours() else "")

    badge_html = (
        f'<div style="font-size:10px;color:{_LGR};padding:2px 0 8px;{_F}">'
        f'{mh_dot}'
        f'<b style="color:{_DGR}">DATA</b>'
        f'&nbsp;·&nbsp;<span style="color:{idx_col}">Index: {idx_lbl}</span>'
        f'&nbsp;·&nbsp;Prices:&nbsp;<span style="color:{price_col}">{price_lbl}</span>'
        f'&nbsp;·&nbsp;FX: &#8377;{usdinr:.2f}'
        f'&nbsp;·&nbsp;Takeaway: {tk_updated}'
        f'</div>'
    )

    # Inline refresh button — sits to the right of the badge on the same row
    _badge_col, _btn_col = st.columns([22, 1])
    with _badge_col:
        st.markdown(badge_html, unsafe_allow_html=True)
    with _btn_col:
        return bool(st.button("🔄", key="z47fs_force_refresh",
                              help="Force refresh — fetch latest data now"))


def _s1_hero(df: pd.DataFrame, n500_live, usdinr, fx_chg) -> None:
    """Section 1 — kept for API compatibility but rendering is done inside _s2_performance."""
    pass


def _s2_performance(df: pd.DataFrame, n500_live=None, usdinr: float = 85.0,
                    fx_chg=None) -> None:
    """Section 2 — horizontal stat strip on top, full-width chart below."""
    _em       = '<em style="font-style:italic;text-transform:none">fortyseven</em>'
    _idx_html = f'Z47^{_em}'
    _idx_vs   = f'Z47^{_em} VS NIFTY&nbsp;500'

    st.markdown(
        f'<p style="{_lbl()}">INDEX PERFORMANCE</p>'
        f'<h2 style="font-size:22px;font-weight:700;color:{_BLK};'
        f'margin:0 0 16px;{_F}">Rebased to 100 · 1 January 2024</h2>',
        unsafe_allow_html=True,
    )

    period = st.radio("Period", ["All", "1M", "3M", "6M", "1Y", "YTD"],
                      index=0, horizontal=True, label_visibility="collapsed",
                      key="z47fs_period")

    # ── Slice & rebase ─────────────────────────────────────────────────────────
    if period == "All":
        plot = df.copy()
    elif period == "YTD":
        yr   = df["date"].iloc[-1].year
        plot = df[df["date"] >= pd.Timestamp(yr, 1, 1)].copy()
    else:
        days = {"1M": 30, "3M": 90, "6M": 180, "1Y": 365}[period]
        cut  = df["date"].iloc[-1] - pd.Timedelta(days=days)
        plot = df[df["date"] >= cut].copy()

    if not plot.empty:
        base = plot.iloc[0]
        for col in ["z47_float", "n500_indexed"]:
            plot[col] = plot[col] / base[col] * 100

    # ── Period-responsive return figures ──────────────────────────────────────
    kw    = _period_kw(period)
    z47_r = _pct_since(df, "z47_float",    **kw)
    n5_r  = _pct_since(df, "n500_indexed", **kw)

    def _sign(v): return (f"+{v:.1f}%" if v >= 0 else f"{v:.1f}%") if v is not None else "—"
    def _cc(v):   return (_GRN if v >= 0 else _RED) if v is not None else _LGR

    _pl_s = (f"font-size:11px;font-weight:600;letter-spacing:0.08em;"
             f"text-transform:uppercase;color:{_LGR};margin:0 0 2px;{_F}")
    _pv_s = f"font-size:20px;font-weight:700;margin:0;line-height:1.1;{_F}"
    st.markdown(
        f'<div style="display:flex;gap:40px;padding:4px 0 16px;align-items:flex-start">'
        f'<div><p style="{_pl_s}">{_idx_html}</p>'
        f'<p style="{_pv_s};color:{_cc(z47_r)}">{_sign(z47_r)}</p></div>'
        f'<div><p style="{_pl_s}">Nifty 500</p>'
        f'<p style="{_pv_s};color:{_cc(n5_r)}">{_sign(n5_r)}</p></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Stat block data ────────────────────────────────────────────────────────
    last    = df.iloc[-1]
    now_ts  = _now_ist_str()
    z47_v   = float(last["z47_float"])
    z47_all = _pct_since(df, "z47_float",    all_time=True)
    n5_all  = _pct_since(df, "n500_indexed", all_time=True)
    spread  = round(z47_all - n5_all, 1) if z47_all is not None and n5_all is not None else None
    s_str   = (f"+{spread:.1f}% ahead" if spread and spread >= 0
               else (f"{spread:.1f}% behind" if spread is not None else "—"))
    s_color = _GRN if (spread or 0) >= 0 else _RED

    n5_str = f"{n500_live:,.0f}" if n500_live else "—"
    fx_str = f"₹{usdinr:.2f}" if usdinr else "—"
    z47_d  = _delta_html(z47_all, suffix="%", size=14)
    n5_d   = _delta_html(n5_all,  suffix="%", size=14)
    fx_d   = _delta_html(fx_chg,  suffix="%", size=14)

    # ── Horizontal stat strip — 4 equal columns, full width ───────────────────
    _cp    = (f"background:{_WHT};border:1px solid {_BRD};border-radius:8px;"
              f"padding:20px 16px;display:flex;flex-direction:column;gap:5px")
    _lc    = (f"font-size:10px;font-weight:700;letter-spacing:0.08em;"
              f"text-transform:uppercase;color:{_OG};{_F}")
    _lc_vs = (f"font-size:9px;font-weight:700;letter-spacing:0.06em;"
              f"text-transform:uppercase;color:{_OG};{_F}")
    _vc    = (f"font-size:30px;font-weight:800;color:{_BLK};"
              f"line-height:1.05;white-space:nowrap;{_F}")
    _sc    = f"font-size:11px;color:{_LGR};{_F}"

    st.markdown(
        f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;'
        f'gap:12px;margin-bottom:20px">'
        # Card 1 — Z47^fortyseven
        f'<div style="{_cp}">'
        f'<div style="{_lc}">{_idx_html}</div>'
        f'<div style="{_vc}">{z47_v:.1f}</div>'
        f'{z47_d}'
        f'<div style="{_sc}">Since Jan 2024</div>'
        f'</div>'
        # Card 2 — Nifty 500
        f'<div style="{_cp}">'
        f'<div style="{_lc}">Nifty 500</div>'
        f'<div style="{_vc}">{n5_str}</div>'
        f'{n5_d}'
        f'<div style="{_sc}">Since Jan 2024</div>'
        f'</div>'
        # Card 3 — Z47^fortyseven vs Nifty 500
        f'<div style="{_cp}">'
        f'<div style="{_lc_vs}">{_idx_vs}</div>'
        f'<div style="font-size:22px;font-weight:700;color:{s_color};'
        f'white-space:nowrap;line-height:1.1;{_F}">{s_str}</div>'
        f'<div style="font-size:12px;color:{_DGR};{_F}">Since 1 Jan 2024</div>'
        f'<div style="{_sc}">Cumulative return spread</div>'
        f'</div>'
        # Card 4 — USD / INR
        f'<div style="{_cp}">'
        f'<div style="{_lc}">USD / INR</div>'
        f'<div style="{_vc}">{fx_str}</div>'
        f'{fx_d}'
        f'<div style="{_sc}">Daily change · {now_ts}</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Period-specific axis config — full-width chart, larger fonts ───────────
    _tf = dict(family="Inter", color="#4A4A4A")
    if period == "All":
        _x_end = plot["date"].max().strftime("%Y-%m-%d") if not plot.empty else "2026-12-31"
        _x_kw = dict(dtick="M3", tick0="2024-01-01", tickformat="%b %Y",
                     range=["2023-12-15", _x_end],
                     tickfont=dict(size=12, **_tf))
        _y_kw = dict(range=[98, 152], dtick=10, tick0=100,
                     tickfont=dict(size=12, **_tf))
    elif period == "1Y":
        _x_kw = dict(dtick="M2", tickformat="%b %Y", tickfont=dict(size=12, **_tf))
        _y_kw = dict(tickfont=dict(size=12, **_tf))
    elif period in ("6M", "YTD", "3M"):
        _x_kw = dict(dtick="M1", tickformat="%b %Y", tickfont=dict(size=12, **_tf))
        _y_kw = dict(tickfont=dict(size=12, **_tf))
    else:  # 1M
        _x_kw = dict(tickformat="%d %b", tickfont=dict(size=12, **_tf))
        _y_kw = dict(tickfont=dict(size=12, **_tf))

    # ── Build chart ────────────────────────────────────────────────────────────
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=plot["date"], y=plot["z47_float"],
        name="Z47^fortyseven", mode="lines",
        line=dict(color=_OG, width=2.5),
        hovertemplate="%{x|%d %b %Y} · Z47: %{y:.1f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=plot["date"], y=plot["n500_indexed"],
        name="Nifty 500", mode="lines",
        line=dict(color="#1F77B4", width=1.8),
        hovertemplate="%{x|%d %b %Y} · Nifty 500: %{y:.1f}<extra></extra>"))
    fig.update_layout(
        paper_bgcolor=_WHT, plot_bgcolor=_WHT, height=360, hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.0,
                    xanchor="right", x=1, bgcolor="rgba(255,255,255,0.9)",
                    font=dict(size=13, color=_DGR, family="Inter")),
        xaxis=dict(showgrid=False, linecolor=_BRD, linewidth=1, showline=True, **_x_kw),
        yaxis=dict(showgrid=True, gridcolor="#F5F5F5", showline=False, **_y_kw),
        margin=dict(l=0, r=0, t=8, b=0),
        transition_duration=0,
    )

    # ── Full-width chart ───────────────────────────────────────────────────────
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    try:
        last_dt  = df["date"].max()
        age_days = (pd.Timestamp.today().normalize() - last_dt).days
        msg      = f"Index history through: {last_dt.strftime('%d %b %Y')} · auto-updates daily"
        if age_days > 3:
            msg += f" · ⚠️ {age_days} days old, check logs"
        st.caption(msg)
    except Exception:
        pass


def _s3_returns(df: pd.DataFrame) -> None:
    """Section 3 — Returns heatmap matrix, fully inline-styled."""
    st.markdown(f'<p style="{_lbl()}">RETURNS SUMMARY</p>', unsafe_allow_html=True)

    periods = [
        ("1M",            {"days": 30}),
        ("3M",            {"days": 90}),
        ("6M",            {"days": 180}),
        ("1Y",            {"days": 365}),
        ("YTD",           {"ytd": True}),
        ("Since Jan 2024", {"all_time": True}),
    ]
    rows_cfg = [
        ('Z47^<em style="font-style:italic">fortyseven</em>', "z47_float"),
        ("Nifty 500",      "n500_indexed"),
    ]

    th_s  = (f"padding:10px 16px;text-align:center;font-size:11px;font-weight:600;"
             f"letter-spacing:0.05em;color:{_LGR};background:{_WHT};"
             f"border-bottom:1px solid {_BRD};text-transform:uppercase;{_F}")
    th_l  = f"text-align:left;{th_s};min-width:150px"
    tbl   = (f'<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse">'
             f'<thead><tr><th style="{th_l}"></th>')
    for lbl, _ in periods:
        tbl += f'<th style="{th_s}">{lbl}</th>'
    tbl += "</tr></thead><tbody>"
    for idx_name, col in rows_cfg:
        tbl += (f'<tr><td style="padding:14px 16px;font-size:14px;font-weight:700;'
                f'color:{_BLK};border-bottom:1px solid {_BRD};white-space:nowrap;{_F}">'
                f'{idx_name}</td>')
        for _, kw in periods:
            v  = _pct_since(df, col, **kw)
            vs = (f"+{v:.1f}%" if v > 0 else f"{v:.1f}%") if v is not None else "—"
            # No background tint — signal carried entirely by text colour
            tc = _GRN if (v or 0) > 0 else (_RED if (v or 0) < 0 else _LGR)
            tbl += (f'<td style="padding:14px 16px;text-align:center;font-weight:700;'
                    f'font-size:15px;background:{_WHT};color:{tc};'
                    f'border-bottom:1px solid {_BRD};{_F}">{vs}</td>')
        tbl += "</tr>"
    tbl += "</tbody></table>"
    st.markdown(tbl, unsafe_allow_html=True)


def _process_bold(text: str) -> str:
    """Convert **text** markers to inline <strong> HTML (used in takeaway renderer)."""
    return re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)


def _s4_takeaway() -> None:
    """Section 4 — Monthly takeaway, structured multi-section renderer."""
    tk       = HARDCODED_INDEX_TAKEAWAY
    window   = tk.get("window", "")
    updated  = tk.get("updated", "")
    sections = tk.get("sections")

    st.markdown(
        f'<p style="{_lbl()}">MONTHLY TAKEAWAY'
        f'{(" · " + window.upper()) if window else ""}</p>',
        unsafe_allow_html=True,
    )

    # ── Legacy flat-bullet fallback (no sections key) ──────────────────────────
    if not sections:
        text    = tk.get("text", "")
        bullets = [ln.strip() for ln in text.splitlines() if ln.strip().startswith("•")]
        if not bullets:
            st.markdown(f'<p style="color:{_DGR};{_F}">{text}</p>', unsafe_allow_html=True)
            return
        items_html = ""
        for i, b in enumerate(bullets):
            content = b.lstrip("•").strip()
            weight  = "600" if i == 0 else "400"
            mt      = "0" if i == 0 else "10px"
            items_html += (
                f'<li style="margin-top:{mt};list-style:none;padding-left:18px;'
                f'position:relative;font-weight:{weight};line-height:1.65;color:{_BLK};{_F}">'
                f'<span style="position:absolute;left:0;color:{_OG};'
                f'font-weight:800;font-size:16px;line-height:1.2">•</span>'
                f'{content}</li>'
            )
        _today    = date.today()
        _fwd      = (7 - _today.weekday()) % 7 or 7
        _next_mon = _today + timedelta(days=_fwd)
        _next_str = f"Monday {_next_mon.day} {_next_mon.strftime('%b')}"
        st.markdown(
            f'<div style="border-top:2px solid {_OG};border-bottom:1px solid {_BRD};'
            f'background:{_WHT};padding:28px 32px 24px;margin:8px 0">'
            f'<ul style="margin:0;padding:0">{items_html}</ul>'
            f'</div>'
            f'<p style="font-size:11px;color:{_LGR};margin-top:7px;{_F}">'
            f'Last updated: {updated} &nbsp;·&nbsp; Next refresh: {_next_str}</p>',
            unsafe_allow_html=True,
        )
        return

    # ── Structured sections renderer ───────────────────────────────────────────
    _today    = date.today()
    _fwd      = (7 - _today.weekday()) % 7 or 7
    _next_mon = _today + timedelta(days=_fwd)
    _next_str = f"Monday {_next_mon.day} {_next_mon.strftime('%b')}"

    body_html        = ""
    is_first_section = True

    for sec in sections:
        stype   = sec.get("type", "main_bullet")
        header  = sec.get("header", "")
        sub_bul = sec.get("sub_bullets", [])

        if stype == "section_title":
            # "Net Read" — orange small-caps label + sub-bullets (no divider line)
            body_html += (
                f'<div style="margin-top:32px">'
                f'<p style="margin:0 0 10px;font-size:11px;font-weight:700;'
                f'letter-spacing:0.08em;text-transform:uppercase;color:{_OG};{_F}">'
                f'{_process_bold(header)}</p>'
            )
            for sb in sub_bul:
                body_html += (
                    f'<div style="position:relative;padding-left:14px;margin-bottom:7px">'
                    f'<span style="position:absolute;left:0;top:6px;color:{_BLK};'
                    f'font-size:8px;line-height:1">&#9679;</span>'
                    f'<p style="margin:0;font-size:14px;line-height:1.65;'
                    f'font-weight:500;color:{_BLK};{_F}">{_process_bold(sb)}</p>'
                    f'</div>'
                )
            body_html += '</div>'

        else:
            # main_bullet: orange • + header (split at " ; " for label/verdict styling)
            mt = "0" if is_first_section else "22px"
            if " ; " in header:
                lbl_part, verd_part = header.split(" ; ", 1)
                hdr_html = (
                    f'<span style="font-weight:700;color:{_BLK}">'
                    f'{_process_bold(lbl_part)}</span>'
                    f'<span style="color:{_LGR}"> &nbsp;·&nbsp; </span>'
                    f'<span style="font-weight:500;color:{_BLK}">'
                    f'{_process_bold(verd_part)}</span>'
                )
            else:
                hdr_html = (
                    f'<span style="font-weight:700;color:{_BLK}">'
                    f'{_process_bold(header)}</span>'
                )
            body_html += (
                f'<div style="margin-top:{mt}">'
                f'<p style="margin:0 0 7px;font-size:14px;line-height:1.5;{_F}">'
                f'<span style="color:{_OG};font-weight:800;font-size:16px;'
                f'margin-right:8px;line-height:1.2">•</span>'
                f'{hdr_html}</p>'
            )
            for j, sb in enumerate(sub_bul):
                mt_sb = "0" if j == 0 else "5px"
                body_html += (
                    f'<div style="position:relative;margin:{mt_sb} 0 0 24px;padding-left:14px">'
                    f'<span style="position:absolute;left:0;top:6px;color:{_BLK};'
                    f'font-size:8px;line-height:1">&#9679;</span>'
                    f'<p style="margin:0;font-size:13.5px;line-height:1.65;'
                    f'color:{_DGR};font-weight:400;{_F}">{_process_bold(sb)}</p>'
                    f'</div>'
                )
            body_html += '</div>'

        is_first_section = False

    st.markdown(
        f'<div style="border-top:2px solid {_OG};border-bottom:1px solid {_BRD};'
        f'background:{_WHT};padding:28px 32px 24px;margin:8px 0">'
        f'{body_html}'
        f'</div>'
        f'<p style="font-size:11px;color:{_LGR};margin-top:7px;{_F}">'
        f'Last updated: {updated} &nbsp;·&nbsp; Next refresh: {_next_str}</p>',
        unsafe_allow_html=True,
    )


def _s5_movers(returns_1m: dict, name_map: dict) -> None:
    """Section 5 — Top 5 gainers & losers: card wrapper, no ticker column."""
    st.markdown(f'<p style="{_lbl()}">TOP MOVERS · LAST MONTH</p>', unsafe_allow_html=True)

    valid  = {t: v for t, v in returns_1m.items() if v is not None and not pd.isna(v)}
    top5g  = sorted(valid.items(), key=lambda x: -x[1])[:5]
    top5l  = sorted(valid.items(), key=lambda x:  x[1])[:5]

    def _table_html(items, title, color):
        rows = "".join(
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:16px 0;border-bottom:1px solid #F0F0F0">'
            f'<span style="font-size:15px;font-weight:500;color:{_BLK};{_F}">'
            f'{name_map.get(tk, tk)}</span>'
            f'<span style="font-size:17px;font-weight:700;color:{color};{_F}">'
            f'{"+" if pct>=0 else ""}{pct:.1f}%</span>'
            f'</div>'
            for tk, pct in items
        )
        return (
            f'<div style="{_card_wrap("height:100%")}">'
            f'<div style="font-size:18px;font-weight:700;color:{_BLK};'
            f'margin-bottom:4px;{_F}">{title}</div>'
            f'<div style="font-size:10px;font-weight:700;letter-spacing:0.08em;'
            f'text-transform:uppercase;color:{_LGR};margin-bottom:20px;{_F}">'
            f'1 MONTH RETURN</div>'
            f'{rows}</div>'
        )

    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown(_table_html(top5g, "Top Gainers", _GRN), unsafe_allow_html=True)
    with c2:
        st.markdown(_table_html(top5l, "Top Losers",  _RED), unsafe_allow_html=True)


def _s6_1m_chart(returns_1m: dict, name_map: dict) -> None:
    """Section 6 — 1-Month chart all 47. Fully guarded against bad data."""
    st.markdown(
        f'<p style="{_lbl()}">1-MONTH PRICE MOVEMENT · ALL CONSTITUENTS</p>',
        unsafe_allow_html=True,
    )
    try:
        # Filter and validate — remove NaN / None / infinite values
        valid  = [(t, float(v)) for t, v in returns_1m.items()
                  if v is not None and not pd.isna(v) and abs(float(v)) < 500]
        if len(valid) < 3:
            st.info("1-month data temporarily unavailable — fewer than 3 valid data points.")
            return

        items  = sorted(valid, key=lambda x: x[1])
        vals   = [v for _, v in items]
        names  = [name_map.get(t, t) for t, _ in items]
        colors = [_OG if v >= 0 else "#555555" for v in vals]
        labels = [("+" if v >= 0 else "") + f"{v:.1f}%" for v in vals]

        fig = go.Figure(go.Bar(
            x=vals, y=names, orientation="h",
            marker_color=colors,
            text=labels, textposition="outside",
            textfont=dict(size=10, color="#4A4A4A"),
            hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
        ))
        fig.update_layout(
            paper_bgcolor=_WHT, plot_bgcolor=_WHT,
            height=max(700, len(items) * 18),
            xaxis=dict(showgrid=False, zeroline=True, zerolinecolor=_BRD,
                       zerolinewidth=1.5, tickfont=dict(size=10, color=_LGR)),
            yaxis=dict(showgrid=False, tickfont=dict(size=11, color=_DGR)),
            margin=dict(l=0, r=72, t=8, b=40),
            transition_duration=0,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    except Exception as _e:
        print(f"[z47fs s6_1m_chart ERROR] {_e}")
        # Graceful text fallback — never show "please refresh"
        try:
            v_all = [(t, float(v)) for t, v in returns_1m.items() if v is not None and not pd.isna(v)]
            if v_all:
                top1 = max(v_all, key=lambda x: x[1])
                bot1 = min(v_all, key=lambda x: x[1])
                pos  = sum(1 for _, v in v_all if v >= 0)
                st.markdown(
                    f'<p style="color:{_DGR};font-size:14px;{_F}">'
                    f'1-month returns: '
                    f'<b style="color:{_GRN}">+{top1[1]:.1f}%</b> ({name_map.get(top1[0], top1[0])}) '
                    f'to <b style="color:{_RED}">{bot1[1]:.1f}%</b> '
                    f'({name_map.get(bot1[0], bot1[0])}). '
                    f'{pos} of {len(v_all)} constituents advanced.</p>',
                    unsafe_allow_html=True,
                )
        except Exception:
            st.markdown(
                f'<p style="color:{_LGR};font-size:14px;{_F}">'
                f'1-month chart temporarily unavailable.</p>',
                unsafe_allow_html=True,
            )


def _s7_constituents(returns_1m: dict, mcaps: dict,
                     price_cache: dict, usdinr: float) -> None:
    """Section 7 — Constituents table, sorted by market cap desc."""
    st.markdown(
        f'<p style="{_lbl()}">CONSTITUENTS · LIVE PRICES</p>',
        unsafe_allow_html=True,
    )

    SHORT_S = {
        "Fintech / Financial Services": "Fintech",
        "Consumer / Consumer Tech":     "Consumer Tech",
        "B2B": "B2B",
        "SaaS / AI": "SaaS / AI",
    }

    def _mcap_inr(c):
        mc = mcaps.get(c["ticker"])
        if mc:
            return mc["mc"] if mc["currency"] == "INR" else mc["mc"] * usdinr
        return c["mkt_cap_mn"]

    sorted_cos = sorted(COMPANIES, key=_mcap_inr, reverse=True)

    th = (f"padding:10px 14px;font-size:10px;font-weight:700;letter-spacing:0.07em;"
          f"color:{_LGR};text-transform:uppercase;border-bottom:1px solid {_BRD};"
          f"background:#FAFAFA;white-space:nowrap;{_F}")

    tbl = (f'<div style="overflow-x:auto"><table style="width:100%;'
           f'border-collapse:collapse;border:1px solid {_BRD}">'
           f'<thead><tr>'
           f'<th style="text-align:left;{th};width:28%">Company</th>'
           f'<th style="text-align:left;{th};width:18%">Sector</th>'
           f'<th style="text-align:right;{th};width:13%">Price</th>'
           f'<th style="text-align:right;{th};width:10%">Day Chg</th>'
           f'<th style="text-align:right;{th};width:10%">1M Chg</th>'
           f'<th style="text-align:right;{th};width:15%">Mkt Cap (&#8377; Mn)</th>'
           f'</tr></thead><tbody>')

    for c in sorted_cos:
        q   = price_cache.get(c["ticker"], {})
        px  = q.get("price")
        pct = q.get("pct_change")
        m1  = returns_1m.get(c["ticker"])
        mc  = mcaps.get(c["ticker"])

        mc_inr = round(
            mc["mc"] if mc and mc["currency"]=="INR" else (mc["mc"]*usdinr if mc else c["mkt_cap_mn"]), 0
        )
        px_str = (f"&#8377;{px:,.2f}" if px and c["exchange"]=="NSE"
                  else (f"${px:,.2f}" if px else f'<span style="color:{_LGR}">—</span>'))

        tbl += (
            f'<tr style="border-bottom:1px solid {_BRD}">'
            f'<td style="padding:12px 14px;font-size:14px;font-weight:500;color:{_BLK};{_F}">'
            f'{c["name"]}</td>'
            f'<td style="padding:12px 14px;font-size:11px;color:{_LGR};{_F}">'
            f'{SHORT_S.get(c["sector"],c["sector"])}</td>'
            f'<td style="padding:12px 14px;text-align:right;font-size:14px;'
            f'font-weight:500;color:{_BLK};{_F}">{px_str}</td>'
            f'<td style="padding:12px 14px;text-align:right;font-size:13px;{_F}">'
            f'{_chg_cell(pct)}</td>'
            f'<td style="padding:12px 14px;text-align:right;font-size:13px;{_F}">'
            f'{_chg_cell(m1)}</td>'
            f'<td style="padding:12px 14px;text-align:right;font-size:13px;color:{_DGR};{_F}">'
            f'{mc_inr:,.0f}</td>'
            f'</tr>'
        )
    tbl += "</tbody></table></div>"
    st.markdown(tbl, unsafe_allow_html=True)
    st.caption(f"Prices via NSE / Yahoo Finance · Market cap live · Sorted by mkt cap · "
               f"USD/INR: ₹{usdinr:.2f}")


def _s8_sector() -> None:
    """Section 8 — Sector composition donut + list.
    Per-slice fills with contrast-checked text colours:
      Consumer Tech  → light grey  #ECECEC  / dark text
      Fintech        → medium orange #FF9A5C / dark text
      B2B            → brand orange  #FF6B1A / dark text
      SaaS / AI      → dark grey    #2A2A2A / WHITE text
    """
    st.markdown(f'<p style="{_lbl()}">SECTOR COMPOSITION</p>', unsafe_allow_html=True)
    from collections import Counter

    # Explicit per-sector fill + text-colour map — immune to Counter ordering
    _SECTOR_STYLE = {
        "Consumer / Consumer Tech":     {"fill": "#ECECEC", "text": _BLK,  "label_text": _BLK},
        "Fintech / Financial Services": {"fill": "#FF9A5C", "text": _BLK,  "label_text": _BLK},
        "B2B":                          {"fill": _OG,       "text": _BLK,  "label_text": _BLK},
        "SaaS / AI":                    {"fill": "#2A2A2A", "text": "#FFFFFF", "label_text": "#FFFFFF"},
    }

    counts  = Counter(c["sector"] for c in COMPANIES)
    total   = sum(counts.values())
    SHORT   = {"Fintech / Financial Services": "Fintech",
               "Consumer / Consumer Tech":     "Consumer Tech",
               "B2B": "B2B", "SaaS / AI": "SaaS / AI"}

    sectors     = list(counts.keys())
    vals        = [counts[s] for s in sectors]
    fill_colors = [_SECTOR_STYLE.get(s, {"fill": _LGR})["fill"]       for s in sectors]
    text_colors = [_SECTOR_STYLE.get(s, {"text": _BLK})["text"]       for s in sectors]

    fig = go.Figure(go.Pie(
        labels=[SHORT.get(s, s) for s in sectors],
        values=vals,
        hole=0.65,
        marker=dict(colors=fill_colors, line=dict(color=_WHT, width=2)),
        textinfo="percent+label",
        textfont=dict(size=10, color=text_colors),   # per-slice text colour list
        hovertemplate="%{label}: %{value} cos<extra></extra>",
        showlegend=False,
    ))
    fig.add_annotation(text=f"<b>{total}</b>", x=0.5, y=0.56, showarrow=False,
                       font=dict(size=30, color=_BLK))
    fig.add_annotation(text="companies", x=0.5, y=0.43, showarrow=False,
                       font=dict(size=11, color=_LGR))
    fig.update_layout(paper_bgcolor=_WHT, plot_bgcolor=_WHT, height=300,
                      margin=dict(l=0, r=0, t=8, b=8), transition_duration=0)

    cl, cr = st.columns([1, 1], gap="large")
    with cl:
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with cr:
        # Legend with matching colour swatches
        rows_html = "".join(
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:11px 0;border-bottom:1px solid {_BRD}">'
            f'<span style="display:flex;align-items:center;gap:8px;{_F}">'
            f'<span style="display:inline-block;width:12px;height:12px;border-radius:2px;'
            f'background:{_SECTOR_STYLE.get(s,{}).get("fill",_LGR)};'
            f'border:1px solid rgba(0,0,0,0.1);flex-shrink:0"></span>'
            f'<span style="font-size:13px;color:{_BLK};font-weight:500">'
            f'{SHORT.get(s, s)}</span></span>'
            f'<span style="font-size:12px;color:{_LGR};{_F}">'
            f'{cnt} co · {cnt/total*100:.1f}%</span>'
            f'</div>'
            for s, cnt in sorted(counts.items(), key=lambda x: -x[1])
        )
        st.markdown(f'<div style="margin-top:20px">{rows_html}</div>',
                    unsafe_allow_html=True)


def _s9_methodology() -> None:
    """Section 9 — Four-part methodology section per brand spec."""

    def _bullet_list(points: list[str]) -> str:
        return "".join(
            f'<li style="margin-bottom:10px;color:{_DGR};font-size:14px;'
            f'line-height:1.65;list-style:none;padding-left:18px;position:relative;{_F}">'
            f'<span style="position:absolute;left:0;color:{_OG};font-weight:700">•</span>'
            f'{p}</li>'
            for p in points
        )

    def _sub_section(label: str, points: list[str], intro: str = "") -> str:
        intro_html = (f'<p style="font-size:14px;color:{_DGR};margin:0 0 12px;'
                      f'line-height:1.65;{_F}">{intro}</p>' if intro else "")
        return (
            f'<p style="{_lbl("margin-top:28px")};">{label}</p>'
            f'{intro_html}'
            f'<ul style="margin:0;padding:0">{_bullet_list(points)}</ul>'
        )

    # ── Sub-section 1: Methodology ────────────────────────────────────────────
    s1 = _sub_section("METHODOLOGY", [
        "47 listed Indian new-age technology and new-economy financial-services companies "
        "selected for their role in India's transition to a developed economy by 2047",
        "Free-float market-capitalisation weighted index, rebased to 100 on 1 January 2024; "
        "individual constituent weight capped at 10% (iterative redistribution)",
        "For constituents listed after 1 January 2024, included from their first full "
        "trading day post-listing; no synthetic pre-listing prices are used",
        "<b>Constituent changes &mdash; portfolio units adjustment.</b> When a constituent is "
        "added, removed, or replaced, constituent units are recalculated on the effective date "
        "so that the index level is unchanged at the moment of the change. The constituent "
        "change is value-neutral; subsequent index movements reflect only price changes of "
        "the new basket. This ensures the historical index series is continuous and free of "
        "artificial jumps from basket reconstitution.",
        "Constituents reviewed quarterly &mdash; additions on listing, removals on delisting, "
        "prolonged suspension, or classification change",
        "Price data sourced from NSE / BSE via Yahoo Finance with 5-minute live refresh "
        "during market hours",
        "Returns computed in INR terms; benchmark comparison against Nifty 500",
        "Sector classification: Fintech / Financial Services &nbsp;·&nbsp; "
        "Consumer / Consumer Tech &nbsp;·&nbsp; B2B &nbsp;·&nbsp; SaaS / AI",
        "Data refresh cadence &mdash; prices: 5 min &nbsp;·&nbsp; index level: daily "
        "&nbsp;·&nbsp; takeaways: weekly (Monday)",
    ])

    # ── Sub-section 2: Inclusion Criteria ─────────────────────────────────────
    s2 = _sub_section(
        "INCLUSION CRITERIA",
        [
            "Listed on NSE, BSE, Nasdaq, or NYSE in the last decade, with an Indian founding "
            "team and India as a core market (with Info Edge and MakeMyTrip, both listed 2010, "
            "grandfathered as foundational predecessors)",
            "Operates a new-age, technology-led, or category-creating business model",
            "Has received institutional venture, growth-equity, or private-equity capital at "
            "some point in its lifecycle; i.e., not a pure promoter-only or "
            "family-conglomerate business",
            "Minimum market capitalisation of &#8377;2,000 crore at the time of index entry",
            "Added to the index from their first full trading day post-listing, provided all "
            "other criteria are met at that date",
        ],
        intro='A company qualifies for Z47^<em>fortyseven</em> if it meets ALL of the following:',
    )

    # ── Sub-section 3: Review Policy ──────────────────────────────────────────
    s3 = _sub_section(
        "REVIEW POLICY",
        [
            "New listings that meet the inclusion criteria",
            "Changes in business model, sector classification, or market cap that affect "
            "a constituent's eligibility",
            "Delistings, prolonged suspensions, mergers, or material restructuring",
            "Refinements to the methodology itself as the index matures",
        ],
        intro=(
            'The constituent list is not static. Z47^<em>fortyseven</em> is reviewed quarterly and '
            "may be updated to reflect:"
        ),
    )
    s3 += (
        f'<p style="font-size:14px;color:{_DGR};margin:16px 0 0;line-height:1.65;{_F}">'
        f'Replacements and other constituent changes could happen in the future depending '
        f'on new listings or changes to current companies due to any reason. Constituent '
        f'changes are applied prospectively from the effective date, with a divisor '
        f'adjustment to keep the index level continuous; they are not retroactively '
        f'spliced into the historical series.'
        f'</p>'
    )

    # ── Sub-section 4: Disclosure ─────────────────────────────────────────────
    s4 = _sub_section("DISCLAIMER", [
        "For informational and discussion purposes only. Not investment advice. Past "
        "performance is not indicative of future results.",
    ])

    st.markdown(s1 + s2 + s3 + s4, unsafe_allow_html=True)


def _s10_footer(usdinr: float) -> None:
    """Section 10 — Data status + disclaimer."""
    now_ts  = _now_ist_str("%H:%M IST · %d %b %Y")
    updated = HARDCODED_INDEX_TAKEAWAY.get("updated", "—")
    st.markdown(
        f'<div style="margin-top:16px;padding:12px 0;border-top:1px solid {_BRD}">'
        f'<p style="font-size:11px;color:{_LGR};{_F}">'
        f'<b style="font-size:10px;font-weight:700;letter-spacing:0.08em;'
        f'text-transform:uppercase;color:{_DGR}">DATA STATUS</b>'
        f'&nbsp;·&nbsp;Index: today'
        f'&nbsp;·&nbsp;Prices: live {now_ts}'
        f'&nbsp;·&nbsp;FX: &#8377;{usdinr:.2f}'
        f'&nbsp;·&nbsp;Takeaway: {updated}'
        f'</p></div>'
        f'<div style="padding:28px 0 16px;text-align:center;border-top:1px solid {_BRD}">'
        f'<p style="font-size:12px;color:{_LGR};line-height:1.75;max-width:680px;'
        f'margin:0 auto;{_F}">The Z47^<em>fortyseven</em> Index is published by Z47 for informational '
        f'and discussion purposes only. It does not constitute investment advice. Past '
        f'performance is not indicative of future results. Constituent data and prices '
        f'are sourced from public exchanges and third-party data providers.</p>'
        f'<p style="font-size:12px;color:{_LGR};margin-top:12px;{_F}">'
        f'<a href="https://www.z47.com" target="_blank" '
        f'style="color:{_OG};text-decoration:none;font-weight:600">z47.com</a>'
        f'&nbsp;·&nbsp; © 2026 Z47</p></div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def render() -> None:
    """Render the Z47fortyseven public-facing page."""
    from streamlit_autorefresh import st_autorefresh

    # ── Adaptive auto-refresh: 3 min during market hours, 15 min outside ─────
    _mh = _is_market_hours()
    _refresh_ms = 180_000 if _mh else 900_000
    st_autorefresh(interval=_refresh_ms, key="z47fs_autorefresh")

    # ── Weekly content cache refresh (Monday-keyed, idempotent) ──────────────
    _maybe_refresh_weekly()

    # ── Background + nav-pill color overrides ────────────────────────────────
    _bg_css = (
        "<style>"
        ".stApp,.stApp>div,.block-container{background-color:#FFFFFF!important}"
        # Active nav pill → brand orange; nowrap on button AND inner text elements
        "button[data-testid='baseButton-primary']{"
        "background-color:#FF6B1A!important;"
        "border-color:#FF6B1A!important;"
        "color:#FFFFFF!important;"
        "white-space:nowrap!important;"
        "word-break:normal!important;"
        "hyphens:none!important}"
        "button[data-testid='baseButton-primary'] p,"
        "button[data-testid='baseButton-primary'] span{"
        "white-space:nowrap!important;"
        "word-break:normal!important;"
        "hyphens:none!important}"
        "button[data-testid='baseButton-primary']:hover{"
        "background-color:#e55e14!important;"
        "border-color:#e55e14!important}"
        # Inactive nav pill → white + light border; same nowrap treatment
        "button[data-testid='baseButton-secondary']{"
        "background-color:#FFFFFF!important;"
        "border-color:#E8E8E8!important;"
        "color:#0A0A0A!important;"
        "white-space:nowrap!important;"
        "word-break:normal!important;"
        "hyphens:none!important}"
        "button[data-testid='baseButton-secondary'] p,"
        "button[data-testid='baseButton-secondary'] span{"
        "white-space:nowrap!important;"
        "word-break:normal!important;"
        "hyphens:none!important}"
        "button[data-testid='baseButton-secondary']:hover{"
        "border-color:#FF6B1A!important}"
        "</style>"
    )
    try:
        st.html(_bg_css)
    except AttributeError:
        st.markdown(_bg_css, unsafe_allow_html=True)

    # ── Google Fonts ──────────────────────────────────────────────────────────
    st.markdown(
        '<link href="https://fonts.googleapis.com/css2?family=Inter:'
        'ital,wght@0,400;0,500;0,600;0,700;0,800;1,400;1,700&display=swap"'
        ' rel="stylesheet">',
        unsafe_allow_html=True,
    )

    # ── Hero band — rendered ONCE at the top regardless of active section ──────
    st.markdown('<div style="padding-top:16px"></div>', unsafe_allow_html=True)
    _hero_band()

    # ── Load data — session-state cache avoids refetch on pill switches ──────
    # Fetch logic (market-hours aware, 1-hr TTL):
    #   • No cache       → always fetch (cold start)
    #   • Market CLOSED  → always serve from cache; never refetch outside hours
    #   • Market OPEN    → refetch only when cache is older than _DATA_TTL_S
    # Each source is isolated: one failed ticker/feed never crashes the page.
    _ss         = st.session_state
    _now_epoch  = datetime.now(_IST_TZ).timestamp()
    _DATA_TTL_S = 3600  # 1-hour TTL — matches "updated hourly" claim
    _have_cache = "z47fs_cache" in _ss
    _cache_age  = _now_epoch - _ss.get("z47fs_fetch_epoch", 0.0)
    # Outside market hours: never hit the network; serve whatever cache we have.
    # Inside market hours: refetch when cache is stale (>1hr) or absent.
    _should_fetch = not _have_cache or (_mh and _cache_age >= _DATA_TTL_S)

    if _should_fetch:
        # ── Real network fetch ────────────────────────────────────────────────
        _fetch_start  = _now_ist()
        _fetch_errors: list[str] = []
        _prev = _ss.get("z47fs_cache", {})   # stale cache for fallback values

        with st.spinner(""):
            try:
                n500_live, usdinr, fx_chg = _live_indices()
            except Exception as _e:
                _fetch_errors.append(f"indices:{_e}")
                n500_live = fx_chg = None
                usdinr = float(_prev.get("usdinr") or 85.0)

            try:
                returns_1m = _fetch_1m_returns()
            except Exception as _e:
                _fetch_errors.append(f"1m_returns:{_e}")
                returns_1m = _prev.get("returns_1m") or {}

            try:
                mcaps = _fetch_mcaps()
            except Exception as _e:
                _fetch_errors.append(f"mcaps:{_e}")
                mcaps = _prev.get("mcaps") or {}

            try:
                hist = _load_history()
            except Exception as _e:
                _fetch_errors.append(f"history:{_e}")
                hist = pd.DataFrame()

            # Constituent prices — each ticker isolated
            price_cache: dict = {}
            def _fp(c):
                try:
                    return c["ticker"], _fetch_price(c["ticker"], c["exchange"])
                except Exception:
                    return c["ticker"], {}
            with ThreadPoolExecutor(max_workers=12) as _px_ex:
                for _ftk, _fpd in _px_ex.map(_fp, COMPANIES):
                    price_cache[_ftk] = _fpd

            try:
                df = _extend_history(hist, n500_live) if not hist.empty else pd.DataFrame()
            except Exception as _e:
                _fetch_errors.append(f"extend_history:{_e}")
                df = hist if not hist.empty else pd.DataFrame()

        name_map = {c["ticker"]: c["name"] for c in COMPANIES}

        if _fetch_errors:
            print(f"[z47fs fetch errors] {'; '.join(_fetch_errors)}")

        if not df.empty:
            # Success — store fresh data and update timestamp
            _ss["z47fs_cache"] = {
                "df": df, "n500_live": n500_live,
                "usdinr": usdinr, "fx_chg": fx_chg,
                "returns_1m": returns_1m, "mcaps": mcaps,
                "price_cache": price_cache, "name_map": name_map,
            }
            _ss["z47fs_fetch_ts"]    = _fetch_start.strftime("%H:%M IST")
            _ss["z47fs_fetch_epoch"] = _fetch_start.timestamp()
            print(f"[FETCH {_now_ist_str('%Y-%m-%d %H:%M IST')}] "
                  f"loaded in {(_now_ist()-_fetch_start).total_seconds():.1f}s "
                  f"(market={'OPEN' if _mh else 'CLOSED'})"
                  f"{' errors:'+','.join(_fetch_errors) if _fetch_errors else ''}")
        elif _have_cache:
            # Fresh fetch produced no usable data — fall back to stale cache
            _c = _prev
            df          = _c["df"];          n500_live   = _c["n500_live"]
            usdinr      = _c["usdinr"];      fx_chg      = _c["fx_chg"]
            returns_1m  = _c["returns_1m"];  mcaps       = _c["mcaps"]
            price_cache = _c["price_cache"]; name_map    = _c["name_map"]
            st.warning(
                f"⚠️ Live refresh failed — showing last available data "
                f"from {_ss.get('z47fs_fetch_ts', '—')}. "
                f"Auto-retrying in {_refresh_ms//1000}s.",
                icon="⚠️",
            )
        else:
            # No data at all
            st.error(
                "Unable to load market data. "
                "Please click 🔄 to retry, or refresh the page.",
                icon="🚫",
            )
            _slim_footer()
            return
    else:
        # ── Fast path: serve from session-state cache (pill switch / hot rerun) ─
        _c          = _ss["z47fs_cache"]
        df          = _c["df"];          n500_live   = _c["n500_live"]
        usdinr      = _c["usdinr"];      fx_chg      = _c["fx_chg"]
        returns_1m  = _c["returns_1m"];  mcaps       = _c["mcaps"]
        price_cache = _c["price_cache"]; name_map    = _c["name_map"]

    # ── Freshness badge — timestamp from actual fetch, not current time ───────
    _saved_ts = _ss.get("z47fs_fetch_ts", "—")
    _age_s    = _now_epoch - _ss.get("z47fs_fetch_epoch", _now_epoch)

    # ── Freshness strip + inline refresh button ───────────────────────────────
    if _render_header_bar(df, usdinr, fetch_ts=_saved_ts, fetch_age_s=_age_s):
        # User clicked 🔄 — clear function caches AND session-state cache, rerun
        _live_indices.clear()
        _fetch_price.clear()
        _fetch_1m_returns.clear()
        _fetch_mcaps.clear()
        _load_history.clear()
        for _k in ("z47fs_cache", "z47fs_fetch_ts", "z47fs_fetch_epoch"):
            _ss.pop(_k, None)
        print(f"[FORCE-REFRESH {_now_ist_str('%Y-%m-%d %H:%M IST')}] user clicked 🔄")
        st.rerun()

    # ── Section sub-nav (4 pills, matching IPOs tab pattern) ────────────────
    _SECTIONS = [
        ("performance",  "Performance"),
        ("insights",     "Z47 Insights"),
        ("constituents", "Constituents"),
        ("about",        "Methodology"),
    ]
    _section_ids = [s[0] for s in _SECTIONS]

    # Init session state — honour ?section= query param on first load
    if "z47fs_section" not in st.session_state:
        _qs_sec = st.query_params.get("section", "performance")
        st.session_state.z47fs_section = (
            _qs_sec if _qs_sec in _section_ids else "performance"
        )
    _active = st.session_state.z47fs_section

    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
    # Each pill sizes to its label text; trailing gap keeps the strip left-aligned.
    # use_container_width=False lets each button shrink to content width so
    # "Methodology" is never forced into a narrow fixed-width box.
    _nc1, _nc2, _nc3, _nc4, _ncgap = st.columns([1.5, 1.5, 1.5, 2.0, 2.5])
    for _ncol, (_sid, _slabel) in zip([_nc1, _nc2, _nc3, _nc4], _SECTIONS):
        with _ncol:
            if st.button(
                _slabel,
                key=f"z47fs_snav_{_sid}",
                type="primary" if _active == _sid else "secondary",
                use_container_width=False,
            ):
                st.session_state.z47fs_section = _sid
                st.query_params["section"] = _sid
                st.rerun()
    st.markdown(
        "<hr style='border-color:#E8E8E8;margin:6px 0 14px 0'>",
        unsafe_allow_html=True,
    )

    # ── Active section content ────────────────────────────────────────────────
    if _active == "performance":
        _section_label("PERFORMANCE")
        _s2_performance(df, n500_live, usdinr, fx_chg)
        _divider()
        _s3_returns(df)
        _divider()
        if returns_1m:
            _s5_movers(returns_1m, name_map)
        else:
            st.info("1-month return data loading — auto-refreshes every 3 minutes during market hours.")

    elif _active == "insights":
        _section_label("Z47 INSIGHTS")
        _s4_takeaway()
        _s_kissht_takeaway()

    elif _active == "constituents":
        _section_label("CONSTITUENTS")
        _s8_sector()
        _divider()
        if returns_1m:
            _s6_1m_chart(returns_1m, name_map)
            _divider()
        _s7_constituents(returns_1m, mcaps, price_cache, usdinr)

    elif _active == "about":
        _section_label("METHODOLOGY")
        _s9_methodology()

    # ── Slim footer — always visible regardless of active section ─────────────
    _section_spacer()
    _slim_footer()
