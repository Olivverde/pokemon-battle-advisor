import numpy as np
from poke_env.player import Player
from poke_env.battle import Battle

def embed_battle(battle: Battle) -> np.ndarray:
    obs = np.zeros(41, dtype=np.float32)
    idx = 0

    # HP propio
    obs[idx] = battle.active_pokemon.current_hp_fraction
    idx += 1

    # Status propio (one-hot 6)
    status_map = {None: 0, "par": 1, "brn": 2, "psn": 3, "tox": 4, "frz": 5, "slp": 6}
    status = status_map.get(
        battle.active_pokemon.status.name.lower()
        if battle.active_pokemon.status else None, 0
    )
    if status < 6:
        obs[idx + status] = 1.0
    idx += 6

    # Speed propio
    obs[idx] = battle.active_pokemon.base_stats.get("spe", 0) / 400
    idx += 1

    # HP rival
    if battle.opponent_active_pokemon:
        obs[idx] = battle.opponent_active_pokemon.current_hp_fraction
    idx += 1

    # Status rival (one-hot 6)
    if battle.opponent_active_pokemon:
        status_opp = status_map.get(
            battle.opponent_active_pokemon.status.name.lower()
            if battle.opponent_active_pokemon.status else None, 0
        )
        if status_opp < 6:
            obs[idx + status_opp] = 1.0
    idx += 6

    # Speed rival
    if battle.opponent_active_pokemon:
        obs[idx] = battle.opponent_active_pokemon.base_stats.get("spe", 0) / 400
    idx += 1

    # Type advantage
    if battle.available_moves and battle.opponent_active_pokemon:
        multipliers = [battle.active_pokemon.damage_multiplier(m) 
                      for m in battle.available_moves]
        obs[idx] = max(multipliers) / 4.0
    idx += 1

    # HP equipo propio (6 slots)
    team = list(battle.team.values())
    for i in range(6):
        if i < len(team):
            obs[idx] = team[i].current_hp_fraction
        idx += 1

    # Vivos propios
    obs[idx] = sum(1 for p in battle.team.values() if not p.fainted) / 6
    idx += 1

    # HP equipo rival (6 slots)
    opp_team = list(battle.opponent_team.values())
    for i in range(6):
        if i < len(opp_team):
            obs[idx] = opp_team[i].current_hp_fraction
        idx += 1

    # Vivos rivales
    obs[idx] = sum(1 for p in battle.opponent_team.values() 
                   if not p.fainted) / 6
    idx += 1

    # PP ratio (4 moves)
    for i in range(4):
        if i < len(battle.available_moves):
            move = battle.available_moves[i]
            obs[idx] = move.current_pp / move.max_pp if move.max_pp > 0 else 0
        idx += 1

    # Boosts propios (atk, def, spe)
    boosts = battle.active_pokemon.boosts
    obs[idx] = boosts.get("atk", 0) / 6
    obs[idx+1] = boosts.get("def", 0) / 6
    obs[idx+2] = boosts.get("spe", 0) / 6
    idx += 3

    # Boosts rivales
    if battle.opponent_active_pokemon:
        opp_boosts = battle.opponent_active_pokemon.boosts
        obs[idx] = opp_boosts.get("atk", 0) / 6
        obs[idx+1] = opp_boosts.get("def", 0) / 6
        obs[idx+2] = opp_boosts.get("spe", 0) / 6

    return obs


def calc_reward(battle) -> float:
    if battle.won:
        return 1.0
    elif battle.lost:
        return -1.0
    vivos_propios = sum(1 for p in battle.team.values() if not p.fainted)
    vivos_rivales = sum(1 for p in battle.opponent_team.values() 
                        if not p.fainted)
    return (vivos_propios - vivos_rivales) / 6 * 0.1


def action_to_move(action: int, battle):
    # Force switch — solo switches disponibles
    if battle.force_switch:
        if battle.available_switches:
            return battle.available_switches[0]
        return None

    # Intentar move
    if action < 4:
        if battle.available_moves:
            idx = min(action, len(battle.available_moves) - 1)
            return battle.available_moves[idx]
    
    # Intentar switch
    if action >= 4 and battle.available_switches:
        switch_idx = action - 4
        switch_idx = min(switch_idx, len(battle.available_switches) - 1)
        return battle.available_switches[switch_idx]
    
    # Fallback — cualquier cosa disponible
    if battle.available_moves:
        return battle.available_moves[0]
    if battle.available_switches:
        return battle.available_switches[0]
    
    return None