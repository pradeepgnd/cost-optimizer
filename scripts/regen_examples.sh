#!/usr/bin/env bash
# Regenerate output_examples from the current code in SAMPLE_MODE. Deletes the sample runs DB first so run_ids can be reused.
set -euo pipefail
cd "$(dirname "$0")/.."
rm -f runs-sample.db
for i in 1 2 3; do
  SAMPLE_MODE=true python run.py --input "input_examples/example_$i.json" --output "output_examples/example_${i}_output.json"
done
echo "regenerated 3 outputs; traces in logs/"
