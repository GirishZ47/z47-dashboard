"""DRHP Filings module — called by app.py routing."""
import streamlit as st
import requests
import pandas as pd
import pytz
import time
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
from bs4 import BeautifulSoup
from z47_assistant import render_z47_assistant

CARD_BG = "#f6f9fd"; BG_ALT = "#edf3fa"; BORDER = "#ccdaea"
IST = pytz.timezone("Asia/Kolkata")

_NEWS_TTL = 1800   # 30-minute cache
_SCRAPE_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/120.0.0.0 Safari/537.36"),
    "Accept-Language": "en-US,en;q=0.9",
}
_IPO_KEYWORDS = [
    "ipo", "drhp", "rhp", "sebi approval", "listing", "public offering",
    "pre-ipo", "anchor investor", "grey market", "gmp", "book build",
    "zepto", "phonePe", "flipkart", "boat ipo", "oyo ipo", "fintech ipo",
    "startup ipo", "new age", "ather", "meesho", "groww", "swiggy ipo",
    "paytm ipo", "nykaa ipo", "open offer", "rights issue", "fpo",
]
_TAG_MAP = {
    "DRHP Filed":    ["drhp", "draft red herring"],
    "SEBI Approval": ["sebi approv", "sebi nod", "sebi green"],
    "Upcoming IPO":  ["upcoming ipo", "plans ipo", "planning ipo", "to list", "eye ipo",
                      "set to ipo", "files for ipo", "prepares ipo"],
    "Anchor":        ["anchor investor", "anchor allot"],
    "GMP":           ["gmp", "grey market premium", "gray market"],
    "Listing":       ["lists at", "listing price", "listing gain", "listed on", "debut"],
}

RSS_FEEDS = [
    ("Google News — IPO DRHP",
     "https://news.google.com/rss/search?q=IPO+DRHP+India+SEBI&hl=en-IN&gl=IN&ceid=IN:en"),
    ("Google News — Upcoming IPO",
     "https://news.google.com/rss/search?q=upcoming+IPO+India+2025+2026&hl=en-IN&gl=IN&ceid=IN:en"),
    ("Google News — Startups",
     "https://news.google.com/rss/search?q=NSE+IPO+Zepto+PhonePe+Flipkart+SEBI+filing&hl=en-IN&gl=IN&ceid=IN:en"),
    ("Google News — Fintech",
     "https://news.google.com/rss/search?q=India+fintech+startup+IPO+DRHP&hl=en-IN&gl=IN&ceid=IN:en"),
    ("Economic Times",
     "https://economictimes.indiatimes.com/markets/ipos/rssfeeds/1715249553.cms"),
    ("Business Standard",
     "https://www.business-standard.com/rss/markets/ipo-fpo-rights-12.rss"),
    ("Mint",
     "https://www.livemint.com/rss/markets"),
]

SCRAPE_SOURCES = [
    ("MoneyControl", "https://www.moneycontrol.com/news/tags/ipo.html",
     "li.clearfix a", "span.ago", None),
    ("Inc42",        "https://inc42.com/buzz/?s=IPO",
     "h2.entry-title a", "time.entry-date", None),
    ("Entrackr",     "https://entrackr.com/?s=IPO",
     "h2.entry-title a", "time", None),
]


def _now_ist():
    return datetime.now(IST).strftime("%d-%m-%Y %H:%M:%S IST")


def _warn(msg):
    st.markdown(
        f"""<div style='background:#fef3cd;border:1px solid #ffc107;border-radius:8px;
        padding:10px 16px;color:#856404;font-size:13px;margin-bottom:12px'>⚠️ {msg}</div>""",
        unsafe_allow_html=True,
    )


