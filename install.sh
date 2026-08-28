#!/usr/bin/env bash
set -euo pipefail
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
COMMON=()
SELECTED=()
EXTRA=()
PASS=0
usage(){ cat <<'USAGE'
Usage: ./install.sh [integration ...] [common options] [-- integration-specific-options]

With no integration names, installs all integrations.
Common options: --hermes-home PATH --force --no-config --no-enable
Other: --list, -h, --help

Example:
  ./install.sh
  ./install.sh gitea --force
  ./install.sh gitea -- --allow-http
USAGE
}
list_integrations(){
  for d in "$ROOT"/integrations/*; do
    [[ -d "$d" && -x "$d/install.sh" ]] || continue
    basename "$d"
  done | sort
}
while [[ $# -gt 0 ]]; do
  if [[ "$PASS" -eq 1 ]]; then EXTRA+=("$1"); shift; continue; fi
  case "$1" in
    --) PASS=1; shift;;
    --hermes-home) [[ $# -ge 2 ]] || { echo "--hermes-home requires PATH" >&2; exit 2; }; COMMON+=("$1" "$2"); shift 2;;
    --force|--no-config|--no-enable) COMMON+=("$1"); shift;;
    --list) list_integrations; exit 0;;
    -h|--help) usage; exit 0;;
    -*) echo "Unknown top-level option: $1 (put integration-specific options after --)" >&2; exit 2;;
    *) SELECTED+=("$1"); shift;;
  esac
done
AVAILABLE=( $(list_integrations) )
if [[ ${#SELECTED[@]} -eq 0 ]]; then SELECTED=("${AVAILABLE[@]}"); fi
if [[ ${#EXTRA[@]} -gt 0 && ${#SELECTED[@]} -ne 1 ]]; then
  echo "Integration-specific options after -- require exactly one selected integration." >&2; exit 2
fi
for id in "${SELECTED[@]}"; do
  script="$ROOT/integrations/$id/install.sh"
  [[ -x "$script" ]] || { echo "Unknown integration: $id" >&2; echo "Available: ${AVAILABLE[*]}" >&2; exit 2; }
  echo "==> Installing $id"
  "$script" "${COMMON[@]}" "${EXTRA[@]}"
done
