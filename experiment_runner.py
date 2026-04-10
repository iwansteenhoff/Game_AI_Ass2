#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import json
import os
import signal
import subprocess
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional







BATTLESNAKE_CMD = "battlesnake"        # Config
DEFAULT_WIDTH = 11
DEFAULT_HEIGHT = 11
DEFAULT_GAMEMODE = "standard"
DEFAULT_MAP = "hz_hazard_pits"
DEFAULT_FOOD_SPAWN_CHANCE = 25
DEFAULT_MINIMUM_FOOD = 2
DEFAULT_TIMEOUT = 1000

OUTPUT_DIR = Path("tournament_results")
OUTPUT_DIR.mkdir(exist_ok=True)

SERVER_START_WAIT = 2.0
SERVER_STOP_WAIT = 1.0



        #Agent definitions

@dataclass
class AgentConfig:
    name: str
    script: str
    port: int
    kind: str  # e.g. "heuristic", "mcts"
    rave: Optional[bool] = None
    k: Optional[int] = None
    rollout_depth: Optional[int] = None
    rollout_policy: Optional[str] = None   # "random" or "heuristic"
    expansion_policy: Optional[str] = None # "random" or "heuristic"
    exploration_weight: Optional[float] = None
    timeout_ms: Optional[int] = None

    def to_cmd(self) -> List[str]:
        cmd = ["python", self.script, "--port", str(self.port)]

        if self.rave is not None:
            cmd += ["--rave", str(self.rave).lower()]
        if self.k is not None:
            cmd += ["--k", str(self.k)]
        if self.rollout_depth is not None:
            cmd += ["--rollout-depth", str(self.rollout_depth)]
        if self.rollout_policy is not None:
            cmd += ["--rollout-policy", self.rollout_policy]
        if self.expansion_policy is not None:
            cmd += ["--expansion-policy", self.expansion_policy]
        if self.exploration_weight is not None:
            cmd += ["--exploration-weight", str(self.exploration_weight)]
        if self.timeout_ms is not None:
            cmd += ["--timeout-ms", str(self.timeout_ms)]

        return cmd



          #utility
def safe_name(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in name)


