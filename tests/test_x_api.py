import json

from ai_model_watch.collectors.x_api import parse_x_search_response
from ai_model_watch.models import Source


def test_x_search_response_maps_posts_and_users() -> None:
    source = Source("X Test", "x", "https://api.x.com/2/tweets/search/recent", 2, "AI", False, "x_api")
    payload = json.dumps(
        {
            "data": [
                {
                    "id": "123",
                    "text": "New model update",
                    "author_id": "42",
                    "created_at": "2026-09-27T01:02:03.000Z",
                    "lang": "en",
                },
                {"id": "123", "text": "Duplicate"},
            ],
            "includes": {"users": [{"id": "42", "username": "model_team", "name": "Model Team"}]},
        }
    )

    documents = parse_x_search_response(payload, source)

    assert len(documents) == 1
    assert documents[0].url == "https://x.com/model_team/status/123"
    assert documents[0].author == "model_team"
