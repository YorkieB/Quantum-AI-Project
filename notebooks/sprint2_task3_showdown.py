#!/usr/bin/env python3
"""
Sprint 3 Showdown — Quantum vs Classical on Agent Identification
Uses TreeReader (offline, no download needed) instead of BobcatParser.
"""

import json, time, random, warnings, sys
import numpy as np
from collections import Counter

warnings.filterwarnings("ignore")


def load_dataset(path="sprint2_task3_dataset.json"):
    with open(path) as f:
        return json.load(f)


def balanced_subset(data, n=80, seed=42):
    random.seed(seed)
    np.random.seed(seed)
    by_label = {}
    for item in data:
        by_label.setdefault(item["label"], []).append(item)
    labels = sorted(by_label)
    per_class = n // len(labels)
    remainder = n % len(labels)
    subset = []
    for i, lbl in enumerate(labels):
        k = per_class + (1 if i < remainder else 0)
        subset.extend(random.sample(by_label[lbl], min(k, len(by_label[lbl]))))
    random.shuffle(subset)
    return subset


def acc_fn(y_hat, y):
    return np.mean(np.argmax(y_hat, axis=1) == np.argmax(y, axis=1))


def run_classical(train, val, test):
    from sklearn.linear_model import LogisticRegression
    from sklearn.svm import SVC
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import LabelEncoder

    print(f"[Classical] Training on {len(train)} sentences (full set)")

    X_tr = [d["text"] for d in train]
    y_tr = [d["label"] for d in train]
    X_va = [d["text"] for d in val]
    y_va = [d["label"] for d in val]
    X_te = [d["text"] for d in test]
    y_te = [d["label"] for d in test]

    le = LabelEncoder()
    y_tr_enc = le.fit_transform(y_tr)
    y_va_enc = le.transform(y_va)
    y_te_enc = le.transform(y_te)

    configs = [
        ("TF-IDF + LogReg",     TfidfVectorizer(), LogisticRegression(max_iter=1000, C=1.0)),
        ("TF-IDF + SVM-linear", TfidfVectorizer(), SVC(kernel="linear", probability=True)),
        ("TF-IDF + SVM-rbf",    TfidfVectorizer(), SVC(kernel="rbf",    probability=True)),
    ]

    try:
        import spacy
        nlp = spacy.load("en_core_web_md")
        def spacy_feats(texts):
            return np.array([nlp(t).vector for t in texts])
        spacy_X_tr = spacy_feats(X_tr)
        spacy_X_va = spacy_feats(X_va)
        spacy_X_te = spacy_feats(X_te)
        spacy_configs = [
            ("spaCy + LogReg",  LogisticRegression(max_iter=1000)),
            ("spaCy + SVM-rbf", SVC(kernel="rbf", probability=True)),
        ]
    except Exception:
        print("  [warn] spaCy en_core_web_md not found -- skipping")
        spacy_configs = []

    results = []
    for name, vec, clf in configs:
        t0 = time.time()
        pipe = Pipeline([("vec", vec), ("clf", clf)])
        pipe.fit(X_tr, y_tr_enc)
        elapsed = time.time() - t0
        tr_acc = pipe.score(X_tr, y_tr_enc)
        va_acc = pipe.score(X_va, y_va_enc)
        te_acc = pipe.score(X_te, y_te_enc)
        proba  = pipe.predict_proba(X_te).max(axis=1).mean()
        results.append({"method": name, "train_acc": round(tr_acc,4),
                        "val_acc": round(va_acc,4), "test_acc": round(te_acc,4),
                        "confidence": round(proba,4), "time": round(elapsed,3),
                        "train_size": len(train)})
        print(f"  {name:22s} | test={te_acc:.4f} | conf={proba:.4f} | {elapsed:.3f}s")

    for name, clf in spacy_configs:
        t0 = time.time()
        clf.fit(spacy_X_tr, y_tr_enc)
        elapsed = time.time() - t0
        tr_acc = clf.score(spacy_X_tr, y_tr_enc)
        va_acc = clf.score(spacy_X_va, y_va_enc)
        te_acc = clf.score(spacy_X_te, y_te_enc)
        proba  = clf.predict_proba(spacy_X_te).max(axis=1).mean()
        results.append({"method": name, "train_acc": round(tr_acc,4),
                        "val_acc": round(va_acc,4), "test_acc": round(te_acc,4),
                        "confidence": round(proba,4), "time": round(elapsed,3),
                        "train_size": len(train)})
        print(f"  {name:22s} | test={te_acc:.4f} | conf={proba:.4f} | {elapsed:.3f}s")

    return results


