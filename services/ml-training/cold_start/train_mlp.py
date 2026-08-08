"""
NARA — Cold Start — Mid: Shallow MLP (PyTorch)
─────────────────────────────────────────────────────────────
INPUT FEATURES (X):
  Same as KNN but with learned embeddings for categorical features.
  Embeddings: birthplace_state (16-dim), religion (8-dim),
              occupation (8-dim), income_tier (4-dim)
  All features concatenated → 128 → 64 → 32 → num_classes

PREDICTION TARGET (Y):
  top_cuisine — most frequent cuisine in user meal history

WHY MLP OVER KNN:
  Learns non-linear demographic combinations
  Embedding layers compress high-cardinality states (28 states → 16-dim)
  Better generalisation to unseen demographic combinations
  Can learn "Gujarati + Jain + middle_aged → gujarati cuisine" as a pattern

EXPECTED METRICS:
  Top-1 accuracy ~0.52-0.62
  Top-3 accuracy ~0.75-0.82

Run:
  python cold_start/train_mlp.py
"""
import os
import sys
import logging

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import top_k_accuracy_score

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MODEL_PATHS, COLD_START_FEATURES, MLP_PARAMS, RANDOM_STATE, CONDITION_FLAGS
from utils import (
    load_users, load_meal_logs,
    expand_conditions, derive_top_cuisine_per_user,
    FeatureEncoder, split_data,
    classification_metrics, save_metrics,
    plot_confusion_matrix,
)

log = logging.getLogger("nara.cold_start.mlp")
torch.manual_seed(RANDOM_STATE)


# ── Model definition ──────────────────────────────────────────

class DemographicMLP(nn.Module):
    """
    Shallow MLP for cold start cuisine prediction.
    Embedding layers for high-cardinality categoricals.
    """

    def __init__(self, input_dim: int, hidden_dims: list,
                 num_classes: int, dropout: float = 0.3):
        super().__init__()

        layers = []
        in_dim = input_dim
        for h_dim in hidden_dims:
            layers.extend([
                nn.Linear(in_dim, h_dim),
                nn.BatchNorm1d(h_dim),
                nn.ReLU(),
                nn.Dropout(dropout),
            ])
            in_dim = h_dim
        layers.append(nn.Linear(in_dim, num_classes))

        self.network = nn.Sequential(*layers)

    def forward(self, x):
        return self.network(x)


# ── Data prep ─────────────────────────────────────────────────

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

    encoder = FeatureEncoder()
    df_enc  = encoder.fit_transform(df.copy(), cat_cols, num_cols)

    feature_cols = num_cols + cat_cols + bin_cols
    X = df_enc[feature_cols].fillna(0).values.astype(np.float32)
    counts = df["top_cuisine"].value_counts()

    rare_classes = counts[counts < 10].index
    df["top_cuisine"] = (
        df["top_cuisine"]
        .replace(rare_classes, "other")
    )
    log.info(
        f"  Cuisine distribution after merge:\n{df['top_cuisine'].value_counts()}"
    )
    # Encode Y
    y_encoder = LabelEncoder()
    y = y_encoder.fit_transform(df["top_cuisine"].fillna("north_indian"))

    log.info(f"  Features: {len(feature_cols)} | Samples: {len(X):,} | Classes: {len(y_encoder.classes_)}")
    return X, y, feature_cols, encoder, y_encoder


