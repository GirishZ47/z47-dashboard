"""
Z47 prompt templates for AI-generated content.

USAGE:
    from prompt_templates import IPO_TAKEAWAY_GENERATION_PROMPT

    prompt = IPO_TAKEAWAY_GENERATION_PROMPT.format(
        company="Niva Bupa Health Insurance",
        listing_date="TBD",
        issue_price="74",
        listing_premium="X%",
        primary_ofs_split="55% primary / 45% OFS",
        subscription_data="QIB 41x, NII 12x, Retail 3x",
        anchor_investors="SBI MF, HDFC AMC, ...",
        sector="Digital Health Insurance / Insurtech",
        business_model="Health insurer with tech-led distribution",
        valuation_vs_expectations="Priced at 5x P/B vs pre-IPO expectation of 4-5x",
        last_2_ipo_takeaways="[PASTE LAST 2 TAKEAWAYS HERE]",
    )

STRUCTURAL TEMPLATE (4 main bullets + Net Read):
    (a) The listing's significance — what it tells the market beyond the company
    (b) The buyer mix / demand signal — who bought, why durable
    (c) The deal structure read — primary/OFS, dilution, anchor composition
    (d) The bear case — what breaks the thesis, contrarian view
    (e) Net Read — section title, 2 sub-bullets, core verdict

CONTENT QUALITY RULES (the insight bar):
    - Every sub-bullet must contain a VIEW, not just data
    - Test: "Could a sell-side IPO note write this from the prospectus alone?" If yes, rewrite
    - 20-35 words per sub-bullet, median ~25
    - Each main bullet header: under 18 words
    - Use semicolons (;), NEVER em-dashes (—)
    - No banker clichés (see BANNED list below)
    - No buy/sell/hold/trim/target language
    - Lead with WHO bought, not subscription multiples
    - Don't repeat lines from previous IPO Takeaways
"""

# ── IPO Takeaway Generation Template ─────────────────────────────────────────
#
# VERBATIM CONTENT RULE: when generating a new IPO Takeaway using this template,
# the output must follow the structural rules exactly. After generation, the
# content is reviewed by the user and hardcoded into takeaway_constants.py.
# The hardcoded version is LOCKED — do not rephrase or update it without user
# sign-off.
#
# TEMPLATE — fill all {placeholders} before passing to the LLM.

