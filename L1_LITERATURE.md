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

---

## 2026-08-23 16:2x UTC — Track A 3rd re-check, still blocked — PushNotification sent

Routing: `L1_LITERATURE.md` and `MEMO_V4_SKELETON.md` tied for oldest raw
file-mtime (both last touched by the 10:26 UTC Track D fire), but by
dedicated-track work (excluding side-effect touches) Track A's last real
attempt was 08:26 UTC vs Track D's 10:26 UTC — so Track A routed this fire,
consistent with the 08:24 and 10:2x entries' own "next fire" notes.

Probed all four briefed sources fresh (not a single-probe spot check this
time, since the 3-in-a-row threshold was in play):

- `arxiv.org/list/cs.LG/recent` — `EGRESS_BLOCKED`
- `api.semanticscholar.org` (graph search endpoint) — `EGRESS_BLOCKED`
- `ar5iv.org/list/cs.LG/recent` — `EGRESS_BLOCKED`

3/3 consecutive fires (02:27, 08:24, this one) hitting the identical
proxy-level `EGRESS_BLOCKED` error, ~14h apart, no drift in error shape.
This is now well past the self-set threshold from the prior two entries —
sent one `PushNotification` this fire per that guidance. Track A remains
structurally unable to do its job (arxiv/semanticscholar literature sweep)
until the egress allowlist is updated; this is a config change outside this
routine's own access, not something a future fire can work around.

Did not re-read `remasking_test:research-ideation/LANDSCAPE.md` this fire
(no network-derived deltas to cross-check against it, and the 10:2x entry
already pulled the one outstanding correction found there into the memo).

**Next fire on Track A:** if the allowlist gets fixed, this is a hard reset
— run the full four-source sweep from the original brief, not a single
probe, since ~14h of arxiv/semanticscholar output will be unread backlog.
If still blocked, log a short "still blocked, Nth" entry and route straight
to B/C/D without repeating the full probe — no need to re-send the
notification every fire once Lucas has been told once; only re-notify if
something *changes* (unblocked, or a new reason the block matters more).

---

## 2026-08-24 00:2x UTC — Track A 4th re-check, still blocked (no re-notify)

Routing: last dedicated-track touch per file, oldest first — A (16:25 UTC
08-23) < D (18:26) < B (20:26) < C (22:25) — so Track A routes again.

Single fresh probe per the prior entry's own guidance (no need to repeat
the full 3-source sweep once 3/3 was already established and notified):

- `arxiv.org/list/cs.LG/recent` — `EGRESS_BLOCKED`, identical error shape
  to the prior three fires (02:27, 08:24, 16:25 UTC on 08-23).

4/4 consecutive fires now. Per the standing guidance from the last entry,
this is a "nothing changed" case — no PushNotification sent (Lucas was
already told once at the 3/3 mark; only re-notify on unblock or on the
block mattering in some new way, neither of which applies here). Routed
straight to Track D instead: folded new `L1_AUDIT_FINDINGS.md` finding #8
(FixedPolicy interface mismatch, logged at `cfa0905`) into
`MEMO_V4_SKELETON.md`'s caveats list — low urgency, doesn't touch any
number in the pilot tables, noted as such.

Also checked: no pilot output file has landed yet (`s1/runs/` has no new
`*result*.jsonl` since the last audit pass; no `v2.jsonl` anywhere in the
tree) — memo skeleton tables are still all placeholders, as expected.

**Next fire on Track A:** same as before — single probe is enough once
blocked status is established; only escalate to a full sweep on unblock.
By the routing rule this next fire should land on Track B (last touched
20:26 UTC 08-23), assuming Track A stays blocked.

## 2026-08-24 06:2x UTC — Track A 6th re-check, still blocked — routed to Track B

Fresh probes this fire:
- `arxiv.org/list/cs.LG/recent` — `EGRESS_BLOCKED`, same error shape as all
  five prior fires (02:27, 08:24, 16:25, 00:25, 06:28 UTC across 08-23/08-24).
- `www.semanticscholar.org/search?...` — also `EGRESS_BLOCKED` (checked this
  fire in addition to arxiv, since arxiv alone has been the only probe on
  most prior re-checks; same result, domain-level block not arxiv-specific).

