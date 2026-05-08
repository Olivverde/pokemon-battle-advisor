import json
import os
import time

import boto3
import pandas as pd
import requests
from parser import parse_replay_log

RAW_BUCKET = os.environ.get("RAW_BUCKET", "pokemon-advisor-raw-317520059338")
PROCESSED_BUCKET = os.environ.get("PROCESSED_BUCKET", "pokemon-advisor-processed-317520059338")
SHOWDOWN_MOVE_API = "https://pokeapi.co/api/v2/move/"
MAX_KEYS = 1000
TIMEOUT = 10

s3_client = boto3.client("s3")


def list_s3_logs() -> list[str]:
    keys = []
    continuation_token = None

    while True:
        params = {
            "Bucket": RAW_BUCKET,
            "Prefix": "logs/",
            "MaxKeys": MAX_KEYS,
        }
        if continuation_token:
            params["ContinuationToken"] = continuation_token

        response = s3_client.list_objects_v2(**params)
        contents = response.get("Contents", [])
        keys.extend([item["Key"] for item in contents if item["Key"].endswith(".log")])

        if response.get("IsTruncated"):
            continuation_token = response.get("NextContinuationToken")
        else:
            break

    return keys


def download_log(key: str) -> str | None:
    try:
        response = s3_client.get_object(Bucket=RAW_BUCKET, Key=key)
        payload = response["Body"].read()
        return payload.decode("utf-8", errors="replace")
    except Exception as exc:
        print(f"Error descargando {key} desde S3: {exc}")
        return None


def normalize_move_name(move_name: str) -> str:
    normalized = move_name.strip().lower()
    normalized = normalized.replace(" ", "-")
    normalized = normalized.replace("'", "").replace(".", "").replace(",", "")
    normalized = normalized.replace(":", "").replace("é", "e").replace("á", "a")
    normalized = normalized.replace("í", "i").replace("ó", "o").replace("ú", "u")
    return normalized


def resolve_move_category(move_name: str, move_cache: dict) -> str:
    if not isinstance(move_name, str) or not move_name.strip():
        return "UNKNOWN"

    key = normalize_move_name(move_name)
    if key in move_cache:
        return move_cache[key]

    try:
        url = f"{SHOWDOWN_MOVE_API}{key}"
        response = requests.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        damage_class = response.json().get("damage_class", {}).get("name", "unknown")

        if damage_class == "physical":
            result = "ATTACK_PHYSICAL"
        elif damage_class == "special":
            result = "ATTACK_SPECIAL"
        elif damage_class == "status":
            result = "STATUS"
        else:
            result = "UNKNOWN"
    except Exception as exc:
        print(f"Error consultando PokeAPI para {move_name}: {exc}")
        result = "UNKNOWN"

    move_cache[key] = result
    time.sleep(0.2)
    return result


def process_dataframe(df: pd.DataFrame, move_cache: dict) -> pd.DataFrame:
    if df.empty:
        return df

    unknown_mask = df["action"] == "MOVE_UNKNOWN"
    unique_moves = df.loc[unknown_mask, "move_name"].dropna().unique()

    for move_name in unique_moves:
        category = resolve_move_category(move_name, move_cache)
        df.loc[(df["action"] == "MOVE_UNKNOWN") & (df["move_name"] == move_name), "action"] = category

    return df


def handler(event, context):
    print(f"Iniciando Lambda parser con RAW_BUCKET={RAW_BUCKET} y PROCESSED_BUCKET={PROCESSED_BUCKET}")

    processed_logs = 0
    total_rows = 0
    move_cache: dict[str, str] = {}

    keys = list_s3_logs()
    print(f"Encontrados {len(keys)} logs en S3")

    all_frames = []

    for key in keys:
        battle_id = key.split("/")[-1].replace(".log", "")
        log_text = download_log(key)

        if log_text is None:
            print(f"Omitiendo {key} por error de descarga")
            continue

        try:
            df = parse_replay_log(log_text, battle_id)
            df = process_dataframe(df, move_cache)
            if not df.empty:
                all_frames.append(df)
                processed_logs += 1
                total_rows += len(df)
            else:
                print(f"Advertencia: {battle_id} produjo DataFrame vacío")
        except Exception as exc:
            print(f"Error procesando log {key}: {exc}")
            continue

    if all_frames:
        combined_df = pd.concat(all_frames, ignore_index=True)
    else:
        combined_df = pd.DataFrame()

    output_csv = combined_df.to_csv(index=False)

    try:
        s3_client.put_object(
            Bucket=PROCESSED_BUCKET,
            Key="battle_turns_enriched.csv",
            Body=output_csv.encode("utf-8"),
        )
        print(f"Guardado CSV procesado en s3://{PROCESSED_BUCKET}/battle_turns_enriched.csv")
    except Exception as exc:
        print(f"Error guardando CSV en S3: {exc}")
        return {
            "statusCode": 500,
            "body": {"error": str(exc)},
        }

    move_unknown_remaining = int((combined_df["action"] == "MOVE_UNKNOWN").sum()) if not combined_df.empty else 0

    return {
        "statusCode": 200,
        "body": {
            "logs_procesados": processed_logs,
            "filas_generadas": len(combined_df),
            "move_unknown_restantes": move_unknown_remaining,
        },
    }


if __name__ == "__main__":
    result = handler({}, None)
    print(json.dumps(result, indent=2))
