#!/bin/bash
# S1 end-to-end runner for the L1 wedge test.
# Assumes you have already:
#   1. Cloned this fork (lhendre/proseco) to your GPU box
#   2. Created a python env with torch + transformers + datasets + huggingface_hub
#   3. Logged in to huggingface_hub (huggingface-cli login) if the ProSeCo
#      checkpoint requires auth
# Run: bash s1/run.sh

set -euo pipefail

# ---- config ----
CHECKPOINT="${CHECKPOINT:-kuleshov-group/proseco-llada-sft}"
N_SAMPLES="${N_SAMPLES:-200}"
BENCHMARKS="${BENCHMARKS:-gsm8k humaneval}"
OUT_DIR="${OUT_DIR:-s1/runs}"

# ---- env sanity ----
echo "[s1] python: $(python --version)"
echo "[s1] torch cuda available:"
python -c "import torch; print(f'  cuda={torch.cuda.is_available()} device_count={torch.cuda.device_count()}')"

# ---- deps (uncomment on a fresh box) ----
# pip install -q torch --index-url https://download.pytorch.org/whl/cu121
# pip install -q transformers datasets huggingface_hub tqdm

mkdir -p "$OUT_DIR"

echo "[s1] running: checkpoint=$CHECKPOINT n=$N_SAMPLES benchmarks=$BENCHMARKS"
python s1/run_s1.py \
    --checkpoint "$CHECKPOINT" \
    --n_samples_per_benchmark "$N_SAMPLES" \
    --benchmarks $BENCHMARKS \
    --out_dir "$OUT_DIR"

echo "[s1] analyzing..."
python s1/analyze.py "$OUT_DIR"

echo ""
echo "[s1] Done. If L1 LIVED, paste the VERDICT section back to Claude and we"
echo "     design the learned policy (Phase B, ~1-2 weeks). If L1 DIED, we"
echo "     kill it and pivot to S8 or a fresh Mode F idea."
