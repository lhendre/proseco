# Message to Yair (Slack / email draft)

**One-line hook:** "Found a signal ProSeCo's leaving on the table — I've certified it at the step level and piloted the live version. The decisive run needs 2-3 days on your A100s (also resolves my int8 confound). Memo: [link]"

**Longer version (send as a Slack DM before the meeting, memo linked):**

Hey Yair — quick update ahead of Friday.

The corrector-scheduling idea I've been noodling on for a few weeks landed a real result and a fully-specified next step. Two-sentence version:

*ProSeCo's corrector fires every step, but a cheap 5-feature MLP reading the shape of the predictor's confidence distribution (min / std / entropy, not just mean) predicts whether the corrector will do anything, and skipping when it won't preserves accuracy. On 23k held-out invocations from proseco-llada-sft, the shape signal beats a scalar-confidence-linear controller (the CadLLM family) by ΔAUC = +0.019 GSM8K / +0.033 HumanEval, tight bootstrap CIs, P(moat ≤ 0) = 0. The pilot version deployed as a live skip policy is the top-accuracy policy on both benchmarks (+5 pp over fixed on GSM8K, +2.5 pp on HumanEval), but at n=40 the margins land in an ambiguous zone I pre-registered as expected outcome.*

What I'm asking:

- **2-3 days A100 time** to run the decisive experiment: n=100+ × 3-5 seeds, retuned CadLLM to matched compute, bf16 instead of int8 (my T4 setup imposes an int8 quantization confound on a signal that IS the logit distribution's shape — running on your hardware kills that confound for free).
- The experiment is pre-registered end-to-end in the repo (`PHASE_B_PREREG_2026-08-22.md`, commit `a796b4f`, locked before v2 launch). Success/kill/ambiguous outcomes all have pre-committed responses including the "if this too is ambiguous, paper pivots to X" clause.

Full memo, tables, mechanism, caveats: [artifact URL]

Repo: `lhendre/proseco:s1-instrumentation`. All Phase B code + weights + the audit finding that caught a leakage bug in my own pilot are there.

Even in the worst-case outcome the paper has a floor — the certified Phase A diagnostic (shape > mean on 23k invocations) is a standalone workshop-paper contribution, plus L1 as a compute-parity method. What A100 time decides is main-conference vs workshop, not whether there's a paper.

Talk more Friday. Happy to walk through the memo live.

— Lucas

---

## Notes for delivery

- **Send the memo link the day BEFORE the meeting**, not at the meeting. Lets Yair pre-read.
- **Slack message ~150 words**; memo does the heavy lift.
- **Do not lead with "ambiguous"**. Lead with the certified Phase A result and the pilot trending right; ambiguity gets its one honest paragraph inside.
- **The ask is specific**: 2-3 days A100 time. Not "some compute." Not "any help." Specific = actionable.
- **The floor matters**: mention it because Yair will worry about wasted lab time. Floor = workshop paper worst case.
- If Yair asks "what's the primary comparison": `l1_mlp:0.40` vs the CadLLM threshold whose observed mean NFE lands closest to L1's, paired-bootstrap over prompts. See pre-reg.
