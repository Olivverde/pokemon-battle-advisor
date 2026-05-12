import asyncio
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from collections import deque
import random
from poke_env.player import Player, RandomPlayer
from poke_env import LocalhostServerConfiguration
from poke_env.ps_client.account_configuration import AccountConfiguration
from pokemon_env import embed_battle, calc_reward, action_to_move

# ── RED NEURONAL ─────────────────────────────────────────
class DQNNetwork(nn.Module):
    def __init__(self, obs_size=41, n_actions=9):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(obs_size, 128),
            nn.ReLU(),
            nn.Linear(128, 128),
            nn.ReLU(),
            nn.Linear(128, n_actions)
        )
    
    def forward(self, x):
        return self.net(x)

# ── REPLAY BUFFER ─────────────────────────────────────────
class ReplayBuffer:
    def __init__(self, capacity=10000):
        self.buffer = deque(maxlen=capacity)
    
    def push(self, state, action, reward, next_state, done):
        self.buffer.append((state, action, reward, next_state, done))
    
    def sample(self, batch_size):
        batch = random.sample(self.buffer, batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)
        return (np.array(states), np.array(actions), 
                np.array(rewards), np.array(next_states), 
                np.array(dones))
    
    def __len__(self):
        return len(self.buffer)

# ── AGENTE DQN ────────────────────────────────────────────
class DQNAgent(Player):
    
    def __init__(self, model, buffer, epsilon, **kwargs):
        super().__init__(**kwargs)
        self.model = model
        self.buffer = buffer
        self.epsilon = epsilon
        self.last_obs = None
        self.last_action = None
        self.total_reward = 0
        self.battles_done = 0

    def choose_move(self, battle):
        obs = embed_battle(battle)
        
        # Epsilon-greedy
        if random.random() < self.epsilon:
            action = random.randint(0, 8)
        else:
            with torch.no_grad():
                q_values = self.model(torch.FloatTensor(obs).unsqueeze(0))
                action = q_values.argmax().item()

        # Guardar transición anterior
        if self.last_obs is not None:
            reward = calc_reward(battle)
            self.buffer.push(
                self.last_obs, self.last_action, 
                reward, obs, False
            )
            self.total_reward += reward

        self.last_obs = obs
        self.last_action = action

        # Convertir acción a orden
        move = action_to_move(action, battle)
        if move is not None:
            return self.create_order(move)
        return self.choose_random_move(battle)

    def _battle_finished_callback(self, battle):
        # Guardar transición final
        if self.last_obs is not None:
            final_obs = embed_battle(battle)
            reward = calc_reward(battle)
            self.buffer.push(
                self.last_obs, self.last_action,
                reward, final_obs, True
            )
            self.total_reward += reward

        self.last_obs = None
        self.last_action = None
        self.battles_done += 1

# ── LOOP DE ENTRENAMIENTO ─────────────────────────────────
async def train():
    
    # Parámetros
    N_BATTLES = 4000
    BATCH_SIZE = 32
    LEARNING_STARTS = 500
    GAMMA = 0.99
    LR = 1e-4
    EPSILON_START = 1.0
    EPSILON_END = 0.05
    EPSILON_DECAY = 0.999
    LOG_EVERY = 100

    # Inicializar
    model = DQNNetwork()
    target_model = DQNNetwork()
    target_model.load_state_dict(model.state_dict())
    buffer = ReplayBuffer(capacity=50000)
    optimizer = optim.Adam(model.parameters(), lr=LR)
    epsilon = EPSILON_START

    # Oponente random
    opponent = RandomPlayer(
        account_configuration=AccountConfiguration("Opponent", None),
        battle_format="gen1randombattle",
        server_configuration=LocalhostServerConfiguration,
    )

    # Agente DQN
    agent = DQNAgent(
        model=model,
        buffer=buffer,
        epsilon=epsilon,
        account_configuration=AccountConfiguration("DQNAgent", None),
        battle_format="gen1randombattle",
        server_configuration=LocalhostServerConfiguration,
    )

    print(f"Entrenando DQN por {N_BATTLES} batallas...")
    print(f"{'Batalla':>8} | {'Win Rate':>8} | {'Epsilon':>8} | {'Buffer':>8}")
    print("-" * 45)

    wins_window = deque(maxlen=LOG_EVERY)

    for i in range(N_BATTLES):
        
        # Actualizar epsilon
        agent.epsilon = epsilon
        
        # Jugar una batalla
        await agent.battle_against(opponent, n_battles=1)
        
        # Registrar resultado
        wins_window.append(agent.n_won_battles)


        # Entrenar si hay suficientes experiencias
        if len(buffer) >= LEARNING_STARTS and len(buffer) >= BATCH_SIZE:
            states, actions, rewards, next_states, dones = buffer.sample(BATCH_SIZE)
            
            states_t = torch.FloatTensor(states)
            actions_t = torch.LongTensor(actions)
            rewards_t = torch.FloatTensor(rewards)
            next_states_t = torch.FloatTensor(next_states)
            dones_t = torch.FloatTensor(dones)

            # Q values actuales
            q_values = model(states_t).gather(1, actions_t.unsqueeze(1)).squeeze(1)
            
            # Q values target
            with torch.no_grad():
                next_q = target_model(next_states_t).max(1)[0]
                target_q = rewards_t + GAMMA * next_q * (1 - dones_t)

            loss = nn.MSELoss()(q_values, target_q)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        # Actualizar target network cada 10 batallas
        if i % 10 == 0:
            target_model.load_state_dict(model.state_dict())

        # Decay epsilon
        epsilon = max(EPSILON_END, epsilon * EPSILON_DECAY)

        # Log cada N batallas
        if (i + 1) % LOG_EVERY == 0:
            win_rate = agent.n_won_battles / (i + 1) * 100
            print(f"{i+1:>8} | {win_rate:>7.1f}% | {epsilon:>8.3f} | {len(buffer):>8}")

    # Resultado final
    print(f"\nFinal: {agent.n_won_battles}/{N_BATTLES} ganadas = {agent.n_won_battles/N_BATTLES*100:.1f}%")
    
    # Guardar modelo
    torch.save(model.state_dict(), "dqn_pokemon_v1.pt")
    print("Modelo guardado en dqn_pokemon_v1.pt")

if __name__ == "__main__":
    asyncio.run(train())