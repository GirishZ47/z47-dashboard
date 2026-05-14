"""Reusable Z47 Assistant — renders a collapsible chat UI on any page/tab."""
import os
import streamlit as st
import anthropic

# ── Model & tool constants ────────────────────────────────────────────────────
_SEARCH_MODEL    = "claude-sonnet-4-6"   # web search needs stronger reasoning
_STREAM_MODEL    = "claude-haiku-4-5"    # kept for streaming-only contexts
_WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search"}
_SEARCH_BETA     = "web-search-2025-03-05"


# ── Core: non-streaming call with web search ──────────────────────────────────

def ask_z47_with_search(messages: list, system_prompt: str,
                        max_tokens: int = 2000) -> str:
    """
    Non-streaming Q&A with the built-in web_search_20250305 tool.

    Claude automatically searches the web when needed (P/E ratios, quarterly
    results, analyst targets, live news) and returns a final synthesised answer.
    Anthropic runs the actual search server-side — no second API call needed.

    Returns a plain Markdown string for display.
    """
    api_key = (st.secrets.get("ANTHROPIC_API_KEY", "")
               or os.environ.get("ANTHROPIC_API_KEY", ""))
    if not api_key or api_key.startswith("sk-ant-..."):
        return ("⚠️ No Anthropic API key configured. "
                "Add `ANTHROPIC_API_KEY` to `.streamlit/secrets.toml`.")
    try:
        client   = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=_SEARCH_MODEL,
            max_tokens=max_tokens,
            system=system_prompt,
            tools=[_WEB_SEARCH_TOOL],
            messages=messages[-20:],           # keep rolling 20-message window
            extra_headers={"anthropic-beta": _SEARCH_BETA},
        )
        # Extract every text block (Claude may emit text before AND after a search)
        text_parts = [
            blk.text.strip()
            for blk in response.content
            if getattr(blk, "type", "") == "text" and blk.text.strip()
        ]
        return "\n\n".join(text_parts) if text_parts else (
            "Could not generate a response. Please try again.")

    except anthropic.AuthenticationError:
        return "⚠️ Invalid API key — check `ANTHROPIC_API_KEY` in secrets.toml."
    except anthropic.RateLimitError:
        return "⚠️ Rate limit reached. Please wait a moment and try again."
    except Exception as e:
        print(f"[Z47 Assistant] ask_with_search error: {e}")
        return f"⚠️ Assistant error: {e}"


# ── Fallback: streaming call (no web search) ──────────────────────────────────

def stream_z47_response(messages, system_prompt):
    """Stream response from Claude — no web search. Used as a lightweight fallback."""
    api_key = (st.secrets.get("ANTHROPIC_API_KEY", "")
               or os.environ.get("ANTHROPIC_API_KEY", ""))
    if not api_key or api_key.startswith("sk-ant-..."):
        yield ("⚠️ No Anthropic API key configured. "
               "Add your key to `.streamlit/secrets.toml` under `ANTHROPIC_API_KEY`.")
        return
    try:
        client = anthropic.Anthropic(api_key=api_key)
        with client.messages.stream(
            model=_STREAM_MODEL,
            max_tokens=1024,
            system=system_prompt,
            messages=messages[-20:],
        ) as stream:
            for text in stream.text_stream:
                yield text
    except anthropic.AuthenticationError:
        yield "⚠️ Invalid API key."
    except anthropic.RateLimitError:
        yield "⚠️ Rate limit hit. Please wait a moment and try again."
    except Exception as e:
        yield f"⚠️ Error contacting AI: {e}"


# ── System prompts ────────────────────────────────────────────────────────────

_SEARCH_GUIDANCE = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHEN TO USE WEB SEARCH vs PRE-COMPUTED DATA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

USE PRE-COMPUTED DATA (from context above) for:
• Price returns — 1W / 1M / 3M / 6M / 1Y / YTD / since listing
• Top gainers and losers over any period
• Index vs Nifty / Sensex comparison
• Market cap data
• Sector performance

USE WEB SEARCH TOOL for everything else:
• P/E, P/B, EV/EBITDA ratios
  → search: "[company] PE ratio screener.in"
• Quarterly results (revenue, PAT, EBITDA)
  → search: "[company] Q4 FY26 results"
• Analyst price targets
  → search: "[company] analyst target price moneycontrol"
• Latest company news
  → search: "[company] news May 2026"
• AUM, GMV, GWP, or sector-specific KPIs
  → search: "[company] AUM FY26"
• Any number NOT in the pre-computed context

PREFERRED SOURCES (in order):
1. screener.in — best for Indian stock financials
2. moneycontrol.com — P/E, analyst targets, news
3. economictimes.com — results, news
4. nseindia.com — official NSE data
5. tickertape.in — multiples and ratios

RESPONSE RULES:
1. Always give a direct answer with real numbers.
   Never say "I don't have data" — search if not in context.
2. Cite your source: "(Source: Screener.in, May 2026)"
3. Bullet points for lists; **bold** for key numbers.
4. Under 150 words unless the question needs detail.
5. Never end with "Would you like..." — just answer.
6. If search fails: say "Could not find [metric] —
   try screener.in/company/[SYMBOL]"
