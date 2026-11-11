#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
    echo "Usage: bash scripts/smoke_container.sh IMAGE TRUSTED_MODEL [PREPARED_CSV]" >&2
    exit 2
fi

host_python=.venv/bin/python
if [ ! -x "$host_python" ]; then
    host_python=python3
fi
# Check host dependencies before starting the container.
"$host_python" -c 'import numpy, pandas, predict'

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

# The temporary directory is private; its mounted files are readable by UID 10001.
cp -- "$2" "$scratch/model.joblib"
cp -- "${3:-$(dirname "$2")/evaluation.csv}" "$scratch/input.csv"
chmod 0644 "$scratch/model.joblib" "$scratch/input.csv"
container=$(docker run --detach --publish 127.0.0.1::8000 \
    --mount "type=bind,source=$scratch/model.joblib,target=/models/model.joblib,readonly" \
    --mount "type=bind,source=$scratch/input.csv,target=/data/input.csv,readonly" "$1")
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

docker exec "$container" python -m mlops.batch \
    --input /data/input.csv --output /tmp/predictions
docker cp "$container:/tmp/predictions" "$scratch/predictions"

"$host_python" - "$scratch" <<'PY'
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from predict import load_bundle, model_matrix, predict_eur

root = Path(sys.argv[1])
assert json.loads((root / "health.json").read_text()) == {"status": "ok"}
assert "centru" in json.loads((root / "options.json").read_text())["sector"]
assert "overpriced" in (root / "index.html").read_text()
response = json.loads((root / "prediction.json").read_text())
assert response["fair_price"] > 0 and response["listed_price"] == 700
assert response["verdict"] in {"fair price", "overpriced", "good deal"}
assert response["drivers"]

assert (root / "predictions/_SUCCESS").is_file()
inputs = pd.read_csv(root / "input.csv")
scored = pd.concat(pd.read_csv(part) for part in sorted((root / "predictions").glob("part-*.csv")))
assert len(scored) == len(inputs)
bundle = load_bundle(root / "model.joblib")
columns = [name for name in bundle["features"] if name in inputs.columns]
pd.testing.assert_frame_equal(
    scored[columns].sort_values(columns).reset_index(drop=True),
    inputs[columns].sort_values(columns).reset_index(drop=True),
    check_dtype=False,
)
expected = predict_eur(model_matrix(scored.to_dict("records"), bundle), bundle)
np.testing.assert_allclose(scored["predicted_rent_eur"], expected, rtol=1e-5)
assert "price" not in scored.columns
print("Container passed API and Spark prediction checks as UID 10001.")
PY
