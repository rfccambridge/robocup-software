import sys
import time
import numpy as np
import logging
import threading

from gamestate import GameState
from vision import SSLVisionDataProvider
from strategy import Strategy
from visualization import Visualizer

if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)
    VERBOSE = False

    # initialize gamestate
    gamestate = GameState()
    gamestate.start_analyzing()
    
    # spin up ssl-vision data polling to update gamestate
    vision = SSLVisionDataProvider(gamestate)
    vision.start()
    
    # spin up visualization to show robots on screen
    viz = Visualizer(gamestate)
    viz.start_visualizing()

    only_viz = True
    if only_viz:
        while True:
            pass
    
    # intialize robots command interface
    strategy = Strategy(gamestate)

    goal_x = 3000
    goal_y = 1000

    while True:
        # set goal pos to click location on visualization window
        if viz.user_click_field:
            goal_x, goal_y = viz.user_click_field

        # tell robot to go straight towards goal position
        strategy.move_robot(8, (goal_x, goal_y))
        # TO TEST: tell robot to greedily pathfind to goal position
        # TODO: discuss parameters + more advanced pathfinding options: 
        # A*, time projection, RRT (see old c# codebase)
        # strategy.greedy_path_find(8, (goal_x, goal_y))

    # clean up comms
    strategy.die()

    # clean up threads
    viz.stop_visualizing()
    gamestate.stop_updating()
