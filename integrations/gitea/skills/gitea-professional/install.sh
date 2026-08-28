#!/usr/bin/env bash
set -euo pipefail

SKILL_NAME="gitea-professional"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TARGET_ROOT="${HOME}/.hermes/skills/devops"
FORCE=0
RUN_TESTS=1

usage() {
  cat <<USAGE
Usage: ./install.sh [--force] [--target-root DIR] [--skip-tests]

Installs ${SKILL_NAME} into Hermes user-local skills.
USAGE
}

while (($#)); do
  case "$1" in
    --force) FORCE=1; shift ;;
    --target-root) TARGET_ROOT="${2:?missing directory after --target-root}"; shift 2 ;;
    --skip-tests) RUN_TESTS=0; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

TARGET="${TARGET_ROOT%/}/${SKILL_NAME}"

command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 is required." >&2; exit 1; }
command -v git >/dev/null 2>&1 || { echo "ERROR: git is required." >&2; exit 1; }

python3 - "$SCRIPT_DIR/SKILL.md" <<'PY'
from pathlib import Path
import re, sys
p = Path(sys.argv[1])
s = p.read_text(encoding="utf-8")
if not s.startswith("---\n"):
    raise SystemExit("SKILL.md: missing YAML frontmatter")
for field in ("name", "description", "version"):
    if not re.search(rf"(?m)^{field}:\s*.+$", s):
        raise SystemExit(f"SKILL.md: missing {field}")
PY

python3 -m py_compile "$SCRIPT_DIR/scripts/gitea.py" "$SCRIPT_DIR/scripts/gitea_client.py" "$SCRIPT_DIR/scripts/doctor.py" "$SCRIPT_DIR/scripts/audit_workflow.py"

if (( RUN_TESTS )); then
  (cd "$SCRIPT_DIR" && python3 -m unittest discover -s tests -v)
fi

mkdir -p "$TARGET_ROOT"
if [[ -e "$TARGET" ]]; then
  if (( ! FORCE )); then
    echo "ERROR: $TARGET already exists. Use --force to upgrade." >&2
    exit 1
  fi
  stamp="$(date +%Y%m%d-%H%M%S)"
  backup="${TARGET}.backup-${stamp}"
  mv "$TARGET" "$backup"
  echo "Existing skill backed up to: $backup"
fi

mkdir -p "$TARGET"
cp -a "$SCRIPT_DIR"/. "$TARGET"/
find "$TARGET" -type d -name __pycache__ -prune -exec rm -rf {} +
find "$TARGET" -type f -name '*.pyc' -delete
rm -f "$TARGET"/*.zip "$TARGET"/*.tar.gz "$TARGET"/*.sha256 2>/dev/null || true

cat <<DONE
Installed: $TARGET

Next:
  hermes config set skills.config.gitea.base_url https://TU-GITEA

Then start a new Hermes session and load gitea-professional.
The former standalone gitea-actions skill is not required by version 2.0.0.
GITEA_TOKEN is configured through Hermes secure skill setup; do not put it in config.yaml or SKILL.md.
DONE
