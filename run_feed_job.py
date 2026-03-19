from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import TypedDict, cast, override


FEED_URL = "https://aitrends.kr/"
DEFAULT_STATE_LIMIT = 500
DEFAULT_MAX_POSTS = 10
DEFAULT_COLOR = 65535
USER_AGENT = "AITRENDS Feed Bot/1.0"


@dataclass
class FeedItem:
    url: str
    title: str
    summary: str
    article_id: int


class SentArticle(TypedDict):
    url: str
    sent_at: str


class State(TypedDict):
    version: int
    articles: list[SentArticle]


class EmbedFooter(TypedDict):
    text: str


class EmbedField(TypedDict):
    name: str
    value: str
    inline: bool


class Embed(TypedDict):
    title: str
    description: str
    url: str
    color: int
    footer: EmbedFooter


class AllowedMentions(TypedDict):
    parse: list[str]


class WebhookPayload(TypedDict):
    username: str
    allowed_mentions: AllowedMentions
    embeds: list[Embed]


class FeedHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.items: list[FeedItem] = []
        self._current_href: str | None = None
        self._current_title_parts: list[str] = []
        self._current_summary_parts: list[str] = []
        self._capture_title: bool = False
        self._capture_summary: bool = False
        self._seen_summary: bool = False

    @override
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        if tag == "a":
            href = attr_map.get("href")
            if href and href.startswith("/articles/"):
                self._flush_current_item()
                self._current_href = urllib.parse.urljoin(FEED_URL, href)
                self._current_title_parts = []
                self._current_summary_parts = []
                self._seen_summary = False
        elif tag == "h3" and self._current_href:
            self._capture_title = True
        elif tag == "p" and self._current_href and not self._seen_summary:
            self._capture_summary = True
            self._seen_summary = True

    @override
    def handle_endtag(self, tag: str) -> None:
        if tag == "h3":
            self._capture_title = False
        elif tag == "p":
            self._capture_summary = False

    @override
    def handle_data(self, data: str) -> None:
        text = normalize_space(data)
        if not text:
            return
        if self._capture_title:
            self._current_title_parts.append(text)
        elif self._capture_summary:
            self._current_summary_parts.append(text)

    @override
    def close(self) -> None:
        super().close()
        self._flush_current_item()

    def _flush_current_item(self) -> None:
        if not self._current_href:
            return
        title = normalize_space(" ".join(self._current_title_parts))
        summary = normalize_space(" ".join(self._current_summary_parts))
        if title and summary:
            article_id = extract_article_id(self._current_href)
            self.items.append(
                FeedItem(
                    url=self._current_href,
                    title=title,
                    summary=summary,
                    article_id=article_id,
                )
            )
        self._current_href = None
        self._current_title_parts = []
        self._current_summary_parts = []
        self._capture_title = False
        self._capture_summary = False
        self._seen_summary = False


def normalize_space(value: str) -> str:
    return " ".join(value.split())


def extract_article_id(url: str) -> int:
    path = urllib.parse.urlparse(url).path.rstrip("/")
    try:
        return int(path.split("/")[-1])
    except (TypeError, ValueError, IndexError):
        return -1


