"""Command line entry point: ``linkedin-agent serve | mcp | skills | run``."""

from __future__ import annotations

import argparse
import json
import logging
import sys


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="linkedin-agent", description="Self-hosted LinkedIn agent")
    sub = p.add_subparsers(dest="cmd")

    s = sub.add_parser("serve", help="Run the web portal + scheduler")
    s.add_argument("--host")
    s.add_argument("--port", type=int)

    m = sub.add_parser("mcp", help="Run the MCP server (stdio by default)")
    m.add_argument("--http", action="store_true", help="Use streamable HTTP instead of stdio")

    sub.add_parser("skills", help="List available skills")

    r = sub.add_parser("run", help="Run one skill and print the result")
    r.add_argument("skill_id")
    r.add_argument("--input", "-i", action="append", default=[], help="key=value (repeatable)")

    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.cmd == "serve":
        import uvicorn

        from .config import settings

        host = args.host or settings.host
        port = args.port or settings.port
        print(f"\n  LinkedIn Agent portal → http://{'localhost' if host in ('0.0.0.0', '127.0.0.1') else host}:{port}\n")
        uvicorn.run("linkedin_agent.server:app", host=host, port=port, log_level="info")
    elif args.cmd == "mcp":
        from .mcp_server import main as mcp_main

        mcp_main(http=args.http)
    elif args.cmd == "skills":
        from . import skills

        for sk in skills.SKILLS:
            print(f"{sk.category:<14} {sk.id:<22} {sk.description}")
    elif args.cmd == "run":
        from . import db, skills

        db.init()
        inputs = dict(kv.split("=", 1) for kv in args.input)
        print(json.dumps(skills.run(args.skill_id, inputs), indent=2, ensure_ascii=False))
    else:
        p.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