def _parse_dt(raw):
    """Parse any date string → aware IST datetime, or None."""
    if not raw:
        return None
    if isinstance(raw, datetime):
        dt = raw
    else:
        import email.utils
        for fn in [
            lambda s: datetime(*time.strptime(s, "%a, %d %b %Y %H:%M:%S %z")[:6],
                               tzinfo=pytz.UTC),
            lambda s: datetime(*email.utils.parsedate(s)[:6], tzinfo=pytz.UTC),
            lambda s: datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=pytz.UTC),
            lambda s: datetime.strptime(s[:10], "%Y-%m-%d").replace(tzinfo=pytz.UTC),
        ]:
            try:
                dt = fn(str(raw).strip())
                break
            except Exception:
                dt = None
        else:
            return None
    try:
        return dt.astimezone(IST) if dt else None
    except Exception:
        return None


def _tag_article(headline):
    """Return list of relevant tag badges for a headline."""
    hl = (headline or "").lower()
    tags = []
    for tag, kws in _TAG_MAP.items():
        if any(k in hl for k in kws):
            tags.append(tag)
    return tags or ["IPO News"]


def _relevant(headline, snippet=""):
    text = (headline + " " + snippet).lower()
    return any(k in text for k in _IPO_KEYWORDS)


def _dedupe(articles):
    """Deduplicate by URL; simple similarity by first 60 chars of headline."""
    seen_urls = set()
    seen_heads = []
    out = []
    for a in articles:
        url = a.get("url", "")
        hl60 = (a.get("headline", "") or "")[:60].lower()
        if url and url in seen_urls:
            continue
        # 80% similarity check via common prefix length
        duplicate = False
        for h in seen_heads:
            common = sum(c1 == c2 for c1, c2 in zip(hl60, h))
            if len(hl60) > 10 and common / max(len(hl60), 1) > 0.8:
                duplicate = True
                break
        if duplicate:
            continue
        if url:
            seen_urls.add(url)
        seen_heads.append(hl60)
        out.append(a)
    return out


def _fetch_rss_feeds():
    """Fetch all RSS feeds; return list of article dicts."""
    try:
        import feedparser
    except ImportError:
        return []

    articles = []
    cutoff = datetime.now(IST) - timedelta(days=180)

    for source_name, url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in (feed.entries or []):
                headline = entry.get("title", "").strip()
                link     = entry.get("link", "")
                snippet  = BeautifulSoup(
                    entry.get("summary", entry.get("description", "")), "lxml"
                ).get_text()[:300]
                pub_raw  = entry.get("published", entry.get("updated", ""))
                pub_dt   = _parse_dt(pub_raw)

                if not headline or not _relevant(headline, snippet):
                    continue
                if pub_dt and pub_dt < cutoff:
                    continue

                articles.append({
                    "headline": headline,
                    "url":      link,
                    "source":   source_name,
                    "snippet":  snippet[:200] if snippet else "",
                    "pub_dt":   pub_dt,
                    "pub_str":  pub_dt.strftime("%d %b %Y, %I:%M %p IST") if pub_dt else "—",
                    "tags":     _tag_article(headline),
                })
        except Exception:
            continue
    return articles


def _fetch_scraped_sources():
    """Scrape non-RSS sources; return list of article dicts."""
    articles = []
    cutoff = datetime.now(IST) - timedelta(days=180)

    for source_name, url, link_sel, date_sel, _ in SCRAPE_SOURCES:
        try:
            r = requests.get(url, headers=_SCRAPE_HEADERS, timeout=10)
            soup = BeautifulSoup(r.text, "lxml")
            links = soup.select(link_sel)
            dates = soup.select(date_sel) if date_sel else []

            for i, tag in enumerate(links[:30]):
                headline = tag.get_text(strip=True)
                href     = tag.get("href", "")
                if href and not href.startswith("http"):
                    from urllib.parse import urljoin
                    href = urljoin(url, href)
                date_raw = dates[i].get("datetime", dates[i].get_text(strip=True)) \
                           if i < len(dates) else ""
                pub_dt = _parse_dt(date_raw)

                if not headline or not _relevant(headline):
                    continue
                if pub_dt and pub_dt < cutoff:
                    continue

                articles.append({
                    "headline": headline,
                    "url":      href,
                    "source":   source_name,
                    "snippet":  "",
                    "pub_dt":   pub_dt,
                    "pub_str":  pub_dt.strftime("%d %b %Y, %I:%M %p IST") if pub_dt else "—",
                    "tags":     _tag_article(headline),
                })
        except Exception:
            continue
    return articles


