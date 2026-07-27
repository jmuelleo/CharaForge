"""Curation pass over a raw/<tag>/ folder: drop corrupt files and near-duplicates.

Dry-run by default (reports only); pass --apply to actually move rejects out
of the way. Rejects are moved, never deleted -- easy to undo by moving them
back if a keep/reject call turns out wrong.
"""
from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path

import imagehash
from PIL import Image

_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


class UnionFind:
    def __init__(self, n: int):
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


@dataclass
class CurationReport:
    total: int
    corrupt: list[Path]
    duplicate_groups: list[list[Path]]  # each group's first element is the kept one

    @property
    def rejected(self) -> list[Path]:
        return self.corrupt + [p for group in self.duplicate_groups for p in group[1:]]

    def summary(self) -> str:
        dupes = sum(len(g) - 1 for g in self.duplicate_groups)
        kept = self.total - len(self.corrupt) - dupes
        lines = [
            f"{self.total} images scanned",
            f"{len(self.corrupt)} corrupt",
            f"{dupes} near-duplicates across {len(self.duplicate_groups)} groups",
            f"{kept} would remain",
        ]
        return "\n".join(lines)


def _find_corrupt(image_paths: list[Path]) -> list[Path]:
    corrupt = []
    for path in image_paths:
        try:
            with Image.open(path) as im:
                im.load()
        except Exception:
            corrupt.append(path)
    return corrupt


def _find_duplicate_groups(image_paths: list[Path], threshold: int) -> list[list[Path]]:
    """Groups perceptually-similar images (hamming distance <= threshold).

    Within each group, the highest-resolution image is kept (sorted first).
    O(n^2) hash comparisons -- fine into the low thousands of images; would
    need an index (e.g. a BK-tree) to scale much further.
    """
    hashes = []
    valid_paths = []
    for path in image_paths:
        try:
            with Image.open(path) as im:
                hashes.append(imagehash.phash(im))
                valid_paths.append(path)
        except Exception:
            continue  # corrupt files are handled separately

    n = len(valid_paths)
    uf = UnionFind(n)
    for i in range(n):
        for j in range(i + 1, n):
            if hashes[i] - hashes[j] <= threshold:
                uf.union(i, j)

    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(uf.find(i), []).append(i)

    def pixel_count(idx: int) -> int:
        with Image.open(valid_paths[idx]) as im:
            return im.width * im.height

    duplicate_groups = []
    for indices in groups.values():
        if len(indices) < 2:
            continue
        indices.sort(key=pixel_count, reverse=True)
        duplicate_groups.append([valid_paths[i] for i in indices])
    return duplicate_groups


def curate_directory(dir_path: str | Path, threshold: int = 4) -> CurationReport:
    dir_path = Path(dir_path)
    image_paths = sorted(p for p in dir_path.iterdir() if p.suffix.lower() in _IMAGE_SUFFIXES)

    corrupt = _find_corrupt(image_paths)
    corrupt_set = set(corrupt)
    candidates = [p for p in image_paths if p not in corrupt_set]
    duplicate_groups = _find_duplicate_groups(candidates, threshold)

    return CurationReport(total=len(image_paths), corrupt=corrupt, duplicate_groups=duplicate_groups)


def apply_report(report: CurationReport, dir_path: str | Path) -> None:
    """Moves rejected images (and their .json metadata sidecar, if any) into
    dir_path/_rejected/. Never deletes."""
    dir_path = Path(dir_path)
    rejected_dir = dir_path / "_rejected"
    rejected_dir.mkdir(exist_ok=True)

    for image_path in report.rejected:
        for candidate in (image_path, image_path.with_suffix(".json")):
            if candidate.exists():
                shutil.move(str(candidate), str(rejected_dir / candidate.name))


def main() -> None:
    parser = argparse.ArgumentParser(description="Curate a raw/<tag>/ image folder")
    parser.add_argument("--dir", required=True, help="Folder to curate (e.g. data/raw/frieren)")
    parser.add_argument("--threshold", type=int, default=4, help="Max phash hamming distance to count as duplicate")
    parser.add_argument("--apply", action="store_true", help="Actually move rejects (default: dry run, report only)")
    args = parser.parse_args()

    report = curate_directory(args.dir, threshold=args.threshold)
    print(report.summary())

    if args.apply:
        apply_report(report, args.dir)
        print(f"Moved {len(report.rejected)} files to {Path(args.dir) / '_rejected'}")
    else:
        print("Dry run -- pass --apply to move rejects to _rejected/")


if __name__ == "__main__":
    main()
