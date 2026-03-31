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
    
    
    my_snake = game_state.get("you")
    
          # abandon if the state results in our death
    if my_snake is None or my_snake.get("health", 0) <= 0:
        return -100000.0  
        


            #Gather states
    my_head = my_snake["body"][0]
    my_health = my_snake["health"]
    my_length = my_snake["length"]
    

    
         # positive rewards
    
    score += my_length * 100.0 
    


    
    score += my_health * 1.0 
    
    
    food_list = game_state["board"]["food"]      #  Penalties


    if len(food_list) > 0:
        min_distance = float('inf')
        
            #Loop through all food to find the closest one
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

    if my_neck["x"] < my_head["x"]:  # Neck is left of head, don't move left
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

        # Choose a random move from the safe ones
    
    
    # TODO: Step 4 - Move towards food instead of random, to regain health and survive longer
    
    best_move = random.choice(safe_moves)     

    best_score = -float('inf')            # Start with the lowest possible score

    for move in safe_moves:
        


        next_head = {"x": my_head["x"], "y": my_head["y"]}
        if move == "up":
            next_head["y"] += 1


        elif move == "down":
            next_head["y"] -= 1
        elif move == "left":
            next_head["x"] -= 1
        elif move == "right":
            next_head["x"] += 1

        
        mock_state = copy.deepcopy(game_state)
        
        
        mock_state["you"]["body"].insert(0, next_head)   # Add the new head
        mock_state["you"]["body"].pop()       #remove the tail tip
        
        
        score = evaluate_board(mock_state)

        
        if score > best_score:
            best_score = score
            best_move = move
            
    next_move = best_move

    
    

    print(f"MOVE {game_state['turn']}: {next_move}")
    return {"move": next_move}


# Start server when `python main.py` is run
if __name__ == "__main__":
    from server import run_server
    
    run_server({"info": info, "start": start, "move": move, "end": end})