6/6 consecutive now. No re-notify (Lucas already told once at the 3/3 mark;
nothing new here). L1_LITERATURE.md was the oldest-touched of the four
track files this fire (last real content at 00:24 UTC 08-24, older than
L1_AUDIT_FINDINGS.md's 02:26, L1_FEATURE_IDEAS.md's 04:26, and
MEMO_V4_SKELETON.md's 06:28), so by the routing rule this fire should have
been Track A itself — and was: this re-check *is* that fire's Track A
attempt, blocked as above. Per the established fallback (see 467f7b6's
log entry), routed to whichever of B/C/D was oldest-touched instead:
that's Track B (L1_AUDIT_FINDINGS.md, last touched 02:26 UTC, ahead of
C's 04:26 and D's 06:28). Did a Track B audit pass this fire — see
`L1_AUDIT_FINDINGS.md` finding #10 (`torch.allclose` on integer token ids
in the corrector convergence check, `llada/generate.py` lines 281-284,
silently misclassifies some real changes as no-ops for token ids ≥100000,
corrupting the `broke_at_step_1` label `l1_training.py` trains on).

**Next fire:** if Track A stays blocked again, route to whichever of B/C/D
is then oldest-touched — after this fire that'll be Track C
(L1_FEATURE_IDEAS.md, 04:26 UTC) unless D gets touched again first.

## 2026-08-24 18:2x UTC — Track A 7th re-check, still blocked (no re-notify)

Single fresh probe per standing guidance (full sweep already established
3/3 and notified; no need to repeat until unblocked):

- `arxiv.org/list/cs.LG/recent` — `EGRESS_BLOCKED`, identical error shape
  to all six prior fires.

7/7 consecutive. No re-notify (Lucas already told once at the 3/3 mark;
nothing new here). Routed to Track C (oldest-touched of B/C/D at 12:27 UTC,
ahead of D's 14:26 and B's 16:27) — see `L1_FEATURE_IDEAS.md`'s seventh
pass, three new proposals (#19-#21).

**Next fire on Track A:** same as before — single probe suffices; full
four-source sweep only on unblock. By the routing rule the next fire
should land on Track D (`MEMO_V4_SKELETON.md`, 14:26 UTC) unless Track A
unblocks first, since this fire touched C.

---

## 2026-08-25 02:2x UTC — Track A 8th–10th re-checks, still blocked (no re-notify) — backfill note

The 22:26 (08-24) and 00:26 (08-25) fires each did a single-probe Track A
re-check as their routing landed elsewhere (Track B fire N+7, Track C pass
8 respectively) — both logged "still blocked" in their commit messages
(`c271205`, `5fc6b3d`) but neither wrote a dated entry to this file, so
this entry backfills that gap. This fire's own fresh probe:

- `arxiv.org/list/cs.LG/recent` — `EGRESS_BLOCKED`, identical error shape
  to all nine prior fires (02:27, 08:24, 16:25 on 08-23; 00:25, 06:28,
  08:28*, 18:26 on 08-24; plus the two backfilled 22:26/00:26 checks).

10/10 consecutive now, spanning ~24h since the last full sweep. No
re-notify — Lucas was already told once at the 3/3 mark (16:25 UTC
08-23) and nothing has changed since (same error shape, same domain-level
block). This has now been the *routing-selected* track ten fires running
without ever completing its actual job; the fallback-to-B/C/D pattern is
working as designed but is worth flagging in plain terms: **Track A has
produced zero literature-scan output since this routine started** and
will keep producing zero until the egress allowlist adds arxiv.org /
semanticscholar.org. That's a standing fact, not new information, so
still no PushNotification — but noting it here explicitly in case a
future fire's "worth re-notifying" judgment call benefits from seeing the
duration spelled out rather than inferring it from a re-check counter.

Per routing rule, falling through to whichever of B/C/D is oldest-touched:
D (`MEMO_V4_SKELETON.md`, last real content 20:25 UTC 08-24) is oldest,
ahead of B (22:26) and C (00:26) — routing this fire to Track D.

**Next fire on Track A:** same as always — single probe, log briefly here
(actually write the entry this time), fall through if still blocked.
