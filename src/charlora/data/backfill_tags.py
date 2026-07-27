"""Backfills tag_string_artist/general/copyright/meta into metadata JSON
files collected before DanbooruPost captured those per-category fields.

Re-fetches each post's full metadata by id (JSON only, no image
re-download) and merges the missing fields into the existing .json sidecar.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

from .booru_client import DanbooruClient

_BACKFILL_FIELDS = ["tag_string_artist", "tag_string_general", "tag_string_copyright", "tag_string_meta"]


def backfill_directory(dir_path: str | Path, client: Optional[DanbooruClient] = None) -> int:
    dir_path = Path(dir_path)
    owns_client = client is None
    client = client or DanbooruClient()
    updated = 0
    try:
        for meta_path in sorted(dir_path.glob("*.json")):
            meta = json.loads(meta_path.read_text())
            if all(field in meta for field in _BACKFILL_FIELDS):
                continue  # already backfilled, nothing to do

            post = client.get_post(meta["id"])
            if post is None:
                print(f"skipping {meta_path.name}: post {meta['id']} no longer exists on Danbooru")
                continue

            for field in _BACKFILL_FIELDS:
                meta[field] = getattr(post, field)
            meta_path.write_text(json.dumps(meta, indent=2))
            updated += 1
        return updated
    finally:
        if owns_client:
            client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill per-category tag fields into existing metadata JSON")
    parser.add_argument("--dir", required=True, help="Folder of already-collected metadata (e.g. data/raw/frieren)")
    args = parser.parse_args()

    updated = backfill_directory(args.dir)
    print(f"Updated {updated} metadata files in {args.dir}")


if __name__ == "__main__":
    main()
