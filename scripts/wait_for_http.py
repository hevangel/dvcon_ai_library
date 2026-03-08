#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import time
import urllib.error
import urllib.request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Wait until an HTTP endpoint is ready.")
    parser.add_argument("--url", required=True, help="Target URL to poll.")
    parser.add_argument(
        "--contains",
        default="",
        help="Optional response substring that must be present.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=180.0,
        help="Maximum total seconds to wait.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="Seconds between retries.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    deadline = time.monotonic() + args.timeout
    last_error = "timed out before first request"

    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(args.url, timeout=10) as response:
                body = response.read().decode("utf-8", errors="replace")
                if args.contains and args.contains not in body:
                    last_error = f"response missing expected text: {args.contains!r}"
                elif 200 <= response.status < 300:
                    print(f"Ready: {args.url}")
                    return 0
                else:
                    last_error = f"unexpected status: {response.status}"
        except urllib.error.URLError as exc:
            last_error = str(exc)

        time.sleep(args.interval)

    print(f"Timed out waiting for {args.url}: {last_error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
