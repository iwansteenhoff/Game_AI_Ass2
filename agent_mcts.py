# Welcome to
# __________         __    __  .__                               __
# \______   \_____ _/  |__/  |_|  |   ____   ______ ____ _____  |  | __ ____
#  |    |  _/\__  \\   __\   __\  | _/ __ \ /  ___//    \\__  \ |  |/ // __ \
#  |    |   \ / __ \|  |  |  | |  |_\  ___/ \___ \|   |  \/ __ \|    <\  ___/
#  |________/(______/__|  |__| |____/\_____>______>___|__(______/__|__\\_____>
#
# This file can be a nice home for your Battlesnake logic and helper functions.
#
# To get you started we've included code to prevent your Battlesnake from moving backwards.
# For more info see docs.battlesnake.com

import argparse
import copy
import math
import random
import typing


def str_to_bool(value: str) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y", "on"}


parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, default=8000)
parser.add_argument("--rave", type=str, default="true")
parser.add_argument("--k", type=int, default=600)
parser.add_argument("--rollout-depth", type=int, default=10)
parser.add_argument(
    "--rollout-policy",
    type=str,
    choices=["random", "heuristic"],
    default="heuristic",
)
parser.add_argument(
    "--expansion-policy",
    type=str,
    choices=["random", "heuristic", "topk"],
    default="topk",
)
parser.add_argument("--exploration-weight", type=float, default=1.41)
parser.add_argument("--timeout-ms", type=float, default=700.0)
parser.add_argument("--top-k-expansion", type=int, default=2)

ARGS, _UNKNOWN = parser.parse_known_args()

PORT = ARGS.port
RAVE_ENABLED = str_to_bool(ARGS.rave)
RAVE_K = ARGS.k
ROLLOUT_DEPTH = ARGS.rollout_depth
ROLLOUT_POLICY = ARGS.rollout_policy
EXPANSION_POLICY = ARGS.expansion_policy
EXPLORATION_WEIGHT = ARGS.exploration_weight
TIMEOUT_MS = ARGS.timeout_ms
TOP_K_EXPANSION = max(1, ARGS.top_k_expansion)


class Node:
    def __init__(self, game_state: dict, parent=None, move=None):
        self.state = game_state
        self.parent = parent
        self.move = move
        self.children = []

        self.visits = 0
        self.value = 0.0

        self.untried_moves = get_legal_moves(game_state, game_state["you"])

        self.rave_visits = {m: 0 for m in ["up", "down", "left", "right"]}
        self.rave_value = {m: 0.0 for m in ["up", "down", "left", "right"]}

    def is_fully_expanded(self):
        return len(self.untried_moves) == 0

    def best_child(self, rave=False, k=600, exploration_weight=1.41):
        unvisited_children = [child for child in self.children if child.visits == 0]
        if unvisited_children:
            return random.choice(unvisited_children)

        best_score = -float("inf")
        best_node = None

        for child in self.children:
            q_mcts = child.value / child.visits

            if rave:
                if self.rave_visits[child.move] > 0:
                    q_rave = self.rave_value[child.move] / self.rave_visits[child.move]
                else:
                    q_rave = 0.0

                beta = k / (k + child.visits)
                combined = (1 - beta) * q_mcts + beta * q_rave
            else:
                combined = q_mcts

            explore = exploration_weight * math.sqrt(
                math.log(self.visits + 1) / child.visits
            )
            score = combined + explore

            if score > best_score:
                best_score = score
                best_node = child

        return best_node


def get_hazard_stack_count(turn: int) -> int:
    if turn < 26:
        return 0
    if turn < 101:
        return 1 + (turn - 26) // 25
    if turn < 176:
        return 4

    drain_step = (turn - 176) // 25
    return max(0, 3 - drain_step)


def get_hazard_damage(turn: int) -> int:
    return 14 * get_hazard_stack_count(turn)


