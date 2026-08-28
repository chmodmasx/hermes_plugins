#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
SELECTED=("$@")
AVAILABLE=( $(for d in "$ROOT"/integrations/*; do [[ -d "$d" && -x "$d/verify.sh" ]] && basename "$d"; done | sort) )
[[ ${#SELECTED[@]} -gt 0 ]] || SELECTED=("${AVAILABLE[@]}")
for id in "${SELECTED[@]}"; do
  script="$ROOT/integrations/$id/verify.sh"
  [[ -x "$script" ]] || { echo "Unknown integration: $id" >&2; exit 2; }
  echo "==> Verifying $id"
  "$script"
done
echo "==> Verifying monorepo contract"
(cd "$ROOT" && python3 -m unittest discover -s tests -v)
