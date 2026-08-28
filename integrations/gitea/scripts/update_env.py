#!/usr/bin/env python3
"""Atomically upsert selected Hermes .env values without printing secrets."""
from __future__ import annotations
import argparse, os, tempfile
from pathlib import Path


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--token-env", default="GITEA_TOKEN")
    ap.add_argument("--allow-http", action="store_true")
    ns=ap.parse_args()
    token=os.environ.get(ns.token_env)
    if not token:
        raise SystemExit(f"{ns.token_env} is not set")
    path=Path(ns.file).expanduser(); path.parent.mkdir(parents=True, exist_ok=True)
    existing=path.read_text() if path.exists() else ""
    updates={"GITEA_BASE_URL":ns.base_url, "GITEA_TOKEN":token}
    if ns.allow_http: updates["GITEA_ALLOW_HTTP"]="1"
    output=[]; seen=set()
    for line in existing.splitlines():
        stripped=line.strip()
        if stripped and not stripped.startswith("#") and "=" in line:
            key=line.split("=",1)[0].strip()
            if key in updates:
                if key not in seen: output.append(f"{key}={updates[key]}"); seen.add(key)
                continue
        output.append(line)
    if output and output[-1] != "": output.append("")
    for key,value in updates.items():
        if key not in seen: output.append(f"{key}={value}")
    text="\n".join(output).rstrip()+"\n"
    fd,tmp=tempfile.mkstemp(prefix=".env.gitea-", dir=str(path.parent), text=True)
    try:
        os.fchmod(fd,0o600)
        with os.fdopen(fd,"w") as f: f.write(text); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,path); os.chmod(path,0o600)
    finally:
        try: os.unlink(tmp)
        except FileNotFoundError: pass
    print(f"Configured {path} (GITEA_TOKEN stored with mode 0600; value not printed)")
    return 0
if __name__ == "__main__": raise SystemExit(main())
