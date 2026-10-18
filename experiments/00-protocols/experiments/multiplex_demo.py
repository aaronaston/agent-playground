#!/usr/bin/env python3
"""Show what HTTP/2 multiplexing changes, using curl against httpbin.org.

compare_http.py makes one request per protocol, which can only show the
negotiated version. The differences that matter are properties of *many*
requests sharing a connection, so each demo here runs several transfers
at once (`curl -Z`) and prints a timeline of when each one finished.

  A. connections   N parallel GETs. HTTP/1.1 opens N connections. HTTP/2
                   opens one and runs N streams on it.
  B. browser cap   8 x /delay/2. Browsers allow about 6 HTTP/1.1
                   connections per host, so 8 requests go in two waves.
                   HTTP/2 runs all 8 on one connection in one wave.
  C. head-of-line  A slow and a fast request on ONE connection. HTTP/1.1
                   cannot interleave, so the fast one waits. HTTP/2 lets
                   the fast one finish first. (curl does not pipeline, so
                   --parallel-max 1 is how we get a single HTTP/1.1
                   connection.)

Usage: python experiments/multiplex_demo.py [A|B|C ...] [--json PATH]
       (default: all demos; --json also records per-transfer phase timings
        and connection ids for multiplex_viz.py)
"""

import datetime as dt
import json
import re
import subprocess
import sys
import time

HOST = "https://httpbin.org"
RECORD = []   # filled when --json is given

# conn_id needs curl >= 8.2. The timings are each relative to the transfer's
# own start, so the viz reconstructs absolute positions from the arrival time
# of this marker minus time_total.
MARKER = ("%{stderr}DONE %{url} http/%{http_version} %{time_total}s "
          "conn=%{conn_id} connect=%{time_connect} tls=%{time_appconnect} "
          "ttfb=%{time_starttransfer}\\n")


def run(label, version, urls, parallel_max=None):
    cmd = ["curl", "-sS", "-Z", "-v", version]
    if parallel_max:
        cmd += ["--parallel-max", str(parallel_max)]
    # %{stderr} makes curl write the marker to stderr, which is unbuffered,
    # so each line arrives as its transfer finishes. (-v output also goes
    # to stderr; we parse both from the same stream.)
    cmd += ["-w", MARKER]
    for u in urls:
        cmd += ["-o", "/dev/null", u]

    print(f"\n--- {label}: {version} "
          f"{'(parallel-max ' + str(parallel_max) + ')' if parallel_max else ''}")
    t0 = time.monotonic()
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                            text=True, bufsize=1)
    stderr_lines = []
    transfers = []
    for line in proc.stderr:
        stderr_lines.append(line)
        if line.startswith("DONE"):
            now = time.monotonic() - t0
            _, url, ver, total, *kv = line.split()
            f = dict(x.split("=") for x in kv)
            total_s = float(total.rstrip("s"))
            print(f"  +{now:5.2f}s  finished {url.removeprefix(HOST):<10} "
                  f"{ver}  (own duration {total}, conn {f['conn']})")
            transfers.append({
                "url": url.removeprefix(HOST), "http_version": ver.removeprefix("http/"),
                "conn_id": int(f["conn"]), "end": round(now, 4),
                "start": round(now - total_s, 4), "total": total_s,
                "connect": float(f["connect"]), "appconnect": float(f["tls"]),
                "starttransfer": float(f["ttfb"]),
            })
    proc.wait()
    stderr = "".join(stderr_lines)
    wall = time.monotonic() - t0

    connects = len(re.findall(r"^\* Connected to", stderr, re.M))
    if connects == 1:
        # curl reports conn_id -1 for transfers multiplexed onto a connection
        # another transfer opened; with one connection they all share it.
        for t in transfers:
            t["conn_id"] = 0
    streams = re.findall(r"\[HTTP/2\] \[(\d+)\] OPENED stream", stderr)
    print(f"  wall {wall:.2f}s   TCP connections: {connects}"
          + (f"   HTTP/2 stream ids: {', '.join(streams)}" if streams else ""))
    RECORD.append({
        "demo": label, "proto": version.lstrip("-"), "parallel_max": parallel_max,
        "wall": round(wall, 4), "connections": connects,
        "stream_ids": [int(x) for x in streams], "transfers": transfers,
    })


def demo_a():
    urls = [f"{HOST}/get"] * 4
    print("\n=== A. Four parallel GETs: how many connections? ===")
    run("A", "--http1.1", urls)
    run("A", "--http2", urls)


def demo_b():
    urls = [f"{HOST}/delay/2"] * 8
    print("\n=== B. Eight 2-second requests under a browser-style 6-connection cap ===")
    run("B", "--http1.1", urls, parallel_max=6)
    run("B", "--http2", urls)


def demo_c():
    urls = [f"{HOST}/delay/3", f"{HOST}/get"]
    print("\n=== C. Slow request then fast request on ONE connection ===")
    run("C", "--http1.1", urls, parallel_max=1)
    run("C", "--http2", urls)


TITLES = {
    "A": "Four parallel GETs: how many connections?",
    "B": "Eight 2-second requests under a browser-style six-connection cap",
    "C": "Slow request then fast request on one connection",
}

if __name__ == "__main__":
    args = sys.argv[1:]
    out = None
    if "--json" in args:
        i = args.index("--json"); out = args[i + 1]; del args[i:i + 2]
    picks = [a.upper() for a in args] or ["A", "B", "C"]
    for p in picks:
        {"A": demo_a, "B": demo_b, "C": demo_c}[p]()
    if out:
        curl_ver = subprocess.run(["curl", "--version"], capture_output=True,
                                  text=True).stdout.split("\n")[0]
        doc = {"generated": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
               "host": HOST, "curl": curl_ver, "titles": TITLES, "runs": RECORD}
        with open(out, "w") as fh:
            json.dump(doc, fh, indent=1)
        print(f"\nwrote {out}")
