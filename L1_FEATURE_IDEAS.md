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
per-position instrumentation)** → **block-position variant (lowest
priority, documented overfit history on this exact problem class)**.
Not re-deciding this ordering from scratch each pass — flagging here so the
next Track C fire building on this file starts from "what hasn't been tried
yet" rather than re-deriving the same four brief-listed motivations a third
time.

---

## 2026-08-23 — Track C, fourth pass: structural gap in the entropy feature triplet, plus two shape statistics not yet proposed

All four routine-brief motivations are covered (passes 1-2), and passes 1-3
between them cover per-position margin, pooled-vocab mixture entropy, and
within-block spatial clustering of low-confidence positions. Re-reading
`features_from_predictor_logits` (`l1_policy.py:119-135`) once more before
proposing anything, specifically comparing what's computed for `t` (top1)
against what's computed for `e` (entropy), since the two tensors are built
from the same `pp` in the same function and get asymmetric treatment.

### 10. `predictor_entropy_std_active` — closes an unexplained asymmetry in the existing feature set (cheapest, category: (1), no threshold, no new instrumentation)

The confidence branch keeps three moments of `t` over active positions:
mean, min, **std**. The entropy branch keeps only two of `e`: mean, **max**.
There's no stated design-doc rationale for why entropy gets a tail-extremum
(`max`) where confidence gets a spread statistic (`std`) instead of also
getting its own tail-extremum (`min`) or its own spread. This isn't a new
motivation invented for this pass — it's the same "shape, not just level"
argument the design doc already uses to justify the 5-feature set over a
scalar-confidence baseline, applied to a spot where the current set doesn't
actually follow its own logic. `entropy_std_active` = `e.std()` (guarded to
0.0 when `e.numel() <= 1`, exactly like the existing `predictor_conf_std_active`
guard at `l1_policy.py:132`) is one extra line next to the current
`e.mean()`/`e.max()` calls, pure function of `e` already in scope, no
threshold, no cross-invocation state.

Concrete failure mode this could catch: two blocks with identical
`entropy_mean_active` and `entropy_max_active` can differ in whether most
positions cluster near that mean (low std — a uniformly medium-uncertain
block) or whether most positions are near-zero entropy with one or two
outliers pulling the mean up to match the first block (high std — a
mostly-easy block with a small hard subset). `entropy_max_active` alone
can't distinguish these because both blocks can share the same single
maximum; only the spread across the rest of the distribution can.

**Priority: try this first of the three below.** It's the cheapest (one
line), needs no threshold, and — unlike #3/#8/#9 in prior passes, which all
add a structurally new statistic — this one is motivated by an inconsistency
in the current set's own design rather than a new hypothesis, which makes a
null result easier to interpret (either the asymmetry was harmless, or it
was quietly costing AUC).

### 11. Skewness of active-position top1 confidence (`predictor_conf_skew_active`) — third moment, category: (1)

