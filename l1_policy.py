"""L1 corrector-entry policy.

Small MLP over the five multi-conf features from Phase A's S1 v3 analysis.
Feature set is FROZEN — position and mask-size features excluded per the
Phase A finding that they add only ~+0.001 AUC on top of confidence shape
and inflate overfitting risk on Phase B's smaller eval subsets.

Two entry points:
  L1Policy(weights_path).predict(features_dict) -> float in [0, 1]
  features_from_predictor_logits(logits, active_mask) -> dict
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch

FEATURE_KEYS = (
    "predictor_conf_mean_active",
    "predictor_conf_min_active",
    "predictor_conf_std_active",
    "predictor_entropy_mean_active",
    "predictor_entropy_max_active",
)


class L1Policy:
    """One-hidden-layer MLP, 5 → 16 → 1, sigmoid output.

    Weights + input normalization stats are loaded from a JSON produced by
    l1_training.py. Runs on CPU with numpy — the entire forward pass is two
    matmuls per invocation opportunity, so it doesn't move to GPU."""

    def __init__(self, weights_path: str | Path):
        with open(weights_path) as f:
            state = json.load(f)
        self.W1 = np.array(state["W1"], dtype=np.float32)  # (5, 16)
        self.b1 = np.array(state["b1"], dtype=np.float32)  # (16,)
        self.W2 = np.array(state["W2"], dtype=np.float32)  # (16, 1)
        self.b2 = np.array(state["b2"], dtype=np.float32)  # (1,)
        self.mean = np.array(state["mean"], dtype=np.float32)  # (5,)
        self.std = np.array(state["std"], dtype=np.float32)  # (5,)
        self.threshold = float(state.get("threshold", 0.5))

    def _forward(self, x: np.ndarray) -> float:
        z = (x - self.mean) / (self.std + 1e-8)
        h = np.maximum(0.0, z @ self.W1 + self.b1)
        logit = float(h @ self.W2 + self.b2)
        return 1.0 / (1.0 + np.exp(-logit))

    def predict(self, features: dict) -> float:
        """P(was_useful | features)."""
        x = np.array([features[k] for k in FEATURE_KEYS], dtype=np.float32)
        return self._forward(x)

    def should_invoke(self, features: dict) -> bool:
        """Threshold-based invocation decision."""
        return self.predict(features) >= self.threshold

    def set_threshold(self, threshold: float) -> None:
        """For matched-FLOPs calibration."""
        self.threshold = float(threshold)


class CadLLMLinearPolicy:
    """Fair-comparison baseline: scalar mean confidence, one threshold.

    Represents the mechanism family (CadLLM, AdaBlock-dLLM, DepCap, Dynamic-dLLM,
    KLASS, Apple-RL, TraceLock, LESS). NOT CadLLM's released code."""

    def __init__(self, threshold: float = 0.7):
        self.threshold = float(threshold)

    def predict(self, features: dict) -> float:
        # Directly return 1 - mean_confidence as the "useful" score.
        # Low confidence -> high probability the corrector will change something.
        return 1.0 - float(features["predictor_conf_mean_active"])

    def should_invoke(self, features: dict) -> bool:
        return self.predict(features) >= self.threshold

    def set_threshold(self, threshold: float) -> None:
        self.threshold = float(threshold)


class FixedPolicy:
    """Baseline: invoke every apply_corrector_every_n_steps steps.

    This is ProSeCo's current behavior. Its "should_invoke" ignores features and
    just checks the step index. Kept here for interface uniformity so the runner
    can swap all three policies through one path."""

    def __init__(self, every_n: int = 2):
        self.every_n = int(every_n)

    def should_invoke_at_step(self, step_in_block: int) -> bool:
        return (step_in_block + 1) % self.every_n == 0


def features_from_predictor_logits(
    logits: torch.Tensor,
    active_mask: torch.Tensor,
    active_region_start: int,
    block_end: int,
) -> dict:
    """Compute the five multi-conf features from predictor logits.

    Args:
        logits: full predictor logits, shape (B, seq_len, vocab)
        active_mask: bool mask, shape (B, block_length), True where the position
                     is still masked (i.e. the corrector could touch it)
        active_region_start: int, index where the block-slice starts
        block_end: int, index where the block-slice ends

    Returns a dict with the five FEATURE_KEYS, all Python floats. If no positions
    are active in the block, returns zeros — the caller decides what to do."""
    with torch.no_grad():
        pl = logits[:, active_region_start:block_end].float()
        pp = torch.softmax(pl, dim=-1)
        top1 = pp.max(dim=-1).values.reshape(-1)
        ent = -(pp.clamp_min(1e-12).log() * pp).sum(dim=-1).reshape(-1)
        am = active_mask.reshape(-1).bool()
        if not am.any():
            return {k: 0.0 for k in FEATURE_KEYS}
        t = top1[am]
        e = ent[am]
        return {
            "predictor_conf_mean_active": float(t.mean()),
            "predictor_conf_min_active": float(t.min()),
            "predictor_conf_std_active": float(t.std()) if t.numel() > 1 else 0.0,
            "predictor_entropy_mean_active": float(e.mean()),
            "predictor_entropy_max_active": float(e.max()),
        }


def load_policy(spec: str, weights_path: str | None = None):
    """Factory for the three policies. `spec` is one of:

      "fixed:N"          — invoke every N steps (N defaults to 2)
      "cadllm_linear:T"  — CadLLM-family control, threshold T on (1 - conf_mean)
      "l1_mlp:PATH"      — L1 MLP with weights loaded from PATH
      "l1_mlp"           — L1 MLP with weights from `weights_path` argument
    """
    if spec.startswith("fixed"):
        n = int(spec.split(":", 1)[1]) if ":" in spec else 2
        return FixedPolicy(every_n=n)
    if spec.startswith("cadllm_linear"):
        t = float(spec.split(":", 1)[1]) if ":" in spec else 0.3
        return CadLLMLinearPolicy(threshold=t)
    if spec.startswith("l1_mlp"):
        # Formats accepted:
        #   "l1_mlp"                       -> weights_path arg, default threshold
        #   "l1_mlp:0.40"                  -> weights_path arg, threshold=0.40
        #   "l1_mlp:/path/to/w.json"       -> that path, default threshold
        #   "l1_mlp:/path/to/w.json:0.40"  -> that path, threshold=0.40
        rest = spec[len("l1_mlp"):].lstrip(":")
        path = weights_path
        threshold = None
        if rest:
            parts = rest.rsplit(":", 1)
            # heuristic: last chunk is a threshold if it parses as a float in [0,1]
            def is_thresh(s):
                try:
                    v = float(s)
                    return 0.0 <= v <= 1.0
                except ValueError:
                    return False
            if len(parts) == 2 and is_thresh(parts[1]):
                path = parts[0]
                threshold = float(parts[1])
            elif is_thresh(rest):
                threshold = float(rest)
            else:
                path = rest
        if path is None:
            raise ValueError(f"l1_mlp spec {spec!r} needs a weights path (either in spec or via weights_path arg)")
        p = L1Policy(weights_path=path)
        if threshold is not None:
            p.set_threshold(threshold)
        return p
    raise ValueError(f"unknown policy spec {spec!r}")
