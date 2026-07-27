"""Tests against the real Danbooru API (small limit, no auth needed).

DanbooruClient launches a real, visible Chromium browser (see booru_client.py
for why), so the tests share one instance via a module-scoped fixture instead
of paying that startup cost per test.
"""
import pytest

from charlora.data.booru_client import DanbooruClient, DanbooruPost
from charlora.data.collect import CollectionConfig, passes_filters


@pytest.fixture(scope="module")
def client():
    with DanbooruClient(requests_per_second=1.0) as c:
        yield c


def test_search_posts_returns_results(client):
    posts = client.search_posts(tags="kitagawa_marin", limit=5, page=1)
    assert len(posts) > 0
    assert all(isinstance(p, DanbooruPost) for p in posts)
    assert all(p.id > 0 for p in posts)


def test_search_posts_explicit_rating_reachable_anonymously(client):
    posts = client.search_posts(tags="kitagawa_marin rating:explicit", limit=3, page=1)
    assert len(posts) > 0
    assert all(p.rating == "e" for p in posts)


def test_iter_all_posts_paginates(client):
    posts = list(client.iter_all_posts(tags="kitagawa_marin", limit=5, max_pages=2))
    assert len(posts) <= 10
    assert len(posts) > 5  # confirms it actually advanced past page 1


def test_download_bytes_fetches_image(client):
    posts = client.search_posts(tags="kitagawa_marin", limit=1, page=1)
    image_bytes = client.download_bytes(posts[0].file_url)
    assert len(image_bytes) > 1000


def test_passes_filters_excludes_low_resolution():
    config = CollectionConfig(
        booru_tag="kitagawa_marin",
        ratings=["general", "sensitive", "questionable", "explicit"],
        min_short_side=768,
        exclude_tags=["photo", "cosplay"],
        max_character_count=1,
    )
    small_post = DanbooruPost(
        id=1, md5="a", file_url="http://x", file_ext="jpg",
        image_width=500, image_height=500, rating="g",
        tag_string="kitagawa_marin solo", tag_string_character="kitagawa_marin",
    )
    assert not passes_filters(small_post, config)


def test_passes_filters_excludes_cosplay_photos():
    config = CollectionConfig(
        booru_tag="kitagawa_marin",
        ratings=["general", "sensitive", "questionable", "explicit"],
        min_short_side=768,
        exclude_tags=["photo", "cosplay"],
        max_character_count=1,
    )
    photo_post = DanbooruPost(
        id=2, md5="b", file_url="http://x", file_ext="jpg",
        image_width=2000, image_height=2000, rating="g",
        tag_string="kitagawa_marin solo photo cosplay", tag_string_character="kitagawa_marin",
    )
    assert not passes_filters(photo_post, config)


def test_passes_filters_excludes_video_posts():
    config = CollectionConfig(
        booru_tag="kitagawa_marin",
        ratings=["general", "sensitive", "questionable", "explicit"],
        min_short_side=768,
        exclude_tags=["photo", "cosplay"],
        max_character_count=1,
    )
    video_post = DanbooruPost(
        id=4, md5="d", file_url="http://x", file_ext="mp4",
        image_width=1920, image_height=1080, rating="g",
        tag_string="kitagawa_marin solo", tag_string_character="kitagawa_marin",
    )
    assert not passes_filters(video_post, config)


def test_passes_filters_excludes_multi_character():
    config = CollectionConfig(
        booru_tag="kitagawa_marin",
        ratings=["general", "sensitive", "questionable", "explicit"],
        min_short_side=768,
        exclude_tags=["photo", "cosplay"],
        max_character_count=1,
    )
    multi_post = DanbooruPost(
        id=3, md5="c", file_url="http://x", file_ext="jpg",
        image_width=2000, image_height=2000, rating="g",
        tag_string="kitagawa_marin gojo_akane 2girls", tag_string_character="kitagawa_marin gojo_akane",
    )
    assert not passes_filters(multi_post, config)