def run_quantum(train_all, val, test, n_qubits_runs=[1,2,3],
                train_n=80, epochs=80, lr=0.05, batch_size=30):
    from lambeq import (TreeReader, TreeReaderMode, SpiderAnsatz, AtomicType,
                        NumpyModel, QuantumTrainer, Dataset, CrossEntropyLoss)

    reader = TreeReader(mode=TreeReaderMode.RULE_ONLY)
    N, S   = AtomicType.NOUN, AtomicType.SENTENCE

    q_train = balanced_subset(train_all, n=train_n)
    label_set = sorted(set(d["label"] for d in train_all))
    n_classes  = len(label_set)
    lbl2idx    = {l: i for i, l in enumerate(label_set)}

    print(f"[Quantum] Training on {len(q_train)} balanced sentences (of {len(train_all)})")
    print(f"  Labels ({n_classes}): {label_set}")
    print(f"  Config: {epochs} epochs, lr={lr}, batch={batch_size}")
    print(f"  Parser: TreeReader (RULE_ONLY mode, offline)")

    def encode_labels(data):
        oh = np.zeros((len(data), n_classes))
        for i, d in enumerate(data):
            oh[i, lbl2idx[d["label"]]] = 1
        return oh

    def parse_and_align(data, tag=""):
        texts = [d["text"] for d in data]
        diags = reader.sentences2diagrams(texts, suppress_exceptions=True)
        paired = [(d, item) for d, item in zip(diags, data) if d is not None]
        if paired:
            diags_clean, items_clean = zip(*paired)
        else:
            diags_clean, items_clean = [], []
        labels = encode_labels(items_clean)
        n_fail = len(data) - len(diags_clean)
        if n_fail:
            print(f"  [{tag}] {n_fail}/{len(data)} sentences failed parsing")
        return list(diags_clean), labels

    print("  Parsing diagrams ...")
    tr_diags, tr_labels = parse_and_align(q_train, "train")
    va_diags, va_labels = parse_and_align(val, "val")
    te_diags, te_labels = parse_and_align(test, "test")
    print(f"  Parsed: {len(tr_diags)} train / {len(va_diags)} val / {len(te_diags)} test")

    if len(tr_diags) == 0:
        print("  ERROR: No diagrams parsed. Cannot train quantum model.")
        return []

    results = []
    for nq in n_qubits_runs:
        print(f"\n  -- Quantum N={nq} --")
        ansatz = SpiderAnsatz({N: nq, S: nq})

        tr_circs = [ansatz(d) for d in tr_diags]
        va_circs = [ansatz(d) for d in va_diags]
        te_circs = [ansatz(d) for d in te_diags]

        all_circs = tr_circs + va_circs + te_circs
        model = NumpyModel.from_diagrams(all_circs)
        n_params = len(model.weights)
        print(f"  Parameters: {n_params}")

        trainer = QuantumTrainer(
            model=model,
            loss_function=CrossEntropyLoss(),
            epochs=epochs,
            optimizer="SPSAOptimizer",
            optim_hyperparams={"a": lr, "c": 0.06, "A": 0.01 * epochs},
            evaluate_functions={"acc": acc_fn},
            evaluate_on_train=True,
            verbose="text",
            seed=nq * 42,
        )

        tr_dataset = Dataset(tr_circs, tr_labels, batch_size=batch_size)
        va_dataset = Dataset(va_circs, va_labels)
        te_dataset = Dataset(te_circs, te_labels)

        t0 = time.time()
        trainer.fit(tr_dataset, va_dataset, log_interval=10)
        elapsed = time.time() - t0

        preds = model(te_circs)
        te_acc = float(np.mean(np.argmax(preds, axis=1) == np.argmax(te_labels, axis=1)))
        conf   = float(preds.max(axis=1).mean())

        tr_preds = model(tr_circs)
        tr_acc = float(np.mean(np.argmax(tr_preds, axis=1) == np.argmax(tr_labels, axis=1)))

        va_preds = model(va_circs)
        va_acc = float(np.mean(np.argmax(va_preds, axis=1) == np.argmax(va_labels, axis=1)))

        results.append({
            "method":     f"Quantum N={nq}",
            "train_acc":  round(tr_acc, 4),
            "val_acc":    round(va_acc, 4),
            "test_acc":   round(te_acc, 4),
            "confidence": round(conf, 4),
            "time":       round(elapsed, 1),
            "n_params":   n_params,
            "train_size": len(tr_circs),
        })
        print(f"  Result: train={tr_acc:.4f} val={va_acc:.4f} test={te_acc:.4f} conf={conf:.4f} time={elapsed:.1f}s")

    return results


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--data",        default="sprint2_task3_dataset.json")
    ap.add_argument("--out",         default="sprint3_showdown_results.json")
    ap.add_argument("--q-train-n",   type=int,   default=80)
    ap.add_argument("--epochs",      type=int,   default=80)
    ap.add_argument("--lr",          type=float, default=0.05)
    ap.add_argument("--batch-size",  type=int,   default=30)
    ap.add_argument("--q-runs",      nargs="+",  type=int, default=[1,2,3])
    ap.add_argument("--skip-quantum",   action="store_true")
    ap.add_argument("--skip-classical", action="store_true")
    args = ap.parse_args()

    data = load_dataset(args.data)
    train, val, test = data["train"], data["val"], data["test"]

    print("=" * 60)
    print("SPRINT 3 SHOWDOWN -- Agent Identification (Syntax-Dependent)")
    print("=" * 60)
    print(f"Dataset: {len(train)} train / {len(val)} val / {len(test)} test")
    labels = sorted(set(d["label"] for d in train))
    print(f"Labels ({len(labels)}): {labels}")
    print(f"Random chance: {1/len(labels):.4f}")
    print(f"Quantum config: {args.q_train_n} train, {args.epochs} epochs, lr={args.lr}")
    print("=" * 60)

    results = {"classical": [], "quantum": [], "metadata": {
        "dataset": args.data,
        "n_labels": len(labels),
        "labels": labels,
        "chance": round(1/len(labels), 4),
        "quantum_config": {"train_n": args.q_train_n, "epochs": args.epochs,
                           "lr": args.lr, "batch_size": args.batch_size},
    }}

    if not args.skip_classical:
        results["classical"] = run_classical(train, val, test)

    if not args.skip_quantum:
        results["quantum"] = run_quantum(
            train_all=train, val=val, test=test,
            n_qubits_runs=args.q_runs,
            train_n=args.q_train_n,
            epochs=args.epochs,
            lr=args.lr,
            batch_size=args.batch_size,
        )

    with open(args.out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved -> {args.out}")

    chance = 1/len(labels)
    print(f"\n{'='*60}")
    print(f"SUMMARY (chance = {chance:.1%})")
    print(f"{'='*60}")
    print(f"{'Method':24s} {'Train':>8s} {'Val':>8s} {'Test':>8s} {'Time':>8s}")
    print("-" * 60)
    for r in results["classical"] + results["quantum"]:
        marker = "+" if r["test_acc"] > chance * 2 else "~" if r["test_acc"] > chance else "x"
        print(f"{marker} {r['method']:22s} {r['train_acc']:8.4f} {r['val_acc']:8.4f} {r['test_acc']:8.4f} {r['time']:>7}s")
    print(f"\nKey: + = above 2x chance | ~ = above chance | x = at/below chance")


if __name__ == "__main__":
    main()
