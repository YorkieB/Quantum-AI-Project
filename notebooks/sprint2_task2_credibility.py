#!/usr/bin/env python3
"""
Sprint 2, Task 2.2: Classical Credibility Classifier
======================================================
Jarvis Quantum - Module 4 (Credibility Verifier) baseline

Dataset: Synthetic credibility dataset with linguistic features
  - REAL (0): Factual, measured, sourced claims
  - FAKE (1): Sensational, emotional, unsourced claims

Classical approach: Extract linguistic features + sklearn classifiers
This sets the bar for the quantum credibility verifier.
"""

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import json
import os
import time
import random
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.preprocessing import StandardScaler
import spacy

random.seed(42)
np.random.seed(42)

print("Loading spaCy...")
nlp = spacy.load("en_core_web_sm")

# ================================================================
# PART 1: BUILD CREDIBILITY DATASET
# ================================================================
print("\nGenerating credibility dataset...")

# REAL news patterns — measured, specific, sourced
real_templates = [
    "According to {source}, {topic} {measured_verb} by {percent} percent in {timeframe}.",
    "A study published in {journal} found that {topic} {measured_verb} {quantity}.",
    "The {org} reported that {topic} {past_verb} during {timeframe}.",
    "{expert} from {university} stated that {topic} remains {adjective_neutral}.",
    "Data from {source} shows {topic} has {changed} by {quantity} since {year}.",
    "Research conducted by {university} suggests {topic} may {measured_verb} over {timeframe}.",
    "Officials at {org} confirmed that {topic} {past_verb} as expected.",
    "The latest figures from {source} indicate {topic} {measured_verb} {quantity} this {timeframe}.",
    "A report by {org} found {percent} percent of {group} experienced {topic}.",
    "In a peer reviewed study {expert} demonstrated that {topic} {measured_verb} {quantity}.",
    "Government statistics show {topic} {changed} gradually over {timeframe}.",
    "The {org} analysis revealed a {adjective_neutral} trend in {topic}.",
    "Published data confirms {topic} {past_verb} within normal parameters.",
    "Experts at {university} observed that {topic} {measured_verb} as predicted.",
    "The annual {org} survey found {topic} {changed} by {percent} percent.",
    "Independent auditors verified that {topic} {past_verb} according to standards.",
    "A meta analysis of {quantity} studies concluded {topic} shows {adjective_neutral} results.",
    "Quarterly earnings reports show {topic} {measured_verb} by {percent} percent.",
    "Census data indicates {topic} {changed} steadily in recent {timeframe}.",
    "Clinical trials published in {journal} demonstrated {topic} {measured_verb} {quantity}.",
]

fake_templates = [
    "BREAKING: {topic} will {extreme_verb} {extreme_amount} and nobody is talking about it!",
    "They don't want you to know that {topic} is {extreme_adj} {extreme_amount}!",
    "EXPOSED: The truth about {topic} that {group} are hiding from you!",
    "SHOCKING: {topic} could {extreme_verb} everything we know about {vague_topic}!",
    "Scientists BAFFLED as {topic} {extreme_verb} beyond all expectations!!!",
    "You won't BELIEVE what {topic} really means for {group}!",
    "SECRET documents reveal {topic} has been {extreme_adj} all along!",
    "ALERT: {topic} is about to {extreme_verb} and the media is silent!",
    "Exposed: {group} exposed for covering up {topic}!",
    "URGENT: {topic} {extreme_verb} overnight and experts are STUNNED!",
    "The real reason {topic} is {extreme_adj} will shock you!",
    "Exposed: {topic} is a complete {negative_noun} designed to fool {group}!",
    "WAKE UP: {topic} proves everything {group} told you is a LIE!",
    "Exposed: the {extreme_adj} truth about {topic} finally revealed!",
    "MUST READ: {topic} {extreme_verb} and it changes everything!",
    "Exposed: every single thing about {topic} is {extreme_adj}!",
    "{topic} exposed: the biggest {negative_noun} in history!",
    "INSANE: {topic} just {extreme_verb} and nobody can explain why!!!",
    "This ONE fact about {topic} destroys everything {group} believe!",
    "WARNING: {topic} is {extreme_adj} and getting worse every day!",
]

