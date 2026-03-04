#!/usr/bin/env python3
"""
Pick one random sample_id that exists in ALL parallel folders in the current root,
and copy ALL audio files for that sample_id from each folder into an output dir.

Default sample_id extraction: prefix before first '_' in filename.
Example:
  sampleA_prompt.wav         -> sample_id = sampleA
  sampleA_wavslm2k_c1.wav    -> sample_id = sampleA

Usage:
  python pick_sample.py
  python pick_sample.py --out picked
  python pick_sample.py --seed 0
  python pick_sample.py --ext wav,flac,mp3
  python pick_sample.py --id_regex '^(.+?)_'   # customize how to extract sample_id
"""

import argparse
import os
import random
import re
import shutil
from pathlib import Path
from typing import Dict, List, Set, Tuple


AUDIO_EXT_DEFAULT = ("wav", "flac", "mp3", "ogg", "m4a", "aac")


def list_parallel_folders(root: Path, exclude: Set[str]) -> List[Path]:
    folders = []
    for p in root.iterdir():
        if p.is_dir() and p.name not in exclude and not p.name.startswith("."):
            folders.append(p)
    folders.sort(key=lambda x: x.name)
    return folders


def gather_audio_files(folder: Path, exts: Set[str]) -> List[Path]:
    files = []
    for ext in exts:
        files.extend(folder.glob(f"**/*.{ext}"))
    # Keep deterministic ordering (useful for debugging)
    files.sort(key=lambda p: str(p))
    return files


def extract_sample_id(name: str, rgx: re.Pattern) -> str:
    m = rgx.search(name)
    if not m:
        return None
    return m.group(1)


def build_index(
    folders: List[Path],
    exts: Set[str],
    id_regex: str,
) -> Tuple[Dict[str, Dict[str, List[Path]]], Set[str]]:
    """
    Returns:
      index[sample_id][folder_name] = list of files
      common_ids = set of sample_ids present in every folder
    """
    rgx = re.compile(id_regex)
    per_folder_ids: List[Set[str]] = []
    index: Dict[str, Dict[str, List[Path]]] = {}

    for folder in folders:
        audio = gather_audio_files(folder, exts)
        ids_here: Set[str] = set()

        for f in audio:
            sid = extract_sample_id(f.name, rgx)
            if sid is None:
                continue
            ids_here.add(sid)
            index.setdefault(sid, {}).setdefault(folder.name, []).append(f)

        per_folder_ids.append(ids_here)

    if not per_folder_ids:
        return index, set()

    common_ids = set.intersection(*per_folder_ids)
    return index, common_ids


def copy_sample(
    sample_id: str,
    folders: List[Path],
    index: Dict[str, Dict[str, List[Path]]],
    out_root: Path,
    keep_subdirs: bool,
) -> None:
    out_dir = out_root / f"sample_{sample_id}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nSelected sample_id: {sample_id}")
    print(f"Output directory:   {out_dir}\n")

    for folder in folders:
        folder_name = folder.name
        files = index.get(sample_id, {}).get(folder_name, [])

        if not files:
            # Shouldn't happen if sample_id is common, but keep safe.
            print(f"[WARN] No files found in {folder_name} for {sample_id}")
            continue

        dest_base = out_dir / folder_name
        dest_base.mkdir(parents=True, exist_ok=True)

        for src in files:
            if keep_subdirs:
                rel = src.relative_to(folder)
                dest = dest_base / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
            else:
                dest = dest_base / src.name

            shutil.copy2(src, dest)

        print(f"{folder_name}: copied {len(files)} file(s)")

    print("\nDone.\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=str, default=".", help="Root directory (default: current dir)")
    ap.add_argument("--out", type=str, default="_picked", help="Where to place the copied sample bundle")
    ap.add_argument("--seed", type=int, default=None, help="Random seed (optional)")
    ap.add_argument(
        "--ext",
        type=str,
        default=",".join(AUDIO_EXT_DEFAULT),
        help=f"Comma-separated audio extensions (default: {','.join(AUDIO_EXT_DEFAULT)})",
    )
    ap.add_argument(
        "--id_regex",
        type=str,
        default=r"^([^_]+)_",
        help=r"Regex with ONE capturing group for sample_id (default: ^([^_]+)_)",
    )
    ap.add_argument(
        "--exclude",
        type=str,
        default="_picked,.git",
        help="Comma-separated folder names to exclude",
    )
    ap.add_argument(
        "--keep_subdirs",
        action="store_true",
        help="Preserve subdirectory structure within each folder (if you have nested dirs).",
    )
    args = ap.parse_args()

    root = Path(args.root).resolve()
    out_root = (root / args.out).resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    exts = {e.strip().lower().lstrip(".") for e in args.ext.split(",") if e.strip()}
    exclude = {x.strip() for x in args.exclude.split(",") if x.strip()}
    exclude.add(out_root.name)

    folders = list_parallel_folders(root, exclude=exclude)
    if not folders:
        raise SystemExit(f"No parallel folders found in {root} (after excluding: {sorted(exclude)})")

    index, common_ids = build_index(folders, exts, args.id_regex)
    if not common_ids:
        raise SystemExit(
            "No common sample_id found across all folders.\n"
            "Tip: check your naming convention and tweak --id_regex."
        )

    rng = random.Random(args.seed)
    sample_id = rng.choice(sorted(common_ids))

    copy_sample(sample_id, folders, index, out_root, keep_subdirs=args.keep_subdirs)


if __name__ == "__main__":
    main()