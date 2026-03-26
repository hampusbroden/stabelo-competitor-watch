"""
Stabelo Competitor Watch
Posts a daily competitive intelligence report to Slack.
Monitors Swedish mortgage providers for news, product changes, and strategic moves.
Runs via GitHub Actions on weekday mornings.
"""

import anthropic
import urllib.request
import urllib.error
import json
import os
import time
from datetime import datetime

# ── CONFIG ────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")
MODEL = os.environ.get("BRIEFING_MODEL", "claude-sonnet-4-6")
MAX_RETRIES = 3

# ── COMPETITORS ──────────────────────────────────────────────────────────────
COMPETITORS = [
    "Swedbank",
    "Handelsbanken",
    "Nordea",
    "SEB",
    "SBAB",
    "Länsförsäkringar bank",
    "Danske Bank",
    "Skandiabanken",
    "Landshypotek",
    "Avanza",
    "Nordnet",
    "ICA Banken",
    "Ikanobanken",
    "Ålandsbanken",
    "Borgo",
]

# ── PROMPT ────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a competitive intelligence analyst specializing in the Swedish mortgage and housing finance market. You write a daily surveillance report for the leadership team at Stabelo AB — a Swedish digital-first mortgage lender supervised by Finansinspektionen.

Your job is to monitor Stabelo's competitors and produce a concise, high-signal daily report. The tone is sharp and direct — no filler, no hype. Every insight should help Stabelo understand what competitors are doing and how to respond.

Context about Stabelo:
- Digital-first mortgage lender, FI-supervised
- Competes on speed, transparency, and digital experience
- Key differentiators: AI-driven credit assessment, fully digital mortgage process
- Leadership team is commercially minded and technically literate
- Key areas of interest: pricing, product launches, partnerships, tech investments, regulatory moves, marketing campaigns, hiring signals

Competitors to monitor:
{competitors}

FORMAT — output plain text only, no markdown headers with #, use these exact section dividers:

🔍 [TIME] STABELO COMPETITOR WATCH
📅 [WEEKDAY, DAY MONTH YEAR]

─────────────────────────────

1. TOP STORIES
─────────────────────────────
• [Competitor]: [1-2 sentence summary of what happened and why it matters to Stabelo]
• [repeat for each noteworthy development, typically 3-6 items]

─────────────────────────────
2. MARKET RATES
─────────────────────────────
Report yesterday's closing rates:
• 3M STIBOR: [rate]
• 1Y SEK Swap: [rate]
• 3Y SEK Swap: [rate]
• 5Y SEK Swap: [rate]
• 10Y SEK Swap: [rate]
Include direction (up/down/unchanged) vs previous day and any notable trend context.

─────────────────────────────
3. COMPETITOR RATE & PRICING MOVEMENTS
─────────────────────────────
• [Any announced rate changes, campaign offers, pricing moves, or cashback deals from competitors. If nothing notable, state "No significant pricing moves detected in the last 24 hours."]

─────────────────────────────
4. PRODUCT & DIGITAL DEVELOPMENTS
─────────────────────────────
• [New product launches, app updates, digital service changes, API/open banking moves, customer experience changes]

─────────────────────────────
5. STRATEGIC SIGNALS
─────────────────────────────
• [Partnerships, acquisitions, leadership changes, hiring patterns, regulatory filings, earnings highlights, market share data]

─────────────────────────────
6. CUSTOMER SENTIMENT & DISCUSSIONS
─────────────────────────────
Monitor what customers are saying about our competitors on social platforms and review sites (Reddit, Facebook Groups, Twitter/X, LinkedIn, Trustpilot, App Store/Google Play reviews, YouTube comments, Quora, Discord, forums, etc.):
• [Competitor]: [Summary of notable customer complaints, praise, or trending discussions — with platform source]
• [Only include genuine, recent discussions. If nothing notable, state "No significant customer discussions detected."]

─────────────────────────────
7. STABELO IMPLICATIONS
─────────────────────────────
• [2-3 concrete takeaways: What should Stabelo consider doing in response? Any threats or opportunities? Include insights from customer sentiment where relevant.]

─────────────────────────────
8. GENOMSNITTSRÄNTA (AVERAGE MORTGAGE RATES)
─────────────────────────────
Report the latest published genomsnittsränta (average actual mortgage rate) for each of these banks across all binding periods (3 months, 1 year, 3 years, 5 years, 10 years):

