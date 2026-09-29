import json

from ai_model_watch.collectors.reddit import parse_reddit_listing
from ai_model_watch.models import Source


def test_reddit_listing_maps_posts_and_skips_stickied() -> None:
    source = Source("Reddit Test", "reddit", "https://reddit.com", 3, "Test", False, "reddit_json")
    payload = json.dumps({
        "data": {
            "children": [
                {"data": {"title": "AI model update", "permalink": "/r/test/1", "selftext": "Details", "created_utc": 1}},
                {"data": {"title": "Pinned", "permalink": "/r/test/2", "stickied": True}},
            ]
        }
    })
    documents = parse_reddit_listing(payload, source)
    assert len(documents) == 1
    assert documents[0].url == "https://www.reddit.com/r/test/1"
