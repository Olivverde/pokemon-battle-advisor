"""Configuration management"""

import os
import json
from typing import Dict, Any


def load_config(config_path: str = "config/config.json") -> Dict[str, Any]:
    """Carga configuración desde archivo JSON"""
    with open(config_path, "r") as f:
        return json.load(f)


def get_output_dir(subdir: str = "raw") -> str:
    """Obtiene ruta del directorio de output"""
    path = f"data/{subdir}"
    os.makedirs(path, exist_ok=True)
    return path
