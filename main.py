import sys
import time
import numpy as np
import logging
import threading

from gamestate import GameState
from vision import SSLVisionDataProvider
from strategy import Strategy
from visualization import Visualizer
from comms import Comms

if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)
    VERBOSE = False

    # initialize gamestate
    gamestate = GameState()
    gamestate.start_analyzing()

    # spin up visualization to show robots on screen
    viz = Visualizer(gamestate)
    viz.start_visualizing()
    
    # spin up ssl-vision data polling to update gamestate
    vision = SSLVisionDataProvider(gamestate)
    vision.start()
    
    # spin up comms to send commands to robots
    #comms = Comms(gamestate)
    #comms.start_sending()
    
    # intialize algorithm module
    strategy = Strategy(gamestate)

    goal_x = 3000
    goal_y = 1000

    while True:
        # set goal pos to click location on visualization window
        if viz.user_click_field:
            goal_x, goal_y = viz.user_click_field

        # tell robot to go straight towards goal position
        strategy.move_straight(8, (goal_x, goal_y, 0))
        # TO TEST: tell robot to greedily pathfind to goal position
        # TODO: discuss parameters + more advanced pathfinding options: 
        # A*, time projection, RRT (see old c# codebase)
        # strategy.greedy_path_find(8, (goal_x, goal_y))
        
        # yield to other threads
        time.sleep(0)


    # clean up comms
    strategy.die()

    # clean up threads
    viz.stop_visualizing()
    gamestate.stop_updating()
