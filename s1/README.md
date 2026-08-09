# S1: Per-block corrector-usefulness measurement for L1

**Status: gate for L1** (see `IDEAS.md` in `lhendre/remasking_test` on branch `research-ideation`).

## The wedge L1 is exploiting

ProSeCo's `apply_corrector_every_n_steps` (ω) is set globally per config —
every block in every sample gets correction on the same decode-step schedule.
The paper (2602.11590 v3) shows aggregate robustness to ω/S but doesn't
measure per-block variance in whether correction was *useful*.

L1's hypothesis: per-block corrector-usefulness varies enough that a learned
per-block gate ("should THIS block get correction?") beats globally-fixed ω at
matched total FLOPs.

## What S1 measures

For every corrector invocation, `llada/generate.py` (S1-instrumented) logs:
- `block_idx`, `step_in_block` — which block, which decode step
- `corrector_break_step` — number of corrector iterations before convergence
- `broke_at_step_1` — TRUE if the corrector's first iteration produced the
  same tokens as the seed argmax = **correction was a no-op**
- `active_mask_size`, `n_active_positions_changed_by_corrector` — how many
  still-masked positions the corrector actually changed from the seed argmax

## L1 go/no-go

`s1/analyze.py` computes per-block-position:
- `frac_noop`: fraction of invocations at this block position that were no-ops
- `mean_frac_active_changed`: mean fraction of active positions the corrector
  changed

Verdict rules:
- **L1 LIVES** if CV(frac_noop) > 0.30 OR CV(frac_active_changed) > 0.30, AND
  at least one block has frac_noop > 0.70 while another has < 0.30 (the exact
  profile a per-block gate exploits: some blocks nearly always useless to
  correct, others usually useful).
- **L1 DIES** otherwise. Uniform per-block corrector behavior means a learned
  gate has nothing to allocate.

## Run

```bash
bash s1/run.sh
```

Defaults: 200 samples each on GSM8K + HumanEval, ProSeCo LLaDA-SFT checkpoint,
ProSeCo Max hyperparameters per benchmark from Table 3 of the paper.

Estimated cost: ~$10-30 on a single A10G/L4 for a night (LLaDA-8B is ~15GB
VRAM in bfloat16; a 24GB card fits it comfortably; 12GB does not without
quantization). Estimated wall-clock: 4-8 hours depending on GPU.

To smoke-test on a smaller model first:
```bash
CHECKPOINT=GSAI-ML/LLaDA-8B-Instruct N_SAMPLES=10 bash s1/run.sh
```

## Output

- `s1/runs/gsm8k_<timestamp>.jsonl`, `s1/runs/humaneval_<timestamp>.jsonl` —
  raw records
- `s1/runs/s1_verdict.png` — per-block metric plot
- Stdout: verdict table + LIVES/DIES per benchmark

Paste the VERDICT section back to Claude to move to Phase B (if LIVES) or
pivot (if DIES).
