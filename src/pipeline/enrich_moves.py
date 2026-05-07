import json
import os
import time
import requests
import pandas as pd
from typing import Dict, Optional

CACHE_FILE = "data/processed/move_cache.json"

def load_cache() -> Dict[str, str]:
    """Carga el cache de movimientos desde archivo JSON."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_cache(cache: Dict[str, str]) -> None:
    """Guarda el cache de movimientos en archivo JSON."""
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

def normalize_move_name(move_name: str) -> Optional[str]:
    """Normaliza el nombre del movimiento para la URL de PokeAPI."""
    if move_name is None or not isinstance(move_name, str):
        return None

    # Convertir a minúsculas y reemplazar espacios con guiones
    normalized = move_name.lower().replace(" ", "-")

    # Limpiar caracteres especiales
    normalized = normalized.replace("'", "").replace(".", "").replace(":", "").replace(",", "")

    return normalized

def get_move_damage_class(move_name: str, cache: Dict[str, str]) -> str:
    """Obtiene la clase de daño del movimiento desde PokeAPI o cache."""
    move_key = normalize_move_name(move_name)
    if not move_key:
        return "UNKNOWN"

    # Verificar cache primero
    if move_key in cache:
        cached_value = cache[move_key]
        # Si ya está en el formato correcto, devolverlo
        if cached_value in ["ATTACK_PHYSICAL", "ATTACK_SPECIAL", "STATUS", "UNKNOWN"]:
            return cached_value
        # Si está en formato antiguo, convertirlo
        elif cached_value == "physical":
            return "ATTACK_PHYSICAL"
        elif cached_value == "special":
            return "ATTACK_SPECIAL"
        elif cached_value == "status":
            return "STATUS"
        elif cached_value == "unknown":
            return "UNKNOWN"

    # Consultar PokeAPI
    try:
        url = f"https://pokeapi.co/api/v2/move/{move_key}"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            damage_class = data.get("damage_class", {}).get("name", "unknown")

            # Mapear a nuestros valores
            if damage_class == "physical":
                result = "ATTACK_PHYSICAL"
            elif damage_class == "special":
                result = "ATTACK_SPECIAL"
            elif damage_class == "status":
                result = "STATUS"
            else:
                result = "UNKNOWN"

        elif response.status_code == 404:
            result = "UNKNOWN"
        else:
            print(f"Error {response.status_code} para movimiento: {move_name}")
            result = "UNKNOWN"

    except Exception as e:
        print(f"Error consultando movimiento {move_name}: {e}")
        result = "UNKNOWN"

    # Guardar en cache (siempre en formato correcto)
    cache[move_key] = result

    # Rate limiting
    time.sleep(0.2)

    return result

def main():
    """Función principal para enriquecer el dataset."""
    print("🔄 Iniciando enriquecimiento de movimientos...")

    # Cargar dataset
    input_file = "data/processed/battle_turns_dataset.csv"
    if not os.path.exists(input_file):
        print(f"❌ Error: No se encuentra el archivo {input_file}")
        return

    df = pd.read_csv(input_file)
    print(f"📊 Dataset cargado: {len(df)} filas")

    # Cargar cache
    cache = load_cache()
    print(f"💾 Cache cargado: {len(cache)} movimientos")

    # Encontrar movimientos únicos con MOVE_UNKNOWN
    move_unknown_mask = df['action'] == 'MOVE_UNKNOWN'
    unique_moves = df.loc[move_unknown_mask, 'move_name'].dropna().unique()

    print(f"🎯 Encontrados {len(unique_moves)} movimientos únicos con MOVE_UNKNOWN")

    # Procesar cada movimiento
    processed = 0
    for move_name in unique_moves:
        damage_class = get_move_damage_class(move_name, cache)

        # Actualizar todas las filas con este movimiento
        move_mask = (df['move_name'] == move_name) & move_unknown_mask
        df.loc[move_mask, 'action'] = damage_class

        processed += 1
        if processed % 50 == 0:
            print(f"✅ Procesados {processed}/{len(unique_moves)} movimientos")

    # Guardar cache actualizado
    save_cache(cache)
    print(f"💾 Cache guardado: {len(cache)} movimientos")

    # Guardar dataset enriquecido
    output_file = "data/processed/battle_turns_enriched.csv"
    df.to_csv(output_file, index=False)
    print(f"💾 Dataset guardado en: {output_file}")

    # Mostrar distribución final
    print("\n📈 DISTRIBUCIÓN FINAL DE ACTIONS:")
    action_counts = df['action'].value_counts()
    total_actions = len(df)

    for action, count in action_counts.items():
        percentage = (count / total_actions) * 100
        print(f"  {action}: {count} ({percentage:.1f}%)")

    # Verificar que no queden MOVE_UNKNOWN
    unknown_count = (df['action'] == 'MOVE_UNKNOWN').sum()
    if unknown_count == 0:
        print("✅ ¡Éxito! No quedan movimientos MOVE_UNKNOWN")
    else:
        print(f"⚠️  Aún quedan {unknown_count} movimientos MOVE_UNKNOWN")

if __name__ == "__main__":
    main()