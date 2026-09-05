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

---

## 2026-08-23 — Track B audit (fire N+2, commit 386a6c3 reviewed)

Re-read `l1_policy.py`, `l1_training.py`, `phase_b_pilot.py`, and
`llada/generate.py`'s `corrector_policy` hook again, then went one level
below the code this time and pulled the actual git blob SHAs of the files
under `s1/runs/` (the directory `l1_training.py --runs_dir` points at by
default, and the directory this repo actually has committed data in) to
check finding #3's "the numbers happen to line up" inference against the
real files rather than just `l1_weights.json`'s summary counts. Found a
concrete, previously-unflagged bug. One smaller eval-parsing bug too.

### 6. HIGH — `s1/runs/*.jsonl` contains byte-identical files committed
under different timestamp names; `l1_training.py`'s unfiltered glob loads
each one's records multiple times, overweighting those prompts in the loss
that trained `l1_weights.json` (the exact policy the live EC2 pilot is
testing right now as `l1_mlp:0.40`)

`git ls-tree` blob SHAs for the non-empty files currently in `s1/runs/`:

| blob sha (first 8) | size | files sharing it |
|---|---|---|
| `590dc20f` | 133,741 B | `gsm8k_20260810_064421.jsonl`, `gsm8k_20260811_161123.jsonl`, `gsm8k_20260813_035659.jsonl` (**3 copies**) |
| `881be987` | 1,490,966 B | `gsm8k_20260811_170447.jsonl`, `gsm8k_20260813_045034.jsonl` (**2 copies**) |
| `afca41b2` | 171,384 B | `gsm8k_20260812_050405.jsonl` (unique) |
| `a70b2d0f` | 69,072 B | `humaneval_20260810_064421.jsonl`, `humaneval_20260811_161123.jsonl`, `humaneval_20260813_035659.jsonl` (**3 copies**) |
| `a1278690` | 1,229,091 B | `humaneval_20260811_170447.jsonl` (unique) |
| `eaa454b1` | 64,718 B | `humaneval_20260812_050405.jsonl` (unique) |
| `06f787cd` | 1,449,919 B | `humaneval_20260813_045034.jsonl` (unique) |

(Three more `gsm8k_2026081*_060*.jsonl` files are the git empty-blob SHA —
0 bytes, contribute nothing, harmless.)

So of 9 `gsm8k_*.jsonl` files, only 3 distinct non-empty contents exist,
spread across 6 filenames; of 6 `humaneval_*.jsonl` files, only 4 distinct
contents exist, spread across 6 filenames (`a70b2d0f` alone is committed 3
times).

`l1_training.py`'s `load_records()`:

```python
for path in sorted(glob.glob(f"{runs_dir}/*.jsonl")) + sorted(glob.glob(f"{runs_dir}/v2_n50/*.jsonl")):
    if "v1_pre_confidence" in path or "prior" in path or "v3_partial" in path:
        continue
    for line in open(path):
        ...
        recs.append(r)
```

None of these filenames contain `v1_pre_confidence`, `prior`, or
`v3_partial`, and there is no dedup by content hash or by
`(sample_id, block_idx, step_in_block)` — every file that glob-matches gets
its lines appended to `recs` independently. Concretely: every invocation
record from the `590dc20f`/`a70b2d0f` run is read into `recs` **3 times**,
every record from the `881be987` run **2 times**, while the `afca41b2` /
`a1278690` / `eaa454b1` / `06f787cd` runs are read once each. (There's also
no `s1/runs/v2_n50/` directory in this repo at all — the docstring's
"pooled v2 (N=50) + v3 (N=100)" framing doesn't match what's actually on
disk here; all the data lives flat in `s1/runs/`, undifferentiated by
version, which is presumably why the version-name exclusion filter never
fires.)

**Why this isn't caught by the grouped 80/20 split:** `GroupShuffleSplit`
groups by `sample_id`, so every copy of a given prompt's invocations lands
in the same fold — this does **not** cause train/test leakage. What it does
cause: the BCE loss (and the reported `n_train_invocations` /
`n_test_invocations` counts in `l1_weights.json`'s `meta`) implicitly
triples the gradient contribution of whichever prompts happen to be in the
`590dc20f`/`a70b2d0f` run and doubles the `881be987` run's, relative to
every other prompt in the pool. If those over-represented runs have
systematically different corrector-usefulness statistics than the rest of
the pool (e.g. different `broke_at_step_1` base rate — plausible if they're
from an earlier/later date with a different checkpoint or hyperparameter
history per the `s1/README.md` protocol notes), the trained MLP is
disproportionately fit to those prompts' quirks rather than the intended
uniform 200-prompt pool.

**Concrete failure scenario:** if `590dc20f`'s ~50-ish gsm8k prompts (guess
from file size relative to `afca41b2`'s) have an unusually high or low
`broke_at_step_1` rate compared to the rest of the pool — plausible sampling
noise on any subset this size — that subset's influence on the trained
decision boundary is 3x what a uniform-weighted 200-prompt pool would give
it, which is exactly the kind of hidden non-uniform weighting that would
make a reported held-out AUC (already flagged as optimistically biased by
selection in finding #4) diverge further from true generalization
performance — and this bias is baked into the actual `l1_weights.json`
currently deployed as `l1_mlp:0.40` in the live Phase B pilot, not just an
offline metrics artifact.

**Recommend:** before the next retrain (and ideally before trusting the
current `l1_weights.json`), dedup `s1/runs/*.jsonl` by content hash (or by
`(sample_id, block_idx, step_in_block)` composite key) in `load_records()`,
delete or `git rm` the duplicate-name files from the repo, and print the
count of duplicate lines dropped so silent re-duplication is visible in
future training runs. Given this directly affects the weights under live
test, flagging via PushNotification per the routine's rule for
pilot-invalidating-adjacent findings — this doesn't invalidate the pilot's
downstream-accuracy *methodology*, but it means the `l1_mlp:0.40` policy
being measured may not be the policy the design doc describes (uniform
200-prompt pool), and if the pilot's L1 result disappoints, this is a
confound to rule out before concluding the *feature set* is at fault.

### 7. MEDIUM — `gsm8k_answer_match`'s `\boxed{}` regex doesn't handle
nested braces, silently mis-scoring (or zero-scoring) any answer written as
a LaTeX fraction or other braced macro

```python
matches = list(re.finditer(r"\\boxed\{([^}]*)\}", text))
```

`[^}]*` stops at the **first** `}`, including one that belongs to a nested
group inside the boxed content. For a generation containing
`\boxed{\frac{1}{4}}`, the regex captures `\frac{1` (everything up to the
first `}`, which closes `\frac{1}`'s inner brace, not the outer `\boxed{}`).
After the existing `.replace(",", "").replace("$", "")` cleanup, `pred =
"\frac{1"`. `float(pred)` raises `ValueError`, falls through to the string-
equality fallback `pred == target`, which is false against a numeric gold
target like `"0.25"` — the row is scored wrong even when the model's answer
is correct, with no crash or warning.

**Concrete failure scenario:** any GSM8K generation whose final boxed
answer is written as `\boxed{\frac{a}{b}}` (a live-model formatting choice,
not a hypothetical) is scored incorrect regardless of whether the fraction
is right. Since this is a formatting-style effect rather than a
policy-dependent one, it's unlikely to bias the *relative* comparison
between policies (all policies share the same underlying model and prompt,
so fraction-formatting rate should be roughly constant across the
`fixed`/`cadllm_linear`/`l1_mlp` conditions) — but it does mean the raw
accuracy numbers in the table are a systematic undercount versus true solve
rate, and if fraction-formatting rate happens to correlate with corrector
invocation pattern (e.g. the corrector fixing more `\frac{}` formatting in
one policy than another), it's no longer policy-neutral.

**Recommend:** match balanced/nested braces (a small recursive or
depth-counting regex, or split on `\boxed{` and manually scan-match the
closing brace) instead of `[^}]*`, and re-run `gsm8k_answer_match` against
any already-collected `gen_text` rows to check how many contain
`\boxed{\frac` or similar nested patterns before trusting the current
accuracy table.

---

## 2026-08-23 — Track B audit (fire N+3, commit c83fb41 reviewed)

Status check on findings #1-#7 against current file contents (not commit
messages), then one new finding from re-reading `l1_policy.py` against how
`phase_b_pilot.py` and `llada/generate.py` actually call it.

**Re-verified status:**
- #1 (stale CLI defaults) — **fixed**. `phase_b_pilot.py` now defaults
  `--n_samples 100` and `--policies` to the exact locked-prereg list
  (`fixed`, `cadllm_linear:0.15/0.20/0.25`, `l1_mlp:0.40`), with a comment
  pointing at this finding.
- #2 (first-`\boxed{}`-match) — **fixed**. `gsm8k_answer_match` now takes
  `matches[-1]` with a docstring citing this finding.
- #3 (unenforced train/test index invariant) — **still open**, unchanged.
- #4 (checkpoint/early-stop selection bias on `final_test_auc`) — **still
  open**. `l1_training.py` is unchanged: same `Xte`/`yte_np` used for
  `best_auc` selection, `patience`-driven early stop, and the reported
  `final_test_auc`. No val/test split added.
- #5 (broad `except (AssertionError, Exception)` in `phase_b_evaluate.py`
  swallowing rescore failures silently) — **still open**, unchanged.
- #6 (byte-identical duplicate `s1/runs/*.jsonl` files, unfiltered glob
  loads each 2-3x, overweights those prompts in `l1_weights.json`'s
  training loss) — **still open**. Confirmed via `ls s1/runs/`: all the
  same duplicate-named files from finding #6 are still committed, and
  `load_records()` in `l1_training.py` still has no dedup by content hash
  or by `(sample_id, block_idx, step_in_block)`. This is the same
  `l1_weights.json` behind the live `l1_mlp:0.40` EC2 pilot arm — not
  re-paging since this was already flagged via PushNotification when
  found (fire N+2) and nothing about it has changed since, but noting it
  is still unresolved going into whatever pilot results land next.
- #7 (`\boxed{}` regex doesn't handle nested braces, e.g. `\frac{}`) —
  **still open**, unchanged regex (`r"\\boxed\{([^}]*)\}"`).

### 8. LOW/MEDIUM — `FixedPolicy` (in `l1_policy.py`) implements the wrong
interface for how `generate.py` actually calls a non-`None` `corrector_policy`
— currently harmless only because `phase_b_pilot.py` special-cases around it

`llada/generate.py`'s corrector-entry decision (lines 199-208) has exactly
two branches:

```python
if corrector_policy is None:
    invoke_corrector = (step + 1) % apply_corrector_every_n_steps == 0
    phase_b_features = None
else:
    phase_b_features = features_from_predictor_logits(...)
    invoke_corrector = corrector_policy.should_invoke(phase_b_features)
```

Any non-`None` `corrector_policy` object gets `.should_invoke(features_dict)`
called on it. But `l1_policy.py`'s `FixedPolicy` class does **not** define
`should_invoke` — it only defines `should_invoke_at_step(step_in_block)`,
a different name and signature (ignores features, takes a step index
instead). `load_policy("fixed")` (and `load_policy("fixed:N")`) both return
a `FixedPolicy` instance. If that instance were ever passed as
`corrector_policy=` to `generate()`, the very first predictor step would
raise `AttributeError: 'FixedPolicy' object has no attribute 'should_invoke'`.

**Why the pilot doesn't hit this today:** `phase_b_pilot.py`'s `run_one`
(line 156-158) special-cases it away —
`policy_obj = None; if policy_spec != "fixed": policy_obj = load_policy(...)`
— so the `fixed` arm always passes `corrector_policy=None` and takes the
first branch, never touching `FixedPolicy` at all. `FixedPolicy` is
currently dead code from the pilot's perspective: constructible via
`load_policy`, but never actually exercised through `generate()`, and would
crash immediately if it were.

