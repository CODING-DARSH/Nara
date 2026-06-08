"""
NARA — Cold Start — Best: Wide and Deep Network (PyTorch)
─────────────────────────────────────────────────────────────
INPUT FEATURES (X):
  Wide part  : raw one-hot demographic features (memorization)
               birthplace_state, religion, occupation, income_tier,
               is_vegetarian, conditions, dietary_restrictions
  Deep part  : learned embeddings + dense features (generalization)
               All numerical + embedded categoricals
               birthplace_state → 16-dim embedding
               religion         → 8-dim  embedding
               occupation       → 8-dim  embedding
               income_tier      → 4-dim  embedding

PREDICTION TARGET (Y):
  top_cuisine — most frequent cuisine in user meal history

WHY WIDE AND DEEP:
  Wide component: memorizes specific demographic → cuisine patterns
    "Gujarati + Jain + high_income = gujarati cuisine" is memorized directly
  Deep component: generalizes across unseen combinations
    New user from Rajasthan with diabetes gets generalized embedding
  Together: best of both memorization and generalization
  Google used this for Play Store recommendations, same principle applies here

EXPECTED METRICS:
  Top-1 accuracy ~0.60-0.70
  Top-3 accuracy ~0.80-0.87

Run:
  python cold_start/train_wide_deep.py
"""
import os
import sys
import logging

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import LabelEncoder, OneHotEncoder
from sklearn.metrics import top_k_accuracy_score

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MODEL_PATHS, COLD_START_FEATURES, WIDE_DEEP_PARAMS, RANDOM_STATE, CONDITION_FLAGS
from utils import (
    load_users, load_meal_logs,
    expand_conditions, derive_top_cuisine_per_user,
    FeatureEncoder, save_metrics,
    classification_metrics, plot_confusion_matrix,
)

log = logging.getLogger("nara.cold_start.wide_deep")
torch.manual_seed(RANDOM_STATE)


# ── Model definition ──────────────────────────────────────────

class WideAndDeep(nn.Module):
    """
    Wide component: linear on raw sparse features (memorization)
    Deep component: MLP on dense embeddings (generalization)
    Output: concatenate wide + deep → final prediction
    """

    def __init__(self, wide_dim: int, deep_input_dim: int,
                 deep_dims: list, num_classes: int, dropout: float):
        super().__init__()

        # Wide: simple linear
        self.wide = nn.Linear(wide_dim, num_classes)

        # Deep: MLP
        deep_layers = []
        in_dim = deep_input_dim
        for h_dim in deep_dims:
            deep_layers.extend([
                nn.Linear(in_dim, h_dim),
                nn.BatchNorm1d(h_dim),
                nn.ReLU(),
                nn.Dropout(dropout),
            ])
            in_dim = h_dim
        self.deep = nn.Sequential(*deep_layers)
        self.deep_out = nn.Linear(in_dim, num_classes)

    def forward(self, x_wide, x_deep):
        wide_out = self.wide(x_wide)
        deep_out = self.deep_out(self.deep(x_deep))
        # Additive combination
        return wide_out + deep_out


# ── Data preparation ──────────────────────────────────────────

