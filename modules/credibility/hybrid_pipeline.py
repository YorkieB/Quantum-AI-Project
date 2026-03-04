#!/usr/bin/env python3
"""
Module 4: Credibility Verifier — Hybrid Pipeline
==================================================
Orchestrates classical pre-filter + quantum reasoning.

Flow:
  1. Classical scores the claim (fast, ~1ms)
  2. If confident (>threshold): return classical result
  3. If uncertain: run quantum model, blend scores
  4. Return final verdict with method attribution
"""

from classical_model import ClassicalCredibilityModel
from quantum_model import QuantumCredibilityModel


class HybridCredibilityPipeline:
    """
    Hybrid classical+quantum credibility verifier.

    Architecture:
      [Input] -> [Classical TF-IDF] -> Confident? -> [Return classical result]
                                     -> Uncertain? -> [Quantum DisCoCat] -> [Blend] -> [Return]
    """

    def __init__(self, model_dir="models", confidence_threshold=0.65,
                 quantum_weight=0.6):
        """
        Args:
            model_dir: Directory containing saved model files
            confidence_threshold: Below this, route to quantum (0.0-1.0)
            quantum_weight: Weight for quantum score in blending (0.0-1.0)
        """
        self.confidence_threshold = confidence_threshold
        self.quantum_weight = quantum_weight
        self.classical_weight = 1.0 - quantum_weight

        print("Loading classical model...")
        self.classical = ClassicalCredibilityModel(model_dir)
        print("Loading quantum model...")
        self.quantum = QuantumCredibilityModel(model_dir)
        print("Hybrid pipeline ready.")

    def verify(self, statement: str) -> dict:
        """
        Verify credibility of a single statement.

        Returns:
            dict with keys:
                - credibility_score: float 0-1 (1 = fully credible)
                - label: "CREDIBLE" or "NOT_CREDIBLE"
                - confidence: float 0-1
                - method: "classical" or "hybrid"
                - classical_result: dict
                - quantum_result: dict or None
                - reasoning: str
        """
        # Stage 1: Classical pre-filter
        classical_result = self.classical.predict(statement)

        # Check confidence
        if classical_result['confidence'] >= self.confidence_threshold:
            # Classical is confident — no quantum needed
            credibility_score = classical_result['probabilities']['credible']
            return {
                "credibility_score": round(credibility_score, 4),
                "label": classical_result['label'],
                "confidence": classical_result['confidence'],
                "method": "classical",
                "classical_result": classical_result,
                "quantum_result": None,
                "reasoning": (
                    f"Classical model confident ({classical_result['confidence']:.0%}). "
                    f"Quantum bypass — threshold is {self.confidence_threshold:.0%}."
                ),
            }

        # Stage 2: Classical uncertain — invoke quantum
        quantum_result = self.quantum.predict(statement)

        if quantum_result['prediction'] == -1:
            # Quantum parse failed — fall back to classical
            credibility_score = classical_result['probabilities']['credible']
            return {
                "credibility_score": round(credibility_score, 4),
                "label": classical_result['label'],
                "confidence": classical_result['confidence'],
                "method": "classical_fallback",
                "classical_result": classical_result,
                "quantum_result": quantum_result,
                "reasoning": (
                    "Classical uncertain but quantum parse failed. "
                    "Falling back to classical prediction."
                ),
            }

        # Stage 3: Blend classical + quantum
        c_cred = classical_result['probabilities']['credible']
        q_cred = quantum_result['probabilities']['credible']

        blended_credible = (self.classical_weight * c_cred +
                           self.quantum_weight * q_cred)
        blended_not_credible = 1.0 - blended_credible

        label = "CREDIBLE" if blended_credible > 0.5 else "NOT_CREDIBLE"
        confidence = max(blended_credible, blended_not_credible)

        # Check if quantum changed the decision
        agreement = classical_result['label'] == quantum_result['label']
        if agreement:
            reasoning = (
                f"Classical uncertain ({classical_result['confidence']:.0%}), "
                f"quantum confirms: {quantum_result['label']} ({quantum_result['confidence']:.0%}). "
                f"Both models agree."
            )
        else:
            reasoning = (
                f"Classical says {classical_result['label']} ({classical_result['confidence']:.0%}), "
                f"quantum says {quantum_result['label']} ({quantum_result['confidence']:.0%}). "
                f"Models disagree — using weighted blend "
                f"({self.classical_weight:.0%} classical / {self.quantum_weight:.0%} quantum)."
            )

        return {
            "credibility_score": round(blended_credible, 4),
            "label": label,
            "confidence": round(confidence, 4),
            "method": "hybrid",
            "classical_result": classical_result,
            "quantum_result": quantum_result,
            "reasoning": reasoning,
        }

    def verify_batch(self, statements: list) -> list:
        """Verify credibility for multiple statements."""
        return [self.verify(s) for s in statements]


if __name__ == "__main__":
    # Quick test
    pipeline = HybridCredibilityPipeline()

    test_statements = [
        "The unemployment rate decreased by 3.2 percent according to the Bureau of Labor Statistics.",
        "Scientists exposed the truth about vaccines and nobody is talking about it!",
        "The trade deficit increased slightly in the third quarter of 2024.",
        "EXPOSED: Everything about climate change is a complete hoax!",
        "A new study found moderate exercise may reduce heart disease risk.",
    ]

    print("\n" + "=" * 70)
    print("HYBRID CREDIBILITY PIPELINE — TEST")
    print("=" * 70)

    for stmt in test_statements:
        result = pipeline.verify(stmt)
        print(f"\n  \"{stmt[:60]}...\"")
        print(f"    Score: {result['credibility_score']:.3f} | "
              f"Label: {result['label']} | "
              f"Method: {result['method']} | "
              f"Confidence: {result['confidence']:.3f}")
        print(f"    Reasoning: {result['reasoning']}")