# Fill-in values
sources = ["the Office for National Statistics", "the World Health Organisation",
           "the Bureau of Labor Statistics", "Reuters", "the Federal Reserve",
           "the European Central Bank", "the Census Bureau", "Bloomberg",
           "the Department of Health", "the National Science Foundation"]

journals = ["Nature", "The Lancet", "Science", "the British Medical Journal",
            "the Journal of Finance", "PNAS", "Cell", "the New England Journal of Medicine"]

orgs = ["World Bank", "International Monetary Fund", "United Nations",
        "Federal Reserve", "European Commission", "National Health Service",
        "Centers for Disease Control", "Environmental Protection Agency"]

universities = ["Oxford University", "MIT", "Stanford", "Cambridge University",
                "Harvard Medical School", "ETH Zurich", "Imperial College London"]

experts = ["Professor Smith", "Dr Chen", "Professor Williams", "Dr Patel",
           "Professor Jones", "Dr Nguyen", "Professor Garcia", "Dr Kim"]

topics_cred = [
    "inflation", "unemployment", "housing prices", "renewable energy adoption",
    "vaccine efficacy", "carbon emissions", "GDP growth", "literacy rates",
    "life expectancy", "crime rates", "internet adoption", "food prices",
    "electric vehicle sales", "average wages", "healthcare spending",
    "education funding", "trade volumes", "population growth",
    "renewable capacity", "manufacturing output", "consumer spending",
    "interest rates", "productivity levels", "research funding",
]

vague_topics = ["the economy", "public health", "the environment", "society",
                "the future", "our way of life", "the truth", "reality"]

groups = ["the government", "big corporations", "mainstream media", "politicians",
          "the establishment", "the elites", "the authorities", "the experts"]

measured_verbs = ["increased", "decreased", "improved", "declined",
                  "stabilised", "fluctuated", "grew", "fell", "rose"]
past_verbs = ["performed", "changed", "developed", "progressed",
              "remained stable", "shifted", "evolved", "adjusted"]
changed = ["increased", "decreased", "shifted", "changed", "evolved"]

extreme_verbs = ["destroy", "collapse", "explode", "skyrocket", "crash",
                 "obliterate", "shatter", "devastate", "transform", "revolutionise"]
extreme_adj = ["catastrophic", "devastating", "unbelievable", "terrifying",
               "mind blowing", "earth shattering", "outrageous", "insane",
               "horrifying", "unprecedented"]
negative_nouns = ["scam", "hoax", "fraud", "lie", "conspiracy", "coverup",
                  "deception", "scheme", "swindle"]

adjective_neutral = ["stable", "moderate", "gradual", "consistent",
                     "steady", "measured", "modest", "incremental"]

percents = ["2.3", "5.1", "0.8", "3.7", "12", "7.4", "1.6", "4.2", "8.9", "15"]
quantities = ["significantly", "marginally", "substantially", "slightly",
              "moderately", "noticeably", "measurably"]
years = ["2020", "2021", "2022", "2023", "2024", "2025"]
timeframes = ["the past year", "the last quarter", "recent months",
              "the last decade", "the first half of the year", "the past five years"]
extreme_amounts = ["more than anyone predicted", "beyond imagination",
                   "faster than ever before", "at an alarming rate"]


def fill_credibility(template):
    s = template
    s = s.replace("{source}", random.choice(sources))
    s = s.replace("{journal}", random.choice(journals))
    s = s.replace("{org}", random.choice(orgs))
    s = s.replace("{university}", random.choice(universities))
    s = s.replace("{expert}", random.choice(experts))
    s = s.replace("{topic}", random.choice(topics_cred))
    s = s.replace("{vague_topic}", random.choice(vague_topics))
    s = s.replace("{group}", random.choice(groups))
    s = s.replace("{measured_verb}", random.choice(measured_verbs))
    s = s.replace("{past_verb}", random.choice(past_verbs))
    s = s.replace("{changed}", random.choice(changed))
    s = s.replace("{extreme_verb}", random.choice(extreme_verbs))
    s = s.replace("{extreme_adj}", random.choice(extreme_adj))
    s = s.replace("{extreme_amount}", random.choice(extreme_amounts))
    s = s.replace("{negative_noun}", random.choice(negative_nouns))
    s = s.replace("{adjective_neutral}", random.choice(adjective_neutral))
    s = s.replace("{percent}", random.choice(percents))
    s = s.replace("{quantity}", random.choice(quantities))
    s = s.replace("{year}", random.choice(years))
    s = s.replace("{timeframe}", random.choice(timeframes))
    return s


