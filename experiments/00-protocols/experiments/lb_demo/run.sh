#!/usr/bin/env bash
# Start two backends and an nginx with an L7 listener (:8080) and an L4 listener (:8081),
# then show where requests on ONE client connection land. Needs docker.
set -euo pipefail
cd "$(dirname "$0")"
cleanup() { docker rm -f backend1 backend2 lb >/dev/null 2>&1 || true; docker network rm lbdemo >/dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup
docker network create lbdemo >/dev/null
for i in 1 2; do
  docker run -d --rm --name backend$i --hostname backend$i --network lbdemo \
    -v "$PWD/backend.py:/backend.py:ro" python:3.12-alpine python /backend.py >/dev/null
done
# wait until both backends answer before putting nginx in front of them
for i in 1 2; do
  for _ in $(seq 1 30); do
    docker exec backend$i python -c 'import urllib.request;urllib.request.urlopen("http://127.0.0.1:8000/")' 2>/dev/null && break
    sleep 0.5
  done
done
docker run -d --rm --name lb --network lbdemo -p 8080:8080 -p 8081:8081 \
  -v "$PWD/nginx.conf:/etc/nginx/nginx.conf:ro" nginx:alpine >/dev/null
curl -s --retry 15 --retry-delay 1 --retry-connrefused -o /dev/null http://127.0.0.1:8080/ || true

U=http://127.0.0.1
echo; echo "=== 1. L7 proxy, HTTP/2: four requests on ONE connection ==="
curl -sv --http2-prior-knowledge -Z $U:8080/a $U:8080/b $U:8080/c $U:8080/d 2>&1 \
  | grep -E '^\* Connected to|OPENED stream|^< x-upstream|served by'
echo; echo "=== 2. L7 proxy, HTTP/1.1 keep-alive: four requests on ONE connection ==="
curl -sv --http1.1 $U:8080/a $U:8080/b $U:8080/c $U:8080/d 2>&1 \
  | grep -E '^\* Connected to|Re-using|^< X-Upstream|served by'
echo; echo "=== 3. L4 proxy, HTTP/1.1 keep-alive: four requests on ONE connection ==="
curl -sv --http1.1 $U:8081/a $U:8081/b $U:8081/c $U:8081/d 2>&1 \
  | grep -E '^\* Connected to|Re-using|served by'
echo; echo "=== 4. L4 proxy: three SEPARATE connections ==="
for i in 1 2 3; do curl -s $U:8081/; done
