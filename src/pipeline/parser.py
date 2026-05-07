"""Parser para logs de batallas de Pokémon Showdown"""

from typing import Dict, List, Any, Optional
import re
import pandas as pd


def parse_replay_log(log_content: str, battle_id: str) -> pd.DataFrame:
    """
    Parsea un log de batalla y extrae datos turno por turno.

    Args:
        log_content: Contenido del log como string
        battle_id: ID de la batalla (nombre del archivo)

    Returns:
        DataFrame con una fila por turno y acción
    """
    lines = log_content.strip().split("\n")

    # Estado del juego
    game_state = {
        "turn": 0,
        "p1_active": None,
        "p2_active": None,
        "p1_hp": 100,
        "p2_hp": 100,
        "weather": None,
        "terrain": None,
        "p1_spikes": 0,
        "p2_spikes": 0,
        "p1_stealth_rock": False,
        "p2_stealth_rock": False,
    }

    # Dataset de salida
    turn_data = []

    # Buffer para acciones del turno actual
    current_turn_actions = {"p1": None, "p2": None}

    for line in lines:
        if not line.strip() or line.startswith(">"):
            continue

        parts = line.split("|")

        if len(parts) < 2:
            continue

        tag = parts[1]

        # Inicio de turno
        if tag == "turn":
            # Guardar acciones del turno anterior
            if game_state["turn"] > 0:
                _save_turn_actions(turn_data, game_state, current_turn_actions, battle_id)

            # Resetear acciones para nuevo turno
            current_turn_actions = {"p1": None, "p2": None}
            game_state["turn"] = int(parts[2])

        # Cambio de Pokémon
        elif tag == "switch":
            player = parts[2][0:2]  # p1a o p2a
            pokemon_full = parts[3]
            hp_str = parts[4] if len(parts) > 4 else "100/100"

            # Extraer especie real (sin nickname ni género)
            pokemon_species = _extract_pokemon_species(pokemon_full)
            hp_percent = _parse_hp(hp_str)

            # Actualizar estado
            if player.startswith("p1"):
                game_state["p1_active"] = pokemon_species
                game_state["p1_hp"] = hp_percent
                current_turn_actions["p1"] = "SWITCH"
            else:
                game_state["p2_active"] = pokemon_species
                game_state["p2_hp"] = hp_percent
                current_turn_actions["p2"] = "SWITCH"

        # Movimiento usado
        elif tag == "move":
            player = parts[2][0:2]
            move_name = parts[3]

            # Clasificar movimiento
            action_type = _classify_move(move_name)

            if player.startswith("p1"):
                current_turn_actions["p1"] = action_type
            else:
                current_turn_actions["p2"] = action_type

        # Daño recibido
        elif tag == "-damage":
            if len(parts) >= 4:
                target = parts[2]
                hp_str = parts[3]

                hp_percent = _parse_hp(hp_str)

                if target.startswith("p1"):
                    game_state["p1_hp"] = hp_percent
                elif target.startswith("p2"):
                    game_state["p2_hp"] = hp_percent

        # Curación
        elif tag == "-heal":
            if len(parts) >= 4:
                target = parts[2]
                hp_str = parts[3]

                hp_percent = _parse_hp(hp_str)

                if target.startswith("p1"):
                    game_state["p1_hp"] = hp_percent
                elif target.startswith("p2"):
                    game_state["p2_hp"] = hp_percent

        # Clima
        elif tag == "-weather":
            if len(parts) >= 3:
                weather = parts[2]
                if weather == "none":
                    game_state["weather"] = None
                else:
                    game_state["weather"] = weather

        # Terreno
        elif tag == "-fieldstart":
            if len(parts) >= 3 and "terrain" in parts[2]:
                terrain = parts[2].replace("terrain", "").strip()
                game_state["terrain"] = terrain

        elif tag == "-fieldend":
            if len(parts) >= 3 and "terrain" in parts[2]:
                game_state["terrain"] = None

        # Entry hazards
        elif tag == "-sidestart":
            if len(parts) >= 4:
                side = parts[2]  # p1 o p2
                hazard = parts[3]

                if hazard == "Spikes":
                    if side == "p1":
                        game_state["p1_spikes"] = min(game_state["p1_spikes"] + 1, 3)
                    else:
                        game_state["p2_spikes"] = min(game_state["p2_spikes"] + 1, 3)

                elif hazard == "stealthrock":
                    if side == "p1":
                        game_state["p1_stealth_rock"] = True
                    else:
                        game_state["p2_stealth_rock"] = True

        elif tag == "-sideend":
            if len(parts) >= 4:
                side = parts[2]
                hazard = parts[3]

                if hazard == "Spikes":
                    if side == "p1":
                        game_state["p1_spikes"] = max(game_state["p1_spikes"] - 1, 0)
                    else:
                        game_state["p2_spikes"] = max(game_state["p2_spikes"] - 1, 0)

                elif hazard == "stealthrock":
                    if side == "p1":
                        game_state["p1_stealth_rock"] = False
                    else:
                        game_state["p2_stealth_rock"] = False

    # Guardar último turno si tiene acciones
    if game_state["turn"] > 0 and (current_turn_actions["p1"] or current_turn_actions["p2"]):
        _save_turn_actions(turn_data, game_state, current_turn_actions, battle_id)

    return pd.DataFrame(turn_data)


