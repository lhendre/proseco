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

Re-checked 2026-08-25 ~14:2x UTC (Track D pass 10, oldest-touched of B/C/D this fire — Track D
last touched 08:25 UTC vs. Track B 10:26 and Track C 12:29; Track A's 12th consecutive
`EGRESS_BLOCKED` routed here, see `L1_LITERATURE.md`): `v2.jsonl` still hasn't landed — `phase_b/`
absent from the repo root, `s1/runs/` unchanged (same 16 files as every prior pass). Re-fetched
`MEMO_L1_REV4.html` via the Artifact read path and diffed the extracted body against the local copy
programmatically (not eyeballed) — byte-identical apart from one trailing blank line introduced by
the frame wrapper; still rev. 4, dated 2026-08-16, same pilot table, no Section 1/2 changes needed.
Re-pulled `remasking_test:research-ideation/LANDSCAPE.md` — HEAD advanced to `2130ee5` (one new
commit since pass 9's `8a56216`, a clean Mode F fresh-paper sweep with no corpus additions) —
grep-confirmed the Gate-8 cluster is still the same 10 entries, related-work paragraph unchanged.
Folded `L1_AUDIT_FINDINGS.md` finding #14 (logged fire N+9, commit `a823da2`) into the caveats list
below, placed at the bottom near #12/#13 — like those, it's a documentation/rigor gap (undocumented
reconciliation between `s1/analyze.py`'s per-block CV/spread "DIES on HumanEval" verdict and the
AUC-based Phase A rationale that put HumanEval in the Phase B pilot) rather than a bug touching any
number this memo currently reports.