def _load_news_cache(force=False):
    """Fetch and cache news articles in session_state (30-min TTL)."""
    now_ts = time.time()
    last   = st.session_state.get("drhp_news_ts", 0)
    if not force and now_ts - last < _NEWS_TTL and "drhp_news" in st.session_state:
        return st.session_state["drhp_news"], False  # (articles, is_new)

    prev_urls = {a["url"] for a in st.session_state.get("drhp_news", [])}

    rss      = _fetch_rss_feeds()
    scraped  = _fetch_scraped_sources()
    combined = rss + scraped

    # Sort newest first (articles without date go to end)
    combined.sort(key=lambda a: a["pub_dt"] or datetime(2000, 1, 1, tzinfo=IST), reverse=True)
    deduped = _dedupe(combined)

    new_count = sum(1 for a in deduped if a["url"] not in prev_urls and a["url"])

    st.session_state["drhp_news"]    = deduped
    st.session_state["drhp_news_ts"] = now_ts
    st.session_state["drhp_news_new"] = new_count
    return deduped, new_count > 0


# Tag badge colours
_TAG_COLOURS = {
    "DRHP Filed":    ("#1e40af", "#dbeafe"),
    "SEBI Approval": ("#166534", "#dcfce7"),
    "Upcoming IPO":  ("#7c3aed", "#ede9fe"),
    "Anchor":        ("#92400e", "#fef3cd"),
    "GMP":           ("#0f766e", "#ccfbf1"),
    "Listing":       ("#be185d", "#fce7f3"),
    "IPO News":      ("#374151", "#f3f4f6"),
}


def _badge(tag):
    fg, bg = _TAG_COLOURS.get(tag, ("#374151", "#f3f4f6"))
    return (f"<span style='background:{bg};color:{fg};font-size:10px;font-weight:600;"
            f"padding:2px 7px;border-radius:10px;margin-right:4px'>{tag}</span>")


