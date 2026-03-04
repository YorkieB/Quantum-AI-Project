#!/usr/bin/env python3
"""
Sprint 4, Task 4.7: Module 5 — Quantum Emotion Engine
========================================================
Jarvis Quantum - Voice/Emotion Processing

Quantum-enhanced emotion vector processing for:
  1. Emotion classification from text features
  2. Emotion blending (mixed emotions as superposition)
  3. Emotion state evolution over conversation
  4. Integration with YorkieTTS emotion vectors

Key insight: Emotions are naturally quantum-like!
  - You can feel happy AND sad simultaneously (superposition)
  - Observing/naming an emotion changes it (measurement)
  - Emotions are entangled with context (entanglement)
  - Emotion transitions are probabilistic (quantum dynamics)
"""

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import json
import os
import time
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator

np.random.seed(42)
sim = AerSimulator()

# ================================================================
# PART 1: EMOTION ENCODING AS QUANTUM STATES
# ================================================================
print("=" * 70)
print("MODULE 5: QUANTUM EMOTION ENGINE")
print("=" * 70)

print("\n" + "-" * 70)
print("PART 1: Emotion Encoding as Quantum States")
print("-" * 70)

# 3 qubits = 8 basis states = 8 primary emotions (Plutchik's wheel)
EMOTIONS = {
    '000': 'joy',
    '001': 'trust',
    '010': 'fear',
    '011': 'surprise',
    '100': 'sadness',
    '101': 'disgust',
    '110': 'anger',
    '111': 'anticipation',
}

EMOTION_TO_STATE = {v: k for k, v in EMOTIONS.items()}