**Secondary, non-crashing consequence of the current workaround:** because
the `fixed` arm takes the `corrector_policy is None` branch, it skips the
`features_from_predictor_logits` call entirely, while `cadllm_linear` and
`l1_mlp` both pay for it every predictor step. That's a small extra amount
of per-step tensor work (softmax + entropy over the active block region)
that only the two adaptive arms incur. Doesn't affect `total_nfe` /
`predictor_nfe` (no extra model forward passes, pure post-hoc tensor ops on
already-computed logits) so it shouldn't move the accuracy-vs-matched-NFE
comparison, but if wall-clock/throughput is ever reported per policy, the
`fixed` arm has a structural head start unrelated to its actual decision
rule.

**Recommend:** either give `FixedPolicy` a `should_invoke(features)` method
(ignoring `features`, delegating to an internally-tracked step counter) so
it's actually usable as a drop-in `corrector_policy` and the `run_one`
special-case can be removed (one code path for all three arms, matching
this audit brief's fair-comparison goal (c) more literally), or — if the
special-case in `run_one` is intentionally kept as the fast path for
`fixed` — delete/rename `should_invoke_at_step` and add a comment on
`FixedPolicy` noting it's not wired into `generate()`'s `corrector_policy`
protocol and would need `should_invoke` to be. Low urgency (nothing is
broken today, this doesn't touch the current pilot's data), but it's an
interface mismatch that would produce a loud crash — not a silent wrong
number — for the next person who assumes `load_policy("fixed")` is a
plug-compatible `corrector_policy` for `generate()`.

---

## 2026-08-24 - Track B audit (fire N+4, commit 467f7b6 reviewed)

No code changed since fire N+3 (`git diff cfa0905 HEAD -- l1_policy.py
l1_training.py phase_b_pilot.py phase_b_evaluate.py llada/generate.py
PHASE_B_PREREG_2026-08-22.md` is empty - only `L1_LITERATURE.md`,
`L1_FEATURE_IDEAS.md`, and `MEMO_V4_SKELETON.md` changed in between, from
Track C/D/A fires). Findings #1-#2 fixed, #3-#8 still open and unchanged -
re-confirmed by re-reading current file contents, not just diffing.

Read `phase_b_evaluate.py`'s NFE-matching and paired-bootstrap logic in full
for the first time this pass (prior fires focused on `l1_training.py` /
`l1_policy.py` / `s1/runs/`). The "pick the CadLLM threshold whose observed
mean NFE lands closest to L1's" selection (`phase_b_evaluate.py` lines
105-108) looked at first glance like data-dependent cherry-picking of the
comparator, but `PHASE_B_PREREG_2026-08-22.md` line 54 explicitly
pre-registers exactly this procedure ("uses whichever bracket point lands
closest in mean NFE, decided by the observed NFEs, not by which one L1
beats") - not a bug, already locked pre-hoc. `paired_bootstrap`'s cluster
resampling (same resampled id list applied to both A and B per iteration)
is the correct paired-bootstrap construction. No issues found in either.

### 9. MEDIUM - `humaneval_pass` extracts the FIRST fenced python code block
via `re.search`, the same first-match failure mode already fixed for
GSM8K's `\boxed{}` parsing (finding #2) but never applied to the HumanEval
side

```python
code_match = re.search(r"```python\s*\n(.*?)```", text, re.DOTALL)
body = code_match.group(1) if code_match else text
```

Finding #2 (fixed in the commit before `c83fb41`) established the exact
principle this violates: a generation that produces more than one candidate
answer in the same text - an early wrong attempt, a "wait, let me
reconsider" retry, or (specific to this pilot) a diffusion-model corrector
editing tokens in a way that leaves stray or duplicated fenced blocks in the
decoded output - gets silently scored against whichever occurrence the
regex happens to grab, not necessarily the model's final one.
`gsm8k_answer_match` was switched to `matches[-1]` for exactly this reason;
`humaneval_pass` still takes `re.search`'s first match, three fires later.

**Why this one is a bigger fairness concern than #7 (the gsm8k `\frac{}`
nested-brace bug):** finding #7 was argued to be policy-neutral because
fraction-formatting rate should be roughly constant across `fixed` /
`cadllm_linear` / `l1_mlp` (same model, same prompt). That argument does
**not** transfer here. The whole premise of Phase B is that the three
policies invoke the corrector at different rates and at different decision
points, and the corrector's job is specifically to clean up degenerate/
low-confidence token regions. If heavier corrector invocation (e.g.
`cadllm_linear:0.15`, which brackets from above with more invocations, or
`l1_mlp:0.40` if it invokes more on messy generations) systematically
produces fewer stray/duplicate code fences than a lighter policy, first-
match code-fence extraction would score policies asymmetrically for a
reason unrelated to whether the *actual solution* is correct - directly
undermining audit-brief goal (c), fair comparison across policies sharing
every code path except `should_invoke`.

**Concrete failure scenario:** a generation containing two fenced python
blocks - e.g. the model emits a first attempt, the corrector's edits shift
enough tokens around a block boundary that decoding produces a leftover
fragment of the pre-edit block before the final one - gets scored against
the first (possibly stale/wrong) block regardless of whether the second one
passes HumanEval's tests. No crash, no warning, just a wrong `correct` value
that `phase_b_evaluate.py`'s accuracy table takes at face value.

**Not yet confirmed against real data** - no Phase B v2 `pilot.jsonl` has
landed yet (only stale `s1/runs/` files predate this design), so this is a
plausible mechanism from reading the code, not something observed in
output. Not paging on it for that reason: unlike finding #6 (confirmed via
actual committed blob SHAs), this needs `gen_text` from a real run to check
the multi-fence rate before treating it as confirmed rather than
theoretical.

**Recommend:** switch to last-match (or, more robustly, prefer a fenced
block that contains a `def {entry_point}` matching `gold["entry_point"]`)
for consistency with the fix already applied to `gsm8k_answer_match`;
before trusting the HumanEval accuracy column in any `phase_b/pilot.jsonl`
output, grep `gen_text` for rows with more than one fenced-python-block
occurrence and check whether that rate differs by policy - if it's ~0
across all rows this finding is moot in practice, if it's nonzero and
policy-skewed the HumanEval comparison needs a rescore with a fixed
extractor before the memo cites it.

---

## 2026-08-24 — Track B audit (fire N+5, commit 194bb4f reviewed)

No code changed since fire N+4 (`git diff 47404b5 HEAD -- l1_policy.py
l1_training.py phase_b_pilot.py phase_b_evaluate.py llada/generate.py
PHASE_B_PREREG_2026-08-22.md` is empty — only `L1_FEATURE_IDEAS.md` and
`MEMO_V4_SKELETON.md` changed, from Track C/D/A fires). No `phase_b/pilot.jsonl`
or `v2.jsonl` has landed yet (`s1/runs/` still holds only the same
pre-Phase-B files from prior fires). Findings #1–#2 fixed, #3–#9 still open
and unchanged, re-confirmed by re-reading current file contents.

Re-read `llada/generate.py`'s corrector fixed-point loop end-to-end for the
first time looking specifically at the convergence check itself (prior
fires focused on the feature-extraction and policy-dispatch code around
it), and found a new issue in the mechanism that produces the `y` label
`l1_training.py` trains against.

### 10. MEDIUM/HIGH — `torch.allclose` on integer token-id tensors silently
treats some genuinely-different corrector outputs as "converged", corrupting
the `broke_at_step_1` label that `l1_training.py` uses as ground truth

`llada/generate.py` lines 281–284, inside the corrector's fixed-point loop:

```python
if torch.allclose(
    corrector_x[:, active_region_start:block_end],
    corrected_tokens,
):
    if corrector_step == 1:
        s1_broke_at_step_1 = True
    break
```

Both tensors are `torch.long` **token ids**, not continuous values —
`corrector_x`/`corrected_tokens` come from `torch.argmax(corrector_logits, ...)`
(line 279). `torch.allclose`'s default tolerance is
`atol=1e-8, rtol=1e-5`, applied per PyTorch's documented formula
`|input - other| <= atol + rtol * |other|`. That formula is evaluated
generically for integer dtypes too — it isn't gated on floating point. Two
*different* token ids `a`, `b` with `|a - b| == 1` are judged "close"
whenever `b >= ~100000` (`1 <= 1e-8 + 1e-5 * b` solves to `b >= 99999.999`,
so `b == 100000` already clears it). `mask_id=126336` (`llada/generate.py`
line 69) — the tokenizer's id space extends at least that far, so roughly
the top ~20% of the vocabulary (ids ≥ 100000 out of ~126k) falls inside the
affected range.

**Concrete failure mode:** on corrector step 1, if the model's argmax
prediction genuinely flips to an adjacent-id token in that top ~20% of
vocab space (an off-by-one id, not necessarily a semantically similar
token — id adjacency is an artifact of vocab construction, not meaning),
`torch.allclose` reports "no change" even though `corrector_x` and
`corrected_tokens` disagree at that position. `s1_broke_at_step_1` gets set
`True` for a corrector invocation that actually *did* do something.

