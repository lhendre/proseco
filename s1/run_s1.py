"""S1 runner: measures per-block corrector-invocation behavior on GSM8K + HumanEval.

Loads the ProSeCo LLaDA-SFT checkpoint (or a smaller stand-in), runs generation
on N samples per benchmark with the S1-instrumented generate() from
llada/generate.py, and writes one JSONL row per corrector invocation to
s1/runs/<benchmark>_<timestamp>.jsonl.

Downstream: analyze.py reads these JSONL files and produces the L1 go/no-go
verdict (per-block variance in "correction was a no-op" rate).
"""
import argparse
import json
import os
import time
from pathlib import Path

import torch
from datasets import load_dataset
from transformers import AutoModel, AutoTokenizer

# Import the instrumented generate() from llada/generate.py — this file lives
# at s1/run_s1.py, so it needs the repo root on sys.path to find `llada`.
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from llada.generate import generate  # noqa: E402


# ProSeCo Max hyperparameters from Table 3 of the paper (2602.11590 v3):
# gen_length=1024, block_length=32, 1 token/step => steps=1024 (32 per block × 32 blocks).
# ProSeCo's `steps` param must be divisible by num_blocks (=32), so 1024 is the fit.
# Average NFEs from Table 3 (343/499/818) are OUTPUT metrics after early-EOS stopping,
# not the input `steps` value.
BENCHMARK_CONFIG = {
    "gsm8k": {
        "apply_corrector_every_n_steps": 2,   # ω (Table 3 GSM8K Max)
        "max_corrector_steps_per_loop": 1,    # S (Table 3 GSM8K Max)
        "steps": 1024,
        "gen_length": 1024,
        "block_length": 32,
    },
    "humaneval": {
        "apply_corrector_every_n_steps": 2,   # ω (Table 3 HumanEval Max)
        "max_corrector_steps_per_loop": 4,    # S (Table 3 HumanEval Max)
        "steps": 1024,
        "gen_length": 1024,
        "block_length": 32,
    },
}


GSM8K_PROMPT = (
    "Solve the following math problem. Show your step-by-step reasoning, "
    "then provide the final answer inside \\boxed{{}}\n\n{problem}"
)

HUMANEVAL_PROMPT = (
    "Here is a problem for which you need to generate/complete code:\n\n"
    "{question}\n\n"
    "Please continue to complete the function with python programming language. "
    "You are not allowed to modify the given code and do the completion only.\n\n"
    "The solution should be in the following format:\n"
    "```python\n# Your code here\n```"
)


def load_benchmark(name, n_samples, seed=0):
    """Return a list of dicts with 'prompt' and 'id' keys."""
    if name == "gsm8k":
        ds = load_dataset("openai/gsm8k", "main", split="test")
        ds = ds.shuffle(seed=seed).select(range(n_samples))
        return [
            {"id": f"gsm8k_{i}", "prompt": GSM8K_PROMPT.format(problem=r["question"])}
            for i, r in enumerate(ds)
        ]
    elif name == "humaneval":
        ds = load_dataset("openai/openai_humaneval", split="test")
        # HumanEval has only 164 problems total; cap n_samples
        if n_samples > len(ds):
            print(f"[warn] HumanEval only has {len(ds)} problems; using all.")
            n_samples = len(ds)
        # Not shuffling HumanEval — 164 is small and reproducibility matters
        ds = ds.select(range(n_samples))
        return [
            {"id": r["task_id"], "prompt": HUMANEVAL_PROMPT.format(question=r["prompt"])}
            for r in ds
        ]
    else:
        raise ValueError(f"unknown benchmark {name}")


def _patch_llada_for_bnb(checkpoint):
    """LLaDA's custom modeling_llada.py exposes `_tied_weights_keys` (old HF API).
    Transformers >=5.x's bitsandbytes quantizer calls `all_tied_weights_keys` (new API).
    Patch the class to add the missing attribute before quantized load.
    """
    from transformers import AutoConfig
    from transformers.dynamic_module_utils import get_class_from_dynamic_module

    config = AutoConfig.from_pretrained(checkpoint, trust_remote_code=True)
    auto_map = getattr(config, "auto_map", {}) or {}
    class_ref = auto_map.get("AutoModel") or auto_map.get("AutoModelForCausalLM")
    if not class_ref:
        print(f"[s1] warning: no auto_map found on {checkpoint}, skipping patch")
        return

    model_class = get_class_from_dynamic_module(
        class_reference=class_ref,
        pretrained_model_name_or_path=checkpoint,
    )
    if not hasattr(model_class, "all_tied_weights_keys"):
        # Empty DICT (not list) — transformers 5.x uses `.keys()` on this in
        # modeling_utils.get_total_byte_count (~line 5100), so it must be a mapping.
        # bnb's `if len(...) > 0` check also works on empty dict → skips cleanly.
        model_class.all_tied_weights_keys = {}
        print(f"[s1] patched {model_class.__name__}.all_tied_weights_keys = {{}}")