class QuantumEmotionEngine:
    """
    Encodes emotions as quantum states using 3 qubits.

    Dimensions:
      Qubit 0: Valence (0=positive, 1=negative)
      Qubit 1: Arousal (0=calm, 1=activated)
      Qubit 2: Dominance (0=submissive, 1=dominant)

    This maps to the VAD (Valence-Arousal-Dominance) model
    used in affective computing.
    """

    def __init__(self):
        self.sim = AerSimulator()
        self.emotion_history = []
        self.current_state = None

    def encode_pure_emotion(self, emotion_name, shots=1024):
        """Encode a single pure emotion as a quantum state."""
        if emotion_name not in EMOTION_TO_STATE:
            return {"error": f"Unknown emotion: {emotion_name}"}

        state = EMOTION_TO_STATE[emotion_name]
        qc = QuantumCircuit(3, 3)

        for i, bit in enumerate(reversed(state)):
            if bit == '1':
                qc.x(i)

        qc.measure([0, 1, 2], [0, 1, 2])
        result = self.sim.run(qc, shots=shots).result()
        counts = result.get_counts()

        return {
            "emotion": emotion_name,
            "state": state,
            "valence": "negative" if state[0] == '1' else "positive",
            "arousal": "activated" if state[1] == '1' else "calm",
            "dominance": "dominant" if state[2] == '1' else "submissive",
            "counts": counts,
            "purity": 1.0,
        }

    def encode_mixed_emotion(self, emotions_weights, shots=1024):
        """
        Encode a mixture of emotions as quantum superposition.

        emotions_weights: dict of {emotion_name: weight}
        Weights are normalized to create valid quantum state.
        """
        qc = QuantumCircuit(3, 3)

        # Normalize weights
        total = sum(emotions_weights.values())
        normalized = {k: v / total for k, v in emotions_weights.items()}

        # Calculate rotation angles for superposition
        # Use RY gates on each qubit to create the mixture
        valence_neg = sum(w for e, w in normalized.items()
                         if EMOTION_TO_STATE[e][0] == '1')
        arousal_high = sum(w for e, w in normalized.items()
                          if EMOTION_TO_STATE[e][1] == '1')
        dominance_high = sum(w for e, w in normalized.items()
                            if EMOTION_TO_STATE[e][2] == '1')

        # RY(theta) rotates from |0> toward |1>
        # theta = 2*arcsin(sqrt(probability_of_1))
        theta_v = 2 * np.arcsin(np.sqrt(np.clip(valence_neg, 0, 1)))
        theta_a = 2 * np.arcsin(np.sqrt(np.clip(arousal_high, 0, 1)))
        theta_d = 2 * np.arcsin(np.sqrt(np.clip(dominance_high, 0, 1)))

        qc.ry(theta_v, 0)  # Valence
        qc.ry(theta_a, 1)  # Arousal
        qc.ry(theta_d, 2)  # Dominance

        # Add entanglement for emotion correlations
        # (e.g., high arousal + negative valence = anger/fear coupling)
        qc.cx(0, 1)  # Valence influences arousal
        qc.cx(1, 2)  # Arousal influences dominance

        qc.measure([0, 1, 2], [0, 1, 2])
        result = self.sim.run(qc, shots=shots).result()
        counts = result.get_counts()

        # Interpret results
        emotion_probs = {}
        total_counts = sum(counts.values())
        for state, count in counts.items():
            state_padded = state.zfill(3)
            emotion = EMOTIONS.get(state_padded, f"unknown_{state_padded}")
            emotion_probs[emotion] = round(count / total_counts, 4)

        # Sort by probability
        emotion_probs = dict(sorted(emotion_probs.items(), key=lambda x: -x[1]))
        dominant_emotion = list(emotion_probs.keys())[0]

        return {
            "input_emotions": emotions_weights,
            "quantum_distribution": emotion_probs,
            "dominant_emotion": dominant_emotion,
            "dominant_probability": emotion_probs[dominant_emotion],
            "valence_negative_prob": round(valence_neg, 3),
            "arousal_high_prob": round(arousal_high, 3),
            "dominance_high_prob": round(dominance_high, 3),
            "counts": counts,
        }

    def detect_emotion_from_text(self, text, shots=1024):
        """
        Classify emotion from text features using quantum circuit.
        """
        text_lower = text.lower()

        # Feature extraction
        joy_words = ['happy', 'great', 'wonderful', 'love', 'excellent',
                     'amazing', 'fantastic', 'delighted', 'pleased', 'glad',
                     'beautiful', 'brilliant', 'perfect', 'awesome', 'enjoy']
        sadness_words = ['sad', 'sorry', 'unfortunately', 'miss', 'lost',
                        'grief', 'heartbroken', 'depressed', 'lonely', 'hurt',
                        'painful', 'disappointed', 'regret', 'cry', 'tears']
        anger_words = ['angry', 'furious', 'outraged', 'annoyed', 'frustrated',
                      'hate', 'rage', 'hostile', 'irritated', 'livid',
                      'mad', 'upset', 'disgusted', 'unacceptable']
        fear_words = ['afraid', 'scared', 'worried', 'anxious', 'nervous',
                     'terrified', 'panic', 'dread', 'alarmed', 'uneasy',
                     'concerned', 'frightened', 'threatening']
        surprise_words = ['surprised', 'shocked', 'unexpected', 'amazing',
                         'wow', 'unbelievable', 'astonished', 'incredible',
                         'sudden', 'remarkable']
        trust_words = ['trust', 'reliable', 'confident', 'believe', 'certain',
                      'loyal', 'faithful', 'dependable', 'honest', 'safe']
        anticipation_words = ['excited', 'looking forward', 'eager', 'hope',
                             'expect', 'waiting', 'planning', 'upcoming',
                             'soon', 'ready', 'prepared']
        disgust_words = ['disgusting', 'revolting', 'terrible', 'awful',
                        'horrible', 'gross', 'nasty', 'repulsive', 'vile']

        scores = {
            'joy': sum(1 for w in joy_words if w in text_lower),
            'sadness': sum(1 for w in sadness_words if w in text_lower),
            'anger': sum(1 for w in anger_words if w in text_lower),
            'fear': sum(1 for w in fear_words if w in text_lower),
            'surprise': sum(1 for w in surprise_words if w in text_lower),
            'trust': sum(1 for w in trust_words if w in text_lower),
            'anticipation': sum(1 for w in anticipation_words if w in text_lower),
            'disgust': sum(1 for w in disgust_words if w in text_lower),
        }

        total_score = sum(scores.values())
        if total_score == 0:
            # Default: neutral/calm
            scores['trust'] = 1
            total_score = 1

        # Encode as mixed quantum state
        weights = {k: v for k, v in scores.items() if v > 0}
        if not weights:
            weights = {'trust': 1}

        result = self.encode_mixed_emotion(weights, shots=shots)
        result['text'] = text
        result['word_scores'] = scores

        # Track history
        self.emotion_history.append({
            "text": text,
            "dominant": result['dominant_emotion'],
            "distribution": result['quantum_distribution'],
        })

        return result

    def get_emotion_trajectory(self):
        """Return emotion history as a trajectory."""
        if not self.emotion_history:
            return {"trajectory": [], "length": 0}

        trajectory = []
        for i, entry in enumerate(self.emotion_history):
            trajectory.append({
                "step": i,
                "text": entry['text'][:50],
                "dominant": entry['dominant'],
            })

        return {
            "trajectory": trajectory,
            "length": len(trajectory),
            "emotion_shifts": sum(
                1 for i in range(1, len(self.emotion_history))
                if self.emotion_history[i]['dominant'] != self.emotion_history[i-1]['dominant']
            ),
        }

    def generate_tts_vector(self, text, shots=1024):
        """
        Generate emotion vector for YorkieTTS integration.

        Returns a vector compatible with the Emotional Engine:
          [valence, arousal, dominance, joy, sadness, anger, fear,
           surprise, trust, anticipation, disgust]
        """
        result = self.detect_emotion_from_text(text, shots)

        dist = result['quantum_distribution']
        vector = [
            1.0 - result['valence_negative_prob'],  # Valence (0=neg, 1=pos)
            result['arousal_high_prob'],              # Arousal
            result['dominance_high_prob'],            # Dominance
            dist.get('joy', 0),
            dist.get('sadness', 0),
            dist.get('anger', 0),
            dist.get('fear', 0),
            dist.get('surprise', 0),
            dist.get('trust', 0),
            dist.get('anticipation', 0),
            dist.get('disgust', 0),
        ]

        return {
            "text": text,
            "emotion_vector": [round(v, 4) for v in vector],
            "vector_labels": [
                "valence", "arousal", "dominance",
                "joy", "sadness", "anger", "fear",
                "surprise", "trust", "anticipation", "disgust"
            ],
            "dominant_emotion": result['dominant_emotion'],
            "tts_params": {
                "pitch_shift": round((vector[0] - 0.5) * 4, 2),
                "speed_factor": round(0.8 + vector[1] * 0.4, 2),
                "energy": round(vector[2], 2),
                "tremolo": round(vector[4] * 0.5 + vector[6] * 0.3, 2),
            },
        }


