#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
echo "[1/4] Plugin Python/contract tests"
python3 -m py_compile "$ROOT"/plugin/gitea-hermes/*.py
(cd "$ROOT/plugin/gitea-hermes" && python3 -m unittest discover -s tests -v)
echo "[2/4] Skill tests"
(cd "$ROOT/skills/gitea-professional" && python3 -m unittest discover -s tests -v)
echo "[3/4] Integration installer/layout tests"
(cd "$ROOT" && python3 -m unittest discover -s tests -v)
echo "[4/4] Hermes/native and live checks"
if command -v hermes >/dev/null 2>&1; then hermes plugins doctor "$ROOT/plugin/gitea-hermes" --ci; else echo "SKIP: hermes CLI not in PATH"; fi
if [[ -n "${GITEA_BASE_URL:-}" && -n "${GITEA_TOKEN:-}" ]]; then
  LIVE_ARGS=()
  case "${GITEA_ALLOW_HTTP:-}" in 1|true|TRUE|yes|YES|on|ON) LIVE_ARGS+=(--allow-http) ;; esac
  python3 "$ROOT/skills/gitea-professional/scripts/doctor.py" --base-url "$GITEA_BASE_URL" "${LIVE_ARGS[@]}"
else
  echo "SKIP: live Gitea check (GITEA_BASE_URL/GITEA_TOKEN not exported)"
fi