def run(args):
    device = "cuda"
    print(f"[s1] loading checkpoint: {args.checkpoint}  (quantize={args.quantize})")

    # LLaDA-8B in bfloat16 = ~16GB weights, which does not fit on Tesla T4 (15.6GB VRAM).
    # int8 quantization via bitsandbytes drops to ~8GB, comfortable fit on T4, with
    # <1% argmax-output shift on inference. int4 drops further to ~4GB but has larger
    # shift that would bias S1's per-block corrector-usefulness measurements.
    if args.quantize in ("int8", "int4"):
        _patch_llada_for_bnb(args.checkpoint)

    if args.quantize == "int8":
        from transformers import BitsAndBytesConfig
        quant = BitsAndBytesConfig(load_in_8bit=True)
        model = AutoModel.from_pretrained(
            args.checkpoint,
            trust_remote_code=True,
            quantization_config=quant,
            device_map={"": 0},  # single-GPU placement; accelerate handles the rest
        ).eval()
    elif args.quantize == "int4":
        from transformers import BitsAndBytesConfig
        quant = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_quant_type="nf4",
        )
        model = AutoModel.from_pretrained(
            args.checkpoint,
            trust_remote_code=True,
            quantization_config=quant,
            device_map={"": 0},
        ).eval()
    else:
        # bfloat16, full precision — requires >16GB VRAM
        model = AutoModel.from_pretrained(
            args.checkpoint,
            trust_remote_code=True,
            torch_dtype=torch.bfloat16,
        ).to(device).eval()

    tokenizer = AutoTokenizer.from_pretrained(
        args.checkpoint, trust_remote_code=True,
    )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    for bench_name in args.benchmarks:
        cfg = BENCHMARK_CONFIG[bench_name]
        samples = load_benchmark(bench_name, args.n_samples_per_benchmark)
        out_path = out_dir / f"{bench_name}_{timestamp}.jsonl"
        print(f"[s1] {bench_name}: {len(samples)} samples, writing {out_path}")

        with open(out_path, "w") as f:
            for i, s in enumerate(samples):
                messages = [{"role": "user", "content": s["prompt"]}]
                chat = tokenizer.apply_chat_template(
                    messages, add_generation_prompt=True, tokenize=False,
                )
                input_ids = torch.tensor(
                    tokenizer(chat)["input_ids"], device=device,
                ).unsqueeze(0)

                s1_log = []
                t0 = time.time()
                _, metrics, _ = generate(
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
                    s1_log=s1_log,
                )
                dt = time.time() - t0

                # Write one row per corrector invocation, tagged with sample id + benchmark
                for rec in s1_log:
                    rec["sample_id"] = s["id"]
                    rec["benchmark"] = bench_name
                    rec["config_omega"] = cfg["apply_corrector_every_n_steps"]
                    rec["config_S_max"] = cfg["max_corrector_steps_per_loop"]
                    f.write(json.dumps(rec) + "\n")
                f.flush()
                if (i + 1) % 5 == 0 or i + 1 == len(samples):
                    print(
                        f"[s1] {bench_name} {i+1}/{len(samples)} "
                        f"invocations={len(s1_log)} nfe={metrics['total_nfe']} "
                        f"wall={dt:.1f}s"
                    )
        print(f"[s1] done {bench_name}, wrote {out_path}")

    print(f"[s1] all done. run: python s1/analyze.py {out_dir}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument(
        "--checkpoint",
        default="kuleshov-group/proseco-llada-sft",
        help="HuggingFace repo id (default: ProSeCo LLaDA-SFT). "
             "For a smaller/faster smoke test, try GSAI-ML/LLaDA-8B-Instruct.",
    )
    p.add_argument(
        "--benchmarks",
        nargs="+",
        default=["gsm8k", "humaneval"],
        choices=["gsm8k", "humaneval"],
    )
    p.add_argument("--n_samples_per_benchmark", type=int, default=200)
    p.add_argument("--out_dir", default="s1/runs")
    p.add_argument(
        "--quantize",
        default="int8",
        choices=["int8", "int4", "none"],
        help="int8 (default, ~8GB VRAM, fits T4); int4 (~4GB, may bias S1 signal); "
             "none (bfloat16, needs ~16GB VRAM, e.g., A10G/L4/A100).",
    )
    args = p.parse_args()
    run(args)
