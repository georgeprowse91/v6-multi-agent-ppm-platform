#!/usr/bin/env bash
set -euo pipefail

lucide_matches=$(rg -n "from 'lucide-react'" apps/web/frontend/src --glob '!**/Icon.tsx' || true)
if [[ -n "$lucide_matches" ]]; then
  echo "$lucide_matches" >&2
  echo "Direct lucide-react imports are not permitted. Use the shared Icon component instead." >&2
  exit 1
fi

svg_matches=$(rg -n "<svg" apps/web/frontend/src || true)
if [[ -n "$svg_matches" ]]; then
  echo "$svg_matches" >&2
  echo "Inline SVG icons are not permitted in UI code. Use the shared Icon component instead." >&2
  exit 1
fi
