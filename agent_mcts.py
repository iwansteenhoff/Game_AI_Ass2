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

import random
import typing
import copy
import math
import time


class Node:
    def __init__(self, game_state: dict, parent=None, move=None):
        self.state = game_state
        self.parent = parent
        self.move = move
        self.children = []
        
        self.visits = 0
        self.value = 0.0
        
        self.untried_moves = get_legal_moves(game_state, game_state["you"])

        self.rave_visits = {m: 0 for m in ["up","down","left","right"]}
        self.rave_value  = {m: 0.0 for m in ["up","down","left","right"]}


    def is_fully_expanded(self):
        return len(self.untried_moves) == 0
    

    def best_child(self, rave=False, k=600, exploration_weight=1.41):

        best_score = -float('inf')
        best_node = None
        
        for child in self.children:

            if child.visits == 0:
                return child
            
            if rave: 
                q_mcts = child.value / child.visits
                if self.rave_visits[child.move] > 0:
                    q_rave = self.rave_value[child.move] / self.rave_visits[child.move]
                else:
                    q_rave = 0.0
                beta = k / (k + child.visits)
                combined = (1 - beta) * q_mcts + beta * q_rave
            
            else:
                combined = child.value / child.visits

            explore = exploration_weight * math.sqrt(math.log(self.visits + 1) / child.visits)
            score = combined + explore
            
            if score > best_score:
                best_score = score

                best_node = child
                


        return best_node

def simulate_next_state(current_state: dict, move: str) -> dict:
    import copy
    import random

    mock_state = copy.deepcopy(current_state)

    snakes = mock_state["board"]["snakes"]
    food_list = mock_state["board"]["food"]
    hazards = mock_state["board"].get("hazards", [])
    board_width = mock_state["board"]["width"]
    board_height = mock_state["board"]["height"]

    def next_head_from_move(head: dict, move: str) -> dict:
        new_head = {"x": head["x"], "y": head["y"]}
        if move == "up":
            new_head["y"] += 1
        elif move == "down":
            new_head["y"] -= 1
        elif move == "left":
            new_head["x"] -= 1
        elif move == "right":
            new_head["x"] += 1
        return new_head

    # Step 1: choose one move for every snake
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

    # Step 2: determine which snakes eat food
    ate_food = {}
    for snake in snakes:
        snake_id = snake["id"]
        next_head = planned_heads[snake_id]
        ate_food[snake_id] = (next_head is not None and next_head in food_list)

    # Step 3: build body-occupancy map for collision checks
    # Tail cell is removed from the blocking set if that snake does not eat,
    # because then the tail moves away this turn.
    occupied_cells = set()

    for snake in snakes:
        body = snake["body"]
        snake_id = snake["id"]

        if len(body) == 0:
            continue

        if ate_food[snake_id]:
            blocking_body = body[:]      # full body blocks if snake grows
        else:
            blocking_body = body[:-1]    # tail moves away if no food eaten

        for cell in blocking_body:
            occupied_cells.add((cell["x"], cell["y"]))

    # Step 4: mark snakes dead from wall/body/health/no-move
    dead_snake_ids = set()

    for snake in snakes:
        snake_id = snake["id"]
        next_head = planned_heads[snake_id]

        if next_head is None:
            dead_snake_ids.add(snake_id)
            continue

        # wall collision
        if next_head["x"] < 0 or next_head["x"] >= board_width:
            dead_snake_ids.add(snake_id)
            continue
        if next_head["y"] < 0 or next_head["y"] >= board_height:
            dead_snake_ids.add(snake_id)
            continue

        # body collision
        if (next_head["x"], next_head["y"]) in occupied_cells:
            dead_snake_ids.add(snake_id)
            continue

        # health after move
        new_health = snake["health"] - 1
        if next_head in hazards:
            new_health -= 14  
        if ate_food[snake_id]:
            new_health = 100

        if new_health <= 0:
            dead_snake_ids.add(snake_id)

    # Step 5: resolve head-to-head collisions
    head_positions = {}
    for snake in snakes:
        snake_id = snake["id"]
        if snake_id in dead_snake_ids:
            continue

        next_head = planned_heads[snake_id]
        pos = (next_head["x"], next_head["y"])
        head_positions.setdefault(pos, []).append(snake)

    for pos, snakes_on_pos in head_positions.items():
        if len(snakes_on_pos) <= 1:
            continue

        max_length = max(s["length"] for s in snakes_on_pos)
        winners = [s for s in snakes_on_pos if s["length"] == max_length]

        if len(winners) > 1:
            # equal length head-to-head: all die
            for s in snakes_on_pos:
                dead_snake_ids.add(s["id"])
        else:
            winner_id = winners[0]["id"]
            for s in snakes_on_pos:
                if s["id"] != winner_id:
                    dead_snake_ids.add(s["id"])

    # Step 6: apply updates to surviving snakes
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
                snake["health"] -= 14

        surviving_snakes.append(snake)

    # Step 7: remove eaten food
    mock_state["board"]["food"] = [
        food for food in food_list
        if (food["x"], food["y"]) not in consumed_food_positions
    ]

    # Step 8: write surviving snakes back to board
    mock_state["board"]["snakes"] = surviving_snakes

    # Step 9: update mock_state["you"]
    updated_you = None
    for snake in surviving_snakes:
        if snake["id"] == my_id:
            updated_you = snake
            break

    if updated_you is None:
        # Keep a minimal dead representation so evaluate_board can detect death
        dead_you = copy.deepcopy(mock_state["you"])
        dead_you["health"] = 0
        mock_state["you"] = dead_you
    else:
        mock_state["you"] = updated_you

    return mock_state


                            # MCTS loop

