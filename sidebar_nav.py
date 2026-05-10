"""Shared sidebar navigation — imported by app.py and all pages/."""
import streamlit as st

BORDER = "#ccdaea"
BG_ALT = "#edf3fa"


def render_sidebar():
    """Render the Z47 nav in the sidebar (call once per page, after set_page_config)."""
    st.markdown(
        f"""<style>
        section[data-testid="stSidebar"] {{ background: {BG_ALT}; }}
        </style>""",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        """<div style='padding:8px 0 16px 0'>
        <div style='font-size:17px;font-weight:800;color:#1a0f00;margin-bottom:2px'>Z47 Dashboard</div>
        <div style='font-size:11px;color:#a38060'>Indian New-Age Tech &amp; Fintech</div>
        </div>""",
        unsafe_allow_html=True,
    )
    st.sidebar.page_link("app.py",                              label="📊 Z47 Index")
    st.sidebar.page_link("pages/1_📈_Recent_IPOs.py",           label="📈 Recent IPOs")
    st.sidebar.page_link("pages/2_🚀_Upcoming_IPOs.py",         label="🚀 Upcoming IPOs")
    st.sidebar.page_link("pages/3_💼_Block_&_Bulk_Deals.py",    label="💼 Block & Bulk Deals")
    st.sidebar.page_link("pages/4_📋_DRHP_Filings.py",          label="📋 DRHP Filings")
    st.sidebar.markdown(
        f"<hr style='border-color:{BORDER};margin:12px 0'>",
        unsafe_allow_html=True,
    )
