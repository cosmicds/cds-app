#!/usr/bin/env bash
# Regenerate Pydantic models from the live CosmicDS OpenAPI schemas.
# Run from anywhere inside the cds-client package:
#
#   bash packages/cds-client/scripts/generate_models.sh
#
# Requires: uv (https://docs.astral.sh/uv/)
set -euo pipefail

MODELS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../src/cds_client/models" && pwd)"

COMMON_ARGS=(
    --output-model-type pydantic_v2.BaseModel
    --use-standard-collections
    --use-union-operator
    --input-file-type openapi
)

echo "Generating base models..."
uvx --from "datamodel-code-generator[http]" datamodel-codegen \
    --url https://api.cosmicds.cfa.harvard.edu/docs.json \
    --output "$MODELS_DIR/_generated_base.py" \
    "${COMMON_ARGS[@]}"

echo "Generating Hubble models..."
uvx --from "datamodel-code-generator[http]" datamodel-codegen \
    --url https://api.cosmicds.cfa.harvard.edu/hubbles_law/docs.json \
    --output "$MODELS_DIR/_generated_hubble.py" \
    "${COMMON_ARGS[@]}"

# Prepend the DO NOT EDIT banner (codegen only writes its own header)
for f in "$MODELS_DIR/_generated_base.py" "$MODELS_DIR/_generated_hubble.py"; do
    tmp=$(mktemp)
    head -n 2 "$f" > "$tmp"                        # keep codegen header lines
    echo "#" >> "$tmp"
    echo "# DO NOT EDIT — regenerate with: scripts/generate_models.sh" >> "$tmp"
    tail -n +3 "$f" >> "$tmp"
    mv "$tmp" "$f"
done

echo "Done. Review any field changes in base.py / hubble.py wrappers."