def get_mcts_move(game_state: dict, rave, k, timeout_ms: float = 750.0) -> str:
    start_time = time.time() * 1000.0
    root_node = Node(game_state=game_state)
    simulations_run = 0

    
    while (time.time() * 1000.0) - start_time < timeout_ms:

        
           #  selection
        current_node = root_node
        simulation_moves = []

        # Selection
        while current_node.is_fully_expanded() and len(current_node.children) > 0:
            current_node = current_node.best_child(rave=rave, k=k)
            if current_node.move is not None:
                simulation_moves.append(current_node.move)

        # Expansion
        if not current_node.is_fully_expanded():
            
            scored_moves = []

            for i, move in enumerate(current_node.untried_moves):
                next_state = simulate_next_state(current_node.state, move)
                score = evaluate_board(next_state)
                scored_moves.append((score, i))

            scored_moves.sort(reverse=True)

            top_k = scored_moves[:2]
            _, best_idx = random.choice(top_k)

            move_to_try = current_node.untried_moves.pop(best_idx)

            new_state = simulate_next_state(current_node.state, move_to_try)

            child_node = Node(game_state=new_state, parent=current_node, move=move_to_try)
            current_node.children.append(child_node)
            current_node = child_node
            simulation_moves.append(move_to_try)

        # Rollout
        rollout_state = current_node.state
        rollout_d = 10

        for _ in range(rollout_d):
            my_snake = rollout_state.get("you")

            if my_snake is None or my_snake.get("health", 0) <= 0:
                break

            legal_moves = get_legal_moves(rollout_state, rollout_state["you"])
            if not legal_moves:
                break

            best_rollout_move = None
            best_rollout_score = -float("inf")

            for move in legal_moves:
                next_state = simulate_next_state(rollout_state, move)
                score = evaluate_board(next_state)
                if score > best_rollout_score:
                    best_rollout_score = score
                    best_rollout_move = move

            simulation_moves.append(best_rollout_move)
            rollout_state = simulate_next_state(rollout_state, best_rollout_move)

        final_score = evaluate_board(rollout_state)

        # Backpropagation
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

# info is called when you create your Battlesnake on play.battlesnake.com
# and controls your Battlesnake's appearance
# TIP: If you open your Battlesnake URL in a browser you should see this data
def info() -> typing.Dict:
    print("INFO")

    return {
        "apiversion": "1",
        "author": "",  # TODO: Your Battlesnake Username
        "color": "#888888",  # TODO: Choose color
        "head": "default",  # TODO: Choose head
        "tail": "default",  # TODO: Choose tail
    }


