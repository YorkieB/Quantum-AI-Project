#!/usr/bin/env python3
"""
Sprint 4, Task 4.3: BobcatParser Retry
"""

import warnings
warnings.filterwarnings('ignore')

import lambeq
from lambeq import BobcatParser, stairs_reader
import time

print(f"lambeq version: {lambeq.__version__}")

test_sentences = [
    "the unemployment rate dropped three percent last quarter",
    "scientists discovered a new species in the ocean",
    "the president signed the bill into law yesterday",
    "researchers found that exercise improves memory",
    "the company reported record profits this year",
]

print("\n" + "=" * 60)
print("TEST 1: BobcatParser Server Connectivity")
print("=" * 60)

bobcat_available = False

try:
    print("\n  Attempting BobcatParser connection...")
    t_start = time.time()
    bobcat = BobcatParser(verbose='text')
    diagrams = bobcat.sentences2diagrams(test_sentences)
    elapsed = time.time() - t_start

    n_success = sum(1 for d in diagrams if d is not None)
    print(f"\n  BobcatParser: {n_success}/{len(test_sentences)} parsed in {elapsed:.1f}s")

    if n_success > 0:
        bobcat_available = True
        print("  SERVER IS ONLINE!")
        for sent, diag in zip(test_sentences, diagrams):
            if diag is not None:
                n_boxes = len(diag.boxes)
                print(f"    \"{sent[:50]}\" -> {n_boxes} boxes")

except Exception as e:
    print(f"\n  BobcatParser FAILED: {type(e).__name__}: {e}")
    print("  Server still offline.")

print("\n" + "=" * 60)
print("TEST 2: StairsReader (offline fallback)")
print("=" * 60)

reader = stairs_reader
t_start = time.time()
stairs_diagrams = reader.sentences2diagrams(test_sentences)
elapsed = time.time() - t_start

n_success = sum(1 for d in stairs_diagrams if d is not None)
print(f"\n  StairsReader: {n_success}/{len(test_sentences)} parsed in {elapsed:.1f}s")

for sent, diag in zip(test_sentences, stairs_diagrams):
    if diag is not None:
        n_boxes = len(diag.boxes)
        print(f"    \"{sent[:50]}\" -> {n_boxes} boxes")

print("\n" + "=" * 60)
print("RESULT")
print("=" * 60)

if bobcat_available:
    print("\n  BobcatParser is ONLINE!")
    print("  Recommendation: Use BobcatParser for all future experiments.")
    print("  Re-run LIAR credibility with full CCG parsing.")
else:
    print("\n  BobcatParser still offline.")
    print("  Continuing with StairsReader.")
    print("  To check manually:")
    print("    python -c \"from lambeq import BobcatParser; BobcatParser(verbose='text')\"")

print("\nTask 4.3 Complete")