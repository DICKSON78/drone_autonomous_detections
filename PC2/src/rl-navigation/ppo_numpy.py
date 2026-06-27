import numpy as np
from typing import List, Tuple
import pickle
import os


def mlp(sizes: List[int]):
    layers = []
    for i in range(len(sizes) - 1):
        w = np.random.randn(sizes[i], sizes[i + 1]) * np.sqrt(2.0 / sizes[i])
        b = np.zeros(sizes[i + 1])
        layers.append([w, b])
    return layers


def forward(x, params):
    acts = [x]
    for w, b in params[:-1]:
        x = np.tanh(x @ w + b)
        acts.append(x)
    w, b = params[-1]
    return x @ w + b, acts


def forward_full(x, params):
    for w, b in params[:-1]:
        x = np.tanh(x @ w + b)
    w, b = params[-1]
    return x @ w + b


class CategoricalNet:
    def __init__(self, obs_dim, act_dim, hidden_sizes=(64, 64)):
        self.pi_params = mlp([obs_dim] + list(hidden_sizes) + [act_dim])
        self.v_params = mlp([obs_dim] + list(hidden_sizes) + [1])
        self.log_std = np.full(act_dim, -0.5)

    def get_action(self, obs):
        mean = forward_full(obs, self.pi_params)
        action = mean + np.exp(self.log_std) * np.random.randn(*mean.shape)
        logp = self._logp(action, mean)
        val = forward_full(obs, self.v_params).squeeze(-1)
        return action, logp, val

    def get_action_value(self, obs):
        mean = forward_full(obs, self.pi_params)
        action = mean + np.exp(self.log_std) * np.random.randn(*mean.shape)
        return action.squeeze()

    def _logp(self, action, mean):
        var = np.exp(2 * self.log_std)
        log_prob = -0.5 * ((action - mean) ** 2 / var + np.log(2 * np.pi) + 2 * self.log_std)
        return log_prob.sum(axis=-1)

    def evaluate(self, obs, act):
        mean = forward_full(obs, self.pi_params)
        logp = self._logp(act, mean)
        val = forward_full(obs, self.v_params).squeeze(-1)
        return logp, val, mean


def backprop_through_mlp(grad_output, acts, params):
    dws = []
    dbs = []
    grad = grad_output
    for i in range(len(params) - 1, -1, -1):
        w, b = params[i]
        act = acts[i]
        dw = act.T @ grad
        db = grad.sum(axis=0)
        if i > 0:
            grad = grad @ w.T * (1 - act ** 2)
        dws.insert(0, dw)
        dbs.insert(0, db)
    return dws, dbs


class PPOBuffer:
    def __init__(self, obs_dim, act_dim, size, gamma=0.99, lam=0.95):
        self.obs_buf = np.zeros((size, obs_dim), dtype=np.float32)
        self.act_buf = np.zeros((size, act_dim), dtype=np.float32)
        self.adv_buf = np.zeros(size, dtype=np.float32)
        self.ret_buf = np.zeros(size, dtype=np.float32)
        self.val_buf = np.zeros(size, dtype=np.float32)
        self.logp_buf = np.zeros(size, dtype=np.float32)
        self.rew_buf = np.zeros(size, dtype=np.float32)
        self.gamma, self.lam = gamma, lam
        self.ptr, self.path_start_idx = 0, 0
        self.max_size = size

    def store(self, obs, act, rew, val, logp):
        i = self.ptr
        self.obs_buf[i] = obs
        self.act_buf[i] = act
        self.rew_buf[i] = rew
        self.val_buf[i] = val
        self.logp_buf[i] = logp
        self.ptr += 1

    def finish_path(self, last_val=0.0):
        s = self.path_start_idx
        path = np.arange(s, self.ptr)
        rews = self.rew_buf[path]
        vals = np.append(self.val_buf[path], last_val)
        deltas = rews + self.gamma * vals[1:] - vals[:-1]
        adv = np.zeros_like(rews)
        gae = 0.0
        for t in reversed(range(len(rews))):
            gae = deltas[t] + self.gamma * self.lam * gae
            adv[t] = gae
        self.adv_buf[path] = adv
        self.ret_buf[path] = adv + self.val_buf[path]
        self.path_start_idx = self.ptr

    def get(self):
        n = self.ptr
        adv = self.adv_buf[:n]
        adv = (adv - adv.mean()) / (adv.std() + 1e-8)
        return (self.obs_buf[:n], self.act_buf[:n],
                adv, self.ret_buf[:n], self.logp_buf[:n])


