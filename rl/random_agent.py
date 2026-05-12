import asyncio
from poke_env.player import RandomPlayer
from poke_env import LocalhostServerConfiguration
from poke_env.ps_client.account_configuration import AccountConfiguration

async def main():
    
    account1 = AccountConfiguration("RandomPlayer1", None)
    account2 = AccountConfiguration("RandomPlayer2", None)
    
    player1 = RandomPlayer(
        account_configuration=account1,
        battle_format="gen1randombattle",
        server_configuration=LocalhostServerConfiguration,
    )
    
    player2 = RandomPlayer(
        account_configuration=account2,
        battle_format="gen1randombattle",
        server_configuration=LocalhostServerConfiguration,
    )

    await asyncio.sleep(2)

    total = 1000
    bloque = 10
    
    for i in range(total // bloque):
        await player1.battle_against(player2, n_battles=bloque)
        print(f"Batalla {(i+1)*bloque:3d}/100 | "
              f"P1: {player1.n_won_battles} ganadas | "
              f"Win rate P1: {player1.n_won_battles/((i+1)*bloque)*100:.1f}%")

    # ← AQUÍ va el análisis de batallas
    print("\n--- Resumen de batallas ---")
    for battle_id, battle in list(player1.battles.items())[:5]:
        print(f"\nBatalla: {battle_id}")
        print(f"  Ganó: {battle.won}")
        print(f"  Turnos: {battle.turn}")
        print(f"  Equipo propio: {[p.species for p in battle.team.values()]}")
        print(f"  Equipo rival: {[p.species for p in battle.opponent_team.values()]}")

    # Al final de main(), después de las batallas
    battle = list(player1.battles.values())[0]

    # Al final de main()
    battle = list(player1.battles.values())[0]

    print("\n--- TODOS LOS ATRIBUTOS DISPONIBLES ---")
    for attr in dir(battle):
        if not attr.startswith('_'):
            try:
                value = getattr(battle, attr)
                if not callable(value):
                    print(f"{attr}: {value}")
            except:
                pass

if __name__ == "__main__":
    asyncio.run(main())