# Generate sentences
TARGET = 400
real_sentences = list(dict.fromkeys(
    [fill_credibility(random.choice(real_templates)) for _ in range(TARGET * 3)]
))[:TARGET]
fake_sentences = list(dict.fromkeys(
    [fill_credibility(random.choice(fake_templates)) for _ in range(TARGET * 3)]
))[:TARGET]

print(f"  Generated: {len(real_sentences)} REAL, {len(fake_sentences)} FAKE")

# Combine and split
all_data = [(s, 0) for s in real_sentences] + [(s, 1) for s in fake_sentences]
random.shuffle(all_data)

n = len(all_data)
n_train = int(n * 0.70)
n_val = int(n * 0.15)

train_data = all_data[:n_train]
val_data = all_data[n_train:n_train + n_val]
test_data = all_data[n_train + n_val:]

train_sents = [s for s, l in train_data]
train_labels = np.array([l for s, l in train_data])
val_sents = [s for s, l in val_data]
val_labels = np.array([l for s, l in val_data])
test_sents = [s for s, l in test_data]
test_labels = np.array([l for s, l in test_data])

print(f"  Train: {len(train_data)} | Val: {len(val_data)} | Test: {len(test_data)}")

# Save dataset
os.makedirs("data", exist_ok=True)
cred_dataset = {
    "description": "Jarvis Credibility Dataset v1 - Real vs Fake claims",
    "classes": {"0": "REAL", "1": "FAKE"},
    "train": [{"sentence": s, "label": l} for s, l in train_data],
    "val": [{"sentence": s, "label": l} for s, l in val_data],
    "test": [{"sentence": s, "label": l} for s, l in test_data],
}
with open("data/jarvis_credibility_v1.json", "w") as f:
    json.dump(cred_dataset, f, indent=2)

# ================================================================
# PART 2: FEATURE ENGINEERING
# ================================================================
print("\nExtracting features...")

def extract_features(sentences):
    """Extract linguistic credibility features."""
    features = []
    for sent in sentences:
        doc = nlp(sent)
        text = sent

        # Surface features
        n_words = len(text.split())
        n_chars = len(text)
        n_caps = sum(1 for c in text if c.isupper())
        caps_ratio = n_caps / max(n_chars, 1)
        n_exclaim = text.count('!')
        n_question = text.count('?')
        n_allcaps_words = sum(1 for w in text.split() if w.isupper() and len(w) > 1)

        # Punctuation intensity
        n_punct = sum(1 for c in text if c in '!?.:;,')
        punct_ratio = n_punct / max(n_words, 1)

        # Emotional/sensational indicators
        sensational_words = [
            'shocking', 'breaking', 'exposed', 'secret', 'urgent',
            'alert', 'destroy', 'collapse', 'explode', 'insane',
            'devastating', 'unbelievable', 'terrifying', 'horrifying',
            'scam', 'hoax', 'fraud', 'lie', 'conspiracy', 'coverup',
            'wake up', 'must read', 'you won\'t believe', 'baffled',
            'stunned', 'shatter', 'obliterate', 'mind blowing',
            'earth shattering', 'outrageous', 'unprecedented',
        ]
        text_lower = text.lower()
        n_sensational = sum(1 for w in sensational_words if w in text_lower)

        # Credibility indicators
        credibility_words = [
            'according to', 'study', 'research', 'data', 'report',
            'published', 'professor', 'university', 'percent',
            'statistics', 'survey', 'analysis', 'peer reviewed',
            'clinical', 'findings', 'evidence', 'demonstrated',
            'observed', 'confirmed', 'verified', 'measured',
            'journal', 'quarterly', 'annual', 'census',
        ]
        n_credibility = sum(1 for w in credibility_words if w in text_lower)

        # Vague vs specific language
        vague_words = ['everything', 'everyone', 'nobody', 'always', 'never',
                       'all', 'nothing', 'completely', 'totally', 'entire']
        n_vague = sum(1 for w in vague_words if w in text_lower)

        # Named entities (real news tends to cite specifics)
        n_entities = len(doc.ents)

        # Numbers (real news has specific figures)
        n_numbers = sum(1 for token in doc if token.like_num)

        # Average word length (complex vocabulary)
        avg_word_len = np.mean([len(w) for w in text.split()]) if n_words > 0 else 0

        # Sentence structure
        n_sentences = len(list(doc.sents))

        features.append([
            n_words, n_chars, caps_ratio, n_exclaim, n_question,
            n_allcaps_words, punct_ratio, n_sensational, n_credibility,
            n_vague, n_entities, n_numbers, avg_word_len, n_sentences,
        ])

    return np.array(features)