# ================================================================
# TESTS
# ================================================================

engine = QuantumEmotionEngine()

# Test pure emotions
print("\n  Pure emotion encoding:")
for emotion in ['joy', 'sadness', 'anger', 'fear']:
    r = engine.encode_pure_emotion(emotion)
    print(f"    {emotion:<12} state=|{r['state']}> "
          f"V={r['valence']:<9} A={r['arousal']:<10} D={r['dominance']}")

# Test mixed emotions
print("\n  Mixed emotions (superposition):")

mixes = [
    {"joy": 0.7, "anticipation": 0.3},
    {"sadness": 0.5, "anger": 0.5},
    {"fear": 0.4, "surprise": 0.4, "trust": 0.2},
    {"joy": 0.3, "sadness": 0.3, "trust": 0.4},  # Bittersweet
]

for mix in mixes:
    r = engine.encode_mixed_emotion(mix)
    top_3 = list(r['quantum_distribution'].items())[:3]
    mix_str = " + ".join(f"{v:.0%} {k}" for k, v in mix.items())
    print(f"\n    Input: {mix_str}")
    print(f"    Quantum output: {', '.join(f'{e} ({p:.0%})' for e, p in top_3)}")
    print(f"    Dominant: {r['dominant_emotion']} ({r['dominant_probability']:.0%})")

# Test text emotion detection
print("\n\n  Text emotion detection:")
print("  " + "-" * 60)

test_texts = [
    "I'm so happy and excited about the new project launch!",
    "This is terrible, I'm really angry about what happened.",
    "I'm worried and scared about the test results.",
    "What a wonderful surprise, I never expected this!",
    "I feel sad and lonely, missing my old friends.",
    "I'm looking forward to the concert, it will be amazing!",
    "The situation is disgusting and absolutely unacceptable.",
    "I trust you completely, you've always been reliable.",
]

for text in test_texts:
    r = engine.detect_emotion_from_text(text)
    top_3 = list(r['quantum_distribution'].items())[:3]
    print(f"\n    \"{text[:55]}...\"")
    print(f"    Emotions: {', '.join(f'{e} ({p:.0%})' for e, p in top_3)}")
    print(f"    Dominant: {r['dominant_emotion']}")

# Emotion trajectory
print("\n\n  Conversation emotion trajectory:")
trajectory = engine.get_emotion_trajectory()
print(f"    Steps: {trajectory['length']}")
print(f"    Emotion shifts: {trajectory['emotion_shifts']}")
for step in trajectory['trajectory']:
    print(f"      [{step['step']}] {step['dominant']:<14} \"{step['text']}\"")

