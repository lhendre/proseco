# MEMO_V4_SKELETON.md — fill-in template for the Phase B v2 decisive-run memo

Drafted 2026-08-23 by the L1 research-iteration bot (Track D). Source: `MEMO_L1_REV4.html`
(pilot-stage memo, still accurate for Sections 1-2) + `PHASE_B_PREREG_2026-08-22.md`
(locked criteria, copied verbatim below) + `phase_b_evaluate.py` (exact output columns
this table maps to). `phase_b/v2.jsonl` was "in flight" as of the last commit that
touched this repo — check whether it has landed before using this.

Re-checked 2026-08-23 ~18:25 UTC (Track D pass 4): `phase_b/v2.jsonl` still hasn't landed in this
repo (no `phase_b/` directory present) — EC2 run status not visible from here, Lucas drives that
side directly per the routine brief. Re-fetched `MEMO_L1_REV4.html` and `LANDSCAPE.md`; no changes
to Sections 1-2 source material or the Gate-8 competitor count (still 10). One non-Kuleshov paper
(SchED, 2512.02892) had its authorship attribution corrected on `research-ideation` this same day
(was wrongly flagged Kuleshov-authored 08-21, corrected non-Kuleshov 08-23) — it's a global
sequence-level halting mechanism, not part of L1's pre-commit-eligibility competitor cluster or its
shape-vs-scalar precedent cluster, so no change needed to the related-work paragraph below. Also
folded in 4 newer `L1_AUDIT_FINDINGS.md` entries (#4-#7) into the "Known caveats" list in Section 3
below — #6 in particular affects the `l1_mlp:0.40` weights this run is testing and should be
resolved before trusting that row.

Re-checked 2026-08-24 ~06:26 UTC (Track D pass 5, routed here after Track A's 5th consecutive
`EGRESS_BLOCKED`): `v2.jsonl` still hasn't landed anywhere in the tree (checked `phase_b/` and
`s1/runs/` — only the same stale pre-v2 `s1/runs/*.jsonl` files as last pass, no new files). Did
not re-fetch `MEMO_L1_REV4.html`/`LANDSCAPE.md` this pass (no network-derived delta to check them
against, same reasoning as the prior no-op re-checks). Folded in `L1_AUDIT_FINDINGS.md` finding
#9 (logged this fire, commit `47404b5`) into the caveats list below — flagged MEDIUM but, like
#6, it's a fairness confound (not policy-neutral) rather than a simple accuracy bug, so it's
placed near the top of the list rather than with the policy-neutral findings.

Re-checked 2026-08-24 ~14:2x UTC (Track D pass 6): `v2.jsonl` still hasn't landed anywhere in the
tree (`phase_b/` still absent, `s1/runs/` unchanged since last pass). Re-cloned
`remasking_test:research-ideation/LANDSCAPE.md` — most recent entry (commit `8a56216`, logging
dLLM-Cache/DyLLM as a systems/caching BG paper) is not part of L1's pre-commit-eligibility or
shape-vs-scalar-precedent clusters, so the Gate-8 competitor count (10) and the related-work
paragraph below are still unchanged. Folded in `L1_AUDIT_FINDINGS.md` finding #10 (logged fire
N+5, commit `e5c7254`) into the caveats list below, placed above #9 — it's higher-severity
(MEDIUM/HIGH vs. MEDIUM) and, unlike #9, potentially affects the deployed `l1_mlp:0.40` weights
themselves rather than just the HumanEval scoring path.

Re-checked 2026-08-24 ~20:2x UTC (Track D pass 7, longest-stale track this fire — Track D last
touched 14:26 vs. Track B 16:27 and Track A/C 18:26): `v2.jsonl` still hasn't landed — `phase_b/`
absent, `s1/runs/` unchanged (same 15 pre-Phase-B `.jsonl` files + `s1_verdict.png` as every prior
pass). This pass actually fetched `MEMO_L1_REV4.html`'s canonical source
(`https://claude.ai/code/artifact/de1f873d-060f-4956-bffa-b6f36d37fe33`, works over this sandbox's
egress even though `arxiv.org` doesn't — Track A's 7 consecutive `EGRESS_BLOCKED` results are
apparently host-specific, not a blanket network failure) and confirmed it's byte-identical to the
local `MEMO_L1_REV4.html` (still rev. 4, dated 2026-08-16, same pilot table) — no Section 1/2 text
changes needed. Re-fetched `remasking_test:research-ideation/LANDSCAPE.md`'s recent history — HEAD
is still commit `8a56216` (same as pass 6, no new commits since), so the Gate-8 competitor count
(10) and the related-work paragraph are unchanged again. Folded `L1_AUDIT_FINDINGS.md` finding #11
(logged fire N+6, commit `f9e72d6`) into the caveats list below, placed above #4 — it's a
methodology gap in the *training-time* AUC number itself (same class as #4, both undermine trust
in "0.9589 matches Phase A ceiling") rather than a Phase B pilot/eval bug.