**Why this matters more than a cosmetic convergence-detection glitch:**
`l1_training.py` line 60 —
`y = np.array([0.0 if r.get("broke_at_step_1", False) else 1.0 ...])` —
uses this exact flag, inverted, as the binary training label for both the
L1 MLP and the Phase A linear baseline it's compared against. This is the
`y` that produced AUC=0.9589 and the currently-deployed `l1_weights.json`
under live test on EC2 right now. A false `broke_at_step_1=True` doesn't
just mislabel a training row — it mislabels it in the direction that make
the *policy's actual behavior* (the corrector doing useful work) look like
a no-op, i.e. it's a labeling bug that specifically corrupts the boundary
the classifier is trying to learn, for exactly the token-id range the
tokenizer happens to place `mask_id` and (per LLaDA's usual vocab layout)
much of the special/control-token region in.

**Not yet confirmed against real data** — same caveat as finding #9: no
`torch.` runtime available in this fire's sandbox to reproduce the
`allclose` call directly (verified against the documented formula instead,
not empirically), and none of the `s1/runs/*.jsonl` records log raw
predicted token ids (schema is `block_idx, step_in_block,
corrector_break_step, hit_max, broke_at_step_1, active_mask_size,
n_active_positions_changed_by_corrector, sample_id, benchmark,
config_omega, config_S_max` — no token-id field to check the hit rate
against). Can't currently estimate what fraction of `broke_at_step_1=True`
rows in the S1 v3 training set this actually flipped.

**Recommend:** replace the `torch.allclose(...)` convergence check with an
exact-match test appropriate for discrete ids —
`torch.equal(corrector_x[:, active_region_start:block_end], corrected_tokens)`
or `(corrector_x[:, active_region_start:block_end] == corrected_tokens).all()`
— either is a one-line fix with no behavior change for the (presumably
large majority of) cases where ids are below 100000. Before the next L1
retrain, it'd be worth a quick offline check: rerun the S1 v3 logging
pass's convergence check with the exact-match version against the same
generations (if logits/argmax are still reproducible from the checkpoint)
and diff how many `broke_at_step_1` labels flip. If the flip rate is
near-zero this finding is moot in practice; if it's non-trivial, `l1_weights.json`
was trained against a partially-corrupted label and the S1 v3 AUC numbers
in `PHASE_B_L1_DESIGN.md` should be treated as provisional until relabeled.
This is a training-data integrity issue for the *already-trained* MLP, not
a bug in the Phase B pilot script itself (the pilot only calls
`L1Policy.predict`/`should_invoke` at inference time — `broke_at_step_1` is
never computed during pilot runs) — flagging as MEDIUM/HIGH rather than
paging immediately, since it affects the model already under test rather
than corrupting the pilot's own accuracy/NFE measurements, and the actual
label-flip rate is unconfirmed. Worth prioritizing a re-check the next time
Lucas is looking at retraining L1 or auditing the S1 v3 pipeline.

---

## 2026-08-24 — Track B audit (fire N+6, commit f9e72d6 reviewed)

Track A egress re-check this fire: still `EGRESS_BLOCKED` on `arxiv.org`
(7/7 consecutive fires now, same error shape). No re-notify — already
flagged to Lucas at the 3/3 mark, nothing new to report. Routed to Track B
per the fallback rule (A and B tied oldest-touched at `e5c7254`; B wins the
tie since C and D were both refreshed more recently, at `faae54f` and
`f9e72d6`).

`git diff 194bb4f HEAD -- l1_policy.py l1_training.py phase_b_pilot.py
phase_b_evaluate.py llada/generate.py PHASE_B_PREREG_2026-08-22.md` is
empty — no code changed since fire N+5, only `L1_FEATURE_IDEAS.md` and
`MEMO_V4_SKELETON.md` (Track C/D). Findings #1–#2 fixed, #3–#10 still open
and unchanged. Still no `phase_b/pilot.jsonl` or `v2.jsonl` in the tree —
`s1/runs/` in this checkout holds only the same 15 pre-Phase-B files as
every prior fire (checked: `total`/`withconf` counts per file are
identical to fire N+2's tally, and none contain
`predictor_conf_mean_active` — confirming again that this repo checkout
never receives the confidence-logging data L1 actually trains on; that
lives only on the EC2 box at the CLI's default `--runs_dir`).

This fire looked at a part of `l1_training.py` no prior fire had examined:
the train/test split itself, given both benchmarks are pooled into one
`load_records()` call.

### 11. MEDIUM — `l1_training.py`'s train/test split is grouped by
`sample_id` but not stratified by benchmark, so the reported headline AUC
can be composed of an arbitrary and unreported GSM8K/HumanEval mix

```python
X, y, g = make_X_y_g(recs)
gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
train_idx, test_idx = next(gss.split(X, y, g))
...
auc = roc_auc_score(yte_np, probs)
```

`make_X_y_g` builds `g` from `r["sample_id"]` alone. Every record in
`s1/runs/*.jsonl` also carries a `benchmark` field (confirmed in the
checked-in reference files, e.g. `s1/runs/humaneval_20260810_064421.jsonl`
line 1: `"sample_id": "HumanEval/0", "benchmark": "humaneval", ...`), but
`load_records`/`make_X_y_g` never reads it — it isn't part of `X`, `y`, or
`g`, and never enters the split. `GroupShuffleSplit` guarantees no
`sample_id` (prompt) straddles the train/test boundary, which is the right
guard against the leakage findings #1/#3 already cover — but it has no
concept of benchmark as a second grouping axis, so with `random_state=42`
fixed there is exactly one realized split, and nothing in the code checks
or reports what fraction of the ~20% held-out *invocations* (not prompts)
come from GSM8K vs. HumanEval. `sklearn` has no single splitter that does
group-safety AND stratification simultaneously (`StratifiedGroupKFold`
exists but isn't used here; `GroupShuffleSplit` alone can't stratify).

**Why this matters beyond a cosmetic reporting gap:** `PHASE_B_L1_DESIGN.md`
line 7 reports Phase A's linear-baseline edge as benchmark-asymmetric
(`ΔAUC = +0.019 GSM8K / +0.033 HumanEval / +0.027 combined`) — HumanEval is
where L1's edge over the scalar-confidence baseline is largest. If the one
realized 80/20 split happens to under-represent HumanEval invocations in
the *test* fold (plausible: HumanEval blocks are code, tend to run longer
per prompt and have different invocation density than GSM8K's shorter CoT
blocks, so invocation-level record counts don't split 50/50 by prompt-level
group even under a "fair" random assignment), the reported
`final_test_auc = 0.9589` in `l1_weights.json`'s `meta` block is a *number
with no confidence interval and unknown per-benchmark composition* — it
could be flattering GSM8K's easier separability, or diluting HumanEval's
larger signal, or genuinely mixed representatively; there's no way to tell
from what's saved. This is the exact number PHASE_B_L1_DESIGN.md cites as
"matching the Phase A linear ceiling" and the exact number gating whether
L1 was worth deploying to the EC2 pilot at all.

**Recommend:** at minimum, log per-benchmark AUC alongside the pooled
number in `state["meta"]` (`final_test_auc_gsm8k`, `final_test_auc_humaneval`,
plus `n_test_invocations_gsm8k`/`_humaneval`) so a skewed split is visible
after the fact without needing to retrain. For a real fix, either (a)
split each benchmark's records independently with `GroupShuffleSplit`
(80/20 by `sample_id` within GSM8K, separately within HumanEval, then
concatenate the two train sets and the two test sets) so the test
composition is fixed by construction rather than left to chance, or (b) at
minimum try a few different `random_state` seeds for the current pooled
split and report the AUC range — if it's tight, the current single-split
number is fine as reported and this finding is moot in practice; if it
swings meaningfully, the headline number needs the split-independence fix
before the next retrain. Not flagging as HIGH: this doesn't invalidate the
Phase B pilot's own accuracy/NFE measurements (those come from
`phase_b_pilot.py` running the already-fixed `l1_weights.json` against
held-out *prompts*, a separate and correctly-leakage-guarded population per
finding #1/#3's `TRAIN_POOL_N` cutoff) — it's a question mark over how
trustworthy the training-time AUC number is as a *selection criterion*,
not a corruption of the deployed policy's live-tested behavior.

---

## 2026-08-24 — Track B audit (fire N+7, commit 3937917 reviewed)

Track A egress re-check this fire: still `EGRESS_BLOCKED` on `arxiv.org`
(8/8 consecutive fires now, same error shape — tested directly this fire
via a fresh fetch of `arxiv.org/list/cs.LG/recent`, not just inferred from
a stale flag). No re-notify — already flagged to Lucas at the 3/3 mark,
nothing new to report.

Routed to Track B per the fallback rule: of the four track files,
`L1_AUDIT_FINDINGS.md` (Track B) was last touched at fire N+6 (`f4aab3a`,
16:27:55Z), older than `L1_LITERATURE.md`/`L1_FEATURE_IDEAS.md` (both
`ec83a52`, 18:26:21Z) and `MEMO_V4_SKELETON.md` (`3937917`, 20:25:23Z) —
no tie this time, B is unambiguously oldest.

`git diff f9e72d6 HEAD -- l1_policy.py l1_training.py phase_b_pilot.py
phase_b_evaluate.py llada/generate.py PHASE_B_PREREG_2026-08-22.md
l1_weights.json` is empty — no code or weights changed since fire N+6's
review commit; the three intervening commits are Track A/C/D file-only
changes. Findings #1–#2 fixed, #3–#11 still open and unchanged. `s1/runs/`
still holds only the same 15 pre-Phase-B files as every prior fire (byte
sizes match fire N+6's tally exactly); no `phase_b/pilot.jsonl` or
`v2.jsonl` anywhere in the tree.

This fire cross-referenced the two places the five multi-conf features get
computed — `l1_policy.py`'s `features_from_predictor_logits` (used live,
at Phase B inference time, to make the corrector-entry decision) and the
inline block in `llada/generate.py`'s S1 logging path (used to produce the
training labels/features that `l1_training.py` fits on) — since no prior
fire had diffed the two against each other line-by-line.

### 12. LOW/MEDIUM — the S1 training-feature computation and the live L1
inference-feature computation are two independent implementations of the
same formula, not one shared function, with nothing enforcing they stay
identical

`llada/generate.py` imports and calls the real, shared
`features_from_predictor_logits` for exactly one purpose — the live Phase B
corrector-entry decision:

```python
# generate.py, lines 203-208 (Phase B inference path)
from l1_policy import features_from_predictor_logits
phase_b_features = features_from_predictor_logits(
    logits, active_mask, active_region_start, block_end,
)
invoke_corrector = corrector_policy.should_invoke(phase_b_features)
```

But the S1 logging path — the code that produces the *training* rows
`l1_training.py` reads via `predictor_conf_mean_active` etc. — does not
call that function. It re-derives the same five quantities inline, a
separate ~20 lines a few hundred lines away in the same file:

```python
# generate.py, lines 240-258 (S1 logging path, only runs when s1_log is not None)
with torch.no_grad():
    pl = logits[:, active_region_start:block_end].float()
    pp = torch.softmax(pl, dim=-1)
    top1 = pp.max(dim=-1).values.reshape(-1)
    ent = -(pp.clamp_min(1e-12).log() * pp).sum(dim=-1).reshape(-1)
    am = active_mask.reshape(-1).bool()
    if am.any():
        top1_a = top1[am]
        ent_a = ent[am]
        s1_predictor_conf = {
            "predictor_conf_mean_active": float(top1_a.mean()),
            "predictor_conf_min_active": float(top1_a.min()),
            "predictor_conf_max_active": float(top1_a.max()),
            "predictor_conf_std_active": float(top1_a.std()) if top1_a.numel() > 1 else 0.0,
            "predictor_entropy_mean_active": float(ent_a.mean()),
            "predictor_entropy_max_active": float(ent_a.max()),
            "predictor_conf_mean_block": float(top1.mean()),
            "predictor_entropy_mean_block": float(ent.mean()),
        }
    else:
        s1_predictor_conf = {}
```

Compared term-by-term against `features_from_predictor_logits` in
`l1_policy.py`: `pl`/`pp`/`top1`/`ent`/`am` are constructed identically
(same slice bounds, same softmax dim, same `1e-12` clamp epsilon, same
`.reshape(-1)`), and the five keys `l1_training.py` actually trains on
(`predictor_conf_mean_active`, `_min_active`, `_std_active`,
`predictor_entropy_mean_active`, `_max_active`) are computed with the same
reductions in both places. So as of this commit the two paths agree — this
is not a live numerical bug, and it does not change any Phase A or Phase B
number reported so far.

**Why it's still worth flagging:** there is no shared call, no shared
constant, and no test asserting the two stay in sync — just two hand-copies
of the same five-line formula, one of which (`l1_policy.py`'s) is already
sitting right there, importable, and in fact imported into this exact file
for the *other* code path three lines above. The natural edit — e.g.
fixing the `1e-12` clamp epsilon per an earlier numerical-stability
concern, switching `pp.clamp_min` to a different floor, adding a sixth
feature, or changing the `.float()` cast to something more precision-aware
for HumanEval's longer contexts — is far more likely to touch only one of
the two copies than both, since a contributor editing the live inference
path (`l1_policy.py`, the file `PHASE_B_L1_DESIGN.md` cites as "FROZEN")
has no obvious reason to also open `generate.py`'s S1 block, and vice
versa. If that happens, `l1_training.py` would keep training on one
formula while `phase_b_pilot.py` scores policies on a silently different
one — a train/inference skew that produces no error, no NaN, no crash, just
a policy whose live behavior no longer matches what its AUC was measured
against. This is the same failure shape as finding #6 (silent data
duplication) and finding #10 (silent mislabeling): nothing throws, the
pipeline runs and reports a clean number, and the corruption is invisible
without a line-by-line diff like this one.

**Recommend:** delete the inline S1 block's re-derivation and call
`features_from_predictor_logits(logits, active_mask, active_region_start,
block_end)` directly, keeping only the S1-specific extra keys
(`predictor_conf_max_active`, `predictor_conf_mean_block`,
`predictor_entropy_mean_block`) as an update on top of its returned dict.
One shared function, one place to fix a numerical-stability issue or add a
feature, and `l1_training.py`'s `FEATURE_KEYS` tuple (which is itself a
third hand-copy of the same five names, in a third file) stays trivially
in sync with whatever `l1_policy.py` actually returns. Low urgency —
today's formulas agree and no reported number is affected — but cheap to
fix now versus expensive to notice after a future retrain silently drifts.

---

## 2026-08-25 — Track B audit (fire N+8, commit 27c7e69 reviewed)