Passes 1-3 added statistics about individual-position shape (#8 margin),
cross-position mixture (#3 pooled entropy), and cross-position spatial order
(#9 contiguous run). None added a higher moment of the *same* `t` distribution
that `mean_active`/`min_active`/`std_active` already summarize with its first
two moments plus an extremum. Skewness is the natural next one, and it's not
redundant with `std` the way, e.g., a second std-like statistic would be:
two blocks can share identical mean and std of `t` while differing in
whether the distribution's mass sits mostly above the mean with a thin low
tail (negative skew — one or a few severely-bad positions pulling a mostly-good
block down) or mostly below the mean with a thin high tail (positive skew —
a mostly-mediocre block with one clean position). These describe different
corrector-worthiness situations (a small localized fix vs. a broadly
mediocre block) that `mean`/`min`/`std` alone cannot separate, since
skewness is by construction the lowest-order moment orthogonal to both.

Standard bias-corrected sample skewness over the same `t = top1[am]` tensor
already computed at `l1_policy.py:127`; no new tensors, no threshold. One
implementation note worth flagging before anyone trains on it: skewness
estimates are noisy at small `n_active` (short blocks), more so than mean or
std — worth checking the distribution of `active_mask_size` in the pooled
v2+v3 JSONL before trusting this feature's magnitude, not just its sign, and
worth reporting AUC-with-vs-without split by block-length quartile rather
than only pooled AUC, in case this feature's contribution is concentrated in
long blocks and adds noise in short ones.

### 12. Pearson correlation between per-position top1 confidence and per-position entropy, over active positions (`conf_entropy_corr_active`) — category: (1)+(3)-adjacent, cheap but conceptually distinct from #3/#8

`t` and `e` are computed from the same `pp` but the existing feature set
never looks at their *joint* relationship across positions — only separate
marginal summaries of each. Proposed: `corr(t, e)` over active positions
(guarded to 0.0 when `am.sum() <= 1`, same edge case as the existing `std`
guards). This is different from #8's margin (a per-position, top-2-only
statistic) and from #3's pooled-vocab entropy (a mixture of the *distributions*
themselves, not a summary relating two already-reduced per-position scalars).

Motivation: a position can be low-`top1` for two structurally different
reasons that current features (including margin and pooled entropy) don't
cleanly separate at the *block* level — mass concentrated on a small number
of alternatives (low top1, low-ish entropy: "confidently wrong," corrector
likely flips to a specific alternative) vs. mass spread thinly over many
tokens (low top1, high entropy: "genuinely unsure," corrector less likely to
converge on one specific fix). A block where low-confidence positions are
predominantly the first kind vs. predominantly the second kind will have
negative vs. positive/weak correlation between `t` and `e` respectively,
which no current single-array summary statistic captures. Flagging the
overlap risk directly: this is close enough in spirit to margin (#8) that
if both are tried, report each one's single-feature-added AUC separately
before combining, same discipline pass 3 already recommended for #3 vs #8 —
otherwise a positive combined result can't be attributed to either.

### Updated running priority (12 ideas total across four passes)

Cheapest / most orthogonal to what's already logged, in order:
**#10 (entropy_std, one-line, motivated by fixing an existing asymmetry)**
→ **#3 ≈ #8 (pooled-vocab entropy / margin, tried in pass 3)** → **#11
(skewness, new moment, needs block-length-quartile check before trusting
magnitude)** → **#12 (conf-entropy correlation, cheap but overlaps #8 —
report single-feature AUC separately)** → **#9 (contiguous run, needs τ)**
→ **#2 (agreement-rate-so-far, needs live-hook statefulness)** → **#1
(rank-within-recent-blocks, needs new per-position instrumentation)** →
**block-position variant (lowest priority, documented overfit history)**.
No implementation done here per the routine brief — this file stays
proposals-only.

---

## 2026-08-24 — Track C, fifth pass: two moment/shape statistics from #10-#12 pushed further, plus one genuinely new signal (top-k truncated entropy)

Checked this file wasn't touched more recently than the other three tracked
files before starting (per the routine's track-selection heuristic) — this
file's last entry was 2026-08-23 22:25 UTC, oldest of the four as of this
fire. Re-read `features_from_predictor_logits` (`l1_policy.py:102-135`)
again against all 12 prior ideas before proposing anything, specifically
looking for statistics that aren't just "the next moment" of `t` or `e`
individually (passes 4-5 risk diminishing returns there) but instead use
`pp` (the full per-position distribution) in a way none of #1-#12 do — only
`t` (top1) and `e` (scalar entropy) have been mined so far; `pp` itself
(the full softmax vector, pre-reduction) has not.

### 13. Top-k truncated, renormalized entropy over active positions (`predictor_topk_entropy_mean_active`, k=5) — category: (1), cheap, uses `pp` directly

`entropy_mean_active` (existing) and `#3`'s pooled-vocab entropy both use
the **full** vocabulary distribution, which for a ~50k-entry vocab means
entropy is often dominated by how much probability mass sits in a long,
low-value tail that has nothing to do with which of the *plausible*
candidates the corrector might pick. Margin (#8) goes to the opposite
extreme and looks at only the top-2. Neither is "uncertainty among the
tokens that actually matter": a position with top-5 probabilities
`[0.3, 0.25, 0.2, 0.15, 0.1]` (genuinely torn between ~5 real candidates)
and a position with top-5 `[0.3, 0.05, 0.04, 0.03, 0.02]` and the rest of
its mass spread over 49995 near-zero tail entries can have *similar* full
entropy (the second position's huge tail inflates its entropy to look like
the first) but describe completely different situations for the corrector
— the first is a genuine multi-way call, the second is confidently
top-1-ish with numerical noise in the tail.

Proposed: take `pp.topk(5, dim=-1).values` (already adjacent to the
existing `pp.max(dim=-1)` call and to #8's proposed `topk(2, ...)` — if #8
is implemented first, this reuses the same `topk` call with `k=5` instead
of `k=2`), renormalize those 5 values to sum to 1, compute entropy of the
renormalized 5-way distribution per position, then mean over active
positions. This is bounded in `[0, ln(5)]` regardless of vocab size, unlike
full entropy which has a much larger effective range dominated by tail
mass — so it's also more numerically comparable across positions/samples
than the existing `entropy_mean_active`, independent of whether it adds
AUC.

**Why this isn't redundant with #3 or #8:** #3 (pooled-vocab entropy) pools
information *across positions*, this pools *across the top-k tokens within
one position* — orthogonal axis. #8 (margin) only looks at 2 tokens and
only their gap, not the shape of the remaining top-k mass (e.g. margin
can't distinguish `[0.4, 0.35, 0.2, 0.05]` from `[0.4, 0.35, 0.1, 0.1,
0.05]` — same top1/top2, different k=5 entropy). k is an open parameter
(flagged like #9's τ) — 5 is a reasonable starting guess (small enough to
exclude tail noise, large enough to catch real multi-way ties) but should
be treated as a hyperparameter to sweep, not a fixed choice, before
trusting a specific k's AUC number over another.

### 14. Mean per-position KL divergence to the block's pooled mean distribution (`kl_to_pooled_mean_active`) — category: (1)+(3), moderate, uses `pp` directly

#3 computes entropy of the *average* distribution (`pp[am].mean(dim=0)`),
a single scalar describing how concentrated the block's aggregate belief
is. It does not describe how much individual positions' distributions
*disagree* with that aggregate — two blocks can have the same pooled-mean
entropy while one has every position closely tracking the mean (low
per-position dispersion) and the other has positions each concentrated on
different, mutually exclusive tokens that happen to average out to the same
pooled shape (high dispersion). This is a distinct question from #12's
`corr(t, e)`, which relates two already-reduced *scalars* per position, not
the *distributions* themselves.

Proposed: `pooled = pp[am].mean(dim=0)` (the same tensor #3 already
computes en route to its entropy), then for each active position `i`,
`KL(pp[i] || pooled)`, averaged over active positions. Reuses #3's `pooled`
tensor exactly — if #3 is implemented, this is one extra reduction on data
already computed, not a new pass over `pp`.

**Concrete failure mode this could catch:** a block where every active
position is torn between the *same* two tokens (e.g. singular/plural
agreement repeated across several positions in a sentence) has low
KL-to-pooled-mean (each position's distribution closely resembles the
average, since they're all doing the same thing) — a coherent, likely
one-shot-fixable pattern. A block where position 3 is confidently choosing
token A, position 7 is confidently choosing token B, and position 12 is
confidently choosing token C (three different, mutually confident but
locally-uncertain-relative-to-block-pattern choices that happen to pool
into a diffuse average) has high KL-to-pooled-mean despite potentially
similar `entropy_mean_active` and pooled-entropy (#3) values to the first
case. #3 alone cannot distinguish "everyone agrees on the ambiguity" from
"everyone is confidently ambiguous about different things."

Cost note: this is the most expensive of the three proposed this pass — a
per-position KL computation is `O(active_mask_size × vocab_size)`, same
order as computing `e` already is, so not prohibitively different in
compute, but conceptually the least "pure single extra line" of the three
(#13's topk entropy and #15 below are both cheaper to reason about in
isolation).

### 15. Std of the top1-top2 margin over active positions (`predictor_margin_std_active`) — category: (1), cheapest of the three, extends #8

Pass 3's margin proposal (#8) kept mean and min, following the same
mean/min pattern as the original `predictor_conf_{mean,min}_active` — but
per pass 4's own logic for #10 (closing the mean/std asymmetry between the
confidence and entropy branches), margin has the identical gap: mean and
min but no spread statistic. `margin_std_active` = std of
`(top1_prob - top2_prob)` over active positions, guarded to 0.0 at
`n_active <= 1` exactly like every other std feature in this file.

Motivation, following the same shape-not-just-level argument used for #10
and #11: two blocks can share the same mean and min margin while one has
uniformly middling margins across all positions (low std — a consistently
semi-confident block) and the other has a mix of very-confident (large
margin) and near-tied (small margin) positions averaging to the same mean
(high std — a block with a real hard subset embedded in an otherwise easy
one). This is the same "outlier subset vs. uniform mediocrity" distinction
#11's skewness proposal makes for raw confidence, applied to margin instead
— a different underlying quantity, not a restatement of #11.

**Priority this pass:** try **#15 first** (cheapest — one extra `.std()`
call directly analogous to three already-justified precedents in this file:
`predictor_conf_std_active`, #10's `entropy_std_active`, if implemented,
and #8's margin itself), then **#13** (needs a k sweep but is a pure
function of `pp` with no cross-invocation state), then **#14** (correct but
the most compute and the least "obviously additive" of the three — best
tried only after #13 and #3 have been evaluated, since it reuses #3's
`pooled` tensor and its marginal value over #3 alone is the open question).

### Updated running priority (15 ideas total across five passes)

**#10 (entropy_std) ≈ #15 (margin_std, this pass) ≈ #3 ≈ #8** (all
one-line-or-near, no threshold, no new instrumentation) → **#13 (top-k
truncated entropy, needs a k sweep)** → **#11 (skewness)** → **#12
(conf-entropy correlation)** → **#14 (KL-to-pooled-mean, this pass — most
compute, reuses #3's tensor, evaluate after #3)** → **#9 (contiguous run,
needs τ)** → **#2 (agreement-rate-so-far, needs live-hook statefulness)**
→ **#1 (rank-within-recent-blocks, needs new per-position
instrumentation)** → **block-position variant (lowest priority, documented
overfit history)**. No implementation done here per the routine brief —
this file stays proposals-only. Next Track C pass should check this
priority list before re-deriving moments/shapes of `t` or `e` a third or
fourth time — the remaining unexplored axis after this pass is genuinely
cross-invocation state (#1, #2) and `pp`-based joint statistics like #14,
not another single-array summary statistic.


---

## 2026-08-24 12:25 UTC — Track C, sixth pass: temporal/within-block-step state, and a budget-awareness feature — a third state category not touched by passes 1-5

Checked this file's last entry (2026-08-24, pass 5) against `L1_AUDIT_FINDINGS.md`
and `MEMO_V4_SKELETON.md`'s latest commits before starting — this file was the
oldest-touched of the four track files, per the routine's selection rule.

Passes 1-5 (15 ideas) exhaust two state categories: (a) single-invocation
statistics of `t`/`e`/`pp` at one predictor call (#3, #8-#15), and (b)
cross-block state keyed by `sample_id`, folded over *already-logged*
corrector-invocation records (#1, #2). Re-reading `llada/generate.py:167-329`
end to end (not just the `features_from_predictor_logits` call site) for
this pass turned up a third category neither of the first two covers:
**cross-step state within a single block**, and separately, **the sampler's
own resource-budget state**, which — unlike (a)/(b) — is not a function of
`pp` or of past corrector outcomes at all.

### 16. Predictor-confidence delta since the previous predictor step in this block (`predictor_conf_delta_prev_step_mean_active` / `_min_active`) — category: new (temporal), needs live-hook state, no new S1 collection required to *start* logging it

`generate.py`'s `while True:` block loop (lines 183-208) calls the predictor
and computes `phase_b_features` **every step**, not just on steps where
`invoke_corrector` ends up `True` — `features_from_predictor_logits` already
runs unconditionally at line 205 whenever `corrector_policy is not None`.
That means the live hook already computes a fresh `top1`/`active_mask` for
every predictor step in the block; nothing currently keeps the *previous*
step's values around to compare against. Right now every one of the 15
prior ideas treats each predictor call as if it exists in isolation — none
asks whether this step's confidence read is a stable read of the block or a
one-step fluctuation.

Proposed: track `prev_top1` (a position-indexed tensor over the block's
positions, not just active-position values, so it survives positions
transitioning in/out of `active_mask` between steps) across iterations of
the block's `while` loop, reset at each new `block_idx`. At each step,
restrict to positions active in *both* the current and previous step's
mask, and compute `(top1_now - top1_prev)` over that intersection:
`predictor_conf_delta_prev_step_mean_active` = mean of that delta,
`_min_active` = most-negative (largest confidence *drop*) — a drop is
plausibly more informative than a rise, symmetric to why the existing
feature set already prefers `min_active` over `max_active` for confidence.
First step of a block has no previous-step intersection; define the
cold-start value as `0.0` (no evidence of change yet), same convention as
idea #2's cold-start choice in pass 1.

**Concrete failure mode this could catch:** two blocks share identical
single-step `predictor_conf_mean_active`, but one block's confidence at
those positions has been stable across the last several predictor steps
(the model reached a stable read) and the other's has been oscillating step
to step (the model is still working out what belongs there). The stable
case is plausibly a worse candidate for corrector invocation — if the
model's belief hasn't moved, another predictor pass alone is unlikely to
resolve it either, whereas oscillation suggests the position is still
"in play" and closer to a value the corrector might usefully intervene on.
No existing feature (single-invocation or cross-block) can see this,
because it requires two *consecutive* predictor calls to compare, and
nothing before this pass tracks predictor state across the `while` loop's
own steps.

**Cost, and why this is not free like #13/#14/#15:** the *live* hook change
is small (one tensor carried across loop iterations, reset per block) but
this is the first idea in the file that changes what the *inline* hook
computes, not just what `l1_training.py` folds over already-logged JSONL
columns — training on this feature needs S1 to start logging per-step
`top1` (or at least the delta) even on non-invoked steps, which the current
JSONL schema does not capture (only invocation-conditional records are
written, per `generate.py:301` `if s1_log is not None:` sitting inside
`if invoke_corrector:`). This is a **new S1 collection requirement**, same
tier of cost as idea #1's "needs new per-position instrumentation" —
flagging explicitly since passes 3-5's ideas were all trainable from
existing v2/v3 JSONL and this one is not.

### 17. Predictor argmax flip rate since the previous step, active positions (`predictor_argmax_flip_rate_active`) — category: new (temporal), same cost tier as #16, complements it

Same cross-step state as #16, but tracks *identity* instability rather than
*magnitude* instability: fraction of positions active in both the current
and previous step whose `argmax` token changed, regardless of how much
`top1`'s probability value moved. This is deliberately not redundant with
#16 — a position can have a large confidence *delta* while the argmax token
stays the same (the model becomes more sure of the same pick) or a small
delta while the argmax *flips* (a near-tied position see-sawing between two
tokens with similar probability each step). The two together span
magnitude-of-change and identity-of-change; neither single-step statistic
in passes 1-5 (including margin, #8) can see either, since margin is a
snapshot of one step's top1-vs-top2 gap, not a comparison across steps.

Motivation: a block with a high flip rate is one where the predictor itself
hasn't converged on stable token identities yet — arguably a *worse* moment
to invoke the corrector (the corrector is fixing an argmax snapshot that
may already be stale by the next predictor step regardless of correction)
rather than a better one, which is a genuinely different prediction from
most of #1-#15 (which mostly hypothesize "more signal here → corrector
more likely to be useful"). Flagging this as a case where the *sign* of the
effect is not obvious a priori and should be checked empirically, not
assumed, before trusting a plausible-sounding story either way.

**Cost:** identical instrumentation requirement to #16 (same `prev_*` state
across the block loop, same new-S1-collection need) — if #16 is
implemented, #17 is a marginal addition to the same tracked state, not a
second independent instrumentation change.

### 18. Budget-state feature: NFE spent so far as a fraction of this generation's matched-FLOPs allowance (`nfe_frac_spent`) — category: new (resource-state, not confidence-based), flag fairness caveat before considering

Distinct from #16/#17 in kind, not just in what state it tracks: this is
not a function of `pp`/`top1`/`ent` at all. `generate.py` already maintains
running `predictor_nfe`, `corrector_nfe`, `total_nfe` counters (lines
162-164, updated throughout the loop) — a policy could, in principle, read
`total_nfe` so far relative to the generation's allotted budget and make
invocation decisions that spend more freely early and more conservatively
as the budget is consumed (or the reverse), rather than treating every
step's decision identically regardless of how much budget remains.

**Why this needs a fairness flag before anyone touches it, not just a "try
it" note like #16/#17:** Phase B's whole comparison design (per
`PHASE_B_L1_DESIGN.md` and the matched-FLOPs framing referenced in
`L1_AUDIT_FINDINGS.md`'s accounting-bug findings) rests on `fixed`,
`cadllm_linear`, and `l1_mlp` sharing every code path except
`should_invoke`. `FixedPolicy` and `CadLLMLinearPolicy` are both
budget-blind by construction (`FixedPolicy` fires on a step-count modulus,
`CadLLMLinearPolicy` thresholds a confidence scalar) — if `l1_mlp` alone
gained access to `total_nfe`/budget state, it would not be a like-for-like
comparison of *feature quality* anymore, it would be comparing a
budget-aware policy against two budget-blind ones, conflating two separate
questions (does L1's feature set predict usefulness better, vs. does
budget-awareness help at all) into one AUC number. If this is pursued, it
needs either (a) a matched budget-aware variant of `CadLLMLinearPolicy` for
a fair three-way comparison, or (b) explicit framing as a separate ablation
question from the frozen 5-feature-set comparison, not a silent sixth
feature quietly added to the existing L1 MLP input. Recommend flagging this
question to Lucas rather than deciding it here, since it changes what
Phase B's headline comparison is measuring, not just what the MLP takes as
input.

### Priority and status note

**#16 and #17 need a new S1 logging change** (per-step, not just
per-invocation, records — or at minimum, live-hook state that starts
getting logged going forward) before they're trainable at all; they cannot
be evaluated against the existing v2/v3 JSONL the way #3/#8/#10/#11/#12/
#13/#14/#15 can. That makes them higher cost than anything in passes 3-5
despite being conceptually simple, on par with idea #1's per-position
instrumentation gap from pass 1. **#18 is a policy-design and
experiment-design question first, a feature-engineering question second** —
flagging it for Lucas's judgment rather than placing it in the AUC-priority
ordering below, since "does it help AUC" isn't the operative question until
the fairness framing is settled.

Updated priority for the *trainable-today* ideas (unchanged from pass 5,
repeated here so the next pass doesn't have to scroll up): **#10 ≈ #15 ≈
#3 ≈ #8** → **#13** → **#11** → **#12** → **#14** → **#9** → **#2** →
**#1**. New-instrumentation-required ideas, separately: **#16 ≈ #17**
(bundle together, same live-hook change) → **block-position variant**
(still lowest priority, documented overfit history). **#18** sits outside
this ordering pending Lucas's call on the fairness question above.

## 2026-08-24 18:2x UTC — Track C, seventh pass: fourth moment, spatial autocorrelation, cross-block carryover

Track A stayed `EGRESS_BLOCKED` this fire (7/7 consecutive fresh probes,
`arxiv.org/list/cs.LG/recent` — see `L1_LITERATURE.md`'s matching entry, no
re-notify per standing guidance). Routing fell to the oldest-touched of
B/C/D: `L1_AUDIT_FINDINGS.md` was just touched last fire (16:27 UTC),
`MEMO_V4_SKELETON.md` at 14:26 UTC, `L1_FEATURE_IDEAS.md` (this file) at
12:27 UTC — oldest, so Track C routes.

Six passes so far (18 ideas, #1-#18) cover: rank/margin/agreement/vocab-
entropy (pass 1), block-position (pass 2), margin + run-length (pass 3),
the mean/std/skew moment family plus a cross-position correlation (pass
4), top-k entropy/KL-dispersion/margin-std (pass 5), and within-block
temporal deltas + a budget-state feature (pass 6). Three gaps remain that
no prior pass touched: the confidence distribution's fourth moment, its
*spatial* (within-block, single-step) structure rather than its shape or
its temporal (across-step) structure, and any signal that crosses a block
boundary rather than staying within one invocation or one sample's history.

### 19. Excess kurtosis of active-position top-1 confidence (`predictor_conf_kurtosis_active`) — cheapest, category (1)

Closes the moment family pass 4 started (`_std`, `#11` skew) but stopped
one short of. Kurtosis measures tail weight / peakedness independent of
what std and skew already capture: two blocks can have identical mean,
std, and skew but different kurtosis if one has a few extreme low-
confidence positions buried in an otherwise uniform mid-confidence spread
(heavy-tailed) versus the same spread with no such outliers
(platykurtic). That's a distinct failure signature from "generally
uncertain" (`_mean`/`_std`) or "lopsided" (`_skew`, #11) — a handful of
near-zero-confidence tokens in one block is exactly the kind of local
catastrophic-miss pattern the corrector exists to catch, and it can hide
inside an unremarkable mean/std/skew reading.

```python
from scipy.stats import kurtosis
conf = top1_probs[active_mask]  # same tensor #8/#10/#11 already slice
predictor_conf_kurtosis_active = float(kurtosis(conf.numpy(), fisher=True, bias=False))
```

Same cost tier as #10/#11/#12 — reuses the exact `conf` slice already
computed for the frozen five features, one more `scipy.stats` call. No new
instrumentation; computable from existing v2/v3 JSONL logits if raw
per-position confidences were retained, otherwise needs the live `pp`
tensor at invocation time same as #10-#15 (check before assuming
retrainable on old data — flag for whoever picks this up to confirm
against what's actually saved per-record in `s1/runs/*.jsonl`, same caveat
pass 4/5 raised and this pass didn't re-verify given the time cap).

### 20. Lag-1 spatial autocorrelation of top-1 confidence over active positions (`predictor_conf_spatial_autocorr_active`) — moderate, category (1)+(3)-adjacent

Distinct from #9 (contiguous low-confidence run length, a threshold-based
count) and from `_std`/kurtosis (both permutation-invariant — they don't
see position order at all). Two blocks with identical multiset of
confidence values can have very different spatial structure: one clustered
(low-confidence positions bunched together — high positive autocorrelation,
also likely to trip #9's run-length stat) versus one alternating
(high/low/high/low — near-zero or negative autocorrelation, but #9 sees no
long run and might miss it entirely if no single run clears its length
threshold). Autocorrelation is continuous and catches the alternating
case #9 structurally cannot.

```python
def lag1_autocorr(x: np.ndarray) -> float:
    if len(x) < 3:
        return 0.0  # degenerate block, same active_mask_size==1/2 guard #9 needs
    x0, x1 = x[:-1] - x.mean(), x[1:] - x.mean()
    denom = np.sqrt((x0 ** 2).sum() * (x1 ** 2).sum())
    return float((x0 * x1).sum() / denom) if denom > 0 else 0.0

predictor_conf_spatial_autocorr_active = lag1_autocorr(conf.numpy())
```

Ordering-dependent, unlike every other feature in the frozen five plus
#1-#18 except #9 — worth flagging explicitly since it's a small but real
mechanism-space expansion (uses position *order* within the block, not
just the multiset of values or absolute block position like #4's
EOS-distance feature). Same degenerate-block edge case #9 already handles
(`active_mask_size` 0/1/2) needs the same guard here.

### 21. Previous block's final active-position mean confidence, carried into this block's feature vector (`prev_block_final_conf_mean`) — moderate-to-expensive, category: new (cross-block), needs live-hook state

Every idea in passes 1-6 (including #16/#17's temporal deltas) is scoped
to a single block: either one invocation's snapshot, or a delta against
the previous *step* inside the same block. None carry information across a
block boundary. If the predictor exits block N confidently, that's mild
evidence the model is "on a roll" for block N+1's early steps too — models
don't reset generation quality at block boundaries even though ProSeCo's
corrector-invocation decision currently does (each block's `active_mask`
and hence the frozen five features start fresh at `block_start`). Whether
that carryover signal is real or just autocorrelated noise from adjacent
generation quality is an open empirical question, not asserted here.

Feasibility, checked against `llada/generate.py`'s block loop
(`for block_idx in block_pbar:` at line 168, `active_region_start`/
`block_end` recomputed each iteration at lines 169-170): the previous
block's final predictor confidence is available for free at zero
additional forward-pass cost — it's just the last computed `pl`/`top1_probs`
slice before the loop moves to `block_idx + 1`, needs one variable
(`prev_block_conf_mean = None` initialized before the loop, updated at the
end of each `block_idx` iteration) threaded through the loop body. For
`block_idx == 0` there is no previous block — needs an explicit sentinel
(e.g. `0.0` with a paired `is_first_block` flag, or drop `block_idx == 0`
records from training the way #4's EOS-distance feature already has to
handle the last-block edge from the other end) rather than a silent
default that could get confused with a genuinely low carried-over
confidence.

**Caveat worth flagging up front, in the same spirit as #18's fairness
question:** this is state that persists *within one generation*, not
across generations or samples — it does not raise the leakage concerns
`L1_AUDIT_FINDINGS.md` findings #1/#3 cover (those are about `sample_id`
crossing the train/test split; `prev_block_final_conf_mean` never crosses
a sample boundary, it resets at `block_idx == 0` for every new generation
same as the frozen five do). No fairness conflict with `cadllm_linear` or
`fixed` either, unlike #18 — both other policies could trivially compute
the same carried scalar from their own inputs (`cadllm_linear` already
reduces to a single mean-confidence number; `fixed` ignores features
entirely and stays budget-blind regardless). Flagging this explicitly
because #18's fairness question is still open with Lucas and it would be
easy to conflate "any feature using cross-invocation state" with #18's
actual problem, which is specifically about *budget* state, not sequence
state in general.

### Updated running priority (21 ideas total across seven passes)

Trainable-today tier, same ordering as pass 6's list, kurtosis (#19) and
spatial autocorrelation (#20) slot in near the existing moment/shape
cluster since they're the same cost tier and reuse the same `conf` slice:
**#10 ≈ #15 ≈ #3 ≈ #8** → **#19 ≈ #20** → **#13** → **#11** → **#12** →
**#14** → **#9** → **#2** → **#1**. New-instrumentation tier unchanged:
**#16 ≈ #17** → **#21** (cheapest of the three new-instrumentation ideas —
zero extra forward-pass cost, just state threading — but still needs the
same live-hook change #16/#17 need before any of the three are trainable
on existing data) → **block-position variant** (still lowest, documented
overfit history). **#18** still sits outside this ordering pending Lucas's
fairness-question call from pass 6.

**Next fire on Track C**, if routing lands here again: all three
easy-signal categories from the original brief (moment/shape, spatial,
temporal/cross-block) now have at least one entry; a fresh pass would need
to either go deeper on one of those three or open a genuinely new category
— worth checking whether any prior pass considered corrector-side signals
(what the *corrector* proposed, not just what the predictor's confidence
looked like going in) before assuming there's nothing left.

## 2026-08-25 — Track C, eighth pass: corrector-side historical signals (the genuinely-new category flagged at the end of pass 7)

Re-read `llada/generate.py:296-328`'s S1 record schema before proposing
anything, specifically to confirm which corrector-*outcome* fields are
already logged per invocation and therefore free to build a history
feature on without new instrumentation: `corrector_break_step`, `hit_max`,
`broke_at_step_1` (already used by #2), `active_mask_size`, and
`n_active_positions_changed_by_corrector`. The last two are unused by any
of the 21 prior ideas — #2 only reads the binary `broke_at_step_1` flag.
That binary collapses two different situations to the same value whenever
it's `False`: a corrector pass that flipped one token out of forty active
positions, and one that flipped thirty-eight. Both count as "disagreed"
for #2's agreement-rate; a magnitude-aware feature distinguishes them.

### 22. Correction magnitude, sample-so-far (`correction_magnitude_mean_so_far`) — cheap, category: (2)

`correction_magnitude_mean_so_far` = mean over this sample's *prior*
corrector invocations (causal, `block_idx' < block_idx` order, same
discipline as #2) of `n_active_positions_changed_by_corrector /
active_mask_size` — the fraction of active positions the corrector
actually touched, not just whether it touched any. Cold-start value (no
prior invocations) = 0.0, matching `FixedPolicy`'s implicit assumption
that there's no evidence of disagreement yet (mirrors #2's cold-start
choice but on the opposite end: #2 defaults optimistic on *agreement*,
this defaults to *no assumed magnitude*, since guessing a nonzero default
here would bias early-block invocation decisions on no evidence).

Motivation: complements #2 rather than duplicating it. Two samples with
identical `agreement_rate_so_far` (say 0.5) can differ sharply in how much
the corrector changes when it does disagree — one sample's disagreements
are single-token nits, another's are broad rewrites of the active region.
The former is weaker evidence that *this* block needs correction (the
corrector's disagreements so far have been minor); the latter is stronger
evidence (disagreements so far have been substantial). #2 cannot see this
distinction because `broke_at_step_1` is boolean per invocation.

Implementation note: same live-hook shape as #2 — `l1_policy.py`'s frozen
5-feature inline hook doesn't carry cross-invocation state today, so this
needs the same per-sample running-history threading through `generate.py`'s
block loop that #2/#16/#17/#21 already require. In `l1_training.py` it's a
cumulative-mean groupby, no new S1 collection — both `active_mask_size` and
`n_active_positions_changed_by_corrector` are already columns in every v2+
JSONL record.

### 23. Correction effort, sample-so-far (`correction_effort_mean_so_far`, `hit_max_rate_so_far`) — cheap, category: (2)

Same causal-history shape as #22, but built on `corrector_break_step`
(iterations the fixed-point loop took to converge) and `hit_max` (whether
it never converged within `max_corrector_steps_per_loop` and was cut off)
instead of the changed-token count. Two features from the same pair of
columns: `correction_effort_mean_so_far` = mean `corrector_break_step`
over prior invocations, and `hit_max_rate_so_far` = fraction of prior
invocations where `hit_max` was `True`. Cold-start: `1.0` for the effort
mean (matches #2's optimistic-agreement default — one step is what
`broke_at_step_1 == True` implies) and `0.0` for `hit_max_rate_so_far`.

Motivation: distinct from both #2 and #22. #2 asks "did it agree
immediately," #22 asks "how much did it change when it didn't," and this
asks "how hard did the corrector have to work to reach a fixed point at
all" — a sample where corrections regularly take 3-4 iterations (or
regularly hit the cap) is one where the active region has been unstable
under repeated correction, plausibly a different regime than a sample
where every past correction converged in 1-2 steps but changed a lot of
tokens (high #22, low #23 — a single confident large rewrite) versus one
where it took many iterations to converge on a small change (low #22,
high #23 — a genuinely contested handful of positions). The 2x2 spanned by
#22 and #23 is not collapsible to either alone.

Caveat: `hit_max_rate_so_far` inherits whatever bias `max_corrector_steps_per_loop`
introduces — a low cap manufactures a high hit-max rate independent of the
sample's real difficulty. Fine as a feature (the policy is trained under
one fixed cap per Phase B run, so this is a consistent, not a confounded,
signal within a run) but flag before comparing feature importances *across*
Phase B runs that use different `max_corrector_steps_per_loop` values.

### 24. Within-block repeat-invocation count (`corrector_invocations_this_block_so_far`) — cheapest of the three, category: new (within-block state, not cross-block or cross-sample)

Distinct scope from #22/#23 (which fold in every prior block) and from
#16/#17/#21 (which are about the *previous* block or *previous step's*
confidence values): this counts how many times the corrector has *already*
fired earlier in the *current* block, before this step's decision. The
`while True` step loop at `generate.py:183` can invoke the corrector more
than once per block (every `apply_corrector_every_n_steps`-th step, or per
whatever the adaptive policy decides) before `block_idx` advances, so this
is a real, currently-undifferentiated situation: two invocation
opportunities with identical predictor-confidence features can be a
block's first correction attempt or its fourth, and the frozen five-feature
set treats them identically.

Motivation: a block that has already been corrected twice this block and
is still showing low-confidence active positions is a different situation
from a block seeing its first invocation opportunity — plausibly evidence
that this block is intrinsically harder (repeated correction not fully
resolving it) or, conversely, that the marginal value of yet another
corrector pass is dropping (diminishing returns already visible in this
block's own trajectory). Cold-start / cheapest of the three to implement
live: unlike #22/#23, this needs no historical outcome data at all, just a
counter reset to `0` at the top of each `block_idx` iteration and
incremented each time `invoke_corrector` is `True` — no `n_active_*` or
`corrector_break_step` bookkeeping required, so it's implementable as a
live-hook change independent of whether #22/#23 ever land.

### Updated running priority (24 ideas total across eight passes)

Trainable-today tier unchanged from pass 7 (all live-hook features, #22-#24
included, sit in the new-instrumentation tier below since none are
computable from the frozen inline hook without cross-invocation state):
**#10 ≈ #15 ≈ #3 ≈ #8** → **#19 ≈ #20** → **#13** → **#11** → **#12** →
**#14** → **#9** → **#2** → **#1**. New-instrumentation tier, #24 added at
the cheap end (counter-only, no outcome bookkeeping) and #22/#23 added
near #2 (same causal cumulative-mean shape, same live-hook cost):
**#24** → **#16 ≈ #17** → **#2 ≈ #22 ≈ #23** (same implementation cost
tier; priority among these three is a modeling question — which of
agreement/magnitude/effort has the most signal — not an implementation
one) → **#21** → **block-position variant** (still lowest, documented
overfit history). **#18** still sits outside this ordering pending Lucas's
fairness-question call from pass 6.

**Next fire on Track C**, if routing lands here again: the corrector-side
history category opened this pass (#22-#24) has three entries now: either
go deeper there (e.g. a feature combining magnitude and effort, or a
recency-weighted/exponential-decay variant of #2/#22/#23 instead of the
flat historical mean all three currently use) or check whether any pass
has considered features derived from the *predicted token identities*
themselves (not just confidence/entropy over the distribution) — e.g.
whether low-confidence active positions disproportionately fall on
numeric/operator tokens in GSM8K vs. identifier/keyword tokens in
HumanEval — which would need a tokenizer-decode step no current feature
uses and is a genuinely different feasibility tier from everything listed
so far.


## 2026-08-25 — Track C, ninth pass: recency-weighted corrector history, and predicted-token lexical category

Track A stayed `EGRESS_BLOCKED` this fire (11/11 consecutive fresh probes,
`arxiv.org/list/cs.LG/recent`, identical error shape — see
`L1_LITERATURE.md`'s matching entry, no re-notify per standing guidance;
Lucas was already told once at the 3/3 mark). Routing: among the four
track files, `L1_FEATURE_IDEAS.md` was the oldest genuinely-touched of
B/C/D (00:26 UTC 08-25, vs. `MEMO_V4_SKELETON.md`'s 02:26 and
`L1_AUDIT_FINDINGS.md`'s 04:27), so Track C routes per the established
fallback rule.

Picking up the two open threads pass 8 flagged rather than re-deriving a
ninth moment/shape statistic of `t` or `e`: (a) a recency-weighted variant
of the flat-historical-mean features (#2, #22, #23), and (b) whether the
*identity* of predicted tokens — not just confidence/entropy over the
distribution — carries signal, which no prior pass has touched since it
needs a tokenizer-decode step none of #1-#24 require.

### 25. Exponential-decay-weighted variant of agreement/magnitude/effort history (`agreement_rate_ewm`, `correction_magnitude_ewm`) — cheap extension of #2/#22, category: (2)

#2, #22, and #23 all fold a sample's prior corrector invocations into a
**flat** mean — block 1 and block 19 (for a sample currently on block 20)
count equally. That's a real modeling choice, not a neutral default: if a
sample's corrector behavior drifts over the generation (e.g. gets easier
as more context accumulates, or harder as compounding errors build up),
a flat mean lags behind the sample's *current* regime by construction,
weighted down by however many early blocks happened to look like.

Proposed: replace (or add alongside, for an ablation) `agreement_rate_so_far`
and `correction_magnitude_mean_so_far` with exponentially-weighted versions
— `agreement_rate_ewm = Σ λ^(k-1) · broke_at_step_1_k` over prior
invocations k=1..n (most recent invocation weighted highest), normalized by
`Σ λ^(k-1)`, same cold-start convention as #2 (1.0) when n=0. Identical
causal-ordering discipline as #2/#22/#23 (`block_idx' < block_idx` only —
same leakage guard already fixed once in `a796b4f`/`phase_b_pilot.py`).

**This is not free of new researcher degrees of freedom, unlike most of
passes 3-5's ideas:** λ (the decay rate) is an open hyperparameter, same
class of concern as #9's τ and #13's k — worth sweeping a small grid
(e.g. λ ∈ {0.5, 0.7, 0.9}, flat-mean as the λ→1 limit) rather than picking
one value and reporting only that AUC. Recommend evaluating this **only
after** #2/#22/#23 themselves have been tried and shown some signal in
their flat form — if the flat versions add nothing, a recency-weighted
version of a signal that isn't there is unlikely to help and isn't worth
the extra hyperparameter surface. Flagging this ordering explicitly since
it's a refinement of unvalidated ideas, not a validated one.

### 26. Lexical/syntactic category of low-confidence active positions' predicted tokens (`low_conf_numeric_frac_active`, benchmark-conditional) — new feasibility tier, needs tokenizer decode

Every one of #1-#25 is a function of the predictor's **probability
distribution** at each active position — none look at **which token** the
distribution's mass actually sits on. `l1_policy.py`'s
`features_from_predictor_logits` has `top1` (a probability) but discards
the corresponding token ids after computing it; recovering "what token is
this" needs `pp.argmax(dim=-1)` (already implicitly computed to get
`top1`, just not retained) decoded through the tokenizer already loaded
elsewhere in `generate.py`.

Motivation, grounded in the benchmark split already central to Phase A's
own headline result (dAUC +0.019 GSM8K / +0.033 HumanEval / +0.027
combined — the two benchmarks already behave differently enough to report
separately): GSM8K's hard positions are plausibly concentrated on numeric
tokens (a wrong digit or operator changes the answer) while HumanEval's
are plausibly concentrated on identifier/keyword/punctuation tokens (a
wrong variable name or bracket breaks the program differently than a wrong
digit changes an equation). A feature like
`low_conf_numeric_frac_active` (fraction of below-median-confidence active
positions whose top-1 token decodes to a numeric-looking string) could let
one MLP implicitly specialize its correction-worthiness read by *what kind*
of token is uncertain, rather than only *how* uncertain — something no
confidence/entropy/margin/moment statistic in #1-#25 can express, since
all of them are computed purely from `pp`'s shape and are blind to which
vocabulary entries the mass sits on.

**Why this is a different feasibility tier than everything else in this
file, including the new-instrumentation ideas (#1, #16/#17, #21-#24):**
those all need new *state* (cross-invocation counters, prior-step tensors)
but reuse data already flowing through the existing pipeline. This needs a
**tokenizer-decode step in the hot path** (or at training time over logged
token ids, if `s1/runs/*.jsonl` records the top-1 token id per position —
not confirmed this pass, flagged for whoever picks this up to check
against the actual JSONL schema before assuming it's free) plus a
category taxonomy (numeric / identifier / keyword / punctuation / other)
that itself needs deciding and is benchmark-specific by construction —
GSM8K and HumanEval don't share a natural token-category distribution, so
this feature's usefulness (if any) is likely to look different by
benchmark in exactly the way the frozen five features currently don't
attempt to be, which cuts both ways: possibly higher marginal AUC on the
per-benchmark breakdown Phase A already reports, but also a new axis
(category taxonomy choice) for the small-N overfitting risk
`PHASE_B_L1_DESIGN.md` already flags for position-based features (see
pass 2's block-position entry) to attach to.

**Recommendation:** lowest priority to actually build of anything in this
file — highest implementation cost (tokenizer wiring + taxonomy design),
least certain payoff, and the one idea here that could plausibly need a
*new* S1 collection pass even to explore offline if token ids aren't
already logged. Worth a five-minute check of the JSONL schema before the
next pass proposes anything token-identity-adjacent, rather than a full
design — flagging the direction, not committing to it.

### Updated running priority (26 ideas total across nine passes)

No change to the trainable-today or new-instrumentation tiers from pass 8;
#25 slots in as a refinement *gated on* #2/#22/#23 showing signal first
(not before them), and #26 opens a new, currently-unranked tier below
everything else (tokenizer-decode + taxonomy cost, payoff unconfirmed):
**#10 ≈ #15 ≈ #3 ≈ #8** → **#19 ≈ #20** → **#13** → **#11** → **#12** →
**#14** → **#9** → **#2** → **#1**. New-instrumentation tier: **#24** →
**#16 ≈ #17** → **#2 ≈ #22 ≈ #23** → **#25 (only after #2/#22/#23
validated)** → **#21** → **block-position variant** (still lowest among
the ranked tiers, documented overfit history). **#26** sits in its own
unranked tier pending a JSONL-schema check for token-id availability.
**#18** still sits outside this ordering pending Lucas's fairness-question
call from pass 6.

No implementation done here per the routine brief — this file stays
proposals-only.

**Next fire on Track C**, if routing lands here again: check whether
`s1/runs/*.jsonl` logs a top-1 token id per position (settles #26's actual
cost) before proposing further token-identity features; otherwise, #25's
λ-sweep framing is the most actionable open item without new data.


## 2026-08-25 — Track C, tenth pass: settling #26's cost, and one new rank-based feature

### JSONL/token-id schema check (settles #26's open question from pass 9)

Read `llada/generate.py`'s `s1_log` construction directly (the `rec` dict built
at the corrector-invocation log site, plus the `s1_predictor_conf` dict merged
into it). Confirmed: **no token ids are logged anywhere in S1's data path**.
The fields written are `block_idx`, `step_in_block`, `corrector_break_step`,
`hit_max`, `broke_at_step_1`, `active_mask_size`,
`n_active_positions_changed_by_corrector`, plus the eight
`predictor_conf_*`/`predictor_entropy_*` scalars — all derived from `pp`
(the softmax) via `.max()`/`.std()`/`.mean()`/etc., never from
`pp.argmax(dim=-1)` itself. `s1_pre_argmax` and the corrector's
`corrected_tokens` tensor both hold real token ids in memory at generation
time but neither is written to `rec`.

This confirms pass 9's flag rather than resolving it favorably: **#26 is not
free**. It needs a new S1 collection pass (add
`pre_correction_argmax_tokens_on_active` — already named as a *docstring*
promise in `generate()`'s S1 INSTRUMENTATION section but never actually
written into `rec` in the current code, a second small gap worth noting to
whoever owns Track B) before it can be explored offline at all, on top of the
tokenizer-decode + taxonomy design cost pass 9 already flagged. Demoting #26
to blocked-on-instrumentation rather than merely low-priority.

### 27. Predictor confidence RANK within block (`predictor_conf_rank_mean_active`, `predictor_conf_rank_min_active`) — cheap, category (1), rank-based rather than magnitude-based

Every one of #1-#26's confidence-shape statistics (#1's own mean/min/std,
#10-#15, #19-#20) operates on the **raw magnitude** of `top1` — the actual
softmax probability values. None of them are **rank-based**: where does each
active position's confidence sit in the sorted order of confidences across
the block, independent of the absolute scale?

Concretely: `ranks = pp_top1_active.argsort().argsort() / (n_active - 1)`
(percentile rank in `[0, 1]`, ties broken arbitrarily — cheap, one extra
`argsort` over a vector already in hand as `t = top1[am]` in
`features_from_predictor_logits`). Then aggregate the same way as the
existing mean/min features: `predictor_conf_rank_mean_active` (how central is
the average active position, rank-wise — near 0.5 means a block with no
clear ordering, near 0 or 1 means most positions cluster at one end of their
own block's distribution) and `predictor_conf_rank_min_active` (is the
worst-confidence position an outlier within *this block* specifically, vs.
`predictor_conf_min_active`, which says how low it is in absolute terms with
no reference to the rest of the block).

Motivation: `predictor_conf_mean_active` and `predictor_conf_std_active`
already capture the block's confidence *distribution*, but a block-level
mean/std pair is scale-dependent — two blocks with the same rank structure
(one clear outlier low-confidence position among otherwise-uniform high
confidence) can have very different `mean_active`/`std_active` values
depending on the block's overall calibration level (which the corrector
policy has no way to distinguish from those two scalars alone). A rank
feature is invariant to that overall level and asks a different question:
not "how confident is this block" but "how does this position's confidence
compare to its own block's other active positions" — closer to the flip-rate
framing in #16/#17 (relative to the block's own history) than to any of
#1-#26's absolute-magnitude family. This was one of the explicit motivations
in the routine's own candidate list ("predictor confidence RANK within
block") and, on inspection, is not covered by anything logged so far.

Cost: cheapest tier — reuses `t = top1[am]` already computed in
`features_from_predictor_logits`, one extra `argsort` call, no new
instrumentation, no tokenizer, no cross-invocation state. Same feasibility
tier as #10/#15/#3/#8.

Caveat carried over from #10-#15: another shape statistic added to an
already-5-feature-frozen set risks the same small-N overfitting
`PHASE_B_L1_DESIGN.md` flags for position features — this is a proposal for
the *next* retraining round after Phase B lands real invocation counts, not
a request to unfreeze `FEATURE_KEYS` now.

### Updated running priority (27 ideas total across ten passes)

#27 slots into the cheapest trainable-today tier alongside #10/#15/#3/#8 —
same feasibility class, and the pass-9 note above means it should be
evaluated together with that group rather than ahead of it, since none of
that tier has been validated against Phase B data yet:
**#10 ≈ #15 ≈ #3 ≈ #8 ≈ #27** → **#19 ≈ #20** → **#13** → **#11** → **#12** →
**#14** → **#9** → **#2** → **#1**. New-instrumentation tier unchanged from
pass 9: **#24** → **#16 ≈ #17** → **#2 ≈ #22 ≈ #23** → **#25 (only after
#2/#22/#23 validated)** → **#21** → **block-position variant** (lowest,
documented overfit history). **#26** moves from "unranked, cost unconfirmed"
to **blocked on new S1 instrumentation** (confirmed this pass — see above)
and stays out of the ranking until that lands. **#18** still sits outside
this ordering pending Lucas's fairness-question call from pass 6.

No implementation done here per the routine brief — this file stays
proposals-only.

**Next fire on Track C**, if routing lands here again: #25's λ-sweep framing
(decay constant choices for the EWM variants of agreement rate / correction
magnitude / effort) is the most actionable open item without new data or new
code, now that #26 is confirmed blocked rather than merely deprioritized.
Also worth a short note to whoever next touches `generate.py` (Track B, most
likely): the docstring for `s1_log` already promises
`pre_correction_argmax_tokens_on_active` / `post_correction_tokens_on_active`
keys that pass 9 and this pass both found are not actually written into
`rec` — either the docstring is stale or the write was dropped; worth
confirming which before anyone builds #26 assuming the docstring is current.

---

## 2026-08-25 — Track C, eleventh pass: triage note, plus two combination features

Ten passes, 27 proposed features, zero implemented (by design — this track
is proposal-only). That ratio is worth naming plainly before adding more:
every single-invocation statistical shape of `t`/`e`/`pp` that's cheap to
compute (mean/min/std/skew/kurtosis, margin, rank, pooled/top-k/KL entropy,
spatial autocorrelation) now has an entry, and most of the remaining
unexplored ground (#1, #16/#17, #21, #26) is gated on new S1 instrumentation
that hasn't landed. Generating a 28th single-array statistic from that same
well is low marginal value relative to what Phase B's pilot data will
actually need once it lands: a validated pick from the existing list, not a
longer list. Recording that read here rather than manufacturing another
moment statistic to hit a quota.

**If Lucas is looking for where to start once pilot data lands:** the
cheapest-and-most-orthogonal tier (**#10, #15, #3, #8, #27, #19, #20** — all
one-`torch`-call, no new instrumentation, no threshold) is the obvious first
ablation batch precisely because it's free to compute against v2/v3 JSONL
already collected — no reason to wait for a new S1 run to at least measure
whether any of these seven move AUC before spending effort on the
instrumentation-gated tier (#1/#16/#17/#21/#22/#23/#24/#25/#26).

Two proposals this pass, both explicit **combinations of already-proposed
features** rather than new raw statistics — a different kind of idea than
passes 1-10, motivated by the AUC-ceiling framing in the routine brief: with
a small hidden layer (5→16→1) and Phase B's still-modest N, an MLP may not
reliably discover a useful nonlinear combination of two flat features on its
own; handing it a pre-computed interaction can be more sample-efficient than
hoping two separate scalars let it find the same relationship.

### 28. Correction magnitude per unit effort, sample-so-far (`correction_magnitude_per_effort_so_far`) — combination of #22 and #23, cheap, category (2)

`correction_magnitude_mean_so_far` (#22) and `correction_effort_mean_so_far`
(#23) are proposed separately in pass 8 as two raw scalars the MLP would
receive independently. Proposed: also compute their ratio,
`#22 / max(#23, 1.0)` — "how much does the corrector change per iteration it
spends," a single number distinguishing "efficient large rewrites" (high
magnitude, low effort) from "slow grinding toward a small fix" (low
magnitude, high effort) without requiring the MLP to learn that division
from two inputs and a small hidden layer. Cold-start: `0.0`, consistent with
#22's cold-start (no assumed magnitude with no evidence). Same live-hook
cost tier as #22/#23 — not a new state requirement, a post-hoc combination
if both are already being tracked.

**Caveat:** only worth adding once #22 and #23 are themselves validated
individually (same ordering discipline pass 9 already applied to #25) —
proposing a ratio of two unvalidated signals compounds an unproven
hypothesis rather than testing a new one.

### 29. Within-block confidence trend since block start (`predictor_conf_trend_since_block_start`) — new but narrow-scope temporal signal, category: new (temporal), cheaper state than #16/#17

Distinct from #16/#17 (step-to-step delta, needs the *previous step's* full
tensor retained) and from #21 (previous *block's* final value): this
compares the current step's `predictor_conf_mean_active` against the value
recorded at this block's *first* predictor step, i.e. a single scalar
(`first_step_conf_mean`) held for the duration of one block's `while` loop,
reset at each new `block_idx` — cheaper state to carry than #16/#17's
full previous-step tensor, since only one number needs to survive across
steps. `predictor_conf_trend_since_block_start = current_mean -
first_step_conf_mean` (positive = block has gotten more confident since it
started, negative = degrading). First step of a block: `0.0` (no trend yet),
same convention as #16.

Motivation: distinguishes "this block started hard and is still hard"
(trend ≈ 0, low absolute confidence) from "this block started hard but is
resolving on its own" (trend positive, low absolute confidence) — the
frozen five features and #1-#28 can express *that* a block is currently
low-confidence but not *whether* it's already trending toward resolution
without correction, which is a different question from #16/#17's per-step
noise-vs-signal framing (this is block-scoped drift, not step-scoped
volatility). Same instrumentation tier as #16/#17/#21/#24 (needs a new S1
per-step logging change to train on, not just live-hook state) — not free,
flagged consistently with how #16/#17 were flagged in pass 6.

### Updated running priority (29 ideas total across eleven passes)

No change to the trainable-today or new-instrumentation tiers' relative
order; #28 and #29 slot in as follows. Trainable-today tier unchanged:
**#10 ≈ #15 ≈ #3 ≈ #8 ≈ #27** → **#19 ≈ #20** → **#13** → **#11** → **#12** →
**#14** → **#9** → **#2** → **#1**. New-instrumentation tier: **#24** →
**#16 ≈ #17 ≈ #29** (same live-hook/S1-logging cost as #16/#17, #29 slightly
cheaper in state size) → **#2 ≈ #22 ≈ #23** → **#28 (only after #22/#23
validated)** → **#25 (only after #2/#22/#23 validated)** → **#21** →
**block-position variant** (lowest, documented overfit history). **#26**
stays blocked on new S1 instrumentation. **#18** stays outside this ordering
pending Lucas's fairness-question call from pass 6.

No implementation done here per the routine brief — this file stays
proposals-only.

**Next fire on Track C**, if routing lands here again: recommend triage over
further generation — check whether Phase B pilot data has landed
(`v2.jsonl`/pilot output referenced in `MEMO_V4_SKELETON.md`'s tracked
status) and, if so, this track's highest-value next action is validating
the trainable-today tier against it, not proposing idea #30.

---

## 2026-09-03 02:2x UTC — Track C, twelfth pass: triage re-check, no data yet, no new idea

Routed here by the routine's own selection rule (`L1_FEATURE_IDEAS.md` is the
oldest-touched of the four track files, last substantive entry 2026-08-25).
Directly answering pass eleven's own "next fire" question from a fresh
independent check rather than assuming the answer still holds: re-listed
`s1/runs/` and searched the full tree for `phase_b/` or `*.jsonl` outside
`s1/runs/` — still tops out at `gsm8k_20260813_045034.jsonl` /
`humaneval_20260813_045034.jsonl` (2026-08-13), no `phase_b/` directory, no
`v2.jsonl`, no `pilot.jsonl` anywhere in the repo tree. Pilot data has not
landed, ~21 days after the newest s1 run and ~11 days since
`PHASE_B_PREREG_2026-08-22.md` locked the v2 protocol.

