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
    "Bostadskreditinstitut",
    "Landshypotek",
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
2. RATE & PRICING MOVEMENTS
─────────────────────────────
• [Any announced rate changes, campaign offers, pricing moves, or cashback deals from competitors. If nothing notable, state "No significant pricing moves detected in the last 48 hours."]

─────────────────────────────
3. PRODUCT & DIGITAL DEVELOPMENTS
─────────────────────────────
• [New product launches, app updates, digital service changes, API/open banking moves, customer experience changes]

─────────────────────────────
4. STRATEGIC SIGNALS
─────────────────────────────
• [Partnerships, acquisitions, leadership changes, hiring patterns, regulatory filings, earnings highlights, market share data]

─────────────────────────────
5. STABELO IMPLICATIONS
─────────────────────────────
• [2-3 concrete takeaways: What should Stabelo consider doing in response? Any threats or opportunities?]

─────────────────────────────
Sources: [2-6 credible sources with URLs where possible]

RULES:
- Cover only real news and developments from the past 48 hours
- Search in both Swedish and English — many sources are in Swedish (e.g. di.se, svd.se, breakit.se, realtid.se, fastighetstidningen.se)
- If a competitor has no news, do not force it — only report genuine developments
- Every insight should connect back to what it means for Stabelo
- Keep the whole report under 1000 words
- No markdown bold, no bullet nesting, no emojis except the section headers above
- Output the time as 07:00 in the header
""".format(competitors="\n".join(f"- {c}" for c in COMPETITORS))

USER_PROMPT = """Search for the latest news, announcements, and developments from the following Swedish mortgage providers over the past 48 hours:

{competitors}

Search terms to use (combine competitor names with these):
- bolån (mortgage), ränta (interest rate), bostadslån (housing loan)
- New products, app launches, digital services
- Partnerships, acquisitions, leadership changes
- Regulatory news, Finansinspektionen
- Swedish mortgage market news

Also check Swedish business news sources: di.se, svd.se/naringsliv, breakit.se, realtid.se, fastighetstidningen.se, privataaffarer.se

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
