#!/usr/bin/env bash
set -euo pipefail

emoji_pattern='[\x{1F300}-\x{1FAFF}\x{2600}-\x{27BF}]'
paths=(apps/web/frontend/src apps/web/static docs)

if rg -n -P "$emoji_pattern" "${paths[@]}"; then
  echo "Emojis are not permitted in UI-rendered content. Use the icon map instead." >&2
  exit 1
fi
