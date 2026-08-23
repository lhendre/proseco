# MEMO_V4_SKELETON.md — fill-in template for the Phase B v2 decisive-run memo

Drafted 2026-08-23 by the L1 research-iteration bot (Track D). Source: `MEMO_L1_REV4.html`
(pilot-stage memo, still accurate for Sections 1-2) + `PHASE_B_PREREG_2026-08-22.md`
(locked criteria, copied verbatim below) + `phase_b_evaluate.py` (exact output columns
this table maps to). `phase_b/v2.jsonl` was "in flight" as of the last commit that
touched this repo — check whether it has landed before using this.

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

**Known caveats to carry forward regardless of verdict** (from `L1_AUDIT_FINDINGS.md`):
- Finding #2 (gsm8k boxed-answer parsing, first-match vs last-match): `phase_b_evaluate.py`
  auto-rescores from `gen_text` on load, so v2 numbers should already be correct — confirm the
  stdout printed `[eval] re-scored N/M rows` and note the count here if nonzero.
- Finding #3 (leakage invariant not enforced, only inferred consistent): still an open TODO,
  worth one sentence in the "open concerns" list if not resolved by run time.

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
