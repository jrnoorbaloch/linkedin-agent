#!/usr/bin/env python3
"""Tiny REST client for a running LinkedIn Agent portal (stdlib only).

    LA_URL=http://localhost:8787 LA_API_TOKEN=... python la.py <command>

Commands:
  status                         connection + counts
  brand                          print brand profile
  skills                         list skills
  run <skill_id> key=value ...   run a skill with the agent's LLM
  draft "<text>" [--comment C]   save a draft
  posts [status]                 list posts
  approve <id> [--at ISO_UTC]    approve (and optionally schedule) a post
  publish <id>                   publish an approved post
  metrics <id> impr react comm repost
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("LA_URL", "http://localhost:8787").rstrip("/")
TOKEN = os.environ.get("LA_API_TOKEN", "")


def call(method: str, path: str, body: dict | None = None):
    req = urllib.request.Request(
        BASE + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"content-type": "application/json", "x-api-token": TOKEN},
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        sys.exit(f"Error {e.code}: {e.read().decode()[:400]}")
    except urllib.error.URLError as e:
        sys.exit(f"Cannot reach LinkedIn Agent at {BASE} ({e.reason}). Is `linkedin-agent serve` running?")


def flag(args: list[str], name: str) -> str | None:
    if name in args:
        i = args.index(name)
        val = args[i + 1]
        del args[i : i + 2]
        return val
    return None


def main(argv: list[str]) -> None:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return
    cmd, args = argv[0], argv[1:]
    if cmd == "status":
        out = call("GET", "/api/dashboard")
    elif cmd == "brand":
        out = call("GET", "/api/brand")["profile"]
    elif cmd == "skills":
        out = [{k: s[k] for k in ("id", "category", "description")} for s in call("GET", "/api/skills")]
    elif cmd == "run":
        out = call("POST", f"/api/skills/{args[0]}", dict(a.split("=", 1) for a in args[1:]))
    elif cmd == "draft":
        comment = flag(args, "--comment")
        out = call("POST", "/api/posts", {"content": args[0], "first_comment": comment})
    elif cmd == "posts":
        out = call("GET", "/api/posts" + (f"?status={args[0]}" if args else ""))
    elif cmd == "approve":
        at = flag(args, "--at")
        out = call("POST", f"/api/posts/{args[0]}/approve", {"scheduled_at": at})
    elif cmd == "publish":
        out = call("POST", f"/api/posts/{args[0]}/publish")
    elif cmd == "metrics":
        pid, *nums = args
        keys = ["impressions", "reactions", "comments", "reposts"]
        out = call("PATCH", f"/api/posts/{pid}", {"metrics": {k: int(v) for k, v in zip(keys, nums)}})
    else:
        sys.exit(f"Unknown command {cmd!r}. Run with --help.")
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:])
