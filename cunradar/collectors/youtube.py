"""YouTube channel video collector.

Uses YouTube's official RSS feeds:
  https://www.youtube.com/feeds/videos.xml?channel_id=CHANNEL_ID

Supports two ways to specify a channel in config:
  1. channel_id  — the "UC..." identifier
  2. handle      — the "@name" handle (auto-resolved to channel_id)
"""

import re
from datetime import datetime, timezone

import feedparser
import requests

from .base import BaseCollector, CollectedItem


def _resolve_handle(handle: str) -> str | None:
    """Resolve a YouTube @handle to a channel_id by scraping the channel page.

    Args:
        handle: Channel handle (e.g. ``"cunzhanglab"`` or ``"@cunzhanglab"``).

    Returns:
        The channel_id (e.g. ``"UC..."``) or ``None`` if resolution fails.
    """
    handle = handle.lstrip("@")
    url = f"https://www.youtube.com/@{handle}"

    try:
        resp = requests.get(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
            timeout=15,
        )
        resp.raise_for_status()
    except Exception as e:
        print(f"  [YouTube] Failed to resolve handle @{handle}: {e}")
        return None

    # Extract channelId from ytInitialData embedded in the page
    # Pattern: "channelId":"UC..."
    m = re.search(r'"channelId"\s*:\s*"((UC|UU)[a-zA-Z0-9_-]+)"', resp.text)
    if m:
        return m.group(1)

    # Fallback: look for externalId in ytcfg
    m = re.search(r'"externalId"\s*:\s*"((UC|UU)[a-zA-Z0-9_-]+)"', resp.text)
    if m:
        return m.group(1)

    print(f"  [YouTube] Could not extract channel_id from @{handle} page")
    return None


class YouTubeCollector(BaseCollector):
    """Collect latest videos from a list of YouTube channels.

    Each channel entry in the config should have:
      - ``name``: display name
      - Either ``channel_id`` (the ``UC...`` string) or ``handle`` (the ``@name``)
    """

    def __init__(self, channels: list[dict]) -> None:
        self.channels = channels

    def collect(self) -> list[CollectedItem]:
        items: list[CollectedItem] = []
        for ch in self.channels:
            name = ch["name"]

            # Resolve channel_id from config
            channel_id = ch.get("channel_id")
            if not channel_id:
                handle = ch.get("handle", name)
                print(f"  [YouTube] Resolving handle @{handle.lstrip('@')} for '{name}'...")
                channel_id = _resolve_handle(handle)
                if not channel_id:
                    print(f"  [YouTube] Skipping '{name}': could not resolve handle")
                    continue

            feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

            try:
                feed = feedparser.parse(feed_url)
            except Exception as e:
                print(f"  [YouTube] Failed to fetch '{name}': {e}")
                continue

            if feed.bozo and not feed.entries:
                print(f"  [YouTube] No entries for '{name}' (bad feed)")
                continue

            for entry in feed.entries:
                video_id = entry.get("yt_videoid", entry.id)
                published = None
                if "published_parsed" in entry and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

                items.append(CollectedItem(
                    source="youtube",
                    source_name=name,
                    item_id=f"yt:{video_id}",
                    title=entry.get("title", "(no title)"),
                    url=f"https://www.youtube.com/watch?v={video_id}",
                    published=published,
                    description=entry.get("summary", ""),
                    extra={"channel_id": channel_id},
                ))

            print(f"  [YouTube] '{name}': {len(feed.entries)} videos found")

        return items
