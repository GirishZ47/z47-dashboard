"""
Z47fortyseven — public-facing index page.
Visual language: z47.com brand (white bg, Inter, orange #FF6B1A).
Layout: BVP Emerging Cloud Index architecture.
Self-contained module — no imports from app.py to avoid circular imports.
"""
from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta, datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

from companies import COMPANIES, yf_ticker

try:
    from takeaway_constants import HARDCODED_INDEX_TAKEAWAY
except Exception:
    HARDCODED_INDEX_TAKEAWAY = {"text": "", "window": "", "updated": "", "icon": ""}

# ── Brand palette ─────────────────────────────────────────────────────────────
_OG  = "#FF6B1A"   # Z47 brand orange
_BLK = "#0A0A0A"   # near-black
_DGR = "#4A4A4A"   # secondary text
_LGR = "#888888"   # caption / label
_BRD = "#E8E8E8"   # border / divider
_GRN = "#1F8A50"   # positive delta
_RED = "#D14343"   # negative delta
_WHT = "#FFFFFF"   # background
_FNT = "'Inter', -apple-system, sans-serif"

# ── CSS injection (scoped to .z47fs wrapper) ──────────────────────────────────
_BRAND_CSS = """
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap"
      rel="stylesheet">
<style>
/* ── global reset inside z47fs ─────────────────────────────────────── */
.z47fs, .z47fs * { font-family: 'Inter', -apple-system, sans-serif !important; box-sizing: border-box; }
.z47fs h1, .z47fs h2, .z47fs h3 { color: #0A0A0A; font-weight: 700; margin: 0; }

/* ── section label (small-caps orange) ─────────────────────────────── */
.z47fs .slabel {
    font-size: 11px; font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; color: #FF6B1A; margin-bottom: 6px;
}

/* ── hero cards ─────────────────────────────────────────────────────── */
.z47fs .hcard {
    background: #FFFFFF; border: 1px solid #E8E8E8;
    padding: 18px 20px;
}
.z47fs .hlbl  { font-size: 10px; font-weight: 700; letter-spacing: 0.1em;
                text-transform: uppercase; color: #FF6B1A; margin-bottom: 6px; }
.z47fs .hval  { font-size: 34px; font-weight: 800; color: #0A0A0A;
                line-height: 1.1; margin-bottom: 4px; }
.z47fs .hdlp  { font-size: 13px; font-weight: 500; color: #1F8A50; }
.z47fs .hdln  { font-size: 13px; font-weight: 500; color: #D14343; }
.z47fs .hsub  { font-size: 10px; color: #888888; margin-top: 3px; }

/* ── period selector styling ─────────────────────────────────────────── */
.z47fs .stRadio > div { flex-direction: row; gap: 0; }
.z47fs .stRadio label {
    font-size: 13px !important; font-weight: 500 !important;
    color: #4A4A4A !important; padding: 6px 14px !important;
    border-bottom: 2px solid transparent !important;
    cursor: pointer !important;
}
.z47fs .stRadio label[data-selected="true"],
.z47fs .stRadio label[aria-checked="true"] {
    color: #FF6B1A !important; font-weight: 700 !important;
    border-bottom: 2px solid #FF6B1A !important;
}

/* ── divider ─────────────────────────────────────────────────────────── */
.z47fs .zdiv { height: 1px; background: #E8E8E8; margin: 44px 0; }
</style>
"""

# ─────────────────────────────────────────────────────────────────────────────
# Data helpers (self-contained — no app.py dependency)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def _live_indices() -> tuple:
    """Return (nifty, sensex, usdinr, fx_day_pct)."""
    nifty = sensex = usdinr = None
    fx_chg = None
    try:    nifty   = round(float(yf.Ticker("^NSEI").fast_info.last_price), 2)
    except: pass
    try:    sensex  = round(float(yf.Ticker("^BSESN").fast_info.last_price), 2)
    except: pass
    try:
        fx_fi   = yf.Ticker("USDINR=X")
        usdinr  = round(float(fx_fi.fast_info.last_price), 2)
        fx_hist = fx_fi.history(period="2d")
        if len(fx_hist) >= 2:
            prev   = float(fx_hist["Close"].iloc[-2])
            fx_chg = round((usdinr / prev - 1) * 100, 2) if prev else None
    except:
        usdinr = 85.0
    return nifty, sensex, usdinr or 85.0, fx_chg


@st.cache_data(ttl=3600, show_spinner=False)
def _load_history() -> pd.DataFrame:
    csv = os.path.join(os.path.dirname(__file__), "z47_history.csv")
    df  = pd.read_csv(csv, parse_dates=["date"])
    return df.sort_values("date").reset_index(drop=True)


