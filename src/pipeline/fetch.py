import requests
import time
import json
import os

# ── CONFIG ──────────────────────────────────────────
FORMAT = "gen9ou"        # Singles competitivo
N_REPLAYS = 500          # Meta del día 1
OUTPUT_DIR = "data/raw"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── PASO 1: Obtener lista de replays ─────────────────
def get_replay_list(format_id, limit=500):
    """
    Showdown API devuelve hasta 51 replays por request.
    Necesitamos paginar con el parámetro 'before'.
    """
    replays = []
    before = None
    
    print(f"Buscando replays de formato: {format_id}")
    
    while len(replays) < limit:
        url = f"https://replay.pokemonshowdown.com/search.json?format={format_id}"
        if before:
            url += f"&before={before}"
        
        response = requests.get(url)
        
        if response.status_code != 200:
            print(f"Error {response.status_code}")
            break
            
        data = response.json()
        
        if not data:
            print("No hay más replays disponibles")
            break
        
        replays.extend(data)
        before = data[-1]["uploadtime"]
        
        print(f"  Replays obtenidos: {len(replays)}")
        time.sleep(0.5)  # Respetar rate limit
    
    return replays[:limit]

# ── PASO 2: Descargar log de cada replay ─────────────
def download_log(battle_id):
    """
    Cada replay tiene su log en texto plano.
    """
    url = f"https://replay.pokemonshowdown.com/{battle_id}.log"
    response = requests.get(url)
    
    if response.status_code == 200:
        return response.text
    return None

# ── PASO 3: Guardar todo localmente ──────────────────
def save_replays(format_id, n=500):
    replay_list = get_replay_list(format_id, limit=n)
    
    saved = 0
    failed = 0
    
    for replay in replay_list:
        battle_id = replay["id"]
        filepath = f"{OUTPUT_DIR}/{battle_id}.log"
        
        # Skip si ya existe
        if os.path.exists(filepath):
            saved += 1
            continue
        
        log = download_log(battle_id)
        
        if log:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(log)
            saved += 1
        else:
            failed += 1
        
        time.sleep(0.3)  # Rate limit
        
        if saved % 50 == 0:
            print(f"  Guardados: {saved} | Fallidos: {failed}")
    
    print(f"\nFinalizado: {saved} logs guardados en {OUTPUT_DIR}/")
    
    # Guardar metadata
    with open(f"{OUTPUT_DIR}/metadata.json", "w") as f:
        json.dump(replay_list, f, indent=2)
    
    return saved

# ── MAIN ─────────────────────────────────────────────
if __name__ == "__main__":
    save_replays(FORMAT, N_REPLAYS)
