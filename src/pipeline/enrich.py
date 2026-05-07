import json
import os
import time
from typing import Dict, Optional

import pandas as pd
import requests

CACHE_FILE = "data/processed/move_cache.json"


def load_cache() -> Dict[str, str]:
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache: Dict[str, str]) -> None:
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def normalize_move_name(move_name: str) -> Optional[str]:
    if move_name is None or not isinstance(move_name, str):
        return None
    normalized = (
        move_name.strip()
        .lower()
        .replace(" ", "-")
        .replace("'", "")
        .replace(".", "")
        .replace(":", "")
        .replace(",", "")
        .replace("é", "e")
        .replace("á", "a")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
    )
    return normalized


def get_move_category(move_name: str, cache: Dict[str, str]) -> str:
    move_key = normalize_move_name(move_name)
    if not move_key:
        return "unknown"

    if move_key in cache:
        return cache[move_key]

    url = f"https://pokeapi.co/api/v2/move/{move_key}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            category = data.get("damage_class", {}).get("name", "unknown")
            cache[move_key] = category
            save_cache(cache)
            time.sleep(0.3)
            return category
        cache[move_key] = "unknown"
        save_cache(cache)
        return "unknown"
    except requests.RequestException:
        return "unknown"


def enrich_dataset(
    input_path: str = "data/processed/battle_turns_dataset.csv",
    output_path: str = "data/processed/battle_turns_dataset_enriched.csv",
) -> pd.DataFrame:
    df = pd.read_csv(input_path)

    if "move_name" not in df.columns:
        raise ValueError(
            "El dataset no contiene la columna 'move_name'. Vuelve a generar el dataset con el parser actualizado."
        )

    cache = load_cache()
    df["move_category"] = "unknown"

    mask = (df["action"] == "MOVE_UNKNOWN") & df["move_name"].notna()
    moves = sorted(df.loc[mask, "move_name"].dropna().unique())
    print(f"Enriqueciendo {len(moves)} movimientos únicos desde PokeAPI...")

    for move in moves:
        category = get_move_category(move, cache)
        print(f"  {move} -> {category}")

    df.loc[mask, "move_category"] = df.loc[mask, "move_name"].apply(
        lambda m: cache.get(normalize_move_name(m), "unknown")
    )

    df.to_csv(output_path, index=False)
    print(f"Dataset enriquecido guardado en: {output_path}")
    return df


if __name__ == "__main__":
    enrich_dataset()
