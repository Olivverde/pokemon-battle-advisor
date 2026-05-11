import asyncio
from poke_env.player import RandomPlayer
from poke_env import LocalhostServerConfiguration
from poke_env.ps_client.account_configuration import AccountConfiguration

async def main():
    
    account1 = AccountConfiguration("RandomPlayer1", None)
    account2 = AccountConfiguration("RandomPlayer2", None)
    
    player1 = RandomPlayer(
        account_configuration=account1,
        battle_format="gen8randombattle",
        server_configuration=LocalhostServerConfiguration,
    )
    
    player2 = RandomPlayer(
        account_configuration=account2,
        battle_format="gen8randombattle",
        server_configuration=LocalhostServerConfiguration,
    )

    # Esperar a que ambos estén conectados
    await asyncio.sleep(2)

    await player1.battle_against(player2, n_battles=10)

    print(f"Player 1 ganó: {player1.n_won_battles} / 10")
    print(f"Player 2 ganó: {player2.n_won_battles} / 10")

if __name__ == "__main__":
    asyncio.run(main())