feature_names = [
    'n_words', 'n_chars', 'caps_ratio', 'n_exclaim', 'n_question',
    'n_allcaps_words', 'punct_ratio', 'n_sensational', 'n_credibility',
    'n_vague', 'n_entities', 'n_numbers', 'avg_word_len', 'n_sentences',
]

X_train_feat = extract_features(train_sents)
X_val_feat = extract_features(val_sents)
X_test_feat = extract_features(test_sents)

# Scale features
scaler = StandardScaler()
X_train_feat_scaled = scaler.fit_transform(X_train_feat)
X_val_feat_scaled = scaler.transform(X_val_feat)
X_test_feat_scaled = scaler.transform(X_test_feat)

# TF-IDF
tfidf = TfidfVectorizer(ngram_range=(1, 2), max_features=2000)
X_train_tfidf = tfidf.fit_transform(train_sents)
X_val_tfidf = tfidf.transform(val_sents)
X_test_tfidf = tfidf.transform(test_sents)

# Combined: TF-IDF + linguistic features
from scipy.sparse import hstack
X_train_combo = hstack([X_train_tfidf, X_train_feat_scaled])
X_val_combo = hstack([X_val_tfidf, X_val_feat_scaled])
X_test_combo = hstack([X_test_tfidf, X_test_feat_scaled])

# spaCy vectors
X_train_spacy = np.array([nlp(s).vector for s in train_sents])
X_val_spacy = np.array([nlp(s).vector for s in val_sents])
X_test_spacy = np.array([nlp(s).vector for s in test_sents])

print(f"  Linguistic features: {X_train_feat.shape[1]}")
print(f"  TF-IDF features: {X_train_tfidf.shape[1]}")
print(f"  spaCy vector dim: {X_train_spacy.shape[1]}")
print(f"  Combined: {X_train_combo.shape[1]}")

# ================================================================
# PART 3: CLASSICAL MODELS
# ================================================================
print("\n" + "=" * 70)
print("CLASSICAL CREDIBILITY BASELINES")
print("=" * 70)

class_names = {0: "REAL", 1: "FAKE"}

models = {
    "Linguistic + LogReg": (LogisticRegression(max_iter=1000, random_state=42),
                            X_train_feat_scaled, X_val_feat_scaled, X_test_feat_scaled),
    "Linguistic + RF": (RandomForestClassifier(n_estimators=100, random_state=42),
                        X_train_feat_scaled, X_val_feat_scaled, X_test_feat_scaled),
    "TF-IDF + SVM": (SVC(kernel='linear', probability=True, random_state=42),
                     X_train_tfidf, X_val_tfidf, X_test_tfidf),
    "TF-IDF + GBM": (GradientBoostingClassifier(n_estimators=100, random_state=42),
                     X_train_tfidf, X_val_tfidf, X_test_tfidf),
    "Combined + LogReg": (LogisticRegression(max_iter=1000, random_state=42),
                          X_train_combo, X_val_combo, X_test_combo),
    "Combined + SVM": (SVC(kernel='linear', probability=True, random_state=42),
                       X_train_combo, X_val_combo, X_test_combo),
    "spaCy + SVM": (SVC(kernel='rbf', probability=True, random_state=42),
                    X_train_spacy, X_val_spacy, X_test_spacy),
}

classical_results = []

