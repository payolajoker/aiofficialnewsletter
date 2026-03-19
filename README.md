# AITRENDS feed job

This folder contains the Python job for scraping `https://aitrends.kr/` and posting new feed items to a Discord webhook.

## Files

- `run_feed_job.py`: fetches the feed, deduplicates by article URL, and posts new items.
- `data/sent_articles.json`: local state file for sent article URLs.

## Requirements

- Python 3.11+
- Discord webhook URL in `AITRENDS_DISCORD_WEBHOOK_URL` for real sends

## Commands

Preview payloads without sending:

```bash
python run_feed_job.py --dry-run --max-posts 3
```

Seed the current feed into state without sending anything:

```bash
python run_feed_job.py --bootstrap
```

Send new items using the environment variable:

```bash
python run_feed_job.py --max-posts 5
```

Or pass the webhook directly:

```bash
python run_feed_job.py --webhook-url "https://discord.com/api/webhooks/..."
```

## Notes

- The job posts one Discord embed per article.
- State is updated only after a post succeeds.
- `--bootstrap` is recommended before the first real scheduled run.

## GitHub Actions secret

- Add `AITRENDS_DISCORD_WEBHOOK_URL` in repository secrets before running the scheduled workflow.
