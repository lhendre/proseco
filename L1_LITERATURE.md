# L1 Literature Scan

Track A (literature scan) log. Append-only, dated entries.

---

## 2026-08-23 02:2x UTC — Track A attempted, blocked by egress policy

This fire's routing (git log recency across `L1_LITERATURE.md`,
`L1_AUDIT_FINDINGS.md`, `L1_FEATURE_IDEAS.md`, `MEMO_V4_SKELETON.md`) picked
Track A: `L1_AUDIT_FINDINGS.md` had just been touched twice in the prior
~20 minutes (audit findings written, then addressed, then a dropped-file
restore — all Track B), while Track A/C had never been touched.

Attempted WebFetch against all three sources this routine is briefed as
having access to:

- `export.arxiv.org` (API query endpoint) — `EGRESS_BLOCKED`
- `arxiv.org` (search UI) — `EGRESS_BLOCKED`
- `ar5iv.org` — `EGRESS_BLOCKED`
- `api.semanticscholar.org` / `www.semanticscholar.org` — `EGRESS_BLOCKED`

All four attempts returned the same proxy-level `EGRESS_BLOCKED` error, not
a content-fetch failure — this looks like a policy/allowlist gap rather than
a transient issue with any one host. Did not attempt the
`remasking_test:research-ideation/LANDSCAPE.md` cross-check's fetch step for
the same reason (that repo file is local via git, so it *was* readable —
see below — but no new arxiv/semanticscholar results existed to cross-check
against it this fire).

**Consequence:** Track A cannot do its job (arxiv/semanticscholar sweep for
masked-diffusion-corrector / adaptive-schedule / confidence-policy /
learned-sampler work) under the current network policy. This will recur on
every future fire that routes to Track A until the egress allowlist is
fixed — worth flagging to Lucas next time a PushNotification-worthy event
gives an opening, or if this file shows the same blocked-result 2-3 fires
in a row with no other progress.

**What I did instead:** read `remasking_test:research-ideation/LANDSCAPE.md`
(local git checkout, no network needed) to check its competitor-tracking
freshness. Its last dated entry is `2026-08-18 ~05:4X UTC` (one later entry
timestamped `2026-08-19 13:45 UTC` appears out of chronological order in the
file, itself flagged there as "unreadable (egress)" — so that sibling
routine has been hitting the same class of egress failure). No entries
since. The file already tracks all 8 Gate-8 competitors named in this
routine's brief (CadLLM, AdaBlock-dLLM, DepCap, Dynamic-dLLM, KLASS,
TraceLock, LESS — "Apple RL" appears under a different label in that file,
0 literal-string hits for "Apple RL" but the RL-scheduling thread is present
under other phrasing); no basis this fire to add a new L1-adjacent finding
since no new source could be read.

Pivoted this fire's remaining budget to Track C (`L1_FEATURE_IDEAS.md`),
which needed no network access and had also never been touched — see that
file for today's entry.

**Next fire on Track A:** re-check whether `arxiv.org` /
`api.semanticscholar.org` egress has been unblocked before repeating this
attempt; if still blocked, skip straight to noting it here again and route
to whichever of B/C/D is actually next in the recency queue instead of
burning the full attempt budget on retries.

---

## 2026-08-23 08:24 UTC — Track A re-check, still blocked

Single-probe re-check per the note above (one `WebFetch` against
`arxiv.org/list/cs.LG/recent`, not a full retry of all four hosts):
`EGRESS_BLOCKED` again, same error shape as last time. This is now 2/2
fires hitting the same wall — worth a PushNotification once this hits 3
in a row per the original threshold, or sooner if Lucas is clearly around
and this is blocking something time-sensitive.

Per the prior entry's guidance, did not burn further budget retrying the
other three hosts and routed this fire's remaining time to Track C
(`L1_FEATURE_IDEAS.md`), which was tied with Track A for oldest-touched
but — unlike Track A — had a completed prior pass and room for a genuine
new entry (see that file's second dated section).

---

## 2026-08-23 10:2x UTC — Correction to the 08:24 entry, found while on Track D

This fire routed to Track D (`MEMO_V4_SKELETON.md` was the oldest-touched
file, ~6h stale vs. Track B's ~4h and Track A/C's ~2h — see git log). While
refreshing the memo's related-work paragraph against
`remasking_test:research-ideation/LANDSCAPE.md` (same local-git read, no
network needed), found two things the 08:24 entry's grep missed:

1. **The Gate-8 cluster is not 8 entries, it's 10.** LANDSCAPE.md's own
   pre-commit-eligibility/early-exit cluster string (searched literally,
   `grep -c` not a manual skim) reads
   `CadLLM/AdaBlock-dLLM/DepCap/Dynamic-dLLM/Apple/KLASS/TraceLock/LESS/SWD/CORA-Diff`
   — SWD (2604.17068) and CORA-Diff (2608.11235) were added to the cluster
   on 2026-08-11 and 2026-08-13/15 respectively, both already Gate-8-swept
   as non-overlapping with L1 in that file. The 08:24 entry's "already
   tracks all 8" claim was correct as of the brief's original list but
   didn't catch that the sibling routine's list had grown past it days
   earlier — worth remembering that "does LANDSCAPE.md contain these 8
   strings" and "is LANDSCAPE.md's cluster still just these 8" are different
   questions.
2. **An unlogged L1-adjacent precedent citation cluster.** LANDSCAPE.md
   (2607.28166 entry and its fire-37/fire-24 follow-ups) explicitly flags six
   papers — Jazbec (2512.09106), STaRR (2601.04205), TACG (2607.03236),
   Mask-Aware Policy Gradients (2607.15200), LATCH/CVC (2607.28166), Ada-DLM
   (ACL 2026.acl-long.819) — as independent convergence on L1's own
   shape-vs-scalar thesis, tagged "worth citing if L1's pitch ... is next
   refined." None had made it into any L1 document until this fire. Pulled
   into `MEMO_V4_SKELETON.md`'s related-work paragraph (see that file,
   Section 5) rather than duplicated in full here. All six are
   WebSearch-snippet-level per LANDSCAPE.md's own flags — primary sources
   still unread, same egress wall this file's Track A entries keep hitting.

No new arxiv-native search performed this fire (that's still blocked, see
08:24 entry) — this is a same-source re-read correction, not a fresh scan.
**Next fire on Track A:** still worth a fresh `arxiv.org` probe (3rd
consecutive block would clear the PushNotification threshold); separately,
if a future Track A fire cross-checks LANDSCAPE.md again, grep the literal
cluster string rather than testing individual competitor names — that's
what caught the gap this time.
