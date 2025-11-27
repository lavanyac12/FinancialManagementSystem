"""
train_classifier.py
Train a TF-IDF + LogisticRegression classifier on a local CSV of transactions.

CSV must contain columns: `description` and `category_id` (category_id should match your DB keys).

Example:
  python backend/train_classifier.py --csv /path/to/my_training.csv --model-out backend/models/tx_category_model.joblib

"""
import argparse
import os
from pathlib import Path
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib


def build_and_train(csv_path: str, model_out: str, test_size: float = 0.15, random_state: int = 42, min_df: int = 2, use_all: bool = False):
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise RuntimeError(f"Training CSV not found at {csv_path}")

    df = pd.read_csv(csv_path)
    # Normalize column names to find description and category columns 
    col_map = {c.lower(): c for c in df.columns}
    desc_col = None
    cat_col = None
    for candidate in ("description", "desc", "transaction description", "details"):
        if candidate in col_map:
            desc_col = col_map[candidate]
            break
    for candidate in ("category_id", "category", "cat", "label"):
        if candidate in col_map:
            cat_col = col_map[candidate]
            break

    # fallback: try to detect columns containing keywords
    if desc_col is None:
        for c in df.columns:
            if "desc" in c.lower() or "description" in c.lower() or "detail" in c.lower():
                desc_col = c
                break
    if cat_col is None:
        for c in df.columns:
            if "cat" in c.lower() or "category" in c.lower() or "label" in c.lower():
                cat_col = c
                break

    if desc_col is None or cat_col is None:
        raise RuntimeError(f"Could not find description/category columns. Detected columns: {list(df.columns)}")

    # rename to expected names
    df = df.rename(columns={desc_col: "description", cat_col: "category_id"})
    df = df.dropna(subset=["description", "category_id"]).astype({"description": str, "category_id": str})
    if df.empty:
        raise RuntimeError("No rows found in training CSV after filtering")

    X = df["description"].astype(str)
    y = df["category_id"].astype(str)

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), lowercase=True, min_df=min_df)),
        ("clf", LogisticRegression(max_iter=2000, class_weight="balanced")),
    ])

    if use_all:
        # Report cross-validated score if dataset is large enough
        from sklearn.model_selection import StratifiedKFold, cross_val_score

        n_samples = len(y)
        n_splits = min(5, n_samples) if n_samples >= 2 else 0
        if n_splits >= 2:
            cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
            print(f"Computing {n_splits}-fold cross-validated F1 (macro) before fitting on full data...")
            scores = cross_val_score(pipeline, X, y, cv=cv, scoring="f1_macro", n_jobs=-1)
            print(f"CV F1 macro: mean={scores.mean():.4f}, std={scores.std():.4f}")
        else:
            print("Not enough samples for cross-validation; skipping CV reporting.")

        print("Training classifier on the entire dataset...")
        pipeline.fit(X, y)
    else:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=random_state, stratify=y)
        print("Training classifier...")
        pipeline.fit(X_train, y_train)
        preds = pipeline.predict(X_test)
        print("Evaluation on held-out test set:")
        print(classification_report(y_test, preds))

    model_out = Path(model_out)
    model_out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, model_out)
    print(f"Saved model to {model_out}")


def parse_args():
    p = argparse.ArgumentParser(description="Train transaction category classifier")
    p.add_argument("--csv", required=True, help="Path to training CSV with `description` and `category_id` columns")
    p.add_argument("--model-out", default="backend/models/tx_category_model.joblib", help="Where to write the trained model")
    p.add_argument("--test-size", type=float, default=0.15)
    p.add_argument("--random-state", type=int, default=42)
    p.add_argument("--min-df", type=int, default=2, help="min_df for TF-IDF vectorizer")
    p.add_argument("--use-all", action="store_true", help="Train on the entire CSV (no held-out test); runs CV if possible before fitting)")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    build_and_train(args.csv, args.model_out, test_size=args.test_size, random_state=args.random_state, min_df=args.min_df, use_all=args.use_all)
