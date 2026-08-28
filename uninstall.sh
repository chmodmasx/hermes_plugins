#!/usr/bin/env bash
set -euo pipefail
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
if [[ $# -eq 0 ]]; then
  echo "Refusing to uninstall every integration implicitly. Specify one or more IDs, or use --all." >&2
  exit 2
fi
if [[ "$1" == "--all" ]]; then
  shift
  IDS=( $(for d in "$ROOT"/integrations/*; do [[ -d "$d" && -x "$d/uninstall.sh" ]] && basename "$d"; done | sort) )
else
  IDS=("$@")
fi
for id in "${IDS[@]}"; do
  script="$ROOT/integrations/$id/uninstall.sh"
  [[ -x "$script" ]] || { echo "Unknown integration: $id" >&2; exit 2; }
  echo "==> Uninstalling $id"
  "$script"
done
