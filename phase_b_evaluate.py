"""Score Phase B against the pre-registered success criteria.

Input: a JSONL of runs (one row per (policy, benchmark, sample)) produced by
phase_b_pilot.py.

Output: per-benchmark accuracy table with NFE, the primary paired-bootstrap
comparison (l1_mlp:0.40 vs the CadLLM threshold whose observed mean NFE lands
closest to L1's), the secondary comparison (l1_mlp vs fixed), and a verdict
per the PHASE_B_L1_DESIGN.md / PHASE_B_PREREG_2026-08-22.md criteria.

Usage: python phase_b_evaluate.py /path/to/v2.jsonl [--l1_policy l1_mlp:0.40]
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict

import numpy as np


def load(path: str, rescore: bool = True) -> list[dict]:
    """Load rows. If rescore=True and the row has a gen_text field, re-score
    correctness with the CURRENT evaluator (post-hoc bug-fix rescue path).
    Rows without gen_text keep their original correct value."""
    rows = [json.loads(l) for l in open(path)]
    if not rescore:
        return rows
    # Lazy import so this file has no torch dep for offline analysis
    from phase_b_pilot import evaluate_generation
    # We need golds; reload from the datasets since we don't stash them in the JSONL.
    # This is slow-ish (one HF dataset load), but analysis is offline.
    from phase_b_pilot import load_benchmark
    gold_by_id: dict[str, tuple] = {}
    for bench in {r["benchmark"] for r in rows}:
        # Load ENOUGH samples to cover any id we might see (held-out span).
        # Both training pool and held-out are within test-split — grab a superset.
        for held_out in (True, False):
            try:
                for s in load_benchmark(bench, 200, held_out=held_out):
                    gold_by_id[s["id"]] = (s["gold"], bench)
            except (AssertionError, Exception):
                pass  # ok if we can't cover both; whatever's loaded is fine
    n_rescored = 0
    for r in rows:
        if "gen_text" in r and r["id"] in gold_by_id:
            gold, bench = gold_by_id[r["id"]]
            new = evaluate_generation(r["gen_text"], gold, bench)
            if new != r["correct"]:
                n_rescored += 1
            r["correct"] = new
    if n_rescored:
        print(f"[eval] re-scored {n_rescored}/{len(rows)} rows with updated evaluator")
    return rows


def index_by_id(rs: list[dict]) -> dict[str, dict]:
    return {r["id"]: r for r in rs}


def paired_bootstrap(A: dict, B: dict, ids: list[str], n_boot: int = 500, seed: int = 42):
    """Paired cluster-bootstrap over prompt ids of the accuracy delta (A - B).
    Returns (observed_delta, ci_low, ci_high, p_le_zero, n_paired)."""
    ids = [i for i in ids if i in A and i in B]
    if not ids:
        return None
    rng = np.random.default_rng(seed)
    def delta(sample_ids):
        return float(np.mean([int(A[i]["correct"]) - int(B[i]["correct"]) for i in sample_ids]))
    obs = delta(ids)
    boot = np.array([delta(rng.choice(ids, size=len(ids), replace=True).tolist()) for _ in range(n_boot)])
    return obs, float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5)), float((boot <= 0).mean()), len(ids)


def evaluate(path: str, l1_policy: str = "l1_mlp:0.40"):
    recs = load(path)
    by_pb = defaultdict(list)
    for r in recs:
        by_pb[(r["policy"], r["benchmark"])].append(r)

    print(f"Loaded {len(recs)} rows from {path}\n")

    # Raw table
    print(f"=== Raw accuracy + NFE (n=samples per cell) ===\n")
    print(f"{'policy':26s} {'bench':10s} {'n':>3s} {'acc':>6s} {'mean_nfe':>9s} {'med_nfe':>7s}")
    for (p, b), rs in sorted(by_pb.items()):
        acc = sum(1 for r in rs if r["correct"]) / len(rs)
        m_nfe = statistics.mean(r["total_nfe"] for r in rs)
        med = statistics.median(r["total_nfe"] for r in rs)
        print(f"{p:26s} {b:10s} {len(rs):3d}  {acc:.3f}  {m_nfe:8.1f}  {med:7.0f}")

    # Pre-registered comparisons per benchmark
    verdicts = {}
    for bench in ["gsm8k", "humaneval"]:
        per_policy = {p: by_pb[(p, bb)] for (p, bb) in by_pb if bb == bench}
        if l1_policy not in per_policy:
            print(f"\n[{bench}] SKIP: {l1_policy} not in data")
            continue
        cad_policies = sorted(p for p in per_policy if p.startswith("cadllm_linear"))
        if not cad_policies:
            print(f"\n[{bench}] SKIP: no cadllm_linear policies in data")
            continue

        # Pick the CadLLM threshold whose mean NFE is closest to L1's
        l1_nfe = statistics.mean(r["total_nfe"] for r in per_policy[l1_policy])
        matched = min(cad_policies, key=lambda pc: abs(statistics.mean(r["total_nfe"] for r in per_policy[pc]) - l1_nfe))
        matched_nfe = statistics.mean(r["total_nfe"] for r in per_policy[matched])

        print(f"\n=== [{bench}] Pre-registered comparisons ===")
        print(f"  L1 mean NFE = {l1_nfe:.1f}. NFE-matched CadLLM = {matched} (mean NFE = {matched_nfe:.1f}, |Δ| = {abs(matched_nfe - l1_nfe):.1f}).")

        ids = sorted(set(r["id"] for rs in per_policy.values() for r in rs))
        idx_l1 = index_by_id(per_policy[l1_policy])
        idx_cad = index_by_id(per_policy[matched])

        primary = paired_bootstrap(idx_l1, idx_cad, ids)
        if primary is None:
            print(f"  PRIMARY: no paired prompts")
            continue
        d, lo, hi, p0, n = primary
        pass_primary = lo > 0
        verdicts[bench] = {"primary_pass": pass_primary, "delta": d, "ci": (lo, hi), "p_le0": p0, "n": n, "matched": matched}
        pv = "PASS" if pass_primary else "AMBIGUOUS"
        print(f"  PRIMARY  l1_mlp:0.40 vs {matched}: Δacc = {d:+.3f}  95%CI = [{lo:+.3f}, {hi:+.3f}]  P(Δ≤0) = {p0:.3f}  n_paired = {n}   → {pv}")

        # Secondary: L1 vs fixed
        if "fixed" in per_policy:
            idx_fx = index_by_id(per_policy["fixed"])
            sec = paired_bootstrap(idx_l1, idx_fx, ids)
            if sec is not None:
                d2, lo2, hi2, p02, n2 = sec
                kill = hi2 < 0
                fx_nfe = statistics.mean(r["total_nfe"] for r in per_policy["fixed"])
                print(f"  SECONDARY l1_mlp:0.40 vs fixed (mean NFE {fx_nfe:.1f}): Δacc = {d2:+.3f}  95%CI = [{lo2:+.3f}, {hi2:+.3f}]  P(Δ≤0) = {p02:.3f}   → {'KILL' if kill else 'not killed'}")
                verdicts[bench]["secondary_delta"] = d2
                verdicts[bench]["kill"] = kill

    # Overall verdict per PHASE_B_L1_DESIGN.md
    if verdicts:
        any_pass = any(v["primary_pass"] for v in verdicts.values())
        all_kill = all(v.get("kill", False) for v in verdicts.values()) and len(verdicts) >= 2
        print(f"\n=== VERDICT (per pre-registered criteria) ===")
        if all_kill:
            print(f"  KILL — L1 loses to fixed on all evaluated benchmarks with CI upper bound < 0.")
            print(f"  Action: kill L1, pivot to next open idea in IDEAS.md.")
        elif any_pass:
            passing = [b for b, v in verdicts.items() if v["primary_pass"]]
            print(f"  PASS on {passing} — L1 beats NFE-matched CadLLM with CI lower bound > 0.")
            print(f"  Action: pitch to Yair for A100 scale-up (multi-seed, MBPP, MATH).")
        else:
            print(f"  AMBIGUOUS — CI straddles zero on every primary comparison.")
            print(f"  Action per pre-reg: pitch to Yair for A100 run (2-3 days, resolves statistical power AND int8/T4 quantization confound).")
            print(f"  If A100 run also ambiguous: paper pivots to diagnostic-signal (Phase A) + compute-parity contribution.")

    return verdicts


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("path")
    p.add_argument("--l1_policy", default="l1_mlp:0.40")
    args = p.parse_args()
    evaluate(args.path, args.l1_policy)
