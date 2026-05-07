"""Script para procesar todos los logs descargados y generar dataset completo"""

import os
import pandas as pd
from src.pipeline import parse_multiple_logs

def process_all_logs():
    """Procesa todos los logs descargados y genera dataset completo"""

    # Obtener lista de logs
    log_dir = "data/raw"
    log_files = [os.path.join(log_dir, f) for f in os.listdir(log_dir) if f.endswith(".log")]

    if not log_files:
        print("No se encontraron logs en data/raw/")
        print("Ejecuta primero: python -m src.pipeline.fetch")
        return

    print(f"Encontrados {len(log_files)} logs para procesar")

    # Procesar todos los logs
    print("Procesando logs... (esto puede tomar varios minutos)")
    df = parse_multiple_logs(log_files)

    if df.empty:
        print("Error: No se pudo procesar ningún log")
        return

    print("\nProcesamiento completado!")
    print(f"Total de turnos extraídos: {len(df)}")
    print(f"Total de batallas procesadas: {df['battle_id'].nunique()}")

    # Estadísticas del dataset
    print("\nEstadísticas del dataset:")
    print(f"Acciones por tipo: {df['action'].value_counts().to_dict()}")
    print(f"Distribución por jugador: {df['player'].value_counts().to_dict()}")
    print(f"Turnos promedio por batalla: {df.groupby('battle_id')['turn'].max().mean():.1f}")
    print(f"HP promedio: {df['hp'].mean():.1f}%")
    print(f"Spikes usados: {df['spikes_own'].sum() + df['spikes_opp'].sum()} capas")
    print(f"Stealth Rock usado: {df['stealth_rock_own'].sum() + df['stealth_rock_opp'].sum()} veces")

    # Pokémon más comunes
    top_pokemon = df['active_pokemon'].value_counts().head(10)
    print(f"\nPokémon más usados: {top_pokemon.to_dict()}")

    # Guardar dataset completo
    output_file = "data/processed/battle_turns_dataset.csv"
    df.to_csv(output_file, index=False)
    print(f"\nDataset guardado en: {output_file}")

    # Guardar estadísticas
    stats_file = "data/processed/dataset_stats.json"
    stats = {
        "total_turns": int(len(df)),
        "total_battles": int(df['battle_id'].nunique()),
        "action_distribution": df['action'].value_counts().to_dict(),
        "player_distribution": df['player'].value_counts().to_dict(),
        "avg_turns_per_battle": float(df.groupby('battle_id')['turn'].max().mean()),
        "avg_hp": float(df['hp'].mean()),
        "total_spikes": int(df['spikes_own'].sum() + df['spikes_opp'].sum()),
        "total_stealth_rock": int(df['stealth_rock_own'].sum() + df['stealth_rock_opp'].sum()),
        "top_pokemon": {k: int(v) for k, v in top_pokemon.head(5).to_dict().items()}
    }

    import json
    with open(stats_file, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"Estadísticas guardadas en: {stats_file}")

    return df

if __name__ == "__main__":
    process_all_logs()