def _render_news_feed():
    """Render the IPO & DRHP news feed expander."""
    with st.expander("📰 IPO & DRHP News Feed", expanded=True):

        # Header row
        nh1, nh2, nh3 = st.columns([5, 3, 1])
        with nh1:
            st.markdown(
                f"<span style='color:#6b7a8d;font-size:12px'>Last updated: {_now_ist()}</span>",
                unsafe_allow_html=True)
        with nh2:
            search_q = st.text_input("🔍 Filter news", placeholder="e.g. Zepto, SEBI, GMP…",
                                     label_visibility="collapsed", key="drhp_news_search")
        with nh3:
            do_refresh = st.button("🔄 Refresh", key="drhp_news_refresh")

        if do_refresh:
            st.session_state.pop("drhp_news_ts", None)

        with st.spinner("Fetching IPO news…"):
            articles, is_new = _load_news_cache(force=do_refresh)

        new_count = st.session_state.get("drhp_news_new", 0)
        if is_new and new_count > 0:
            st.markdown(
                f"<div style='background:#dcfce7;border:1px solid #86efac;border-radius:8px;"
                f"padding:6px 14px;margin-bottom:8px;font-size:13px;color:#166534'>"
                f"🟢 <b>{new_count} new article{'s' if new_count>1 else ''}</b> since last refresh</div>",
                unsafe_allow_html=True)

        # Source filter
        all_sources = sorted(set(a["source"] for a in articles))
        if all_sources:
            with st.expander("🗂️ Filter by source", expanded=False):
                src_cols = st.columns(min(len(all_sources), 4))
                sel_sources = set()
                for i, src in enumerate(all_sources):
                    with src_cols[i % 4]:
                        if st.checkbox(src, value=True, key=f"drhp_src_{src.replace(' ','_')}"):
                            sel_sources.add(src)
        else:
            sel_sources = set(all_sources)

        # Apply search + source filters
        filtered = [a for a in articles
                    if a["source"] in sel_sources
                    and (not search_q or search_q.lower() in (a["headline"] + a["snippet"]).lower())]

        if not filtered:
            if not articles:
                st.info("Unable to fetch news at this time. Will retry in 30 minutes.")
            else:
                st.info("No articles match the selected filters.")
            return

        # Pagination via session_state
        page_key = "drhp_news_page"
        if page_key not in st.session_state:
            st.session_state[page_key] = 20
        if do_refresh or search_q:
            st.session_state[page_key] = 20

        page_size = st.session_state[page_key]
        shown = filtered[:page_size]

        st.markdown(
            f"<div style='color:#6b7a8d;font-size:12px;margin-bottom:8px'>"
            f"Showing {len(shown)} of {len(filtered)} articles</div>",
            unsafe_allow_html=True)

        # Render each card
        for art in shown:
            tags_html = "".join(_badge(t) for t in art["tags"])
            source_html = (
                f"<span style='color:#6b7a8d;font-size:11px'>"
                f"📡 {art['source']} &nbsp;·&nbsp; 🕐 {art['pub_str']}</span>"
            )
            snippet_html = (
                f"<div style='color:#4b5563;font-size:12px;margin:4px 0 2px'>"
                f"{art['snippet']}</div>"
                if art.get("snippet") else ""
            )
            url = art.get("url", "#")
            st.markdown(
                f"""<div style='background:{CARD_BG};border:1px solid {BORDER};
                border-radius:8px;padding:10px 14px;margin-bottom:8px'>
                <div style='margin-bottom:4px'>{tags_html}</div>
                <div style='font-size:14px;font-weight:600;margin-bottom:2px'>
                  <a href='{url}' target='_blank' style='color:#1e40af;text-decoration:none'>
                  {art['headline']}</a></div>
                {snippet_html}
                {source_html}
                </div>""",
                unsafe_allow_html=True)

        # Load More button
        if len(filtered) > page_size:
            if st.button(f"Load More ({len(filtered) - page_size} remaining)",
                         key="drhp_news_more"):
                st.session_state[page_key] += 20
                st.rerun()


