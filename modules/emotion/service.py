#!/usr/bin/env python3
"""
Module 5: Quantum Emotion — FastAPI Service
==============================================
Jarvis Quantum Microservice

Endpoints:
  POST /api/emotion/detect        — Detect emotion from text
  POST /api/emotion/blend         — Blend multiple emotions (superposition)
  POST /api/emotion/tts-vector    — Generate YorkieTTS emotion vector
  GET  /api/emotion/trajectory    — Get conversation emotion history
  POST /api/emotion/reset         — Clear emotion history
  GET  /api/emotion/health        — Health check

Port: 3035
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn
import numpy as np
import time
import os

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator

# ================================================================
# EMOTION ENGINE
# ================================================================

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

# Word lists for detection
EMOTION_WORDS = {
    'joy': ['happy', 'great', 'wonderful', 'love', 'excellent', 'amazing',
            'fantastic', 'delighted', 'pleased', 'glad', 'beautiful',
            'brilliant', 'perfect', 'awesome', 'enjoy', 'cheerful',
            'good', 'best', 'nice', 'fun'],
    'sadness': ['sad', 'sorry', 'unfortunately', 'miss', 'lost', 'grief',
                'heartbroken', 'depressed', 'lonely', 'hurt', 'painful',
                'disappointed', 'regret', 'cry', 'tears', 'unhappy',
                'miserable', 'gloomy'],
    'anger': ['angry', 'furious', 'outraged', 'annoyed', 'frustrated',
              'hate', 'rage', 'hostile', 'irritated', 'livid', 'mad',
              'upset', 'unacceptable', 'terrible', 'awful'],
    'fear': ['afraid', 'scared', 'worried', 'anxious', 'nervous',
             'terrified', 'panic', 'dread', 'alarmed', 'uneasy',
             'concerned', 'frightened', 'threatening', 'danger'],
    'surprise': ['surprised', 'shocked', 'unexpected', 'wow',
                 'unbelievable', 'astonished', 'incredible', 'sudden',
                 'remarkable', 'never expected'],
    'trust': ['trust', 'reliable', 'confident', 'believe', 'certain',
              'loyal', 'faithful', 'dependable', 'honest', 'safe',
              'secure', 'steady'],
    'anticipation': ['excited', 'looking forward', 'eager', 'hope',
                     'expect', 'waiting', 'planning', 'upcoming',
                     'soon', 'ready', 'prepared', 'can\'t wait'],
    'disgust': ['disgusting', 'revolting', 'terrible', 'awful',
                'horrible', 'gross', 'nasty', 'repulsive', 'vile',
                'sickening'],
}


class QuantumEmotionEngine:

    def __init__(self):
        self.sim = AerSimulator()
        self.history = []

    def _score_text(self, text):
        text_lower = text.lower()
        scores = {}
        for emotion, words in EMOTION_WORDS.items():
            score = sum(1 for w in words if w in text_lower)
            if score > 0:
                scores[emotion] = score
        if not scores:
            scores['trust'] = 1  # default neutral
        return scores

    def detect(self, text, shots=1024):
        scores = self._score_text(text)
        total = sum(scores.values())
        normalized = {k: v / total for k, v in scores.items()}

        # Calculate VAD from emotion weights directly
        # Positive emotions: joy, trust, anticipation, surprise
        # Negative emotions: sadness, anger, fear, disgust
        positive = sum(normalized.get(e, 0) for e in ['joy', 'trust', 'anticipation', 'surprise'])
        negative = sum(normalized.get(e, 0) for e in ['sadness', 'anger', 'fear', 'disgust'])

        # High arousal: anger, fear, surprise, anticipation
        # Low arousal: sadness, trust, joy, disgust
        high_arousal = sum(normalized.get(e, 0) for e in ['anger', 'fear', 'surprise', 'anticipation'])
        low_arousal = sum(normalized.get(e, 0) for e in ['sadness', 'trust', 'joy', 'disgust'])

        valence = positive  # 0=negative, 1=positive
        arousal = high_arousal  # 0=calm, 1=activated

        # Quantum circuit: encode the distribution
        qc = QuantumCircuit(3, 3)

        # Direct rotation based on dominant emotion scores
        # No entangling gates — keep the encoding clean
        theta_v = 2 * np.arcsin(np.sqrt(np.clip(1.0 - valence, 0, 1)))
        theta_a = 2 * np.arcsin(np.sqrt(np.clip(arousal, 0, 1)))

        # Dominance: high for anger, anticipation; low for fear, sadness
        dominant_emotions = sum(normalized.get(e, 0) for e in ['anger', 'anticipation', 'disgust'])
        theta_d = 2 * np.arcsin(np.sqrt(np.clip(dominant_emotions, 0, 1)))

        qc.ry(theta_v, 0)  # Valence
        qc.ry(theta_a, 1)  # Arousal
        qc.ry(theta_d, 2)  # Dominance

        qc.measure([0, 1, 2], [0, 1, 2])
        result = self.sim.run(qc, shots=shots).result()
        counts = result.get_counts()

        total_counts = sum(counts.values())
        emotion_probs = {}
        for state, count in counts.items():
            state_padded = state.zfill(3)
            emotion = EMOTIONS.get(state_padded, f"unknown_{state_padded}")
            emotion_probs[emotion] = round(count / total_counts, 4)

        emotion_probs = dict(sorted(emotion_probs.items(), key=lambda x: -x[1]))
        dominant = list(emotion_probs.keys())[0]

        # Also use word scores to determine dominant if quantum is ambiguous
        word_dominant = max(scores, key=scores.get)
        if scores[word_dominant] >= 2 and emotion_probs.get(word_dominant, 0) < 0.1:
            # Word scores strongly disagree with quantum — trust word scores for dominant
            dominant = word_dominant

        self.history.append({
            "text": text[:80],
            "dominant": dominant,
            "distribution": emotion_probs,
        })

        return {
            "text": text,
            "dominant_emotion": dominant,
            "emotion_distribution": emotion_probs,
            "word_scores": scores,
            "valence": round(valence, 4),
            "arousal": round(arousal, 4),
        }

    def blend(self, emotions_weights, shots=1024):
        total = sum(emotions_weights.values())
        normalized = {k: v / total for k, v in emotions_weights.items()}

        positive = sum(normalized.get(e, 0) for e in ['joy', 'trust', 'anticipation', 'surprise'])
        high_arousal = sum(normalized.get(e, 0) for e in ['anger', 'fear', 'surprise', 'anticipation'])
        dominant_e = sum(normalized.get(e, 0) for e in ['anger', 'anticipation', 'disgust'])

        qc = QuantumCircuit(3, 3)
        qc.ry(2 * np.arcsin(np.sqrt(np.clip(1.0 - positive, 0, 1))), 0)
        qc.ry(2 * np.arcsin(np.sqrt(np.clip(high_arousal, 0, 1))), 1)
        qc.ry(2 * np.arcsin(np.sqrt(np.clip(dominant_e, 0, 1))), 2)
        qc.measure([0, 1, 2], [0, 1, 2])

        result = self.sim.run(qc, shots=shots).result()
        counts = result.get_counts()
        total_counts = sum(counts.values())

        probs = {}
        for state, count in counts.items():
            state_padded = state.zfill(3)
            emotion = EMOTIONS.get(state_padded, f"unknown_{state_padded}")
            probs[emotion] = round(count / total_counts, 4)

        probs = dict(sorted(probs.items(), key=lambda x: -x[1]))
        dominant = list(probs.keys())[0]

        return {
            "input_emotions": emotions_weights,
            "quantum_distribution": probs,
            "dominant_emotion": dominant,
            "dominant_probability": probs[dominant],
        }

    def tts_vector(self, text, shots=1024):
        result = self.detect(text, shots)

        dist = result['emotion_distribution']
        valence = result['valence']
        arousal = result['arousal']
        dominance = sum(dist.get(e, 0) for e in ['anger', 'anticipation', 'disgust'])

        vector = [
            round(valence, 4),
            round(arousal, 4),
            round(dominance, 4),
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
            "dominant_emotion": result['dominant_emotion'],
            "emotion_vector": vector,
            "vector_labels": [
                "valence", "arousal", "dominance",
                "joy", "sadness", "anger", "fear",
                "surprise", "trust", "anticipation", "disgust"
            ],
            "tts_params": {
                "pitch_shift": round((valence - 0.5) * 4, 2),
                "speed_factor": round(0.8 + arousal * 0.4, 2),
                "energy": round(dominance, 2),
                "tremolo": round(dist.get('sadness', 0) * 0.5 + dist.get('fear', 0) * 0.3, 2),
            },
        }

    def get_trajectory(self):
        return {
            "steps": len(self.history),
            "trajectory": [
                {"step": i, "text": h['text'], "dominant": h['dominant']}
                for i, h in enumerate(self.history)
            ],
            "shifts": sum(
                1 for i in range(1, len(self.history))
                if self.history[i]['dominant'] != self.history[i-1]['dominant']
            ) if len(self.history) > 1 else 0,
        }

    def reset(self):
        self.history.clear()


# ================================================================
# API MODELS
# ================================================================

class DetectRequest(BaseModel):
    text: str = Field(..., min_length=1)

class EmotionDistribution(BaseModel):
    dominant_emotion: str
    emotion_distribution: dict
    word_scores: dict
    valence: float
    arousal: float
    processing_time_ms: float

class BlendRequest(BaseModel):
    emotions: dict = Field(..., description="Dict of emotion_name: weight, e.g. {'joy': 0.7, 'sadness': 0.3}")

class BlendResponse(BaseModel):
    status: str
    input_emotions: dict
    quantum_distribution: dict
    dominant_emotion: str
    dominant_probability: float

class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1)

class TTSParams(BaseModel):
    pitch_shift: float
    speed_factor: float
    energy: float
    tremolo: float

class TTSResponse(BaseModel):
    status: str
    text: str
    dominant_emotion: str
    emotion_vector: list[float]
    vector_labels: list[str]
    tts_params: TTSParams
    processing_time_ms: float

class TrajectoryStep(BaseModel):
    step: int
    text: str
    dominant: str

class TrajectoryResponse(BaseModel):
    status: str
    steps: int
    shifts: int
    trajectory: list[TrajectoryStep]

class HealthResponse(BaseModel):
    status: str
    history_length: int
    uptime_seconds: float
    version: str


# ================================================================
# SERVICE
# ================================================================

app = FastAPI(
    title="Jarvis Quantum Emotion",
    description="Quantum-enhanced emotion detection and YorkieTTS integration",
    version="0.1.0",
)

engine = QuantumEmotionEngine()
start_time = time.time()
SERVICE_PORT = int(os.environ.get("EMOTION_PORT", 3035))


@app.get("/api/emotion/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="healthy",
        history_length=len(engine.history),
        uptime_seconds=round(time.time() - start_time, 1),
        version="0.1.0",
    )


@app.post("/api/emotion/detect")
async def detect(request: DetectRequest):
    t_start = time.time()
    result = engine.detect(request.text)
    elapsed = (time.time() - t_start) * 1000

    return {
        "status": "success",
        "dominant_emotion": result['dominant_emotion'],
        "emotion_distribution": result['emotion_distribution'],
        "word_scores": result['word_scores'],
        "valence": result['valence'],
        "arousal": result['arousal'],
        "processing_time_ms": round(elapsed, 1),
    }


@app.post("/api/emotion/blend", response_model=BlendResponse)
async def blend(request: BlendRequest):
    valid_emotions = set(EMOTION_TO_STATE.keys())
    for e in request.emotions:
        if e not in valid_emotions:
            raise HTTPException(400, f"Unknown emotion '{e}'. Valid: {sorted(valid_emotions)}")

    result = engine.blend(request.emotions)
    return BlendResponse(status="success", **result)


@app.post("/api/emotion/tts-vector", response_model=TTSResponse)
async def tts_vector(request: TTSRequest):
    t_start = time.time()
    result = engine.tts_vector(request.text)
    elapsed = (time.time() - t_start) * 1000

    return TTSResponse(
        status="success",
        text=result['text'],
        dominant_emotion=result['dominant_emotion'],
        emotion_vector=result['emotion_vector'],
        vector_labels=result['vector_labels'],
        tts_params=TTSParams(**result['tts_params']),
        processing_time_ms=round(elapsed, 1),
    )


@app.get("/api/emotion/trajectory", response_model=TrajectoryResponse)
async def trajectory():
    result = engine.get_trajectory()
    steps = [TrajectoryStep(**s) for s in result['trajectory']]
    return TrajectoryResponse(
        status="success",
        steps=result['steps'],
        shifts=result['shifts'],
        trajectory=steps,
    )


@app.post("/api/emotion/reset")
async def reset():
    engine.reset()
    return {"status": "success", "message": "Emotion history cleared"}


if __name__ == "__main__":
    uvicorn.run("service:app", host="0.0.0.0", port=SERVICE_PORT, reload=False)