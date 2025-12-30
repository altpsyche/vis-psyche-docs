# VizPsyche Book

Documentation for the VizPsyche 3D rendering engine - a hands-on guide to building a graphics engine from scratch.

## Reading the Book

The book chapters are in the `chapters/` folder. Start with:
- **[Chapter Index](chapters/INDEX.md)** - Table of contents and reading order

## Building the Book

This repository includes a build system that generates the book in multiple formats.

### Prerequisites

| Tool | Installation | Purpose |
|------|-------------|---------|
| Python 3.8+ | [python.org](https://python.org) | Build script |
| Pandoc 3.0+ | `scoop install pandoc` | Document conversion |
| MiKTeX | `scoop install miktex` | PDF generation (LaTeX) |

### Quick Start

```bash
# Install Python dependencies
pip install -r build/requirements.txt

# Build all formats
python build/build.py all
```

### Build Commands

| Command | Output |
|---------|--------|
| `python build/build.py pdf` | `dist/vizpsyche-book.pdf` |
| `python build/build.py html` | `dist/html/index.html` |
| `python build/build.py epub` | `dist/vizpsyche-book.epub` |
| `python build/build.py all` | All formats |
| `python build/build.py clean` | Remove `dist/` |

### Output

Generated files are saved to `dist/`:

```
dist/
├── vizpsyche-book.pdf    # Professional PDF with Eisvogel template
├── vizpsyche-book.epub   # eBook format
└── html/
    └── index.html        # Standalone HTML with dark theme
```

## Project Structure

```
vis-psyche-docs/
├── chapters/              # Markdown source files (13 chapters)
│   ├── 00_Introduction.md
│   ├── 01_BuildSystem.md
│   └── ...
├── images/                # Diagrams and figures (PNG)
├── build/                 # Build system
│   ├── build.py           # Main build script
│   ├── chapters.yaml      # Chapter order manifest
│   ├── metadata.yaml      # Book metadata (title, author, styling)
│   ├── requirements.txt   # Python dependencies
│   └── templates/
│       ├── style.css      # Dark theme for HTML/EPUB
│       └── pandoc-latex-template/  # Eisvogel template (submodule)
├── dist/                  # Generated output (gitignored)
└── README.md              # This file
```

## Customization

### Book Metadata

Edit `build/metadata.yaml` to change:
- Title, author, date
- Title page colors
- Link colors
- Font size

### Chapter Order

Edit `build/chapters.yaml` to add/remove/reorder chapters.

### Styling

- **PDF**: Uses [Eisvogel](https://github.com/Wandmalfarbe/pandoc-latex-template) template
- **HTML/EPUB**: Edit `build/templates/style.css`

## License

© 2025 Siva Vadlamani. All rights reserved.
