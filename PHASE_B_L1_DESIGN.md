# Phase B — L1 Design

**Status:** design locked 2026-08-18. Everything below is pre-committed before any Phase B numbers are seen.

## Goal

Turn the Phase A held-out AUC edge (ΔAUC = +0.019 GSM8K / +0.033 HumanEval / +0.027 combined, over a scalar-confidence-linear baseline) into a downstream-accuracy edge at matched total FLOPs, when the policy actually runs inside ProSeCo's sampler.

## Decisions

**Feature set** — five features, per corrector-invocation opportunity, computed from the predictor's logits over active-mask positions in the current block:

- `predictor_conf_mean_active` — mean top-1 probability
- `predictor_conf_min_active` — min top-1 probability
- `predictor_conf_std_active` — std of top-1 probability
- `predictor_entropy_mean_active` — mean per-position entropy
- `predictor_entropy_max_active` — max per-position entropy

Position features (`block_idx`, `active_mask_size`) are **excluded**. Phase A showed they add ~+0.001 AUC on top of confidence-shape; keeping them invites the same overfitting that trashed HumanEval in rev. 2 at N=50 and would recur on the smaller Phase B eval subsets.

**Model** — 1-hidden-layer MLP, 5 → 16 → 1 with ReLU + sigmoid. ~100 params. Small on purpose:

- Phase A's linear logistic regression already captured essentially all of the moat; a transformer or deeper MLP has no signal to expand into and only adds overfitting risk on 200 prompts.
- Fits on CPU in seconds, deploys inline in `generate.py` with a single matmul per invocation opportunity.

**Training** — pooled v2 (N=50) + v3 (N=100) data. 200 prompts total, ~34k invocations. `sklearn.model_selection.GroupShuffleSplit` by `sample_id`, 80/20. BCE loss, Adam(lr=1e-3), early stopping on held-out AUC (patience=20 epochs). Save best-AUC weights.

**Inline deployment** — `llada/generate.py` gets a `corrector_policy` parameter that selects among:

- `"fixed"` — current behavior, invoke every `apply_corrector_every_n_steps` steps
- `"cadllm_linear"` — invoke when `predictor_conf_mean_active < threshold`; threshold calibrated per benchmark to match `"fixed"` total NFE
- `"l1_mlp"` — invoke when MLP(features) > threshold; threshold likewise calibrated

The interface for the two adaptive policies is identical — `policy(features_dict) → float` — so they're a fair comparison, not a rigged one.

**Baseline that matters** — `cadllm_linear` is the fair one-signal control (scalar mean confidence, linearly thresholded). We are NOT running against CadLLM's released code in this pilot; the memo language is "the CadLLM-family mechanism" and it stays that way until Cornell compute funds the full-scale head-to-head.

## Evaluation

**Endpoint** — downstream task accuracy at matched total corrector NFEs.

- GSM8K: solve rate (exact answer match in `\boxed{}`)
- HumanEval: pass@1

**Matched-FLOPs protocol** — for each policy, sweep a threshold / knob that produces different total NFE budgets. Pick pairs across policies at the closest total NFE. Report accuracy for each policy at 3-4 matched budget levels covering the FLOP range ProSeCo Max naturally uses.

**Sample size** — 40 held-out prompts per benchmark, 1 seed. Same 40 held-out prompts across all policy conditions, so paired comparisons are possible.

## Pre-committed success criteria — WRITTEN BEFORE ANY PHASE B NUMBERS ARE SEEN

Evaluated on the 40 held-out prompts per benchmark:

1. **Primary — GSM8K.** L1-MLP's mean solve rate exceeds `cadllm_linear`'s solve rate at the nearest matched-NFE budget, and the **paired cluster-bootstrap 95% CI on the delta (resampling prompts with replacement, 500 iters) has lower bound above zero**.

2. **Primary — HumanEval.** Same test.

3. **PASS if either primary passes** — 2/2 is the strong publication case; 1/2 is enough to justify a Cornell pitch for multi-seed multi-benchmark scaling.

4. **KILL trigger.** L1-MLP loses to *fixed* (not just to `cadllm_linear`) on both benchmarks at matched FLOPs with paired-bootstrap CI upper bound below zero. That means the learned policy is worse than doing nothing; L1 dies for real.

5. **Ambiguous zone (CI-crosses-zero on both).** Report as-is to Yair. Do not spin. Pitch weakened but not dead — next step is multi-seed run to shrink CIs, on Cornell compute.

## Confounds that Phase B does NOT resolve on its own

- **Label validity.** Phase A's `was_useful` label = corrector disagreement. The training data for the L1 MLP inherits this. Phase B's downstream-accuracy endpoint is what tests whether disagreement-predicting is exploitation-worthy, but the policy itself is trained on the proxy. If it fails, unclear whether it's a bad policy or a bad label — mitigation: also train a second L1 MLP variant on ProSeCo's "did-changing-this-block-help-final-accuracy" oracle (extractable offline from v2+v3 by matching final generation to gold), report both.
- **Quantization confound.** Everything trained on int8 + T4 data. Before committing Cornell A100 hours, a cheap fp16 calibration run on the same 200 prompts confirms the confidence-shape signal survives at higher precision. This is the Phase B day-1 check, not a Phase C item.
- **CadLLM-as-proxy.** `cadllm_linear` is the mechanism-family control, not the released implementation. This limitation stays honest in the memo.

## Compute plan

- T4 instance (already running, no new spend).
- CPU-only training (l1_training.py) — 1-2 hours max.
- Matched-FLOPs eval: ~40 prompts × 3 policies × 3-4 budgets = ~500-800 sampling runs on GSM8K + same on HumanEval ≈ 3-5 days T4.
- Total incremental spend: ~$60-90 T4 hours on top of the existing burn.

## Timeline

| Day | Work |
|---|---|
| 1 | Write `l1_policy.py`, `l1_training.py`, train, save weights, offline AUC sanity |
| 2 | Implement `cadllm_linear` + `l1_mlp` inline in `llada/generate.py`, calibrate thresholds |
| 2 | Cheap fp16 calibration check on 20 prompts to check quantization confound |
| 3-5 | Matched-FLOPs pilot on GSM8K |
| 5-7 | Matched-FLOPs pilot on HumanEval |
| 8-10 | Bootstrap CIs, accuracy table, write memo v4 |

## Failure mode → next step

- Both benchmarks lose to fixed: kill L1, pivot to next open idea in `IDEAS.md`.
- Both ambiguous: multi-seed run on Cornell compute.
- Either wins: pitch v4 to Yair with the accuracy table.
