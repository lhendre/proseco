"""Phase B matched-FLOPs pilot.

For each policy in {fixed, cadllm_linear, l1_mlp} × several budget knobs:
  1. Run ProSeCo on a fixed set of held-out prompts.
  2. Log (total NFE, downstream accuracy, per-invocation trace).

Outputs a JSONL where each row is one (policy, budget_knob, sample) triple.
Downstream analysis pairs runs by nearest matched NFE and computes accuracy
deltas with paired cluster-bootstrap CIs.

Success criteria are pre-committed in PHASE_B_L1_DESIGN.md; this script does
not evaluate the criteria — it produces the numbers, and phase_b_evaluate.py
scores them.
"""
from __future__ import annotations

import argparse
import gc
import json
import os
import re
import sys
import time
from pathlib import Path

import torch
from datasets import load_dataset
from transformers import AutoModel, AutoTokenizer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from llada.generate import generate  # noqa: E402
from l1_policy import load_policy  # noqa: E402
from s1.run_s1 import GSM8K_PROMPT, HUMANEVAL_PROMPT, _patch_llada_for_bnb  # noqa: E402

BENCH_CFG = {
    "gsm8k": {
        "steps": 1024,
        "gen_length": 1024,
        "block_length": 32,
        "apply_corrector_every_n_steps": 2,
        "max_corrector_steps_per_loop": 1,
    },
    "humaneval": {
        "steps": 1024,
        "gen_length": 1024,
        "block_length": 32,
        "apply_corrector_every_n_steps": 2,
        "max_corrector_steps_per_loop": 4,
    },
}


TRAIN_POOL_N = 100  # L1 MLP was trained on the first 100 prompts of each benchmark
                    # (v3 protocol, seed=0). Phase B held-out prompts MUST start past
                    # this index to avoid leakage. See L1_AUDIT_FINDINGS.md.


def load_benchmark(name: str, n: int, seed: int = 0, held_out: bool = True):
    """Return n prompts. If held_out=True, prompts are guaranteed disjoint from
    the L1 training pool (first TRAIN_POOL_N with seed=0 for gsm8k, first
    TRAIN_POOL_N indices for humaneval). Default True — the leakage bug in
    the original pilot happened because this was False by construction."""
    if name == "gsm8k":
        ds = load_dataset("openai/gsm8k", "main", split="test")
        # Use the SAME seed=0 shuffle as training, then take the NEXT n after
        # TRAIN_POOL_N. Guaranteed disjoint from training. GSM8K test has 1319.
        ds = ds.shuffle(seed=seed)
        start = TRAIN_POOL_N if held_out else 0
        assert start + n <= len(ds), f"gsm8k held-out request {n} + start {start} exceeds test size {len(ds)}"
        ds = ds.select(range(start, start + n))
        return [
            {"id": f"gsm8k_{start+i}", "prompt": GSM8K_PROMPT.format(problem=r["question"]), "gold": r["answer"]}
            for i, r in enumerate(ds)
        ]
    if name == "humaneval":
        ds = load_dataset("openai/openai_humaneval", split="test")
        # HumanEval has only 164 problems. Training used indices 0..99, so
        # held-out is 100..163 (64 prompts). Cap n at that.
        start = TRAIN_POOL_N if held_out else 0
        n_avail = len(ds) - start
        if n > n_avail:
            print(f"[warn] humaneval held-out: requested {n}, only {n_avail} available (start={start}, total={len(ds)}); using {n_avail}")
            n = n_avail
        ds = ds.select(range(start, start + n))
        return [
            {
                "id": r["task_id"],
                "prompt": HUMANEVAL_PROMPT.format(question=r["prompt"]),
                "gold": {
                    "canonical_solution": r["canonical_solution"],
                    "test": r["test"],
                    "entry_point": r["entry_point"],
                    "prompt": r["prompt"],
                },
            }
            for r in ds
        ]
    raise ValueError(name)


def gsm8k_answer_match(text: str, gold: str) -> bool:
    """Extract \\boxed{N} from generation and compare to gold's final number."""
    m = re.search(r"\\boxed\{([^}]*)\}", text)
    if not m:
        return False
    pred = m.group(1).strip().replace(",", "").replace("$", "")
    m2 = re.search(r"####\s*([-+]?[0-9.,]+)", gold)
    if not m2:
        return False
    target = m2.group(1).replace(",", "").strip()
    try:
        return abs(float(pred) - float(target)) < 1e-6
    except ValueError:
        return pred == target


