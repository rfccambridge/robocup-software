import sys
import time
import numpy as np
import logging
import threading

from commands import Commands
from gamestate import GameState
from visualization import Visualizer

if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)
    VERBOSE = False

    # spin up gamestate to poll data
    gs = GameState()
    gs.start_updating()
    # spin up visualization to show robots on screen
    viz = Visualizer(gs)
    viz.start_visualizing()

    # intialize robots command interface
    commands = Commands(gs)

    goal_x = 1000
    goal_y = 500

    while True:
        # set goal pos to click location on visualization window
        if viz.user_click_field:
            goal_x, goal_y = viz.user_click_field

        # tell robot to go straight towards goal position
        commands.move_robot(8, (goal_x, goal_y))
        # TO TEST: tell robot to greedily pathfind to goal position
        # TODO: discuss parameters + more advanced pathfinding options: 
        # A*, time projection, RRT (see old c# codebase)
        # commands.greedy_path_find(8, (goal_x, goal_y))

    # clean up comms
    commands.die()

    # clean up threads
    viz.stop_visualizing()
    gs.stop_updating()
