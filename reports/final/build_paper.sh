#!/usr/bin/env bash
# Typeset reports/final/AETHER_paper.md into reports/final/AETHER_paper.pdf.
#
#   make paper            (from the repository root)
#   reports/final/build_paper.sh
#
# Pipeline: pandoc (markdown -> LaTeX, with paper_build/filter.lua) -> tectonic (XeTeX).
# Needs: pandoc >= 3.1, tectonic, pdfinfo (poppler). Fonts are the macOS system faces
# Charter, Avenir Next, Menlo and STIX Two Math; see paper_build/preamble.tex.
# Figures: every "![Figure N](../figures/x.png)" in the markdown is typeset from the sibling
# x.pdf (vector) when it exists, else the PNG. Nothing under src/, configs/ or results/ is read.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

MD=AETHER_paper.md
TEX=paper_build/AETHER_paper.tex
PDF=AETHER_paper.pdf

for tool in pandoc tectonic pdfinfo; do
  command -v "$tool" >/dev/null || { echo "build_paper: $tool not found" >&2; exit 1; }
done

echo "build_paper: pandoc -> $TEX"
pandoc "$MD" \
  --from markdown+smart-implicit_figures \
  --to latex \
  --shift-heading-level-by=-1 \
  --lua-filter paper_build/filter.lua \
  --include-in-header paper_build/preamble.tex \
  --include-before-body paper_build/titlepage.tex \
  --number-sections \
  --variable documentclass=article \
  --variable classoption=11pt \
  --variable papersize=a4 \
  --variable colorlinks=true \
  --variable linkcolor=accent \
  --variable urlcolor=accent \
  --variable toc-title=Contents \
  --resource-path=. \
  --output "$TEX"

echo "build_paper: tectonic -> $PDF"
# two passes are implicit: tectonic reruns until the table of contents is stable
tectonic --keep-logs --outdir "$HERE" "$TEX" 2>&1 | grep -v -E '^(note|warning): (could not represent|.*Missing character)' || true

test -s "$PDF" || { echo "build_paper: no PDF produced" >&2; exit 1; }
mv -f AETHER_paper.log paper_build/AETHER_paper.log 2>/dev/null || true

PAGES=$(pdfinfo "$PDF" | awk '/^Pages:/{print $2}')
LOG=paper_build/AETHER_paper.log
OVER=$(grep -c '^Overfull \\hbox' "$LOG" 2>/dev/null || true)
MISSING=$(grep -c 'Missing character' "$LOG" 2>/dev/null || true)
echo "build_paper: $PDF — $PAGES pages, $OVER overfull hboxes, $MISSING missing-glyph warnings"
if [ "${MISSING:-0}" != "0" ]; then
  echo "build_paper: glyphs the fonts could not set (fix in paper_build/filter.lua):" >&2
  grep 'Missing character' "$LOG" | sort | uniq -c | sort -rn | head -20 >&2
fi
