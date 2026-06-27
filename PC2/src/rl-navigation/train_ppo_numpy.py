import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ppo_numpy import train, quick_eval, save_model, forward_full
from cive_env import CIVENavEnv

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "rl")
MODEL_PATH = os.path.join(OUTPUT_DIR, "navigation_agent_cont")


def main(timesteps=100_000):
    np.random.seed(42)
    print(f"[train] Training PPO (numpy) for {timesteps} timesteps...")
    net = train(CIVENavEnv, steps=timesteps, seed=42)
    save_model(net, MODEL_PATH)
    print(f"[train] Model saved to {MODEL_PATH}.pkl")
    wins = quick_eval(net, CIVENavEnv, episodes=20)
    print(f"[train] Win rate: {wins}/20")


def load_and_predict(obs, deterministic=True):
    from ppo_numpy import load_model
    net = load_model(MODEL_PATH)
    return forward_full(np.asarray(obs, dtype=np.float32).reshape(1, -1), net.pi_params).flatten()


if __name__ == "__main__":
    ts = int(sys.argv[1]) if len(sys.argv) > 1 else 100_000
    main(ts)