Re-checked 2026-08-25 ~20:2x UTC (Track D pass 11, oldest-touched of B/C/D this fire — Track D last
touched 14:27 UTC vs. Track B/A 16:26 and Track C 18:26): `v2.jsonl` still hasn't landed — `phase_b/`
absent from the repo root, `origin/s1-instrumentation` fetched with no new commits beyond `4b5abe1`
except fire N+10's re-verify (`f78959d`, no new finding — confirmed no finding #15 exists). Re-fetched
`MEMO_L1_REV4.html` via the Artifact read path and diffed programmatically against the local copy —
byte-identical apart from the same trailing-blank-line wrapper artifact as pass 10; still rev. 4, no
Section 1/2 changes needed. Re-pulled `remasking_test:research-ideation/LANDSCAPE.md` with a fresh
`git fetch` (the initial shallow clone under-reported HEAD as pass 9's `8a56216`; fetching found
`2130ee5` — the same commit pass 10 already reviewed, one commit ahead of `8a56216`, "Mode F —
fresh-paper sweep clean, corpus rotation remains exhausted, blocked-for-input," no corpus additions).
No commits beyond `2130ee5` — Gate-8 cluster confirmed still the same 10 entries, related-work
paragraph unchanged. No new audit finding to fold in; caveats list below is current through #14.

Re-checked 2026-08-26 ~22:2x UTC (Track D pass 12, oldest-touched of A/B/C/D this fire per
per-file timestamps — `L1_FEATURE_IDEAS.md` 18:26 UTC 08-25 vs. this file 20:26 UTC 08-25 — but
Track C's own pass 11 explicitly blocks on pilot data landing, which fire N+11's audit log flagged
as still true, so this fire did the concrete unblocked action item fire N+11 left open instead:
folding its finding-#14 addendum into this memo's caveats list, done above). `v2.jsonl` still
hasn't landed — `phase_b/` absent from repo root, `s1/runs/` unchanged (same 16 files). Code
unchanged: `l1_policy.py`/`l1_training.py`/`l1_weights.json`/`llada/generate.py`/
`PHASE_B_L1_DESIGN.md` still `185e2ca`, `phase_b_pilot.py`/`phase_b_evaluate.py` still `b0b1b8d`.
Did not re-fetch `MEMO_L1_REV4.html` or `LANDSCAPE.md` this pass (no reason to expect either moved
since pass 11 six hours ago and this fire's budget went to the caveat fold instead) — next pass
should re-check both. `arxiv.org`/`semanticscholar.org` still `EGRESS_BLOCKED` (Track A, no
re-notify — already reported).

Re-checked 2026-09-02 ~16:2x UTC (Track D pass 13, routed here after Track C's pass-11 triage gate
held again — `s1/runs/` and repo root re-verified fresh this fire, still no `phase_b/` dir or
`v2.jsonl` anywhere, pilot data still hasn't landed 10+ days after the Phase B code push — and
Track B had no new code to audit, `l1_policy.py`/`phase_b_pilot.py` etc. unchanged since
185e2ca/b0b1b8d). This pass actioned the explicit pickup left by `L1_LITERATURE.md`'s latest entry
(commit `4326975`, 07:25 UTC today): pulled `remasking_test:research-ideation/LANDSCAPE.md` fresh
(HEAD `76c79485`, 2026-09-02 13:48 UTC) and read its own KEY_COMPETITORS header note directly rather
than trusting any prior count — the pre-commit-eligibility/early-exit cluster is now **12 entries**
(CadLLM, AdaBlock-dLLM, DepCap, Dynamic-dLLM, Apple-2512.09106, KLASS, TraceLock, LESS, MDPO/RCR,
SWD, CORA-Diff, DiFFPO/2510.02212), not the 10 this paragraph has cited since 2026-08-23. Two
entries added since the last check: **MDPO/RCR** (2508.13148 — its RCR sub-mechanism is a static
per-token confidence threshold, no corrector-loop concept, Gate-8-closed as non-overlapping) and
**DiFFPO** (2510.02212 — RL-learned *per-prompt* confidence threshold for the main unmask-commit
decision, even coarser-grained than the rest of the cluster; LANDSCAPE.md's own read and the sibling
proseco fire's independent read both call it "not a scoop"). Neither changes L1's differentiation
argument (still: main-loop commit-timing vs. ProSeCo's post-hoc corrector-burst budget on
already-decoded blocks) — updated the paragraph below to the current count/list and refreshed the
"last checked" date. `MEMO_L1_REV4.html` not re-fetched this pass (no reason to expect Sections 1-2
source material moved; last confirmed byte-identical pass 11, 2026-08-25). No new
`L1_AUDIT_FINDINGS.md` entries since #14 (still current through this pass). `v2.jsonl`/`phase_b/`
absence and the `arxiv.org`/`semanticscholar.org` egress block are both already-reported, unchanged
— no re-notify.

Re-checked 2026-09-03 ~08:2x UTC (Track D pass 14, oldest-touched of A/B/C/D this fire — Track D
last touched 16:28 UTC 09-02 vs. Track C 02:26, Track B 04:26, Track A 06:27 today). Independently
re-verified rather than trusting prior passes' claims: `s1/runs/` re-listed directly, still tops
out at `gsm8k_20260813_045034.jsonl`/`humaneval_20260813_045034.jsonl` (2026-08-13), no `phase_b/`
dir or `v2.jsonl`/`pilot.jsonl` anywhere in the tree — pilot data still hasn't landed, ~21 days
after the newest S1 run and ~15 days after the Phase B code push. `l1_policy.py`/`l1_training.py`/
`l1_weights.json`/`llada/generate.py`/`PHASE_B_L1_DESIGN.md` still `185e2ca`; `phase_b_pilot.py`/
`phase_b_evaluate.py`/`PHASE_B_PREREG_2026-08-22.md` still `b0b1b8d` — no new
`L1_AUDIT_FINDINGS.md` entries to fold (Track B's fire two hours earlier this same cycle
independently re-derived finding #8 and found nothing new). `remasking_test:research-ideation`
HEAD unchanged at `76c7948` since pass 13 — Gate-8 competitor count (12) and the related-work
paragraph below stand as last updated.

This pass re-fetched `MEMO_L1_REV4.html`'s canonical source via live `WebFetch` (not just a repo
read) to close the gap prior passes flagged but didn't always re-check every time: does the
*hosted* artifact match the repo copy, in case Lucas edited the live version without pushing to
git? Confirmed byte-identical (26,722 bytes, same rev. 4 / 2026-08-16 content, same pilot table,
same pre-committed success criteria, same provenance block referencing
`~/proseco/phase_b/pilot.jsonl` and `v2.jsonl` "in flight" as of 2026-08-23) — no drift between
hosted and repo versions, no Section 1-2 changes needed.

`arxiv.org`/`semanticscholar.org` egress block and the EC2 pilot stall are both unchanged from the
single escalation already sent 2026-08-29 02:2x UTC, now ~124.5h/5.2 days ago — no re-notify, per
Track A/B's independent re-verification this same cycle.

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

**2026-09-05 12:2x UTC — Track D pass 20:** routed here as oldest-touched track file (`MEMO_V4_SKELETON.md` pass 19 at 04:26 UTC vs. Track C 06:25, Track B 08:27, Track A 10:25 — all confirmed via fresh per-file commit timestamps). Independent re-verification from live GitHub API calls rather than trusting the prior pass's claims: `s1/runs/` re-listed directly, still 16 entries (15 `.jsonl` files + `s1_verdict.png`, plus `.gitkeep`) topping out at `gsm8k_20260813_045034.jsonl`/`humaneval_20260813_045034.jsonl` (2026-08-13) — no `phase_b/` dir or `v2.jsonl`/`pilot*.jsonl` anywhere in the tree, pilot data still hasn't landed, ~23.4 days after the newest `s1` run and ~17.3 days after the Phase B code push (185e2ca, 2026-08-19) described the pilot as running on EC2. Phase B core files re-verified via `list_commits` on each path: `l1_policy.py` still `185e2ca` (2026-08-19); `phase_b_pilot.py` still `b0b1b8d` (2026-08-23) — matches Track B's `e176770` check ~4h earlier this cycle, no new `L1_AUDIT_FINDINGS.md` entry to fold (findings #1-15 stand). `remasking_test:research-ideation` HEAD re-confirmed via fresh `git ls-remote` at `8c5420e` — unchanged since Track A's `9f36dbf` fire earlier this cycle, already a clean sweep with no new Gate-8 competitor, nothing new to fold. `arxiv.org` re-probed directly via live `WebFetch` this pass: still `EGRESS_BLOCKED`, unchanged since 08-19 (~18.0 days). No PushNotification: nothing meets the hard-rule urgency bar (no pilot data landed, no audit finding invalidating results, no new competitor, no feature breakthrough); the standing 08-29 02:2x escalation is now at ~178h/7.4d, last re-flagged at the 09-03 12:2x duration checkpoint (~130h at the time, now exactly ~48h since that single re-flag) — consistent with every fire since 09-03 12:2x, re-flagging again this soon on pure incremental duration alone would be noise, so this pass stands down too.

*Correction (same fire, immediately after publishing the above): this pass's first update to this file accidentally submitted a partial-content PUT that started mid-file at "## Section 1", silently dropping the title, the drafted-2026-08-23 provenance intro, passes 4-13's history, the "How to fill this in" checklist, and the "Header / status pills"/"TL;DR" template sections. Caught immediately by re-reading the file after the write; restored by concatenating the missing head content back onto the existing (correct) body and re-publishing — no information was lost, but the fix required a second commit. If a future pass ever finds this file starting with "# MEMO_V4_SKELETON.md" missing again, that's this same failure mode recurring, not a new one: always re-read the file immediately after any `create_or_update_file` call on it and diff against what was intended before trusting the commit succeeded as intended.*

Next fire: whichever of A/B/C is oldest-touched at that time. EC2 pilot landing (`s1/runs/` new file or a `phase_b/` dir appearing) remains the single unblock for Tracks B/C/D's stalled items; egress proxy allowlisting arxiv.org/semanticscholar.org remains the single unblock for Track A.