def load_and_prepare_data() -> tuple:
    log.info("Loading data...")
    users     = load_users()
    meal_logs = load_meal_logs(parse_dates=False)

    top_cuisine = derive_top_cuisine_per_user(meal_logs)
    df = users.merge(top_cuisine, on="user_id", how="inner")
    df = expand_conditions(df, "conditions")

    restriction_flags = ["vegetarian", "low_gi", "low_sodium", "no_dairy",
                         "no_gluten", "halal", "jain", "no_beef"]
    for flag in restriction_flags:
        df[f"restr_{flag}"] = df["dietary_restrictions"].fillna("").str.contains(
            flag, regex=False).astype(int)

    num_cols  = [c for c in COLD_START_FEATURES["numerical"]  if c in df.columns]
    cat_cols  = [c for c in COLD_START_FEATURES["categorical"] if c in df.columns]
    bin_cols  = [c for c in COLD_START_FEATURES["binary"]      if c in df.columns]
    cond_cols = [c for c in CONDITION_FLAGS if c in df.columns]
    restr_cols= [f"restr_{f}" for f in restriction_flags if f"restr_{f}" in df.columns]
    bin_cols  = list(set(bin_cols + cond_cols + restr_cols))

    df[num_cols] = df[num_cols].fillna(0)
    df[bin_cols] = df[bin_cols].fillna(0).astype(int)

    # ── Wide features: one-hot on key categoricals + binary ──
    wide_cat_cols = ["birthplace_state", "religion", "occupation", "income_tier"]
    wide_cat_cols = [c for c in wide_cat_cols if c in df.columns]

    ohe = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
    wide_cat_arr = ohe.fit_transform(df[wide_cat_cols].fillna("unknown").astype(str))
    wide_bin_arr = df[bin_cols].fillna(0).values.astype(np.float32)
    X_wide       = np.hstack([wide_cat_arr, wide_bin_arr]).astype(np.float32)

    # ── Deep features: scaled numerical + label-encoded categoricals ──
    encoder  = FeatureEncoder()
    df_enc   = encoder.fit_transform(df.copy(), cat_cols, num_cols)
    feat_cols = num_cols + cat_cols + bin_cols
    X_deep   = df_enc[feat_cols].fillna(0).values.astype(np.float32)

    # ── Y ────────────────────────────────────────────────────
    counts = df["top_cuisine"].value_counts()

    rare_classes = counts[counts < 10].index

    df["top_cuisine"] = (
        df["top_cuisine"]
        .replace(rare_classes, "other")
    )
    log.info(
        f"  Cuisine distribution after merge:\n"
        f"{df['top_cuisine'].value_counts()}"
    )
    y_encoder = LabelEncoder()
    y = y_encoder.fit_transform(df["top_cuisine"].fillna("north_indian"))

    log.info(f"  Wide dim: {X_wide.shape[1]} | Deep dim: {X_deep.shape[1]}")
    log.info(f"  Samples: {len(y):,} | Classes: {len(y_encoder.classes_)}")

    return X_wide, X_deep, y, feat_cols, encoder, ohe, y_encoder


