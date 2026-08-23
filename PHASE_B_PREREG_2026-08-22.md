# Phase B — Pre-registration for the N=100 run

**Locked 2026-08-22, before any results are seen. Extends `PHASE_B_L1_DESIGN.md`.**

## What changed since the pilot

1. **Leakage fix.** The pilot's 40 "held-out" prompts were the first 40 shuffled GSM8K prompts (seed=0) and first 40 HumanEval indices — a strict subset of the 100+100 pool the L1 MLP was trained on. All Phase B eval prompts here start at index `TRAIN_POOL_N=100` (from the same seed=0 shuffle for GSM8K, from raw index 100+ for HumanEval), guaranteed disjoint from L1 training data. See `L1_AUDIT_FINDINGS.md`.
2. **CadLLM threshold retuning via bracketing.** Instead of computing a matched threshold on 10-15 calibration prompts (adds a second run stage; not worth the complexity at this scale), the eval sweeps 3 CadLLM thresholds (0.15, 0.20, 0.25) that bracket L1's expected NFE, and the paired-bootstrap comparison uses the CadLLM threshold whose observed mean NFE lands closest to L1's.

## Sample sizes

- GSM8K: **100 held-out prompts** (indices 100-199 of the seed=0 shuffled test split; test split has 1319 total).
- HumanEval: **64 held-out prompts** (indices 100-163; test split has 164 total, so 64 is the ceiling for a truly-held-out set given the training pool).
- Both are single-seed. Multi-seed is deferred to the Cornell A100 run per `PHASE_B_L1_DESIGN.md`.

## Policies

- `fixed` — ProSeCo default schedule (ω=2 for GSM8K, ω=2 for HumanEval; S=1 for GSM8K, S=4 for HumanEval — per paper Table 3 Max settings).
- `cadllm_linear:0.15` — brackets L1's NFE from above (lower threshold = more invocations).
- `cadllm_linear:0.20` — brackets L1's NFE from near.
- `cadllm_linear:0.25` — brackets L1's NFE from below (matches pilot's cadllm_linear:0.25 point).
- `l1_mlp:0.40` — L1 MLP threshold from the pilot; the primary policy of interest.

Every non-corrector-policy parameter matches paper Table 3 Max (see `phase_b_pilot.py BENCH_CFG`):
- steps=1024, gen_length=1024, block_length=32
- temperature=0 (greedy), remasking=low_confidence
- GSM8K: max_corrector_steps_per_loop=1; HumanEval: max_corrector_steps_per_loop=4

**Intentional deviations from paper eval** (unchanged from pilot to keep L1 inference distribution matching its training distribution):
- GSM8K prompt: no few-shot examples (paper uses nemo_skills 8-shot CoT template). Both policies see the same prompt so the comparison is fair; absolute accuracy will be lower than the paper's Table 3 numbers.
- Answer parsing: `\boxed{N}` regex (unchanged from pilot).
- HumanEval prompt matches `llada/prompt_configs/code.yaml` verbatim.

## Primary pre-registered comparison

**`l1_mlp:0.40` vs the CadLLM threshold whose mean NFE lands closest to L1's mean NFE, paired on identical prompts, per benchmark.**

Test: 500-iter paired cluster-bootstrap over held-out prompt ids of the accuracy delta.

- **PASS**: 95% CI lower bound above zero on GSM8K OR HumanEval.
- **KILL trigger**: `l1_mlp:0.40` loses to `fixed` at both benchmarks with paired-bootstrap 95% CI upper bound below zero.
- **AMBIGUOUS**: CI straddles zero on both — the pre-committed outcome that motivates the Cornell A100 ask (multi-seed + larger N shrinks CI ~2-3x, also resolves the int8/T4 quantization confound).
- **THIRD OUTCOME (added 2026-08-22)**: if the eventual A100 run also lands ambiguous, the accuracy-improvement claim is dead at this model scale. Paper pivots to (a) the diagnostic signal contribution (Phase A: `shape > mean` scalar confidence, +9pp R² held-out AUC on 22k invocations), plus (b) compute savings at accuracy parity (`cadllm_linear` and L1 match `fixed` accuracy at fewer FLOPs).

## Secondary comparison

`l1_mlp:0.40` vs `fixed` — same test protocol. Sanity check for the kill trigger. Also lets us report the Pareto position.

## What we're NOT doing (locked to preserve interpretability)

- No feature-set changes since Phase A rev. 3.
- No MLP retraining on different data — the same `l1_weights.json` is used.
- No prompt-template changes between pilot and this run.
- No cherry-picking a specific CadLLM threshold post-hoc. The primary comparison uses whichever bracket point lands closest in mean NFE, decided by the observed NFEs, not by which one L1 beats.

## What still limits this run

- Single-seed. Cannot separate the L1-vs-CadLLM effect from within-prompt decoding stochasticity. Cornell A100 run adds seeds.
- int8/T4 quantization is unchanged. Cornell A100 fp16/bf16 run resolves this.
- CadLLM is represented by its mechanism (scalar-confidence-linear controller), not its released implementation. Deferred to a Cornell-scale head-to-head.
- HumanEval N=64 is the ceiling of the truly-held-out set given how the training pool was scoped. Widening this requires retraining L1 on a smaller training pool, deferred.

## Compute

- Estimated: 100 gsm8k + 64 humaneval = 164 prompts × 5 policies × ~5-6 min/sample avg on T4 int8 ≈ 68-82 hours. Runs in tmux `phase_b_v2`, checkpoints per-prompt for partial-analysis-if-interrupted.
