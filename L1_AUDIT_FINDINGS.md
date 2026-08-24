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
