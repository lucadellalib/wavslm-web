#!/usr/bin/env python3
"""
Recursively crawl current directory and rename files by removing
everything before the first '_' (including the underscore).

Example:
  sampleA_prompt.wav  -> prompt.wav
  123_test.mp3        -> test.mp3

By default this performs a DRY RUN.
Use --apply to actually rename files.
"""

import argparse
from pathlib import Path


def strip_prefix(filename: str) -> str:
    """
    Remove everything before first '_' (including it).
    If no '_' exists, return None.
    """
    if "_" not in filename:
        return None
    return filename.split("_", 1)[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root", type=str, default=".",
        help="Root directory to crawl (default: current directory)"
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Actually perform renaming (default: dry run)"
    )
    parser.add_argument(
        "--ext", type=str, default=None,
        help="Optional comma-separated extensions to filter (e.g. wav,mp3,flac)"
    )

    args = parser.parse_args()

    root = Path(args.root).resolve()

    if args.ext:
        extensions = {e.strip().lower().lstrip(".") for e in args.ext.split(",")}
    else:
        extensions = None

    print(f"\nScanning: {root}\n")

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        if extensions:
            if path.suffix.lower().lstrip(".") not in extensions:
                continue

        new_name = strip_prefix(path.name)
        if new_name is None:
            continue

        new_path = path.with_name(new_name)

        print(f"{path}  →  {new_path}")

        if args.apply:
            if new_path.exists():
                print(f"⚠️  Skipped (target exists): {new_path}")
                continue
            path.rename(new_path)

    if not args.apply:
        print("\nDRY RUN complete. Use --apply to perform renaming.\n")
    else:
        print("\nRenaming complete.\n")


if __name__ == "__main__":
    main()