# start is called when your Battlesnake begins a game
def start(game_state: typing.Dict):
    print("GAME START")


# end is called when your Battlesnake finishes a game
def end(game_state: typing.Dict):
    print("GAME OVER\n")


# move is called on every turn and returns your next move
# Valid moves are "up", "down", "left", or "right"
# See https://docs.battlesnake.com/api/example-move for available data

def evaluate_board(game_state: dict) -> float:
    score = 0.0
    
             # Survival (highest priority)
    my_snake = game_state.get("you")
    
               
    if my_snake is None or my_snake.get("health", 0) <= 0:        #  abandon if the state results in our death
        return -100000.0  
        


        
    my_head = my_snake["body"][0]

    board_width = game_state['board']['width']
    board_height = game_state['board']['height']
    


          # not hit a wall
    if my_head["x"] < 0 or my_head["x"] >= board_width or my_head["y"] < 0 or my_head["y"] >= board_height:
        return -100000.0
        
            # not hit own body
    if my_head in my_snake["body"][1:]:
        return -100000.0



    for snake in game_state['board']['snakes']:
        


        if snake['id'] != my_snake['id']:
            if my_head in snake['body']:
                return -100000.0


    my_health = my_snake["health"]
    my_length = my_snake["length"]
    
    # Positive rewards
    
    score += my_length * 100.0       # Length is heavily weighted (winning criteria)
    

    # Health 
    score += my_health * 1.0 
    

              #   penalties
    food_list = game_state["board"]["food"]


    if len(food_list) > 0:

        min_distance = float('inf')
        
        # Loop through all food for closest one
        for food in food_list:
            distance = abs(my_head["x"] - food["x"]) + abs(my_head["y"] - food["y"])
            if distance < min_distance:
                min_distance = distance
                
        
        
        score -= min_distance * 2.0


    
    
    hazards = game_state["board"]["hazards"]
    if my_head in hazards:


        score -= 500.0  
    
    return score

def get_legal_moves(game_state: dict, snake: dict) -> list[str]:
    head = snake["body"][0]
    body = snake["body"]

    board_width = game_state["board"]["width"]
    board_height = game_state["board"]["height"]

    legal_moves = []

    directions = {
        "up":    {"x": head["x"],     "y": head["y"] + 1},
        "down":  {"x": head["x"],     "y": head["y"] - 1},
        "left":  {"x": head["x"] - 1, "y": head["y"]},
        "right": {"x": head["x"] + 1, "y": head["y"]},
    }

    for move, next_head in directions.items():

        # 1. Out of bounds
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

            other_head = other_snake["body"][0]

            # Manhattan distance 1 = possible head-to-head
            if abs(next_head["x"] - other_head["x"]) + abs(next_head["y"] - other_head["y"]) == 1:
                if other_snake["length"] >= snake["length"]:
                    collision = True
                    break

        if collision:
            continue

        legal_moves.append(move)

    return legal_moves


def move(game_state: typing.Dict) -> typing.Dict:

    rave=True
    k=600

    safe_moves = get_legal_moves(game_state, game_state["you"])

    if len(safe_moves) == 0:
        print(f"MOVE {game_state['turn']}: No safe moves detected! Moving down")
        return {"move": "down"}

    # TODO: Step 4 - Use MCTS 
    
    
    next_move = get_mcts_move(game_state, rave=rave, k=k, timeout_ms=700.0)  #  MCTS with 700ms to act
    

    

    if next_move not in safe_moves and len(safe_moves) > 0:
        print("MCTS picked a dangerous move! Overriding with a safe one.")
        next_move = random.choice(safe_moves)

    print(f"MOVE {game_state['turn']}: {next_move}")
    return {"move": next_move}



# Start server when `python main.py` is run
if __name__ == "__main__":
    from server import run_server
    
    run_server({"info": info, "start": start, "move": move, "end": end})