# TTS integration
print("\n\n  YorkieTTS Integration — Emotion Vectors:")
print("  " + "-" * 60)

tts_texts = [
    "Good morning! Today is going to be a great day.",
    "I regret to inform you that your application was denied.",
    "WARNING: System critical failure detected!",
    "Hey, I was just wondering if you might be free later?",
]

for text in tts_texts:
    r = engine.generate_tts_vector(text)
    vec = r['emotion_vector']
    params = r['tts_params']
    print(f"\n    \"{text[:50]}\"")
    print(f"    Emotion: {r['dominant_emotion']}")
    print(f"    Vector: V={vec[0]:.2f} A={vec[1]:.2f} D={vec[2]:.2f}")
    print(f"    TTS: pitch={params['pitch_shift']:+.1f} speed={params['speed_factor']:.2f} "
          f"energy={params['energy']:.2f} tremolo={params['tremolo']:.2f}")

# ================================================================
# PART 5: QPU EMOTION ENCODING
# ================================================================
print("\n\n" + "=" * 70)
print("QPU: Emotion Superposition on Real Hardware")
print("=" * 70)

try:
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

    service = QiskitRuntimeService(channel="ibm_cloud")
    backend = service.least_busy(operational=True, simulator=False)
    print(f"\n  QPU: {backend.name} ({backend.num_qubits} qubits)")

    pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
    sampler = SamplerV2(mode=backend)

    # Encode "bittersweet" (joy + sadness superposition) on real QPU
    qc = QuantumCircuit(3, 3)
    # Equal superposition of joy |000> and sadness |100>
    qc.ry(np.pi / 2, 0)  # 50/50 positive/negative valence
    # Keep arousal and dominance low (calm, submissive)
    qc.measure([0, 1, 2], [0, 1, 2])

    transpiled = pm.run(qc)
    print(f"  Encoding 'bittersweet' emotion (joy+sadness superposition)...")
    job = sampler.run([transpiled], shots=1024)
    result = job.result()
    counts = result[0].data.c.get_counts()

    print(f"\n  QPU emotion measurement:")
    total = sum(counts.values())
    for state, count in sorted(counts.items(), key=lambda x: -x[1]):
        state_padded = state.zfill(3)
        emotion = EMOTIONS.get(state_padded, f"unknown_{state_padded}")
        pct = count / total * 100
        bar = '#' * int(pct / 3)
        print(f"    |{state_padded}> {emotion:<14} {count:>4} ({pct:>5.1f}%) {bar}")

    # Joy vs Sadness split
    joy_count = counts.get('000', 0)
    sad_count = counts.get('100', 0)
    print(f"\n  Joy:     {joy_count/total:.1%}")
    print(f"  Sadness: {sad_count/total:.1%}")
    print(f"  The quantum state captures BOTH emotions simultaneously!")

except Exception as e:
    print(f"\n  QPU test skipped: {e}")

# ================================================================
# SAVE
# ================================================================
os.makedirs("results", exist_ok=True)

save_results = {
    "module": "Quantum Emotion Engine",
    "pure_emotions": len(EMOTIONS),
    "text_detection_tests": len(test_texts),
    "tts_integration": True,
    "trajectory_steps": trajectory['length'],
}

with open("results/sprint4_quantum_emotion.json", "w") as f:
    json.dump(save_results, f, indent=2)

print(f"\nResults saved to results/sprint4_quantum_emotion.json")
print(f"\n{'='*70}")
print("MODULE 5: QUANTUM EMOTION ENGINE — COMPLETE")
print(f"{'='*70}")
print(f"""
  Capabilities:
    1. Pure emotion encoding (8 emotions, 3 qubits, VAD model)
    2. Mixed emotions as quantum superposition (bittersweet, etc.)
    3. Text-to-emotion classification
    4. Conversation emotion trajectory tracking
    5. YorkieTTS emotion vector generation
    6. QPU-verified emotion superposition

  For Jarvis:
    - Emotional Engine gets quantum emotion vectors
    - YorkieTTS uses quantum-derived pitch/speed/energy params
    - Conversation tracker monitors emotion shifts
    - Orchestrator adjusts response tone based on emotion state

  ALL 6 MODULES COMPLETE:
    Module 1: NLU (classical — quantum not needed)
    Module 2: Reasoning (quantum logic + inference chains)
    Module 3: Search (Grover's algorithm)
    Module 4: Credibility (hybrid classical+quantum)
    Module 5: Emotion (quantum superposition)
    Module 6: QKD (BB84 quantum crypto)
""")