def get_legal_moves(game_state: dict, snake: dict) -> list[str]:
    head = snake["body"][0]
    body = snake["body"]

    board_width = game_state["board"]["width"]
    board_height = game_state["board"]["height"]

    legal_moves = []

    directions = {
        "up": {"x": head["x"], "y": head["y"] + 1},
        "down": {"x": head["x"], "y": head["y"] - 1},
        "left": {"x": head["x"] - 1, "y": head["y"]},
        "right": {"x": head["x"] + 1, "y": head["y"]},
    }

    for move, next_head in directions.items():
        if next_head["x"] < 0 or next_head["x"] >= board_width:
            continue
        if next_head["y"] < 0 or next_head["y"] >= board_height:
            continue

        if next_head in body[:-1]:
            continue

        collision = False
        for other_snake in game_state["board"]["snakes"]:
            if other_snake["id"] == snake["id"]:
                continue

            # body collision with other snake body excluding tail
            if next_head in other_snake["body"][:-1]:
                collision = True
                break

            # possible bad head-to-head
            other_head = other_snake["body"][0]
            if abs(next_head["x"] - other_head["x"]) + abs(next_head["y"] - other_head["y"]) == 1:
                if other_snake["length"] >= snake["length"]:
                    collision = True
                    break

        if collision:
            continue

        legal_moves.append(move)

    return legal_moves


def simulate_next_state(current_state: dict, move: str) -> dict:
    mock_state = copy.deepcopy(current_state)

    snakes = mock_state["board"]["snakes"]
    food_list = mock_state["board"]["food"]
    hazards = mock_state["board"].get("hazards", [])
    board_width = mock_state["board"]["width"]
    board_height = mock_state["board"]["height"]

    next_turn = mock_state.get("turn", 0) + 1
    hazard_damage = get_hazard_damage(next_turn)

    def next_head_from_move(head: dict, move_name: str) -> dict:
        new_head = {"x": head["x"], "y": head["y"]}
        if move_name == "up":
            new_head["y"] += 1
        elif move_name == "down":
            new_head["y"] -= 1
        elif move_name == "left":
            new_head["x"] -= 1
        elif move_name == "right":
            new_head["x"] += 1
        return new_head

    chosen_moves = {}
    planned_heads = {}

    my_id = mock_state["you"]["id"]

    for snake in snakes:
        snake_id = snake["id"]
        head = snake["body"][0]

        if snake_id == my_id:
            chosen_move = move
        else:
            legal_moves = get_legal_moves(mock_state, snake)
            if legal_moves:
                chosen_move = random.choice(legal_moves)
            else:
                chosen_move = None

        chosen_moves[snake_id] = chosen_move

        if chosen_move is None:
            planned_heads[snake_id] = None
        else:
            planned_heads[snake_id] = next_head_from_move(head, chosen_move)

    ate_food = {}
    for snake in snakes:
        snake_id = snake["id"]
        next_head = planned_heads[snake_id]
        ate_food[snake_id] = (next_head is not None and next_head in food_list)

    occupied_cells = set()

    for snake in snakes:
        body = snake["body"]
        snake_id = snake["id"]

        if not body:
            continue

        if ate_food[snake_id]:
            blocking_body = body[:]
        else:
            blocking_body = body[:-1]

        for cell in blocking_body:
            occupied_cells.add((cell["x"], cell["y"]))

    dead_snake_ids = set()

    for snake in snakes:
        snake_id = snake["id"]
        next_head = planned_heads[snake_id]

        if next_head is None:
            dead_snake_ids.add(snake_id)
            continue

        if next_head["x"] < 0 or next_head["x"] >= board_width:
            dead_snake_ids.add(snake_id)
            continue
        if next_head["y"] < 0 or next_head["y"] >= board_height:
            dead_snake_ids.add(snake_id)
            continue

        if (next_head["x"], next_head["y"]) in occupied_cells:
            dead_snake_ids.add(snake_id)
            continue

        new_health = snake["health"] - 1
        if next_head in hazards:
            new_health -= hazard_damage
        if ate_food[snake_id]:
            new_health = 100

        if new_health <= 0:
            dead_snake_ids.add(snake_id)

    head_positions = {}
    for snake in snakes:
        snake_id = snake["id"]
        if snake_id in dead_snake_ids:
            continue

        next_head = planned_heads[snake_id]
        pos = (next_head["x"], next_head["y"])
        head_positions.setdefault(pos, []).append(snake)

    for _, snakes_on_pos in head_positions.items():
        if len(snakes_on_pos) <= 1:
            continue

        max_length = max(s["length"] for s in snakes_on_pos)
        winners = [s for s in snakes_on_pos if s["length"] == max_length]

        if len(winners) > 1:
            for s in snakes_on_pos:
                dead_snake_ids.add(s["id"])
        else:
            winner_id = winners[0]["id"]
            for s in snakes_on_pos:
                if s["id"] != winner_id:
                    dead_snake_ids.add(s["id"])

    surviving_snakes = []
    consumed_food_positions = set()

    for snake in snakes:
        snake_id = snake["id"]

        if snake_id in dead_snake_ids:
            continue

        next_head = planned_heads[snake_id]
        did_eat = ate_food[snake_id]

        snake["body"].insert(0, next_head)

        if did_eat:
            snake["health"] = 100
            snake["length"] += 1
            consumed_food_positions.add((next_head["x"], next_head["y"]))
        else:
            snake["body"].pop()
            snake["health"] -= 1
            if next_head in hazards:
                snake["health"] -= hazard_damage

        surviving_snakes.append(snake)

    mock_state["board"]["food"] = [
        food for food in food_list
        if (food["x"], food["y"]) not in consumed_food_positions
    ]

    mock_state["board"]["snakes"] = surviving_snakes

    updated_you = None
    for snake in surviving_snakes:
        if snake["id"] == my_id:
            updated_you = snake
            break

    if updated_you is None:
        dead_you = copy.deepcopy(mock_state["you"])
        dead_you["health"] = 0
        mock_state["you"] = dead_you
    else:
        mock_state["you"] = updated_you

    mock_state["turn"] = next_turn
    return mock_state