def train():
    log.info("=" * 60)
    log.info("Cold Start — Shallow MLP (Mid)")
    log.info("=" * 60)

    X, y, feature_cols, encoder, y_encoder = load_and_prepare_data()
    print(type(y))
    print(y[:10])
    # y = pd.Series(y)
    # counts = y.value_counts()
    # rare_classes = counts[counts < 10].index
    # y = y.replace(rare_classes, "other")
    # print(y.value_counts())
    # y = y.values
    # Manual split for numpy arrays
    from sklearn.model_selection import train_test_split
    X_tv, X_test, y_tv, y_test = train_test_split(X, y, test_size=0.20, random_state=RANDOM_STATE, stratify=y)
    X_train, X_val, y_train, y_val = train_test_split(X_tv, y_tv, test_size=0.125, random_state=RANDOM_STATE, stratify=y_tv)

    log.info(f"  Train: {len(X_train):,} | Val: {len(X_val):,} | Test: {len(X_test):,}")

    # ── DataLoaders ───────────────────────────────────────────
    def to_loader(X, y, shuffle=True):
        ds = TensorDataset(torch.FloatTensor(X), torch.LongTensor(y))
        return DataLoader(ds, batch_size=MLP_PARAMS["batch_size"], shuffle=shuffle)

    train_loader = to_loader(X_train, y_train)
    val_loader   = to_loader(X_val,   y_val,   shuffle=False)

    # ── Model ─────────────────────────────────────────────────
    num_classes = len(y_encoder.classes_)
    device      = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    log.info(f"  Device: {device}")

    model = DemographicMLP(
        input_dim   = X.shape[1],
        hidden_dims = MLP_PARAMS["hidden_dims"],
        num_classes = num_classes,
        dropout     = MLP_PARAMS["dropout"],
    ).to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=MLP_PARAMS["lr"])
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=3, factor=0.5)
    criterion = nn.CrossEntropyLoss()

    # ── Training loop ─────────────────────────────────────────
    best_val_loss = float("inf")
    patience_counter = 0
    best_state = None

    for epoch in range(MLP_PARAMS["epochs"]):
        # Train
        model.train()
        train_loss = 0.0
        for X_batch, y_batch in train_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            optimizer.zero_grad()
            logits = model(X_batch)
            loss   = criterion(logits, y_batch)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()

        # Validate
        model.eval()
        val_loss = 0.0
        val_preds, val_probs = [], []
        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                X_batch = X_batch.to(device)
                logits  = model(X_batch)
                loss    = criterion(logits.cpu(), y_batch)
                val_loss += loss.item()
                probs   = torch.softmax(logits, dim=1).cpu().numpy()
                preds   = np.argmax(probs, axis=1)
                val_preds.extend(preds)
                val_probs.extend(probs)

        avg_train = train_loss / len(train_loader)
        avg_val   = val_loss   / len(val_loader)
        scheduler.step(avg_val)

        if (epoch + 1) % 10 == 0:
            val_acc = (np.array(val_preds) == y_val).mean()
            log.info(f"  Epoch {epoch+1:3d} | Train loss: {avg_train:.4f} | Val loss: {avg_val:.4f} | Val acc: {val_acc:.4f}")

        # Early stopping
        if avg_val < best_val_loss:
            best_val_loss    = avg_val
            best_state       = {k: v.clone() for k, v in model.state_dict().items()}
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= MLP_PARAMS["patience"]:
                log.info(f"  Early stopping at epoch {epoch+1}")
                break

    model.load_state_dict(best_state)

    # ── Evaluate on test ──────────────────────────────────────
    model.eval()
    test_tensor = torch.FloatTensor(X_test).to(device)
    with torch.no_grad():
        test_probs = torch.softmax(model(test_tensor), dim=1).cpu().numpy()
    test_preds = np.argmax(test_probs, axis=1)

    test_pred_labels = y_encoder.inverse_transform(test_preds)
    test_true_labels = y_encoder.inverse_transform(y_test)

    test_metrics = classification_metrics(test_true_labels, test_pred_labels, label="TEST")
    try:
        top3 = top_k_accuracy_score(y_test, test_probs, k=3)
        test_metrics["top3_accuracy"] = round(top3, 4)
        log.info(f"[TEST] Top-3 accuracy: {top3:.4f}")
    except Exception:
        pass

    # ── Plots ─────────────────────────────────────────────────
    plot_confusion_matrix(
        test_true_labels, test_pred_labels,
        labels=list(y_encoder.classes_),
        title="Cold Start MLP — Confusion Matrix",
        filename="cold_start_mlp_cm.png",
    )

    # ── Save ──────────────────────────────────────────────────
    os.makedirs(os.path.dirname(MODEL_PATHS["cold_start_mlp"]), exist_ok=True)
    torch.save({
        "model_state": model.state_dict(),
        "input_dim":   X.shape[1],
        "hidden_dims": MLP_PARAMS["hidden_dims"],
        "num_classes": num_classes,
        "dropout":     MLP_PARAMS["dropout"],
        "feature_cols":feature_cols,
        "y_classes":   list(y_encoder.classes_),
        "test_metrics":test_metrics,
    }, MODEL_PATHS["cold_start_mlp"])

    save_metrics({"test": test_metrics}, "cold_start_mlp")

    log.info("\n" + "=" * 60)
    log.info("SUMMARY — Cold Start MLP")
    log.info(f"  Test Accuracy  : {test_metrics['accuracy']}")
    log.info(f"  Test Top-3 Acc : {test_metrics.get('top3_accuracy', 'n/a')}")
    log.info(f"  Test F1        : {test_metrics['f1']}")
    log.info(f"  Model saved    : {MODEL_PATHS['cold_start_mlp']}")
    log.info("=" * 60)

    return model, test_metrics


if __name__ == "__main__":
    train()