Track A egress re-check this fire: still `EGRESS_BLOCKED` on `arxiv.org`
(9/9+ consecutive, per `L1_LITERATURE.md`'s own log). No re-notify, not
this fire's track.

Routed to Track B per the fallback rule: `L1_AUDIT_FINDINGS.md` (this
file) was last touched at fire N+7 (`c271205`, 2026-08-24 22:26:52Z),
older than `L1_FEATURE_IDEAS.md` (`5fc6b3d`, 00:26:16Z) and
`L1_LITERATURE.md`/`MEMO_V4_SKELETON.md` (both `27c7e69`, 02:26:39Z).

`git diff c271205 HEAD -- l1_policy.py l1_training.py phase_b_pilot.py
phase_b_evaluate.py llada/generate.py PHASE_B_PREREG_2026-08-22.md
l1_weights.json` is empty — no code or weights changed since fire N+7;
the intervening commits are Track A/C/D file-only changes. Findings
#1–#2 fixed, #3–#12 still open and unchanged. `s1/runs/` still holds the
same 15 pre-Phase-B files as every prior fire; no `phase_b/pilot.jsonl` or
`v2.jsonl` anywhere in the tree — the EC2 pilot still hasn't landed data
into this checkout.

This fire read `s1/run_s1.py` in full for the first time (imported into
`phase_b_pilot.py` for `GSM8K_PROMPT`/`HUMANEVAL_PROMPT`/
`_patch_llada_for_bnb`, but never itself reviewed by a prior Track B
fire — confirmed via `grep -n "run_s1" L1_AUDIT_FINDINGS.md` returning
only one incidental mention). Two results, one confirmatory and one new.

**Confirmatory, strengthens finding #3:** `run_s1.py`'s `load_benchmark`
generates GSM8K training ids as `f"gsm8k_{i}"` for `i` in
`0..n_samples-1` over `ds.shuffle(seed=seed).select(range(n_samples))`.
`phase_b_pilot.py`'s `load_benchmark` generates held-out ids as
`f"gsm8k_{start+i}"` over `ds.shuffle(seed=seed).select(range(start,
start+n))` on a freshly-loaded, unfiltered `openai/gsm8k` test split.
Because `.select()` only slices the *already-shuffled* dataset and both
call sites shuffle with the same `seed=0` on the same unmodified split,
the id numbering is structurally guaranteed to line up — id `gsm8k_100`
in one script refers to the same shuffled-position-100 example in the
other, not just coincidentally. This closes part of finding #3's
uncertainty: the `TRAIN_POOL_N=100` cutoff isn't just "the numbers happen
to check out" (the meta-count argument finding #3 originally relied on)
but is backed by matching index-generation logic in both scripts. It does
**not** close finding #3 fully — nothing still stops a future retrain
from picking up `s1/runs/` files from a differently-configured collection
run (e.g. a run using a different `--checkpoint`/tokenizer where
`.shuffle(seed=0)` on the *same* dataset name could in principle still
diverge if the HF `datasets` cache or library version changed the shuffle
algorithm between collection and Phase B — unverified, not tested here).
Finding #3's original recommendation (assert the invariant explicitly
rather than rely on matching logic across two files) still stands.

### 13. MEDIUM — `phase_b_pilot.py`'s resume path has no defense against a
truncated trailing line, so a mid-write crash turns a resumable pilot run
into one that crashes on every restart

`phase_b_pilot.py` lines 250–255:

```python
done = set()
if out_path.exists():
    for line in open(out_path):
        r = json.loads(line)
        done.add((r["policy"], r["benchmark"], r["id"]))
    print(f"[phase_b] resuming, {len(done)} rows already done")
```

runs unconditionally on every launch when `--out` already exists — this is
the resume mechanism the whole script is built around (the module
docstring frames the run as potentially many hours on a single T4, and the
main loop's `if (policy_spec, bench, s["id"]) in done: continue` is the
only thing that makes re-launching after an interruption cheap instead of
starting over).

Each row is written by `run_one`'s caller as
`f.write(json.dumps(row) + "\n"); f.flush()` (lines 266–267). `gen_text`
is truncated to 4096 chars but the rest of the row (`id`, `benchmark`,
`policy`, NFE counts, `wall_s`, `gen_len`) pushes a single line to
several KB for HumanEval rows. `flush()` only moves Python's buffer into
the OS's page cache — it doesn't make the underlying `write()` atomic, and
a multi-KB line is not guaranteed to land in the file as a single
uninterruptible syscall. If the process is killed (T4 spot-instance
reclaim, OOM-killer on a long int8 run, `Ctrl-C`, CUDA driver reset)
while that `write()` is in flight, the file can end with a partial JSON
line — no trailing `\n`, or a truncated `{"id": "gsm8k_142", "benchm`.

On the next launch, the resume-scan above has no `try/except` around
`json.loads(line)`. A truncated trailing line raises
`json.JSONDecodeError` and crashes `main()` before a single new sample
runs — turning what should be "restart and pick up where it left off"
into "delete or hand-truncate the last line of a multi-hour run's output
file before it will resume at all." On an unattended EC2 box this is the
difference between an interruption costing a few minutes (re-launch,
resume) and costing the entire run (crash loop on relaunch, or all prior
progress discarded if the fix is `rm pilot.jsonl` under time pressure).

Distinct from findings #1–#12: this is a crash-recovery/availability gap,
not a silent-wrong-number bug — the failure mode is a loud crash on
restart, not a corrupted metric. Flagging MEDIUM (not HIGH) because nothing
today indicates it has actually fired — `phase_b/pilot.jsonl` isn't in
this checkout to inspect, and the EC2 pilot may simply not have been
interrupted yet — but the run is long-running exactly on the kind of
hardware (T4, likely spot or at least long-wall-clock) where a mid-write
kill is a real possibility, not a hypothetical.

**Recommend:** make the resume-scan tolerant of a truncated final line —
e.g. wrap the per-line `json.loads` in `try/except
json.JSONDecodeError`, and for the *last* line specifically, either skip
it silently (its row is incomplete, so re-running that one sample is
correct and cheap) or truncate the file to drop it before reopening in
append mode. A minimal version: catch the exception only on the last line
read; any decode error on a non-last line is a different, worse problem
(mid-file corruption) worth failing loudly on instead of silently
skipping.

---

## 2026-08-25 — Track B audit (fire N+9, commit 3a01a56 reviewed)

Re-verify: no code diff in `l1_policy.py`, `l1_training.py`, `phase_b_pilot.py`,
`llada/generate.py`, `phase_b_evaluate.py`, `s1/run_s1.py`, `classifier.py`, or
`l1_weights.json` since fire N+8 (`git diff --stat c65d8e1..HEAD` on those
paths is empty) — intervening commits are Track A/C/D file-only changes.
Findings #1–#13 unchanged. `s1/runs/` still holds the same 15 pre-Phase-B
files; still no `phase_b/pilot.jsonl` or `v2.jsonl` in this checkout.

This fire read `s1/analyze.py` in full for the first time (no prior Track B
fire mentions it — confirmed via `grep -n "analyze.py" L1_AUDIT_FINDINGS.md`
returning nothing before this entry). One new finding.

### 14. MEDIUM — `s1/analyze.py`'s go/no-go verdict (the check that produced
the committed "DIES on HumanEval" result the project appears to have
overridden without a documented rationale) uses unweighted, CI-free, hard
thresholds on top of wildly uneven per-block sample sizes

`s1/analyze.py` is the script whose docstring frames it as *the* Phase A
wedge test: "L1 LIVES if coefficient of variation (std/mean) across block
positions exceeds 0.30 for `frac_noop` OR `frac_active_changed`, AND at
least one block has frac_noop > 0.70 while another has < 0.30." `verdict()`
(lines 105–169) implements exactly that — `cv_ok` is an OR over two CVs,
`spread_condition` is `max(frac_noop) > 0.70 and min(frac_noop) < 0.30`,
and `lives = cv_ok and spread_condition`, computed per-benchmark by
grouping `s1/runs/*.jsonl` records by `(benchmark, block_idx)` with no
weighting for how many invocations back each block.