for name, (clf, X_tr, X_va, X_te) in models.items():
    t_start = time.time()
    clf.fit(X_tr, train_labels)
    elapsed = time.time() - t_start

    train_acc = accuracy_score(train_labels, clf.predict(X_tr))
    val_acc = accuracy_score(val_labels, clf.predict(X_va))
    test_acc = accuracy_score(test_labels, clf.predict(X_te))
    test_f1 = f1_score(test_labels, clf.predict(X_te), average='weighted')

    test_probs = clf.predict_proba(X_te)
    avg_conf = test_probs.max(axis=1).mean()

    result = {
        "method": name,
        "train_acc": round(train_acc, 4),
        "val_acc": round(val_acc, 4),
        "test_acc": round(test_acc, 4),
        "test_f1": round(test_f1, 4),
        "confidence": round(avg_conf, 4),
        "time": round(elapsed, 4),
    }
    classical_results.append(result)

    print(f"\n  {name}")
    print(f"    Train: {train_acc:.1%}  Val: {val_acc:.1%}  Test: {test_acc:.1%}  F1: {test_f1:.3f}  Conf: {avg_conf:.3f}")

# Feature importance from Random Forest
rf_model = [clf for name, (clf, _, _, _) in models.items() if name == "Linguistic + RF"][0]
importances = rf_model.feature_importances_
sorted_idx = np.argsort(importances)[::-1]

print("\n  Top linguistic features (Random Forest):")
for i in range(min(8, len(feature_names))):
    idx = sorted_idx[i]
    print(f"    {feature_names[idx]:<20} {importances[idx]:.3f}")

# ================================================================
# PART 4: QUANTUM CREDIBILITY MODEL
# ================================================================
print("\n" + "=" * 70)
print("QUANTUM CREDIBILITY MODEL")
print("=" * 70)

import torch
from lambeq import (
    RemoveCupsRewriter,
    IQPAnsatz,
    AtomicType,
    PytorchTrainer,
    PytorchQuantumModel,
    Dataset,
    stairs_reader,
)

# Quantum needs shorter sentences — truncate to max 8 words
# (longer sentences = more qubits = exponential slowdown)
MAX_WORDS = 8

def truncate(sentences, labels):
    truncated = []
    kept_labels = []
    for s, l in zip(sentences, labels):
        words = s.split()[:MAX_WORDS]
        truncated.append(" ".join(words))
        kept_labels.append(l)
    return truncated, kept_labels