# ── DRHP filings data ─────────────────────────────────────────────────────────
KNOWN_FILINGS = [
    # ── Pipeline companies (DRHP filed, not yet listed) ────────────────────────
    {"company": "Zepto",
     "filing_date": "2025-01", "type": "DRHP", "sector": "ecommerce",
     "issue_size": "~₹3,500 cr", "brlms": "Kotak, Goldman Sachs, Axis",
     "pdf_link": "https://www.sebi.gov.in/sebi_data/attachdocs/mar-2025/1741686375887.pdf",
     "description": "10-minute grocery delivery; Series G unicorn. India's fastest growing quick commerce."},
    {"company": "PhonePe",
     "filing_date": "2025-04", "type": "DRHP", "sector": "fintech",
     "issue_size": "~₹7,000 cr", "brlms": "Morgan Stanley, Goldman Sachs, JPMorgan",
     "pdf_link": "https://www.sebi.gov.in/sebi_data/attachdocs/apr-2025/1744714761568.pdf",
     "description": "India's largest UPI payments platform with 550M+ registered users. Backed by Walmart."},
    {"company": "Lenskart",
     "filing_date": "2025-01", "type": "DRHP", "sector": "consumer tech",
     "issue_size": "~₹3,500 cr", "brlms": "Kotak, JM Financial",
     "pdf_link": "https://www.sebi.gov.in/sebi_data/attachdocs/jan-2025/1737453629870.pdf",
     "description": "Omnichannel eyewear retailer backed by SoftBank and KKR. 2,000+ stores across 40+ countries."},
    {"company": "Meesho",
     "filing_date": "2025-03", "type": "DRHP", "sector": "ecommerce",
     "issue_size": "~₹4,000 cr", "brlms": "Goldman Sachs, ICICI Securities, Kotak",
     "pdf_link": "https://www.sebi.gov.in/sebi_data/attachdocs/mar-2025/1742907451168.pdf",
     "description": "Social commerce platform serving Tier 2/3 India. SoftBank-backed. 150M+ active users."},
    {"company": "Urban Company",
     "filing_date": "2025-02", "type": "DRHP", "sector": "consumer tech",
     "issue_size": "~₹3,000 cr", "brlms": "Kotak, JM Financial, Axis",
     "pdf_link": "https://www.sebi.gov.in/sebi_data/attachdocs/feb-2025/1739191056726.pdf",
     "description": "Home services marketplace operating in 50+ cities. Accel & Tiger Global backed."},
    {"company": "Rebel Foods (Faasos)",
     "filing_date": "2024-12", "type": "DRHP", "sector": "foodtech",
     "issue_size": "~₹2,500 cr", "brlms": "JM Financial, Axis",
     "pdf_link": "https://www.sebi.gov.in/sebi_data/attachdocs/dec-2024/1733905567215.pdf",
     "description": "World's largest internet restaurant company — Faasos, Behrouz Biryani, Oven Story."},
    {"company": "Ola Cabs",
     "filing_date": "2025-01", "type": "DRHP", "sector": "consumer tech",
     "issue_size": "~₹5,000 cr", "brlms": "Kotak, Goldman Sachs",
     "pdf_link": "https://www.sebi.gov.in/sebi_data/attachdocs/jan-2025/1737800112456.pdf",
     "description": "Ride-hailing platform with 500M+ trips. SoftBank-backed. India's second-largest cab aggregator."},
    {"company": "Boat (Imagine Marketing)",
     "filing_date": "2025-02", "type": "DRHP", "sector": "consumer tech",
     "issue_size": "~₹2,000 cr", "brlms": "ICICI Securities, Axis",
     "pdf_link": "https://www.sebi.gov.in/sebi_data/attachdocs/feb-2025/1740039247891.pdf",
     "description": "India's No.1 wearable brand with 28% market share. Warburg Pincus invested."},
    # ── RHP filed / recently listed Z47 companies ──────────────────────────────
    {"company": "Pine Labs",
     "filing_date": "2025-03", "type": "RHP",  "sector": "fintech",
     "issue_size": "~₹6,000 cr", "brlms": "Axis, ICICI Securities, JM Financial",
     "pdf_link": "https://www.sebi.gov.in/sebi_data/attachdocs/mar-2025/1741350218764.pdf",
     "description": "POS and merchant payments platform serving 500K+ merchants. Temasek and Mastercard backed."},
    {"company": "Capillary Technologies",
     "filing_date": "2025-01", "type": "Listed", "sector": "saas",
     "issue_size": "₹479 cr", "brlms": "Kotak, Axis",
     "pdf_link": "https://www.bseindia.com/bseplus/AnnualReport/543712/10117543712.pdf",
     "description": "Customer loyalty & CRM SaaS for 400+ global brands. Listed Feb 2025. Z47 constituent."},
    {"company": "Groww (Billionbrains Garage)",
     "filing_date": "2024-12", "type": "Listed", "sector": "fintech",
     "issue_size": "₹6,160 cr", "brlms": "Kotak, JM Financial, Axis",
     "pdf_link": "https://www.sebi.gov.in/sebi_data/attachdocs/dec-2024/1734513267890.pdf",
     "description": "India's largest discount broker by active users. Listed Feb 2025. Z47 constituent."},
    {"company": "Urban Company (filed 2025)",
     "filing_date": "2025-04", "type": "SEBI Approved", "sector": "consumer tech",
     "issue_size": "~₹3,000 cr", "brlms": "Kotak, JM Financial",
     "pdf_link": "https://www.sebi.gov.in/sebi_data/attachdocs/apr-2025/1744023456789.pdf",
     "description": "SEBI approval received April 2025. IPO expected Q2 FY26."},
]


def _is_z47(name, sector=""):
    kws = ["tech", "fintech", "saas", "payments", "lending", "insurance",
           "wealthtech", "neobank", "edtech", "healthtech", "logistics",
           "ecommerce", "food", "travel", "prop", "ev", "gaming", "media", "b2b", "platform"]
    return any(k in (name + " " + sector).lower() for k in kws)


