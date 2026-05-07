"""Script para probar el parser con logs reales"""

import os
import pandas as pd
from src.pipeline.parser import parse_multiple_logs

def test_parser():
    """Prueba el parser con algunos logs descargados"""

    # Obtener lista de logs
    log_dir = "data/raw"
    log_files = [os.path.join(log_dir, f) for f in os.listdir(log_dir) if f.endswith(".log")]

    if not log_files:
        print("No se encontraron logs en data/raw/")
        return

    print(f"Encontrados {len(log_files)} logs")

    # Probar con los primeros 5 logs
    test_files = log_files[:5]
    print(f"Probando parser con {len(test_files)} logs...")

    # Parsear logs
    df = parse_multiple_logs(test_files)

    if df.empty:
        print("No se pudo parsear ningún log")
        return

    print("\nParser completado exitosamente!")
    print(f"Total de turnos extraídos: {len(df)}")
    print(f"Columnas: {list(df.columns)}")

    # Mostrar estadísticas
    print("\nEstadísticas:")
    print(f"Acciones únicas: {df['action'].value_counts().to_dict()}")
    print(f"Jugadores: {df['player'].value_counts().to_dict()}")
    print(f"Turnos promedio por batalla: {df.groupby('battle_id')['turn'].max().mean():.1f}")

    # Mostrar muestra de datos
    print("\nMuestra de datos:")
    print(df.head(10).to_string())

    # Guardar resultado de prueba
    output_file = "data/processed/parser_test_sample.csv"
    df.head(100).to_csv(output_file, index=False)
    print(f"\nMuestra guardada en: {output_file}")

if __name__ == "__main__":
    test_parser()