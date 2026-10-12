#!/usr/bin/env python3
"""Compare curl's HTTP/1.1 and HTTP/2 requests to a TLS endpoint."""

import subprocess
import sys

DEFAULT_URL = "https://nghttp2.org/httpbin/stream/5"
WRITE_OUT = (
    "\nHTTP version: %{http_version}\n"
    "Status: %{http_code}\n"
    "Time to first byte: %{time_starttransfer}s\n"
    "Total time: %{time_total}s\n"
)


def run_curl(version, url):
    result = subprocess.run(
        [
            "curl",
            "--silent",
            "--show-error",
            "--no-buffer",
            "--output",
            "/dev/null",
            "--write-out",
            WRITE_OUT,
            version,
            url,
        ],
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode:
        print(f"{version}: curl failed: {result.stderr.strip()}", file=sys.stderr)
        return False
    print(f"{version}:\n{result.stdout.strip()}")
    return True


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    outcomes = [
        run_curl("--http1.1", target),
        run_curl("--http2", target),
    ]
    if not all(outcomes):
        sys.exit(1)