Re-checked 2026-08-25 ~02:2x UTC (Track D pass 8, oldest-touched of B/C/D this fire — Track A
routed here again per its own 10th consecutive `EGRESS_BLOCKED`, see `L1_LITERATURE.md`):
`v2.jsonl` still hasn't landed — `phase_b/` absent, `s1/runs/` byte-count and filenames unchanged
from every prior pass. Re-fetched `MEMO_L1_REV4.html` via the Artifact read path (not WebFetch —
confirmed byte-identical modulo the frame-wrapper's trailing `</body></html>`, diffed the two
files directly rather than eyeballing) — still no Section 1/2 changes needed. Re-pulled
`remasking_test:research-ideation/LANDSCAPE.md` — HEAD still `8a56216` (unchanged since pass 6),
`grep -c` on the literal Gate-8 cluster string still returns 10 — related-work paragraph unchanged
again. Folded `L1_AUDIT_FINDINGS.md` finding #12 (logged fire N+7, commit `c271205`) into the
caveats list below, placed at the bottom near #8 — like #8 it's currently a no-op (the two feature
formulas agree today, verified term-by-term by the audit pass) rather than a bug affecting any
number in this memo, but worth carrying forward as a fragility note.

Re-checked 2026-08-25 ~08:2x UTC (Track D pass 9, oldest-touched of B/C/D this fire — Track D last
touched 02:26 vs. Track B 04:27 and Track A/C 06:32; Track A's 11th consecutive `EGRESS_BLOCKED`
routed here, see `L1_LITERATURE.md`): `v2.jsonl` still hasn't landed — `phase_b/` absent from the
repo root (only `phase_b_evaluate.py`/`phase_b_pilot.py`/`PHASE_B_L1_DESIGN.md`/
`PHASE_B_PREREG_2026-08-22.md` are tracked there), `s1/runs/` unchanged (same 6 gsm8k + 6
humaneval files + `s1_verdict.png` as every prior pass). Re-fetched `MEMO_L1_REV4.html` via the
Artifact read path and diffed against the local copy — still byte-identical (rev. 4, dated
2026-08-16, same pilot table, same provenance block referencing `phase_b/v2.jsonl` as "in flight");
no Section 1/2 text changes needed. Re-cloned `remasking_test:research-ideation/LANDSCAPE.md` —
HEAD is now `8a56216` (one new commit since pass 8, logging dLLM-Cache/DyLLM as a systems/caching
background paper), grep-confirmed not part of L1's pre-commit-eligibility cluster (still
CadLLM/AdaBlock-dLLM/DepCap/Dynamic-dLLM/Apple/KLASS/TraceLock/LESS/SWD/CORA-Diff, 10 entries) or
the shape-vs-scalar precedent cluster — Gate-8 competitor count and the related-work paragraph
below are unchanged again. Folded `L1_AUDIT_FINDINGS.md` finding #13 (logged fire N+8, commit
`c65d8e1`) into the caveats list below, placed near #8/#12 — it's a crash-recovery/availability gap
in `phase_b_pilot.py`'s resume path (unhandled `JSONDecodeError` on a truncated trailing line after
a mid-write kill), not a silent-wrong-number bug, so it doesn't affect any number in this memo's
tables unless the EC2 run has actually been interrupted mid-write (unknown from here — Lucas drives
that side directly).

**How to fill this in (<30 min):**
1. `python phase_b_evaluate.py ~/proseco/phase_b/v2.jsonl` on the EC2 box (or wherever
   `v2.jsonl` lives once the run completes).
2. Copy the "Raw accuracy + NFE" rows into Table V2-1 below (one row per policy x benchmark).
3. Copy the PRIMARY and SECONDARY comparison lines into Table V2-2 and the verdict line
   into the `{{VERDICT}}` slot.
