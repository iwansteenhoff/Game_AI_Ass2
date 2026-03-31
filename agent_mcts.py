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
        
        self.untried_moves = ["up", "down", "left", "right"]









    def is_fully_expanded(self):
        return len(self.untried_moves) == 0
    



    def best_child(self, exploration_weight=1.41):

        best_score = -float('inf')
        best_node = None
        
        for child in self.children:

            if child.visits == 0:
                continue
                
            exploit = child.value / child.visits

            explore = exploration_weight * math.sqrt(math.log(self.visits) / child.visits)
            ucb1_score = exploit + explore
            
            if ucb1_score > best_score:
                best_score = ucb1_score

                best_node = child
                


        return best_node

def simulate_next_state(current_state: dict, move: str) -> dict:
             #future board state

    mock_state = copy.deepcopy(current_state)
    my_snake = mock_state["you"]
    my_head = my_snake["body"][0]


    next_head = {"x": my_head["x"], "y": my_head["y"]}
    if move == "up":
        next_head["y"] += 1
    elif move == "down":
        next_head["y"] -= 1
    elif move == "left":
        next_head["x"] -= 1
    elif move == "right":
        next_head["x"] += 1



    food_list = mock_state["board"]["food"]
    
    ate_food = False


    if next_head in food_list:
        ate_food = True
        food_list.remove(next_head)

    my_snake["body"].insert(0, next_head)

    if ate_food:
        my_snake["health"] = 100
        my_snake["length"] += 1
    else:
        my_snake["health"] -= 1
        my_snake["body"].pop()
    
    return mock_state


                            # MCTS loop

def get_mcts_move(game_state: dict, timeout_ms: float = 750.0) -> str:
    start_time = time.time() * 1000.0
    root_node = Node(game_state=game_state)
    simulations_run = 0

    
    while (time.time() * 1000.0) - start_time < timeout_ms:

        
           #  selection
        current_node = root_node
        while current_node.is_fully_expanded() and len(current_node.children) > 0:
            current_node = current_node.best_child()
        
        # Expansion
        if not current_node.is_fully_expanded():
            
            move_index = random.randrange(len(current_node.untried_moves))
            move_to_try = current_node.untried_moves.pop(move_index)

            new_state = simulate_next_state(current_node.state, move_to_try)

            child_node = Node(game_state = new_state, parent= current_node, move = move_to_try)
            current_node.children.append(child_node)
            current_node = child_node

            

        
        
                    # Simulation
    
    
        rollout_state = current_node.state

        rollout_d = 10

        for _ in range(rollout_d):
            
            my_snake = rollout_state.get("you")

            if my_snake is None or my_snake.get("health",0) <=0:
                break

            random_move = random.choice(["up", "down", "left", "right"])
            rollout_state = simulate_next_state(rollout_state, random_move)

        final_score = evaluate_board(rollout_state)

        
        
           #Backpropagation
        while current_node is not None:

            current_node.visits +=1
            current_node.value += final_score
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


def move(game_state: typing.Dict) -> typing.Dict:

    is_move_safe = {"up": True, "down": True, "left": True, "right": True}


    # We've included code to prevent your Battlesnake from moving backwards
    my_head = game_state["you"]["body"][0]  # Coordinates of your head
    my_neck = game_state["you"]["body"][1]  # Coordinates of your "neck"

    if my_neck["x"] < my_head["x"]:   # Neck is left of head, don't move left
        is_move_safe["left"] = False

    elif my_neck["x"] > my_head["x"]:  # Neck is right of head, don't move right
        is_move_safe["right"] = False

    elif my_neck["y"] < my_head["y"]:  # Neck is below head, don't move down
        is_move_safe["down"] = False

    elif my_neck["y"] > my_head["y"]:  # Neck is above head, don't move up
        is_move_safe["up"] = False

    # TODO: Step 1 - Prevent your Battlesnake from moving out of bounds
    board_width = game_state['board']['width']
    board_height = game_state['board']['height']

    
    if my_head["x"] == 0:
        is_move_safe["left"] = False

    if my_head["x"] == board_width - 1:
        is_move_safe["right"] = False
    
    if my_head["y"] == 0:
        is_move_safe["down"] = False

    if my_head["y"] == board_height - 1:
        is_move_safe["up"] = False




    # TODO: Step 2 - Prevent your Battlesnake from colliding with itself

    my_body = game_state['you']['body']

    next_right = {"x": my_head["x"]+1,"y": my_head["y"]}
    next_left =  {"x": my_head["x"]-1,"y": my_head["y"]}


    next_down =  {"x": my_head["x"],"y": my_head["y"]-1}
    next_up =    {"x": my_head["x"],"y": my_head["y"]+1}


    if next_right in my_body:
        is_move_safe["right"] = False

    
    if next_left in my_body:
        is_move_safe["left"] = False

    if next_down in my_body:
        is_move_safe["down"] = False

    if next_up in my_body:
        is_move_safe["up"]  = False

    

    # TODO: Step 3 - Prevent your Battlesnake from colliding with other Battlesnakes
    opponents = game_state['board']['snakes']
    

    for opponent in opponents:
        opponent_body = opponent["body"]

        if next_right in opponent_body:
            is_move_safe["right"] = False
        
        if next_left in opponent_body:
            is_move_safe["left"] = False

        if next_down in opponent_body:
            is_move_safe["down"] = False

        if next_up in opponent_body:
            is_move_safe["up"]  = False


    
    # Are there any safe moves left?
    safe_moves = []
    for move, isSafe in is_move_safe.items():
        if isSafe:
            safe_moves.append(move)

    if len(safe_moves) == 0:
        print(f"MOVE {game_state['turn']}: No safe moves detected! Moving down")
        return {"move": "down"}

    # TODO: Step 4 - Use MCTS 
    
    
    next_move = get_mcts_move(game_state, timeout_ms=700.0)  #  MCTS with 700ms to act
    

    

    if next_move not in safe_moves and len(safe_moves) > 0:
        print("MCTS picked a dangerous move! Overriding with a safe one.")
        next_move = random.choice(safe_moves)

    print(f"MOVE {game_state['turn']}: {next_move}")
    return {"move": next_move}



# Start server when `python main.py` is run
if __name__ == "__main__":
    from server import run_server
    
    run_server({"info": info, "start": start, "move": move, "end": end})