• Swedbank: 3m: [rate] | 1y: [rate] | 3y: [rate] | 5y: [rate] | 10y: [rate]
• Handelsbanken: 3m: [rate] | 1y: [rate] | 3y: [rate] | 5y: [rate] | 10y: [rate]
• Nordea: 3m: [rate] | 1y: [rate] | 3y: [rate] | 5y: [rate] | 10y: [rate]
• SEB: 3m: [rate] | 1y: [rate] | 3y: [rate] | 5y: [rate] | 10y: [rate]
• SBAB: 3m: [rate] | 1y: [rate] | 3y: [rate] | 5y: [rate] | 10y: [rate]
• Länsförsäkringar bank: 3m: [rate] | 1y: [rate] | 3y: [rate] | 5y: [rate] | 10y: [rate]
• Danske Bank: 3m: [rate] | 1y: [rate] | 3y: [rate] | 5y: [rate] | 10y: [rate]

Note: Banks publish genomsnittsränta by the 5th banking day of each month for the previous month. State the reporting period (e.g. "February 2026") and flag any banks that are late. Use "n/a" for binding periods a bank does not offer.

─────────────────────────────
Sources: [2-6 credible sources with URLs where possible]

RULES:
- Cover only real news and developments from the past 24 hours — do NOT repeat stories that were already covered yesterday. Focus on what is genuinely new today. The genomsnittsränta section is the exception: always report the latest published rates regardless of when they were first reported.
- Search in both Swedish and English — many sources are in Swedish (e.g. di.se, svd.se, breakit.se, realtid.se, fastighetstidningen.se)
- If a competitor has no news, do not force it — only report genuine developments
- Every insight should connect back to what it means for Stabelo
- Keep the whole report under 1000 words
- No markdown bold, no bullet nesting, no emojis except the section headers above
- Output the time as 07:00 in the header
""".format(competitors="\n".join(f"- {c}" for c in COMPETITORS))

USER_PROMPT = """Search for the latest news, announcements, and developments from the following Swedish mortgage providers over the past 24 hours. Only include genuinely new stories — do not repeat anything that would have appeared in yesterday's report:

{competitors}

Search terms to use (combine competitor names with these):
- bolån (mortgage), ränta (interest rate), bostadslån (housing loan)
- New products, app launches, digital services
- Partnerships, acquisitions, leadership changes
- Regulatory news, Finansinspektionen
- Swedish mortgage market news

Also check Swedish business news sources: di.se, svd.se/naringsliv, breakit.se, realtid.se, fastighetstidningen.se, privataaffarer.se

Also search for customer discussions and reviews about these competitors on: Reddit, Facebook Groups, Twitter/X, LinkedIn, Trustpilot, App Store reviews, Google Play reviews, YouTube comments, Quora, Discord, and Swedish forums (e.g. Flashback, Familjeliv). Look for complaints, praise, trending threads, or sentiment shifts.

Then produce today's Stabelo Competitor Watch report following the exact format in your instructions.

Today's date: {date}
""".format(
    competitors=", ".join(COMPETITORS),
    date=datetime.now().strftime("%A, %d %B %Y"),
)

# ── GENERATE REPORT ──────────────────────────────────────────────────────────
def generate_report() -> str:
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=3000,
                tools=[{"type": "web_search_20250305", "name": "web_search"}],
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": USER_PROMPT}],
            )
            break
        except anthropic.APIStatusError as e:
            if attempt == MAX_RETRIES or e.status_code < 500:
                raise
            wait = 2 ** attempt
            print(f"⚠️  API error (attempt {attempt}/{MAX_RETRIES}), retrying in {wait}s...")
            time.sleep(wait)

    # Extract text blocks from response (web_search tool produces multiple block types)
    text_parts = [block.text for block in response.content if hasattr(block, "text")]
    report = "\n".join(text_parts).strip()
    if not report:
        raise RuntimeError("Claude returned no text content")
    return report


# ── POST TO SLACK ─────────────────────────────────────────────────────────────
def post_to_slack(text: str) -> None:
    if not SLACK_WEBHOOK_URL:
        raise RuntimeError("SLACK_WEBHOOK_URL is not set")

    payload = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        SLACK_WEBHOOK_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        status = resp.getcode()
        if status != 200:
            raise RuntimeError(f"Slack returned HTTP {status}")
    print(f"✅ Report posted to Slack at {datetime.now().strftime('%H:%M:%S')}")


# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"🔄 Generating competitor watch for {datetime.now().strftime('%A %d %B %Y')}...")
    try:
        report = generate_report()
        print("─── PREVIEW ───────────────────────────────────────")
        print(report[:500] + "..." if len(report) > 500 else report)
        print("───────────────────────────────────────────────────")
        post_to_slack(report)
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
