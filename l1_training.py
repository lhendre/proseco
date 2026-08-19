"""Train the L1 MLP on pooled v2 + v3 S1 data.

Loads all JSONL from ~/proseco/s1/runs/v2_n50/ and ~/proseco/s1/runs/ (v3),
grouped 80/20 split by sample_id, trains a 5→16→1 MLP with BCE loss and Adam,
saves best-AUC weights + normalization stats as JSON that l1_policy.py loads.

Deliberately small: this is ~150 LOC because Phase A already showed a linear
model captures essentially all of the signal. The MLP's 16 hidden units are
insurance, not a bet on nonlinearity.
"""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.model_selection import GroupShuffleSplit

FEATURE_KEYS = (
    "predictor_conf_mean_active",
    "predictor_conf_min_active",
    "predictor_conf_std_active",
    "predictor_entropy_mean_active",
    "predictor_entropy_max_active",
)


def load_records(runs_dir: str) -> list[dict]:
    recs = []
    for path in sorted(glob.glob(f"{runs_dir}/*.jsonl")) + sorted(glob.glob(f"{runs_dir}/v2_n50/*.jsonl")):
        if "v1_pre_confidence" in path or "prior" in path or "v3_partial" in path:
            continue
        for line in open(path):
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if "predictor_conf_mean_active" in r:
                recs.append(r)
    return recs


class L1MLP(nn.Module):
    def __init__(self, in_dim: int = 5, hidden: int = 16):
        super().__init__()
        self.fc1 = nn.Linear(in_dim, hidden)
        self.fc2 = nn.Linear(hidden, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.fc2(torch.relu(self.fc1(x))).squeeze(-1)


def make_X_y_g(recs: list[dict]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    X = np.array([[float(r.get(k, 0.0) or 0.0) for k in FEATURE_KEYS] for r in recs], dtype=np.float32)
    y = np.array([0.0 if r.get("broke_at_step_1", False) else 1.0 for r in recs], dtype=np.float32)
    g = np.array([r["sample_id"] for r in recs])
    return X, y, g


def train(args):
    recs = load_records(args.runs_dir)
    print(f"[l1_train] loaded {len(recs)} invocations with confidence fields")
    if not recs:
        raise RuntimeError(f"no records found under {args.runs_dir}")

    X, y, g = make_X_y_g(recs)

    # Grouped 80/20 split by sample_id — same protocol as Phase A rev. 3.
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, test_idx = next(gss.split(X, y, g))
    print(f"[l1_train] train invocations = {len(train_idx)}, test invocations = {len(test_idx)}")
    print(f"[l1_train] train prompts = {len(set(g[train_idx]))}, test prompts = {len(set(g[test_idx]))}")

    # Normalize on the training set only.
    mean = X[train_idx].mean(axis=0)
    std = X[train_idx].std(axis=0)
    Xn = (X - mean) / (std + 1e-8)

    Xtr = torch.tensor(Xn[train_idx])
    ytr = torch.tensor(y[train_idx])
    Xte = torch.tensor(Xn[test_idx])
    yte_np = y[test_idx]

    torch.manual_seed(args.seed)
    model = L1MLP()
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    loss_fn = nn.BCEWithLogitsLoss()

    best_auc = -1.0
    best_state = None
    patience = 0
    for epoch in range(args.epochs):
        model.train()
        perm = torch.randperm(len(Xtr))
        for i in range(0, len(Xtr), args.batch):
            b = perm[i : i + args.batch]
            opt.zero_grad()
            logits = model(Xtr[b])
            loss = loss_fn(logits, ytr[b])
            loss.backward()
            opt.step()

        model.eval()
        with torch.no_grad():
            probs = torch.sigmoid(model(Xte)).numpy()
        auc = roc_auc_score(yte_np, probs)
        ap = average_precision_score(yte_np, probs)

        if auc > best_auc + 1e-4:
            best_auc = auc
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
            patience = 0
        else:
            patience += 1

        if epoch % 25 == 0 or epoch == args.epochs - 1:
            print(f"[l1_train] epoch {epoch:4d}  test AUC={auc:.4f}  AP={ap:.4f}  (best AUC={best_auc:.4f})")
        if patience >= args.patience:
            print(f"[l1_train] early stop at epoch {epoch}, best AUC={best_auc:.4f}")
            break

    if best_state is not None:
        model.load_state_dict(best_state)

    # Final held-out numbers to log alongside the weights
    model.eval()
    with torch.no_grad():
        probs = torch.sigmoid(model(Xte)).numpy()
    final_auc = roc_auc_score(yte_np, probs)
    final_ap = average_precision_score(yte_np, probs)
    print(f"[l1_train] FINAL held-out AUC = {final_auc:.4f}, AP = {final_ap:.4f}")

    W1 = model.fc1.weight.detach().cpu().numpy()  # (16, 5)
    b1 = model.fc1.bias.detach().cpu().numpy()
    W2 = model.fc2.weight.detach().cpu().numpy()  # (1, 16)
    b2 = model.fc2.bias.detach().cpu().numpy()
    state = {
        "W1": W1.T.tolist(),  # transpose so l1_policy.py can do x @ W1
        "b1": b1.tolist(),
        "W2": W2.T.tolist(),
        "b2": b2.tolist(),
        "mean": mean.tolist(),
        "std": std.tolist(),
        "threshold": 0.5,
        "meta": {
            "n_train_invocations": int(len(train_idx)),
            "n_test_invocations": int(len(test_idx)),
            "n_train_prompts": int(len(set(g[train_idx]))),
            "n_test_prompts": int(len(set(g[test_idx]))),
            "final_test_auc": float(final_auc),
            "final_test_ap": float(final_ap),
            "features": list(FEATURE_KEYS),
            "arch": "5-16-1 MLP, ReLU, sigmoid",
            "epochs_trained": int(epoch + 1),
            "seed": int(args.seed),
        },
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(state, f, indent=2)
    print(f"[l1_train] wrote {out}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--runs_dir", default="/home/ec2-user/proseco/s1/runs")
    p.add_argument("--out", default="/home/ec2-user/proseco/l1_weights.json")
    p.add_argument("--epochs", type=int, default=300)
    p.add_argument("--batch", type=int, default=256)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--patience", type=int, default=30)
    p.add_argument("--seed", type=int, default=0)
    train(p.parse_args())
