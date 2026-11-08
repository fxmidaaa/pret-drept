#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "Usage: bash scripts/smoke_container.sh IMAGE TRUSTED_SYNTHETIC_MODEL" >&2
    exit 2
fi

scratch=$(mktemp -d)
container=
cleanup() {
    status=$?
    if [ -n "$container" ]; then
        if [ "$status" -ne 0 ]; then
            docker logs "$container" >&2 || true
        fi
        docker rm -f "$container" >/dev/null || true
    fi
    rm -rf -- "$scratch"
}
trap cleanup EXIT

# The temporary directory is private to the caller. Its mounted demo file is readable by UID 10001.
cp -- "$2" "$scratch/model.joblib"
chmod 0644 "$scratch/model.joblib"
container=$(docker run --detach --publish 127.0.0.1::8000 \
    --mount "type=bind,source=$scratch/model.joblib,target=/models/model.joblib,readonly" "$1")
url="http://$(docker port "$container" 8000/tcp)"
test "$(docker exec "$container" id -u)" = 10001

for _ in $(seq 1 45); do
    if curl --silent --fail --max-time 2 "$url/health" >/dev/null; then
        break
    fi
    sleep 1
done

curl --silent --show-error --fail --max-time 10 "$url/health" > "$scratch/health.json"
curl --silent --show-error --fail --max-time 45 "$url/options" > "$scratch/options.json"
curl --silent --show-error --fail --max-time 30 "$url/" > "$scratch/index.html"
curl --silent --show-error --fail --max-time 30 "$url/predict" \
    -H 'Content-Type: application/json' \
    -d '{"rooms":2,"area":55,"floor":3,"total_floors":9,"sector":"centru","author":"agenție","price":700}' \
    > "$scratch/prediction.json"

python - "$scratch" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
assert json.loads((root / "health.json").read_text()) == {"status": "ok"}
assert "centru" in json.loads((root / "options.json").read_text())["sector"]
assert "overpriced" in (root / "index.html").read_text()
response = json.loads((root / "prediction.json").read_text())
assert response["fair_price"] > 0 and response["listed_price"] == 700
assert response["verdict"] in {"fair price", "overpriced", "good deal"}
assert response["drivers"]
print("Container served a prediction with the demo model as UID 10001.")
PY
