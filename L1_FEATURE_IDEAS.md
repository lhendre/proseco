# L1 Feature Ideas

Track C (feature engineering proposals) log. Append-only, dated entries.
Proposals only — nothing here is implemented. Current L1 MLP AUC (0.9589)
matches the Phase A linear ceiling on the frozen 5-feature set
(`predictor_conf_{mean,min,std}_active`, `predictor_entropy_{mean,max}_active`);
these are candidates to push past that ceiling, not swap it out.

---

## 2026-08-23 — Track C, first entry

Scope read: `l1_policy.py`, `l1_training.py`, `PHASE_B_L1_DESIGN.md`,
`llada/generate.py` (corrector-invocation site, lines ~168-323).

### Context on feasibility

Two things matter for whether a proposed feature is cheap or expensive to
add later:

1. **What's already computed at the invocation site.** `features_from_predictor_logits`
   already has the full per-position top-1 probability tensor (`top1`, shape
   `(n_active,)`) and the full softmax distribution (`pp`) in scope before it
   collapses them to mean/min/std/entropy scalars. Anything derivable from
   `top1` or `pp` for the *current* invocation is a pure function of data
   already in hand — no new instrumentation, no re-running S1.
2. **What requires cross-invocation state.** `block_idx` and `active_mask_size`
   are already logged per-record (excluded from the frozen feature set per
   design-doc rationale, but present in the raw JSONL). A feature that needs
   the sequence of *prior* invocations for the same `sample_id` needs the
   feature-extraction step (not the live sampler) to do a running fold over
   records grouped by `sample_id`, sorted by `block_idx` — still no new S1
   run, just a different `load_records`/`make_X_y_g` pass.

None of the three below need new S1 instrumentation. All are computable from
existing v2+v3 JSONL columns plus a re-run of `l1_training.py` with an
extended `FEATURE_KEYS`.

### 1. Predictor confidence RANK within block (cheap, category: (2))

`predictor_conf_mean_active` and `_min_active` describe the *level* of
confidence but not its *shape* across positions in a way that's robust to
block-length variation. A block with 3 active positions and a block with 30
can have the same mean/min/std triple from very different underlying
distributions (e.g. one outlier vs. a uniformly low-confidence block).

Proposed feature: `predictor_conf_min_rank_frac_active` — the min-confidence
position's rank as a fraction of active positions if all active-position
confidences in a **window of recent blocks for this sample** were pooled and
ranked (not just this block). Motivation: the L1 label is corrector
disagreement, which Phase A characterizes as "does the corrector find
something worth fixing" — a position that's the least-confident *for this
sample's recent trajectory*, not just least-confident *in this block*,
should carry more signal than raw min_active, which is already saturated at
AUC~0.96 on its own.

Concrete failure mode this could catch: two blocks both have
`predictor_conf_min_active = 0.4`, but one comes from a sample where 0.4 is
the sample's typical worst-case (nothing unusual, corrector probably won't
fire usefully) and the other comes from a sample where 0.4 is anomalously
low relative to that sample's other blocks (corrector more likely to find
something real). Current features can't distinguish these; a rank-relative
feature can.

Cost: needs the cross-invocation fold described above (group by
`sample_id`, maintain a rolling window of raw `top1` per-position arrays —
which aren't currently persisted per-record, only the reduced mean/min/std
are. **This one actually does need new instrumentation** if we want the
true per-position array; a cheaper approximation using only
`predictor_conf_min_active` values already logged per prior block for the
same sample is available without new S1 runs and is the one to try first.

### 2. Predictor-corrector historical agreement rate, sample-so-far (cheap, category: (2))

`broke_at_step_1` (whether the corrector converged in one iteration) is
already logged per invocation. Proposed feature:
`agreement_rate_so_far` = fraction of this sample's *prior* corrector
invocations (by `block_idx` order) where `broke_at_step_1 == True`, i.e. the
corrector agreed with the predictor immediately. Cold-start value (no prior
invocations) = 1.0 (optimistic prior — matches `FixedPolicy`'s assumption
that the corrector agrees until shown otherwise).

Motivation: samples differ in how "easy" the whole generation is for the
corrector — a sample that's had 5/5 quick-agreement blocks so far likely has
an easy remainder (low base rate of real corrections needed everywhere),
independent of this block's own confidence stats. This is exactly the kind
of population-level signal a per-invocation confidence feature structurally
cannot see, since it only looks at one block in isolation.

Implementation note: must be computed causally (only using `block_idx' <
block_idx` records for the same `sample_id`) to avoid leaking future blocks'
outcomes into a training feature for an earlier block — same discipline as
the leakage bug already caught and fixed in `a796b4f`/`phase_b_pilot.py`'s
`TRAIN_POOL_N` logic. Trivial in `l1_training.py` (group + cumulative mean
over sorted `block_idx`), but the *live* `l1_policy.py` inline hook would
need to track a running per-sample counter across the sampler's block loop —
a small but real stateful addition to `generate.py`, not a one-line change.

### 3. Token-vocabulary entropy over active positions, aggregated (not per-position) (moderate, category: (1) + (2))

Current `predictor_entropy_mean_active` averages the *per-position* entropy
of each active position's own softmax distribution — a measure of
per-token uncertainty. A structurally different signal: entropy of the
**pooled/marginal distribution over the vocabulary**, i.e. treat all active
positions' softmax outputs as a mixture and ask how concentrated the
*combined* probability mass is on a small set of tokens vs. spread across
many. Concretely: `vocab_entropy_pooled_active` = entropy of
`pp[active_mask].mean(dim=0)` (average the softmax distributions across
active positions, then take entropy of that single distribution), as
opposed to `entropy_mean_active` = average of `entropy(pp[i])` over `i`.

These are mathematically different (Jensen's-inequality-different: entropy
of the average ≥ average of the entropies) and capture different things — a
block where every position is confidently split between the *same* two
tokens (e.g. an ambiguous plural/singular choice repeated across the block)
gets high per-position entropy either way, but a block where different
positions are each confidently split between *different* token pairs looks
similar under `entropy_mean_active` but has a much higher pooled-vocab
entropy. Motivation: this could catch "systematic ambiguity" (one
recurring token-choice problem across the block, possibly fixable in one
corrector pass) vs. "diffuse ambiguity" (many unrelated small uncertainties,
possibly not worth a corrector invocation) — a distinction the current
feature set cannot express since it always reduces to a scalar over the
per-position marginals.

Cost: pure function of `pp` already computed in
`features_from_predictor_logits` — cheapest of the three to add to the live
feature dict (no cross-invocation state). The only real cost is retraining
and re-validating on held-out data; given the 5-feature ceiling is already
matched, this is worth trying alone (not bundled with #1/#2) first, to
isolate whether it's this specific shape signal or the historical/rank
signals that move the needle, if either does.

### Priority if pursuing more than one

Try **#3** first (cheapest, no new instrumentation, orthogonal mathematical
signal). If it doesn't move AUC, try **#2** next (needs a small stateful
change to the live hook, but the training-side computation is free from
existing JSONL). **#1** as proposed needs new per-position instrumentation
to do properly — deprioritize unless #2/#3 show promise and justify the
extra S1 collection cost.