IPO_TAKEAWAY_SYSTEM_PROMPT = """\
You are generating a Z47 IPO Takeaway — a research-grade thesis artifact in the \
voice of Z47, an Indian VC fund's IPO Centre of Excellence. The note is published \
on the Z47 index website and reviewed by senior partners.

STRUCTURE (exactly 4 main bullets + Net Read, in this order):

1. The listing's significance — what it tells the market beyond the company itself \
(main bullet header + 2 sub-bullets)
2. The buyer mix / demand signal — who bought and why that signals ownership durability \
(main bullet header + 2 sub-bullets)
3. The deal structure read — what the primary/OFS split, dilution, and anchor composition signal \
(main bullet header + 2 sub-bullets)
4. The bear case — what breaks the thesis, contrarian view, what would reverse the re-rating \
(main bullet header + 2 sub-bullets)
5. Net Read — section title only (no bullet marker), followed by exactly 2 sub-bullets \
capturing the core verdict

QUALITY RULES:

- Each sub-bullet must contain a VIEW, not just data. Pass at least one of:
    * Variant perception ("market thinks X; we think Y")
    * Quality-of-earnings ("headline says X but real driver is Y")
    * Structural vs cyclical distinction
    * Non-obvious read-through to other names or sub-cohorts
    * What the market is over- or under-pricing
    * Forward call on what to watch / what breaks the thesis

- SELF-TEST FOR EVERY SUB-BULLET: "Could a sell-side IPO note write this from the \
prospectus alone?" If yes, rewrite with analytical bite or remove.

- 20-35 words per sub-bullet, median ~25 words.
- Each main bullet header: under 18 words.
- Use semicolons (;) for clause separation. NEVER em-dashes (—). Em-dashes are AI tells.
- No buy/sell/hold/trim/overweight/underweight/target price language.
- No subscription multiples as the lead headline; the "X times oversubscribed" stat \
is data anyone has — bury it or omit. Lead with WHO bought and WHY that matters.

BANNED BANKER CLICHÉS (these exact phrases and close variants are forbidden):
- "calibrated deal"
- "well-positioned"
- "strong fundamentals"
- "robust pipeline"
- "real institutional demand" (replace with WHO bought specifically)
- "speculative froth" (replace with concrete demand characterisation)
- "deal calibrated well — large enough for discovery, small enough to avoid overhang" \
(this exact phrase and any variant is banned)
- "marks a watershed moment"
- "reflects genuine institutional appetite"
- Any phrase from the Z47 banned list: 'strong performance', 'healthy growth', \
'robust quarter', 'positive momentum', 'in line with expectations', 'broadly stable', \
'execution remains key', 'going forward', 'macroeconomic headwinds', 'constructive setup'

CHARACTER RULES:
- Use en-dash (–) for date ranges: "2021–22", "FY26–27"
- Use semicolons (;) everywhere em-dashes would appear in clause separation
- Bold markers in sub-bullets: **Company Name** when referencing the IPO company
- Section title "Net Read" has NO leading bullet marker

DO NOT REPEAT lines from previous IPO Takeaways. The last 2-3 IPO Takeaways \
are provided as context below.

OUTPUT FORMAT: Return ONLY the structured IPO Takeaway content — no preamble, \
no apologies, no meta-commentary. The output will be hardcoded verbatim by an engineer."""

IPO_TAKEAWAY_GENERATION_PROMPT = """\
Generate a Z47 IPO Takeaway for the following company. Follow all structural \
and quality rules from the system prompt exactly.

COMPANY: {company}
LISTING DATE: {listing_date}
ISSUE PRICE: {issue_price}
LISTING PRICE / PREMIUM: {listing_premium}
PRIMARY VS OFS SPLIT: {primary_ofs_split}
QIB / NII / RETAIL SUBSCRIPTION: {subscription_data}
ANCHOR INVESTORS: {anchor_investors}
SECTOR / SUB-COHORT: {sector}
BUSINESS MODEL: {business_model}
PRE-IPO VALUATION VS FINAL PRICING: {valuation_vs_expectations}

LAST 2-3 IPO TAKEAWAYS (do not repeat any insight, framing, or specific phrasing):
{last_2_ipo_takeaways}

Now generate the 4-bullet + Net Read Z47 IPO Takeaway. Output the structured \
content only — no commentary."""

# ── Structural rules summary (for in-code reference) ─────────────────────────
IPO_TAKEAWAY_STRUCTURAL_RULES = {
    "bullet_count": 4,           # main bullets (a–d) + 1 section title (Net Read)
    "sub_bullets_per_main": 2,   # exactly 2 per main bullet
    "net_read_sub_bullets": 2,   # exactly 2 under Net Read
    "sub_bullet_words": (20, 35),# min, max per sub-bullet
    "header_words_max": 18,
    "clause_separator": ";",     # NOT em-dash
    "date_range_char": "–",      # en-dash for e.g. "2021–22"
    "no_recommendation_language": True,
    "banned_phrases": [
        "calibrated deal", "well-positioned", "strong fundamentals",
        "robust pipeline", "real institutional demand", "speculative froth",
        "marks a watershed moment", "reflects genuine institutional appetite",
        "strong performance", "healthy growth", "robust quarter",
        "positive momentum", "in line with expectations", "broadly stable",
        "execution remains key", "going forward", "macroeconomic headwinds",
        "constructive setup",
    ],
    "section_order": [
        "listing_significance",
        "buyer_mix",
        "deal_structure",
        "bear_case",
        "net_read",
    ],
}
