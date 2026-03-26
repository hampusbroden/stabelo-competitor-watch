# Stabelo Competitor Watch

Automated daily competitive intelligence report for the Stabelo leadership team. Uses Claude with web search to monitor Swedish mortgage providers and posts a structured report to Slack every weekday morning.

## Competitors monitored

Swedbank, Handelsbanken, Nordea, SEB, SBAB, Länsförsäkringar bank, Danske Bank, Skandiabanken, Bostadskreditinstitut, Landshypotek

## How it works

1. Claude searches Swedish and English news sources for competitor activity (past 48 hours)
2. Generates a structured report: top stories, rate movements, product/digital developments, strategic signals
3. Concludes with concrete implications for Stabelo
4. Posts to a Slack channel via webhook
5. Runs automatically via GitHub Actions (weekdays at 07:00 Stockholm time)

## Setup

### 1. Configure GitHub Secrets

Go to **Settings → Secrets and variables → Actions** and add:

| Secret | Description |
|--------|-------------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `SLACK_WEBHOOK_URL` | Slack incoming webhook URL for the target channel |

### 2. Create the Slack webhook

1. Go to [Slack API: Incoming Webhooks](https://api.slack.com/messaging/webhooks)
2. Create a new webhook for your target channel
3. Copy the webhook URL into the GitHub secret above

### 3. Test manually

Trigger the workflow manually from the **Actions** tab → **Stabelo Competitor Watch** → **Run workflow**.

### Run locally

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
python stabelo_competitor_watch.py
```

## Configuration

| Environment variable | Default | Description |
|---------------------|---------|-------------|
| `ANTHROPIC_API_KEY` | (required) | Anthropic API key |
| `SLACK_WEBHOOK_URL` | (required) | Slack webhook URL |
| `BRIEFING_MODEL` | `claude-sonnet-4-6` | Claude model to use |

## Schedule

The GitHub Actions workflow runs at **05:00 UTC** (07:00 CEST) on weekdays. Edit the cron in [`.github/workflows/daily_competitor_watch.yml`](.github/workflows/daily_competitor_watch.yml) to adjust.
