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

---

## 2026-08-23 08:xx UTC — Track C, second pass: block-position-relative-to-EOS

The routine brief's candidate list names a 4th motivation not covered by the
first entry: "block-position-relative-to-EOS". Flagging a landmine before
proposing a variant of it, because this is not a fresh idea — it's adjacent
to one Phase B design already tried and rejected.

### Why this needs extra scrutiny, not just a pitch

`PHASE_B_L1_DESIGN.md` line 19 excludes raw `block_idx` and
`active_mask_size` from the frozen 5-feature set explicitly: *"Phase A
showed they add ~+0.001 AUC on top of confidence-shape; keeping them invites
the same overfitting that trashed HumanEval in rev. 2 at N=50."* So a raw
position feature has already been tried, on this exact problem, and burned
a full memo revision on HumanEval overfit. Any position-based proposal has
to explain why it's different from what already failed, not just that it
sounds plausible.

### What's actually available at the invocation site

`llada/generate.py`: `num_blocks = gen_length // block_length` (line 154,
computed once per generation call) and the corrector-invocation loop
iterates `for block_idx in range(num_blocks)` (line 168). So
`block_idx / num_blocks` is a free, already-in-scope ratio — no new
instrumentation.

**Important caveat, checked before proposing this:** LLaDA/ProSeCo's block
loop runs `num_blocks` iterations unconditionally per the `gen_length`
generation budget set at call time (lines 149-168) — I did not find
early-exit-on-EOS logic in this file's block loop. If that's right, "EOS"
in the candidate-list name is really "the generation's configured length
budget," not the model's actual end-of-sequence token position, for
non-terminating generations. Worth Lucas confirming this reading before
anyone trusts the feature name — if there *is* early EOS handling elsewhere
in the sampler that I didn't grep for, the semantics change.

### Proposed feature: `block_frac_remaining = 1 - (block_idx + 1) / num_blocks`

Framed as fraction of the block budget remaining, not raw index, for one
concrete reason the rev. 2 failure doesn't rule out: raw `block_idx` is not
comparable across samples with different `num_blocks` (a `block_idx=3` means
"almost done" for a 4-block generation and "just started" for a 40-block
one) — that non-comparability is a plausible *contributor* to why a raw
position feature overfit at N=50, on top of the small-sample-size problem
the design doc's phrase "at N=50" is already flagging. A normalized fraction
at least removes the cross-sample scale mismatch. It does **not** remove the
small-sample overfitting risk, and Phase B's held-out sets (N=100/64) are
still small enough that this risk is live, not hypothetical.

Motivation for why it might carry signal at all: later blocks condition on
more already-committed tokens, so a confidence-shape signal at
`block_frac_remaining ≈ 0` (last block) may mean something structurally
different from the same shape at `≈ 1` (first block, least context) —
e.g. low confidence late in generation may be rarer and more informative
(less "the model just hasn't seen enough context yet" noise) than the same
raw confidence value early on.

**Recommendation:** given this is a re-run of a feature class that already
caused a HumanEval overfit incident, do not add this casually. If tried,
train/validate it in isolation (not bundled with #1-#3 above), and — unlike
those three — treat a positive-looking AUC bump on the *training* split with
explicit suspicion until it's confirmed on a held-out GroupShuffleSplit at
Phase A's full N (200 prompts), not just Phase B's smaller eval subsets,
given that's the exact condition (small N) under which the earlier position
feature failed. This is squarely a "propose, do not implement" item per the
routine brief — flagging the priority-vs-#1-#3 question for whoever picks
this up: probably lowest priority of the four, precisely because its failure
mode is already documented history here rather than speculative.

---

## 2026-08-23 — Track C, third pass: two features not on the routine brief's list

The prior two entries cover all four motivations named in the routine
brief's candidate list (rank, historical agreement, pooled-vocab entropy,
block-position). Re-reading `features_from_predictor_logits`
(`l1_policy.py:102-135`) for this pass instead of the brief's list, looking
for signal shapes the current 5 features and the 4 already-logged proposals
both miss. Two candidates, both pure functions of `pp` already in scope —
same cheapest cost class as idea #3 above, no cross-invocation state, no new
S1 instrumentation.

### 8. Top1-top2 margin, mean/min over active positions (cheap, category: (1))

None of the 5 frozen features or the 4 proposals above distinguish "one
token is clearly best, runner-up is far behind" from "top-1 and top-2 are
nearly tied." `predictor_conf_mean_active` (top1 prob) and
`predictor_entropy_mean_active` both partially capture this but conflate it
with tail mass: a position where `pp` puts 0.4 on the top token and spreads
the remaining 0.6 thinly across 5000 vocab entries has middling top1 and
*high* entropy (dominated by the long thin tail), while a position with 0.4
on top-1 and 0.35 on a single clear runner-up has the same top1 but much
*lower* entropy and represents a genuinely different situation for the
corrector — a real two-way call rather than diffuse uncertainty. This is the
standard "margin vs. entropy" distinction from active-learning uncertainty
sampling, and it's not represented in the current feature set at all.