Running it against the actual committed data (`python3 s1/analyze.py
s1/runs/`) reproduces exactly what commit `aa12bdb`'s message says
("S1 full int8 verdict: L1 LIVES on GSM8K, DIES on HumanEval per strict
spec"):

```
[gsm8k]     CV(frac_noop)=0.397  CV(frac_active_chg)=0.739  spread=True   -> LIVES
[humaneval] CV(frac_noop)=0.784  CV(frac_active_chg)=0.493  spread=False  -> DIES
OVERALL: L1 LIVES on ['gsm8k'], DIES on ['humaneval'].
```

Two problems, both in the script itself, not just in how its output was
used downstream:

**(a) The HumanEval "DIES" turns on a threshold miss of 0.008.** HumanEval's
`max(frac_noop)` is 0.692 (block 1) against the hardcoded cutoff of 0.70 —
a difference of a little over 1%, with no CI, no permutation test, and no
sensitivity check on the 0.70/0.30/0.30 constants anywhere in the script or
in `PHASE_B_L1_DESIGN.md`. `cv_ok` is actually satisfied comfortably on
HumanEval either way (`CV(frac_noop)=0.784`, well past 0.30). The overall
verdict here is decided entirely by whether one block's `frac_noop` lands
on one side of an un-uncertainty-quantified line.

**(b) Blocks are weighted equally regardless of `n_invocations`, which
spans two orders of magnitude.** Printed per-block counts for HumanEval run
from `n_inv=1792` (block 0) down to `n_inv=32` (blocks 12–26, i.e. 15 of
the 27 blocks the CV/spread computation treats as equally informative).
`frac_noop=0.000` at n=32 (blocks 14/15/17/18/19) is a much noisier
estimate than `frac_noop=0.494` at n=1792 (block 0), but `cv()` and
`spread_condition` fold them into the same unweighted list. Whether the
"DIES" verdict would survive a per-block-count-weighted or n-thresholded
(e.g., blocks with `n_invocations < 100` excluded) re-analysis is untested
— this finding does not claim the verdict would flip, only that the script
as committed cannot currently tell you.

**Why this matters beyond a stale script:** `PHASE_B_L1_DESIGN.md`'s cited
Phase A rationale for running Phase B on *both* benchmarks is a different,
later analysis — pooled v2+v3 logistic-regression/MLP AUC, ΔAUC=+0.033 on
HumanEval, actually the larger of the two benchmark deltas (vs. +0.019
GSM8K) — which is consistent with "L1 has signal on HumanEval," the
opposite emphasis from `analyze.py`'s per-block spread verdict. Nothing in
`PHASE_B_L1_DESIGN.md`, `PHASE_B_PREREG_2026-08-22.md`, `MEMO_V4_SKELETON.md`,
or this findings file documents that the AUC-based analysis supersedes the
`analyze.py` CV/spread check, or explains why a script committed with a
"DIES on HumanEval" verdict message didn't stop HumanEval from being one of
the two benchmarks the live Phase B pilot (currently running on EC2, per
the design doc's Day 3-7 timeline) is spending T4-hours evaluating. Both
things can be true — the AUC analysis may be the more rigorous, superseding
check — but that reconciliation isn't written down anywhere a reviewer
(Yair, or Cornell) would find it, and finding #4 already flags that the
`final_test_auc` number itself has an unresolved question about its
computation. This is a documentation/rigor gap, not (currently) evidence
that Phase B's measured accuracy numbers themselves are wrong.

**Recommend:** either (1) add one paragraph to `PHASE_B_L1_DESIGN.md` or
the memo's related-work/methodology section explicitly stating that the
`analyze.py` per-block spread check was an earlier/coarser heuristic
superseded by the AUC-based analysis, with a one-line reason why the two
disagree on HumanEval, or (2) if that reconciliation was never actually
made, treat this as open: re-run `analyze.py` with per-block sample-size
weighting (e.g. inverse-variance or a minimum-n cutoff per block) and a
bootstrap CI on the spread/CV statistics before citing its "LIVES/DIES"
determination in anything reviewer-facing.

Not paired with a PushNotification: this is a gap in documented rationale
for a decision already made and already in motion (Phase B is mid-pilot on
both benchmarks), not a bug that changes any number the pilot is currently
computing. Flagging here so it's in the trail if Yair or Cornell asks "why
both benchmarks" and the answer isn't otherwise written down.

---

## 2026-08-25 — Track B audit (fire N+10, commit 4b5abe1 reviewed)

No code changed since fire N+9 (`git log c65d8e1..HEAD -- l1_policy.py
l1_training.py phase_b_pilot.py phase_b_evaluate.py llada/generate.py
PHASE_B_PREREG_2026-08-22.md` is empty — only `L1_LITERATURE.md`,
`L1_FEATURE_IDEAS.md`, and `MEMO_V4_SKELETON.md` changed in between, from
Track C/D/A fires). Findings #1–#2 fixed, #3–#14 still open and
unchanged, re-confirmed by re-reading current file contents, not just
diffing. Still no `phase_b/pilot.jsonl` on the repo side (Lucas runs
Phase B directly on EC2; nothing to rescore yet).

Re-read three areas not previously called out as reviewed in their own
right, looking specifically for (d) matched-FLOPs/NFE accounting bugs and
fresh instances of (c) fair-comparison gaps:

- `get_num_transfer_tokens` (`llada/generate.py` lines 41-57): integer
  division of the per-block mask count across steps, remainder
  distributed to the first `rem` steps. Same for every policy (called
  once per block before the corrector-decision loop, independent of
  `corrector_policy`) — no fairness or accounting issue.
- `l1_policy.load_policy` dispatch (`l1_policy.py` lines 138-183): the
  `l1_mlp:PATH:THRESH` parsing heuristic (`is_thresh` — last colon-chunk
  treated as a threshold if it parses as a float in [0,1]) would
  misparse a weights path whose filename looks like a bare float in that
  range (e.g. `l1_mlp:/tmp/0.5:0.40` still works, but a path *ending* in
  something like `.../l1_weights_0.4.json` split on the last `:` doesn't
  hit this because there's no `:` inside the path itself — the ambiguity
  requires an actual colon in the filename, which none of the current
  weights paths have). Not filing as a finding: no realistic path in
  this repo triggers it, and it's a parsing footgun rather than a result-
  affecting bug.
- `phase_b_pilot.py` `main()` wiring (full re-read, not just the CLI-
  defaults slice finding #1 already covers): `temperature=0.0` and
  `remasking="low_confidence"` are hardcoded identically for every
  policy/benchmark in `run_one` (line 167-168) — confirmed shared, not a
  fairness gap. Resume-dedup key is `(policy_spec, bench, s["id"])`
  (line 254/263) — matches the row's own written keys exactly, so
  finding #13's crash risk aside, the dedup logic itself is sound.

No new finding this pass. 9 fires deep into a 14-finding list on
unchanged code — diminishing returns are expected; flagging explicitly
that this was a genuine fresh read of previously-under-covered code
paths, not a rubber-stamp re-verify.

---

## 2026-08-25 — Track B audit (fire N+11, commit cf9838a reviewed)

No code changed since fire N+10 (`git diff f78959d..HEAD -- l1_policy.py
l1_training.py phase_b_pilot.py phase_b_evaluate.py llada/generate.py
PHASE_B_PREREG_2026-08-22.md` is empty — only `L1_FEATURE_IDEAS.md` and
`MEMO_V4_SKELETON.md` changed in between, from Track C/D fires).
Findings #1-#2 fixed, #3-#14 still open and unchanged, re-confirmed by
re-reading current file contents.

This pass targeted state drift rather than new code paths — checked
whether anything the audit depends on had silently changed underneath
it, since 10 straight fires of re-reading unchanged source is unlikely
to find new logic bugs:

- `l1_weights.json` last touched at commit `185e2ca` (2026-08-19,
  original Phase B push) — unchanged since. Still the exact weights
  finding #6's overweighted-duplicate training data produced; still the
  weights the live EC2 pilot's `l1_mlp:0.40` arm loads.
- No `phase_b/pilot.jsonl`, `v2.jsonl`, or any `*pilot*.jsonl`/`*v2*.jsonl`
  anywhere in this checkout — repo-side confirmation Phase B output
  still hasn't landed (Lucas runs EC2 directly, no visibility here).
- `s1/runs/` — recount came up 16 vs. fire N+9's "15 files" note; not
  drift, just an inconsistent prior count (14 dated `.jsonl` run files +
  `s1_verdict.png`, and this pass additionally counted the empty
  `.gitkeep` = 16; fire N+9 apparently didn't count one of
  `.gitkeep`/`s1_verdict.png`). `git log -- s1/runs/` confirms the
  directory's last real commit is still `aa12bdb` (the S1 verdict run) —
  no new files, just a counting inconsistency between fires. Noting so a
  future fire doesn't chase this as a phantom new-file finding.

No new finding this pass. Also cross-checked `PHASE_B_PREREG_2026-08-22.md`
against `phase_b_pilot.py`'s current `BENCH_CFG`/CLI defaults line by line
(sample sizes, policy list + thresholds, steps/gen_length/block_length,
per-benchmark `max_corrector_steps_per_loop`) — all match the locked
prereg exactly. `apply_corrector_every_n_steps=2` (not mentioned in the
prereg) only gates the `fixed` arm's cadence per finding #8; already
covered there as a wall-clock-only, non-NFE fairness note, not a prereg
violation.

---

## 2026-08-26 — Track B: independent cross-repo corroboration of finding #14, new downstream fact (pitch draft flagged stale)

Routine routing pointed at Track C (oldest-touched of A/B/C/D) this fire,
but a fresh check of the sibling routine's repo (`lhendre/remasking_test`,
`research-ideation` branch) turned up state worth folding back here instead
— HEAD had advanced to `4c64fa4` (2026-08-26 13:48 UTC) via `IDEAS.md`/
`IDEATION_LOG.md` changes that don't touch `LANDSCAPE.md`, which is why at
least three prior fires (14:26/16:27/18:24 UTC) missed it: their staleness
check only compared `LANDSCAPE.md`'s own last-commit timestamp, not full
sibling-repo HEAD.

That commit is the sibling routine's own Mode B pass independently
re-deriving finding #14's core contradiction (pooled AUC ΔAUC=+0.033 on
HumanEval vs. `analyze.py`'s per-block "DIES on HumanEval" verdict) after
reading this file — not new information about the codebase itself, so this
is corroboration, not a new bug. What *is* new: that fire explicitly flags
`pitches/PITCH_L1_2026-08-22.md` (a drafted-but-apparently-unsent update to
Yair Schiff) as **stale and should not be sent as currently worded**,
because its central framing — "HumanEval: same audit came back flat, no
meaningful per-block variance" — states the `analyze.py` verdict as settled
fact with no mention of the contradicting AUC analysis. Checked the pitch
file directly: confirmed, lines 9-13 commit to the flat-HumanEval framing
without caveat. It also folds in this file's finding #4 (checkpoint-
selection bias on `AUC=0.9589`) as a second caveat the pitch is missing.

Same disposition as finding #14 itself: **not paired with a
PushNotification.** Nothing here changes a number the live EC2 pilot is
computing, the pitch is (per its own text) already gated on Lucas's
sign-off before sending, and this is the same unreconciled-methodology gap
already on file, now with one concrete downstream consequence (don't send
that draft yet) rather than a new defect. Recording it here so the next
Track D pass folds "pitch draft stale, needs the HumanEval-contradiction +
finding #4 caveats before it goes to Yair" into `MEMO_V4_SKELETON.md`'s
caveat list, since the memo is the more likely actual deliverable and
should not inherit the same unreconciled framing.

## 2026-09-03 — Track B audit (fire N+13, commit b0b1b8d still current)

Routed here because `L1_AUDIT_FINDINGS.md` was the oldest-touched of the
four track files (last substantive entry 2026-08-26T20:26:44Z, ~7 days
stale vs. Track A/C/D all touched within the last day). Fresh independent
re-read from a clean clone, not trusting prior fires' hash claims.

**Confirmed unchanged:** `l1_policy.py`, `l1_training.py`, `l1_weights.json`,
`llada/generate.py`, `PHASE_B_L1_DESIGN.md` all still at 185e2ca
(2026-08-19); `phase_b_pilot.py` / `phase_b_evaluate.py` /
`PHASE_B_PREREG_2026-08-22.md` still at b0b1b8d (2026-08-23). No code has
moved since fire N+11/N+12 — findings #1-14 all still apply as written.

**What this pass actually did** (not a rubber-stamp): re-read
`phase_b_pilot.py` end to end and `l1_policy.py` end to end in full, then
cross-checked two specific angles the audit brief calls out that hadn't had
a dedicated pass recently:

- **Reproducibility / unseeded state**: `l1_training.py`'s
  `GroupShuffleSplit` is `random_state=42` and `torch.manual_seed(args.seed)`
  is called; `phase_b_pilot.py`'s `load_benchmark` uses `ds.shuffle(seed=seed)`
  with the CLI's `--seed` (default 0) consistently for both gsm8k and the
  held-out offset. No unseeded shuffle or order-dependent state found in
  either file.
- **Fair-comparison code paths (goal (c))**: re-derived the
  `corrector_policy is None` vs. not-`None` branch in `generate.py` (lines
  199-208) that produces the "fixed" arm's structural head-start already
  on file as finding #8 — independently arrived at the same conclusion
  (the `fixed` arm skips `features_from_predictor_logits` because
  `phase_b_pilot.py.run_one` special-cases `policy_spec == "fixed"` to
  `corrector_policy=None`, so it never touches `FixedPolicy`, whose
  `should_invoke_at_step` wouldn't satisfy `generate.py`'s
  `.should_invoke(features)` call anyway). This is finding #8's territory
  exactly, including the wall-clock-not-NFE caveat; no new angle survived
  scrutiny beyond what's already written up there.
- **Matched-FLOPs accounting (goal (d))**: `total_nfe`/`predictor_nfe`/
  `corrector_nfe` increments (lines 185-186, 269-270) are untouched by
  which branch computes `phase_b_features`, since that computation is
  pure post-hoc tensor ops on already-computed logits with no `model()`
  call — confirms finding #8's claim that the head-start doesn't leak
  into the NFE-matching comparison. No new accounting bug found.

**No new finding.** All three angles converged on ground already covered
by findings #8/#11 or came back clean. Not manufacturing a new numbered
finding against unchanged code just to have output this pass — the prior
12 audit fires' "no new finding" verdicts stand independently re-verified.

`s1/runs/` re-listed directly: still tops out at
`gsm8k_20260813_045034.jsonl`/`humaneval_20260813_045034.jsonl`
(2026-08-13), no `phase_b/` dir anywhere — pilot data still hasn't landed,
~21 days after the newest S1 run and ~15 days after Phase B code was
described as pushed. `remasking_test:research-ideation` HEAD unchanged at
76c7948 (2026-09-02). Live `WebFetch` to `arxiv.org/list/cs.LG/recent`
independently re-confirmed `EGRESS_BLOCKED`, unchanged since before the
08-29 02:2x escalation.

No PushNotification this fire — both structural blockers (EC2 pilot
stalled, egress proxy blocking arxiv/semanticscholar) are unchanged from
the single escalation already sent on 2026-08-29, now ~124h/5.2d ago; no
new finding, no state change. Next Track B pass: same order (unseeded
state → fair-comparison paths → NFE accounting) if code is still
unchanged; if `phase_b_pilot.py`/`l1_policy.py`/`generate.py` hashes move,
prioritize re-reading the diff over the fixed checklist above.

## 2026-09-03 — Track B audit (fire N+14, commit b0b1b8d still current)

Routed here as the oldest-touched of the four track files (last substantive
entry 04:26 UTC today, fire N+13). Confirmed unchanged: `l1_policy.py`,
`l1_training.py`, `l1_weights.json`, `llada/generate.py`,
`PHASE_B_L1_DESIGN.md` still at `185e2ca` (2026-08-19); `phase_b_pilot.py`,
`phase_b_evaluate.py`, `PHASE_B_PREREG_2026-08-22.md` still at `b0b1b8d`
(2026-08-23). Findings #1-14 all still apply as written.

**What this pass did differently from N+13:** rather than re-diffing code
against itself, read `l1_weights.json`'s actual numeric content (not just
its hash) and cross-checked feature-key *order* end to end across all three
independent copies of `FEATURE_KEYS` that finding #12 flagged as a drift
risk:

- `l1_weights.json.meta.features` (what the MLP was actually trained and
  reported AUC=0.9589 against):
  `[predictor_conf_mean_active, predictor_conf_min_active,
  predictor_conf_std_active, predictor_entropy_mean_active,
  predictor_entropy_max_active]`
- `l1_training.py`'s `FEATURE_KEYS` (line 24, builds the training `X`
  array via `[r.get(k) for k in FEATURE_KEYS]`): identical order.
- `l1_policy.py`'s `FEATURE_KEYS` (line 20, builds the live inference `x`
  vector via `[features[k] for k in FEATURE_KEYS]`, i.e. does *not* rely on
  dict iteration order): identical order.

All three agree today, so `W1`'s row order matches what both training and
live inference index into — no train/inference feature-order skew, which
would be a silent-corruption bug of exactly finding #12's shape (no crash,
no NaN, just a policy scoring against the wrong feature per row). This is
the same conclusion N+13 reached from the code-structure side; this pass
independently confirms it from the data side (the weights file itself)
rather than re-deriving it from reading `generate.py`'s two code paths
again. No new finding — this closes out finding #12's specific "did it
actually drift" question for the current weights file, though the
structural risk (three hand-copies, no shared constant, no test) that
finding #12 recommends fixing remains open and unchanged.

**No new finding.** `s1/runs/` re-listed directly: still 15 files, newest
`gsm8k_20260813_045034.jsonl`/`humaneval_20260813_045034.jsonl`
(2026-08-13) — pilot data still hasn't landed. Live `WebFetch` to
`arxiv.org/list/cs.LG/recent` re-confirmed `EGRESS_BLOCKED`. Both
structural blockers unchanged from the 08-29 escalation (now ~136h/5.7d)
and from today's 12:29 UTC duration re-flag; no new state since that
re-flag two hours ago, so no PushNotification this fire.

Next Track B pass: if code is still unchanged, consider actually running
`l1_training.py`'s training loop against a synthetic/held-out slice to
verify `final_test_auc=0.9589` is reproducible end-to-end rather than only
verifying static consistency (feature order, seeds) — that would be a
genuinely new angle not yet attempted in any of the 14 prior passes.

---

## 2026-09-04 — Track B audit (fire N+15, commit 7dc1bbb still current)

Routed here as oldest-touched of the four track files (`L1_AUDIT_FINDINGS.md`
last substantive entry 2026-09-03T14:26:48Z, vs. A/C/D all touched within the
prior ~10h). Confirmed unchanged via direct hash lookup, not trusting prior
fires' claims: `l1_policy.py`, `l1_training.py`, `l1_weights.json`,
`llada/generate.py`, `PHASE_B_L1_DESIGN.md` still all last-touched at
`185e2ca` (2026-08-19); `phase_b_pilot.py`, `phase_b_evaluate.py`,
`PHASE_B_PREREG_2026-08-22.md` still at `b0b1b8d` (2026-08-23). Findings
#1-14 all still apply as written; #1-#2 remain the only fixed ones.

**Acted on N+14's suggested next angle** (actually run `l1_training.py`'s
training loop to check `final_test_auc=0.9589` reproduces, rather than only
checking static consistency): this sandbox has no `torch` preinstalled.
`pip install scikit-learn` succeeded quickly; `pip install torch
--index-url https://download.pytorch.org/whl/cpu` failed outright — the
policy proxy returns `403 Forbidden` on the `download.pytorch.org` CONNECT
tunnel (a different host than the arxiv/semanticscholar block already on
file, so this is a separate, narrower egress gap, not the same one). Fell
back to plain `pip install torch` from `pypi.org` (which *is* reachable —
confirmed `pypi.org/simple/torch/` returns 200 and a `numpy` wheel installs
in under a second): this did start downloading but did not complete inside
a 150s budget and was killed, vs. this fire's ~20min total cap — CPU torch
wheels run several hundred MB, evidently too slow over whatever the actual
throughput is for a full download+install alongside everything else this
fire needs to do. Not retrying with a longer budget this fire since it would
eat the entire time cap on an install rather than the audit.

**But the bigger blocker, found before the install even mattered:** with
`scikit-learn` available, reimplemented `load_records`/`make_X_y_g` (minus
the `torch` bits) directly against this checkout's actual `s1/runs/*.jsonl`
files to at least check dataset-availability for the split/stratification
question (finding #11), independent of whether torch installs. Result:
**zero of the 16 files' rows contain a `predictor_conf_mean_active` key** —
`load_records`'s own `if "predictor_conf_mean_active" in r` filter admits
nothing, so `recs` is empty and `l1_training.py --runs_dir s1/runs` would
raise `RuntimeError: no records found` if invoked in this checkout right
now. This reconfirms fire N+6's finding via direct data inspection rather
than a field-name grep of one sample line: **this repo checkout structurally
cannot reproduce `final_test_auc=0.9589`, full stop, independent of which
Python packages are available.** The confidence-logged data
`l1_weights.json` was actually trained on has never been committed here —
it exists only on the EC2 box's `~/proseco/s1/runs`, per `l1_training.py`'s
own hardcoded default path (`/home/ec2-user/proseco/s1/runs`) which doesn't
match this checkout's `s1/runs` contents at all. So N+14's proposed
reproducibility check is not something any future automated fire can do
from a fresh git clone regardless of environment fixes — it would need to
run *on the EC2 box itself*, with Lucas's involvement, or with the raw
per-invocation logs pulled off EC2 into this repo first (which nothing
currently does — `s1/runs/` here has been static at the same 16
pre-Phase-B files since before this audit file existed).

**No new numbered finding** — this is a scoping result (what's checkable
from a clean clone vs. not) rather than a code defect, so not adding a
finding number for it. Recording it so no future fire re-attempts the same
torch-install detour without first checking `s1/runs/` for the required
field, and so it's on record that "verify 0.9589 reproduces" needs an EC2
step this routine cannot perform, not just a pip install.

Structural blockers unchanged: EC2 pilot still hasn't landed any
`phase_b/pilot.jsonl`/`v2.jsonl` in this tree (`s1/runs/` still the same 16
files, newest 2026-08-13); the 08-29 escalation is now ~150h/6.25d old with
the last duration re-flag at 09-03 12:29 UTC (~36h ago). No new finding, no
new state beyond the scoping result above — not urgent enough on its own to
re-flag via PushNotification (it narrows *how* the existing "no pilot data"
blocker could ever be resolved by this routine, it doesn't change whether
it's resolved), so no PushNotification this fire.

Next Track B pass: the training-loop-reproduction angle is closed out for
this environment (see above) — pick a different angle. Candidates not yet
tried: read `dataloader.py`/`classifier.py`/`main.py` (never reviewed by any
prior Track B fire, per a `grep -l` sweep this pass didn't have time to run
after the install detour) for anything touching the L1/Phase-B path, or
check whether `PHASE_B_PREREG_2026-08-22.md`'s bootstrap-CI methodology
(`phase_b_evaluate.py`'s `paired_bootstrap`, previously verified as
"correct paired-bootstrap construction" at fire N+4 but never checked for
CI *coverage* under a synthetic simulation) actually achieves nominal
coverage — that's checkable with `scikit-learn`/`numpy` alone, no torch
needed, and wasn't attempted this fire.

---

## 2026-09-04 — Track B audit (fire N+16, commit 63fd901 still current)

Routed here as oldest-touched of the four track files. Re-confirmed via
direct hash lookup that `l1_policy.py`, `l1_training.py`, `l1_weights.json`,
`llada/generate.py`, `PHASE_B_L1_DESIGN.md` are still at `185e2ca`
(2026-08-19), `phase_b_pilot.py`/`phase_b_evaluate.py`/
`PHASE_B_PREREG_2026-08-22.md` still at `b0b1b8d` (2026-08-23), and
`s1/runs/` is still the same 16 files (newest 2026-08-13) — pilot data
still hasn't landed, now ~6.25 days since the 08-29 escalation.

**Acted on N+15's suggested next angle: CI coverage of `paired_bootstrap`
under synthetic simulation.** `numpy` (not preinstalled, unlike the
`scikit-learn` fire N+15 got in) installed cleanly and fast from PyPI —
worth noting for future fires since N+15 hit a wall trying to get `torch`
the same way: plain `pip install numpy` is not blocked, only the
`download.pytorch.org` CONNECT tunnel is. Imported `paired_bootstrap`
directly from this checkout's `phase_b_evaluate.py` (no modification) and
drove it against synthetic paired Bernoulli data at the pilot's actual
pre-registered design point (N=40 prompts/benchmark) plus a few accuracy
levels, checking whether the reported 95% CI actually contains the true
accuracy delta ~95% of the time across 1,500 independent simulated
datasets per config (bootstrap resampling reuses the function's own fixed
`seed=42`, exactly as every real call site does — not varied, since that's
the actual deployed behavior being tested, not an artifact of my harness):

```
   n  acc_a  acc_b  true_d   cov95%  mean_width  mean_obs_d
  40   0.55   0.55   0.000   95.93%       0.424       0.002
  40   0.60   0.50   0.100   93.87%       0.422       0.100
  40   0.70   0.55   0.150   93.47%       0.407       0.151
  40   0.90   0.80   0.100   93.53%       0.300       0.098
```

**New finding (#15, minor, methodological): mild undercoverage of the
primary-comparison CI at the pilot's actual N=40 design point.** At the
true-null config (acc_a=acc_b=0.55) coverage is fine (95.93%, within noise
of nominal). But at every non-null config tried — which is the regime the
PASS/AMBIGUOUS call in `evaluate()` (`pass_primary = lo > 0`) actually
operates in, since the whole point is detecting a positive delta —
coverage runs ~93.5-93.9%, about 1.1-1.5 points below nominal 95%. With
1,500 sims the Monte-Carlo SE on a coverage estimate near 95% is ~0.56pp,
so the 93.47% and 93.53% rows sit roughly 2.6-2.7 SE below nominal — a
real, if small, effect, not sampling noise on my end. This is the known
finite-sample anti-conservatism of the plain percentile bootstrap for
paired binary/proportion data at small N (BCa or a paired permutation test
would likely close most of the gap), and it cuts in the direction that
matters for this design: **a `lo > 0` PASS call at N=40 is slightly more
likely to fire on noise than the nominal 5% one-sided rate implies** —
call it a true single-comparison false-PASS rate closer to ~6.3-6.5%
rather than 5% at the accuracy levels closest to the actual GSM8K/HumanEval
operating point (which is why the 0.70/0.55 and 0.90/0.80 rows, not just
the null row, are the load-bearing ones here).

**Scope and what would sharpen this further:** only 4 of 6 planned configs
finished inside this fire's time budget (n=80 and n=20 edge cases were cut
short, process killed cleanly, no corrupted output) — the n=40 result is
the one that matters since it matches the actual pre-registered design,
so not treating the missing rows as blocking. This is also a coverage
check on i.i.d. synthetic Bernoulli data, which doesn't capture whatever
correlation structure the two real policies' errors actually have on the
same prompts (correlated errors, which is the realistic case since both
policies see the same generation up to the corrector's decisions, usually
*improves* paired-bootstrap coverage relative to the independent case
tested here — so this simulation is if anything a pessimistic/conservative
stress test of coverage, not an optimistic one, which strengthens rather
than undercuts the finding).

**Not PushNotification-worthy on its own:** a ~1.5pp coverage shortfall at
the specific N=40/accuracy-delta regime tested doesn't invalidate Phase B
pilot results outright (the effect is small, and the true operating
characteristics of the real data could differ from this i.i.d. synthetic
model) — it's a caveat to log for whoever writes the memo, not a stop-ship
finding. Recommend `MEMO_V4_SKELETON.md`'s methodology paragraph note this
as a known small-sample caveat on the primary PASS criterion, and that a
future revision of `phase_b_evaluate.py` consider BCa or permutation-based
CIs if the pilot's actual observed delta ends up borderline (CI lower
bound close to zero) — precision matters most exactly there.

Next Track B pass: finish the n=80/n=20 coverage configs cut short here if
a fire has slack (not urgent — n=40 is the design point that matters); or
pick up N+15's other still-open candidate (`dataloader.py`/`classifier.py`/
`main.py`, never reviewed by any prior Track B fire).