def evaluate_board(game_state: dict) -> float:
    score = 0.0

    my_snake = game_state.get("you")

    if my_snake is None or my_snake.get("health", 0) <= 0:
        return -100000.0

    my_head = my_snake["body"][0]

    board_width = game_state["board"]["width"]
    board_height = game_state["board"]["height"]

    if my_head["x"] < 0 or my_head["x"] >= board_width or my_head["y"] < 0 or my_head["y"] >= board_height:
        return -100000.0

    if my_head in my_snake["body"][1:]:
        return -100000.0

    for snake in game_state["board"]["snakes"]:
        if snake["id"] != my_snake["id"]:
            if my_head in snake["body"]:
                return -100000.0

    my_health = my_snake["health"]
    my_length = my_snake["length"]
    turn = game_state.get("turn", 0)

    score += my_length * 100.0
    score += my_health * 1.0

    food_list = game_state["board"]["food"]
    if food_list:
        min_distance = float("inf")
        for food in food_list:
            distance = abs(my_head["x"] - food["x"]) + abs(my_head["y"] - food["y"])
            if distance < min_distance:
                min_distance = distance
        score -= min_distance * 2.0

    hazards = game_state["board"].get("hazards", [])
    if my_head in hazards:
        hazard_damage = get_hazard_damage(turn)
        score -= 1000.0 + 100.0 * hazard_damage
        if my_health <= hazard_damage + 5:
            score -= 20000.0

    return score


def choose_expansion_move(current_node: Node) -> str:
    if EXPANSION_POLICY == "random":
        move_index = random.randrange(len(current_node.untried_moves))
        return current_node.untried_moves.pop(move_index)

    scored_moves = []
    for i, move in enumerate(current_node.untried_moves):
        next_state = simulate_next_state(current_node.state, move)
        score = evaluate_board(next_state)
        scored_moves.append((score, i))

    scored_moves.sort(reverse=True)

    if EXPANSION_POLICY == "heuristic":
        _, best_idx = scored_moves[0]
        return current_node.untried_moves.pop(best_idx)

    # topk
    top_k = scored_moves[: min(TOP_K_EXPANSION, len(scored_moves))]
    _, best_idx = random.choice(top_k)
    return current_node.untried_moves.pop(best_idx)


