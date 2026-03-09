#!/usr/bin/env bash
set -euo pipefail

REQ_FILE="${1:-$HOME/Downloads/studio_request.json}"
PIPELINE="/Users/William/Desktop/image making pipeline/trex_image_pipeline.py"

if [[ ! -f "$REQ_FILE" ]]; then
  echo "Request file not found: $REQ_FILE"
  exit 1
fi

python3 "$PIPELINE" --request-file "$REQ_FILE"