## 2026-09-04 — Track B audit (fire N+17, commit 4df72c2 still current)

Routed here as oldest-touched of the four track files
(`L1_AUDIT_FINDINGS.md` last touched 08:29 UTC vs. Track A 10:25, Track D
12:29, Track C 14:26). Re-confirmed via direct hash lookup: `l1_policy.py`,
`l1_training.py`, `l1_weights.json`, `llada/generate.py`,
`PHASE_B_L1_DESIGN.md` still `185e2ca` (2026-08-19); `phase_b_pilot.py`/
`phase_b_evaluate.py`/`PHASE_B_PREREG_2026-08-22.md` still `b0b1b8d`
(2026-08-23) — no code diff since N+16, findings #1-15 unchanged.
`s1/runs/` still the same 16 files (newest 2026-08-13), no `phase_b/` dir
or `v2.jsonl`/`pilot*.jsonl` anywhere — pilot data still hasn't landed.

**First: checked N+16's "never-reviewed" lead before acting on it, and it
doesn't hold up.** N+16 suggested `dataloader.py`/`classifier.py`/`main.py`
as the next unreviewed files. Grepped every file actually on the Phase B
pilot's import path (`phase_b_pilot.py` → `llada.generate`, `l1_policy`,
`s1.run_s1`; `l1_policy.py`/`l1_training.py`/`phase_b_evaluate.py`
themselves) for references to `classifier`, `dataloader`, or a `main`
import: zero hits. None of those three files are reachable from the
pilot's actual code path — they're leftover S1-era scaffolding, not part
of what determines fair-comparison correctness or matched-FLOPs
accounting for Phase B. Auditing them wouldn't serve this track's
mandate ((c)/(d) above are about the `fixed`/`cadllm_linear`/`l1_mlp`
comparison, which never touches these three files), so declining that
lead rather than manufacturing findings in out-of-scope code.

**Instead, completed N+16's other still-open item: the n=80/n=20 coverage
configs cut short by that fire's time budget.** Same method (i.i.d.
synthetic paired Bernoulli, `paired_bootstrap` imported unmodified from
this checkout, `n_boot=500`, 1,500 sims/config, function's own fixed
`seed=42` at every call site as in real usage):

```
   n  acc_a  acc_b  true_d   cov95%  mean_width  mean_obs_d
  80   0.55   0.55   0.000   93.93%       0.302      -0.001
  80   0.60   0.50   0.100   93.07%       0.301       0.099
  80   0.70   0.55   0.150   92.87%       0.290       0.149
  80   0.90   0.80   0.100   94.80%       0.215       0.100
  20   0.55   0.55   0.000   95.13%       0.595      -0.001
  20   0.60   0.50   0.100   92.53%       0.589       0.102
  20   0.70   0.55   0.150   91.20%       0.570       0.149
  20   0.90   0.80   0.100   90.53%       0.414       0.099
```

**Extends finding #15 (still not a new numbered finding — same
mechanism, now characterized across N): the undercoverage is not specific
to N=40, and worsens as N shrinks.** n=80 sits ~92.9-94.8% (comparable to
n=40's 93.5-93.9%); n=20 is materially worse at the non-null, non-extreme
configs — 91.2-92.5% at the two middle rows, and 90.53% at
acc_a=0.90/acc_b=0.80, roughly 4.5pp below nominal and the single worst
reading across all three N values tested so far. With 1,500 sims the
Monte-Carlo SE near 90-95% coverage is ~0.6-0.8pp, so the n=20 rows are
multiple SE below nominal, not noise. Pattern is monotonic in N (worse at
n=20 than n=40 than n=80) and consistent with the known asymptotic
justification for percentile-bootstrap coverage on binary data —
undercoverage shrinks as N grows, exactly what's observed here.

**Practical relevance to the actual pilot design:** the pre-registered
primary comparison is N=40/benchmark, which N+16 already covered — this
fire's n=80/n=20 rows are context, not a new operating point the pilot
itself uses. But `MEMO_V4_SKELETON.md`'s per-policy-x-budget breakdown
tables imply the memo will eventually report accuracy deltas on
subgroups (e.g. per-budget slices) smaller than the full N=40, plausibly
down near n=20 — if so, this result says those subgroup CIs should be
read as more anti-conservative than the headline N=40 comparison, not
equally trustworthy. Flagging this explicitly for whoever fills in the
memo tables, since it's not obvious from finding #15 alone that the
effect gets worse rather than staying flat at smaller subgroup sizes.

**Not PushNotification-worthy:** this is a quantitative extension of an
already-logged, already-non-urgent finding, using the same synthetic
i.i.d. methodology (still a pessimistic/conservative stress test relative
to the real correlated-error case, per N+16's reasoning) — no new
qualitative risk to the pilot's headline N=40 PASS/AMBIGUOUS call.

No new state elsewhere: `remasking_test:research-ideation` HEAD confirmed
still `5265a8a` (2026-09-03 13:46 UTC) via `git ls-remote`; `arxiv.org`
still `EGRESS_BLOCKED` on a direct check. Standing 08-29 02:2x escalation
now ~158h/6.6d, last re-flagged 09-03 12:2x (~130h) — no PushNotification
this fire, nothing crosses the urgency bar.

Next Track B pass: `classifier.py`/`dataloader.py`/`main.py` are now
confirmed out of scope (see above) — drop that lead. Remaining unreviewed
ground within actual scope: `s1/analyze.py`'s finding #14 verdict logic
was flagged MEDIUM at N+9 but never re-verified against a live pilot
`v2.jsonl` (blocked until one lands); until then, further Track B value
is in either finishing methodological stress-tests of `phase_b_evaluate.py`
(e.g. a BCa or paired-permutation CI implemented as a comparison point,
not a replacement) or a fresh line-by-line diff of `llada/generate.py`'s
`corrector_policy` branch against upstream LLaDA `generate.py` if that
diff has never been done directly (check before assuming).

## 2026-09-05 — Track B audit (fire N+18, commit 2df635a still current)

Routed here as oldest-touched of the four track files
(`L1_AUDIT_FINDINGS.md` last touched 16:29 UTC 09-04 vs. Track A 18:25,
Track D 20:25, Track C 22:25). Re-confirmed via direct hash lookup:
`l1_policy.py`, `l1_training.py`, `l1_weights.json`, `llada/generate.py`,
`PHASE_B_L1_DESIGN.md` still `185e2ca` (2026-08-19); `phase_b_pilot.py`/
`phase_b_evaluate.py`/`PHASE_B_PREREG_2026-08-22.md` still `b0b1b8d`
(2026-08-23) — no code diff since N+17, findings #1-15 unchanged.
`s1/runs/` still the same 16 files (newest 2026-08-13), no `phase_b/` dir
or `v2.jsonl`/`pilot*.jsonl` anywhere — pilot data still hasn't landed.

**Picked up N+17's open lead: did the line-by-line diff of
`llada/generate.py`'s `corrector_policy` addition, but against the right
baseline.** N+17 suggested diffing against *upstream* LLaDA `generate.py`.
Tried that first — `raw.githubusercontent.com` was actually reachable
this fire (unlike `arxiv.org`, which is still `EGRESS_BLOCKED`; worth
noting for Track A: the block is host-specific, not blanket), and the
fetched upstream logic (Gumbel-noise proposal, float64 `low_confidence`
softmax gather, per-row top-k via `num_transfer_tokens`) matches this
repo's `get_transfer_index`/`get_num_transfer_tokens` structurally. But
upstream LLaDA has no corrector concept at all — the corrector loop is a
ProSeCo-original addition, so "diff the corrector_policy branch against
upstream" doesn't have a coherent target; any delta would just be
ProSeCo's pre-existing design, not something Phase B introduced. Redirected
to the diff that actually tests Phase B's own claim: this repo's docstring
(`llada/generate.py` lines 107-108) asserts "Everything else in this
function is byte-identical to the original ProSeCo generate()" — i.e. the
Phase B commit should touch *only* the `corrector_policy`/`phase_b_features`
machinery and nothing in the base predictor/corrector mechanics. That's a
checkable claim: `git diff 787b646 185e2ca -- llada/generate.py` (787b646 =
last commit before Phase B, s1 instrumentation only; 185e2ca = current).

**Result: the claim holds.** The full diff is additive-only: the new
`corrector_policy` parameter/docstring, the `if corrector_policy is
None: ... else: ...` branch replacing the old unconditional
`(step + 1) % apply_corrector_every_n_steps == 0` (which survives verbatim
inside the `None` branch), and s1-logging refactors (`s1_log.append({...})`
→ build `rec` dict, `update()` with predictor-confidence stats) that are
themselves pre-existing s1 v2 additions untouched by Phase B, not new in
this diff. No line in `get_transfer_index`, `get_num_transfer_tokens`, the
EOS-stopping check, or the NFE bookkeeping changed. This directly confirms
something findings #1-15 had assumed but never verified textually: the
`fixed` arm's generation is byte-for-byte the pre-Phase-B code path (modulo
the dead `phase_b_features = None` assignment, which has no runtime
effect), so `fixed` is a faithful, unregressed control — not, e.g.,
accidentally sharing a mutated NFE counter or a subtly different transfer-
index calculation with the adaptive arms. Not a new numbered finding (no
bug found) — closing out N+17's open lead with a documented negative
result so a future fire doesn't re-attempt the upstream-diff framing,
which is the wrong comparison to make.

**One thing this diff sharpens (not new — restates finding #8's mechanism
more precisely):** for the adaptive arms, `phase_b_features` is computed
unconditionally every predictor step (before `should_invoke` is even
called), while for `fixed` it's skipped entirely (`phase_b_features = None`
inline, never calling `features_from_predictor_logits`). This has no
accuracy or NFE effect (feature computation doesn't touch `x`, `logits`
used for generation, or any counter) but is worth noting explicitly for
whoever eventually profiles Phase B wall-clock: `cadllm_linear`/`l1_mlp`
pay one extra softmax+entropy pass over the active region on every step,
`fixed` does not, so a wall-clock-based cost comparison (as opposed to the
pre-registered NFE-based one) would be mildly unfair to the adaptive arms.
The pilot's own metric is NFE (`total_nfe`), not wall time, so this
doesn't affect the pre-registered comparison — flagging only in case
`phase_b_evaluate.py` or the memo ever reports `wall_s` (which `run_one`
does log) as a secondary metric.