def choose_rollout_move(rollout_state: dict, legal_moves: list[str]) -> str:
    if ROLLOUT_POLICY == "random":
        return random.choice(legal_moves)

    best_rollout_move = None
    best_rollout_score = -float("inf")

    for move in legal_moves:
        next_state = simulate_next_state(rollout_state, move)
        score = evaluate_board(next_state)
        if score > best_rollout_score:
            best_rollout_score = score
            best_rollout_move = move

    return best_rollout_move


def get_mcts_move(game_state: dict, rave: bool, k: int, timeout_ms: float = 750.0) -> str:
    import time

    start_time = time.time() * 1000.0
    root_node = Node(game_state=game_state)
    simulations_run = 0

    while (time.time() * 1000.0) - start_time < timeout_ms:
        current_node = root_node
        simulation_moves = []

        while current_node.is_fully_expanded() and len(current_node.children) > 0:
            current_node = current_node.best_child(
                rave=rave,
                k=k,
                exploration_weight=EXPLORATION_WEIGHT,
            )
            if current_node.move is not None:
                simulation_moves.append(current_node.move)

        if not current_node.is_fully_expanded():
            move_to_try = choose_expansion_move(current_node)

            new_state = simulate_next_state(current_node.state, move_to_try)

            child_node = Node(game_state=new_state, parent=current_node, move=move_to_try)
            current_node.children.append(child_node)
            current_node = child_node
            simulation_moves.append(move_to_try)

        rollout_state = current_node.state

        for _ in range(ROLLOUT_DEPTH):
            my_snake = rollout_state.get("you")

            if my_snake is None or my_snake.get("health", 0) <= 0:
                break

            legal_moves = get_legal_moves(rollout_state, rollout_state["you"])
            if not legal_moves:
                break

            rollout_move = choose_rollout_move(rollout_state, legal_moves)
            simulation_moves.append(rollout_move)
            rollout_state = simulate_next_state(rollout_state, rollout_move)

        final_score = evaluate_board(rollout_state)

        unique_moves = set(simulation_moves)

        while current_node is not None:
            current_node.visits += 1
            current_node.value += final_score

            if rave:
                for move in unique_moves:
                    current_node.rave_visits[move] += 1
                    current_node.rave_value[move] += final_score

            current_node = current_node.parent

        simulations_run += 1

    print(f"MCTS ran {simulations_run} simulations in {timeout_ms}ms!")
    best_move = "up"
    most_visits = -1

    for child in root_node.children:
        if child.visits > most_visits:
            most_visits = child.visits
            best_move = child.move

    return best_move


def info() -> typing.Dict:
    print("INFO")
    return {
        "apiversion": "1",
        "author": "",
        "color": "#888888",
        "head": "default",
        "tail": "default",
    }


def start(game_state: typing.Dict):
    print("GAME START")


def end(game_state: typing.Dict):
    print("GAME OVER\n")


def move(game_state: typing.Dict) -> typing.Dict:
    safe_moves = get_legal_moves(game_state, game_state["you"])

    if len(safe_moves) == 0:
        print(f"MOVE {game_state['turn']}: No safe moves detected! Moving down")
        return {"move": "down"}

    next_move = get_mcts_move(
        game_state,
        rave=RAVE_ENABLED,
        k=RAVE_K,
        timeout_ms=TIMEOUT_MS,
    )

    if next_move not in safe_moves and safe_moves:
        print("MCTS picked a dangerous move! Overriding with a safe one.")
        next_move = random.choice(safe_moves)

    print(
        f"MOVE {game_state['turn']}: {next_move} "
        f"[rave={RAVE_ENABLED}, k={RAVE_K}, rollout_depth={ROLLOUT_DEPTH}, "
        f"rollout_policy={ROLLOUT_POLICY}, expansion_policy={EXPANSION_POLICY}, "
        f"c={EXPLORATION_WEIGHT}, timeout_ms={TIMEOUT_MS}]"
    )
    return {"move": next_move}


if __name__ == "__main__":
    from server import run_server

    try:
        run_server(
            {"info": info, "start": start, "move": move, "end": end},
            port=PORT,
        )
    except TypeError:
        run_server({"info": info, "start": start, "move": move, "end": end})