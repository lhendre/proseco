"""S1 analyzer: reads the JSONL log from run_s1.py and produces the L1 verdict.

The L1 wedge: per-block optimal ω (correction frequency) varies enough across
blocks to justify a learned per-block gate. This script measures three signals
per block position, aggregating across all samples in both benchmarks:

    1. `frac_noop`: fraction of corrector invocations at this block position
       that broke at step 1 (i.e., produced the same tokens as the seed argmax
       = correction was a no-op). If a block position has high frac_noop, its
       corrector invocations could have been skipped entirely.

    2. `mean_break_step`: average number of corrector iterations before break.
       Low means fast convergence (weak signal / not much to correct); high
       means the corrector was actually working.

    3. `frac_active_changed`: mean fraction of still-masked positions that the
       corrector actually changed from the seed argmax. This is the "did
       correction earn its keep" metric on the tokens that MIGHT get committed
       this step. High variance across blocks = strongest evidence for L1.

Verdict:
    L1 LIVES if coefficient of variation (std/mean) across block positions
        exceeds 0.30 for `frac_noop` OR `frac_active_changed`, AND at least
        one block has frac_noop > 0.70 while another has < 0.30 (i.e., there
        exist blocks where correction is nearly always useless AND blocks
        where it's usually useful — the exact profile a learned gate exploits).
    L1 DIES otherwise (uniform per-block behavior => nothing for a policy to
        allocate).

Usage: python s1/analyze.py s1/runs/
"""
import argparse
import glob
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path


def load_jsonl_dir(path):
    """Load all *.jsonl files under path into a flat list."""
    path = Path(path)
    if path.is_file():
        files = [path]
    else:
        files = sorted(path.glob("*.jsonl"))
    if not files:
        print(f"[analyze] no .jsonl files under {path}", file=sys.stderr)
        sys.exit(1)
    records = []
    for f in files:
        with open(f) as fh:
            for line in fh:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    print(f"[analyze] loaded {len(records)} corrector-invocation records "
          f"from {len(files)} file(s) under {path}")
    return records


def per_block_metrics(records):
    """Group records by (benchmark, block_idx) and compute per-block metrics."""
    grouped = defaultdict(list)
    for r in records:
        grouped[(r["benchmark"], r["block_idx"])].append(r)

    rows = []
    for (bench, block_idx), recs in sorted(grouped.items()):
        n = len(recs)
        if n == 0:
            continue
        n_noop = sum(1 for r in recs if r.get("broke_at_step_1"))
        mean_break = statistics.mean(r["corrector_break_step"] for r in recs)
        # active_changed_frac: n_active_positions_changed / max(active_mask_size, 1)
        active_fracs = [
            r["n_active_positions_changed_by_corrector"] / max(r["active_mask_size"], 1)
            for r in recs
        ]
        rows.append({
            "benchmark": bench,
            "block_idx": block_idx,
            "n_invocations": n,
            "frac_noop": n_noop / n,
            "mean_break_step": mean_break,
            "mean_frac_active_changed": statistics.mean(active_fracs),
        })
    return rows


def cv(values):
    """Coefficient of variation. Returns None if mean is ~0."""
    values = [v for v in values if v is not None]
    if not values:
        return None
    m = statistics.mean(values)
    if abs(m) < 1e-9:
        return None
    s = statistics.stdev(values) if len(values) > 1 else 0.0
    return s / m