No new state elsewhere: `remasking_test:research-ideation` HEAD checked
via `git ls-remote`, unchanged since 09-03 13:46 UTC. Standing 08-29 02:2x
escalation now ~171h/7.1d, last re-flagged 09-03 12:2x (~130h) — no
PushNotification this fire; this is a confirmatory/negative-result finding
on already-flagged territory (finding #8's mechanism), not a new risk to
the pilot's headline comparison.

Next Track B pass: with the upstream-diff and pre/post-Phase-B-diff leads
both closed, remaining in-scope ground is either (a) `s1/analyze.py`'s
finding #14 verdict logic, still blocked on a live `v2.jsonl`, or (b) an
actual BCa/paired-permutation CI implementation in `phase_b_evaluate.py`
as a comparison point against the existing percentile bootstrap (findings
#15 and its n=80/n=20 extension already show the *direction* of percentile
undercoverage; nobody has yet built the alternative CI to see how large
the practical difference is on this specific paired-accuracy-delta
statistic).

## 2026-09-05 — Track B audit (fire N+19)

Routed here as oldest-touched of the four track files (`L1_AUDIT_FINDINGS.md`
last touched 00:27 UTC 09-05 vs. Track A 02:26, Track D 04:26, Track C
06:25). Fresh independent re-check from a clean clone: `l1_policy.py`,
`l1_training.py`, `l1_weights.json`, `llada/generate.py`,
`PHASE_B_L1_DESIGN.md` still `185e2ca` (2026-08-19); `phase_b_pilot.py`/
`phase_b_evaluate.py`/`PHASE_B_PREREG_2026-08-22.md` still `b0b1b8d`
(2026-08-23) — no code diff since N+18, findings #1-15 unchanged. `s1/runs/`
still the same 16 files (newest 2026-08-13), no `phase_b/` dir or
`v2.jsonl`/`pilot*.jsonl` anywhere — pilot data still hasn't landed.

**Picked up N+18's second open lead: built the BCa bootstrap CI as an
actual comparison point against `phase_b_evaluate.py`'s existing percentile
`paired_bootstrap`, rather than just describing what one would show.**
Implementation (`bca_cmp.py`, not committed — throwaway analysis script,
not a repo change): imports `paired_bootstrap` unmodified from this
checkout for the percentile arm; the BCa arm reuses the identical
bootstrap resample draws' bias-correction (z0 from the fraction of
bootstrap deltas below the observed delta) and acceleration (jackknife
leave-one-prompt-out skewness of the delta statistic), then maps the
2.5/97.5 percentiles through the standard BCa-adjusted quantiles. Same
synthetic i.i.d. paired-Bernoulli generator as findings #15's family
(independent `correct` draws per prompt per arm at fixed accuracies), run
at **N=40 — the pilot's actual pre-registered per-benchmark design
point** (prior sims covered N=20/40/80 for the percentile method alone;
this is the first fire to run a second CI method head-to-head at the
real operating point), 1000 sims/config, `n_boot=500` matching production:

```
config        true_d  pctl_cov  pctl_w  bca_cov   bca_w
null           0.000    94.10%   0.424   93.60%   0.424
small          0.100    92.50%   0.422   93.40%   0.423
med            0.150    93.30%   0.408   94.00%   0.409
large_base     0.100    91.70%   0.299   92.00%   0.298
```

**Result: BCa and the existing percentile method are practically
indistinguishable at the pilot's actual N=40 design point.** Coverage for
both sits in the same 91.7-94.1% band (both mildly under nominal 95%
consistent with finding #15's known small-sample bootstrap behavior on
binary paired data), and mean CI width differs by at most 0.003 across
all four configs — noise at 1000 sims (Monte-Carlo SE on a coverage
proportion here is ~0.7-0.8pp, so neither method's coverage numbers are
distinguishable from the other's). This answers N+18's open question
("nobody has yet built the alternative CI to see how large the practical
difference is") with a concrete negative result: **switching
`phase_b_evaluate.py`'s primary CI from percentile to BCa would not
change the memo's PASS/AMBIGUOUS calls or materially tighten the
reported intervals** — the mild undercoverage documented in finding #15
is a small-N-binary-outcome property of the bootstrap generally, not an
artifact of the specific percentile construction, so it isn't fixed by
swapping construction methods. Not a new numbered finding (no bug, no
actionable delta) — closes N+18's second open lead.

**Practical upshot for whoever finalizes the memo:** no code change is
warranted in `phase_b_evaluate.py` on this basis. If the pre-registered
N=40 comparison's mild anti-conservatism (finding #15) is ever judged
worth correcting, a different fix (larger n_boot, a t-based correction,
or simply reporting the known small-sample caveat in prose) would be
needed — BCa specifically is not the fix, at least not at this sample
size and effect-size range.

No new state elsewhere: `remasking_test:research-ideation` HEAD
re-confirmed unchanged at `8c5420e` (2026-09-05, same as N+19's Track A
check) via fresh clone; `arxiv.org` re-probed directly this fire, still
`EGRESS_BLOCKED`. Standing 08-29 02:2x escalation now ~173h/7.2d, last
re-flagged 09-03 12:2x (~130h) — no PushNotification this fire; this is a
negative/practical-equivalence result on already-flagged territory
(finding #15's family), not a new risk to the pilot's headline
comparison.

Next Track B pass: with the upstream-diff, pre/post-Phase-B diff, and
BCa-vs-percentile leads all now closed, remaining in-scope ground is (a)
`s1/analyze.py`'s finding #14 verdict logic, still blocked on a live
`v2.jsonl`/pilot output, or (b) a paired-permutation test as a third
comparison point (tests H0: delta=0 rather than producing a CI directly,
so it's a different question than coverage — worth doing only if framed
as "does the permutation p-value's significance call ever disagree with
the bootstrap's `p_le_zero`", not another coverage sweep, since (a)/(b)
above already establish coverage doesn't move across construction
methods at this N).

## 2026-09-05 — Track B audit (fire N+20)

Routed here as oldest-touched of the four track files
(`L1_AUDIT_FINDINGS.md` last touched 08:27 UTC vs. Track A 10:25, Track D
12:27/12:33, Track C 14:26). Fresh independent re-check from a clean
clone: `l1_policy.py`, `l1_training.py`, `l1_weights.json`,
`llada/generate.py`, `PHASE_B_L1_DESIGN.md` still `185e2ca` (2026-08-19);
`phase_b_pilot.py`/`phase_b_evaluate.py`/`PHASE_B_PREREG_2026-08-22.md`
still `b0b1b8d` (2026-08-23) — no code diff since N+19, findings #1-15
unchanged. `s1/runs/` still the same 16 files (newest 2026-08-13), no
`phase_b/` dir or `v2.jsonl`/`pilot*.jsonl` anywhere — pilot data still
hasn't landed.

**Picked up N+19's open lead (b): built the paired-permutation test and
ran it head-to-head against `phase_b_evaluate.py`'s existing
`paired_bootstrap`, framed as a significance-call-agreement question, not
another coverage sweep (permutation p-values don't have "coverage").**
Implementation (`sim_permutation_vs_bootstrap.py`, not committed —
throwaway analysis script): a sign-flip permutation test on the paired
per-prompt outcome differences (exchange the sign of each nonzero
`correct_A - correct_B` under H0: no systematic effect, one-sided
p-value = `P(perm_delta >= observed | H0)`), directly comparable to
`paired_bootstrap`'s `p_le_zero` (`P(true delta <= 0)` under the
bootstrap). `paired_bootstrap` imported unmodified from this checkout —
same production code as findings #15/N+19's BCa comparison. Same
synthetic i.i.d. paired-Bernoulli generator, run at **N=40** (the pilot's
actual pre-registered design point), 1000 sims/config, `n_boot=500`
matching production, 2000 permutations/sim, significance threshold
alpha=0.025 for both methods (chosen to mirror a one-sided 97.5% call):

```
config                  p_base  delta | boot_sig_rate perm_sig_rate disagree_rate  both_sig boot_only perm_only
null_p50                  0.50   0.00 |         0.020         0.014         0.006        14         6         0
null_p70                  0.70   0.00 |         0.020         0.012         0.008        12         8         0
small_effect_p50          0.50   0.05 |         0.066         0.047         0.019        47        19         0
small_effect_p70          0.70   0.05 |         0.061         0.041         0.020        41        20         0
medium_effect_p50         0.50   0.10 |         0.136         0.086         0.050        86        50         0
medium_effect_p70         0.70   0.10 |         0.168         0.110         0.062       108        60         2

Overall disagreement rate across 6000 sims: 0.0275
```

**Result: yes, the two methods do disagree, and — new information not
visible from the coverage sims alone — the disagreement is almost
entirely one-directional.** Across all six configs (null and small/medium
true effects, at two base rates), `boot_only` (bootstrap calls
significant, permutation doesn't) outnumbers `perm_only` by 6-108 to 0-2:
the bootstrap's `p_le_zero < 0.025` fires roughly 1.4-1.6x as often as the
permutation test's one-sided p-value at matched alpha, and essentially
never the other way around (2/1000 in the single largest-effect config,
noise at that count). This sharpens finding #15 in a way the coverage
sims didn't: #15 established *that* the percentile bootstrap is mildly
anti-conservative on this statistic; this result establishes the
*direction* is consistent when checked against a genuinely different
inferential method (a permutation test has no bootstrap-resampling
machinery in common with `paired_bootstrap` at all), not an artifact of
how the coverage sims themselves were constructed. Practically: a policy
comparison that the memo would call "significant" off `p_le_zero < 0.025`
has roughly a 1-in-3 to 1-in-2 chance (`boot_only / boot_sig`, i.e.
19/66≈29% to 60/168≈36% across the effect sizes tested) of *not* clearing
the same bar under a permutation test at the identical alpha — worth
knowing if `phase_b_evaluate.py`'s printed `p_le_zero` is ever read as a
frequentist significance level rather than as what it actually is (a
bootstrap-based posterior-ish probability statement), since the two read
similarly in prose but aren't calibrated the same way at N=40.

**Not a new numbered finding** (no bug — `paired_bootstrap` behaves
exactly as its own docstring says; this is a characterization of a known,
already-flagged small-N bootstrap property, now cross-checked against an
independent method) — closes N+19's open lead (b) with a positive
(disagreement exists) but directionally-explained result, unlike N+19's
BCa comparison which closed its lead with a clean negative. **Not
PushNotification-worthy:** no pilot data exists yet for this to apply to,
the pre-registered primary analysis still uses `p_le_zero` exactly as
designed (this doesn't invalidate that choice, it just says don't
over-read `p_le_zero` as a classical p-value), and the underlying
mechanism (small-N binary-outcome bootstrap anti-conservatism) has been
on the books since finding #15.

No new state elsewhere: `remasking_test:research-ideation` HEAD advanced
since last check (`8c5420e` → `69d233d`, 2026-09-05) — read the new
commit directly: "Mode A — clean scan, no new papers, Phase B still
stalled", a non-actionable confirmation entry, nothing to fold into
`L1_LITERATURE.md` or the memo. `s1/runs/` and `phase_b/`/`v2.jsonl`
search re-confirmed empty via fresh `find`. Standing 08-29 02:2x
escalation now ~182h/7.6d, last re-flagged 09-03 12:2x (~130h then) — no
PushNotification this fire; this is a methodological characterization on
already-flagged territory (finding #15's family), not a new risk to the
pilot's headline comparison, and duration alone isn't a re-flag trigger
per the standing policy from the 09-03/09-04 fires.

Next Track B pass: with the upstream-diff, pre/post-Phase-B diff,
BCa-vs-percentile, and permutation-vs-bootstrap leads all now closed, the
only remaining in-scope Track B ground is `s1/analyze.py`'s finding #14
verdict logic, which stays blocked until a live `v2.jsonl`/pilot output
lands. If code/data are still unchanged next Track B fire, that fire
should say so plainly (independent re-verify) rather than manufacture a
fifth synthetic-data methodology exercise — the bootstrap-vs-alternatives
question has now been stress-tested from three independent angles (BCa,
n=20/40/80 sweep, permutation) with consistent conclusions, and a fourth
would be diminishing returns, not new signal.
