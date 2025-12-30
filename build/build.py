#!/usr/bin/env python3
"""
VizPsyche Book Build System

Converts markdown chapters into PDF, HTML, and EPUB formats using Pandoc.
Future: This will be adapted as a BobReview plugin.

Usage:
    python build.py pdf      # Build PDF only
    python build.py html     # Build HTML only
    python build.py epub     # Build EPUB only
    python build.py all      # Build all formats
    python build.py clean    # Remove dist/
"""

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

import yaml

# Paths
BUILD_DIR = Path(__file__).parent
DOCS_DIR = BUILD_DIR.parent
DIST_DIR = DOCS_DIR / "dist"
TEMPLATES_DIR = BUILD_DIR / "templates"
CHAPTERS_FILE = BUILD_DIR / "chapters.yaml"
METADATA_FILE = BUILD_DIR / "metadata.yaml"

# Eisvogel template path (submodule)
EISVOGEL_TEMPLATE = TEMPLATES_DIR / "pandoc-latex-template" / "template-multi-file" / "eisvogel.latex"
STYLE_CSS = TEMPLATES_DIR / "style.css"


def load_chapters() -> list[str]:
    """Load chapter order from chapters.yaml."""
    with open(CHAPTERS_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    chapters = config.get("chapters", [])
    appendices = config.get("appendices", [])
    return chapters + appendices


def get_chapter_paths(chapters: list[str]) -> list[Path]:
    """Convert chapter filenames to full paths."""
    paths = []
    for chapter in chapters:
        path = DOCS_DIR / chapter
        if path.exists():
            paths.append(path)
        else:
            print(f"Warning: Chapter not found: {chapter}")
    return paths


def ensure_dist_dir():
    """Create dist directory if it doesn't exist."""
    DIST_DIR.mkdir(exist_ok=True)


def check_pandoc():
    """Check if Pandoc is installed."""
    try:
        result = subprocess.run(
            ["pandoc", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        version = result.stdout.split("\n")[0]
        print(f"[OK] Found {version}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("[ERROR] Pandoc not found. Please install: https://pandoc.org/installing.html")
        return False


def build_pdf(chapters: list[Path]) -> bool:
    """Build PDF using Pandoc with Eisvogel template."""
    print("\n[PDF] Building...")
    start_time = time.time()
    
    output = DIST_DIR / "vizpsyche-book.pdf"
    
    cmd = [
        "pandoc",
        *[str(p) for p in chapters],
        "-o", str(output),
        "--metadata-file", str(METADATA_FILE),
        "--template", str(EISVOGEL_TEMPLATE),
        "--pdf-engine", "xelatex",
        "--syntax-highlighting=zenburn",
        "--toc",
        "--toc-depth=2",
        "--number-sections",
        "--top-level-division=chapter",
        "--resource-path", str(DOCS_DIR),
        "-V", "geometry:margin=1in",
        "-V", "fontsize=11pt",
    ]
    
    try:
        subprocess.run(cmd, check=True, cwd=DOCS_DIR)
        elapsed = time.time() - start_time
        print(f"[OK] PDF generated: {output} ({elapsed:.1f}s)")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] PDF build failed: {e}")
        return False
    except FileNotFoundError:
        print("[ERROR] xelatex not found. Please install TeX Live or MiKTeX.")
        return False


def build_html(chapters: list[Path]) -> bool:
    """Build standalone HTML with custom CSS."""
    print("\n[HTML] Building...")
    start_time = time.time()
    
    html_dir = DIST_DIR / "html"
    html_dir.mkdir(exist_ok=True)
    output = html_dir / "index.html"
    
    # Copy images
    images_src = DOCS_DIR / "images"
    images_dst = html_dir / "images"
    if images_src.exists():
        if images_dst.exists():
            shutil.rmtree(images_dst)
        shutil.copytree(images_src, images_dst)
    
    cmd = [
        "pandoc",
        *[str(p) for p in chapters],
        "-o", str(output),
        "--metadata-file", str(METADATA_FILE),
        "--standalone",
        "--css", str(STYLE_CSS),
        "--embed-resources",
        "--toc",
        "--toc-depth=2",
        "--number-sections",
        "--syntax-highlighting=zenburn",
        "--resource-path", str(DOCS_DIR),
        "-V", "title-prefix=VizPsyche",
    ]
    
    try:
        subprocess.run(cmd, check=True, cwd=DOCS_DIR)
        elapsed = time.time() - start_time
        print(f"[OK] HTML generated: {output} ({elapsed:.1f}s)")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] HTML build failed: {e}")
        return False


def build_epub(chapters: list[Path]) -> bool:
    """Build EPUB eBook format."""
    print("\n[EPUB] Building...")
    start_time = time.time()
    
    output = DIST_DIR / "vizpsyche-book.epub"
    
    cmd = [
        "pandoc",
        *[str(p) for p in chapters],
        "-o", str(output),
        "--metadata-file", str(METADATA_FILE),
        "--css", str(STYLE_CSS),
        "--toc",
        "--toc-depth=2",
        "--number-sections",
        "--syntax-highlighting=zenburn",
        "--resource-path", str(DOCS_DIR),
        "--split-level=1",
    ]
    
    try:
        subprocess.run(cmd, check=True, cwd=DOCS_DIR)
        elapsed = time.time() - start_time
        print(f"[OK] EPUB generated: {output} ({elapsed:.1f}s)")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] EPUB build failed: {e}")
        return False


def clean():
    """Remove dist directory."""
    print("[CLEAN] Cleaning dist/...")
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
        print("[OK] Removed dist/")
    else:
        print("[OK] dist/ already clean")


def main():
    parser = argparse.ArgumentParser(
        description="VizPsyche Book Build System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python build.py pdf      Build PDF only
    python build.py html     Build HTML only
    python build.py epub     Build EPUB only
    python build.py all      Build all formats
    python build.py clean    Remove dist/
        """
    )
    parser.add_argument(
        "command",
        choices=["pdf", "html", "epub", "all", "clean"],
        help="Build command to run"
    )
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("VizPsyche Book Build System")
    print("=" * 50)
    
    if args.command == "clean":
        clean()
        return
    
    # Check dependencies
    if not check_pandoc():
        sys.exit(1)
    
    # Load chapters
    chapters_list = load_chapters()
    print(f"[OK] Found {len(chapters_list)} chapters")
    
    chapter_paths = get_chapter_paths(chapters_list)
    if not chapter_paths:
        print("[ERROR] No chapters found!")
        sys.exit(1)
    
    ensure_dist_dir()
    
    # Build requested format(s)
    success = True
    
    if args.command in ("pdf", "all"):
        success = build_pdf(chapter_paths) and success
    
    if args.command in ("html", "all"):
        success = build_html(chapter_paths) and success
    
    if args.command in ("epub", "all"):
        success = build_epub(chapter_paths) and success
    
    print("\n" + "=" * 50)
    if success:
        print("[OK] Build complete!")
        print(f"  Output: {DIST_DIR}")
    else:
        print("[ERROR] Build completed with errors")
        sys.exit(1)


if __name__ == "__main__":
    main()