Proposed features: `predictor_margin_mean_active` and
`predictor_margin_min_active` = mean/min over active positions of
`top1_prob - top2_prob`. Computable via `pp.topk(2, dim=-1).values` right
next to the existing `pp.max(dim=-1)` call at `l1_policy.py:122` — one extra
`topk` call, no new tensors held across invocations, no retraining-time-only
computation needed (unlike features #1/#2 above, this is as cheap in the
*live* hook as in offline training, so no live/offline asymmetry to
introduce).

**Concrete failure mode this could catch:** two blocks with identical
`predictor_conf_mean_active ≈ 0.4` and similar `entropy_mean_active` (because
both have long-tailed remaining mass) but different margins — one is a
genuine top-2 coin-flip (small margin, corrector plausibly resolves it one
way or the other) and one has a clear-but-imperfect top-1 pick with the rest
of the mass diffuse noise (large margin, corrector less likely to overturn
it). Current features score these identically; margin doesn't.

**Priority:** try before #1/#2 above (no cross-invocation state, no
live-hook statefulness to add, purely additive to the existing
`features_from_predictor_logits` return dict) — same cost tier as #3
(pooled-vocab entropy), and orthogonal to it (margin is a per-position
top-2 statistic; pooled-vocab entropy is a cross-position mixture
statistic). Worth trying together or in the same ablation pass since
neither one's presence should mask the other's individual contribution —
report both single-feature-added AUCs, not just the combined one.

### 9. Contiguous-run length of low-confidence active positions (moderate, category: (1))

Idea #3's pooled-vocab entropy asks whether uncertainty is concentrated on
one recurring token-choice across the block; this asks a spatially distinct
question: whether the *low-confidence positions themselves* are clustered
together in the sequence or scattered. A block where positions 4-9 (six in a
row) are all low-confidence and everything else is high-confidence describes
one localized hard span — plausibly one semantic unit (a name, a
multi-token number, a code identifier) that the corrector can fix in one
coherent pass. A block with the same *count* of low-confidence positions
scattered singly across 30 positions describes diffuse, probably
independent uncertainty, where a single corrector pass is less likely to
cleanly resolve all of them. `predictor_conf_std_active` and
`entropy_mean_active` are both order-invariant (permuting which active
positions have which values doesn't change either statistic) and
structurally cannot see this.

Proposed feature: `low_conf_max_run_frac_active` = length of the longest
contiguous run of active positions with `top1 < τ` (a fixed threshold, e.g.
the block's own median top1 to stay scale-free — needs picking a concrete τ
before implementing, flagged here as an open parameter not a decided one),
divided by `active_mask_size` to stay comparable across block lengths for
the same normalization reason idea #1's rank-fraction and the
block-position entry's `block_frac_remaining` both normalize by.

**Why this is a different cost tier than #8:** needs positions kept in
their original sequence order (not just reduced to an unordered set of
`top1` values), which `features_from_predictor_logits` already has via
`am`'s position-indexed boolean mask before the `t = top1[am]` flattening
step at `l1_policy.py:127` — so it's still a pure function of the current
invocation's data already in scope, no cross-invocation state needed. But
it needs a threshold choice (τ) that #8 doesn't, and threshold choices are
exactly the kind of extra researcher-degree-of-freedom that's easy to
quietly overfit on a small N — same caution flagged for the block-position
entry above, though this is a within-block spatial statistic rather than a
cross-sample position statistic, so the specific rev-2 HumanEval failure
mode doesn't directly transfer.

**Priority:** below #8 (needs a threshold decision, #8 doesn't), above #1
(no cross-invocation state, #1 needs a rolling window). Try after #3 and #8
have been evaluated individually; if either already saturates AUC further,
this one's marginal value is unclear until that's known.

### Running priority list across all three Track C passes (9 ideas total)

Cheapest / no new instrumentation / no threshold parameter first:
**#3 (pooled-vocab entropy) ≈ #8 (top1-top2 margin)** → **#9 (contiguous
low-conf run, needs a τ)** → **#2 (agreement-rate-so-far, needs live-hook
statefulness)** → **#1 (rank-within-recent-blocks, needs new
per-position instrumentation to do properly)** → **block-position variant
(lowest priority, documented overfit history on this exact problem class)**.
Not re-deciding this ordering from scratch each pass — flagging here so the
next Track C fire building on this file starts from "what hasn't been tried
yet" rather than re-deriving the same four brief-listed motivations a third
time.
