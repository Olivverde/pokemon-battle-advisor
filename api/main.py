from pathlib import Path
from typing import Dict

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="Pokémon Battle Advisor API",
    description="API de inferencia para el modelo Pokémon Battle Advisor",
    version="0.1.0",
)

MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "pokemon_advisor.joblib"
ENCODER_PATH = Path(__file__).resolve().parents[1] / "models" / "label_encoder.joblib"

FEATURE_COLUMNS = [
    "hp",
    "hp_opp",
    "spikes_own",
    "spikes_opp",
    "stealth_rock_own",
    "stealth_rock_opp",
    "active_pokemon",
    "weather_Rain Dance",
    "weather_RainDance",
    "weather_Sandstorm",
    "weather_Snowscape",
    "weather_SunnyDay",
    "weather_none",
    "terrain_none",
]

model = None
label_encoder = None


class PredictRequest(BaseModel):
    hp: float = Field(..., ge=0.0, le=100.0)
    hp_opp: float = Field(..., ge=0.0, le=100.0)
    spikes_own: int = Field(..., ge=0, le=3)
    spikes_opp: int = Field(..., ge=0, le=3)
    stealth_rock_own: int = Field(..., ge=0, le=1)
    stealth_rock_opp: int = Field(..., ge=0, le=1)


class PredictResponse(BaseModel):
    action: str
    probabilities: Dict[str, float]


@app.on_event("startup")
def load_artifacts() -> None:
    global model, label_encoder

    if not MODEL_PATH.exists():
        raise RuntimeError(f"Modelo no encontrado: {MODEL_PATH}")
    if not ENCODER_PATH.exists():
        raise RuntimeError(f"LabelEncoder no encontrado: {ENCODER_PATH}")

    model = joblib.load(MODEL_PATH)
    label_encoder = joblib.load(ENCODER_PATH)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/predict", response_model=PredictResponse)
def predict(payload: PredictRequest) -> PredictResponse:
    if model is None or label_encoder is None:
        raise HTTPException(status_code=500, detail="Modelo no cargado")

    try:
        row = {col: 0 for col in FEATURE_COLUMNS}
        row.update(
            {
                "hp": float(payload.hp),
                "hp_opp": float(payload.hp_opp),
                "spikes_own": int(payload.spikes_own),
                "spikes_opp": int(payload.spikes_opp),
                "stealth_rock_own": int(payload.stealth_rock_own),
                "stealth_rock_opp": int(payload.stealth_rock_opp),
                "active_pokemon": 0,
                "weather_none": 1,
                "terrain_none": 1,
            }
        )

        features = pd.DataFrame([row], columns=FEATURE_COLUMNS)
        probabilities = model.predict_proba(features)[0]
        labels = label_encoder.inverse_transform(np.arange(len(probabilities)))
        prob_dict = {label: float(probabilities[idx]) for idx, label in enumerate(labels)}
        best_action = labels[np.argmax(probabilities)]

        return PredictResponse(action=best_action, probabilities=prob_dict)

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error de inferencia: {exc}")


@app.get("/")
def root() -> Dict[str, str]:
    return {"status": "ok", "message": "Pokémon Battle Advisor API"}
