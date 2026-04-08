# Welcome to
# __________         __    __  .__                               __
# \______   \_____ _/  |__/  |_|  |   ____   ______ ____ _____  |  | __ ____
#  |    |  _/\__  \\   __\   __\  | _/ __ \ /  ___//    \\__  \ |  |/ // __ \
#  |    |   \ / __ \|  |  |  | |  |_\  ___/ \___ \|   |  \/ __ \|    <\  ___/
#  |________/(______/__|  |__| |____/\_____>______>___|__(______/__|__\\_____>
#
# Heuristic Battlesnake agent using the same advanced heuristic implementation
# as the MCTS agent.
#
# For more info see docs.battlesnake.com

import argparse
import copy
import random
import typing


parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, default=8001)
args, _ = parser.parse_known_args()
PORT = args.port


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

        # Allow moving into our own tail if it will move away
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

            # avoid risky head-to-head if opponent is same length or larger
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


def move(game_state: typing.Dict) -> typing.Dict:
    safe_moves = get_legal_moves(game_state, game_state["you"])

    if len(safe_moves) == 0:
        print(f"MOVE {game_state['turn']}: No safe moves detected! Moving down")
        return {"move": "down"}

    best_move = None
    best_score = -float("inf")

    for candidate_move in safe_moves:
        next_state = simulate_next_state(game_state, candidate_move)
        score = evaluate_board(next_state)

        if score > best_score:
            best_score = score
            best_move = candidate_move

    if best_move is None:
        best_move = random.choice(safe_moves)

    print(f"MOVE {game_state['turn']}: {best_move} [advanced heuristic]")
    return {"move": best_move}


if __name__ == "__main__":
    from server import run_server

    try:
        run_server({"info": info, "start": start, "move": move, "end": end}, port=PORT)
    except TypeError:
        run_server({"info": info, "start": start, "move": move, "end": end})