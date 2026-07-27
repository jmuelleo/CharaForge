"""Download pipeline: query Danbooru -> filtered images + tag metadata on disk."""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

from .booru_client import DanbooruClient, DanbooruPost

_RATING_CODE_MAP = {"general": "g", "sensitive": "s", "questionable": "q", "explicit": "e"}
# Danbooru also serves video/animated posts (mp4, webm, gif, zip ugoira) under
# character tags; a static-image LoRA dataset has no use for those.
_STATIC_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


@dataclass
class CollectionConfig:
    booru_tag: str
    ratings: list[str]
    min_short_side: int
    exclude_tags: list[str]
    max_character_count: int

    @classmethod
    def from_yaml(cls, path: str | Path) -> "CollectionConfig":
        data = yaml.safe_load(Path(path).read_text())
        return cls(
            booru_tag=data["character"]["booru_tag"],
            ratings=data["collection"]["ratings"],
            min_short_side=data["collection"]["min_short_side"],
            exclude_tags=data["collection"]["exclude_tags"],
            max_character_count=data["collection"]["max_character_count"],
        )

    @property
    def rating_codes(self) -> set[str]:
        return {_RATING_CODE_MAP[r] for r in self.ratings}


def passes_filters(post: DanbooruPost, config: CollectionConfig) -> bool:
    if post.rating not in config.rating_codes:
        return False
    if not post.file_url:
        return False
    if post.file_ext not in _STATIC_IMAGE_EXTENSIONS:
        return False
    if min(post.image_width, post.image_height) < config.min_short_side:
        return False
    if post.character_count > config.max_character_count:
        return False
    if post.tags & set(config.exclude_tags):
        return False
    return True


def collect_character(
    config: CollectionConfig,
    output_dir: str | Path,
    client: Optional[DanbooruClient] = None,
    max_pages: Optional[int] = None,
) -> list[Path]:
    """Downloads filtered images + tag metadata for a character into output_dir/raw/<tag>/.

    Idempotent: re-running skips images already saved (by post id) and dedupes
    by md5 within a single run.
    """
    owns_client = client is None
    client = client or DanbooruClient()
    try:
        out_dir = Path(output_dir) / "raw" / config.booru_tag
        out_dir.mkdir(parents=True, exist_ok=True)

        seen_md5: set[str] = set()
        saved_paths: list[Path] = []

        for post in client.iter_all_posts(tags=config.booru_tag, max_pages=max_pages):
            if not passes_filters(post, config):
                continue
            if post.md5 and post.md5 in seen_md5:
                continue

            image_path = out_dir / f"{post.id}.{post.file_ext}"
            meta_path = out_dir / f"{post.id}.json"

            if not image_path.exists():
                try:
                    image_bytes = client.download_bytes(post.file_url)
                except RuntimeError as e:
                    # A handful of posts (e.g. unusually large originals) are
                    # unfetchable due to a Chromium/CDP quirk (see
                    # booru_client._fetch); skip them rather than losing the
                    # whole run over a few images.
                    print(f"skipping post {post.id}: {e}")
                    continue
                image_path.write_bytes(image_bytes)
                meta_path.write_text(
                    json.dumps(
                        {
                            "id": post.id,
                            "md5": post.md5,
                            "rating": post.rating,
                            "tag_string": post.tag_string,
                            "tag_string_artist": post.tag_string_artist,
                            "tag_string_general": post.tag_string_general,
                            "tag_string_copyright": post.tag_string_copyright,
                            "tag_string_meta": post.tag_string_meta,
                            "source_url": post.file_url,
                        },
                        indent=2,
                    )
                )

            if post.md5:
                seen_md5.add(post.md5)
            saved_paths.append(image_path)

        return saved_paths
    finally:
        if owns_client:
            client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect character images from Danbooru")
    parser.add_argument("--config", required=True, help="Path to character YAML config")
    parser.add_argument("--output", default="data", help="Output data root directory")
    parser.add_argument("--max-pages", type=int, default=None)
    args = parser.parse_args()

    config = CollectionConfig.from_yaml(args.config)
    saved = collect_character(config, args.output, max_pages=args.max_pages)
    print(f"Saved {len(saved)} images to {Path(args.output) / 'raw' / config.booru_tag}")


if __name__ == "__main__":
    main()
