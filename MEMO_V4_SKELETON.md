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
- Finding #14 (MEDIUM, new 2026-08-25): `s1/analyze.py`'s go/no-go verdict script (the one that
  produced the "DIES on HumanEval" result cited as prior context for L1) rests on unweighted,
  CI-free hard thresholds and misses its 0.70 `frac_noop` cutoff by 0.008 on HumanEval's largest
  (most-informative) block — a documentation/rigor gap, not a bug in any number this memo reports.
  Nothing in this file, `PHASE_B_L1_DESIGN.md`, or `PHASE_B_PREREG_2026-08-22.md` explains why that
  script's per-block spread verdict disagrees with the AUC-based Phase A rationale (ΔAUC +0.033 on
  HumanEval, the larger of the two benchmark deltas) that motivated running Phase B on HumanEval at
  all. If Yair or Cornell asks "why both benchmarks," the answer isn't currently written down
  anywhere reviewer-facing — worth one clarifying sentence in Section 2 or 5 before this memo goes
  out, independent of the v2 verdict.
- Finding #14 addendum (2026-08-26, cross-repo corroboration): `remasking_test:research-ideation`
  independently re-derived the same AUC-vs-`analyze.py` contradiction and flagged
  `pitches/PITCH_L1_2026-08-22.md` (a drafted, apparently-unsent update to Yair) as stale — its
  "HumanEval: same audit came back flat" framing states the `analyze.py` verdict as settled with no
  mention of the contradicting AUC result, and is also missing the finding #4 (checkpoint-selection
  bias on AUC=0.9589) caveat. Not this memo's own bug (this skeleton already carries both caveats
  above and at line ~207), but a reminder not to let this memo's Section 2/5 clarifying sentence
  (previous bullet) regress to that framing, and worth a heads-up to Lucas before that pitch draft
  is sent as currently worded.

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
> SWD, CORA-Diff) and lightweight learned ones (Apple-RL, TraceLock, LESS, MDPO/RCR, DiFFPO) all key
> on a scalar signal — usually mean confidence, sometimes a KL-derived stability index, sometimes an
> RL-learned per-prompt or per-token threshold — to decide when to skip/early-exit correction. L1's
> contribution is that it reads the *shape* of the predictor's confidence distribution (min, std,
> entropy over active positions, not just the mean), which the certified Phase A result shows
> carries additional predictive signal these scalar-keyed methods discard.
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
> Gate-8 competitor list on 2026-09-02 (LANDSCAPE.md HEAD `76c79485`). The
> pre-commit-eligibility/early-exit cluster is now 12 entries, up from the 10 last cited here on
> 2026-08-23: adds **MDPO/RCR** (2508.13148 — RCR's Gate-8 sweep already closed as
> non-overlapping, static per-token confidence threshold, no corrector-loop concept) and
> **DiFFPO** (2510.02212, found 2026-09-02 — RL-learned *per-prompt* confidence threshold for the
> main unmask-commit decision, coarser-grained than the rest of the cluster; both LANDSCAPE.md's
> own read and this repo's independent read call it "not a scoop"). Neither changes L1's
> differentiation argument. Re-verify no further entry has landed since, especially any
> single-scalar-vs-shape comparison that would need citing or distinguishing.

Re-checked 2026-09-03 ~18:2x UTC (Track D pass 15, oldest-touched of A/B/C/D this fire — Track D
last touched 08:26 UTC vs. Track C 10:26, Track B 14:26, Track A 16:26 today). Independently
re-verified rather than trusting prior passes' claims: `s1/runs/` re-listed directly from a fresh
clone, still tops out at `gsm8k_20260813_045034.jsonl`/`humaneval_20260813_045034.jsonl`
(2026-08-13), no `phase_b/` dir or `v2.jsonl`/`pilot.jsonl` anywhere in the tree — pilot data still
hasn't landed. `l1_policy.py`/`l1_training.py`/`l1_weights.json`/`llada/generate.py`/
`PHASE_B_L1_DESIGN.md` confirmed still `185e2ca`; `phase_b_pilot.py`/`phase_b_evaluate.py` still
`b0b1b8d` (matches Track B's own independent re-check two hours earlier this cycle, no new
`L1_AUDIT_FINDINGS.md` entry beyond #14/#14-addendum to fold).

This pass re-fetched `MEMO_L1_REV4.html`'s canonical source live via `WebFetch` (not a repo read)
and read the full body rather than diffing byte-count alone: confirmed still rev. 4, dated
2026-08-16, same Phase A/pilot tables, same pre-committed PASS/AMBIGUOUS/KILL criteria, same
provenance block referencing `~/proseco/phase_b/pilot.jsonl` (400 runs, landed) and
`~/proseco/phase_b/v2.jsonl` as "in flight" as of 2026-08-23 — still no v2 data. No Section 1/2
drift between hosted and repo copies.

`remasking_test:research-ideation` HEAD advanced to `5265a8a` (2026-09-03 13:46 UTC) since pass
14's `76c7948` — read the actual diff (not just the commit title) to confirm: it's a Gate-8 sweep
closure for DiFFPO against remasking_test's own active-idea list (formalizing that no active idea
there overlaps DiFFPO's mechanism), zero `KEY_COMPETITORS`/`LANDSCAPE.md` entries added or changed.
Note the sibling repo's own competitor count for L1 reads "ten" in that commit message — this is
its narrower own-idea-tracking count, not the same as this paragraph's 12-entry
pre-commit-eligibility/early-exit cluster (which additionally counts SWD/CORA-Diff); already
reconciled in pass 13's entry, not a new discrepancy. Gate-8 competitor count (12) and the
related-work paragraph below stand unchanged.

`arxiv.org`/`semanticscholar.org` egress block and the EC2 pilot stall are both unchanged from the
single escalation sent 2026-08-29 02:2x UTC (~136h/5.7d ago) and the duration-based re-flag already
sent this same cycle at 12:2x UTC (~130h/5.4d then) — no third notification; nothing new since
either. Next fire: whichever of A/B/C/D is oldest-touched by then (currently would be Track C, last
substantive touch 10:26); EC2 pilot landing (`s1/runs/` new file or a `phase_b/` dir appearing)
remains the single unblock for Tracks B/C/D's stalled items; egress unblock remains the single
unblock for Track A.

## Provenance block

Copy unchanged from `MEMO_L1_REV4.html`, then append:
```
Phase B v2 data: ~/proseco/phase_b/v2.jsonl · {{n_gsm8k}} GSM8K + {{n_humaneval}} HumanEval,
  5 policies, single seed, held-out from L1 training pool (TRAIN_POOL_N=100)
Evaluated: phase_b_evaluate.py, rescore-on-load enabled
```

## Pass 16 (2026-09-04, Track D)

Routed here as oldest-touched track file (`MEMO_V4_SKELETON.md` 18:26 UTC vs. Track C 22:25,
Track B 00:29, Track A 02:25 — all Sep 3/4). Independent re-verification from a fresh clone rather
than trusting prior passes' claims:

- `s1/runs/` re-listed directly: still tops out at `gsm8k_20260813_045034.jsonl` /
  `humaneval_20260813_045034.jsonl` (2026-08-13). No `phase_b/` dir, `v2.jsonl`, or `pilot*.jsonl`
  anywhere in the tree — pilot data still hasn't landed, now ~22 days after the newest `s1` run.
- `l1_policy.py` / `l1_training.py` / `l1_weights.json` / `llada/generate.py` /
  `PHASE_B_L1_DESIGN.md` confirmed still `185e2ca` (2026-08-19); `phase_b_pilot.py` /
  `phase_b_evaluate.py` still `b0b1b8d` (2026-08-23) — matches Track B's own independent re-check
  ~2h earlier this cycle (`3ee825d`), no new `L1_AUDIT_FINDINGS.md` entry to fold.
- Live `WebFetch` of `MEMO_L1_REV4.html`'s hosted artifact (full body read): still rev. 4, dated
  2026-08-16, same Phase A/pilot tables, same PASS/AMBIGUOUS/KILL criteria, same provenance block
  ("pilot.jsonl" 400 runs landed, "v2.jsonl" "in flight" as of 2026-08-23, still not landed). No
  Section 1/2 drift.
- `remasking_test:research-ideation` HEAD confirmed still `5265a8a` (2026-09-03 13:46 UTC), same
  commit Track A/D already reconciled — cloned fresh and grepped `LANDSCAPE.md`'s own Gate-8 tally
  directly: "CadLLM, AdaBlock-dLLM, DepCap, Dynamic-dLLM, Apple-2512.09106, KLASS, TraceLock, LESS,
  MDPO/RCR, SWD, CORA-Diff — this makes eleven" plus DiFFPO = twelve, independently confirms this
  memo's standing Gate-8 count of 12 with no drift.
- `arxiv.org` egress re-checked directly this pass: still `EGRESS_BLOCKED`, unchanged since 08-19.

No new state anywhere. No PushNotification — nothing meets the urgency bar (no pilot data landed,
no audit finding invalidating results, no new competitor, no feature breakthrough); the standing
08-29 escalation was already re-flagged at the 12:2x UTC duration checkpoint on 09-03, now at
~146h/6.1d with no change since. Next fire: whichever of A/B/C is oldest-touched (Track A 02:25 and
Track B 00:29 today are both newer than this pass; check exact ordering at fire time — Track C
`7dc1bbb` at 22:25 on 09-03 is likely oldest as of this writing). EC2 pilot landing (`s1/runs/` new
file or a `phase_b/` dir appearing) remains the single unblock for Tracks B/C/D's stalled items;
egress unblock remains the single unblock for Track A.

---

**2026-09-04 12:2x UTC — Track D pass 17:** routed here as oldest-touched track file (MEMO_V4_SKELETON.md last real pass 04:2x vs. Track C 06:2x, Track B/A later). Independent re-verification from a fresh clone: `s1/runs/` still exactly 15 files topping out at `gsm8k_20260813_045034.jsonl`/`humaneval_20260813_045034.jsonl` (2026-08-13), no `phase_b/` dir or `v2.jsonl`/`pilot*.jsonl` anywhere in the tree — pilot data still hasn't landed, ~22 days after the newest s1 run and ~16 days after the Phase B code push described the pilot as running. Phase B core files confirmed still `185e2ca` (2026-08-19); `phase_b_pilot.py`/`phase_b_evaluate.py` still `b0b1b8d` (2026-08-23); `PHASE_B_PREREG_2026-08-22.md` still `a796b4f` — no new audit finding to fold. Live-fetched `MEMO_L1_REV4.html`'s hosted artifact in full this pass (not just byte-count): still rev. 4 / 2026-08-16, identical TL;DR, Phase A/pilot tables, and pre-committed success criteria; provenance block still lists `phase_b/pilot.jsonl` (400 runs) as the only landed Phase B data and `phase_b/v2.jsonl` as "in flight" since 2026-08-23, unlanded — matches this file's standing summary verbatim, no drift. `remasking_test:research-ideation` HEAD confirmed still `5265a8a` (2026-09-03 13:46 UTC) via fresh `list_commits` — no new commits to fold. `arxiv.org` re-checked directly: still `EGRESS_BLOCKED`, unchanged since 08-19. No PushNotification: nothing meets the hard-rule urgency bar; standing 08-29 02:2x escalation now at ~154h/6.4d, last re-flagged at the 09-03 12:2x duration checkpoint (~130h) with no state change since — this pass adds another confirmation, not a new milestone. Next fire: whichever of A/B/C is oldest-touched at that time. EC2 pilot landing (`s1/runs/` new file or a `phase_b/` dir appearing) remains the single unblock for Tracks B/C/D's stalled items; egress proxy allowlisting arxiv.org/semanticscholar.org remains the single unblock for Track A.

---

**2026-09-04 20:2x UTC — Track D pass 18:** routed here as oldest-touched track file (`MEMO_V4_SKELETON.md` pass 17 at 12:29 UTC vs. Track C 14:26, Track B 16:29, Track A 18:25 — all Sep 4). Independent re-verification from a fresh clone rather than trusting the prior pass's claims: `s1/runs/` re-listed directly, still exactly the same 15-file set topping out at `gsm8k_20260813_045034.jsonl`/`humaneval_20260813_045034.jsonl` (2026-08-13) plus `s1_verdict.png`, no `phase_b/` dir or `v2.jsonl`/`pilot*.jsonl` anywhere in the tree — pilot data still hasn't landed, ~22 days after the newest `s1` run and ~16 days after the Phase B code push (185e2ca, 2026-08-19) described the pilot as running. Phase B core files (`l1_policy.py`/`l1_training.py`/`l1_weights.json`/`llada/generate.py`/`PHASE_B_L1_DESIGN.md`) confirmed still `185e2ca`; `phase_b_pilot.py`/`phase_b_evaluate.py` still `b0b1b8d` (2026-08-23) — matches Track B's `72ed81c` check four hours earlier this cycle, no new `L1_AUDIT_FINDINGS.md` entry to fold. Live-fetched `MEMO_L1_REV4.html`'s hosted artifact in full: still rev. 4 / 2026-08-16, byte-for-byte consistent with this file's standing summary — same TL;DR, Phase A/pilot tables, PASS/AMBIGUOUS/KILL criteria; provenance block still lists `phase_b/pilot.jsonl` (400 runs) as the only landed Phase B data and `phase_b/v2.jsonl` as "in flight" since 2026-08-23, unlanded. `remasking_test:research-ideation` HEAD confirmed via `git ls-remote` at `8c5420e` (2026-09-04 13:46 UTC Mode F sweep) — already reconciled by Track A's 18:2x fire this cycle as a clean sweep with no new Gate-8 competitor; nothing new to fold here. `arxiv.org` re-checked directly this pass: still `EGRESS_BLOCKED`, unchanged since 08-19. No PushNotification: nothing meets the hard-rule urgency bar (no pilot data landed, no audit finding invalidating results, no new competitor, no feature breakthrough); the standing 08-29 02:2x escalation is now at ~162h/6.75d, last re-flagged at the 09-03 12:2x duration checkpoint (~130h at the time) — re-flagging again this soon on pure duration would be noise per that entry's own reasoning, so this pass stands down again. Next fire: whichever of A/B/C is oldest-touched at that time (Track C `4df72c2` 14:26 UTC is likely oldest as of this writing — verify at fire time). EC2 pilot landing (`s1/runs/` new file or a `phase_b/` dir appearing) remains the single unblock for Tracks B/C/D's stalled items; egress proxy allowlisting arxiv.org/semanticscholar.org remains the single unblock for Track A.

---

**2026-09-05 04:2x UTC — Track D pass 19:** routed here as oldest-touched track file (`MEMO_V4_SKELETON.md` pass 18 at 20:25 UTC vs. Track C 22:25, Track B 00:27, Track A 02:26 — all Sep 4/5, confirmed via fresh per-file commit timestamps, not this log). Independent re-verification from a fresh clone rather than trusting the prior pass's claims: `s1/runs/` re-listed directly, still 16 entries (15 `.jsonl` files + `s1_verdict.png` + `.gitkeep`) topping out at `gsm8k_20260813_045034.jsonl`/`humaneval_20260813_045034.jsonl` (2026-08-13); repo-wide search for `phase_b`/`v2.jsonl`/`pilot*.jsonl` returned nothing — pilot data still hasn't landed, ~23 days after the newest `s1` run and ~17 days after the Phase B code push (185e2ca, 2026-08-19) described the pilot as running on EC2. Phase B core files (`l1_policy.py`/`l1_training.py`/`l1_weights.json`/`llada/generate.py`/`PHASE_B_L1_DESIGN.md`) confirmed still `185e2ca`; `phase_b_pilot.py`/`phase_b_evaluate.py` still `b0b1b8d` — matches Track B's `a4b643c` check ~4h earlier this cycle, no new `L1_AUDIT_FINDINGS.md` entry to fold. Live-fetched `MEMO_L1_REV4.html`'s hosted artifact in full via `WebFetch` (not a repo read, to catch host/repo drift): still rev. 4 / 2026-08-16, byte-for-byte consistent with this file's standing summary — same TL;DR, Phase A/pilot tables, PASS/AMBIGUOUS/KILL criteria, same "$150 spend" and "3 weeks T4 / 2-3 days A100" language; provenance block still lists `phase_b/pilot.jsonl` (400 runs, landed) as the only real Phase B data and `phase_b/v2.jsonl` (100 GSM8K + 64 HumanEval, 4 policies) as "in flight" since 2026-08-23, still unlanded. `remasking_test:research-ideation` HEAD confirmed via fresh `--depth 5` clone at `8c5420e` (2026-09-04 13:46 UTC) — same commit Track A's `2dee0c1` fire already reconciled this cycle; read the commit's own diff directly rather than trusting the prior reconciliation: a clean Mode F fresh-paper sweep (3 WebSearch queries, all hits already-known) plus a note that the sibling repo is tracking this repo's Track B finding #15 for context only, no `LANDSCAPE.md` `KEY_COMPETITORS` entries added — Gate-8 count (12) and the related-work paragraph below stand unchanged. `arxiv.org` re-checked directly this pass: still `EGRESS_BLOCKED`, unchanged since 08-19 (~17.5 days). No PushNotification: nothing meets the hard-rule urgency bar (no pilot data landed, no audit finding invalidating results, no new competitor, no feature breakthrough); the standing 08-29 02:2x escalation crossed the one-week mark on the immediately preceding Track A fire (~168h/7.0d) and is now at ~170h/7.1d, last re-flagged at the 09-03 12:2x duration checkpoint (~130h at the time, ~40h ago from this pass) — re-flagging again this soon on pure incremental duration would be noise per that entry's own established reasoning, so this pass stands down too. Next fire: whichever of A/B/C is oldest-touched at that time. EC2 pilot landing (`s1/runs/` new file or a `phase_b/` dir appearing) remains the single unblock for Tracks B/C/D's stalled items; egress proxy allowlisting arxiv.org/semanticscholar.org remains the single unblock for Track A.

---

**2026-09-05 12:2x UTC — Track D pass 20:** routed here as oldest-touched track file (`MEMO_V4_SKELETON.md` pass 19 at 04:26 UTC vs. Track C 06:25, Track B 08:27, Track A 10:25 — all confirmed via fresh per-file commit timestamps). Independent re-verification from live GitHub API calls rather than trusting the prior pass's claims: `s1/runs/` re-listed directly, still 16 entries (15 `.jsonl` files + `s1_verdict.png`, plus `.gitkeep`) topping out at `gsm8k_20260813_045034.jsonl`/`humaneval_20260813_045034.jsonl` (2026-08-13) — no `phase_b/` dir or `v2.jsonl`/`pilot*.jsonl` anywhere in the tree, pilot data still hasn't landed, ~23.4 days after the newest `s1` run and ~17.3 days after the Phase B code push (185e2ca, 2026-08-19) described the pilot as running on EC2. Phase B core files re-verified via `list_commits` on each path: `l1_policy.py` still `185e2ca` (2026-08-19); `phase_b_pilot.py` still `b0b1b8d` (2026-08-23) — matches Track B's `e176770` check ~4h earlier this cycle, no new `L1_AUDIT_FINDINGS.md` entry to fold (findings #1-15 stand). `remasking_test:research-ideation` HEAD re-confirmed via fresh `git ls-remote` at `8c5420e` — unchanged since Track A's `9f36dbf` fire earlier this cycle, already a clean sweep with no new Gate-8 competitor, nothing new to fold. `arxiv.org` re-probed directly via live `WebFetch` this pass: still `EGRESS_BLOCKED`, unchanged since 08-19 (~18.0 days). No PushNotification: nothing meets the hard-rule urgency bar (no pilot data landed, no audit finding invalidating results, no new competitor, no feature breakthrough); the standing 08-29 02:2x escalation is now at ~178h/7.4d, last re-flagged at the 09-03 12:2x duration checkpoint (~130h at the time, now exactly ~48h since that single re-flag) — consistent with every fire since 09-03 12:2x, re-flagging again this soon on pure incremental duration alone would be noise, so this pass stands down too. Next fire: whichever of A/B/C is oldest-touched at that time. EC2 pilot landing (`s1/runs/` new file or a `phase_b/` dir appearing) remains the single unblock for Tracks B/C/D's stalled items; egress proxy allowlisting arxiv.org/semanticscholar.org remains the single unblock for Track A.
