"""Command line:  python -m sitegen <command>

  sync          pull papers, abstracts, links and teasers into data/ and assets/
  build         render site/ from config.yml, content/ and data/
  serve         serve site/ on http://localhost:8000
  preview       sync + build + serve, and open the browser
  add-failure   add a failure-of-the-month clip
"""
from __future__ import annotations

import argparse
import functools
import http.server
import threading
import webbrowser
from pathlib import Path

from sitegen import build, failures, sync
from sitegen.paths import Paths, find_root


def serve(paths: Paths, port: int, open_browser: bool) -> None:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(paths.site))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    url = f"http://localhost:{port}"
    print(f"Serving {url}  (Ctrl+C to stop)")
    if open_browser:
        threading.Timer(0.8, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="sitegen", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, help="repository root (default: found from the current folder)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("sync", help="pull papers into data/ and assets/teasers/")
    sub.add_parser("build", help="render site/")
    for name in ("serve", "preview"):
        sp = sub.add_parser(name, help="serve site/ locally" if name == "serve" else "sync, build and serve")
        sp.add_argument("--port", type=int, default=8000)
        sp.add_argument("--no-open", action="store_true", help="don't open the browser")
    fp = sub.add_parser("add-failure", help="add a failure-of-the-month video")
    fp.add_argument("video", type=Path)
    fp.add_argument("--caption", default="")
    fp.add_argument("--title", default="")
    args = ap.parse_args(argv)
    paths = Paths(find_root(args.root))

    if args.cmd == "sync":
        sync.run(paths)
    elif args.cmd == "build":
        build.run(paths)
    elif args.cmd == "serve":
        serve(paths, args.port, not args.no_open)
    elif args.cmd == "preview":
        sync.run(paths)
        build.run(paths)
        serve(paths, args.port, not args.no_open)
    elif args.cmd == "add-failure":
        failures.add(paths, args.video, args.caption, args.title)
        build.run(paths)


if __name__ == "__main__":
    main()
