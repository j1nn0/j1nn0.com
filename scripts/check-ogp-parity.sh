#!/usr/bin/env bash
# OGP Parity Check — rerenders each SVG via sips and compares to committed PNG
# Usage: ./scripts/check-ogp-parity.sh
# Requires: sips, ImageMagick (compare)

set -euo pipefail

IMAGES_DIR="static/images"
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

PASS=0
FAIL=0

# Discover post directories containing an SVG source for OGP
for svg in "$IMAGES_DIR"/*/ogp.svg; do
  [[ -f "$svg" ]] || continue

  dir=$(dirname "$svg")
  png="$dir/ogp.png"

  # 1. Verify PNG exists
  if [[ ! -f "$png" ]]; then
    echo "FAIL: $png missing"
    FAIL=$((FAIL + 1))
    continue
  fi

  # 2. Verify PNG dimensions
  w=$(sips -g pixelWidth "$png" 2>/dev/null | awk -F: '/pixelWidth/{gsub(/ /,"",$2); print $2}')
  h=$(sips -g pixelHeight "$png" 2>/dev/null | awk -F: '/pixelHeight/{gsub(/ /,"",$2); print $2}')
  if [[ "$w" -ne 1200 || "$h" -ne 630 ]]; then
    echo "FAIL: $png dimensions ${w}x${h} (expected 1200x630)"
    FAIL=$((FAIL + 1))
    continue
  fi

  # 3. Rerender SVG → PNG via sips
  rerendered="$TMPDIR/$(basename "$dir")_rerendered.png"
  sips -s format png "$svg" --out "$rerendered" >/dev/null 2>&1

  # 4. Pixel-compare with ImageMagick
  diff_out=$(compare -metric AE "$rerendered" "$png" null: 2>&1 || true)
  ae=$(echo "$diff_out" | awk '{print $1}')

  if [[ "$ae" == "0" ]]; then
    echo "PASS: $png ($w x $h) — exact pixel match"
    PASS=$((PASS + 1))
  else
    echo "FAIL: $png — pixel difference: $ae"
    FAIL=$((FAIL + 1))
  fi
done

echo
echo "Results: $PASS passed, $FAIL failed"

if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi
