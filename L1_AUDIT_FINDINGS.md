# L1 Audit Findings

Track B (adversarial audit) log. Append-only, dated entries.

---

## 2026-08-23 — Track B audit (fire N, commit 45fbc04 reviewed)

Scope: `l1_policy.py`, `l1_training.py`, `phase_b_pilot.py`, `phase_b_evaluate.py`,
`llada/generate.py` (corrector_policy hook), `PHASE_B_PREREG_2026-08-22.md`,
`PHASE_B_L1_DESIGN.md`. This is the first entry in this file — a prior fire
apparently found a leakage bug (referenced in commit 45fbc04's message and
already fixed in `a796b4f`/`phase_b_pilot.py`'s `TRAIN_POOL_N` logic), but
never got it pushed here (no GitHub App install at the time). Folding a note
about that below since the file didn't exist to append to.

### 1. CRITICAL — `phase_b_pilot.py` CLI defaults don't match the locked pre-registration

`PHASE_B_PREREG_2026-08-22.md` locks:
- Policies: `fixed`, `cadllm_linear:0.15`, `cadllm_linear:0.20`, `cadllm_linear:0.25`, `l1_mlp:0.40`
- Sample sizes: GSM8K **100**, HumanEval **64**

But `phase_b_pilot.py`'s `argparse` defaults are still the *original pilot's*
values, unchanged since the 185e2ca commit:

```python
p.add_argument("--n_samples", type=int, default=40)
...
p.add_argument(
    "--policies", nargs="+",
    default=[
        "fixed",
        "cadllm_linear:0.20", "cadllm_linear:0.30", "cadllm_linear:0.40",
        "l1_mlp:0.35", "l1_mlp:0.50", "l1_mlp:0.65",
    ],
)
```

If `phase_b_pilot.py` is invoked without explicitly overriding `--policies`
and `--n_samples` on the EC2 box, two things go wrong silently (no crash,
no warning):

- **`l1_mlp:0.40` — the primary policy of interest — is never run at all.**
  `phase_b_evaluate.py`'s default `--l1_policy` is `l1_mlp:0.40`; if it's
  missing from the data, `evaluate()` prints `SKIP: {l1_policy} not in data`
  for every benchmark and produces **no verdict**, not an error — this could
  go unnoticed until someone reads the printed output at the end of a
  68-82 hour T4 run.
- **`--n_samples` defaults to 40, not the locked N=100 (gsm8k).** HumanEval
  self-caps at 64 regardless (`load_benchmark`'s `n_avail` clamp), so that
  one accidentally comes out right even with the stale default — but GSM8K
  would silently run at N=40, not the pre-registered N=100, which changes
  the bootstrap CI width the whole "AMBIGUOUS → pitch Yair for A100" decision
  tree depends on.

**Recommend:** update the `--policies` and `--n_samples` defaults in
`phase_b_pilot.py` to match `PHASE_B_PREREG_2026-08-22.md` exactly (or, more
robustly, have `phase_b_pilot.py` read the policy/N list from the prereg doc
or a shared constants module so the two can't drift again), and before
trusting any `phase_b/pilot.jsonl` output, confirm the run command actually
used `--policies fixed cadllm_linear:0.15 cadllm_linear:0.20 cadllm_linear:0.25 l1_mlp:0.40 --n_samples 100`
(or equivalent per-benchmark control) rather than the bare defaults.

**If the v2 run on EC2 was already launched with explicit CLI args
overriding these defaults, this finding is moot for that run — but the
stale defaults are still a footgun for the next person (or Cornell A100
run) who invokes the script from memory of the pre-reg doc rather than
reading the script.**

### 2. MEDIUM — `gsm8k_answer_match` takes the first `\boxed{}`, not the last

```python
m = re.search(r"\\boxed\{([^}]*)\}", text)
```

`re.search` returns the first match. The GSM8K prompt asks the model to put
its final answer in `\boxed{}`, but nothing stops a model from writing an
intermediate wrong number in `\boxed{}` mid-reasoning and self-correcting
later in the same generation (e.g. "...so the total is \boxed{48}... wait,
I need to add the last leg: \boxed{54}."). Under greedy decoding this is
less common than with sampling, but it's a real failure mode for CoT
generations that don't perfectly follow the prompt's formatting instruction,
and it silently produces a **wrong accuracy number**, not a crash — the kind
of bug that's invisible in a bulk accuracy table.

**Concrete failure scenario:** any GSM8K generation containing more than one
`\boxed{...}` span where the last one is correct and an earlier one is
wrong (or vice versa) is scored against the *wrong* one.

**Recommend:** switch to `list(re.finditer(...))[-1]` (last match), which is
the more common convention for CoT eval harnesses, or grep the pilot output
for `total_boxed_matches > 1` cases to see if this affects any existing
`pilot.jsonl` rows before trusting the accuracy table.

### 3. LOW — leakage-avoidance in `phase_b_pilot.py` rests on an unverified assumption, not an enforced invariant

`TRAIN_POOL_N = 100` in `phase_b_pilot.py` assumes the L1 MLP was trained
*only* on the first 100 shuffled (seed=0) GSM8K prompts and indices 0-99 of
HumanEval. But `l1_training.py`'s `load_records()` doesn't filter by sample
index at all — it globs every `*.jsonl` under `s1/runs/` and
`s1/runs/v2_n50/` except paths containing `v1_pre_confidence`, `prior`, or
`v3_partial`. There is no assertion anywhere that ties the actual set of
`sample_id`s used in training to `TRAIN_POOL_N`.

In this case the numbers happen to check out: `l1_weights.json`'s
`meta.n_train_prompts + meta.n_test_prompts = 160 + 40 = 200`, matching
`PHASE_B_L1_DESIGN.md`'s claimed "200 prompts total" for pooled v2+v3 — so
whatever's on disk in `s1/runs/` right now is consistent with the intended
pool, and the `aa12bdb` "S1 full int8" run's output (2026-08-15, likely
N=200/benchmark by the `run_s1.py` default) does not appear to have leaked
into it. But this is inference from a summary statistic, not a guarantee:
nothing stops a future retrain from silently picking up whatever files
happen to sit in `s1/runs/` at that time, including files from a fuller run
that *does* cover indices 100+.

**Recommend:** have `l1_training.py` print (or assert on) the actual
min/max per-benchmark sample index used in training, and have
`phase_b_pilot.py`'s `load_benchmark` assert that none of its held-out
sample ids appear in that logged training set — turning the current
"the numbers happen to line up" into a checked invariant.

---

## 2026-08-23 — Track B audit (fire N+1, commit 6b015b2 reviewed)

Re-read `l1_policy.py`, `l1_training.py`, `phase_b_pilot.py`,
`phase_b_evaluate.py`, and the `corrector_policy` hook in `llada/generate.py`
end to end. Findings #1-#3 above are confirmed fixed/deferred as described
in `b0b1b8d`'s commit message (verified against current file contents, not
just the commit message). Traced the predictor/corrector NFE bookkeeping in
`generate.py` (lines 162-372): predictor_nfe increments unconditionally
every step regardless of `corrector_policy`, and the corrector only
overwrites already-committed (`~active_mask`) positions, never the ones
`get_transfer_index` is about to newly unmask — so predictor NFE per block
is fixed across all three policies and only `corrector_nfe` varies with the
invocation decision. That's the load-bearing assumption behind "matched
total NFE" and it holds. Two new findings below.

### 4. HIGH — `l1_training.py`'s reported `final_test_auc` (the AUC=0.9589
headline number) is optimistically biased by checkpoint selection on the
same set it's reported on

```python
for epoch in range(args.epochs):
    ...
    with torch.no_grad():
        probs = torch.sigmoid(model(Xte)).numpy()
    auc = roc_auc_score(yte_np, probs)
    if auc > best_auc + 1e-4:
        best_auc = auc
        best_state = {...}          # <- checkpoint chosen by peeking at Xte/yte
        patience = 0
    else:
        patience += 1
    ...
    if patience >= args.patience:   # <- early stop also driven by Xte/yte
        break
...
model.load_state_dict(best_state)
...
final_auc = roc_auc_score(yte_np, probs)   # <- same Xte/yte, reported as the result
```

`Xte`/`yte_np` (the grouped 20% held-out split) is used for three things:
picking which of up to 300 epoch checkpoints to keep (`best_state`), when to
stop early (`patience`), *and* the final reported metric. There's no third
split — no separate validation set distinct from the number that gets
written to `l1_weights.json["meta"]["final_test_auc"]` and quoted as "L1 MLP
hits AUC=0.9589 matching the Phase A linear ceiling." Selecting the
best-of-~300 checkpoints by a metric computed on a fixed set of ~20% of
invocations, then reporting that same metric as the generalization estimate,
is optimistic-selection bias — the reported number is the best draw over up
to 300 correlated trials on one fixed sample, not an unbiased held-out
estimate. The grouped-by-`sample_id` split protects against row-level
leakage (a real invocation from a test prompt was never in the gradient
step), but does not protect against *this* — checkpoint/epoch selection is a
form of fitting to the held-out set, just at the epoch-index granularity
instead of the parameter granularity.

**Concrete scenario:** two epochs, A and B, have true (infinite-data)
generalization AUC 0.955 and 0.950 respectively, but on this specific
160/40-prompt split epoch B happens to score 0.959 due to sampling noise in
which 40 prompts landed in `Xte`. `best_auc` picks B (higher observed AUC),
`final_test_auc` reports 0.959 — a number that overstates true
generalization by ~0.009, undetectable from the training run's own output
because there's no independent set left to check it against.

**Why this matters for the current bet:** Phase A's own held-out ΔAUC
(+0.019 to +0.033 over the scalar-confidence baseline) is a fairly narrow
margin. If the MLP's *reported* 0.9589 is inflated by selection bias while
the *linear baseline it's being compared to* wasn't fit with the same
epoch-hunting procedure (logistic regression has no early-stopping
checkpoint to select), the "MLP matches the linear ceiling" claim is not
comparing like with like — the linear model's number is a plain held-out
fit, the MLP's is a best-of-300-checkpoints number on the same held-out set.

**Recommend:** three-way split (train / val for early-stop+checkpoint
selection / test reported once), or k-fold CV with checkpoint selection
inside each fold, or at minimum re-run with a fixed epoch count (no early
stopping, no best-checkpoint tracking) and report that AUC instead — if it's
close to 0.9589 the bias is small and this is moot; if it's meaningfully
lower, the Phase B pilot's L1 threshold (`l1_mlp:0.40`) was calibrated
against an overstated confidence in the underlying model and the memo's
"matches Phase A ceiling" framing needs a caveat regardless of how the
downstream-accuracy pilot itself turns out. Does not invalidate the Phase B
*pilot* (that's measuring downstream accuracy directly, not this AUC), so
not paging on this — but it undercuts the AUC evidence used to justify
running the pilot in the first place and should be fixed before the memo
cites 0.9589 as a clean number.

### 5. LOW — `phase_b_evaluate.py`'s rescore path can silently no-op on any
exception while loading golds, with no signal that rescoring didn't happen

```python
for held_out in (True, False):
    try:
        for s in load_benchmark(bench, 200, held_out=held_out):
            gold_by_id[s["id"]] = (s["gold"], bench)
    except (AssertionError, Exception):
        pass  # ok if we can't cover both; whatever's loaded is fine
```

`except (AssertionError, Exception)` is redundant (`AssertionError` is a
subclass of `Exception`) and, more importantly, catches *everything* —
`ConnectionError` from a failed HF Hub fetch, a `KeyError` from a schema
change, etc. — not just the expected case (an `AssertionError` from
`load_benchmark`'s bounds check when `held_out=False` and `n=200` exceeds
`n_avail`). If `load_dataset` can't reach the Hub (analysis run off the EC2
box, no cached copy, flaky network), `gold_by_id` silently stays empty,
`r["id"] in gold_by_id` is `False` for every row, `n_rescored` stays 0 with
no distinguishing message from the legitimate "nothing needed rescoring"
case, and `evaluate()` proceeds to print a verdict using whatever `correct`
values were already in the JSONL — silently skipping the "auto-rescore on
load" this file's own module docstring promises, with no error and no
warning. Given findings #1 and #2 were both about defaults/parsing silently
producing wrong numbers without a crash, this is the same failure shape one
layer up: the *rescue path* for stale scoring can itself silently fail to
run.

**Recommend:** narrow the except to `AssertionError` only (the one case the
comment actually names), and print a warning when `gold_by_id` ends up
empty or covers only a subset of the ids seen in `rows`, e.g. `warn:
{n_missing}/{len(rows)} rows have no matching gold, rescore skipped for
them` — so a network hiccup during offline analysis shows up in the output
instead of silently falling back to old scores.

### Noted, not a bug: unsandboxed HumanEval execution

`humaneval_pass()` runs model-generated code via `subprocess.run(["python3",
"-c", full_code], timeout=10)` with no sandboxing beyond the timeout. This
is standard practice for HumanEval-style eval harnesses (pass@k inherently
requires executing generated code) and not something introduced by this
pilot, but flagging since it's running on the same EC2 box as everything
else — a generation that imports something destructive would run
unsandboxed. Not recommending a change given eval-harness convention, just
noting it's there.