# Use smaller quantum training set (balanced)
Q_TRAIN = 60
search_idx = [i for i, l in enumerate(train_labels) if l == 0]
action_idx = [i for i, l in enumerate(train_labels) if l == 1]
selected = sorted(
    list(np.random.choice(search_idx, Q_TRAIN // 2, replace=False)) +
    list(np.random.choice(action_idx, Q_TRAIN // 2, replace=False))
)

q_train_sents_raw = [train_sents[i] for i in selected]
q_train_labels_raw = [int(train_labels[i]) for i in selected]

q_train_sents, q_train_labels = truncate(q_train_sents_raw, q_train_labels_raw)
q_val_sents, q_val_labels = truncate(val_sents, list(val_labels))
q_test_sents, q_test_labels = truncate(test_sents, list(test_labels))

print(f"\n  Quantum subset: {len(q_train_sents)} train (truncated to {MAX_WORDS} words)")

# Parse
reader = stairs_reader
remove_cups = RemoveCupsRewriter()

def parse_clean(sentences, labels):
    raw = reader.sentences2diagrams(sentences)
    pairs = [(d, l) for d, l in zip(raw, labels) if d is not None]
    if len(pairs) < len(sentences):
        print(f"    {len(sentences) - len(pairs)} failed parses removed")
    return [remove_cups(p[0]) for p in pairs], [p[1] for p in pairs]

print("  Parsing...")
q_train_diag, q_train_labels = parse_clean(q_train_sents, q_train_labels)
q_val_diag, q_val_labels = parse_clean(q_val_sents, q_val_labels)
q_test_diag, q_test_labels = parse_clean(q_test_sents, q_test_labels)

print(f"  Parsed: {len(q_train_diag)} train, {len(q_val_diag)} val, {len(q_test_diag)} test")

q_train_labels_2d = np.array([[1-l, l] for l in q_train_labels], dtype=np.float64)
q_val_labels_2d = np.array([[1-l, l] for l in q_val_labels], dtype=np.float64)
q_test_labels_2d = np.array([[1-l, l] for l in q_test_labels], dtype=np.float64)

def loss_fn(y_pred, y_true):
    return torch.nn.functional.mse_loss(y_pred, y_true.to(y_pred.dtype))

def accuracy_fn(y_pred, y_true):
    return (torch.argmax(y_pred, dim=1) == torch.argmax(y_true.to(y_pred.dtype), dim=1)).sum().item() / len(y_true)

# Run quantum N=1 (fastest, proven config)
ansatz = IQPAnsatz(
    {AtomicType.NOUN: 1, AtomicType.SENTENCE: 1},
    n_layers=2,
    n_single_qubit_params=3,
)

print("  Building circuits...")
t_start = time.time()

train_circuits = [ansatz(d) for d in q_train_diag]
val_circuits = [ansatz(d) for d in q_val_diag]
test_circuits = [ansatz(d) for d in q_test_diag]

all_circuits = train_circuits + val_circuits + test_circuits
model = PytorchQuantumModel.from_diagrams(all_circuits)
model.initialise_weights()
print(f"  Parameters: {len(model.symbols)}")

train_dataset = Dataset(train_circuits, q_train_labels_2d, batch_size=8)
val_dataset = Dataset(val_circuits, q_val_labels_2d, batch_size=8)

trainer = PytorchTrainer(
    model=model,
    loss_function=loss_fn,
    optimizer=torch.optim.Adam,
    learning_rate=0.05,
    epochs=80,
    evaluate_functions={"accuracy": accuracy_fn},
    evaluate_on_train=True,
    verbose='text',
    seed=42,
)

print("  Training...")
trainer.fit(train_dataset, val_dataset)
elapsed = time.time() - t_start

# Evaluate
train_preds = model(train_circuits)
val_preds = model(val_circuits)
test_preds = model(test_circuits)

def calc_acc(preds, labels_2d):
    return (torch.argmax(preds, dim=1) == torch.tensor(np.argmax(labels_2d, axis=1))).float().mean().item()

q_train_acc = calc_acc(train_preds, q_train_labels_2d)
q_val_acc = calc_acc(val_preds, q_val_labels_2d)
q_test_acc = calc_acc(test_preds, q_test_labels_2d)
q_test_conf = test_preds.detach().max(dim=1).values.mean().item()

quantum_result = {
    "method": "Quantum N=1 (60 train, 8-word)",
    "train_acc": round(q_train_acc, 4),
    "val_acc": round(q_val_acc, 4),
    "test_acc": round(q_test_acc, 4),
    "confidence": round(q_test_conf, 4),
    "time": round(elapsed, 1),
    "n_params": len(model.symbols),
}

print(f"\n  Quantum N=1: Train: {q_train_acc:.1%}  Val: {q_val_acc:.1%}  Test: {q_test_acc:.1%}  Conf: {q_test_conf:.3f}")

# ================================================================
# FINAL COMPARISON
# ================================================================
print("\n\n" + "=" * 80)
print("CREDIBILITY CLASSIFIER: CLASSICAL vs QUANTUM")
print("=" * 80)

print(f"\n  {'Method':<30} {'Train':<8} {'Val':<8} {'Test':<8} {'Conf':<8} {'Time':<10}")
print("  " + "-" * 72)
for r in classical_results:
    t = f"{r['time']*1000:.0f}ms" if r['time'] < 1 else f"{r['time']:.1f}s"
    print(f"  {r['method']:<30} {r['train_acc']:.0%}     {r['val_acc']:.0%}     "
          f"{r['test_acc']:.0%}     {r['confidence']:.3f}   {t}")
print("  " + "-" * 72)
print(f"  {quantum_result['method']:<30} {quantum_result['train_acc']:.0%}     "
      f"{quantum_result['val_acc']:.0%}     {quantum_result['test_acc']:.0%}     "
      f"{quantum_result['confidence']:.3f}   {quantum_result['time']:.0f}s")

# Save
all_results = {"classical": classical_results, "quantum": [quantum_result]}
with open("results/sprint2_credibility.json", "w") as f:
    json.dump(all_results, f, indent=2)

print(f"\nResults saved to results/sprint2_credibility.json")
print(f"\nDataset saved to data/jarvis_credibility_v1.json")
print("\nTask 2.2 Complete - Credibility Baselines")
print("Next: Analyse where quantum can add value to credibility scoring")