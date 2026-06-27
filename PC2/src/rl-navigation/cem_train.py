import numpy as np
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cive_env import CIVENavEnv

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "rl")
MODEL_PATH = os.path.join(OUTPUT_DIR, "navigation_agent_cont")


def evaluate_params(w, b, hidden, seed=42, episodes=10):
    total_rew = 0.0
    wins = 0
    for ep in range(episodes):
        env = CIVENavEnv(max_steps=500)
        obs, _ = env.reset()
        ep_rew = 0.0
        for _ in range(500):
            h = np.tanh(obs @ w + b)
            action = h @ hidden
            action = np.clip(action, -3, 3)
            obs, reward, done, truncated, _ = env.step(action)
            ep_rew += reward
            if done or truncated:
                if reward > 10:
                    wins += 1
                break
        total_rew += ep_rew
    return total_rew / episodes, wins


def train(iterations=200, pop_size=50, elite_frac=0.2, seed=42):
    np.random.seed(seed)
    obs_dim = 14
    act_dim = 3
    hidden_dim = 32

    n_elite = max(2, int(pop_size * elite_frac))
    noise = 0.1

    w = np.random.randn(obs_dim, hidden_dim).astype(np.float32) * 0.1
    b = np.zeros(hidden_dim, dtype=np.float32)
    h = np.random.randn(hidden_dim, act_dim).astype(np.float32) * 0.1

    best_rew = -1e9
    best_params = None
    param_count = w.size + b.size + h.size

    for it in range(iterations):
        rewards = np.zeros(pop_size)
        all_params = []

        for i in range(pop_size):
            w_i = w + np.random.randn(*w.shape).astype(np.float32) * noise
            b_i = b + np.random.randn(*b.shape).astype(np.float32) * noise
            h_i = h + np.random.randn(*h.shape).astype(np.float32) * noise
            rew, _ = evaluate_params(w_i, b_i, h_i, episodes=3)
            rewards[i] = rew
            all_params.append((w_i, b_i, h_i))

        idx = np.argsort(-rewards)
        elite_idx = idx[:n_elite]

        w = np.mean([all_params[i][0] for i in elite_idx], axis=0)
        b = np.mean([all_params[i][1] for i in elite_idx], axis=0)
        h = np.mean([all_params[i][2] for i in elite_idx], axis=0)

        if rewards[idx[0]] > best_rew:
            best_rew = rewards[idx[0]]
            best_params = (w.copy(), b.copy(), h.copy())

        if it % 20 == 0 or it == iterations - 1:
            # Full evaluation
            final_rew, wins = evaluate_params(w, b, h, episodes=20)
            print(f"  iter {it:3d}: best={best_rew:.1f} avg={rewards.mean():.1f} "
                  f"final_rew={final_rew:.1f} wins={wins}/20")

    return best_params


def save_model(w, b, h):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    import pickle
    with open(MODEL_PATH + '.pkl', 'wb') as f:
        pickle.dump({'w': w, 'b': b, 'h': h}, f)
    print(f"Model saved to {MODEL_PATH}.pkl")


def load_model():
    import pickle
    with open(MODEL_PATH + '.pkl', 'rb') as f:
        data = pickle.load(f)
    return data['w'], data['b'], data['h']


def predict(obs, w, b, h):
    obs = np.asarray(obs, dtype=np.float32).reshape(1, -1)
    h_val = np.tanh(obs @ w + b)
    action = (h_val @ h).flatten()
    return np.clip(action, -3, 3)


if __name__ == "__main__":
    iters = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    print(f"[train] CEM training for {iters} iterations, pop_size=50")
    params = train(iterations=iters)
    if params:
        save_model(*params)
        final_rew, wins = evaluate_params(*params, episodes=50)
        print(f"[train] Final: reward={final_rew:.1f} wins={wins}/50")
