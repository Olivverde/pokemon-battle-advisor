"""Models module - Entrenamiento e inferencia"""

from .trainer import train_model
from .inference import predict_action

__all__ = ["train_model", "predict_action"]
