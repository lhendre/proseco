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

### Noted, not a bug: unsandboxed HumanEval execution

`humaneval_pass()` runs model-generated code via `subprocess.run(["python3",
"-c", full_code], timeout=10)` with no sandboxing beyond the timeout. This
is standard practice for HumanEval-style eval harnesses (pass@k inherently
requires executing generated code) and not something introduced by this
pilot, but flagging since it's running on the same EC2 box as everything
else — a generation that imports something destructive would run
unsandboxed. Not recommending a change given eval-harness convention, just
noting it's there.