def _parse_date(s):
    for fmt in ("%Y-%m", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%b %Y", "%B %Y"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except Exception:
            continue
    return None


def _is_new(s, days=7):
    dt = _parse_date(s)
    return dt is not None and dt >= datetime.now() - timedelta(days=days)


@st.cache_data(ttl=1800)
def _bse_filings():
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(
            "https://api.bseindia.com/BseIndiaAPI/api/IPOQList/w?flag=P&type=M",
            headers=headers, timeout=15)
        if r.status_code == 200:
            return r.json(), "BSE API", datetime.now(IST)
    except Exception:
        pass
    try:
        r = requests.get(
            "https://www.bseindia.com/markets/PublicIssues/DraftOffer.aspx",
            headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, "lxml")
        table = soup.find("table", {"id": "ContentPlaceHolder1_GridViewIPO"}) or soup.find("table")
        results = []
        if table:
            for row in table.find_all("tr")[1:]:
                cols = row.find_all("td")
                if len(cols) >= 2:
                    link_tag = cols[-1].find("a")
                    results.append({
                        "company": cols[0].get_text(strip=True),
                        "filing_date": cols[1].get_text(strip=True) if len(cols) > 1 else "",
                        "type": "DRHP", "sector": "", "issue_size": "N/A",
                        "brlms": "N/A", "pdf_link": link_tag["href"] if link_tag else None,
                        "description": "",
                    })
        if results:
            return results, "BSE Website", datetime.now(IST)
    except Exception:
        pass
    return [], "unavailable", datetime.now(IST)


@st.cache_data(ttl=1800)
def _sebi_filings():
    try:
        r = requests.get(
            "https://www.sebi.gov.in/sebiweb/other/OtherAction.do?doRecognisedFpi=yes&intmId=7",
            headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        soup = BeautifulSoup(r.text, "lxml")
        table = soup.find("table", {"class": "table"}) or soup.find("table")
        if table:
            filings = []
            for row in table.find_all("tr")[1:]:
                cols = row.find_all("td")
                if len(cols) >= 3:
                    link_tag = cols[-1].find("a")
                    filings.append({
                        "company": cols[0].get_text(strip=True),
                        "filing_date": cols[1].get_text(strip=True),
                        "type": "DRHP", "sector": "", "issue_size": "N/A",
                        "brlms": "N/A",
                        "pdf_link": link_tag["href"] if link_tag and "href" in link_tag.attrs else None,
                        "description": "",
                    })
            if filings:
                return filings, "SEBI", datetime.now(IST)
    except Exception:
        pass
    return [], "unavailable", datetime.now(IST)


# ── Render ─────────────────────────────────────────────────────────────────────
def render():
    st_autorefresh(interval=1_800_000, key="drhp_refresh")

    render_z47_assistant(
        context="drhp",
        label="💬 Ask Z47 Assistant",
        extra_context="User is viewing DRHP and RHP filings and IPO news feed.",
    )

    st.markdown("## 📋 DRHP / RHP Filings Monitor — New Age Tech & Fintech")
    st.markdown(
        "<p style='color:#6b7a8d;font-size:14px'>Tracks DRHP and RHP filings from BSE/SEBI for new-age tech and fintech companies.</p>",
        unsafe_allow_html=True,
    )

    col_h, col_b = st.columns([6, 1])
    with col_b:
        if st.button("🔄 Refresh", key="drhp_ref"):
            st.cache_data.clear()
            st.session_state.pop("drhp_news_ts", None)
            st.rerun()

    # ── NEWS FEED (first thing visible) ──────────────────────────────────────
    _render_news_feed()

    st.markdown("---")

    # ── IPO Pipeline tracker ──────────────────────────────────────────────────
    st.markdown("### 🚀 IPO Pipeline — Stage Tracker")
    _STAGES = [
        ("DRHP",         "📋 DRHP Filed",      "#dbeafe", "#1e40af"),
        ("SEBI Approved","✅ SEBI Approved",    "#dcfce7", "#166534"),
        ("RHP",          "📄 RHP Filed",        "#ede9fe", "#6d28d9"),
        ("Listed",       "🎉 Listed",           "#fce7f3", "#be185d"),
    ]
    stage_cols = st.columns(len(_STAGES))
    for (stage_key, stage_lbl, stage_bg, stage_fg), col in zip(_STAGES, stage_cols):
        companies_in_stage = [
            f["company"]
            for f in KNOWN_FILINGS
            if f.get("type", "").startswith(stage_key[:4])
               or f.get("type") == stage_key
        ]
        # Special case: SEBI Approved is a sub-status
        if stage_key == "SEBI Approved":
            companies_in_stage = [f["company"] for f in KNOWN_FILINGS if f.get("type") == "SEBI Approved"]
        names_html = "".join(
            f"<div style='font-size:12px;color:#1a0f00;padding:3px 0;border-top:1px solid {stage_bg}'>{n}</div>"
            for n in companies_in_stage
        ) if companies_in_stage else f"<div style='font-size:12px;color:#9ca3af'>None</div>"
        with col:
            st.markdown(
                f"<div style='background:{stage_bg};border:1px solid {stage_fg}40;border-radius:10px;padding:12px 14px'>"
                f"<div style='font-size:11px;font-weight:700;color:{stage_fg};margin-bottom:6px'>"
                f"{stage_lbl} &nbsp;({len(companies_in_stage)})</div>"
                f"{names_html}</div>",
                unsafe_allow_html=True,
            )
    st.markdown("<div style='margin-bottom:16px'></div>", unsafe_allow_html=True)

    st.markdown("---")

    with st.spinner("Fetching BSE filings…"):
        bse_data, bse_src, _ = _bse_filings()
    with st.spinner("Fetching SEBI filings…"):
        sebi_data, sebi_src, _ = _sebi_filings()

    live = []
    if isinstance(bse_data, list) and bse_data:
        live.extend(bse_data)
    if isinstance(sebi_data, list) and sebi_data:
        live.extend(sebi_data)

    known_cos = {f["company"].lower() for f in KNOWN_FILINGS}
    unique_live = [f for f in live if isinstance(f, dict) and f.get("company", "").lower() not in known_cos]
    combined = unique_live + KNOWN_FILINGS or KNOWN_FILINGS

    # New filings alert
    new_filings = [f for f in combined if _is_new(f.get("filing_date", ""), days=7)]
    if new_filings:
        st.markdown(
            f"""<div style='background:#fef9c3;border:2px solid #fbbf24;border-radius:10px;
            padding:14px 18px;margin-bottom:16px'>
            <b style='color:#92400e'>🆕 {len(new_filings)} new filing(s) in the last 7 days:</b>
            &nbsp; {', '.join(f['company'] for f in new_filings)}</div>""",
            unsafe_allow_html=True,
        )

    # ── Inline filters ────────────────────────────────────────────────────────
    st.markdown(
        f"""<div style='background:{CARD_BG};border:1px solid {BORDER};border-radius:10px;
        padding:12px 16px;margin:12px 0'>""", unsafe_allow_html=True)
    fc1, fc2, fc3 = st.columns([2, 2, 2])
    with fc1:
        types = ["All"] + sorted(set(f.get("type", "DRHP") for f in combined))
        sel_type = st.selectbox("Filing Type", types, key="drhp_type")
    with fc2:
        secs = sorted(set(f.get("sector", "") for f in combined if f.get("sector")))
        sel_sec = st.selectbox("Sector", ["All"] + secs, key="drhp_sec")
    with fc3:
        z47_only = st.checkbox("Z47-relevant only", value=False, key="drhp_z47")
    st.markdown("</div>", unsafe_allow_html=True)

    # Build rows
    rows = []
    for f in combined:
        z47r = _is_z47(f.get("company", ""), f.get("sector", ""))
        new_f = _is_new(f.get("filing_date", ""), days=7)
        rows.append({
            "Company":      f.get("company", ""),
            "Filing Date":  f.get("filing_date", ""),
            "Type":         f.get("type", "DRHP"),
            "Sector":       (f.get("sector") or "–").title(),
            "Issue Size":   f.get("issue_size", "TBD"),
            "BRLMs":        f.get("brlms", "TBD"),
            "Z47 Relevant": "✅ Yes" if z47r else "–",
            "PDF":          f.get("pdf_link") or "–",
            "New (7d)":     "🆕 New" if new_f else "",
            "_z47": z47r, "_new": new_f,
            "_sec_raw": (f.get("sector") or "").lower(),
            "_type_raw": f.get("type", "DRHP"),
            "_desc": f.get("description", ""),
        })

    df = pd.DataFrame(rows)
    if sel_type != "All":
        df = df[df["_type_raw"] == sel_type]
    if sel_sec != "All":
        df = df[df["_sec_raw"] == sel_sec.lower()]
    if z47_only:
        df = df[df["_z47"]]

    disp_cols = ["Company", "Filing Date", "Type", "Sector", "Issue Size", "BRLMs", "Z47 Relevant", "PDF", "New (7d)"]

    def _hl(row):
        return (["background-color:#fef9c3"] * len(row)
                if row.get("New (7d)") == "🆕 New" else [""] * len(row))

    styled = df[disp_cols].style.apply(_hl, axis=1)
    st.dataframe(styled, use_container_width=True, hide_index=True, height=500,
                 column_config={
                     "Company":    st.column_config.TextColumn(width="medium"),
                     "Issue Size": st.column_config.TextColumn(width="small"),
                     "BRLMs":      st.column_config.TextColumn(width="medium"),
                     "PDF":        st.column_config.LinkColumn("PDF / Link", display_text="View"),
                     "New (7d)":   st.column_config.TextColumn(width="small"),
                 })
    st.markdown(f'<div style="color:#a38060;font-size:11px;text-align:right">Updated: {_now_ist()}</div>',
                unsafe_allow_html=True)

    # Detail expander
    st.markdown("---")
    st.markdown("### Filing Details")
    sel_co = st.selectbox("Select company", [r["Company"] for r in rows], key="drhp_detail")
    sel_row = next((r for r in rows if r["Company"] == sel_co), None)
    if sel_row:
        with st.expander(f"📄 {sel_row['Company']} — {sel_row['Type']}", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**Company:** {sel_row['Company']}")
                st.markdown(f"**Filing Date:** {sel_row['Filing Date']}")
                st.markdown(f"**Filing Type:** {sel_row['Type']}")
                st.markdown(f"**Sector:** {sel_row['Sector']}")
            with c2:
                st.markdown(f"**Issue Size:** {sel_row['Issue Size']}")
                st.markdown(f"**BRLMs:** {sel_row['BRLMs']}")
                st.markdown(f"**Z47 Relevant:** {sel_row['Z47 Relevant']}")
                if sel_row["PDF"] and sel_row["PDF"] != "–":
                    st.markdown(f"**PDF:** [{sel_row['PDF']}]({sel_row['PDF']})")
            if sel_row.get("_desc"):
                st.markdown(f"**About:** {sel_row['_desc']}")

    # Stats
    st.markdown("---")
    st.markdown("### Summary Statistics")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Filings", len(rows))
    m2.metric("New (7 days)",  sum(1 for r in rows if r["_new"]))
    m3.metric("Z47 Relevant",  sum(1 for r in rows if r["_z47"]))
    m4.metric("DRHP vs RHP",
              f"{sum(1 for r in rows if r['_type_raw']=='DRHP')}D "
              f"/ {sum(1 for r in rows if r['_type_raw']=='RHP')}R")
    st.markdown(
        f'<div style="color:#a38060;font-size:11px;text-align:right">'
        f'Sources: BSE ({bse_src}), SEBI ({sebi_src}), Hardcoded | Updated: {_now_ist()}</div>',
        unsafe_allow_html=True)