4. Swap `{{...}}` placeholders in Sections 1-2 for real numbers where noted (most of
   Sections 1-2 can be copied unchanged from `MEMO_L1_REV4.html` — only the pilot-stage
   caveats in Section 3 need replacing with the v2 numbers).
5. Re-check `related-work` paragraph below against `remasking_test:research-ideation/LANDSCAPE.md`
   for any new Gate-8-relevant entries added since this skeleton was drafted (2026-08-23) —
   do not paste it in unchanged if the landscape has moved.

---

## Header / status pills

- Title: "L1 — a learned skip policy for ProSeCo's corrector"
- Eyebrow: "Collaboration proposal · rev. 4" (or bump to rev. 5 if rev. 4 was already sent to Yair)
- Status pills: `Phase A: signal certified on 22k held-out invocations` (unchanged) /
  `Phase B decisive run: {{PASS|AMBIGUOUS|KILL}}` (replaces the pilot's "trending, undersized" pill) /
  `Ask: {{updated ask — may collapse to "paper floor" language if AMBIGUOUS/KILL, or "A100 scale-up + MBPP/MATH" if PASS}}`

## TL;DR (rewrite, don't reuse verbatim — the claim strength changes with the verdict)

- If PASS: lead with the certified accuracy win, matched-NFE, CI lower bound above zero.
- If AMBIGUOUS: lead with Phase A certification (unchanged, still true) + "task-level signal still
  trending but CI straddles zero at N={{n_gsm8k}}/{{n_humaneval}} single-seed; A100 multi-seed run
  requested to resolve" — this is the pre-committed AMBIGUOUS path, not a downgrade to hide.
- If KILL: lead with the honest kill — do not bury it. Cite the exact CI upper bound that fired
  the kill trigger. Pivot statement goes here (diagnostic-signal-only paper, per Section 5 below).

## Section 1 — The idea, precisely

Copy unchanged from `MEMO_L1_REV4.html`. This section describes the mechanism (5-feature MLP,
shape-vs-mean argument) and does not depend on Phase B v2's outcome.

## Section 2 — Phase A: the signal is real, certified on 23k held-out invocations

Copy the existing table unchanged (ΔAUC +0.019 GSM8K / +0.033 HumanEval / +0.027 combined,
95% CI, P(moat≤0)=0.000 on all three). This result does not change between pilot and v2 — it's
upstream of both.

## Section 3 — Phase B decisive run (REPLACES the pilot table)

Delete the pilot-stage table and its "deliberately underpowered" framing entirely — this section
now reports the pre-registered N=100(GSM8K)/N=64(HumanEval) run, not the N=40 pilot.

**Table V2-1 — Raw accuracy + NFE per policy x benchmark**
(maps 1:1 to `phase_b_evaluate.py`'s "Raw accuracy + NFE" printout)

| Policy | Benchmark | n | Accuracy | Mean NFE | Median NFE |
|---|---|---|---|---|---|
| fixed | gsm8k | {{n}} | {{acc}} | {{mean_nfe}} | {{med_nfe}} |
| cadllm_linear:0.15 | gsm8k | {{n}} | {{acc}} | {{mean_nfe}} | {{med_nfe}} |
| cadllm_linear:0.20 | gsm8k | {{n}} | {{acc}} | {{mean_nfe}} | {{med_nfe}} |
| cadllm_linear:0.25 | gsm8k | {{n}} | {{acc}} | {{mean_nfe}} | {{med_nfe}} |
| l1_mlp:0.40 | gsm8k | {{n}} | {{acc}} | {{mean_nfe}} | {{med_nfe}} |
| fixed | humaneval | {{n}} | {{acc}} | {{mean_nfe}} | {{med_nfe}} |
| cadllm_linear:0.15 | humaneval | {{n}} | {{acc}} | {{mean_nfe}} | {{med_nfe}} |
| cadllm_linear:0.20 | humaneval | {{n}} | {{acc}} | {{mean_nfe}} | {{med_nfe}} |
| cadllm_linear:0.25 | humaneval | {{n}} | {{acc}} | {{mean_nfe}} | {{med_nfe}} |
| l1_mlp:0.40 | humaneval | {{n}} | {{acc}} | {{mean_nfe}} | {{med_nfe}} |

**Table V2-2 — Pre-registered comparisons**
(maps to the "PRIMARY"/"SECONDARY" printout lines)

| Benchmark | Comparison | NFE-matched policy | Δacc | 95% CI | P(Δ≤0) | n_paired | Result |
|---|---|---|---|---|---|---|---|
| gsm8k | PRIMARY: l1_mlp:0.40 vs matched CadLLM | {{matched}} | {{delta}} | [{{lo}}, {{hi}}] | {{p_le0}} | {{n}} | {{PASS/AMBIGUOUS}} |
| gsm8k | SECONDARY: l1_mlp:0.40 vs fixed | fixed | {{delta}} | [{{lo}}, {{hi}}] | {{p_le0}} | {{n}} | {{KILL / not killed}} |
| humaneval | PRIMARY: l1_mlp:0.40 vs matched CadLLM | {{matched}} | {{delta}} | [{{lo}}, {{hi}}] | {{p_le0}} | {{n}} | {{PASS/AMBIGUOUS}} |
| humaneval | SECONDARY: l1_mlp:0.40 vs fixed | fixed | {{delta}} | [{{lo}}, {{hi}}] | {{p_le0}} | {{n}} | {{KILL / not killed}} |

**Overall verdict:** `{{VERDICT}}` — paste the exact "=== VERDICT ===" block text from
`phase_b_evaluate.py`'s stdout here verbatim, then write one sentence translating it into the ask
(see TL;DR guidance above).

**Known caveats to carry forward regardless of verdict** (from `L1_AUDIT_FINDINGS.md`,
refreshed 2026-08-23 — 4 findings added since this skeleton was first drafted, #4/#6 are new
and matter more than the original #2/#3):
- **Finding #6 (HIGH, most important — check before trusting the `l1_mlp:0.40` row at all):**
  `s1/runs/*.jsonl` had byte-identical files committed under different timestamp names;
  `l1_training.py`'s unfiltered glob read some prompts' invocations 2-3x, overweighting them in
  the BCE loss that produced the *exact* `l1_weights.json` deployed as `l1_mlp:0.40` in this run.
  Does not invalidate the pilot's accuracy methodology, but if the `l1_mlp:0.40` row disappoints,
  this is a confound to rule out before concluding the feature set is at fault — confirm whether
  `s1/runs/` was deduped and `l1_weights.json` retrained before this run's data was collected, and
  say so explicitly in Section 3 (either "weights retrained on deduped pool" or "confound not yet
  ruled out, numbers below are provisional").
- **Finding #11 (MEDIUM, new 2026-08-24 — same "0.9589" citation as #4 below, different
  mechanism):** `l1_training.py`'s train/test split (`GroupShuffleSplit` on `sample_id`) guards
  against prompt leakage but has no benchmark-stratification axis, so the one realized 80/20 split
  has an unreported and unverified GSM8K/HumanEval mix in the held-out fold. Phase A's own
  certified result shows L1's edge is benchmark-asymmetric (ΔAUC +0.019 GSM8K / +0.033
  HumanEval) — if the test fold under- or over-represents HumanEval invocations, the reported
  `final_test_auc = 0.9589` in `l1_weights.json` could be flattering GSM8K, diluting HumanEval, or
  genuinely representative, with no way to tell from what's saved. Same citation as finding #4
  below is affected; combine into one caveat next to the 0.9589 number rather than two separate
  footnotes. Doesn't touch Phase B's downstream accuracy tables (those are prompt-level, correctly
  guarded by #1/#3) — it's specifically a trust question over the training-time selection number.
- **Finding #4 (HIGH):** the Phase A "AUC=0.9589" / "matches Phase A ceiling" framing
  (Section 1/2 language) is optimistic-selection-biased — `l1_training.py` picks its
  best-of-~300-checkpoints by peeking at the same held-out set it then reports the metric on, with
  no third split. Doesn't touch Phase B's downstream-accuracy numbers directly, but if Section 1-2
  text is copied verbatim from `MEMO_L1_REV4.html` as instructed above, add a one-line caveat next
  to the 0.9589 citation rather than presenting it as a clean held-out number.
- **Finding #10 (MEDIUM/HIGH, new 2026-08-24 — check before trusting `l1_weights.json`/the
  `l1_mlp:0.40` policy itself, not just this run's tables):** the S1 v3 instrumentation's
  corrector-convergence check (`torch.allclose` on integer LLaDA token-id tensors,
  `diffusion.py`) can silently misjudge two *different* token ids as "equal" once either id is
  ≥100000 (roughly the top ~20% of the ~126k vocab, which is where `mask_id`/special tokens
  live) — `torch.allclose`'s default `atol=1e-8, rtol=1e-5` tolerance is wide enough at that
  magnitude to swallow an off-by-one id mismatch. `l1_training.py` uses this check's output
  (`broke_at_step_1`, inverted) as the binary training label for the exact MLP
  (`l1_weights.json`) deployed as `l1_mlp:0.40` in this run — a false positive mislabels a
  corrector invocation that did real work as a no-op, corrupting the label in the direction that
  hides the policy's actual behavior. **Not yet confirmed against real data** (no token-id field
  logged in `s1/runs/*.jsonl` to check the false-positive rate directly, and no `torch.` runtime
  available to reproduce the `allclose` call this fire — verified against PyTorch's documented
  tolerance formula only). If this run's `l1_mlp:0.40` row disappoints and finding #6's dedup
  confound has already been ruled out, this is the next thing to check before concluding the
  feature set itself is at fault — a training-label integrity issue in the already-trained MLP,
  not a bug in the Phase B pilot/eval scripts themselves.
- **Finding #9 (MEDIUM, new 2026-08-24 — check before trusting the HumanEval accuracy
  column across policies):** `humaneval_pass` extracts the FIRST fenced python code block via
  `re.search`, the same first-match bug already fixed for GSM8K's `\boxed{}` parsing (#2 below)
  but never applied to the HumanEval side. Unlike #7, this is NOT policy-neutral: if heavier
  corrector invocation (`cadllm_linear:0.15`/`l1_mlp:0.40`) systematically leaves fewer stray/
  duplicate fenced blocks than a lighter policy, first-match extraction scores policies
  asymmetrically for a reason unrelated to actual solution correctness — undermining the fair
  head-to-head this table exists to report. Not yet confirmed against real data (no v2.jsonl
  landed as of this draft). Before citing the HumanEval row: grep `v2.jsonl`'s `gen_text` for
  rows with more than one fenced-python-block occurrence and check whether that rate differs by
  policy; if ~0 across all rows this is moot, if nonzero and policy-skewed the HumanEval numbers
  need a rescore with a fixed (last-match, or `def {entry_point}`-matching) extractor before this
  memo cites them.
- Finding #2 (gsm8k boxed-answer parsing, first-match vs last-match): `phase_b_evaluate.py`
  auto-rescores from `gen_text` on load, so v2 numbers should already be correct — confirm the
  stdout printed `[eval] re-scored N/M rows` and note the count here if nonzero.
- Finding #7 (MEDIUM): the boxed-answer regex also mis-scores `\boxed{\frac{a}{b}}`-style nested
  answers as wrong even when correct (stops at the first `}`) — same rescore-on-load fix as #2
  should cover it if `phase_b_evaluate.py`'s regex was patched; if not, raw GSM8K accuracy in
  Table V2-1 is a systematic undercount (policy-neutral, so relative deltas should be fine).
- Finding #3 (leakage invariant not enforced, only inferred consistent): still an open TODO,
  worth one sentence in the "open concerns" list if not resolved by run time.
- Finding #5 (LOW): `phase_b_evaluate.py`'s rescore path can silently no-op on a network hiccup
  with no warning — if the stdout has no `[eval] re-scored` line at all (not even `0/0`), don't
  assume rescoring ran; re-check before trusting the accuracy table.
- Finding #8 (LOW, new 2026-08-23): `FixedPolicy` in `l1_policy.py` doesn't implement the
  `should_invoke(features)` interface `generate.py` expects of a non-`None` `corrector_policy` —
  currently harmless because `phase_b_pilot.py` special-cases the `fixed` arm to pass
  `corrector_policy=None` instead. Doesn't affect any number in this memo's tables (no code path
  in the actual pilot run touches it), but as a side effect the `fixed` arm skips the
  `features_from_predictor_logits` call that `cadllm_linear`/`l1_mlp` both pay for every predictor
  step — a small constant-per-step compute asymmetry, not a `total_nfe` difference. Only relevant
  if this memo ever reports wall-clock/throughput per policy; irrelevant to the accuracy tables.
- Finding #12 (LOW, new 2026-08-24): `generate.py`'s inline S1 instrumentation block and
  `l1_policy.py`'s `features_from_predictor_logits` are two independent hand-copies of the same
  five-feature formula (no shared call, no equivalence test) — verified term-by-term to currently
  agree, so this does not affect any number in this memo. Flagged as a train/inference-skew risk
  for future edits: a change to one copy (e.g. a numerical-stability fix) would silently desync
  from the other with no error, corrupting the meaning of a future retrain's AUC without touching
  today's `l1_mlp:0.40` weights. No action needed for this memo; worth a one-line footnote only if
  `l1_weights.json` is ever retrained between now and publication.
- Finding #13 (MEDIUM, new 2026-08-25): `phase_b_pilot.py`'s resume path
  (`json.loads` per line against the existing `--out` file) has no `try/except` around a
  truncated trailing line, so a mid-write kill (spot-instance reclaim, OOM, `Ctrl-C`, CUDA driver
  reset) on the long-running T4 pilot turns a resumable run into one that crashes on every
  relaunch until the last line is hand-truncated. Crash-recovery/availability issue, not a
  wrong-number bug — doesn't affect any table in this memo unless the EC2 run has actually been
  interrupted mid-write (not knowable from this repo checkout; ask Lucas if `v2.jsonl` takes
  unusually long to land).

## Section 4 — The decisive experiment / A100 ask

Copy unchanged from `MEMO_L1_REV4.html` UNLESS the v2 verdict is PASS, in which case update the
ask language to "scale up an already-positive result" rather than "resolve an ambiguous one" —
the axes table (N, seeds, held-out, CadLLM tuning, precision) stays the same either way since
those all remain true limitations of the T4 single-seed run.

## Section 5 — Paper floor + open concerns

Copy unchanged — the PASS / AMBIGUOUS-or-floors two-column structure already covers the v2
outcomes, just update which column is bolded/leading based on `{{VERDICT}}`.

**Related-work paragraph (refresh before use):**
> Existing training-free adaptive schedulers (CadLLM, AdaBlock-dLLM, DepCap, Dynamic-dLLM, KLASS,
> SWD, CORA-Diff) and lightweight learned ones (Apple-RL, TraceLock, LESS) all key on a scalar
> signal — usually mean confidence, sometimes a KL-derived stability index — to decide when to
> skip/early-exit correction. L1's contribution is that it reads the *shape* of the predictor's
> confidence distribution (min, std, entropy over active positions, not just the mean), which the
> certified Phase A result shows carries additional predictive signal these scalar-keyed methods
> discard.
>
> **Independent precedent for the shape-vs-scalar thesis (new, found 2026-08-23):** six papers
> outside this cluster converge on the same design principle from the other direction — that
> *multi-signal/trajectory-aware* stopping beats single-scalar snapshots — for the sibling
> pre-commit (not-yet-decoded-token) decision: Jazbec (2512.09106), STaRR (2601.04205), TACG
> (2607.03236), Mask-Aware Policy Gradients (2607.15200), LATCH/CVC (2607.28166), and Ada-DLM
> (ACL 2026.acl-long.819). None scoop L1 (different decision target — pre-commit eligibility vs.
> ProSeCo's corrector-burst budget over already-generated text) but they're citable as independent
> validation of the thesis. Source: `remasking_test:research-ideation/LANDSCAPE.md`'s KEY_COMPETITORS
> section (2607.28166 entry + its fire-37/fire-24 updates), logged there as "worth citing if L1's
> pitch ... is next refined" but not yet pulled into any L1 document before this pass. Caveat: most
> of these are WebSearch-snippet-level reads per LANDSCAPE.md's own flags (arxiv/ar5iv/semanticscholar
> were `EGRESS_BLOCKED` on the fires that logged them) — verify primary sources before citing in
> anything sent externally.
>
> This paragraph was last checked against `remasking_test:research-ideation/LANDSCAPE.md`'s
> Gate-8 competitor list on 2026-08-23. Correction to the prior draft: the cluster is NOT 8 entries
> matching the pill list above — LANDSCAPE.md's actual pre-commit-eligibility/early-exit cluster
> already carries 10 (adds SWD/2604.17068 and CORA-Diff/2608.11235 to the original 8), both
> confirmed non-overlapping with L1 by LANDSCAPE.md's own Gate-8 sweeps (2026-08-11 and 2026-08-15).
> Re-verify no further entry has landed since, especially any single-scalar-vs-shape comparison
> that would need citing or distinguishing.

## Provenance block

Copy unchanged from `MEMO_L1_REV4.html`, then append:
```
Phase B v2 data: ~/proseco/phase_b/v2.jsonl · {{n_gsm8k}} GSM8K + {{n_humaneval}} HumanEval,
  5 policies, single seed, held-out from L1 training pool (TRAIN_POOL_N=100)
Evaluated: phase_b_evaluate.py, rescore-on-load enabled
```