def _sgd_step(params, dws, dbs, lr):
    for i in range(len(params)):
        params[i][0] -= lr * dws[i] / dws[i].size ** 0.5
        params[i][1] -= lr * dbs[i] / dbs[i].size ** 0.5


def ppo_update(net, obs, act, adv, ret, old_logp,
               clip_ratio=0.2, pi_lr=3e-4, vf_lr=1e-3,
               train_iters=80, target_kl=0.01):
    n = len(obs)

    for _ in range(train_iters):
        logp, val, mean = net.evaluate(obs, act)

        ratio = np.exp(logp - old_logp)
        clip_adv = np.clip(ratio, 1 - clip_ratio, 1 + clip_ratio) * adv
        pi_loss = -(np.minimum(ratio * adv, clip_adv)).mean()

        _, acts_pi = forward(obs, net.pi_params)
        indicator = np.where(ratio * adv < clip_adv, 1, 0)
        pg_scale = -(adv * indicator * ratio)
        d_mean = (pg_scale.reshape(-1, 1) * (act - mean) /
                  np.exp(net.log_std) ** 2) / n
        dws, dbs = backprop_through_mlp(d_mean, acts_pi, net.pi_params)
        _sgd_step(net.pi_params, dws, dbs, pi_lr)

        v_out, acts_v = forward(obs, net.v_params)
        v_loss = ((val - ret) ** 2).mean()
        d_val = 2 * (val - ret).reshape(-1, 1) / n
        dws_v, dbs_v = backprop_through_mlp(d_val, acts_v, net.v_params)
        _sgd_step(net.v_params, dws_v, dbs_v, vf_lr)

        with np.errstate(all='ignore'):
            kl = (old_logp - logp).mean()
        if kl > 1.5 * target_kl:
            break


def train(env_fn, steps=100_000, seed=0):
    np.random.seed(seed)
    env = env_fn()
    obs_dim = env.observation_space.shape[0]
    act_dim = env.action_space.shape[0]

    net = CategoricalNet(obs_dim, act_dim)
    buf = PPOBuffer(obs_dim, act_dim, 2048, gamma=0.99, lam=0.95)

    obs, _ = env.reset()
    ep_rews = []
    for t in range(steps):
        action, logp, val = net.get_action(obs.reshape(1, -1))
        action = action.flatten()
        val = val.item()
        logp = logp.item()

        next_obs, reward, done, truncated, _ = env.step(action)
        buf.store(obs, action, reward, val, logp)
        obs = next_obs

        epoch_end = (t + 1) % buf.max_size == 0 or done or truncated

        if done or truncated:
            buf.finish_path(0.0)
            obs, _ = env.reset()
        elif epoch_end:
            val_last = forward_full(obs.reshape(1, -1), net.v_params).item()
            buf.finish_path(val_last)

        if epoch_end:
            batch = buf.get()
            ppo_update(net, *batch)
            buf.ptr, buf.path_start_idx = 0, 0
            if (t + 1) % (buf.max_size * 5) == 0:
                wins = quick_eval(net, env_fn)
                print(f"  step {t+1}: win rate {wins}/10")

    return net


def quick_eval(net, env_fn, episodes=10):
    env = env_fn()
    wins = 0
    for _ in range(episodes):
        obs, _ = env.reset()
        for _ in range(env.max_steps):
            action = forward_full(obs.reshape(1, -1), net.pi_params).flatten()
            obs, reward, done, truncated, _ = env.step(action)
            if done or truncated:
                if reward > 10:
                    wins += 1
                break
    return wins


def save_model(net, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + '.pkl', 'wb') as f:
        pickle.dump({'pi_params': net.pi_params, 'v_params': net.v_params,
                      'log_std': net.log_std}, f)


def load_model(path):
    with open(path + '.pkl', 'rb') as f:
        data = pickle.load(f)
    net = object.__new__(CategoricalNet)
    net.pi_params = data['pi_params']
    net.v_params = data['v_params']
    net.log_std = data['log_std']
    return net
