#!/usr/bin/env python3
"""Read and print events from an SSE endpoint."""

import sys
from urllib.request import urlopen


def read_events(url):
    event = {"data": [], "has_data": False}
    with urlopen(url, timeout=30) as response:
        content_type = response.headers.get_content_type()
        if content_type != "text/event-stream":
            raise ValueError(f"Expected text/event-stream, got {content_type}")

        for raw_line in response:
            line = raw_line.decode("utf-8").rstrip("\r\n")
            if not line:
                if event["has_data"]:
                    data = "\n".join(event["data"])
                    print(
                        f"id={event.get('id', '')!r} "
                        f"event={event.get('event', 'message')!r} "
                        f"data={data}"
                    )
                event = {"data": [], "has_data": False}
            elif line.startswith(":"):
                print(f"comment: {line[1:].strip()}")
            else:
                field, _, value = line.partition(":")
                if value.startswith(" "):
                    value = value[1:]
                if field == "data":
                    event["data"].append(value)
                    event["has_data"] = True
                elif field in {"event", "id", "retry"}:
                    event[field] = value


if __name__ == "__main__":
    read_events(sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/events")