def _save_turn_actions(turn_data: List[Dict], game_state: Dict, actions: Dict, battle_id: str):
    """Guarda las acciones de un turno en el dataset"""

    # Acción del jugador 1
    if actions["p1"]:
        turn_data.append({
            "battle_id": battle_id,
            "turn": game_state["turn"],
            "player": "p1",
            "active_pokemon": game_state["p1_active"],
            "hp": game_state["p1_hp"],
            "weather": game_state["weather"],
            "terrain": game_state["terrain"],
            "spikes_own": game_state["p1_spikes"],
            "spikes_opp": game_state["p2_spikes"],
            "stealth_rock_own": game_state["p1_stealth_rock"],
            "stealth_rock_opp": game_state["p2_stealth_rock"],
            "action": actions["p1"]
        })

    # Acción del jugador 2
    if actions["p2"]:
        turn_data.append({
            "battle_id": battle_id,
            "turn": game_state["turn"],
            "player": "p2",
            "active_pokemon": game_state["p2_active"],
            "hp": game_state["p2_hp"],
            "weather": game_state["weather"],
            "terrain": game_state["terrain"],
            "spikes_own": game_state["p2_spikes"],
            "spikes_opp": game_state["p1_spikes"],
            "stealth_rock_own": game_state["p2_stealth_rock"],
            "stealth_rock_opp": game_state["p1_stealth_rock"],
            "action": actions["p2"]
        })


def _extract_pokemon_species(pokemon_str: str) -> str:
    """Extrae la especie real del Pokémon (sin nickname ni género)"""
    # Formato: "Nickname|Species, Gender" o solo "Species, Gender"
    if "|" in pokemon_str:
        # Tiene nickname: "Bilmuri|Okidogi, M"
        species_part = pokemon_str.split("|")[1]
    else:
        # Sin nickname: "Okidogi, M"
        species_part = pokemon_str

    # Quitar género: "Okidogi, M" -> "Okidogi"
    return species_part.split(",")[0].strip()


def _parse_hp(hp_str: str) -> int:
    """Parsea string de HP como '80/100' a porcentaje"""
    if "/" in hp_str:
        current, total = hp_str.split("/")
        try:
            return int((float(current) / float(total)) * 100)
        except ValueError:
            return 100
    return 100


def _classify_move(move_name: str) -> str:
    """Clasifica un movimiento como STATUS o MOVE_UNKNOWN"""
    # Lista de movimientos de estado comunes
    status_moves = {
        "protect", "detect", "spikyshield", "kingsshield", "banefulbunker",
        "toxic", "stealthrock", "spikes", "toxicspikes", "stickyweb",
        "reflect", "lightscreen", "auroraveil", "safeguard",
        "mist", "tailwind", "healbell", "aromatherapy", "wish", "healingwish",
        "lunardance", "rest", "sleeptalk", "substitute", "leechseed",
        "curse", "bellydrum", "bulkup", "calmmind", "cosmicpower", "dragondance",
        "quiverdance", "shellsmash", "swordsdance", "nastyplot", "tailglow",
        "agility", "rockpolish", "autotomize", "shiftgear", "workup",
        "honeclaws", "coil", "meditate", "sharpen", "howl", "morningsun",
        "moonlight", "synthesis", "growth", "acidarmor", "barrier", "cosmicpower",
        "cottonguard", "defensecurl", "harden", "irondefense", "skullbash",
        "stockpile", "withdraw", "amnesia", "chargebeam", "fierydance",
        "focusenergy", "geomancy", "ingrain", "meditate", "powertrick",
        "psychup", "quiverdance", "ragepowder", "rototiller", "shellsmash",
        "tailwind", "telekinesis", "yawn", "confuseray", "darkvoid",
        "glare", "grasswhistle", "hypnosis", "lovelykiss", "sing",
        "sleeppowder", "spore", "supersonic", "sweetkiss", "teeterdance",
        "thunderwave", "toxic", "willowisp", "poisongas", "poisonpowder",
        "smog", "sludge", "venoshock", "acid", "bite", "crunch", "darkpulse",
        "feintattack", "nightslash", "pursuit", "shadowball", "shadowclaw",
        "shadowpunch", "shadowsneak", "suckerpunch", "thief", "knockoff",
        "trick", "switcheroo", "skillswap", "trickroom", "gravity",
        "magicroom", "wonderroom", "healblock", "embargo", "taunt",
        "torment", "disable", "encore", "attract", "captivate", "charm",
        "cottonguard", "defog", "haze", "rapidspin", "roar", "whirlwind",
        "circlethrow", "dragontail", "uturn", "voltswitch", "watershuriken"
    }

    move_lower = move_name.lower().replace(" ", "").replace("-", "")

    if move_lower in status_moves:
        return "STATUS"
    else:
        return "MOVE_UNKNOWN"


def parse_multiple_logs(log_files: List[str]) -> pd.DataFrame:
    """
    Parsea múltiples archivos de log y combina los resultados.

    Args:
        log_files: Lista de rutas a archivos .log

    Returns:
        DataFrame combinado con todos los turnos
    """
    all_data = []

    for log_file in log_files:
        try:
            # Manejar encoding problemático
            with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            battle_id = log_file.split("/")[-1].replace(".log", "")
            df = parse_replay_log(content, battle_id)
            all_data.append(df)

        except Exception as e:
            print(f"Error procesando {log_file}: {e}")
            continue

    if all_data:
        return pd.concat(all_data, ignore_index=True)
    else:
        return pd.DataFrame()


# Funciones legacy para compatibilidad
def extract_features_from_turn(turn_data: Dict[str, Any]) -> Dict[str, float]:
    """Extrae features de ingeniería de un turno de batalla (legacy)"""
    features = {}

    # TODO: Implementar extracción de features
    # - HP relativo
    # - Ventaja de tipos
    # - Boosts de stats
    # - Predicción de movimiento

    return features
