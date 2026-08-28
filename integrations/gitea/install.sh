#!/usr/bin/env bash
set -euo pipefail
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
FORCE=0; CONFIGURE=1; ENABLE=1; ALLOW_HTTP=0
usage(){ cat <<EOF
Usage: ./install.sh [--hermes-home PATH] [--force] [--no-config] [--no-enable] [--allow-http]

Secrets are never accepted as command-line arguments. Set GITEA_TOKEN in the environment
or enter it at the hidden prompt. --allow-http is only for explicitly trusted local instances.
EOF
}
while [[ $# -gt 0 ]]; do
  case "$1" in
    --hermes-home) HERMES_HOME="$2"; shift 2;;
    --force) FORCE=1; shift;;
    --no-config) CONFIGURE=0; shift;;
    --no-enable) ENABLE=0; shift;;
    --allow-http) ALLOW_HTTP=1; shift;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2;;
  esac
done
PLUGIN_DST="$HERMES_HOME/plugins/gitea-hermes"
SKILL_DST="$HERMES_HOME/skills/gitea-professional"
mkdir -p "$HERMES_HOME/plugins" "$HERMES_HOME/skills"
for dst in "$PLUGIN_DST" "$SKILL_DST"; do
  if [[ -e "$dst" && "$FORCE" -ne 1 ]]; then echo "Refusing to overwrite $dst (use --force)." >&2; exit 3; fi
done
if [[ "$FORCE" -eq 1 ]]; then
  TS="$(date +%Y%m%d-%H%M%S)"; B="$HERMES_HOME/backups/gitea-hermes-$TS"; mkdir -p "$B"
  [[ ! -e "$PLUGIN_DST" ]] || mv "$PLUGIN_DST" "$B/plugin"
  [[ ! -e "$SKILL_DST" ]] || mv "$SKILL_DST" "$B/skill"
fi
cp -a "$ROOT/plugin/gitea-hermes" "$PLUGIN_DST"
cp -a "$ROOT/skills/gitea-professional" "$SKILL_DST"
find "$PLUGIN_DST" "$SKILL_DST" -type d -name __pycache__ -prune -exec rm -rf {} + || true
find "$PLUGIN_DST" "$SKILL_DST" -type f -name '*.pyc' -delete || true

if [[ "$CONFIGURE" -eq 1 ]]; then
  BASE="${GITEA_BASE_URL:-}"
  if [[ -z "$BASE" && -t 0 ]]; then read -r -p "Canonical Gitea URL (e.g. https://git.example.com): " BASE; fi
  TOKEN="${GITEA_TOKEN:-}"
  if [[ -z "$TOKEN" && -t 0 ]]; then read -r -s -p "Gitea PAT for dedicated Hermes bot: " TOKEN; echo; fi
  if [[ -n "$BASE" && -n "$TOKEN" ]]; then
    if [[ "$BASE" == http://* && "$ALLOW_HTTP" -ne 1 ]]; then echo "Plain HTTP refused. Re-run with --allow-http only for a trusted local instance." >&2; exit 4; fi
    export GITEA_TOKEN="$TOKEN"
    args=(--file "$HERMES_HOME/.env" --base-url "$BASE")
    [[ "$ALLOW_HTTP" -ne 1 ]] || args+=(--allow-http)
    python3 "$ROOT/scripts/update_env.py" "${args[@]}"
  else
    echo "Gitea credentials not configured. Set GITEA_BASE_URL and GITEA_TOKEN in $HERMES_HOME/.env before enabling the plugin."
    ENABLE=0
  fi
fi

if command -v hermes >/dev/null 2>&1; then
  echo "Running Hermes Plugin Doctor..."
  hermes plugins doctor "$PLUGIN_DST" --ci
  if [[ "$ENABLE" -eq 1 ]]; then hermes plugins enable gitea-hermes; fi
else
  echo "Hermes CLI not found in PATH; files were installed but plugin doctor/enable were skipped."
fi

echo "Installed plugin: $PLUGIN_DST"
echo "Installed skill:  $SKILL_DST"
echo "Run ./verify.sh to test the bundle and optional live Gitea connectivity."
