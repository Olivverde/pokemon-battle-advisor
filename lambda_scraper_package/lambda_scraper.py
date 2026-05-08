import json
import os
import time

import boto3
import requests

BUCKET = os.environ.get("RAW_BUCKET", "pokemon-advisor-raw-317520059338")
FORMAT = os.environ.get("POKEMON_FORMAT", "gen9ou")
MAX_REPLAYS = int(os.environ.get("MAX_REPLAYS", "50"))
SHOWDOWN_API = "https://replay.pokemonshowdown.com/search.json"
TIMEOUT = 10

s3_client = boto3.client("s3")


def get_replay_list() -> list[dict]:
    """Obtiene la lista de replays desde la API de Pokémon Showdown."""
    try:
        params = {"format": FORMAT}
        response = requests.get(SHOWDOWN_API, params=params, timeout=TIMEOUT)
        response.raise_for_status()
        replays = response.json()
        return replays[:MAX_REPLAYS]
    except Exception as e:
        print(f"❌ Error obteniendo lista de replays: {e}")
        return []


def replay_exists_in_s3(battle_id: str) -> bool:
    """Verifica si un replay ya existe en S3."""
    try:
        s3_client.head_object(Bucket=BUCKET, Key=f"logs/{battle_id}.log")
        return True
    except s3_client.exceptions.NoSuchKey:
        return False
    except Exception as e:
        print(f"⚠️  Error verificando {battle_id} en S3: {e}")
        return False


def download_log(battle_id: str) -> str | None:
    """Descarga el log de un replay desde Pokémon Showdown."""
    try:
        url = f"https://replay.pokemonshowdown.com/{battle_id}.log"
        response = requests.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"❌ Error descargando {battle_id}: {e}")
        return None


def upload_to_s3(battle_id: str, log_text: str) -> bool:
    """Sube el log a S3."""
    try:
        s3_client.put_object(
            Bucket=BUCKET,
            Key=f"logs/{battle_id}.log",
            Body=log_text.encode("utf-8"),
        )
        return True
    except Exception as e:
        print(f"❌ Error subiendo {battle_id} a S3: {e}")
        return False


def handler(event, context):
    """Handler principal de la Lambda function."""
    print(f"🚀 Iniciando descarga de replays")
    print(f"Format: {FORMAT}, Max replays: {MAX_REPLAYS}, Bucket: {BUCKET}")

    downloaded = 0
    skipped = 0
    errors = 0

    replays = get_replay_list()
    print(f"📊 Encontrados {len(replays)} replays disponibles")

    for replay in replays:
        battle_id = replay.get("id")
        if not battle_id:
            print(f"⚠️  Replay sin ID, omitiendo")
            errors += 1
            continue

        # Verificar si ya existe en S3
        if replay_exists_in_s3(battle_id):
            print(f"⏭️  {battle_id} ya existe en S3, omitiendo")
            skipped += 1
            time.sleep(0.3)
            continue

        # Descargar el log
        log_text = download_log(battle_id)
        if not log_text:
            errors += 1
            time.sleep(0.3)
            continue

        # Subir a S3
        if upload_to_s3(battle_id, log_text):
            print(f"✅ {battle_id} descargado y subido a S3")
            downloaded += 1
        else:
            errors += 1

        # Rate limiting
        time.sleep(0.3)

    message = f"Descargados: {downloaded}, Existentes: {skipped}, Errores: {errors}"
    print(f"📈 {message}")

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": message,
                "downloaded": downloaded,
                "skipped": skipped,
                "errors": errors,
            }
        ),
    }


# Para testing local
if __name__ == "__main__":
    event = {}
    context = None
    result = handler(event, context)
    print(result)