Per pass eleven's own reasoning — 29 ideas across eleven passes already cover
every cheap single-array statistic of `top1`/`entropy`/`pp`, including all
four motivations this routine's own prompt template lists as candidates
(#1 confidence rank within block, #2 predictor-corrector agreement rate,
#3 pooled vocabulary entropy, and block-position-relative-to-EOS from the
second pass) — manufacturing a 30th untested statistic against that same
well is still lower value than what's actually blocking: a validated pick
from the existing trainable-today tier (**#10 ≈ #15 ≈ #3 ≈ #8 ≈ #27** →
**#19 ≈ #20** → ...) once real invocation data exists to validate against.
That reasoning hasn't changed since pass eleven, so this pass doesn't
re-litigate it or add a 30th entry to satisfy a quota — declining to
generate is the deliberate output here, not an omission.

No implementation done, no new idea added. Ranking and tiers unchanged from
pass eleven. Priority list stands at 29 ideas / eleven passes.

**Next fire on Track C**, if routing lands here again: same check — has
`s1/runs/` gained a new file, or has a `phase_b/`/`v2.jsonl` appeared
anywhere in the tree? If yes, that's the trigger to start validating the
trainable-today tier (`#10/#15/#3/#8/#27/#19/#20`) against real data instead
of continuing to triage-and-wait.

(Stray duplicate fragment trailing this section in a prior pass's edit
removed here — no content change, just a leftover half-sentence cleaned up.)

---

## 2026-09-03 10:2x UTC — Track C, thirteenth pass: triage re-check, no data yet, no new idea

Routed here by the routine's own selection rule (`L1_FEATURE_IDEAS.md` last
substantive touch 2026-09-03 02:26 UTC pass 12, oldest of the four track
files by fresh commit-timestamp check versus Track B 04:26, Track A 06:27,
Track D 08:26 — all today). Re-ran pass twelve's own check from a fresh
clone rather than trusting the prior pass's conclusion: full-tree search for
`phase_b/`, `v2.jsonl`, `pilot.jsonl` and a direct `s1/runs/` listing both
confirm the same 15 files topping out at `gsm8k_20260813_045034.jsonl` /
`humaneval_20260813_045034.jsonl` (2026-08-13) — no new run, no pilot
output. Pilot data still hasn't landed, ~21 days after the newest s1 run.