def timestamp_str() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def terminate_process(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return

    try:
        proc.terminate()
        proc.wait(timeout=SERVER_STOP_WAIT)
    except subprocess.TimeoutExpired:
        proc.kill()


def start_agent(agent: AgentConfig) -> subprocess.Popen:
    print(f"Starting agent {agent.name} on port {agent.port}")

    env = os.environ.copy()
    env["PORT"] = str(agent.port)

    proc = subprocess.Popen(
        agent.to_cmd(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        preexec_fn=os.setsid if os.name != "nt" else None,
        env=env,
    )
    return proc


def stop_agents(procs: List[subprocess.Popen]) -> None:
    for proc in procs:
        terminate_process(proc)


def load_last_state(path: Path):
    if not path.exists():
        return None

    try:
        with path.open("r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except Exception:
        return None

    for line in reversed(lines):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and "turn" in obj:
            return obj

    return None

def parse_match_statistics(log_path: Path, agent_a_name: str, agent_b_name: str) -> dict:
    import json

    def empty_stats():
        return {
            "survival_turns": 0,
            "final_length": 0,
            "max_length": 0,
            "food_eaten": 0,
            "hazard_turns": 0,
            "hazard_entries": 0,
            "avg_health": 0.0,
            "min_health": None,
            "avg_latency": 0.0,
            "death_cause": "unknown",
            "alive_final": 0,
        }

    stats = {
        agent_a_name: empty_stats(),
        agent_b_name: empty_stats(),
    }

    turn_states = []
    winner_name = None
    is_draw = None

    if not log_path.exists():
        return {
            "winner_from_log": None,
            "is_draw_from_log": None,
            "survival_turns_a": 0,
            "survival_turns_b": 0,
            "final_length_a": 0,
            "final_length_b": 0,
            "max_length_a": 0,
            "max_length_b": 0,
            "food_eaten_a": 0,
            "food_eaten_b": 0,
            "hazard_turns_a": 0,
            "hazard_turns_b": 0,
            "hazard_entries_a": 0,
            "hazard_entries_b": 0,
            "avg_health_a": 0.0,
            "avg_health_b": 0.0,
            "min_health_a": None,
            "min_health_b": None,
            "avg_latency_a": 0.0,
            "avg_latency_b": 0.0,
            "death_cause_a": "unknown",
            "death_cause_b": "unknown",
            "alive_final_a": 0,
            "alive_final_b": 0,
        }

    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue


            
            if isinstance(obj, dict) and "turn" in obj and "board" in obj:
                turn_states.append(obj)

            if isinstance(obj, dict) and "winnerName" in obj:
                winner_name = obj.get("winnerName")
                is_draw = obj.get("isDraw")

    
    if not turn_states:
        return {
            "winner_from_log": winner_name,
            "is_draw_from_log": is_draw,
            "survival_turns_a": 0,
            "survival_turns_b": 0,
            "final_length_a": 0,
            "final_length_b": 0,
            "max_length_a": 0,
            "max_length_b": 0,
            "food_eaten_a": 0,
            "food_eaten_b": 0,
            "hazard_turns_a": 0,
            "hazard_turns_b": 0,
            "hazard_entries_a": 0,
            "hazard_entries_b": 0,
            "avg_health_a": 0.0,
            "avg_health_b": 0.0,
            "min_health_a": None,
            "min_health_b": None,
            "avg_latency_a": 0.0,
            "avg_latency_b": 0.0,
            "death_cause_a": "unknown",
            "death_cause_b": "unknown",
            "alive_final_a": 0,
            "alive_final_b": 0,
        }

    health_history = {agent_a_name: [], agent_b_name: []}
    latency_history = {agent_a_name: [], agent_b_name: []}
    prev_hazard = {agent_a_name: False, agent_b_name: False}

    # Track presence by turn for death analysis
    present_by_turn = {agent_a_name: [], agent_b_name: []}

    for turn_state in turn_states:
        turn = turn_state["turn"]
        snakes = turn_state["board"]["snakes"]
        hazards = turn_state["board"].get("hazards", [])

        snake_map = {snake["name"]: snake for snake in snakes}

        for agent_name in [agent_a_name, agent_b_name]:
            snake = snake_map.get(agent_name)
            present_by_turn[agent_name].append((turn, snake))

            if snake is None:
                continue

            stats[agent_name]["survival_turns"] = turn
            stats[agent_name]["final_length"] = snake.get("length", 0)
            stats[agent_name]["max_length"] = max(
                stats[agent_name]["max_length"],
                snake.get("length", 0),
            )

            health = snake.get("health", 0)
            health_history[agent_name].append(health)

            if stats[agent_name]["min_health"] is None:
                stats[agent_name]["min_health"] = health
            else:
                stats[agent_name]["min_health"] = min(stats[agent_name]["min_health"], health)

            latency_raw = snake.get("latency", "0")
            try:
                latency_val = float(latency_raw)
            except (ValueError, TypeError):
                latency_val = 0.0
            latency_history[agent_name].append(latency_val)

            head = snake.get("head", snake["body"][0])
            in_hazard = head in hazards

            if in_hazard:
                stats[agent_name]["hazard_turns"] += 1

            if in_hazard and not prev_hazard[agent_name]:
                stats[agent_name]["hazard_entries"] += 1

            prev_hazard[agent_name] = in_hazard

    # Food eaten from positive length changes
    for agent_name in [agent_a_name, agent_b_name]:
        prev_length = None
        for _, snake in present_by_turn[agent_name]:
            if snake is None:
                continue
            curr_length = snake.get("length", 0)
            if prev_length is not None and curr_length > prev_length:
                stats[agent_name]["food_eaten"] += curr_length - prev_length
            prev_length = curr_length

         # Averages
    for agent_name in [agent_a_name, agent_b_name]:
        if health_history[agent_name]:
            stats[agent_name]["avg_health"] = sum(health_history[agent_name]) / len(health_history[agent_name])
        if latency_history[agent_name]:
            stats[agent_name]["avg_latency"] = sum(latency_history[agent_name]) / len(latency_history[agent_name])

     #final alive
    last_turn_state = turn_states[-1]
    final_alive_names = {snake["name"] for snake in last_turn_state["board"]["snakes"]}
    stats[agent_a_name]["alive_final"] = int(agent_a_name in final_alive_names)
    stats[agent_b_name]["alive_final"] = int(agent_b_name in final_alive_names)

    def infer_death_cause(agent_name: str) -> str:
        # If alive at the end, no death
        if agent_name in final_alive_names:
            return "alive"

           # Find last turn where the snake was still present
        last_seen_turn = None
        last_seen_snake = None
        next_turn_state = None

        agent_turns = present_by_turn[agent_name]
        for i, (turn, snake) in enumerate(agent_turns):
            if snake is not None:
                last_seen_turn = turn
                last_seen_snake = snake
                if i + 1 < len(agent_turns):
                    next_turn_state = turn_states[i + 1]

        if last_seen_snake is None:
            return "unknown"

        board = turn_states[[t["turn"] for t in turn_states].index(last_seen_turn)]["board"]
        head = last_seen_snake.get("head", last_seen_snake["body"][0])
        body = last_seen_snake["body"]
        health = last_seen_snake.get("health", 0)
        hazards = board.get("hazards", [])

           # Heuristic death inference
        if health <= 1:
            return "starvation"

        if head in hazards and health <= 15:
            return "hazard"

        if head in body[1:]:
            return "self_collision"

        for other in board["snakes"]:
            if other["name"] != agent_name and head in other["body"]:
                return "body_collision"

        if next_turn_state is not None:
            next_snakes = next_turn_state["board"]["snakes"]
            next_heads = {}
            for snake in next_snakes:
                next_heads.setdefault((snake["head"]["x"], snake["head"]["y"]), []).append(snake)

               # if agent disappeared and other heads collided, call it head_to_head if plausible
            for heads_same_square in next_heads.values():
                if len(heads_same_square) > 1:
                    return "head_to_head"

        return "unknown"

    stats[agent_a_name]["death_cause"] = infer_death_cause(agent_a_name)
    stats[agent_b_name]["death_cause"] = infer_death_cause(agent_b_name)

    return {
        "winner_from_log": winner_name,
        "is_draw_from_log": is_draw,
        "survival_turns_a": stats[agent_a_name]["survival_turns"],
        "survival_turns_b": stats[agent_b_name]["survival_turns"],
        "final_length_a": stats[agent_a_name]["final_length"],
        "final_length_b": stats[agent_b_name]["final_length"],
        "max_length_a": stats[agent_a_name]["max_length"],
        "max_length_b": stats[agent_b_name]["max_length"],
        "food_eaten_a": stats[agent_a_name]["food_eaten"],
        "food_eaten_b": stats[agent_b_name]["food_eaten"],
        "hazard_turns_a": stats[agent_a_name]["hazard_turns"],
        "hazard_turns_b": stats[agent_b_name]["hazard_turns"],
        "hazard_entries_a": stats[agent_a_name]["hazard_entries"],
        "hazard_entries_b": stats[agent_b_name]["hazard_entries"],
        "avg_health_a": round(stats[agent_a_name]["avg_health"], 3),
        "avg_health_b": round(stats[agent_b_name]["avg_health"], 3),
        "min_health_a": stats[agent_a_name]["min_health"],
        "min_health_b": stats[agent_b_name]["min_health"],
        "avg_latency_a": round(stats[agent_a_name]["avg_latency"], 3),
        "avg_latency_b": round(stats[agent_b_name]["avg_latency"], 3),
        "death_cause_a": stats[agent_a_name]["death_cause"],
        "death_cause_b": stats[agent_b_name]["death_cause"],
        "alive_final_a": stats[agent_a_name]["alive_final"],
        "alive_final_b": stats[agent_b_name]["alive_final"],
    }

def extract_1v1_result(last_state: dict, agent_a_name: str, agent_b_name: str):
    snakes = last_state["board"]["snakes"]
    turn = last_state.get("turn", None)

    alive_names = [snake["name"] for snake in snakes]
    lengths = {snake["name"]: snake["length"] for snake in snakes}

    if agent_a_name in alive_names and agent_b_name not in alive_names:
        winner = agent_a_name
    elif agent_b_name in alive_names and agent_a_name not in alive_names:
        winner = agent_b_name
    elif agent_a_name in alive_names and agent_b_name in alive_names:
        # fallback tie-break by length
        len_a = lengths.get(agent_a_name, 0)
        len_b = lengths.get(agent_b_name, 0)
        if len_a > len_b:
            winner = agent_a_name
        elif len_b > len_a:
            winner = agent_b_name
        else:
            winner = "draw"
    else:
        winner = "draw"

    return {
        "winner": winner,
        "turns": turn,
        "length_a": lengths.get(agent_a_name, 0),
        "length_b": lengths.get(agent_b_name, 0),
        "alive_a": int(agent_a_name in alive_names),
        "alive_b": int(agent_b_name in alive_names),
    }



      # Match runner
def build_battlesnake_play_cmd(
    agents: List[AgentConfig],
    output_path: Path,
    seed: int,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    gamemode: str = DEFAULT_GAMEMODE,
    map_name: str = DEFAULT_MAP,
    food_spawn_chance: int = DEFAULT_FOOD_SPAWN_CHANCE,
    minimum_food: int = DEFAULT_MINIMUM_FOOD,
    timeout: int = DEFAULT_TIMEOUT,
) -> List[str]:
    cmd = [
        BATTLESNAKE_CMD, "play",
        "-W", str(width),
        "-H", str(height),
        "-g", gamemode,
        "-m", map_name,
    ]

    for agent in agents:
        cmd += ["--name", agent.name, "--url", f"http://127.0.0.1:{agent.port}"]

    cmd += [
        "--foodSpawnChance", str(food_spawn_chance),
        "--minimumFood", str(minimum_food),
        "--seed", str(seed),
        "--timeout", str(timeout),
        "--output", str(output_path),
    ]

    return cmd


def run_match_1v1(
    agent_a: AgentConfig,
    agent_b: AgentConfig,
    seed: int,
    output_dir: Path,
    swap_positions: bool = False,
) -> dict:
    if swap_positions:
        play_agents = [agent_b, agent_a]
    else:
        play_agents = [agent_a, agent_b]

    log_path = output_dir / f"game_{safe_name(agent_a.name)}_vs_{safe_name(agent_b.name)}_seed{seed}_swap{int(swap_positions)}.json"
    if log_path.exists():
        log_path.unlink()

    procs = [start_agent(play_agents[0]), start_agent(play_agents[1])]
    time.sleep(SERVER_START_WAIT)

    try:
        cmd = build_battlesnake_play_cmd(
            agents=play_agents,
            output_path=log_path,
            seed=seed,
        )
        print("Running:", " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print("Battlesnake play failed:")
            print(result.stdout)
            print(result.stderr)
            return {
                "agent_a": agent_a.name,
                "agent_b": agent_b.name,
                "seed": seed,
                "swap_positions": int(swap_positions),
                "error": 1,
            }

        last_state = load_last_state(log_path)
        if last_state is None:
            return {
                "agent_a": agent_a.name,
                "agent_b": agent_b.name,
                "seed": seed,
                "swap_positions": int(swap_positions),
                "error": 1,
            }

        res = extract_1v1_result(last_state, agent_a.name, agent_b.name)
        extra_stats = parse_match_statistics(log_path, agent_a.name, agent_b.name)

        row = {
            "agent_a": agent_a.name,
            "agent_b": agent_b.name,
            "seed": seed,
            "swap_positions": int(swap_positions),
            "winner": res["winner"],
            "turns": res["turns"],
            "length_a": res["length_a"],
            "length_b": res["length_b"],
            "alive_a": res["alive_a"],
            "alive_b": res["alive_b"],
            "error": 0,
            "agent_a_kind": agent_a.kind,
            "agent_b_kind": agent_b.kind,
            "agent_a_rave": agent_a.rave,
            "agent_b_rave": agent_b.rave,
            "agent_a_k": agent_a.k,
            "agent_b_k": agent_b.k,
            "agent_a_rollout_depth": agent_a.rollout_depth,
            "agent_b_rollout_depth": agent_b.rollout_depth,
            "agent_a_rollout_policy": agent_a.rollout_policy,
            "agent_b_rollout_policy": agent_b.rollout_policy,
            "agent_a_expansion_policy": agent_a.expansion_policy,
            "agent_b_expansion_policy": agent_b.expansion_policy,
            "agent_a_exploration_weight": agent_a.exploration_weight,
            "agent_b_exploration_weight": agent_b.exploration_weight,
            "agent_a_timeout_ms": agent_a.timeout_ms,
            "agent_b_timeout_ms": agent_b.timeout_ms,
        }

        row.update(extra_stats)
        return row

    finally:
        stop_agents(procs)



    # CSV helpers

def write_rows_to_csv(rows: List[dict], csv_path: Path) -> None:
    if not rows:
        return

    fieldnames = sorted({k for row in rows for k in row.keys()})
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)





# Elo

def expected_score(r_a: float, r_b: float) -> float:
    return 1.0 / (1.0 + 10 ** ((r_b - r_a) / 400.0))


def update_elo(r_a: float, r_b: float, score_a: float, k_factor: float = 32.0):
    exp_a = expected_score(r_a, r_b)
    exp_b = expected_score(r_b, r_a)

    new_a = r_a + k_factor * (score_a - exp_a)
    new_b = r_b + k_factor * ((1.0 - score_a) - exp_b)
    return new_a, new_b


def compute_elo(rows: List[dict], k_factor: float = 32.0) -> dict:
    ratings = {}

    for row in rows:
        if row.get("error", 0) != 0:
            continue

        a = row["agent_a"]
        b = row["agent_b"]
        ratings.setdefault(a, 1500.0)
        ratings.setdefault(b, 1500.0)

        winner = row["winner"]
        if winner == a:
            score_a = 1.0
        elif winner == b:
            score_a = 0.0
        else:
            score_a = 0.5

        ratings[a], ratings[b] = update_elo(ratings[a], ratings[b], score_a, k_factor)

    return ratings



    # Experiments
def run_pairwise_experiment(
    experiment_name: str,
    agent_a: AgentConfig,
    agent_b: AgentConfig,
    seeds: List[int],
) -> Path:
    exp_dir = OUTPUT_DIR / f"{timestamp_str()}_{safe_name(experiment_name)}"
    exp_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for seed in seeds:
        rows.append(run_match_1v1(agent_a, agent_b, seed, exp_dir, swap_positions=False))
        rows.append(run_match_1v1(agent_a, agent_b, seed, exp_dir, swap_positions=True))

    csv_path = exp_dir / "results.csv"
    write_rows_to_csv(rows, csv_path)

    ratings = compute_elo(rows)
    with (exp_dir / "elo.json").open("w", encoding="utf-8") as f:
        json.dump(ratings, f, indent=2)

    print(f"Saved results to {csv_path}")
    print("ELO:", ratings)
    return csv_path


def run_round_robin_experiment(
    experiment_name: str,
    agents: List[AgentConfig],
    seeds: List[int],
) -> Path:
    exp_dir = OUTPUT_DIR / f"{timestamp_str()}_{safe_name(experiment_name)}"
    exp_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for i in range(len(agents)):
        for j in range(i + 1, len(agents)):
            a = agents[i]
            b = agents[j]
            for seed in seeds:
                rows.append(run_match_1v1(a, b, seed, exp_dir, swap_positions=False))
                rows.append(run_match_1v1(a, b, seed, exp_dir, swap_positions=True))

    csv_path = exp_dir / "results.csv"
    write_rows_to_csv(rows, csv_path)

    ratings = compute_elo(rows)
    with (exp_dir / "elo.json").open("w", encoding="utf-8") as f:
        json.dump(ratings, f, indent=2)

    print(f"Saved round robin results to {csv_path}")
    print("ELO:", ratings)
    return csv_path




def make_heuristic_agent(name: str, port: int) -> AgentConfig:   #example agent builders
    return AgentConfig(
        name=name,
        script="agent_heuristic.py",
        port=port,
        kind="heuristic",
    )


def make_mcts_agent(
    name: str,
    port: int,
    rave: bool,
    k: int,
    rollout_depth: int,
    rollout_policy: str,
    expansion_policy: str,
    exploration_weight: float,
    timeout_ms: int,
) -> AgentConfig:
    return AgentConfig(
        name=name,
        script="agent_mcts.py",
        port=port,
        kind="mcts",
        rave=rave,
        k=k,
        rollout_depth=rollout_depth,
        rollout_policy=rollout_policy,
        expansion_policy=expansion_policy,
        exploration_weight=exploration_weight,
        timeout_ms=timeout_ms,
    )



      # Main (define experiments)
def main():
    seeds = list(range(1,11)) # 20 seeds -> 40 games per pair with swaps

   
        # Experiment 1: rollout policy
   
    # mcts_random = make_mcts_agent(
    #     name="MCTS_random",
    #     port=8000,
    #     rave=False,
    #     k=600,
    #     rollout_depth=10,
    #     rollout_policy="random",
    #     expansion_policy="random",
    #     exploration_weight=1.41,
    #     timeout_ms=700,
    # )

    # mcts_heuristic = make_mcts_agent(
    #     name="MCTS_heuristic",
    #     port=8001,
    #     rave=False,
    #     k=600,
    #     rollout_depth=10,
    #     rollout_policy="heuristic",
    #     expansion_policy="random",
    #     exploration_weight=1.41,
    #     timeout_ms=700,
    # )

    # run_pairwise_experiment(
    #     experiment_name="exp1_rollout_random_vs_heuristic",
    #     agent_a=mcts_random,
    #     agent_b=mcts_heuristic,
    #     seeds=seeds,
    # )


    
          #experiment 2: RAVE
    
    # mcts_heuristic_no_rave = make_mcts_agent(
    #     name="MCTS_noRAVE",
    #     port=8000,
    #     rave=False,
    #     k=600,
    #     rollout_depth=10,
    #     rollout_policy="heuristic",
    #     expansion_policy="random",
    #     exploration_weight=1.41,
    #     timeout_ms=700,
    # )

    # mcts_heuristic_rave = make_mcts_agent(
    #     name="MCTS_RAVE",
    #     port=8001,
    #     rave=True,
    #     k=600,
    #     rollout_depth=10,
    #     rollout_policy="heuristic",
    #     expansion_policy="random",
    #     exploration_weight=1.41,
    #     timeout_ms=700,
    # )

    # run_pairwise_experiment(
    #     experiment_name="exp2_rave_off_vs_on",
    #     agent_a=mcts_heuristic_no_rave,
    #     agent_b=mcts_heuristic_rave,
    #     seeds=seeds,
    # )

    
         # Experiment 3: expansion policy
    
    # mcts_rave_randomexp = make_mcts_agent(
    #     name="MCTS_RAVE_randExp",
    #     port=8000,
    #     rave=True,
    #     k=600,
    #     rollout_depth=10,
    #     rollout_policy="heuristic",
    #     expansion_policy="random",
    #     exploration_weight=1.41,
    #     timeout_ms=700,
    # )

    
    # mcts_rave_heurexp = make_mcts_agent(
    #     name="MCTS_RAVE_heurExp",
    #     port=8001,
    #     rave=True,
    #     k=600,
    #     rollout_depth=10,
    #     rollout_policy="heuristic",
    #     expansion_policy="heuristic",
    #     exploration_weight=1.41,
    #     timeout_ms=700,
    # )

    # run_pairwise_experiment(
    #     experiment_name="exp3_expansion_random_vs_heuristic",
    #     agent_a=mcts_rave_randomexp,
    #     agent_b=mcts_rave_heurexp,
    #     seeds=seeds,
    # )

    
          # Experiment 4: hyperparameter tests
    
    heuristic_baseline = make_heuristic_agent("Heuristic", 8001)

    # Default full MCTS settings used as reference
    default_rave = True
    default_k = 600
    default_rollout_policy = "heuristic"
    default_expansion_policy = "heuristic"
    default_exploration_weight = 1.41
    default_rollout_depth = 10
    default_timeout_ms = 700

             # 4A Exploration constant
    for exploration_weight in [0.7, 1.41]:
        tested_agent = make_mcts_agent(
            name=f"MCTS_full_c{str(exploration_weight).replace('.', '_')}",
            port=8000,
            rave=default_rave,
            k=default_k,
            rollout_depth=default_rollout_depth,
            rollout_policy=default_rollout_policy,
            expansion_policy=default_expansion_policy,
            exploration_weight=exploration_weight,
            timeout_ms=default_timeout_ms,
        )

        run_pairwise_experiment(
            experiment_name=f"exp4a_exploration_constant_{str(exploration_weight).replace('.', '_')}_vs_heuristic",
            agent_a=tested_agent,
            agent_b=heuristic_baseline,
            seeds=seeds,
        )

             #    4B rollout depth
    for rollout_depth in [5, 15]:
        tested_agent = make_mcts_agent(
            name=f"MCTS_full_d{rollout_depth}",
            port=8000,
            rave=default_rave,
            k=default_k,
            rollout_depth=rollout_depth,
            rollout_policy=default_rollout_policy,
            expansion_policy=default_expansion_policy,
            exploration_weight=default_exploration_weight,
            timeout_ms=default_timeout_ms,
        )

        run_pairwise_experiment(
            experiment_name=f"exp4b_rollout_depth_{rollout_depth}_vs_heuristic",
            agent_a=tested_agent,
            agent_b=heuristic_baseline,
            seeds=seeds,
        )

            # 4C. Timeout budget
    for timeout_ms in [700, 995]:
        tested_agent = make_mcts_agent(
            name=f"MCTS_full_t{timeout_ms}",
            port=8000,
            rave=default_rave,
            k=default_k,
            rollout_depth=default_rollout_depth,
            rollout_policy=default_rollout_policy,
            expansion_policy=default_expansion_policy,
            exploration_weight=default_exploration_weight,
            timeout_ms=timeout_ms,
        )

        run_pairwise_experiment(
            experiment_name=f"exp4c_timeout_{timeout_ms}_vs_heuristic",
            agent_a=tested_agent,
            agent_b=heuristic_baseline,
            seeds=seeds,
        )

    
       # Final round robin
    agents = [
        make_heuristic_agent("Heuristic", 8000),
        make_mcts_agent("MCTS_random", 8001, False, 600, 10, "random", "random", 1.41, 700),
        make_mcts_agent("MCTS_heuristic", 8000, False, 600, 10, "heuristic", "random", 1.41, 700),
        make_mcts_agent("MCTS_RAVE", 8001, True, 600, 10, "heuristic", "random", 1.41, 700),
        make_mcts_agent("MCTS_full", 8000, True, 600, 10, "heuristic", "heuristic", 1.41, 700),
    ]

    run_round_robin_experiment(
        experiment_name="final_round_robin",
        agents=agents,
        seeds=list(range(1, 11)),
    )


if __name__ == "__main__":
    main()