def _extend_history(hist: pd.DataFrame, nifty_live, sensex_live) -> pd.DataFrame:
    """Fill all trading days between last CSV date and today via yfinance."""
    last      = hist.iloc[-1]
    today     = pd.Timestamp.today().normalize()
    last_date = pd.Timestamp(last["date"]).normalize()
    if last_date >= today:
        return hist

    nb_base = float(last.get("nifty_abs")  or 0)
    sb_base = float(last.get("sensex_abs") or 0)
    z47_b   = float(last["z47_float"])
    ni_b    = float(last["nifty_indexed"])
    si_b    = float(last["sensex_indexed"])
    z47mc_b = float(last.get("z47_mcap") or z47_b)

    new_rows: list[dict] = []
    try:
        s   = (last_date + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        e   = (today + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        nf  = yf.download("^NSEI",  start=s, end=e, progress=False, auto_adjust=True)
        sf  = yf.download("^BSESN", start=s, end=e, progress=False, auto_adjust=True)

        def _cls(d):
            if d.empty: return pd.Series(dtype=float)
            if isinstance(d.columns, pd.MultiIndex): return d["Close"].squeeze()
            return d["Close"].squeeze() if "Close" in d.columns else d.iloc[:, 0]

        nfc = _cls(nf);  sfc = _cls(sf)
        for dt in nfc.index:
            dn = pd.Timestamp(dt).normalize()
            if dn <= last_date: continue
            nb_new = float(nfc.loc[dt])
            if not nb_new or not nb_base: continue
            r = nb_new / nb_base
            try:    sb_new = float(sfc.loc[dt])
            except: sb_new = sb_base * r
            si_new = si_b * (sb_new / sb_base) if sb_base else si_b * r
            new_rows.append({
                "date": dn,
                "z47_float": round(z47_b * r, 4), "z47_mcap": round(z47mc_b * r, 4),
                "nifty_indexed": round(ni_b * r, 4), "sensex_indexed": round(si_new, 4),
                "nifty_abs": round(nb_new, 2), "sensex_abs": round(sb_new, 2),
            })
    except Exception as _e:
        print(f"[z47fs extend_history] {_e}")

    if not new_rows:
        ratio  = (nifty_live / nb_base) if nb_base and nifty_live else 1.0
        sb_td  = sensex_live or (sb_base * ratio)
        si_td  = si_b * (sb_td / sb_base) if sb_base else si_b * ratio
        new_rows = [{"date": today,
                     "z47_float": round(z47_b*ratio,4), "z47_mcap": round(z47mc_b*ratio,4),
                     "nifty_indexed": round(ni_b*ratio,4), "sensex_indexed": round(si_td,4),
                     "nifty_abs": nifty_live or nb_base, "sensex_abs": sb_td}]

    return pd.concat([hist, pd.DataFrame(new_rows).sort_values("date")], ignore_index=True)


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_price(symbol: str, exchange: str) -> dict:
    """Live price with cascade fallback: fast_info → history(5d) → {}."""
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
            return {"price": px, "pct_change": round((px/pc-1)*100, 2) if pc else None}
    except Exception:
        pass
    return {}


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_1m_returns() -> dict[str, float]:
    """Exact 1-calendar-month returns for all 47 companies."""
    tickers = [yf_ticker(c) for c in COMPANIES]
    try:
        raw = yf.download(tickers, period="50d", progress=False, auto_adjust=True)
        closes = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
        if closes.empty:
            return {}
        target = date.today() - timedelta(days=30)
        # Find first available trading day on or after target
        valid_i = [i for i, d in enumerate(closes.index) if d.date() >= target]
        if not valid_i:
            return {}
        base_i  = valid_i[0]
        result  = {}
        tk_map  = {yf_ticker(c): c["ticker"] for c in COMPANIES}
        for yftk in closes.columns:
            s = closes[yftk].dropna()
            if len(s) <= base_i:
                continue
            b = float(s.iloc[base_i])
            e = float(s.iloc[-1])
            if b and b > 0:
                result[tk_map.get(yftk, yftk)] = round((e / b - 1) * 100, 2)
        return result
    except Exception as _e:
        print(f"[z47fs 1m_returns] {_e}")
        return {}


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_mcaps() -> dict:
    """Live market caps for all 47 companies (parallel fast_info)."""
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


# ─────────────────────────────────────────────────────────────────────────────
# Utility helpers
# ─────────────────────────────────────────────────────────────────────────────

def _pct_since(df: pd.DataFrame, col: str,
               days: int | None = None,
               ytd: bool = False,
               all_time: bool = False) -> float | None:
    if df.empty:
        return None
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
    if sub.empty:
        return None
    base = sub[col].iloc[0]
    return round((last / base - 1) * 100, 2) if base else None


def _delta(v, suffix="%"):
    if v is None:
        return f'<span style="color:{_LGR}">—</span>'
    color = _GRN if v >= 0 else _RED
    sign  = "+" if v > 0 else ""
    return f'<span style="color:{color};font-weight:500">{sign}{v:.1f}{suffix}</span>'


def _chg_cell(v):
    if v is None:
        return f'<span style="color:{_LGR}">—</span>'
    color = _GRN if v >= 0 else _RED
    sign  = "+" if v > 0 else ""
    return f'<span style="color:{color};font-weight:600">{sign}{v:.1f}%</span>'


def _slabel(text: str) -> None:
    st.markdown(f'<p class="z47fs slabel">{text}</p>', unsafe_allow_html=True)


def _divider() -> None:
    st.markdown('<div class="z47fs zdiv"></div>', unsafe_allow_html=True)


def _period_kw(period: str) -> dict:
    if period == "All":  return {"all_time": True}
    if period == "YTD":  return {"ytd": True}
    return {"days": {"1M": 30, "3M": 90, "6M": 180, "1Y": 365}[period]}


# ─────────────────────────────────────────────────────────────────────────────
# Section renderers
# ─────────────────────────────────────────────────────────────────────────────

def _s1_hero(df: pd.DataFrame, nifty_live, sensex_live, usdinr, fx_chg) -> None:
    """Section 1 — Hero: 5 live stat cards."""
    last   = df.iloc[-1]
    z47_v  = last["z47_float"]
    now_ts = datetime.now().strftime("%H:%M IST")

    z47_all  = _pct_since(df, "z47_float",     all_time=True)
    nif_all  = _pct_since(df, "nifty_indexed",  all_time=True)
    sen_all  = _pct_since(df, "sensex_indexed", all_time=True)
    z47_ytd  = _pct_since(df, "z47_float",     ytd=True)
    nif_ytd  = _pct_since(df, "nifty_indexed",  ytd=True)
    sen_ytd  = _pct_since(df, "sensex_indexed", ytd=True)

    spread   = round(z47_all - nif_all, 1) if z47_all is not None and nif_all is not None else None
    s_color  = _GRN if (spread or 0) >= 0 else _RED
    s_str    = (f"+{spread:.1f}pp ahead" if spread and spread >= 0
                else f"{spread:.1f}pp behind") if spread is not None else "—"

    def _card(label, value_html, delta_html, sub):
        return (
            f"<div class='z47fs hcard'>"
            f"<div class='z47fs hlbl'>{label}</div>"
            f"<div class='z47fs hval'>{value_html}</div>"
            f"{delta_html}"
            f"<div class='z47fs hsub'>{sub}</div>"
            f"</div>"
        )

    def _dl(v, suffix="%"):
        if v is None: return "<div></div>"
        col  = _GRN if v >= 0 else _RED
        cls  = "hdlp" if v >= 0 else "hdln"
        sign = "+" if v > 0 else ""
        return f"<div class='z47fs {cls}'>{sign}{v:.1f}{suffix}</div>"

    c1, c2, c3, c4, c5 = st.columns(5, gap="small")
    with c1:
        st.markdown(_card(
            "Z47fortyseven", f"{z47_v:.1f}",
            _dl(z47_all), f"Since Jan 2024 · {now_ts}"
        ), unsafe_allow_html=True)
    with c2:
        nf_str = f"{nifty_live:,.0f}" if nifty_live else "—"
        st.markdown(_card("Nifty 50", nf_str, _dl(nif_ytd), f"YTD · {now_ts}"), unsafe_allow_html=True)
    with c3:
        sx_str = f"{sensex_live:,.0f}" if sensex_live else "—"
        st.markdown(_card("Sensex", sx_str, _dl(sen_ytd), f"YTD · {now_ts}"), unsafe_allow_html=True)
    with c4:
        st.markdown(
            f"<div class='z47fs hcard'>"
            f"<div class='z47fs hlbl'>Z47 vs Nifty 50</div>"
            f"<div style='font-size:20px;font-weight:700;color:{s_color};margin:6px 0 4px'>{s_str}</div>"
            f"<div style='font-size:12px;color:{_DGR}'>Since 1 Jan 2024</div>"
            f"<div class='z47fs hsub'>Cumulative return spread</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with c5:
        fx_str = f"₹{usdinr:.2f}" if usdinr else "—"
        fx_dl  = _dl(fx_chg) if fx_chg else "<div></div>"
        st.markdown(_card("USD / INR", fx_str, fx_dl, f"Daily chg · {now_ts}"), unsafe_allow_html=True)


def _s2_performance(df: pd.DataFrame) -> None:
    """Section 2 — Index performance chart + period selector."""
    _slabel("INDEX PERFORMANCE")
    st.markdown(
        f"<h2 style='font-size:22px;font-weight:700;color:{_BLK};margin-bottom:4px'>"
        "Rebased to 100 · 1 January 2024</h2>",
        unsafe_allow_html=True,
    )

    period = st.radio(
        label="Period", label_visibility="collapsed",
        options=["All", "1M", "3M", "6M", "1Y", "YTD"],
        index=0, horizontal=True, key="z47fs_period",
    )

    # Slice and rebase
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
        for col in ["z47_float", "nifty_indexed", "sensex_indexed"]:
            plot[col] = plot[col] / base[col] * 100

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=plot["date"], y=plot["z47_float"], name="Z47fortyseven", mode="lines",
        line=dict(color=_OG, width=2.5),
        hovertemplate="%{x|%d %b %Y} · Z47: %{y:.1f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=plot["date"], y=plot["nifty_indexed"], name="Nifty 50", mode="lines",
        line=dict(color="#1F77B4", width=1.8),
        hovertemplate="%{x|%d %b %Y} · Nifty: %{y:.1f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=plot["date"], y=plot["sensex_indexed"], name="Sensex", mode="lines",
        line=dict(color="#2CA02C", width=1.8),
        hovertemplate="%{x|%d %b %Y} · Sensex: %{y:.1f}<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor=_WHT, plot_bgcolor=_WHT, height=360,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1,
                    font=dict(family=_FNT, size=12, color=_DGR),
                    bgcolor="rgba(255,255,255,0.9)"),
        xaxis=dict(showgrid=False, linecolor=_BRD, linewidth=1, showline=True,
                   tickfont=dict(family=_FNT, size=10, color=_LGR)),
        yaxis=dict(showgrid=True, gridcolor="#F5F5F5", gridwidth=1, showline=False,
                   tickfont=dict(family=_FNT, size=10, color=_LGR)),
        margin=dict(l=0, r=0, t=8, b=0),
        font=dict(family=_FNT),
        transition_duration=0,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # Stat callout row below chart
    kw  = _period_kw(period)
    z47_r = _pct_since(df, "z47_float",     **kw)
    nif_r = _pct_since(df, "nifty_indexed",  **kw)
    sen_r = _pct_since(df, "sensex_indexed", **kw)
    _sign = lambda v: (f"+{v:.1f}%" if v >= 0 else f"{v:.1f}%") if v is not None else "—"
    _col  = lambda v: (_GRN if v >= 0 else _RED) if v is not None else _LGR
    parts = [
        f'<b style="color:{_col(z47_r)}">{_sign(z47_r)}</b> Z47fortyseven',
        f'<b style="color:{_col(nif_r)}">{_sign(nif_r)}</b> Nifty 50',
        f'<b style="color:{_col(sen_r)}">{_sign(sen_r)}</b> Sensex',
    ]
    st.markdown(
        f"<p style='font-size:13px;color:{_DGR};margin-top:6px'>" +
        "&nbsp; · &nbsp;".join(parts) + "</p>",
        unsafe_allow_html=True,
    )

    # Index history freshness
    try:
        last_dt  = df["date"].max()
        age_days = (pd.Timestamp.today().normalize() - last_dt).days
        st.caption(
            f"Index history through: {last_dt.strftime('%d %b %Y')} · "
            + ("auto-updates daily" if age_days <= 3 else f"⚠️ {age_days} days old — reload to refresh")
        )
    except Exception:
        pass


def _s3_returns(df: pd.DataFrame) -> None:
    """Section 3 — Returns heatmap matrix."""
    _slabel("RETURNS SUMMARY")

    periods = [
        ("1M",            {"days": 30}),
        ("3M",            {"days": 90}),
        ("6M",            {"days": 180}),
        ("1Y",            {"days": 365}),
        ("YTD",           {"ytd": True}),
        ("Since Jan 2024", {"all_time": True}),
    ]
    rows = [
        ("Z47fortyseven", "z47_float"),
        ("Nifty 50",       "nifty_indexed"),
        ("Sensex",         "sensex_indexed"),
    ]

    def _cell_colors(v):
        if v is None:
            return "#FAFAFA", _LGR
        intensity = min(abs(v) / 30.0, 1.0)
        if v >= 0:
            r2 = int(220 + (255 - 220) * (1 - intensity))
            g2 = int(242 + (255 - 242) * (1 - intensity))
            b2 = int(220 + (255 - 220) * (1 - intensity))
            bg = f"rgb({r2},{g2},{b2})"
            txt = "#0A4A1A" if intensity > 0.35 else _BLK
        else:
            r2 = 255
            g2 = int(220 + (255 - 220) * (1 - intensity))
            b2 = int(220 + (255 - 220) * (1 - intensity))
            bg = f"rgb({r2},{g2},{b2})"
            txt = "#6A0A0A" if intensity > 0.35 else _BLK
        return bg, txt

    th = (f"padding:10px 14px;text-align:center;font-size:10px;font-weight:700;"
          f"letter-spacing:0.07em;color:{_LGR};background:#FAFAFA;"
          f"border-bottom:1px solid {_BRD};text-transform:uppercase")
    tbl  = (f'<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;'
            f'border:1px solid {_BRD}">')
    tbl += f'<thead><tr><th style="text-align:left;{th};min-width:140px"></th>'
    for lbl, _ in periods:
        tbl += f'<th style="{th}">{lbl}</th>'
    tbl += "</tr></thead><tbody>"

    for idx_name, col in rows:
        tbl += (f'<tr><td style="padding:13px 16px;font-size:14px;font-weight:600;'
                f'color:{_BLK};border-bottom:1px solid {_BRD};white-space:nowrap">'
                f'{idx_name}</td>')
        for _, kw in periods:
            v  = _pct_since(df, col, **kw)
            bg, txt = _cell_colors(v)
            vs = (f"+{v:.1f}%" if v > 0 else f"{v:.1f}%") if v is not None else "—"
            tbl += (f'<td style="padding:13px 14px;text-align:center;font-weight:700;'
                    f'font-size:13px;background:{bg};color:{txt};'
                    f'border-bottom:1px solid {_BRD}">{vs}</td>')
        tbl += "</tr>"
    tbl += "</tbody></table></div>"
    st.markdown(tbl, unsafe_allow_html=True)


def _s4_takeaway() -> None:
    """Section 4 — Monthly takeaway in Z47 brand style (no purple gradient)."""
    tk      = HARDCODED_INDEX_TAKEAWAY
    window  = tk.get("window", "")
    text    = tk.get("text", "")
    updated = tk.get("updated", "")

    _slabel(f"MONTHLY TAKEAWAY · {window.upper()}" if window else "MONTHLY TAKEAWAY")

    bullets = [ln.strip() for ln in text.splitlines() if ln.strip().startswith("•")]
    if not bullets:
        st.markdown(f'<p style="color:{_DGR}">{text}</p>', unsafe_allow_html=True)
        return

    items_html = ""
    for i, b in enumerate(bullets):
        content = b.lstrip("•").strip()
        is_first = i == 0
        is_watch = "What to watch:" in content
        if is_watch:
            content = content.replace(
                "What to watch:",
                f'<strong style="font-size:11px;letter-spacing:0.08em;'
                f'text-transform:uppercase;color:{_BLK}">WHAT TO WATCH &nbsp;·&nbsp;</strong>',
            )
        weight = "600" if is_first or is_watch else "400"
        mt     = "16px" if is_first else "10px"
        items_html += (
            f'<li style="margin-top:{mt};margin-bottom:0;font-weight:{weight};'
            f'line-height:1.65;color:{_BLK};list-style:none;'
            f'padding-left:18px;position:relative;">'
            f'<span style="position:absolute;left:0;color:{_OG};font-weight:800;font-size:16px;'
            f'line-height:1.2">•</span>'
            f'{content}</li>'
        )

    _today    = date.today()
    _days_fwd = (7 - _today.weekday()) % 7 or 7
    _next_mon = _today + timedelta(days=_days_fwd)
    _next_str = f"Monday {_next_mon.day} {_next_mon.strftime('%b')}"

    st.markdown(
        f'<div style="border-top:2px solid {_OG};border-bottom:1px solid {_BRD};'
        f'background:{_WHT};padding:28px 32px 24px;margin:8px 0">'
        f'<ul style="margin:0;padding:0">{items_html}</ul>'
        f'</div>'
        f'<p style="font-size:11px;color:{_LGR};margin-top:7px">'
        f'Last updated: {updated} &nbsp;·&nbsp; Next refresh: {_next_str}</p>',
        unsafe_allow_html=True,
    )


def _s5_movers(returns_1m: dict, name_map: dict) -> None:
    """Section 5 — Top 5 gainers & losers."""
    _slabel("TOP MOVERS · LAST MONTH")

    top5g = sorted(returns_1m.items(), key=lambda x: -x[1])[:5]
    top5l = sorted(returns_1m.items(), key=lambda x:  x[1])[:5]

    def _table(items, title, color):
        rows = "".join(
            f'<tr style="border-bottom:1px solid #F0F0F0">'
            f'<td style="padding:13px 0;font-size:14px;font-weight:500;color:{_BLK}">'
            f'{name_map.get(tk, tk)}</td>'
            f'<td style="padding:13px 6px;font-size:11px;color:{_LGR};font-family:monospace">'
            f'{tk}</td>'
            f'<td style="padding:13px 0;text-align:right;font-size:15px;font-weight:700;color:{color}">'
            f'{"+" if pct >= 0 else ""}{pct:.1f}%</td>'
            f'</tr>'
            for tk, pct in items
        )
        return (
            f'<div style="font-size:18px;font-weight:700;color:{_BLK};margin-bottom:2px">{title}</div>'
            f'<div style="font-size:10px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;'
            f'color:{_LGR};margin-bottom:10px">1 MONTH RETURN</div>'
            f'<table style="width:100%;border-collapse:collapse"><tbody>{rows}</tbody></table>'
        )

    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown(_table(top5g, "Top Gainers", _GRN), unsafe_allow_html=True)
    with c2:
        st.markdown(_table(top5l, "Top Losers", _RED), unsafe_allow_html=True)


def _s6_1m_chart(returns_1m: dict, name_map: dict) -> None:
    """Section 6 — 1-Month price movement, all 47 constituents."""
    _slabel("1-MONTH PRICE MOVEMENT · ALL CONSTITUENTS")

    items  = sorted(returns_1m.items(), key=lambda x: x[1])
    vals   = [v for _, v in items]
    names  = [name_map.get(t, t) for t, _ in items]
    colors = [_OG if v >= 0 else "#555555" for v in vals]
    labels = [f"{'+'  if v >= 0 else ''}{v:.1f}%" for v in vals]

    fig = go.Figure(go.Bar(
        x=vals, y=names, orientation="h",
        marker_color=colors,
        text=labels, textposition="outside",
        textfont=dict(size=10, color=_DGR, family=_FNT),
        hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor=_WHT, plot_bgcolor=_WHT,
        height=max(720, len(COMPANIES) * 18),
        xaxis=dict(
            showgrid=False, zeroline=True, zerolinecolor=_BRD, zerolinewidth=1.5,
            title="1-Month Return (%)",
            titlefont=dict(size=11, color=_LGR, family=_FNT),
            tickfont=dict(size=10, color=_LGR, family=_FNT),
        ),
        yaxis=dict(showgrid=False, tickfont=dict(size=11, color=_DGR, family=_FNT)),
        margin=dict(l=0, r=72, t=8, b=40),
        font=dict(family=_FNT),
        transition_duration=0,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _s7_constituents(returns_1m: dict, mcaps: dict,
                     price_cache: dict, usdinr: float) -> None:
    """Section 7 — Constituents table, sorted by market cap desc."""
    _slabel("CONSTITUENTS · LIVE PRICES")

    SHORT_SECTOR = {
        "Fintech / Financial Services": "Fintech",
        "Consumer / Consumer Tech": "Consumer Tech",
        "B2B": "B2B",
        "SaaS / AI": "SaaS / AI",
    }

    th = (f"padding:10px 14px;font-size:10px;font-weight:700;letter-spacing:0.07em;"
          f"color:{_LGR};text-transform:uppercase;border-bottom:1px solid {_BRD};"
          f"background:#FAFAFA;white-space:nowrap")

    tbl = (
        f'<div style="overflow-x:auto">'
        f'<table style="width:100%;border-collapse:collapse;border:1px solid {_BRD}">'
        f'<thead><tr>'
        f'<th style="text-align:left;{th}">Company</th>'
        f'<th style="text-align:left;{th}">Sector</th>'
        f'<th style="text-align:left;{th}">Ticker</th>'
        f'<th style="text-align:right;{th}">Price</th>'
        f'<th style="text-align:right;{th}">Day Chg</th>'
        f'<th style="text-align:right;{th}">1M Chg</th>'
        f'<th style="text-align:right;{th}">Mkt Cap (₹ Mn)</th>'
        f'</tr></thead><tbody>'
    )

    # Sort by live market cap desc (fall back to static)
    def _mcap_inr(c):
        mc = mcaps.get(c["ticker"])
        if mc:
            return mc["mc"] if mc["currency"] == "INR" else mc["mc"] * usdinr
        return c["mkt_cap_mn"]

    sorted_cos = sorted(COMPANIES, key=_mcap_inr, reverse=True)

    for c in sorted_cos:
        q   = price_cache.get(c["ticker"], {})
        px  = q.get("price")
        pct = q.get("pct_change")
        m1  = returns_1m.get(c["ticker"])
        mc  = mcaps.get(c["ticker"])

        if mc:
            mc_inr = round(mc["mc"] if mc["currency"] == "INR" else mc["mc"] * usdinr, 0)
        else:
            mc_inr = round(c["mkt_cap_mn"], 0)

        if px:
            px_str = f"₹{px:,.2f}" if c["exchange"] == "NSE" else f"${px:,.2f}"
        else:
            px_str = f'<span style="color:{_LGR}">—</span>'

        tbl += (
            f'<tr style="border-bottom:1px solid {_BRD}">'
            f'<td style="padding:12px 14px;font-size:14px;font-weight:500;color:{_BLK}">{c["name"]}</td>'
            f'<td style="padding:12px 14px;font-size:11px;color:{_LGR}">'
            f'{SHORT_SECTOR.get(c["sector"], c["sector"])}</td>'
            f'<td style="padding:12px 14px;font-size:12px;font-family:monospace;color:{_DGR}">'
            f'{c["ticker"]}</td>'
            f'<td style="padding:12px 14px;text-align:right;font-size:14px;font-weight:500;'
            f'color:{_BLK}">{px_str}</td>'
            f'<td style="padding:12px 14px;text-align:right;font-size:13px">{_chg_cell(pct)}</td>'
            f'<td style="padding:12px 14px;text-align:right;font-size:13px">{_chg_cell(m1)}</td>'
            f'<td style="padding:12px 14px;text-align:right;font-size:13px;color:{_DGR}">'
            f'{mc_inr:,.0f}</td>'
            f'</tr>'
        )

    tbl += f'</tbody></table></div>'
    st.markdown(tbl, unsafe_allow_html=True)
    st.caption(
        f"Prices via NSE / Yahoo Finance · Market cap live · "
        f"Sorted by market cap · USD/INR: ₹{usdinr:.2f}"
    )


def _s8_sector(returns_1m: dict) -> None:
    """Section 8 — Sector composition donut + list."""
    _slabel("SECTOR COMPOSITION")

    from collections import Counter
    counts  = Counter(c["sector"] for c in COMPANIES)
    sectors = list(counts.keys())
    vals    = [counts[s] for s in sectors]
    total   = sum(vals)
    # Monochromatic orange + grey palette
    palette = [_OG, "#FF9A5C", "#FFC39A", "#4A4A4A", "#888888"]
    colors  = (palette * 4)[:len(sectors)]

    SHORT = {
        "Fintech / Financial Services": "Fintech",
        "Consumer / Consumer Tech": "Consumer Tech",
        "B2B": "B2B",
        "SaaS / AI": "SaaS / AI",
    }
    labels = [SHORT.get(s, s) for s in sectors]

    fig = go.Figure(go.Pie(
        labels=labels, values=vals, hole=0.65,
        marker=dict(colors=colors, line=dict(color=_WHT, width=2)),
        textinfo="percent+label",
        textfont=dict(family=_FNT, size=10, color=_BLK),
        hovertemplate="%{label}: %{value} companies<extra></extra>",
        showlegend=False,
    ))
    fig.add_annotation(
        text=f"<b>{total}</b>",
        x=0.5, y=0.56, showarrow=False,
        font=dict(size=32, family=_FNT, color=_BLK),
    )
    fig.add_annotation(
        text="companies",
        x=0.5, y=0.43, showarrow=False,
        font=dict(size=11, family=_FNT, color=_LGR),
    )
    fig.update_layout(
        paper_bgcolor=_WHT, plot_bgcolor=_WHT, height=300,
        margin=dict(l=0, r=0, t=8, b=8),
        font=dict(family=_FNT),
        transition_duration=0,
    )

    cl, cr = st.columns([1, 1], gap="large")
    with cl:
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with cr:
        rows_html = ""
        for s, cnt in sorted(counts.items(), key=lambda x: -x[1]):
            w = cnt / total * 100
            rows_html += (
                f'<div style="display:flex;justify-content:space-between;align-items:center;'
                f'padding:11px 0;border-bottom:1px solid {_BRD}">'
                f'<span style="font-size:13px;color:{_BLK};font-weight:500">'
                f'{SHORT.get(s, s)}</span>'
                f'<span style="font-size:12px;color:{_LGR}">{cnt} co · {w:.1f}%</span>'
                f'</div>'
            )
        st.markdown(f'<div style="margin-top:20px">{rows_html}</div>', unsafe_allow_html=True)


def _s9_methodology() -> None:
    """Section 9 — Methodology."""
    _slabel("METHODOLOGY")

    points = [
        "47 listed Indian new-age tech and financial-services companies selected for their role in India's transition to a developed economy by 2047",
        "Equal-weight index rebased to 100 on 1 January 2024",
        "Constituents reviewed quarterly — additions on listing, removals on delisting or classification change",
        "Price data sourced from NSE / BSE via Yahoo Finance, with 15-minute live refresh during market hours",
        "Returns computed in INR terms; benchmark comparisons against Nifty 50 and BSE Sensex",
        "Sector classification follows Z47's internal taxonomy: Fintech / Financial Services · Consumer / Consumer Tech · B2B · SaaS / AI",
        "Data refresh cadence — prices: 15 min · index level: daily · takeaways: weekly (Monday auto-refresh)",
        "For informational purposes only. Not investment advice.",
    ]
    items = "".join(
        f'<li style="margin-bottom:10px;color:{_DGR};font-size:14px;line-height:1.65;'
        f'list-style:none;padding-left:18px;position:relative">'
        f'<span style="position:absolute;left:0;color:{_OG};font-weight:700">•</span>'
        f'{p}</li>'
        for p in points
    )
    st.markdown(f'<ul style="margin:0;padding:0">{items}</ul>', unsafe_allow_html=True)


def _s10_footer(usdinr: float) -> None:
    """Section 10 — System status + disclaimer footer."""
    now_ts  = datetime.now().strftime("%H:%M IST · %d %b %Y")
    updated = HARDCODED_INDEX_TAKEAWAY.get("updated", "—")

    st.markdown(
        f'<div style="margin-top:20px;padding:12px 0;border-top:1px solid {_BRD}">'
        f'<p style="font-size:11px;color:{_LGR}">'
        f'<b style="font-size:10px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;'
        f'color:{_DGR}">DATA STATUS</b>'
        f'&nbsp;·&nbsp; Index: today'
        f'&nbsp;·&nbsp; Prices: live {now_ts}'
        f'&nbsp;·&nbsp; FX: ₹{usdinr:.2f}'
        f'&nbsp;·&nbsp; Takeaway: {updated}'
        f'</p></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div style="padding:28px 0 16px;text-align:center;border-top:1px solid {_BRD}">'
        f'<p style="font-size:12px;color:{_LGR};line-height:1.75;max-width:680px;margin:0 auto">'
        f'The Z47fortyseven Index is published by Z47 for informational and discussion purposes only. '
        f'It does not constitute investment advice. Past performance is not indicative of future results. '
        f'Constituent data and prices are sourced from public exchanges and third-party data providers.'
        f'</p>'
        f'<p style="font-size:12px;color:{_LGR};margin-top:12px">'
        f'<a href="https://www.z47.com" target="_blank" '
        f'style="color:{_OG};text-decoration:none;font-weight:600">z47.com</a>'
        f'&nbsp;·&nbsp; © 2026 Z47'
        f'</p></div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def render() -> None:
    """Render the Z47fortyseven public-facing page."""
    # Auto-refresh every 5 minutes (same cadence as Z47'47 tab)
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=300_000, key="z47fs_autorefresh")

    # ── Inject brand CSS ──────────────────────────────────────────────────────
    st.markdown(_BRAND_CSS, unsafe_allow_html=True)

    # ── Page header ───────────────────────────────────────────────────────────
    st.markdown(
        f'<div class="z47fs" style="padding:28px 0 4px">'
        f'<h1 style="font-size:34px;font-weight:800;color:{_BLK};'
        f'margin:0;letter-spacing:-0.5px">'
        f'Z47<em style="font-style:italic">fortyseven</em>'
        f'</h1>'
        f'<p style="font-size:14px;color:{_DGR};margin-top:5px">'
        f"India's index of 47 new-age tech and financial-services companies"
        f'</p></div>',
        unsafe_allow_html=True,
    )

    # ── Load all data (parallel where possible) ───────────────────────────────
    with st.spinner(""):
        nifty_live, sensex_live, usdinr, fx_chg = _live_indices()
        hist       = _load_history()
        df         = _extend_history(hist, nifty_live, sensex_live)
        returns_1m = _fetch_1m_returns()
        mcaps      = _fetch_mcaps()

        # Live prices — parallel fetch for all 47
        price_cache: dict = {}
        def _fp(c):
            return c["ticker"], _fetch_price(c["ticker"], c["exchange"])
        with ThreadPoolExecutor(max_workers=12) as ex:
            for tk, pd_data in ex.map(_fp, COMPANIES):
                price_cache[tk] = pd_data

    name_map = {c["ticker"]: c["name"] for c in COMPANIES}

    # ── Render all 10 sections inside brand wrapper ───────────────────────────
    st.markdown('<div class="z47fs">', unsafe_allow_html=True)

    # S1 — Hero
    _s1_hero(df, nifty_live, sensex_live, usdinr, fx_chg)
    _divider()

    # S2 — Performance chart
    _s2_performance(df)
    _divider()

    # S3 — Returns heatmap
    _s3_returns(df)
    _divider()

    # S4 — Monthly takeaway
    _s4_takeaway()
    _divider()

    # S5 — Top movers
    if returns_1m:
        _s5_movers(returns_1m, name_map)
        _divider()

    # S6 — 1M chart all constituents
    if returns_1m:
        _s6_1m_chart(returns_1m, name_map)
        _divider()

    # S7 — Constituents table
    _s7_constituents(returns_1m, mcaps, price_cache, usdinr)
    _divider()

    # S8 — Sector composition
    _s8_sector(returns_1m)
    _divider()

    # S9 — Methodology
    _s9_methodology()

    # S10 — Footer
    _s10_footer(usdinr)

    st.markdown('</div>', unsafe_allow_html=True)
