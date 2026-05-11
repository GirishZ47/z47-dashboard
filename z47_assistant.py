"""Reusable Z47 Assistant — renders a collapsible chat UI on any page/tab."""
import os
import streamlit as st
import anthropic


def stream_z47_response(messages, system_prompt):
    """Stream response from Claude given message history + system prompt."""
    api_key = st.secrets.get("ANTHROPIC_API_KEY", os.environ.get("ANTHROPIC_API_KEY", ""))
    if not api_key or api_key.startswith("sk-ant-..."):
        yield "⚠️ No Anthropic API key configured. Add your key to `.streamlit/secrets.toml` under `ANTHROPIC_API_KEY`."
        return
    try:
        client = anthropic.Anthropic(api_key=api_key)
        with client.messages.stream(
            model="claude-haiku-4-5",
            max_tokens=1024,
            system=system_prompt,
            messages=messages[-20:],  # keep last 20 messages for context
        ) as stream:
            for text in stream.text_stream:
                yield text
    except anthropic.AuthenticationError:
        yield "⚠️ Invalid API key."
    except anthropic.RateLimitError:
        yield "⚠️ Rate limit hit. Please wait a moment and try again."
    except Exception as e:
        yield f"⚠️ Error contacting AI: {e}"


SYSTEM_PROMPTS = {
    "z47_index": (
        "You are the Z47 Assistant, an expert financial analyst for Z47 — a venture capital firm "
        "tracking an index of 47 Indian internet and new-age tech companies. "
        "The user is viewing the Z47 Index page. Help them understand index performance, sector trends, "
        "individual company metrics, and how Z47 compares to Nifty 50 and Sensex. "
        "Be concise, data-driven, and insightful. If the answer isn't in context data provided, "
        "draw on your general knowledge of Indian tech/startup ecosystem."
    ),
    "recent_ipos": (
        "You are the Z47 Assistant. The user is viewing Recent IPO data for Indian new-age tech and "
        "fintech companies (2024-2026 listings). Help them understand: IPO details and financials, "
        "valuation multiples (EV/Revenue, P/E, P/B) at listing and current price, anchor investor "
        "significance, pre-IPO investor returns, lock-up expiry implications, subscription levels "
        "and what oversubscription signals, grey market premium interpretation, and post-listing "
        "performance drivers. Be specific when asked about individual companies."
    ),
    "upcoming_ipos": (
        "You are the Z47 Assistant. The user is viewing Upcoming IPO data for Indian new-age tech "
        "companies. Help them understand: DRHP vs RHP filings and what they mean, how to evaluate "
        "expected valuations and EV/Revenue multiples, what to look for when assessing an upcoming IPO, "
        "how to interpret GMP (grey market premium), and key risk factors for pre-IPO investments. "
        "Provide context on companies in the pipeline (Zepto, PhonePe, Meesho, Boat, Lenskart, etc.)."
    ),
    "drhp": (
        "You are the Z47 Assistant. The user is viewing DRHP and RHP filings for Indian new-age tech "
        "companies. Help them understand: what to look for in a DRHP/RHP prospectus, key financial "
        "metrics and red flags, how BRLMs (book running lead managers) influence IPO quality, "
        "SEBI filing timelines and what they mean, sector-specific metrics for tech/fintech filings, "
        "and how to compare upcoming IPOs with recent peers."
    ),
    "block_deals": (
        "You are the Z47 Assistant. The user is viewing Block and Bulk Deal data for Z47 Index "
        "companies. Help them understand: the difference between block deals and bulk deals, "
        "what large institutional trades signal about conviction or exits, how to interpret "
        "deal timing and size relative to stock performance, which Z47 companies are seeing "
        "significant institutional activity, and the significance of buy vs sell pressure from "
        "large investors. Be analytical and draw connections to broader market context."
    ),
}


def render_z47_assistant(context: str = "z47_index", label: str = "💬 Ask Z47 Assistant",
                          extra_context: str = ""):
    """
    Render a collapsible Z47 assistant chat widget.

    Args:
        context: One of 'z47_index', 'recent_ipos', 'upcoming_ipos', 'drhp', 'block_deals'
        label: Expander label shown to user
        extra_context: Optional extra data/context string appended to system prompt
    """
    chat_key = f"chat_{context}"
    if chat_key not in st.session_state:
        st.session_state[chat_key] = []

    system_prompt = SYSTEM_PROMPTS.get(context, SYSTEM_PROMPTS["z47_index"])
    if extra_context:
        system_prompt += f"\n\n--- CURRENT PAGE DATA ---\n{extra_context}"

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
                    "z47_index":     "Ask about Z47 Index performance, sectors, companies…",
                    "recent_ipos":   "Ask about IPO valuations, returns, lock-ups, investors…",
                    "upcoming_ipos": "Ask about upcoming IPOs, DRHP filings, GMP…",
                    "drhp":          "Ask about DRHP/RHP filings, red flags, metrics…",
                    "block_deals":   "Ask about block deals, institutional activity, signals…",
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
                response_text = st.write_stream(
                    stream_z47_response(msgs_for_api, system_prompt)
                )
            st.session_state[chat_key].append({"role": "assistant", "content": response_text})
            st.rerun()