def humaneval_pass(text: str, gold: dict) -> bool:
    """Extract python code from generation and run it against HumanEval test."""
    code_match = re.search(r"```python\s*\n(.*?)```", text, re.DOTALL)
    body = code_match.group(1) if code_match else text
    full_code = gold["prompt"] + body + "\n" + gold["test"] + f"\ncheck({gold['entry_point']})\n"
    try:
        import subprocess
        result = subprocess.run(
            ["python3", "-c", full_code],
            timeout=10,
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except Exception:
        return False


def evaluate_generation(text: str, gold, bench: str) -> bool:
    if bench == "gsm8k":
        return gsm8k_answer_match(text, gold)
    if bench == "humaneval":
        return humaneval_pass(text, gold)
    return False


def run_one(model, tokenizer, sample: dict, bench: str, policy_spec: str,
            weights_path: str | None, cfg: dict) -> dict:
    device = "cuda"
    messages = [{"role": "user", "content": sample["prompt"]}]
    chat = tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
    input_ids = torch.tensor(tokenizer(chat)["input_ids"], device=device).unsqueeze(0)

    policy_obj = None
    if policy_spec != "fixed":
        policy_obj = load_policy(policy_spec, weights_path=weights_path)

    t0 = time.time()
    x, metrics, _ = generate(
        model,
        input_ids,
        steps=cfg["steps"],
        gen_length=cfg["gen_length"],
        block_length=cfg["block_length"],
        temperature=0.0,
        remasking="low_confidence",
        max_corrector_steps_per_loop=cfg["max_corrector_steps_per_loop"],
        apply_corrector_every_n_steps=cfg["apply_corrector_every_n_steps"],
        tokenizer=tokenizer,
        corrector_policy=policy_obj,
    )
    dt = time.time() - t0
    gen = tokenizer.decode(x[0, input_ids.shape[1]:], skip_special_tokens=True)
    correct = evaluate_generation(gen, sample["gold"], bench)

    return {
        "id": sample["id"],
        "benchmark": bench,
        "policy": policy_spec,
        "correct": bool(correct),
        "total_nfe": int(metrics["total_nfe"]),
        "predictor_nfe": int(metrics["predictor_nfe"]),
        "corrector_nfe": int(metrics["corrector_nfe"]),
        "wall_s": float(dt),
        "gen_len": len(gen),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--checkpoint", default="kuleshov-group/proseco-llada-sft")
    p.add_argument("--quantize", default="int8", choices=["int8", "int4", "none"])
    p.add_argument("--benchmarks", nargs="+", default=["gsm8k", "humaneval"])
    p.add_argument("--n_samples", type=int, default=40)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--weights", default="/home/ec2-user/proseco/l1_weights.json")
    p.add_argument("--out", default="/home/ec2-user/proseco/phase_b/pilot.jsonl")
    p.add_argument(
        "--policies", nargs="+",
        default=[
            "fixed",  # ProSeCo default schedule
            # CadLLM-linear at three thresholds — sweeps NFE budget
            "cadllm_linear:0.20",
            "cadllm_linear:0.30",
            "cadllm_linear:0.40",
            # L1 MLP at three thresholds — sweeps NFE budget
            "l1_mlp:0.35",
            "l1_mlp:0.50",
            "l1_mlp:0.65",
        ],
    )
    args = p.parse_args()

    print(f"[phase_b] loading {args.checkpoint} (quantize={args.quantize})")
    if args.quantize in ("int8", "int4"):
        _patch_llada_for_bnb(args.checkpoint)

    if args.quantize == "int8":
        from transformers import BitsAndBytesConfig
        model = AutoModel.from_pretrained(
            args.checkpoint, trust_remote_code=True,
            quantization_config=BitsAndBytesConfig(load_in_8bit=True),
            device_map={"": 0},
        ).eval()
    elif args.quantize == "int4":
        from transformers import BitsAndBytesConfig
        model = AutoModel.from_pretrained(
            args.checkpoint, trust_remote_code=True,
            quantization_config=BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_quant_type="nf4",
            ),
            device_map={"": 0},
        ).eval()
    else:
        model = AutoModel.from_pretrained(
            args.checkpoint, trust_remote_code=True, torch_dtype=torch.bfloat16,
        ).to("cuda").eval()

    tokenizer = AutoTokenizer.from_pretrained(args.checkpoint, trust_remote_code=True)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Resume: don't re-run rows already in the output file.
    done = set()
    if out_path.exists():
        for line in open(out_path):
            r = json.loads(line)
            done.add((r["policy"], r["benchmark"], r["id"]))
        print(f"[phase_b] resuming, {len(done)} rows already done")

    with open(out_path, "a") as f:
        for bench in args.benchmarks:
            cfg = BENCH_CFG[bench]
            samples = load_benchmark(bench, args.n_samples, seed=args.seed)
            for policy_spec in args.policies:
                for i, s in enumerate(samples):
                    if (policy_spec, bench, s["id"]) in done:
                        continue
                    row = run_one(model, tokenizer, s, bench, policy_spec, args.weights, cfg)
                    f.write(json.dumps(row) + "\n")
                    f.flush()
                    if (i + 1) % 5 == 0 or i + 1 == len(samples):
                        print(
                            f"[phase_b] {policy_spec:24s} {bench:9s} {i+1:3d}/{len(samples)} "
                            f"correct={row['correct']} total_nfe={row['total_nfe']} wall={row['wall_s']:.1f}s"
                        )
                    if (i + 1) % 5 == 0:
                        torch.cuda.empty_cache()
                        gc.collect()

    print(f"[phase_b] done, wrote {out_path}")


if __name__ == "__main__":
    main()