"""

SYSTEM_PROMPTS = {
    "z47_index": (
        "You are the Z47 Assistant — expert financial analyst for the Z47 Index, "
        "a free-float market-cap weighted index of 47 Indian new-age tech and "
        "financial services companies.\n\n"
        "You have two capabilities:\n"
        "1. Pre-computed live data in the context below (returns, prices, market caps)\n"
        "2. A web_search tool to fetch anything live (P/E ratios, quarterly results, "
        "analyst targets, news)\n\n"
        + _SEARCH_GUIDANCE
    ),
    "recent_ipos": (
        "You are the Z47 Assistant. The user is viewing Recent IPO data for Indian new-age tech and "
        "fintech companies (2024-2026 listings). Help them understand: IPO details and financials, "
        "valuation multiples (EV/Revenue, P/E, P/B) at listing and current price, anchor investor "
        "significance, pre-IPO investor returns, lock-up expiry implications, subscription levels "
        "and what oversubscription signals, grey market premium interpretation, and post-listing "
        "performance drivers. Be specific when asked about individual companies.\n\n"
        "You also have a web_search tool — use it for live P/E ratios, recent quarterly results, "
        "analyst targets, or any financial metric not in the page context."
    ),
    "upcoming_ipos": (
        "You are the Z47 Assistant. The user is viewing Upcoming IPO data for Indian new-age tech "
        "companies. Help them understand: DRHP vs RHP filings and what they mean, how to evaluate "
        "expected valuations and EV/Revenue multiples, what to look for when assessing an upcoming IPO, "
        "how to interpret GMP (grey market premium), and key risk factors for pre-IPO investments. "
        "Provide context on companies in the pipeline (Zepto, PhonePe, Meesho, Boat, Lenskart, etc.).\n\n"
        "You have a web_search tool — use it for latest GMP, filing updates, or any live data."
    ),
    "drhp": (
        "You are the Z47 Assistant. The user is viewing DRHP and RHP filings for Indian new-age tech "
        "companies. Help them understand: what to look for in a DRHP/RHP prospectus, key financial "
        "metrics and red flags, how BRLMs (book running lead managers) influence IPO quality, "
        "SEBI filing timelines and what they mean, sector-specific metrics for tech/fintech filings, "
        "and how to compare upcoming IPOs with recent peers.\n\n"
        "You have a web_search tool — use it for latest SEBI filings, news, or company financials."
    ),
    "block_deals": (
        "You are the Z47 Assistant. The user is viewing Block and Bulk Deal data for Z47 Index "
        "companies. Help them understand: the difference between block deals and bulk deals, "
        "what large institutional trades signal about conviction or exits, how to interpret "
        "deal timing and size relative to stock performance, which Z47 companies are seeing "
        "significant institutional activity, and the significance of buy vs sell pressure from "
        "large investors. Be analytical and draw connections to broader market context.\n\n"
        "You have a web_search tool — use it for recent deal news, analyst commentary, or "
        "context on specific institutional buyers/sellers."
    ),
}


# ── UI widget ─────────────────────────────────────────────────────────────────

def render_z47_assistant(context: str = "z47_index",
                         label: str = "💬 Ask Z47 Assistant",
                         extra_context: str = ""):
    """
    Render a collapsible Z47 assistant chat widget with web search.

    Args:
        context:       One of 'z47_index', 'recent_ipos', 'upcoming_ipos',
                       'drhp', 'block_deals'
        label:         Expander label shown to user
        extra_context: Optional pre-computed data appended to system prompt
    """
    chat_key = f"chat_{context}"
    if chat_key not in st.session_state:
        st.session_state[chat_key] = []

    system_prompt = SYSTEM_PROMPTS.get(context, SYSTEM_PROMPTS["z47_index"])
    if extra_context:
        system_prompt = (
            system_prompt
            + "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            + "PRE-COMPUTED LIVE DATA (use this for return / price questions)\n"
            + "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            + extra_context
        )

    with st.expander(label, expanded=False):
        # Render chat history
        for msg in st.session_state[chat_key]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Input form
        form_key = f"assistant_form_{context}"
        with st.form(key=form_key, clear_on_submit=True, border=False):
            col_in, col_btn = st.columns([9, 1])
            with col_in:
                placeholders = {
                    "z47_index":     "Ask anything — P/E ratios, top movers, quarterly results, analyst targets…",
                    "recent_ipos":   "Ask about IPO valuations, returns, lock-ups, investors, latest results…",
                    "upcoming_ipos": "Ask about upcoming IPOs, DRHP filings, GMP, valuations…",
                    "drhp":          "Ask about DRHP/RHP filings, red flags, metrics, news…",
                    "block_deals":   "Ask about block deals, institutional activity, signals, news…",
                }
                user_input = st.text_input(
                    "question",
                    placeholder=placeholders.get(context, "Ask anything about Z47…"),
                    label_visibility="collapsed",
                    key=f"input_{context}",
                )
            with col_btn:
                submitted = st.form_submit_button("Ask →", use_container_width=True)

        if submitted and user_input.strip():
            prompt = user_input.strip()
            st.session_state[chat_key].append({"role": "user", "content": prompt})

            msgs_for_api = [{"role": m["role"], "content": m["content"]}
                            for m in st.session_state[chat_key]]

            with st.chat_message("assistant"):
                with st.spinner("🔍 Searching and analyzing…"):
                    response_text = ask_z47_with_search(msgs_for_api, system_prompt)
                st.markdown(response_text)

            st.session_state[chat_key].append(
                {"role": "assistant", "content": response_text}
            )
            st.rerun()