def verdict(rows):
    """L1 go/no-go verdict per benchmark, plus aggregate."""
    print("\n" + "=" * 78)
    print("PER-BLOCK METRICS")
    print("=" * 78)
    print(f"{'bench':<12} {'block':>6} {'n_inv':>7} "
          f"{'frac_noop':>12} {'mean_brk':>10} {'frac_active_chg':>18}")
    print("-" * 78)
    for r in rows:
        print(f"{r['benchmark']:<12} {r['block_idx']:>6} {r['n_invocations']:>7} "
              f"{r['frac_noop']:>12.3f} {r['mean_break_step']:>10.2f} "
              f"{r['mean_frac_active_changed']:>18.4f}")

    verdicts = {}
    print("\n" + "=" * 78)
    print("VERDICT")
    print("=" * 78)

    for bench in sorted(set(r["benchmark"] for r in rows)):
        brows = [r for r in rows if r["benchmark"] == bench]
        if len(brows) < 3:
            print(f"[{bench}] not enough blocks ({len(brows)}) for a variance verdict")
            continue

        noop_vals = [r["frac_noop"] for r in brows]
        change_vals = [r["mean_frac_active_changed"] for r in brows]
        cv_noop = cv(noop_vals)
        cv_change = cv(change_vals)

        max_noop = max(noop_vals)
        min_noop = min(noop_vals)
        spread_condition = (max_noop > 0.70) and (min_noop < 0.30)

        cv_ok = (
            (cv_noop is not None and cv_noop > 0.30)
            or (cv_change is not None and cv_change > 0.30)
        )
        lives = cv_ok and spread_condition

        print(f"\n[{bench}] blocks={len(brows)}")
        print(f"  CV(frac_noop)         = {cv_noop:.3f}" if cv_noop is not None else "  CV(frac_noop) = undefined (mean~0)")
        print(f"  CV(frac_active_chg)   = {cv_change:.3f}" if cv_change is not None else "  CV(frac_active_chg) = undefined (mean~0)")
        print(f"  frac_noop min={min_noop:.3f} max={max_noop:.3f}")
        print(f"  spread condition (some blocks >70% noop AND some <30% noop): {spread_condition}")
        print(f"  → L1 {'LIVES' if lives else 'DIES'} on {bench}")
        verdicts[bench] = lives

    print("\n" + "=" * 78)
    if all(verdicts.values()) and verdicts:
        print("OVERALL: L1 LIVES on all benchmarks tested. Recommend proceeding to")
        print("         Phase B (design learned per-block ω policy, ~1-2 weeks).")
    elif any(verdicts.values()):
        mixed = [b for b, v in verdicts.items() if v]
        dead = [b for b, v in verdicts.items() if not v]
        print(f"OVERALL: L1 LIVES on {mixed}, DIES on {dead}.")
        print("         Recommend scoping the L1 paper to just the surviving benchmarks,")
        print("         OR investigate why the wedge differs across task domains.")
    else:
        print("OVERALL: L1 DIES on all benchmarks tested.")
        print("         Per-block corrector behavior is too uniform for a learned")
        print("         allocation policy to beat globally-fixed ω at matched FLOPs.")
        print("         Recommend killing L1 and pivoting to S8 or a fresh Mode F idea.")
    print("=" * 78)

    return verdicts


def maybe_plot(rows, out_path):
    """Optional matplotlib plot; skipped if matplotlib not installed."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("[analyze] matplotlib not installed, skipping plot")
        return
    fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    for bench in sorted(set(r["benchmark"] for r in rows)):
        brows = sorted([r for r in rows if r["benchmark"] == bench],
                       key=lambda r: r["block_idx"])
        xs = [r["block_idx"] for r in brows]
        axes[0].plot(xs, [r["frac_noop"] for r in brows], marker="o", label=bench)
        axes[1].plot(xs, [r["mean_frac_active_changed"] for r in brows],
                     marker="o", label=bench)
    axes[0].set_ylabel("frac corrector invocations that were no-ops")
    axes[0].axhline(0.7, color="gray", linestyle=":", alpha=0.5)
    axes[0].axhline(0.3, color="gray", linestyle=":", alpha=0.5)
    axes[0].legend()
    axes[1].set_ylabel("mean frac active positions changed by corrector")
    axes[1].set_xlabel("block_idx")
    axes[1].legend()
    fig.suptitle("S1: per-block corrector usefulness (L1 wedge test)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    print(f"[analyze] plot saved to {out_path}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("logs_dir_or_file", help="s1/runs/  or  s1/runs/gsm8k_*.jsonl")
    p.add_argument("--plot", default="s1/runs/s1_verdict.png")
    args = p.parse_args()

    records = load_jsonl_dir(args.logs_dir_or_file)
    rows = per_block_metrics(records)
    verdict(rows)
    maybe_plot(rows, args.plot)
