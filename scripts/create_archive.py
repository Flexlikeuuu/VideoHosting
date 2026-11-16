#!/usr/bin/env python3
import os
import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_ZIP = ROOT_DIR / "youtube-clone-mvp.zip"

EXCLUDE_DIRS = {
    "node_modules",
    "dist",
    ".pytest_cache",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    "tmp",
    ".venv",
    "venv",
}

EXCLUDE_FILES = {
    ".env",
    "youtube-clone-mvp.zip",
}


def make_archive():
    if OUTPUT_ZIP.exists():
        OUTPUT_ZIP.unlink()

    print(f"[*] Packaging project from {ROOT_DIR} into {OUTPUT_ZIP.name}...")

    total_files = 0
    total_uncompressed_bytes = 0

    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, dirs, files in os.walk(ROOT_DIR):
            # Prune excluded directories in-place
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

            for file in files:
                if file in EXCLUDE_FILES or file.endswith(".pyc") or file.endswith(".pyo"):
                    continue

                full_path = Path(root) / file
                rel_path = full_path.relative_to(ROOT_DIR)

                # Skip if any parent part is in EXCLUDE_DIRS
                if any(part in EXCLUDE_DIRS for part in rel_path.parts):
                    continue

                zf.write(full_path, arcname=str(rel_path))
                total_files += 1
                total_uncompressed_bytes += full_path.stat().st_size

    zip_size_mb = OUTPUT_ZIP.stat().st_size / (1024 * 1024)
    raw_size_mb = total_uncompressed_bytes / (1024 * 1024)

    print("==================================================")
    print(f"✅ Archive created: {OUTPUT_ZIP}")
    print(f"📦 Total files bundled: {total_files}")
    print(f"📊 Uncompressed size: {raw_size_mb:.2f} MB")
    print(f"🗜️ Compressed archive size: {zip_size_mb:.2f} MB")
    print("==================================================")


if __name__ == "__main__":
    make_archive()