Pass eleven's saturation reasoning still holds on review — 29 ideas across
eleven passes already cover all four of this routine's own candidate
feature motivations (confidence rank within block, predictor-corrector
agreement rate, pooled vocabulary entropy, block-position-relative-to-EOS).
Nothing about this pass's re-check changes that; declined to manufacture
idea #30 again rather than pad the file to look busy. No implementation
done, no new idea added, ranking and tiers unchanged from pass eleven.

Cross-checked the other three tracks briefly before closing out this pass:
Track A — live WebFetch to `arxiv.org/list/cs.LG/recent` returned
`EGRESS_BLOCKED`, unchanged since 08-19. Track B — `l1_policy.py` /
`l1_training.py` / `l1_weights.json` / `llada/generate.py` /
`PHASE_B_L1_DESIGN.md` still `185e2ca` (2026-08-19); `phase_b_pilot.py` /
`phase_b_evaluate.py` still `b0b1b8d`; `PHASE_B_PREREG_2026-08-22.md` still
`a796b4f` — findings #1-14 stand. Track D — fresh clone of
`remasking_test:research-ideation`, HEAD unchanged at `76c7948`
(2026-09-02 13:48 UTC) — nothing newer to fold.

No PushNotification this fire — both structural blockers (egress proxy,
EC2 pilot stall) are unchanged from the single escalation already sent
2026-08-29 02:2x UTC, now ~152h / 6.3 days ago; nothing new occurred this
cycle to justify a re-flag.

**Next fire on Track C**, if routing lands here again: same check — has
`s1/runs/` gained a new file, or has a `phase_b/`/`v2.jsonl` appeared
anywhere in the tree? That remains the sole trigger to start validating the
trainable-today tier (`#10/#15/#3/#8/#27/#19/#20`) against real data instead
of continuing to triage-and-wait.
