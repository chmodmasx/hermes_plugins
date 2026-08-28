#!/usr/bin/env python3
"""Explicitly provision a repository Gitea webhook for an existing Hermes route.

The webhook secret is read from an environment variable, never a CLI argument.
This script is intentionally not exposed as an LLM tool.
"""
from __future__ import annotations
import argparse, importlib.util, json, os, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PLUGIN=ROOT/"plugin"/"gitea-hermes"
name="gitea_webhook_setup_plugin"
spec=importlib.util.spec_from_file_location(name, PLUGIN/"__init__.py", submodule_search_locations=[str(PLUGIN)])
mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod
assert spec.loader; spec.loader.exec_module(mod)
client_mod=sys.modules[name+".client"]; policy=sys.modules[name+".policy"]


def main():
    ap=argparse.ArgumentParser(description="Create an idempotent Gitea repository webhook for Hermes")
    ap.add_argument("owner"); ap.add_argument("repo"); ap.add_argument("url")
    ap.add_argument("--events", required=True, help="Comma-separated Gitea event names, for example pull_request,push")
    ap.add_argument("--secret-env", default="HERMES_GITEA_WEBHOOK_SECRET")
    ap.add_argument("--name", default="Hermes Agent")
    ns=ap.parse_args()
    secret=os.environ.get(ns.secret_env)
    if not secret: raise SystemExit(f"Set {ns.secret_env} in the environment; secret values are not accepted on the command line")
    if not ns.url.lower().startswith("https://") and not ns.url.startswith("http://127.0.0.1") and not ns.url.startswith("http://localhost"):
        raise SystemExit("Webhook URL must use HTTPS unless it is loopback")
    c=client_mod.GiteaClient.from_environment(**policy.client_kwargs())
    rp=policy.repo_path(ns.owner,ns.repo)
    hooks=c.paginate(rp+"/hooks",limit=50,max_pages=20)["items"]
    for hook in hooks:
        if isinstance(hook,dict) and ((hook.get("config") or {}).get("url") == ns.url):
            print(json.dumps({"ok":True,"created":False,"hook":hook},ensure_ascii=False)); return 0
    body={"type":"gitea","name":ns.name,"active":True,"events":[e.strip() for e in ns.events.split(",") if e.strip()],"config":{"url":ns.url,"content_type":"json","secret":secret}}
    response=c.request("POST",rp+"/hooks",body=body,sensitive_values=[secret]).data
    print(json.dumps({"ok":True,"created":True,"hook":response},ensure_ascii=False)); return 0
if __name__=="__main__": raise SystemExit(main())