def train():
    log.info("=" * 60)
    log.info("Cold Start — Wide and Deep (Best)")
    log.info("=" * 60)

    X_wide, X_deep, y, feat_cols, encoder, ohe, y_encoder = load_and_prepare_data()

    from sklearn.model_selection import train_test_split
    idx = np.arange(len(y))
    idx_tv, idx_test = train_test_split(idx, test_size=0.20, random_state=RANDOM_STATE, stratify=y)
    idx_train, idx_val = train_test_split(idx_tv, test_size=0.125, random_state=RANDOM_STATE, stratify=y[idx_tv])

    def to_loader(idx, shuffle=True):
        ds = TensorDataset(
            torch.FloatTensor(X_wide[idx]),
            torch.FloatTensor(X_deep[idx]),
            torch.LongTensor(y[idx]),
        )
        return DataLoader(ds, batch_size=WIDE_DEEP_PARAMS["batch_size"], shuffle=shuffle)

    train_loader = to_loader(idx_train)
    val_loader   = to_loader(idx_val,  shuffle=False)

    num_classes = len(y_encoder.classes_)
    device      = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    log.info(f"  Device: {device}")

    model = WideAndDeep(
        wide_dim      = X_wide.shape[1],
        deep_input_dim= X_deep.shape[1],
        deep_dims     = WIDE_DEEP_PARAMS["deep_dims"],
        num_classes   = num_classes,
        dropout       = WIDE_DEEP_PARAMS["dropout"],
    ).to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=WIDE_DEEP_PARAMS["lr"])
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=WIDE_DEEP_PARAMS["epochs"]
    )
    criterion = nn.CrossEntropyLoss()

    best_val_loss    = float("inf")
    patience_counter = 0
    best_state       = None

    for epoch in range(WIDE_DEEP_PARAMS["epochs"]):
        model.train()
        train_loss = 0.0
        for xw, xd, yb in train_loader:
            xw, xd, yb = xw.to(device), xd.to(device), yb.to(device)
            optimizer.zero_grad()
            logits = model(xw, xd)
            loss   = criterion(logits, yb)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_loss += loss.item()

        model.eval()
        val_loss  = 0.0
        val_preds = []
        with torch.no_grad():
            for xw, xd, yb in val_loader:
                xw, xd = xw.to(device), xd.to(device)
                logits  = model(xw, xd)
                loss    = criterion(logits.cpu(), yb)
                val_loss += loss.item()
                val_preds.extend(torch.argmax(logits, dim=1).cpu().numpy())

        avg_train = train_loss / len(train_loader)
        avg_val   = val_loss   / len(val_loader)
        scheduler.step()

        if (epoch + 1) % 10 == 0:
            val_acc = (np.array(val_preds) == y[idx_val]).mean()
            log.info(f"  Epoch {epoch+1:3d} | Train: {avg_train:.4f} | Val: {avg_val:.4f} | Val acc: {val_acc:.4f}")

        if avg_val < best_val_loss:
            best_val_loss    = avg_val
            best_state       = {k: v.clone() for k, v in model.state_dict().items()}
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= WIDE_DEEP_PARAMS["patience"]:
                log.info(f"  Early stopping at epoch {epoch+1}")
                break

    model.load_state_dict(best_state)

    # ── Test evaluation ───────────────────────────────────────
    model.eval()
    xw_t = torch.FloatTensor(X_wide[idx_test]).to(device)
    xd_t = torch.FloatTensor(X_deep[idx_test]).to(device)
    with torch.no_grad():
        test_probs = torch.softmax(model(xw_t, xd_t), dim=1).cpu().numpy()
    test_preds = np.argmax(test_probs, axis=1)

    test_pred_labels = y_encoder.inverse_transform(test_preds)
    test_true_labels = y_encoder.inverse_transform(y[idx_test])

    test_metrics = classification_metrics(test_true_labels, test_pred_labels, label="TEST")
    try:
        top3 = top_k_accuracy_score(y[idx_test], test_probs, k=3)
        test_metrics["top3_accuracy"] = round(top3, 4)
        log.info(f"[TEST] Top-3 accuracy: {top3:.4f}")
    except Exception:
        pass

    plot_confusion_matrix(
        test_true_labels, test_pred_labels,
        labels=list(y_encoder.classes_),
        title="Cold Start Wide&Deep — Confusion Matrix",
        filename="cold_start_wide_deep_cm.png",
    )

    os.makedirs(os.path.dirname(MODEL_PATHS["cold_start_wide_deep"]), exist_ok=True)
    torch.save({
        "model_state":  model.state_dict(),
        "wide_dim":     X_wide.shape[1],
        "deep_dim":     X_deep.shape[1],
        "deep_dims":    WIDE_DEEP_PARAMS["deep_dims"],
        "num_classes":  num_classes,
        "dropout":      WIDE_DEEP_PARAMS["dropout"],
        "feat_cols":    feat_cols,
        "y_classes":    list(y_encoder.classes_),
        "test_metrics": test_metrics,
    }, MODEL_PATHS["cold_start_wide_deep"])

    save_metrics({"test": test_metrics}, "cold_start_wide_deep")

    log.info("\n" + "=" * 60)
    log.info("SUMMARY — Cold Start Wide and Deep")
    log.info(f"  Test Accuracy  : {test_metrics['accuracy']}")
    log.info(f"  Test Top-3 Acc : {test_metrics.get('top3_accuracy', 'n/a')}")
    log.info(f"  Test F1        : {test_metrics['f1']}")
    log.info(f"  Model saved    : {MODEL_PATHS['cold_start_wide_deep']}")
    log.info("=" * 60)

    return model, test_metrics


if __name__ == "__main__":
    train()