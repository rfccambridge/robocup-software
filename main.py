import sys
import time
import numpy as np
import logging
import threading

from commands import RealWorldCoordTransformer
from commands import Commands
from comms import JohnRobot
from vision import SSLVisionDataProvider
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

    # initialize robots to give commands to
    #robot = JohnRobot()
    trans = RealWorldCoordTransformer()
    ROBOT_ID = 8 # this can change if coordinates are flipped in ssl-vision!
    # proportional scaling constant for distance differences
    SPEED_SCALE = .25
    MAX_SPEED = 50

    # TO TEST: factored out above stuff to class
    #commands = BasicCommands()

    goal_x = 500
    goal_y = 500

    while True:
        # set goal pos to click location on visualization window
        if viz.user_click_field:
            # y and x are flipped for shits
            goal_x, goal_y = viz.user_click_field

        # tell robot to go to goal position
        # TO TEST: replace all below code with commands.move
        # commands.move_robot(8, (goal_x, goal_y))
        if ROBOT_ID in gs._robots:
            gs.update_waypoint(ROBOT_ID, np.array([goal_x, goal_y]))
            pos = gs._robots[ROBOT_ID]
            og_x, og_y, og_w = pos
            delta = (goal_x - og_x, goal_y - og_y)
            # normalized offsets from robot's perspective
            robot_x, robot_y = trans.transform(og_w, delta)

            if VERBOSE:
                print("Original coordinates", og_x, og_y, og_w)
                print('Delta {}'.format(delta))
                print('(normalized diff) Robot X %f Robot Y %f' % (robot_x, robot_y))

            # move with speed proportional to delta
            speed = min(trans.magnitude(delta) * SPEED_SCALE, MAX_SPEED)
            #robot.move(speed * robot_y, speed * robot_x, 0, .2)
        else:
            print("no robot seen")
    # clean up comms
    #robot.die()
    #commands.die()

    # clean up threads
    viz.stop_visualizing()
    gs.stop_updating()