def fetch_feed_html(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        body = cast(bytes, response.read())
    return body.decode("utf-8")


def parse_feed_items(html: str) -> list[FeedItem]:
    parser = FeedHTMLParser()
    parser.feed(html)
    parser.close()

    deduped: dict[str, FeedItem] = {}
    for item in parser.items:
        deduped[item.url] = item

    items = list(deduped.values())
    items.sort(key=lambda item: item.article_id)
    return items


def load_state(state_path: Path) -> State:
    if not state_path.exists():
        return {"version": 1, "articles": []}
    with state_path.open("r", encoding="utf-8") as handle:
        state = json.load(handle)
    if not isinstance(state, dict) or not isinstance(state.get("articles"), list):
        raise ValueError(f"Invalid state file: {state_path}")
    articles: list[SentArticle] = []
    for entry in state["articles"]:
        if isinstance(entry, dict) and isinstance(entry.get("url"), str) and isinstance(entry.get("sent_at"), str):
            articles.append({"url": entry["url"], "sent_at": entry["sent_at"]})
    return {"version": int(state.get("version", 1)), "articles": articles}


def save_state(state_path: Path, state: State) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with state_path.open("w", encoding="utf-8") as handle:
        _ = json.dump(state, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def build_sent_index(state: State) -> set[str]:
    return {entry["url"] for entry in state["articles"]}


def trim_state(state: State, limit: int) -> None:
    state["articles"] = state["articles"][-limit:]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "..."


def build_payload(item: FeedItem) -> WebhookPayload:
    description = truncate(item.summary, 4096)
    return {
        "username": "AITRENDS",
        "allowed_mentions": {"parse": []},
        "embeds": [
            {
                "title": truncate(item.title, 256),
                "description": description,
                "url": item.url,
                "color": DEFAULT_COLOR,
                "footer": {"text": "AI Trends"},
            }
        ],
    }


def post_to_discord(webhook_url: str, payload: WebhookPayload) -> object:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    attempts = 0
    while True:
        attempts += 1
        request = urllib.request.Request(
            webhook_url + ("&" if "?" in webhook_url else "?") + "wait=true",
            data=body,
            headers={
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                response_body = cast(bytes, response.read())
                return json.loads(response_body.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempts <= 3:
                retry_after = parse_retry_after(exc)
                time.sleep(retry_after)
                continue
            if 500 <= exc.code < 600 and attempts <= 3:
                time.sleep(attempts)
                continue
            raise
        except urllib.error.URLError:
            if attempts <= 3:
                time.sleep(attempts)
                continue
            raise


def parse_retry_after(exc: urllib.error.HTTPError) -> float:
    header_value = exc.headers.get("Retry-After")
    if header_value:
        try:
            return float(header_value)
        except ValueError:
            pass
    try:
        data = json.loads(exc.read().decode("utf-8"))
    except Exception:
        return 1.0
    if not isinstance(data, dict):
        return 1.0
    retry_after = data.get("retry_after", 1)
    try:
        return float(retry_after)
    except (TypeError, ValueError):
        return 1.0


def mark_sent(state: State, item: FeedItem) -> None:
    state["articles"].append({"url": item.url, "sent_at": now_iso()})


def bootstrap_state(state: State, items: list[FeedItem], limit: int) -> int:
    existing = build_sent_index(state)
    added = 0
    for item in items:
        if item.url in existing:
            continue
        mark_sent(state, item)
        existing.add(item.url)
        added += 1
    trim_state(state, limit)
    return added


def run_job(args: argparse.Namespace) -> int:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8")
    state_path = Path(args.state_path)
    state = load_state(state_path)
    html = fetch_feed_html(args.feed_url)
    items = parse_feed_items(html)

    if not items:
        print("No feed items found.", file=sys.stderr)
        return 1

    sent_index = build_sent_index(state)
    new_items = [item for item in items if item.url not in sent_index]

    print(f"Fetched: {len(items)}")
    print(f"New: {len(new_items)}")

    if args.bootstrap:
        added = bootstrap_state(state, items, args.state_limit)
        save_state(state_path, state)
        print(f"Bootstrap saved {added} article(s) to state.")
        return 0

    if not new_items:
        print("No new items to send.")
        return 0

    to_send = new_items[: args.max_posts]
    if args.dry_run:
        for item in to_send:
            print(json.dumps(build_payload(item), ensure_ascii=False, indent=2))
        return 0

    webhook_url = args.webhook_url or os.environ.get("AITRENDS_DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("Webhook URL is required unless using --dry-run or --bootstrap.", file=sys.stderr)
        return 2

    successes = 0
    for item in to_send:
        post_to_discord(webhook_url, build_payload(item))
        mark_sent(state, item)
        trim_state(state, args.state_limit)
        successes += 1
        print(f"Sent: {item.url}")

    save_state(state_path, state)
    print(f"Saved state with {successes} successful send(s).")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch AITRENDS feed items and post new ones to Discord.")
    parser.add_argument("--feed-url", default=FEED_URL)
    parser.add_argument("--state-path", default=str(Path(__file__).with_name("data") / "sent_articles.json"))
    parser.add_argument("--state-limit", type=int, default=DEFAULT_STATE_LIMIT)
    parser.add_argument("--max-posts", type=int, default=DEFAULT_MAX_POSTS)
    parser.add_argument("--webhook-url")
    parser.add_argument("--bootstrap", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return run_job(args)


if __name__ == "__main__":
    raise SystemExit(main())
